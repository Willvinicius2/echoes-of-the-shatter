using System;
using System.Collections.Generic;
using System.Text;

namespace Echoes.Interop.Native
{
    /// <summary>
    /// Inventario, equipamento, comparacao, venda e loot no chao (API C 1.4). Todas as regras (capacidades, posicoes liberadas, ordenacao, precos,
    /// o que cai e para onde vai) sao do core; aqui so chamadas e leitura do JSON. Main thread.
    /// </summary>
    public sealed unsafe partial class SaveGame
    {
        ShatterRng lootRng;
        bool lootRngReady;

        static InvResult Result(int status, int result) => status == 0 ? (InvResult)result : InvResult.Error;

        static IntPtr StatsPointer(IStatBlock stats)
        {
            var native = stats as NativeStatBlock;
            return native != null ? native.Handle.DangerousGetHandle() : IntPtr.Zero;
        }

        /// <summary>
        /// Bloco de atributos do personagem do save (equipamento com afixos), pelo core, com o nivel de jogo dado (o heroi do prototipo joga no
        /// nivel da cena, nao no do save). O bloco devolvido e o que <see cref="Equip"/>/<see cref="Unequip"/> atualizam.
        /// </summary>
        internal IStatBlock StatsOfCharacter(NativeRulesCore rules, int characterIndex, int level)
        {
            var json = System.Text.RegularExpressions.Regex.Replace(CharacterJson(characterIndex), @"""level"":\s*\d+", "\"level\":" + Math.Max(1, level), System.Text.RegularExpressions.RegexOptions.None, TimeSpan.FromSeconds(1));
            var bytes = Encoding.UTF8.GetBytes(json);
            IntPtr raw = IntPtr.Zero;
            ShatterError err = default;
            int status;
            fixed (byte* p = bytes) status = ShatterNative.shatter_statblock_from_character_json(rules.DbPointer, p, (nuint)bytes.Length, &raw, &err);
            if (status != 0) throw new ArgumentException("hero stats from save failed: " + NativeBuffers.ErrorMessage(ref err));
            return new NativeStatBlock(new StatBlockHandle(raw)) { IsHero = true };
        }

        public InventoryInfo Inventory(NativeRulesCore rules, int characterIndex)
        {
            ShatterInventoryInfo info;
            var status = ShatterNative.shatter_inventory_info_get(rules.DbPointer, Raw, (nuint)characterIndex, &info);
            return status == 0 ? new InventoryInfo(info.backpack_capacity, info.backpack_used, info.stash_capacity, info.stash_used) : default;
        }

        /// <summary>Posicao de equipamento liberada no prototipo (rules.csv equip_slot_*); slot na ordem de <see cref="ItemSlots"/>.</summary>
        public static bool SlotEnabled(NativeRulesCore rules, int slot)
        {
            byte enabled = 0;
            return ShatterNative.shatter_inventory_slot_enabled(rules.DbPointer, slot, &enabled) == 0 && enabled != 0;
        }

        public List<ItemInstanceInfo> ListItems(int characterIndex, ItemContainer container)
        {
            var save = Raw;
            var status = NativeBuffers.ReadString((byte* o, nuint cap, nuint* needed) => ShatterNative.shatter_inventory_list_json(save, (nuint)characterIndex, (int)container, o, cap, needed), out var json, 4096);
            return status == 0 ? ItemInstanceInfo.ListFromJson(json) : new List<ItemInstanceInfo>();
        }

        /// <summary>Equipamento do personagem: um item (ou nulo) por posicao, na ordem de <see cref="ItemSlots"/>.</summary>
        public ItemInstanceInfo[] Equipment(int characterIndex)
        {
            var result = new ItemInstanceInfo[ItemSlots.Names.Length];
            var o = MiniJson.AsObject(MiniJson.Parse(CharacterJson(characterIndex)));
            var equipment = MiniJson.AsObject(o.TryGetValue("equipment", out var e) ? e : null);
            for (var i = 0; i < result.Length; i++)
                if (equipment.TryGetValue(ItemSlots.Names[i], out var item)) result[i] = ItemInstanceInfo.FromJson(item as Dictionary<string, object>);
            return result;
        }

        public bool Sort(NativeRulesCore rules, int characterIndex) => ShatterNative.shatter_inventory_sort(rules.DbPointer, Raw, (nuint)characterIndex) == 0;

        public InvResult Move(NativeRulesCore rules, int characterIndex, ulong uid, ItemContainer to)
        {
            int result;
            var status = ShatterNative.shatter_inventory_move(rules.DbPointer, Raw, (nuint)characterIndex, uid, (int)to, &result);
            return Result(status, result);
        }

        /// <summary>Equipa o item da Mochila (slot -1 = posicao padrao). Com <paramref name="stats"/> (o bloco do heroi) so os modificadores dos itens trocados saem/entram.</summary>
        public EquipOutcome Equip(NativeRulesCore rules, int characterIndex, ulong uid, int slot, IStatBlock stats)
        {
            ShatterEquipResult r = default;
            var status = ShatterNative.shatter_inventory_equip(rules.DbPointer, Raw, (nuint)characterIndex, uid, slot, StatsPointer(stats), &r);
            return status == 0 ? new EquipOutcome((InvResult)r.result, r.slot, r.displaced_uid, r.displaced != 0) : new EquipOutcome(InvResult.Error, -1, 0, false);
        }

        public EquipOutcome Unequip(NativeRulesCore rules, int characterIndex, int slot, IStatBlock stats)
        {
            ShatterEquipResult r = default;
            var status = ShatterNative.shatter_inventory_unequip(rules.DbPointer, Raw, (nuint)characterIndex, slot, StatsPointer(stats), &r);
            return status == 0 ? new EquipOutcome((InvResult)r.result, r.slot, r.displaced_uid, r.displaced != 0) : new EquipOutcome(InvResult.Error, -1, 0, false);
        }

        /// <summary>Comparacao com o equipado para o tooltip (o item pode estar na Mochila, no Bau ou no chao). Nada e alterado.</summary>
        public ItemComparison Compare(NativeRulesCore rules, int characterIndex, ulong uid, int slot = -1)
        {
            var db = rules.DbPointer;
            var save = Raw;
            var status = NativeBuffers.ReadString((byte* o, nuint cap, nuint* needed) => ShatterNative.shatter_inventory_compare(db, save, (nuint)characterIndex, uid, slot, o, cap, needed), out var json, 1024);
            return status == 0 ? ItemComparison.FromJson(json) : new ItemComparison { Result = InvResult.Error };
        }

        /// <summary>Valor de venda em Ouro (so informacao por enquanto; o uso do Ouro e pergunta ao dono).</summary>
        public long SellValue(NativeRulesCore rules, int characterIndex, ulong uid)
        {
            long value = 0;
            return ShatterNative.shatter_inventory_sell_value(rules.DbPointer, Raw, (nuint)characterIndex, uid, &value) == 0 ? value : 0;
        }

        public InvResult Sell(NativeRulesCore rules, int characterIndex, ItemContainer container, ulong uid, out long gold)
        {
            long paid = 0;
            int result;
            var status = ShatterNative.shatter_inventory_sell(rules.DbPointer, Raw, (nuint)characterIndex, (int)container, uid, &paid, &result);
            gold = status == 0 ? paid : 0;
            return Result(status, result);
        }

        public InvResult Discard(int characterIndex, ItemContainer container, ulong uid)
        {
            int result;
            var status = ShatterNative.shatter_inventory_discard(Raw, (nuint)characterIndex, (int)container, uid, &result);
            return Result(status, result);
        }

        // ------------------------------------------------------------------------------ loot no chao

        void EnsureLootRng(ulong seed)
        {
            if (lootRngReady) return;
            ShatterRng rng;
            if (ShatterNative.shatter_rng_for_stream(seed, 2u, 0UL, &rng) != 0) return;
            lootRng = rng;
            lootRngReady = true;
        }

        /// <summary>
        /// Rola a tabela de loot (mesmo contexto e RNG do shatter_loot_roll) e poe os itens NO CHAO; Ouro e Lascas entram direto no save.
        /// Devolve o JSON {"items":[...],"stacks":[...],"rares_dropped":n} do core ou vazio em erro. O RNG de loot e deste save (semeado uma vez).
        /// </summary>
        public string DropLoot(NativeRulesCore rules, string tableId, int areaLevel, int raresAlreadyDropped, int maxRares, ulong seed, out string error)
        {
            EnsureLootRng(seed);
            var id = NativeBuffers.Utf8(tableId);
            var ctx = new ShatterLootContext { quantity_mult = 1.0, mode = 0, area_level = areaLevel, rares_already_dropped = raresAlreadyDropped, max_rares = maxRares };
            var db = rules.DbPointer;
            var save = Raw;
            var buffer = new byte[2048];
            for (var attempt = 0; attempt < 3; attempt++)
            {
                var rng = lootRng; // buffer pequeno nao muda nada (nem o rng): cada tentativa parte do mesmo estado
                nuint needed = 0;
                ShatterError err = default;
                int status;
                fixed (byte* idp = id)
                fixed (byte* o = buffer)
                    status = ShatterNative.shatter_save_drop_loot(db, save, idp, (nuint)id.Length, &ctx, &rng, o, (nuint)buffer.Length, &needed, &err);
                if (status == NativeBuffers.BufferTooSmall)
                {
                    buffer = new byte[Math.Max(1, (int)needed)];
                    continue;
                }
                error = status == 0 ? string.Empty : NativeBuffers.ErrorMessage(ref err);
                if (status != 0) return string.Empty;
                lootRng = rng;
                return Encoding.UTF8.GetString(buffer, 0, (int)needed);
            }
            error = "buffer";
            return string.Empty;
        }

        /// <summary>Poe no chao um loot ja rolado (ex.: o do Guardiao, com o Unico). Grave o save ANTES (RF-55): o chao nao e salvo.</summary>
        public bool GroundAddLoot(string lootJson, out string error)
        {
            var bytes = Encoding.UTF8.GetBytes(lootJson);
            ShatterError err = default;
            int status;
            fixed (byte* p = bytes) status = ShatterNative.shatter_save_ground_add_loot(Raw, p, (nuint)bytes.Length, &err);
            error = status == 0 ? string.Empty : NativeBuffers.ErrorMessage(ref err);
            return status == 0;
        }

        public List<ItemInstanceInfo> GroundItems()
        {
            var save = Raw;
            var status = NativeBuffers.ReadString((byte* o, nuint cap, nuint* needed) => ShatterNative.shatter_save_ground_list(save, o, cap, needed), out var json, 2048);
            return status == 0 ? ItemInstanceInfo.ListFromJson(json) : new List<ItemInstanceInfo>();
        }

        /// <summary>Chao para a Mochila; cheia e Unico: Bau; senao Full e o item FICA no chao.</summary>
        public PickupDest Pickup(NativeRulesCore rules, int characterIndex, ulong uid)
        {
            int dest;
            var status = ShatterNative.shatter_save_pickup(rules.DbPointer, Raw, (nuint)characterIndex, uid, &dest);
            return status == 0 ? (PickupDest)dest : PickupDest.Error;
        }

        public InvResult GroundDiscard(ulong uid)
        {
            int result;
            var status = ShatterNative.shatter_save_ground_discard(Raw, uid, &result);
            return Result(status, result);
        }

        public void GroundClear() => ShatterNative.shatter_save_ground_clear(Raw);
    }

    public sealed partial class NativeRulesCore
    {
        /// <summary>Conjunto visual do item (docs/04 17.4): uniques.visualSetId, depois item_bases.visualSetId, depois vset.starter. Vem do core (a Unity nao le o CSV).</summary>
        public unsafe string ItemVisualSetId(string baseId, string uniqueId)
        {
            var b = NativeBuffers.Utf8(baseId);
            var u = NativeBuffers.Utf8(uniqueId);
            var db = DbPointer;
            var buffer = new byte[64];
            for (var attempt = 0; attempt < 3; attempt++)
            {
                nuint needed = 0;
                int status;
                fixed (byte* bp = b)
                fixed (byte* up = u)
                fixed (byte* o = buffer)
                    status = ShatterNative.shatter_item_visual_set_id(db, bp, (nuint)b.Length, up, (nuint)u.Length, o, (nuint)buffer.Length, &needed);
                if (status == NativeBuffers.BufferTooSmall)
                {
                    buffer = new byte[Math.Max(1, (int)needed)];
                    continue;
                }
                return status == 0 ? Encoding.UTF8.GetString(buffer, 0, (int)needed) : string.Empty;
            }
            return string.Empty;
        }
        }
}
