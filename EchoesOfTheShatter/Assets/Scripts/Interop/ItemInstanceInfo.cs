using System;
using System.Collections.Generic;
using System.Globalization;

namespace Echoes.Interop
{
    public enum ItemRarity { Normal = 0, Magic = 1, Rare = 2, Unique = 3 }

    /// <summary>Resultado das operacoes de inventario do core (<c>SHATTER_INV_*</c>); recusa nao muda nada.</summary>
    public enum InvResult { Ok = 0, NotFound = 1, Full = 2, SlotMismatch = 3, SlotLocked = 4, SlotEmpty = 5, UnknownContent = 6, Error = 99 }

    /// <summary>Onde o item pego do chao foi parar (<c>SHATTER_PICKUP_*</c>).</summary>
    public enum PickupDest { Backpack = 0, Stash = 1, Full = 2, NotFound = 3, Error = 99 }

    public enum ItemContainer { Backpack = 0, Stash = 1 }

    public readonly struct AffixInfo
    {
        public readonly string AffixId;
        public readonly double Value;
        /// <summary>Passos de Lapidar ja dados neste afixo (0 a 3; economia, docs/16 11.4).</summary>
        public readonly int Polish;

        public AffixInfo(string affixId, double value, int polish = 0)
        {
            AffixId = affixId;
            Value = value;
            Polish = polish;
        }
    }

    /// <summary>Um <c>ItemInstance</c> do save (docs/06): lido do JSON do core; o cliente so mostra.</summary>
    public sealed class ItemInstanceInfo
    {
        public ulong Uid;
        public string BaseId = string.Empty;
        public ItemRarity Rarity;
        public int ItemLevel = 1;
        public string UniqueId = string.Empty;
        public readonly List<AffixInfo> Affixes = new List<AffixInfo>();
        public bool HasInscription;
        /// <summary>Melhorias do Encantador (docs/16 11.6): quantas vezes a peca foi refinada, reforjada ou recebeu afixo; entra na semente do proximo sorteio.</summary>
        public int CraftSteps, CraftReforges;

        public bool IsUnique => Rarity == ItemRarity.Unique;

        public static ItemRarity ParseRarity(string text)
        {
            switch (text)
            {
                case "magic": return ItemRarity.Magic;
                case "rare": return ItemRarity.Rare;
                case "unique": return ItemRarity.Unique;
                default: return ItemRarity.Normal;
            }
        }

        public static ItemInstanceInfo FromJson(Dictionary<string, object> o)
        {
            if (o == null || o.Count == 0) return null;
            var item = new ItemInstanceInfo
            {
                BaseId = MiniJson.Str(o, "base_id"),
                Rarity = ParseRarity(MiniJson.Str(o, "rarity")),
                ItemLevel = MiniJson.Int(o, "item_level", 1),
                UniqueId = MiniJson.Str(o, "unique_id"),
                HasInscription = MiniJson.Bool(o, "has_inscription"),
                CraftSteps = MiniJson.Int(o, "craft_steps"),
                CraftReforges = MiniJson.Int(o, "craft_reforges"),
            };
            ulong.TryParse(MiniJson.Str(o, "uid", "0"), NumberStyles.None, CultureInfo.InvariantCulture, out item.Uid);
            foreach (var a in MiniJson.AsArray(o.TryGetValue("affixes", out var list) ? list : null))
            {
                var ao = MiniJson.AsObject(a);
                item.Affixes.Add(new AffixInfo(MiniJson.Str(ao, "affix_id"), MiniJson.Num(ao, "value"), MiniJson.Int(ao, "polish")));
            }
            return item;
        }

        /// <summary>Lista de itens a partir de um array JSON (ou de {"items":[...]}).</summary>
        public static List<ItemInstanceInfo> ListFromJson(string json)
        {
            var result = new List<ItemInstanceInfo>();
            if (string.IsNullOrEmpty(json)) return result;
            var parsed = MiniJson.Parse(json);
            var array = parsed is Dictionary<string, object> obj ? MiniJson.AsArray(obj.TryGetValue("items", out var items) ? items : null) : MiniJson.AsArray(parsed);
            foreach (var entry in array)
            {
                var item = FromJson(MiniJson.AsObject(entry));
                if (item != null) result.Add(item);
            }
            return result;
        }
    }

    /// <summary>Resumo de ocupacao (<c>shatter_inventory_info</c>).</summary>
    public readonly struct InventoryInfo
    {
        public readonly int BackpackCapacity, BackpackUsed, StashCapacity, StashUsed;

        public InventoryInfo(int backpackCapacity, int backpackUsed, int stashCapacity, int stashUsed)
        {
            BackpackCapacity = backpackCapacity;
            BackpackUsed = backpackUsed;
            StashCapacity = stashCapacity;
            StashUsed = stashUsed;
        }
    }

    /// <summary>Resultado de equipar/desequipar (<c>shatter_equip_result</c>).</summary>
    public readonly struct EquipOutcome
    {
        public readonly InvResult Result;
        public readonly int Slot;
        public readonly ulong DisplacedUid;
        public readonly bool Displaced;

        public EquipOutcome(InvResult result, int slot, ulong displacedUid, bool displaced)
        {
            Result = result;
            Slot = slot;
            DisplacedUid = displacedUid;
            Displaced = displaced;
        }

        public bool Ok => Result == InvResult.Ok;
    }

    /// <summary>Um atributo que muda na comparacao com o equipado (so os que mudam).</summary>
    public readonly struct CompareDelta
    {
        public readonly string Stat;
        public readonly double Before, After;

        public CompareDelta(string stat, double before, double after)
        {
            Stat = stat;
            Before = before;
            After = after;
        }

        public double Change => After - Before;
    }

    /// <summary>Comparacao para o tooltip (<c>shatter_inventory_compare</c>): calculada pelo core; a UI so mostra setas.</summary>
    public sealed class ItemComparison
    {
        public InvResult Result;
        public string Slot = string.Empty;
        public ulong EquippedUid;
        public bool IsWeapon;
        public double WeaponDpsBefore, WeaponDpsAfter;
        public readonly List<CompareDelta> Deltas = new List<CompareDelta>();

        public static ItemComparison FromJson(string json)
        {
            var c = new ItemComparison();
            if (string.IsNullOrEmpty(json)) { c.Result = InvResult.Error; return c; }
            var o = MiniJson.AsObject(MiniJson.Parse(json));
            c.Result = (InvResult)MiniJson.Int(o, "result");
            c.Slot = MiniJson.Str(o, "slot");
            ulong.TryParse(MiniJson.Str(o, "equipped_uid", "0"), NumberStyles.None, CultureInfo.InvariantCulture, out c.EquippedUid);
            c.IsWeapon = MiniJson.Bool(o, "is_weapon");
            c.WeaponDpsBefore = MiniJson.Num(o, "weapon_dps_before");
            c.WeaponDpsAfter = MiniJson.Num(o, "weapon_dps_after");
            foreach (var d in MiniJson.AsArray(o.TryGetValue("deltas", out var deltas) ? deltas : null))
            {
                var dobj = MiniJson.AsObject(d);
                c.Deltas.Add(new CompareDelta(MiniJson.Str(dobj, "stat"), MiniJson.Num(dobj, "before"), MiniJson.Num(dobj, "after")));
            }
            return c;
        }
    }

    /// <summary>Ordem de <c>ItemSlot</c> do core (item.h) e os nomes de texto dos slots no save.</summary>
    public static class ItemSlots
    {
        public static readonly string[] Names = { "main_hand", "off_hand", "head", "body", "hands", "feet", "amulet", "ring", "ring2", "belt", "legs" };

        public static int IndexOf(string name) => Array.IndexOf(Names, name);
    }
}
