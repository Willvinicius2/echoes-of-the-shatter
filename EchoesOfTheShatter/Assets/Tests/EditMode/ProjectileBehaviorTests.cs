using System;
using System.Collections.Generic;
using Echoes.Gameplay;
using Echoes.Interop;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    /// <summary>
    /// Comportamento dos golpes à distância pelos dados do core (docs/18, seção 8 item 3): perfuração (SkillInfo.Pierce), leque (Behavior.Fan), explosão
    /// (Behavior.Explodes), área no cursor (GroundTargeted), área em quem usa (SelfCentered) e salto com tiro (DashBackShot). Os testes com o stub marcam o
    /// Behavior na própria habilidade (só o núcleo nativo o preenche); os com a DLL conferem a classificação real.
    /// </summary>
    [Category("Gameplay")]
    public sealed class ProjectileBehaviorTests
    {
        const string Piercing = "skill.archer.piercing_shot";
        const string Fan = "skill.archer.fan_shot";
        const string Orb = "skill.mage.arcane_orb";
        const string Rain = "skill.archer.arrow_rain";
        const string Nova = "skill.mage.frost_nova";
        const string Leap = "skill.archer.back_leap";

        sealed class Rig : IDisposable
        {
            public readonly TestWorld World;
            public readonly Combatant Hero;
            public readonly HeroCombatLogic Logic;
            public readonly SkillInfo Skill;

            public Rig(string skillId, Action<SkillInfo> mark = null, IRulesCore rules = null)
            {
                World = new TestWorld(null, rules);
                Skill = World.Rules.FindSkill(skillId);
                Assert.IsNotNull(Skill, skillId);
                mark?.Invoke(Skill);
                var hero = World.AddHero(PlanarVector.Zero, 5, new[] { skillId, "", "", "", "", "" });
                Hero = hero.combatant;
                Logic = hero.logic;
                World.Combat.GainResource(Hero, 100.0);
                Logic.AimPoint = new PlanarVector(0f, 6f);
            }

            public Combatant Enemy(float x, float z)
            {
                var enemy = World.AddEnemy("enemy.hollow_sentinel", new PlanarVector(x, z)).combatant;
                return enemy;
            }

            public void Cast()
            {
                Logic.Press(HeroCommand.BasicAttack);
                World.Combat.Step(World.Step);
            }

            public void Seconds(double seconds) => World.Run(seconds);

            public void Dispose() => World.Dispose();
        }

        // Inimigos parados: o teste mede o golpe, não a IA.
        static void Freeze(Combatant enemy) => enemy.Effects.Apply("effect.stun", 1.0, "test");

        static float Speed(SkillInfo skill) => WorldUnits.ToMeters(skill.ProjectileSpeedUu);

        // ---------------------------------------------------------------------------------------------------------- perfuração

        [Test]
        public void ProjectileWithoutPierceStopsAtTheFirstTarget()
        {
            using (var rig = new Rig(Piercing, s => s.Pierce = 0))
            {
                var a = rig.Enemy(0f, 3f);
                var b = rig.Enemy(0f, 5f);
                rig.Cast();
                rig.Seconds(0.6);
                Assert.AreEqual(1, rig.World.HitsOn(a));
                Assert.AreEqual(0, rig.World.HitsOn(b));
                Assert.AreEqual(0, rig.World.Combat.Projectiles.Active.Count, "o projétil acabou no primeiro acerto");
            }
        }

        [Test]
        public void PierceAllCrossesEveryTargetAndHitsEachOnce()
        {
            using (var rig = new Rig(Piercing, s => s.Pierce = SkillInfo.PierceAll))
            {
                var targets = new[] { rig.Enemy(0f, 3f), rig.Enemy(0f, 5f), rig.Enemy(0f, 7f) };
                rig.Cast();
                rig.Seconds(0.6);
                foreach (var target in targets) Assert.AreEqual(1, rig.World.HitsOn(target), "RF-16: um acerto por alvo por projétil");
            }
        }

        [Test]
        public void PierceNCrossesNTargetsBeyondTheFirstInFlightOrder()
        {
            using (var rig = new Rig(Piercing, s => s.Pierce = 1))
            {
                var far = rig.Enemy(0f, 7f);
                var near = rig.Enemy(0f, 3f);
                var middle = rig.Enemy(0f, 5f);
                rig.Cast();
                rig.Seconds(0.6);
                Assert.AreEqual(1, rig.World.HitsOn(near));
                Assert.AreEqual(1, rig.World.HitsOn(middle), "atravessa 1 alvo além do primeiro");
                Assert.AreEqual(0, rig.World.HitsOn(far), "o terceiro, na ordem do voo, não é acertado");
            }
        }

        // ---------------------------------------------------------------------------------------------------------- leque

        [Test]
        public void FanSpreadsTheProjectilesAcrossTheConeAngleAroundTheAim()
        {
            using (var rig = new Rig(Fan, s => s.Behavior = new SkillBehavior(false, true, false, false, false)))
            {
                Assert.AreEqual(3, rig.Skill.Projectiles);
                rig.Cast();
                rig.Seconds(rig.Skill.Windup + 0.05);
                var shots = rig.World.Combat.Projectiles.Active;
                Assert.AreEqual(3, shots.Count);
                var angles = new List<float>();
                foreach (var shot in shots) angles.Add(PlanarVector.AngleDegrees(shot.Direction, PlanarVector.Forward));
                angles.Sort();
                Assert.AreEqual(0f, angles[0], 0.5f, "um no meio");
                Assert.AreEqual((float)rig.Skill.ConeAngleDegrees * 0.5f, angles[1], 0.5f);
                Assert.AreEqual((float)rig.Skill.ConeAngleDegrees * 0.5f, angles[2], 0.5f, "um para cada lado, a meia abertura");
            }
        }

        [Test]
        public void WithoutTheFanFlagTheProjectilesLeaveTogetherOnTheAim()
        {
            using (var rig = new Rig(Fan))
            {
                rig.Cast();
                rig.Seconds(rig.Skill.Windup + 0.05);
                foreach (var shot in rig.World.Combat.Projectiles.Active) Assert.AreEqual(0f, PlanarVector.AngleDegrees(shot.Direction, PlanarVector.Forward), 0.01f);
            }
        }

        [Test]
        public void SeveralArrowsOfTheSameFanCanHitTheSameCloseTargetOnceEach()
        {
            using (var rig = new Rig(Fan, s => s.Behavior = new SkillBehavior(false, true, false, false, false)))
            {
                var target = rig.Enemy(0f, 1.2f);
                Freeze(target);
                rig.Cast();
                rig.Seconds(0.6);
                Assert.AreEqual(3, rig.World.HitsOn(target), "RF-16 vale por projétil: as três flechas acertam o alvo colado");
            }
        }

        // ---------------------------------------------------------------------------------------------------------- explosão

        [Test]
        public void ExplosionHitsEveryTargetInTheRadiusOnceAtTheImpactPoint()
        {
            using (var rig = new Rig(Orb, s => s.Behavior = new SkillBehavior(true, false, false, false, false)))
            {
                var hitTarget = rig.Enemy(0f, 4f);
                var splash = rig.Enemy(1.0f, 4f);       // a 1,0 m do impacto, dentro dos 1,3 m
                var outside = rig.Enemy(3.0f, 4f);
                var ends = new List<ProjectileEvent>();
                rig.World.Events.Subscribe<ProjectileEvent>((in ProjectileEvent e) =>
                {
                    if (!e.Spawned) ends.Add(e);
                });
                Freeze(hitTarget);
                Freeze(splash);
                Freeze(outside);
                rig.Cast();
                rig.Seconds(1.0);
                Assert.AreEqual(1, rig.World.HitsOn(hitTarget));
                Assert.AreEqual(1, rig.World.HitsOn(splash), "dano em área no ponto do impacto, um acerto por alvo");
                Assert.AreEqual(0, rig.World.HitsOn(outside));
                Assert.AreEqual(1, ends.Count);
                Assert.AreEqual(WorldUnits.ToMeters(rig.Skill.RadiusUu), ends[0].ExplosionRadiusMeters, 1e-4f, "o VFX lê o raio no evento de fim do projétil");
                Assert.Less(ends[0].Position.Z, 4f, "o ponto do impacto é onde o projétil tocou o alvo, não o centro dele");
            }
        }

        [Test]
        public void ProjectileThatDoesNotExplodeIgnoresTheRadiusAsABody()
        {
            using (var rig = new Rig(Orb))
            {
                var near = rig.Enemy(1.0f, 4f);
                Freeze(near);
                rig.Cast();
                rig.Seconds(1.0);
                // Sem o flag (stub), o radius do CSV segue sendo a meia largura do corredor: comportamento antigo.
                Assert.AreEqual(1, rig.World.HitsOn(near));
            }
            Assert.AreEqual(0f, ProjectileSystem.BodyRadiusMeters(MarkExplodes(Orb)), "quem explode voa como um ponto");
        }

        static SkillInfo MarkExplodes(string id)
        {
            var rules = TestWorld.LoadRules();
            var skill = rules.FindSkill(id);
            skill.Behavior = new SkillBehavior(true, false, false, false, false);
            return skill;
        }

        // ---------------------------------------------------------------------------------------------------------- área no cursor e em quem usa

        [Test]
        public void GroundTargetedAreaLocksTheCircleAtTheCursorAndHitsAtTheEndOfTheImpact()
        {
            using (var rig = new Rig(Rain, s => s.Behavior = new SkillBehavior(false, false, false, true, false)))
            {
                var inside = rig.Enemy(0f, 6f);
                var outside = rig.Enemy(0f, 11f);
                Freeze(inside);
                Freeze(outside);
                rig.Logic.AimPoint = new PlanarVector(0f, 6f);
                rig.Cast();
                rig.Seconds(rig.Skill.Windup + rig.Skill.Impact * 0.5);
                Assert.AreEqual(0, rig.World.HitsOn(inside), "ainda não caiu: o impact é o atraso até acertar");
                rig.Logic.AimPoint = new PlanarVector(0f, 11f); // o cursor foge depois de lançar: o círculo não segue
                rig.Seconds(rig.Skill.Impact * 0.5 + 0.1);
                Assert.AreEqual(1, rig.World.HitsOn(inside), "caiu no círculo travado no começo");
                Assert.AreEqual(0, rig.World.HitsOn(outside));
            }
        }

        [Test]
        public void GroundTargetedAreaIsLimitedByTheRangeFromTheHero()
        {
            using (var rig = new Rig(Rain, s => s.Behavior = new SkillBehavior(false, false, false, true, false)))
            {
                var edge = rig.Enemy(0f, WorldUnits.ToMeters(rig.Skill.RangeUu));
                Freeze(edge);
                rig.Logic.AimPoint = new PlanarVector(0f, 40f);
                rig.Cast();
                rig.Seconds(rig.Skill.Windup + rig.Skill.Impact + 0.1);
                Assert.AreEqual(1, rig.World.HitsOn(edge), "cursor longe demais: o círculo cai no alcance máximo");
            }
        }

        [Test]
        public void SelfCenteredAreaIgnoresTheCursor()
        {
            using (var rig = new Rig(Nova, s => s.Behavior = new SkillBehavior(false, false, true, false, false)))
            {
                var radius = WorldUnits.ToMeters(rig.Skill.RadiusUu);
                var close = rig.Enemy(radius - 0.9f, 0f);
                var far = rig.Enemy(radius + 1.5f, 0f);
                Freeze(close);
                Freeze(far);
                rig.Logic.AimPoint = new PlanarVector(0f, 30f);
                rig.Cast();
                rig.Seconds(rig.Skill.Windup + rig.Skill.Impact + 0.1);
                Assert.AreEqual(1, rig.World.HitsOn(close), "centrada em quem usa");
                Assert.AreEqual(0, rig.World.HitsOn(far));
            }
        }

        // ---------------------------------------------------------------------------------------------------------- DLL: classificação real do core

        [Test]
        public void NativeCoreClassifiesTheArcherAndMageSkillsAndTheLogicFollowsIt()
        {
            var rules = TestWorld.LoadNativeRules();
            using (var rig = new Rig(Leap, null, rules))
            {
                Assert.IsTrue(rig.Skill.Behavior.DashBackShot);
                Assert.IsTrue(rules.FindSkill(Fan).Behavior.Fan);
                Assert.IsTrue(rules.FindSkill(Orb).Behavior.Explodes);
                Assert.IsTrue(rules.FindSkill(Rain).Behavior.GroundTargeted);
                Assert.IsTrue(rules.FindSkill(Nova).Behavior.SelfCentered);
                Assert.AreEqual(SkillInfo.PierceAll, rules.FindSkill(Piercing).Pierce);

                // Salto para trás: sai para longe da mira, o alcance inteiro, e atira no pico (dash_shot_range).
                var start = rig.Hero.Position;
                rig.Cast();
                rig.Seconds(rig.Skill.Windup + rig.Skill.Impact + 0.02);
                var jumped = start.Z - rig.Hero.Position.Z;
                Assert.AreEqual(WorldUnits.ToMeters(rig.Skill.RangeUu), jumped, 0.3f, "pulou o alcance para trás da mira (+Z)");
                var shots = rig.World.Combat.Projectiles.Active;
                Assert.AreEqual(1, shots.Count, "o tiro do pico");
                Assert.AreEqual(WorldUnits.ToMeters(rules.Combat.DashShotRangeUu), shots[0].RemainingMeters, 1.5f, "alcance dash_shot_range (já voou alguns passos)");
                Assert.Greater(shots[0].Direction.Z, 0.99f, "atira para a mira, não para trás");
            }
        }
    }
}
