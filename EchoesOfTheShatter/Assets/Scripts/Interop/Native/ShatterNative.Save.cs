using System;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

namespace Echoes.Interop.Native
{
    // Save, relogio e expedicao confiavel (shatter_c.h: secoes Save, Expedicao e "Expedicao confiavel"). O C# nao serializa nem grava
    // o save: tudo passa pelo core. As structs sao so inteiros e doubles (layout sequencial igual ao do header).

    [StructLayout(LayoutKind.Sequential)]
    internal struct ShatterForecastBands
    {
        public double xp_p10, xp_p50, xp_p90, gold_p10, gold_p50, gold_p90, retreat_probability;
        public int worst_resist_gap, reserved;
    }

    [StructLayout(LayoutKind.Sequential)]
    internal struct ShatterForecastBandsEx
    {
        public ShatterForecastBands baseValue;
        public int calibration, reserved;
    }

    /// <summary><c>shatter_save</c>: o save em memoria (main thread). Quem cria destroi.</summary>
    internal sealed class SaveHandle : SafeHandleZeroOrMinusOneIsInvalid
    {
        public SaveHandle() : base(true) { }

        public SaveHandle(IntPtr raw) : base(true) { SetHandle(raw); }

        protected override bool ReleaseHandle()
        {
            ShatterNative.shatter_save_destroy(handle);
            return true;
        }
    }

    internal static unsafe partial class ShatterNative
    {
        const string SaveLib = "shattercore";

        [DllImport(SaveLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_save_create(IntPtr* output);

        [DllImport(SaveLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern void shatter_save_destroy(IntPtr save);

        [DllImport(SaveLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_save_read(IntPtr db, byte* basePath, nuint len, IntPtr* output, ShatterLoadReport* report, ShatterError* err);

        [DllImport(SaveLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_save_write(IntPtr save, byte* basePath, nuint len, ShatterError* err);

        [DllImport(SaveLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_save_to_json(IntPtr save, byte pretty, byte* output, nuint cap, nuint* needed);

        [DllImport(SaveLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_save_from_json(byte* json, nuint len, IntPtr* output, int* loadStatus, ShatterError* err);

        [DllImport(SaveLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_save_summary_get(IntPtr save, ShatterSaveSummary* output);

        [DllImport(SaveLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_save_touch_last_seen(IntPtr save, ShatterTrustedNow* now);

        [DllImport(SaveLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_save_apply_daily_rest(IntPtr db, IntPtr save, ShatterTrustedNow* now, int* charges);

        [DllImport(SaveLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_save_character_json(IntPtr save, nuint index, byte* output, nuint cap, nuint* needed);

        [DllImport(SaveLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_save_record_area_run(IntPtr db, IntPtr save, nuint characterIndex, byte* mapId, nuint mapIdLen,
                                                              byte reachedEnd, byte bossDefeated, ShatterAreaRunReward* output);

        [DllImport(SaveLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_save_add_loot(IntPtr save, byte* lootJson, nuint len, ShatterError* err);

        [DllImport(SaveLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_save_roll_boss_loot(IntPtr db, IntPtr save, nuint characterIndex, byte* enemyId, nuint enemyIdLen, int areaLevel,
                                                             ShatterRng* lootRng, byte* output, nuint cap, nuint* needed, ShatterError* err);

        [DllImport(SaveLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_expedition_simulate_range(IntPtr db, byte* requestJson, nuint requestLen, byte* progressJson, nuint progressLen,
                                                                   uint firstEncounter, uint count, byte* output, nuint cap, nuint* needed, ShatterError* err);

        [DllImport(SaveLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_expedition_finalize(IntPtr db, byte* requestJson, nuint requestLen, byte* progressJson, nuint progressLen,
                                                             uint flags, byte* output, nuint cap, nuint* needed, ShatterError* err);

        [DllImport(SaveLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_expedition_check(IntPtr db, IntPtr save, byte* paramsJson, nuint len, int* startCheck,
                                                          byte* output, nuint cap, nuint* needed, ShatterError* err);

        [DllImport(SaveLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_save_expedition_request(IntPtr db, IntPtr save, nuint index, ShatterClockInput* clock,
                                                                 ShatterOfflineWindow* window, byte* output, nuint cap, nuint* needed, ShatterError* err);

        [DllImport(SaveLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_clock_resolve_now(ShatterClockInput* input, ShatterRules* rules, ShatterTrustedNow* output);

        [DllImport(SaveLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_expedition_forecast_ex(IntPtr db, byte* requestJson, nuint len, ulong baseSeed, int samples,
                                                                ShatterForecastBandsEx* output, ShatterError* err);

        [DllImport(SaveLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_save_start_expedition_trusted(IntPtr db, IntPtr save, byte* paramsJson, nuint len,
                                                                       ShatterTrustedNow* now, int* startCheck, ShatterError* err);

        [DllImport(SaveLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_save_collect_expedition_trusted(IntPtr db, IntPtr save, nuint index, ShatterClockInput* clock, uint flags,
                                                                         int* collectStatus, byte* output, nuint cap, nuint* needed, ShatterError* err);
    }
}
