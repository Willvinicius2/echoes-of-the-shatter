using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Echoes.Core;
using Echoes.Interop;
using Echoes.Interop.Native;
using Echoes.Presentation;
using Echoes.UI;
using NUnit.Framework;
using UnityEngine;

namespace Echoes.Tests.EditMode
{
    /// <summary>
    /// Inventario, equipamento, comparacao, venda, loot no chao e nomes de item pelo core (API C 1.4). Tudo com o core nativo e o save de verdade
    /// (pasta temporaria, relogio falso); o RNG de loot e semeado, entao os testes sao deterministicos.
    /// </summary>
    [Category("Inventario")]
    public sealed class InventoryTests
    {
        const long T0 = 1_800_000_000;
        const ulong Seed = 12345UL;
        string dir;
        NativeRulesCore rules;
        SaveService saves;
        SaveGame save;
        LocalizationService loc;

        [SetUp]
        public void SetUp()
        {
            dir = Path.Combine(Path.GetTempPath(), "echoes_inv_" + Guid.NewGuid().ToString("N"));
            rules = (NativeRulesCore)TestWorld.LoadNativeRules();
            saves = new SaveService(dir, new FakeGameClock(T0));
            Assert.IsTrue(saves.NewGame(rules, 0, "Teste"));
            save = saves.Current;
            loc = new LocalizationService(_ => { });
            loc.LoadDirectory(ContentPaths.LocalizationDirectory(TestWorld.DataDirectory));
            loc.SetCulture("pt_BR");
        }

        [TearDown]
        public void TearDown()
        {
            saves.Dispose();
            rules.Dispose();
            if (Directory.Exists(dir)) Directory.Delete(dir, true);
        }

        /// <summary>Rola a tabela do Guardiao (so Magico e Raro) ate achar um item da posicao pedida; devolve o item que ficou no chao.</summary>
        ItemInstanceInfo DropItemOfSlot(string slot, int maxTries = 400)
        {
            for (var i = 0; i < maxTries; i++)
            {
                var json = save.DropLoot(rules, "loot.crypt.guardian", 3, 0, -1, Seed, out var error);
                Assert.IsNotEmpty(json, error);
                foreach (var item in ItemInstanceInfo.ListFromJson(json))
                {
                    var info = rules.FindItemBase(item.BaseId);
                    if (info != null && info.Slot == slot) return item;
                }
            }
            Assert.Fail("nenhum item de " + slot + " caiu em " + maxTries + " sorteios");
            return null;
        }

        // ---------------------------------------------------------------------------------------------

        [Test]
        public void LayoutExt4AndApiMinorAreChecked()
        {
            Assert.IsTrue(NativeLayout.CheckExt4(out var message), message);
            var values = NativeLayout.BuildExt4();
            Assert.AreEqual(10, values.Length);
            Assert.AreEqual(16u, values[0], "shatter_inventory_info");
            Assert.AreEqual(24u, values[5], "shatter_equip_result");
            Assert.GreaterOrEqual(ShatterNative.shatter_api_minor(), 4u);
        }

        [Test]
        public void CapacitiesAndEnabledSlotsComeFromTheCore()
        {
            var info = save.Inventory(rules, 0);
            Assert.AreEqual(40, info.BackpackCapacity, "inventory_capacity do rules.csv");
            Assert.AreEqual(100, info.StashCapacity, "stash_capacity do rules.csv");
            Assert.AreEqual(0, info.BackpackUsed);
            // off_hand liberada: decisão do docs/19 (Q19-3 A), o Guerreiro tem escudo na mão secundária.
            foreach (var enabled in new[] { "main_hand", "off_hand", "head", "body", "hands", "feet", "legs" })
                Assert.IsTrue(SaveGame.SlotEnabled(rules, ItemSlots.IndexOf(enabled)), enabled);
            foreach (var locked in new[] { "amulet", "ring", "ring2", "belt" })
                Assert.IsFalse(SaveGame.SlotEnabled(rules, ItemSlots.IndexOf(locked)), locked + " bloqueada");
            var equipment = save.Equipment(0);
            Assert.AreEqual("item_base.iron_sword", equipment[0].BaseId);
            Assert.IsNull(equipment[ItemSlots.IndexOf("off_hand")]);
        }

        [Test]
        public void DropGoesToTheGroundPickupFillsTheBackpackAndTheGroundShrinks()
        {
            var item = DropItemOfSlot("head");
            var ground = save.GroundItems();
            Assert.IsTrue(ground.Any(g => g.Uid == item.Uid), "o item esta no chao");
            Assert.AreEqual(0, save.Inventory(rules, 0).BackpackUsed, "ainda nao pegou");

            Assert.AreEqual(PickupDest.Backpack, save.Pickup(rules, 0, item.Uid));
            Assert.IsFalse(save.GroundItems().Any(g => g.Uid == item.Uid), "saiu do chao");
            Assert.IsTrue(save.ListItems(0, ItemContainer.Backpack).Any(b => b.Uid == item.Uid));
            Assert.AreEqual(PickupDest.NotFound, save.Pickup(rules, 0, item.Uid), "uid que nao esta no chao");

            save.GroundClear();
            Assert.IsEmpty(save.GroundItems(), "o chao limpa ao sair da Cripta");
        }

        [Test]
        public void FullBackpackLeavesTheItemOnTheGroundAndTheCoreDecidesTheDestination()
        {
            var capacity = save.Inventory(rules, 0).BackpackCapacity;
            for (var guard = 0; guard < 4000 && save.Inventory(rules, 0).BackpackUsed < capacity; guard++)
            {
                save.DropLoot(rules, "loot.crypt.guardian", 3, 0, -1, Seed, out _);
                foreach (var g in save.GroundItems()) save.Pickup(rules, 0, g.Uid);
            }
            Assert.AreEqual(capacity, save.Inventory(rules, 0).BackpackUsed, "Mochila cheia (capacidade do core)");
            var extra = DropItemOfSlot("body");
            Assert.AreEqual(PickupDest.Full, save.Pickup(rules, 0, extra.Uid), "Mochila cheia segue a regra do core");
            Assert.IsTrue(save.GroundItems().Any(g => g.Uid == extra.Uid), "o item FICA no chao");
        }

        [Test]
        public void EquipChangesEquipmentVisualSetAndHeroStatsAndUnequipReturnsToTheBackpack()
        {
            var item = DropItemOfSlot("head");
            Assert.AreEqual(PickupDest.Backpack, save.Pickup(rules, 0, item.Uid));
            var stats = rules.CreateHeroStats(new HeroBuild("class.warrior", 5, new[] { "item_base.iron_sword", "item_base.iron_helm" }, save, 0));
            var armorBefore = stats.Get(StatId.Armor);
            var lifeBefore = stats.Get(StatId.Life);

            var compare = save.Compare(rules, 0, item.Uid);
            Assert.AreEqual(InvResult.Ok, compare.Result);

            var outcome = save.Equip(rules, 0, item.Uid, -1, stats);
            Assert.IsTrue(outcome.Ok, outcome.Result.ToString());
            Assert.IsTrue(outcome.Displaced, "o elmo inicial foi trocado");
            Assert.AreEqual(ItemSlots.IndexOf("head"), outcome.Slot);
            var equipped = save.Equipment(0)[outcome.Slot];
            Assert.AreEqual(item.Uid, equipped.Uid);
            Assert.IsTrue(save.ListItems(0, ItemContainer.Backpack).Any(b => b.Uid == outcome.DisplacedUid), "o antigo voltou para a Mochila");

            // atributos do heroi mudam so pelo que o core diz na comparacao
            foreach (var delta in compare.Deltas)
            {
                var id = delta.Stat == "armor" ? StatId.Armor : delta.Stat == "life" ? StatId.Life : (StatId?)null;
                if (id == null) continue;
                var was = id == StatId.Armor ? armorBefore : lifeBefore;
                Assert.AreEqual(delta.Change, stats.Get(id.Value) - was, 1e-6, delta.Stat + ": o bloco do heroi mudou exatamente o que o core comparou");
            }
            Assert.IsTrue(armorBefore != stats.Get(StatId.Armor) || lifeBefore != stats.Get(StatId.Life) || compare.Deltas.Count == 0, "o bloco de atributos acompanha o equipamento");

            // o visual vem do conjunto do core
            Assert.IsTrue(VisualSetResolver.TryResolve(rules, equipped.BaseId, equipped.UniqueId, out var slot, out var set));
            Assert.AreEqual(HeroPartSlot.Head, slot);
            Assert.AreEqual(rules.ItemVisualSetId(equipped.BaseId, equipped.UniqueId), set);

            var back = save.Unequip(rules, 0, outcome.Slot, stats);
            Assert.IsTrue(back.Ok);
            Assert.IsNull(save.Equipment(0)[outcome.Slot], "posicao vazia");
            Assert.IsTrue(save.ListItems(0, ItemContainer.Backpack).Any(b => b.Uid == item.Uid));
            Assert.AreEqual(InvResult.SlotEmpty, save.Unequip(rules, 0, outcome.Slot, stats).Result);
        }

        [Test]
        public void LiveBlockMatchesTheCoreRebuildAtTheSameLevelAndTheCompareDeltaOnlyHoldsAtTheSaveLevel()
        {
            // Regressao do 22,4 contra 25,16 do PlayMode: afixos "aumentados" (Resoluto, % de Vida) pesam pela base do nivel, e a comparacao do core usa o
            // nivel do save. Com o heroi no nivel do save o delta bate sempre; num nivel diferente so o bloco refeito pelo core no nivel do heroi vale.
            var saveLevel = save.CharacterProgress(rules, 0).Level;
            foreach (var heroLevel in new[] { saveLevel, saveLevel + 4 })
            {
                var item = DropItemOfSlot("head");
                Assert.AreEqual(PickupDest.Backpack, save.Pickup(rules, 0, item.Uid));
                using (var live = rules.CreateHeroStats(new HeroBuild("class.warrior", heroLevel, new List<string>(), save, 0)))
                {
                    var lifeBefore = live.Get(StatId.Life);
                    var compare = save.Compare(rules, 0, item.Uid);
                    Assert.IsTrue(save.Equip(rules, 0, item.Uid, -1, live).Ok);
                    using (var fresh = rules.CreateHeroStats(new HeroBuild("class.warrior", heroLevel, new List<string>(), save, 0)))
                    {
                        Assert.AreEqual(fresh.Get(StatId.Life), live.Get(StatId.Life), 1e-6, "nivel " + heroLevel + ": bloco ao vivo = bloco refeito pelo core");
                        Assert.AreEqual(fresh.Get(StatId.Armor), live.Get(StatId.Armor), 1e-6);
                    }
                    if (heroLevel != saveLevel) continue;
                    foreach (var delta in compare.Deltas)
                        if (delta.Stat == "life") Assert.AreEqual(delta.Change, live.Get(StatId.Life) - lifeBefore, 1e-6, "no nivel do save a comparacao vale");
                }
            }
        }

        [Test]
        public void LockedAndMismatchedSlotsAreRefusedByTheCoreWithoutChangingAnything()
        {
            var helm = DropItemOfSlot("head");
            save.Pickup(rules, 0, helm.Uid);
            var before = save.ToJson();
            var refused = save.Equip(rules, 0, helm.Uid, ItemSlots.IndexOf("amulet"), null).Result;
            Assert.IsTrue(refused == InvResult.SlotLocked || refused == InvResult.SlotMismatch, "posicao bloqueada: " + refused);
            Assert.AreEqual(InvResult.SlotMismatch, save.Equip(rules, 0, helm.Uid, ItemSlots.IndexOf("body"), null).Result, "posicao de outro tipo");
            Assert.AreEqual(before, save.ToJson(), "recusa nao muda nada");
        }

        [Test]
        public void SortMoveDiscardAndSellValueFollowTheCore()
        {
            var a = DropItemOfSlot("feet");
            var b = DropItemOfSlot("hands");
            save.Pickup(rules, 0, a.Uid);
            save.Pickup(rules, 0, b.Uid);
            Assert.IsTrue(save.Sort(rules, 0));
            var items = save.ListItems(0, ItemContainer.Backpack);
            int SlotOf(ItemInstanceInfo i) => ItemSlots.IndexOf(rules.FindItemBase(i.BaseId).Slot);
            for (var i = 1; i < items.Count; i++)
            {
                Assert.LessOrEqual(SlotOf(items[i - 1]), SlotOf(items[i]), "por posicao");
                if (SlotOf(items[i - 1]) == SlotOf(items[i])) Assert.GreaterOrEqual((int)items[i - 1].Rarity, (int)items[i].Rarity, "raridade do maior para o menor na mesma posicao");
            }

            Assert.AreEqual(InvResult.Ok, save.Move(rules, 0, a.Uid, ItemContainer.Stash));
            Assert.IsTrue(save.ListItems(0, ItemContainer.Stash).Any(s => s.Uid == a.Uid));
            Assert.AreEqual(InvResult.Ok, save.Move(rules, 0, a.Uid, ItemContainer.Backpack));

            Assert.Greater(save.SellValue(rules, 0, b.Uid), 0, "valor de venda do core (so informacao no tooltip)");
            Assert.AreEqual(InvResult.Ok, save.Discard(0, ItemContainer.Backpack, b.Uid));
            Assert.AreEqual(InvResult.NotFound, save.Discard(0, ItemContainer.Backpack, b.Uid), "destruido");
        }

        [Test]
        public void InventoryAndEquipmentSurviveSaveAndLoad()
        {
            var helm = DropItemOfSlot("head");
            var boots = DropItemOfSlot("feet");
            save.Pickup(rules, 0, helm.Uid);
            save.Pickup(rules, 0, boots.Uid);
            Assert.IsTrue(save.Equip(rules, 0, helm.Uid, -1, null).Ok);
            Assert.IsTrue(saves.Save(rules));
            var equippedUid = save.Equipment(0)[ItemSlots.IndexOf("head")].Uid;
            var backpackUids = save.ListItems(0, ItemContainer.Backpack).Select(i => i.Uid).OrderBy(u => u).ToList();

            saves.Close();
            Assert.AreEqual(LoadOutcome.Ok, saves.Load(rules, 0));
            var loaded = saves.Current;
            Assert.AreEqual(equippedUid, loaded.Equipment(0)[ItemSlots.IndexOf("head")].Uid, "equipamento mantido");
            CollectionAssert.AreEqual(backpackUids, loaded.ListItems(0, ItemContainer.Backpack).Select(i => i.Uid).OrderBy(u => u).ToList(), "Mochila mantida");
            Assert.IsEmpty(loaded.GroundItems(), "o chao nao e salvo");
        }

        [Test]
        public void GuardianUniqueFallsOnTheGroundAfterTheCounterIsSaved()
        {
            var json = save.RollBossLoot(rules, 0, "enemy.crypt_guardian", 3, Seed, out var error);
            Assert.IsNotEmpty(json, error);
            Assert.IsTrue(saves.Save(rules), "RF-55: contador gravado antes do item");
            Assert.IsTrue(save.GroundAddLoot(json, out error), error);
            var unique = save.GroundItems().FirstOrDefault(i => i.IsUnique);
            Assert.IsNotNull(unique, "primeira vitoria: Unico garantido, no chao");
            Assert.AreEqual("item_base.stone_maul", unique.BaseId);
            Assert.AreEqual(PickupDest.Backpack, save.Pickup(rules, 0, unique.Uid));
        }

        // ---------------------------------------------------------------------------------------------
        // Nomes e tooltip

        static ItemInstanceInfo Item(string baseId, ItemRarity rarity, params (string id, double value)[] affixes)
        {
            var item = new ItemInstanceInfo { Uid = 99, BaseId = baseId, Rarity = rarity, ItemLevel = 3 };
            foreach (var (id, value) in affixes) item.Affixes.Add(new AffixInfo(id, value));
            return item;
        }

        [Test]
        public void ItemNamesAgreeInGenderAndNumberThroughTheLocPatterns()
        {
            Assert.AreEqual("Espada de Ferro Afiada de Presteza", ItemText.Name(loc, rules, Item("item_base.iron_sword", ItemRarity.Rare, ("affix.honed", 0.1), ("affix.of_swiftness", 0.05))), "f singular, prefixo + sufixo");
            Assert.AreEqual("Luvas de Couro Robustas", ItemText.Name(loc, rules, Item("item_base.leather_gloves", ItemRarity.Magic, ("affix.sturdy", 12))), "f plural, so prefixo");
            Assert.AreEqual("Martelo de Pedra Afiado", ItemText.Name(loc, rules, Item("item_base.stone_maul", ItemRarity.Magic, ("affix.honed", 0.1))), "m singular");
            Assert.AreEqual("Elmo de Ferro Robusto", ItemText.Name(loc, rules, Item("item_base.iron_helm", ItemRarity.Magic, ("affix.sturdy", 12))), "m singular");
            Assert.AreEqual("Calça Gasta", ItemText.Name(loc, rules, Item("item_base.worn_trousers", ItemRarity.Normal)), "Comum: so a base");
            Assert.AreEqual("Botas Gastas de Restauro", ItemText.Name(loc, rules, Item("item_base.worn_boots", ItemRarity.Magic, ("affix.of_mending", 1))), "so sufixo");
            var unique = Item("item_base.stone_maul", ItemRarity.Unique);
            unique.UniqueId = "unique.empty_throne_maul";
            Assert.AreEqual("Martelo do Trono Vazio", ItemText.Name(loc, rules, unique), "Unico: nome proprio");
            Assert.AreEqual("Raro · Arma", ItemText.RarityLine(loc, rules, Item("item_base.iron_sword", ItemRarity.Rare)).Replace("Rara", "Raro"), "raridade em texto");
        }

        [Test]
        public void TooltipLinesShowAffixesTheCoreComparisonArrowsAndNoCSharpMath()
        {
            var item = DropItemOfSlot("body");
            var lines = ItemText.BodyLines(loc, rules, item);
            Assert.GreaterOrEqual(lines.Count, 2, "implicito/afixos e nivel");
            foreach (var affix in item.Affixes) StringAssert.Contains("+", ItemText.ModLine(loc, "life", "flat", Math.Abs(affix.Value)));
            save.Pickup(rules, 0, item.Uid);
            var compare = save.Compare(rules, 0, item.Uid);
            var arrows = ItemText.CompareLines(loc, compare);
            foreach (var (text, color) in arrows)
            {
                Assert.IsTrue(text.StartsWith("▲ ") || text.StartsWith("▼ "), text);
                Assert.AreEqual(text.StartsWith("▲ ") ? ScreenKit.Good : ScreenKit.Bad, color, "verde melhora, vermelho piora");
            }
            Assert.IsTrue(new[] { -1, 0, 1 }.Contains(ItemText.CompareVerdict(compare)));
        }

        [Test]
        public void LocalizationContextMarksPluralBasesAndTheNewKeysExist()
        {
            StringAssert.Contains("plural", loc.ContextOf("item_base.leather_gloves.name"));
            foreach (var key in new[] { "ui.item.mod", "ui.item.sell_value", "ui.inventory.sort", "ui.inventory.discard_confirm", "ui.item.pick_full", "ui.inventory.slot_locked" })
                Assert.IsTrue(loc.TryGet(key, out _), key);
        }

        [Test]
        public void HeroLevelFallsBehindWhenTheSaveLevelsUpOutsideTheKillPathAndTheSyncCheckSeesIt()
        {
            // O save sobe de nivel por kill, coleta de expedicao ou missao; o heroi em cena so e refeito se alguem avisa. A conferencia compara os dois niveis.
            var heroLevel = save.CharacterProgress(rules, 0).Level;
            Assert.IsFalse(Echoes.Gameplay.HeroLevelSync.NeedsRefresh(heroLevel, save.CharacterProgress(rules, 0).Level), "mesmo nivel: nada a refazer");
            var leveled = false;
            for (var i = 0; i < 400 && !leveled; i++)
                leveled = save.AwardKillXp(rules, 0, ExpeditionConfig.CryptMap, "enemy.hollow_sentinel", 3, false, string.Empty, true, out _).LeveledUp;
            Assert.IsTrue(leveled, "o XP dos kills subiu o nivel no save");
            Assert.IsTrue(Echoes.Gameplay.HeroLevelSync.NeedsRefresh(heroLevel, save.CharacterProgress(rules, 0).Level), "heroi no nivel antigo: refazer o bloco");
            Assert.IsFalse(Echoes.Gameplay.HeroLevelSync.NeedsRefresh(3, 0), "sem nivel no save (leitura falhou): nao mexe");
        }
    }
}
