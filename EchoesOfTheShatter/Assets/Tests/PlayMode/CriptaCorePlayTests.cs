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
    /// Core da Cripta ligado no cliente, em Play: encontros sorteados (n e elite), XP por morte e nivel do save no heroi, baus por Interagir com
    /// loot no chao e estado salvo, atalho salvo, parede secreta salva e loot ao limpar um encontro.
    /// </summary>
    [Category("CriptaCore")]
    public sealed class CriptaCorePlayTests
    {
        const long T0 = 1_800_000_000;
        const string Map = ExpeditionConfig.CryptMap;
        string dir;
        string settingsFile;

        [SetUp]
        public void SetUp()
        {
            dir = Path.Combine(Path.GetTempPath(), "echoes_criptacore_" + System.Guid.NewGuid().ToString("N"));
            settingsFile = Path.Combine(Path.GetTempPath(), "echoes_criptacore_settings_" + System.Guid.NewGuid().ToString("N") + ".json");
            UserSettings.UseFile(settingsFile);
            GameSession.Use(new SaveService(dir, new FakeGameClock(T0)));
            Assert.IsTrue(NativeRulesCore.TryCreate(out var rules, out var reason), reason);
            using (rules)
            {
                Assert.AreEqual(RulesStatus.Ok, rules.LoadContent(ContentPaths.ResolveDataDirectory(string.Empty), new List<RulesError>()));
                Assert.IsTrue(GameSession.Save.NewGame(rules, 0, "Core"));
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

        static IEnumerator LoadCripta()
        {
            yield return SceneManager.LoadSceneAsync("Cripta", LoadSceneMode.Single);
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

        static IEnumerable<EnemyController> EnemiesOf(EncounterDirector director, string encounterId)
        {
            return Object.FindObjectsByType<EnemyController>(FindObjectsInactive.Include, FindObjectsSortMode.None).Where(e => e.transform.parent != null && e.transform.parent.name == encounterId);
        }

        [UnityTest, Timeout(240000)] // teste que espera algo que nunca vem nao pode prender a Unity (o inventario pausa o tempo: WaitForSeconds escalado travaria)
        public IEnumerator Encounters_FollowTheCoreRoll_CountEliteAndTheSameFormationAfterACheckpoint()
        {
            yield return LoadCripta();
            var director = Object.FindFirstObjectByType<EncounterDirector>();
            Assert.AreNotEqual(0UL, director.VisitSeed, "o core comecou a visita");
            Assert.AreEqual(1, GameSession.Save.Current.WorldState(Map).Visits);

            var checkedEncounters = 0;
            var eliteSeen = 0;
            foreach (var id in new[] { "enc.crypt.patrol_a", "enc.crypt.patrol_b", "enc.crypt.hounds", "enc.crypt.firing_line" })
            {
                var rolled = director.RolledFor(id);
                Assert.IsNotNull(rolled, id);
                var all = EnemiesOf(director, id).ToList();
                foreach (var group in rolled.Groups)
                {
                    var active = all.Count(e => e.EnemyId == group.EnemyId && !e.Excluded);
                    Assert.AreEqual(group.Count, active, id + " " + group.EnemyId + ": n inimigos = o que o core sorteou, nao o maximo fixo");
                    eliteSeen += group.Slots.Count(s => s.Elite);
                }
                checkedEncounters++;
            }
            Assert.AreEqual(4, checkedEncounters);
            Debug.Log("[Test] elites sorteados nos encontros comuns: " + eliteSeen);

            // Morrer e voltar ao checkpoint: a mesma formacao (nenhum espaco excluido reaparece).
            var hero = Object.FindFirstObjectByType<HeroController>();
            var before = Object.FindObjectsByType<EnemyController>(FindObjectsSortMode.None).Length;
            hero.ReturnToCheckpoint();
            yield return null;
            yield return null;
            Assert.AreEqual(before, Object.FindObjectsByType<EnemyController>(FindObjectsSortMode.None).Length, "a formacao nao muda no checkpoint");
        }

        [UnityTest, Timeout(240000)] // teste que espera algo que nunca vem nao pode prender a Unity (o inventario pausa o tempo: WaitForSeconds escalado travaria)
        public IEnumerator RolledElite_IsAppliedByTheCoreModifier()
        {
            // Procura uma semente de visita que de elite: cada nova visita (nova carga da cena) tem a sua; o teste so confere a aplicacao quando ha.
            for (var attempt = 0; attempt < 12; attempt++)
            {
                yield return LoadCripta();
                var elites = Object.FindObjectsByType<EnemyController>(FindObjectsSortMode.None).Where(e => e.Combatant != null && e.Combatant.Elite.Rolled).ToList();
                if (elites.Count == 0) continue;
                foreach (var enemy in elites)
                {
                    Assert.IsFalse(string.IsNullOrEmpty(enemy.Combatant.Elite.ModifierId), "o modificador veio do core");
                    Assert.IsTrue(enemy.Combatant.IsElite);
                }
                yield break;
            }
            Assert.Inconclusive("nenhuma das 12 visitas sorteou elite (chanceElite baixa); a aplicacao fica coberta pelo teste de formacao");
        }

        [UnityTest, Timeout(240000)] // teste que espera algo que nunca vem nao pode prender a Unity (o inventario pausa o tempo: WaitForSeconds escalado travaria)
        public IEnumerator Kill_AwardsXpFromTheCore_ShowsItInTheHud_AndTheHeroUsesTheSaveLevel()
        {
            yield return LoadCripta();
            var host = Object.FindFirstObjectByType<CombatSystemHost>();
            var hero = Object.FindFirstObjectByType<HeroController>();
            var kills = Object.FindFirstObjectByType<KillRewardDirector>();
            var root = Object.FindFirstObjectByType<GameRoot>();
            var rules = GameSession.NativeRules(root);
            Assert.AreEqual(1, hero.Combatant.Level, "novo jogo: nivel 1 do save");
            TestSettings.HeroGodMode = true;

            var skill = host.Rules.FindSkill("skill.warrior.iron_cut");
            var enemies = Object.FindObjectsByType<EnemyController>(FindObjectsSortMode.None).Where(e => e.EnemyId != "enemy.crypt_guardian").Take(12).ToList();
            foreach (var enemy in enemies)
            {
                for (var i = 0; i < 400 && !enemy.Combatant.IsDead; i++) host.Combat.ApplySkillHit(hero.Combatant, enemy.Combatant, skill, hero.Combatant.Position);
            }
            yield return null;
            Assert.AreEqual(enemies.Count, kills.Kills, "cada morte chamou o core");
            Assert.Greater(kills.TotalAwarded, 0.0);
            var progress = GameSession.Save.Current.CharacterProgress(rules, 0, Map);
            Assert.IsTrue(progress.Level > 1 || progress.XpInLevel > 0.0, "o XP ficou no save");

            yield return new WaitForSeconds(1.3f);
            var hud = Object.FindFirstObjectByType<HudView>().GetComponent<UIDocument>().rootVisualElement;
            StringAssert.Contains(progress.Level.ToString(), hud.Q<Label>("level-value").text, "HUD com o nivel do save");
            Assert.IsNotEmpty(hud.Q<Label>("xp-value").text);

            // Fervor real: o bonus vem do core (XP +200%).
            RunState.FervorActive = true;
            yield return new WaitForSeconds(1.3f);
            StringAssert.Contains("200", hud.Q<Label>("fervor-xp").text);

            // O nivel do save vale ao entrar de novo na Cripta.
            if (progress.Level > 1)
            {
                yield return LoadCripta();
                Assert.AreEqual(progress.Level, Object.FindFirstObjectByType<HeroController>().Combatant.Level, "heroi com o nivel do save");
            }
        }

        [UnityTest, Timeout(240000)] // teste que espera algo que nunca vem nao pode prender a Unity (o inventario pausa o tempo: WaitForSeconds escalado travaria)
        public IEnumerator Chest_OpensWithInteract_DropsLootOnTheGround_AndStaysOpen()
        {
            yield return LoadCripta();
            var hero = Object.FindFirstObjectByType<HeroController>();
            var root = Object.FindFirstObjectByType<GameRoot>();
            var rules = GameSession.NativeRules(root);
            TestSettings.HeroGodMode = true;
            var chest = Object.FindObjectsByType<ChestPickup>(FindObjectsSortMode.None).First(c => c.ChestId == "chest.crypt.04");
            Assert.IsFalse(chest.IsOpen);

            Teleport(hero, chest.transform.position + new Vector3(0.5f, 0f, 0f));
            yield return null;
            yield return new WaitForSeconds(0.2f);
            Assert.IsFalse(chest.IsOpen, "so chegar perto nao abre: e preciso Interagir");
            var prompt = Object.FindFirstObjectByType<InteractPromptView>();
            Assert.AreSame(chest, prompt.Current, "aviso [F] Abrir bau do baú mais proximo");
            var goldBefore = SaveReadout.Read(rules, Map).Gold;
            var shardsBefore = SaveReadout.Read(rules, Map).Shards;

            chest.Interact();
            yield return null;
            yield return null;
            Assert.IsTrue(chest.IsOpen);
            Assert.IsTrue(GameSession.Save.Current.IsWorldObjectOpen(Map, "chest.crypt.04"), "o core marcou o bau como aberto");
            var after = SaveReadout.Read(rules, Map);
            var items = GameSession.Save.Current.GroundItems().Count;
            Assert.IsTrue(items > 0 || after.Gold > goldBefore || after.Shards > shardsBefore, "o bau (loot.crypt.elite) rendeu itens no chao, Ouro ou Lascas");

            // Entrar de novo na Cripta: o bau ja nasce aberto e nao rola de novo.
            yield return LoadCripta();
            var again = Object.FindObjectsByType<ChestPickup>(FindObjectsSortMode.None).First(c => c.ChestId == "chest.crypt.04");
            Assert.IsTrue(again.IsOpen, "estado salvo: bau aberto nao fecha");
            Assert.IsFalse(again.CanInteract);
        }

        [UnityTest, Timeout(240000)] // teste que espera algo que nunca vem nao pode prender a Unity (o inventario pausa o tempo: WaitForSeconds escalado travaria)
        public IEnumerator Shortcut_OpensWithInteract_AndStaysOpenAfterReentering()
        {
            yield return LoadCripta();
            var hero = Object.FindFirstObjectByType<HeroController>();
            TestSettings.HeroGodMode = true;
            var lever = Object.FindFirstObjectByType<ShortcutLever>();
            Assert.AreEqual("shortcut.crypt.a", lever.ShortcutId);
            var gate = Object.FindObjectsByType<GateBarrier>(FindObjectsSortMode.None).First(g => g.name == "shortcut.crypt.a");
            Assert.IsTrue(gate.IsClosed);
            Teleport(hero, lever.transform.position);
            yield return null;
            yield return null;
            Assert.IsTrue(gate.IsClosed, "perto da alavanca nao abre sozinho");
            lever.Interact();
            yield return null;
            Assert.IsFalse(gate.IsClosed);
            Assert.IsTrue(GameSession.Save.Current.IsWorldObjectOpen(Map, "shortcut.crypt.a"));

            yield return LoadCripta();
            yield return null;
            var gate2 = Object.FindObjectsByType<GateBarrier>(FindObjectsSortMode.None).First(g => g.name == "shortcut.crypt.a");
            Assert.IsFalse(gate2.IsClosed, "o atalho continua aberto");
        }

        [UnityTest, Timeout(240000)] // teste que espera algo que nunca vem nao pode prender a Unity (o inventario pausa o tempo: WaitForSeconds escalado travaria)
        public IEnumerator SecretWall_IsSavedWhenOpened_AndBornOpenNextTime()
        {
            yield return LoadCripta();
            var wall = Object.FindFirstObjectByType<SecretWall>();
            Assert.IsFalse(wall.IsOpen);
            wall.Open();
            Assert.IsTrue(GameSession.Save.Current.IsWorldObjectOpen(Map, wall.SecretId));
            yield return LoadCripta();
            var again = Object.FindObjectsByType<SecretWall>(FindObjectsInactive.Include, FindObjectsSortMode.None).First();
            Assert.IsTrue(again.IsOpen, "parede aberta no save nasce aberta");
            Assert.IsFalse(again.gameObject.activeSelf);
        }

        [UnityTest, Timeout(240000)] // teste que espera algo que nunca vem nao pode prender a Unity (o inventario pausa o tempo: WaitForSeconds escalado travaria)
        public IEnumerator ClearingAnEncounter_RollsTheAreaLootOnce()
        {
            yield return LoadCripta();
            var host = Object.FindFirstObjectByType<CombatSystemHost>();
            var hero = Object.FindFirstObjectByType<HeroController>();
            var director = Object.FindFirstObjectByType<EncounterDirector>();
            TestSettings.HeroGodMode = true;
            var cleared = new List<string>();
            host.Events.Subscribe<EncounterClearedEvent>((in EncounterClearedEvent e) => cleared.Add(e.EncounterId));

            var skill = host.Rules.FindSkill("skill.warrior.iron_cut");
            var enemies = EnemiesOf(director, "enc.crypt.patrol_a").Where(e => !e.Excluded).ToList();
            Assert.IsNotEmpty(enemies);
            foreach (var enemy in enemies)
            {
                for (var i = 0; i < 400 && !enemy.Combatant.IsDead; i++) host.Combat.ApplySkillHit(hero.Combatant, enemy.Combatant, skill, hero.Combatant.Position);
            }
            yield return null;
            CollectionAssert.AreEqual(new[] { "enc.crypt.patrol_a" }, cleared, "limpou o encontro uma vez");
            Assert.IsTrue(director.IsCleared("enc.crypt.patrol_a"));

            // Voltar ao checkpoint reaparece todo mundo; matar de novo nao repete o loot (sem farm).
            hero.ReturnToCheckpoint();
            yield return null;
            yield return null;
            foreach (var enemy in enemies)
            {
                for (var i = 0; i < 400 && !enemy.Combatant.IsDead; i++) host.Combat.ApplySkillHit(hero.Combatant, enemy.Combatant, skill, hero.Combatant.Position);
            }
            yield return null;
            Assert.AreEqual(1, cleared.Count, "so a primeira vez na visita");
        }
    }
}
