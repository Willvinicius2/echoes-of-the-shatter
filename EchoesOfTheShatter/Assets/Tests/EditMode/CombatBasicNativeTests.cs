using System.Collections.Generic;
using Echoes.Interop;
using Echoes.Interop.Native;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    /// <summary>
    /// API C 1.5 (docs/18, docs/09 secao 12) pela DLL nativa: chaves novas do combo, kit basico por classe, defesa com arco,
    /// regeneracao em movimento, recurso por golpe, perfuracao e comportamento de forma. Sem a DLL, ignorados com o motivo.
    /// </summary>
    [Category("Interop")]
    public sealed class CombatBasicNativeTests
    {
        const double Tolerance = 1e-9;

        [Test]
        public void Ext5LayoutAndApiMinorAreChecked()
        {
            TestWorld.LoadNativeRules().Dispose();
            Assert.IsTrue(NativeLayout.CheckExt5(out var message), message);
            Assert.AreEqual(26, NativeLayout.BuildExt5().Length);
            Assert.GreaterOrEqual(ShatterNative.shatter_api_minor(), 5u);
        }

        [Test]
        public void CombatRulesAndKitsComeFromTheCore()
        {
            using (var core = TestWorld.LoadNativeRules())
            {
                var combat = core.Combat;
                Assert.Greater(combat.ComboWindowSeconds, 0.0);
                Assert.Greater(combat.ComboWindowAfterDodgeSeconds, 0.0);
                Assert.Greater(combat.AttackBufferSeconds, 0.0);
                Assert.Greater(combat.HeavyHoldThresholdSeconds, 0.0);
                Assert.Greater(combat.LightWindupCreditMax, 0.0);
                Assert.LessOrEqual(combat.LightWindupCreditMax, 1.0);
                Assert.Greater(combat.GuardLowerTimeSeconds, 0.0);
                Assert.Greater(combat.DashShotRangeUu, 0.0);

                foreach (var classId in new[] { "class.warrior", "class.archer", "class.mage" })
                {
                    var kit = core.FindBasicKit(classId);
                    Assert.IsNotNull(kit, classId);
                    Assert.AreEqual(classId, kit.ClassId);
                    Assert.That(kit.LightChain.Count, Is.InRange(1, 3), classId);
                    Assert.AreEqual(core.FindClass(classId).StartingSkill, kit.LightChain[0], "o golpe 1 e a habilidade inicial");
                    foreach (var id in kit.LightChain) Assert.IsNotNull(core.FindSkill(id), id);
                    Assert.IsNotNull(core.FindSkill(kit.HeavySkill), kit.HeavySkill);
                    Assert.Greater(kit.HeavyChargeSeconds, 0.0);
                    Assert.GreaterOrEqual(kit.HeavyMaxMultiplier, 1.0);
                    Assert.IsNotEmpty(kit.ChargeEffect);
                    Assert.IsNotEmpty(kit.GuardEffect);
                    Assert.That(kit.GuardArcDegrees, Is.InRange(1.0, 360.0));
                }
                Assert.Less(core.FindBasicKit("class.warrior").GuardArcDegrees, 360.0, "o Guerreiro defende so pela frente");
                Assert.AreEqual(360.0, core.FindBasicKit("class.mage").GuardArcDegrees, Tolerance, "a cupula do Mago");
                var archer = core.FindBasicKit("class.archer");
                Assert.AreEqual(archer.LightChain[0], archer.LightChain[1], "o Arqueiro repete o golpe 1");
                Assert.IsNull(core.FindBasicKit("class.nope"));
                Assert.IsNull(core.FindBasicKit(null));
            }
        }

        [Test]
        public void GuardEffectOnlyReducesDamageFromInsideTheArc()
        {
            using (var core = TestWorld.LoadNativeRules())
            using (var attacker = core.CreateEmptyStats())
            using (var defender = core.CreateEmptyStats())
            using (var effects = core.CreateEffectSet(defender, null))
            {
                Assert.IsTrue(effects.Apply("effect.guarding.warrior", 1.0, "self"));
                var request = new HitRequest
                {
                    Attacker = attacker,
                    Defender = defender,
                    SkillTags = SkillTags.Attack | SkillTags.Melee | SkillTags.Physical,
                    BaseDamage = new DamageByType { Physical = 100.0 },
                    Coefficient = 1.0,
                    CanBeBlocked = true,
                    DefenderLife = 1000.0,
                };
                var rngOutside = core.CreateRng(99UL, RngStream.Combat, 0UL);
                var outside = core.ResolveHit(in request, ref rngOutside);
                request.FromGuardArc = true;
                var rngInside = core.CreateRng(99UL, RngStream.Combat, 0UL);
                var inside = core.ResolveHit(in request, ref rngInside);

                Assert.AreEqual(100.0, outside.TotalDamage, Tolerance, "fora do arco: dano cheio");
                Assert.Less(inside.TotalDamage, outside.TotalDamage, "dentro do arco: o efeito de defesa vale");
                Assert.AreEqual(rngOutside.State, rngInside.State, "a flag nao desloca o fluxo de sorteios");
                Assert.AreEqual(1.0, defender.Get(StatId.DamageTaken), Tolerance, "sem o contexto de arco o atributo nao muda");
                Assert.AreEqual(inside.TotalDamage / 100.0, defender.GetTagged(StatId.DamageTaken, SkillTags.Guard), Tolerance);
                Assert.Less(defender.Get(StatId.MoveSpeed), 1.0, "a lentidao de defender vale sempre");
            }
        }

        [Test]
        public void HeavyChargeMultiplierIsAppliedByTheCore()
        {
            using (var core = TestWorld.LoadNativeRules())
            using (var attacker = core.CreateEmptyStats())
            using (var defender = core.CreateEmptyStats())
            {
                var kit = core.FindBasicKit("class.warrior");
                var request = new HitRequest
                {
                    Attacker = attacker,
                    Defender = defender,
                    SkillTags = SkillTags.Attack | SkillTags.Melee | SkillTags.Physical,
                    BaseDamage = new DamageByType { Physical = 100.0 },
                    Coefficient = 1.0,
                    CanBeBlocked = true,
                    DefenderLife = 100000.0,
                };
                var rngPlain = core.CreateRng(3UL, RngStream.Combat, 0UL);
                var plain = core.ResolveHit(in request, ref rngPlain);

                request.IsHeavy = true;
                request.ClassId = "class.warrior";
                request.ChargeFraction = 1.0;
                var rngHeavy = core.CreateRng(3UL, RngStream.Combat, 0UL);
                var full = core.ResolveHit(in request, ref rngHeavy);
                Assert.AreEqual(plain.TotalDamage * kit.HeavyMaxMultiplier, full.TotalDamage, Tolerance, "carga maxima = heavy_max_mult, calculado no core");
                Assert.AreEqual(rngPlain.State, rngHeavy.State);

                request.ChargeFraction = 0.0;
                var rngMin = core.CreateRng(3UL, RngStream.Combat, 0UL);
                Assert.AreEqual(plain.TotalDamage, core.ResolveHit(in request, ref rngMin).TotalDamage, Tolerance, "carga minima = golpe comum");

                request.ChargeFraction = 1.5;
                var rngBad = core.CreateRng(3UL, RngStream.Combat, 0UL);
                var before = rngBad.State;
                var ex = Assert.Throws<NativeCallException>(() => core.ResolveHit(in request, ref rngBad));
                Assert.AreEqual(RulesStatus.InvalidArgument, ex.Status);
                Assert.AreEqual(before, rngBad.State, "recusado antes de sortear");
            }
        }

        [Test]
        public void FocusRegeneratesSlowerWhileMovingAndTheWarriorGainsResourceOnHitAndBlock()
        {
            using (var core = TestWorld.LoadNativeRules())
            {
                var archerInfo = core.FindClass("class.archer");
                using (var stats = core.CreateHeroStats(new HeroBuild("class.archer", 1, new[] { "item_base.hunter_bow" })))
                {
                    Assert.Less(archerInfo.RegenMultWhileMoving, 1.0);
                    var regen = stats.Get(StatId.ResourceRegen);
                    Assert.Greater(regen, 0.0);
                    var still = core.CreateVitals(stats, archerInfo);
                    var moving = still;
                    still.Resource = 0.0;
                    moving.Resource = 0.0;
                    core.TickVitals(ref still, stats, archerInfo, 1.0, true, false);
                    core.TickVitals(ref moving, stats, archerInfo, 1.0, true, true);
                    Assert.AreEqual(regen, still.Resource, Tolerance);
                    Assert.AreEqual(regen * archerInfo.RegenMultWhileMoving, moving.Resource, Tolerance);
                }

                var warriorInfo = core.FindClass("class.warrior");
                using (var stats = core.CreateHeroStats(new HeroBuild("class.warrior", 1, new[] { "item_base.iron_sword" })))
                {
                    var v = core.CreateVitals(stats, warriorInfo);
                    v.Resource = 0.0;
                    core.GainResourceOnHit(ref v, stats, warriorInfo);
                    Assert.AreEqual(warriorInfo.ResourceOnHit, v.Resource, Tolerance);
                    core.GainResourceOnBlock(ref v, stats, warriorInfo);
                    Assert.AreEqual(warriorInfo.ResourceOnHit + warriorInfo.ResourceOnBlock, v.Resource, Tolerance);
                }
            }
        }

        [Test]
        public void PierceAndShapeBehaviorComeFromTheCore()
        {
            using (var core = TestWorld.LoadNativeRules())
            {
                Assert.AreEqual(SkillInfo.PierceAll, core.FindSkill("skill.archer.piercing_shot").Pierce);
                Assert.AreEqual(SkillInfo.PierceAll, core.FindSkill("skill.mage.arcane_ray").Pierce);
                Assert.AreEqual(0, core.FindSkill("skill.archer.quick_shot").Pierce);
                Assert.IsTrue(core.FindSkill("skill.mage.fireball").Behavior.Explodes);
                Assert.IsTrue(core.FindSkill("skill.archer.fan_shot").Behavior.Fan);
                Assert.IsTrue(core.FindSkill("skill.mage.frost_nova").Behavior.SelfCentered);
                Assert.IsTrue(core.FindSkill("skill.archer.arrow_rain").Behavior.GroundTargeted);
                Assert.IsTrue(core.FindSkill("skill.archer.back_leap").Behavior.DashBackShot);
                Assert.IsFalse(core.FindSkill("skill.warrior.charge").Behavior.DashBackShot);
                Assert.IsFalse(core.FindSkill("skill.warrior.iron_cut").Behavior.Explodes);
                foreach (var id in new[] { "skill.mage.fireball", "skill.mage.arcane_orb" })
                {
                    var s = core.FindSkill(id);
                    Assert.Greater(s.ExplosionRadiusUu, s.RadiusUu, id + ": a explosao e maior que a largura de colisao");
                    Assert.Greater(s.RadiusUu, 0.0, id);
                }
                Assert.AreEqual(0.0, core.FindSkill("skill.mage.arcane_dart").ExplosionRadiusUu);
                Assert.Greater(core.FindSkill("skill.warrior.combo_3").KnockbackUu, 0.0, "empurrao do golpe de fecho");
                Assert.AreEqual(0.0, core.FindSkill("skill.warrior.iron_cut").KnockbackUu);
            }
        }
    }
}
