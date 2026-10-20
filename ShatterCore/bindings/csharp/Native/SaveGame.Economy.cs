using System;
using System.Collections.Generic;
using System.Text;

namespace Echoes.Interop.Native
{
    /// <summary>
    /// Vendedor, recompra, Frasco de Recarga e Encantador (API C 1.6; docs/16 secao 11). Precos, custos, sorteios, limites e a lista de
    /// candidatos sao do core; aqui so chamadas e leitura do JSON. Cada operacao recusada (resultado != Ok) nao muda nada nem cobra.
    /// Depois de melhorar um item EQUIPADO, refaca o bloco de atributos do heroi (<see cref="StatsOfCharacter"/>). Grave o save depois de
    /// cada melhoria (auto-save, RF-54). Main thread.
    /// </summary>
    public sealed unsafe partial class SaveGame
    {
        public const string GoldId = "currency.gold";
        public const string ShardsId = "material.shards";
        public const string RefillFlaskId = "consumable.refill_flask";

        /// <summary>Saldo de uma pilha do save (Ouro, Lascas, Frasco de Recarga). Id desconhecido = 0.</summary>
        public long Currency(string id)
        {
            var bytes = NativeBuffers.Utf8(id);
            long amount = 0;
            int status;
            fixed (byte* p = bytes) status = ShatterNative.shatter_currency_get(Raw, p, (nuint)bytes.Length, &amount);
            return status == 0 ? amount : 0;
        }

        // ------------------------------------------------------------------------------ Encantador

        static CraftOutcome ToOutcome(int status, in ShatterCraftResult r) =>
            status == 0 ? new CraftOutcome((CraftResult)r.result, r.changed_affix, r.gold_spent, r.shards_spent, r.shards_gained) : CraftOutcome.Failed;

        /// <summary>Previa (custo, faixa, avisos) sem mudar nada. <paramref name="arg"/>: Reforjar = afixo travado (-1 nenhum); Lapidar = afixo; Adicionar = -1.</summary>
        public CraftQuote QuoteCraft(NativeRulesCore rules, int characterIndex, ulong uid, CraftOp op, int arg = -1)
        {
            var db = rules.DbPointer;
            var save = Raw;
            var status = NativeBuffers.ReadString((byte* o, nuint cap, nuint* needed) =>
                ShatterNative.shatter_craft_quote_json(db, save, (nuint)characterIndex, uid, (int)op, arg, o, cap, needed), out var json, 512);
            var quote = status == 0 ? CraftQuote.FromJson(json) : new CraftQuote();
            quote.Op = op;
            return quote;
        }

        /// <summary>Refinar: Comum vira Magico com 1 a 2 afixos.</summary>
        public CraftOutcome CraftRefine(NativeRulesCore rules, int characterIndex, ulong uid)
        {
            ShatterCraftResult r = default;
            var status = ShatterNative.shatter_craft_refine(rules.DbPointer, Raw, (nuint)characterIndex, uid, &r);
            return ToOutcome(status, r);
        }

        /// <summary>Reforjar: sorteia de novo os afixos mantendo a quantidade. <paramref name="lockedAffixIndex"/> trava 1 afixo (-1 nenhum).</summary>
        public CraftOutcome CraftReforge(NativeRulesCore rules, int characterIndex, ulong uid, int lockedAffixIndex = -1)
        {
            ShatterCraftResult r = default;
            var status = ShatterNative.shatter_craft_reforge(rules.DbPointer, Raw, (nuint)characterIndex, uid, lockedAffixIndex, &r);
            return ToOutcome(status, r);
        }

        /// <summary>Adicionar afixo, passo 1: candidatos (ate 3) e custo. Nao altera nada; reabrir devolve os mesmos.</summary>
        public AffixOfferInfo CraftAddAffixOffer(NativeRulesCore rules, int characterIndex, ulong uid)
        {
            var db = rules.DbPointer;
            var save = Raw;
            var status = NativeBuffers.ReadString((byte* o, nuint cap, nuint* needed) =>
                ShatterNative.shatter_craft_add_affix_offer(db, save, (nuint)characterIndex, uid, o, cap, needed), out var json, 512);
            return status == 0 ? AffixOfferInfo.FromJson(json) : new AffixOfferInfo();
        }

        /// <summary>Adicionar afixo, passo 2: escolhe o candidato (indice da oferta) e confirma.</summary>
        public CraftOutcome CraftAddAffixApply(NativeRulesCore rules, int characterIndex, ulong uid, int candidateIndex)
        {
            ShatterCraftResult r = default;
            var status = ShatterNative.shatter_craft_add_affix_apply(rules.DbPointer, Raw, (nuint)characterIndex, uid, candidateIndex, &r);
            return ToOutcome(status, r);
        }

        /// <summary>Lapidar: um passo (25% da faixa, ate 3) num afixo, sem sorteio.</summary>
        public CraftOutcome CraftPolish(NativeRulesCore rules, int characterIndex, ulong uid, int affixIndex)
        {
            ShatterCraftResult r = default;
            var status = ShatterNative.shatter_craft_polish(rules.DbPointer, Raw, (nuint)characterIndex, uid, affixIndex, &r);
            return ToOutcome(status, r);
        }

        /// <summary>Desmontar: o item some e devolve Lascas (<see cref="CraftOutcome.ShardsGained"/>). Equipado e Unico recusam.</summary>
        public CraftOutcome CraftDismantle(NativeRulesCore rules, int characterIndex, ulong uid)
        {
            ShatterCraftResult r = default;
            var status = ShatterNative.shatter_craft_dismantle(rules.DbPointer, Raw, (nuint)characterIndex, uid, &r);
            return ToOutcome(status, r);
        }

        // ------------------------------------------------------------------------------ Vendedor

        static VendorOutcome ToOutcome(int status, in ShatterVendorResult r) =>
            status == 0 ? new VendorOutcome((VendorResult)r.result, r.evicted != 0, (ItemRarity)r.evicted_rarity, r.gold) : VendorOutcome.Failed;

        /// <summary>Vende ao Vendedor (Mochila ou Bau; equipado nao vende): paga o valor do core e poe o item na recompra.</summary>
        public VendorOutcome VendorSell(NativeRulesCore rules, int characterIndex, ItemContainer container, ulong uid)
        {
            ShatterVendorResult r = default;
            var status = ShatterNative.shatter_vendor_sell(rules.DbPointer, Raw, (nuint)characterIndex, (int)container, uid, &r);
            return ToOutcome(status, r);
        }

        /// <summary>Recompra do Vendedor: os 10 ultimos vendidos, o mais recente primeiro, com o preco de cada um.</summary>
        public BuybackInfo VendorBuybackInfo(NativeRulesCore rules)
        {
            var db = rules.DbPointer;
            var save = Raw;
            var status = NativeBuffers.ReadString((byte* o, nuint cap, nuint* needed) =>
                ShatterNative.shatter_vendor_buyback_json(db, save, o, cap, needed), out var json, 2048);
            return status == 0 ? BuybackInfo.FromJson(json) : new BuybackInfo();
        }

        /// <summary>Recompra por uid (repetir nao cobra de novo): 1,25 x o valor pago, o item volta para a Mochila.</summary>
        public VendorOutcome VendorRebuy(NativeRulesCore rules, int characterIndex, ulong uid)
        {
            ShatterVendorResult r = default;
            var status = ShatterNative.shatter_vendor_buyback(rules.DbPointer, Raw, (nuint)characterIndex, uid, &r);
            return ToOutcome(status, r);
        }

        /// <summary>Estoque do Vendedor (o Frasco de Recarga), com preco, maximo levado e quantos o jogador ja tem.</summary>
        public List<VendorStockInfo> VendorStock(NativeRulesCore rules)
        {
            var db = rules.DbPointer;
            var save = Raw;
            var status = NativeBuffers.ReadString((byte* o, nuint cap, nuint* needed) =>
                ShatterNative.shatter_vendor_stock_json(db, save, o, cap, needed), out var json, 512);
            return status == 0 ? VendorStockInfo.ListFromJson(json) : new List<VendorStockInfo>();
        }

        /// <summary>Compra <paramref name="qty"/> (>= 1) do estoque; respeita o maximo levado (Frasco: 3) e o Ouro. "Encher ate 3" = max - Owned.</summary>
        public VendorOutcome VendorBuy(NativeRulesCore rules, string stockId, int qty)
        {
            var id = NativeBuffers.Utf8(stockId);
            ShatterVendorResult r = default;
            int status;
            fixed (byte* p = id) status = ShatterNative.shatter_vendor_buy(rules.DbPointer, Raw, p, (nuint)id.Length, qty, &r);
            return ToOutcome(status, r);
        }

        // ------------------------------------------------------------------------------ Frasco de Recarga

        /// <summary>
        /// Usa um Frasco de Recarga no cinto vivo do personagem: restaura 1 carga da pocao com menos cargas (empate: Vida), sem passar do
        /// maximo, gasta 1 frasco do save e inicia a trava global. Arena e expedicao recusam. O cinto precisa ser o nativo.
        /// </summary>
        public FlaskOutcome UseRefillFlask(NativeRulesCore rules, IPotionBelt belt, FlaskContext context)
        {
            var native = belt as NativePotionBelt;
            if (native == null) return FlaskOutcome.Failed;
            ShatterFlaskResult r = default;
            var status = ShatterNative.shatter_flask_use(rules.DbPointer, Raw, native.Pointer, (int)context, &r);
            if (status != 0) return FlaskOutcome.Failed;
            native.Invalidate();
            return new FlaskOutcome((FlaskResult)r.result, r.potion_index, r.charges_after, r.flasks_left);
        }
    }
}
