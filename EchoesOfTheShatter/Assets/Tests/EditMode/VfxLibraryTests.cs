using System.Collections.Generic;
using System.Linq;
using Echoes.EditorTools;
using Echoes.Presentation;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace Echoes.Tests.EditMode
{
    /// <summary>
    /// Biblioteca de VFX das habilidades (docs/18 seção 6): cobertura das habilidades, orçamento de partículas e luzes (docs/03 seção 3.8),
    /// regra de cor jogador x ameaça e as contas puras do lançamento do projétil. Usa os assets gerados pelo VfxLibraryBuilder (idempotente).
    /// </summary>
    public sealed class VfxLibraryTests
    {
        static List<SkillPresentationSet> sets;

        [OneTimeSetUp]
        public void Build()
        {
            VfxLibraryBuilder.Build();
            var library = AssetDatabase.LoadAssetAtPath<SkillVfxLibrary>(VfxLibraryBuilder.LibraryPath);
            Assert.IsNotNull(library, "SO_SkillVfxLibrary em Resources/Echoes");
            sets = library.sets;
        }

        static SkillVfxEntry Entry(string id)
        {
            foreach (var set in sets)
            {
                if (set.TryGetVfx(id, out var entry)) return entry;
            }
            Assert.Fail("sem entrada de VFX para " + id);
            return null;
        }

        [TestCase("skill.warrior.iron_cut")]
        [TestCase("skill.warrior.combo_2")]
        [TestCase("skill.warrior.combo_3")]
        [TestCase("skill.warrior.heavy_slash")]
        public void WarriorStrikesLeaveABladeTrailAndASparkOnImpact(string id)
        {
            var e = Entry(id);
            Assert.IsTrue(e.trail.IsSet, id + ": rastro da lamina");
            Assert.IsNotNull(e.trail.prefab.GetComponentInChildren<BladeTrail>(), id + ": o rastro usa a faixa BladeTrail");
            Assert.IsNotEmpty(e.hitFx, id + ": faisca de impacto");
        }

        [TestCase("skill.warrior.iron_cut")]
        [TestCase("skill.warrior.combo_2")]
        [TestCase("skill.warrior.combo_3")]
        [TestCase("skill.warrior.heavy_slash")]
        public void WarriorStrikesSweepABladeArcBigEnoughToReadFrom56Meters(string id)
        {
            var e = Entry(id);
            var spec = e.releaseFx.FirstOrDefault(s => s.IsSet && s.prefab.GetComponentInChildren<VfxArcSwipe>(true) != null);
            Assert.IsNotNull(spec, id + ": arco de lamina no impacto");
            Assert.AreEqual(VfxPlace.OwnerFeet, spec.place, id + ": o arco nasce no heroi e gira para o golpe");
            var arc = new SerializedObject(spec.prefab.GetComponentInChildren<VfxArcSwipe>(true));
            Assert.GreaterOrEqual(arc.FindProperty("outerRadius").floatValue - arc.FindProperty("innerRadius").floatValue, 1.1f, id + ": faixa de pelo menos 1,1 m (85 px a 56 m)");
            Assert.GreaterOrEqual(Mathf.Abs(arc.FindProperty("endDegrees").floatValue - arc.FindProperty("startDegrees").floatValue), 170f, id + ": varre pelo menos 170 graus");
        }

        [Test]
        public void TheSecondComboHitSweepsBackTheOtherWay()
        {
            float Direction(string id)
            {
                var arc = new SerializedObject(Entry(id).releaseFx[0].prefab.GetComponentInChildren<VfxArcSwipe>(true));
                return Mathf.Sign(arc.FindProperty("endDegrees").floatValue - arc.FindProperty("startDegrees").floatValue);
            }
            Assert.AreNotEqual(Direction("skill.warrior.iron_cut"), Direction("skill.warrior.combo_2"));
        }

        [Test]
        public void TheGuardShowsTheProtectedFrontOnTheGroundAndFadesWithThePool()
        {
            var guard = Entry("class.warrior#guard");
            var arc = guard.windupFx.FirstOrDefault(s => s.IsSet && s.prefab.GetComponentInChildren<VfxArcSwipe>(true) != null);
            Assert.IsNotNull(arc, "arco no chao (docs/18 fx.guard.arc_hint)");
            Assert.AreEqual(VfxPlace.OwnerFeet, arc.place);
            Assert.IsTrue(arc.follow, "acompanha o heroi enquanto segura");
            foreach (var swipe in arc.prefab.GetComponentsInChildren<VfxArcSwipe>(true))
                Assert.IsTrue(new SerializedObject(swipe).FindProperty("persistent").boolValue, "arco fixo, nao varrido");
        }

        [Test]
        public void TheFireIsMadeOfSoftCloudsFromTheFireAtlasNotHardEdgedShards()
        {
            var e = Entry("skill.mage.fireball");
            foreach (var prefab in new[] { e.projectile, e.endFx[0].prefab })
            {
                var puffs = prefab.GetComponentsInChildren<ParticleSystemRenderer>(true).Where(r => r.sharedMaterial != null && r.sharedMaterial.mainTexture != null && r.sharedMaterial.mainTexture.name == "T_VFX_FirePuff").ToArray();
                Assert.IsNotEmpty(puffs, prefab.name + ": nuvens de fogo");
                foreach (var puff in puffs)
                    Assert.IsTrue(puff.GetComponent<ParticleSystem>().textureSheetAnimation.enabled, prefab.name + "/" + puff.name + ": sorteia a celula do atlas");
            }
        }

        [Test]
        public void TheArrowRainMarkerStaysUntilTheLastArrowLands()
        {
            var e = Entry("skill.archer.arrow_rain");
            Assert.IsTrue(e.windupFx[0].survivePhaseChange, "a marcacao nao some quando o impacto comeca");
            Assert.IsTrue(e.windupFx[0].seconds >= 0.95f, "dura a preparacao mais o impacto (0,25 + 0,7 s dos dados)");
        }

        [Test]
        public void TheThirdComboHitTrailIsWiderThanTheOthers()
        {
            Assert.Greater(Entry("skill.warrior.combo_3").trailWidth, Entry("skill.warrior.iron_cut").trailWidth);
        }

        [Test]
        public void TheHeavyStrikeGlowsWhileChargingAndFlashesAtFullCharge()
        {
            var e = Entry("skill.warrior.heavy_slash");
            Assert.IsNotEmpty(e.chargeFx, "brilho de carga e anel no chao");
            Assert.IsTrue(e.chargeFx.Any(s => s.place == VfxPlace.OwnerFeet), "anel de carga nos pes");
            Assert.IsTrue(e.chargeFx.Any(s => s.place == VfxPlace.Anchor && s.follow), "brilho acompanha a arma");
            Assert.IsNotEmpty(e.chargeFullFx, "pisca no maximo");
        }

        [Test]
        public void GuardAndPerfectGuardHaveTheirEffects()
        {
            Assert.IsNotEmpty(Entry("class.warrior#guard").windupFx, "tremeluzir do escudo");
            Assert.IsNotEmpty(Entry("class.warrior#perfect").releaseFx, "clarao da defesa perfeita");
            Assert.IsNotEmpty(Entry("class.mage#guard").windupFx, "cupula da Barreira Arcana");
            Assert.IsNotEmpty(Entry("class.mage#guard_break").releaseFx, "estilhaca ao acabar a Mana");
        }

        [TestCase("skill.archer.quick_shot")]
        [TestCase("skill.archer.fan_shot")]
        [TestCase("skill.archer.piercing_shot")]
        [TestCase("skill.archer.back_leap")]
        [TestCase("skill.mage.arcane_dart")]
        [TestCase("skill.mage.arcane_orb")]
        [TestCase("skill.mage.fireball")]
        [TestCase("skill.enemy.ghost_arrow")]
        public void ProjectileSkillsHaveAVisualThatLeavesTheHand(string id)
        {
            var e = Entry(id);
            Assert.IsNotNull(e.projectile, id + ": visual do projetil");
            Assert.IsNotEmpty(e.launchAnchor, id + ": o projetil sai da mao (ancora), nao do centro do corpo");
            Assert.Greater(e.launchBlendMeters, 0f);
        }

        [Test]
        public void TheFireballFliesAsAFireballAndExplodesInAnAreaWithSizeFromTheSkill()
        {
            var e = Entry("skill.mage.fireball");
            Assert.IsNotNull(e.projectile.GetComponentInChildren<Light>(true), "luz que viaja com a bola");
            Assert.IsNotNull(e.projectile.GetComponentInChildren<VfxLight>(true), "luz com orcamento");
            Assert.IsNotEmpty(e.endFx);
            Assert.Greater(e.endFx[0].authoredRadiusMeters, 0f, "o tamanho da explosao segue o raio da habilidade");
            var systems = e.endFx[0].prefab.GetComponentsInChildren<ParticleSystem>(true);
            foreach (var part in new[] { "Flash", "ShockGround", "Embers", "Scorch" })
                Assert.IsTrue(systems.Any(p => p.name == part), "explosao: " + part);
            var scorch = systems.First(p => p.name == "Scorch");
            Assert.AreEqual(3f, scorch.main.startLifetime.constant, 0.31f, "a marca de queimado some em ~3 s");
        }

        [Test]
        public void TheArrowRainMarksTheCircleBeforeTheArrowsFall()
        {
            var e = Entry("skill.archer.arrow_rain");
            Assert.IsNotEmpty(e.windupFx, "marcacao no chao na preparacao");
            Assert.IsNotEmpty(e.releaseFx, "flechas caindo no impacto");
            Assert.IsTrue(e.windupFx.Concat(e.releaseFx).All(s => s.place == VfxPlace.AimGround && s.authoredRadiusMeters > 0f));
            var spec = e.releaseFx[0];
            Assert.Greater(spec.endsWithPhaseAfter, 0f, "o inicio vem do tempo do impacto (SkillPhaseEvent), nao de atraso fixo no prefab");
            var arrows = spec.prefab.GetComponentsInChildren<ParticleSystem>(true).First(p => p.name == "Arrows");
            Assert.AreEqual(0f, arrows.main.startDelay.constant, "sem atraso fixo no prefab");
            var fall = arrows.main.startLifetime.constant;
            var emit = arrows.main.duration;
            // Com dois tempos de impacto diferentes, as flechas pousam entre (fim - 0,1 s) e o fim da fase.
            foreach (var phase in new[] { 0.7f, 0.5f })
            {
                var start = VfxMath.DelayToEndWithPhase(phase, spec.endsWithPhaseAfter);
                Assert.That(start + fall, Is.GreaterThanOrEqualTo(phase - 0.1f - 1e-4f), $"impacto de {phase} s: primeira flecha");
                Assert.That(start + fall + emit, Is.LessThanOrEqualTo(phase + 1e-4f), $"impacto de {phase} s: ultima flecha");
            }
            Assert.AreEqual(0f, VfxMath.DelayToEndWithPhase(0.1f, spec.endsWithPhaseAfter), "fase curta demais: toca de imediato");
        }

        [Test]
        public void TheNovaAndTheRayScaleWithTheSkill()
        {
            Assert.Greater(Entry("skill.mage.frost_nova").releaseFx[0].authoredRadiusMeters, 0f);
            Assert.IsTrue(Entry("skill.mage.arcane_ray").releaseFx.Any(s => s.lengthFromRange), "o feixe vai ate o alcance");
        }

        [Test]
        public void EveryPrefabStaysInsideTheParticleAndLightBudget()
        {
            foreach (var path in AssetDatabase.FindAssets("t:Prefab", new[] { VfxLibraryBuilder.PrefabDir }).Select(AssetDatabase.GUIDToAssetPath))
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                foreach (var ps in prefab.GetComponentsInChildren<ParticleSystem>(true))
                    Assert.LessOrEqual(ps.main.maxParticles, 150, $"{path}/{ps.name}: ate 150 particulas por sistema (docs/03 3.8)");
                var lights = prefab.GetComponentsInChildren<Light>(true);
                Assert.LessOrEqual(lights.Length, 1, path + ": uma luz por efeito");
                foreach (var light in lights)
                {
                    Assert.AreEqual(LightShadows.None, light.shadows, path + ": luz sem sombra");
                    Assert.IsNotNull(light.GetComponent<VfxLight>(), path + ": a luz passa pelo orcamento (VfxLight)");
                }
                foreach (var renderer in prefab.GetComponentsInChildren<Renderer>(true))
                {
                    Assert.AreEqual(UnityEngine.Rendering.ShadowCastingMode.Off, renderer.shadowCastingMode, $"{path}/{renderer.name}: VFX nao projeta sombra");
                    foreach (var material in renderer.sharedMaterials) Assert.IsNotNull(material, $"{path}/{renderer.name}: material");
                }
            }
        }

        [Test]
        public void ThePlayerNeverUsesTheThreatRedAsFill()
        {
            var threat = new Color(0.878f, 0.188f, 0.118f); // #E0301E: so ameaca usa como massa ou faixa (docs/03 2.4)
            foreach (var path in AssetDatabase.FindAssets("t:Prefab", new[] { VfxLibraryBuilder.PrefabDir }).Select(AssetDatabase.GUIDToAssetPath))
            {
                if (path.Contains("_Enemy_")) continue;
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                foreach (var ps in prefab.GetComponentsInChildren<ParticleSystem>(true))
                {
                    if (!ps.colorOverLifetime.enabled) continue;
                    foreach (var key in ps.colorOverLifetime.color.gradient.colorKeys)
                    {
                        var d = new Vector3(key.color.r - threat.r, key.color.g - threat.g, key.color.b - threat.b).magnitude;
                        Assert.Greater(d, 0.1f, $"{path}/{ps.name}: cor de ameaca no efeito do jogador");
                    }
                }
            }
        }

        [Test]
        public void TheEnemyArrowIsAnOpaqueMassWithADarkOutlineAndARedBand()
        {
            var prefab = Entry("skill.enemy.ghost_arrow").projectile;
            var renderers = prefab.GetComponentsInChildren<MeshRenderer>(true);
            Assert.GreaterOrEqual(renderers.Length, 2, "flecha + contorno");
            Assert.IsTrue(renderers.Any(r => r.sharedMaterial.name == "M_VFX_MeshOutline"), "contorno escuro");
            Assert.IsTrue(prefab.GetComponentsInChildren<ParticleSystem>(true).Any(p => p.name == "RedBand"), "faixa vermelha da ameaca");
        }

        [Test]
        public void LaunchBlendStartsAtTheHandAndEndsOnTheLogicalPath()
        {
            Assert.AreEqual(0f, VfxMath.LaunchBlend(0f, 1.5f), 1e-5f);
            Assert.AreEqual(1f, VfxMath.LaunchBlend(1.5f, 1.5f), 1e-5f);
            Assert.AreEqual(1f, VfxMath.LaunchBlend(9f, 1.5f), 1e-5f);
            Assert.AreEqual(0.5f, VfxMath.LaunchBlend(0.75f, 1.5f), 1e-5f);
            Assert.AreEqual(1f, VfxMath.LaunchBlend(0f, 0f), 1e-5f, "sem distancia de mistura o visual ja nasce na trajetoria");
        }

        [Test]
        public void RadiusScaleFollowsTheRealRadiusOfTheSkill()
        {
            Assert.AreEqual(1f, VfxMath.RadiusScale(2.2f, 2.2f, 1f), 1e-5f);
            Assert.AreEqual(0.5f, VfxMath.RadiusScale(1.1f, 2.2f, 1f), 1e-5f);
            Assert.AreEqual(2f, VfxMath.RadiusScale(0f, 2.2f, 2f), 1e-5f, "habilidade sem raio: escala do dado");
            Assert.AreEqual(1.5f, VfxMath.RadiusScale(5f, 0f, 1.5f), 1e-5f, "prefab sem raio de autoria: escala do dado");
        }
    }
}
