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

namespace Echoes.Tests.PlayMode
{
    /// <summary>
    /// Refugio ponta a ponta no Play: Ilsa inicia a expedicao (heroi ocupado, portal da Cripta retido com dlg.ilsa.busy), o relogio falso avanca,
    /// o Tico coleta uma vez so e o portal leva a Cripta. Save num diretorio temporario e relogio falso (GameSession.Use).
    /// </summary>
    [Category("Refugio")]
    public sealed class RefugePlayTests
    {
        const long T0 = 1_800_000_000;
        string dir;
        FakeGameClock clock;

        [SetUp]
        public void SetUp()
        {
            dir = Path.Combine(Path.GetTempPath(), "echoes_refuge_" + System.Guid.NewGuid().ToString("N"));
            clock = new FakeGameClock(T0);
            GameSession.Use(new SaveService(dir, clock));
            SystemGameClock.DebugOffsetSeconds = 0;
        }

        [TearDown]
        public void TearDown()
        {
            GameSession.Reset();
            Time.timeScale = 1f;
            if (Directory.Exists(dir)) Directory.Delete(dir, true);
        }

        [UnityTest]
        public IEnumerator ExpeditionRunsFromIlsaToTicoAndThePortalRespectsTheBusyHero()
        {
            // Um save novo no slot 1 (com um motor de regras proprio so para criar o jogo).
            Assert.IsTrue(NativeRulesCore.TryCreate(out var rules, out var reason), reason);
            using (rules)
            {
                Assert.AreEqual(RulesStatus.Ok, rules.LoadContent(ContentPaths.ResolveDataDirectory(string.Empty), new List<RulesError>()));
                Assert.IsTrue(GameSession.Save.NewGame(rules, 0, "Playtest"));
            }

            yield return SceneManager.LoadSceneAsync("Refugio", LoadSceneMode.Single);
            yield return null;
            yield return null;

            var controller = Object.FindFirstObjectByType<RefugeController>();
            var hero = Object.FindFirstObjectByType<HeroController>();
            Assert.IsNotNull(controller);
            Assert.IsNotNull(hero);
            Assert.AreEqual(2, Object.FindObjectsByType<InteractableNpc>(FindObjectsSortMode.None).Length, "Ilsa e Tico");

            // Ilsa: antes de dominar a Cripta, a fala e dlg.ilsa.not_dominated (a configuracao nao abre).
            controller.TalkToIlsa();
            Assert.IsTrue(controller.ScreenOpen);
            controller.CloseScreen();
            controller.DebugConquerCrypt();
            Assert.AreEqual(5, GameSession.Save.Current.Summary.MarkerCharges);

            // Configurar (a tela abre) e iniciar pelo relogio confiavel.
            controller.OpenExpeditionScreen();
            Assert.IsTrue(controller.ScreenOpen);
            controller.Config.Hours = 1;
            Assert.AreEqual(StartCheck.Ok, controller.StartExpedition());
            Assert.IsFalse(controller.ScreenOpen);
            Assert.IsTrue(GameSession.Expedition.IsHeroBusy, "heroi ocupado durante a expedicao");

            // Portal da Cripta retido: o heroi fica no Refugio e a fala dlg.ilsa.busy aparece.
            var portal = Object.FindObjectsByType<PortalZone>(FindObjectsSortMode.None).First(p => p.TargetArea == AreaTravel.CryptArea);
            yield return MoveHeroTo(hero, portal.transform.position + new Vector3(8f, 0f, 0f));
            yield return null;
            yield return MoveHeroTo(hero, portal.transform.position);
            yield return null;
            yield return null;
            Assert.AreEqual("Refugio", SceneManager.GetActiveScene().name, "o portal nao leva a Cripta com o heroi em rota");
            var root = Object.FindFirstObjectByType<GameRoot>();
            StringAssert.Contains(root.Localization.Get("dlg.ilsa.busy"), ScreenHost.Current.Toasts.Current);

            // Tico: ainda em curso, depois pronto; coleta uma vez so.
            controller.TalkToTico();
            controller.CloseScreen();
            Assert.AreEqual(ExpeditionPhase.Running, GameSession.Expedition.State(GameSession.NativeRules(root)).Phase);
            clock.Advance(3601);
            Assert.AreEqual(ExpeditionPhase.ReadyToCollect, GameSession.Expedition.State(GameSession.NativeRules(root)).Phase);
            Assert.AreEqual(CollectStatus.Collected, controller.CollectAndShowReport());
            Assert.IsNotNull(controller.LastReport);
            Assert.IsTrue(controller.LastReport.IsEstimate, "selo Estimativa");
            controller.CloseScreen();
            Assert.AreEqual(CollectStatus.Already, controller.CollectAndShowReport(), "coleta uma vez so");
            Assert.IsFalse(GameSession.Expedition.IsHeroBusy, "heroi livre depois de coletar");

            // O save foi gravado na coleta: recarregar do disco nao permite coletar de novo.
            var live = GameSession.NativeRules(root);
            GameSession.Save.Close();
            Assert.AreEqual(LoadOutcome.Ok, GameSession.Save.Load(live, 0));
            Assert.AreEqual(CollectStatus.Already, GameSession.Expedition.Collect(live, out _));
        }

        [UnityTest]
        public IEnumerator PortalTakesTheFreeHeroToTheCryptAndTheCryptPortalBringsHimBack()
        {
            Assert.IsTrue(NativeRulesCore.TryCreate(out var rules, out var reason), reason);
            using (rules)
            {
                rules.LoadContent(ContentPaths.ResolveDataDirectory(string.Empty), new List<RulesError>());
                Assert.IsTrue(GameSession.Save.NewGame(rules, 0, "Viagem"));
            }
            yield return SceneManager.LoadSceneAsync("Refugio", LoadSceneMode.Single);
            yield return null;
            yield return null;
            var hero = Object.FindFirstObjectByType<HeroController>();
            var portal = Object.FindObjectsByType<PortalZone>(FindObjectsSortMode.None).First(p => p.TargetArea == AreaTravel.CryptArea);
            yield return MoveHeroTo(hero, portal.transform.position + new Vector3(8f, 0f, 0f));
            yield return null;
            yield return MoveHeroTo(hero, portal.transform.position);
            for (var i = 0; i < 30 && SceneManager.GetActiveScene().name != "Cripta"; i++) yield return null;
            Assert.AreEqual("Cripta", SceneManager.GetActiveScene().name, "o portal do Refugio leva a Cripta");
            yield return null;
            yield return null;
            var entry = Object.FindObjectsByType<PortalZone>(FindObjectsSortMode.None).First(p => p.TargetArea == "area.refuge");
            Assert.IsTrue(entry.Travels, "os portais da Cripta trocam de cena (nao devolvem ao checkpoint)");
        }

        static IEnumerator MoveHeroTo(HeroController hero, Vector3 position)
        {
            var controller = hero.GetComponent<CharacterController>();
            controller.enabled = false;
            hero.transform.position = new Vector3(position.x, 0f, position.z);
            controller.enabled = true;
            yield return null;
        }
    }
}
