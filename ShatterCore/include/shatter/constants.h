// ShatterCore — constantes de regra.
// Os valores padrão abaixo são os do plano (docs/00_plano_existente.md) e servem
// para os testes unitários. No jogo, TODOS vêm de Content/Data/rules.csv (colunas
// key,value) e sobrescrevem estes; o nome da chave no CSV está no comentário.
#pragma once

#include <array>

namespace shatter {

struct RulesConstants {
    // --- Combate (seção 10, "Ordem de cálculo de um golpe") ---
    double critMultiplierBase = 1.5;       // crit_multiplier_base
    double evasionCap = 0.70;              // evasion_cap
    double blockCap = 0.50;                // block_cap
    double blockMitigation = 1.0;          // block_mitigation: fração do golpe anulada no bloqueio (1 = anula). PROVISÓRIO, decidir em playtest
    double resistCap = 0.75;               // resist_cap
    double resistFloor = -1.0;             // resist_floor: resistência negativa mínima (-100%)
    double armorDamageFactor = 5.0;        // armor_damage_factor (k da fórmula de armadura, ver damage.h)
    double armorMaxReduction = 0.90;       // armor_max_reduction
    double triggerInternalCooldown = 0.25; // trigger_icd_min (s): recarga interna mínima de efeitos disparados
    double minCooldown = 0.1;              // cooldown_min (s)
    double fixedStep = 1.0 / 60.0;         // realtime_step (s): passo fixo do combate em tempo real

    // --- Idle (seção 7) ---
    double simStep = 0.1;                  // sim_step (s)
    double simStepFastNonBoss = 0.25;      // sim_step_fast (s): só se o orçamento de 2 s estourar (flag abaixo)
    bool   useFastStepNonBoss = false;     // sim_fast_enabled
    double maxOfflineHours = 12.0;         // max_offline_hours
    double maxExpeditionHours = 12.0;      // max_expedition_hours
    double minExpeditionHours = 1.0;       // min_expedition_hours
    int    maxAiRules = 6;                 // max_ai_rules
    int    maxRaresPerExpedition = 4;      // max_rares_per_expedition
    int    xpLevelCapAboveArea = 2;        // xp_cap_levels_above_area
    double aiBaseDodgeTelegraphed = 0.5;   // ai_base_dodge (fração de golpes telegrafados que a IA esquiva)
    double retreatLifeFraction = 0.25;     // retreat_life_fraction: recua se vida < 25% e sem poção de cura (docs/13, item 10)
    // Vigor: multiplicador de XP/ouro/materiais por faixa de hora da expedição.
    // vigor_h1_4, vigor_h5_8, vigor_h9_12
    std::array<double, 3> vigorByBand = {1.0, 0.7, 0.4};
    double vigorBandHours = 4.0;           // vigor_band_hours

    // --- Chaves de docs/13 e da rodada 2: OBRIGATÓRIAS em rules.csv (ausente = E_KEY_MISSING no Finalize). Os valores
    // abaixo são neutros (0): o número de balanceamento mora só no CSV (CLAUDE.md), nunca num padrão escondido. ---
    // Esquiva (item 1)
    int    dodgeMaxCharges = 0;            // dodge_max_charges
    double dodgeRecharge = 0.0;            // dodge_recharge (s por carga, em série)
    double dodgeDuration = 0.0;            // dodge_duration (s)
    double dodgeIframes = 0.0;             // dodge_iframes: invulnerável em [0, iframes)
    double dodgeDistance = 0.0;            // dodge_distance (uu)
    double dodgeCostResource = 0.0;        // dodge_cost_resource
    double dodgeBuffer = 0.0;              // dodge_buffer (s de buffer de entrada; o C# aplica)
    double dodgePerfectResource = 0.0;     // dodge_perfect_resource: recurso ao ser invulnerável no golpe
    double dodgeCancelRecoveryFraction = 0.0;    // dodge_cancel_recovery_fraction: a esquiva cancela a partir desta fração da recuperação
    double outOfCombatSeconds = 0.0;             // out_of_combat_seconds: sem dar nem levar golpe = fora de combate (RF-14)
    // Guarda Quebrada (item 3)
    double guardBreakStaggerSeconds = 0.0;       // guard_break_stagger_seconds
    double guardBreakStaggerDamageTaken = 0.0;   // guard_break_stagger_damage_taken (fração a mais de dano recebido)
    double guardBreakImmunityBoss = 0.0;         // guard_break_immunity_boss (s)
    double guardBreakImmunityOther = 0.0;        // guard_break_immunity_other (s)
    double bossShieldDownSeconds = 0.0;          // boss_shield_down_seconds
    // Elite sorteado (item 5)
    double eliteLifeMult = 0.0;            // elite_life_mult
    double eliteDamageMult = 0.0;          // elite_damage_mult
    double eliteXpMult = 0.0;              // elite_xp_mult
    // Poções (item 2)
    double potionLockout = 0.0;            // potion_lockout: trava global entre usos (s)
    // Rodada 2 (docs/13, R2): dano base físico da "arma" sem arma equipada; margem da área visível de R-VIS-1.
    double unarmedWeaponDamagePhysical = 0.0;  // unarmed_weapon_damage_physical
    double requireOnScreenMargin = 0.0;        // require_on_screen_margin (uu)

    // --- Fervor (jogo manual). O idle é a taxa base = 1. ---
    double fervorXpMult = 3.0;             // fervor_xp_mult
    double fervorGoldMatMult = 1.25;       // fervor_gold_mat_mult
    double fervorRareChanceMult = 2.0;     // fervor_rare_mult

    // --- Cargas do Marco ---
    int chargesMax = 12;                   // charges_max
    int chargesPerHour = 1;                // charges_per_hour
    int chargesClearArea = 1;              // charges_clear_area
    int chargesBoss = 2;                   // charges_boss
    int chargesNewArea = 3;                // charges_new_area
    int chargesDailyRest = 4;              // charges_daily_rest

    // --- Relógio (seção 10, "Relógio e tempo offline") ---
    double clockRollbackToleranceSec = 300.0;  // clock_rollback_tolerance_s (5 min)
    double steamClockMaxSkewSec = 600.0;       // steam_clock_max_skew_s (10 min)

    // --- Progressão ---
    // XP para o próximo nível = xpBase + xpScale × (nível − 1)^xpExponent
    double xpBase = 100.0;                 // xp_base
    double xpScale = 60.0;                 // xp_scale
    double xpExponent = 1.5;               // xp_exponent
    int    maxLevel = 30;                  // max_level
};

}  // namespace shatter
