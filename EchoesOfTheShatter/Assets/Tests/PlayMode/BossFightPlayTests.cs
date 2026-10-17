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
    /// O Guardiao DE VERDADE: o heroi (vida de teste por TestSettings.HeroGodMode, nunca no CSV) vence a luta na Cripta. Confere a porta que reabre,
    /// o dominio e as +5 cargas no save, e o Unico da primeira vitoria rolado pelo core (shatter_save_roll_boss_loot) e entregue ao Bau do save.
    /// </summary>
    [Category("BossFight")]
    public sealed class BossFightPlayTests
    {
        string dir;

        [SetUp]
        public void SetUp()
        {
            dir = Path.Combine(Path.GetTempPath(), "echoes_boss_" + System.Guid.NewGuid().ToString("N"));
            GameSession.Use(new SaveService(dir, new FakeGameClock(1_800_000_000)));
            TestSettings.HeroGodMode = true;
        }

        [TearDown]
        public void TearDown()
        {
            TestSettings.HeroGodMode = false;
            GameSession.Reset();
            Time.timeScale = 1f;
            if (Directory.Exists(dir)) Directory.Delete(dir, true);
        }

        [UnityTest, Timeout(240000)]
        public IEnumerator HeroBeatsTheGuardianAndTheCoreGrantsTheUniqueOnTheFirstWin()
        {
            Assert.IsTrue(NativeRulesCore.TryCreate(out var rules, out var reason), reason);
            using (rules)
            {
                rules.LoadContent(ContentPaths.ResolveDataDirectory(string.Empty), new List<RulesError>());
                Assert.IsTrue(GameSession.Save.NewGame(rules, 0, "Guardiao"));
            }
            yield return SceneManager.LoadSceneAsync("Cripta", LoadSceneMode.Single);
            yield return null;
            yield return null;

            var host = Object.FindFirstObjectByType<CombatSystemHost>();
            var hero = Object.FindFirstObjectByType<HeroController>();
            var arena = Object.FindFirstObjectByType<ArenaController>();
            var gate = Object.FindObjectsByType<GateBarrier>(FindObjectsSortMode.None).First(g => g.name == "gate.crypt.arena");
            var boss = arena.Boss;
            Assert.AreEqual("enemy.crypt_guardian", boss.EnemyId);
            Assert.IsFalse(gate.IsClosed);

            // Entra na arena: a porta fecha atras e a luta comeca.
            var controller = hero.GetComponent<CharacterController>();
            controller.enabled = false;
            hero.transform.position = new Vector3(arena.Trigger.center.x, 0f, arena.Trigger.center.y);
            controller.enabled = true;
            for (var i = 0; i < 10 && arena.Phase != ArenaPhase.Fighting; i++) yield return null;
            Assert.AreEqual(ArenaPhase.Fighting, arena.Phase);
            Assert.IsTrue(gate.IsClosed, "a porta fechou atras do heroi");
            yield return new WaitForSeconds(2f);
            Assert.IsNotNull(arena.Boss.Logic.Boss, "o Guardiao nativo acordou");

            // O heroi golpeia por tras do escudo frontal (a origem do golpe fica atras do chefe) ate ele cair, atravessando as fases.
            var skill = host.Rules.FindSkill("skill.warrior.iron_cut");
            var phases = new HashSet<int>();
            var captured = false;
            var landed = 0;
            var attempts = 0;
            var started = Time.realtimeSinceStartup;
            while (!boss.Combatant.IsDead && Time.realtimeSinceStartup - started < 200f)
            {
                var info = boss.Logic.Boss.Info;
                phases.Add(info.Phase);
                var p = boss.Combatant.Position;
                var behind = new PlanarVector(p.X - (float)info.FacingX * 3f, p.Z - (float)info.FacingZ * 3f);
                for (var k = 0; k < 3; k++)
                {
                    attempts++;
                    if (host.Combat.ApplySkillHit(hero.Combatant, boss.Combatant, skill, behind)) landed++;
                }
                // Golpes espacados: o hitstop congela os timers do chefe e golpes a cada quadro o travariam no meio do padrao (a fase 2 so comeca no fim do golpe).
                yield return new WaitForSeconds(0.5f);
                if (!captured && attempts >= 6 && !boss.Combatant.IsDead)
                {
                    // A barra do chefe aparece na luta (a captura hud_chefe.png sai do player: -bossshot, BossShotRunner).
                    var bar = ScreenHost.Current.Root.Q<UnityEngine.UIElements.VisualElement>("boss-bar");
                    Assert.IsNotNull(bar, "BossBarView montada");
                    Assert.AreEqual(UnityEngine.UIElements.DisplayStyle.Flex, bar.style.display.value, "a barra do chefe aparece durante a luta");
                    captured = true;
                }
            }
            Assert.IsTrue(captured, "a barra do chefe foi conferida durante a luta");
            var last = boss.Logic.Boss.Info;
            Assert.IsTrue(boss.Combatant.IsDead, $"o Guardiao caiu (vida {boss.Combatant.Life}/{boss.Combatant.MaxLife}, golpes {landed}/{attempts}, fase {last.Phase}, estado {last.State}, escudo {last.ShieldUp}, invulneravel {last.Invulnerable}, heroi vivo {!hero.Combatant.IsDead})");
            for (var i = 0; i < 30 && arena.Phase != ArenaPhase.Won; i++) yield return null;
            Assert.AreEqual(ArenaPhase.Won, arena.Phase);
            Assert.IsTrue(phases.Contains(1));
            Assert.IsFalse(gate.IsClosed, "a porta reabre ao fim da luta");

            // Dominio e +5 cargas gravados no save (no disco tambem).
            var save = GameSession.Save;
            Assert.AreEqual(5, save.Current.Summary.MarkerCharges, "primeira conquista: +5 cargas");
            Assert.AreEqual(5, RunRecorder.LastReward.ChargesGained);
            Assert.IsTrue(RunRecorder.LastReward.NewConquest);
            Assert.IsTrue(save.Current.CharacterJson(0).Contains(ExpeditionConfig.CryptMap), "dominio da Cripta");

            // Unico da 1a vitoria (garantido pelo core) entregue ao Bau do save.
            Assert.IsFalse(string.IsNullOrEmpty(RunRecorder.LastLootJson), "loot do Guardiao rolado pelo core");
            StringAssert.Contains("\"rarity\":\"unique\"", RunRecorder.LastLootJson);
            // O Unico cai NO CHAO (feixe laranja) pelo core; o contador ja foi gravado antes. Pegar manda para a Mochila (ou o Bau se cheia).
            var rulesNow = GameSession.NativeRules(Object.FindFirstObjectByType<GameRoot>());
            var unique = save.Current.GroundItems().Find(i => i.IsUnique);
            Assert.IsNotNull(unique, "o Unico esta no chao");
            Assert.IsNotNull(Object.FindFirstObjectByType<GroundLootDirector>().Views.TryGetValue(unique.Uid, out var uniqueView) ? uniqueView : null, "com o feixe de raridade");
            Assert.AreEqual(PickupDest.Backpack, save.Current.Pickup(rulesNow, 0, unique.Uid));
            Assert.IsTrue(save.Save(rulesNow));

            var root = Object.FindFirstObjectByType<GameRoot>();
            var live = GameSession.NativeRules(root);
            save.Close();
            Assert.AreEqual(LoadOutcome.Ok, save.Load(live, 0));
            var json = save.Current.ToJson();
            StringAssert.Contains("\"rarity\":\"unique\"", json, "o Unico esta no save do disco");
            StringAssert.Contains(ExpeditionConfig.CryptMap, save.Current.CharacterJson(0));
        }

        [Test]
        public void ToastQueueKeepsEveryNoticeAndLetsTheBannerPassFirst()
        {
            var root = new UnityEngine.UIElements.VisualElement();
            var layer = new ToastLayer(root);
            layer.Show("info 1", ToastKind.Info);   // esta na tela
            layer.Show("info 2", ToastKind.Info);
            layer.Show("cargas", ToastKind.Charges);
            layer.Show("banner", ToastKind.Banner);
            layer.Show("item", ToastKind.Item);
            Assert.AreEqual("info 1", layer.Current, "o que esta na tela nao e cortado");
            Assert.AreEqual(4, layer.PendingCount, "nenhum aviso se perde");
            Assert.AreEqual(3.5f, ToastLayer.SecondsFor(ToastKind.Banner));
            Assert.Greater(ToastLayer.SecondsFor(ToastKind.Banner), ToastLayer.SecondsFor(ToastKind.Info), "duracao por tipo");
        }
    }
}
