using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Echoes.Core;
using Echoes.Interop;
using Echoes.Interop.Native;
using Echoes.UI;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    /// <summary>
    /// Economia pelo cliente (API C 1.6): Vendedor (valor do core, recompra de 10 a 1,25x, Frasco de Recarga com maximo), Encantador (previa e
    /// confirmacao pelo core) e os numeros que a UI le do rules.csv. Tudo com o core nativo e o save real.
    /// </summary>
    [Category("Economia")]
    public sealed class EconomyClientTests
    {
        const long T0 = 1_800_000_000;
        string dir;
        NativeRulesCore rules;
        SaveService saves;

        [SetUp]
        public void SetUp()
        {
            dir = Path.Combine(Path.GetTempPath(), "echoes_economy_" + Guid.NewGuid().ToString("N"));
            rules = (NativeRulesCore)TestWorld.LoadNativeRules();
            saves = new SaveService(dir, new FakeGameClock(T0));
            Assert.IsTrue(saves.NewGame(rules, 0, "Teste"));
        }

        [TearDown]
        public void TearDown()
        {
            saves.Dispose();
            rules.Dispose();
            if (Directory.Exists(dir)) Directory.Delete(dir, true);
        }

        SaveGame Save => saves.Current;

        /// <summary>Rola o loot das tabelas da Cripta ate o save ter o Ouro e as Lascas pedidos; devolve os itens que foram para a Mochila.</summary>
        List<ItemInstanceInfo> Farm(long gold, long shards, int minItems = 0, int minNormal = 0)
        {
            var picked = new List<ItemInstanceInfo>();
            var tables = new[] { "loot.crypt.elite", "loot.crypt.guardian", "loot.crypt.common" };
            for (var i = 0; i < 1500 && (Save.Currency(SaveGame.GoldId) < gold || Save.Currency(SaveGame.ShardsId) < shards || picked.Count < minItems || picked.Count(p => p.Rarity == ItemRarity.Normal) < minNormal); i++)
            {
                var json = Save.DropLoot(rules, tables[i % tables.Length], 3, 0, -1, (ulong)(1000 + i), out _);
                foreach (var item in ItemInstanceInfo.ListFromJson(json))
                    if (Save.Pickup(rules, 0, item.Uid) == PickupDest.Backpack) picked.Add(item);
            }
            Assert.GreaterOrEqual(Save.Currency(SaveGame.GoldId), gold, "Ouro farmado");
            Assert.GreaterOrEqual(Save.Currency(SaveGame.ShardsId), shards, "Lascas farmadas");
            return picked;
        }

        [Test]
        public void RulesCsv_ReadsThePolishStepsAndTheBuybackNumbers()
        {
            Assert.AreEqual(3.0, RulesCsv.Number("polish_max_steps", -1.0, TestWorld.DataDirectory));
            Assert.AreEqual(10.0, RulesCsv.Number("vendor_buyback_slots", -1.0, TestWorld.DataDirectory));
            Assert.AreEqual(1.25, RulesCsv.Number("vendor_buyback_price_factor", -1.0, TestWorld.DataDirectory), 1e-9);
            Assert.AreEqual(-1.0, RulesCsv.Number("chave_que_nao_existe", -1.0, TestWorld.DataDirectory));
        }

        [Test]
        public void Vendor_PaysTheCoreValue_AndBuybackCostsOnePointTwoFiveTimes()
        {
            var items = Farm(0, 0, 1);
            var item = items.First(i => !i.IsUnique);
            var value = Save.SellValue(rules, 0, item.Uid);
            var goldBefore = Save.Currency(SaveGame.GoldId);
            var sold = Save.VendorSell(rules, 0, ItemContainer.Backpack, item.Uid);
            Assert.IsTrue(sold.Ok);
            Assert.AreEqual(value, sold.Gold, "o Vendedor paga o valor do core");
            Assert.AreEqual(goldBefore + value, Save.Currency(SaveGame.GoldId));

            var buyback = Save.VendorBuybackInfo(rules);
            Assert.AreEqual(10, buyback.Capacity, "10 ultimos itens");
            Assert.AreEqual(1, buyback.Count);
            Assert.AreEqual(item.Uid, buyback.Items[0].Item.Uid, "o mais recente primeiro");
            Assert.AreEqual((long)Math.Ceiling(value * 1.25 - 1e-9), buyback.Items[0].Price, "recompra: 1,25 x o valor pago, arredondado para cima");

            var rebought = Save.VendorRebuy(rules, 0, item.Uid);
            Assert.IsTrue(rebought.Ok, rebought.Result.ToString());
            Assert.AreEqual(0, Save.VendorBuybackInfo(rules).Count);
            var again = Save.VendorRebuy(rules, 0, item.Uid);
            Assert.IsFalse(again.Ok, "recomprar de novo nao cobra nem duplica");
        }

        [Test]
        public void Vendor_BuybackKeepsOnlyTheLastTen_AndWarnsBeforeEvicting()
        {
            var items = Farm(0, 0, 12, 0).Where(i => !i.IsUnique).Take(11).ToList();
            Assert.GreaterOrEqual(items.Count, 11, "itens para encher a recompra");
            for (var i = 0; i < 10; i++) Assert.IsTrue(Save.VendorSell(rules, 0, ItemContainer.Backpack, items[i].Uid).Ok);
            var full = Save.VendorBuybackInfo(rules);
            Assert.AreEqual(10, full.Count);
            Assert.IsTrue(full.WouldEvict, "a proxima venda expulsa o mais antigo: a UI avisa antes");
            var eleventh = Save.VendorSell(rules, 0, ItemContainer.Backpack, items[10].Uid);
            Assert.IsTrue(eleventh.Ok);
            Assert.IsTrue(eleventh.Evicted);
            Assert.AreEqual(10, Save.VendorBuybackInfo(rules).Count);
        }

        [Test]
        public void Flask_CarryCapIsThree_AndRefusesTheFourth()
        {
            Farm(300, 0);
            var stock = Save.VendorStock(rules).Find(s => s.RefId == SaveGame.RefillFlaskId);
            Assert.AreEqual(3, stock.CarryCap, "refill_flask_carry_cap");
            Assert.AreEqual(50, stock.PriceGold);
            Assert.AreEqual(0, stock.Owned);
            var gold = Save.Currency(SaveGame.GoldId);
            var fill = Save.VendorBuy(rules, stock.Id, stock.CarryCap - stock.Owned); // "Encher ate 3"
            Assert.IsTrue(fill.Ok, fill.Result.ToString());
            Assert.AreEqual(gold - 3 * stock.PriceGold, Save.Currency(SaveGame.GoldId));
            Assert.AreEqual(3, Save.VendorStock(rules).Find(s => s.RefId == SaveGame.RefillFlaskId).Owned);
            var fourth = Save.VendorBuy(rules, stock.Id, 1);
            Assert.IsFalse(fourth.Ok);
            Assert.AreEqual(VendorResult.CarryCap, fourth.Result, "o botao fica cinza com 'Ja tem o maximo'");
        }

        [Test]
        public void Enchant_QuoteShowsCostsAndReasonsFromTheCore()
        {
            Farm(500, 100, 3, 2);
            var common = Save.ListItems(0, ItemContainer.Backpack).First(i => i.Rarity == ItemRarity.Normal);
            var refine = Save.QuoteCraft(rules, 0, common.Uid, CraftOp.Refine);
            Assert.AreEqual(CraftResult.Ok, refine.Result);
            Assert.Greater(refine.Gold, 0);
            Assert.Greater(refine.Shards, 0);
            Assert.AreEqual(CraftResult.WrongRarity, Save.QuoteCraft(rules, 0, common.Uid, CraftOp.Reforge).Result, "Comum nao reforja: motivo do botao cinza");
            Assert.AreEqual(CraftResult.WrongRarity, Save.QuoteCraft(rules, 0, common.Uid, CraftOp.Add).Result);

            var goldBefore = Save.Currency(SaveGame.GoldId);
            var shardsBefore = Save.Currency(SaveGame.ShardsId);
            var outcome = Save.CraftRefine(rules, 0, common.Uid);
            Assert.IsTrue(outcome.Ok, outcome.Result.ToString());
            Assert.AreEqual(goldBefore - refine.Gold, Save.Currency(SaveGame.GoldId), "cobra exatamente a previa");
            Assert.AreEqual(shardsBefore - refine.Shards, Save.Currency(SaveGame.ShardsId));
            var magic = Save.ListItems(0, ItemContainer.Backpack).First(i => i.Uid == common.Uid);
            Assert.AreEqual(ItemRarity.Magic, magic.Rarity);
            Assert.That(magic.Affixes.Count, Is.InRange(refine.AffixCountMin, refine.AffixCountMax), "a faixa da previa vale");

            var reforge = Save.QuoteCraft(rules, 0, magic.Uid, CraftOp.Reforge);
            Assert.AreEqual(CraftResult.Ok, reforge.Result);
            Assert.Greater(reforge.ShardsWithLock, reforge.ShardsNoLock, "travar 1 afixo custa mais Lascas");
        }

        [Test]
        public void Enchant_AffixRangeComesFromTheContent_AndQualityIsPositionInTheRange()
        {
            Farm(500, 100, 3, 2);
            var common = Save.ListItems(0, ItemContainer.Backpack).First(i => i.Rarity == ItemRarity.Normal);
            Assert.IsTrue(Save.CraftRefine(rules, 0, common.Uid).Ok);
            var magic = Save.ListItems(0, ItemContainer.Backpack).First(i => i.Uid == common.Uid);
            foreach (var affix in magic.Affixes)
            {
                var (min, max, stat, _) = ItemWidgets.AffixRange(rules, affix.AffixId);
                Assert.Less(min, max, affix.AffixId);
                Assert.IsNotEmpty(stat);
                Assert.That(affix.Value, Is.InRange(min - 1e-9, max + 1e-9), "valor sorteado dentro da faixa do CSV");
                Assert.That(ItemWidgets.Quality(affix.Value, min, max), Is.InRange(0f, 1f));
            }
            Assert.AreEqual(0f, ItemWidgets.Quality(5, 5, 10));
            Assert.AreEqual(1f, ItemWidgets.Quality(10, 5, 10));
            Assert.AreEqual(0.5f, ItemWidgets.Quality(7.5, 5, 10), 1e-6);
            Assert.AreEqual(1f, ItemWidgets.Quality(3, 4, 4), "faixa vazia: cheia");
        }
    }
}
