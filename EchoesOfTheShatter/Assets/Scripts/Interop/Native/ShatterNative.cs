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
    internal static unsafe class ShatterNative
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
    }
}
