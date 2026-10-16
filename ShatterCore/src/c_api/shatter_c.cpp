// ShatterCore — implementação da API C (include/shatter/shatter_c.h; docs/04_arquitetura.md, seção 9).
// Fina: valida argumentos, converte structs/JSON e chama o core. Nenhuma regra nova mora aqui.
// Sem exceções, sem estado global; toda função exportada é noexcept (falha de alocação é fatal).
#include "shatter/shatter_c.h"

#include <cstddef>
#include <cstring>
#include <limits>
#include <memory>
#include <new>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "shatter/shatter.h"

// Handles opacos: as structs do header C são definidas aqui (namespace global, nomes do header).
struct shatter_db {
    shatter::ContentDB db;
    bool finalized = false;
    bool ok = false;
};
struct shatter_save {
    shatter::SaveData data;
};
struct shatter_statblock {
    shatter::StatBlock sb;
};
struct shatter_effects {
    shatter::EffectContainer fx;
    std::vector<shatter::EffectEvent> events;  // eventos do último tick
};

namespace {

using namespace shatter;
using json::Value;

// ---------------------------------------------------------------------------------------------
// Layout das structs blittable (conferido também por static_assert: x64, Windows e Linux).
// ---------------------------------------------------------------------------------------------
static_assert(sizeof(shatter_error) == 264, "shatter_error");
static_assert(sizeof(shatter_rng) == 16, "shatter_rng");
static_assert(sizeof(shatter_rules) == 288, "shatter_rules");
static_assert(offsetof(shatter_rules, max_ai_rules) == 240, "shatter_rules.max_ai_rules");
static_assert(offsetof(shatter_rules, sim_fast_enabled) == 280, "shatter_rules.sim_fast_enabled");
static_assert(sizeof(shatter_modifier) == 16, "shatter_modifier");
static_assert(sizeof(shatter_hit_input) == 64, "shatter_hit_input");
static_assert(offsetof(shatter_hit_input, skill_tags) == 56, "shatter_hit_input.skill_tags");
static_assert(sizeof(shatter_hit_result) == 112, "shatter_hit_result");
static_assert(offsetof(shatter_hit_result, outcome) == 104, "shatter_hit_result.outcome");
static_assert(sizeof(shatter_effect_event) == 168, "shatter_effect_event");
static_assert(sizeof(shatter_clock_input) == 32, "shatter_clock_input");
static_assert(sizeof(shatter_trusted_now) == 16, "shatter_trusted_now");
static_assert(sizeof(shatter_offline_window) == 16, "shatter_offline_window");
static_assert(sizeof(shatter_loot_context) == 24, "shatter_loot_context");
static_assert(sizeof(shatter_load_report) == 8, "shatter_load_report");
static_assert(sizeof(shatter_save_summary) == 56, "shatter_save_summary");
static_assert(sizeof(shatter_area_run_reward) == 8, "shatter_area_run_reward");
static_assert(sizeof(shatter_forecast) == 64, "shatter_forecast");
static_assert(SHATTER_STAT_COUNT == kStatCount, "StatId e SHATTER_STAT_* divergiram");
static_assert(SHATTER_TAG_PHYSICAL == static_cast<int>(Tag::Physical), "Tag e SHATTER_TAG_* divergiram");
static_assert(SHATTER_STOP_CONTENT_MISMATCH == static_cast<int>(StopReason::ContentMismatch), "StopReason");
static_assert(SHATTER_START_UNKNOWN_CONTENT == static_cast<int>(StartCheck::UnknownContent), "StartCheck");
static_assert(SHATTER_TRIGGER_ON_TAKE_DAMAGE == static_cast<int>(TriggerKind::OnTakeDamage), "TriggerKind");

#define SHATTER_LAYOUT_SIZE(T) static_cast<std::uint32_t>(sizeof(T))
#define SHATTER_LAYOUT_OFF(T, f) static_cast<std::uint32_t>(offsetof(T, f))

// Ordem fixa (o C# monta a mesma lista): para cada struct, sizeof e depois offsetof dos campos.
const std::uint32_t kLayout[] = {
    SHATTER_LAYOUT_SIZE(shatter_error), SHATTER_LAYOUT_OFF(shatter_error, code), SHATTER_LAYOUT_OFF(shatter_error, line),
    SHATTER_LAYOUT_OFF(shatter_error, message),
    SHATTER_LAYOUT_SIZE(shatter_rng), SHATTER_LAYOUT_OFF(shatter_rng, state), SHATTER_LAYOUT_OFF(shatter_rng, inc),
    SHATTER_LAYOUT_SIZE(shatter_rules), SHATTER_LAYOUT_OFF(shatter_rules, crit_multiplier_base),
    SHATTER_LAYOUT_OFF(shatter_rules, max_ai_rules), SHATTER_LAYOUT_OFF(shatter_rules, sim_fast_enabled),
    SHATTER_LAYOUT_SIZE(shatter_modifier), SHATTER_LAYOUT_OFF(shatter_modifier, value),
    SHATTER_LAYOUT_OFF(shatter_modifier, required_tags), SHATTER_LAYOUT_OFF(shatter_modifier, stat),
    SHATTER_LAYOUT_OFF(shatter_modifier, kind),
    SHATTER_LAYOUT_SIZE(shatter_hit_input), SHATTER_LAYOUT_OFF(shatter_hit_input, base_damage),
    SHATTER_LAYOUT_OFF(shatter_hit_input, coefficient), SHATTER_LAYOUT_OFF(shatter_hit_input, defender_life),
    SHATTER_LAYOUT_OFF(shatter_hit_input, defender_barrier), SHATTER_LAYOUT_OFF(shatter_hit_input, skill_tags),
    SHATTER_LAYOUT_OFF(shatter_hit_input, is_damage_over_time), SHATTER_LAYOUT_OFF(shatter_hit_input, can_be_blocked),
    SHATTER_LAYOUT_SIZE(shatter_hit_result), SHATTER_LAYOUT_OFF(shatter_hit_result, after_modifiers),
    SHATTER_LAYOUT_OFF(shatter_hit_result, after_mitigation), SHATTER_LAYOUT_OFF(shatter_hit_result, total_damage),
    SHATTER_LAYOUT_OFF(shatter_hit_result, absorbed_by_barrier), SHATTER_LAYOUT_OFF(shatter_hit_result, life_lost),
    SHATTER_LAYOUT_OFF(shatter_hit_result, defender_life_after),
    SHATTER_LAYOUT_OFF(shatter_hit_result, defender_barrier_after), SHATTER_LAYOUT_OFF(shatter_hit_result, outcome),
    SHATTER_LAYOUT_OFF(shatter_hit_result, critical), SHATTER_LAYOUT_OFF(shatter_hit_result, landed),
    SHATTER_LAYOUT_OFF(shatter_hit_result, killed),
    SHATTER_LAYOUT_SIZE(shatter_effect_event), SHATTER_LAYOUT_OFF(shatter_effect_event, kind),
    SHATTER_LAYOUT_OFF(shatter_effect_event, effect_id_len), SHATTER_LAYOUT_OFF(shatter_effect_event, damage),
    SHATTER_LAYOUT_OFF(shatter_effect_event, effect_id),
    SHATTER_LAYOUT_SIZE(shatter_clock_input), SHATTER_LAYOUT_OFF(shatter_clock_input, local_now_utc),
    SHATTER_LAYOUT_OFF(shatter_clock_input, steam_now_utc), SHATTER_LAYOUT_OFF(shatter_clock_input, last_seen_utc),
    SHATTER_LAYOUT_OFF(shatter_clock_input, has_steam_time),
    SHATTER_LAYOUT_SIZE(shatter_trusted_now), SHATTER_LAYOUT_OFF(shatter_trusted_now, now),
    SHATTER_LAYOUT_OFF(shatter_trusted_now, used_steam), SHATTER_LAYOUT_OFF(shatter_trusted_now, rollback_detected),
    SHATTER_LAYOUT_SIZE(shatter_offline_window), SHATTER_LAYOUT_OFF(shatter_offline_window, effective_seconds),
    SHATTER_LAYOUT_OFF(shatter_offline_window, finished), SHATTER_LAYOUT_OFF(shatter_offline_window, ended_by_rollback),
    SHATTER_LAYOUT_SIZE(shatter_loot_context), SHATTER_LAYOUT_OFF(shatter_loot_context, quantity_mult),
    SHATTER_LAYOUT_OFF(shatter_loot_context, mode), SHATTER_LAYOUT_OFF(shatter_loot_context, area_level),
    SHATTER_LAYOUT_OFF(shatter_loot_context, rares_already_dropped), SHATTER_LAYOUT_OFF(shatter_loot_context, max_rares),
    SHATTER_LAYOUT_SIZE(shatter_load_report), SHATTER_LAYOUT_OFF(shatter_load_report, status),
    SHATTER_LAYOUT_OFF(shatter_load_report, used_backup),
    SHATTER_LAYOUT_SIZE(shatter_save_summary), SHATTER_LAYOUT_OFF(shatter_save_summary, next_item_uid),
    SHATTER_LAYOUT_OFF(shatter_save_summary, last_seen_utc), SHATTER_LAYOUT_OFF(shatter_save_summary, last_rest_day),
    SHATTER_LAYOUT_OFF(shatter_save_summary, content_version), SHATTER_LAYOUT_OFF(shatter_save_summary, save_version),
    SHATTER_LAYOUT_OFF(shatter_save_summary, character_count), SHATTER_LAYOUT_OFF(shatter_save_summary, marker_charges),
    SHATTER_LAYOUT_OFF(shatter_save_summary, expedition_slots),
    SHATTER_LAYOUT_OFF(shatter_save_summary, expedition_count),
    SHATTER_LAYOUT_OFF(shatter_save_summary, running_expedition),
    SHATTER_LAYOUT_SIZE(shatter_area_run_reward), SHATTER_LAYOUT_OFF(shatter_area_run_reward, charges_gained),
    SHATTER_LAYOUT_OFF(shatter_area_run_reward, new_conquest),
    SHATTER_LAYOUT_SIZE(shatter_forecast), SHATTER_LAYOUT_OFF(shatter_forecast, xp_p10),
    SHATTER_LAYOUT_OFF(shatter_forecast, gold_p10), SHATTER_LAYOUT_OFF(shatter_forecast, retreat_probability),
    SHATTER_LAYOUT_OFF(shatter_forecast, worst_resist_gap),
};
static_assert(sizeof(kLayout) / sizeof(kLayout[0]) == SHATTER_LAYOUT_COUNT, "SHATTER_LAYOUT_COUNT desatualizado");

#undef SHATTER_LAYOUT_SIZE
#undef SHATTER_LAYOUT_OFF

// ---------------------------------------------------------------------------------------------
// Erros, texto e buffers
// ---------------------------------------------------------------------------------------------
void ClearError(shatter_error* err) {
    if (err == nullptr) return;
    err->code = SHATTER_OK;
    err->line = 0;
    err->message[0] = '\0';
}

shatter_status SetError(shatter_error* err, shatter_status code, std::string_view msg, int line = 0) {
    if (err != nullptr) {
        err->code = code;
        err->line = line;
        std::size_t n = msg.size() < sizeof(err->message) - 1 ? msg.size() : sizeof(err->message) - 1;
        // Corta antes de um byte de continuação para não deixar UTF-8 quebrado.
        while (n > 0 && n < msg.size() && (static_cast<unsigned char>(msg[n]) & 0xC0u) == 0x80u) --n;
        if (n > 0) std::memcpy(err->message, msg.data(), n);
        err->message[n] = '\0';
    }
    return code;
}

bool ValidUtf8(std::string_view s) {
    std::size_t i = 0;
    while (i < s.size()) {
        const unsigned char c = static_cast<unsigned char>(s[i]);
        if (c < 0x80) { ++i; continue; }
        std::size_t len = 0;
        std::uint32_t cp = 0;
        if ((c & 0xE0) == 0xC0) { len = 2; cp = c & 0x1Fu; }
        else if ((c & 0xF0) == 0xE0) { len = 3; cp = c & 0x0Fu; }
        else if ((c & 0xF8) == 0xF0) { len = 4; cp = c & 0x07u; }
        else return false;
        if (i + len > s.size()) return false;
        for (std::size_t k = 1; k < len; ++k) {
            const unsigned char cc = static_cast<unsigned char>(s[i + k]);
            if ((cc & 0xC0) != 0x80) return false;
            cp = (cp << 6) | (cc & 0x3Fu);
        }
        if ((len == 2 && cp < 0x80) || (len == 3 && cp < 0x800) || (len == 4 && cp < 0x10000)) return false;  // overlong
        if (cp > 0x10FFFF || (cp >= 0xD800 && cp <= 0xDFFF)) return false;
        i += len;
    }
    return true;
}

// Texto de entrada (ponteiro + comprimento). Nulo só com comprimento 0.
bool Text(const char* s, std::size_t len, std::string_view& out) {
    if (s == nullptr) {
        if (len != 0) return false;
        out = std::string_view();
        return true;
    }
    out = std::string_view(s, len);
    return ValidUtf8(out);
}

shatter_status WriteOut(std::string_view data, std::uint8_t* out, std::size_t cap, std::size_t* needed) {
    if (needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    *needed = data.size();
    if (cap < data.size()) return SHATTER_BUFFER_TOO_SMALL;
    if (!data.empty()) {
        if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
        std::memcpy(out, data.data(), data.size());
    }
    return SHATTER_OK;
}

// Banco utilizável (não nulo e finalizado sem erros).
const ContentDB* UsableDb(const shatter_db* db) { return (db != nullptr && db->ok) ? &db->db : nullptr; }

shatter_status DbError(const shatter_db* db, shatter_error* err) {
    if (db == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "db is null");
    return SetError(err, SHATTER_CONTENT_INVALID, "content database is not finalized or has errors");
}

bool ParseJsonText(const char* s, std::size_t len, Value& out, shatter_error* err, shatter_status& status) {
    std::string_view text;
    if (!Text(s, len, text) || s == nullptr) {
        status = SetError(err, SHATTER_INVALID_ARGUMENT, "json text is null or not valid UTF-8");
        return false;
    }
    json::ParseError pe;
    if (!json::Parse(text, out, &pe)) {
        status = SetError(err, SHATTER_PARSE_ERROR, "json: " + pe.message, pe.line);
        return false;
    }
    return true;
}

// ---------------------------------------------------------------------------------------------
// Regras: RulesConstants <-> shatter_rules
// ---------------------------------------------------------------------------------------------
void ToC(const RulesConstants& r, shatter_rules& o) {
    std::memset(&o, 0, sizeof(o));
    o.crit_multiplier_base = r.critMultiplierBase;
    o.evasion_cap = r.evasionCap;
    o.block_cap = r.blockCap;
    o.block_mitigation = r.blockMitigation;
    o.resist_cap = r.resistCap;
    o.resist_floor = r.resistFloor;
    o.armor_damage_factor = r.armorDamageFactor;
    o.armor_max_reduction = r.armorMaxReduction;
    o.trigger_icd_min = r.triggerInternalCooldown;
    o.cooldown_min = r.minCooldown;
    o.realtime_step = r.fixedStep;
    o.sim_step = r.simStep;
    o.sim_step_fast = r.simStepFastNonBoss;
    o.max_offline_hours = r.maxOfflineHours;
    o.max_expedition_hours = r.maxExpeditionHours;
    o.min_expedition_hours = r.minExpeditionHours;
    o.ai_base_dodge = r.aiBaseDodgeTelegraphed;
    o.retreat_life_fraction = r.retreatLifeFraction;
    o.vigor_h1_4 = r.vigorByBand[0];
    o.vigor_h5_8 = r.vigorByBand[1];
    o.vigor_h9_12 = r.vigorByBand[2];
    o.vigor_band_hours = r.vigorBandHours;
    o.fervor_xp_mult = r.fervorXpMult;
    o.fervor_gold_mat_mult = r.fervorGoldMatMult;
    o.fervor_rare_mult = r.fervorRareChanceMult;
    o.clock_rollback_tolerance_s = r.clockRollbackToleranceSec;
    o.steam_clock_max_skew_s = r.steamClockMaxSkewSec;
    o.xp_base = r.xpBase;
    o.xp_scale = r.xpScale;
    o.xp_exponent = r.xpExponent;
    o.max_ai_rules = r.maxAiRules;
    o.max_rares_per_expedition = r.maxRaresPerExpedition;
    o.xp_cap_levels_above_area = r.xpLevelCapAboveArea;
    o.charges_max = r.chargesMax;
    o.charges_per_hour = r.chargesPerHour;
    o.charges_clear_area = r.chargesClearArea;
    o.charges_boss = r.chargesBoss;
    o.charges_new_area = r.chargesNewArea;
    o.charges_daily_rest = r.chargesDailyRest;
    o.max_level = r.maxLevel;
    o.sim_fast_enabled = r.useFastStepNonBoss ? 1 : 0;
}

RulesConstants FromC(const shatter_rules& o) {
    RulesConstants r;
    r.critMultiplierBase = o.crit_multiplier_base;
    r.evasionCap = o.evasion_cap;
    r.blockCap = o.block_cap;
    r.blockMitigation = o.block_mitigation;
    r.resistCap = o.resist_cap;
    r.resistFloor = o.resist_floor;
    r.armorDamageFactor = o.armor_damage_factor;
    r.armorMaxReduction = o.armor_max_reduction;
    r.triggerInternalCooldown = o.trigger_icd_min;
    r.minCooldown = o.cooldown_min;
    r.fixedStep = o.realtime_step;
    r.simStep = o.sim_step;
    r.simStepFastNonBoss = o.sim_step_fast;
    r.maxOfflineHours = o.max_offline_hours;
    r.maxExpeditionHours = o.max_expedition_hours;
    r.minExpeditionHours = o.min_expedition_hours;
    r.aiBaseDodgeTelegraphed = o.ai_base_dodge;
    r.retreatLifeFraction = o.retreat_life_fraction;
    r.vigorByBand = {o.vigor_h1_4, o.vigor_h5_8, o.vigor_h9_12};
    r.vigorBandHours = o.vigor_band_hours;
    r.fervorXpMult = o.fervor_xp_mult;
    r.fervorGoldMatMult = o.fervor_gold_mat_mult;
    r.fervorRareChanceMult = o.fervor_rare_mult;
    r.clockRollbackToleranceSec = o.clock_rollback_tolerance_s;
    r.steamClockMaxSkewSec = o.steam_clock_max_skew_s;
    r.xpBase = o.xp_base;
    r.xpScale = o.xp_scale;
    r.xpExponent = o.xp_exponent;
    r.maxAiRules = o.max_ai_rules;
    r.maxRaresPerExpedition = o.max_rares_per_expedition;
    r.xpLevelCapAboveArea = o.xp_cap_levels_above_area;
    r.chargesMax = o.charges_max;
    r.chargesPerHour = o.charges_per_hour;
    r.chargesClearArea = o.charges_clear_area;
    r.chargesBoss = o.charges_boss;
    r.chargesNewArea = o.charges_new_area;
    r.chargesDailyRest = o.charges_daily_rest;
    r.maxLevel = o.max_level;
    r.useFastStepNonBoss = o.sim_fast_enabled != 0;
    return r;
}

// ---------------------------------------------------------------------------------------------
// Conteúdo -> JSON (nomes iguais às colunas do CSV, em snake_case)
// ---------------------------------------------------------------------------------------------
constexpr const char* kShapeNames[] = {"melee", "cone", "projectile", "area", "dash", "self", "channel", "trap"};
constexpr const char* kStackRuleNames[] = {"refresh", "stack_n", "strongest_only"};
constexpr const char* kTriggerNames[] = {"none", "on_hit", "on_crit", "on_block", "on_kill", "on_take_damage"};
constexpr const char* kModKindNames[] = {"flat", "increased", "more"};
constexpr const char* kLootKindNames[] = {"item_base", "unique", "stack", "spec_book", "map_stone", "echo_fragment",
                                          "table", "nothing"};

template <std::size_t N>
const char* Name(const char* const (&names)[N], std::size_t i) {
    return i < N ? names[i] : "";
}

Value Ids(const std::vector<ContentId>& ids) {
    Value a = Value::MakeArray();
    for (const ContentId& id : ids) a.Push(Value(id));
    return a;
}

Value Doubles(const double* v, std::size_t n) {
    Value a = Value::MakeArray();
    for (std::size_t i = 0; i < n; ++i) a.Push(Value(v[i]));
    return a;
}

Value Tags(TagMask m) {
    Value a = Value::MakeArray();
    const std::string s = TagListToString(m);
    std::size_t pos = 0;
    while (pos < s.size()) {
        const std::size_t bar = s.find('|', pos);
        a.Push(Value(s.substr(pos, bar == std::string::npos ? std::string::npos : bar - pos)));
        if (bar == std::string::npos) break;
        pos = bar + 1;
    }
    return a;
}

Value Mods(const std::vector<Modifier>& mods) {
    Value a = Value::MakeArray();
    for (const Modifier& m : mods) {
        Value o = Value::MakeObject();
        o.Set("stat", Value(ToString(m.stat)));
        o.Set("kind", Value(Name(kModKindNames, static_cast<std::size_t>(m.kind))));
        o.Set("value", Value(m.value));
        o.Set("required_tags", Tags(m.requiredTags));
        a.Push(std::move(o));
    }
    return a;
}

Value Growths(const std::vector<StatGrowth>& gs) {
    Value a = Value::MakeArray();
    for (const StatGrowth& g : gs) {
        Value o = Value::MakeObject();
        o.Set("stat", Value(ToString(g.stat)));
        o.Set("base", Value(g.base));
        o.Set("per_level", Value(g.perLevel));
        a.Push(std::move(o));
    }
    return a;
}

bool StartsWith(std::string_view s, std::string_view p) { return s.substr(0, p.size()) == p; }

bool LookupJson(const ContentDB& db, std::string_view id, Value& o) {
    o = Value::MakeObject();
    if (StartsWith(id, "class.")) {
        const ClassData* d = db.FindClass(id);
        if (d == nullptr) return false;
        o.Set("type", Value("class"));
        o.Set("id", Value(d->id));
        o.Set("resource_id", Value(d->resourceId));
        o.Set("starting_skill", Value(d->startingSkill));
        o.Set("specializations", Ids(d->specializations));
        o.Set("stats", Growths(d->stats));
        o.Set("resource_on_hit", Value(d->resourceOnHit));
        o.Set("resource_on_block", Value(d->resourceOnBlock));
        o.Set("resource_decay_out_of_combat", Value(d->resourceDecayOutOfCombat));
        o.Set("regen_mult_while_moving", Value(d->regenMultWhileMoving));
        return true;
    }
    if (StartsWith(id, "skill.")) {
        const SkillData* d = db.FindSkill(id);
        if (d == nullptr) return false;
        o.Set("type", Value("skill"));
        o.Set("id", Value(d->id));
        o.Set("class_id", Value(d->classId));
        o.Set("spec_id", Value(d->specId));
        o.Set("tags", Tags(d->tags));
        o.Set("tags_mask", Value(static_cast<std::uint32_t>(d->tags)));
        o.Set("shape", Value(Name(kShapeNames, static_cast<std::size_t>(d->shape))));
        o.Set("scales_with_weapon", Value(d->scalesWithWeapon));
        o.Set("base_damage", Doubles(d->baseDamage.data(), d->baseDamage.size()));
        o.Set("coefficient_by_rank", Doubles(d->coefficientByRank.data(), d->coefficientByRank.size()));
        o.Set("cost", Value(d->cost));
        o.Set("cooldown", Value(d->cooldown));
        o.Set("windup", Value(d->windup));
        o.Set("impact", Value(d->impact));
        o.Set("recovery", Value(d->recovery));
        o.Set("range", Value(d->range));
        o.Set("radius", Value(d->radius));
        o.Set("projectiles", Value(d->projectiles));
        o.Set("on_hit_effects", Ids(d->onHitEffects));
        o.Set("self_effects", Ids(d->selfEffects));
        Value idle = Value::MakeObject();
        idle.Set("supported", Value(d->idle.supported));
        idle.Set("avg_targets_hit", Value(d->idle.avgTargetsHit));
        idle.Set("fraction_of_group_hit", Value(d->idle.fractionOfGroupHit));
        idle.Set("approach_time", Value(d->idle.approachTime));
        idle.Set("uptime", Value(d->idle.uptime));
        idle.Set("dodge_telegraphed_bonus", Value(d->idle.dodgeTelegraphedBonus));
        idle.Set("damage_taken_mult", Value(d->idle.damageTakenMult));
        idle.Set("parity_sample_size", Value(d->idle.paritySampleSize));
        o.Set("idle", std::move(idle));
        o.Set("unlock_level", Value(d->unlockLevel));
        return true;
    }
    if (StartsWith(id, "effect.")) {
        const EffectData* d = db.FindEffect(id);
        if (d == nullptr) return false;
        o.Set("type", Value("effect"));
        o.Set("id", Value(d->id));
        o.Set("duration", Value(d->duration));
        o.Set("tick_interval", Value(d->tickInterval));
        o.Set("stack_rule", Value(Name(kStackRuleNames, static_cast<std::size_t>(d->stackRule))));
        o.Set("max_stacks", Value(d->maxStacks));
        o.Set("damage_per_tick", Doubles(d->damagePerTick.data(), d->damagePerTick.size()));
        o.Set("modifiers", Mods(d->modifiers));
        o.Set("barrier", Value(d->barrier));
        o.Set("trigger", Value(Name(kTriggerNames, static_cast<std::size_t>(d->trigger))));
        o.Set("trigger_chance", Value(d->triggerChance));
        o.Set("internal_cooldown", Value(d->internalCooldown));
        o.Set("tags", Tags(d->tags));
        return true;
    }
    if (StartsWith(id, "enemy.")) {
        const EnemyData* d = db.FindEnemy(id);
        if (d == nullptr) return false;
        o.Set("type", Value("enemy"));
        o.Set("id", Value(d->id));
        o.Set("family_id", Value(d->familyId));
        o.Set("stats", Growths(d->stats));
        Value atks = Value::MakeArray();
        for (const EnemyAttack& a : d->attacks) {
            Value ao = Value::MakeObject();
            ao.Set("skill_id", Value(a.skillId));
            ao.Set("weight", Value(a.weight));
            ao.Set("telegraphed", Value(a.telegraphed));
            atks.Push(std::move(ao));
        }
        o.Set("attacks", std::move(atks));
        o.Set("xp_base", Value(d->xpBase));
        o.Set("xp_per_level", Value(d->xpPerLevel));
        o.Set("loot_table_id", Value(d->lootTableId));
        o.Set("is_boss", Value(d->isBoss));
        o.Set("is_elite", Value(d->isElite));
        o.Set("move_speed", Value(d->moveSpeed));
        o.Set("aggro_range", Value(d->aggroRange));
        return true;
    }
    if (StartsWith(id, "affix.")) {
        const AffixData* d = db.FindAffix(id);
        if (d == nullptr) return false;
        o.Set("type", Value("affix"));
        o.Set("id", Value(d->id));
        o.Set("kind", Value(d->kind == AffixKind::Prefix ? "prefix" : "suffix"));
        o.Set("stat", Value(ToString(d->stat)));
        o.Set("mod_kind", Value(Name(kModKindNames, static_cast<std::size_t>(d->modKind))));
        o.Set("required_tags", Tags(d->requiredTags));
        o.Set("min_value", Value(d->minValue));
        o.Set("max_value", Value(d->maxValue));
        o.Set("min_item_level", Value(d->minItemLevel));
        o.Set("weight", Value(d->weight));
        Value slots = Value::MakeArray();
        for (ItemSlot s : d->allowedSlots) slots.Push(Value(ToString(s)));
        o.Set("allowed_slots", std::move(slots));
        o.Set("group", Value(d->group));
        o.Set("craft_inscription", Value(d->craftInscription));
        return true;
    }
    if (StartsWith(id, "item_base.")) {
        const ItemBaseData* d = db.FindItemBase(id);
        if (d == nullptr) return false;
        o.Set("type", Value("item_base"));
        o.Set("id", Value(d->id));
        o.Set("slot", Value(ToString(d->slot)));
        o.Set("item_level", Value(d->itemLevel));
        o.Set("implicit_mods", Mods(d->implicitMods));
        o.Set("weapon_damage", Doubles(d->weaponDamage.data(), d->weaponDamage.size()));
        o.Set("attack_time", Value(d->attackTime));
        o.Set("weapon_tags", Tags(d->weaponTags));
        o.Set("grammatical_gender", Value(std::string(1, d->grammaticalGender)));
        return true;
    }
    if (StartsWith(id, "unique.")) {
        const UniqueData* d = db.FindUnique(id);
        if (d == nullptr) return false;
        o.Set("type", Value("unique"));
        o.Set("id", Value(d->id));
        o.Set("base_id", Value(d->baseId));
        o.Set("fixed_mods", Mods(d->fixedMods));
        o.Set("rule_effect_id", Value(d->ruleEffectId));
        o.Set("idle_supported", Value(d->idleSupported));
        return true;
    }
    if (StartsWith(id, "loot.")) {
        const LootTableData* d = db.FindLootTable(id);
        if (d == nullptr) return false;
        o.Set("type", Value("loot_table"));
        o.Set("id", Value(d->id));
        o.Set("rolls", Value(d->rolls));
        o.Set("drop_chance", Value(d->dropChance));
        o.Set("rarity_weights", Doubles(d->rarityWeights.data(), d->rarityWeights.size()));
        Value entries = Value::MakeArray();
        for (const LootEntry& e : d->entries) {
            Value eo = Value::MakeObject();
            eo.Set("kind", Value(Name(kLootKindNames, static_cast<std::size_t>(e.kind))));
            eo.Set("ref_id", Value(e.refId));
            eo.Set("weight", Value(e.weight));
            eo.Set("min_amount", Value(e.minAmount));
            eo.Set("max_amount", Value(e.maxAmount));
            eo.Set("min_area_level", Value(e.minAreaLevel));
            eo.Set("max_area_level", Value(e.maxAreaLevel));
            eo.Set("manual_only", Value(e.manualOnly));
            entries.Push(std::move(eo));
        }
        o.Set("entries", std::move(entries));
        return true;
    }
    if (StartsWith(id, "enc.")) {
        const EncounterTemplate* d = db.FindEncounter(id);
        if (d == nullptr) return false;
        o.Set("type", Value("encounter"));
        o.Set("id", Value(d->id));
        Value groups = Value::MakeArray();
        for (const EncounterGroup& g : d->groups) {
            Value go = Value::MakeObject();
            go.Set("enemy_id", Value(g.enemyId));
            go.Set("count_min", Value(g.countMin));
            go.Set("count_max", Value(g.countMax));
            go.Set("elite_chance", Value(g.eliteChance));
            groups.Push(std::move(go));
        }
        o.Set("groups", std::move(groups));
        o.Set("weight", Value(d->weight));
        o.Set("travel_time", Value(d->travelTime));
        o.Set("is_boss", Value(d->isBoss));
        return true;
    }
    if (StartsWith(id, "map.")) {
        const MapData* d = db.FindMap(id);
        if (d == nullptr) return false;
        o.Set("type", Value("map"));
        o.Set("id", Value(d->id));
        o.Set("monster_level", Value(d->monsterLevel));
        o.Set("tier", Value(d->tier));
        o.Set("encounters", Ids(d->encounters));
        o.Set("boss_encounter", Value(d->bossEncounter));
        o.Set("area_loot_table", Value(d->areaLootTable));
        o.Set("idle_allowed", Value(d->idleAllowed));
        return true;
    }
    return false;
}

// ---------------------------------------------------------------------------------------------
// Loot, progresso e resultado de expedição <-> JSON
// ---------------------------------------------------------------------------------------------
Value StacksToJson(const std::vector<StackEntry>& stacks) {
    Value a = Value::MakeArray();
    for (const StackEntry& s : stacks) {
        Value o = Value::MakeObject();
        o.Set("id", Value(s.id));
        o.Set("amount", Value(s.amount));
        a.Push(std::move(o));
    }
    return a;
}

Value LootToJson(const LootDrop& d) {
    Value o = Value::MakeObject();
    Value items = Value::MakeArray();
    for (const ItemInstance& it : d.items) items.Push(ItemToJson(it));
    o.Set("items", std::move(items));
    o.Set("stacks", StacksToJson(d.stacks));
    o.Set("rares_dropped", Value(d.raresDropped));
    return o;
}

bool StacksFromJson(const Value& v, std::vector<StackEntry>& out, std::string* err) {
    out.clear();
    for (const Value& s : v.Items()) {
        if (s.type() != json::Type::Object || s["id"].AsString().empty()) {
            if (err) *err = "stack without id";
            return false;
        }
        out.push_back({s["id"].AsString(), s["amount"].AsInt(0)});
    }
    return true;
}

bool LootFromJson(const Value& v, LootDrop& out, std::string* err) {
    if (v.type() != json::Type::Object) {
        if (err) *err = "loot is not an object";
        return false;
    }
    out = LootDrop();
    for (const Value& iv : v["items"].Items()) {
        ItemInstance it;
        if (!ItemFromJson(iv, it, err)) return false;
        out.items.push_back(std::move(it));
    }
    if (!StacksFromJson(v["stacks"], out.stacks, err)) return false;
    out.raresDropped = static_cast<int>(v["rares_dropped"].AsInt(0));
    return true;
}

Value ReceiptToJson(const EncounterReceipt& rc) {
    Value o = Value::MakeObject();
    o.Set("index", Value(rc.index));
    o.Set("template_id", Value(rc.templateId));
    o.Set("outcome", Value(rc.outcome == EncounterOutcome::Cleared ? "cleared" : "retreated"));
    o.Set("start_time", Value(rc.startTime));
    o.Set("duration", Value(rc.duration));
    o.Set("kills", Value(rc.kills));
    o.Set("elites_killed", Value(rc.elitesKilled));
    o.Set("potions_used", Value(rc.potionsUsed));
    o.Set("heal_failures", Value(rc.healFailures));
    o.Set("damage_taken", Value(rc.damageTaken));
    o.Set("damage_dealt", Value(rc.damageDealt));
    o.Set("xp_raw", Value(rc.xpRaw));
    o.Set("loot", LootToJson(rc.loot));
    o.Set("life_fraction_at_end", Value(rc.lifeFractionAtEnd));
    o.Set("vigor_band", Value(static_cast<int>(rc.vigorBand)));
    return o;
}

bool ReceiptFromJson(const Value& o, EncounterReceipt& rc, std::string* err) {
    if (o.type() != json::Type::Object) {
        if (err) *err = "receipt is not an object";
        return false;
    }
    rc = EncounterReceipt();
    rc.index = static_cast<std::uint32_t>(o["index"].AsInt(0));
    rc.templateId = o["template_id"].AsString();
    const std::string& outcome = o["outcome"].AsString();
    if (outcome == "cleared") rc.outcome = EncounterOutcome::Cleared;
    else if (outcome == "retreated") rc.outcome = EncounterOutcome::Retreated;
    else {
        if (err) *err = "receipt: bad outcome";
        return false;
    }
    rc.startTime = o["start_time"].AsDouble(0.0);
    rc.duration = o["duration"].AsDouble(0.0);
    rc.kills = static_cast<int>(o["kills"].AsInt(0));
    rc.elitesKilled = static_cast<int>(o["elites_killed"].AsInt(0));
    rc.potionsUsed = static_cast<int>(o["potions_used"].AsInt(0));
    rc.healFailures = static_cast<int>(o["heal_failures"].AsInt(0));
    rc.damageTaken = o["damage_taken"].AsDouble(0.0);
    rc.damageDealt = o["damage_dealt"].AsDouble(0.0);
    rc.xpRaw = o["xp_raw"].AsDouble(0.0);
    if (!LootFromJson(o["loot"], rc.loot, err)) return false;
    rc.lifeFractionAtEnd = o["life_fraction_at_end"].AsDouble(1.0);
    const std::int64_t band = o["vigor_band"].AsInt(0);
    rc.vigorBand = static_cast<std::uint8_t>(band < 0 ? 0 : (band > 2 ? 2 : band));
    return true;
}

// O progresso atravessa a fronteira inteiro (doubles com 17 dígitos: ida e volta exata).
Value ProgressToJson(const ExpeditionProgress& p) {
    Value o = Value::MakeObject();
    o.Set("next_encounter", Value(p.nextEncounter));
    o.Set("elapsed", Value(p.elapsed));
    o.Set("life", Value(p.life));
    o.Set("resource", Value(p.resource));
    o.Set("barrier", Value(p.barrier));
    o.Set("potions_left", Value(p.potionsLeft));
    o.Set("rares_dropped", Value(p.raresDropped));
    o.Set("stop", Value(ToString(p.stop)));
    Value receipts = Value::MakeArray();
    for (const EncounterReceipt& rc : p.receipts) receipts.Push(ReceiptToJson(rc));
    o.Set("receipts", std::move(receipts));
    return o;
}

bool ProgressFromJson(const Value& o, ExpeditionProgress& p, std::string* err) {
    if (o.type() != json::Type::Object) {
        if (err) *err = "progress is not an object";
        return false;
    }
    p = ExpeditionProgress();
    const std::int64_t next = o["next_encounter"].AsInt(0);
    if (next < 0 || next > static_cast<std::int64_t>(std::numeric_limits<std::uint32_t>::max())) {
        if (err) *err = "progress: bad next_encounter";
        return false;
    }
    p.nextEncounter = static_cast<std::uint32_t>(next);
    p.elapsed = o["elapsed"].AsDouble(0.0);
    p.life = o["life"].AsDouble(-1.0);
    p.resource = o["resource"].AsDouble(-1.0);
    p.barrier = o["barrier"].AsDouble(0.0);
    p.potionsLeft = o["potions_left"].AsInt(-1);
    p.raresDropped = static_cast<int>(o["rares_dropped"].AsInt(0));
    if (!ParseStopReason(o["stop"].AsString(), p.stop)) {
        if (err) *err = "progress: bad stop";
        return false;
    }
    for (const Value& rv : o["receipts"].Items()) {
        EncounterReceipt rc;
        if (!ReceiptFromJson(rv, rc, err)) return false;
        p.receipts.push_back(std::move(rc));
    }
    return true;
}

Value ResultToJson(const ExpeditionResult& r, std::uint32_t flags) {
    Value o = Value::MakeObject();
    o.Set("stop", Value(ToString(r.stop)));
    o.Set("effective_seconds", Value(r.effectiveSeconds));
    o.Set("encounters_cleared", Value(r.encountersCleared));
    o.Set("kills", Value(r.kills));
    o.Set("potions_used", Value(r.potionsUsed));
    o.Set("heal_failures", Value(r.healFailures));
    o.Set("xp_gained", Value(r.xpGained));
    o.Set("xp_capped", Value(r.xpCapped));
    Value items = Value::MakeArray();
    for (const ItemInstance& it : r.items) items.Push(ItemToJson(it));
    o.Set("items", std::move(items));
    o.Set("stacks", StacksToJson(r.stacks));
    o.Set("rares_dropped", Value(r.raresDropped));
    Value tips = Value::MakeArray();
    for (const std::string& k : r.tipKeys) tips.Push(Value(k));
    o.Set("tip_keys", std::move(tips));
    o.Set("result_hash", json::FromUInt64(r.resultHash));
    o.Set("receipt_count", Value(static_cast<std::int64_t>(r.receipts.size())));
    if ((flags & SHATTER_RESULT_RECEIPTS) != 0) {
        Value receipts = Value::MakeArray();
        for (const EncounterReceipt& rc : r.receipts) receipts.Push(ReceiptToJson(rc));
        o.Set("receipts", std::move(receipts));
    }
    return o;
}

// Parte do resultado que a coleta usa (itens, pilhas, XP e hash).
bool CollectableFromJson(const Value& o, ExpeditionResult& r, std::string* err) {
    if (o.type() != json::Type::Object) {
        if (err) *err = "result is not an object";
        return false;
    }
    r = ExpeditionResult();
    const Value* hash = o.Find("result_hash");
    if (hash == nullptr || hash->type() != json::Type::String) {
        if (err) *err = "result: result_hash must be a decimal string";
        return false;
    }
    r.resultHash = hash->AsUInt64(0);
    if (!ParseStopReason(o["stop"].AsString(), r.stop)) {
        if (err) *err = "result: bad stop";
        return false;
    }
    for (const Value& iv : o["items"].Items()) {
        ItemInstance it;
        if (!ItemFromJson(iv, it, err)) return false;
        r.items.push_back(std::move(it));
    }
    if (!StacksFromJson(o["stacks"], r.stacks, err)) return false;
    r.xpGained = o["xp_gained"].AsDouble(0.0);
    return true;
}

// Pedido de expedição + marca opcional "ended_by_rollback" (posta por shatter_save_expedition_request).
bool RequestFromText(const char* s, std::size_t len, ExpeditionRequest& req, OfflineWindow& w, shatter_error* err,
                     shatter_status& status) {
    Value v;
    if (!ParseJsonText(s, len, v, err, status)) return false;
    std::string msg;
    if (!ExpeditionRequestFromJson(v, req, &msg)) {
        status = SetError(err, SHATTER_PARSE_ERROR, "request: " + msg);
        return false;
    }
    w = OfflineWindow();
    w.effectiveSeconds = req.effectiveSeconds;
    w.endedByRollback = v["ended_by_rollback"].AsBool(false);
    return true;
}

bool ProgressFromText(const char* s, std::size_t len, ExpeditionProgress& p, shatter_error* err,
                      shatter_status& status) {
    if (s == nullptr && len == 0) {
        p = ExpeditionProgress();
        return true;
    }
    Value v;
    if (!ParseJsonText(s, len, v, err, status)) return false;
    std::string msg;
    if (!ProgressFromJson(v, p, &msg)) {
        status = SetError(err, SHATTER_PARSE_ERROR, msg);
        return false;
    }
    return true;
}

// Parâmetros de início de expedição (JSON do cabeçalho de shatter_c.h).
bool StartParamsFromText(const char* s, std::size_t len, ExpeditionStartParams& p, shatter_error* err,
                         shatter_status& status) {
    Value v;
    if (!ParseJsonText(s, len, v, err, status)) return false;
    if (v.type() != json::Type::Object) {
        status = SetError(err, SHATTER_PARSE_ERROR, "start params: not an object");
        return false;
    }
    p = ExpeditionStartParams();
    const std::int64_t ci = v["character_index"].AsInt(0);
    if (ci < 0) {
        status = SetError(err, SHATTER_INVALID_ARGUMENT, "start params: negative character_index");
        return false;
    }
    p.characterIndex = static_cast<std::size_t>(ci);
    p.mapId = v["map_id"].AsString();
    const Value* obj = v.Find("objective");
    if (obj != nullptr && !ParseExpeditionObjective(obj->AsString(), p.objective)) {
        status = SetError(err, SHATTER_PARSE_ERROR, "start params: bad objective");
        return false;
    }
    for (const Value& rv : v["rules"].Items()) {
        AiRule r;
        if (!ParseAiCondition(rv["condition"].AsString(), r.condition) ||
            !ParseAiAction(rv["action"].AsString(), r.action)) {
            status = SetError(err, SHATTER_PARSE_ERROR, "start params: bad rule");
            return false;
        }
        r.param = rv["param"].AsDouble(0.0);
        r.refId = rv["ref_id"].AsString();
        p.rules.push_back(std::move(r));
    }
    const std::int64_t hours = v["duration_hours"].AsInt(0);
    p.durationHours = hours < 0 ? 0 : (hours > 1000 ? 1000 : static_cast<int>(hours));
    p.seed = v["seed"].AsUInt64(0);
    p.startUtc = v["start_utc"].AsInt(0);
    return true;
}

shatter_status WriteJson(const Value& v, bool pretty, std::uint8_t* out, std::size_t cap, std::size_t* needed) {
    return WriteOut(json::Serialize(v, pretty), out, cap, needed);
}

}  // namespace

// =============================================================================================
// Funções exportadas
// =============================================================================================
extern "C" {

SHATTER_API std::uint32_t SHATTER_CALL shatter_api_version(void) SHATTER_NOEXCEPT { return SHATTER_C_API_VERSION; }

SHATTER_API void SHATTER_CALL shatter_core_version(std::uint32_t* major, std::uint32_t* minor) SHATTER_NOEXCEPT {
    if (major != nullptr) *major = kCoreVersionMajor;
    if (minor != nullptr) *minor = kCoreVersionMinor;
}

SHATTER_API const char* SHATTER_CALL shatter_status_name(shatter_status status) SHATTER_NOEXCEPT {
    switch (status) {
        case SHATTER_OK: return "ok";
        case SHATTER_INVALID_ARGUMENT: return "invalid_argument";
        case SHATTER_BUFFER_TOO_SMALL: return "buffer_too_small";
        case SHATTER_PARSE_ERROR: return "parse_error";
        case SHATTER_CONTENT_INVALID: return "content_invalid";
        case SHATTER_IO_ERROR: return "io_error";
        case SHATTER_VERSION_MISMATCH: return "version_mismatch";
        case SHATTER_NOT_FOUND: return "not_found";
        case SHATTER_INTERNAL: return "internal";
        default: return "unknown";
    }
}

SHATTER_API shatter_status SHATTER_CALL shatter_layout_info(std::uint32_t* out, std::size_t cap,
                                                          std::size_t* needed) SHATTER_NOEXCEPT {
    if (needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    *needed = SHATTER_LAYOUT_COUNT;
    if (cap < SHATTER_LAYOUT_COUNT) return SHATTER_BUFFER_TOO_SMALL;
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    std::memcpy(out, kLayout, sizeof(kLayout));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_layout_check(const std::uint32_t* values, std::size_t n,
                                                           shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (values == nullptr && n != 0) return SetError(err, SHATTER_INVALID_ARGUMENT, "values is null");
    if (n != SHATTER_LAYOUT_COUNT)
        return SetError(err, SHATTER_VERSION_MISMATCH,
                        "layout count " + std::to_string(n) + " != " + std::to_string(SHATTER_LAYOUT_COUNT));
    for (std::size_t i = 0; i < n; ++i) {
        if (values[i] != kLayout[i])
            return SetError(err, SHATTER_VERSION_MISMATCH,
                            "layout entry " + std::to_string(i) + ": caller " + std::to_string(values[i]) +
                                " != native " + std::to_string(kLayout[i]),
                            static_cast<int>(i) + 1);
    }
    return SHATTER_OK;
}

// --- Conteúdo -----------------------------------------------------------------------------------
SHATTER_API shatter_status SHATTER_CALL shatter_db_load_directory(const char* path, std::size_t path_len,
                                                                 shatter_db** out,
                                                                 shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (out == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "out is null");
    *out = nullptr;
    std::string_view p;
    if (path == nullptr || !Text(path, path_len, p) || p.empty())
        return SetError(err, SHATTER_INVALID_ARGUMENT, "path is null, empty or not valid UTF-8");
    std::unique_ptr<shatter_db> box(new (std::nothrow) shatter_db());
    if (!box) return SetError(err, SHATTER_INTERNAL, "out of memory");
    box->db.LoadDirectory(std::string(p));
    box->ok = box->db.Finalize();
    box->finalized = true;
    shatter_status st = SHATTER_OK;
    if (!box->ok) {
        const auto& errs = box->db.Errors();
        bool io = false;
        for (const ContentError& e : errs) io = io || StartsWith(e.message, "E_IO");
        const ContentError& first = errs.front();
        st = SetError(err, io ? SHATTER_IO_ERROR : SHATTER_CONTENT_INVALID,
                      first.table + ": " + first.message + " (+" + std::to_string(errs.size() - 1) + " more)",
                      first.line);
    }
    *out = box.release();
    return st;
}

SHATTER_API shatter_status SHATTER_CALL shatter_db_create(shatter_db** out) SHATTER_NOEXCEPT {
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    *out = new (std::nothrow) shatter_db();
    return *out != nullptr ? SHATTER_OK : SHATTER_INTERNAL;
}

SHATTER_API shatter_status SHATTER_CALL shatter_db_load_table(shatter_db* db, const char* table, std::size_t table_len,
                                                             const char* csv, std::size_t csv_len,
                                                             shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (db == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "db is null");
    if (db->finalized) return SetError(err, SHATTER_CONTENT_INVALID, "table loaded after finalize");
    std::string_view name, text;
    if (table == nullptr || !Text(table, table_len, name) || !Text(csv, csv_len, text))
        return SetError(err, SHATTER_INVALID_ARGUMENT, "table name or csv is null or not valid UTF-8");
    const std::size_t before = db->db.Errors().size();
    if (db->db.LoadTableCsv(name, text)) return SHATTER_OK;
    const auto& errs = db->db.Errors();
    if (errs.size() > before) {
        const ContentError& e = errs[before];
        return SetError(err, SHATTER_CONTENT_INVALID, e.table + ": " + e.message, e.line);
    }
    return SetError(err, SHATTER_CONTENT_INVALID, "table rejected");
}

SHATTER_API shatter_status SHATTER_CALL shatter_db_finalize(shatter_db* db, shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (db == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "db is null");
    db->ok = db->db.Finalize();
    db->finalized = true;
    if (db->ok) return SHATTER_OK;
    const ContentError& e = db->db.Errors().front();
    return SetError(err, SHATTER_CONTENT_INVALID, e.table + ": " + e.message, e.line);
}

SHATTER_API void SHATTER_CALL shatter_db_destroy(shatter_db* db) SHATTER_NOEXCEPT { delete db; }

SHATTER_API shatter_status SHATTER_CALL shatter_db_errors_json(const shatter_db* db, std::uint8_t* out,
                                                              std::size_t cap, std::size_t* needed) SHATTER_NOEXCEPT {
    if (db == nullptr) return SHATTER_INVALID_ARGUMENT;
    Value a = Value::MakeArray();
    for (const ContentError& e : db->db.Errors()) {
        Value o = Value::MakeObject();
        o.Set("table", Value(e.table));
        o.Set("line", Value(e.line));
        o.Set("message", Value(e.message));
        a.Push(std::move(o));
    }
    return WriteJson(a, false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_db_content_version(const shatter_db* db,
                                                                  std::uint32_t* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    *out = d->ContentVersion();
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_db_rules(const shatter_db* db, shatter_rules* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    ToC(d->Rules(), *out);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_db_xp_to_next_level(const shatter_db* db, std::int32_t level,
                                                                   double* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    *out = d->XpToNextLevel(level);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_db_lookup_json(const shatter_db* db, const char* id, std::size_t id_len,
                                                              std::uint8_t* out, std::size_t cap,
                                                              std::size_t* needed) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    std::string_view key;
    if (id == nullptr || !Text(id, id_len, key)) return SHATTER_INVALID_ARGUMENT;
    Value o;
    if (!LookupJson(*d, key, o)) return SHATTER_NOT_FOUND;
    return WriteJson(o, false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_db_ids_json(const shatter_db* db, const char* table,
                                                           std::size_t table_len, std::uint8_t* out, std::size_t cap,
                                                           std::size_t* needed) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    std::string_view name;
    if (table == nullptr || !Text(table, table_len, name)) return SHATTER_INVALID_ARGUMENT;
    Value a = Value::MakeArray();
    if (name == "maps") {
        for (const MapData& m : d->Maps()) a.Push(Value(m.id));
    } else if (name == "affixes") {
        for (const AffixData& x : d->Affixes()) a.Push(Value(x.id));
    } else if (name == "item_bases") {
        for (const ItemBaseData& x : d->ItemBases()) a.Push(Value(x.id));
    } else {
        return SHATTER_NOT_FOUND;
    }
    return WriteJson(a, false, out, cap, needed);
}

// --- RNG ----------------------------------------------------------------------------------------
SHATTER_API shatter_status SHATTER_CALL shatter_rng_for_stream(std::uint64_t seed, std::uint32_t stream,
                                                              std::uint64_t index,
                                                              shatter_rng* out) SHATTER_NOEXCEPT {
    if (out == nullptr || stream < SHATTER_RNG_COMBAT || stream > SHATTER_RNG_EVENTS) return SHATTER_INVALID_ARGUMENT;
    const Pcg32 r = Pcg32::ForStream(seed, static_cast<RngStream>(stream), index);
    out->state = r.State();
    out->inc = r.Increment();
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rng_next_u32(shatter_rng* rng, std::uint32_t* out) SHATTER_NOEXCEPT {
    if (rng == nullptr || out == nullptr) return SHATTER_INVALID_ARGUMENT;
    Pcg32 r = Pcg32::FromRaw(rng->state, rng->inc);
    *out = r.NextU32();
    rng->state = r.State();
    rng->inc = r.Increment();
    return SHATTER_OK;
}

// --- StatBlock ----------------------------------------------------------------------------------
SHATTER_API shatter_status SHATTER_CALL shatter_statblock_create(shatter_statblock** out) SHATTER_NOEXCEPT {
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    *out = new (std::nothrow) shatter_statblock();
    return *out != nullptr ? SHATTER_OK : SHATTER_INTERNAL;
}

SHATTER_API void SHATTER_CALL shatter_statblock_destroy(shatter_statblock* sb) SHATTER_NOEXCEPT { delete sb; }

SHATTER_API shatter_status SHATTER_CALL shatter_statblock_from_character_json(const shatter_db* db, const char* json_text,
                                                                            std::size_t len, shatter_statblock** out,
                                                                            shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (out == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "out is null");
    *out = nullptr;
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return DbError(db, err);
    Value v;
    shatter_status st = SHATTER_OK;
    if (!ParseJsonText(json_text, len, v, err, st)) return st;
    CharacterState c;
    std::string msg;
    if (!CharacterFromJson(v, c, &msg)) return SetError(err, SHATTER_PARSE_ERROR, "character: " + msg);
    std::unique_ptr<shatter_statblock> box(new (std::nothrow) shatter_statblock());
    if (!box) return SetError(err, SHATTER_INTERNAL, "out of memory");
    if (!BuildStatBlock(*d, c, box->sb, &msg)) return SetError(err, SHATTER_CONTENT_INVALID, msg);
    *out = box.release();
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_statblock_from_save(const shatter_db* db, const shatter_save* save,
                                                                  std::size_t character_index, shatter_statblock** out,
                                                                  shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (out == nullptr || save == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "out or save is null");
    *out = nullptr;
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return DbError(db, err);
    if (character_index >= save->data.characters.size())
        return SetError(err, SHATTER_INVALID_ARGUMENT, "character index out of range");
    std::unique_ptr<shatter_statblock> box(new (std::nothrow) shatter_statblock());
    if (!box) return SetError(err, SHATTER_INTERNAL, "out of memory");
    std::string msg;
    if (!BuildStatBlock(*d, save->data.characters[character_index], box->sb, &msg))
        return SetError(err, SHATTER_CONTENT_INVALID, msg);
    *out = box.release();
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_statblock_for_enemy(const shatter_db* db, const char* enemy_id,
                                                                  std::size_t enemy_id_len, std::int32_t level,
                                                                  shatter_statblock** out) SHATTER_NOEXCEPT {
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    *out = nullptr;
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    std::string_view id;
    if (enemy_id == nullptr || !Text(enemy_id, enemy_id_len, id)) return SHATTER_INVALID_ARGUMENT;
    const EnemyData* e = d->FindEnemy(id);
    if (e == nullptr) return SHATTER_NOT_FOUND;
    std::unique_ptr<shatter_statblock> box(new (std::nothrow) shatter_statblock());
    if (!box) return SHATTER_INTERNAL;
    BuildEnemyStatBlock(*e, level, box->sb);
    *out = box.release();
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_statblock_set_base(shatter_statblock* sb, std::uint32_t stat,
                                                                 double value) SHATTER_NOEXCEPT {
    if (sb == nullptr || stat >= SHATTER_STAT_COUNT) return SHATTER_INVALID_ARGUMENT;
    sb->sb.SetBase(static_cast<StatId>(stat), value);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_statblock_get_base(const shatter_statblock* sb, std::uint32_t stat,
                                                                 double* out) SHATTER_NOEXCEPT {
    if (sb == nullptr || out == nullptr || stat >= SHATTER_STAT_COUNT) return SHATTER_INVALID_ARGUMENT;
    *out = sb->sb.GetBase(static_cast<StatId>(stat));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_statblock_get(const shatter_statblock* sb, std::uint32_t stat,
                                                            std::uint32_t context_tags, double* out) SHATTER_NOEXCEPT {
    if (sb == nullptr || out == nullptr || stat >= SHATTER_STAT_COUNT) return SHATTER_INVALID_ARGUMENT;
    *out = sb->sb.GetTagged(static_cast<StatId>(stat), context_tags);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_statblock_apply_tagged(const shatter_statblock* sb, std::uint32_t stat,
                                                                     std::uint32_t context_tags, double base,
                                                                     double* out) SHATTER_NOEXCEPT {
    if (sb == nullptr || out == nullptr || stat >= SHATTER_STAT_COUNT) return SHATTER_INVALID_ARGUMENT;
    *out = sb->sb.ApplyTagged(static_cast<StatId>(stat), context_tags, base);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_statblock_add_modifier(shatter_statblock* sb,
                                                                     const shatter_modifier* mod, const char* source,
                                                                     std::size_t source_len) SHATTER_NOEXCEPT {
    std::string_view src;
    if (sb == nullptr || mod == nullptr || mod->stat >= SHATTER_STAT_COUNT || mod->kind > SHATTER_MOD_MORE ||
        !Text(source, source_len, src))
        return SHATTER_INVALID_ARGUMENT;
    Modifier m;
    m.stat = static_cast<StatId>(mod->stat);
    m.kind = static_cast<ModKind>(mod->kind);
    m.value = mod->value;
    m.requiredTags = mod->required_tags;
    m.source = std::string(src);
    sb->sb.AddModifier(m);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_statblock_remove_modifiers_from(shatter_statblock* sb,
                                                                              const char* source,
                                                                              std::size_t source_len,
                                                                              std::uint32_t* removed) SHATTER_NOEXCEPT {
    std::string_view src;
    if (sb == nullptr || !Text(source, source_len, src)) return SHATTER_INVALID_ARGUMENT;
    const std::size_t n = sb->sb.RemoveModifiersFrom(src);
    if (removed != nullptr) *removed = static_cast<std::uint32_t>(n);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_statblock_clear_modifiers(shatter_statblock* sb) SHATTER_NOEXCEPT {
    if (sb == nullptr) return SHATTER_INVALID_ARGUMENT;
    sb->sb.ClearModifiers();
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_statblock_revision(const shatter_statblock* sb,
                                                                 std::uint64_t* out) SHATTER_NOEXCEPT {
    if (sb == nullptr || out == nullptr) return SHATTER_INVALID_ARGUMENT;
    *out = sb->sb.Revision();
    return SHATTER_OK;
}

// --- Golpe ---------------------------------------------------------------------------------------
SHATTER_API shatter_status SHATTER_CALL shatter_resolve_hit(const shatter_statblock* attacker,
                                                          const shatter_statblock* defender,
                                                          const shatter_hit_input* input, const shatter_rules* rules,
                                                          shatter_rng* rng, shatter_hit_result* out) SHATTER_NOEXCEPT {
    if (attacker == nullptr || defender == nullptr || input == nullptr || rules == nullptr || rng == nullptr ||
        out == nullptr)
        return SHATTER_INVALID_ARGUMENT;
    HitInput in;
    in.attacker = &attacker->sb;
    in.defender = &defender->sb;
    in.skillTags = input->skill_tags;
    for (int t = 0; t < kDamageTypeCount; ++t) in.baseDamage[static_cast<std::size_t>(t)] = input->base_damage[t];
    in.coefficient = input->coefficient;
    in.isDamageOverTime = input->is_damage_over_time != 0;
    in.canBeBlocked = input->can_be_blocked != 0;
    in.defenderLife = input->defender_life;
    in.defenderBarrier = input->defender_barrier;
    Pcg32 r = Pcg32::FromRaw(rng->state, rng->inc);
    const HitResult hr = ResolveHit(in, FromC(*rules), r);
    rng->state = r.State();
    rng->inc = r.Increment();
    std::memset(out, 0, sizeof(*out));
    for (int t = 0; t < kDamageTypeCount; ++t) {
        out->after_modifiers[t] = hr.afterModifiers[static_cast<std::size_t>(t)];
        out->after_mitigation[t] = hr.afterMitigation[static_cast<std::size_t>(t)];
    }
    out->total_damage = hr.totalDamage;
    out->absorbed_by_barrier = hr.absorbedByBarrier;
    out->life_lost = hr.lifeLost;
    out->defender_life_after = hr.defenderLifeAfter;
    out->defender_barrier_after = hr.defenderBarrierAfter;
    out->outcome = static_cast<std::uint8_t>(hr.outcome);
    out->critical = hr.critical ? 1 : 0;
    out->landed = hr.landed ? 1 : 0;
    out->killed = hr.killed ? 1 : 0;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_effective_cooldown(double base_cooldown, double cooldown_recovery,
                                                                 const shatter_rules* rules,
                                                                 double* out) SHATTER_NOEXCEPT {
    if (rules == nullptr || out == nullptr) return SHATTER_INVALID_ARGUMENT;
    *out = EffectiveCooldown(base_cooldown, cooldown_recovery, FromC(*rules));
    return SHATTER_OK;
}

// --- Efeitos -------------------------------------------------------------------------------------
SHATTER_API shatter_status SHATTER_CALL shatter_effects_create(shatter_effects** out) SHATTER_NOEXCEPT {
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    *out = new (std::nothrow) shatter_effects();
    return *out != nullptr ? SHATTER_OK : SHATTER_INTERNAL;
}

SHATTER_API void SHATTER_CALL shatter_effects_destroy(shatter_effects* fx) SHATTER_NOEXCEPT { delete fx; }

SHATTER_API shatter_status SHATTER_CALL shatter_effects_apply(shatter_effects* fx, const shatter_db* db,
                                                            const char* effect_id, std::size_t effect_id_len,
                                                            const char* source_entity, std::size_t source_len,
                                                            double magnitude, std::uint32_t triggered_by,
                                                            shatter_statblock* target,
                                                            std::uint8_t* applied) SHATTER_NOEXCEPT {
    std::string_view id, src;
    if (fx == nullptr || target == nullptr || applied == nullptr || effect_id == nullptr ||
        triggered_by > SHATTER_TRIGGER_ON_TAKE_DAMAGE || !Text(effect_id, effect_id_len, id) ||
        !Text(source_entity, source_len, src))
        return SHATTER_INVALID_ARGUMENT;
    *applied = 0;
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    const EffectData* e = d->FindEffect(id);
    if (e == nullptr) return SHATTER_NOT_FOUND;
    *applied = fx->fx.Apply(*e, src, magnitude, static_cast<TriggerKind>(triggered_by), target->sb, d->Rules()) ? 1 : 0;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_effects_tick(shatter_effects* fx, const shatter_db* db, double dt,
                                                           shatter_statblock* target,
                                                           std::size_t* event_count) SHATTER_NOEXCEPT {
    if (fx == nullptr || target == nullptr || event_count == nullptr) return SHATTER_INVALID_ARGUMENT;
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    fx->events.clear();
    fx->fx.Tick(dt, d->EffectLookup(), target->sb, fx->events);
    *event_count = fx->events.size();
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_effects_events(const shatter_effects* fx, shatter_effect_event* out,
                                                             std::size_t cap, std::size_t* needed) SHATTER_NOEXCEPT {
    if (fx == nullptr || needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    *needed = fx->events.size();
    if (cap < fx->events.size()) return SHATTER_BUFFER_TOO_SMALL;
    if (!fx->events.empty() && out == nullptr) return SHATTER_INVALID_ARGUMENT;
    for (std::size_t i = 0; i < fx->events.size(); ++i) {
        const EffectEvent& e = fx->events[i];
        shatter_effect_event& o = out[i];
        std::memset(&o, 0, sizeof(o));
        o.kind = e.kind == EffectEvent::Kind::DamageTick ? SHATTER_EFFECT_EVENT_DAMAGE_TICK : SHATTER_EFFECT_EVENT_EXPIRED;
        for (int t = 0; t < kDamageTypeCount; ++t) o.damage[t] = e.damage[static_cast<std::size_t>(t)];
        o.effect_id_len = static_cast<std::uint32_t>(e.effectId.size());
        const std::size_t n = e.effectId.size() < sizeof(o.effect_id) - 1 ? e.effectId.size() : sizeof(o.effect_id) - 1;
        if (n > 0) std::memcpy(o.effect_id, e.effectId.data(), n);
        o.effect_id[n] = '\0';
    }
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_effects_stack_count(const shatter_effects* fx, const char* effect_id,
                                                                  std::size_t effect_id_len,
                                                                  std::int32_t* out) SHATTER_NOEXCEPT {
    std::string_view id;
    if (fx == nullptr || out == nullptr || effect_id == nullptr || !Text(effect_id, effect_id_len, id))
        return SHATTER_INVALID_ARGUMENT;
    *out = fx->fx.StackCount(id);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_effects_clear(shatter_effects* fx,
                                                            shatter_statblock* target) SHATTER_NOEXCEPT {
    if (fx == nullptr || target == nullptr) return SHATTER_INVALID_ARGUMENT;
    fx->fx.Clear(target->sb);
    fx->events.clear();
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_effects_active_json(const shatter_effects* fx, std::uint8_t* out,
                                                                  std::size_t cap,
                                                                  std::size_t* needed) SHATTER_NOEXCEPT {
    if (fx == nullptr) return SHATTER_INVALID_ARGUMENT;
    Value a = Value::MakeArray();
    for (const ActiveEffect& e : fx->fx.Active()) {
        Value o = Value::MakeObject();
        o.Set("effect_id", Value(e.effectId));
        o.Set("source", Value(e.sourceEntity));
        o.Set("magnitude", Value(e.magnitude));
        o.Set("remaining", Value(e.remaining));
        a.Push(std::move(o));
    }
    return WriteJson(a, false, out, cap, needed);
}

// --- Relógio -------------------------------------------------------------------------------------
SHATTER_API shatter_status SHATTER_CALL shatter_clock_resolve_now(const shatter_clock_input* in,
                                                                const shatter_rules* rules,
                                                                shatter_trusted_now* out) SHATTER_NOEXCEPT {
    if (in == nullptr || rules == nullptr || out == nullptr) return SHATTER_INVALID_ARGUMENT;
    ClockInput ci;
    ci.localNowUtc = in->local_now_utc;
    ci.hasSteamTime = in->has_steam_time != 0;
    ci.steamNowUtc = in->steam_now_utc;
    ci.lastSeenUtc = in->last_seen_utc;
    const TrustedNow t = ResolveNow(ci, FromC(*rules));
    std::memset(out, 0, sizeof(*out));
    out->now = t.now;
    out->used_steam = t.usedSteam ? 1 : 0;
    out->rollback_detected = t.rollbackDetected ? 1 : 0;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_clock_expedition_window(std::int64_t start_utc,
                                                                      std::int32_t duration_hours,
                                                                      const shatter_trusted_now* now,
                                                                      std::int64_t last_seen_utc,
                                                                      const shatter_rules* rules,
                                                                      shatter_offline_window* out) SHATTER_NOEXCEPT {
    if (now == nullptr || rules == nullptr || out == nullptr) return SHATTER_INVALID_ARGUMENT;
    TrustedNow t;
    t.now = now->now;
    t.usedSteam = now->used_steam != 0;
    t.rollbackDetected = now->rollback_detected != 0;
    const OfflineWindow w = ComputeExpeditionWindow(start_utc, duration_hours, t, last_seen_utc, FromC(*rules));
    std::memset(out, 0, sizeof(*out));
    out->effective_seconds = w.effectiveSeconds;
    out->finished = w.finished ? 1 : 0;
    out->ended_by_rollback = w.endedByRollback ? 1 : 0;
    return SHATTER_OK;
}

// --- Loot ---------------------------------------------------------------------------------------
SHATTER_API shatter_status SHATTER_CALL shatter_loot_roll(const shatter_db* db, shatter_save* save,
                                                        const char* table_id, std::size_t table_id_len,
                                                        const shatter_loot_context* ctx, shatter_rng* rng,
                                                        std::uint8_t* out, std::size_t cap, std::size_t* needed,
                                                        shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    std::string_view id;
    if (ctx == nullptr || rng == nullptr || needed == nullptr || table_id == nullptr ||
        !Text(table_id, table_id_len, id) || (ctx->mode != SHATTER_LOOT_MANUAL && ctx->mode != SHATTER_LOOT_IDLE))
        return SetError(err, SHATTER_INVALID_ARGUMENT, "bad loot arguments");
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return DbError(db, err);
    const LootTableData* t = d->FindLootTable(id);
    if (t == nullptr) return SetError(err, SHATTER_NOT_FOUND, "loot table not found: " + std::string(id));
    // Trabalha em cópias do RNG e do contador de uid: só confirma se a saída couber no buffer.
    std::uint64_t uid = save != nullptr ? save->data.nextItemUid : 0;
    LootContext lc;
    lc.mode = static_cast<LootMode>(ctx->mode);
    lc.areaLevel = ctx->area_level;
    lc.quantityMult = ctx->quantity_mult;
    lc.raresAlreadyDropped = ctx->rares_already_dropped;
    lc.maxRares = ctx->max_rares;
    lc.nextItemUid = save != nullptr ? &uid : nullptr;
    Pcg32 r = Pcg32::FromRaw(rng->state, rng->inc);
    const LootDrop drop = RollLootTable(*d, *t, lc, r);
    const shatter_status st = WriteJson(LootToJson(drop), false, out, cap, needed);
    if (st != SHATTER_OK) return SetError(err, st, st == SHATTER_BUFFER_TOO_SMALL ? "buffer too small" : "bad output");
    rng->state = r.State();
    rng->inc = r.Increment();
    if (save != nullptr) save->data.nextItemUid = uid;
    return SHATTER_OK;
}

// --- Save ---------------------------------------------------------------------------------------
SHATTER_API shatter_status SHATTER_CALL shatter_save_create(shatter_save** out) SHATTER_NOEXCEPT {
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    *out = new (std::nothrow) shatter_save();
    return *out != nullptr ? SHATTER_OK : SHATTER_INTERNAL;
}

SHATTER_API void SHATTER_CALL shatter_save_destroy(shatter_save* save) SHATTER_NOEXCEPT { delete save; }

SHATTER_API shatter_status SHATTER_CALL shatter_save_read(const shatter_db* db, const char* base_path, std::size_t len,
                                                        shatter_save** out, shatter_load_report* report,
                                                        shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (out == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "out is null");
    *out = nullptr;
    if (report != nullptr) {
        report->status = static_cast<std::int32_t>(LoadStatus::Missing);
        report->used_backup = 0;
    }
    std::string_view path;
    if (base_path == nullptr || !Text(base_path, len, path) || path.empty())
        return SetError(err, SHATTER_INVALID_ARGUMENT, "path is null, empty or not valid UTF-8");
    if (db != nullptr && UsableDb(db) == nullptr) return DbError(db, err);
    std::unique_ptr<shatter_save> box(new (std::nothrow) shatter_save());
    if (!box) return SetError(err, SHATTER_INTERNAL, "out of memory");
    const std::unique_ptr<IFileIO> io = MakeStdFileIO();
    const LoadReport rep = ReadSaveFile(*io, std::string(path), box->data);
    if (report != nullptr) {
        report->status = static_cast<std::int32_t>(rep.status);
        report->used_backup = rep.usedBackup;
    }
    switch (rep.status) {
        case LoadStatus::Ok: break;
        case LoadStatus::Missing: return SetError(err, SHATTER_NOT_FOUND, "save not found");
        case LoadStatus::TooNew: return SetError(err, SHATTER_VERSION_MISMATCH, rep.error);
        default: return SetError(err, SHATTER_PARSE_ERROR, rep.error);
    }
    if (db != nullptr && !SaveContentVersionSupported(box->data, db->db)) {
        if (report != nullptr) report->status = static_cast<std::int32_t>(LoadStatus::TooNew);
        return SetError(err, SHATTER_VERSION_MISMATCH,
                        "save content_version " + std::to_string(box->data.contentVersion) +
                            " is newer than the game content " + std::to_string(db->db.ContentVersion()));
    }
    *out = box.release();
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_save_write(const shatter_save* save, const char* base_path,
                                                         std::size_t len, shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    std::string_view path;
    if (save == nullptr || base_path == nullptr || !Text(base_path, len, path) || path.empty())
        return SetError(err, SHATTER_INVALID_ARGUMENT, "save or path is null, empty or not valid UTF-8");
    const std::unique_ptr<IFileIO> io = MakeStdFileIO();
    std::string msg;
    if (!WriteSaveFile(*io, std::string(path), save->data, &msg)) return SetError(err, SHATTER_IO_ERROR, msg);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_save_to_json(const shatter_save* save, std::uint8_t pretty,
                                                           std::uint8_t* out, std::size_t cap,
                                                           std::size_t* needed) SHATTER_NOEXCEPT {
    if (save == nullptr) return SHATTER_INVALID_ARGUMENT;
    return WriteOut(SerializeJson(save->data, pretty != 0), out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_save_from_json(const char* json_text, std::size_t len,
                                                             shatter_save** out, std::int32_t* load_status,
                                                             shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (out == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "out is null");
    *out = nullptr;
    std::string_view text;
    if (json_text == nullptr || !Text(json_text, len, text))
        return SetError(err, SHATTER_INVALID_ARGUMENT, "json is null or not valid UTF-8");
    std::unique_ptr<shatter_save> box(new (std::nothrow) shatter_save());
    if (!box) return SetError(err, SHATTER_INTERNAL, "out of memory");
    std::string msg;
    const LoadStatus st = ParseJson(text, box->data, &msg);
    if (load_status != nullptr) *load_status = static_cast<std::int32_t>(st);
    if (st == LoadStatus::TooNew) return SetError(err, SHATTER_VERSION_MISMATCH, msg);
    if (st != LoadStatus::Ok) return SetError(err, SHATTER_PARSE_ERROR, msg);
    *out = box.release();
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_save_summary_get(const shatter_save* save,
                                                               shatter_save_summary* out) SHATTER_NOEXCEPT {
    if (save == nullptr || out == nullptr) return SHATTER_INVALID_ARGUMENT;
    const SaveData& s = save->data;
    std::memset(out, 0, sizeof(*out));
    out->next_item_uid = s.nextItemUid;
    out->last_seen_utc = s.lastSeenUtc;
    out->last_rest_day = s.lastRestDay;
    out->content_version = s.contentVersion;
    out->save_version = s.saveVersion;
    out->character_count = static_cast<std::int32_t>(s.characters.size());
    out->marker_charges = s.markerCharges;
    out->expedition_slots = s.expeditionSlots;
    out->expedition_count = static_cast<std::int32_t>(s.expeditions.size());
    out->running_expedition = -1;
    for (std::size_t i = 0; i < s.expeditions.size(); ++i) {
        if (s.expeditions[i].status == ExpeditionStatus::Running) {
            out->running_expedition = static_cast<std::int32_t>(i);
            break;
        }
    }
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_save_touch_last_seen(shatter_save* save,
                                                                   const shatter_trusted_now* now) SHATTER_NOEXCEPT {
    if (save == nullptr || now == nullptr) return SHATTER_INVALID_ARGUMENT;
    TrustedNow t;
    t.now = now->now;
    save->data.lastSeenUtc = NextLastSeen(save->data.lastSeenUtc, t);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_save_apply_daily_rest(const shatter_db* db, shatter_save* save,
                                                                    const shatter_trusted_now* now,
                                                                    std::int32_t* charges) SHATTER_NOEXCEPT {
    if (save == nullptr || now == nullptr) return SHATTER_INVALID_ARGUMENT;
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    TrustedNow t;
    t.now = now->now;
    t.usedSteam = now->used_steam != 0;
    t.rollbackDetected = now->rollback_detected != 0;
    save->data.markerCharges = ApplyDailyRest(save->data.markerCharges, save->data.lastRestDay, t, d->Rules());
    if (charges != nullptr) *charges = save->data.markerCharges;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_save_character_json(const shatter_save* save, std::size_t index,
                                                                  std::uint8_t* out, std::size_t cap,
                                                                  std::size_t* needed) SHATTER_NOEXCEPT {
    if (save == nullptr || index >= save->data.characters.size()) return SHATTER_INVALID_ARGUMENT;
    return WriteJson(CharacterToJson(save->data.characters[index]), false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_save_record_area_run(const shatter_db* db, shatter_save* save,
                                                                   std::size_t character_index, const char* map_id,
                                                                   std::size_t map_id_len, std::uint8_t reached_end,
                                                                   std::uint8_t boss_defeated,
                                                                   shatter_area_run_reward* out) SHATTER_NOEXCEPT {
    std::string_view id;
    if (save == nullptr || map_id == nullptr || !Text(map_id, map_id_len, id)) return SHATTER_INVALID_ARGUMENT;
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    if (character_index >= save->data.characters.size()) return SHATTER_INVALID_ARGUMENT;
    if (d->FindMap(id) == nullptr) return SHATTER_NOT_FOUND;
    AreaRunOutcome run;
    run.reachedEnd = reached_end != 0;
    run.bossDefeated = boss_defeated != 0;
    AreaRunReward rw;
    if (!RecordAreaRun(*d, save->data, character_index, ContentId(id), run, &rw)) return SHATTER_INTERNAL;
    if (out != nullptr) {
        std::memset(out, 0, sizeof(*out));
        out->charges_gained = rw.chargesGained;
        out->new_conquest = rw.newConquest ? 1 : 0;
    }
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_save_add_loot(shatter_save* save, const char* loot_json,
                                                            std::size_t len, shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (save == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "save is null");
    Value v;
    shatter_status st = SHATTER_OK;
    if (!ParseJsonText(loot_json, len, v, err, st)) return st;
    LootDrop drop;
    std::string msg;
    if (!LootFromJson(v, drop, &msg)) return SetError(err, SHATTER_PARSE_ERROR, "loot: " + msg);
    // Tudo validado: agora altera o save (uid 0 recebe um novo; o contador fica acima do maior uid).
    SaveData& s = save->data;
    for (ItemInstance& it : drop.items) {
        if (it.uid == 0) it.uid = s.nextItemUid++;
        if (it.uid >= s.nextItemUid) s.nextItemUid = it.uid + 1;
        s.stash.push_back(std::move(it));
    }
    for (const StackEntry& e : drop.stacks) {
        bool found = false;
        for (StackEntry& c : s.currencies) {
            if (c.id == e.id) {
                c.amount += e.amount;
                found = true;
                break;
            }
        }
        if (!found) s.currencies.push_back(e);
    }
    return SHATTER_OK;
}

// --- Expedição ------------------------------------------------------------------------------------
SHATTER_API shatter_status SHATTER_CALL shatter_expedition_check(const shatter_db* db, const shatter_save* save,
                                                               const char* params_json, std::size_t len,
                                                               std::int32_t* start_check, std::uint8_t* out,
                                                               std::size_t cap, std::size_t* needed,
                                                               shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (save == nullptr || start_check == nullptr || needed == nullptr)
        return SetError(err, SHATTER_INVALID_ARGUMENT, "save, start_check or needed is null");
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return DbError(db, err);
    ExpeditionStartParams p;
    shatter_status st = SHATTER_OK;
    if (!StartParamsFromText(params_json, len, p, err, st)) return st;
    SaveData copy = save->data;  // só confere: a decisão é a mesma do início, sobre uma cópia
    std::vector<ContentId> blocking;
    const StartCheck check = StartExpedition(*d, copy, p, &blocking);
    st = WriteJson(Ids(blocking), false, out, cap, needed);
    if (st != SHATTER_OK) return SetError(err, st, "buffer too small");
    *start_check = static_cast<std::int32_t>(check);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_save_start_expedition(const shatter_db* db, shatter_save* save,
                                                                    const char* params_json, std::size_t len,
                                                                    std::int32_t* start_check,
                                                                    shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (save == nullptr || start_check == nullptr)
        return SetError(err, SHATTER_INVALID_ARGUMENT, "save or start_check is null");
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return DbError(db, err);
    ExpeditionStartParams p;
    shatter_status st = SHATTER_OK;
    if (!StartParamsFromText(params_json, len, p, err, st)) return st;
    *start_check = static_cast<std::int32_t>(StartExpedition(*d, save->data, p, nullptr));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_save_expedition_request(const shatter_db* db, const shatter_save* save,
                                                                      std::size_t index,
                                                                      const shatter_clock_input* clock,
                                                                      shatter_offline_window* window,
                                                                      std::uint8_t* out, std::size_t cap,
                                                                      std::size_t* needed,
                                                                      shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (save == nullptr || clock == nullptr || needed == nullptr)
        return SetError(err, SHATTER_INVALID_ARGUMENT, "save, clock or needed is null");
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return DbError(db, err);
    if (index >= save->data.expeditions.size()) return SetError(err, SHATTER_INVALID_ARGUMENT, "expedition index out of range");
    const SavedExpedition& e = save->data.expeditions[index];
    if (e.status != ExpeditionStatus::Running) return SetError(err, SHATTER_INVALID_ARGUMENT, "expedition is not running");
    // O last_seen vem do save (o do clock é ignorado aqui): é o último ponto conhecido.
    ClockInput ci;
    ci.localNowUtc = clock->local_now_utc;
    ci.hasSteamTime = clock->has_steam_time != 0;
    ci.steamNowUtc = clock->steam_now_utc;
    ci.lastSeenUtc = save->data.lastSeenUtc;
    const TrustedNow now = ResolveNow(ci, d->Rules());
    const OfflineWindow w =
        ComputeExpeditionWindow(e.request.startUtc, e.request.durationHours, now, save->data.lastSeenUtc, d->Rules());
    ExpeditionRequest req = e.request;
    req.effectiveSeconds = w.effectiveSeconds;
    Value v = ExpeditionRequestToJson(req);
    v.Set("ended_by_rollback", Value(w.endedByRollback));
    const shatter_status st = WriteJson(v, false, out, cap, needed);
    if (st != SHATTER_OK) return SetError(err, st, "buffer too small");
    if (window != nullptr) {
        std::memset(window, 0, sizeof(*window));
        window->effective_seconds = w.effectiveSeconds;
        window->finished = w.finished ? 1 : 0;
        window->ended_by_rollback = w.endedByRollback ? 1 : 0;
    }
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_expedition_simulate(const shatter_db* db, const char* request_json,
                                                                  std::size_t len, std::uint32_t flags,
                                                                  std::uint8_t* out, std::size_t cap,
                                                                  std::size_t* needed,
                                                                  shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (needed == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "needed is null");
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return DbError(db, err);
    ExpeditionRequest req;
    OfflineWindow w;
    shatter_status st = SHATTER_OK;
    if (!RequestFromText(request_json, len, req, w, err, st)) return st;
    ExpeditionProgress p = SimulateRange(*d, req, ExpeditionProgress(), 0, std::numeric_limits<std::uint32_t>::max());
    ApplyWindowStop(p, w);
    st = WriteJson(ResultToJson(FinalizeExpedition(*d, req, p), flags), false, out, cap, needed);
    return st == SHATTER_OK ? st : SetError(err, st, "buffer too small");
}

SHATTER_API shatter_status SHATTER_CALL shatter_expedition_simulate_range(const shatter_db* db,
                                                                        const char* request_json,
                                                                        std::size_t request_len,
                                                                        const char* progress_json,
                                                                        std::size_t progress_len,
                                                                        std::uint32_t first_encounter,
                                                                        std::uint32_t count, std::uint8_t* out,
                                                                        std::size_t cap, std::size_t* needed,
                                                                        shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (needed == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "needed is null");
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return DbError(db, err);
    ExpeditionRequest req;
    OfflineWindow w;
    ExpeditionProgress start;
    shatter_status st = SHATTER_OK;
    if (!RequestFromText(request_json, request_len, req, w, err, st)) return st;
    if (!ProgressFromText(progress_json, progress_len, start, err, st)) return st;
    const ExpeditionProgress p = SimulateRange(*d, req, start, first_encounter, count);
    st = WriteJson(ProgressToJson(p), false, out, cap, needed);
    return st == SHATTER_OK ? st : SetError(err, st, "buffer too small");
}

SHATTER_API shatter_status SHATTER_CALL shatter_expedition_finalize(const shatter_db* db, const char* request_json,
                                                                  std::size_t request_len, const char* progress_json,
                                                                  std::size_t progress_len, std::uint32_t flags,
                                                                  std::uint8_t* out, std::size_t cap,
                                                                  std::size_t* needed,
                                                                  shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (needed == nullptr || progress_json == nullptr)
        return SetError(err, SHATTER_INVALID_ARGUMENT, "needed or progress is null");
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return DbError(db, err);
    ExpeditionRequest req;
    OfflineWindow w;
    ExpeditionProgress p;
    shatter_status st = SHATTER_OK;
    if (!RequestFromText(request_json, request_len, req, w, err, st)) return st;
    if (!ProgressFromText(progress_json, progress_len, p, err, st)) return st;
    ApplyWindowStop(p, w);
    st = WriteJson(ResultToJson(FinalizeExpedition(*d, req, p), flags), false, out, cap, needed);
    return st == SHATTER_OK ? st : SetError(err, st, "buffer too small");
}

SHATTER_API shatter_status SHATTER_CALL shatter_expedition_forecast(const shatter_db* db, const char* request_json,
                                                                  std::size_t len, std::uint64_t base_seed,
                                                                  std::int32_t samples, shatter_forecast* out,
                                                                  shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (out == nullptr || samples < 1 || samples > 100000)
        return SetError(err, SHATTER_INVALID_ARGUMENT, "out is null or samples out of [1, 100000]");
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return DbError(db, err);
    ExpeditionRequest req;
    OfflineWindow w;
    shatter_status st = SHATTER_OK;
    if (!RequestFromText(request_json, len, req, w, err, st)) return st;
    const ExpeditionForecast f = ForecastExpedition(*d, req, base_seed, samples);
    std::memset(out, 0, sizeof(*out));
    out->xp_p10 = f.xpP10;
    out->xp_p50 = f.xpP50;
    out->xp_p90 = f.xpP90;
    out->gold_p10 = f.goldP10;
    out->gold_p50 = f.goldP50;
    out->gold_p90 = f.goldP90;
    out->retreat_probability = f.retreatProbability;
    out->worst_resist_gap = static_cast<std::int32_t>(f.worstResistGap);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_save_collect_expedition(const shatter_db* db, shatter_save* save,
                                                                      std::size_t index, const char* result_json,
                                                                      std::size_t len, std::uint8_t* collected,
                                                                      shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (save == nullptr || collected == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "save or collected is null");
    *collected = 0;
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return DbError(db, err);
    if (index >= save->data.expeditions.size()) return SetError(err, SHATTER_INVALID_ARGUMENT, "expedition index out of range");
    Value v;
    shatter_status st = SHATTER_OK;
    if (!ParseJsonText(result_json, len, v, err, st)) return st;
    ExpeditionResult r;
    std::string msg;
    if (!CollectableFromJson(v, r, &msg)) return SetError(err, SHATTER_PARSE_ERROR, msg);
    *collected = CollectExpedition(*d, save->data, index, r) ? 1 : 0;
    return SHATTER_OK;
}

}  // extern "C"
