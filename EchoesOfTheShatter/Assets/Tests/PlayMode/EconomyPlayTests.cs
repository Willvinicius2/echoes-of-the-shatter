using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using Echoes.Interop.Native;
using Echoes.UI;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;
using UnityEngine.UIElements;

namespace Echoes.Tests.PlayMode
{
    /// <summary>
    /// Refugio com Vendedor (S-14), Encantador (S-15) e Bau (S-04), Frasco de Recarga na Cripta e subida de nivel imediata no heroi.
    /// </summary>
    [Category("Economia")]
    public sealed class EconomyPlayTests
    {
        const long T0 = 1_800_000_000;
        string dir;
        string settingsFile;
        FakeGameClock clock;

        [SetUp]
        public void SetUp()
        {
            dir = Path.Combine(Path.GetTempPath(), "echoes_economy_play_" + System.Guid.NewGuid().ToString("N"));
            settingsFile = Path.Combine(Path.GetTempPath(), "echoes_economy_play_settings_" + System.Guid.NewGuid().ToString("N") + ".json");
            UserSettings.UseFile(settingsFile);
            clock = new FakeGameClock(T0);
            GameSession.Use(new SaveService(dir, clock));
            Assert.IsTrue(NativeRulesCore.TryCreate(out var rules, out var reason), reason);
            using (rules)
            {
                Assert.AreEqual(RulesStatus.Ok, rules.LoadContent(ContentPaths.ResolveDataDirectory(string.Empty), new List<RulesError>()));
                Assert.IsTrue(GameSession.Save.NewGame(rules, 0, "Economia"));
                Farm(rules, 900, 150, 4);
                GameSession.Save.Save(rules);
            }
            RunState.Reset();
        }

        [TearDown]
        public void TearDown()
        {
            GameSession.Reset();
            RunState.Reset();
            UserSettings.UseFile(null);
            Time.timeScale = 1f;
            TestSettings.HeroGodMode = false;
            if (Directory.Exists(dir)) Directory.Delete(dir, true);
            if (File.Exists(settingsFile)) File.Delete(settingsFile);
        }

        static void Farm(NativeRulesCore rules, long gold, long shards, int minItems)
        {
            var save = GameSession.Save.Current;
            var items = 0;
            for (var i = 0; i < 500 && (save.Currency(SaveGame.GoldId) < gold || save.Currency(SaveGame.ShardsId) < shards || items < minItems); i++)
            {
                var json = save.DropLoot(rules, i % 2 == 0 ? "loot.crypt.guardian" : "loot.crypt.common", 3, 0, -1, (ulong)(2000 + i), out _);
                foreach (var item in ItemInstanceInfo.ListFromJson(json))
                    if (save.Pickup(rules, 0, item.Uid) == PickupDest.Backpack) items++;
            }
        }

        static IEnumerator Load(string scene)
        {
            yield return SceneManager.LoadSceneAsync(scene, LoadSceneMode.Single);
            yield return null;
            yield return null;
        }

        static NativeRulesCore Rules() => GameSession.NativeRules(Object.FindFirstObjectByType<GameRoot>());
        static SaveGame Save => GameSession.Save.Current;
        static VisualElement Root() => ScreenHost.Current.Root;

        static void Teleport(HeroController hero, Vector3 position)
        {
            var controller = hero.GetComponent<CharacterController>();
            controller.enabled = false;
            hero.transform.position = new Vector3(position.x, 0f, position.z);
            controller.enabled = true;
        }

        // ------------------------------------------------------------------------------------------------ pontos do Refugio

        [UnityTest, Timeout(240000)]
        public IEnumerator Refuge_HasTheFiveInteractionPoints_AndEachOneOpensItsScreen()
        {
            yield return Load("Refugio");
            var ids = Object.FindObjectsByType<InteractableNpc>(FindObjectsSortMode.None).Select(n => n.npcId).OrderBy(x => x).ToList();
            CollectionAssert.AreEquivalent(new[] { "enchanter", "ilsa", "stash", "tico", "vendor" }, ids);
            var controller = Object.FindFirstObjectByType<RefugeController>();
            var hero = Object.FindFirstObjectByType<HeroController>();
            var points = Object.FindObjectsByType<InteractableNpc>(FindObjectsSortMode.None);
            foreach (var a in points)
                foreach (var b in points)
                    Assert.LessOrEqual(Vector3.Distance(a.transform.position, b.transform.position), 24f, "pontos proximos uns dos outros (docs/16 S-04: ate 12 m do heroi andando)");

            // O aviso mostra o nome pela chave de Loc e Interagir abre a tela do ponto.
            var vendorPoint = points.First(n => n.npcId == "vendor");
            Teleport(hero, vendorPoint.transform.position + new Vector3(1f, 0f, 0f));
            yield return null;
            yield return null;
            var prompt = Root().Query<Label>().ToList().Select(l => l.text).FirstOrDefault(t => t.Contains("Vendedor"));
            Assert.IsNotNull(prompt, "aviso [F] Vendedor");
            controller.Interact("vendor");
            Assert.IsTrue(controller.ScreenOpen);
            Assert.IsNotNull(Root().Q<VisualElement>("vendor-body"));
            controller.CloseScreen();
            controller.Interact("enchanter");
            Assert.IsNotNull(Root().Q<VisualElement>("enchant-body"));
            controller.CloseScreen();
            controller.Interact("stash");
            yield return null;
            Assert.IsTrue(InventoryController.IsOpen, "o Bau abre o inventario");
            Object.FindFirstObjectByType<InventoryController>().Close();
        }

        // ------------------------------------------------------------------------------------------------ Vendedor

        [UnityTest, Timeout(240000)]
        public IEnumerator Vendor_SellsByTheCoreValue_RebuysAndBuysFlasksUpToTheCap()
        {
            yield return Load("Refugio");
            var controller = Object.FindFirstObjectByType<RefugeController>();
            var rules = Rules();
            var screen = controller.OpenVendor();
            Assert.IsNotNull(screen);
            var item = Save.ListItems(0, ItemContainer.Backpack).First(i => !i.IsUnique && i.Rarity != ItemRarity.Rare);
            var value = Save.SellValue(rules, 0, item.Uid);
            var goldBefore = Save.Currency(SaveGame.GoldId);
            var used = Save.Inventory(rules, 0).BackpackUsed;

            screen.SelectForTest(item, ItemContainer.Backpack);
            Assert.IsNotNull(Root().Q<VisualElement>("sell-detail"));
            StringAssert.Contains(value.ToString(), Root().Q<Label>("sell-value").text, "Vale N Ouro (valor do core)");

            // Comum e Magico: sem confirmacao e com 5 s para desfazer (o core so vende quando a janela fecha).
            Root().Q<Button>("act-sell").SendClickForTest();
            yield return null;
            Assert.AreEqual(1, screen.PendingCount);
            Assert.IsNull(Root().Q<VisualElement>("vendor-modal"));
            Assert.AreEqual(goldBefore, Save.Currency(SaveGame.GoldId), "ainda nao vendeu");
            Assert.IsTrue(screen.UndoSale(item.Uid));
            Assert.AreEqual(0, screen.PendingCount);
            Assert.AreEqual(used, Save.Inventory(rules, 0).BackpackUsed);

            var outcome = screen.SellNow(item.Uid, ItemContainer.Backpack, true);
            Assert.IsTrue(outcome.Ok);
            Assert.AreEqual(goldBefore + value, Save.Currency(SaveGame.GoldId));

            // Recomprar: o item volta pelo preco do core (1,25x).
            screen.SetTab(VendorScreen.Tab.Buyback);
            var row = Root().Q<VisualElement>("buyback-row");
            Assert.IsNotNull(row, "a venda aparece na recompra");
            var price = Save.VendorBuybackInfo(rules).Items[0].Price;
            Assert.AreEqual((long)System.Math.Ceiling(value * 1.25 - 1e-9), price);
            var rebought = screen.Rebuy(item.Uid);
            Assert.IsTrue(rebought.Ok);
            Assert.AreEqual(goldBefore + value - price, Save.Currency(SaveGame.GoldId));
            Assert.AreEqual(used, Save.Inventory(rules, 0).BackpackUsed, "o item voltou para a Mochila");

            // Frascos: comprar 1, encher ate 3 e o quarto fica cinza com o motivo.
            screen.SetTab(VendorScreen.Tab.Flasks);
            Assert.IsNotNull(Root().Q<Button>("act-buy-flask"));
            StringAssert.Contains("0/3", Root().Q<Label>("flask-owned").text);
            Assert.IsTrue(screen.BuyFlask("vendor.refill_flask", 1).Ok);
            Assert.IsTrue(screen.BuyFlask("vendor.refill_flask", 2).Ok);
            StringAssert.Contains("3/3", Root().Q<Label>("flask-owned").text);
            Assert.IsFalse(Root().Q<Button>("act-buy-flask").enabledSelf, "no maximo: botao cinza");
            StringAssert.Contains("máximo", Root().Query<Label>("reason").ToList().First().text.ToLowerInvariant());
            controller.CloseScreen();
        }

        [UnityTest, Timeout(240000)]
        public IEnumerator Vendor_MarkedItemsSumTheirCoreValue_AndRareAsksForConfirmation()
        {
            yield return Load("Refugio");
            var controller = Object.FindFirstObjectByType<RefugeController>();
            var rules = Rules();
            var screen = controller.OpenVendor();
            var items = Save.ListItems(0, ItemContainer.Backpack).Where(i => !i.IsUnique).Take(3).ToList();
            Assert.GreaterOrEqual(items.Count, 2);
            var expected = items.Sum(i => Save.SellValue(rules, 0, i.Uid));
            var cells = Root().Query<VisualElement>("cell").ToList();
            Assert.IsNotEmpty(cells);
            foreach (var item in items) screen.SelectForTest(item, ItemContainer.Backpack);
            foreach (var item in items) screen.MarkForTest(item.Uid);
            var total = Root().Q<Label>("marked-total");
            Assert.IsNotNull(total, "Vender marcados mostra o total e a contagem por raridade");
            StringAssert.Contains(expected.ToString(), total.text);
            controller.CloseScreen();
        }

        // ------------------------------------------------------------------------------------------------ Encantador

        [UnityTest, Timeout(240000)]
        public IEnumerator Enchanter_RefineAddPolishAndDismantle_FollowTheCore_WithCostsAndReasons()
        {
            yield return Load("Refugio");
            var controller = Object.FindFirstObjectByType<RefugeController>();
            var rules = Rules();
            var screen = controller.OpenEnchanter();
            Assert.IsNotNull(screen);

            // Uma peca de armadura Comum (armas nao tem afixo para adicionar).
            var common = Save.ListItems(0, ItemContainer.Backpack).First(i => i.Rarity == ItemRarity.Normal && rules.FindItemBase(i.BaseId).Slot != "main_hand");
            screen.SelectItem(common.Uid);
            Assert.IsNotNull(Root().Q<VisualElement>("enchant-ops"));
            // Comum: so Refinar e Desmontar; o resto cinza com o motivo escrito.
            Assert.IsTrue(Root().Q<Button>("btn-refine").enabledSelf);
            Assert.IsFalse(Root().Q<Button>("btn-reforge").enabledSelf);
            var reasons = Root().Query<Label>("reason").ToList().Select(l => l.text).ToList();
            CollectionAssert.Contains(reasons, "Raridade não permitida");
            Assert.IsNotNull(Root().Q<Label>("cost-gold"), "custo em Ouro sempre visivel");
            Assert.IsNotNull(Root().Q<Label>("cost-shards"), "custo em Lascas sempre visivel");

            // Refinar: confirmacao com a faixa e o custo; o item vira Magico e o Ouro cai exatamente a previa.
            var quote = Save.QuoteCraft(rules, 0, common.Uid, CraftOp.Refine);
            var goldBefore = Save.Currency(SaveGame.GoldId);
            screen.ChooseOpForTest(CraftOp.Refine);
            Assert.IsNotNull(Root().Q<VisualElement>("confirm-box"));
            Root().Q<Button>("confirm").SendClickForTest();
            yield return null;
            var magic = Save.ListItems(0, ItemContainer.Backpack).First(i => i.Uid == common.Uid);
            Assert.AreEqual(ItemRarity.Magic, magic.Rarity);
            Assert.AreEqual(goldBefore - quote.Gold, Save.Currency(SaveGame.GoldId));
            Assert.IsNotNull(Root().Q<Label>("enchant-message"), "toast Item melhorado");

            // Adicionar afixo: 3 candidatos do core; escolhe 1; depois o botao fica cinza (ja recebeu um afixo adicionado).
            if (magic.Affixes.Count < 2)
            {
                screen.ChooseOpForTest(CraftOp.Add);
                var candidates = Root().Query<VisualElement>().Where(e => e.name != null && e.name.StartsWith("candidate-")).ToList();
                Assert.That(candidates.Count, Is.InRange(1, 3));
                screen.SelectOfferForTest(0);
                var before = magic.Affixes.Count;
                Root().Q<Button>("confirm").SendClickForTest();
                yield return null;
                var after = Save.ListItems(0, ItemContainer.Backpack).First(i => i.Uid == common.Uid);
                Assert.AreEqual(before + 1, after.Affixes.Count);
                Assert.IsFalse(Root().Q<Button>("btn-add").enabledSelf);
                CollectionAssert.Contains(Root().Query<Label>("reason").ToList().Select(l => l.text).ToList(), "Já recebeu um afixo adicionado");
            }

            // Lapidar: valor atual -> valor novo e o custo do passo.
            screen.ChooseOpForTest(CraftOp.Polish);
            screen.SelectAffixForTest(0);
            StringAssert.Contains("→", Root().Q<Label>("polish-preview").text);
            var affixBefore = Save.ListItems(0, ItemContainer.Backpack).First(i => i.Uid == common.Uid).Affixes[0];
            Root().Q<Button>("confirm").SendClickForTest();
            yield return null;
            var polished = Save.ListItems(0, ItemContainer.Backpack).First(i => i.Uid == common.Uid).Affixes[0];
            Assert.AreEqual(affixBefore.Polish + 1, polished.Polish, "um passo de lapidacao");
            Assert.GreaterOrEqual(polished.Value, affixBefore.Value);

            // Reforjar: aviso fixo "Nao da para desfazer" e a trava de 1 afixo.
            screen.ChooseOpForTest(CraftOp.Reforge);
            StringAssert.Contains("Não dá para desfazer", Root().Q<Label>("warn-reforge").text);
            screen.SelectAffixForTest(0);
            screen.SelectAffixForTest(0); // clicar de novo destrava
            controller.CloseScreen();
        }

        [UnityTest, Timeout(240000)]
        public IEnumerator Enchanter_UniqueIsUntouchable_AndEquippedChangesRefreshTheHeroStats()
        {
            yield return Load("Refugio");
            var controller = Object.FindFirstObjectByType<RefugeController>();
            var hero = Object.FindFirstObjectByType<HeroController>();
            var rules = Rules();
            // Unico do Guardiao no Bau (RollBossLoot + AddLoot).
            var json = Save.RollBossLoot(rules, 0, "enemy.crypt_guardian", 3, 42UL, out var error);
            Assert.IsNotEmpty(json, error);
            Assert.IsTrue(Save.AddLoot(json, out error), error);
            var unique = Save.ListItems(0, ItemContainer.Stash).First(i => i.IsUnique);
            var screen = controller.OpenEnchanter();
            screen.SelectItem(unique.Uid);
            foreach (var name in new[] { "btn-refine", "btn-reforge", "btn-add", "btn-polish", "btn-dismantle" })
                Assert.IsFalse(Root().Q<Button>(name).enabledSelf, name + " cinza no Unico");
            CollectionAssert.Contains(Root().Query<Label>("reason").ToList().Select(l => l.text).ToList(), "Item único não pode ser melhorado");
            controller.CloseScreen();

            // Peca equipada: melhorar refaz o bloco de atributos do heroi pelo core.
            var weapon = Save.Equipment(0)[0];
            Assert.IsNotNull(weapon);
            var statsBefore = hero.Combatant.Stats;
            screen = controller.OpenEnchanter();
            screen.SelectItem(weapon.Uid);
            screen.ChooseOpForTest(CraftOp.Refine);
            Root().Q<Button>("confirm").SendClickForTest();
            yield return null;
            Assert.AreNotSame(statsBefore, hero.Combatant.Stats, "o heroi recebeu o bloco novo do core");
            Assert.AreEqual(ItemRarity.Magic, Save.Equipment(0)[0].Rarity);
            controller.CloseScreen();
        }

        // ------------------------------------------------------------------------------------------------ Frasco na Cripta

        [UnityTest, Timeout(240000)]
        public IEnumerator Flask_RestoresOneChargeInTheRun_ButNotInTheArena()
        {
            var rules0 = Rules0();
            Assert.IsTrue(Save.VendorBuy(rules0, "vendor.refill_flask", 3).Ok);
            rules0.Dispose();
            yield return Load("Cripta");
            var hero = Object.FindFirstObjectByType<HeroController>();
            var arena = Object.FindFirstObjectByType<ArenaController>();
            var user = Object.FindFirstObjectByType<FlaskUser>();
            TestSettings.HeroGodMode = true;
            hero.Logic.Press(HeroCommand.Potion1);
            yield return new WaitForSeconds(0.8f);
            var potion = hero.Logic.GetPotion(0);
            Assert.Less(potion.Charges, potion.MaxCharges);
            yield return new WaitForSeconds(1.2f); // trava global entre usos
            var before = potion.Charges;
            var outcome = user.Use();
            Assert.IsTrue(outcome.Ok, outcome.Result.ToString());
            Assert.AreEqual(before + 1, hero.Logic.GetPotion(outcome.PotionIndex).Charges, "restaura 1 carga");
            Assert.AreEqual(2, outcome.FlasksLeft, "gasta 1 frasco do save");

            Teleport(hero, new Vector3(arena.Trigger.center.x, 0f, arena.Trigger.center.y));
            for (var i = 0; i < 20 && arena.Phase != ArenaPhase.Fighting; i++) yield return null;
            hero.Logic.Press(HeroCommand.Potion1);
            yield return new WaitForSeconds(1.0f);
            var blocked = user.Use();
            Assert.AreEqual(FlaskResult.ArenaLocked, blocked.Result, "bloqueado na arena do Guardiao");
            Assert.AreEqual(2, Save.VendorStock(GameSession.NativeRules(Object.FindFirstObjectByType<GameRoot>())).Find(s => s.RefId == SaveGame.RefillFlaskId).Owned, "nao gastou");
        }

        static NativeRulesCore Rules0()
        {
            Assert.IsTrue(NativeRulesCore.TryCreate(out var rules, out var reason), reason);
            rules.LoadContent(ContentPaths.ResolveDataDirectory(string.Empty), new List<RulesError>());
            return rules;
        }

        // ------------------------------------------------------------------------------------------------ nivel imediato

        [UnityTest, Timeout(300000)]
        public IEnumerator LevelUp_AppliesAtOnce_StatsAndSkillUnlocks()
        {
            yield return Load("Cripta");
            var host = Object.FindFirstObjectByType<CombatSystemHost>();
            var hero = Object.FindFirstObjectByType<HeroController>();
            TestSettings.HeroGodMode = true;
            Assert.AreEqual(1, hero.Combatant.Level);
            var maxLifeBefore = hero.Combatant.MaxLife;
            var statsBefore = hero.Combatant.Stats;
            var unlockedBefore = Enumerable.Range(0, HeroCombatLogic.SlotCount).Count(i => hero.Logic.GetSlot(i).Unlocked);

            var skill = host.Rules.FindSkill("skill.warrior.iron_cut");
            var enemies = Object.FindObjectsByType<EnemyController>(FindObjectsSortMode.None).Where(e => e.EnemyId != "enemy.crypt_guardian").ToList();
            foreach (var enemy in enemies)
            {
                for (var i = 0; i < 400 && !enemy.Combatant.IsDead; i++) host.Combat.ApplySkillHit(hero.Combatant, enemy.Combatant, skill, hero.Combatant.Position);
                if (hero.Combatant.Level > 1) break;
            }
            yield return null;
            var progress = Save.CharacterProgress(GameSession.NativeRules(Object.FindFirstObjectByType<GameRoot>()), 0);
            Assert.Greater(progress.Level, 1, "os kills do teste sobem o nivel no save");
            Assert.AreEqual(progress.Level, hero.Combatant.Level, "o heroi tem o nivel novo na hora, sem reentrar na area");
            Assert.AreNotSame(statsBefore, hero.Combatant.Stats, "o core recalculou o bloco de atributos");
            Assert.Greater(hero.Combatant.MaxLife, maxLifeBefore, "mais vida maxima (class_stats.csv: perLevel)");
            var unlockedAfter = Enumerable.Range(0, HeroCombatLogic.SlotCount).Count(i => hero.Logic.GetSlot(i).Unlocked);
            Assert.Greater(unlockedAfter, unlockedBefore, "habilidades do novo nivel liberadas (skills.csv: unlockLevel)");
        }
    }

    static class EconomyUiTestExtensions
    {
        public static void SendClickForTest(this Button button)
        {
            using (var e = NavigationSubmitEvent.GetPooled())
            {
                e.target = button;
                button.SendEvent(e);
            }
        }
    }
}
