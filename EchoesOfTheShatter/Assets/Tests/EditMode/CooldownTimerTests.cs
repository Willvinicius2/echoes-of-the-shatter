using Echoes.Gameplay;
using Echoes.Interop;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    [Category("Gameplay")]
    public sealed class CooldownTimerTests
    {
        [Test]
        public void ReadyUntilStarted()
        {
            var cd = new CooldownTimer();
            Assert.IsTrue(cd.IsReady);
            cd.Start(4.0);
            Assert.IsFalse(cd.IsReady);
            Assert.AreEqual(1.0, cd.FractionRemaining, 1e-9);
        }

        [Test]
        public void ReadyAfterDuration()
        {
            var cd = new CooldownTimer();
            cd.Start(1.0);
            for (var i = 0; i < 59; i++) cd.Tick(1.0 / 60.0);
            Assert.IsFalse(cd.IsReady);
            cd.Tick(1.0 / 60.0);
            Assert.IsTrue(cd.IsReady);
            Assert.AreEqual(0.0, cd.Remaining, 1e-12);
        }

        [Test]
        public void ZeroDurationIsAlwaysReady()
        {
            var cd = new CooldownTimer();
            cd.Start(0.0);
            Assert.IsTrue(cd.IsReady);
            Assert.AreEqual(0.0, cd.FractionRemaining);
        }

        [Test]
        public void EffectiveCooldownComesFromCsvWithMinimum()
        {
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var charge = world.Rules.FindSkill("skill.warrior.charge");
                var ironCut = world.Rules.FindSkill("skill.warrior.iron_cut");
                Assert.AreEqual(charge.Cooldown, world.Rules.GetEffectiveCooldown(hero.combatant.Stats, charge), 1e-9);
                Assert.AreEqual(0.0, world.Rules.GetEffectiveCooldown(hero.combatant.Stats, ironCut), "sem recarga no CSV = 0");
            }
        }

        [Test]
        public void SkillGoesOnCooldownAndDeniesUntilReady()
        {
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var slot = hero.logic.GetSlot(2); // Fenda de Pedra (Q), custa recurso
                var cost = world.Rules.GetEffectiveCost(hero.combatant.Stats, slot.Skill);
                world.Combat.GainResource(hero.combatant, cost * 3);

                hero.logic.Press(HeroCommand.Skill2);
                world.Run(world.Step);
                Assert.IsTrue(hero.logic.IsCasting, "começou a Fenda");
                Assert.IsFalse(slot.Cooldown.IsReady);

                world.Run(slot.Skill.Windup + slot.Skill.Impact + slot.Skill.Recovery + world.Step);
                Assert.IsFalse(hero.logic.IsCasting);
                hero.logic.Press(HeroCommand.Skill2);
                world.Run(world.Step);
                Assert.IsFalse(hero.logic.IsCasting, "ainda em recarga");
                Assert.IsTrue(world.Denied.Exists(d => d.Reason == DenyReason.Cooldown));
            }
        }
    }
}
