using System.Linq;
using Echoes.EditorTools;
using Echoes.Gameplay;
using Echoes.Presentation;
using NUnit.Framework;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace Echoes.Tests.EditMode
{
    /// <summary>
    /// Rev5, os inimigos: pé no chão (escala medida), flinch de tronco curto, atordoamento dos inimigos Generic, peso do chefe e da morte pelos SO,
    /// rampa e virada pelos valores de feel (sem regra nova).
    /// </summary>
    public sealed class EnemyFeelTests
    {
        static AnimatorController Controller(string name) => AssetDatabase.LoadAssetAtPath<AnimatorController>(AnimatorControllerBuilder.ControllerPath(name));

        [Test]
        public void HumanoidEnemiesStepOnTheGroundWithMeasuredScales()
        {
            foreach (var spec in new[] { AnimatorControllerBuilder.EnemyHumanoid, AnimatorControllerBuilder.Boss })
            {
                var c = Controller(spec.Name);
                var loco = c.layers[0].stateMachine.states.First(s => s.state.name == "Locomotion").state;
                var tree = (BlendTree)loco.motion;
                var measured = LocomotionGroundSpeed.Load(spec.Name);
                Assert.IsNotNull(measured, spec.Name + ": velocidade de solo medida");
                // O ultimo filho e o passo na velocidade de perseguicao: escala x velocidade de solo do clipe = velocidade do jogo (pe nao desliza).
                var last = tree.children[tree.children.Length - 1];
                var clipGround = tree.children.Length == 3 ? measured.run : measured.walk;
                Assert.AreEqual(last.threshold, last.timeScale * clipGround, last.threshold * 0.12f + 0.05f, spec.Name + ": o pe acompanha o chao na velocidade de perseguicao");
            }
        }

        [Test]
        public void SentinelRunsWithAScaleThatFitsItsChaseSpeed()
        {
            var tree = (BlendTree)Controller("AC_EnemyHumanoid").layers[0].stateMachine.states.First(s => s.state.name == "Locomotion").state.motion;
            Assert.AreEqual(3, tree.children.Length, "Idle, Walk (patrulha) e Run (perseguicao)");
            Assert.AreEqual("Running_A", tree.children[2].motion.name);
            Assert.AreEqual(2.2f, tree.children[2].threshold, 1e-3f, "enemies.csv: 220 uu/s");
        }

        [Test]
        public void HumanoidEnemyFlinchIsAShortTorsoOnlyLayer()
        {
            foreach (var name in new[] { "AC_EnemyHumanoid", "AC_Boss" })
            {
                var c = Controller(name);
                var hit = c.layers.First(l => l.name == "Hit");
                Assert.IsNotNull(hit.avatarMask, name + ": o flinch so mexe o tronco (mascara), as pernas seguem a locomocao");
                var state = hit.stateMachine.states.First(s => s.state.name == "Hit").state;
                Assert.LessOrEqual(state.motion.averageDuration * state.transitions.Single().exitTime / state.speed, AnimatorControllerBuilder.EnemyFlinchPlaySeconds + 0.01f, name + ": flinch curto");
            }
            var bossSet = AssetDatabase.LoadAssetAtPath<SkillPresentationSet>("Assets/Data/Presentation/SO_SkillPresentation_Boss.asset");
            Assert.Less(bossSet.hitFlinchWeight, 0.5f, "o chefe quase nao se encolhe");
        }

        [Test]
        public void GenericEnemiesHaveAStunStateDrivenByIsStaggered()
        {
            foreach (var name in new[] { "AC_Hound", "AC_GhostArcher" })
            {
                var c = Controller(name);
                Assert.IsTrue(c.parameters.Any(p => p.name == "IsStaggered"), name);
                var stun = c.layers[0].stateMachine.states.First(s => s.state.name == "Stun").state;
                Assert.Greater(stun.speed, 0f, name + ": atordoado mas vivo, nao congelado");
                Assert.Less(stun.speed, 0.5f);
            }
        }

        [Test]
        public void HoundFeetAreMeasuredFromThePaws()
        {
            var measured = LocomotionGroundSpeed.Load("AC_Hound");
            Assert.IsNotNull(measured);
            Assert.Greater(measured.walk, 0.3f);
            Assert.Greater(measured.run, 1f);
            Assert.Greater(measured.run, measured.walk);
        }

        [Test]
        public void BossWeightAndDeathWeightComeFromTheSkillPresentationAssets()
        {
            var boss = AssetDatabase.LoadAssetAtPath<SkillPresentationSet>("Assets/Data/Presentation/SO_SkillPresentation_Boss.asset");
            Assert.IsTrue(boss.TryGet("skill.enemy.guardian_hammer", out var hammer));
            Assert.Greater(hammer.shakeMeters, 0.03f, "martelo do Guardiao: tremor de camera");
            Assert.Greater(hammer.lungeMeters, 0.2f);
            Assert.IsTrue(boss.TryGet("skill.enemy.guardian_shield_charge", out var charge));
            Assert.Greater(charge.shakeMeters, 0f, "Investida do Escudo: tremor");
            Assert.Greater(boss.deathDissolveDelaySeconds, 0.3f, "a queda tem peso antes do dissolve");
            var feel = AssetDatabase.LoadAssetAtPath<CombatFeelSettings>("Assets/Data/Presentation/SO_CombatFeel.asset").ToValues();
            foreach (var id in new[] { "skill.enemy.guardian_hammer", "skill.enemy.guardian_shield_bash", "skill.enemy.guardian_shield_charge" })
                Assert.IsTrue(feel.IsHeavy(id), id + ": hitstop de chefe pelo SO_CombatFeel");
        }

        [Test]
        public void SentinelStrikeIsTheAuthoredBlenderClipWithTheCoreTimings()
        {
            var action = Controller("AC_EnemyHumanoid").layers[1].stateMachine.states.First(st => st.state.name == "Strike").state;
            Assert.AreEqual(EchoesAnimationImport.SentinelStrikeName, action.motion.name, "golpe da Sentinela: tronco torce, peso para tras (Blender, anim_lib)");
            Assert.AreEqual(EchoesAnimationImport.SentinelFrames / EchoesAnimationImport.Fps, ((AnimationClip)action.motion).length, 0.05f);
            var set = AssetDatabase.LoadAssetAtPath<SkillPresentationSet>("Assets/Data/Presentation/SO_SkillPresentation_EnemyHumanoid.asset");
            Assert.IsTrue(set.TryGet("skill.enemy.sentinel_strike", out var entry));
            Assert.AreEqual(EchoesAnimationImport.SentinelWindupFrame / (float)EchoesAnimationImport.SentinelFrames, entry.windupEnd, 1e-3f, "fim da preparacao nos quadros do autor");
            Assert.AreEqual(EchoesAnimationImport.SentinelImpactFrame / (float)EchoesAnimationImport.SentinelFrames, entry.impactEnd, 1e-3f);
        }

        [Test]
        public void FlinchTotalIsAboutAThirdOfASecond()
        {
            foreach (var name in new[] { "AC_EnemyHumanoid", "AC_Boss", "AC_Hound", "AC_GhostArcher" })
            {
                var hit = Controller(name).layers.First(l => l.name == "Hit");
                var state = hit.stateMachine.states.First(st => st.state.name == "Hit").state;
                var exit = state.transitions.Single();
                var played = state.motion.averageDuration * exit.exitTime / state.speed;
                var total = AnimatorControllerBuilder_EntryBlend + played + exit.duration;
                Assert.That(total, Is.InRange(0.2f, 0.36f), name + ": flinch de ~0,3 s no total, com fades curtos");
                Assert.LessOrEqual(exit.duration, 0.08f + 1e-4f, name + ": saida em fade curto");
            }
        }

        const float AnimatorControllerBuilder_EntryBlend = Echoes.Presentation.PresentationController.ActionBlendSeconds;

        [Test]
        public void EnemyApproachRingAndAvoidanceAreFeelValues()
        {
            var feel = AssetDatabase.LoadAssetAtPath<CombatFeelSettings>("Assets/Data/Presentation/SO_CombatFeel.asset").ToValues();
            Assert.AreEqual(0.9f, feel.EnemyApproachFraction, 1e-4f);
            Assert.AreEqual(70f, feel.EnemySurroundSpreadDegrees, 1e-4f, "o grupo se espalha em volta do heroi em ate +-70 graus");
            Assert.Greater(feel.EnemyAvoidancePrioritySpread, 0, "prioridades de evasao diferentes quebram a simetria entre vizinhos");
            Assert.AreEqual(0.3f, feel.EnemyAvoidanceRadiusMeters, 1e-4f, "raio de evasao menor que o corpo: o inimigo nao freia por causa dos vizinhos");
        }

        [Test]
        public void EnemyRampAndTurnAreFeelValues()
        {
            var feel = AssetDatabase.LoadAssetAtPath<CombatFeelSettings>("Assets/Data/Presentation/SO_CombatFeel.asset").ToValues();
            Assert.AreEqual(0.15f, feel.EnemyAccelSeconds, 1e-4f);
            Assert.AreEqual(0.12f, feel.EnemyDecelSeconds, 1e-4f);
            Assert.Greater(feel.EnemyAttackTurnDegreesPerSecond, feel.EnemyTurnDegreesPerSecond, "o giro firma no telegrafo e no golpe");
            var defaults = CombatFeelSettings.CreateDefaultValues();
            Assert.AreEqual(feel.EnemyTurnDegreesPerSecond, defaults.EnemyTurnDegreesPerSecond, 1e-4f);
        }
    }
}
