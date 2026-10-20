using System;
using System.Collections.Generic;
using System.Globalization;

namespace Echoes.Interop
{
    // Economia do prototipo (docs/16 secao 11; API C 1.6, docs/09 secao 13). Todo custo, sorteio e regra e do core: estes tipos so
    // carregam o que o core devolveu. Nenhuma formula, preco ou sorteio no C#.

    /// <summary>Resultado das melhorias do Encantador (<c>SHATTER_CRAFT_*</c>). Recusa nao muda nada nem cobra.</summary>
    public enum CraftResult
    {
        Ok = 0, NotFound = 1, Unique = 2, WrongRarity = 3, AffixLimit = 4, AlreadyInscribed = 5, PolishMax = 6, NoCandidate = 7,
        NoGold = 8, NoShards = 9, EquippedDismantle = 10, UnknownContent = 11, BadIndex = 12, Error = 99,
    }

    /// <summary>Operacao do Encantador (<c>SHATTER_CRAFT_OP_*</c>), usada na previa.</summary>
    public enum CraftOp { Refine = 0, Reforge = 1, Add = 2, Polish = 3, Dismantle = 4 }

    /// <summary>O que uma melhoria feita custou e mudou (<c>shatter_craft_result</c>).</summary>
    public readonly struct CraftOutcome
    {
        public readonly CraftResult Result;
        /// <summary>Lapidar: afixo lapidado. Adicionar: o afixo novo. Reforjar com trava: onde ficou o travado. Senao -1.</summary>
        public readonly int ChangedAffix;
        public readonly long GoldSpent, ShardsSpent, ShardsGained;

        public CraftOutcome(CraftResult result, int changedAffix, long goldSpent, long shardsSpent, long shardsGained)
        {
            Result = result;
            ChangedAffix = changedAffix;
            GoldSpent = goldSpent;
            ShardsSpent = shardsSpent;
            ShardsGained = shardsGained;
        }

        public bool Ok => Result == CraftResult.Ok;
        public static CraftOutcome Failed => new CraftOutcome(CraftResult.Error, -1, 0, 0, 0);
    }

    /// <summary>Previa de uma operacao do Encantador (custo, faixa e avisos); nao altera nada e nunca mostra o resultado do sorteio.</summary>
    public sealed class CraftQuote
    {
        public CraftOp Op;
        /// <summary>NoGold/NoShards trazem os custos mesmo assim (a UI mostra em vermelho).</summary>
        public CraftResult Result = CraftResult.Error;
        public long Gold, Shards, ShardsGain;
        public int AffixCountMin, AffixCountMax;
        public int PolishStep;
        public double PolishFrom, PolishTo;
        /// <summary>Reforjar: Lascas com e sem a trava de um afixo (o Ouro e o mesmo).</summary>
        public long ShardsWithLock, ShardsNoLock;
        public int Reforges;
        /// <summary>Ha uma expedicao Running: a melhoria so vale a partir da proxima (aviso, nao bloqueia).</summary>
        public bool ExpeditionRunning;
        public long HaveGold, HaveShards;

        public static CraftQuote FromJson(string json)
        {
            var q = new CraftQuote();
            if (string.IsNullOrEmpty(json)) return q;
            var o = MiniJson.AsObject(MiniJson.Parse(json));
            q.Result = (CraftResult)MiniJson.Int(o, "result", 99);
            q.Gold = (long)MiniJson.Num(o, "gold");
            q.Shards = (long)MiniJson.Num(o, "shards");
            q.ShardsGain = (long)MiniJson.Num(o, "shards_gain");
            q.AffixCountMin = MiniJson.Int(o, "affix_count_min");
            q.AffixCountMax = MiniJson.Int(o, "affix_count_max");
            q.PolishStep = MiniJson.Int(o, "polish_step");
            q.PolishFrom = MiniJson.Num(o, "polish_from");
            q.PolishTo = MiniJson.Num(o, "polish_to");
            q.ShardsWithLock = (long)MiniJson.Num(o, "shards_with_lock");
            q.ShardsNoLock = (long)MiniJson.Num(o, "shards_no_lock");
            q.Reforges = MiniJson.Int(o, "reforges");
            q.ExpeditionRunning = MiniJson.Bool(o, "expedition_running");
            q.HaveGold = (long)MiniJson.Num(o, "have_gold");
            q.HaveShards = (long)MiniJson.Num(o, "have_shards");
            return q;
        }
    }

    /// <summary>Um cartao de Adicionar afixo: o afixo e a faixa do valor (o valor sai so ao confirmar).</summary>
    public readonly struct AffixCandidateInfo
    {
        public readonly string AffixId;
        public readonly double Min, Max;

        public AffixCandidateInfo(string affixId, double min, double max)
        {
            AffixId = affixId;
            Min = min;
            Max = max;
        }
    }

    /// <summary>Oferta de Adicionar afixo: os mesmos candidatos enquanto o item nao mudar (fechar e reabrir nao re-sorteia).</summary>
    public sealed class AffixOfferInfo
    {
        public CraftResult Result = CraftResult.Error;
        public long Gold, Shards;
        public readonly List<AffixCandidateInfo> Candidates = new List<AffixCandidateInfo>();

        public static AffixOfferInfo FromJson(string json)
        {
            var offer = new AffixOfferInfo();
            if (string.IsNullOrEmpty(json)) return offer;
            var o = MiniJson.AsObject(MiniJson.Parse(json));
            offer.Result = (CraftResult)MiniJson.Int(o, "result", 99);
            offer.Gold = (long)MiniJson.Num(o, "gold");
            offer.Shards = (long)MiniJson.Num(o, "shards");
            foreach (var c in MiniJson.AsArray(o.TryGetValue("candidates", out var list) ? list : null))
            {
                var co = MiniJson.AsObject(c);
                offer.Candidates.Add(new AffixCandidateInfo(MiniJson.Str(co, "affix_id"), MiniJson.Num(co, "min"), MiniJson.Num(co, "max")));
            }
            return offer;
        }
    }

    /// <summary>Resultado das operacoes do Vendedor (<c>SHATTER_VENDOR_*</c>).</summary>
    public enum VendorResult { Ok = 0, NotFound = 1, Full = 2, NoGold = 3, CarryCap = 4, BadQuantity = 5, UnknownContent = 6, Error = 99 }

    /// <summary>Venda, recompra ou compra (<c>shatter_vendor_result</c>).</summary>
    public readonly struct VendorOutcome
    {
        public readonly VendorResult Result;
        /// <summary>Venda: a recompra cheia expulsou o item mais antigo (ele deixou de existir).</summary>
        public readonly bool Evicted;
        public readonly ItemRarity EvictedRarity;
        /// <summary>Venda: Ouro recebido. Recompra e compra: Ouro gasto.</summary>
        public readonly long Gold;

        public VendorOutcome(VendorResult result, bool evicted, ItemRarity evictedRarity, long gold)
        {
            Result = result;
            Evicted = evicted;
            EvictedRarity = evictedRarity;
            Gold = gold;
        }

        public bool Ok => Result == VendorResult.Ok;
        public static VendorOutcome Failed => new VendorOutcome(VendorResult.Error, false, ItemRarity.Normal, 0);
    }

    /// <summary>Item na recompra: o que o jogador recebeu na venda e o preco para recomprar (calculado pelo core).</summary>
    public sealed class BuybackEntryInfo
    {
        public ItemInstanceInfo Item;
        public long Paid, Price;
    }

    /// <summary>Recompra do Vendedor (os 10 ultimos itens vendidos, o mais recente primeiro).</summary>
    public sealed class BuybackInfo
    {
        public int Capacity, Count;
        /// <summary>A proxima venda expulsa o mais antigo: a UI avisa antes, com confirmacao extra para Raro e Unico.</summary>
        public bool WouldEvict;
        public ItemRarity EvictRarity;
        public readonly List<BuybackEntryInfo> Items = new List<BuybackEntryInfo>();

        public static BuybackInfo FromJson(string json)
        {
            var info = new BuybackInfo();
            if (string.IsNullOrEmpty(json)) return info;
            var o = MiniJson.AsObject(MiniJson.Parse(json));
            info.Capacity = MiniJson.Int(o, "capacity");
            info.Count = MiniJson.Int(o, "count");
            info.WouldEvict = MiniJson.Bool(o, "would_evict");
            info.EvictRarity = (ItemRarity)MiniJson.Int(o, "evict_rarity");
            foreach (var e in MiniJson.AsArray(o.TryGetValue("items", out var list) ? list : null))
            {
                var eo = MiniJson.AsObject(e);
                var item = ItemInstanceInfo.FromJson(MiniJson.AsObject(eo.TryGetValue("item", out var it) ? it : null));
                if (item == null) continue;
                info.Items.Add(new BuybackEntryInfo { Item = item, Paid = (long)MiniJson.Num(eo, "paid"), Price = (long)MiniJson.Num(eo, "price") });
            }
            return info;
        }
    }

    /// <summary>Uma linha do estoque do Vendedor (<c>vendor_stock.csv</c>) com quantos o jogador ja leva.</summary>
    public readonly struct VendorStockInfo
    {
        public readonly string Id, RefId;
        public readonly long PriceGold;
        public readonly int CarryCap, Owned;

        public VendorStockInfo(string id, string refId, long priceGold, int carryCap, int owned)
        {
            Id = id;
            RefId = refId;
            PriceGold = priceGold;
            CarryCap = carryCap;
            Owned = owned;
        }

        public static List<VendorStockInfo> ListFromJson(string json)
        {
            var list = new List<VendorStockInfo>();
            if (string.IsNullOrEmpty(json)) return list;
            foreach (var e in MiniJson.AsArray(MiniJson.Parse(json)))
            {
                var o = MiniJson.AsObject(e);
                list.Add(new VendorStockInfo(MiniJson.Str(o, "id"), MiniJson.Str(o, "ref_id"), (long)MiniJson.Num(o, "price_gold"),
                    MiniJson.Int(o, "carry_cap"), MiniJson.Int(o, "owned")));
            }
            return list;
        }
    }

    /// <summary>Onde o Frasco de Recarga e usado: a luta do Guardiao testa as cargas do docs/13 e a expedicao nao usa frasco.</summary>
    public enum FlaskContext { Run = 0, Arena = 1, Idle = 2 }

    public enum FlaskResult { Ok = 0, NoFlask = 1, ArenaLocked = 2, IdleForbidden = 3, PotionsFull = 4, LockedOut = 5, UnknownContent = 6, Error = 99 }

    /// <summary>Uso do Frasco de Recarga (<c>shatter_flask_result</c>).</summary>
    public readonly struct FlaskOutcome
    {
        public readonly FlaskResult Result;
        /// <summary>Posicao da pocao restaurada no cinto (ordem de potions.csv); -1 se nenhuma.</summary>
        public readonly int PotionIndex;
        public readonly int ChargesAfter, FlasksLeft;

        public FlaskOutcome(FlaskResult result, int potionIndex, int chargesAfter, int flasksLeft)
        {
            Result = result;
            PotionIndex = potionIndex;
            ChargesAfter = chargesAfter;
            FlasksLeft = flasksLeft;
        }

        public bool Ok => Result == FlaskResult.Ok;
        public static FlaskOutcome Failed => new FlaskOutcome(FlaskResult.Error, -1, 0, 0);
    }
}
