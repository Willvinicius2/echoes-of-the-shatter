// ShatterCore — implementação da API C (include/shatter/shatter_c.h; docs/tecnico/04_arquitetura.md, seção 9).
// Fina: valida argumentos, converte structs/JSON e chama o core. Nenhuma regra nova mora aqui.
// Sem exceções, sem estado global; toda função exportada é noexcept (falha de alocação é fatal).
#include "shatter/shatter_c.h"

#include <algorithm>
#include <cmath>
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
    // Dono do banco (docs/17, B8): cada shatter_boss vivo segura uma referência; shatter_db_destroy com chefes vivos só
    // marca o pedido e o banco é liberado quando o último chefe sai (sem uso de memória liberada).
    mutable int bossRefs = 0;  // handles de chefe e destroy são da main thread (contrato do header)
    bool destroyRequested = false;
};
struct shatter_save {
    shatter::SaveData data;
    std::vector<shatter::ItemInstance> ground;  // loot no chão: transitório, NÃO vai para o arquivo (docs/16 4.2)
};
struct shatter_story {
    shatter::StoryDB db;
};
struct shatter_statblock {
    shatter::StatBlock sb;
};
struct shatter_effects {
    shatter::EffectContainer fx;
    std::vector<shatter::EffectEvent> events;  // eventos do último tick
};
struct shatter_potions {
    shatter::PotionBelt belt;
};
struct shatter_actor {
    shatter::ActionStatus st;
    shatter::FleeState flee;
};
struct shatter_boss {
    const shatter_db* owner = nullptr;  // banco que o criou (referência contada)
    shatter::BossFight fight;
    std::vector<shatter::BossEvent> events;  // desde o último step (apply_damage/apply_effect anexam)
    shatter_boss(const shatter::ContentDB& d, const shatter::EnemyData& e, int level, std::uint64_t seed)
        : fight(d, e, level, seed) {}
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
// API C 1.1: layout das structs novas, conversões e auxiliares
// ---------------------------------------------------------------------------------------------
static_assert(sizeof(shatter_rules_ext) == 152, "shatter_rules_ext");
static_assert(sizeof(shatter_vitals) == 40, "shatter_vitals");
static_assert(sizeof(shatter_action_timing) == 40, "shatter_action_timing");
static_assert(sizeof(shatter_potion_outcome) == 56, "shatter_potion_outcome");
static_assert(sizeof(shatter_dodge_state) == 24, "shatter_dodge_state");
static_assert(sizeof(shatter_actor_apply) == 32, "shatter_actor_apply");
static_assert(sizeof(shatter_actor_info) == 32, "shatter_actor_info");
static_assert(sizeof(shatter_elite_info) == 152, "shatter_elite_info");
static_assert(sizeof(shatter_vec2) == 16, "shatter_vec2");
static_assert(sizeof(shatter_boss_context) == 32, "shatter_boss_context");
static_assert(sizeof(shatter_boss_event) == 216, "shatter_boss_event");
static_assert(sizeof(shatter_boss_info) == 80, "shatter_boss_info");
static_assert(sizeof(shatter_boss_damage) == 24, "shatter_boss_damage");
static_assert(sizeof(shatter_boss_progress) == 8, "shatter_boss_progress");
static_assert(sizeof(shatter_forecast_ex) == 72, "shatter_forecast_ex");
static_assert(sizeof(shatter_rules_ext2) == 16, "shatter_rules_ext2");
static_assert(static_cast<int>(BossEvent::Kind::Died) == SHATTER_BOSS_EVT_DIED, "BossEvent::Kind");
static_assert(static_cast<int>(BossState::Dead) == SHATTER_BOSS_DEAD, "BossState");
static_assert(static_cast<int>(PotionUseStatus::LockedOut) == SHATTER_POTION_LOCKED_OUT, "PotionUseStatus");
static_assert(static_cast<int>(DodgeStartStatus::NotEnoughResource) == SHATTER_DODGE_NOT_ENOUGH_RESOURCE, "DodgeStartStatus");
static_assert(static_cast<int>(IdleCalibration::BotParity) == SHATTER_CALIBRATION_BOT_PARITY, "IdleCalibration");

#define SHATTER_LAYOUT_SIZE(T) static_cast<std::uint32_t>(sizeof(T))
#define SHATTER_LAYOUT_OFF(T, f) static_cast<std::uint32_t>(offsetof(T, f))
const std::uint32_t kLayoutExt[] = {
    SHATTER_LAYOUT_SIZE(shatter_rules_ext),
    SHATTER_LAYOUT_OFF(shatter_rules_ext, dodge_recharge), SHATTER_LAYOUT_OFF(shatter_rules_ext, dodge_duration),
    SHATTER_LAYOUT_OFF(shatter_rules_ext, dodge_iframes), SHATTER_LAYOUT_OFF(shatter_rules_ext, dodge_distance),
    SHATTER_LAYOUT_OFF(shatter_rules_ext, dodge_cost_resource), SHATTER_LAYOUT_OFF(shatter_rules_ext, dodge_buffer),
    SHATTER_LAYOUT_OFF(shatter_rules_ext, dodge_perfect_resource),
    SHATTER_LAYOUT_OFF(shatter_rules_ext, dodge_cancel_recovery_fraction),
    SHATTER_LAYOUT_OFF(shatter_rules_ext, guard_break_stagger_seconds),
    SHATTER_LAYOUT_OFF(shatter_rules_ext, guard_break_stagger_damage_taken),
    SHATTER_LAYOUT_OFF(shatter_rules_ext, guard_break_immunity_boss),
    SHATTER_LAYOUT_OFF(shatter_rules_ext, guard_break_immunity_other),
    SHATTER_LAYOUT_OFF(shatter_rules_ext, boss_shield_down_seconds),
    SHATTER_LAYOUT_OFF(shatter_rules_ext, elite_life_mult), SHATTER_LAYOUT_OFF(shatter_rules_ext, elite_damage_mult),
    SHATTER_LAYOUT_OFF(shatter_rules_ext, elite_xp_mult), SHATTER_LAYOUT_OFF(shatter_rules_ext, potion_lockout),
    SHATTER_LAYOUT_OFF(shatter_rules_ext, out_of_combat_seconds),
    SHATTER_LAYOUT_OFF(shatter_rules_ext, dodge_max_charges),
    SHATTER_LAYOUT_SIZE(shatter_vitals),
    SHATTER_LAYOUT_OFF(shatter_vitals, life), SHATTER_LAYOUT_OFF(shatter_vitals, resource),
    SHATTER_LAYOUT_OFF(shatter_vitals, barrier), SHATTER_LAYOUT_OFF(shatter_vitals, barrier_seconds_left),
    SHATTER_LAYOUT_OFF(shatter_vitals, potion_barrier),
    SHATTER_LAYOUT_SIZE(shatter_action_timing),
    SHATTER_LAYOUT_OFF(shatter_action_timing, windup), SHATTER_LAYOUT_OFF(shatter_action_timing, impact),
    SHATTER_LAYOUT_OFF(shatter_action_timing, recovery), SHATTER_LAYOUT_OFF(shatter_action_timing, cooldown),
    SHATTER_LAYOUT_OFF(shatter_action_timing, cost),
    SHATTER_LAYOUT_SIZE(shatter_potion_outcome),
    SHATTER_LAYOUT_OFF(shatter_potion_outcome, heal_amount),
    SHATTER_LAYOUT_OFF(shatter_potion_outcome, barrier_amount),
    SHATTER_LAYOUT_OFF(shatter_potion_outcome, barrier_seconds), SHATTER_LAYOUT_OFF(shatter_potion_outcome, use_time),
    SHATTER_LAYOUT_OFF(shatter_potion_outcome, move_speed_while_using),
    SHATTER_LAYOUT_OFF(shatter_potion_outcome, lockout), SHATTER_LAYOUT_OFF(shatter_potion_outcome, status),
    SHATTER_LAYOUT_SIZE(shatter_dodge_state),
    SHATTER_LAYOUT_OFF(shatter_dodge_state, recharge_remaining), SHATTER_LAYOUT_OFF(shatter_dodge_state, elapsed),
    SHATTER_LAYOUT_OFF(shatter_dodge_state, charges), SHATTER_LAYOUT_OFF(shatter_dodge_state, active),
    SHATTER_LAYOUT_SIZE(shatter_actor_apply),
    SHATTER_LAYOUT_OFF(shatter_actor_apply, stun_seconds), SHATTER_LAYOUT_OFF(shatter_actor_apply, stagger_seconds),
    SHATTER_LAYOUT_OFF(shatter_actor_apply, guard_break_stacks), SHATTER_LAYOUT_OFF(shatter_actor_apply, applied),
    SHATTER_LAYOUT_OFF(shatter_actor_apply, stunned), SHATTER_LAYOUT_OFF(shatter_actor_apply, stun_blocked),
    SHATTER_LAYOUT_OFF(shatter_actor_apply, interrupted), SHATTER_LAYOUT_OFF(shatter_actor_apply, staggered),
    SHATTER_LAYOUT_OFF(shatter_actor_apply, remove_barrier),
    SHATTER_LAYOUT_SIZE(shatter_actor_info),
    SHATTER_LAYOUT_OFF(shatter_actor_info, stun_remaining), SHATTER_LAYOUT_OFF(shatter_actor_info, stagger_remaining),
    SHATTER_LAYOUT_OFF(shatter_actor_info, immunity_remaining), SHATTER_LAYOUT_OFF(shatter_actor_info, can_act),
    SHATTER_LAYOUT_OFF(shatter_actor_info, stun_immune),
    SHATTER_LAYOUT_SIZE(shatter_elite_info),
    SHATTER_LAYOUT_OFF(shatter_elite_info, life_mult), SHATTER_LAYOUT_OFF(shatter_elite_info, damage_mult),
    SHATTER_LAYOUT_OFF(shatter_elite_info, xp_mult), SHATTER_LAYOUT_OFF(shatter_elite_info, barrier_fraction_of_life),
    SHATTER_LAYOUT_OFF(shatter_elite_info, move_speed_mult),
    SHATTER_LAYOUT_OFF(shatter_elite_info, attack_speed_mult), SHATTER_LAYOUT_OFF(shatter_elite_info, recovery_mult),
    SHATTER_LAYOUT_OFF(shatter_elite_info, death_explosion_radius),
    SHATTER_LAYOUT_OFF(shatter_elite_info, death_explosion_damage),
    SHATTER_LAYOUT_OFF(shatter_elite_info, death_explosion_fuse), SHATTER_LAYOUT_OFF(shatter_elite_info, modifier_id),
    SHATTER_LAYOUT_OFF(shatter_elite_info, rolled),
    SHATTER_LAYOUT_SIZE(shatter_vec2),
    SHATTER_LAYOUT_OFF(shatter_vec2, x), SHATTER_LAYOUT_OFF(shatter_vec2, z),
    SHATTER_LAYOUT_SIZE(shatter_boss_context),
    SHATTER_LAYOUT_OFF(shatter_boss_context, boss), SHATTER_LAYOUT_OFF(shatter_boss_context, player),
    SHATTER_LAYOUT_SIZE(shatter_boss_event),
    SHATTER_LAYOUT_OFF(shatter_boss_event, seconds), SHATTER_LAYOUT_OFF(shatter_boss_event, kind),
    SHATTER_LAYOUT_OFF(shatter_boss_event, phase), SHATTER_LAYOUT_OFF(shatter_boss_event, count),
    SHATTER_LAYOUT_OFF(shatter_boss_event, pattern_id), SHATTER_LAYOUT_OFF(shatter_boss_event, skill_id),
    SHATTER_LAYOUT_OFF(shatter_boss_event, enemy_id),
    SHATTER_LAYOUT_SIZE(shatter_boss_info),
    SHATTER_LAYOUT_OFF(shatter_boss_info, life), SHATTER_LAYOUT_OFF(shatter_boss_info, max_life),
    SHATTER_LAYOUT_OFF(shatter_boss_info, shield_down_remaining),
    SHATTER_LAYOUT_OFF(shatter_boss_info, turn_rate_deg_per_sec), SHATTER_LAYOUT_OFF(shatter_boss_info, facing_x),
    SHATTER_LAYOUT_OFF(shatter_boss_info, facing_z), SHATTER_LAYOUT_OFF(shatter_boss_info, stagger_remaining),
    SHATTER_LAYOUT_OFF(shatter_boss_info, stun_remaining), SHATTER_LAYOUT_OFF(shatter_boss_info, phase),
    SHATTER_LAYOUT_OFF(shatter_boss_info, state), SHATTER_LAYOUT_OFF(shatter_boss_info, shield_up),
    SHATTER_LAYOUT_OFF(shatter_boss_info, invulnerable),
    SHATTER_LAYOUT_SIZE(shatter_boss_damage),
    SHATTER_LAYOUT_OFF(shatter_boss_damage, applied), SHATTER_LAYOUT_OFF(shatter_boss_damage, life_after),
    SHATTER_LAYOUT_OFF(shatter_boss_damage, shield_blocked), SHATTER_LAYOUT_OFF(shatter_boss_damage, invulnerable),
    SHATTER_LAYOUT_OFF(shatter_boss_damage, clamped_by_phase), SHATTER_LAYOUT_OFF(shatter_boss_damage, killed),
    SHATTER_LAYOUT_SIZE(shatter_boss_progress),
    SHATTER_LAYOUT_OFF(shatter_boss_progress, kills), SHATTER_LAYOUT_OFF(shatter_boss_progress, kills_since_unique),
    SHATTER_LAYOUT_SIZE(shatter_forecast_ex),
    SHATTER_LAYOUT_OFF(shatter_forecast_ex, base), SHATTER_LAYOUT_OFF(shatter_forecast_ex, calibration),
};
static_assert(sizeof(kLayoutExt) / sizeof(kLayoutExt[0]) == SHATTER_LAYOUT_EXT_COUNT, "SHATTER_LAYOUT_EXT_COUNT desatualizado");
#undef SHATTER_LAYOUT_SIZE
#undef SHATTER_LAYOUT_OFF

const std::uint32_t kLayoutExt2[] = {static_cast<std::uint32_t>(sizeof(shatter_rules_ext2)),
                                    static_cast<std::uint32_t>(offsetof(shatter_rules_ext2, unarmed_weapon_damage_physical)),
                                    static_cast<std::uint32_t>(offsetof(shatter_rules_ext2, require_on_screen_margin))};
static_assert(sizeof(kLayoutExt2) / sizeof(kLayoutExt2[0]) == SHATTER_LAYOUT_EXT2_COUNT, "SHATTER_LAYOUT_EXT2_COUNT desatualizado");

const std::uint32_t kLayoutExt3[] = {
    static_cast<std::uint32_t>(sizeof(shatter_flee_result)), static_cast<std::uint32_t>(offsetof(shatter_flee_result, remaining)),
    static_cast<std::uint32_t>(offsetof(shatter_flee_result, fleeing)), static_cast<std::uint32_t>(offsetof(shatter_flee_result, started)),
    static_cast<std::uint32_t>(offsetof(shatter_flee_result, ended)), static_cast<std::uint32_t>(offsetof(shatter_flee_result, can_flee))};
static_assert(sizeof(kLayoutExt3) / sizeof(kLayoutExt3[0]) == SHATTER_LAYOUT_EXT3_COUNT, "SHATTER_LAYOUT_EXT3_COUNT desatualizado");

#define SHATTER_L5(T, F) static_cast<std::uint32_t>(offsetof(T, F))
const std::uint32_t kLayoutExt5[] = {
    SHATTER_L5(shatter_hit_input, from_guard_arc),
    static_cast<std::uint32_t>(sizeof(shatter_combat_rules)),
    SHATTER_L5(shatter_combat_rules, combo_window), SHATTER_L5(shatter_combat_rules, combo_window_after_dodge),
    SHATTER_L5(shatter_combat_rules, attack_buffer), SHATTER_L5(shatter_combat_rules, heavy_hold_threshold),
    SHATTER_L5(shatter_combat_rules, light_windup_credit_max), SHATTER_L5(shatter_combat_rules, guard_lower_time),
    SHATTER_L5(shatter_combat_rules, dash_shot_range),
    static_cast<std::uint32_t>(sizeof(shatter_basic_kit)),
    SHATTER_L5(shatter_basic_kit, heavy_charge_time), SHATTER_L5(shatter_basic_kit, heavy_max_mult),
    SHATTER_L5(shatter_basic_kit, guard_arc), SHATTER_L5(shatter_basic_kit, guard_max_hold),
    SHATTER_L5(shatter_basic_kit, guard_cooldown), SHATTER_L5(shatter_basic_kit, guard_perfect_window),
    SHATTER_L5(shatter_basic_kit, guard_perfect_cooldown), SHATTER_L5(shatter_basic_kit, guard_perfect_resource),
    SHATTER_L5(shatter_basic_kit, guard_drain_per_damage), SHATTER_L5(shatter_basic_kit, light_chain_count),
    SHATTER_L5(shatter_basic_kit, guard_perfect_effect_count), SHATTER_L5(shatter_basic_kit, light_chain),
    SHATTER_L5(shatter_basic_kit, heavy_skill), SHATTER_L5(shatter_basic_kit, charge_effect),
    SHATTER_L5(shatter_basic_kit, guard_effect), SHATTER_L5(shatter_basic_kit, guard_perfect_effects)};
#undef SHATTER_L5
static_assert(sizeof(kLayoutExt5) / sizeof(kLayoutExt5[0]) == SHATTER_LAYOUT_EXT5_COUNT, "SHATTER_LAYOUT_EXT5_COUNT desatualizado");

// Copia texto para um campo char[N] (NUL no fim, cortado em fronteira de caractere UTF-8).
template <std::size_t N>
void CopyText(char (&dst)[N], const std::string& s) {
    std::size_t n = s.size() < N - 1 ? s.size() : N - 1;
    while (n > 0 && n < s.size() && (static_cast<unsigned char>(s[n]) & 0xC0u) == 0x80u) --n;
    if (n > 0) std::memcpy(dst, s.data(), n);
    dst[n] = '\0';
}

bool FindClassArg(const ContentDB& d, const char* id, std::size_t len, const ClassData*& cls) {
    std::string_view s;
    if (!Text(id, len, s)) return false;
    cls = s.empty() ? nullptr : d.FindClass(s);
    return s.empty() || cls != nullptr;
}

void VitalsToC(const Vitals& v, shatter_vitals& o) {
    o.life = v.life;
    o.resource = v.resource;
    o.barrier = v.barrier;
    o.barrier_seconds_left = v.barrierSecondsLeft;
    o.potion_barrier = v.potionBarrier;
}
Vitals VitalsFromC(const shatter_vitals& c) {
    Vitals v;
    v.life = c.life;
    v.resource = c.resource;
    v.barrier = c.barrier;
    v.barrierSecondsLeft = c.barrier_seconds_left;
    v.potionBarrier = c.potion_barrier;
    return v;
}

// Aplica o resultado de uma poção em `vitals` e preenche a saída C (cura já limitada à vida máxima).
void ApplyPotionToVitals(const PotionOutcome& po, double maxLife, shatter_vitals& vitals, shatter_potion_outcome& out) {
    out.status = SHATTER_POTION_OK;
    out.use_time = po.useTime;
    out.move_speed_while_using = po.moveSpeedWhileUsing;
    // A regra (teto da cura, renovação da barreira só na parte da poção) é do core e a mesma do simulador idle.
    Vitals v = VitalsFromC(vitals);
    out.heal_amount = ApplyPotionOutcome(v, po, maxLife);
    VitalsToC(v, vitals);
    if (po.barrierAmount > 0.0) {
        out.barrier_amount = po.barrierAmount;
        out.barrier_seconds = po.barrierSeconds;
    }
}

void DodgeToC(const DodgeState& s, shatter_dodge_state& o) {
    std::memset(&o, 0, sizeof(o));
    o.charges = s.charges;
    o.recharge_remaining = s.rechargeRemaining;
    o.elapsed = s.elapsed;
    o.active = s.active ? 1 : 0;
}
DodgeState DodgeFromC(const shatter_dodge_state& c) {
    DodgeState s;
    s.charges = c.charges;
    s.rechargeRemaining = c.recharge_remaining;
    s.elapsed = c.elapsed;
    s.active = c.active != 0;
    return s;
}

void ApplyToC(const StatusApply& r, shatter_actor_apply& o) {
    std::memset(&o, 0, sizeof(o));
    o.stun_seconds = r.stunSeconds;
    o.stagger_seconds = r.staggerSeconds;
    o.guard_break_stacks = r.guardBreakStacks;
    o.applied = r.applied ? 1 : 0;
    o.stunned = r.stunned ? 1 : 0;
    o.stun_blocked = r.stunBlocked ? 1 : 0;
    o.interrupted = r.interrupted ? 1 : 0;
    o.staggered = r.staggered ? 1 : 0;
    o.remove_barrier = r.removeBarrier ? 1 : 0;
}

void EliteToC(const EliteProfile& p, shatter_elite_info& o) {
    std::memset(&o, 0, sizeof(o));
    o.life_mult = p.lifeMult;
    o.damage_mult = p.damageMult;
    o.xp_mult = p.xpMult;
    o.barrier_fraction_of_life = p.barrierFractionOfLife;
    o.move_speed_mult = p.moveSpeedMult;
    o.attack_speed_mult = p.attackSpeedMult;
    o.recovery_mult = p.recoveryMult;
    o.death_explosion_radius = p.deathExplosionRadius;
    o.death_explosion_damage = p.deathExplosionDamage;
    o.death_explosion_fuse = p.deathExplosionFuse;
    CopyText(o.modifier_id, p.modifierId);
    o.rolled = p.rolled ? 1 : 0;
}
void BossEventToC(const BossEvent& e, shatter_boss_event& o) {
    std::memset(&o, 0, sizeof(o));
    o.seconds = e.seconds;
    o.kind = static_cast<std::uint32_t>(e.kind);
    o.phase = e.phase;
    o.count = e.count;
    CopyText(o.pattern_id, e.patternId);
    CopyText(o.skill_id, e.skillId);
    CopyText(o.enemy_id, e.enemyId);
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
        idle.Set("calibration", Value(ToString(d->idle.calibration)));
        o.Set("idle", std::move(idle));
        o.Set("unlock_level", Value(d->unlockLevel));
        o.Set("cone_angle", Value(d->coneAngle));
        o.Set("knockback", Value(d->knockback));
        o.Set("wall_stagger_seconds", Value(d->wallStaggerSeconds));
        o.Set("projectile_speed", Value(d->projectileSpeed));
        o.Set("pierce", Value(d->pierce));
        o.Set("explosion_radius", Value(d->explosionRadius));
        const SkillBehavior b = ClassifySkill(*d);
        Value bv = Value::MakeObject();
        bv.Set("explodes", Value(b.explodes));
        bv.Set("fan", Value(b.fan));
        bv.Set("self_centered", Value(b.selfCentered));
        bv.Set("ground_targeted", Value(b.groundTargeted));
        bv.Set("dash_back_shot", Value(b.dashBackShot));
        o.Set("behavior", std::move(bv));
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
        o.Set("interrupts_action", Value(d->interruptsAction));
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
        o.Set("stun_immune", Value(d->stunImmune));
        o.Set("shield_arc_degrees", Value(d->shieldArcDegrees));
        o.Set("turn_rate_deg_per_sec", Value(d->turnRateDegPerSec));
        o.Set("turn_rate_deg_per_sec_phase2", Value(d->turnRateDegPerSecPhase2));
        o.Set("guard_break_stagger_seconds", Value(d->guardBreakStaggerSeconds));
        o.Set("guard_break_immunity_seconds", Value(d->guardBreakImmunitySeconds));
        o.Set("modifier_id", Value(d->modifierId));
        o.Set("elite_loot_table_id", Value(d->eliteLootTableId));
        o.Set("patrol_speed_mult", Value(d->patrolSpeedMult));
        if (const EnemyAiData* ai = db.FindEnemyAi(d->id)) {
            Value a = Value::MakeObject();
            a.Set("aggro_range", Value(ai->aggroRange));
            a.Set("alert_radius", Value(ai->alertRadius));
            a.Set("leash_range", Value(ai->leashRange));
            a.Set("leash_seconds", Value(ai->leashSeconds));
            a.Set("preferred_min", Value(ai->preferredMin));
            a.Set("preferred_max", Value(ai->preferredMax));
            a.Set("retreat_below", Value(ai->retreatBelow));
            a.Set("retreat_max_seconds", Value(ai->retreatMaxSeconds));
            a.Set("circle_min", Value(ai->circleMin));
            a.Set("circle_max", Value(ai->circleMax));
            a.Set("circle_speed", Value(ai->circleSpeed));
            a.Set("attack_tokens", Value(ai->attackTokens));
            a.Set("token_interval_min", Value(ai->tokenIntervalMin));
            a.Set("token_interval_max", Value(ai->tokenIntervalMax));
            a.Set("flee_life_fraction", Value(ai->fleeLifeFraction));
            a.Set("flee_seconds", Value(ai->fleeSeconds));
            a.Set("flee_once_per_life", Value(ai->fleeOncePerLife));
            a.Set("attack_cooldown", Value(ai->attackCooldown));
            a.Set("max_simultaneous_shooters", Value(ai->maxSimultaneousShooters));
            a.Set("require_on_screen", Value(ai->requireOnScreen));
            o.Set("ai", std::move(a));
        }
        Value phases = Value::MakeArray();
        for (const BossPhaseData& ph : db.BossPhases()) {
            if (ph.bossId != d->id) continue;
            Value po = Value::MakeObject();
            po.Set("phase", Value(ph.phase));
            po.Set("life_threshold", Value(ph.lifeThreshold));
            po.Set("transition_seconds", Value(ph.transitionSeconds));
            po.Set("summon_enemy_id", Value(ph.summonEnemyId));
            po.Set("summon_count", Value(ph.summonCount));
            po.Set("shield_seconds", Value(ph.shieldSeconds));
            po.Set("summon_at_fraction", Value(ph.summonAtFraction));
            po.Set("turn_rate", Value(ph.turnRate));
            po.Set("decision_delay_min", Value(ph.decisionDelayMin));
            po.Set("decision_delay_max", Value(ph.decisionDelayMax));
            phases.Push(std::move(po));
        }
        o.Set("phases", std::move(phases));
        Value patterns = Value::MakeArray();
        for (const BossPatternData& pt : db.BossPatterns()) {
            if (pt.bossId != d->id) continue;
            Value po = Value::MakeObject();
            po.Set("id", Value(pt.id));
            po.Set("phase", Value(pt.phase));
            po.Set("skill_id", Value(pt.skillId));
            po.Set("weight", Value(pt.weight));
            po.Set("telegraph_seconds", Value(pt.telegraphSeconds));
            po.Set("recovery_seconds", Value(pt.recoverySeconds));
            po.Set("cooldown", Value(pt.cooldown));
            po.Set("max_repeat", Value(pt.maxRepeat));
            po.Set("player_near_weight_mult", Value(pt.playerNearWeightMult));
            po.Set("ignore_if_behind", Value(pt.ignoreIfBehind));
            patterns.Push(std::move(po));
        }
        o.Set("patterns", std::move(patterns));
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
        o.Set("visual_set_id", Value(d->visualSetId));
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
        o.Set("idle_parity_sample_size", Value(d->idleParitySampleSize));
        o.Set("idle_calibration", Value(ToString(d->idleCalibration)));
        o.Set("visual_set_id", Value(d->visualSetId));
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
            eo.Set("fixed_chance", Value(e.fixedChance));
            eo.Set("guarantee_first_kill", Value(e.guaranteeFirstKill));
            eo.Set("pity_kills", Value(e.pityKills));
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
    if (StartsWith(id, "potion.")) {
        const PotionData* d = db.FindPotion(id);
        if (d == nullptr) return false;
        o.Set("type", Value("potion"));
        o.Set("id", Value(d->id));
        o.Set("kind", Value(d->kind == PotionKind::Heal ? "heal" : "barrier"));
        o.Set("fraction_of_max_life", Value(d->fractionOfMaxLife));
        o.Set("duration", Value(d->duration));
        o.Set("max_charges", Value(d->maxCharges));
        o.Set("recharge_seconds", Value(d->rechargeSeconds));
        o.Set("use_time", Value(d->useTime));
        o.Set("move_speed_while_using", Value(d->moveSpeedWhileUsing));
        o.Set("global_lockout", Value(d->globalLockout > 0.0 ? d->globalLockout : db.Rules().potionLockout));
        o.Set("refill_on_elite_kill", Value(d->refillOnEliteKill));
        o.Set("hotkey_slot", Value(d->hotkeySlot));
        return true;
    }
    if (StartsWith(id, "modifier.elite.")) {
        const EliteModifierData* d = db.FindEliteModifier(id);
        if (d == nullptr) return false;
        o.Set("type", Value("elite_modifier"));
        o.Set("id", Value(d->id));
        o.Set("weight_prototype", Value(d->weightPrototype));
        o.Set("life_mult", Value(d->lifeMult));
        o.Set("damage_mult", Value(d->damageMult));
        o.Set("xp_mult", Value(d->xpMult));
        o.Set("barrier_fraction_of_life", Value(d->barrierFractionOfLife));
        o.Set("move_speed_mult", Value(d->moveSpeedMult));
        o.Set("attack_speed_mult", Value(d->attackSpeedMult));
        o.Set("recovery_mult", Value(d->recoveryMult));
        o.Set("death_explosion_radius", Value(d->deathExplosionRadius));
        o.Set("death_explosion_damage", Value(d->deathExplosionDamage));
        o.Set("death_explosion_fuse", Value(d->deathExplosionFuse));
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
    o.Set("dodges_used", Value(rc.dodgesUsed));
    if (rc.devouredUses != 0) o.Set("devoured_uses", Value(rc.devouredUses));
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
    rc.dodgesUsed = static_cast<int>(o["dodges_used"].AsInt(0));
    rc.devouredUses = static_cast<int>(std::clamp<std::int64_t>(o["devoured_uses"].AsInt(0), 0, 1000000));
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
    Value slots = Value::MakeArray();
    for (const PotionSlotState& s : p.potionSlots) {
        Value so = Value::MakeObject();
        so.Set("potion_id", Value(s.potionId));
        so.Set("charges", Value(s.charges));
        so.Set("recharge_remaining", Value(s.rechargeRemaining));
        slots.Push(std::move(so));
    }
    o.Set("potion_slots", std::move(slots));
    o.Set("dodge_charges", Value(p.dodgeCharges));
    o.Set("dodge_recharge", Value(p.dodgeRecharge));
    o.Set("ward_amount", Value(p.wardAmount));
    o.Set("ward_remaining", Value(p.wardRemaining));
    o.Set("rares_dropped", Value(p.raresDropped));
    if (p.devouredUsesSpent != 0) o.Set("devoured_uses_spent", Value(p.devouredUsesSpent));
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
    for (const Value& s : o["potion_slots"].Items()) {
        PotionSlotState ps;
        ps.potionId = s["potion_id"].AsString();
        ps.charges = static_cast<int>(s["charges"].AsInt(0));
        ps.rechargeRemaining = s["recharge_remaining"].AsDouble(0.0);
        p.potionSlots.push_back(std::move(ps));
    }
    p.dodgeCharges = static_cast<int>(o["dodge_charges"].AsInt(-1));
    p.dodgeRecharge = o["dodge_recharge"].AsDouble(0.0);
    p.wardAmount = o["ward_amount"].AsDouble(0.0);
    p.wardRemaining = o["ward_remaining"].AsDouble(0.0);
    p.raresDropped = static_cast<int>(o["rares_dropped"].AsInt(0));
    p.devouredUsesSpent = static_cast<int>(std::clamp<std::int64_t>(o["devoured_uses_spent"].AsInt(0), 0, 1000000));
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
    o.Set("calibration", Value(ToString(r.calibration)));  // "manual_estimate": mostrar o selo "estimativa"
    o.Set("result_hash", json::FromUInt64(r.resultHash));
    o.Set("receipt_count", Value(static_cast<std::int64_t>(r.receipts.size())));
    if ((flags & SHATTER_RESULT_RECEIPTS) != 0) {
        Value receipts = Value::MakeArray();
        for (const EncounterReceipt& rc : r.receipts) receipts.Push(ReceiptToJson(rc));
        o.Set("receipts", std::move(receipts));
    }
    return o;
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
    p.storyStatBonusPct = static_cast<int>(std::clamp<std::int64_t>(v["story_stat_bonus_pct"].AsInt(0), 0, 100));
    p.storyPotionEffectPct = static_cast<int>(std::clamp<std::int64_t>(v["story_potion_effect_pct"].AsInt(0), 0, 100));
    p.storyEliteBonusPct = static_cast<int>(std::clamp<std::int64_t>(v["story_elite_bonus_pct"].AsInt(0), 0, 100));
    std::string msg;
    if (!ReadStoryIdleFields(v, p.storyDevouredSkills, p.storyDevouredUses, p.storyStainLootTable, &msg)) {
        status = SetError(err, SHATTER_PARSE_ERROR, "start params: " + msg);
        return false;
    }
    return true;
}

shatter_status WriteJson(const Value& v, bool pretty, std::uint8_t* out, std::size_t cap, std::size_t* needed) {
    return WriteOut(json::Serialize(v, pretty), out, cap, needed);
}

}  // namespace

// =============================================================================================
// Funções exportadas
// =============================================================================================
namespace {

Value VerdictJson(const StoryVerdict& v) {
    Value o = Value::MakeObject();
    o.Set("verdict_id", Value(v.id));
    o.Set("choice", Value(v.choice == VerdictChoice::Devour ? "devour" : "exorcise"));
    o.Set("hunger_delta", Value(static_cast<std::int64_t>(v.hungerDelta)));
    o.Set("stat_bonus_pct", Value(static_cast<std::int64_t>(v.statBonusPct)));
    o.Set("grants_relic", Value(v.grantsRelic));
    o.Set("grants_signature", Value(v.grantsSignature));
    o.Set("region_state", Value(v.regionState));
    o.Set("hub_state", Value(v.hubState));
    o.Set("last_words_key", Value(v.lastWordsKey));
    return o;
}

}  // namespace

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

SHATTER_API void SHATTER_CALL shatter_db_destroy(shatter_db* db) SHATTER_NOEXCEPT {
    if (db == nullptr) return;
    if (db->bossRefs > 0) {
        db->destroyRequested = true;  // há chefes vivos: o último a sair libera
        return;
    }
    delete db;
}

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
namespace {
shatter_status ResolveHitImpl(const shatter_statblock* attacker, const shatter_statblock* defender,
                              const shatter_hit_input* input, const shatter_rules* rules, shatter_rng* rng,
                              shatter_hit_result* out, double hitMore) {
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
    in.fromGuardArc = input->from_guard_arc != 0;
    in.hitMore = hitMore;
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
}  // namespace

SHATTER_API shatter_status SHATTER_CALL shatter_resolve_hit(const shatter_statblock* attacker,
                                                          const shatter_statblock* defender,
                                                          const shatter_hit_input* input, const shatter_rules* rules,
                                                          shatter_rng* rng, shatter_hit_result* out) SHATTER_NOEXCEPT {
    return ResolveHitImpl(attacker, defender, input, rules, rng, out, 1.0);
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
    if (db != nullptr && db->ok) NormalizeSavePotions(db->db, box->data);  // save v1 migrado: completa os slots de poção
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
    (void)d;
    (void)params_json;
    (void)len;
    *start_check = 0;
    // Retirada na API 1.1 (docs/11, M-03): start_utc e seed vinham do chamador.
    return SetError(err, SHATTER_INVALID_ARGUMENT,
                    "removed in API 1.1: use shatter_save_start_expedition_trusted (start_utc and seed come from the core)");
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
    (void)d;
    (void)index;
    (void)result_json;
    (void)len;
    // Retirada na API 1.1 (docs/11, A-05): o resultado vinha do chamador.
    return SetError(err, SHATTER_INVALID_ARGUMENT,
                    "removed in API 1.1: use shatter_save_collect_expedition_trusted (the core recomputes the result)");
}

// =============================================================================================
// API C 1.1 (shatter_c.h, "API C 1.1") — regras novas do protótipo e correções de confiança
// =============================================================================================
SHATTER_API std::uint32_t SHATTER_CALL shatter_api_minor(void) SHATTER_NOEXCEPT { return SHATTER_C_API_MINOR; }

SHATTER_API shatter_status SHATTER_CALL shatter_layout_info_ext(std::uint32_t* out, std::size_t cap,
                                                              std::size_t* needed) SHATTER_NOEXCEPT {
    if (needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    *needed = SHATTER_LAYOUT_EXT_COUNT;
    if (cap < SHATTER_LAYOUT_EXT_COUNT) return SHATTER_BUFFER_TOO_SMALL;
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    std::memcpy(out, kLayoutExt, sizeof(kLayoutExt));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_layout_check_ext(const std::uint32_t* values, std::size_t n,
                                                               shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (values == nullptr && n != 0) return SetError(err, SHATTER_INVALID_ARGUMENT, "values is null");
    if (n != SHATTER_LAYOUT_EXT_COUNT)
        return SetError(err, SHATTER_VERSION_MISMATCH,
                        "ext layout count " + std::to_string(n) + " != " + std::to_string(SHATTER_LAYOUT_EXT_COUNT));
    for (std::size_t i = 0; i < n; ++i) {
        if (values[i] != kLayoutExt[i])
            return SetError(err, SHATTER_VERSION_MISMATCH,
                            "ext layout entry " + std::to_string(i) + ": caller " + std::to_string(values[i]) +
                                " != native " + std::to_string(kLayoutExt[i]),
                            static_cast<int>(i) + 1);
    }
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_db_rules_ext(const shatter_db* db, shatter_rules_ext* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    const RulesConstants& r = d->Rules();
    std::memset(out, 0, sizeof(*out));
    out->dodge_recharge = r.dodgeRecharge;
    out->dodge_duration = r.dodgeDuration;
    out->dodge_iframes = r.dodgeIframes;
    out->dodge_distance = r.dodgeDistance;
    out->dodge_cost_resource = r.dodgeCostResource;
    out->dodge_buffer = r.dodgeBuffer;
    out->dodge_perfect_resource = r.dodgePerfectResource;
    out->dodge_cancel_recovery_fraction = r.dodgeCancelRecoveryFraction;
    out->guard_break_stagger_seconds = r.guardBreakStaggerSeconds;
    out->guard_break_stagger_damage_taken = r.guardBreakStaggerDamageTaken;
    out->guard_break_immunity_boss = r.guardBreakImmunityBoss;
    out->guard_break_immunity_other = r.guardBreakImmunityOther;
    out->boss_shield_down_seconds = r.bossShieldDownSeconds;
    out->elite_life_mult = r.eliteLifeMult;
    out->elite_damage_mult = r.eliteDamageMult;
    out->elite_xp_mult = r.eliteXpMult;
    out->potion_lockout = r.potionLockout;
    out->out_of_combat_seconds = r.outOfCombatSeconds;
    out->dodge_max_charges = r.dodgeMaxCharges;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_layout_info_ext2(std::uint32_t* out, std::size_t cap,
                                                               std::size_t* needed) SHATTER_NOEXCEPT {
    if (needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    *needed = SHATTER_LAYOUT_EXT2_COUNT;
    if (cap < SHATTER_LAYOUT_EXT2_COUNT) return SHATTER_BUFFER_TOO_SMALL;
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    std::memcpy(out, kLayoutExt2, sizeof(kLayoutExt2));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_layout_check_ext2(const std::uint32_t* values, std::size_t n,
                                                                shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (values == nullptr && n != 0) return SetError(err, SHATTER_INVALID_ARGUMENT, "values is null");
    if (n != SHATTER_LAYOUT_EXT2_COUNT) return SetError(err, SHATTER_VERSION_MISMATCH, "ext2 layout count differs");
    for (std::size_t i = 0; i < n; ++i) {
        if (values[i] != kLayoutExt2[i])
            return SetError(err, SHATTER_VERSION_MISMATCH, "ext2 layout entry " + std::to_string(i) + " differs",
                            static_cast<int>(i) + 1);
    }
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_layout_info_ext3(std::uint32_t* out, std::size_t cap,
                                                               std::size_t* needed) SHATTER_NOEXCEPT {
    if (needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    *needed = SHATTER_LAYOUT_EXT3_COUNT;
    if (cap < SHATTER_LAYOUT_EXT3_COUNT) return SHATTER_BUFFER_TOO_SMALL;
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    std::memcpy(out, kLayoutExt3, sizeof(kLayoutExt3));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_layout_check_ext3(const std::uint32_t* values, std::size_t n,
                                                                shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (values == nullptr && n != 0) return SetError(err, SHATTER_INVALID_ARGUMENT, "values is null");
    if (n != SHATTER_LAYOUT_EXT3_COUNT) return SetError(err, SHATTER_VERSION_MISMATCH, "ext3 layout count differs");
    for (std::size_t i = 0; i < n; ++i) {
        if (values[i] != kLayoutExt3[i])
            return SetError(err, SHATTER_VERSION_MISMATCH, "ext3 layout entry " + std::to_string(i) + " differs",
                            static_cast<int>(i) + 1);
    }
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_db_rules_ext2(const shatter_db* db, shatter_rules_ext2* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    out->unarmed_weapon_damage_physical = d->Rules().unarmedWeaponDamagePhysical;
    out->require_on_screen_margin = d->Rules().requireOnScreenMargin;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_skill_base_damage(const shatter_db* db, const char* skill_id,
                                                                std::size_t skill_id_len, const char* weapon_base_id,
                                                                std::size_t weapon_base_id_len,
                                                                double out[4]) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    std::string_view sid, wid;
    if (out == nullptr || skill_id == nullptr || !Text(skill_id, skill_id_len, sid) ||
        !Text(weapon_base_id, weapon_base_id_len, wid))
        return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    const SkillData* s = d->FindSkill(sid);
    if (s == nullptr) return SHATTER_NOT_FOUND;
    const ItemBaseData* w = nullptr;
    if (!wid.empty()) {
        w = d->FindItemBase(wid);
        if (w == nullptr) return SHATTER_NOT_FOUND;
    }
    const std::array<double, kDamageTypeCount> dmg = ComputeSkillBaseDamage(*d, *s, w);
    for (int t = 0; t < kDamageTypeCount; ++t) out[t] = dmg[static_cast<std::size_t>(t)];
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_resolve_hit_db(const shatter_db* db, const shatter_statblock* attacker,
                                                             const shatter_statblock* defender,
                                                             const shatter_hit_input* input, shatter_rng* rng,
                                                             shatter_hit_result* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    shatter_rules rules;
    ToC(d->Rules(), rules);
    return shatter_resolve_hit(attacker, defender, input, &rules, rng, out);
}

SHATTER_API shatter_status SHATTER_CALL shatter_resolve_hit_charged(
    const shatter_db* db, const shatter_statblock* attacker, const shatter_statblock* defender,
    const shatter_hit_input* input, const char* class_id, std::size_t class_id_len, double charge_fraction,
    shatter_rng* rng, shatter_hit_result* out, shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    const ContentDB* d = UsableDb(db);
    std::string_view cid;
    if (attacker == nullptr || defender == nullptr || input == nullptr || rng == nullptr || out == nullptr ||
        class_id == nullptr || !Text(class_id, class_id_len, cid))
        return SetError(err, SHATTER_INVALID_ARGUMENT, "null argument or class_id is not valid UTF-8");
    if (d == nullptr) return DbError(db, err);
    const BasicKitData* kit = d->FindBasicKit(cid);
    if (kit == nullptr) return SetError(err, SHATTER_NOT_FOUND, "class has no basic kit (basic_kits.csv)");
    double mult = 1.0;
    // Erro tipado, antes de qualquer efeito: fração fora de [0, 1] ou NaN. Nada muda e o rng não avança.
    if (!HeavyChargeMultiplier(*kit, charge_fraction, mult))
        return SetError(err, SHATTER_INVALID_ARGUMENT, "charge_fraction must be in [0, 1]");
    shatter_rules rules;
    ToC(d->Rules(), rules);
    const shatter_status st = ResolveHitImpl(attacker, defender, input, &rules, rng, out, mult);
    if (st != SHATTER_OK) return SetError(err, st, "resolve_hit failed");
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_effective_cooldown_db(const shatter_db* db, double base_cooldown,
                                                                    double cooldown_recovery,
                                                                    double* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    *out = EffectiveCooldown(base_cooldown, cooldown_recovery, d->Rules());
    return SHATTER_OK;
}

// --- Vitals ---------------------------------------------------------------------------------------
SHATTER_API shatter_status SHATTER_CALL shatter_vitals_create(const shatter_db* db, const shatter_statblock* stats,
                                                            const char* class_id, std::size_t class_id_len,
                                                            shatter_vitals* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (stats == nullptr || out == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    const ClassData* cls = nullptr;
    if (!FindClassArg(*d, class_id, class_id_len, cls)) return SHATTER_INVALID_ARGUMENT;
    VitalsToC(CreateVitals(stats->sb, cls), *out);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_vitals_tick(const shatter_db* db, shatter_vitals* vitals,
                                                          const shatter_statblock* stats, const char* class_id,
                                                          std::size_t class_id_len, double dt,
                                                          std::uint8_t in_combat) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (vitals == nullptr || stats == nullptr || !std::isfinite(dt)) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    const ClassData* cls = nullptr;
    if (!FindClassArg(*d, class_id, class_id_len, cls)) return SHATTER_INVALID_ARGUMENT;
    Vitals v = VitalsFromC(*vitals);
    TickVitals(v, stats->sb, cls, dt, in_combat != 0);
    VitalsToC(v, *vitals);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_vitals_gain_resource(shatter_vitals* vitals,
                                                                   const shatter_statblock* stats,
                                                                   double amount) SHATTER_NOEXCEPT {
    if (vitals == nullptr || stats == nullptr || !std::isfinite(amount)) return SHATTER_INVALID_ARGUMENT;
    Vitals v = VitalsFromC(*vitals);
    GainResource(v, stats->sb, amount);
    VitalsToC(v, *vitals);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_vitals_spend_resource(shatter_vitals* vitals, double amount,
                                                                    std::uint8_t* ok) SHATTER_NOEXCEPT {
    if (vitals == nullptr || ok == nullptr || !std::isfinite(amount)) return SHATTER_INVALID_ARGUMENT;
    Vitals v = VitalsFromC(*vitals);
    *ok = TrySpendResource(v, amount) ? 1 : 0;
    VitalsToC(v, *vitals);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_vitals_tick_ex(const shatter_db* db, shatter_vitals* vitals,
                                                             const shatter_statblock* stats, const char* class_id,
                                                             std::size_t class_id_len, double dt, std::uint8_t in_combat,
                                                             std::uint8_t moving) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (vitals == nullptr || stats == nullptr || !std::isfinite(dt)) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    const ClassData* cls = nullptr;
    if (!FindClassArg(*d, class_id, class_id_len, cls)) return SHATTER_INVALID_ARGUMENT;
    Vitals v = VitalsFromC(*vitals);
    TickVitals(v, stats->sb, cls, dt, in_combat != 0, moving != 0);
    VitalsToC(v, *vitals);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_vitals_gain_on_hit(const shatter_db* db, shatter_vitals* vitals,
                                                                 const shatter_statblock* stats, const char* class_id,
                                                                 std::size_t class_id_len) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (vitals == nullptr || stats == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    const ClassData* cls = nullptr;
    if (!FindClassArg(*d, class_id, class_id_len, cls)) return SHATTER_INVALID_ARGUMENT;
    Vitals v = VitalsFromC(*vitals);
    GainResourceOnHit(v, stats->sb, cls);
    VitalsToC(v, *vitals);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_vitals_gain_on_block(const shatter_db* db, shatter_vitals* vitals,
                                                                   const shatter_statblock* stats, const char* class_id,
                                                                   std::size_t class_id_len) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (vitals == nullptr || stats == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    const ClassData* cls = nullptr;
    if (!FindClassArg(*d, class_id, class_id_len, cls)) return SHATTER_INVALID_ARGUMENT;
    Vitals v = VitalsFromC(*vitals);
    GainResourceOnBlock(v, stats->sb, cls);
    VitalsToC(v, *vitals);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_db_combat_rules(const shatter_db* db,
                                                              shatter_combat_rules* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    const RulesConstants& r = d->Rules();
    std::memset(out, 0, sizeof(*out));
    out->combo_window = r.comboWindow;
    out->combo_window_after_dodge = r.comboWindowAfterDodge;
    out->attack_buffer = r.attackBuffer;
    out->heavy_hold_threshold = r.heavyHoldThreshold;
    out->light_windup_credit_max = r.lightWindupCreditMax;
    out->guard_lower_time = r.guardLowerTime;
    out->dash_shot_range = r.dashShotRange;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_basic_kit_get(const shatter_db* db, const char* class_id,
                                                            std::size_t class_id_len,
                                                            shatter_basic_kit* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    std::string_view cid;
    if (out == nullptr || class_id == nullptr || !Text(class_id, class_id_len, cid)) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    const BasicKitData* k = d->FindBasicKit(cid);
    if (k == nullptr) return SHATTER_NOT_FOUND;
    std::memset(out, 0, sizeof(*out));
    out->heavy_charge_time = k->heavyChargeTime;
    out->heavy_max_mult = k->heavyMaxMult;
    out->guard_arc = k->guardArc;
    out->guard_max_hold = k->guardMaxHold;
    out->guard_cooldown = k->guardCooldown;
    out->guard_perfect_window = k->guardPerfectWindow;
    out->guard_perfect_cooldown = k->guardPerfectCooldown;
    out->guard_perfect_resource = k->guardPerfectResource;
    out->guard_drain_per_damage = k->guardDrainPerDamage;
    // O carregamento já garantiu 1 a 3 golpes leves, até 4 efeitos da perfeita e IDs de até 63 bytes.
    out->light_chain_count = static_cast<std::int32_t>(k->lightChain.size());
    for (std::size_t i = 0; i < k->lightChain.size() && i < kMaxLightChain; ++i) CopyText(out->light_chain[i], k->lightChain[i]);
    CopyText(out->heavy_skill, k->heavySkill);
    CopyText(out->charge_effect, k->chargeEffect);
    CopyText(out->guard_effect, k->guardEffect);
    out->guard_perfect_effect_count = static_cast<std::int32_t>(k->guardPerfectEffects.size());
    for (std::size_t i = 0; i < k->guardPerfectEffects.size() && i < kMaxGuardPerfectEffects; ++i)
        CopyText(out->guard_perfect_effects[i], k->guardPerfectEffects[i]);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_layout_info_ext5(std::uint32_t* out, std::size_t cap,
                                                               std::size_t* needed) SHATTER_NOEXCEPT {
    if (needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    *needed = SHATTER_LAYOUT_EXT5_COUNT;
    if (cap < SHATTER_LAYOUT_EXT5_COUNT) return SHATTER_BUFFER_TOO_SMALL;
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    std::memcpy(out, kLayoutExt5, sizeof(kLayoutExt5));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_layout_check_ext5(const std::uint32_t* values, std::size_t n,
                                                                shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (values == nullptr && n != 0) return SetError(err, SHATTER_INVALID_ARGUMENT, "values is null");
    if (n != SHATTER_LAYOUT_EXT5_COUNT) return SetError(err, SHATTER_VERSION_MISMATCH, "ext5 layout count differs");
    for (std::size_t i = 0; i < n; ++i) {
        if (values[i] != kLayoutExt5[i])
            return SetError(err, SHATTER_VERSION_MISMATCH, "ext5 layout entry " + std::to_string(i) + " differs",
                            static_cast<int>(i) + 1);
    }
    return SHATTER_OK;
}

// --- Tempos, velocidade, ataque ---------------------------------------------------------------------
SHATTER_API shatter_status SHATTER_CALL shatter_skill_timing(const shatter_db* db, const char* skill_id,
                                                           std::size_t skill_id_len, const shatter_statblock* stats,
                                                           const char* modifier_id, std::size_t modifier_id_len,
                                                           shatter_action_timing* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    std::string_view sid, mid;
    if (stats == nullptr || out == nullptr || skill_id == nullptr || !Text(skill_id, skill_id_len, sid) ||
        !Text(modifier_id, modifier_id_len, mid))
        return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    const SkillData* s = d->FindSkill(sid);
    if (s == nullptr) return SHATTER_NOT_FOUND;
    EliteProfile elite;
    const EliteProfile* ep = nullptr;
    if (!mid.empty()) {
        const EliteModifierData* m = d->FindEliteModifier(mid);
        if (m == nullptr) return SHATTER_NOT_FOUND;
        elite = MakeEliteProfile(*d, m, false);
        ep = &elite;
    }
    const ActionTimingInfo t = ComputeActionTiming(*d, *s, stats->sb, ep);
    out->windup = t.windup;
    out->impact = t.impact;
    out->recovery = t.recovery;
    out->cooldown = t.cooldown;
    out->cost = t.cost;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_skill_timing_weapon(const shatter_db* db, const char* skill_id,
                                                                  std::size_t skill_id_len, const shatter_statblock* stats,
                                                                  const char* class_id, std::size_t class_id_len,
                                                                  const char* weapon_base_id, std::size_t weapon_base_id_len,
                                                                  shatter_action_timing* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    std::string_view sid, cid, wid;
    if (stats == nullptr || out == nullptr || skill_id == nullptr || !Text(skill_id, skill_id_len, sid) ||
        !Text(class_id, class_id_len, cid) || !Text(weapon_base_id, weapon_base_id_len, wid))
        return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    const SkillData* s = d->FindSkill(sid);
    if (s == nullptr) return SHATTER_NOT_FOUND;
    const ItemBaseData* weapon = nullptr;
    if (!wid.empty()) {
        weapon = d->FindItemBase(wid);
        if (weapon == nullptr) return SHATTER_NOT_FOUND;
    }
    const ActionTimingInfo t = ComputeActionTiming(*d, *s, stats->sb, nullptr, WeaponTimeFactor(*s, weapon, ClassRefAttackTime(*d, cid)));
    out->windup = t.windup;
    out->impact = t.impact;
    out->recovery = t.recovery;
    out->cooldown = t.cooldown;
    out->cost = t.cost;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_move_speed(const shatter_statblock* stats, double base_uu_per_sec,
                                                         double* out) SHATTER_NOEXCEPT {
    if (stats == nullptr || out == nullptr || !std::isfinite(base_uu_per_sec)) return SHATTER_INVALID_ARGUMENT;
    *out = MoveSpeedUu(stats->sb, base_uu_per_sec);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_can_act(const shatter_statblock* stats, const shatter_actor* actor,
                                                      std::uint8_t* out) SHATTER_NOEXCEPT {
    if (stats == nullptr || out == nullptr) return SHATTER_INVALID_ARGUMENT;
    *out = (CanAct(stats->sb) && (actor == nullptr || actor->st.CanAct())) ? 1 : 0;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_can_move(const shatter_statblock* stats, const shatter_actor* actor,
                                                       std::uint8_t* out) SHATTER_NOEXCEPT {
    if (stats == nullptr || out == nullptr) return SHATTER_INVALID_ARGUMENT;
    *out = (CanMove(stats->sb) && (actor == nullptr || actor->st.CanAct())) ? 1 : 0;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_pick_attack(const shatter_db* db, const char* enemy_id,
                                                          std::size_t enemy_id_len, shatter_rng* rng,
                                                          std::int32_t* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    std::string_view id;
    if (rng == nullptr || out == nullptr || enemy_id == nullptr || !Text(enemy_id, enemy_id_len, id))
        return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    const EnemyData* e = d->FindEnemy(id);
    if (e == nullptr) return SHATTER_NOT_FOUND;
    Pcg32 r = Pcg32::FromRaw(rng->state, rng->inc);
    *out = PickEnemyAttack(*e, r);
    rng->state = r.State();
    rng->inc = r.Increment();
    return SHATTER_OK;
}

// --- Poções ------------------------------------------------------------------------------------------
SHATTER_API shatter_status SHATTER_CALL shatter_potion_resolve(const shatter_db* db, const char* potion_id,
                                                             std::size_t potion_id_len, const shatter_statblock* stats,
                                                             shatter_vitals* vitals,
                                                             shatter_potion_outcome* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    std::string_view id;
    if (stats == nullptr || vitals == nullptr || out == nullptr || potion_id == nullptr ||
        !Text(potion_id, potion_id_len, id))
        return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    const PotionData* p = d->FindPotion(id);
    std::memset(out, 0, sizeof(*out));
    if (p == nullptr) {
        out->status = SHATTER_POTION_UNKNOWN;
        return SHATTER_NOT_FOUND;
    }
    const double maxLife = stats->sb.Get(StatId::Life);
    ApplyPotionToVitals(ResolvePotion(*p, maxLife, stats->sb.Get(StatId::PotionEffect)), maxLife, *vitals, *out);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_potions_create(const shatter_db* db, shatter_potions** out) SHATTER_NOEXCEPT {
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    *out = nullptr;
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    std::unique_ptr<shatter_potions> box(new (std::nothrow) shatter_potions());
    if (!box) return SHATTER_INTERNAL;
    box->belt = MakeFullPotionBelt(*d);
    *out = box.release();
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_potions_from_save(const shatter_db* db, const shatter_save* save,
                                                                std::size_t character_index,
                                                                shatter_potions** out) SHATTER_NOEXCEPT {
    if (out == nullptr || save == nullptr) return SHATTER_INVALID_ARGUMENT;
    *out = nullptr;
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    if (character_index >= save->data.characters.size()) return SHATTER_INVALID_ARGUMENT;
    std::unique_ptr<shatter_potions> box(new (std::nothrow) shatter_potions());
    if (!box) return SHATTER_INTERNAL;
    box->belt = MakePotionBelt(*d, save->data.characters[character_index].potionSlots);
    *out = box.release();
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_potions_to_save(const shatter_potions* potions, shatter_save* save,
                                                              std::size_t character_index) SHATTER_NOEXCEPT {
    if (potions == nullptr || save == nullptr || character_index >= save->data.characters.size())
        return SHATTER_INVALID_ARGUMENT;
    save->data.characters[character_index].potionSlots = potions->belt.slots;
    return SHATTER_OK;
}

SHATTER_API void SHATTER_CALL shatter_potions_destroy(shatter_potions* potions) SHATTER_NOEXCEPT { delete potions; }

SHATTER_API shatter_status SHATTER_CALL shatter_potions_tick(const shatter_db* db, shatter_potions* potions,
                                                           double dt) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (potions == nullptr || !std::isfinite(dt)) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    TickPotions(*d, potions->belt, dt);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_potions_use(const shatter_db* db, shatter_potions* potions,
                                                          const char* potion_id, std::size_t potion_id_len,
                                                          const shatter_statblock* stats, shatter_vitals* vitals,
                                                          shatter_potion_outcome* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    std::string_view id;
    if (potions == nullptr || stats == nullptr || vitals == nullptr || out == nullptr || potion_id == nullptr ||
        !Text(potion_id, potion_id_len, id))
        return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    std::memset(out, 0, sizeof(*out));
    const double maxLife = stats->sb.Get(StatId::Life);
    PotionOutcome po;
    const PotionUseStatus st = UsePotion(*d, potions->belt, id, maxLife, stats->sb.Get(StatId::PotionEffect), &po);
    out->status = static_cast<std::int32_t>(st);
    if (st != PotionUseStatus::Ok) return SHATTER_OK;
    ApplyPotionToVitals(po, maxLife, *vitals, *out);
    out->lockout = po.lockout;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_potions_refill(const shatter_db* db, shatter_potions* potions) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (potions == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    RefillPotions(*d, potions->belt);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_potions_on_elite_killed(const shatter_db* db, shatter_potions* potions,
                                                                      std::uint8_t* added) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (potions == nullptr || added == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    *added = AddChargeOnEliteKill(*d, potions->belt) ? 1 : 0;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_potions_info_json(const shatter_db* db, const shatter_potions* potions,
                                                                std::uint8_t* out, std::size_t cap,
                                                                std::size_t* needed) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (potions == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    Value root = Value::MakeObject();
    root.Set("lockout_remaining", Value(potions->belt.lockoutRemaining));
    Value arr = Value::MakeArray();
    for (const PotionSlotState& s : potions->belt.slots) {
        const PotionData* p = d->FindPotion(s.potionId);
        if (p == nullptr) continue;
        Value o = Value::MakeObject();
        o.Set("potion_id", Value(s.potionId));
        o.Set("kind", Value(p->kind == PotionKind::Heal ? "heal" : "barrier"));
        o.Set("charges", Value(s.charges));
        o.Set("max_charges", Value(p->maxCharges));
        o.Set("recharge_remaining", Value(s.rechargeRemaining));
        o.Set("hotkey_slot", Value(p->hotkeySlot));
        arr.Push(std::move(o));
    }
    root.Set("slots", std::move(arr));
    return WriteJson(root, false, out, cap, needed);
}

// --- Esquiva -----------------------------------------------------------------------------------------
SHATTER_API shatter_status SHATTER_CALL shatter_dodge_init(const shatter_db* db, shatter_dodge_state* state) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (state == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    DodgeState s;
    NormalizeDodge(d->Rules(), s);
    DodgeToC(s, *state);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_dodge_tick(const shatter_db* db, shatter_dodge_state* state,
                                                         double dt) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (state == nullptr || !std::isfinite(dt)) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    DodgeState s = DodgeFromC(*state);
    TickDodge(d->Rules(), s, dt);
    DodgeToC(s, *state);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_dodge_start(const shatter_db* db, shatter_dodge_state* state,
                                                          double resource_available,
                                                          std::int32_t* status) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (state == nullptr || status == nullptr || !std::isfinite(resource_available)) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    DodgeState s = DodgeFromC(*state);
    *status = static_cast<std::int32_t>(TryStartDodge(d->Rules(), s, resource_available));
    DodgeToC(s, *state);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_dodge_invulnerable(const shatter_db* db,
                                                                 const shatter_dodge_state* state,
                                                                 std::uint8_t* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (state == nullptr || out == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    *out = DodgeInvulnerable(d->Rules(), DodgeFromC(*state)) ? 1 : 0;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_dodge_perfect_reward(const shatter_db* db,
                                                                   const shatter_dodge_state* state,
                                                                   double* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (state == nullptr || out == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    *out = DodgePerfectReward(d->Rules(), DodgeFromC(*state));
    return SHATTER_OK;
}

// --- Stun e Guarda Quebrada --------------------------------------------------------------------------
SHATTER_API shatter_status SHATTER_CALL shatter_actor_create(const shatter_db* db, const char* enemy_id,
                                                           std::size_t enemy_id_len, std::uint8_t elite,
                                                           shatter_actor** out) SHATTER_NOEXCEPT {
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    *out = nullptr;
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    std::string_view id;
    if (!Text(enemy_id, enemy_id_len, id)) return SHATTER_INVALID_ARGUMENT;
    const EnemyData* e = nullptr;
    if (!id.empty()) {
        e = d->FindEnemy(id);
        if (e == nullptr) return SHATTER_NOT_FOUND;
    }
    std::unique_ptr<shatter_actor> box(new (std::nothrow) shatter_actor());
    if (!box) return SHATTER_INTERNAL;
    box->st.Init(MakeStatusProfile(*d, e, elite != 0));
    if (e != nullptr) {
        if (const EnemyAiData* ai = d->FindEnemyAi(e->id)) {
            FleeProfile fp;
            fp.lifeFraction = ai->fleeLifeFraction;
            fp.seconds = ai->fleeSeconds;
            fp.oncePerLife = ai->fleeOncePerLife;
            box->flee = FleeState(fp);
        }
    }
    *out = box.release();
    return SHATTER_OK;
}

SHATTER_API void SHATTER_CALL shatter_actor_destroy(shatter_actor* actor) SHATTER_NOEXCEPT { delete actor; }

SHATTER_API shatter_status SHATTER_CALL shatter_actor_apply_effect(shatter_actor* actor, const shatter_db* db,
                                                                 const char* effect_id, std::size_t effect_id_len,
                                                                 const char* source, std::size_t source_len,
                                                                 double magnitude, shatter_effects* fx,
                                                                 shatter_statblock* target,
                                                                 shatter_actor_apply* out) SHATTER_NOEXCEPT {
    std::string_view id, src;
    if (actor == nullptr || fx == nullptr || target == nullptr || out == nullptr || effect_id == nullptr ||
        !Text(effect_id, effect_id_len, id) || !Text(source, source_len, src) || !std::isfinite(magnitude))
        return SHATTER_INVALID_ARGUMENT;
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    const EffectData* e = d->FindEffect(id);
    if (e == nullptr) return SHATTER_NOT_FOUND;
    ApplyToC(actor->st.ApplyEffect(*d, *e, src, magnitude, TriggerKind::None, fx->fx, target->sb, true), *out);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_actor_tick(shatter_actor* actor, double dt, shatter_statblock* target,
                                                         std::uint8_t* stagger_ended) SHATTER_NOEXCEPT {
    if (actor == nullptr || target == nullptr || stagger_ended == nullptr || !std::isfinite(dt))
        return SHATTER_INVALID_ARGUMENT;
    *stagger_ended = actor->st.Tick(dt, target->sb) ? 1 : 0;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_actor_info_get(const shatter_actor* actor,
                                                             shatter_actor_info* out) SHATTER_NOEXCEPT {
    if (actor == nullptr || out == nullptr) return SHATTER_INVALID_ARGUMENT;
    std::memset(out, 0, sizeof(*out));
    out->stun_remaining = actor->st.StunRemaining();
    out->stagger_remaining = actor->st.StaggerRemaining();
    out->immunity_remaining = actor->st.ImmunityRemaining();
    out->can_act = actor->st.CanAct() ? 1 : 0;
    out->stun_immune = actor->st.Profile().stunImmune ? 1 : 0;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_actor_flee_step(shatter_actor* actor, double dt, double life,
                                                              double max_life, std::uint8_t has_target, std::uint8_t dead,
                                                              shatter_flee_result* out) SHATTER_NOEXCEPT {
    if (actor == nullptr || out == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (!std::isfinite(dt) || dt < 0.0 || !std::isfinite(life) || !std::isfinite(max_life)) return SHATTER_INVALID_ARGUMENT;
    const FleeStep s = actor->flee.Step(dt, life, max_life, has_target != 0, dead != 0);
    std::memset(out, 0, sizeof(*out));
    out->remaining = s.remaining;
    out->fleeing = s.fleeing ? 1 : 0;
    out->started = s.started ? 1 : 0;
    out->ended = s.ended ? 1 : 0;
    out->can_flee = actor->flee.Profile().lifeFraction > 0.0 ? 1 : 0;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_actor_flee_reset(shatter_actor* actor) SHATTER_NOEXCEPT {
    if (actor == nullptr) return SHATTER_INVALID_ARGUMENT;
    actor->flee.Reset();
    return SHATTER_OK;
}

// --- Inventário, equipamento, venda e loot no chão (API 1.4) -----------------------------------------
namespace {

std::int32_t ToC(InvResult r) { return static_cast<std::int32_t>(r); }

const ItemInstance* FindAnywhere(const shatter_save& s, std::size_t ci, std::uint64_t uid) {
    if (const ItemInstance* it = FindInContainer(s.data, ci, Container::Backpack, uid)) return it;
    if (const ItemInstance* it = FindInContainer(s.data, ci, Container::Stash, uid)) return it;
    for (const ItemInstance& g : s.ground)
        if (g.uid == uid) return &g;
    if (ci < s.data.characters.size())
        for (const auto& e : s.data.characters[ci].equipment)
            if (e && e->uid == uid) return &*e;
    return nullptr;
}

bool ContainerOk(std::int32_t c) { return c == SHATTER_CONTAINER_BACKPACK || c == SHATTER_CONTAINER_STASH; }

void FillEquip(const EquipOutcome& o, shatter_equip_result* out) {
    std::memset(out, 0, sizeof(*out));
    out->result = ToC(o.result);
    out->slot = o.slot == ItemSlot::Count ? -1 : static_cast<std::int32_t>(o.slot);
    out->displaced_uid = o.displacedUid;
    out->displaced = o.displaced ? 1 : 0;
}

// Coloca o loot no chão (itens com uid) e soma as pilhas ao save.
void GroundAdd(shatter_save& save, LootDrop&& drop) {
    SaveData& s = save.data;
    for (ItemInstance& it : drop.items) {
        if (it.uid == 0) it.uid = s.nextItemUid++;
        if (it.uid >= s.nextItemUid) s.nextItemUid = it.uid + 1;
        save.ground.push_back(std::move(it));
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
}

const std::uint32_t kLayoutExt4[] = {
    static_cast<std::uint32_t>(sizeof(shatter_inventory_info)),
    static_cast<std::uint32_t>(offsetof(shatter_inventory_info, backpack_capacity)),
    static_cast<std::uint32_t>(offsetof(shatter_inventory_info, backpack_used)),
    static_cast<std::uint32_t>(offsetof(shatter_inventory_info, stash_capacity)),
    static_cast<std::uint32_t>(offsetof(shatter_inventory_info, stash_used)),
    static_cast<std::uint32_t>(sizeof(shatter_equip_result)),
    static_cast<std::uint32_t>(offsetof(shatter_equip_result, result)),
    static_cast<std::uint32_t>(offsetof(shatter_equip_result, slot)),
    static_cast<std::uint32_t>(offsetof(shatter_equip_result, displaced_uid)),
    static_cast<std::uint32_t>(offsetof(shatter_equip_result, displaced))
    };
static_assert(sizeof(kLayoutExt4) / sizeof(kLayoutExt4[0]) == SHATTER_LAYOUT_EXT4_COUNT, "SHATTER_LAYOUT_EXT4_COUNT desatualizado");

}  // namespace

SHATTER_API shatter_status SHATTER_CALL shatter_inventory_info_get(const shatter_db* db, const shatter_save* save,
                                                                 std::size_t character_index,
                                                                 shatter_inventory_info* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (save == nullptr || out == nullptr || character_index >= save->data.characters.size()) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    const InventoryInfo i = GetInventoryInfo(*d, save->data, character_index);
    out->backpack_capacity = i.backpackCapacity;
    out->backpack_used = i.backpackUsed;
    out->stash_capacity = i.stashCapacity;
    out->stash_used = i.stashUsed;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_inventory_slot_enabled(const shatter_db* db, std::int32_t slot,
                                                                     std::uint8_t* enabled) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (enabled == nullptr || slot < 0 || slot >= kItemSlotCount) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    *enabled = d->Rules().equipSlotEnabled[static_cast<std::size_t>(slot)] ? 1 : 0;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_inventory_list_json(const shatter_save* save, std::size_t character_index,
                                                                  std::int32_t container, std::uint8_t* out,
                                                                  std::size_t cap, std::size_t* needed) SHATTER_NOEXCEPT {
    if (save == nullptr || needed == nullptr || character_index >= save->data.characters.size() || !ContainerOk(container))
        return SHATTER_INVALID_ARGUMENT;
    const std::vector<ItemInstance>& v = container == SHATTER_CONTAINER_STASH ? save->data.stash
                                                                              : save->data.characters[character_index].backpack;
    Value a = Value::MakeArray();
    for (const ItemInstance& it : v) a.Push(ItemToJson(it));
    return WriteJson(a, false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_inventory_sort(const shatter_db* db, shatter_save* save,
                                                             std::size_t character_index) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (save == nullptr || character_index >= save->data.characters.size()) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    return SortBackpack(*d, save->data, character_index) == InvResult::Ok ? SHATTER_OK : SHATTER_INTERNAL;
}

SHATTER_API shatter_status SHATTER_CALL shatter_inventory_move(const shatter_db* db, shatter_save* save,
                                                             std::size_t character_index, std::uint64_t uid,
                                                             std::int32_t to, std::int32_t* result) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (save == nullptr || result == nullptr || character_index >= save->data.characters.size() || !ContainerOk(to))
        return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    *result = ToC(MoveItem(*d, save->data, character_index, uid, static_cast<Container>(to)));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_inventory_equip(const shatter_db* db, shatter_save* save,
                                                              std::size_t character_index, std::uint64_t uid,
                                                              std::int32_t slot, shatter_statblock* stats,
                                                              shatter_equip_result* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (save == nullptr || out == nullptr || character_index >= save->data.characters.size() || slot < -1 ||
        slot >= kItemSlotCount)
        return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    const ItemSlot target = slot < 0 ? ItemSlot::Count : static_cast<ItemSlot>(slot);
    FillEquip(Equip(*d, save->data, character_index, uid, target, stats != nullptr ? &stats->sb : nullptr), out);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_inventory_unequip(const shatter_db* db, shatter_save* save,
                                                                std::size_t character_index, std::int32_t slot,
                                                                shatter_statblock* stats,
                                                                shatter_equip_result* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (save == nullptr || out == nullptr || character_index >= save->data.characters.size() || slot < 0 ||
        slot >= kItemSlotCount)
        return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    FillEquip(Unequip(*d, save->data, character_index, static_cast<ItemSlot>(slot), stats != nullptr ? &stats->sb : nullptr), out);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_inventory_compare(const shatter_db* db, const shatter_save* save,
                                                                std::size_t character_index, std::uint64_t uid,
                                                                std::int32_t slot, std::uint8_t* out, std::size_t cap,
                                                                std::size_t* needed) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (save == nullptr || needed == nullptr || character_index >= save->data.characters.size() || slot < -1 ||
        slot >= kItemSlotCount)
        return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    ItemComparison cmp;
    const ItemInstance* it = FindAnywhere(*save, character_index, uid);
    if (it == nullptr) cmp.result = InvResult::NotFound;
    else cmp = CompareItem(*d, save->data.characters[character_index], *it, slot < 0 ? ItemSlot::Count : static_cast<ItemSlot>(slot));
    Value o = Value::MakeObject();
    o.Set("result", Value(static_cast<std::int64_t>(ToC(cmp.result))));
    o.Set("slot", Value(cmp.slot == ItemSlot::Count ? std::string() : std::string(ToString(cmp.slot))));
    o.Set("equipped_uid", json::FromUInt64(cmp.equippedUid));
    o.Set("is_weapon", Value(cmp.isWeapon));
    o.Set("weapon_dps_before", Value(cmp.weaponDpsBefore));
    o.Set("weapon_dps_after", Value(cmp.weaponDpsAfter));
    Value deltas = Value::MakeArray();
    for (const StatDelta& dl : cmp.deltas) {
        Value e = Value::MakeObject();
        e.Set("stat", Value(ToString(dl.stat)));
        e.Set("before", Value(dl.before));
        e.Set("after", Value(dl.after));
        deltas.Push(std::move(e));
    }
    o.Set("deltas", std::move(deltas));
    return WriteJson(o, false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_inventory_sell_value(const shatter_db* db, const shatter_save* save,
                                                                   std::size_t character_index, std::uint64_t uid,
                                                                   std::int64_t* value) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (save == nullptr || value == nullptr || character_index >= save->data.characters.size()) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    const ItemInstance* it = FindAnywhere(*save, character_index, uid);
    if (it == nullptr) return SHATTER_NOT_FOUND;
    *value = SellValue(*d, *it);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_inventory_sell(const shatter_db* db, shatter_save* save,
                                                             std::size_t character_index, std::int32_t container,
                                                             std::uint64_t uid, std::int64_t* gold,
                                                             std::int32_t* result) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (save == nullptr || result == nullptr || character_index >= save->data.characters.size() || !ContainerOk(container))
        return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    std::int64_t paid = 0;
    *result = ToC(SellItem(*d, save->data, character_index, static_cast<Container>(container), uid, &paid));
    if (gold != nullptr) *gold = *result == SHATTER_INV_OK ? paid : 0;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_inventory_discard(shatter_save* save, std::size_t character_index,
                                                                std::int32_t container, std::uint64_t uid,
                                                                std::int32_t* result) SHATTER_NOEXCEPT {
    if (save == nullptr || result == nullptr || character_index >= save->data.characters.size() || !ContainerOk(container))
        return SHATTER_INVALID_ARGUMENT;
    *result = ToC(DiscardItem(save->data, character_index, static_cast<Container>(container), uid));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_item_visual_set_id(const shatter_db* db, const char* base_id,
                                                                 std::size_t base_id_len, const char* unique_id,
                                                                 std::size_t unique_id_len, std::uint8_t* out,
                                                                 std::size_t cap, std::size_t* needed) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    std::string_view base, uni;
    if (needed == nullptr || !Text(base_id, base_id_len, base) || !Text(unique_id, unique_id_len, uni)) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    if (d->FindItemBase(base) == nullptr) return SHATTER_NOT_FOUND;
    if (!uni.empty() && d->FindUnique(uni) == nullptr) return SHATTER_NOT_FOUND;
    ItemInstance probe;
    probe.baseId = ContentId(base);
    probe.uniqueId = ContentId(uni);
    return WriteOut(ItemVisualSetId(*d, probe), out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_save_drop_loot(const shatter_db* db, shatter_save* save,
                                                             const char* table_id, std::size_t table_id_len,
                                                             const shatter_loot_context* ctx, shatter_rng* rng,
                                                             std::uint8_t* out, std::size_t cap, std::size_t* needed,
                                                             shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (save == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "save is null");
    // shatter_loot_roll só confirma uid e rng se a saída couber: aqui nada muda se ela falhar.
    const shatter_status st = shatter_loot_roll(db, save, table_id, table_id_len, ctx, rng, out, cap, needed, err);
    if (st != SHATTER_OK) return st;
    Value v;
    json::ParseError pe;
    LootDrop drop;
    std::string msg;
    if (!json::Parse(std::string_view(reinterpret_cast<const char*>(out), *needed), v, &pe) || !LootFromJson(v, drop, &msg))
        return SetError(err, SHATTER_INTERNAL, "drop_loot: " + msg);
    GroundAdd(*save, std::move(drop));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_save_ground_add_loot(shatter_save* save, const char* loot_json,
                                                                   std::size_t len, shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (save == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "save is null");
    Value v;
    shatter_status st = SHATTER_OK;
    if (!ParseJsonText(loot_json, len, v, err, st)) return st;
    LootDrop drop;
    std::string msg;
    if (!LootFromJson(v, drop, &msg)) return SetError(err, SHATTER_PARSE_ERROR, "loot: " + msg);
    GroundAdd(*save, std::move(drop));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_save_ground_list(const shatter_save* save, std::uint8_t* out,
                                                               std::size_t cap, std::size_t* needed) SHATTER_NOEXCEPT {
    if (save == nullptr || needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    Value o = Value::MakeObject();
    Value items = Value::MakeArray();
    for (const ItemInstance& it : save->ground) items.Push(ItemToJson(it));
    o.Set("items", std::move(items));
    return WriteJson(o, false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_save_pickup(const shatter_db* db, shatter_save* save,
                                                          std::size_t character_index, std::uint64_t uid,
                                                          std::int32_t* dest) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (save == nullptr || dest == nullptr || character_index >= save->data.characters.size()) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    for (std::size_t i = 0; i < save->ground.size(); ++i) {
        if (save->ground[i].uid != uid) continue;
        const PickupDest r = PickupItem(*d, save->data, character_index, save->ground[i]);
        if (r != PickupDest::Full) save->ground.erase(save->ground.begin() + static_cast<std::ptrdiff_t>(i));
        *dest = r == PickupDest::Backpack ? SHATTER_PICKUP_BACKPACK
                : r == PickupDest::Stash  ? SHATTER_PICKUP_STASH
                                          : SHATTER_PICKUP_FULL;
        return SHATTER_OK;
    }
    *dest = SHATTER_PICKUP_NOT_FOUND;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_save_ground_discard(shatter_save* save, std::uint64_t uid,
                                                                  std::int32_t* result) SHATTER_NOEXCEPT {
    if (save == nullptr || result == nullptr) return SHATTER_INVALID_ARGUMENT;
    for (std::size_t i = 0; i < save->ground.size(); ++i) {
        if (save->ground[i].uid == uid) {
            save->ground.erase(save->ground.begin() + static_cast<std::ptrdiff_t>(i));
            *result = SHATTER_INV_OK;
            return SHATTER_OK;
        }
    }
    *result = SHATTER_INV_NOT_FOUND;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_save_ground_clear(shatter_save* save) SHATTER_NOEXCEPT {
    if (save == nullptr) return SHATTER_INVALID_ARGUMENT;
    save->ground.clear();
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_layout_info_ext4(std::uint32_t* out, std::size_t cap,
                                                               std::size_t* needed) SHATTER_NOEXCEPT {
    if (needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    *needed = SHATTER_LAYOUT_EXT4_COUNT;
    if (cap < SHATTER_LAYOUT_EXT4_COUNT) return SHATTER_BUFFER_TOO_SMALL;
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    std::memcpy(out, kLayoutExt4, sizeof(kLayoutExt4));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_layout_check_ext4(const std::uint32_t* values, std::size_t n,
                                                                shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (values == nullptr && n != 0) return SetError(err, SHATTER_INVALID_ARGUMENT, "values is null");
    if (n != SHATTER_LAYOUT_EXT4_COUNT) return SetError(err, SHATTER_VERSION_MISMATCH, "ext4 layout count differs");
    for (std::size_t i = 0; i < n; ++i) {
        if (values[i] != kLayoutExt4[i])
            return SetError(err, SHATTER_VERSION_MISMATCH, "ext4 layout entry " + std::to_string(i) + " differs",
                            static_cast<int>(i) + 1);
    }
    return SHATTER_OK;
}

// --- Elite --------------------------------------------------------------------------------------------
SHATTER_API shatter_status SHATTER_CALL shatter_elite_roll(const shatter_db* db, shatter_rng* events_rng,
                                                         shatter_elite_info* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (events_rng == nullptr || out == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    Pcg32 r = Pcg32::FromRaw(events_rng->state, events_rng->inc);
    const EliteModifierData* mod = RollEliteModifier(*d, r);
    events_rng->state = r.State();
    events_rng->inc = r.Increment();
    EliteToC(MakeEliteProfile(*d, mod, true), *out);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_elite_profile(const shatter_db* db, const char* modifier_id,
                                                            std::size_t modifier_id_len, std::uint8_t rolled,
                                                            shatter_elite_info* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    std::string_view id;
    if (out == nullptr || !Text(modifier_id, modifier_id_len, id)) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    const EliteModifierData* mod = nullptr;
    if (!id.empty()) {
        mod = d->FindEliteModifier(id);
        if (mod == nullptr) return SHATTER_NOT_FOUND;
    }
    EliteToC(MakeEliteProfile(*d, mod, rolled != 0), *out);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_elite_apply(const shatter_db* db, const shatter_elite_info* info,
                                                          shatter_statblock* stats, double* barrier) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (info == nullptr || stats == nullptr || barrier == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    // O perfil sai do BANCO (modifier_id + rolled); os multiplicadores da struct do chamador não valem (A-06).
    const std::string_view mid(info->modifier_id, strnlen(info->modifier_id, sizeof(info->modifier_id)));
    const EliteModifierData* mod = nullptr;
    if (!mid.empty()) {
        mod = d->FindEliteModifier(mid);
        if (mod == nullptr) return SHATTER_NOT_FOUND;
    }
    const EliteProfile p = MakeEliteProfile(*d, mod, info->rolled != 0);
    ApplyEliteToStats(p, stats->sb);
    *barrier = EliteBarrier(p, stats->sb.Get(StatId::Life));
    return SHATTER_OK;
}

// --- Chefe --------------------------------------------------------------------------------------------
SHATTER_API shatter_status SHATTER_CALL shatter_boss_create(const shatter_db* db, const char* enemy_id,
                                                          std::size_t enemy_id_len, std::int32_t level,
                                                          std::uint64_t seed, shatter_boss** out) SHATTER_NOEXCEPT {
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    *out = nullptr;
    const ContentDB* d = UsableDb(db);
    std::string_view id;
    if (enemy_id == nullptr || !Text(enemy_id, enemy_id_len, id)) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    const EnemyData* e = d->FindEnemy(id);
    if (e == nullptr) return SHATTER_NOT_FOUND;
    std::unique_ptr<shatter_boss> box(new (std::nothrow) shatter_boss(*d, *e, level, seed));
    if (!box) return SHATTER_INTERNAL;
    if (!box->fight.Valid()) return SHATTER_CONTENT_INVALID;  // sem linhas em boss_phases.csv
    box->owner = db;
    ++db->bossRefs;
    *out = box.release();
    return SHATTER_OK;
}

SHATTER_API void SHATTER_CALL shatter_boss_destroy(shatter_boss* boss) SHATTER_NOEXCEPT {
    if (boss == nullptr) return;
    const shatter_db* owner = boss->owner;
    delete boss;
    if (owner != nullptr && --owner->bossRefs == 0 && owner->destroyRequested)
        delete const_cast<shatter_db*>(owner);  // o banco foi destruído antes do último chefe
}

SHATTER_API shatter_status SHATTER_CALL shatter_boss_reset(shatter_boss* boss, shatter_statblock* stats) SHATTER_NOEXCEPT {
    if (boss == nullptr) return SHATTER_INVALID_ARGUMENT;
    boss->events.clear();
    boss->fight.Reset(stats != nullptr ? &stats->sb : nullptr);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_boss_start(shatter_boss* boss) SHATTER_NOEXCEPT {
    if (boss == nullptr) return SHATTER_INVALID_ARGUMENT;
    boss->fight.Start();
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_boss_step(shatter_boss* boss, double dt, const shatter_boss_context* ctx,
                                                        shatter_statblock* stats, std::size_t* event_count) SHATTER_NOEXCEPT {
    if (boss == nullptr || ctx == nullptr || stats == nullptr || event_count == nullptr || !std::isfinite(dt) ||
        !std::isfinite(ctx->boss.x) || !std::isfinite(ctx->boss.z) || !std::isfinite(ctx->player.x) ||
        !std::isfinite(ctx->player.z))
        return SHATTER_INVALID_ARGUMENT;
    boss->events.clear();
    BossFight::Context c;
    c.boss = {ctx->boss.x, ctx->boss.z};
    c.player = {ctx->player.x, ctx->player.z};
    boss->fight.Step(dt, c, stats->sb, boss->events);
    *event_count = boss->events.size();
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_boss_apply_damage(shatter_boss* boss, double amount,
                                                                shatter_vec2 boss_pos, shatter_vec2 origin,
                                                                shatter_boss_damage* out) SHATTER_NOEXCEPT {
    if (boss == nullptr || out == nullptr || !std::isfinite(amount) || !std::isfinite(boss_pos.x) ||
        !std::isfinite(boss_pos.z) || !std::isfinite(origin.x) || !std::isfinite(origin.z))
        return SHATTER_INVALID_ARGUMENT;
    const BossFight::DamageResult r =
        boss->fight.ApplyDamage(amount, Vec2{boss_pos.x, boss_pos.z}, Vec2{origin.x, origin.z}, boss->events);
    std::memset(out, 0, sizeof(*out));
    out->applied = r.applied;
    out->life_after = r.lifeAfter;
    out->shield_blocked = r.shieldBlocked ? 1 : 0;
    out->invulnerable = r.invulnerable ? 1 : 0;
    out->clamped_by_phase = r.clampedByPhase ? 1 : 0;
    out->killed = r.killed ? 1 : 0;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_boss_apply_effect(shatter_boss* boss, const shatter_db* db,
                                                                const char* effect_id, std::size_t effect_id_len,
                                                                const char* source, std::size_t source_len,
                                                                double magnitude, shatter_effects* fx,
                                                                shatter_statblock* stats,
                                                                shatter_actor_apply* out) SHATTER_NOEXCEPT {
    std::string_view id, src;
    if (boss == nullptr || fx == nullptr || stats == nullptr || out == nullptr || effect_id == nullptr ||
        !Text(effect_id, effect_id_len, id) || !Text(source, source_len, src) || !std::isfinite(magnitude))
        return SHATTER_INVALID_ARGUMENT;
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    const EffectData* e = d->FindEffect(id);
    if (e == nullptr) return SHATTER_NOT_FOUND;
    ApplyToC(boss->fight.ApplyEffect(*d, *e, src, magnitude, fx->fx, stats->sb, boss->events), *out);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_boss_wall_hit(shatter_boss* boss, shatter_statblock* stats,
                                                            std::uint8_t* applied) SHATTER_NOEXCEPT {
    if (boss == nullptr || stats == nullptr || applied == nullptr) return SHATTER_INVALID_ARGUMENT;
    *applied = boss->fight.OnWallHit(stats->sb, boss->events) ? 1 : 0;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_boss_events(const shatter_boss* boss, shatter_boss_event* out,
                                                          std::size_t cap, std::size_t* needed) SHATTER_NOEXCEPT {
    if (boss == nullptr || needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    *needed = boss->events.size();
    if (cap < boss->events.size()) return SHATTER_BUFFER_TOO_SMALL;
    if (!boss->events.empty() && out == nullptr) return SHATTER_INVALID_ARGUMENT;
    for (std::size_t i = 0; i < boss->events.size(); ++i) BossEventToC(boss->events[i], out[i]);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_boss_info_get(const shatter_boss* boss, shatter_boss_info* out) SHATTER_NOEXCEPT {
    if (boss == nullptr || out == nullptr) return SHATTER_INVALID_ARGUMENT;
    const BossFight& f = boss->fight;
    std::memset(out, 0, sizeof(*out));
    out->life = f.Life();
    out->max_life = f.MaxLife();
    out->shield_down_remaining = f.ShieldDownRemaining();
    out->turn_rate_deg_per_sec = f.TurnRateDegPerSec();
    out->facing_x = f.Facing().x;
    out->facing_z = f.Facing().z;
    out->stagger_remaining = f.Status().StaggerRemaining();
    out->stun_remaining = f.Status().StunRemaining();
    out->phase = f.Phase();
    out->state = static_cast<std::int32_t>(f.State());
    out->shield_up = f.ShieldUp() ? 1 : 0;
    out->invulnerable = f.Invulnerable() ? 1 : 0;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_boss_shield_covers(const shatter_boss* boss, shatter_vec2 boss_pos,
                                                                 shatter_vec2 origin, std::uint8_t* out) SHATTER_NOEXCEPT {
    if (boss == nullptr || out == nullptr) return SHATTER_INVALID_ARGUMENT;
    *out = boss->fight.ShieldCovers(Vec2{boss_pos.x, boss_pos.z}, Vec2{origin.x, origin.z}) ? 1 : 0;
    return SHATTER_OK;
}

// --- Único do chefe -----------------------------------------------------------------------------------
SHATTER_API shatter_status SHATTER_CALL shatter_save_boss_progress_get(const shatter_save* save,
                                                                     std::size_t character_index,
                                                                     const char* enemy_id, std::size_t enemy_id_len,
                                                                     shatter_boss_progress* out) SHATTER_NOEXCEPT {
    std::string_view id;
    if (save == nullptr || out == nullptr || enemy_id == nullptr || !Text(enemy_id, enemy_id_len, id) ||
        character_index >= save->data.characters.size())
        return SHATTER_INVALID_ARGUMENT;
    out->kills = 0;
    out->kills_since_unique = 0;
    if (const BossProgressEntry* b = FindBossProgress(save->data.characters[character_index].bossProgress, ContentId(id))) {
        out->kills = b->kills;
        out->kills_since_unique = b->killsSinceUnique;
    }
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_save_roll_boss_loot(const shatter_db* db, shatter_save* save,
                                                                  std::size_t character_index, const char* enemy_id,
                                                                  std::size_t enemy_id_len, std::int32_t area_level,
                                                                  shatter_rng* loot_rng, std::uint8_t* out,
                                                                  std::size_t cap, std::size_t* needed,
                                                                  shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    std::string_view id;
    if (save == nullptr || loot_rng == nullptr || needed == nullptr || enemy_id == nullptr ||
        !Text(enemy_id, enemy_id_len, id) || character_index >= save->data.characters.size())
        return SetError(err, SHATTER_INVALID_ARGUMENT, "bad argument");
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return DbError(db, err);
    const EnemyData* e = d->FindEnemy(id);
    if (e == nullptr) return SetError(err, SHATTER_NOT_FOUND, "enemy not found");
    // Trabalha em cópias e só confirma se a saída couber (nada muda com BUFFER_TOO_SMALL).
    CharacterState& ch = save->data.characters[character_index];
    BossProgressEntry prog;
    prog.enemyId = e->id;
    if (const BossProgressEntry* found = FindBossProgress(ch.bossProgress, e->id)) prog = *found;
    std::uint64_t uid = save->data.nextItemUid;
    Pcg32 r = Pcg32::FromRaw(loot_rng->state, loot_rng->inc);
    const LootDrop drop = RollBossLoot(*d, *e, area_level < 1 ? 1 : area_level, prog, &uid, r);
    const std::string text = json::Serialize(LootToJson(drop), false);
    *needed = text.size();
    if (cap < text.size()) return SetError(err, SHATTER_BUFFER_TOO_SMALL, "buffer too small");
    if (!text.empty() && out == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "out is null");
    FindOrAddBossProgress(ch.bossProgress, e->id) = prog;
    save->data.nextItemUid = uid;
    loot_rng->state = r.State();
    loot_rng->inc = r.Increment();
    if (!text.empty()) std::memcpy(out, text.data(), text.size());
    return SHATTER_OK;
}

// --- Expedição confiável ---------------------------------------------------------------------------------
SHATTER_API shatter_status SHATTER_CALL shatter_expedition_forecast_ex(const shatter_db* db, const char* request_json,
                                                                     std::size_t len, std::uint64_t base_seed,
                                                                     std::int32_t samples, shatter_forecast_ex* out,
                                                                     shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (out == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "out is null");
    shatter_forecast base;
    const shatter_status st = shatter_expedition_forecast(db, request_json, len, base_seed, samples, &base, err);
    if (st != SHATTER_OK) return st;
    // O selo vem do pedido (barra e equipamento do snapshot), não do resultado das amostras.
    ExpeditionRequest req;
    OfflineWindow w;
    shatter_status st2 = SHATTER_OK;
    if (!RequestFromText(request_json, len, req, w, err, st2)) return st2;
    std::memset(out, 0, sizeof(*out));
    out->base = base;
    out->calibration = static_cast<std::int32_t>(BuildIdleCalibration(*UsableDb(db), req.snapshot.character));
    return SHATTER_OK;
}

namespace {

// Núcleo do início confiável: o "agora" já foi resolvido pelo core (ou conferido contra o last_seen do SAVE).
shatter_status StartTrustedCommon(const ContentDB& d, shatter_save* save, const char* params_json, std::size_t len,
                                  UnixSeconds nowUtc, bool rollback, std::int32_t* start_check, shatter_error* err) {
    Value v;
    shatter_status st = SHATTER_OK;
    if (!ParseJsonText(params_json, len, v, err, st)) return st;
    if (v.Has("seed") || v.Has("start_utc"))
        return SetError(err, SHATTER_INVALID_ARGUMENT, "seed and start_utc come from the core, not from the caller");
    ExpeditionStartParams p;
    if (!StartParamsFromText(params_json, len, p, err, st)) return st;
    if (rollback) {  // RF-48: relógio voltando não inicia expedição (nada muda)
        *start_check = SHATTER_START_CLOCK_ROLLBACK;
        return SHATTER_OK;
    }
    // O início nunca fica antes do último ponto visto do save.
    const UnixSeconds start = std::max(nowUtc, save->data.lastSeenUtc);
    if (start <= 0 || start > kMaxSaveUtc) return SetError(err, SHATTER_INVALID_ARGUMENT, "now is out of range");
    p.startUtc = start;
    p.seed = DeriveExpeditionSeed(save->data, p.characterIndex, p.startUtc);
    const StartCheck check = StartExpedition(d, save->data, p, nullptr);
    if (check == StartCheck::Ok) save->data.lastSeenUtc = std::max(save->data.lastSeenUtc, start);  // mesmo passo
    *start_check = static_cast<std::int32_t>(check);
    return SHATTER_OK;
}

}  // namespace

SHATTER_API shatter_status SHATTER_CALL shatter_save_start_expedition_trusted(const shatter_db* db, shatter_save* save,
                                                                            const char* params_json, std::size_t len,
                                                                            const shatter_trusted_now* now,
                                                                            std::int32_t* start_check,
                                                                            shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (save == nullptr || now == nullptr || start_check == nullptr)
        return SetError(err, SHATTER_INVALID_ARGUMENT, "save, now or start_check is null");
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return DbError(db, err);
    // Não confia na flag do chamador: confere o "agora" contra o last_seen do SAVE e a tolerância do banco.
    const bool rollback = now->rollback_detected != 0 ||
                          (save->data.lastSeenUtc > 0 && static_cast<double>(now->now) <
                                                              static_cast<double>(save->data.lastSeenUtc) - d->Rules().clockRollbackToleranceSec);
    return StartTrustedCommon(*d, save, params_json, len, now->now, rollback, start_check, err);
}

SHATTER_API shatter_status SHATTER_CALL shatter_save_start_expedition_clock(const shatter_db* db, shatter_save* save,
                                                                          const char* params_json, std::size_t len,
                                                                          const shatter_clock_input* clock,
                                                                          std::int32_t* start_check,
                                                                          shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (save == nullptr || clock == nullptr || start_check == nullptr)
        return SetError(err, SHATTER_INVALID_ARGUMENT, "save, clock or start_check is null");
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return DbError(db, err);
    ClockInput ci;  // mesmo ResolveNow da coleta, com o last_seen do SAVE (o do clock é ignorado)
    ci.localNowUtc = clock->local_now_utc;
    ci.hasSteamTime = clock->has_steam_time != 0;
    ci.steamNowUtc = clock->steam_now_utc;
    ci.lastSeenUtc = save->data.lastSeenUtc;
    const TrustedNow now = ResolveNow(ci, d->Rules());
    return StartTrustedCommon(*d, save, params_json, len, now.now, now.rollbackDetected, start_check, err);
}

SHATTER_API shatter_status SHATTER_CALL shatter_save_collect_expedition_trusted(
    const shatter_db* db, shatter_save* save, std::size_t index, const shatter_clock_input* clock, std::uint32_t flags,
    std::int32_t* collect_status, std::uint8_t* out, std::size_t cap, std::size_t* needed,
    shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (save == nullptr || clock == nullptr || collect_status == nullptr || needed == nullptr)
        return SetError(err, SHATTER_INVALID_ARGUMENT, "save, clock, collect_status or needed is null");
    *needed = 0;
    const ContentDB* d = UsableDb(db);
    if (d == nullptr) return DbError(db, err);
    if (index >= save->data.expeditions.size())
        return SetError(err, SHATTER_INVALID_ARGUMENT, "expedition index out of range");
    const SavedExpedition& e = save->data.expeditions[index];
    if (e.status == ExpeditionStatus::Collected) {
        *collect_status = SHATTER_COLLECT_ALREADY;
        return SHATTER_OK;
    }
    if (e.status != ExpeditionStatus::Running) return SetError(err, SHATTER_INVALID_ARGUMENT, "expedition is not running");
    if (e.characterIndex < 0 || static_cast<std::size_t>(e.characterIndex) >= save->data.characters.size())
        return SetError(err, SHATTER_INVALID_ARGUMENT, "expedition character_index does not exist");
    // Relógio confiável + último ponto conhecido do SAVE (o last_seen do clock é ignorado).
    ClockInput ci;
    ci.localNowUtc = clock->local_now_utc;
    ci.hasSteamTime = clock->has_steam_time != 0;
    ci.steamNowUtc = clock->steam_now_utc;
    ci.lastSeenUtc = save->data.lastSeenUtc;
    const TrustedNow now = ResolveNow(ci, d->Rules());
    const OfflineWindow w =
        ComputeExpeditionWindow(e.request.startUtc, e.request.durationHours, now, save->data.lastSeenUtc, d->Rules());
    if (!w.finished) {
        *collect_status = SHATTER_COLLECT_NOT_FINISHED;
        return SHATTER_OK;
    }
    ExpeditionRequest req = e.request;
    req.effectiveSeconds = w.effectiveSeconds;
    ExpeditionProgress p = SimulateRange(*d, req, ExpeditionProgress(), 0, std::numeric_limits<std::uint32_t>::max());
    ApplyWindowStop(p, w);
    const ExpeditionResult result = FinalizeExpedition(*d, req, p);
    const std::string text = json::Serialize(ResultToJson(result, flags), false);
    *needed = text.size();
    if (cap < text.size()) return SetError(err, SHATTER_BUFFER_TOO_SMALL, "buffer too small");
    if (!text.empty() && out == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "out is null");
    const bool collected = CollectExpedition(*d, save->data, index, result);
    *collect_status = collected ? SHATTER_COLLECT_COLLECTED : SHATTER_COLLECT_ALREADY;
    if (!text.empty()) std::memcpy(out, text.data(), text.size());
    return SHATTER_OK;
}

// --- Economia do protótipo: Vendedor, Frasco de Recarga e Encantador (API 1.6) -------------------------------------
namespace {

static_assert(sizeof(shatter_craft_result) == 32, "shatter_craft_result");
static_assert(sizeof(shatter_vendor_result) == 24, "shatter_vendor_result");
static_assert(sizeof(shatter_flask_result) == 16, "shatter_flask_result");
static_assert(static_cast<int>(CraftResult::BadIndex) == SHATTER_CRAFT_BAD_INDEX, "CraftResult");
static_assert(static_cast<int>(CraftOp::Dismantle) == SHATTER_CRAFT_OP_DISMANTLE, "CraftOp");
static_assert(static_cast<int>(VendorResult::UnknownContent) == SHATTER_VENDOR_UNKNOWN_CONTENT, "VendorResult");
static_assert(static_cast<int>(FlaskResult::UnknownContent) == SHATTER_FLASK_UNKNOWN_CONTENT, "FlaskResult");
static_assert(static_cast<int>(FlaskContext::Idle) == SHATTER_FLASK_CTX_IDLE, "FlaskContext");

const std::uint32_t kLayoutExt6[] = {
    static_cast<std::uint32_t>(sizeof(shatter_craft_result)),
    static_cast<std::uint32_t>(offsetof(shatter_craft_result, result)),
    static_cast<std::uint32_t>(offsetof(shatter_craft_result, changed_affix)),
    static_cast<std::uint32_t>(offsetof(shatter_craft_result, gold_spent)),
    static_cast<std::uint32_t>(offsetof(shatter_craft_result, shards_spent)),
    static_cast<std::uint32_t>(offsetof(shatter_craft_result, shards_gained)),
    static_cast<std::uint32_t>(sizeof(shatter_vendor_result)),
    static_cast<std::uint32_t>(offsetof(shatter_vendor_result, result)),
    static_cast<std::uint32_t>(offsetof(shatter_vendor_result, evicted)),
    static_cast<std::uint32_t>(offsetof(shatter_vendor_result, evicted_rarity)),
    static_cast<std::uint32_t>(offsetof(shatter_vendor_result, gold)),
    static_cast<std::uint32_t>(sizeof(shatter_flask_result)),
    static_cast<std::uint32_t>(offsetof(shatter_flask_result, result)),
    static_cast<std::uint32_t>(offsetof(shatter_flask_result, potion_index)),
    static_cast<std::uint32_t>(offsetof(shatter_flask_result, charges_after)),
    static_cast<std::uint32_t>(offsetof(shatter_flask_result, flasks_left)),
};
static_assert(sizeof(kLayoutExt6) / sizeof(kLayoutExt6[0]) == SHATTER_LAYOUT_EXT6_COUNT, "SHATTER_LAYOUT_EXT6_COUNT desatualizado");

void FillCraft(const CraftPlan& p, shatter_craft_result* out) {
    std::memset(out, 0, sizeof(*out));
    out->result = static_cast<std::int32_t>(p.result);
    out->changed_affix = p.result == CraftResult::Ok ? p.changedAffix : -1;
    if (p.result == CraftResult::Ok) {
        out->gold_spent = p.gold;
        out->shards_spent = p.shards;
        out->shards_gained = p.shardsGain;
    }
}

shatter_status RunCraft(const shatter_db* db, shatter_save* save, std::size_t ci, std::uint64_t uid, CraftOp op, int arg,
                        shatter_craft_result* out) {
    const ContentDB* d = UsableDb(db);
    if (save == nullptr || out == nullptr || ci >= save->data.characters.size()) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    CraftPlan p = PlanCraft(*d, save->data, ci, uid, op, arg);
    CommitCraft(save->data, ci, p);
    FillCraft(p, out);
    return SHATTER_OK;
}

void FillVendor(VendorResult r, std::int64_t gold, bool evicted, Rarity rarity, shatter_vendor_result* out) {
    std::memset(out, 0, sizeof(*out));
    out->result = static_cast<std::int32_t>(r);
    out->gold = r == VendorResult::Ok ? gold : 0;
    out->evicted = evicted ? 1 : 0;
    out->evicted_rarity = evicted ? static_cast<std::int32_t>(rarity) : 0;
}

}  // namespace

SHATTER_API shatter_status SHATTER_CALL shatter_currency_get(const shatter_save* save, const char* id, std::size_t id_len,
                                                           std::int64_t* amount) SHATTER_NOEXCEPT {
    std::string_view name;
    if (save == nullptr || amount == nullptr || id == nullptr || !Text(id, id_len, name)) return SHATTER_INVALID_ARGUMENT;
    *amount = CurrencyAmount(save->data, name);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_craft_quote_json(const shatter_db* db, const shatter_save* save,
                                                               std::size_t character_index, std::uint64_t uid,
                                                               std::int32_t op, std::int32_t arg, std::uint8_t* out,
                                                               std::size_t cap, std::size_t* needed) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (save == nullptr || needed == nullptr || character_index >= save->data.characters.size() || op < 0 ||
        op > SHATTER_CRAFT_OP_DISMANTLE)
        return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    const CraftOp cop = static_cast<CraftOp>(op);
    CraftPlan p;
    if (cop == CraftOp::Add && arg < 0) {  // prévia da oferta: custo sem escolher candidato
        const AffixOffer offer = OfferAddAffix(*d, save->data, character_index, uid);
        p.op = cop;
        p.uid = uid;
        p.result = offer.result;
        p.gold = offer.gold;
        p.shards = offer.shards;
        if (p.result == CraftResult::Ok) {
            if (CurrencyAmount(save->data, kGoldId) < p.gold) p.result = CraftResult::NoGold;
            else if (CurrencyAmount(save->data, kShardsId) < p.shards) p.result = CraftResult::NoShards;
        }
    } else {
        p = PlanCraft(*d, save->data, character_index, uid, cop, arg);
    }
    Value o = Value::MakeObject();
    o.Set("op", Value(ToString(cop)));
    o.Set("result", Value(static_cast<std::int64_t>(p.result)));
    o.Set("gold", Value(p.gold));
    o.Set("shards", Value(p.shards));
    o.Set("shards_gain", Value(p.shardsGain));
    o.Set("affix_count_min", Value(static_cast<std::int64_t>(p.affixCountMin)));
    o.Set("affix_count_max", Value(static_cast<std::int64_t>(p.affixCountMax)));
    o.Set("polish_step", Value(static_cast<std::int64_t>(p.polishStep)));
    o.Set("polish_from", Value(p.polishFrom));
    o.Set("polish_to", Value(p.polishTo));
    o.Set("shards_with_lock", Value(p.shardsWithLock));
    o.Set("shards_no_lock", Value(p.shardsNoLock));
    o.Set("reforges", Value(static_cast<std::int64_t>(p.reforgesBefore)));
    o.Set("expedition_running", Value(HasRunningExpedition(save->data, character_index)));
    o.Set("have_gold", Value(CurrencyAmount(save->data, kGoldId)));
    o.Set("have_shards", Value(CurrencyAmount(save->data, kShardsId)));
    return WriteJson(o, false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_craft_refine(const shatter_db* db, shatter_save* save,
                                                           std::size_t character_index, std::uint64_t uid,
                                                           shatter_craft_result* out) SHATTER_NOEXCEPT {
    return RunCraft(db, save, character_index, uid, CraftOp::Refine, 0, out);
}

SHATTER_API shatter_status SHATTER_CALL shatter_craft_reforge(const shatter_db* db, shatter_save* save,
                                                            std::size_t character_index, std::uint64_t uid,
                                                            std::int32_t locked_affix_index,
                                                            shatter_craft_result* out) SHATTER_NOEXCEPT {
    return RunCraft(db, save, character_index, uid, CraftOp::Reforge, locked_affix_index, out);
}

SHATTER_API shatter_status SHATTER_CALL shatter_craft_add_affix_offer(const shatter_db* db, const shatter_save* save,
                                                                    std::size_t character_index, std::uint64_t uid,
                                                                    std::uint8_t* out, std::size_t cap,
                                                                    std::size_t* needed) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (save == nullptr || needed == nullptr || character_index >= save->data.characters.size()) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    const AffixOffer offer = OfferAddAffix(*d, save->data, character_index, uid);
    Value o = Value::MakeObject();
    o.Set("result", Value(static_cast<std::int64_t>(offer.result)));
    o.Set("gold", Value(offer.gold));
    o.Set("shards", Value(offer.shards));
    Value arr = Value::MakeArray();
    for (const AffixCandidate& c : offer.candidates) {
        Value e = Value::MakeObject();
        e.Set("affix_id", Value(c.affixId));
        e.Set("min", Value(c.minValue));
        e.Set("max", Value(c.maxValue));
        arr.Push(std::move(e));
    }
    o.Set("candidates", std::move(arr));
    return WriteJson(o, false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_craft_add_affix_apply(const shatter_db* db, shatter_save* save,
                                                                    std::size_t character_index, std::uint64_t uid,
                                                                    std::int32_t candidate_index,
                                                                    shatter_craft_result* out) SHATTER_NOEXCEPT {
    return RunCraft(db, save, character_index, uid, CraftOp::Add, candidate_index, out);
}

SHATTER_API shatter_status SHATTER_CALL shatter_craft_polish(const shatter_db* db, shatter_save* save,
                                                           std::size_t character_index, std::uint64_t uid,
                                                           std::int32_t affix_index, shatter_craft_result* out) SHATTER_NOEXCEPT {
    return RunCraft(db, save, character_index, uid, CraftOp::Polish, affix_index, out);
}

SHATTER_API shatter_status SHATTER_CALL shatter_craft_dismantle(const shatter_db* db, shatter_save* save,
                                                              std::size_t character_index, std::uint64_t uid,
                                                              shatter_craft_result* out) SHATTER_NOEXCEPT {
    return RunCraft(db, save, character_index, uid, CraftOp::Dismantle, 0, out);
}

SHATTER_API shatter_status SHATTER_CALL shatter_vendor_sell(const shatter_db* db, shatter_save* save,
                                                          std::size_t character_index, std::int32_t container,
                                                          std::uint64_t uid, shatter_vendor_result* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (save == nullptr || out == nullptr || character_index >= save->data.characters.size() || !ContainerOk(container))
        return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    std::int64_t gold = 0;
    bool evicted = false;
    Rarity rarity = Rarity::Normal;
    const VendorResult r = VendorSell(*d, save->data, character_index, static_cast<Container>(container), uid, &gold, &evicted, &rarity);
    FillVendor(r, gold, evicted, rarity, out);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_vendor_buyback_json(const shatter_db* db, const shatter_save* save,
                                                                  std::uint8_t* out, std::size_t cap,
                                                                  std::size_t* needed) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (save == nullptr || needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    const BuybackInfo info = GetBuybackInfo(*d, save->data);
    Value o = Value::MakeObject();
    o.Set("capacity", Value(static_cast<std::int64_t>(info.capacity)));
    o.Set("count", Value(static_cast<std::int64_t>(info.count)));
    o.Set("would_evict", Value(info.wouldEvict));
    o.Set("evict_rarity", Value(static_cast<std::int64_t>(info.evictRarity)));
    Value items = Value::MakeArray();
    for (const BuybackEntry& e : save->data.vendorBuyback) {
        Value eo = Value::MakeObject();
        eo.Set("item", ItemToJson(e.item));
        eo.Set("paid", Value(e.paid));
        eo.Set("price", Value(BuybackPrice(*d, e.paid)));
        items.Push(std::move(eo));
    }
    o.Set("items", std::move(items));
    return WriteJson(o, false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_vendor_buyback(const shatter_db* db, shatter_save* save,
                                                             std::size_t character_index, std::uint64_t uid,
                                                             shatter_vendor_result* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (save == nullptr || out == nullptr || character_index >= save->data.characters.size()) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    std::int64_t spent = 0;
    const VendorResult r = VendorBuyback(*d, save->data, character_index, uid, &spent);
    FillVendor(r, spent, false, Rarity::Normal, out);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_vendor_stock_json(const shatter_db* db, const shatter_save* save,
                                                                std::uint8_t* out, std::size_t cap,
                                                                std::size_t* needed) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (save == nullptr || needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    Value arr = Value::MakeArray();
    for (const VendorStockData& v : d->VendorStock()) {
        Value e = Value::MakeObject();
        e.Set("id", Value(v.id));
        e.Set("ref_id", Value(v.refId));
        e.Set("price_gold", Value(v.priceGold));
        e.Set("carry_cap", Value(static_cast<std::int64_t>(v.carryCap)));
        e.Set("owned", Value(CurrencyAmount(save->data, v.refId)));
        arr.Push(std::move(e));
    }
    return WriteJson(arr, false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_vendor_buy(const shatter_db* db, shatter_save* save, const char* stock_id,
                                                         std::size_t stock_id_len, std::int32_t qty,
                                                         shatter_vendor_result* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    std::string_view id;
    if (save == nullptr || out == nullptr || stock_id == nullptr || !Text(stock_id, stock_id_len, id)) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    std::int64_t spent = 0;
    const VendorResult r = VendorBuy(*d, save->data, id, qty, &spent);
    FillVendor(r, spent, false, Rarity::Normal, out);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_flask_use(const shatter_db* db, shatter_save* save, shatter_potions* potions,
                                                        std::int32_t context, shatter_flask_result* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (save == nullptr || potions == nullptr || out == nullptr || context < SHATTER_FLASK_CTX_RUN || context > SHATTER_FLASK_CTX_IDLE)
        return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    const FlaskOutcome o = UseRefillFlask(*d, save->data, potions->belt, static_cast<FlaskContext>(context));
    out->result = static_cast<std::int32_t>(o.result);
    out->potion_index = o.potionIndex;
    out->charges_after = o.chargesAfter;
    out->flasks_left = o.flasksLeft;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_layout_info_ext6(std::uint32_t* out, std::size_t cap,
                                                               std::size_t* needed) SHATTER_NOEXCEPT {
    if (needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    *needed = SHATTER_LAYOUT_EXT6_COUNT;
    if (cap < SHATTER_LAYOUT_EXT6_COUNT) return SHATTER_BUFFER_TOO_SMALL;
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    std::memcpy(out, kLayoutExt6, sizeof(kLayoutExt6));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_layout_check_ext6(const std::uint32_t* values, std::size_t n,
                                                                shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (values == nullptr && n != 0) return SetError(err, SHATTER_INVALID_ARGUMENT, "values is null");
    if (n != SHATTER_LAYOUT_EXT6_COUNT) return SetError(err, SHATTER_VERSION_MISMATCH, "ext6 layout count differs");
    for (std::size_t i = 0; i < n; ++i) {
        if (values[i] != kLayoutExt6[i])
            return SetError(err, SHATTER_VERSION_MISMATCH, "ext6 layout entry " + std::to_string(i) + " differs",
                            static_cast<int>(i) + 1);
    }
    return SHATTER_OK;
}


// --- Core da Cripta: mundo, baús, encontros, XP e Fervor (API 1.7) ------------------------------------------------
namespace {

static_assert(sizeof(shatter_xp_info) == 40, "shatter_xp_info");
static_assert(sizeof(shatter_fervor_info) == 48, "shatter_fervor_info");

const std::uint32_t kLayoutExt7[] = {
    static_cast<std::uint32_t>(sizeof(shatter_xp_info)),
    static_cast<std::uint32_t>(offsetof(shatter_xp_info, awarded)),
    static_cast<std::uint32_t>(offsetof(shatter_xp_info, xp_in_level)),
    static_cast<std::uint32_t>(offsetof(shatter_xp_info, xp_to_next)),
    static_cast<std::uint32_t>(offsetof(shatter_xp_info, level_before)),
    static_cast<std::uint32_t>(offsetof(shatter_xp_info, level)),
    static_cast<std::uint32_t>(offsetof(shatter_xp_info, level_cap)),
    static_cast<std::uint32_t>(offsetof(shatter_xp_info, reserved)),
    static_cast<std::uint32_t>(sizeof(shatter_fervor_info)),
    static_cast<std::uint32_t>(offsetof(shatter_fervor_info, xp_mult)),
    static_cast<std::uint32_t>(offsetof(shatter_fervor_info, gold_mat_mult)),
    static_cast<std::uint32_t>(offsetof(shatter_fervor_info, rare_mult)),
    static_cast<std::uint32_t>(offsetof(shatter_fervor_info, xp_bonus)),
    static_cast<std::uint32_t>(offsetof(shatter_fervor_info, gold_mat_bonus)),
    static_cast<std::uint32_t>(offsetof(shatter_fervor_info, rare_bonus)),
};
static_assert(sizeof(kLayoutExt7) / sizeof(kLayoutExt7[0]) == SHATTER_LAYOUT_EXT7_COUNT, "SHATTER_LAYOUT_EXT7_COUNT desatualizado");

void FillXp(const XpAward& a, shatter_xp_info* out) {
    std::memset(out, 0, sizeof(*out));
    out->awarded = a.awarded;
    out->xp_in_level = a.xpInLevel;
    out->xp_to_next = a.xpToNext;
    out->level_before = a.levelBefore;
    out->level = a.levelAfter;
    out->level_cap = a.levelCap;
}

}  // namespace

SHATTER_API shatter_status SHATTER_CALL shatter_world_begin_visit(const shatter_db* db, shatter_save* save, const char* map_id,
                                                                std::size_t map_id_len, std::uint64_t* visit_seed) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    std::string_view map;
    if (save == nullptr || visit_seed == nullptr || map_id == nullptr || !Text(map_id, map_id_len, map)) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    if (d->FindMap(map) == nullptr) return SHATTER_NOT_FOUND;
    return BeginAreaVisit(*d, save->data, ContentId(map), visit_seed) ? SHATTER_OK : SHATTER_INVALID_ARGUMENT;
}

SHATTER_API shatter_status SHATTER_CALL shatter_world_object_get(const shatter_save* save, const char* map_id,
                                                               std::size_t map_id_len, const char* object_id,
                                                               std::size_t object_id_len, std::uint8_t* opened) SHATTER_NOEXCEPT {
    std::string_view map, obj;
    if (save == nullptr || opened == nullptr || map_id == nullptr || object_id == nullptr || !Text(map_id, map_id_len, map) ||
        !Text(object_id, object_id_len, obj))
        return SHATTER_INVALID_ARGUMENT;
    *opened = IsWorldObjectOpen(save->data, map, obj) ? 1 : 0;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_world_object_set(shatter_save* save, const char* map_id, std::size_t map_id_len,
                                                               const char* object_id, std::size_t object_id_len,
                                                               std::uint8_t opened) SHATTER_NOEXCEPT {
    std::string_view map, obj;
    if (save == nullptr || map_id == nullptr || object_id == nullptr || !Text(map_id, map_id_len, map) ||
        !Text(object_id, object_id_len, obj))
        return SHATTER_INVALID_ARGUMENT;
    return SetWorldObjectOpen(save->data, ContentId(map), ContentId(obj), opened != 0) ? SHATTER_OK : SHATTER_INVALID_ARGUMENT;
}

SHATTER_API shatter_status SHATTER_CALL shatter_world_state_json(const shatter_save* save, const char* map_id,
                                                               std::size_t map_id_len, std::uint8_t* out, std::size_t cap,
                                                               std::size_t* needed) SHATTER_NOEXCEPT {
    std::string_view map;
    if (save == nullptr || needed == nullptr || map_id == nullptr || !Text(map_id, map_id_len, map)) return SHATTER_INVALID_ARGUMENT;
    Value o = Value::MakeObject();
    o.Set("map_id", Value(std::string(map)));
    const WorldAreaState* a = FindWorldArea(save->data, map);
    o.Set("visits", Value(static_cast<std::int64_t>(a != nullptr ? a->visits : 0u)));
    Value arr = Value::MakeArray();
    if (a != nullptr)
        for (const ContentId& id : a->opened) arr.Push(Value(id));
    o.Set("opened", std::move(arr));
    return WriteJson(o, false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_map_info_json(const shatter_db* db, const char* map_id, std::size_t map_id_len,
                                                            std::uint8_t* out, std::size_t cap, std::size_t* needed) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    std::string_view map;
    if (needed == nullptr || map_id == nullptr || !Text(map_id, map_id_len, map)) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    const MapData* m = d->FindMap(map);
    if (m == nullptr) return SHATTER_NOT_FOUND;
    Value o = Value::MakeObject();
    o.Set("map_id", Value(m->id));
    o.Set("monster_level", Value(static_cast<std::int64_t>(m->monsterLevel)));
    o.Set("tier", Value(static_cast<std::int64_t>(m->tier)));
    o.Set("area_loot_table", Value(m->areaLootTable));
    o.Set("boss_encounter", Value(m->bossEncounter));
    Value encs = Value::MakeArray();
    for (const ContentId& id : m->encounters) encs.Push(Value(id));
    o.Set("encounters", std::move(encs));
    Value chests = Value::MakeArray();
    for (const ChestData& c : d->Chests()) {
        if (c.mapId != m->id) continue;
        Value co = Value::MakeObject();
        co.Set("id", Value(c.id));
        co.Set("loot_table", Value(c.lootTable));
        chests.Push(std::move(co));
    }
    o.Set("chests", std::move(chests));
    return WriteJson(o, false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_encounter_roll_json_ex(const shatter_db* db, const char* encounter_id,
                                                                     std::size_t encounter_id_len, std::uint64_t visit_seed,
                                                                     std::int32_t elite_bonus_pct, std::uint8_t* out,
                                                                     std::size_t cap, std::size_t* needed) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    std::string_view enc;
    if (elite_bonus_pct < 0 || elite_bonus_pct > 100) return SHATTER_INVALID_ARGUMENT;
    if (needed == nullptr || encounter_id == nullptr || !Text(encounter_id, encounter_id_len, enc)) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    RolledEncounter r;
    if (!RollEncounter(*d, enc, visit_seed, r, elite_bonus_pct)) return SHATTER_NOT_FOUND;
    Value o = Value::MakeObject();
    o.Set("encounter_id", Value(r.encounterId));
    o.Set("is_boss", Value(r.isBoss));
    Value groups = Value::MakeArray();
    for (const RolledGroup& g : r.groups) {
        Value go = Value::MakeObject();
        go.Set("enemy_id", Value(g.enemyId));
        go.Set("count", Value(static_cast<std::int64_t>(g.slots.size())));
        Value slots = Value::MakeArray();
        for (const RolledSlot& sl : g.slots) {
            Value so = Value::MakeObject();
            so.Set("elite", Value(static_cast<std::int64_t>(sl.elite ? 1 : 0)));
            so.Set("modifier_id", Value(sl.modifierId));
            slots.Push(std::move(so));
        }
        go.Set("slots", std::move(slots));
        groups.Push(std::move(go));
    }
    o.Set("groups", std::move(groups));
    return WriteJson(o, false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_encounter_roll_json(const shatter_db* db, const char* encounter_id,
                                                                  std::size_t encounter_id_len, std::uint64_t visit_seed,
                                                                  std::uint8_t* out, std::size_t cap,
                                                                  std::size_t* needed) SHATTER_NOEXCEPT {
    return shatter_encounter_roll_json_ex(db, encounter_id, encounter_id_len, visit_seed, 0, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_chest_open(const shatter_db* db, shatter_save* save, const char* map_id,
                                                         std::size_t map_id_len, const char* chest_id, std::size_t chest_id_len,
                                                         const shatter_loot_context* ctx, shatter_rng* rng, std::uint8_t* out,
                                                         std::size_t cap, std::size_t* needed, std::int32_t* result,
                                                         shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    const ContentDB* d = UsableDb(db);
    std::string_view map, chest;
    if (save == nullptr || needed == nullptr || result == nullptr || map_id == nullptr || chest_id == nullptr ||
        !Text(map_id, map_id_len, map) || !Text(chest_id, chest_id_len, chest) || !IsValidContentId(chest))
        return SetError(err, SHATTER_INVALID_ARGUMENT, "bad chest arguments");
    if (d == nullptr) return DbError(db, err);
    *needed = 0;
    if (d->FindMap(map) == nullptr) return SetError(err, SHATTER_NOT_FOUND, "map not found");
    if (IsWorldObjectOpen(save->data, map, chest)) {
        *result = SHATTER_CHEST_ALREADY_OPEN;
        return SHATTER_OK;
    }
    const std::string table = ChestLootTable(*d, map, chest);
    if (table.empty()) {
        *result = SHATTER_CHEST_NO_TABLE;
        return SHATTER_OK;
    }
    {  // o estado do mundo precisa caber ANTES de rolar: o loot só sai junto com a marca de aberto
        const WorldAreaState* a = FindWorldArea(save->data, map);
        if ((a == nullptr && save->data.world.size() >= kMaxWorldAreas) || (a != nullptr && a->opened.size() >= kMaxWorldObjects))
            return SetError(err, SHATTER_INVALID_ARGUMENT, "world state is full");
    }
    const shatter_status st = shatter_save_drop_loot(db, save, table.data(), table.size(), ctx, rng, out, cap, needed, err);
    if (st != SHATTER_OK) return st;  // buffer pequeno e erros: nada mudou
    SetWorldObjectOpen(save->data, ContentId(map), ContentId(chest), true);
    *result = SHATTER_CHEST_OPENED;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_encounter_clear_loot(const shatter_db* db, shatter_save* save, const char* map_id,
                                                                   std::size_t map_id_len, const shatter_loot_context* ctx,
                                                                   shatter_rng* rng, std::uint8_t* out, std::size_t cap,
                                                                   std::size_t* needed, shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    const ContentDB* d = UsableDb(db);
    std::string_view map;
    if (save == nullptr || map_id == nullptr || !Text(map_id, map_id_len, map)) return SetError(err, SHATTER_INVALID_ARGUMENT, "bad map");
    if (d == nullptr) return DbError(db, err);
    const std::string table = AreaLootTable(*d, map);
    if (table.empty()) return SetError(err, SHATTER_NOT_FOUND, "map has no area loot table");
    return shatter_save_drop_loot(db, save, table.data(), table.size(), ctx, rng, out, cap, needed, err);
}

SHATTER_API shatter_status SHATTER_CALL shatter_xp_award_kill(const shatter_db* db, shatter_save* save, std::size_t character_index,
                                                            const char* map_id, std::size_t map_id_len, const char* enemy_id,
                                                            std::size_t enemy_id_len, std::int32_t monster_level,
                                                            std::uint8_t elite_rolled, const char* modifier_id,
                                                            std::size_t modifier_id_len, std::uint8_t fervor,
                                                            shatter_xp_info* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    std::string_view map, enemy, mod;
    if (save == nullptr || out == nullptr || character_index >= save->data.characters.size() || enemy_id == nullptr ||
        !Text(map_id, map_id_len, map) || !Text(enemy_id, enemy_id_len, enemy) || !Text(modifier_id, modifier_id_len, mod) ||
        monster_level < 1 || monster_level > 1000)
        return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    if (d->FindEnemy(enemy) == nullptr || (!mod.empty() && d->FindEliteModifier(mod) == nullptr)) return SHATTER_NOT_FOUND;
    FillXp(AwardKillXp(*d, save->data, character_index, map, enemy, monster_level, elite_rolled != 0, mod, fervor != 0), out);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_character_progress(const shatter_db* db, const shatter_save* save,
                                                                 std::size_t character_index, const char* map_id,
                                                                 std::size_t map_id_len, shatter_xp_info* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    std::string_view map;
    if (save == nullptr || out == nullptr || character_index >= save->data.characters.size() || !Text(map_id, map_id_len, map))
        return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    FillXp(CharacterProgress(*d, save->data, character_index, map), out);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_fervor_get(const shatter_db* db, shatter_fervor_info* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return SHATTER_CONTENT_INVALID;
    const FervorInfo f = GetFervorInfo(*d);
    out->xp_mult = f.xpMult;
    out->gold_mat_mult = f.goldMatMult;
    out->rare_mult = f.rareMult;
    out->xp_bonus = f.xpBonus;
    out->gold_mat_bonus = f.goldMatBonus;
    out->rare_bonus = f.rareBonus;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_layout_info_ext7(std::uint32_t* out, std::size_t cap,
                                                               std::size_t* needed) SHATTER_NOEXCEPT {
    if (needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    *needed = SHATTER_LAYOUT_EXT7_COUNT;
    if (cap < SHATTER_LAYOUT_EXT7_COUNT) return SHATTER_BUFFER_TOO_SMALL;
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    std::memcpy(out, kLayoutExt7, sizeof(kLayoutExt7));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_layout_check_ext7(const std::uint32_t* values, std::size_t n,
                                                                shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (values == nullptr && n != 0) return SetError(err, SHATTER_INVALID_ARGUMENT, "values is null");
    if (n != SHATTER_LAYOUT_EXT7_COUNT) return SetError(err, SHATTER_VERSION_MISMATCH, "ext7 layout count differs");
    for (std::size_t i = 0; i < n; ++i) {
        if (values[i] != kLayoutExt7[i])
            return SetError(err, SHATTER_VERSION_MISMATCH, "ext7 layout entry " + std::to_string(i) + " differs",
                            static_cast<int>(i) + 1);
    }
    return SHATTER_OK;
}


// --- Movimento do herói (rampa de aceleração e desaceleração) ----------------------------------------------------
static_assert(sizeof(shatter_hero_move_rules) == 16, "shatter_hero_move_rules");

SHATTER_API shatter_status SHATTER_CALL shatter_db_hero_move_rules(const shatter_db* db, shatter_hero_move_rules* out) SHATTER_NOEXCEPT {
    const ContentDB* d = UsableDb(db);
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (d == nullptr) return db == nullptr ? SHATTER_INVALID_ARGUMENT : SHATTER_CONTENT_INVALID;
    out->accel_seconds = d->Rules().heroMoveAccelSeconds;
    out->decel_seconds = d->Rules().heroMoveDecelSeconds;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_layout_info_ext8(std::uint32_t* out, std::size_t cap, std::size_t* needed) SHATTER_NOEXCEPT {
    if (needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    *needed = SHATTER_LAYOUT_EXT8_COUNT;
    if (cap < SHATTER_LAYOUT_EXT8_COUNT) return SHATTER_BUFFER_TOO_SMALL;
    if (out == nullptr) return SHATTER_INVALID_ARGUMENT;
    out[0] = static_cast<std::uint32_t>(sizeof(shatter_hero_move_rules));
    out[1] = static_cast<std::uint32_t>(offsetof(shatter_hero_move_rules, accel_seconds));
    out[2] = static_cast<std::uint32_t>(offsetof(shatter_hero_move_rules, decel_seconds));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_layout_check_ext8(const std::uint32_t* values, std::size_t n, shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    std::uint32_t expected[SHATTER_LAYOUT_EXT8_COUNT] = {};
    std::size_t needed = 0;
    shatter_layout_info_ext8(expected, SHATTER_LAYOUT_EXT8_COUNT, &needed);
    if (values == nullptr && n != 0) return SetError(err, SHATTER_INVALID_ARGUMENT, "values is null");
    if (n != SHATTER_LAYOUT_EXT8_COUNT) return SetError(err, SHATTER_VERSION_MISMATCH, "ext8 layout count differs");
    for (std::size_t i = 0; i < n; ++i) {
        if (values[i] != expected[i])
            return SetError(err, SHATTER_VERSION_MISMATCH, "ext8 layout entry " + std::to_string(i) + " differs", static_cast<int>(i) + 1);
    }
    return SHATTER_OK;
}

// --- História (story.h) -------------------------------------------------------------------------

SHATTER_API shatter_status SHATTER_CALL shatter_story_load_directory(const char* path, std::size_t path_len, const shatter_db* db,
                                                                   shatter_story** out, shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (out == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "out is null");
    *out = nullptr;
    std::string_view p;
    if (path == nullptr || !Text(path, path_len, p) || p.empty())
        return SetError(err, SHATTER_INVALID_ARGUMENT, "path is null, empty or not valid UTF-8");
    std::unique_ptr<shatter_story> box(new (std::nothrow) shatter_story());
    if (!box) return SetError(err, SHATTER_INTERNAL, "out of memory");
    box->db.LoadDirectory(std::string(p));
    const ContentDB* content = db != nullptr ? UsableDb(db) : nullptr;
    if (db != nullptr && content == nullptr) return SetError(err, SHATTER_CONTENT_INVALID, "db is not a valid finalized content db");
    if (box->db.Errors().empty()) box->db.Finalize(content);
    const auto& errs = box->db.Errors();
    if (!errs.empty()) {
        const ContentError& first = errs.front();
        const bool io = StartsWith(first.message, "E_IO");
        return SetError(err, io ? SHATTER_IO_ERROR : SHATTER_CONTENT_INVALID,
                        first.table + ": " + first.message + " (+" + std::to_string(errs.size() - 1) + " more)", first.line);
    }
    *out = box.release();
    return SHATTER_OK;
}

SHATTER_API void SHATTER_CALL shatter_story_destroy(shatter_story* story) SHATTER_NOEXCEPT { delete story; }

SHATTER_API shatter_status SHATTER_CALL shatter_story_record_echo(const shatter_story* story, shatter_save* save, const char* echo_id,
                                                                std::size_t echo_id_len, std::uint8_t* is_new) SHATTER_NOEXCEPT {
    std::string_view id;
    if (story == nullptr || save == nullptr || is_new == nullptr || echo_id == nullptr || !Text(echo_id, echo_id_len, id))
        return SHATTER_INVALID_ARGUMENT;
    *is_new = 0;
    if (story->db.FindEcho(id) == nullptr) return SHATTER_NOT_FOUND;
    const bool added = RecordEcho(story->db, save->data, id);
    *is_new = added ? 1 : 0;
    // Não registrou e o Eco não estava lá: o save está cheio (kMaxSavedEchoes). Não perde em silêncio.
    if (!added && std::find(save->data.story.echoes.begin(), save->data.story.echoes.end(), id) == save->data.story.echoes.end())
        return SHATTER_INVALID_ARGUMENT;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_story_apply_verdict(const shatter_story* story, shatter_save* save,
                                                                  const char* verdict_id, std::size_t verdict_id_len,
                                                                  std::int32_t* result) SHATTER_NOEXCEPT {
    std::string_view id;
    if (story == nullptr || save == nullptr || result == nullptr || verdict_id == nullptr || !Text(verdict_id, verdict_id_len, id))
        return SHATTER_INVALID_ARGUMENT;
    *result = static_cast<std::int32_t>(ApplyVerdict(story->db, save->data, id));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_story_state_json(const shatter_story* story, const shatter_save* save, std::uint8_t* out,
                                                               std::size_t cap, std::size_t* needed) SHATTER_NOEXCEPT {
    if (story == nullptr || save == nullptr || needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    const StoryState& st = save->data.story;
    Value o = Value::MakeObject();
    o.Set("hunger", Value(static_cast<std::int64_t>(st.hunger)));
    o.Set("hunger_max", Value(static_cast<std::int64_t>(story->db.HungerMax())));
    o.Set("stat_bonus_pct", Value(static_cast<std::int64_t>(TotalStatBonusPct(story->db, save->data))));
    o.Set("potion_effect_pct", Value(static_cast<std::int64_t>(TotalPotionEffectPct(story->db, save->data))));
    Value stainMaps = Value::MakeObject();  // mapId -> pontos de elite; só áreas com Mancha
    for (const StoryRegion& reg : story->db.Regions()) {
        const int bonus = StainEliteBonusPctForMap(story->db, save->data, reg.mapId);
        if (bonus > 0) stainMaps.Set(reg.mapId, Value(static_cast<std::int64_t>(bonus)));
    }
    o.Set("stain_elite_bonus_by_map", std::move(stainMaps));
    Value stainLoot = Value::MakeObject();  // mapId -> tabela de loot extra; só áreas com Mancha e com stain_loot_table
    for (const StoryRegion& reg : story->db.Regions()) {
        const std::string table = StainLootTableForMap(story->db, save->data, reg.mapId);
        if (!table.empty()) stainLoot.Set(reg.mapId, Value(table));
    }
    o.Set("stain_loot_table_by_map", std::move(stainLoot));
    o.Set("devoured_hunger_cost", Value(static_cast<std::int64_t>(story->db.DevouredHungerCost())));
    // docs/09, 15.5: o que a expedição idle recebe (story_devoured_skills / story_devoured_uses).
    Value devoured = Value::MakeArray();
    for (const ContentId& id : DevouredSkills(story->db, save->data)) devoured.Push(Value(id));
    o.Set("devoured_skills", std::move(devoured));
    o.Set("idle_devoured_uses", Value(static_cast<std::int64_t>(IdleDevouredUses(story->db, save->data))));
    Value gated = Value::MakeArray();   // recompensas travadas por gate_reward, com `open` = já liberada
    for (const std::string& g : story->db.GatedRewards()) {
        Value go = Value::MakeObject();
        go.Set("reward", Value(g));
        go.Set("open", Value(IsRewardOpen(story->db, save->data, g)));
        gated.Push(std::move(go));
    }
    o.Set("gated_rewards", std::move(gated));
    Value echoes = Value::MakeArray();
    for (const ContentId& id : st.echoes) echoes.Push(Value(id));
    o.Set("echoes", std::move(echoes));
    Value verdicts = Value::MakeArray();
    for (const StoryVerdictRecord& r : st.verdicts) {
        const StoryVerdict* v = story->db.FindVerdict(r.verdictId);
        Value vo = v != nullptr ? VerdictJson(*v) : Value::MakeObject();
        vo.Set("region_id", Value(r.regionId));
        vo.Set("verdict_id", Value(r.verdictId));
        verdicts.Push(std::move(vo));
    }
    o.Set("verdicts", std::move(verdicts));
    Value quests = Value::MakeArray();
    for (const StoryQuest& q : story->db.Quests()) {
        Value qo = Value::MakeObject();
        qo.Set("quest_id", Value(q.id));
        qo.Set("region_id", Value(q.regionId));
        qo.Set("giver", Value(q.giver));
        qo.Set("objective_type", Value(q.objectiveType));
        qo.Set("objective_target", Value(q.objectiveTarget));
        qo.Set("objective_count", Value(static_cast<std::int64_t>(q.objectiveCount)));
        qo.Set("progress", Value(static_cast<std::int64_t>(QuestProgress(story->db, save->data, q.id))));
        const QuestStatus status = GetQuestStatus(story->db, save->data, q.id);
        qo.Set("status", Value(status == QuestStatus::Done ? "done" : status == QuestStatus::Active ? "active" : "locked"));
        qo.Set("requires", Value(q.requires_));
        qo.Set("reward", Value(q.reward));
        quests.Push(std::move(qo));
    }
    o.Set("quests", std::move(quests));
    return WriteJson(o, false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_story_region_json(const shatter_story* story, const shatter_save* save,
                                                                const char* region_id, std::size_t region_id_len, std::uint8_t* out,
                                                                std::size_t cap, std::size_t* needed) SHATTER_NOEXCEPT {
    std::string_view id;
    if (story == nullptr || save == nullptr || needed == nullptr || region_id == nullptr || !Text(region_id, region_id_len, id))
        return SHATTER_INVALID_ARGUMENT;
    const StoryRegion* r = story->db.FindRegion(id);
    if (r == nullptr) return SHATTER_NOT_FOUND;
    const StoryVerdict* decided = DecidedVerdict(story->db, save->data, id);
    Value o = Value::MakeObject();
    o.Set("region_id", Value(r->id));
    o.Set("map_id", Value(r->mapId));
    o.Set("general_id", Value(r->generalId));
    o.Set("decided", Value(decided != nullptr));
    o.Set("verdict_id", Value(decided != nullptr ? decided->id : std::string()));
    o.Set("echoes_found", Value(static_cast<std::int64_t>(EchoesFound(story->db, save->data, id))));
    std::int64_t total = 0;
    for (const StoryEcho& e : story->db.Echoes()) total += e.regionId == r->id ? 1 : 0;
    o.Set("echoes_total", Value(total));
    Value options = Value::MakeArray();
    for (const ContentId* vid : {&r->exorcizeVerdict, &r->devourVerdict}) {
        const StoryVerdict* v = story->db.FindVerdict(*vid);
        if (v != nullptr) options.Push(VerdictJson(*v));
    }
    o.Set("options", std::move(options));
    return WriteJson(o, false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_story_skill_revealed(const shatter_story* story, const shatter_save* save,
                                                                   const char* region_id, std::size_t region_id_len,
                                                                   const char* skill_id, std::size_t skill_id_len,
                                                                   std::uint8_t* revealed) SHATTER_NOEXCEPT {
    std::string_view region, skill;
    if (story == nullptr || save == nullptr || revealed == nullptr || region_id == nullptr || skill_id == nullptr ||
        !Text(region_id, region_id_len, region) || !Text(skill_id, skill_id_len, skill))
        return SHATTER_INVALID_ARGUMENT;
    if (story->db.FindRegion(region) == nullptr) return SHATTER_NOT_FOUND;
    *revealed = IsSkillRevealed(story->db, save->data, region, skill) ? 1 : 0;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_story_quest_event(const shatter_story* story, shatter_save* save, const char* type,
                                                                std::size_t type_len, const char* target, std::size_t target_len,
                                                                std::uint32_t* completed) SHATTER_NOEXCEPT {
    std::string_view ty, tg;
    if (story == nullptr || save == nullptr || completed == nullptr || type == nullptr || target == nullptr || !Text(type, type_len, ty) ||
        !Text(target, target_len, tg))
        return SHATTER_INVALID_ARGUMENT;
    *completed = static_cast<std::uint32_t>(ReportQuestEvent(story->db, save->data, ty, tg));
    return SHATTER_OK;
}

}  // extern "C"

// =============================================================================================
// Roguelike 2D da Cripta (rogue.h; API 1.8). Fina: valida argumentos, converte JSON e chama o core.
// =============================================================================================
struct shatter_rogue {
    shatter::RogueData data;
    shatter::RogueState state;
    shatter::RogueWaves waves;  // spawner de hordas (API 1.11)
    std::string savePath;  // vazio = sem gravação automática
};

namespace {

bool RogueId(const char* s, std::size_t len, std::string_view& out) { return s != nullptr && Text(s, len, out); }

// Gravação automática depois de uma ação do meta que deu certo (salvar() do meta_2d.gd).
shatter_status RogueAutoSave(const shatter_rogue* r, shatter_error* err = nullptr) {
    if (r->savePath.empty()) return SHATTER_OK;
    std::unique_ptr<IFileIO> io = MakeStdFileIO();
    std::string msg;
    if (!WriteRogueMetaFile(*io, r->savePath, r->state, &msg)) return SetError(err, SHATTER_IO_ERROR, "rogue save: " + msg);
    return SHATTER_OK;
}

// Objeto JSON stat -> número, na ordem do texto. Valor que não é número: erro.
bool RogueParseStats(const char* s, std::size_t len, RogueStats& out, shatter_error* err, shatter_status& status) {
    Value v;
    if (!ParseJsonText(s, len, v, err, status)) return false;
    if (v.type() != json::Type::Object) {
        status = SetError(err, SHATTER_PARSE_ERROR, "stats: not an object");
        return false;
    }
    out.clear();
    for (const auto& m : v.Members()) {
        if (!m.second.IsNumber()) {
            status = SetError(err, SHATTER_PARSE_ERROR, "stats: value is not a number: " + m.first);
            return false;
        }
        out.emplace_back(m.first, m.second.AsDouble(0.0));
    }
    return true;
}

Value RogueStatsValue(const RogueStats& s) {
    Value o = Value::MakeObject();
    for (const auto& p : s) o.Set(p.first, Value(p.second));
    return o;
}

Value RogueNodeValue(const RogueNode& n) {
    Value o = Value::MakeObject();
    o.Set("id", Value(n.id));
    o.Set("kind", Value(n.kind));
    o.Set("room", Value(n.room));
    Value en = Value::MakeArray();
    for (const RogueEnemyCount& e : n.enemyList) {
        Value x = Value::MakeObject();
        x.Set("id", Value(e.enemy));
        x.Set("count", Value(e.count));
        en.Push(std::move(x));
    }
    o.Set("enemies", std::move(en));
    o.Set("enemy_total", Value(n.enemyTotal));
    return o;
}

Value RoguePathsValue(const std::vector<RogueNode>& paths) {
    Value a = Value::MakeArray();
    for (const RogueNode& n : paths) a.Push(RogueNodeValue(n));
    return a;
}

Value RogueQtyList(const std::vector<std::pair<ContentId, std::int64_t>>& list) {
    Value a = Value::MakeArray();
    for (const auto& m : list) {
        Value x = Value::MakeObject();
        x.Set("id", Value(m.first));
        x.Set("qty", Value(m.second));
        a.Push(std::move(x));
    }
    return a;
}

}  // namespace

extern "C" {

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_load_directory(const char* path, std::size_t path_len, shatter_rogue** out,
                                                                   shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (out == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "out is null");
    *out = nullptr;
    std::string_view p;
    if (!RogueId(path, path_len, p) || p.empty()) return SetError(err, SHATTER_INVALID_ARGUMENT, "path is null, empty or not valid UTF-8");
    std::unique_ptr<shatter_rogue> box(new (std::nothrow) shatter_rogue());
    if (!box) return SetError(err, SHATTER_INTERNAL, "out of memory");
    if (box->data.LoadDirectory(std::string(p))) box->data.Finalize();
    const auto& errs = box->data.Errors();
    if (!errs.empty()) {
        const ContentError& first = errs.front();
        return SetError(err, StartsWith(first.message, "E_IO") ? SHATTER_IO_ERROR : SHATTER_CONTENT_INVALID,
                        first.table + ": " + first.message + " (+" + std::to_string(errs.size() - 1) + " more)", first.line);
    }
    box->state = RogueState(box->data);
    box->waves = RogueWaves(box->data);
    *out = box.release();
    return SHATTER_OK;
}

SHATTER_API void SHATTER_CALL shatter_rogue_destroy(shatter_rogue* rogue) SHATTER_NOEXCEPT { delete rogue; }

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_setting(const shatter_rogue* rogue, const char* key, std::size_t key_len,
                                                            double* out) SHATTER_NOEXCEPT {
    std::string_view k;
    if (rogue == nullptr || out == nullptr || !RogueId(key, key_len, k)) return SHATTER_INVALID_ARGUMENT;
    return rogue->data.Setting(k, *out) ? SHATTER_OK : SHATTER_NOT_FOUND;
}

// --- Save do meta ---
SHATTER_API shatter_status SHATTER_CALL shatter_rogue_save_path_set(shatter_rogue* rogue, const char* path,
                                                                  std::size_t path_len) SHATTER_NOEXCEPT {
    std::string_view p;
    if (rogue == nullptr || !Text(path, path_len, p)) return SHATTER_INVALID_ARGUMENT;
    rogue->savePath = std::string(p);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_meta_load(shatter_rogue* rogue, std::int32_t* result) SHATTER_NOEXCEPT {
    if (rogue == nullptr || result == nullptr || rogue->savePath.empty()) return SHATTER_INVALID_ARGUMENT;
    std::unique_ptr<IFileIO> io = MakeStdFileIO();
    *result = static_cast<std::int32_t>(ReadRogueMetaFile(*io, rogue->savePath, rogue->state));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_meta_save(const shatter_rogue* rogue, shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (rogue == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "rogue is null");
    if (rogue->savePath.empty()) return SetError(err, SHATTER_INVALID_ARGUMENT, "no save path");
    return RogueAutoSave(rogue, err);
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_meta_save_json(const shatter_rogue* rogue, std::uint8_t* out, std::size_t cap,
                                                                   std::size_t* needed) SHATTER_NOEXCEPT {
    if (rogue == nullptr || needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    return WriteOut(rogue->state.MetaToJson(), out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_meta_load_json(shatter_rogue* rogue, const char* json_text, std::size_t len,
                                                                   std::int32_t* result) SHATTER_NOEXCEPT {
    std::string_view t;
    if (rogue == nullptr || result == nullptr || !RogueId(json_text, len, t)) return SHATTER_INVALID_ARGUMENT;
    *result = static_cast<std::int32_t>(rogue->state.MetaFromJson(t));
    return SHATTER_OK;
}

// --- Meta ---
SHATTER_API shatter_status SHATTER_CALL shatter_rogue_meta_buy(shatter_rogue* rogue, const char* id, std::size_t id_len,
                                                             std::int32_t* result) SHATTER_NOEXCEPT {
    std::string_view s;
    if (rogue == nullptr || result == nullptr || !RogueId(id, id_len, s)) return SHATTER_INVALID_ARGUMENT;
    const RogueMetaResult r = rogue->state.Buy(s);
    *result = static_cast<std::int32_t>(r);
    return r == RogueMetaResult::Ok ? RogueAutoSave(rogue) : SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_meta_can_buy(const shatter_rogue* rogue, const char* id, std::size_t id_len,
                                                                 std::int32_t* result) SHATTER_NOEXCEPT {
    std::string_view s;
    if (rogue == nullptr || result == nullptr || !RogueId(id, id_len, s)) return SHATTER_INVALID_ARGUMENT;
    *result = static_cast<std::int32_t>(rogue->state.CheckBuy(s));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_meta_craft(shatter_rogue* rogue, const char* id, std::size_t id_len,
                                                               std::int32_t* result) SHATTER_NOEXCEPT {
    std::string_view s;
    if (rogue == nullptr || result == nullptr || !RogueId(id, id_len, s)) return SHATTER_INVALID_ARGUMENT;
    const RogueMetaResult r = rogue->state.Craft(s);
    *result = static_cast<std::int32_t>(r);
    return r == RogueMetaResult::Ok ? RogueAutoSave(rogue) : SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_meta_can_craft(const shatter_rogue* rogue, const char* id, std::size_t id_len,
                                                                   std::int32_t* result) SHATTER_NOEXCEPT {
    std::string_view s;
    if (rogue == nullptr || result == nullptr || !RogueId(id, id_len, s)) return SHATTER_INVALID_ARGUMENT;
    *result = static_cast<std::int32_t>(rogue->state.CheckCraft(s));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_meta_equip(shatter_rogue* rogue, const char* id, std::size_t id_len,
                                                               std::int32_t* result) SHATTER_NOEXCEPT {
    std::string_view s;
    if (rogue == nullptr || result == nullptr || !RogueId(id, id_len, s)) return SHATTER_INVALID_ARGUMENT;
    const RogueMetaResult r = rogue->state.Equip(s);
    *result = static_cast<std::int32_t>(r);
    return r == RogueMetaResult::Ok ? RogueAutoSave(rogue) : SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_meta_prepare_run(shatter_rogue* rogue) SHATTER_NOEXCEPT {
    if (rogue == nullptr) return SHATTER_INVALID_ARGUMENT;
    rogue->state.PrepareRun();
    return RogueAutoSave(rogue);
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_meta_credit(shatter_rogue* rogue, const char* gains_json, std::size_t len,
                                                                shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (rogue == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "rogue is null");
    Value v;
    shatter_status st = SHATTER_OK;
    if (!ParseJsonText(gains_json, len, v, err, st)) return st;
    if (v.type() != json::Type::Object) return SetError(err, SHATTER_PARSE_ERROR, "gains: not an object");
    std::int64_t fragments = 0;
    if (const Value* f = v.Find("fragmentos")) {
        fragments = f->IsNumber() ? f->AsInt(-1) : -1;
        if (fragments < 0) return SetError(err, SHATTER_PARSE_ERROR, "gains: fragmentos must be a non-negative integer");
    }
    std::vector<std::pair<ContentId, std::int64_t>> mats;
    if (const Value* m = v.Find("materiais")) {
        if (m->type() != json::Type::Object) return SetError(err, SHATTER_PARSE_ERROR, "gains: materiais is not an object");
        for (const auto& kv : m->Members()) {
            const std::int64_t q = kv.second.IsNumber() ? kv.second.AsInt(-1) : -1;
            if (q < 0) return SetError(err, SHATTER_PARSE_ERROR, "gains: material quantity must be a non-negative integer");
            if (rogue->data.FindMaterial(kv.first) < 0) return SetError(err, SHATTER_NOT_FOUND, "gains: unknown material " + kv.first);
            mats.emplace_back(kv.first, q);
        }
    }
    if (!rogue->state.Credit(fragments, mats)) return SetError(err, SHATTER_INTERNAL, "gains: credit refused");
    return RogueAutoSave(rogue, err);
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_meta_fragments(const shatter_rogue* rogue, std::int64_t* out) SHATTER_NOEXCEPT {
    if (rogue == nullptr || out == nullptr) return SHATTER_INVALID_ARGUMENT;
    *out = rogue->state.Fragments();
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_meta_material(const shatter_rogue* rogue, const char* id, std::size_t id_len,
                                                                  std::int64_t* out) SHATTER_NOEXCEPT {
    std::string_view s;
    if (rogue == nullptr || out == nullptr || !RogueId(id, id_len, s)) return SHATTER_INVALID_ARGUMENT;
    if (rogue->data.FindMaterial(s) < 0) return SHATTER_NOT_FOUND;
    *out = rogue->state.Material(s);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_meta_level(const shatter_rogue* rogue, const char* id, std::size_t id_len,
                                                               std::int32_t* out) SHATTER_NOEXCEPT {
    std::string_view s;
    if (rogue == nullptr || out == nullptr || !RogueId(id, id_len, s)) return SHATTER_INVALID_ARGUMENT;
    if (rogue->data.FindMetaDef(s) < 0) return SHATTER_NOT_FOUND;
    *out = rogue->state.Level(s);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_meta_stock(const shatter_rogue* rogue, const char* id, std::size_t id_len,
                                                               std::int32_t* out) SHATTER_NOEXCEPT {
    std::string_view s;
    if (rogue == nullptr || out == nullptr || !RogueId(id, id_len, s)) return SHATTER_INVALID_ARGUMENT;
    const int k = rogue->data.FindRecipe(s);
    if (k < 0) return SHATTER_NOT_FOUND;
    *out = rogue->data.Recipes()[static_cast<std::size_t>(k)].amulet ? (rogue->state.Owns(s) ? 1 : 0) : rogue->state.Stock(s);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_meta_owns(const shatter_rogue* rogue, const char* id, std::size_t id_len,
                                                              std::uint8_t* out) SHATTER_NOEXCEPT {
    std::string_view s;
    if (rogue == nullptr || out == nullptr || !RogueId(id, id_len, s)) return SHATTER_INVALID_ARGUMENT;
    if (rogue->data.FindRecipe(s) < 0) return SHATTER_NOT_FOUND;
    *out = rogue->state.Owns(s) ? 1 : 0;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_skill_unlocked(const shatter_rogue* rogue, const char* upgrade_id,
                                                                   std::size_t upgrade_id_len, std::uint8_t* out) SHATTER_NOEXCEPT {
    std::string_view s;
    if (rogue == nullptr || out == nullptr || !RogueId(upgrade_id, upgrade_id_len, s)) return SHATTER_INVALID_ARGUMENT;
    if (rogue->data.FindUpgrade(s) < 0) return SHATTER_NOT_FOUND;
    *out = rogue->state.Unlocked(s) ? 1 : 0;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_meta_json(const shatter_rogue* rogue, std::uint8_t* out, std::size_t cap,
                                                              std::size_t* needed) SHATTER_NOEXCEPT {
    if (rogue == nullptr || needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    const RogueData& d = rogue->data;
    const RogueState& s = rogue->state;
    Value o = Value::MakeObject();
    o.Set("fragments", Value(s.Fragments()));
    Value mats = Value::MakeArray();
    for (const ContentId& m : d.Materials()) {
        Value x = Value::MakeObject();
        x.Set("id", Value(m));
        x.Set("qty", Value(s.Material(m)));
        mats.Push(std::move(x));
    }
    o.Set("materials", std::move(mats));
    o.Set("equipped", Value(s.Equipped()));
    Value ups = Value::MakeArray();
    for (const RogueMetaDef& m : d.MetaDefs()) {
        Value x = Value::MakeObject();
        x.Set("id", Value(m.id));
        x.Set("kind", Value(m.ability ? "ability" : "stat"));
        x.Set("target", Value(m.target));
        x.Set("stat", Value(m.stat));
        x.Set("mode", Value(RogueModeName(m.mode)));
        x.Set("value", Value(m.value));
        x.Set("cost", Value(m.cost));
        x.Set("level", Value(s.Level(m.id)));
        x.Set("max_level", Value(m.maxLevel));
        x.Set("can_buy", Value(static_cast<int>(s.CheckBuy(m.id))));
        ups.Push(std::move(x));
    }
    o.Set("upgrades", std::move(ups));
    Value recs = Value::MakeArray();
    for (const RogueRecipe& r : d.Recipes()) {
        Value x = Value::MakeObject();
        x.Set("id", Value(r.id));
        x.Set("kind", Value(r.amulet ? "amulet" : "consumable"));
        x.Set("stat", Value(r.stat));
        x.Set("mode", Value(RogueModeName(r.mode)));
        x.Set("value", Value(r.value));
        x.Set("cost", RogueQtyList(r.materials));
        x.Set("fragments", Value(r.fragments));
        x.Set("max_stock", Value(r.maxStock));
        x.Set("owned", Value(s.Owns(r.id)));
        x.Set("stock", Value(s.Stock(r.id)));
        x.Set("active", Value(s.Active(r.id)));
        x.Set("equipped", Value(s.Equipped() == r.id));
        x.Set("can_craft", Value(static_cast<int>(s.CheckCraft(r.id))));
        recs.Push(std::move(x));
    }
    o.Set("recipes", std::move(recs));
    return WriteJson(o, false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_drop_json(const shatter_rogue* rogue, const char* enemy_id,
                                                              std::size_t enemy_id_len, std::uint8_t* out, std::size_t cap,
                                                              std::size_t* needed) SHATTER_NOEXCEPT {
    std::string_view s;
    if (rogue == nullptr || needed == nullptr || !RogueId(enemy_id, enemy_id_len, s)) return SHATTER_INVALID_ARGUMENT;
    Value o = Value::MakeObject();
    if (const RogueDrop* d = rogue->data.FindDrop(s)) {
        o.Set("enemy", Value(d->enemy));
        o.Set("fragments", Value(d->fragments));
        o.Set("material", Value(d->material));
        o.Set("material_qty", Value(d->materialQty));
    }
    return WriteJson(o, false, out, cap, needed);
}

// --- Stats ---
SHATTER_API shatter_status SHATTER_CALL shatter_rogue_stats_apply(const shatter_rogue* rogue, const char* base_json, std::size_t len,
                                                                std::uint8_t include_run, std::uint8_t* out, std::size_t cap,
                                                                std::size_t* needed, shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (rogue == nullptr || needed == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "rogue or needed is null");
    RogueStats base;
    shatter_status st = SHATTER_OK;
    if (!RogueParseStats(base_json, len, base, err, st)) return st;
    RogueStats s = rogue->state.ApplyMeta(base);
    if (include_run != 0 && rogue->state.Phase() != RoguePhase::None) s = rogue->state.ApplyRunUpgrades(s);
    if (include_run != 0) s = rogue->state.ApplySkillPassives(s);
    return WriteJson(RogueStatsValue(s), false, out, cap, needed);
}

// --- Corrida ---
SHATTER_API shatter_status SHATTER_CALL shatter_rogue_run_start(shatter_rogue* rogue, std::uint64_t seed, const char* base_json,
                                                              std::size_t len, shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (rogue == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "rogue is null");
    RogueStats base;
    shatter_status st = SHATTER_OK;
    if (!RogueParseStats(base_json, len, base, err, st)) return st;
    const bool credited = rogue->state.StartRun(seed, base);
    return credited ? RogueAutoSave(rogue, err) : SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_run_phase(const shatter_rogue* rogue, std::int32_t* out) SHATTER_NOEXCEPT {
    if (rogue == nullptr || out == nullptr) return SHATTER_INVALID_ARGUMENT;
    *out = static_cast<std::int32_t>(rogue->state.Phase());
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_run_paths_json(const shatter_rogue* rogue, std::uint32_t stage, std::uint8_t* out,
                                                                   std::size_t cap, std::size_t* needed) SHATTER_NOEXCEPT {
    if (rogue == nullptr || needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    if (stage >= rogue->data.Stages().size()) return SHATTER_NOT_FOUND;
    return WriteJson(RoguePathsValue(rogue->data.Paths(static_cast<int>(stage))), false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_run_external_cards_set(shatter_rogue* rogue, std::uint8_t on,
                                                                          std::int32_t* result) SHATTER_NOEXCEPT {
    if (rogue == nullptr || result == nullptr) return SHATTER_INVALID_ARGUMENT;
    *result = static_cast<std::int32_t>(rogue->state.SetExternalCards(on != 0));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_run_external_cards_get(const shatter_rogue* rogue,
                                                                          std::uint8_t* out) SHATTER_NOEXCEPT {
    if (rogue == nullptr || out == nullptr) return SHATTER_INVALID_ARGUMENT;
    *out = rogue->state.ExternalCards() ? 1 : 0;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_run_enemy_killed(shatter_rogue* rogue, const char* enemy_id,
                                                                     std::size_t enemy_id_len, std::uint8_t* room_cleared,
                                                                     std::int32_t* result) SHATTER_NOEXCEPT {
    std::string_view s;
    if (rogue == nullptr || room_cleared == nullptr || result == nullptr || !RogueId(enemy_id, enemy_id_len, s))
        return SHATTER_INVALID_ARGUMENT;
    RogueKill k;
    *result = static_cast<std::int32_t>(rogue->state.EnemyKilled(s, &k));
    *room_cleared = k.roomCleared ? 1 : 0;
    return k.skillPoints > 0 ? RogueAutoSave(rogue) : SHATTER_OK;  // pontos de habilidade são do meta (API 1.10)
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_run_choose_card(shatter_rogue* rogue, const char* upgrade_id,
                                                                    std::size_t upgrade_id_len, double hp, double* hp_out,
                                                                    std::int32_t* result) SHATTER_NOEXCEPT {
    std::string_view s;
    if (rogue == nullptr || hp_out == nullptr || result == nullptr || !RogueId(upgrade_id, upgrade_id_len, s))
        return SHATTER_INVALID_ARGUMENT;
    *result = static_cast<std::int32_t>(rogue->state.ChooseCard(s, hp, hp_out));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_run_rest(shatter_rogue* rogue, double hp, double* hp_out,
                                                             std::int32_t* result) SHATTER_NOEXCEPT {
    if (rogue == nullptr || hp_out == nullptr || result == nullptr) return SHATTER_INVALID_ARGUMENT;
    *result = static_cast<std::int32_t>(rogue->state.Rest(hp, hp_out));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_run_door(shatter_rogue* rogue, std::int32_t* result) SHATTER_NOEXCEPT {
    if (rogue == nullptr || result == nullptr) return SHATTER_INVALID_ARGUMENT;
    *result = static_cast<std::int32_t>(rogue->state.UseDoor());
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_run_choose_path(shatter_rogue* rogue, std::uint32_t path_index,
                                                                    std::int32_t* result) SHATTER_NOEXCEPT {
    if (rogue == nullptr || result == nullptr) return SHATTER_INVALID_ARGUMENT;
    const int idx = path_index > 1000000u ? -1 : static_cast<int>(path_index);
    *result = static_cast<std::int32_t>(rogue->state.ChoosePath(idx));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_run_player_died(shatter_rogue* rogue, std::int32_t* result) SHATTER_NOEXCEPT {
    if (rogue == nullptr || result == nullptr) return SHATTER_INVALID_ARGUMENT;
    *result = static_cast<std::int32_t>(rogue->state.PlayerDied());
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_run_finish(shatter_rogue* rogue, std::int32_t* result) SHATTER_NOEXCEPT {
    if (rogue == nullptr || result == nullptr) return SHATTER_INVALID_ARGUMENT;
    const bool hadGains = rogue->state.GainFragments() != 0 || !rogue->state.GainMaterials().empty();
    const bool ok = rogue->state.FinishRun();
    *result = static_cast<std::int32_t>(ok ? RogueRunResult::Ok : RogueRunResult::WrongPhase);
    return ok && hadGains ? RogueAutoSave(rogue) : SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_run_json(const shatter_rogue* rogue, std::uint8_t* out, std::size_t cap,
                                                             std::size_t* needed) SHATTER_NOEXCEPT {
    if (rogue == nullptr || needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    const RogueState& s = rogue->state;
    Value o = Value::MakeObject();
    o.Set("phase", Value(RoguePhaseName(s.Phase())));
    o.Set("stage", Value(s.Stage()));
    o.Set("stages_total", Value(s.StagesTotal()));
    const RogueNode* node = s.CurrentNode();
    o.Set("node", node != nullptr ? RogueNodeValue(*node) : Value());
    o.Set("alive", Value(s.Alive()));
    o.Set("rest_pending", Value(s.RestPending()));
    Value offer = Value::MakeArray();
    for (const ContentId& id : s.Offer()) offer.Push(Value(id));
    o.Set("offer", std::move(offer));
    Value ups = Value::MakeArray();
    for (const RogueUpgrade& u : rogue->data.Upgrades()) {
        Value x = Value::MakeObject();
        x.Set("id", Value(u.id));
        x.Set("stat", Value(u.stat));
        x.Set("mode", Value(RogueModeName(u.mode)));
        x.Set("value", Value(u.value));
        x.Set("level", Value(s.RunLevel(u.id)));
        x.Set("max_level", Value(u.maxLevel));
        x.Set("unlocked", Value(s.Unlocked(u.id)));
        ups.Push(std::move(x));
    }
    o.Set("upgrades", std::move(ups));
    if (s.Phase() == RoguePhase::Route) o.Set("route_options", RoguePathsValue(rogue->data.Paths(s.Stage())));
    Value gains = Value::MakeObject();
    gains.Set("fragments", Value(s.GainFragments()));
    gains.Set("materials", RogueQtyList(s.GainMaterials()));
    o.Set("gains", std::move(gains));
    o.Set("external_cards", Value(s.ExternalCards()));
    return WriteJson(o, false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_run_stats_json(const shatter_rogue* rogue, std::uint8_t* out, std::size_t cap,
                                                                   std::size_t* needed) SHATTER_NOEXCEPT {
    if (rogue == nullptr || needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    const RogueStats s = rogue->state.Phase() == RoguePhase::None ? RogueStats() : rogue->state.RunStats();
    return WriteJson(RogueStatsValue(s), false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_run_summary_json(const shatter_rogue* rogue, std::uint8_t* out, std::size_t cap,
                                                                     std::size_t* needed) SHATTER_NOEXCEPT {
    if (rogue == nullptr || needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    const RogueSummary sum = rogue->state.Summary();
    Value o = Value::MakeObject();
    o.Set("victory", Value(sum.victory));
    o.Set("stage_reached", Value(sum.stageReached));
    o.Set("stages_total", Value(sum.stagesTotal));
    o.Set("upgrades_total", Value(sum.upgradesTotal));
    o.Set("fragments", Value(sum.fragments));
    o.Set("materials", RogueQtyList(sum.materials));
    return WriteJson(o, false, out, cap, needed);
}

// --- Estado completo ---
SHATTER_API shatter_status SHATTER_CALL shatter_rogue_state_json(const shatter_rogue* rogue, std::uint8_t* out, std::size_t cap,
                                                               std::size_t* needed) SHATTER_NOEXCEPT {
    if (rogue == nullptr || needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    return WriteOut(rogue->state.StateJson(), out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_state_restore(shatter_rogue* rogue, const char* json_text, std::size_t len,
                                                                  shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    std::string_view t;
    if (rogue == nullptr || !RogueId(json_text, len, t)) return SetError(err, SHATTER_INVALID_ARGUMENT, "rogue or json is null");
    std::string msg;
    if (!rogue->state.RestoreState(t, &msg)) return SetError(err, SHATTER_PARSE_ERROR, "rogue state: " + msg);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_state_hash(const shatter_rogue* rogue, std::uint8_t* out, std::size_t cap,
                                                               std::size_t* needed) SHATTER_NOEXCEPT {
    if (rogue == nullptr || needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    return WriteOut(rogue->state.StateHash(), out, cap, needed);
}


// --- Habilidades por classe (API 1.10) ---
SHATTER_API shatter_status SHATTER_CALL shatter_rogue_class_set(shatter_rogue* rogue, const char* class_id, std::size_t class_id_len,
                                                              std::int32_t* result) SHATTER_NOEXCEPT {
    std::string_view s;
    if (rogue == nullptr || result == nullptr || !RogueId(class_id, class_id_len, s)) return SHATTER_INVALID_ARGUMENT;
    const RogueSkillResult r = rogue->state.SetClass(s);
    *result = static_cast<std::int32_t>(r);
    return r == RogueSkillResult::Ok ? RogueAutoSave(rogue) : SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_skills_json(const shatter_rogue* rogue, std::uint8_t* out, std::size_t cap,
                                                                std::size_t* needed) SHATTER_NOEXCEPT {
    if (rogue == nullptr || needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    const RogueState& st = rogue->state;
    Value o = Value::MakeObject();
    o.Set("class", Value(st.ClassId()));
    Value classes = Value::MakeArray();
    for (const RogueClass& c : rogue->data.Classes()) classes.Push(Value(c.id));
    o.Set("classes", std::move(classes));
    o.Set("points", Value(st.SkillPoints()));
    Value slots = Value::MakeArray();
    for (int k = 0; k < kRogueSkillSlots; ++k) slots.Push(Value(st.SkillSlot(k)));
    o.Set("slots", std::move(slots));
    Value skills = Value::MakeArray();
    if (st.ClassIndex() >= 0) {
        for (const RogueSkillDef& d : rogue->data.Classes()[static_cast<std::size_t>(st.ClassIndex())].skills) {
            Value x = Value::MakeObject();
            x.Set("id", Value(d.id));
            x.Set("active", Value(d.active));
            x.Set("parent", Value(d.parent));
            x.Set("level", Value(st.SkillLevel(d.id)));
            x.Set("max_level", Value(d.maxLevel));
            x.Set("points", Value(d.points));
            x.Set("can_learn", Value(static_cast<int>(st.CheckLearn(d.id))));
            x.Set("cooldown", Value(st.SkillCooldownLeft(d.id)));
            skills.Push(std::move(x));
        }
    }
    o.Set("skills", std::move(skills));
    return WriteJson(o, false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_skill_def_json(const shatter_rogue* rogue, const char* skill_id,
                                                                   std::size_t skill_id_len, std::int32_t level, std::uint8_t* out,
                                                                   std::size_t cap, std::size_t* needed) SHATTER_NOEXCEPT {
    std::string_view s;
    if (rogue == nullptr || needed == nullptr || !RogueId(skill_id, skill_id_len, s)) return SHATTER_INVALID_ARGUMENT;
    RogueSkillLevelDef d;
    if (!rogue->state.SkillDefAt(s, level < 0 ? -1 : level, d)) return SHATTER_NOT_FOUND;
    Value o = Value::MakeObject();
    for (const auto& t : d.texts) o.Set(t.first, Value(t.second));
    for (const auto& n : d.numbers) o.Set(n.first, Value(n.second));
    o.Set("nivel", Value(d.level));
    return WriteJson(o, false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_skill_can_learn(const shatter_rogue* rogue, const char* skill_id,
                                                                    std::size_t skill_id_len, std::int32_t* result) SHATTER_NOEXCEPT {
    std::string_view s;
    if (rogue == nullptr || result == nullptr || !RogueId(skill_id, skill_id_len, s)) return SHATTER_INVALID_ARGUMENT;
    *result = static_cast<std::int32_t>(rogue->state.CheckLearn(s));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_skill_learn(shatter_rogue* rogue, const char* skill_id, std::size_t skill_id_len,
                                                                std::int32_t* result) SHATTER_NOEXCEPT {
    std::string_view s;
    if (rogue == nullptr || result == nullptr || !RogueId(skill_id, skill_id_len, s)) return SHATTER_INVALID_ARGUMENT;
    const RogueSkillResult r = rogue->state.Learn(s);
    *result = static_cast<std::int32_t>(r);
    return r == RogueSkillResult::Ok ? RogueAutoSave(rogue) : SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_skill_equip(shatter_rogue* rogue, std::uint32_t slot, const char* skill_id,
                                                                std::size_t skill_id_len, std::int32_t* result) SHATTER_NOEXCEPT {
    std::string_view s;
    if (rogue == nullptr || result == nullptr || !Text(skill_id, skill_id_len, s)) return SHATTER_INVALID_ARGUMENT;
    const int k = slot > 1000u ? -1 : static_cast<int>(slot);
    const RogueSkillResult r = rogue->state.EquipSkill(k, s);
    *result = static_cast<std::int32_t>(r);
    return r == RogueSkillResult::Ok ? RogueAutoSave(rogue) : SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_skill_respec(shatter_rogue* rogue, std::int32_t* result) SHATTER_NOEXCEPT {
    if (rogue == nullptr || result == nullptr) return SHATTER_INVALID_ARGUMENT;
    const RogueSkillResult r = rogue->state.Respec();
    *result = static_cast<std::int32_t>(r);
    return r == RogueSkillResult::Ok ? RogueAutoSave(rogue) : SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_skill_points_add(shatter_rogue* rogue, std::int64_t points,
                                                                     std::int32_t* result) SHATTER_NOEXCEPT {
    if (rogue == nullptr || result == nullptr) return SHATTER_INVALID_ARGUMENT;
    const RogueSkillResult r = rogue->state.AddSkillPoints(points);
    *result = static_cast<std::int32_t>(r);
    return r == RogueSkillResult::Ok && points > 0 ? RogueAutoSave(rogue) : SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_skill_tick(shatter_rogue* rogue, double dt) SHATTER_NOEXCEPT {
    if (rogue == nullptr) return SHATTER_INVALID_ARGUMENT;
    rogue->state.TickSkills(dt);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_skill_can_use(const shatter_rogue* rogue, std::uint32_t slot, double mana,
                                                                  std::int32_t* result) SHATTER_NOEXCEPT {
    if (rogue == nullptr || result == nullptr) return SHATTER_INVALID_ARGUMENT;
    *result = static_cast<std::int32_t>(rogue->state.CheckUse(slot > 1000u ? -1 : static_cast<int>(slot), mana));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_skill_commit_use(shatter_rogue* rogue, std::uint32_t slot, double mana,
                                                                     double* cost_out, std::int32_t* result) SHATTER_NOEXCEPT {
    if (rogue == nullptr || cost_out == nullptr || result == nullptr) return SHATTER_INVALID_ARGUMENT;
    *result = static_cast<std::int32_t>(rogue->state.CommitUse(slot > 1000u ? -1 : static_cast<int>(slot), mana, cost_out));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_skill_passives_apply(const shatter_rogue* rogue, const char* base_json,
                                                                         std::size_t len, std::uint8_t* out, std::size_t cap,
                                                                         std::size_t* needed, shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    if (rogue == nullptr || needed == nullptr) return SetError(err, SHATTER_INVALID_ARGUMENT, "rogue or needed is null");
    RogueStats base;
    shatter_status st = SHATTER_OK;
    if (!RogueParseStats(base_json, len, base, err, st)) return st;
    return WriteJson(RogueStatsValue(rogue->state.ApplySkillPassives(base)), false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_skill_cooldown(const shatter_rogue* rogue, std::uint32_t slot,
                                                                   double* fraction_out) SHATTER_NOEXCEPT {
    if (rogue == nullptr || fraction_out == nullptr) return SHATTER_INVALID_ARGUMENT;
    *fraction_out = rogue->state.SlotCooldownFraction(slot > 1000u ? -1 : static_cast<int>(slot));
    return SHATTER_OK;
}

}  // extern "C"

// --- Spawner de hordas (API 1.11) ---
namespace {

Value RogueSpawnValue(const RogueWaveSpawn& w) {
    Value o = Value::MakeObject();
    o.Set("id", Value(w.id));
    o.Set("enemy", Value(w.enemy));
    o.Set("elite", Value(w.elite));
    o.Set("boss", Value(w.boss));
    o.Set("wave", Value(w.wave));
    o.Set("edge", Value(w.edge));
    o.Set("pos", Value(w.pos));
    o.Set("hp_mult", Value(w.hpMult));
    o.Set("damage_mult", Value(w.damageMult));
    return o;
}

double RogueUsToSeconds(std::int64_t us) { return static_cast<double>(us) / 1000000.0; }

}  // namespace

extern "C" {

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_wave_start(shatter_rogue* rogue, const char* phase_id, std::size_t phase_id_len,
                                                               std::uint64_t seed, std::int32_t* result) SHATTER_NOEXCEPT {
    std::string_view p;
    if (rogue == nullptr || result == nullptr || !RogueId(phase_id, phase_id_len, p)) return SHATTER_INVALID_ARGUMENT;
    *result = static_cast<std::int32_t>(rogue->waves.Start(p, seed));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_wave_stop(shatter_rogue* rogue) SHATTER_NOEXCEPT {
    if (rogue == nullptr) return SHATTER_INVALID_ARGUMENT;
    rogue->waves.Stop();
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_wave_tick(shatter_rogue* rogue, double dt, std::uint32_t* spawned) SHATTER_NOEXCEPT {
    if (rogue == nullptr || spawned == nullptr) return SHATTER_INVALID_ARGUMENT;
    *spawned = static_cast<std::uint32_t>(rogue->waves.Tick(dt));
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_wave_take_json(shatter_rogue* rogue, std::uint8_t* out, std::size_t cap,
                                                                   std::size_t* needed) SHATTER_NOEXCEPT {
    if (rogue == nullptr || needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    Value a = Value::MakeArray();
    for (const RogueWaveSpawn& w : rogue->waves.Pending()) a.Push(RogueSpawnValue(w));
    const shatter_status st = WriteJson(a, false, out, cap, needed);
    if (st == SHATTER_OK) rogue->waves.ClearPending();
    return st;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_wave_killed(shatter_rogue* rogue, std::uint32_t spawn_id, std::uint8_t* complete,
                                                                std::int32_t* result) SHATTER_NOEXCEPT {
    if (rogue == nullptr || complete == nullptr || result == nullptr) return SHATTER_INVALID_ARGUMENT;
    *result = static_cast<std::int32_t>(rogue->waves.Killed(spawn_id));
    *complete = rogue->waves.Complete() ? 1 : 0;
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_wave_json(const shatter_rogue* rogue, std::uint8_t* out, std::size_t cap,
                                                              std::size_t* needed) SHATTER_NOEXCEPT {
    if (rogue == nullptr || needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    const RogueWaves& w = rogue->waves;
    const RogueWaveDef* d = w.CurrentDef();
    Value o = Value::MakeObject();
    o.Set("phase", Value(w.PhaseId()));
    o.Set("running", Value(w.Running()));
    o.Set("complete", Value(w.Complete()));
    o.Set("wave", Value(w.Wave()));
    o.Set("waves_total", Value(w.WavesTotal()));
    o.Set("time", Value(RogueUsToSeconds(w.TimeUs())));
    o.Set("wave_time", Value(RogueUsToSeconds(w.WaveTimeUs())));
    o.Set("wave_duration", Value(d != nullptr ? d->duration : 0.0));
    o.Set("budget", Value(d != nullptr ? d->budget : std::int64_t{0}));
    o.Set("budget_left", Value(w.BudgetLeft()));
    o.Set("exhausted", Value(w.Exhausted()));
    o.Set("alive", Value(w.Alive()));
    o.Set("cap", Value(d != nullptr ? d->cap : 0));
    o.Set("boss", Value(d != nullptr ? d->boss : std::string()));
    o.Set("boss_spawned", Value(w.BossSpawned()));
    o.Set("boss_alive", Value(w.BossAlive()));
    o.Set("spawned", Value(w.SpawnedTotal()));
    o.Set("killed", Value(w.KilledTotal()));
    o.Set("pending", Value(static_cast<std::int64_t>(w.Pending().size())));
    return WriteJson(o, false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_wave_defs_json(const shatter_rogue* rogue, std::uint8_t* out, std::size_t cap,
                                                                   std::size_t* needed) SHATTER_NOEXCEPT {
    if (rogue == nullptr || needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    Value phases = Value::MakeArray();
    for (const std::string& id : rogue->data.WavePhases()) {
        Value ph = Value::MakeObject();
        ph.Set("id", Value(id));
        Value waves = Value::MakeArray();
        for (const RogueWaveDef& d : rogue->data.Waves()) {
            if (d.phase != id) continue;
            Value x = Value::MakeObject();
            x.Set("wave", Value(d.wave));
            x.Set("duration", Value(d.duration));
            x.Set("interval", Value(d.interval));
            x.Set("batch", Value(d.batch));
            x.Set("budget", Value(d.budget));
            x.Set("cap", Value(d.cap));
            Value mix = Value::MakeArray();
            for (const RogueWaveMix& m : d.mix) {
                Value e = Value::MakeObject();
                e.Set("id", Value(m.enemy));
                e.Set("weight", Value(m.weight));
                e.Set("cost", Value(m.cost));
                mix.Push(std::move(e));
            }
            x.Set("enemies", std::move(mix));
            x.Set("elites", Value(d.elites));
            x.Set("elite_hp", Value(d.eliteHp));
            x.Set("elite_damage", Value(d.eliteDamage));
            x.Set("boss", Value(d.boss));
            waves.Push(std::move(x));
        }
        ph.Set("waves", std::move(waves));
        phases.Push(std::move(ph));
    }
    Value o = Value::MakeObject();
    o.Set("phases", std::move(phases));
    return WriteJson(o, false, out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_wave_state_json(const shatter_rogue* rogue, std::uint8_t* out, std::size_t cap,
                                                                    std::size_t* needed) SHATTER_NOEXCEPT {
    if (rogue == nullptr || needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    return WriteOut(rogue->waves.StateJson(), out, cap, needed);
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_wave_state_restore(shatter_rogue* rogue, const char* json_text, std::size_t len,
                                                                       shatter_error* err) SHATTER_NOEXCEPT {
    ClearError(err);
    std::string_view t;
    if (rogue == nullptr || !RogueId(json_text, len, t)) return SetError(err, SHATTER_INVALID_ARGUMENT, "rogue or json is null");
    std::string msg;
    if (!rogue->waves.RestoreState(t, &msg)) return SetError(err, SHATTER_PARSE_ERROR, "rogue wave state: " + msg);
    return SHATTER_OK;
}

SHATTER_API shatter_status SHATTER_CALL shatter_rogue_wave_state_hash(const shatter_rogue* rogue, std::uint8_t* out, std::size_t cap,
                                                                    std::size_t* needed) SHATTER_NOEXCEPT {
    if (rogue == nullptr || needed == nullptr) return SHATTER_INVALID_ARGUMENT;
    return WriteOut(rogue->waves.StateHash(), out, cap, needed);
}

}  // extern "C"
