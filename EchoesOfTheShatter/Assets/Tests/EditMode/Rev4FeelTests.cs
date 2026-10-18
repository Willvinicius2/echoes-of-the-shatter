using Echoes.EditorTools;
using Echoes.Gameplay;
using Echoes.Presentation;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace Echoes.Tests.EditMode
{
    /// <summary>
    /// Rev4 do polimento de combate: corrida A como padrão (teto 2,2 só na corrida), hitstop leve da explosão e peso por habilidade
    /// (coice do arco, empurrão do cajado, tremor mínimo no tiro carregado e na Bola de Fogo) gravados nos SO.
    /// </summary>
    public sealed class Rev4FeelTests
    {
        [Test]
        public void RunUsesTheApprovedCapOf2Point2AndWalkKeeps1Point35()
        {
            if (string.IsNullOrEmpty(System.Environment.GetEnvironmentVariable("ECHOES_RUN_MAX_SCALE")))
                Assert.AreEqual(2.2f, LocomotionGroundSpeed.RunMaxScale, 1e-4f, "corrida A: teto 2,2 sem variável de ambiente");
            Assert.AreEqual(1.35f, LocomotionGroundSpeed.MaxScale, 1e-4f, "a caminhada e o resto seguem em 1,35");
            // 4,5 m/s com o clipe de 2,057 m/s de solo: a escala cabe no teto e o pé acompanha o chão (4,5 ÷ 2,057 = 2,19).
            var scale = LocomotionGroundSpeed.PlaybackScale(4.5f, 2.057f, 2.2f);
            Assert.AreEqual(4.5f / 2.057f, scale, 1e-3f);
            Assert.Less(Mathf.Abs(scale * 2.057f - 4.5f), 0.05f, "pé deslizando menos de 0,05 m/s");
            Assert.AreEqual(1.35f, LocomotionGroundSpeed.PlaybackScale(4.5f, 2.057f), 1e-4f, "sem o teto da corrida, o limite é 1,35");
        }

        [Test]
        public void LightHitstopOnlyForTheListedSkillsAndComesFromTheFeelAsset()
        {
            var asset = AssetDatabase.LoadAssetAtPath<CombatFeelSettings>("Assets/Data/Presentation/SO_CombatFeel.asset");
            Assert.IsNotNull(asset);
            foreach (var values in new[] { asset.ToValues(), CombatFeelSettings.CreateDefaultValues() })
            {
                Assert.AreEqual(0.035, values.LightHitstopFor("skill.mage.fireball"), 1e-9, "explosão da Bola de Fogo: hitstop leve de 35 ms");
                Assert.AreEqual(0.0, values.LightHitstopFor("skill.warrior.iron_cut"), 1e-9);
                Assert.AreEqual(0.0, values.LightHitstopFor(null), 1e-9);
                Assert.IsFalse(values.IsHeavy("skill.mage.fireball"), "leve, não pesado");
                Assert.IsTrue(values.IsHeavy("skill.warrior.heavy_slash"));
                Assert.IsTrue(values.IsHeavy("skill.warrior.combo_3"));
            }
        }

        [Test]
        public void SkillWeightIsAuthoredInTheSkillPresentationAssets()
        {
            var warrior = AssetDatabase.LoadAssetAtPath<SkillPresentationSet>(AnimatorControllerBuilder.WarriorSkillSetPath);
            Assert.IsTrue(warrior.TryGet("skill.warrior.combo_3", out var finisher));
            Assert.Greater(finisher.lungeMeters, 0.2f, "o fecho do combo avança o corpo");
            Assert.LessOrEqual(finisher.lungeMeters, 0.4f);

            var archer = AssetDatabase.LoadAssetAtPath<SkillPresentationSet>(AnimatorControllerBuilder.ArcherHeroSkillSetPath);
            foreach (var id in new[] { "skill.archer.quick_shot", "skill.archer.fan_shot", "skill.archer.piercing_shot" })
            {
                Assert.IsTrue(archer.TryGet(id, out var shot), id);
                Assert.AreEqual(-0.08f, shot.lungeMeters, 1e-4f, id + ": coice de 0,08 m ao soltar a flecha");
            }
            Assert.IsTrue(archer.TryGet("skill.archer.piercing_shot", out var charged));
            Assert.Greater(charged.shakeMeters, 0f, "tremor mínimo no tiro carregado");
            Assert.Less(charged.shakeMeters, 0.03f, "mínimo");

            var mage = AssetDatabase.LoadAssetAtPath<SkillPresentationSet>(AnimatorControllerBuilder.MageHeroSkillSetPath);
            Assert.IsTrue(mage.TryGet("skill.mage.fireball", out var fireball));
            Assert.Greater(fireball.lungeMeters, 0f, "empurrão de conjuração");
            Assert.Greater(fireball.shakeMeters, 0f, "tremor mínimo na Bola de Fogo");
        }

        [Test]
        public void ImpactCarryAndExitBlendsComeFromTheSkillSet()
        {
            var set = AssetDatabase.LoadAssetAtPath<SkillPresentationSet>(AnimatorControllerBuilder.WarriorSkillSetPath);
            Assert.Greater(set.impactCarrySeconds, 0f, "o swing do leve continua um pouco na recuperação (impacto de 4 a 5 quadros)");
            Assert.LessOrEqual(set.impactCarrySeconds, 0.12f);
            Assert.GreaterOrEqual(set.recoveryMinSpeed, 1f);
            Assert.LessOrEqual(set.recoveryMaxSpeed, 1.2f + 1e-4f);
            Assert.LessOrEqual(set.maxWindupSpeed, 2.5f + 1e-4f);
        }
    }
}
