using System.Collections.Generic;
using Echoes.Gameplay;
using Echoes.Interop;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    /// <summary>
    /// Combate em passo fixo com o stub do motor de regras e os CSV reais. Cobre RF-11, RF-13, RF-15,
    /// RF-16, RF-17 (hitstop por entidade) e RF-20 sem cena.
    /// </summary>
    [Category("Gameplay")]
    public sealed class CombatSystemTests
    {
        const string Sentinel = "enemy.hollow_sentinel";
        const string Herald = "enemy.stone_herald";

        [Test]
        public void IronCutHitsEachTargetAtMostOncePerSwing()
        {
            // RF-16: um inimigo grande registra 1 acerto por golpe.
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var big = world.AddEnemy(Herald, new PlanarVector(0f, 1.2f), radius: 1.5f);
                hero.logic.Press(HeroCommand.BasicAttack);
                world.Run(0.6);
                Assert.AreEqual(1, world.HitsOn(big.combatant));
            }
        }

        [Test]
        public void IronCutDamagesThroughTheRulesCore()
        {
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var enemy = world.AddEnemy(Sentinel, new PlanarVector(0f, 1.2f));
                var before = enemy.combatant.Life;
                hero.logic.Press(HeroCommand.BasicAttack);
                world.Run(0.6);
                Assert.AreEqual(1, world.Hits.Count);
                var hit = world.Hits[0];
                Assert.IsTrue(hit.Result.Landed);
                Assert.AreEqual(before - hit.Result.LifeLost, enemy.combatant.Life, 1e-9);
                Assert.Greater(hit.Result.LifeLost, 0.0);
            }
        }

        [Test]
        public void IronCutGeneratesMomentum()
        {
            // RF-14: acertar enche o Ímpeto (resourceOnHit do classes.csv).
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                world.AddEnemy(Sentinel, new PlanarVector(0f, 1.2f));
                Assert.AreEqual(0.0, hero.combatant.Resource, "Ímpeto começa vazio");
                hero.logic.Press(HeroCommand.BasicAttack);
                world.Run(0.3);
                Assert.AreEqual(hero.combatant.Class.ResourceOnHit, hero.combatant.Resource, 1.0);
            }
        }

        [Test]
        public void MomentumDrainsOutOfCombat()
        {
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                world.Combat.GainResource(hero.combatant, 50.0);
                world.Run(world.Rules.Combat.OutOfCombatSeconds + 30.0);
                Assert.AreEqual(0.0, hero.combatant.Resource, 1e-9);
            }
        }

        [Test]
        public void SkillWithoutMomentumIsDenied()
        {
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                hero.logic.Press(HeroCommand.Skill2); // Fenda de Pedra custa Ímpeto
                world.Run(world.Step);
                Assert.IsFalse(hero.logic.IsCasting);
                Assert.IsTrue(world.Denied.Exists(d => d.Reason == DenyReason.NoResource));
            }
        }

        [Test]
        public void StoneRiftHitsThreeGroupedEnemiesAhead()
        {
            // RF-13: a Fenda de Pedra atinge 3 ou mais inimigos agrupados à frente.
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var a = world.AddEnemy(Sentinel, new PlanarVector(-0.6f, 2.5f));
                var b = world.AddEnemy(Sentinel, new PlanarVector(0f, 3f));
                var c = world.AddEnemy(Sentinel, new PlanarVector(0.6f, 2.5f));
                world.Combat.GainResource(hero.combatant, 100.0);
                hero.logic.Press(HeroCommand.Skill2);
                world.Run(0.6);
                Assert.AreEqual(1, world.HitsOn(a.combatant));
                Assert.AreEqual(1, world.HitsOn(b.combatant));
                Assert.AreEqual(1, world.HitsOn(c.combatant));
            }
        }

        [Test]
        public void ChargeHitsOnArrivalNotBefore()
        {
            // RF-13: a Investida aplica dano na chegada.
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var enemy = world.AddEnemy(Sentinel, new PlanarVector(0f, 4f));
                world.Combat.GainResource(hero.combatant, 100.0);
                hero.logic.AimPoint = enemy.combatant.Position;
                hero.logic.Press(HeroCommand.Skill1);
                world.Run(world.Step);
                var skill = hero.logic.CurrentSkill;
                Assert.AreEqual(SkillShape.Dash, skill.Shape);

                // Fim da preparação: começa o avanço, ainda sem dano.
                world.Run(skill.Windup);
                Assert.AreEqual(ActionPhase.Impact, hero.logic.Action.Phase);
                var velocity = hero.logic.CurrentVelocity();
                Assert.Greater(velocity.Magnitude, 0f, "avança durante o impacto");
                Assert.AreEqual(0, world.HitsOn(enemy.combatant));

                // A cena move o herói; aqui ele chega ao alvo pela velocidade da lógica.
                hero.combatant.Position = enemy.combatant.Position - PlanarVector.Forward * 0.8f;
                world.Run(skill.Impact);
                Assert.AreEqual(1, world.HitsOn(enemy.combatant));
            }
        }

        [Test]
        public void DodgeIFramesAvoidTheHitAndLateDodgeDoesNot()
        {
            // RF-15: golpe aos 0,1 s da esquiva causa 0; aos 0,3 s causa dano.
            Assert.IsTrue(DodgeAvoidsHit(0.1), "aos 0,1 s da esquiva o golpe é evitado");
            Assert.IsFalse(DodgeAvoidsHit(0.3), "aos 0,3 s da esquiva o golpe acerta");
        }

        /// <summary>Esquiva <paramref name="secondsBeforeImpact"/> antes do impacto; true se o golpe foi evitado.</summary>
        static bool DodgeAvoidsHit(double secondsBeforeImpact)
        {
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var enemy = world.AddEnemy(Sentinel, new PlanarVector(0f, 1.2f));
                var telegraphs = new List<TelegraphEvent>();
                world.Events.Subscribe<TelegraphEvent>((in TelegraphEvent e) => { if (e.Started) telegraphs.Add(e); });

                for (var i = 0; i < 600 && telegraphs.Count == 0; i++) world.Combat.Step(world.Step);
                Assert.AreEqual(1, telegraphs.Count, "o inimigo telegrafou");
                var windup = telegraphs[0].DurationSeconds;

                world.Run(windup - secondsBeforeImpact - world.Step);
                hero.logic.Press(HeroCommand.Dodge);
                var lifeBefore = hero.combatant.Life;
                world.Run(secondsBeforeImpact + 2 * world.Step);

                Assert.IsTrue(hero.logic.Dodge.IsDodging || hero.logic.Dodge.Charges.Charges < hero.logic.Dodge.Charges.MaxCharges, "esquivou");
                var avoided = world.Avoided.Count > 0;
                if (avoided) Assert.AreEqual(lifeBefore, hero.combatant.Life, 1.0, "esquiva perfeita não tira vida");
                else Assert.Greater(world.HitsOn(hero.combatant), 0);
                return avoided;
            }
        }

        [Test]
        public void SameScriptSameDamageAt30And144Fps()
        {
            // RF-11: o mesmo roteiro de entrada contra um Arauto dá o mesmo dano a 30 e a 144 FPS.
            var at30 = ScriptedDamage(30);
            var at144 = ScriptedDamage(144);
            Assert.Greater(at30, 0.0);
            Assert.AreEqual(at30, at144, 1e-9);
        }

        static double ScriptedDamage(int fps)
        {
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var herald = world.AddEnemy(Herald, new PlanarVector(0f, 1.4f));
                var frames = fps * 4;
                for (var f = 0; f < frames; f++)
                {
                    // Aperta o ataque básico a cada 0,5 s de tempo real (mesmos instantes nas duas taxas).
                    if (f % (fps / 2) == 0) hero.logic.Press(HeroCommand.BasicAttack);
                    world.Combat.Tick(1.0 / fps);
                }
                var total = 0.0;
                foreach (var hit in world.Hits)
                {
                    if (ReferenceEquals(hit.Target, herald.combatant)) total += hit.Result.TotalDamage;
                }
                return total;
            }
        }

        [Test]
        public void HitstopFreezesOnlyTheEntitiesInvolved()
        {
            // RF-17: hitstop por entidade; o resto do combate continua.
            var feel = new CombatFeelValues { HitstopCriticalSeconds = 0.08, HitstopHeavySeconds = 0.06, HitstopPlayerHitSeconds = 0.04 };
            feel.HeavySkills.Add("skill.warrior.stone_rift");
            using (var world = new TestWorld(feel))
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var target = world.AddEnemy(Sentinel, new PlanarVector(0f, 2.5f));
                var bystander = world.AddEnemy(Sentinel, new PlanarVector(20f, 0f));
                world.Combat.GainResource(hero.combatant, 100.0);
                hero.logic.Press(HeroCommand.Skill2);

                for (var i = 0; i < 120 && world.Hits.Count == 0; i++) world.Combat.Step(world.Step);
                Assert.AreEqual(1, world.Hits.Count);
                Assert.IsTrue(hero.combatant.Hitstop.IsActive, "quem bateu congela");
                Assert.IsTrue(target.combatant.Hitstop.IsActive, "quem apanhou congela");
                Assert.IsFalse(bystander.combatant.Hitstop.IsActive, "o resto não");

                var elapsed = hero.logic.Action.TotalElapsed;
                world.Combat.Step(world.Step);
                Assert.AreEqual(elapsed, hero.logic.Action.TotalElapsed, 1e-12, "timers parados no hitstop");
                Assert.AreEqual(0f, hero.logic.CurrentVelocity().Magnitude);
            }
        }

        [Test]
        public void EnemyGoesThroughTheFiveStatesAgainstTheHero()
        {
            // RF-20 (roteiro AI.EnemyFiveStatesInLog sem cena).
            using (var world = new TestWorld())
            {
                world.AddHero(PlanarVector.Zero);
                var enemy = world.AddEnemy(Sentinel, new PlanarVector(0f, 1.2f));
                var seen = new HashSet<EnemyBrainState> { enemy.logic.Brain.State };
                enemy.logic.StateChanged += (from, to) => seen.Add(to);
                world.Run(3.0);
                Assert.IsTrue(seen.SetEquals(new[]
                {
                    EnemyBrainState.Idle, EnemyBrainState.Chase, EnemyBrainState.Telegraph,
                    EnemyBrainState.Attack, EnemyBrainState.Recover,
                }));
            }
        }

        [Test]
        public void KilledEnemyStopsActingAndDeathIsPublished()
        {
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var enemy = world.AddEnemy(Sentinel, new PlanarVector(0f, 1.2f), level: 1);
                var deaths = new List<CombatantDiedEvent>();
                world.Events.Subscribe<CombatantDiedEvent>((in CombatantDiedEvent e) => deaths.Add(e));
                for (var i = 0; i < 40 && !enemy.combatant.IsDead; i++)
                {
                    hero.logic.Press(HeroCommand.BasicAttack);
                    world.Run(0.5);
                }
                Assert.IsTrue(enemy.combatant.IsDead);
                Assert.AreEqual(1, deaths.Count);
                Assert.AreSame(hero.combatant, deaths[0].Killer);
                Assert.AreEqual(EnemyBrainState.Dead, enemy.logic.Brain.State);
            }
        }

        [Test]
        public void PotionWithZeroChargesDoesNothingAndWarns()
        {
            // RF-19: poção com 0 cargas não faz nada e dá aviso.
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var potion = hero.logic.GetPotion(0);
                Assert.IsNotNull(potion);
                while (potion.Charges.TryConsume()) { }
                hero.logic.Press(HeroCommand.Potion1);
                world.Run(world.Step);
                Assert.IsFalse(hero.logic.IsDrinking);
                Assert.IsTrue(world.Denied.Exists(d => d.Reason == DenyReason.PotionEmpty));
            }
        }

        [Test]
        public void LifePotionHealsAfterDrinking()
        {
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var enemy = world.AddEnemy(Herald, new PlanarVector(0f, 1.2f));
                for (var i = 0; i < 600 && hero.combatant.Life >= hero.combatant.MaxLife; i++) world.Combat.Step(world.Step);
                Assert.Less(hero.combatant.Life, hero.combatant.MaxLife, "o Arauto acertou");
                world.Combat.Unregister(enemy.combatant);

                var before = hero.combatant.Life;
                var charges = hero.logic.GetPotion(0).Charges.Charges;
                hero.logic.Press(HeroCommand.Potion1);
                world.Run(world.Step);
                Assert.IsTrue(hero.logic.IsDrinking);
                world.Run(hero.logic.GetPotion(0).Potion.UseTime + world.Step);
                Assert.Greater(hero.combatant.Life, before);
                Assert.AreEqual(charges - 1, hero.logic.GetPotion(0).Charges.Charges);
            }
        }

        [Test]
        public void ReviveRefillsLifeAndPotions()
        {
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var potion = hero.logic.GetPotion(0);
                potion.Charges.TryConsume();
                world.Combat.Revive(hero.combatant);
                Assert.AreEqual(hero.combatant.MaxLife, hero.combatant.Life, 1e-9);
                Assert.IsTrue(potion.Charges.IsFull);
            }
        }

        [Test]
        public void LockedSkillIsDenied()
        {
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero, level: 1);
                Assert.IsTrue(hero.logic.GetSlot(0).Unlocked, "Corte de Ferro libera no nível 1");
                Assert.IsFalse(hero.logic.GetSlot(1).Unlocked, "Investida libera no nível 2");
                hero.logic.Press(HeroCommand.Skill1);
                world.Run(world.Step);
                Assert.IsTrue(world.Denied.Exists(d => d.Reason == DenyReason.Locked));
            }
        }
    }
}
