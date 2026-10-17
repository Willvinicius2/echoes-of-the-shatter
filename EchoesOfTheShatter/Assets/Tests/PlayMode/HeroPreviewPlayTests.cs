using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using Echoes.Interop.Native;
using Echoes.Presentation;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace Echoes.Tests.PlayMode
{
    /// <summary>Previa visual dos herois (-hero / tela inicial) e o Cao de Cinza animado na Cripta.</summary>
    [Category("HeroPreview")]
    public sealed class HeroPreviewPlayTests
    {
        string dir;
        string previous;

        [SetUp]
        public void SetUp()
        {
            previous = HeroChoice.Id;
            dir = Path.Combine(Path.GetTempPath(), "echoes_hero_" + System.Guid.NewGuid().ToString("N"));
            GameSession.Use(new SaveService(dir, new FakeGameClock(1_800_000_000)));
        }

        [TearDown]
        public void TearDown()
        {
            HeroChoice.Id = previous;
            GameSession.Reset();
            if (Directory.Exists(dir)) Directory.Delete(dir, true);
        }

        static void NewSave()
        {
            Assert.IsTrue(NativeRulesCore.TryCreate(out var rules, out var reason), reason);
            using (rules)
            {
                rules.LoadContent(ContentPaths.ResolveDataDirectory(string.Empty), new List<RulesError>());
                Assert.IsTrue(GameSession.Save.NewGame(rules, 0, "Previa"));
            }
        }

        [UnityTest]
        public IEnumerator TheChosenHeroAppearsInTheRefuge()
        {
            NewSave();
            foreach (var (id, prefabName, weapon) in new[] { ("mage", "P_Hero_Mage", "Weapon_Staff"), ("archer", "P_Hero_Archer", "Weapon_Bow"), ("warrior", "P_Hero_Warrior", "Weapon_WarriorHammer") })
            {
                HeroChoice.Id = id;
                yield return SceneManager.LoadSceneAsync("Refugio", LoadSceneMode.Single);
                yield return null;
                yield return null;
                var hero = Object.FindFirstObjectByType<HeroController>();
                var body = hero.transform.Find("Body");
                Assert.IsNotNull(body, id);
                StringAssert.StartsWith(prefabName, body.name.Replace("(Clone)", string.Empty).Replace("Body", prefabName), id);
                Assert.IsNotNull(body.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == weapon), id + ": " + weapon);
                Assert.IsNotNull(body.GetComponentInChildren<ModularCharacter>(), id + ": modular");
                Assert.IsNotNull(hero.GetComponentInChildren<Animator>(), id);
            }
        }

        [UnityTest]
        public IEnumerator TheHoundsInTheCryptUseTheHoundAnimator()
        {
            NewSave();
            HeroChoice.Id = "warrior";
            yield return SceneManager.LoadSceneAsync("Cripta", LoadSceneMode.Single);
            yield return null;
            yield return null;
            var hounds = Object.FindObjectsByType<EnemyController>(FindObjectsInactive.Include, FindObjectsSortMode.None).Where(e => e.EnemyId == "enemy.ash_hound" || e.EnemyId == "enemy.swift_ash_hound").ToList();
            Assert.Greater(hounds.Count, 0, "ha Caes na Cripta");
            foreach (var hound in hounds)
            {
                var animator = hound.GetComponentInChildren<Animator>(true);
                Assert.IsNotNull(animator, hound.name);
                Assert.AreEqual("AC_Hound", animator.runtimeAnimatorController.name, hound.name);
                Assert.IsNotNull(hound.GetComponent<PresentationController>());
            }
        }
    }
}
