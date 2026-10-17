using System;
using System.Collections.Generic;
using Echoes.Gameplay;
using Echoes.Interop;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    /// <summary>
    /// Máquina de entrada do ataque básico (docs/18, seções 1.3 e 1.4): clique ou segurar, crédito de preparação, janela do combo, fila de clique,
    /// carga com soltura automática, defesa e cancelamentos. Os valores abaixo são FALSOS e existem só nestes testes: a máquina lê tudo de
    /// <see cref="IBasicKit"/> e os números reais vêm do core (basic_kits.csv e rules.csv). Tudo em ticks de 1/60 s.
    /// </summary>
    [Category("Gameplay")]
    public sealed class BasicKitMachineTests
    {
        /// <summary>Valores de teste (NÃO são dados de jogo). Os três golpes leves e o forte são habilidades reais só para ter fases e custo.</summary>
        sealed class FakeKit : IBasicKit
        {
            public double ComboWindow { get; set; } = 0.4;
            public double ComboWindowAfterDodge { get; set; } = 0.3;
            public double AttackBuffer { get; set; } = 0.15;
            public double HeavyHoldThreshold { get; set; } = 0.35;
            public double LightWindupCreditMax { get; set; } = 0.7;
            public double GuardLowerTime { get; set; } = 0.1;
            public IReadOnlyList<SkillInfo> LightChain { get; set; }
            public SkillInfo HeavySkill { get; set; }
            public double HeavyChargeTime { get; set; } = 0.9;
            public double HeavyMaxMult { get; set; } = 2.0;
            public string ChargeEffect { get; set; } = string.Empty;
            public string GuardEffect { get; set; } = string.Empty;
            public double GuardArcDegrees { get; set; } = 120.0;
            public double GuardMaxHold { get; set; }
            public double GuardCooldown { get; set; } = 0.25;
            public double GuardPerfectWindow { get; set; } = 0.2;
            public double GuardPerfectCooldown { get; set; } = 0.8;
        }

        sealed class Rig : IDisposable
        {
            public readonly TestWorld World = new TestWorld();
            public readonly FakeKit Kit = new FakeKit();
            public Combatant Hero;
            public HeroCombatLogic Logic;
            public readonly List<BasicInputEvent> Basic = new List<BasicInputEvent>();
            public readonly List<SkillPhaseEvent> Phases = new List<SkillPhaseEvent>();

            public Rig(Action<FakeKit> tweak = null, string heavy = "skill.warrior.iron_cut")
            {
                var rules = World.Rules;
                Kit.LightChain = new[] { rules.FindSkill("skill.warrior.iron_cut"), rules.FindSkill("skill.warrior.shield_bash"), rules.FindSkill("skill.warrior.stone_rift") };
                Kit.HeavySkill = rules.FindSkill(heavy);
                tweak?.Invoke(Kit);
                var hero = World.AddHero(PlanarVector.Zero, 5, null, Kit);
                Hero = hero.combatant;
                Logic = hero.logic;
                World.Combat.GainResource(Hero, 100.0);
                World.Events.Subscribe<BasicInputEvent>(OnBasic);
                World.Events.Subscribe<SkillPhaseEvent>(OnPhase);
            }

            void OnBasic(in BasicInputEvent evt) => Basic.Add(evt);
            void OnPhase(in SkillPhaseEvent evt) => Phases.Add(evt);

            public void Ticks(int count)
            {
                for (var i = 0; i < count; i++) World.Combat.Step(World.Step);
            }

            public void Seconds(double seconds) => Ticks((int)Math.Round(seconds / World.Step));

            /// <summary>Roda até a condição (no máximo 600 ticks) e devolve quantos rodou.</summary>
            public int Until(Func<bool> condition)
            {
                for (var i = 0; i < 600; i++)
                {
                    if (condition()) return i;
                    World.Combat.Step(World.Step);
                }
                Assert.Fail("A condição nunca aconteceu em 600 ticks.");
                return -1;
            }

            public void Click(int heldTicks = 1)
            {
                Logic.ButtonDown(HeroCommand.BasicAttack);
                Ticks(heldTicks);
                Logic.ButtonUp(HeroCommand.BasicAttack);
            }

            public int Count(BasicInputKind kind)
            {
                var n = 0;
                foreach (var e in Basic)
                {
                    if (e.Kind == kind) n++;
                }
                return n;
            }

            public string Skill => Logic.CurrentSkill != null ? Logic.CurrentSkill.Id : null;

            public double Remaining => Logic.Action.Timing.Recovery - Logic.Action.PhaseElapsed;

            public void Dispose() => World.Dispose();
        }

        const string Cut = "skill.warrior.iron_cut";
        const string Bash = "skill.warrior.shield_bash";
        const string Rift = "skill.warrior.stone_rift";

        // ---------------------------------------------------------------------------------------------------------- clique e segurar

        [Test]
        public void ClickStartsTheFirstLightAndTheHeldTimeDiscountsTheWindup()
        {
            using (var rig = new Rig())
            {
                rig.Logic.ButtonDown(HeroCommand.BasicAttack);
                rig.Ticks(3);
                Assert.IsFalse(rig.Logic.IsCasting, "decide ao soltar: ainda nada");
                rig.Logic.ButtonUp(HeroCommand.BasicAttack);
                rig.Ticks(1);
                Assert.IsTrue(rig.Logic.IsCasting);
                Assert.AreEqual(Cut, rig.Skill);
                var windup = rig.Logic.Action.Timing.Windup;
                Assert.AreEqual(windup - 3 * rig.World.Step, rig.Phases[0].PhaseSeconds, 1e-9, "3 ticks apertados descontam da preparação");
            }
        }

        [Test]
        public void WindupCreditIsCappedAtTheConfiguredFraction()
        {
            using (var rig = new Rig())
            {
                rig.Click(20); // 0,333 s: ainda é clique (< 0,35 s)
                rig.Ticks(1);
                Assert.AreEqual(Cut, rig.Skill);
                var windup = rig.Logic.Action.Timing.Windup;
                Assert.AreEqual(windup * (1.0 - rig.Kit.LightWindupCreditMax), rig.Phases[0].PhaseSeconds, 1e-9);
            }
        }

        [Test]
        public void HoldingPastTheThresholdStartsTheCharge()
        {
            using (var rig = new Rig())
            {
                rig.Logic.ButtonDown(HeroCommand.BasicAttack);
                rig.Ticks(20);
                Assert.IsFalse(rig.Logic.IsCharging, "0,333 s ainda é clique");
                rig.Ticks(1);
                Assert.IsTrue(rig.Logic.IsCharging, "0,35 s = 21 ticks");
                Assert.AreEqual(1, rig.Count(BasicInputKind.ChargeStarted));
                Assert.IsFalse(rig.Logic.IsCasting, "carregar não é a preparação do golpe");
            }
        }

        [Test]
        public void ReleasingTheChargeThrowsTheHeavyWithAMultiplierThatGrowsWithTheCharge()
        {
            using (var rig = new Rig())
            {
                rig.Logic.ButtonDown(HeroCommand.BasicAttack);
                rig.Ticks(21);
                rig.Logic.ButtonUp(HeroCommand.BasicAttack);
                rig.Ticks(1);
                Assert.IsTrue(rig.Logic.IsCasting, "soltar na carga mínima já lança o forte");
                Assert.AreEqual(1.0, rig.Basic.Find(e => e.Kind == BasicInputKind.HeavyReleased).Value, 1e-9);
            }
            using (var rig = new Rig())
            {
                rig.Logic.ButtonDown(HeroCommand.BasicAttack);
                rig.Ticks(21 + 27); // metade da carga (0,9 s = 54 ticks)
                rig.Logic.ButtonUp(HeroCommand.BasicAttack);
                rig.Ticks(1);
                Assert.AreEqual(1.5, rig.Basic.Find(e => e.Kind == BasicInputKind.HeavyReleased).Value, 1e-9, "1 + (2 - 1) * 0,5");
            }
        }

        [Test]
        public void ChargeReleasesByItselfAtTheMaximumAndHoldingMoreAddsNothing()
        {
            using (var rig = new Rig())
            {
                rig.Logic.ButtonDown(HeroCommand.BasicAttack);
                rig.Ticks(21 + 54 + 2);
                Assert.AreEqual(1, rig.Count(BasicInputKind.ChargeFull));
                Assert.AreEqual(1, rig.Count(BasicInputKind.HeavyReleased));
                Assert.AreEqual(2.0, rig.Basic.Find(e => e.Kind == BasicInputKind.HeavyReleased).Value, 1e-9);
                rig.Until(() => !rig.Logic.IsCasting);
                rig.Ticks(60);
                Assert.IsFalse(rig.Logic.IsCharging, "o botão ainda está apertado e não recarrega sozinho");
                Assert.AreEqual(1, rig.Count(BasicInputKind.HeavyReleased));
                rig.Logic.ButtonUp(HeroCommand.BasicAttack);
                rig.Ticks(5);
                Assert.IsFalse(rig.Logic.IsCasting, "soltar depois do disparo automático não dispara nada");
            }
        }

        [Test]
        public void HeavyWithoutResourceBecomesALightInsteadOfAnEmptyCharge()
        {
            using (var rig = new Rig(null, Rift)) // stone_rift custa recurso; o herói começa sem (zera abaixo)
            {
                // gasta o recurso que o Rig deu
                rig.World.Combat.TrySpendResource(rig.Hero, 100.0);
                rig.Logic.ButtonDown(HeroCommand.BasicAttack);
                rig.Ticks(22);
                Assert.IsFalse(rig.Logic.IsCharging, "sem recurso no limiar, nada de carga vazia");
                Assert.IsTrue(rig.Logic.IsCasting);
                Assert.AreEqual(Cut, rig.Skill, "vira o golpe leve");
                Assert.AreEqual(0, rig.Count(BasicInputKind.ChargeStarted));
            }
        }

        [Test]
        public void HeavyCostIsPaidOnReleaseNotOnCharge()
        {
            using (var rig = new Rig(null, Rift))
            {
                var before = rig.Hero.Resource;
                rig.Logic.ButtonDown(HeroCommand.BasicAttack);
                rig.Ticks(40);
                Assert.IsTrue(rig.Logic.IsCharging);
                var cost = rig.Hero.Resource;
                Assert.Greater(cost, before - 10.0, "carregando não gasta (só o decaimento do Ímpeto fora de combate)");
                rig.Logic.ButtonUp(HeroCommand.BasicAttack);
                rig.Ticks(1);
                Assert.Less(rig.Hero.Resource, cost - 30.0, "soltar cobra o custo do golpe forte (40)");
            }
        }

        [Test]
        public void HeavyMultiplierScalesTheDamageOfTheHit()
        {
            double Damage(double multiplier)
            {
                using (var world = new TestWorld())
                {
                    var hero = world.AddHero(PlanarVector.Zero);
                    var enemy = world.AddEnemy("enemy.hollow_sentinel", new PlanarVector(0f, 1f));
                    var skill = world.Rules.FindSkill(Cut);
                    world.Combat.ApplySkillHit(hero.combatant, enemy.combatant, skill, hero.combatant.Position, multiplier);
                    return world.Hits[0].Result.TotalDamage;
                }
            }
            var one = Damage(1.0);
            var two = Damage(2.0);
            Assert.Greater(one, 0.0);
            Assert.Greater(two, one * 1.5, "o multiplicador entra no coeficiente do golpe");
        }

        // ---------------------------------------------------------------------------------------------------------- combo

        [Test]
        public void ComboAdvancesInsideTheWindowAndResetsAfterIt()
        {
            using (var rig = new Rig())
            {
                rig.Click();
                rig.Ticks(1);
                Assert.AreEqual(Cut, rig.Skill);
                rig.Until(() => !rig.Logic.IsCasting);
                Assert.AreEqual(1, rig.Logic.ComboIndex);
                rig.Seconds(0.2); // dentro da janela (0,4 s)
                rig.Click();
                rig.Ticks(1);
                Assert.AreEqual(Bash, rig.Skill, "2º golpe do combo");
                rig.Until(() => !rig.Logic.IsCasting);
                rig.Seconds(0.1);
                rig.Click();
                rig.Ticks(1);
                Assert.AreEqual(Rift, rig.Skill, "3º golpe do combo");
                rig.Until(() => !rig.Logic.IsCasting);
                Assert.AreEqual(0, rig.Logic.ComboIndex, "depois do 3º o índice volta a 0");
            }
            using (var rig = new Rig())
            {
                rig.Click();
                rig.Ticks(1);
                rig.Until(() => !rig.Logic.IsCasting);
                rig.Seconds(0.5); // perdeu a janela
                Assert.AreEqual(0, rig.Logic.ComboIndex);
                Assert.AreEqual(1, rig.Count(BasicInputKind.ComboReset));
                rig.Click();
                rig.Ticks(1);
                Assert.AreEqual(Cut, rig.Skill, "volta ao 1º golpe");
            }
        }

        [Test]
        public void ClickDuringWindupAndImpactIsIgnored()
        {
            using (var rig = new Rig())
            {
                rig.Click();
                rig.Ticks(2);
                Assert.AreEqual(ActionPhase.Windup, rig.Logic.Action.Phase);
                rig.Click(); // compromisso do golpe
                rig.Until(() => rig.Logic.Action.Phase == ActionPhase.Recovery);
                rig.Until(() => !rig.Logic.IsCasting);
                rig.Ticks(5);
                Assert.IsFalse(rig.Logic.IsCasting, "o clique da preparação não ficou na fila");
                Assert.AreEqual(1, rig.Logic.ComboIndex);
            }
        }

        [Test]
        public void ClickEarlyInTheRecoveryIsIgnoredButTheLastBufferQueuesTheNextStrike()
        {
            using (var rig = new Rig())
            {
                rig.Click();
                rig.Ticks(1);
                rig.Until(() => rig.Logic.Action.Phase == ActionPhase.Recovery);
                rig.Ticks(1);
                Assert.Greater(rig.Remaining, rig.Kit.AttackBuffer, "ainda cedo na recuperação");
                rig.Click();
                rig.Until(() => !rig.Logic.IsCasting);
                rig.Ticks(1);
                Assert.IsFalse(rig.Logic.IsCasting, "clique cedo demais é ignorado (evita golpe acidental ao martelar)");
            }
            using (var rig = new Rig())
            {
                rig.Click();
                rig.Ticks(1);
                rig.Until(() => rig.Logic.Action.Phase == ActionPhase.Recovery && rig.Remaining <= 0.1);
                rig.Click();
                Assert.AreEqual(Cut, rig.Skill, "o 1º golpe ainda está na recuperação");
                rig.Until(() => rig.Skill != Cut);
                Assert.AreEqual(Bash, rig.Skill, "o 2º golpe começa no fim da recuperação, sem folga");
                Assert.IsTrue(rig.Logic.IsCasting);
            }
        }

        [Test]
        public void DodgeKeepsTheComboIndexAndReopensTheWindowAtTheEndOfTheDodge()
        {
            using (var rig = new Rig())
            {
                rig.Click();
                rig.Ticks(1);
                rig.Until(() => rig.Logic.Action.Phase == ActionPhase.Recovery && rig.Logic.Action.RecoveryFraction >= 0.5);
                rig.Logic.Press(HeroCommand.Dodge);
                rig.Ticks(2);
                Assert.IsTrue(rig.Logic.Dodge.IsDodging, "a esquiva cancela a metade final da recuperação");
                Assert.AreEqual(1, rig.Logic.ComboIndex, "o combo guarda o índice");
                rig.Until(() => !rig.Logic.Dodge.IsDodging);
                rig.Seconds(0.2); // dentro dos 0,3 s depois da esquiva
                rig.Click();
                rig.Ticks(1);
                Assert.AreEqual(Bash, rig.Skill, "esquivar e voltar ao combo");
            }
            using (var rig = new Rig())
            {
                rig.Click();
                rig.Ticks(1);
                rig.Until(() => rig.Logic.Action.Phase == ActionPhase.Recovery && rig.Logic.Action.RecoveryFraction >= 0.5);
                rig.Logic.Press(HeroCommand.Dodge);
                rig.Until(() => rig.Logic.Dodge.IsDodging);
                rig.Until(() => !rig.Logic.Dodge.IsDodging);
                rig.Seconds(0.4); // passou de 0,3 s
                rig.Click();
                rig.Ticks(1);
                Assert.AreEqual(Cut, rig.Skill, "janela perdida: volta ao 1º golpe");
            }
        }

        [Test]
        public void SkillInTheSecondHalfOfTheRecoveryCancelsItAndResetsTheCombo()
        {
            using (var rig = new Rig())
            {
                rig.Click();
                rig.Ticks(1);
                rig.Until(() => rig.Logic.Action.Phase == ActionPhase.Recovery && rig.Logic.Action.RecoveryFraction < 0.5);
                rig.Logic.Press(HeroCommand.Skill2); // Fenda de Pedra (Q)
                rig.Ticks(1);
                Assert.AreEqual(Cut, rig.Skill, "na 1ª metade a recuperação não cancela");
            }
            using (var rig = new Rig())
            {
                rig.Click();
                rig.Ticks(1);
                rig.Until(() => rig.Logic.Action.Phase == ActionPhase.Recovery && rig.Logic.Action.RecoveryFraction >= 0.5);
                rig.Logic.Press(HeroCommand.Skill2);
                rig.Ticks(1);
                Assert.AreEqual(Rift, rig.Skill, "na metade final cancela a recuperação");
                Assert.AreEqual(0, rig.Logic.ComboIndex, "e o combo zera");
                Assert.AreEqual(1, rig.Count(BasicInputKind.ComboReset));
            }
        }

        // ---------------------------------------------------------------------------------------------------------- carga

        [Test]
        public void DodgeCancelsTheChargeForFree()
        {
            using (var rig = new Rig())
            {
                rig.Logic.ButtonDown(HeroCommand.BasicAttack);
                rig.Ticks(30);
                Assert.IsTrue(rig.Logic.IsCharging);
                var resource = rig.Hero.Resource;
                rig.Logic.Press(HeroCommand.Dodge);
                rig.Ticks(2);
                Assert.IsFalse(rig.Logic.IsCharging);
                Assert.IsTrue(rig.Logic.Dodge.IsDodging);
                Assert.AreEqual(1, rig.Count(BasicInputKind.ChargeCancelled));
                Assert.AreEqual(0, rig.Count(BasicInputKind.HeavyReleased));
                rig.Logic.ButtonUp(HeroCommand.BasicAttack);
                rig.Until(() => !rig.Logic.Dodge.IsDodging);
                rig.Ticks(5);
                Assert.IsFalse(rig.Logic.IsCasting, "soltar depois do cancelamento não lança o forte");
                Assert.Greater(rig.Hero.Resource, resource - 10.0, "cancelar a carga não cobra nada (só o decaimento do Ímpeto)");
            }
        }

        [Test]
        public void GuardAndSkillAlsoCancelTheCharge()
        {
            using (var rig = new Rig())
            {
                rig.Logic.ButtonDown(HeroCommand.BasicAttack);
                rig.Ticks(30);
                rig.Logic.ButtonDown(HeroCommand.Skill1); // botão direito
                rig.Ticks(2);
                Assert.IsFalse(rig.Logic.IsCharging);
                Assert.IsTrue(rig.Logic.IsGuarding);
                Assert.AreEqual(1, rig.Count(BasicInputKind.ChargeCancelled));
            }
            using (var rig = new Rig())
            {
                rig.Logic.ButtonDown(HeroCommand.BasicAttack);
                rig.Ticks(30);
                rig.Logic.Press(HeroCommand.Skill2);
                rig.Ticks(2);
                Assert.IsFalse(rig.Logic.IsCharging);
                Assert.AreEqual(Rift, rig.Skill);
                Assert.AreEqual(1, rig.Count(BasicInputKind.ChargeCancelled));
            }
        }

        // ---------------------------------------------------------------------------------------------------------- defesa

        [Test]
        public void GuardGoesUpWhileTheRightButtonIsHeldAndTheHeroDoesNotAttack()
        {
            using (var rig = new Rig())
            {
                rig.Logic.ButtonDown(HeroCommand.Skill1);
                rig.Ticks(2);
                Assert.IsTrue(rig.Logic.IsGuarding);
                Assert.IsTrue(rig.Logic.IsAiming);
                rig.Click();
                rig.Logic.Press(HeroCommand.Skill2);
                rig.Ticks(20);
                Assert.IsFalse(rig.Logic.IsCasting, "enquanto defende, clique e Q/E/R são ignorados");
                rig.Logic.ButtonUp(HeroCommand.Skill1);
                rig.Ticks(2);
                Assert.IsFalse(rig.Logic.IsGuarding);
                rig.Ticks(10);
                Assert.IsFalse(rig.Logic.IsCasting, "o clique de antes não ficou guardado");
                Assert.AreEqual(1, rig.Count(BasicInputKind.GuardUp));
                Assert.AreEqual(1, rig.Count(BasicInputKind.GuardDown));
            }
        }

        [Test]
        public void StrikeAfterLoweringTheGuardWaitsForTheLowerTime()
        {
            using (var rig = new Rig())
            {
                rig.Logic.ButtonDown(HeroCommand.Skill1);
                rig.Ticks(4);
                rig.Logic.ButtonUp(HeroCommand.Skill1);
                rig.Ticks(1);
                rig.Click(); // logo depois de baixar: espera guard_lower_time (0,1 s = 6 ticks)
                var waited = rig.Until(() => rig.Logic.IsCasting);
                Assert.GreaterOrEqual(waited, 4, "não ataca de imediato");
                Assert.LessOrEqual(waited, 8);
            }
        }

        [Test]
        public void GuardFallsAloneAtTheMaximumAndNeedsANewPressAfterTheCooldown()
        {
            using (var rig = new Rig(k =>
            {
                k.GuardMaxHold = 0.2;
                k.GuardCooldown = 1.0;
            }))
            {
                rig.Logic.ButtonDown(HeroCommand.Skill1);
                rig.Ticks(2);
                Assert.IsTrue(rig.Logic.IsGuarding);
                rig.Ticks(14);
                Assert.IsFalse(rig.Logic.IsGuarding, "0,2 s = 12 ticks");
                Assert.AreEqual(1, rig.Count(BasicInputKind.GuardBroke));
                rig.Seconds(1.2);
                Assert.IsFalse(rig.Logic.IsGuarding, "continua apertado, mas precisa apertar de novo");
                rig.Logic.ButtonUp(HeroCommand.Skill1);
                rig.Ticks(1);
                rig.Logic.ButtonDown(HeroCommand.Skill1);
                rig.Ticks(2);
                Assert.IsTrue(rig.Logic.IsGuarding);
            }
            using (var rig = new Rig(k =>
            {
                k.GuardMaxHold = 0.2;
                k.GuardCooldown = 1.0;
            }))
            {
                rig.Logic.ButtonDown(HeroCommand.Skill1);
                rig.Ticks(20);
                rig.Logic.ButtonUp(HeroCommand.Skill1);
                rig.Ticks(1);
                rig.Logic.ButtonDown(HeroCommand.Skill1);
                rig.Ticks(10);
                Assert.IsFalse(rig.Logic.IsGuarding, "em espera de 1,0 s depois de cair");
            }
        }

        [Test]
        public void PerfectGuardOpensOnlyRightAfterThePressAndHonorsTheCooldown()
        {
            using (var rig = new Rig())
            {
                rig.Logic.ButtonDown(HeroCommand.Skill1);
                rig.Ticks(2);
                Assert.IsTrue(rig.Logic.GuardPerfectOpen, "primeiros 0,2 s");
                rig.Ticks(15);
                Assert.IsFalse(rig.Logic.GuardPerfectOpen, "segurar desde antes não vale");
                rig.Logic.ButtonUp(HeroCommand.Skill1);
                rig.Ticks(20); // 0,33 s desde o último aperto
                rig.Logic.ButtonDown(HeroCommand.Skill1);
                rig.Ticks(2);
                Assert.IsTrue(rig.Logic.IsGuarding);
                Assert.IsFalse(rig.Logic.GuardPerfectOpen, "re-liberada só 0,8 s depois do último aperto");
                rig.Logic.ButtonUp(HeroCommand.Skill1);
                rig.Seconds(1.0);
                rig.Logic.ButtonDown(HeroCommand.Skill1);
                rig.Ticks(2);
                Assert.IsTrue(rig.Logic.GuardPerfectOpen);
            }
        }

        [Test]
        public void GuardFromTheSecondHalfOfTheRecoveryCancelsAndResetsTheComboButWaitsInTheFirstHalf()
        {
            using (var rig = new Rig())
            {
                rig.Click();
                rig.Ticks(1);
                rig.Until(() => rig.Logic.Action.Phase == ActionPhase.Recovery && rig.Logic.Action.RecoveryFraction < 0.5);
                rig.Logic.ButtonDown(HeroCommand.Skill1);
                rig.Ticks(1);
                Assert.IsFalse(rig.Logic.IsGuarding, "1ª metade da recuperação: ainda não cancela");
                rig.Until(() => rig.Logic.IsGuarding);
                Assert.IsFalse(rig.Logic.IsCasting, "entrou na defesa cancelando o resto da recuperação");
                Assert.AreEqual(0, rig.Logic.ComboIndex, "o combo zera");
            }
        }

        [Test]
        public void DodgeDropsTheGuard()
        {
            using (var rig = new Rig())
            {
                rig.Logic.ButtonDown(HeroCommand.Skill1);
                rig.Ticks(3);
                rig.Logic.Press(HeroCommand.Dodge);
                rig.Ticks(2);
                Assert.IsFalse(rig.Logic.IsGuarding);
                Assert.IsTrue(rig.Logic.Dodge.IsDodging);
            }
        }

        [Test]
        public void GuardCoversOnlyTheFrontArc()
        {
            using (var rig = new Rig())
            {
                rig.Logic.AimPoint = new PlanarVector(0f, 5f); // mira +Z
                rig.Logic.ButtonDown(HeroCommand.Skill1);
                rig.Ticks(2);
                Assert.IsTrue(rig.Logic.GuardCovers(new PlanarVector(0f, 3f)), "de frente");
                Assert.IsTrue(rig.Logic.GuardCovers(new PlanarVector(2f, 2f)), "45°: dentro dos 60° de cada lado");
                Assert.IsFalse(rig.Logic.GuardCovers(new PlanarVector(3f, 0.5f)), "de lado");
                Assert.IsFalse(rig.Logic.GuardCovers(new PlanarVector(0f, -3f)), "pelas costas");
            }
            using (var rig = new Rig(k => k.GuardArcDegrees = 360.0))
            {
                rig.Logic.ButtonDown(HeroCommand.Skill1);
                rig.Ticks(2);
                Assert.IsTrue(rig.Logic.GuardCovers(new PlanarVector(0f, -3f)), "cúpula: 360°");
            }
            using (var rig = new Rig())
            {
                Assert.IsFalse(rig.Logic.GuardCovers(new PlanarVector(0f, 3f)), "sem defesa não cobre nada");
            }
        }

        // ---------------------------------------------------------------------------------------------------------- atordoamento e determinismo

        [Test]
        public void StunCancelsEverythingAndZeroesTheCombo()
        {
            using (var rig = new Rig())
            {
                rig.Click();
                rig.Ticks(1);
                rig.Until(() => !rig.Logic.IsCasting);
                Assert.AreEqual(1, rig.Logic.ComboIndex);
                rig.Logic.ButtonDown(HeroCommand.BasicAttack);
                rig.Ticks(30);
                Assert.IsTrue(rig.Logic.IsCharging);
                rig.World.Combat.ApplyEffect(rig.Hero, "effect.stun", 1.0, "test");
                rig.Ticks(2);
                Assert.IsFalse(rig.Logic.IsCharging);
                Assert.AreEqual(0, rig.Logic.ComboIndex);
                Assert.AreEqual(1, rig.Count(BasicInputKind.ChargeCancelled));
            }
        }

        [Test]
        public void SameInputsGiveTheSameEventSequence()
        {
            string Run()
            {
                using (var rig = new Rig())
                {
                    rig.Click(5);
                    rig.Seconds(0.5);
                    rig.Logic.ButtonDown(HeroCommand.BasicAttack);
                    rig.Seconds(1.0);
                    rig.Logic.ButtonUp(HeroCommand.BasicAttack);
                    rig.Logic.ButtonDown(HeroCommand.Skill1);
                    rig.Seconds(0.5);
                    var sb = new System.Text.StringBuilder();
                    foreach (var e in rig.Basic) sb.Append(e.Kind).Append(':').Append(e.Value.ToString("0.####")).Append(';');
                    foreach (var p in rig.Phases) sb.Append(p.Skill != null ? p.Skill.Id : "-").Append(p.Phase).Append(p.PhaseSeconds.ToString("0.####")).Append(';');
                    return sb.ToString();
                }
            }
            Assert.AreEqual(Run(), Run());
        }

        [Test]
        public void WithoutAKitTheOldInputStillWorks()
        {
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                Assert.IsFalse(hero.logic.HasKit);
                hero.logic.ButtonDown(HeroCommand.BasicAttack); // sem kit: vira o Press antigo
                world.Run(world.Step * 2);
                Assert.IsTrue(hero.logic.IsCasting);
            }
        }
    }
}
