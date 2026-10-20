using System;
using System.Runtime.InteropServices;

namespace Echoes.Interop.Native
{
    // Economia do prototipo: Vendedor, Frasco de Recarga e Encantador (shatter_c.h API 1.6; docs/09 secao 13).
    // Tudo e regra do core; o C# so chama e mostra.

    [StructLayout(LayoutKind.Sequential)]
    internal struct ShatterCraftResult
    {
        public int result;          // SHATTER_CRAFT_*
        public int changed_affix;
        public long gold_spent;
        public long shards_spent;
        public long shards_gained;
    }

    [StructLayout(LayoutKind.Sequential)]
    internal struct ShatterVendorResult
    {
        public int result;          // SHATTER_VENDOR_*
        public int evicted;
        public int evicted_rarity;
        public int reserved;
        public long gold;
    }

    [StructLayout(LayoutKind.Sequential)]
    internal struct ShatterFlaskResult
    {
        public int result;          // SHATTER_FLASK_*
        public int potion_index;
        public int charges_after;
        public int flasks_left;
    }

    internal static unsafe partial class ShatterNative
    {
        const string EconomyLib = "shattercore";

        [DllImport(EconomyLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_currency_get(IntPtr save, byte* id, nuint idLen, long* amount);

        [DllImport(EconomyLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_craft_quote_json(IntPtr db, IntPtr save, nuint characterIndex, ulong uid, int op, int arg, byte* output, nuint cap, nuint* needed);

        [DllImport(EconomyLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_craft_refine(IntPtr db, IntPtr save, nuint characterIndex, ulong uid, ShatterCraftResult* output);

        [DllImport(EconomyLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_craft_reforge(IntPtr db, IntPtr save, nuint characterIndex, ulong uid, int lockedAffixIndex, ShatterCraftResult* output);

        [DllImport(EconomyLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_craft_add_affix_offer(IntPtr db, IntPtr save, nuint characterIndex, ulong uid, byte* output, nuint cap, nuint* needed);

        [DllImport(EconomyLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_craft_add_affix_apply(IntPtr db, IntPtr save, nuint characterIndex, ulong uid, int candidateIndex, ShatterCraftResult* output);

        [DllImport(EconomyLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_craft_polish(IntPtr db, IntPtr save, nuint characterIndex, ulong uid, int affixIndex, ShatterCraftResult* output);

        [DllImport(EconomyLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_craft_dismantle(IntPtr db, IntPtr save, nuint characterIndex, ulong uid, ShatterCraftResult* output);

        [DllImport(EconomyLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_vendor_sell(IntPtr db, IntPtr save, nuint characterIndex, int container, ulong uid, ShatterVendorResult* output);

        [DllImport(EconomyLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_vendor_buyback_json(IntPtr db, IntPtr save, byte* output, nuint cap, nuint* needed);

        [DllImport(EconomyLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_vendor_buyback(IntPtr db, IntPtr save, nuint characterIndex, ulong uid, ShatterVendorResult* output);

        [DllImport(EconomyLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_vendor_stock_json(IntPtr db, IntPtr save, byte* output, nuint cap, nuint* needed);

        [DllImport(EconomyLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_vendor_buy(IntPtr db, IntPtr save, byte* stockId, nuint stockIdLen, int qty, ShatterVendorResult* output);

        [DllImport(EconomyLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_flask_use(IntPtr db, IntPtr save, IntPtr potions, int context, ShatterFlaskResult* output);

        [DllImport(EconomyLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_layout_check_ext6(uint* values, nuint n, ShatterError* err);
    }
}
