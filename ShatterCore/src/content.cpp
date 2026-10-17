// ShatterCore — ContentDB: carga dos CSV, validação (Finalize) e lookups.
// Regras: sem exceções; IDs só em std::unordered_map para busca (nunca iterado); listas em ordem do CSV.
#include "shatter/content.h"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <system_error>

#include "csv.h"
#include "numtext.h"

namespace shatter {

bool ParseSkillShape(std::string_view text, SkillShape& out) {
    static constexpr struct { const char* n; SkillShape s; } kShapes[] = {
        {"melee", SkillShape::Melee},     {"cone", SkillShape::Cone}, {"projectile", SkillShape::Projectile},
        {"area", SkillShape::Area},       {"dash", SkillShape::Dash}, {"self", SkillShape::Self},
        {"channel", SkillShape::Channel}, {"trap", SkillShape::Trap},
    };
    for (const auto& e : kShapes) {
        if (text == e.n) { out = e.s; return true; }
    }
    return false;
}

bool ParseIdleCalibration(std::string_view text, IdleCalibration& out) {
    if (text == "none") { out = IdleCalibration::None; return true; }
    if (text == "manual_estimate") { out = IdleCalibration::ManualEstimate; return true; }
    if (text == "bot_parity") { out = IdleCalibration::BotParity; return true; }
    return false;
}

const char* ToString(IdleCalibration c) {
    switch (c) {
        case IdleCalibration::None: return "none";
        case IdleCalibration::ManualEstimate: return "manual_estimate";
        case IdleCalibration::BotParity: return "bot_parity";
    }
    return "none";
}

bool ParsePotionKind(std::string_view text, PotionKind& out) {
    if (text == "heal") { out = PotionKind::Heal; return true; }
    if (text == "barrier") { out = PotionKind::Barrier; return true; }
    return false;
}

namespace {

using detail::CsvRow;
using detail::CsvTable;

constexpr std::size_t kRuleKeyCount = 62 + 18;

// --- tabela de chaves de rules.csv (faixas = validação estrutural do 06_dados.md, não balanceamento) ---
struct RuleDef {
    const char* key;
    char type;  // 'd' número, 'i' inteiro, 'b' booleano
    double lo;
    double hi;
    bool loExclusive;
    void (*set)(RulesConstants&, double);
};

constexpr double kInf = 1e300;

const RuleDef kRuleDefs[kRuleKeyCount] = {
    {"crit_multiplier_base", 'd', 1, kInf, false, [](RulesConstants& r, double v) { r.critMultiplierBase = v; }},
    {"evasion_cap", 'd', 0, 1, false, [](RulesConstants& r, double v) { r.evasionCap = v; }},
    {"block_cap", 'd', 0, 1, false, [](RulesConstants& r, double v) { r.blockCap = v; }},
    {"block_mitigation", 'd', 0, 1, false, [](RulesConstants& r, double v) { r.blockMitigation = v; }},
    {"resist_cap", 'd', 0, 0.95, false, [](RulesConstants& r, double v) { r.resistCap = v; }},
    {"resist_floor", 'd', -5, 0, false, [](RulesConstants& r, double v) { r.resistFloor = v; }},
    {"armor_damage_factor", 'd', 0, kInf, true, [](RulesConstants& r, double v) { r.armorDamageFactor = v; }},
    {"armor_max_reduction", 'd', 0, 0.99, false, [](RulesConstants& r, double v) { r.armorMaxReduction = v; }},
    {"trigger_icd_min", 'd', 0.25, 10, false, [](RulesConstants& r, double v) { r.triggerInternalCooldown = v; }},
    {"cooldown_min", 'd', 0.1, 10, false, [](RulesConstants& r, double v) { r.minCooldown = v; }},
    {"realtime_step", 'd', 0, 0.1, true, [](RulesConstants& r, double v) { r.fixedStep = v; }},
    {"sim_step", 'd', 0, 1, true, [](RulesConstants& r, double v) { r.simStep = v; }},
    {"sim_step_fast", 'd', 0, 1, true, [](RulesConstants& r, double v) { r.simStepFastNonBoss = v; }},
    {"sim_fast_enabled", 'b', 0, 1, false, [](RulesConstants& r, double v) { r.useFastStepNonBoss = v != 0.0; }},
    {"max_offline_hours", 'd', 0, 48, true, [](RulesConstants& r, double v) { r.maxOfflineHours = v; }},
    {"max_expedition_hours", 'd', 0, 48, true, [](RulesConstants& r, double v) { r.maxExpeditionHours = v; }},
    {"min_expedition_hours", 'd', 0, 48, true, [](RulesConstants& r, double v) { r.minExpeditionHours = v; }},
    {"max_ai_rules", 'i', 1, 16, false, [](RulesConstants& r, double v) { r.maxAiRules = static_cast<int>(v); }},
    {"max_rares_per_expedition", 'i', 0, 100, false,
     [](RulesConstants& r, double v) { r.maxRaresPerExpedition = static_cast<int>(v); }},
    {"xp_cap_levels_above_area", 'i', 0, 10, false,
     [](RulesConstants& r, double v) { r.xpLevelCapAboveArea = static_cast<int>(v); }},
    {"ai_base_dodge", 'd', 0, 1, false, [](RulesConstants& r, double v) { r.aiBaseDodgeTelegraphed = v; }},
    {"retreat_life_fraction", 'd', 0, 1, false, [](RulesConstants& r, double v) { r.retreatLifeFraction = v; }},
    {"vigor_h1_4", 'd', 0, 1, false, [](RulesConstants& r, double v) { r.vigorByBand[0] = v; }},
    {"vigor_h5_8", 'd', 0, 1, false, [](RulesConstants& r, double v) { r.vigorByBand[1] = v; }},
    {"vigor_h9_12", 'd', 0, 1, false, [](RulesConstants& r, double v) { r.vigorByBand[2] = v; }},
    {"vigor_band_hours", 'd', 0, 12, true, [](RulesConstants& r, double v) { r.vigorBandHours = v; }},
    {"fervor_xp_mult", 'd', 1, kInf, false, [](RulesConstants& r, double v) { r.fervorXpMult = v; }},
    {"fervor_gold_mat_mult", 'd', 1, kInf, false, [](RulesConstants& r, double v) { r.fervorGoldMatMult = v; }},
    {"fervor_rare_mult", 'd', 1, kInf, false, [](RulesConstants& r, double v) { r.fervorRareChanceMult = v; }},
    {"charges_max", 'i', 1, 100, false, [](RulesConstants& r, double v) { r.chargesMax = static_cast<int>(v); }},
    {"charges_per_hour", 'i', 1, 12, false, [](RulesConstants& r, double v) { r.chargesPerHour = static_cast<int>(v); }},
    {"charges_clear_area", 'i', 0, 12, false,
     [](RulesConstants& r, double v) { r.chargesClearArea = static_cast<int>(v); }},
    {"charges_boss", 'i', 0, 12, false, [](RulesConstants& r, double v) { r.chargesBoss = static_cast<int>(v); }},
    {"charges_new_area", 'i', 0, 12, false, [](RulesConstants& r, double v) { r.chargesNewArea = static_cast<int>(v); }},
    {"charges_daily_rest", 'i', 0, 12, false,
     [](RulesConstants& r, double v) { r.chargesDailyRest = static_cast<int>(v); }},
    {"clock_rollback_tolerance_s", 'd', 0, kInf, false,
     [](RulesConstants& r, double v) { r.clockRollbackToleranceSec = v; }},
    {"steam_clock_max_skew_s", 'd', 0, kInf, false, [](RulesConstants& r, double v) { r.steamClockMaxSkewSec = v; }},
    {"xp_base", 'd', 0, kInf, true, [](RulesConstants& r, double v) { r.xpBase = v; }},
    {"xp_scale", 'd', 0, kInf, false, [](RulesConstants& r, double v) { r.xpScale = v; }},
    {"xp_exponent", 'd', 0, 3, false, [](RulesConstants& r, double v) { r.xpExponent = v; }},
    {"max_level", 'i', 1, 100, false, [](RulesConstants& r, double v) { r.maxLevel = static_cast<int>(v); }},
    // --- ADIÇÃO (docs/13): opcionais; o validador de dados do merge exige todas. ---
    {"dodge_max_charges", 'i', 1, 10, false, [](RulesConstants& r, double v) { r.dodgeMaxCharges = static_cast<int>(v); }},
    {"dodge_recharge", 'd', 0, 60, true, [](RulesConstants& r, double v) { r.dodgeRecharge = v; }},
    {"dodge_duration", 'd', 0, 5, true, [](RulesConstants& r, double v) { r.dodgeDuration = v; }},
    {"dodge_iframes", 'd', 0, 5, false, [](RulesConstants& r, double v) { r.dodgeIframes = v; }},
    {"dodge_distance", 'd', 0, 5000, false, [](RulesConstants& r, double v) { r.dodgeDistance = v; }},
    {"dodge_cost_resource", 'd', 0, kInf, false, [](RulesConstants& r, double v) { r.dodgeCostResource = v; }},
    {"dodge_buffer", 'd', 0, 1, false, [](RulesConstants& r, double v) { r.dodgeBuffer = v; }},
    {"dodge_perfect_resource", 'd', 0, kInf, false, [](RulesConstants& r, double v) { r.dodgePerfectResource = v; }},
    {"guard_break_stagger_seconds", 'd', 0, 60, false, [](RulesConstants& r, double v) { r.guardBreakStaggerSeconds = v; }},
    {"guard_break_stagger_damage_taken", 'd', 0, 5, false,
     [](RulesConstants& r, double v) { r.guardBreakStaggerDamageTaken = v; }},
    {"guard_break_immunity_boss", 'd', 0, 120, false, [](RulesConstants& r, double v) { r.guardBreakImmunityBoss = v; }},
    {"guard_break_immunity_other", 'd', 0, 120, false, [](RulesConstants& r, double v) { r.guardBreakImmunityOther = v; }},
    {"boss_shield_down_seconds", 'd', 0, 120, false, [](RulesConstants& r, double v) { r.bossShieldDownSeconds = v; }},
    {"elite_life_mult", 'd', 0, kInf, true, [](RulesConstants& r, double v) { r.eliteLifeMult = v; }},
    {"elite_damage_mult", 'd', 0, kInf, true, [](RulesConstants& r, double v) { r.eliteDamageMult = v; }},
    {"elite_xp_mult", 'd', 0, kInf, true, [](RulesConstants& r, double v) { r.eliteXpMult = v; }},
    {"potion_lockout", 'd', 0, 60, false, [](RulesConstants& r, double v) { r.potionLockout = v; }},
    // Pedidas pelo IRulesCore do C# (docs/11, A-01); ainda não estão em rules.csv: opcionais.
    {"dodge_cancel_recovery_fraction", 'd', 0, 1, false,
     [](RulesConstants& r, double v) { r.dodgeCancelRecoveryFraction = v; }},
    {"out_of_combat_seconds", 'd', 0, 600, false, [](RulesConstants& r, double v) { r.outOfCombatSeconds = v; }},
    // Rodada 2 (docs/13, R2): opcionais no core; o validador de dados as exige.
    {"unarmed_weapon_damage_physical", 'd', 0, kInf, false,
     [](RulesConstants& r, double v) { r.unarmedWeaponDamagePhysical = v; }},
    {"require_on_screen_margin", 'd', 0, kInf, false, [](RulesConstants& r, double v) { r.requireOnScreenMargin = v; }},
    // Etapa 3 (docs/16): inventário, equipamento e venda.
    {"inventory_capacity", 'i', 1, 1000, false, [](RulesConstants& r, double v) { r.inventoryCapacity = static_cast<int>(v); }},
    {"stash_capacity", 'i', 0, 10000, false, [](RulesConstants& r, double v) { r.stashCapacity = static_cast<int>(v); }},
    {"sell_price_normal", 'i', 0, 1000000000, false, [](RulesConstants& r, double v) { r.sellPrice[0] = static_cast<int>(v); }},
    {"sell_price_magic", 'i', 0, 1000000000, false, [](RulesConstants& r, double v) { r.sellPrice[1] = static_cast<int>(v); }},
    {"sell_price_rare", 'i', 0, 1000000000, false, [](RulesConstants& r, double v) { r.sellPrice[2] = static_cast<int>(v); }},
    {"sell_price_unique", 'i', 0, 1000000000, false, [](RulesConstants& r, double v) { r.sellPrice[3] = static_cast<int>(v); }},
    {"sell_level_factor", 'd', 0, 10, false, [](RulesConstants& r, double v) { r.sellLevelFactor = v; }},
    {"equip_slot_main_hand", 'b', 0, 1, false, [](RulesConstants& r, double v) { r.equipSlotEnabled[0] = v != 0.0; }},
    {"equip_slot_off_hand", 'b', 0, 1, false, [](RulesConstants& r, double v) { r.equipSlotEnabled[1] = v != 0.0; }},
    {"equip_slot_head", 'b', 0, 1, false, [](RulesConstants& r, double v) { r.equipSlotEnabled[2] = v != 0.0; }},
    {"equip_slot_body", 'b', 0, 1, false, [](RulesConstants& r, double v) { r.equipSlotEnabled[3] = v != 0.0; }},
    {"equip_slot_hands", 'b', 0, 1, false, [](RulesConstants& r, double v) { r.equipSlotEnabled[4] = v != 0.0; }},
    {"equip_slot_feet", 'b', 0, 1, false, [](RulesConstants& r, double v) { r.equipSlotEnabled[5] = v != 0.0; }},
    {"equip_slot_amulet", 'b', 0, 1, false, [](RulesConstants& r, double v) { r.equipSlotEnabled[6] = v != 0.0; }},
    {"equip_slot_ring", 'b', 0, 1, false, [](RulesConstants& r, double v) { r.equipSlotEnabled[7] = v != 0.0; }},
    {"equip_slot_ring2", 'b', 0, 1, false, [](RulesConstants& r, double v) { r.equipSlotEnabled[8] = v != 0.0; }},
    {"equip_slot_belt", 'b', 0, 1, false, [](RulesConstants& r, double v) { r.equipSlotEnabled[9] = v != 0.0; }},
    {"equip_slot_legs", 'b', 0, 1, false, [](RulesConstants& r, double v) { r.equipSlotEnabled[10] = v != 0.0; }},
};

// --- leitor de células tipado ----------------------------------------------------------------
class Cells {
public:
    Cells(const CsvTable& t, const CsvRow& r, std::vector<ContentError>& errs, const std::string& table)
        : t_(t), r_(r), errs_(errs), table_(table) {}

    bool bad() const { return bad_; }
    int line() const { return r_.line; }

    void Err(const char* code, const std::string& msg) {
        bad_ = true;
        ContentError e;
        e.table = table_;
        e.line = r_.line;
        e.message = std::string(code) + ": " + msg;
        errs_.push_back(std::move(e));
    }

    std::string_view Raw(std::string_view col) const {
        for (std::size_t i = 0; i < t_.header.size(); ++i) {
            if (t_.header[i] == col) return r_.cells[i];
        }
        return {};
    }

    bool Empty(std::string_view col) const { return Raw(col).empty(); }

    std::string Str(std::string_view col, bool required) {
        const std::string_view v = Raw(col);
        if (v.empty() && required) Err("E_REQUIRED", std::string(col) + " is required");
        return std::string(v);
    }

    // ID com formato válido (vazio permitido se !required).
    ContentId Id(std::string_view col, bool required) {
        const std::string_view v = Raw(col);
        if (v.empty()) {
            if (required) Err("E_REQUIRED", std::string(col) + " is required");
            return {};
        }
        if (!IsValidContentId(v)) Err("E_ID_FORMAT", std::string(col) + ": invalid id '" + std::string(v) + "'");
        return std::string(v);
    }

    double Num(std::string_view col, double def, double lo, double hi, bool loExcl = false) {
        const std::string_view v = Raw(col);
        if (v.empty()) return def;
        double x = 0.0;
        if (!detail::ParseDouble(v, x) || !std::isfinite(x)) {
            Err("E_TYPE", std::string(col) + ": not a number '" + std::string(v) + "'");
            return def;
        }
        if (x < lo || x > hi || (loExcl && x <= lo)) {
            Err("E_RANGE", std::string(col) + ": " + std::string(v) + " out of range");
            return def;
        }
        return x;
    }

    std::int64_t Int(std::string_view col, std::int64_t def, std::int64_t lo, std::int64_t hi) {
        const std::string_view v = Raw(col);
        if (v.empty()) return def;
        std::int64_t x = 0;
        if (!detail::ParseInt64(v, x)) {
            Err("E_TYPE", std::string(col) + ": not an integer '" + std::string(v) + "'");
            return def;
        }
        if (x < lo || x > hi) {
            Err("E_RANGE", std::string(col) + ": " + std::string(v) + " out of range");
            return def;
        }
        return x;
    }

    bool Bool(std::string_view col, bool def) {
        const std::string_view v = Raw(col);
        if (v.empty()) return def;
        if (v == "true") return true;
        if (v == "false") return false;
        Err("E_TYPE", std::string(col) + ": not a boolean '" + std::string(v) + "'");
        return def;
    }

    TagMask Tags(std::string_view col, bool required) {
        const std::string_view v = Raw(col);
        if (v.empty()) {
            if (required) Err("E_REQUIRED", std::string(col) + " is required");
            return 0;
        }
        TagMask m = 0;
        if (!ParseTagList(v, m)) Err("E_ENUM", std::string(col) + ": unknown tag in '" + std::string(v) + "'");
        return m;
    }

    std::vector<ContentId> IdList(std::string_view col) {
        std::vector<ContentId> out;
        const std::string_view v = Raw(col);
        for (std::string_view item : detail::SplitView(v, '|')) {
            if (item.empty() || !IsValidContentId(item)) {
                Err("E_ID_FORMAT", std::string(col) + ": invalid id in list");
                continue;
            }
            if (std::find(out.begin(), out.end(), item) != out.end()) {
                Err("E_DUP_ID", std::string(col) + ": repeated item '" + std::string(item) + "'");
                continue;
            }
            out.emplace_back(item);
        }
        return out;
    }

    std::vector<Modifier> Mods(std::string_view col) {
        std::vector<Modifier> out;
        for (std::string_view item : detail::SplitView(Raw(col), '|')) {
            const auto parts = detail::SplitView(item, ':');
            if (parts.size() < 3 || parts.size() > 4) {
                Err("E_TYPE", std::string(col) + ": bad modifier '" + std::string(item) + "'");
                continue;
            }
            Modifier m;
            double val = 0.0;
            if (!ParseStatId(parts[0], m.stat)) { Err("E_ENUM", std::string(col) + ": unknown stat"); continue; }
            if (!ParseModKind(parts[1], m.kind)) { Err("E_ENUM", std::string(col) + ": unknown mod kind"); continue; }
            if (!detail::ParseDouble(parts[2], val)) { Err("E_TYPE", std::string(col) + ": bad value"); continue; }
            m.value = val;
            if (parts.size() == 4 && !ParseTagList(parts[3], m.requiredTags)) {
                Err("E_ENUM", std::string(col) + ": unknown tag");
                continue;
            }
            out.push_back(std::move(m));
        }
        return out;
    }

    std::vector<StatGrowth> Growths(std::string_view col) {
        std::vector<StatGrowth> out;
        for (std::string_view item : detail::SplitView(Raw(col), '|')) {
            const auto parts = detail::SplitView(item, ':');
            StatGrowth g;
            if (parts.size() != 3 || !ParseStatId(parts[0], g.stat) || !detail::ParseDouble(parts[1], g.base) ||
                !detail::ParseDouble(parts[2], g.perLevel)) {
                Err("E_TYPE", std::string(col) + ": bad growth '" + std::string(item) + "'");
                continue;
            }
            out.push_back(g);
        }
        return out;
    }

private:
    const CsvTable& t_;
    const CsvRow& r_;
    std::vector<ContentError>& errs_;
    const std::string& table_;
    bool bad_ = false;
};

bool StartsWith(std::string_view s, std::string_view p) { return s.substr(0, p.size()) == p; }

// --- colunas esperadas por tabela (cabeçalho exato, em qualquer ordem) -------------------------
struct TableDef {
    const char* name;
    std::vector<const char*> columns;          // obrigatórias
    std::vector<const char*> optionalColumns{};  // colunas que podem faltar no cabeçalho (valor neutro); {} evita
                                                 // -Wmissing-field-initializers (GCC/Clang) nas tabelas sem colunas opcionais
};

const std::vector<TableDef>& TableDefs() {
    static const std::vector<TableDef> defs = {
        {"rules.csv", {"key", "value"}},
        {"meta.csv", {"key", "value"}},
        {"classes.csv",
         {"id", "resourceId", "startingSkill", "specializations", "resourceOnHit", "resourceOnBlock",
          "resourceDecayOutOfCombat", "regenMultWhileMoving"}},
        {"class_stats.csv", {"classId", "stat", "base", "perLevel"}},
        {"skills.csv",
         {"id", "classId", "specId", "tags", "shape", "scalesWithWeapon", "baseDamagePhysical", "baseDamageFire",
          "baseDamageCold", "baseDamageLightning", "coefficientRank1", "coefficientRank2", "coefficientRank3", "cost",
          "cooldown", "windup", "impact", "recovery", "range", "radius", "projectiles", "onHitEffects",
          "selfEffects", "idleSupported", "idleAvgTargetsHit", "idleFractionOfGroupHit", "idleApproachTime",
          "idleUptime", "idleDodgeTelegraphedBonus", "idleDamageTakenMult", "idleParitySampleSize",
          "unlockLevel"},
         {"coneAngle", "knockback", "projectileSpeed", "idleCalibration", "wallStaggerSeconds"}},
        {"effects.csv",
         {"id", "duration", "tickInterval", "stackRule", "maxStacks", "damagePerTickPhysical", "damagePerTickFire",
          "damagePerTickCold", "damagePerTickLightning", "modifiers", "barrier", "trigger", "triggerChance",
          "internalCooldown", "tags"},
         {"interruptsAction"}},
        {"enemies.csv",
         {"id", "familyId", "stats", "xpBase", "xpPerLevel", "lootTableId", "isBoss", "isElite", "moveSpeed",
          "aggroRange"},
         {"stunImmune", "shieldArcDegrees", "turnRateDegPerSec", "turnRateDegPerSecPhase2", "guardBreakStaggerSeconds",
          "guardBreakImmunitySeconds", "modifierId", "eliteLootTableId", "patrolSpeedMult"}},
        {"enemy_attacks.csv", {"enemyId", "skillId", "weight", "telegraphed"}},
        {"affixes.csv",
         {"id", "kind", "stat", "modKind", "requiredTags", "minValue", "maxValue", "minItemLevel", "weight",
          "allowedSlots", "group", "craftInscription"}},
        {"item_bases.csv",
         {"id", "slot", "itemLevel", "implicitMods", "weaponDamagePhysical", "weaponDamageFire", "weaponDamageCold",
          "weaponDamageLightning", "attackTime", "weaponTags", "grammaticalGender"},
         {"visualSetId"}},
        {"uniques.csv", {"id", "baseId", "fixedMods", "ruleEffectId", "idleSupported"},
         {"idleParitySampleSize", "idleCalibration", "visualSetId"}},
        {"loot_tables.csv",
         {"id", "rolls", "dropChance", "rarityWeightNormal", "rarityWeightMagic", "rarityWeightRare"}},
        {"loot_entries.csv",
         {"tableId", "kind", "refId", "weight", "minAmount", "maxAmount", "minAreaLevel", "maxAreaLevel",
          "manualOnly"},
         {"fixedChance", "guaranteeFirstKill", "pityKills"}},
        {"encounters.csv", {"id", "groups", "weight", "travelTime", "isBoss"}},
        {"maps.csv", {"id", "monsterLevel", "tier", "encounters", "bossEncounter", "areaLootTable", "idleAllowed"}},
        // Tabelas de docs/13 ("Para o Data Engineer"): obrigatórias, como as demais (arquivo faltando = E_IO).
        {"potions.csv",
         {"id", "kind", "fractionOfMaxLife", "duration", "maxCharges", "rechargeSeconds", "useTime",
          "moveSpeedWhileUsing", "globalLockout", "refillOnEliteKill", "hotkeySlot"}},
        {"elite_modifiers.csv",
         {"id", "weightPrototype", "lifeMult", "damageMult", "xpMult", "barrierFractionOfLife", "moveSpeedMult",
          "attackSpeedMult", "recoveryMult", "deathExplosionRadius", "deathExplosionDamage", "deathExplosionFuse"}},
        {"boss_phases.csv",
         {"bossId", "phase", "lifeThreshold", "transitionSeconds", "summonEnemyId", "summonCount", "shieldSeconds",
          "turnRate", "decisionDelayMin", "decisionDelayMax"},
         {"summonAtFraction"}},
        {"boss_patterns.csv",
         {"id", "bossId", "phase", "skillId", "weight", "telegraphSeconds", "recoverySeconds", "cooldown", "maxRepeat",
          "playerNearWeightMult", "ignoreIfBehind"}},
        {"enemy_ai.csv",
         {"enemyId", "aggroRange", "alertRadius", "leashRange", "leashSeconds", "preferredMin", "preferredMax",
          "retreatBelow", "retreatMaxSeconds", "circleMin", "circleMax", "circleSpeed", "attackTokens",
          "tokenIntervalMin", "tokenIntervalMax", "fleeLifeFraction", "fleeSeconds", "fleeOncePerLife",
          "attackCooldown", "maxSimultaneousShooters"},
         {"requireOnScreen"}},
    };
    return defs;
}

template <typename T>
struct Registry {
    std::vector<T> items;
    std::vector<int> lines;
    std::unordered_map<std::string, std::size_t> index;  // só para busca

    const T* Find(std::string_view id) const {
        const auto it = index.find(std::string(id));
        return it == index.end() ? nullptr : &items[it->second];
    }
    void Push(T d, int line) {
        index[d.id] = items.size();
        items.push_back(std::move(d));
        lines.push_back(line);
    }
};

}  // namespace

// ===============================================================================================
namespace {
struct ContentImpl {
    Registry<ClassData> classes;
    Registry<SkillData> skills;
    Registry<EffectData> effects;
    Registry<EnemyData> enemies;
    Registry<AffixData> affixes;
    Registry<ItemBaseData> bases;
    Registry<UniqueData> uniques;
    Registry<LootTableData> loot;
    Registry<EncounterTemplate> encounters;
    Registry<MapData> maps;
    Registry<PotionData> potions;
    Registry<EliteModifierData> eliteModifiers;
    std::vector<BossPatternData> bossPatterns;
    std::vector<int> bossPatternLines;
    std::vector<BossPhaseData> bossPhases;
    std::vector<int> bossPhaseLines;
    std::vector<EnemyAiData> enemyAis;
    std::vector<int> enemyAiLines;

    struct ClassStatRow { ContentId classId; StatGrowth g; int line = 0; };
    struct EnemyAttackRow { ContentId enemyId; EnemyAttack a; int line = 0; };
    struct LootEntryRow { ContentId tableId; LootEntry e; int line = 0; };
    std::vector<ClassStatRow> classStatRows;
    std::vector<EnemyAttackRow> enemyAttackRows;
    std::vector<LootEntryRow> lootEntryRows;

    std::unordered_map<std::string, std::pair<std::string, int>> idOwner;  // id -> (tabela, linha)
    std::unordered_map<ContentId, const EffectData*> effectLookup;

    bool rulesLoaded = false;
    bool metaLoaded = false;
    std::vector<std::string> loadedTables;  // nomes das tabelas carregadas por LoadTableCsv (para exigir as de docs/13)
    std::array<bool, kRuleKeyCount> ruleSeen{};
    bool finalized = false;
    bool finalizeOk = false;
};
}  // namespace

struct ContentDB::Impl : ContentImpl {};

ContentDB::ContentDB() : impl_(std::make_unique<Impl>()) {}
ContentDB::~ContentDB() = default;
ContentDB::ContentDB(ContentDB&&) noexcept = default;
ContentDB& ContentDB::operator=(ContentDB&&) noexcept = default;

namespace {

void PushErr(std::vector<ContentError>& errs, const std::string& table, int line, const char* code,
             const std::string& msg) {
    ContentError e;
    e.table = table;
    e.line = line;
    e.message = std::string(code) + ": " + msg;
    errs.push_back(std::move(e));
}

// Registra o ID (formato, prefixo, unicidade global). false = registro descartado.
bool RegisterId(ContentImpl& impl, std::vector<ContentError>& errs, const std::string& table, int line,
                const ContentId& id, std::string_view prefix) {
    if (!IsValidContentId(id)) {
        PushErr(errs, table, line, "E_ID_FORMAT", "invalid id '" + id + "'");
        return false;
    }
    if (!StartsWith(id, prefix)) {
        PushErr(errs, table, line, "E_ID_PREFIX", "id '" + id + "' must start with '" + std::string(prefix) + "'");
        return false;
    }
    const auto it = impl.idOwner.find(id);
    if (it != impl.idOwner.end()) {
        PushErr(errs, table, line, "E_DUP_ID",
                "id '" + id + "' repeated (first in " + it->second.first + " line " + std::to_string(it->second.second) + ")");
        return false;
    }
    impl.idOwner.emplace(id, std::make_pair(table, line));
    return true;
}

}  // namespace

// ===============================================================================================
// Carga das tabelas
// ===============================================================================================
namespace {

struct LoadCtx {
    ContentImpl& impl;
    std::vector<ContentError>& errs;
    RulesConstants& rules;
    std::uint32_t& contentVersion;
    const std::string& table;
    const CsvTable& csv;
};

void LoadRules(LoadCtx& c) {
    c.impl.rulesLoaded = true;
    for (const CsvRow& row : c.csv.rows) {
        Cells cell(c.csv, row, c.errs, c.table);
        const std::string key = cell.Str("key", true);
        const std::string_view valText = cell.Raw("value");
        if (cell.bad()) continue;
        std::size_t idx = kRuleKeyCount;
        for (std::size_t i = 0; i < kRuleKeyCount; ++i) {
            if (key == kRuleDefs[i].key) { idx = i; break; }
        }
        if (idx == kRuleKeyCount) { cell.Err("E_UNKNOWN_KEY", "unknown rule '" + key + "'"); continue; }
        if (c.impl.ruleSeen[idx]) { cell.Err("E_DUP_ID", "rule '" + key + "' repeated"); continue; }
        const RuleDef& def = kRuleDefs[idx];
        double v = 0.0;
        if (def.type == 'b') {
            if (valText == "true") v = 1.0;
            else if (valText == "false") v = 0.0;
            else { cell.Err("E_TYPE", key + ": not a boolean"); continue; }
        } else if (def.type == 'i') {
            std::int64_t iv = 0;
            if (!detail::ParseInt64(valText, iv)) { cell.Err("E_TYPE", key + ": not an integer"); continue; }
            v = static_cast<double>(iv);
        } else if (!detail::ParseDouble(valText, v) || !std::isfinite(v)) {
            cell.Err("E_TYPE", key + ": not a number");
            continue;
        }
        if (def.type != 'b' && (v < def.lo || v > def.hi || (def.loExclusive && v <= def.lo))) {
            cell.Err("E_RANGE", key + ": " + std::string(valText) + " out of range");
            continue;
        }
        if (std::string_view(def.key) == "xp_exponent" && v * 2.0 != std::floor(v * 2.0)) {
            cell.Err("E_RANGE", "xp_exponent must be a multiple of 0.5");
            continue;
        }
        c.impl.ruleSeen[idx] = true;
        def.set(c.rules, v);
    }
}

void LoadMeta(LoadCtx& c) {
    c.impl.metaLoaded = true;
    bool seen = false;
    for (const CsvRow& row : c.csv.rows) {
        Cells cell(c.csv, row, c.errs, c.table);
        const std::string key = cell.Str("key", true);
        if (cell.bad()) continue;
        if (key != "content_version") { cell.Err("E_UNKNOWN_KEY", "unknown meta key '" + key + "'"); continue; }
        const std::int64_t v = cell.Int("value", 0, 1, 4294967295LL);
        if (cell.Empty("value")) cell.Err("E_REQUIRED", "value is required");
        if (cell.bad()) continue;
        c.contentVersion = static_cast<std::uint32_t>(v);
        seen = true;
    }
    if (!seen) PushErr(c.errs, c.table, 0, "E_REQUIRED", "content_version missing");
}

void LoadClasses(LoadCtx& c) {
    for (const CsvRow& row : c.csv.rows) {
        Cells cell(c.csv, row, c.errs, c.table);
        ClassData d;
        d.id = cell.Id("id", true);
        d.resourceId = cell.Str("resourceId", true);
        if (!d.resourceId.empty() && d.resourceId != "resource.momentum" && d.resourceId != "resource.focus" &&
            d.resourceId != "resource.mana")
            cell.Err("E_ENUM", "resourceId: unknown resource '" + d.resourceId + "'");
        d.startingSkill = cell.Id("startingSkill", true);
        d.specializations = cell.IdList("specializations");
        d.resourceOnHit = cell.Num("resourceOnHit", 0.0, 0.0, kInf);
        d.resourceOnBlock = cell.Num("resourceOnBlock", 0.0, 0.0, kInf);
        d.resourceDecayOutOfCombat = cell.Num("resourceDecayOutOfCombat", 0.0, 0.0, kInf);
        d.regenMultWhileMoving = cell.Num("regenMultWhileMoving", 1.0, 0.0, 1.0);
        if (cell.bad()) continue;
        if (!RegisterId(c.impl, c.errs, c.table, row.line, d.id, "class.")) continue;
        c.impl.classes.Push(std::move(d), row.line);
    }
}

void LoadClassStats(LoadCtx& c) {
    for (const CsvRow& row : c.csv.rows) {
        Cells cell(c.csv, row, c.errs, c.table);
        ContentImpl::ClassStatRow r;
        r.classId = cell.Id("classId", true);
        const std::string stat = cell.Str("stat", true);
        if (!stat.empty() && !ParseStatId(stat, r.g.stat)) cell.Err("E_ENUM", "stat: unknown '" + stat + "'");
        r.g.base = cell.Num("base", 0.0, -kInf, kInf);
        if (cell.Empty("base")) cell.Err("E_REQUIRED", "base is required");
        r.g.perLevel = cell.Num("perLevel", 0.0, -kInf, kInf);
        r.line = row.line;
        if (cell.bad()) continue;
        c.impl.classStatRows.push_back(std::move(r));
    }
}

void LoadSkills(LoadCtx& c) {
    for (const CsvRow& row : c.csv.rows) {
        Cells cell(c.csv, row, c.errs, c.table);
        SkillData d;
        d.id = cell.Id("id", true);
        d.classId = cell.Id("classId", false);
        d.specId = cell.Id("specId", false);
        if (!d.specId.empty() && !StartsWith(d.specId, "spec.")) cell.Err("E_ID_PREFIX", "specId must start with 'spec.'");
        d.tags = cell.Tags("tags", true);  // decisão P8: tags obrigatórias no CSV (como no esquema)
        const std::string shape = cell.Str("shape", true);
        if (!shape.empty() && !ParseSkillShape(shape, d.shape)) cell.Err("E_ENUM", "shape: unknown '" + shape + "'");
        d.scalesWithWeapon = cell.Bool("scalesWithWeapon", false);
        d.baseDamage[0] = cell.Num("baseDamagePhysical", 0.0, 0.0, kInf);
        d.baseDamage[1] = cell.Num("baseDamageFire", 0.0, 0.0, kInf);
        d.baseDamage[2] = cell.Num("baseDamageCold", 0.0, 0.0, kInf);
        d.baseDamage[3] = cell.Num("baseDamageLightning", 0.0, 0.0, kInf);
        d.coefficientByRank[0] = cell.Num("coefficientRank1", 1.0, 0.0, kInf);
        d.coefficientByRank[1] = cell.Num("coefficientRank2", 1.0, 0.0, kInf);
        d.coefficientByRank[2] = cell.Num("coefficientRank3", 1.0, 0.0, kInf);
        d.cost = cell.Num("cost", 0.0, 0.0, kInf);
        d.cooldown = cell.Num("cooldown", 0.0, 0.0, kInf);
        d.windup = cell.Num("windup", 0.0, 0.0, kInf);
        d.impact = cell.Num("impact", 0.0, 0.0, kInf);
        d.recovery = cell.Num("recovery", 0.0, 0.0, kInf);
        d.range = cell.Num("range", 0.0, 0.0, kInf);
        d.radius = cell.Num("radius", 0.0, 0.0, kInf);
        d.projectiles = static_cast<int>(cell.Int("projectiles", 1, 1, 50));
        d.coneAngle = cell.Num("coneAngle", 0.0, 0.0, 360.0);
        d.knockback = cell.Num("knockback", 0.0, 0.0, kInf);
        d.wallStaggerSeconds = cell.Num("wallStaggerSeconds", 0.0, 0.0, 60.0);
        d.projectileSpeed = cell.Num("projectileSpeed", 0.0, 0.0, kInf);
        d.onHitEffects = cell.IdList("onHitEffects");
        d.selfEffects = cell.IdList("selfEffects");
        d.idle.supported = cell.Bool("idleSupported", false);
        d.idle.avgTargetsHit = cell.Num("idleAvgTargetsHit", 1.0, 0.0, kInf);
        d.idle.fractionOfGroupHit = cell.Num("idleFractionOfGroupHit", 0.0, 0.0, 1.0);
        d.idle.approachTime = cell.Num("idleApproachTime", 0.0, 0.0, kInf);
        d.idle.uptime = cell.Num("idleUptime", 1.0, 0.0, 1.0);
        d.idle.dodgeTelegraphedBonus = cell.Num("idleDodgeTelegraphedBonus", 0.0, 0.0, 1.0);
        d.idle.damageTakenMult = cell.Num("idleDamageTakenMult", 1.0, 0.0, kInf);
        d.idle.paritySampleSize = static_cast<std::uint32_t>(cell.Int("idleParitySampleSize", 0, 0, 4294967295LL));
        {
            // Coluna ausente/vazia: amostra > 0 vale como paridade (comportamento anterior); amostra 0 = sem selo.
            const std::string_view cal = cell.Raw("idleCalibration");
            if (cal.empty()) d.idle.calibration = d.idle.paritySampleSize > 0 ? IdleCalibration::BotParity : IdleCalibration::None;
            else if (!ParseIdleCalibration(cal, d.idle.calibration)) cell.Err("E_ENUM", "idleCalibration: unknown '" + std::string(cal) + "'");
        }
        d.unlockLevel = static_cast<int>(cell.Int("unlockLevel", 1, 1, 100));
        if (cell.bad()) continue;
        if (!RegisterId(c.impl, c.errs, c.table, row.line, d.id, "skill.")) continue;
        c.impl.skills.Push(std::move(d), row.line);
    }
}

void LoadEffects(LoadCtx& c) {
    for (const CsvRow& row : c.csv.rows) {
        Cells cell(c.csv, row, c.errs, c.table);
        EffectData d;
        d.id = cell.Id("id", true);
        d.duration = cell.Num("duration", 0.0, 0.0, kInf);
        d.tickInterval = cell.Num("tickInterval", 0.0, 0.0, kInf);
        const std::string_view rule = cell.Raw("stackRule");
        if (!rule.empty() && !ParseStackRule(rule, d.stackRule)) cell.Err("E_ENUM", "stackRule: unknown");
        d.maxStacks = static_cast<int>(cell.Int("maxStacks", 1, 1, 100));
        d.damagePerTick[0] = cell.Num("damagePerTickPhysical", 0.0, 0.0, kInf);
        d.damagePerTick[1] = cell.Num("damagePerTickFire", 0.0, 0.0, kInf);
        d.damagePerTick[2] = cell.Num("damagePerTickCold", 0.0, 0.0, kInf);
        d.damagePerTick[3] = cell.Num("damagePerTickLightning", 0.0, 0.0, kInf);
        d.modifiers = cell.Mods("modifiers");
        d.barrier = cell.Num("barrier", 0.0, 0.0, kInf);
        const std::string_view trig = cell.Raw("trigger");
        if (trig.empty() || trig == "none") d.trigger = TriggerKind::None;
        else if (trig == "on_hit") d.trigger = TriggerKind::OnHit;
        else if (trig == "on_crit") d.trigger = TriggerKind::OnCrit;
        else if (trig == "on_block") d.trigger = TriggerKind::OnBlock;
        else if (trig == "on_kill") d.trigger = TriggerKind::OnKill;
        else if (trig == "on_take_damage") d.trigger = TriggerKind::OnTakeDamage;
        else cell.Err("E_ENUM", "trigger: unknown '" + std::string(trig) + "'");
        d.triggerChance = cell.Num("triggerChance", 1.0, 0.0, 1.0);
        d.internalCooldown = cell.Num("internalCooldown", 0.0, 0.0, kInf);
        d.tags = cell.Tags("tags", false);
        d.interruptsAction = cell.Bool("interruptsAction", false);
        if (cell.bad()) continue;
        if (!RegisterId(c.impl, c.errs, c.table, row.line, d.id, "effect.")) continue;
        c.impl.effects.Push(std::move(d), row.line);
    }
}

void LoadEnemies(LoadCtx& c) {
    for (const CsvRow& row : c.csv.rows) {
        Cells cell(c.csv, row, c.errs, c.table);
        EnemyData d;
        d.id = cell.Id("id", true);
        d.familyId = cell.Id("familyId", true);
        if (!d.familyId.empty() && !StartsWith(d.familyId, "family.")) cell.Err("E_ID_PREFIX", "familyId must start with 'family.'");
        if (cell.Empty("stats")) cell.Err("E_REQUIRED", "stats is required");
        d.stats = cell.Growths("stats");
        d.xpBase = cell.Num("xpBase", 0.0, 0.0, kInf);
        d.xpPerLevel = cell.Num("xpPerLevel", 0.0, 0.0, kInf);
        d.lootTableId = cell.Id("lootTableId", false);
        d.isBoss = cell.Bool("isBoss", false);
        d.isElite = cell.Bool("isElite", false);
        d.moveSpeed = cell.Num("moveSpeed", 0.0, 0.0, kInf);
        d.aggroRange = cell.Num("aggroRange", 0.0, 0.0, kInf);
        d.stunImmune = cell.Bool("stunImmune", false);
        d.shieldArcDegrees = cell.Num("shieldArcDegrees", 0.0, 0.0, 360.0);
        d.turnRateDegPerSec = cell.Num("turnRateDegPerSec", 0.0, 0.0, kInf);
        d.turnRateDegPerSecPhase2 = cell.Num("turnRateDegPerSecPhase2", 0.0, 0.0, kInf);
        d.guardBreakStaggerSeconds = cell.Num("guardBreakStaggerSeconds", 0.0, 0.0, 60.0);
        d.guardBreakImmunitySeconds = cell.Num("guardBreakImmunitySeconds", 0.0, 0.0, 120.0);
        d.modifierId = cell.Id("modifierId", false);
        d.eliteLootTableId = cell.Id("eliteLootTableId", false);
        d.patrolSpeedMult = cell.Num("patrolSpeedMult", 0.0, 0.0, 1.0);
        if (!cell.Empty("patrolSpeedMult") && !(d.patrolSpeedMult > 0.0)) cell.Err("E_RANGE", "patrolSpeedMult must be in (0, 1]");
        if (cell.bad()) continue;
        if (!RegisterId(c.impl, c.errs, c.table, row.line, d.id, "enemy.")) continue;
        c.impl.enemies.Push(std::move(d), row.line);
    }
}

void LoadEnemyAttacks(LoadCtx& c) {
    for (const CsvRow& row : c.csv.rows) {
        Cells cell(c.csv, row, c.errs, c.table);
        ContentImpl::EnemyAttackRow r;
        r.enemyId = cell.Id("enemyId", true);
        r.a.skillId = cell.Id("skillId", true);
        r.a.weight = cell.Num("weight", 1.0, 0.0, kInf, true);
        r.a.telegraphed = cell.Bool("telegraphed", false);
        r.line = row.line;
        if (cell.bad()) continue;
        c.impl.enemyAttackRows.push_back(std::move(r));
    }
}

void LoadAffixes(LoadCtx& c) {
    for (const CsvRow& row : c.csv.rows) {
        Cells cell(c.csv, row, c.errs, c.table);
        AffixData d;
        d.id = cell.Id("id", true);
        const std::string_view kind = cell.Raw("kind");
        if (kind == "prefix") d.kind = AffixKind::Prefix;
        else if (kind == "suffix") d.kind = AffixKind::Suffix;
        else cell.Err(kind.empty() ? "E_REQUIRED" : "E_ENUM", "kind: prefix or suffix expected");
        const std::string stat = cell.Str("stat", true);
        if (!stat.empty() && !ParseStatId(stat, d.stat)) cell.Err("E_ENUM", "stat: unknown '" + stat + "'");
        const std::string mk = cell.Str("modKind", true);
        if (!mk.empty() && !ParseModKind(mk, d.modKind)) cell.Err("E_ENUM", "modKind: unknown '" + mk + "'");
        d.requiredTags = cell.Tags("requiredTags", false);
        d.minValue = cell.Num("minValue", 0.0, -kInf, kInf);
        d.maxValue = cell.Num("maxValue", 0.0, -kInf, kInf);
        if (cell.Empty("minValue")) cell.Err("E_REQUIRED", "minValue is required");
        if (cell.Empty("maxValue")) cell.Err("E_REQUIRED", "maxValue is required");
        d.minItemLevel = static_cast<int>(cell.Int("minItemLevel", 1, 1, 100));
        d.weight = cell.Num("weight", 1.0, 0.0, kInf, true);
        for (std::string_view s : detail::SplitView(cell.Raw("allowedSlots"), '|')) {
            ItemSlot slot = ItemSlot::MainHand;
            if (!ParseItemSlot(s, slot)) { cell.Err("E_ENUM", "allowedSlots: unknown slot"); continue; }
            d.allowedSlots.push_back(slot);
        }
        d.group = cell.Str("group", false);
        d.craftInscription = cell.Bool("craftInscription", false);
        if (cell.bad()) continue;
        if (!RegisterId(c.impl, c.errs, c.table, row.line, d.id, "affix.")) continue;
        c.impl.affixes.Push(std::move(d), row.line);
    }
}

void LoadItemBases(LoadCtx& c) {
    for (const CsvRow& row : c.csv.rows) {
        Cells cell(c.csv, row, c.errs, c.table);
        ItemBaseData d;
        d.id = cell.Id("id", true);
        const std::string slot = cell.Str("slot", true);
        if (!slot.empty() && !ParseItemSlot(slot, d.slot)) cell.Err("E_ENUM", "slot: unknown '" + slot + "'");
        d.itemLevel = static_cast<int>(cell.Int("itemLevel", 1, 1, 100));
        d.implicitMods = cell.Mods("implicitMods");
        d.weaponDamage[0] = cell.Num("weaponDamagePhysical", 0.0, 0.0, kInf);
        d.weaponDamage[1] = cell.Num("weaponDamageFire", 0.0, 0.0, kInf);
        d.weaponDamage[2] = cell.Num("weaponDamageCold", 0.0, 0.0, kInf);
        d.weaponDamage[3] = cell.Num("weaponDamageLightning", 0.0, 0.0, kInf);
        d.attackTime = cell.Num("attackTime", 0.0, 0.0, kInf);
        d.weaponTags = cell.Tags("weaponTags", false);
        const std::string_view g = cell.Raw("grammaticalGender");
        if (g.empty() || g == "m") d.grammaticalGender = 'm';
        else if (g == "f") d.grammaticalGender = 'f';
        else cell.Err("E_ENUM", "grammaticalGender: m or f expected");
        d.visualSetId = cell.Id("visualSetId", false);
        if (!d.visualSetId.empty() && !StartsWith(d.visualSetId, "vset.")) cell.Err("E_ID_PREFIX", "visualSetId must start with 'vset.'");
        if (cell.bad()) continue;
        if (!RegisterId(c.impl, c.errs, c.table, row.line, d.id, "item_base.")) continue;
        c.impl.bases.Push(std::move(d), row.line);
    }
}

void LoadUniques(LoadCtx& c) {
    for (const CsvRow& row : c.csv.rows) {
        Cells cell(c.csv, row, c.errs, c.table);
        UniqueData d;
        d.id = cell.Id("id", true);
        d.baseId = cell.Id("baseId", true);
        d.fixedMods = cell.Mods("fixedMods");
        d.ruleEffectId = cell.Id("ruleEffectId", false);
        d.idleSupported = cell.Bool("idleSupported", false);
        d.visualSetId = cell.Id("visualSetId", false);
        if (!d.visualSetId.empty() && !StartsWith(d.visualSetId, "vset.")) cell.Err("E_ID_PREFIX", "visualSetId must start with 'vset.'");
        d.idleParitySampleSize = static_cast<std::uint32_t>(cell.Int("idleParitySampleSize", 0, 0, 4294967295LL));
        {
            const std::string_view cal = cell.Raw("idleCalibration");
            if (cal.empty()) d.idleCalibration = d.idleParitySampleSize > 0 ? IdleCalibration::BotParity : IdleCalibration::None;
            else if (!ParseIdleCalibration(cal, d.idleCalibration)) cell.Err("E_ENUM", "idleCalibration: unknown '" + std::string(cal) + "'");
        }
        if (cell.bad()) continue;
        if (!RegisterId(c.impl, c.errs, c.table, row.line, d.id, "unique.")) continue;
        c.impl.uniques.Push(std::move(d), row.line);
    }
}

void LoadLootTables(LoadCtx& c) {
    for (const CsvRow& row : c.csv.rows) {
        Cells cell(c.csv, row, c.errs, c.table);
        LootTableData d;
        d.id = cell.Id("id", true);
        d.rolls = static_cast<int>(cell.Int("rolls", 1, 1, 100));
        d.dropChance = cell.Num("dropChance", 1.0, 0.0, 1.0);
        d.rarityWeights[0] = cell.Num("rarityWeightNormal", 80.0, 0.0, kInf);
        d.rarityWeights[1] = cell.Num("rarityWeightMagic", 18.0, 0.0, kInf);
        d.rarityWeights[2] = cell.Num("rarityWeightRare", 2.0, 0.0, kInf);
        if (cell.bad()) continue;
        if (!RegisterId(c.impl, c.errs, c.table, row.line, d.id, "loot.")) continue;
        c.impl.loot.Push(std::move(d), row.line);
    }
}

void LoadLootEntries(LoadCtx& c) {
    static constexpr struct { const char* n; LootEntryKind k; } kKinds[] = {
        {"item_base", LootEntryKind::ItemBase}, {"unique", LootEntryKind::Unique},
        {"stack", LootEntryKind::Stack},        {"spec_book", LootEntryKind::SpecBook},
        {"map_stone", LootEntryKind::MapStone}, {"echo_fragment", LootEntryKind::EchoFragment},
        {"table", LootEntryKind::Table},        {"nothing", LootEntryKind::Nothing},
    };
    for (const CsvRow& row : c.csv.rows) {
        Cells cell(c.csv, row, c.errs, c.table);
        ContentImpl::LootEntryRow r;
        r.tableId = cell.Id("tableId", true);
        const std::string_view kind = cell.Raw("kind");
        bool found = false;
        for (const auto& k : kKinds) {
            if (kind == k.n) { r.e.kind = k.k; found = true; }
        }
        if (!found) cell.Err(kind.empty() ? "E_REQUIRED" : "E_ENUM", "kind: unknown '" + std::string(kind) + "'");
        r.e.refId = cell.Id("refId", false);
        r.e.weight = cell.Num("weight", 1.0, 0.0, kInf);  // > 0 exigido no Finalize, menos nas entradas fixas
        r.e.fixedChance = cell.Num("fixedChance", 0.0, 0.0, 1.0);
        r.e.guaranteeFirstKill = cell.Bool("guaranteeFirstKill", false);
        r.e.pityKills = static_cast<int>(cell.Int("pityKills", 0, 0, 1000));
        r.e.minAmount = cell.Int("minAmount", 1, 1, INT64_MAX);
        r.e.maxAmount = cell.Int("maxAmount", 1, 1, INT64_MAX);
        r.e.minAreaLevel = static_cast<int>(cell.Int("minAreaLevel", 1, 1, 999));
        r.e.maxAreaLevel = static_cast<int>(cell.Int("maxAreaLevel", 999, 1, 999));
        r.e.manualOnly = cell.Bool("manualOnly", false);
        r.line = row.line;
        if (cell.bad()) continue;
        c.impl.lootEntryRows.push_back(std::move(r));
    }
}

void LoadEncounters(LoadCtx& c) {
    for (const CsvRow& row : c.csv.rows) {
        Cells cell(c.csv, row, c.errs, c.table);
        EncounterTemplate d;
        d.id = cell.Id("id", true);
        if (cell.Empty("groups")) cell.Err("E_REQUIRED", "groups is required");
        for (std::string_view item : detail::SplitView(cell.Raw("groups"), '|')) {
            const auto p = detail::SplitView(item, ':');
            EncounterGroup g;
            std::int64_t mn = 0, mx = 0;
            if (p.size() != 4 || !IsValidContentId(p[0]) || !detail::ParseInt64(p[1], mn) ||
                !detail::ParseInt64(p[2], mx) || !detail::ParseDouble(p[3], g.eliteChance)) {
                cell.Err("E_TYPE", "groups: bad group '" + std::string(item) + "'");
                continue;
            }
            if (mn < 1 || mx < mn || mx > 1000 || g.eliteChance < 0.0 || g.eliteChance > 1.0) {
                cell.Err("E_RANGE", "groups: bad counts or elite chance in '" + std::string(item) + "'");
                continue;
            }
            g.enemyId = std::string(p[0]);
            g.countMin = static_cast<int>(mn);
            g.countMax = static_cast<int>(mx);
            d.groups.push_back(std::move(g));
        }
        d.weight = cell.Num("weight", 1.0, 0.0, kInf, true);
        d.travelTime = cell.Num("travelTime", 0.0, 0.0, kInf);
        d.isBoss = cell.Bool("isBoss", false);
        if (cell.bad()) continue;
        if (!RegisterId(c.impl, c.errs, c.table, row.line, d.id, "enc.")) continue;
        c.impl.encounters.Push(std::move(d), row.line);
    }
}

void LoadMaps(LoadCtx& c) {
    for (const CsvRow& row : c.csv.rows) {
        Cells cell(c.csv, row, c.errs, c.table);
        MapData d;
        d.id = cell.Id("id", true);
        d.monsterLevel = static_cast<int>(cell.Int("monsterLevel", 1, 1, 100));
        if (cell.Empty("monsterLevel")) cell.Err("E_REQUIRED", "monsterLevel is required");
        d.tier = static_cast<int>(cell.Int("tier", 0, 0, 5));
        if (cell.Empty("encounters")) cell.Err("E_REQUIRED", "encounters is required");
        d.encounters = cell.IdList("encounters");
        d.bossEncounter = cell.Id("bossEncounter", false);
        d.areaLootTable = cell.Id("areaLootTable", false);
        d.idleAllowed = cell.Bool("idleAllowed", true);
        if (cell.bad()) continue;
        if (!RegisterId(c.impl, c.errs, c.table, row.line, d.id, "map.")) continue;
        c.impl.maps.Push(std::move(d), row.line);
    }
}


void LoadPotions(LoadCtx& c) {
    for (const CsvRow& row : c.csv.rows) {
        Cells cell(c.csv, row, c.errs, c.table);
        PotionData d;
        d.id = cell.Id("id", true);
        const std::string_view kind = cell.Raw("kind");
        if (!ParsePotionKind(kind, d.kind)) cell.Err(kind.empty() ? "E_REQUIRED" : "E_ENUM", "kind: heal or barrier expected");
        d.fractionOfMaxLife = cell.Num("fractionOfMaxLife", 0.0, 0.0, 1.0);
        d.duration = cell.Num("duration", 0.0, 0.0, kInf);
        d.maxCharges = static_cast<int>(cell.Int("maxCharges", 1, 1, 20));
        d.rechargeSeconds = cell.Num("rechargeSeconds", 0.0, 0.0, kInf);
        d.useTime = cell.Num("useTime", 0.0, 0.0, kInf);
        d.moveSpeedWhileUsing = cell.Num("moveSpeedWhileUsing", 1.0, 0.0, 1.0);
        d.globalLockout = cell.Num("globalLockout", 0.0, 0.0, 60.0);
        d.refillOnEliteKill = cell.Bool("refillOnEliteKill", false);
        d.hotkeySlot = static_cast<int>(cell.Int("hotkeySlot", 1, 1, 9));
        if (cell.bad()) continue;
        if (!RegisterId(c.impl, c.errs, c.table, row.line, d.id, "potion.")) continue;
        c.impl.potions.Push(std::move(d), row.line);
    }
}

void LoadEliteModifiers(LoadCtx& c) {
    for (const CsvRow& row : c.csv.rows) {
        Cells cell(c.csv, row, c.errs, c.table);
        EliteModifierData d;
        d.id = cell.Id("id", true);
        d.weightPrototype = cell.Num("weightPrototype", 0.0, 0.0, kInf);
        d.lifeMult = cell.Num("lifeMult", 1.0, 0.0, kInf, true);
        d.damageMult = cell.Num("damageMult", 1.0, 0.0, kInf, true);
        d.xpMult = cell.Num("xpMult", 1.0, 0.0, kInf, true);
        d.barrierFractionOfLife = cell.Num("barrierFractionOfLife", 0.0, 0.0, 5.0);
        d.moveSpeedMult = cell.Num("moveSpeedMult", 1.0, 0.0, kInf, true);
        d.attackSpeedMult = cell.Num("attackSpeedMult", 1.0, 0.0, kInf, true);
        d.recoveryMult = cell.Num("recoveryMult", 1.0, 0.0, kInf, true);
        d.deathExplosionRadius = cell.Num("deathExplosionRadius", 0.0, 0.0, kInf);
        d.deathExplosionDamage = cell.Num("deathExplosionDamage", 0.0, 0.0, kInf);
        d.deathExplosionFuse = cell.Num("deathExplosionFuse", 0.0, 0.0, kInf);
        if (cell.bad()) continue;
        if (!RegisterId(c.impl, c.errs, c.table, row.line, d.id, "modifier.elite.")) continue;
        c.impl.eliteModifiers.Push(std::move(d), row.line);
    }
}

void LoadBossPhases(LoadCtx& c) {
    for (const CsvRow& row : c.csv.rows) {
        Cells cell(c.csv, row, c.errs, c.table);
        BossPhaseData d;
        d.bossId = cell.Id("bossId", true);
        d.phase = static_cast<int>(cell.Int("phase", 1, 1, 9));
        if (cell.Empty("phase")) cell.Err("E_REQUIRED", "phase is required");
        d.lifeThreshold = cell.Num("lifeThreshold", 1.0, 0.0, 1.0);
        d.transitionSeconds = cell.Num("transitionSeconds", 0.0, 0.0, kInf);
        d.summonEnemyId = cell.Id("summonEnemyId", false);
        d.summonCount = static_cast<int>(cell.Int("summonCount", 0, 0, 20));
        d.shieldSeconds = cell.Num("shieldSeconds", 0.0, 0.0, kInf);
        d.summonAtFraction = cell.Num("summonAtFraction", 0.0, 0.0, 1.0);
        d.turnRate = cell.Num("turnRate", 0.0, 0.0, kInf);
        d.decisionDelayMin = cell.Num("decisionDelayMin", 0.0, 0.0, kInf);
        d.decisionDelayMax = cell.Num("decisionDelayMax", 0.0, 0.0, kInf);
        if (cell.bad()) continue;
        c.impl.bossPhases.push_back(std::move(d));
        c.impl.bossPhaseLines.push_back(row.line);
    }
}

void LoadBossPatterns(LoadCtx& c) {
    for (const CsvRow& row : c.csv.rows) {
        Cells cell(c.csv, row, c.errs, c.table);
        BossPatternData d;
        d.id = cell.Id("id", true);
        d.bossId = cell.Id("bossId", true);
        d.phase = static_cast<int>(cell.Int("phase", 1, 1, 9));
        if (cell.Empty("phase")) cell.Err("E_REQUIRED", "phase is required");
        d.skillId = cell.Id("skillId", true);
        d.weight = cell.Num("weight", 1.0, 0.0, kInf);
        d.telegraphSeconds = cell.Num("telegraphSeconds", 0.0, 0.0, kInf);
        d.recoverySeconds = cell.Num("recoverySeconds", 0.0, 0.0, kInf);
        d.cooldown = cell.Num("cooldown", 0.0, 0.0, kInf);
        d.maxRepeat = static_cast<int>(cell.Int("maxRepeat", 0, 0, 100));
        d.playerNearWeightMult = cell.Num("playerNearWeightMult", 1.0, 0.0, kInf);
        d.ignoreIfBehind = cell.Bool("ignoreIfBehind", false);
        if (cell.bad()) continue;
        // O mesmo id repete por fase: a chave é id + phase (docs/06, seção 5a).
        bool dup = false;
        for (const BossPatternData& q : c.impl.bossPatterns) dup = dup || (q.id == d.id && q.phase == d.phase);
        if (dup) { cell.Err("E_DUP_ID", "pattern '" + d.id + "' repeated for phase " + std::to_string(d.phase)); continue; }
        if (!StartsWith(d.id, "pattern.")) { cell.Err("E_ID_PREFIX", "id must start with 'pattern.'"); continue; }
        c.impl.bossPatterns.push_back(std::move(d));
        c.impl.bossPatternLines.push_back(row.line);
    }
}

void LoadEnemyAis(LoadCtx& c) {
    for (const CsvRow& row : c.csv.rows) {
        Cells cell(c.csv, row, c.errs, c.table);
        EnemyAiData d;
        d.enemyId = cell.Id("enemyId", true);
        d.aggroRange = cell.Num("aggroRange", 0.0, 0.0, kInf);
        d.alertRadius = cell.Num("alertRadius", 0.0, 0.0, kInf);
        d.leashRange = cell.Num("leashRange", 0.0, 0.0, kInf);
        d.leashSeconds = cell.Num("leashSeconds", 0.0, 0.0, kInf);
        d.preferredMin = cell.Num("preferredMin", 0.0, 0.0, kInf);
        d.preferredMax = cell.Num("preferredMax", 0.0, 0.0, kInf);
        d.retreatBelow = cell.Num("retreatBelow", 0.0, 0.0, kInf);
        d.retreatMaxSeconds = cell.Num("retreatMaxSeconds", 0.0, 0.0, kInf);
        d.circleMin = cell.Num("circleMin", 0.0, 0.0, kInf);
        d.circleMax = cell.Num("circleMax", 0.0, 0.0, kInf);
        d.circleSpeed = cell.Num("circleSpeed", 0.0, 0.0, kInf);
        d.attackTokens = static_cast<int>(cell.Int("attackTokens", 0, 0, 100));
        d.tokenIntervalMin = cell.Num("tokenIntervalMin", 0.0, 0.0, kInf);
        d.tokenIntervalMax = cell.Num("tokenIntervalMax", 0.0, 0.0, kInf);
        d.fleeLifeFraction = cell.Num("fleeLifeFraction", 0.0, 0.0, 1.0);
        d.fleeSeconds = cell.Num("fleeSeconds", 0.0, 0.0, kInf);
        d.fleeOncePerLife = cell.Bool("fleeOncePerLife", false);
        d.attackCooldown = cell.Num("attackCooldown", 0.0, 0.0, kInf);
        d.maxSimultaneousShooters = static_cast<int>(cell.Int("maxSimultaneousShooters", 0, 0, 100));
        d.requireOnScreen = cell.Bool("requireOnScreen", false);
        if (cell.bad()) continue;
        c.impl.enemyAis.push_back(std::move(d));
        c.impl.enemyAiLines.push_back(row.line);
    }
}

}  // namespace

bool ContentDB::LoadTableCsv(std::string_view tableName, std::string_view csvText) {
    const std::size_t before = errors_.size();
    const std::string table(tableName);
    if (impl_->finalized) {
        PushErr(errors_, table, 0, "E_STATE", "table loaded after Finalize");
        return false;
    }
    const TableDef* def = nullptr;
    for (const TableDef& d : TableDefs()) {
        if (table == d.name) def = &d;
    }
    if (def == nullptr) {
        PushErr(errors_, table, 0, "E_UNKNOWN_TABLE", "unknown table '" + table + "'");
        return false;
    }
    CsvTable csv;
    detail::CsvError cerr;
    if (!detail::ParseCsv(csvText, csv, cerr)) {
        PushErr(errors_, table, cerr.line, cerr.message.substr(0, cerr.message.find(':')).c_str(),
                cerr.message.substr(cerr.message.find(':') == std::string::npos ? 0 : cerr.message.find(':') + 2));
        return false;
    }
    // Cabeçalho exato (qualquer ordem): nada faltando, nada sobrando, sem repetição.
    bool headerOk = true;
    for (const char* col : def->columns) {
        if (std::find(csv.header.begin(), csv.header.end(), std::string_view(col)) == csv.header.end()) {
            PushErr(errors_, table, csv.headerLine, "E_HEADER", std::string("missing column '") + col + "'");
            headerOk = false;
        }
    }
    for (std::size_t i = 0; i < csv.header.size(); ++i) {
        bool known = false;
        for (const char* col : def->columns) known = known || csv.header[i] == col;
        for (const char* col : def->optionalColumns) known = known || csv.header[i] == col;
        if (!known) {
            PushErr(errors_, table, csv.headerLine, "E_HEADER", "unknown column '" + std::string(csv.header[i]) + "'");
            headerOk = false;
        }
        if (std::find(csv.header.begin(), csv.header.begin() + static_cast<std::ptrdiff_t>(i), csv.header[i]) !=
            csv.header.begin() + static_cast<std::ptrdiff_t>(i)) {
            PushErr(errors_, table, csv.headerLine, "E_HEADER", "repeated column '" + std::string(csv.header[i]) + "'");
            headerOk = false;
        }
    }
    if (!headerOk) return false;

    impl_->loadedTables.push_back(table);
    LoadCtx ctx{*impl_, errors_, rules_, contentVersion_, table, csv};
    if (table == "rules.csv") LoadRules(ctx);
    else if (table == "meta.csv") LoadMeta(ctx);
    else if (table == "classes.csv") LoadClasses(ctx);
    else if (table == "class_stats.csv") LoadClassStats(ctx);
    else if (table == "skills.csv") LoadSkills(ctx);
    else if (table == "effects.csv") LoadEffects(ctx);
    else if (table == "enemies.csv") LoadEnemies(ctx);
    else if (table == "enemy_attacks.csv") LoadEnemyAttacks(ctx);
    else if (table == "affixes.csv") LoadAffixes(ctx);
    else if (table == "item_bases.csv") LoadItemBases(ctx);
    else if (table == "uniques.csv") LoadUniques(ctx);
    else if (table == "loot_tables.csv") LoadLootTables(ctx);
    else if (table == "loot_entries.csv") LoadLootEntries(ctx);
    else if (table == "encounters.csv") LoadEncounters(ctx);
    else if (table == "maps.csv") LoadMaps(ctx);
    else if (table == "potions.csv") LoadPotions(ctx);
    else if (table == "elite_modifiers.csv") LoadEliteModifiers(ctx);
    else if (table == "boss_phases.csv") LoadBossPhases(ctx);
    else if (table == "boss_patterns.csv") LoadBossPatterns(ctx);
    else if (table == "enemy_ai.csv") LoadEnemyAis(ctx);
    return errors_.size() == before;
}

bool ContentDB::LoadDirectory(const std::string& path) {
    namespace fs = std::filesystem;
    const std::size_t before = errors_.size();
    std::error_code ec;
    const fs::path dir = fs::u8path(path);
    if (!fs::is_directory(dir, ec)) {
        PushErr(errors_, path, 0, "E_IO", "directory not found");
        return false;
    }
    // Ordem fixa (a da lista de tabelas): resultado independe da ordem do sistema de arquivos.
    for (const TableDef& def : TableDefs()) {
        const fs::path file = dir / def.name;
        if (!fs::is_regular_file(file, ec)) {
            PushErr(errors_, def.name, 0, "E_IO", "table file missing");
            continue;
        }
        std::ifstream in(file, std::ios::binary);
        if (!in) {
            PushErr(errors_, def.name, 0, "E_IO", "cannot open file");
            continue;
        }
        const std::string text((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
        LoadTableCsv(def.name, text);
    }
    // *.csv desconhecido na raiz da pasta também é erro (subpastas, como Loc/, são ignoradas).
    for (fs::directory_iterator it(dir, ec), end; !ec && it != end; it.increment(ec)) {
        if (!it->is_regular_file(ec)) continue;
        const std::string name = it->path().filename().u8string();  // UTF-8 (string() usa a página de código no Windows)
        if (it->path().extension() != ".csv") continue;
        bool known = false;
        for (const TableDef& def : TableDefs()) known = known || name == def.name;
        if (!known) PushErr(errors_, name, 0, "E_UNKNOWN_TABLE", "unknown table file");
    }
    return errors_.size() == before;
}

// ===============================================================================================
// Add programático
// ===============================================================================================
#define SHATTER_DEFINE_ADD(Type, member, prefix)                                                       \
    void ContentDB::Add(Type d) {                                                                      \
        if (impl_->finalized) { PushErr(errors_, #member, 0, "E_STATE", "Add after Finalize"); return; } \
        if (!RegisterId(*impl_, errors_, #member, 0, d.id, prefix)) return;                            \
        impl_->member.Push(std::move(d), 0);                                                           \
    }
SHATTER_DEFINE_ADD(ClassData, classes, "class.")
SHATTER_DEFINE_ADD(SkillData, skills, "skill.")
SHATTER_DEFINE_ADD(EffectData, effects, "effect.")
SHATTER_DEFINE_ADD(EnemyData, enemies, "enemy.")
SHATTER_DEFINE_ADD(AffixData, affixes, "affix.")
SHATTER_DEFINE_ADD(ItemBaseData, bases, "item_base.")
SHATTER_DEFINE_ADD(UniqueData, uniques, "unique.")
SHATTER_DEFINE_ADD(LootTableData, loot, "loot.")
SHATTER_DEFINE_ADD(EncounterTemplate, encounters, "enc.")
SHATTER_DEFINE_ADD(MapData, maps, "map.")
SHATTER_DEFINE_ADD(PotionData, potions, "potion.")
SHATTER_DEFINE_ADD(EliteModifierData, eliteModifiers, "modifier.elite.")
#undef SHATTER_DEFINE_ADD

void ContentDB::Add(BossPatternData d) {
    if (impl_->finalized) { PushErr(errors_, "bossPatterns", 0, "E_STATE", "Add after Finalize"); return; }
    impl_->bossPatterns.push_back(std::move(d));
    impl_->bossPatternLines.push_back(0);
}

void ContentDB::Add(BossPhaseData d) {
    if (impl_->finalized) { PushErr(errors_, "bossPhases", 0, "E_STATE", "Add after Finalize"); return; }
    impl_->bossPhases.push_back(std::move(d));
    impl_->bossPhaseLines.push_back(0);
}

void ContentDB::Add(EnemyAiData d) {
    if (impl_->finalized) { PushErr(errors_, "enemyAis", 0, "E_STATE", "Add after Finalize"); return; }
    impl_->enemyAis.push_back(std::move(d));
    impl_->enemyAiLines.push_back(0);
}

// ===============================================================================================
// Lookups
// ===============================================================================================
const ClassData* ContentDB::FindClass(std::string_view id) const { return impl_->classes.Find(id); }
const SkillData* ContentDB::FindSkill(std::string_view id) const { return impl_->skills.Find(id); }
const EffectData* ContentDB::FindEffect(std::string_view id) const { return impl_->effects.Find(id); }
const EnemyData* ContentDB::FindEnemy(std::string_view id) const { return impl_->enemies.Find(id); }
const AffixData* ContentDB::FindAffix(std::string_view id) const { return impl_->affixes.Find(id); }
const ItemBaseData* ContentDB::FindItemBase(std::string_view id) const { return impl_->bases.Find(id); }
const UniqueData* ContentDB::FindUnique(std::string_view id) const { return impl_->uniques.Find(id); }
const LootTableData* ContentDB::FindLootTable(std::string_view id) const { return impl_->loot.Find(id); }
const EncounterTemplate* ContentDB::FindEncounter(std::string_view id) const { return impl_->encounters.Find(id); }
const MapData* ContentDB::FindMap(std::string_view id) const { return impl_->maps.Find(id); }
const PotionData* ContentDB::FindPotion(std::string_view id) const { return impl_->potions.Find(id); }
const EliteModifierData* ContentDB::FindEliteModifier(std::string_view id) const { return impl_->eliteModifiers.Find(id); }
const BossPatternData* ContentDB::FindBossPattern(std::string_view id, int phase) const {
    for (const BossPatternData& p : impl_->bossPatterns) {
        if (p.id == id && p.phase == phase) return &p;
    }
    return nullptr;
}
const EnemyAiData* ContentDB::FindEnemyAi(std::string_view enemyId) const {
    for (const EnemyAiData& a : impl_->enemyAis) {
        if (a.enemyId == enemyId) return &a;
    }
    return nullptr;
}
const BossPhaseData* ContentDB::FindBossPhase(std::string_view bossId, int phase) const {
    for (const BossPhaseData& p : impl_->bossPhases) {
        if (p.bossId == bossId && p.phase == phase) return &p;
    }
    return nullptr;
}
const std::vector<PotionData>& ContentDB::Potions() const { return impl_->potions.items; }
const std::vector<EliteModifierData>& ContentDB::EliteModifiers() const { return impl_->eliteModifiers.items; }
const std::vector<BossPhaseData>& ContentDB::BossPhases() const { return impl_->bossPhases; }
const std::vector<BossPatternData>& ContentDB::BossPatterns() const { return impl_->bossPatterns; }
const std::vector<EnemyAiData>& ContentDB::EnemyAis() const { return impl_->enemyAis; }
const std::vector<AffixData>& ContentDB::Affixes() const { return impl_->affixes.items; }
const std::vector<ItemBaseData>& ContentDB::ItemBases() const { return impl_->bases.items; }
const std::vector<MapData>& ContentDB::Maps() const { return impl_->maps.items; }
const std::unordered_map<ContentId, const EffectData*>& ContentDB::EffectLookup() const {
    return impl_->effectLookup;
}

// XP do nível `level` para `level+1`: xpBase + xpScale × (level−1)^xpExponent.
// Expoente em múltiplos de 0,5 (validado no CSV): n^k × (sqrt(n) se houver meio) — sem pow.
double ContentDB::XpToNextLevel(int level) const {
    const double n = level > 1 ? static_cast<double>(level - 1) : 0.0;
    const double e2 = std::floor(rules_.xpExponent * 2.0 + 0.5);  // expoente × 2, inteiro
    const int whole = static_cast<int>(e2) / 2;
    const bool half = (static_cast<int>(e2) % 2) != 0;
    double p = 1.0;
    for (int i = 0; i < whole; ++i) p *= n;
    if (half) p *= std::sqrt(n);
    if (n == 0.0 && (whole > 0 || half)) p = 0.0;
    return rules_.xpBase + rules_.xpScale * p;
}

// ===============================================================================================
// Finalize
// ===============================================================================================
namespace {

struct Fin {
    ContentImpl& im;
    std::vector<ContentError>& errs;
    const RulesConstants& rules;

    void E(const char* table, int line, const char* code, const std::string& msg) {
        PushErr(errs, table, line, code, msg);
    }
};

int LootDepth(Fin& f, std::size_t idx, std::vector<int>& state, std::vector<int>& memo) {
    // state: 0 = não visitado, 1 = em visita, 2 = pronto. Devolve profundidade (1 = sem subtabelas); -1 se ciclo.
    if (state[idx] == 2) return memo[idx];
    if (state[idx] == 1) return -1;
    state[idx] = 1;
    int best = 1;
    for (const LootEntry& e : f.im.loot.items[idx].entries) {
        if (e.kind != LootEntryKind::Table) continue;
        const auto it = f.im.loot.index.find(e.refId);
        if (it == f.im.loot.index.end()) continue;  // referência inexistente: já reportada
        const int d = LootDepth(f, it->second, state, memo);
        if (d < 0) { state[idx] = 2; memo[idx] = -1; return -1; }
        best = std::max(best, 1 + d);
    }
    state[idx] = 2;
    memo[idx] = best;
    return best;
}

}  // namespace

bool ContentDB::Finalize() {
    if (impl_->finalized) return impl_->finalizeOk;
    impl_->finalized = true;
    ContentImpl& im = *impl_;
    Fin f{im, errors_, rules_};

    // --- regras globais ---
    if (im.rulesLoaded) {
        for (std::size_t i = 0; i < kRuleKeyCount; ++i) {
            if (!im.ruleSeen[i])
                f.E("rules.csv", 0, "E_REQUIRED", std::string("rule '") + kRuleDefs[i].key + "' missing");
        }
        if (rules_.dodgeIframes > rules_.dodgeDuration) f.E("rules.csv", 0, "E_RULE", "dodge_iframes > dodge_duration");
        if (rules_.minExpeditionHours > rules_.maxExpeditionHours)
            f.E("rules.csv", 0, "E_RULE", "min_expedition_hours > max_expedition_hours");
        if (rules_.simStepFastNonBoss < rules_.simStep) f.E("rules.csv", 0, "E_RULE", "sim_step_fast < sim_step");
        if (3.0 * rules_.vigorBandHours < rules_.maxExpeditionHours)
            f.E("rules.csv", 0, "E_RULE", "3 * vigor_band_hours < max_expedition_hours");
    }
    if (!im.metaLoaded && contentVersion_ == 0) f.E("meta.csv", 0, "E_REQUIRED", "content_version not loaded");
    if (im.rulesLoaded) {
        // Conteúdo vindo de CSV: as tabelas de docs/13 são obrigatórias (docs/17, M4). Sem elas o jogo ficaria sem poção,
        // sem fases de chefe, sem elites e sem fichas de ataque, em silêncio.
        for (const char* t : {"potions.csv", "elite_modifiers.csv", "boss_phases.csv", "boss_patterns.csv", "enemy_ai.csv"}) {
            if (std::find(im.loadedTables.begin(), im.loadedTables.end(), std::string(t)) == im.loadedTables.end())
                f.E(t, 0, "E_REQUIRED", "required table not loaded");
        }
    }

    // --- filhos: class_stats, enemy_attacks, loot_entries (independe da ordem de carga) ---
    for (const ContentImpl::ClassStatRow& r : im.classStatRows) {
        const auto it = im.classes.index.find(r.classId);
        if (it == im.classes.index.end()) {
            f.E("class_stats.csv", r.line, "E_FK", "classId '" + r.classId + "' not in classes.csv");
            continue;
        }
        auto& stats = im.classes.items[it->second].stats;
        const bool dup = std::any_of(stats.begin(), stats.end(), [&](const StatGrowth& g) { return g.stat == r.g.stat; });
        if (dup) { f.E("class_stats.csv", r.line, "E_DUP_ID", "stat repeated for class '" + r.classId + "'"); continue; }
        stats.push_back(r.g);
    }
    for (const ContentImpl::EnemyAttackRow& r : im.enemyAttackRows) {
        const auto it = im.enemies.index.find(r.enemyId);
        if (it == im.enemies.index.end()) {
            f.E("enemy_attacks.csv", r.line, "E_FK", "enemyId '" + r.enemyId + "' not in enemies.csv");
            continue;
        }
        auto& atks = im.enemies.items[it->second].attacks;
        const bool dup = std::any_of(atks.begin(), atks.end(), [&](const EnemyAttack& a) { return a.skillId == r.a.skillId; });
        if (dup) { f.E("enemy_attacks.csv", r.line, "E_DUP_ID", "attack repeated for enemy '" + r.enemyId + "'"); continue; }
        atks.push_back(r.a);
    }
    for (const ContentImpl::LootEntryRow& r : im.lootEntryRows) {
        const auto it = im.loot.index.find(r.tableId);
        if (it == im.loot.index.end()) {
            f.E("loot_entries.csv", r.line, "E_FK", "tableId '" + r.tableId + "' not in loot_tables.csv");
            continue;
        }
        im.loot.items[it->second].entries.push_back(r.e);
    }
    // Linhas das entradas (para erro por entrada), na mesma ordem de anexação.
    // (entradas programáticas têm linha 0.)

    // --- classes ---
    for (std::size_t i = 0; i < im.classes.items.size(); ++i) {
        const ClassData& c = im.classes.items[i];
        const int ln = im.classes.lines[i];
        const SkillData* s = im.skills.Find(c.startingSkill);
        if (s == nullptr) f.E("classes.csv", ln, "E_FK", "startingSkill '" + c.startingSkill + "' not in skills.csv");
        else if (s->unlockLevel != 1) f.E("classes.csv", ln, "E_RULE", "startingSkill must have unlockLevel 1");
        bool life = false, res = false;
        for (const StatGrowth& g : c.stats) {
            if (g.stat == StatId::Life && g.base > 0.0) life = true;
            if (g.stat == StatId::Resource) res = true;
        }
        if (!life) f.E("classes.csv", ln, "E_RULE", "class needs 'life' with base > 0 in class_stats.csv");
        if (!res) f.E("classes.csv", ln, "E_RULE", "class needs 'resource' in class_stats.csv");
        for (const ContentId& sp : c.specializations) {
            if (!StartsWith(sp, "spec.")) f.E("classes.csv", ln, "E_ID_PREFIX", "specialization '" + sp + "' must start with 'spec.'");
        }
    }

    // --- skills ---
    for (std::size_t i = 0; i < im.skills.items.size(); ++i) {
        const SkillData& s = im.skills.items[i];
        const int ln = im.skills.lines[i];
        if (!s.classId.empty()) {
            if (im.classes.Find(s.classId) == nullptr) {
                f.E("skills.csv", ln, "E_FK", "classId '" + s.classId + "' not in classes.csv");
            } else {
                const std::string seg = s.classId.substr(std::string_view("class.").size());
                if (!StartsWith(s.id, "skill." + seg + "."))
                    f.E("skills.csv", ln, "E_RULE", "id must start with 'skill." + seg + ".'");
            }
        } else if (!StartsWith(s.id, "skill.enemy.") && !StartsWith(s.id, "skill.common.")) {
            f.E("skills.csv", ln, "E_RULE", "skill without class must be skill.enemy.* or skill.common.*");
        }
        if (s.cooldown > 0.0 && s.cooldown < rules_.minCooldown)
            f.E("skills.csv", ln, "E_RANGE", "cooldown below cooldown_min");
        for (const ContentId& e : s.onHitEffects)
            if (im.effects.Find(e) == nullptr) f.E("skills.csv", ln, "E_FK", "onHitEffects: '" + e + "' not in effects.csv");
        for (const ContentId& e : s.selfEffects)
            if (im.effects.Find(e) == nullptr) f.E("skills.csv", ln, "E_FK", "selfEffects: '" + e + "' not in effects.csv");
        if (s.idle.supported) {
            if (s.idle.paritySampleSize == 0) f.E("skills.csv", ln, "E_RULE", "idleSupported requires idleParitySampleSize > 0");
            if (s.idle.avgTargetsHit <= 0.0 && s.idle.fractionOfGroupHit <= 0.0)
                f.E("skills.csv", ln, "E_RULE", "idleSupported requires idle targets");
            if (s.idle.calibration == IdleCalibration::None)
                f.E("skills.csv", ln, "E_RULE", "idleSupported requires idleCalibration manual_estimate or bot_parity");
        }
    }

    // --- efeitos ---
    for (std::size_t i = 0; i < im.effects.items.size(); ++i) {
        const EffectData& e = im.effects.items[i];
        const int ln = im.effects.lines[i];
        bool dmg = false;
        for (double d : e.damagePerTick) dmg = dmg || d > 0.0;
        if (dmg && e.tickInterval <= 0.0) f.E("effects.csv", ln, "E_RULE", "damage per tick requires tickInterval > 0");
        if (e.tickInterval > 0.0 && e.duration <= 0.0) f.E("effects.csv", ln, "E_RULE", "tickInterval requires duration > 0");
        if (e.maxStacks < 1) f.E("effects.csv", ln, "E_RANGE", "maxStacks < 1");
    }

    // --- inimigos ---
    for (std::size_t i = 0; i < im.enemies.items.size(); ++i) {
        const EnemyData& e = im.enemies.items[i];
        const int ln = im.enemies.lines[i];
        bool life = false;
        for (const StatGrowth& g : e.stats) life = life || (g.stat == StatId::Life && g.base > 0.0);
        if (!life) f.E("enemies.csv", ln, "E_RULE", "enemy needs 'life' with base > 0");
        if (e.attacks.empty()) f.E("enemies.csv", ln, "E_RULE", "enemy needs at least one row in enemy_attacks.csv");
        if (!e.lootTableId.empty() && im.loot.Find(e.lootTableId) == nullptr)
            f.E("enemies.csv", ln, "E_FK", "lootTableId '" + e.lootTableId + "' not in loot_tables.csv");
    }
    for (const ContentImpl::EnemyAttackRow& r : im.enemyAttackRows) {
        if (im.skills.Find(r.a.skillId) == nullptr)
            f.E("enemy_attacks.csv", r.line, "E_FK", "skillId '" + r.a.skillId + "' not in skills.csv");
    }
    for (std::size_t i = 0; i < im.enemies.items.size(); ++i) {  // ataques programáticos
        if (im.enemies.lines[i] != 0) continue;
        for (const EnemyAttack& a : im.enemies.items[i].attacks)
            if (im.skills.Find(a.skillId) == nullptr) f.E("enemies.csv", 0, "E_FK", "attack skill '" + a.skillId + "' not found");
    }

    // --- afixos ---
    for (std::size_t i = 0; i < im.affixes.items.size(); ++i) {
        const AffixData& a = im.affixes.items[i];
        const int ln = im.affixes.lines[i];
        if (a.minValue > a.maxValue) f.E("affixes.csv", ln, "E_RANGE", "minValue > maxValue");
        if (!(a.weight > 0.0)) f.E("affixes.csv", ln, "E_RANGE", "weight must be > 0");
        if (a.minItemLevel < 1) f.E("affixes.csv", ln, "E_RANGE", "minItemLevel < 1");
    }

    // --- bases de item ---
    for (std::size_t i = 0; i < im.bases.items.size(); ++i) {
        const ItemBaseData& b = im.bases.items[i];
        const int ln = im.bases.lines[i];
        double wdmg = 0.0;
        for (double d : b.weaponDamage) wdmg += d;
        if (b.slot == ItemSlot::MainHand) {
            if (b.attackTime <= 0.0) f.E("item_bases.csv", ln, "E_RULE", "main_hand requires attackTime > 0");
            if (wdmg <= 0.0) f.E("item_bases.csv", ln, "E_RULE", "main_hand requires weapon damage > 0");
            if (b.weaponTags != Mask(Tag::Melee) && b.weaponTags != Mask(Tag::Projectile))
                f.E("item_bases.csv", ln, "E_RULE", "main_hand weaponTags must be exactly melee or projectile");
        } else if (wdmg > 0.0 || b.attackTime > 0.0 || b.weaponTags != 0) {
            f.E("item_bases.csv", ln, "E_RULE", "only main_hand may have weapon damage, attackTime or weaponTags");
        }
    }

    // --- únicos ---
    for (std::size_t i = 0; i < im.uniques.items.size(); ++i) {
        const UniqueData& u = im.uniques.items[i];
        const int ln = im.uniques.lines[i];
        if (im.bases.Find(u.baseId) == nullptr) f.E("uniques.csv", ln, "E_FK", "baseId '" + u.baseId + "' not in item_bases.csv");
        if (!u.ruleEffectId.empty() && im.effects.Find(u.ruleEffectId) == nullptr)
            f.E("uniques.csv", ln, "E_FK", "ruleEffectId '" + u.ruleEffectId + "' not in effects.csv");
        if (u.idleSupported) {
            if (u.idleParitySampleSize == 0) f.E("uniques.csv", ln, "E_RULE", "idleSupported requires idleParitySampleSize > 0");
            if (u.idleCalibration == IdleCalibration::None)
                f.E("uniques.csv", ln, "E_RULE", "idleSupported requires idleCalibration manual_estimate or bot_parity");
        }
    }

    // --- tabelas de loot e entradas ---
    for (std::size_t i = 0; i < im.loot.items.size(); ++i) {
        const LootTableData& t = im.loot.items[i];
        const int ln = im.loot.lines[i];
        if (t.entries.empty()) f.E("loot_tables.csv", ln, "E_RULE", "table needs at least one entry");
        if (t.rarityWeights[0] + t.rarityWeights[1] + t.rarityWeights[2] <= 0.0)
            f.E("loot_tables.csv", ln, "E_RULE", "rarity weights must sum > 0");
        if (t.rolls < 1) f.E("loot_tables.csv", ln, "E_RANGE", "rolls < 1");
    }
    {
        // linha de cada entrada: para tabelas vindas do CSV, as linhas estão em lootEntryRows (mesma ordem de anexação).
        std::vector<std::size_t> cursor(im.loot.items.size(), 0);
        auto entryLine = [&](std::size_t tableIdx, std::size_t entryIdx) -> int {
            // conta quantas entradas programáticas existem antes das do CSV
            const std::size_t total = im.loot.items[tableIdx].entries.size();
            std::size_t csvCount = 0;
            for (const ContentImpl::LootEntryRow& r : im.lootEntryRows) {
                const auto it = im.loot.index.find(r.tableId);
                if (it != im.loot.index.end() && it->second == tableIdx) ++csvCount;
            }
            const std::size_t progCount = total - csvCount;
            if (entryIdx < progCount) return 0;
            std::size_t k = entryIdx - progCount;
            for (const ContentImpl::LootEntryRow& r : im.lootEntryRows) {
                const auto it = im.loot.index.find(r.tableId);
                if (it != im.loot.index.end() && it->second == tableIdx) {
                    if (k == 0) return r.line;
                    --k;
                }
            }
            return 0;
        };
        (void)cursor;
        for (std::size_t ti = 0; ti < im.loot.items.size(); ++ti) {
            const auto& entries = im.loot.items[ti].entries;
            for (std::size_t ei = 0; ei < entries.size(); ++ei) {
                const LootEntry& e = entries[ei];
                const int ln = entryLine(ti, ei);
                const char* T = "loot_entries.csv";
                if (!(e.weight > 0.0) && !e.IsFixed()) f.E(T, ln, "E_RANGE", "weight must be > 0");
                if (e.IsFixed() && !e.manualOnly) f.E(T, ln, "E_RULE", "fixed entries (fixedChance/guaranteeFirstKill/pityKills) require manualOnly = true");
                if (e.IsFixed() && e.kind == LootEntryKind::Nothing) f.E(T, ln, "E_RULE", "fixed entry cannot be 'nothing'");
                if (e.minAmount > e.maxAmount) f.E(T, ln, "E_RANGE", "minAmount > maxAmount");
                if (e.minAreaLevel > e.maxAreaLevel) f.E(T, ln, "E_RANGE", "minAreaLevel > maxAreaLevel");
                switch (e.kind) {
                    case LootEntryKind::ItemBase:
                        if (im.bases.Find(e.refId) == nullptr) f.E(T, ln, "E_FK", "refId '" + e.refId + "' not in item_bases.csv");
                        break;
                    case LootEntryKind::Unique:
                        if (im.uniques.Find(e.refId) == nullptr) f.E(T, ln, "E_FK", "refId '" + e.refId + "' not in uniques.csv");
                        break;
                    case LootEntryKind::Table:
                        if (im.loot.Find(e.refId) == nullptr) f.E(T, ln, "E_FK", "refId '" + e.refId + "' not in loot_tables.csv");
                        break;
                    case LootEntryKind::Stack:
                        // decisão P3: sem tabela para currency/material/page/sigil: só prefixo e formato
                        if (!(StartsWith(e.refId, "currency.") || StartsWith(e.refId, "material.") ||
                              StartsWith(e.refId, "page.") || StartsWith(e.refId, "sigil.common.")))
                            f.E(T, ln, "E_ID_PREFIX", "stack refId must start with currency., material., page. or sigil.common.");
                        if (e.refId == "material.echo_fragment")
                            f.E(T, ln, "E_RULE", "material.echo_fragment is not a stack (use echo_fragment)");
                        break;
                    case LootEntryKind::SpecBook:
                        if (!StartsWith(e.refId, "book.spec.")) f.E(T, ln, "E_ID_PREFIX", "spec_book refId must start with 'book.spec.'");
                        break;
                    case LootEntryKind::MapStone:
                        if (!StartsWith(e.refId, "map_stone.")) f.E(T, ln, "E_ID_PREFIX", "map_stone refId must start with 'map_stone.'");
                        break;
                    case LootEntryKind::EchoFragment:
                        if (e.refId != "material.echo_fragment") f.E(T, ln, "E_RULE", "echo_fragment refId must be material.echo_fragment");
                        break;
                    case LootEntryKind::Nothing:
                        if (!e.refId.empty()) f.E(T, ln, "E_RULE", "nothing must not have refId");
                        break;
                }
                const bool top = e.kind == LootEntryKind::Unique || e.kind == LootEntryKind::SpecBook ||
                                 e.kind == LootEntryKind::MapStone || e.kind == LootEntryKind::EchoFragment;
                if (top && !e.manualOnly) f.E(T, ln, "E_RULE", "top-tier entries require manualOnly = true");
                if (e.IsFixed()) {
                    // Entrada fixa só rola na tabela de TOPO do chefe (loot.cpp): em subtabela ou em tabela de outro inimigo
                    // o Finalize aceitaria uma entrada que nunca cai.
                    const ContentId& tid = im.loot.items[ti].id;
                    bool bossTop = false, subtable = false;
                    for (const EnemyData& en : im.enemies.items) bossTop = bossTop || (en.isBoss && en.lootTableId == tid);
                    for (const LootTableData& other : im.loot.items)
                        for (const LootEntry& oe : other.entries) subtable = subtable || (oe.kind == LootEntryKind::Table && oe.refId == tid);
                    if (!bossTop || subtable)
                        f.E(T, ln, "E_RULE", "fixed entry must be in the top-level loot table of a boss (not a subtable)");
                }
            }
        }
    }
    {
        std::vector<int> state(im.loot.items.size(), 0), memo(im.loot.items.size(), 0);
        for (std::size_t i = 0; i < im.loot.items.size(); ++i) {
            const int d = LootDepth(f, i, state, memo);
            if (d < 0) f.E("loot_tables.csv", im.loot.lines[i], "E_RULE", "loot subtable cycle");
            else if (d > 8) f.E("loot_tables.csv", im.loot.lines[i], "E_RULE", "loot subtable depth > 8");
        }
    }

    // --- encontros ---
    for (std::size_t i = 0; i < im.encounters.items.size(); ++i) {
        const EncounterTemplate& e = im.encounters.items[i];
        const int ln = im.encounters.lines[i];
        if (e.groups.empty()) f.E("encounters.csv", ln, "E_REQUIRED", "groups must not be empty");
        bool hasBoss = false;
        for (const EncounterGroup& g : e.groups) {
            const EnemyData* en = im.enemies.Find(g.enemyId);
            if (en == nullptr) f.E("encounters.csv", ln, "E_FK", "groups: '" + g.enemyId + "' not in enemies.csv");
            else hasBoss = hasBoss || en->isBoss;
            if (g.countMin > g.countMax) f.E("encounters.csv", ln, "E_RANGE", "groups: min > max");
            if (g.countMin < 1) f.E("encounters.csv", ln, "E_RANGE", "groups: min must be >= 1");
            if (g.eliteChance < 0.0 || g.eliteChance > 1.0) f.E("encounters.csv", ln, "E_RANGE", "groups: elite chance out of [0,1]");
        }
        if (e.isBoss != hasBoss && !e.groups.empty() &&
            std::all_of(e.groups.begin(), e.groups.end(), [&](const EncounterGroup& g) { return im.enemies.Find(g.enemyId) != nullptr; }))
            f.E("encounters.csv", ln, "E_RULE", "isBoss must match the presence of a boss in groups");
    }

    // --- mapas ---
    for (std::size_t i = 0; i < im.maps.items.size(); ++i) {
        const MapData& m = im.maps.items[i];
        const int ln = im.maps.lines[i];
        if (m.encounters.empty()) f.E("maps.csv", ln, "E_REQUIRED", "encounters must not be empty");
        for (const ContentId& id : m.encounters) {
            const EncounterTemplate* e = im.encounters.Find(id);
            if (e == nullptr) f.E("maps.csv", ln, "E_FK", "encounters: '" + id + "' not in encounters.csv");
            else if (e->isBoss) f.E("maps.csv", ln, "E_RULE", "boss encounter '" + id + "' belongs in bossEncounter");
        }
        if (!m.bossEncounter.empty()) {
            const EncounterTemplate* e = im.encounters.Find(m.bossEncounter);
            if (e == nullptr) f.E("maps.csv", ln, "E_FK", "bossEncounter '" + m.bossEncounter + "' not in encounters.csv");
            else if (!e->isBoss) f.E("maps.csv", ln, "E_RULE", "bossEncounter must have isBoss = true");
        }
        if (!m.areaLootTable.empty() && im.loot.Find(m.areaLootTable) == nullptr)
            f.E("maps.csv", ln, "E_FK", "areaLootTable '" + m.areaLootTable + "' not in loot_tables.csv");
    }

    // --- ADIÇÃO (docs/13): poções, modificadores, fases, padrões, IA ---
    for (std::size_t i = 0; i < im.potions.items.size(); ++i) {
        const PotionData& p = im.potions.items[i];
        const int ln = im.potions.lines[i];
        if (!(p.fractionOfMaxLife > 0.0)) f.E("potions.csv", ln, "E_RANGE", "fractionOfMaxLife must be > 0");
        if (p.kind == PotionKind::Barrier && !(p.duration > 0.0)) f.E("potions.csv", ln, "E_RULE", "barrier potion requires duration > 0");
        if (!(p.rechargeSeconds > 0.0)) f.E("potions.csv", ln, "E_RANGE", "rechargeSeconds must be > 0");
        for (std::size_t j = 0; j < i; ++j) {
            if (im.potions.items[j].hotkeySlot == p.hotkeySlot) f.E("potions.csv", ln, "E_DUP_ID", "hotkeySlot repeated");
        }
    }
    for (std::size_t i = 0; i < im.eliteModifiers.items.size(); ++i) {
        const EliteModifierData& m = im.eliteModifiers.items[i];
        const int ln = im.eliteModifiers.lines[i];
        if (m.deathExplosionRadius > 0.0 && !(m.deathExplosionDamage > 0.0))
            f.E("elite_modifiers.csv", ln, "E_RULE", "deathExplosionRadius > 0 requires deathExplosionDamage > 0");
    }
    for (std::size_t i = 0; i < im.bossPhases.size(); ++i) {
        const BossPhaseData& ph = im.bossPhases[i];
        const int ln = im.bossPhaseLines[i];
        const char* T = "boss_phases.csv";
        const EnemyData* boss = im.enemies.Find(ph.bossId);
        if (boss == nullptr) f.E(T, ln, "E_FK", "bossId '" + ph.bossId + "' not in enemies.csv");
        else if (!boss->isBoss) f.E(T, ln, "E_RULE", "bossId '" + ph.bossId + "' is not a boss (isBoss = true)");
        if (ph.decisionDelayMin > ph.decisionDelayMax) f.E(T, ln, "E_RANGE", "decisionDelayMin > decisionDelayMax");
        if (!ph.summonEnemyId.empty() && im.enemies.Find(ph.summonEnemyId) == nullptr)
            f.E(T, ln, "E_FK", "summonEnemyId '" + ph.summonEnemyId + "' not in enemies.csv");
        if (ph.summonCount > 0 && ph.summonEnemyId.empty()) f.E(T, ln, "E_RULE", "summonCount > 0 requires summonEnemyId");
        if (ph.summonCount > 0 && !(ph.summonAtFraction > 0.0 && ph.summonAtFraction < 1.0))
            f.E(T, ln, "E_RULE", "summonCount > 0 requires summonAtFraction in (0, 1)");
        for (std::size_t j = 0; j < i; ++j) {
            if (im.bossPhases[j].bossId == ph.bossId && im.bossPhases[j].phase == ph.phase)
                f.E(T, ln, "E_DUP_ID", "phase repeated for boss '" + ph.bossId + "'");
        }
    }
    {
        // Fases de cada chefe: 1..N sem buracos e com limiares estritamente decrescentes.
        std::vector<ContentId> seen;
        for (const BossPhaseData& ph : im.bossPhases) {
            if (std::find(seen.begin(), seen.end(), ph.bossId) != seen.end()) continue;
            seen.push_back(ph.bossId);
            int n = 0;
            for (const BossPhaseData& q : im.bossPhases) n += q.bossId == ph.bossId ? 1 : 0;
            double prev = 2.0;
            for (int k = 1; k <= n; ++k) {
                const BossPhaseData* q = nullptr;
                for (const BossPhaseData& x : im.bossPhases) {
                    if (x.bossId == ph.bossId && x.phase == k) q = &x;
                }
                if (q == nullptr) { f.E("boss_phases.csv", 0, "E_RULE", "boss '" + ph.bossId + "' phases must be 1..N without gaps"); break; }
                if (!(q->lifeThreshold < prev)) f.E("boss_phases.csv", 0, "E_RULE", "boss '" + ph.bossId + "' lifeThreshold must decrease with phase");
                prev = q->lifeThreshold;
            }
        }
    }
    for (std::size_t i = 0; i < im.bossPatterns.size(); ++i) {
        const BossPatternData& pt = im.bossPatterns[i];
        const int ln = im.bossPatternLines[i];
        const char* T = "boss_patterns.csv";
        const EnemyData* boss = im.enemies.Find(pt.bossId);
        if (boss == nullptr) f.E(T, ln, "E_FK", "bossId '" + pt.bossId + "' not in enemies.csv");
        else if (!boss->isBoss) f.E(T, ln, "E_RULE", "bossId '" + pt.bossId + "' is not a boss (isBoss = true)");
        if (im.skills.Find(pt.skillId) == nullptr) f.E(T, ln, "E_FK", "skillId '" + pt.skillId + "' not in skills.csv");
        bool hasPhase = false;
        bool bossHasPhases = false;
        for (const BossPhaseData& ph : im.bossPhases) {
            if (ph.bossId != pt.bossId) continue;
            bossHasPhases = true;
            hasPhase = hasPhase || ph.phase == pt.phase;
        }
        if (bossHasPhases && !hasPhase) f.E(T, ln, "E_FK", "phase " + std::to_string(pt.phase) + " not in boss_phases.csv");
    }
    for (const BossPhaseData& ph : im.bossPhases) {
        bool any = false;
        for (const BossPatternData& pt : im.bossPatterns) any = any || (pt.bossId == ph.bossId && pt.phase == ph.phase && pt.weight > 0.0);
        if (!any) f.E("boss_patterns.csv", 0, "E_RULE", "boss '" + ph.bossId + "' phase " + std::to_string(ph.phase) + " needs a pattern with weight > 0");
    }
    for (std::size_t i = 0; i < im.enemyAis.size(); ++i) {
        const EnemyAiData& a = im.enemyAis[i];
        const int ln = im.enemyAiLines[i];
        const char* T = "enemy_ai.csv";
        if (im.enemies.Find(a.enemyId) == nullptr) f.E(T, ln, "E_FK", "enemyId '" + a.enemyId + "' not in enemies.csv");
        if (a.preferredMin > a.preferredMax) f.E(T, ln, "E_RANGE", "preferredMin > preferredMax");
        if (a.circleMin > a.circleMax) f.E(T, ln, "E_RANGE", "circleMin > circleMax");
        if (a.tokenIntervalMin > a.tokenIntervalMax) f.E(T, ln, "E_RANGE", "tokenIntervalMin > tokenIntervalMax");
        for (std::size_t j = 0; j < i; ++j) {
            if (im.enemyAis[j].enemyId == a.enemyId) f.E(T, ln, "E_DUP_ID", "enemy repeated in enemy_ai.csv");
        }
    }
    for (std::size_t i = 0; i < im.enemies.items.size(); ++i) {
        const EnemyData& e = im.enemies.items[i];
        const int ln = im.enemies.lines[i];
        if (!e.modifierId.empty() && im.eliteModifiers.Find(e.modifierId) == nullptr)
            f.E("enemies.csv", ln, "E_FK", "modifierId '" + e.modifierId + "' not in elite_modifiers.csv");
        if (!e.eliteLootTableId.empty() && im.loot.Find(e.eliteLootTableId) == nullptr)
            f.E("enemies.csv", ln, "E_FK", "eliteLootTableId '" + e.eliteLootTableId + "' not in loot_tables.csv");
    }

    // --- lookup de efeitos ---
    im.effectLookup.clear();
    for (const EffectData& e : im.effects.items) im.effectLookup.emplace(e.id, &e);

    im.finalizeOk = errors_.empty();
    return im.finalizeOk;
}

}  // namespace shatter
