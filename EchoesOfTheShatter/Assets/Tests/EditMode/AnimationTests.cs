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
        public void ChibiAvatarsGetTheMuscleSetupAndAreHumanoid()
        {
            var owners = KayKitAnimationImport.AvatarOwners().ToList();
            Assert.GreaterOrEqual(owners.Count, 3, "rig, Arauto e Guardiao tem avatar proprio");
            foreach (var path in owners)
            {
                var importer = (ModelImporter)AssetImporter.GetAtPath(path);
                var description = importer.humanDescription;
                Assert.AreEqual(KayKitAnimationImport.ArmStretch, description.armStretch, 1e-4f, path);
                Assert.AreEqual(KayKitAnimationImport.LegStretch, description.legStretch, 1e-4f, path);
                Assert.IsTrue(AssetDatabase.LoadAllAssetRepresentationsAtPath(path).OfType<Avatar>().Any(a => a.isHuman && a.isValid), path + ": avatar Humanoid valido");
                foreach (var bone in description.human)
                {
                    var expected = bone.humanName == "Neck" ? KayKitAnimationImport.NeckLimit
                        : bone.humanName == "Head" ? KayKitAnimationImport.HeadLimit
                        : bone.humanName == "Spine" || bone.humanName == "Chest" || bone.humanName == "UpperChest" ? KayKitAnimationImport.TorsoLimit : 0f;
                    if (expected <= 0f) continue;
                    Assert.IsFalse(bone.limit.useDefaultValues, path + " " + bone.humanName);
                    Assert.AreEqual(expected, bone.limit.max.x, 1e-4f, path + " " + bone.humanName + ": o tronco e a cabeca grande nao se dobram como no humano");
                }
            }
            foreach (var model in new[] { "StoneHerald/SK_Enemy_StoneHerald", "CryptGuardian/SK_Boss_CryptGuardian" })
            {
                var importer = (ModelImporter)AssetImporter.GetAtPath($"Assets/Art/Characters/{model}.fbx");
                Assert.AreEqual(ModelImporterAvatarSetup.CreateFromThisModel, importer.avatarSetup, model + ": escala propria, avatar proprio (senao o corpo afunda)");
            }
        }

        [Test]
        public void WeaponsStayChildrenOfTheHandBonesAndTheHierarchyIsExposed()
        {
            foreach (var (prefab, right, left) in new[] { ("P_Hero_Warrior", "Weapon_WarriorHammer", "Weapon_WarriorShield"), ("P_Boss_CryptGuardian", "Weapon_GuardianHammer", "Weapon_GuardianShield") })
            {
                var go = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>($"Assets/Art/Prefabs/{prefab}.prefab"));
                try
                {
                    var animator = go.GetComponentInChildren<Animator>();
                    Assert.IsTrue(animator.hasTransformHierarchy, prefab + ": sem Optimize Game Objects, o Animator nao esconde a hierarquia");
                    var hammer = CharacterPrefabBuilder.FindDeep(go.transform, right);
                    var shield = CharacterPrefabBuilder.FindDeep(go.transform, left);
                    Assert.IsNotNull(hammer, right);
                    Assert.IsNotNull(shield, left);
                    Assert.IsTrue(hammer.IsChildOf(animator.GetBoneTransform(HumanBodyBones.RightHand)), prefab + ": martelo na mao direita");
                    Assert.IsTrue(shield.IsChildOf(animator.GetBoneTransform(HumanBodyBones.LeftHand)), prefab + ": escudo na mao esquerda");
                    // Seguem o osso quando o clipe amostra a pose.
                    var clip = KayKitAnimationImport.FindClip($"{KayKitAnimationImport.Root}/Medium/Rig_Medium_CombatMelee.fbx", prefab.Contains("Boss") ? "Melee_2H_Attack_Chop" : "Melee_1H_Attack_Slice_Horizontal");
                    var before = hammer.position;
                    clip.SampleAnimation(animator.gameObject, clip.length * 0.3f);
                    Assert.Greater(Vector3.Distance(before, hammer.position), 0.05f, prefab + ": a arma acompanha a mao");
                    Assert.AreEqual(0f, Vector3.Distance(hammer.position, animator.GetBoneTransform(HumanBodyBones.RightHand).position), 0.2f, prefab + ": e continua na mao");
                }
                finally
                {
                    Object.DestroyImmediate(go);
                }
            }
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
            foreach (var name in new[] { "Hammer", "ShieldBash", "ChargeWindup", "ChargeRun", "ChargeRecover", "Roar" }) CollectionAssert.Contains(bossStates, name);
        }

        [Test]
        public void NoPlaceholderClipsRemain()
        {
            foreach (var name in new[] { "AC_Warrior", "AC_EnemyHumanoid", "AC_Boss", "AC_GhostArcher" })
            {
                var c = AssetDatabase.LoadAssetAtPath<AnimatorController>(AnimatorControllerBuilder.ControllerPath(name));
                Assert.IsNotNull(c, name);
                foreach (var layer in c.layers)
                    foreach (var s in layer.stateMachine.states)
                        Assert.AreNotEqual(AnimatorControllerBuilder.PlaceholderTag, s.state.tag, $"{name}/{s.state.name}: placeholder trocado pelos golpes do Blender");
            }
            Assert.AreEqual(0, AnimatorControllerBuilder.PlaceholderReport.Count);
        }

        [Test]
        public void StunUsesTheSharedBlenderClipInTheThreeControllers()
        {
            var stun = EchoesAnimationImport.Clip(EchoesAnimationImport.StunName);
            Assert.IsNotNull(stun);
            Assert.IsTrue(stun.isHumanMotion, "Humanoid (serve ao Warrior e aos humanoides)");
            foreach (var name in new[] { "AC_Warrior", "AC_EnemyHumanoid", "AC_Boss" })
            {
                var c = AssetDatabase.LoadAssetAtPath<AnimatorController>(AnimatorControllerBuilder.ControllerPath(name));
                var state = c.layers[0].stateMachine.states.First(x => x.state.name == "Stun").state;
                Assert.AreEqual(stun, state.motion, name);
            }
        }

        [Test]
        public void EchoesClipsAreImportedWithFramesLoopAndEvents()
        {
            foreach (var spec in EchoesAnimationImport.Clips)
            {
                var clip = EchoesAnimationImport.Clip(spec.Name);
                Assert.IsNotNull(clip, spec.Name);
                Assert.AreEqual(spec.Seconds, clip.length, 0.05f, spec.Name + ": duracao do _clips_*.json");
                Assert.AreEqual(spec.Loop, clip.isLooping, spec.Name);
                Assert.AreEqual(spec.Kind != EchoesAnimationImport.Kind.ArcherGeneric, clip.isHumanMotion, spec.Name + ": Humanoid ou Generic");
                Assert.AreEqual(spec.Events.Length, clip.events.Length, spec.Name);
                foreach (var e in spec.Events)
                {
                    var found = clip.events.FirstOrDefault(x => x.stringParameter == e.name);
                    Assert.IsNotNull(found, spec.Name + ":" + e.name);
                    Assert.AreEqual(EchoesAnimationImport.EventFunction, found.functionName);
                    Assert.AreEqual(e.frame / EchoesAnimationImport.Fps, found.time, 0.04f, spec.Name + ":" + e.name + " no quadro certo");
                }
            }
        }

        [Test]
        public void GhostArcherControllerHasIdleGlideShootHitAndDeath()
        {
            var c = AssetDatabase.LoadAssetAtPath<AnimatorController>(AnimatorControllerBuilder.ControllerPath(AnimatorControllerBuilder.ArcherControllerName));
            Assert.IsNotNull(c);
            var parameters = c.parameters.Select(p => p.name).ToList();
            foreach (var name in new[] { "Speed", "ActionSpeed", "IsDead" }) CollectionAssert.Contains(parameters, name);
            CollectionAssert.AreEquivalent(new[] { "Locomotion", "Death" }, c.layers[0].stateMachine.states.Select(s => s.state.name));
            CollectionAssert.AreEquivalent(new[] { "Empty", "Shoot" }, c.layers[1].stateMachine.states.Select(s => s.state.name));
            CollectionAssert.AreEquivalent(new[] { "Empty", "Hit" }, c.layers[2].stateMachine.states.Select(s => s.state.name));
            var tree = (BlendTree)c.layers[0].stateMachine.states.First(s => s.state.name == "Locomotion").state.motion;
            Assert.AreEqual("Speed", tree.blendParameter);
            Assert.AreEqual(2, tree.children.Length, "Idle e Glide");
            Assert.Less(tree.children[0].threshold, tree.children[1].threshold);
            Assert.AreEqual(EchoesAnimationImport.Clip("AN_GhostArcher_Idle"), tree.children[0].motion);
            Assert.AreEqual(EchoesAnimationImport.Clip("AN_GhostArcher_Glide"), tree.children[1].motion);

            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Art/Prefabs/P_Enemy_GhostArcher.prefab");
            Assert.AreEqual(AnimatorControllerBuilder.ArcherControllerName, prefab.GetComponentInChildren<Animator>().runtimeAnimatorController.name);
            Assert.IsNotNull(prefab.GetComponentInChildren<AnimationEventRelay>());
            Assert.AreEqual(prefab.GetComponentInChildren<Animator>().gameObject, prefab.GetComponentInChildren<AnimationEventRelay>().gameObject, "o relay fica no objeto do Animator");
            Assert.IsNotNull(prefab.GetComponent<SpectralSway>(), "balanco procedural somado ao Idle");
        }

        [Test]
        public void GhostArcherMaterialDoesNotWashOutWithRim()
        {
            var material = AssetDatabase.LoadAssetAtPath<Material>("Assets/Art/Materials/Characters/M_Enemy_GhostArcher.mat");
            Assert.LessOrEqual(material.GetFloat("_RimIntensity"), CharacterPrefabBuilder.ArcherRimIntensity + 1e-4f, "rim fraco no tecido translucido");
            var mask = AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Art/Characters/GhostArcher/T_Enemy_GhostArcher_M.png");
            Assert.IsNotNull(mask);
            var path = Path.Combine(Application.dataPath, "Art/Characters/GhostArcher/T_Enemy_GhostArcher_M.png");
            var png = new Texture2D(2, 2);
            png.LoadImage(File.ReadAllBytes(path));
            var pixels = png.GetPixels32();
            double g = 0;
            foreach (var p in pixels) g += p.g;
            Assert.Less(g / pixels.Length, 90.0, "mascara G (rim) corrigida, baixa");
            Object.DestroyImmediate(png);
        }

        [Test]
        public void ArcherShotReleaseFrameMatchesTheCoreImpact()
        {
            var set = AssetDatabase.LoadAssetAtPath<SkillPresentationSet>($"{AnimatorControllerBuilder.SkillSetDir}/{AnimatorControllerBuilder.ArcherSkillSetName}.asset");
            Assert.IsTrue(set.TryGet(AnimatorControllerBuilder.ArcherSkillId, out var entry));
            var shoot = EchoesAnimationImport.Spec("AN_GhostArcher_Shoot");
            // A preparacao do core termina exatamente no quadro do disparo: o evento "release" e o projetil do core saem juntos.
            Assert.AreEqual(EchoesAnimationImport.ShootReleaseFrame / (float)shoot.Frames, entry.windupEnd, 1e-4f);
            var clip = EchoesAnimationImport.Clip("AN_GhostArcher_Shoot");
            var release = clip.events.First(e => e.stringParameter == "release");
            Assert.AreEqual(entry.windupEnd * clip.length, release.time, 0.03f);
            using (var rules = TestWorld.LoadNativeRules())
            {
                var timing = rules.GetActionTiming(rules.CreateEnemyStats("enemy.ghost_archer", 3), rules.FindSkill(AnimatorControllerBuilder.ArcherSkillId));
                var speed = entry.windupEnd * entry.clipSeconds / (float)timing.Windup;
                Assert.Greater(speed, 0.5f);
                Assert.Less(speed, 2f, "a velocidade do clipe fica numa faixa natural");
            }
        }

        [Test]
        public void BossRoarAndShieldChargeAreTimedByTheCore()
        {
            var set = AssetDatabase.LoadAssetAtPath<SkillPresentationSet>($"{AnimatorControllerBuilder.SkillSetDir}/SO_SkillPresentation_Boss.asset");
            var roar = EchoesAnimationImport.Clip(EchoesAnimationImport.RoarName);
            Assert.AreEqual(roar.length, set.roarClipSeconds, 1e-3f);
            Assert.IsNotNull(roar.events.FirstOrDefault(e => e.stringParameter == "summon_marks"), "Sentinelas no quadro 30");
            Assert.IsNotNull(roar.events.FirstOrDefault(e => e.stringParameter == "slam"), "impacto no quadro 48");
            Assert.IsTrue(set.TryGet("skill.enemy.guardian_shield_charge", out var charge));
            Assert.IsTrue(charge.HasPhaseStates);
            Assert.AreEqual("ChargeWindup", charge.windupState);
            Assert.AreEqual("ChargeRun", charge.impactState);
            Assert.AreEqual("ChargeRecover", charge.recoveryState);
            Assert.IsTrue(EchoesAnimationImport.Clip(EchoesAnimationImport.ChargeRunName).isLooping, "corrida em laco");
            using (var rules = TestWorld.LoadNativeRules())
            {
                var timing = rules.GetActionTiming(rules.CreateEnemyStats("enemy.crypt_guardian", 5), rules.FindSkill("skill.enemy.guardian_shield_charge"));
                Assert.AreEqual(0.9, timing.Windup, 0.15, "preparacao do core perto de 0,9 s do clipe");
                Assert.AreEqual(charge.windupClipSeconds / (float)timing.Windup, 1f, 0.5f);
                Assert.AreEqual(charge.recoveryClipSeconds / (float)timing.Recovery, 1f, 0.5f);
            }
        }

        [Test]
        public void ImpactSquashSpringsBackToTheBaseScaleAndCanBeDisabled()
        {
            var baseScale = new Vector3(1f, 1f, 1f);
            var squashed = ImpactSquash.ScaleAt(baseScale, 0.12f, 0f);
            Assert.Less(squashed.y, 1f, "achata");
            Assert.Greater(squashed.x, 1f, "alarga");
            Assert.AreEqual(squashed.x, squashed.z, 1e-6f);
            var stretched = ImpactSquash.ScaleAt(baseScale, -0.06f, 0f);
            Assert.Greater(stretched.y, 1f, "estica");
            Assert.That(Vector3.Distance(ImpactSquash.ScaleAt(baseScale, 0.12f, 1f), baseScale), Is.LessThan(0.01f), "volta a escala base");
            var go = new GameObject("squash");
            try
            {
                go.AddComponent<AttributeComponent>();
                var squash = go.AddComponent<ImpactSquash>();
                Assert.IsTrue(squash.IsActive);
                ImpactSquash.GlobalEnabled = false;
                Assert.IsFalse(squash.IsActive, "desligavel nas opcoes");
            }
            finally
            {
                ImpactSquash.GlobalEnabled = true;
                Object.DestroyImmediate(go);
            }
        }

        [Test]
        public void SpectralSwayIsSmallAndBounded()
        {
            for (var t = 0f; t < 10f; t += 0.1f)
            {
                var offset = SpectralSway.OffsetAt(t, 1.2f, 2.5f, 0.35f);
                Assert.Less(Quaternion.Angle(Quaternion.identity, offset), 4f, "balanco leve (poucos graus)");
            }
        }

        [Test]
        public void PrefabsCarryTheirController()
        {
            foreach (var (prefab, controller) in new[]
            {
                ("P_Hero_Warrior", "AC_Warrior"), ("P_Enemy_HollowSentinel", "AC_EnemyHumanoid"), ("P_Enemy_StoneHerald", "AC_EnemyHumanoid"),
                ("P_Boss_CryptGuardian", "AC_Boss"), ("P_Enemy_GhostArcher", "AC_GhostArcher"),
            })
            {
                var go = AssetDatabase.LoadAssetAtPath<GameObject>($"Assets/Art/Prefabs/{prefab}.prefab");
                var animator = go.GetComponentInChildren<Animator>();
                Assert.AreEqual(controller, animator.runtimeAnimatorController.name, prefab);
                Assert.IsFalse(animator.applyRootMotion, prefab + ": sem root motion");
            }
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
