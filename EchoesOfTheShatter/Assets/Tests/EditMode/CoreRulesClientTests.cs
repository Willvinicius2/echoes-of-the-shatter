using System.Collections.Generic;
using Echoes.Gameplay;
using Echoes.Interop;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    /// <summary>
    /// Casos automáticos de docs/10_qa.md, seção 8, que valem para o cliente: o gameplay consulta e avança o estado pelo core
    /// (cinto de poções, esquiva, actor de stun e Guarda Quebrada, chefe, elite). Os números vêm dos CSV; nada é fixado aqui.
    /// Os de cinto e esquiva rodam no stub e no nativo; os de stun, chefe e elite só no nativo (o stub não os tem).
    /// </summary>
    [Category("CoreRules")]
    public sealed class CoreRulesClientTests
    {
        const string Sentinel = "enemy.hollow_sentinel";
        const string Herald = "enemy.stone_herald";
        const string Shielded = "enemy.shielded_sentinel";
        const string Guardian = "enemy.crypt_guardian";
        const double Tol = 1e-6;

        static IRulesCore Core(string kind) => kind == "native" ? TestWorld.LoadNativeRules() : TestWorld.LoadRules();

        static IStatBlock Hero(IRulesCore rules)
        {
            var build = new HeroBuild("class.warrior", 5, new[] { "item_base.iron_sword" });
            return rules.CreateHeroStats(in build);
        }

        // ---------------------------------------------------------------------------------------
        // 8.1 Poções (cinto do core)
        // ---------------------------------------------------------------------------------------

        [TestCase("native")]
        [TestCase("stub")]
        public void POT07_GlobalLockoutBlocksTheOtherPotionUntilItEnds(string kind)
        {
            using (var rules = Core(kind))
            using (var stats = Hero(rules))
            using (var belt = rules.CreatePotionBelt())
            {
                var lockout = rules.Combat.PotionLockoutSeconds;
                Assert.AreEqual(PotionUseStatus.Ok, belt.TryUse(0, stats));
                Assert.AreEqual(PotionUseStatus.LockedOut, belt.TryUse(1, stats), "no mesmo instante");
                belt.Tick(lockout - 0.05);
                Assert.AreEqual(PotionUseStatus.LockedOut, belt.TryUse(1, stats), "antes do fim da trava");
                belt.Tick(0.06);
                Assert.AreEqual(PotionUseStatus.Ok, belt.TryUse(1, stats), "depois da trava");
            }
        }

        [TestCase("native")]
        [TestCase("stub")]
        public void POT08_RechargeIsSerialOneChargeAtATime(string kind)
        {
            using (var rules = Core(kind))
            using (var stats = Hero(rules))
            using (var belt = rules.CreatePotionBelt())
            {
                var info = rules.Potions[0];
                var lockout = rules.Combat.PotionLockoutSeconds;
                var elapsed = 0.0;
                for (var i = 0; i < info.MaxCharges; i++)
                {
                    Assert.AreEqual(PotionUseStatus.Ok, belt.TryUse(0, stats));
                    belt.Tick(lockout + 0.01);
                    elapsed += lockout + 0.01;
                }
                Assert.AreEqual(0, belt.GetEntry(0).Charges);
                belt.Tick(info.RechargeSeconds - elapsed + 0.5);
                Assert.AreEqual(1, belt.GetEntry(0).Charges, "1 carga ao fim de uma recarga");
                belt.Tick(info.RechargeSeconds);
                Assert.AreEqual(2, belt.GetEntry(0).Charges, "nunca duas ao mesmo tempo");
                belt.Tick(info.RechargeSeconds);
                Assert.AreEqual(info.MaxCharges, belt.GetEntry(0).Charges);
            }
        }

        [TestCase("native")]
        [TestCase("stub")]
        public void POT10_To12_EliteKillRefillsTheLowestAndNeverOverflows(string kind)
        {
            using (var rules = Core(kind))
            using (var stats = Hero(rules))
            using (var belt = rules.CreatePotionBelt())
            {
                var lockout = rules.Combat.PotionLockoutSeconds + 0.01;
                // POT-10: Vida 1/3 e Resguardo 0/2 -> o Resguardo (menos cargas) ganha 1.
                belt.TryUse(0, stats); belt.Tick(lockout);
                belt.TryUse(0, stats); belt.Tick(lockout);
                belt.TryUse(1, stats); belt.Tick(lockout);
                belt.TryUse(1, stats); belt.Tick(lockout);
                Assert.AreEqual(1, belt.GetEntry(0).Charges);
                Assert.AreEqual(0, belt.GetEntry(1).Charges);
                Assert.IsTrue(belt.OnEliteKilled());
                Assert.AreEqual(1, belt.GetEntry(0).Charges);
                Assert.AreEqual(1, belt.GetEntry(1).Charges, "o Resguardo ganhou 1");

                // POT-11: empate vai para a Vida.
                belt.Refill();
                belt.TryUse(0, stats); belt.Tick(lockout);
                Assert.AreEqual(2, belt.GetEntry(0).Charges);
                Assert.AreEqual(belt.GetEntry(1).MaxCharges, belt.GetEntry(1).Charges);
                Assert.IsTrue(belt.OnEliteKilled());
                Assert.IsTrue(belt.GetEntry(0).IsFull, "a Vida recebeu a carga");
                Assert.IsTrue(belt.GetEntry(1).IsFull);

                // POT-12: tudo cheio, nada a acrescentar.
                Assert.IsFalse(belt.OnEliteKilled());
                Assert.IsTrue(belt.GetEntry(0).IsFull);
            }
        }

        [TestCase("native")]
        [TestCase("stub")]
        public void POT14_RefillOnRevive(string kind)
        {
            using (var world = new TestWorld(null, Core(kind)))
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var potion = hero.logic.GetPotion(0);
                hero.logic.Press(HeroCommand.Potion1);
                world.Run(potion.Potion.UseTime + 0.1);
                Assert.Less(potion.Charges, potion.MaxCharges);
                world.Combat.Revive(hero.combatant);
                Assert.IsTrue(potion.IsFull, "o checkpoint enche as poções");
            }
        }

        [Test]
        public void POT09_DrinkingTakesUseTimeAndSlowsMovement()
        {
            using (var world = new TestWorld(null, TestWorld.LoadNativeRules()))
            {
                var hero = world.AddHero(PlanarVector.Zero);
                hero.logic.MoveInput = new PlanarVector(1f, 0f);
                var walk = hero.logic.CurrentVelocity().Magnitude;
                Assert.Greater(walk, 0f);
                var potion = hero.logic.GetPotion(0).Potion;
                hero.logic.Press(HeroCommand.Potion1);
                world.Run(world.Step);
                Assert.IsTrue(hero.logic.IsDrinking);
                // A rampa de movimento (API C 1.7) leva a velocidade ao alvo em accel s; depois dela vale a velocidade do uso.
                world.Run(world.Rules.Combat.HeroMoveAccelSeconds * 2.0);
                Assert.IsTrue(hero.logic.IsDrinking);
                Assert.AreEqual(walk * potion.MoveSpeedWhileUsing, hero.logic.CurrentVelocity().Magnitude, 1e-3, "velocidade durante o uso");
                world.Run(potion.UseTime + world.Step);
                Assert.IsFalse(hero.logic.IsDrinking, "o uso dura use_time");
                world.Run(world.Rules.Combat.HeroMoveAccelSeconds * 2.0);
                Assert.AreEqual(walk, hero.logic.CurrentVelocity().Magnitude, 1e-3);
            }
        }

        // ---------------------------------------------------------------------------------------
        // 8.2 Esquiva (estado do core)
        // ---------------------------------------------------------------------------------------

        [TestCase("native")]
        [TestCase("stub")]
        public void ESQ01_InvulnerabilityIncludesStartAndExcludesItsEnd(string kind)
        {
            using (var rules = Core(kind))
            using (var dodge = rules.CreateDodge())
            {
                var iframes = rules.Combat.DodgeInvulnerableSeconds;
                Assert.AreEqual(DodgeStartStatus.Ok, dodge.TryStart(0.0));
                Assert.IsTrue(dodge.IsInvulnerable, "t = 0,00");
                dodge.Tick(iframes - 0.001);
                Assert.IsTrue(dodge.IsInvulnerable, "logo antes do fim");
                dodge.Tick(0.001);
                Assert.IsFalse(dodge.IsInvulnerable, "t = dodge_iframes");
            }
        }

        [TestCase("native")]
        [TestCase("stub")]
        public void ESQ02_03_ThreeChargesThenDeniedAndSerialRecharge(string kind)
        {
            using (var rules = Core(kind))
            using (var dodge = rules.CreateDodge())
            {
                var duration = rules.Combat.DodgeDurationSeconds;
                var recharge = rules.Combat.DodgeRechargeSeconds;
                for (var i = 0; i < dodge.MaxCharges; i++)
                {
                    Assert.AreEqual(DodgeStartStatus.Ok, dodge.TryStart(0.0), "esquiva " + (i + 1));
                    dodge.Tick(duration + 0.01);
                }
                Assert.AreEqual(DodgeStartStatus.NoCharges, dodge.TryStart(0.0), "a 4a seguida e negada");
                dodge.Tick(recharge - dodge.MaxCharges * (duration + 0.01) + 0.05);
                Assert.AreEqual(1, dodge.Charges, "1 carga em dodge_recharge");
                dodge.Tick(recharge * 2.0);
                Assert.AreEqual(dodge.MaxCharges, dodge.Charges, "cheia depois de recarregar todas");
            }
        }

        [Test]
        public void ESQ04_DodgeCostsOnlyACharge()
        {
            using (var world = new TestWorld(null, TestWorld.LoadNativeRules()))
            {
                var hero = world.AddHero(PlanarVector.Zero);
                world.Combat.GainResource(hero.combatant, 50.0);
                var life = hero.combatant.Life;
                // Controle: o mesmo tempo sem esquivar, para separar o decaimento natural do Impeto fora de combate.
                double control;
                using (var other = new TestWorld(null, TestWorld.LoadNativeRules()))
                {
                    var h2 = other.AddHero(PlanarVector.Zero);
                    other.Combat.GainResource(h2.combatant, 50.0);
                    other.Run(world.Step * 2);
                    control = h2.combatant.Resource;
                }
                hero.logic.Press(HeroCommand.Dodge);
                world.Run(world.Step * 2);
                Assert.IsTrue(hero.logic.Dodge.IsDodging);
                Assert.AreEqual(control - world.Rules.Combat.DodgeResourceCost, hero.combatant.Resource, Tol, "so a carga (dodge_cost_resource do CSV)");
                Assert.AreEqual(life, hero.combatant.Life, Tol);
                Assert.AreEqual(hero.logic.Dodge.MaxCharges - 1, hero.logic.Dodge.Charges);
            }
        }

        [Test]
        public void ESQ10_PerfectDodgeGivesTheResourcePerHitInsideTheIFrames()
        {
            using (var world = new TestWorld(null, TestWorld.LoadNativeRules()))
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var enemy = world.AddEnemy(Sentinel, new PlanarVector(0f, 1.2f));
                var skill = world.Rules.FindSkill("skill.warrior.iron_cut");
                hero.logic.Press(HeroCommand.Dodge);
                world.Run(world.Step * 2);
                Assert.IsTrue(hero.combatant.IsInvulnerable);
                var before = hero.combatant.Resource;
                world.Combat.ApplySkillHit(enemy.combatant, hero.combatant, skill, enemy.combatant.Position);
                world.Combat.ApplySkillHit(enemy.combatant, hero.combatant, skill, enemy.combatant.Position);
                var reward = world.Rules.Combat.DodgePerfectResource;
                Assert.AreEqual(reward * 2.0, hero.combatant.Resource - before, Tol, "dois golpes nos i-frames: o recurso vale por golpe");
            }
        }

        // ---------------------------------------------------------------------------------------
        // 8.3 Stun e imunidades; 8.4 Guarda Quebrada (actor do core)
        // ---------------------------------------------------------------------------------------

        [Test]
        public void STN01_04_StunLastsItsDurationAndRefreshesInsteadOfStacking()
        {
            using (var world = new TestWorld(null, TestWorld.LoadNativeRules()))
            {
                var enemy = world.AddEnemy(Sentinel, new PlanarVector(50f, 50f));
                Assert.IsTrue(world.Rules.CanAct(enemy.combatant.Stats));
                Assert.IsTrue(world.Combat.ApplyEffect(enemy.combatant, "effect.stun", 1.0, "hero"));
                var duration = enemy.combatant.Effects.LastApply.StunSeconds; // a duracao vem do effects.csv, pelo core
                Assert.Greater(duration, 0.5);
                Assert.IsFalse(world.Rules.CanAct(enemy.combatant.Stats), "atordoado nao age");
                Assert.IsFalse(world.Rules.CanMove(enemy.combatant.Stats));
                world.Run(0.5);
                Assert.IsTrue(world.Combat.ApplyEffect(enemy.combatant, "effect.stun", 1.0, "hero"), "a 2a Escudada renova");
                world.Run(duration - 0.1);
                Assert.IsFalse(world.Rules.CanAct(enemy.combatant.Stats), "ainda atordoado: terminou 0,8 s depois da 2a");
                world.Run(0.3);
                Assert.IsTrue(world.Rules.CanAct(enemy.combatant.Stats), "terminou");
            }
        }

        [Test]
        public void STN02_StunInterruptsTheWindupAndTheHitNeverLands()
        {
            using (var world = new TestWorld(null, TestWorld.LoadNativeRules()))
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var enemy = world.AddEnemy(Sentinel, new PlanarVector(0f, 1.2f));
                var telegraphs = new List<TelegraphEvent>();
                world.Events.Subscribe<TelegraphEvent>((in TelegraphEvent e) => telegraphs.Add(e));
                for (var i = 0; i < 600 && telegraphs.Count == 0; i++) world.Combat.Step(world.Step);
                Assert.AreEqual(1, telegraphs.Count, "o inimigo telegrafou");
                Assert.IsTrue(telegraphs[0].Started);

                world.Combat.ApplyEffect(enemy.combatant, "effect.stun", 1.0, "hero");
                Assert.IsTrue(enemy.combatant.Effects.LastApply.Interrupted, "o core manda interromper");
                Assert.IsTrue(telegraphs.Exists(t => !t.Started), "o aviso foi cancelado");
                var life = hero.combatant.Life;
                world.Run(telegraphs[0].DurationSeconds + 0.1);
                Assert.AreEqual(life, hero.combatant.Life, Tol, "o golpe nao saiu");
            }
        }

        [Test]
        public void STN03_ImmuneTargetsReceiveNoStun()
        {
            using (var world = new TestWorld(null, TestWorld.LoadNativeRules()))
            {
                foreach (var id in new[] { Shielded, Herald })
                {
                    var enemy = world.AddEnemy(id, new PlanarVector(50f, 50f));
                    Assert.IsFalse(world.Combat.ApplyEffect(enemy.combatant, "effect.stun", 1.0, "hero"), id);
                    Assert.IsTrue(enemy.combatant.Effects.LastApply.StunBlocked, id);
                    Assert.IsTrue(world.Rules.CanAct(enemy.combatant.Stats), id);
                }
                var rolled = world.Rules.GetEliteProfile("modifier.elite.swift", true);
                var elite = world.AddEnemy(Sentinel, new PlanarVector(60f, 50f), elite: rolled);
                Assert.IsFalse(world.Combat.ApplyEffect(elite.combatant, "effect.stun", 1.0, "hero"), "elite sorteado");
            }
        }

        [Test]
        public void STN05_CommonTargetGetsTheStacksWithoutStagger()
        {
            using (var world = new TestWorld(null, TestWorld.LoadNativeRules()))
            {
                var enemy = world.AddEnemy(Sentinel, new PlanarVector(50f, 50f));
                for (var i = 0; i < 3; i++) world.Combat.ApplyEffect(enemy.combatant, "effect.guard_break", 1.0, "hero");
                Assert.AreEqual(3, enemy.combatant.Effects.StackCount("effect.guard_break"));
                Assert.IsFalse(enemy.combatant.Effects.LastApply.Staggered);
                Assert.IsTrue(world.Rules.CanAct(enemy.combatant.Stats));
            }
        }

        [Test]
        public void GQ01_02_ThreeStacksStaggerTheEliteAndRemoveItsBarrier()
        {
            using (var world = new TestWorld(null, TestWorld.LoadNativeRules()))
            {
                var shield = world.Rules.GetEliteProfile("modifier.elite.shield", true);
                var elite = world.AddEnemy(Sentinel, new PlanarVector(50f, 50f), elite: shield);
                Assert.Greater(elite.combatant.Barrier, 0.0, "elite com Escudo nasce com barreira");
                for (var i = 0; i < 3; i++) world.Combat.ApplyEffect(elite.combatant, "effect.guard_break", 1.0, "hero");
                var last = elite.combatant.Effects.LastApply;
                Assert.IsTrue(last.Staggered, "3 acumulos em alvo imune: stagger");
                Assert.AreEqual(0, elite.combatant.Effects.StackCount("effect.guard_break"), "os acumulos foram consumidos");
                Assert.AreEqual(0.0, elite.combatant.Barrier, "a quebra remove a barreira inteira");
                Assert.IsFalse(world.Rules.CanAct(elite.combatant.Stats), "atordoado pelo stagger");
            }
        }

        // ---------------------------------------------------------------------------------------
        // 8.5 Escudo frontal e 8.6 fases do Guardião (chefe do core)
        // ---------------------------------------------------------------------------------------

        static (TestWorld world, (Combatant combatant, HeroCombatLogic logic) hero, (Combatant combatant, EnemyCombatLogic logic) boss) BossWorld()
        {
            var world = new TestWorld(null, TestWorld.LoadNativeRules());
            var hero = world.AddHero(PlanarVector.Zero);
            var boss = world.AddEnemy(Guardian, new PlanarVector(0f, 14f), 5, 1.5f);
            world.Run(4.0); // o core gira o chefe para o jogador (turnRate da fase)
            Assert.IsNotNull(boss.logic.Boss, "o chefe nativo foi criado");
            return (world, hero, boss);
        }

        [Test]
        public void ESC01_02_ShieldBlocksHitsFromTheFrontAndNotFromBehind()
        {
            var (world, hero, boss) = BossWorld();
            using (world)
            {
                var skill = world.Rules.FindSkill("skill.warrior.iron_cut");
                var blocked = new List<ShieldBlockedEvent>();
                world.Events.Subscribe<ShieldBlockedEvent>((in ShieldBlockedEvent e) => blocked.Add(e));
                var life = boss.combatant.Life;
                var resource = hero.combatant.Resource;

                // Origem do golpe no lado em que o chefe olha (ele gira para o jogador).
                Assert.IsFalse(world.Combat.ApplySkillHit(hero.combatant, boss.combatant, skill, hero.combatant.Position), "de frente: escudo");
                Assert.AreEqual(1, blocked.Count);
                Assert.AreEqual(life, boss.combatant.Life, Tol, "0 de vida");
                Assert.AreEqual(resource, hero.combatant.Resource, Tol, "sem Impeto");

                var behind = boss.combatant.Position + (boss.combatant.Position - hero.combatant.Position).NormalizedOr(PlanarVector.Forward) * 3f;
                Assert.IsTrue(world.Combat.ApplySkillHit(hero.combatant, boss.combatant, skill, behind), "por tras: dano normal");
                Assert.Less(boss.combatant.Life, life);
                Assert.AreEqual(1, blocked.Count);
            }
        }

        [Test]
        public void ESC05_TurnIsLockedFromWindupToTheEndOfTheImpact()
        {
            var (world, hero, boss) = BossWorld();
            using (world)
            {
                var telegraph = new List<TelegraphEvent>();
                world.Events.Subscribe<TelegraphEvent>((in TelegraphEvent e) => { if (ReferenceEquals(e.Owner, boss.combatant)) telegraph.Add(e); });
                for (var i = 0; i < 3000 && telegraph.Count == 0; i++) world.Combat.Step(world.Step);
                Assert.IsNotEmpty(telegraph, "o chefe telegrafou um padrao");
                var locked = boss.combatant.Forward;
                // O jogador circula durante a preparacao: a direcao do chefe nao muda ate o fim do impacto.
                for (var i = 0; i < 20 && telegraph.Count == 1; i++)
                {
                    hero.combatant.Position = new PlanarVector((float)System.Math.Sin(i * 0.3) * 8f, 14f + (float)System.Math.Cos(i * 0.3) * 8f);
                    world.Combat.Step(world.Step);
                    Assert.AreEqual(locked.X, boss.combatant.Forward.X, 1e-4f, "giro travado (passo " + i + ")");
                    Assert.AreEqual(locked.Z, boss.combatant.Forward.Z, 1e-4f, "giro travado (passo " + i + ")");
                }
            }
        }

        [Test]
        public void GQ03_GuardBreakDropsTheBossShieldAndItComesBack()
        {
            var (world, hero, boss) = BossWorld();
            using (world)
            {
                var events = new List<BossStateEvent>();
                world.Events.Subscribe<BossStateEvent>((in BossStateEvent e) => events.Add(e));
                Assert.IsTrue(boss.logic.Boss.Info.ShieldUp);
                for (var i = 0; i < 3; i++) world.Combat.ApplyEffect(boss.combatant, "effect.guard_break", 1.0, "hero");
                world.Run(world.Step * 2);
                var down = events.Find(e => e.Kind == BossEventKind.ShieldDown);
                Assert.AreEqual(BossEventKind.ShieldDown, down.Kind, "o escudo caiu");
                Assert.IsFalse(boss.logic.Boss.Info.ShieldUp);
                world.Run(down.Seconds + 0.5);
                Assert.IsTrue(boss.logic.Boss.Info.ShieldUp, "o escudo voltou");
                Assert.IsTrue(events.Exists(e => e.Kind == BossEventKind.ShieldUp));
            }
        }

        [Test]
        public void GRD01_Phase2StartsAtFiftyPercentAndSummonsOnce()
        {
            var (world, hero, boss) = BossWorld();
            using (world)
            {
                var events = new List<BossStateEvent>();
                world.Events.Subscribe<BossStateEvent>((in BossStateEvent e) => events.Add(e));
                var info = boss.logic.Boss.Info;
                Assert.AreEqual(1, info.Phase);
                var behindX = info.FacingX * -4.0;
                var behindZ = info.FacingZ * -4.0;
                var bx = boss.combatant.Position.X;
                var bz = boss.combatant.Position.Z;
                var toHalf = info.Life - info.MaxLife * 0.5;
                boss.logic.Boss.ApplyDamage(toHalf - 1.0, bx, bz, bx + behindX, bz + behindZ);
                world.Run(world.Step * 2);
                Assert.AreEqual(1, boss.logic.Boss.Info.Phase, "um pouco acima de 50%: ainda fase 1");
                boss.logic.Boss.ApplyDamage(1.0, bx, bz, bx + behindX, bz + behindZ);
                world.Run(5.0); // a fase 2 comeca quando o chefe termina o golpe em curso (sem interromper)
                Assert.AreEqual(2, boss.logic.Boss.Info.Phase, "em 50%: fase 2");
                Assert.AreEqual(1, events.FindAll(e => e.Kind == BossEventKind.PhaseStart && e.Phase == 2).Count);
                Assert.AreEqual(1, events.FindAll(e => e.Kind == BossEventKind.SummonSpawn).Count, "a invocacao acontece uma vez");
            }
        }

        // ---------------------------------------------------------------------------------------
        // Elite sorteado pelo fluxo de eventos
        // ---------------------------------------------------------------------------------------

        [Test]
        public void EliteRollIsDeterministicAndUsesTheEventsStream()
        {
            using (var rules = TestWorld.LoadNativeRules())
            {
                var a = rules.CreateRng(42, RngStream.Events, CombatSystem.EliteStreamIndex);
                var b = rules.CreateRng(42, RngStream.Events, CombatSystem.EliteStreamIndex);
                var start = a.State;
                var first = rules.RollElite(ref a);
                var second = rules.RollElite(ref b);
                Assert.AreEqual(first.ModifierId, second.ModifierId, "mesma seed, mesmo modificador");
                Assert.AreNotEqual(start, a.State, "consome numero do fluxo");
                Assert.AreEqual(a.State, b.State);
                Assert.IsTrue(first.Rolled);

                using (var stats = rules.CreateEnemyStats(Sentinel, 3))
                {
                    var life = stats.Get(StatId.Life);
                    rules.ApplyElite(stats, in first);
                    Assert.AreEqual(life * first.LifeMult, stats.Get(StatId.Life), 1e-6);
                }
            }
        }

        // ---------------------------------------------------------------------------------------
        // Rodada 2 (docs/09 secao 8): dano desarmado pelo core e batida da Investida do Guardiao
        // ---------------------------------------------------------------------------------------

        [Test]
        public void UnarmedDamageComesFromTheCore()
        {
            using (var rules = TestWorld.LoadNativeRules())
            {
                var skill = rules.FindSkill("skill.warrior.iron_cut");
                var unarmed = rules.GetSkillBaseDamage(skill, null);
                Assert.Greater(rules.Combat.UnarmedWeaponDamagePhysical, 0.0, "unarmed_weapon_damage_physical do rules.csv");
                Assert.AreEqual(rules.Combat.UnarmedWeaponDamagePhysical, unarmed.Physical, Tol, "sem arma: o desarmado, so fisico");
                Assert.AreEqual(0.0, unarmed.Fire + unarmed.Cold + unarmed.Lightning, Tol);
                var armed = rules.GetSkillBaseDamage(skill, rules.FindItemBase("item_base.iron_sword"));
                Assert.Greater(armed.Physical, unarmed.Physical, "com a espada o dano e o da arma");
            }
        }

        [Test]
        public void ChargeHittingAPillarStaggersTheBossAndDropsItsShield()
        {
            using (var world = new TestWorld(null, TestWorld.LoadNativeRules()))
            {
                var hero = world.AddHero(new PlanarVector(0f, 0f));
                var boss = world.AddEnemy(Guardian, new PlanarVector(0f, 16f), 5, 1f);
                boss.logic.IsDashBlocked = (from, to, radius) => true; // um pilar em toda a trajetoria
                var events = new List<BossStateEvent>();
                world.Events.Subscribe<BossStateEvent>((in BossStateEvent e) => events.Add(e));
                world.Run(1.0);
                // Fase 2: so ela tem a Investida do Escudo.
                var info = boss.logic.Boss.Info;
                var bx = boss.combatant.Position.X;
                var bz = boss.combatant.Position.Z;
                boss.logic.Boss.ApplyDamage(info.Life - info.MaxLife * 0.5, bx, bz, bx - info.FacingX * 4.0, bz - info.FacingZ * 4.0);
                var staggered = false;
                for (var i = 0; i < 60 * 90 && !staggered; i++)
                {
                    world.Combat.Step(world.Step);
                    staggered = events.Exists(e => e.Kind == BossEventKind.ShieldDown) && events.Exists(e => e.Kind == BossEventKind.StaggerStart);
                }
                Assert.IsTrue(staggered, "a batida da Investida num pilar derruba o escudo e atordoa o chefe (shatter_boss_wall_hit)");
                Assert.IsTrue(world.Hits.Count == 0 || world.Hits.TrueForAll(h => !ReferenceEquals(h.Target, hero.combatant)), "o heroi longe nao foi atingido");
            }
        }
    }
}
