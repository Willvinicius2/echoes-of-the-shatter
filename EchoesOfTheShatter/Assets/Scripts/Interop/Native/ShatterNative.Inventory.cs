using System;
using System.Runtime.InteropServices;

namespace Echoes.Interop.Native
{
    // Inventario, equipamento, venda e loot no chao (shatter_c.h API 1.4; docs/09 secao 11). Tudo e regra do core; o C# so chama e mostra.

    [StructLayout(LayoutKind.Sequential)]
    internal struct ShatterInventoryInfo
    {
        public int backpack_capacity, backpack_used, stash_capacity, stash_used;
    }

    [StructLayout(LayoutKind.Sequential)]
    internal unsafe struct ShatterEquipResult
    {
        public int result;
        public int slot;
        public ulong displaced_uid;
        public byte displaced;
        public fixed byte reserved[7];
    }

    internal static unsafe partial class ShatterNative
    {
        const string InventoryLib = "shattercore";

        [DllImport(InventoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_inventory_info_get(IntPtr db, IntPtr save, nuint characterIndex, ShatterInventoryInfo* output);

        [DllImport(InventoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_inventory_slot_enabled(IntPtr db, int slot, byte* enabled);

        [DllImport(InventoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_inventory_list_json(IntPtr save, nuint characterIndex, int container, byte* output, nuint cap, nuint* needed);

        [DllImport(InventoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_inventory_sort(IntPtr db, IntPtr save, nuint characterIndex);

        [DllImport(InventoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_inventory_move(IntPtr db, IntPtr save, nuint characterIndex, ulong uid, int to, int* result);

        [DllImport(InventoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_inventory_equip(IntPtr db, IntPtr save, nuint characterIndex, ulong uid, int slot, IntPtr stats, ShatterEquipResult* output);

        [DllImport(InventoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_inventory_unequip(IntPtr db, IntPtr save, nuint characterIndex, int slot, IntPtr stats, ShatterEquipResult* output);

        [DllImport(InventoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_inventory_compare(IntPtr db, IntPtr save, nuint characterIndex, ulong uid, int slot, byte* output, nuint cap, nuint* needed);

        [DllImport(InventoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_inventory_sell_value(IntPtr db, IntPtr save, nuint characterIndex, ulong uid, long* value);

        [DllImport(InventoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_inventory_sell(IntPtr db, IntPtr save, nuint characterIndex, int container, ulong uid, long* gold, int* result);

        [DllImport(InventoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_inventory_discard(IntPtr save, nuint characterIndex, int container, ulong uid, int* result);

        [DllImport(InventoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_item_visual_set_id(IntPtr db, byte* baseId, nuint baseIdLen, byte* uniqueId, nuint uniqueIdLen, byte* output, nuint cap, nuint* needed);

        [DllImport(InventoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_save_drop_loot(IntPtr db, IntPtr save, byte* tableId, nuint tableIdLen, ShatterLootContext* ctx, ShatterRng* rng, byte* output, nuint cap, nuint* needed, ShatterError* err);

        [DllImport(InventoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_save_ground_add_loot(IntPtr save, byte* lootJson, nuint len, ShatterError* err);

        [DllImport(InventoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_save_ground_list(IntPtr save, byte* output, nuint cap, nuint* needed);

        [DllImport(InventoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_save_pickup(IntPtr db, IntPtr save, nuint characterIndex, ulong uid, int* dest);

        [DllImport(InventoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_save_ground_discard(IntPtr save, ulong uid, int* result);

        [DllImport(InventoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_save_ground_clear(IntPtr save);

        [DllImport(InventoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_layout_check_ext4(uint* values, nuint n, ShatterError* err);
    }
}
