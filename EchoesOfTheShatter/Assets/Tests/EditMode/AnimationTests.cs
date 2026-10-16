using System.Collections.Generic;
using System.IO;
using System.Linq;
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
    /// <summary>
    /// Animação com os clipes CC0 do KayKit (só as animações): importação, retarget pelo avatar Humanoid, controllers com os estados e os
    /// parâmetros, e os eventos do combate que o PresentationController converte em trocas de estado (o Animator nunca decide regra).
    /// </summary>
    [Category("Animation")]
    public sealed class AnimationTests
    {
        [OneTimeSetUp]
        public void Build()
        {
            CharacterPrefabBuilder.BuildAll(); // importa os clipes, monta os controllers, os prefabs e os SO_SkillPresentation_*
        }

        [Test]
        public void KayKitIsCreditedAsCc0AndOnlyTheNeededClipsAreImported()
        {
            var license = Path.Combine(Application.dataPath, "Art/Animations/ThirdParty/KayKit/License.txt");
            Assert.IsTrue(File.Exists(license));
            StringAssert.Contains("CC0", File.ReadAllText(license));
            var readme = File.ReadAllText(Path.Combine(Application.dataPath, "Art/Animations/ThirdParty/KayKit/README.md"));
            StringAssert.Contains("CC0", readme);
            StringAssert.Contains("Kay Lousberg", readme);

            foreach (var pair in KayKitAnimationImport.Files)
            {
                var importer = (ModelImporter)AssetImporter.GetAtPath(pair.Key);
                Assert.IsNotNull(importer, pair.Key);
                Assert.AreEqual(ModelImporterAnimationType.Human, importer.animationType, pair.Key + ": Humanoid para o retarget");
                var clips = importer.clipAnimations;
                CollectionAssert.AreEquivalent(pair.Value.Select(c => c.Take), clips.Select(c => c.name), pair.Key + ": so os clipes necessarios");
                foreach (var clip in clips)
                {
                    var spec = pair.Value.First(c => c.Take == clip.name);
                    Assert.IsTrue(clip.lockRootRotation && clip.lockRootHeightY && clip.lockRootPositionXZ, clip.name + ": sem root motion");
                    Assert.IsTrue(clip.heightFromFeet, clip.name + ": altura pelos pes (pe no chao)");
                    Assert.AreEqual(spec.Loop, clip.loopTime, clip.name);
                    Assert.IsNotNull(KayKitAnimationImport.FindClip(pair.Key, clip.name), clip.name);
                }
            }
        }

        [Test]
        public void ChibiRigGetsTheMuscleSetupForTheShortArms()
        {
            var importer = (ModelImporter)AssetImporter.GetAtPath(CharacterAssetPostprocessor.RigPath);
            Assert.AreEqual(KayKitAnimationImport.ArmStretch, importer.humanDescription.armStretch, 1e-4f);
            Assert.AreEqual(KayKitAnimationImport.LegStretch, importer.humanDescription.legStretch, 1e-4f);
            Assert.IsTrue(AssetDatabase.LoadAssetAtPath<Avatar>(CharacterAssetPostprocessor.RigPath).isHuman);
        }

        [Test]
        public void ControllersHaveTheStatesAndParameters()
        {
            foreach (var spec in AnimatorControllerBuilder.All)
            {
                var c = AssetDatabase.LoadAssetAtPath<AnimatorController>(AnimatorControllerBuilder.ControllerPath(spec.Name));
                Assert.IsNotNull(c, spec.Name);
                var parameters = c.parameters.ToDictionary(p => p.name);
                foreach (var name in new[] { "Speed", "ActionSpeed", "IsDead", "IsStaggered" }) Assert.IsTrue(parameters.ContainsKey(name), spec.Name + "." + name);
                Assert.AreEqual(1f, parameters["ActionSpeed"].defaultFloat, spec.Name);
                Assert.AreEqual(spec.Name == "AC_Boss", parameters.ContainsKey("Phase"), spec.Name + ": Phase so no chefe");

                Assert.AreEqual(3, c.layers.Length, spec.Name);
                Assert.AreEqual("Action", c.layers[1].name);
                Assert.AreEqual("Hit", c.layers[2].name);
                var baseStates = c.layers[0].stateMachine.states.Select(s => s.state.name).ToList();
                CollectionAssert.AreEquivalent(new[] { "Locomotion", "Death", "Stun" }, baseStates, spec.Name);
                var actionStates = c.layers[1].stateMachine.states.Select(s => s.state.name).ToList();
                CollectionAssert.AreEquivalent(new[] { "Empty" }.Concat(spec.Actions.Select(a => a.State)), actionStates, spec.Name);
                CollectionAssert.AreEquivalent(new[] { "Empty", "Hit" }, c.layers[2].stateMachine.states.Select(s => s.state.name), spec.Name);

                var loco = c.layers[0].stateMachine.states.First(s => s.state.name == "Locomotion").state;
                var tree = loco.motion as BlendTree;
                Assert.IsNotNull(tree, spec.Name + ": Locomotion e um blend pela velocidade");
                Assert.AreEqual("Speed", tree.blendParameter);
                Assert.AreEqual(3, tree.children.Length, "Idle, Walk e Run");
                Assert.Less(tree.children[0].threshold, tree.children[1].threshold);
                Assert.Less(tree.children[1].threshold, tree.children[2].threshold);

                foreach (var action in c.layers[1].stateMachine.states.Select(s => s.state).Where(s => s.name != "Empty"))
                {
                    Assert.IsNotNull(action.motion, spec.Name + "/" + action.name);
                    Assert.IsTrue(action.speedParameterActive && action.speedParameter == "ActionSpeed", action.name + ": a velocidade do clipe segue o core");
                }
            }
        }

        [Test]
        public void WarriorHasTheSkillAndDodgeStates()
        {
            var c = AssetDatabase.LoadAssetAtPath<AnimatorController>(AnimatorControllerBuilder.ControllerPath("AC_Warrior"));
            var states = c.layers[1].stateMachine.states.Select(s => s.state.name).ToList();
            foreach (var name in new[] { "Basic", "Charge", "Rift", "Bash", "Dodge" }) CollectionAssert.Contains(states, name);
            var boss = AssetDatabase.LoadAssetAtPath<AnimatorController>(AnimatorControllerBuilder.ControllerPath("AC_Boss"));
            var bossStates = boss.layers[1].stateMachine.states.Select(s => s.state.name).ToList();
            foreach (var name in new[] { "Hammer", "ShieldBash", "Charge", "Roar" }) CollectionAssert.Contains(bossStates, name);
        }

        [Test]
        public void MissingClipsAreMarkedAsPlaceholdersAndListed()
        {
            var placeholders = new List<string>();
            foreach (var spec in AnimatorControllerBuilder.All)
            {
                var c = AssetDatabase.LoadAssetAtPath<AnimatorController>(AnimatorControllerBuilder.ControllerPath(spec.Name));
                foreach (var layer in c.layers)
                {
                    foreach (var s in layer.stateMachine.states)
                    {
                        if (s.state.tag == AnimatorControllerBuilder.PlaceholderTag) placeholders.Add($"{spec.Name}/{s.state.name}");
                    }
                }
            }
            CollectionAssert.AreEquivalent(new[]
            {
                "AC_Warrior/Stun", "AC_EnemyHumanoid/Stun", "AC_Boss/Stun", "AC_Boss/Charge", "AC_Boss/Roar",
            }, placeholders);
        }

        [Test]
        public void PrefabsCarryTheirControllerExceptTheGenericArcher()
        {
            foreach (var (prefab, controller) in new[]
            {
                ("P_Hero_Warrior", "AC_Warrior"), ("P_Enemy_HollowSentinel", "AC_EnemyHumanoid"), ("P_Enemy_StoneHerald", "AC_EnemyHumanoid"),
                ("P_Boss_CryptGuardian", "AC_Boss"),
            })
            {
                var go = AssetDatabase.LoadAssetAtPath<GameObject>($"Assets/Art/Prefabs/{prefab}.prefab");
                var animator = go.GetComponent<Animator>();
                Assert.AreEqual(controller, animator.runtimeAnimatorController.name, prefab);
                Assert.IsFalse(animator.applyRootMotion, prefab + ": sem root motion");
            }
            var archer = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Art/Prefabs/P_Enemy_GhostArcher.prefab");
            Assert.IsNull(archer.GetComponent<Animator>().runtimeAnimatorController, "o Espectro (Generic, sem pernas) fica sem animacao: pedido de Blender/Mixamo");
        }

        [Test]
        public void SkillPresentationSetsTimeTheStrikeFromTheClips()
        {
            foreach (var spec in AnimatorControllerBuilder.All)
            {
                var set = AssetDatabase.LoadAssetAtPath<SkillPresentationSet>($"{AnimatorControllerBuilder.SkillSetDir}/{spec.SkillSet}.asset");
                Assert.IsNotNull(set, spec.SkillSet);
                foreach (var action in spec.Actions.Where(a => !string.IsNullOrEmpty(a.SkillId)))
                {
                    Assert.IsTrue(set.TryGet(action.SkillId, out var entry), action.SkillId);
                    Assert.AreEqual(action.State, entry.animatorState, action.SkillId);
                    Assert.Greater(entry.clipSeconds, 0.1f, action.SkillId);
                    Assert.Less(entry.windupEnd, entry.impactEnd, action.SkillId + ": preparacao antes do impacto");
                    Assert.LessOrEqual(entry.impactEnd, 1f, action.SkillId);
                }
            }
            var boss = AssetDatabase.LoadAssetAtPath<SkillPresentationSet>($"{AnimatorControllerBuilder.SkillSetDir}/SO_SkillPresentation_Boss.asset");
            Assert.AreEqual("Roar", boss.roarState);
            Assert.Greater(boss.roarClipSeconds, 0.1f);
        }

        // ---------------------------------------------------------------------------------------------
        // Eventos do combate que a apresentacao converte em trocas de estado
        // ---------------------------------------------------------------------------------------------

        [Test]
        public void EnemyAttacksPublishTheirPhasesForThePresentation()
        {
            using (var world = new TestWorld(null, TestWorld.LoadNativeRules()))
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var enemy = world.AddEnemy("enemy.hollow_sentinel", new PlanarVector(0f, 1.2f));
                var phases = new List<SkillPhaseEvent>();
                world.Events.Subscribe<SkillPhaseEvent>((in SkillPhaseEvent e) => { if (ReferenceEquals(e.Owner, enemy.combatant)) phases.Add(e); });
                for (var i = 0; i < 600 && !phases.Exists(p => p.Phase == ActionPhase.Recovery); i++) world.Combat.Step(world.Step);
                var order = phases.Select(p => p.Phase).ToList();
                CollectionAssert.AreEqual(new[] { ActionPhase.Windup, ActionPhase.Impact, ActionPhase.Recovery }, order.Take(3).ToList(), "preparacao, impacto, recuperacao");
                Assert.Greater(phases[0].PhaseSeconds, 0.0, "a velocidade do clipe segue o windup do core");
                Assert.Greater(phases[1].PhaseSeconds, 0.0);
                Assert.AreEqual("skill.enemy.sentinel_strike", phases[0].Skill.Id);
            }
        }

        [Test]
        public void BossPatternsAndPhaseRoarReachThePresentation()
        {
            using (var world = new TestWorld(null, TestWorld.LoadNativeRules()))
            {
                var hero = world.AddHero(new PlanarVector(0f, 0f));
                var boss = world.AddEnemy("enemy.crypt_guardian", new PlanarVector(0f, 16f), 3, 1f);
                var phases = new List<SkillPhaseEvent>();
                var states = new List<BossStateEvent>();
                world.Events.Subscribe<SkillPhaseEvent>((in SkillPhaseEvent e) => { if (ReferenceEquals(e.Owner, boss.combatant)) phases.Add(e); });
                world.Events.Subscribe<BossStateEvent>((in BossStateEvent e) => states.Add(e));
                world.Run(8.0);
                Assert.IsTrue(phases.Exists(p => p.Phase == ActionPhase.Windup), "o padrao do chefe comeca com a preparacao");
                Assert.IsTrue(phases.Exists(p => p.Phase == ActionPhase.Impact));
                var info = boss.logic.Boss.Info;
                var bx = boss.combatant.Position.X;
                var bz = boss.combatant.Position.Z;
                boss.logic.Boss.ApplyDamage(info.Life - info.MaxLife * 0.5, bx, bz, bx - info.FacingX * 4.0, bz - info.FacingZ * 4.0);
                world.Run(6.0);
                var roar = states.Find(e => e.Kind == BossEventKind.PhaseStart && e.Phase == 2);
                Assert.AreEqual(BossEventKind.PhaseStart, roar.Kind, "o rugido da fase 2 sai do core");
                Assert.Greater(roar.Seconds, 0.0, "a velocidade do clipe de rugido segue transitionSeconds");
            }
        }
    }
}
