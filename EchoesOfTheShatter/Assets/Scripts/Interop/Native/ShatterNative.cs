using System;
using System.Runtime.InteropServices;

namespace Echoes.Interop.Native
{
    /// <summary>
    /// P/Invoke para <c>shattercore.dll</c> (API C v1, shatter_c.h). Unica classe que declara
    /// <c>[DllImport]</c> (docs/04_arquitetura.md, secao 9.3). Assinaturas so com tipos blittable e
    /// ponteiros; sem string, bool ou array gerenciado; sem callbacks da DLL para o C#.
    /// Declara so o que o <see cref="NativeRulesCore"/> usa; o resto do header (save, expedicao, loot,
    /// relogio) entra quando a camada de save/idle precisar.
    /// </summary>
    internal static unsafe partial class ShatterNative
    {
        const string Lib = "shattercore";

        /// <summary><c>SHATTER_C_API_VERSION</c> para a qual este arquivo foi escrito.</summary>
        public const uint ExpectedApiVersion = 1u;

        // --- Versao e layout
        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern uint shatter_api_version();

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_layout_check(uint* values, nuint n, ShatterError* err);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_layout_info(uint* output, nuint cap, nuint* needed);

        // --- Conteudo
        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_db_load_directory(byte* path, nuint pathLen, IntPtr* output, ShatterError* err);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern void shatter_db_destroy(IntPtr db);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_db_errors_json(IntPtr db, byte* output, nuint cap, nuint* needed);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_db_content_version(IntPtr db, uint* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_db_rules(IntPtr db, ShatterRules* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_db_lookup_json(IntPtr db, byte* id, nuint idLen, byte* output, nuint cap, nuint* needed);

        // --- RNG
        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_rng_for_stream(ulong seed, uint stream, ulong index, ShatterRng* output);

        // --- Atributos
        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_statblock_create(IntPtr* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern void shatter_statblock_destroy(IntPtr sb);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_statblock_from_character_json(IntPtr db, byte* json, nuint len, IntPtr* output, ShatterError* err);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_statblock_for_enemy(IntPtr db, byte* enemyId, nuint enemyIdLen, int level, IntPtr* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_statblock_get(IntPtr sb, uint stat, uint contextTags, double* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_statblock_revision(IntPtr sb, ulong* output);

        // --- Golpe e recarga
        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_resolve_hit(IntPtr attacker, IntPtr defender, ShatterHitInput* input,
                                                     ShatterRules* rules, ShatterRng* rng, ShatterHitResult* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_effective_cooldown(double baseCooldown, double cooldownRecovery, ShatterRules* rules, double* output);

        // --- Efeitos
        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_effects_create(IntPtr* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern void shatter_effects_destroy(IntPtr fx);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_effects_apply(IntPtr fx, IntPtr db, byte* effectId, nuint effectIdLen,
                                                       byte* sourceEntity, nuint sourceLen, double magnitude,
                                                       uint triggeredBy, IntPtr target, byte* applied);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_effects_tick(IntPtr fx, IntPtr db, double dt, IntPtr target, nuint* eventCount);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_effects_events(IntPtr fx, ShatterEffectEvent* output, nuint cap, nuint* needed);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_effects_stack_count(IntPtr fx, byte* effectId, nuint effectIdLen, int* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_effects_clear(IntPtr fx, IntPtr target);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_effects_active_json(IntPtr fx, byte* output, nuint cap, nuint* needed);

        // =============================================================================================
        // API C 1.1 (minor 1)
        // =============================================================================================
        public const uint ExpectedApiMinor = 5u;

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern uint shatter_api_minor();

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_layout_check_ext(uint* values, nuint n, ShatterError* err);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_db_rules_ext(IntPtr db, ShatterRulesExt* output);

        // Rodada 2
        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_layout_check_ext2(uint* values, nuint n, ShatterError* err);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_db_rules_ext2(IntPtr db, ShatterRulesExt2* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_skill_base_damage(IntPtr db, byte* skillId, nuint skillIdLen, byte* weaponBaseId, nuint weaponBaseIdLen, double* output4);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_boss_wall_hit(IntPtr boss, IntPtr stats, byte* applied);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_resolve_hit_db(IntPtr db, IntPtr attacker, IntPtr defender, ShatterHitInput* input,
                                                        ShatterRng* rng, ShatterHitResult* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_effective_cooldown_db(IntPtr db, double baseCooldown, double cooldownRecovery, double* output);

        // --- Vida, recurso, tempos, velocidade, ataque
        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_vitals_create(IntPtr db, IntPtr stats, byte* classId, nuint classIdLen, ShatterVitals* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_vitals_tick(IntPtr db, ShatterVitals* vitals, IntPtr stats, byte* classId, nuint classIdLen,
                                                     double dt, byte inCombat);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_vitals_gain_resource(ShatterVitals* vitals, IntPtr stats, double amount);

        // API C 1.5 (combate basico, docs/09 secao 12)
        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_layout_check_ext5(uint* values, nuint n, ShatterError* err);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_db_combat_rules(IntPtr db, ShatterCombatRules* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_basic_kit_get(IntPtr db, byte* classId, nuint classIdLen, ShatterBasicKit* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_vitals_tick_ex(IntPtr db, ShatterVitals* vitals, IntPtr stats, byte* classId, nuint classIdLen,
                                                        double dt, byte inCombat, byte moving);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_vitals_gain_on_hit(IntPtr db, ShatterVitals* vitals, IntPtr stats, byte* classId, nuint classIdLen);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_vitals_gain_on_block(IntPtr db, ShatterVitals* vitals, IntPtr stats, byte* classId, nuint classIdLen);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_vitals_spend_resource(ShatterVitals* vitals, double amount, byte* ok);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_skill_timing(IntPtr db, byte* skillId, nuint skillIdLen, IntPtr stats,
                                                      byte* modifierId, nuint modifierIdLen, ShatterActionTiming* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_move_speed(IntPtr stats, double baseUuPerSec, double* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_can_act(IntPtr stats, IntPtr actor, byte* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_can_move(IntPtr stats, IntPtr actor, byte* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_pick_attack(IntPtr db, byte* enemyId, nuint enemyIdLen, ShatterRng* rng, int* output);

        // --- Pocoes
        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_potion_resolve(IntPtr db, byte* potionId, nuint potionIdLen, IntPtr stats,
                                                        ShatterVitals* vitals, ShatterPotionOutcome* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_potions_create(IntPtr db, IntPtr* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern void shatter_potions_destroy(IntPtr potions);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_potions_tick(IntPtr db, IntPtr potions, double dt);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_potions_use(IntPtr db, IntPtr potions, byte* potionId, nuint potionIdLen, IntPtr stats,
                                                     ShatterVitals* vitals, ShatterPotionOutcome* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_potions_refill(IntPtr db, IntPtr potions);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_potions_on_elite_killed(IntPtr db, IntPtr potions, byte* added);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_potions_info_json(IntPtr db, IntPtr potions, byte* output, nuint cap, nuint* needed);

        // --- Esquiva (estado POD do chamador)
        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_dodge_init(IntPtr db, ShatterDodgeState* state);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_dodge_tick(IntPtr db, ShatterDodgeState* state, double dt);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_dodge_start(IntPtr db, ShatterDodgeState* state, double resourceAvailable, int* status);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_dodge_invulnerable(IntPtr db, ShatterDodgeState* state, byte* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_dodge_perfect_reward(IntPtr db, ShatterDodgeState* state, double* output);

        // --- Stun e Guarda Quebrada (actor)
        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_actor_create(IntPtr db, byte* enemyId, nuint enemyIdLen, byte elite, IntPtr* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern void shatter_actor_destroy(IntPtr actor);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_actor_apply_effect(IntPtr actor, IntPtr db, byte* effectId, nuint effectIdLen,
                                                            byte* source, nuint sourceLen, double magnitude, IntPtr fx,
                                                            IntPtr target, ShatterActorApply* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_actor_tick(IntPtr actor, double dt, IntPtr target, byte* staggerEnded);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_actor_info_get(IntPtr actor, ShatterActorInfo* output);

        // API 1.3: fuga do inimigo decidida pelo core
        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_actor_flee_step(IntPtr actor, double dt, double life, double maxLife, byte hasTarget, byte dead, ShatterFleeResult* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_actor_flee_reset(IntPtr actor);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_layout_check_ext3(uint* values, nuint n, ShatterError* err);

        // --- Elite
        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_elite_roll(IntPtr db, ShatterRng* eventsRng, ShatterEliteInfo* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_elite_profile(IntPtr db, byte* modifierId, nuint modifierIdLen, byte rolled, ShatterEliteInfo* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_elite_apply(IntPtr db, ShatterEliteInfo* info, IntPtr stats, double* barrier);

        // --- Chefe
        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_boss_create(IntPtr db, byte* enemyId, nuint enemyIdLen, int level, ulong seed, IntPtr* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern void shatter_boss_destroy(IntPtr boss);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_boss_reset(IntPtr boss, IntPtr stats);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_boss_start(IntPtr boss);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_boss_step(IntPtr boss, double dt, ShatterBossContext* ctx, IntPtr stats, nuint* eventCount);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_boss_apply_damage(IntPtr boss, double amount, ShatterVec2 bossPos, ShatterVec2 origin, ShatterBossDamage* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_boss_apply_effect(IntPtr boss, IntPtr db, byte* effectId, nuint effectIdLen,
                                                           byte* source, nuint sourceLen, double magnitude, IntPtr fx,
                                                           IntPtr stats, ShatterActorApply* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_boss_events(IntPtr boss, ShatterBossEvent* output, nuint cap, nuint* needed);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_boss_info_get(IntPtr boss, ShatterBossInfo* output);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_boss_shield_covers(IntPtr boss, ShatterVec2 bossPos, ShatterVec2 origin, byte* output);
    }
}
