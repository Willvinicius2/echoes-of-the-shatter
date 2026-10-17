using System.Linq;
using Echoes.Core;
using Echoes.EditorTools;
using Echoes.Gameplay;
using Echoes.Interop;
using Echoes.Presentation;
using NUnit.Framework;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace Echoes.Tests.EditMode
{
    /// <summary>Cao de Cinza (AC_Hound, mordida pelos tempos do core, fuga pelo fleeLifeFraction), arco do Arqueiro, Mago modular e a previa visual dos herois.</summary>
    [Category("Hound")]
    public sealed class HoundAndHeroesTests
    {
        [OneTimeSetUp]
        public void Build()
        {
            CharacterPrefabBuilder.BuildAll();
        }

        [Test]
        public void HoundClipsAreGenericWithTheBiteEventsFromTheArt()
        {
            foreach (var name in new[] { EchoesAnimationImport.HoundIdle, EchoesAnimationImport.HoundWalk, EchoesAnimationImport.HoundRun, EchoesAnimationImport.HoundBite, EchoesAnimationImport.HoundHit, EchoesAnimationImport.HoundFlee, EchoesAnimationImport.HoundDeath })
            {
                var spec = EchoesAnimationImport.Spec(name);
                var clip = EchoesAnimationImport.Clip(name);
                Assert.IsNotNull(clip, name);
                Assert.IsFalse(clip.isHumanMotion, name + ": Generic (quadrupede)");
                Assert.AreEqual(spec.Seconds, clip.length, 0.05f, name);
                Assert.AreEqual(spec.Loop, clip.isLooping, name);
            }
            var bite = EchoesAnimationImport.Clip(EchoesAnimationImport.HoundBite);
            foreach (var (eventName, frame) in new[] { ("windup_end", 9), ("impact", 12), ("recovery_end", 24) })
            {
                var e = bite.events.FirstOrDefault(x => x.stringParameter == eventName);
                Assert.IsNotNull(e, eventName);
                Assert.AreEqual(frame / EchoesAnimationImport.Fps, e.time, 0.05f, eventName);
            }
        }

        [Test]
        public void HoundControllerHasLocomotionFleeDeathBiteAndHit()
        {
            var c = AssetDatabase.LoadAssetAtPath<AnimatorController>(AnimatorControllerBuilder.ControllerPath(AnimatorControllerBuilder.HoundControllerName));
            Assert.IsNotNull(c);
            var parameters = c.parameters.Select(p => p.name).ToList();
            foreach (var name in new[] { "Speed", "ActionSpeed", "IsDead", "IsFleeing" }) CollectionAssert.Contains(parameters, name);
            CollectionAssert.AreEquivalent(new[] { "Locomotion", "Flee", "Death" }, c.layers[0].stateMachine.states.Select(s => s.state.name));
            CollectionAssert.AreEquivalent(new[] { "Empty", "Bite" }, c.layers[1].stateMachine.states.Select(s => s.state.name));
            CollectionAssert.AreEquivalent(new[] { "Empty", "Hit" }, c.layers[2].stateMachine.states.Select(s => s.state.name));
            var tree = (BlendTree)c.layers[0].stateMachine.states.First(s => s.state.name == "Locomotion").state.motion;
            Assert.AreEqual(3, tree.children.Length, "Idle, Walk e Run");
            Assert.Less(tree.children[0].threshold, tree.children[1].threshold);
            Assert.Less(tree.children[1].threshold, tree.children[2].threshold);
            var flee = c.layers[0].stateMachine.states.First(s => s.state.name == "Flee").state;
            Assert.AreEqual(EchoesAnimationImport.Clip(EchoesAnimationImport.HoundFlee), flee.motion);
        }

        [Test]
        public void HoundPrefabIsWiredAndBiteSpeedFollowsTheCoreTimes()
        {
            const string houndPath = "Assets/Art/Prefabs/P_Enemy_AshHound.prefab";
            AssetDatabase.ImportAsset(houndPath, ImportAssetOptions.ForceUpdate); // o controller e recriado a cada montagem: recarrega a referencia
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(houndPath);
            Assert.IsNotNull(prefab);
            var animator = prefab.GetComponentInChildren<Animator>();
            Assert.AreEqual(AnimatorControllerBuilder.HoundControllerName, animator.runtimeAnimatorController.name);
            Assert.IsNotNull(prefab.GetComponentInChildren<AnimationEventRelay>());
            Assert.AreEqual(prefab.GetComponentInChildren<Animator>().gameObject, prefab.GetComponentInChildren<AnimationEventRelay>().gameObject);

            var set = AssetDatabase.LoadAssetAtPath<SkillPresentationSet>($"{AnimatorControllerBuilder.SkillSetDir}/{AnimatorControllerBuilder.HoundSkillSetName}.asset");
            Assert.IsTrue(set.TryGet(AnimatorControllerBuilder.HoundSkillId, out var entry));
            Assert.AreEqual(9 / 24f, entry.windupEnd, 1e-4f);
            Assert.AreEqual(12 / 24f, entry.impactEnd, 1e-4f);
            using (var rules = TestWorld.LoadNativeRules())
            {
                var timing = rules.GetActionTiming(rules.CreateEnemyStats("enemy.ash_hound", 3), rules.FindSkill(AnimatorControllerBuilder.HoundSkillId));
                var windupSpeed = entry.windupEnd * entry.clipSeconds / (float)timing.Windup;
                Assert.Greater(windupSpeed, 0.4f);
                Assert.Less(windupSpeed, 2.5f, "a velocidade do clipe segue a preparacao do core");
            }
        }

        [Test]
        public void HoundFleesBelowTheCoreFractionOnceThenFightsAgain()
        {
            using (var world = new TestWorld(null, TestWorld.LoadNativeRules()))
            {
                var hero = world.AddHero(new PlanarVector(0f, 0f));
                var hound = world.AddEnemy("enemy.ash_hound", new PlanarVector(0f, 6f));
                hound.logic.IntegratesMovement = true; // sem NavMeshAgent o proprio passo fixo move o inimigo
                var info = world.Rules.FindEnemy("enemy.ash_hound");
                Assert.Greater(info.FleeLifeFraction, 0.0, "fleeLifeFraction vem do core (enemy_ai.csv)");
                Assert.Greater(info.FleeSeconds, 0.0);
                world.Run(0.5);
                Assert.IsFalse(hound.logic.IsFleeing, "vida cheia: nao foge");

                var vitals = hound.combatant.Vitals;
                vitals.Life = hound.combatant.MaxLife * info.FleeLifeFraction * 0.5;
                hound.combatant.SetVitals(in vitals);
                world.Run(0.2);
                Assert.IsTrue(hound.logic.IsFleeing, "abaixo da fracao: foge");
                var before = PlanarVector.Distance(hound.combatant.Position, hero.combatant.Position);
                world.Run(info.FleeSeconds * 0.5);
                Assert.Greater(PlanarVector.Distance(hound.combatant.Position, hero.combatant.Position), before, "foge para longe do heroi");
                world.Run(info.FleeSeconds + 0.5);
                Assert.IsFalse(hound.logic.IsFleeing, "a fuga acaba depois de fleeSeconds");
                if (info.FleeOncePerLife)
                {
                    vitals = hound.combatant.Vitals;
                    vitals.Life = hound.combatant.MaxLife * info.FleeLifeFraction * 0.4;
                    hound.combatant.SetVitals(in vitals);
                    world.Run(0.3);
                    Assert.IsFalse(hound.logic.IsFleeing, "uma vez por vida");
                }
                world.Combat.Revive(hound.combatant);
                vitals = hound.combatant.Vitals;
                vitals.Life = hound.combatant.MaxLife * info.FleeLifeFraction * 0.4;
                hound.combatant.SetVitals(in vitals);
                world.Run(0.3);
                Assert.IsTrue(hound.logic.IsFleeing, "o revive libera a fuga de novo (shatter_actor_flee_reset)");
            }
        }

        [Test]
        public void ArcherHoldsTheBowInTheLeftHandAndMageTheStaffInTheRight()
        {
            foreach (var (prefab, weapon, hand) in new[] { ("P_Hero_Archer", "Weapon_Bow", HumanBodyBones.LeftHand), ("P_Hero_Mage", "Weapon_Staff", HumanBodyBones.RightHand) })
            {
                var go = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>($"Assets/Art/Prefabs/{prefab}.prefab"));
                try
                {
                    var animator = go.GetComponentInChildren<Animator>();
                    var model = CharacterPrefabBuilder.FindDeep(go.transform, weapon);
                    Assert.IsNotNull(model, prefab + ": " + weapon);
                    Assert.IsTrue(model.IsChildOf(animator.GetBoneTransform(hand)), prefab + ": " + weapon + " na mao certa");
                    Assert.IsNotNull(go.GetComponent<ModularCharacter>(), prefab + ": modular");
                    Assert.AreEqual("AC_Warrior", prefab == "P_Hero_Archer" ? CharacterPrefabBuilder.Archer.Controller : CharacterPrefabBuilder.Mage.Controller, prefab + ": kit de teste do Guerreiro (previa visual)");
                }
                finally
                {
                    Object.DestroyImmediate(go);
                }
            }
            var catalog = AssetDatabase.LoadAssetAtPath<HeroPartCatalog>(HeroModularBuilder.CatalogPath("Mage"));
            Assert.AreEqual(5, catalog.parts.Count, "Mago: 5 pecas Starter");
        }

        [Test]
        public void HeroChoiceCyclesAmongTheThreeHeroes()
        {
            var previous = HeroChoice.Id;
            try
            {
                HeroChoice.Id = "warrior";
                HeroChoice.Cycle();
                Assert.AreEqual("archer", HeroChoice.Id);
                HeroChoice.Cycle();
                Assert.AreEqual("mage", HeroChoice.Id);
                HeroChoice.Cycle();
                Assert.AreEqual("warrior", HeroChoice.Id);
                HeroChoice.Id = "inexistente";
                Assert.AreEqual("warrior", HeroChoice.Id, "id invalido cai no Guerreiro");
            }
            finally
            {
                HeroChoice.Id = previous;
            }
        }
    }
}
