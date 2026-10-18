using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using Echoes.Interop.Native;
using Echoes.Presentation;
using Echoes.UI;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;
using UnityEngine.UIElements;

namespace Echoes.Tests.PlayMode
{
    /// <summary>
    /// Fechamento da Cripta no cliente, em Play: Fase 2 do Guardiao, checkpoint (poções, save, retorno visual), morte (textos e save), vitoria (faixa,
    /// RF-50), HUD completo, menus (Continuar, Opcoes, Pausa), relatorio e inventario (atributos, recursos, posicoes escondidas, desfazer).
    /// </summary>
    static class UiTestExtensions
    {
        /// <summary>Clique no botao sem mouse: o evento de "submit" do teclado/controle aciona o Clickable.</summary>
        public static void SendClick(this Button button)
        {
            using (var e = NavigationSubmitEvent.GetPooled())
            {
                e.target = button;
                button.SendEvent(e);
            }
        }
    }

    [Category("Mapa")]
    public sealed class MapaPlayTests
    {
        const long T0 = 1_800_000_000;
        string dir;
        string settingsFile;

        [SetUp]
        public void SetUp()
        {
            dir = Path.Combine(Path.GetTempPath(), "echoes_mapa_" + System.Guid.NewGuid().ToString("N"));
            settingsFile = Path.Combine(Path.GetTempPath(), "echoes_mapa_settings_" + System.Guid.NewGuid().ToString("N") + ".json");
            UserSettings.UseFile(settingsFile);
            GameSession.Use(new SaveService(dir, new FakeGameClock(T0)));
            Assert.IsTrue(NativeRulesCore.TryCreate(out var rules, out var reason), reason);
            using (rules)
            {
                Assert.AreEqual(RulesStatus.Ok, rules.LoadContent(ContentPaths.ResolveDataDirectory(string.Empty), new List<RulesError>()));
                Assert.IsTrue(GameSession.Save.NewGame(rules, 0, "Mapa"));
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

        static IEnumerator LoadScene(string name)
        {
            yield return SceneManager.LoadSceneAsync(name, LoadSceneMode.Single);
            yield return null;
            yield return null;
        }

        static void Teleport(HeroController hero, Vector3 position)
        {
            var controller = hero.GetComponent<CharacterController>();
            controller.enabled = false;
            hero.transform.position = new Vector3(position.x, 0f, position.z);
            controller.enabled = true;
        }

        static VisualElement HudRoot() => Object.FindFirstObjectByType<HudView>().GetComponent<UIDocument>().rootVisualElement;

        // ------------------------------------------------------------------------------------------------ Fase 2

        [UnityTest]
        public IEnumerator SummonEventSpawnsTwoSentinelsAtTheMarks_AndTheyGoAwayWhenTheFightRestarts()
        {
            yield return LoadScene("Cripta");
            var host = Object.FindFirstObjectByType<CombatSystemHost>();
            var arena = Object.FindFirstObjectByType<ArenaController>();
            var summoner = Object.FindFirstObjectByType<BossSummoner>();
            Assert.IsNotNull(summoner);
            var before = Object.FindObjectsByType<EnemyController>(FindObjectsSortMode.None).Count(e => e.EnemyId == "enemy.hollow_sentinel");

            var evt = new BossStateEvent { Owner = arena.Boss.Combatant, Kind = BossEventKind.SummonSpawn, Count = 2, EnemyId = "enemy.hollow_sentinel" };
            host.Events.Publish(in evt);
            yield return null;
            yield return null;
            Assert.AreEqual(2, summoner.Spawned.Count);
            foreach (var sentinel in summoner.Spawned)
            {
                Assert.IsTrue(sentinel.gameObject.activeInHierarchy);
                Assert.IsNotNull(sentinel.Combatant, "registrou no combate");
                Assert.IsFalse(sentinel.Combatant.IsDead);
            }
            Assert.AreEqual(before + 2, Object.FindObjectsByType<EnemyController>(FindObjectsSortMode.None).Count(e => e.EnemyId == "enemy.hollow_sentinel"));

            var reset = new ArenaStateEvent { Phase = ArenaPhase.Waiting }; // morte do heroi: a luta reinicia
            host.Events.Publish(in reset);
            yield return null;
            yield return null;
            Assert.AreEqual(0, summoner.Spawned.Count);
            Assert.AreEqual(before, Object.FindObjectsByType<EnemyController>(FindObjectsSortMode.None).Count(e => e.EnemyId == "enemy.hollow_sentinel"), "nenhuma sobra na cena");
        }

        // ------------------------------------------------------------------------------------------------ checkpoint

        [UnityTest]
        public IEnumerator Checkpoint_RefillsPotionsSavesAndShowsTheReturn()
        {
            yield return LoadScene("Cripta");
            var host = Object.FindFirstObjectByType<CombatSystemHost>();
            var hero = Object.FindFirstObjectByType<HeroController>();
            var hooks = Object.FindFirstObjectByType<CriptaSaveHooks>();
            var zones = Object.FindObjectsByType<CheckpointZone>(FindObjectsSortMode.None).Where(z => z.transform != hero.Checkpoint).ToList();
            Assert.IsNotEmpty(zones, "ha checkpoint alem do primeiro");
            var zone = zones.OrderBy(z => z.name).First();
            TestSettings.HeroGodMode = true;

            hero.Logic.Press(HeroCommand.Potion1);
            yield return new WaitForSeconds(0.6f);
            var potion = hero.Logic.GetPotion(0);
            Assert.Less(potion.Charges, potion.MaxCharges, "gastou uma carga");

            var reached = new List<string>();
            host.Events.Subscribe<CheckpointReachedEvent>((in CheckpointReachedEvent e) => reached.Add(e.CheckpointId));
            var saves = hooks.SaveCount;
            Teleport(hero, zone.transform.position);
            yield return null;
            yield return null;
            yield return new WaitForSeconds(0.2f);

            Assert.AreSame(zone.transform, hero.Checkpoint, "o ponto de retorno mudou");
            Assert.AreEqual(1, reached.Count);
            Assert.AreEqual(potion.MaxCharges, potion.Charges, "as pocoes encheram (regra do core)");
            Assert.Greater(hooks.SaveCount, saves, "salvou ao passar no checkpoint");
            var flash = HudRoot().Q<VisualElement>("checkpoint-flash");
            Assert.IsTrue(flash.ClassListContains("hud__flash--on") || UserSettings.ReduceFlashes, "retorno visual (clarao dourado)");
        }

        // ------------------------------------------------------------------------------------------------ morte

        [UnityTest]
        public IEnumerator Death_ShowsNothingLostThenSavesAfterTheReturn()
        {
            yield return LoadScene("Cripta");
            var root = Object.FindFirstObjectByType<GameRoot>();
            var hero = Object.FindFirstObjectByType<HeroController>();
            var hooks = Object.FindFirstObjectByType<CriptaSaveHooks>();
            var saves = hooks.SaveCount;

            hero.ForceDeathForTest();
            yield return null;
            yield return null;
            var overlay = HudRoot().Q<VisualElement>("death-overlay");
            Assert.IsFalse(overlay.ClassListContains("hud--hidden"), "tela de morte visivel");
            var texts = overlay.Query<Label>().ToList().Select(l => l.text).ToList();
            CollectionAssert.Contains(texts, root.Localization.Get("ui.death.title"));
            CollectionAssert.Contains(texts, root.Localization.Get("ui.death.nothing_lost"), "S-12: Nada foi perdido");
            CollectionAssert.Contains(texts, root.Localization.Get("ui.death.checkpoint"), "fora da arena: volta ao checkpoint");

            yield return new WaitForSeconds(2.2f);
            Assert.IsFalse(hero.Combatant.IsDead, "voltou ao checkpoint");
            Assert.Greater(hooks.SaveCount, saves, "salvou depois de morrer");
        }

        [UnityTest]
        public IEnumerator Death_InTheArenaShowsTheFightRestarts()
        {
            yield return LoadScene("Cripta");
            var root = Object.FindFirstObjectByType<GameRoot>();
            var hero = Object.FindFirstObjectByType<HeroController>();
            var arena = Object.FindFirstObjectByType<ArenaController>();
            Teleport(hero, new Vector3(arena.Trigger.center.x, 0f, arena.Trigger.center.y));
            for (var i = 0; i < 20 && arena.Phase != ArenaPhase.Fighting; i++) yield return null;
            Assert.AreEqual(ArenaPhase.Fighting, arena.Phase);
            hero.ForceDeathForTest();
            yield return null;
            yield return null;
            var texts = HudRoot().Q<VisualElement>("death-overlay").Query<Label>().ToList().Select(l => l.text).ToList();
            CollectionAssert.Contains(texts, root.Localization.Get("ui.death.boss_restart"), "S-12: A luta recomeça");
            CollectionAssert.Contains(texts, root.Localization.Get("ui.death.nothing_lost"));
        }

        // ------------------------------------------------------------------------------------------------ vitoria (RF-50)

        [UnityTest]
        public IEnumerator Victory_WithoutReachingTheArena_DoesNotConquerTheArea()
        {
            yield return LoadScene("Cripta");
            var host = Object.FindFirstObjectByType<CombatSystemHost>();
            var arena = Object.FindFirstObjectByType<ArenaController>();
            Assert.IsFalse(arena.EverTriggered);
            var won = new ArenaStateEvent { Phase = ArenaPhase.Won }; // cheat de teste: chefe vencido sem percorrer a area
            host.Events.Publish(in won);
            yield return null;
            Assert.IsFalse(RunRecorder.LastReward.NewConquest, "A3-08: sem chegar a arena nao grava dominio");
            Assert.AreEqual(0, GameSession.Save.Current.Summary.MarkerCharges);
        }

        [UnityTest]
        public IEnumerator Victory_AfterTheArenaGrantsDomainAndShowsTheBanner()
        {
            yield return LoadScene("Cripta");
            var root = Object.FindFirstObjectByType<GameRoot>();
            var host = Object.FindFirstObjectByType<CombatSystemHost>();
            var hero = Object.FindFirstObjectByType<HeroController>();
            var arena = Object.FindFirstObjectByType<ArenaController>();
            TestSettings.HeroGodMode = true;
            Teleport(hero, new Vector3(arena.Trigger.center.x, 0f, arena.Trigger.center.y));
            for (var i = 0; i < 20 && !arena.EverTriggered; i++) yield return null;
            Assert.IsTrue(arena.EverTriggered);

            var won = new ArenaStateEvent { Phase = ArenaPhase.Won };
            host.Events.Publish(in won);
            yield return null;
            Assert.IsTrue(RunRecorder.LastReward.NewConquest);
            Assert.Greater(GameSession.Save.Current.Summary.MarkerCharges, 0);
            Assert.AreEqual(root.Localization.Get("ui.boss.defeated"), ScreenHost.Current.Banners.Current, "a faixa de vitoria");
            Assert.AreEqual(root.Localization.Get("ui.boss.marker_installed"), ScreenHost.Current.Banners.CurrentSubtitle);
        }

        // ------------------------------------------------------------------------------------------------ HUD

        [UnityTest]
        public IEnumerator Hud_ShowsGoldChargesLevelFervorAndTheAreaBanner()
        {
            Assert.IsTrue(NativeRulesCore.TryCreate(out var seedRules, out var why), why);
            using (seedRules)
            {
                seedRules.LoadContent(ContentPaths.ResolveDataDirectory(string.Empty), new List<RulesError>());
                GameSession.Save.Current.RecordAreaRun(seedRules, 0, ExpeditionConfig.CryptMap, true, true);
                GameSession.Save.Save(seedRules);
            }
            RunState.FervorActive = true;
            yield return LoadScene("Cripta");
            var root = Object.FindFirstObjectByType<GameRoot>();
            yield return new WaitForSeconds(1.3f);
            var hud = HudRoot();
            Assert.AreEqual("Cripta Partida", ScreenHost.Current.Banners.Current, "F-06: faixa com o nome da area");
            Assert.IsNotEmpty(hud.Q<Label>("gold-value").text, "Ouro");
            StringAssert.StartsWith("5/", hud.Q<Label>("charges-value").text, "Cargas do Marco");
            StringAssert.Contains("1", hud.Q<Label>("level-value").text);
            Assert.IsNotEmpty(hud.Q<Label>("xp-value").text);
            Assert.IsFalse(hud.Q<VisualElement>("fervor").ClassListContains("hud--hidden"), "Fervor ativo aparece");

            RunState.FervorActive = false;
            yield return null;
            Assert.IsTrue(hud.Q<VisualElement>("fervor").ClassListContains("hud--hidden"), "sem Fervor, some");

            root.Localization.SetCulture("en");
            yield return null;
            Assert.AreEqual("Gold", hud.Query<LocLabel>().ToList().First(l => l.LocKey == "ui.common.gold").text, "idioma trocado sem reiniciar");
        }

        [UnityTest]
        public IEnumerator Portal_FadesToBlackBeforeSwitchingAndTheNewSceneFadesIn()
        {
            yield return LoadScene("Refugio");
            var hero = Object.FindFirstObjectByType<HeroController>();
            var portal = Object.FindObjectsByType<PortalZone>(FindObjectsSortMode.None).First(p => p.TargetArea == AreaTravel.CryptArea);
            Teleport(hero, portal.transform.position + new Vector3(8f, 0f, 0f));
            yield return null;
            yield return null;
            Teleport(hero, portal.transform.position);
            var sawFade = false;
            var started = Time.realtimeSinceStartup;
            while (Time.realtimeSinceStartup - started < 10f && SceneManager.GetActiveScene().name != "Cripta")
            {
                if (ScreenHost.Current != null && ScreenHost.Current.Fade != null && ScreenHost.Current.Fade.Alpha > 0.05f) sawFade = true;
                yield return null;
            }
            Assert.IsTrue(sawFade, "escureceu antes de trocar");
            Assert.AreEqual("Cripta", SceneManager.GetActiveScene().name);
            yield return null;
            Assert.Greater(ScreenHost.Current.Fade.Alpha, 0f, "a nova cena comeca no preto e clareia");
            yield return new WaitForSeconds(0.8f);
            Assert.AreEqual(0f, ScreenHost.Current.Fade.Alpha, 0.01f);
        }

        // ------------------------------------------------------------------------------------------------ menus

        [UnityTest]
        public IEnumerator MainMenu_ContinueShowsTheSaveLegendVersionAndLogs()
        {
            yield return LoadScene("MainMenu");
            var doc = Object.FindFirstObjectByType<MainMenuController>().GetComponent<UIDocument>().rootVisualElement;
            var cont = doc.Q<Button>("continue");
            Assert.IsNotNull(cont, "com save existente: Continuar");
            var legend = doc.Q<Label>("continue-legend").text;
            StringAssert.Contains("Mapa", legend);
            StringAssert.Contains("Nível 1", legend);
            StringAssert.Contains("Refúgio do Marco", legend);
            StringAssert.Contains(Application.version, doc.Q<Label>("version").text);
            Assert.IsNotNull(doc.Q<Label>("open-logs"));
            Assert.IsNotNull(doc.Q<Button>("options"));
            Assert.IsNull(doc.Q<VisualElement>("expedition-seal"), "sem expedicao pronta, sem selo");
            // Novo jogo sobre um save existente pede para apagar antes (segurar 1 s).
            doc.Q<Button>("play").SendClick();
            yield return null;
            Assert.IsNotNull(doc.Q<Button>("overwrite-hold"));
        }

        [UnityTest]
        public IEnumerator MainMenu_WithoutSaveHasNoContinue_AndNewGameOverASaveAsksFirst()
        {
            GameSession.Save.Close();
            GameSession.Save.Delete(0);
            yield return LoadScene("MainMenu");
            var menu = Object.FindFirstObjectByType<MainMenuController>();
            var doc = menu.GetComponent<UIDocument>().rootVisualElement;
            Assert.IsNull(doc.Q<Button>("continue"), "primeira execucao: so Novo jogo");
            Assert.IsNotNull(doc.Q<Button>("play"));
        }

        [UnityTest]
        public IEnumerator Options_SwitchLanguageRemapDodgeAndShake_WorkAndPersist()
        {
            yield return LoadScene("MainMenu");
            var menu = Object.FindFirstObjectByType<MainMenuController>();
            var root = Object.FindFirstObjectByType<GameRoot>();
            var doc = menu.GetComponent<UIDocument>().rootVisualElement;
            doc.Q<Button>("options").SendClick();
            yield return null;
            Assert.IsTrue(menu.Options.IsOpen);

            // Idioma: troca sem reiniciar e persiste.
            doc.Q<Button>("lang-en").SendClick();
            yield return null;
            Assert.AreEqual("en", root.Localization.Culture);
            Assert.AreEqual("en", UserSettings.Culture);
            Assert.AreEqual("Options", root.Localization.Get("ui.options.title"));

            // Tremor de tela: Normal -> Reduzido -> Desligado.
            doc.Q<Button>("tab-access").SendClick();
            yield return null;
            Assert.AreEqual(ShakeMode.Normal, UserSettings.Shake);
            doc.Q<Button>("shake").SendClick();
            Assert.AreEqual(ShakeMode.Reduced, UserSettings.Shake);
            doc.Q<Button>("shake").SendClick();
            Assert.AreEqual(ShakeMode.Off, UserSettings.Shake);
            Assert.AreEqual(0f, UserSettings.ShakeFactor);

            // Controles: a tabela mostra a esquiva e a acao Interagir.
            doc.Q<Button>("tab-controls").SendClick();
            yield return null;
            Assert.IsNotNull(doc.Q<VisualElement>("row-Dodge"));
            Assert.IsNotNull(doc.Q<VisualElement>("row-Interact"));
            Assert.IsNull(doc.Q<VisualElement>("row-Pause"), "Esc nao e remapeavel");
        }

        [UnityTest]
        public IEnumerator Pause_HasOptionsQuitAndTheSaveWarning()
        {
            yield return LoadScene("Refugio");
            var pause = Object.FindFirstObjectByType<PauseController>();
            var doc = pause.GetComponent<UIDocument>().rootVisualElement;
            pause.SetPaused(true);
            yield return null;
            Assert.IsNotNull(doc.Q<Button>("pause-options"));
            Assert.IsNotNull(doc.Q<Button>("pause-quit"), "Sair do jogo");
            Assert.IsNotNull(doc.Q<Button>("pause-logs"));
            doc.Q<Button>("pause-quit").SendClick();
            yield return null;
            var root = Object.FindFirstObjectByType<GameRoot>();
            CollectionAssert.Contains(doc.Query<Label>().ToList().Select(l => l.text).ToList(), root.Localization.Get("ui.pause.save_warning"), "aviso de salvamento");
            doc.Q<Button>("exit-cancel").SendClick();
            yield return null;
            Assert.IsNotNull(doc.Q<Button>("pause-resume"));
            doc.Q<Button>("pause-options").SendClick();
            yield return null;
            Assert.IsTrue(pause.Options.IsOpen);
            pause.SetPaused(false);
            Assert.IsFalse(pause.Options.IsOpen);
            Assert.AreEqual(1f, Time.timeScale);
        }

        // ------------------------------------------------------------------------------------------------ relatorio

        [UnityTest]
        public IEnumerator Report_HasPlayRouteAndAdjustRule_AndPlayRouteTurnsFervorOn()
        {
            yield return LoadScene("Refugio");
            var controller = Object.FindFirstObjectByType<RefugeController>();
            var root = Object.FindFirstObjectByType<GameRoot>();
            controller.DebugConquerCrypt();
            controller.Config.Hours = 1;
            Assert.AreEqual(StartCheck.Ok, controller.StartExpedition());
            SystemGameClock.DebugOffsetSeconds += 3601;
            try
            {
                controller.StartCollect();
                for (var i = 0; i < 600 && controller.IsCollecting; i++) yield return null;
                Assert.AreEqual(CollectStatus.Collected, controller.LastCollectStatus);
            }
            finally
            {
                SystemGameClock.DebugOffsetSeconds = 0;
            }
            yield return null;
            var doc = ScreenHost.Current.Root;
            Assert.IsNotNull(doc.Q<Button>("report-play-route"), "Jogar esta rota agora");
            Assert.IsNotNull(doc.Q<Button>("report-adjust-rule"), "Ajustar regra");

            controller.AdjustRule(controller.LastReport.TipKey);
            yield return null;
            Assert.IsTrue(controller.ScreenOpen, "abre a configuracao da expedicao");
            Assert.IsFalse(RunState.FervorActive);

            controller.PlayRoute();
            var started = Time.realtimeSinceStartup;
            while (Time.realtimeSinceStartup - started < 10f && SceneManager.GetActiveScene().name != "Cripta") yield return null;
            Assert.AreEqual("Cripta", SceneManager.GetActiveScene().name);
            Assert.IsTrue(RunState.FervorActive, "a rota do relatorio joga com Fervor (RF-32)");
            yield return null;
            yield return null;
            Assert.IsFalse(HudRoot().Q<VisualElement>("fervor").ClassListContains("hud--hidden"));
        }

        // ------------------------------------------------------------------------------------------------ inventario

        [UnityTest]
        public IEnumerator Inventory_ShowsStatsGoldShards_HidesLockedSlots_AndUndoesACommonDiscard()
        {
            yield return LoadScene("Refugio");
            var inventory = Object.FindFirstObjectByType<InventoryController>();
            var root = Object.FindFirstObjectByType<GameRoot>();
            var rules = GameSession.NativeRules(root);
            var save = GameSession.Save.Current;

            // Um item Comum na Mochila (rola a tabela comum ate vir um).
            ItemInstanceInfo common = null;
            for (var i = 0; i < 200 && common == null; i++)
            {
                var json = save.DropLoot(rules, "loot.crypt.common", 3, 0, -1, (ulong)(100 + i), out _);
                foreach (var item in ItemInstanceInfo.ListFromJson(json))
                {
                    if (item.Rarity != ItemRarity.Normal) continue;
                    if (save.Pickup(rules, 0, item.Uid) == PickupDest.Backpack) { common = item; break; }
                }
            }
            Assert.IsNotNull(common, "item Comum para o teste");

            inventory.Show();
            yield return null;
            var doc = ScreenHost.Current.Root;
            Assert.IsNotNull(doc.Q<VisualElement>("stat-life"), "painel de atributos");
            Assert.IsNotNull(doc.Q<VisualElement>("stat-armor"));
            Assert.IsNotNull(doc.Q<VisualElement>("res-gold"), "Ouro");
            Assert.IsNotNull(doc.Q<VisualElement>("res-shards"), "Lascas");
            foreach (var hidden in new[] { "off_hand", "amulet", "ring", "ring2", "belt" })
                Assert.IsNull(doc.Q<VisualElement>("slot-" + hidden), "posicao sem conteudo escondida: " + hidden);
            foreach (var shown in new[] { "main_hand", "head", "body", "hands", "legs", "feet" })
                Assert.IsNotNull(doc.Q<VisualElement>("slot-" + shown), shown);
            Assert.IsNull(doc.Q<VisualElement>("lock"), "sem cadeados");

            // Descartar Comum: sem confirmacao, 5 s para desfazer.
            var before = save.ListItems(0, ItemContainer.Backpack).Count;
            Assert.IsTrue(inventory.SelectUid(common.Uid));
            doc.Q<Button>("act-discard").SendClick();
            yield return null;
            Assert.AreEqual(1, inventory.PendingDiscardCount);
            Assert.IsNull(doc.Q<VisualElement>("discard-modal"), "Comum nao pede confirmacao");
            Assert.AreEqual(before, save.ListItems(0, ItemContainer.Backpack).Count, "o core so descarta quando a janela fecha");
            Assert.IsTrue(inventory.UndoDiscard(common.Uid));
            Assert.AreEqual(0, inventory.PendingDiscardCount);
            Assert.IsTrue(inventory.SelectUid(common.Uid), "o item voltou");

            inventory.SelectUid(common.Uid);
            doc.Q<Button>("act-discard").SendClick();
            yield return new WaitForSeconds(RunRecorderUndoWait());
            Assert.AreEqual(0, inventory.PendingDiscardCount);
            Assert.AreEqual(before - 1, save.ListItems(0, ItemContainer.Backpack).Count, "passados 5 s o descarte vale");
            inventory.Close();
        }

        static float RunRecorderUndoWait() => InventoryController.UndoSeconds + 0.8f;
    }
}
