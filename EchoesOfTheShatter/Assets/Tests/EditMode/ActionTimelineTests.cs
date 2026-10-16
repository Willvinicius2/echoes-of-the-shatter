using Echoes.Gameplay;
using Echoes.Interop;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    [Category("Gameplay")]
    public sealed class ActionTimelineTests
    {
        const double Step = 1.0 / 60.0;

        [Test]
        public void PhasesRunInOrderWithEvents()
        {
            var t = new ActionTimeline();
            t.Begin(new ActionTiming(0.15, 0.1, 0.2));
            Assert.AreEqual(ActionPhase.Windup, t.Phase);

            var seen = ActionTimelineEvents.None;
            var impactStep = -1;
            var steps = 0;
            while (t.IsActive && steps < 1000)
            {
                var e = t.Tick(Step);
                steps++;
                if ((e & ActionTimelineEvents.ImpactStarted) != 0) impactStep = steps;
                seen |= e;
            }
            Assert.AreEqual(ActionTimelineEvents.ImpactStarted | ActionTimelineEvents.ImpactEnded | ActionTimelineEvents.Finished, seen);
            Assert.AreEqual(9, impactStep, "0,15 s = 9 passos de 1/60");
            Assert.AreEqual(27, steps, "0,45 s = 27 passos de 1/60");
        }

        [Test]
        public void LeftoverTimeCarriesIntoNextPhase()
        {
            var t = new ActionTimeline();
            t.Begin(new ActionTiming(0.1, 0.1, 0.1));
            var e = t.Tick(0.25);
            Assert.AreEqual(ActionTimelineEvents.ImpactStarted | ActionTimelineEvents.ImpactEnded, e);
            Assert.AreEqual(ActionPhase.Recovery, t.Phase);
            Assert.AreEqual(0.05, t.PhaseElapsed, 1e-9);
        }

        [Test]
        public void ZeroLengthPhasesPassImmediately()
        {
            var t = new ActionTimeline();
            t.Begin(new ActionTiming(0.0, 0.0, 0.2));
            var e = t.Tick(0.0);
            Assert.AreEqual(ActionTimelineEvents.ImpactStarted | ActionTimelineEvents.ImpactEnded, e);
            Assert.AreEqual(ActionPhase.Recovery, t.Phase);
        }

        [Test]
        public void RecoveryFractionTracksSecondHalf()
        {
            var t = new ActionTimeline();
            t.Begin(new ActionTiming(0.0, 0.0, 0.4));
            t.Tick(0.0);
            t.Tick(0.2);
            Assert.AreEqual(0.5, t.RecoveryFraction, 1e-9);
        }

        [Test]
        public void IronCutCycleIsBetween04And06Seconds()
        {
            // RF-13: Corte de Ferro tem ciclo total entre 0,4 e 0,6 s (tempos do skills.csv).
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var skill = world.Rules.FindSkill("skill.warrior.iron_cut");
                var timing = world.Rules.GetActionTiming(hero.combatant.Stats, skill);
                Assert.That(timing.Total, Is.InRange(0.4, 0.6));
            }
        }
    }
}
