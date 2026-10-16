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

                // A lógica move o herói no passo fixo (A-04): ele chega ao alvo pela velocidade da Investida.
                world.Run(skill.Impact);
                Assert.Less(PlanarVector.Distance(hero.combatant.Position, enemy.combatant.Position), 0.5f, "chegou ao alvo");
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
                // Este teste isola a janela de invulnerabilidade: o herói fica no lugar (como se uma parede o segurasse),
                // senão a esquiva o tiraria do alcance do golpe (deslocamento coberto em MovementDodgeAndChargeAreFrameRateIndependent).
                var home = hero.combatant.Position;
                var steps = (int)System.Math.Round((secondsBeforeImpact + 2 * world.Step) / world.Step);
                for (var i = 0; i < steps; i++)
                {
                    world.Combat.Step(world.Step);
                    hero.combatant.Position = home;
                }

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
        public void MovementDodgeAndChargeAreFrameRateIndependent()
        {
            // A-04: andar, esquiva, Investida, perseguição e knockback avançam no passo fixo; a posição final
            // não pode depender do FPS. As ações entram em passos fixos exatos (iguais nas três taxas).
            var at30 = ScriptedPath(30);
            var at60 = ScriptedPath(60);
            var at144 = ScriptedPath(144);
            Assert.Greater(PlanarVector.Distance(at30.hero, PlanarVector.Zero), 3f, "o herói tem de ter andado");
            Assert.AreNotEqual(at30.enemy, new PlanarVector(0f, 6f), "o inimigo tem de ter perseguido");
            AssertSamePosition(at30.hero, at60.hero, "herói 30 x 60");
            AssertSamePosition(at30.hero, at144.hero, "herói 30 x 144");
            AssertSamePosition(at30.enemy, at60.enemy, "inimigo 30 x 60");
            AssertSamePosition(at30.enemy, at144.enemy, "inimigo 30 x 144");
        }

        [Test]
        public void ChargeCoversTheSameDistanceAtAnyFrameRate()
        {
            // A-04: a distância da Investida é velocidade x duração da fase, não soma de quadros.
            var distances = new List<float>();
            foreach (var fps in new[] { 30, 60, 144 })
            {
                using (var world = new TestWorld())
                {
                    var hero = world.AddHero(PlanarVector.Zero);
                    world.Combat.GainResource(hero.combatant, 100.0);
                    hero.logic.AimPoint = new PlanarVector(0f, 6f);
                    hero.logic.Press(HeroCommand.Skill1);
                    RunToStep(world, fps, 60, null);
                    distances.Add(PlanarVector.Distance(hero.combatant.Position, PlanarVector.Zero));
                }
            }
            Assert.Greater(distances[0], 1f, "a Investida precisa deslocar o herói");
            Assert.AreEqual(distances[0], distances[1], 1e-3f);
            Assert.AreEqual(distances[0], distances[2], 1e-3f);
        }

        static (PlanarVector hero, PlanarVector enemy) ScriptedPath(int fps)
        {
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var enemy = world.AddEnemy(Sentinel, new PlanarVector(0f, 6f));
                enemy.logic.IntegratesMovement = true;
                world.Combat.GainResource(hero.combatant, 100.0);
                hero.logic.MoveInput = new PlanarVector(1f, 0f);
                hero.logic.AimPoint = new PlanarVector(5f, 3f);
                bool dodged = false, charged = false, struck = false;
                RunToStep(world, fps, 240, step =>
                {
                    if (step >= 60 && !dodged) { dodged = true; hero.logic.Press(HeroCommand.Dodge); }
                    if (step >= 120 && !charged) { charged = true; hero.logic.Press(HeroCommand.Skill1); }
                    if (step >= 180 && !struck) { struck = true; hero.logic.Press(HeroCommand.BasicAttack); }
                });
                return (hero.combatant.Position, enemy.combatant.Position);
            }
        }

        // Roda quadros de 1/fps até o passo fixo alvo; antes de cada quadro entrega ao roteiro o passo atual,
        // então a entrada cai no mesmo passo nas três taxas (a 30 FPS o contador avança de 2 em 2: só passos pares).
        static void RunToStep(TestWorld world, int fps, long targetStep, System.Action<long> script)
        {
            var guard = fps * 20;
            while (world.Combat.StepCount < targetStep && guard-- > 0)
            {
                script?.Invoke(world.Combat.StepCount);
                world.Combat.Tick(1.0 / fps);
            }
        }

        static void AssertSamePosition(PlanarVector expected, PlanarVector actual, string label)
        {
            Assert.AreEqual(expected.X, actual.X, 1e-3f, label + " X");
            Assert.AreEqual(expected.Z, actual.Z, 1e-3f, label + " Z");
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
        public void RegistrationOrderIsStableAndHeroesComeFirst()
        {
            // A ordem de passo não depende da ordem dos Start: time, depois a chave da hierarquia.
            using (var world = new TestWorld())
            {
                var rules = world.Rules;
                Combatant Make(string id)
                {
                    var info = rules.FindEnemy(id);
                    var stats = rules.CreateEnemyStats(id, 3);
                    return new Combatant(CombatTeam.Enemy, id, 3, stats, rules.CreateEffectSet(stats, info), null, info, null, 0.5f);
                }
                var b = Make(Sentinel);
                var a = Make(Herald);
                world.Combat.Register(b, null, "0002");
                world.Combat.Register(a, null, "0001");
                var hero = world.AddHero(PlanarVector.Zero);
                Assert.AreSame(hero.combatant, world.Combat.Combatants[0]);
                Assert.AreSame(a, world.Combat.Combatants[1]);
                Assert.AreSame(b, world.Combat.Combatants[2]);
                world.Combat.Unregister(a);
                Assert.AreSame(b, world.Combat.Combatants[1]);
            }
        }

        [Test]
        public void DeniedDodgeIsReportedOnce()
        {
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                while (hero.logic.Dodge.Charges.TryConsume()) { }
                hero.logic.Press(HeroCommand.Dodge);
                world.Run(0.2);
                Assert.AreEqual(1, world.Denied.FindAll(d => d.Reason == DenyReason.NoDodgeCharges).Count);
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
