using System;
using System.Runtime.InteropServices;

namespace Echoes.Interop.Native
{
    // Core da Cripta: mundo, baus, encontros, XP, Fervor e tempo da arma (shatter_c.h API 1.7; docs/09 secao 14).

    [StructLayout(LayoutKind.Sequential)]
    internal struct ShatterXpInfo
    {
        public double awarded;
        public double xp_in_level;
        public double xp_to_next;
        public int level_before;
        public int level;
        public int level_cap;
        public int reserved;
    }

    [StructLayout(LayoutKind.Sequential)]
    internal struct ShatterFervorInfo
    {
        public double xp_mult, gold_mat_mult, rare_mult;
        public double xp_bonus, gold_mat_bonus, rare_bonus;
    }

    [StructLayout(LayoutKind.Sequential)]
    internal struct ShatterHeroMoveRules
    {
        public double accel_seconds, decel_seconds;
    }

    internal static unsafe partial class ShatterNative
    {
        [DllImport("shattercore", CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_db_hero_move_rules(IntPtr db, ShatterHeroMoveRules* output);

        [DllImport("shattercore", CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_layout_check_ext8(uint* values, nuint n, ShatterError* err);

        const string CryptLib = "shattercore";

        [DllImport(CryptLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_world_begin_visit(IntPtr db, IntPtr save, byte* mapId, nuint mapIdLen, ulong* visitSeed);

        [DllImport(CryptLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_world_object_get(IntPtr save, byte* mapId, nuint mapIdLen, byte* objectId, nuint objectIdLen, byte* opened);

        [DllImport(CryptLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_world_object_set(IntPtr save, byte* mapId, nuint mapIdLen, byte* objectId, nuint objectIdLen, byte opened);

        [DllImport(CryptLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_world_state_json(IntPtr save, byte* mapId, nuint mapIdLen, byte* output, nuint cap, nuint* needed);

        [DllImport(CryptLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_map_info_json(IntPtr db, byte* mapId, nuint mapIdLen, byte* output, nuint cap, nuint* needed);

        [DllImport(CryptLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_encounter_roll_json(IntPtr db, byte* encounterId, nuint encounterIdLen, ulong visitSeed, byte* output, nuint cap, nuint* needed);

        /// <summary>Igual a <see cref="shatter_encounter_roll_json"/> com pontos de elite extras (0..100) da Mancha.</summary>
        [DllImport(CryptLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_encounter_roll_json_ex(IntPtr db, byte* encounterId, nuint encounterIdLen, ulong visitSeed, int eliteBonusPct,
                                                                byte* output, nuint cap, nuint* needed);

        [DllImport(CryptLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_chest_open(IntPtr db, IntPtr save, byte* mapId, nuint mapIdLen, byte* chestId, nuint chestIdLen,
                                                    ShatterLootContext* ctx, ShatterRng* rng, byte* output, nuint cap, nuint* needed, int* result, ShatterError* err);

        [DllImport(CryptLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_encounter_clear_loot(IntPtr db, IntPtr save, byte* mapId, nuint mapIdLen, ShatterLootContext* ctx, ShatterRng* rng,
                                                              byte* output, nuint cap, nuint* needed, ShatterError* err);

        [DllImport(CryptLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_xp_award_kill(IntPtr db, IntPtr save, nuint characterIndex, byte* mapId, nuint mapIdLen, byte* enemyId, nuint enemyIdLen,
                                                       int monsterLevel, byte eliteRolled, byte* modifierId, nuint modifierIdLen, byte fervor, ShatterXpInfo* output);

        [DllImport(CryptLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_character_progress(IntPtr db, IntPtr save, nuint characterIndex, byte* mapId, nuint mapIdLen, ShatterXpInfo* output);

        [DllImport(CryptLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_fervor_get(IntPtr db, ShatterFervorInfo* output);

        [DllImport(CryptLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_skill_timing_weapon(IntPtr db, byte* skillId, nuint skillIdLen, IntPtr stats, byte* classId, nuint classIdLen,
                                                             byte* weaponBaseId, nuint weaponBaseIdLen, ShatterActionTiming* output);

        [DllImport(CryptLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_layout_check_ext7(uint* values, nuint n, ShatterError* err);
    }
}
