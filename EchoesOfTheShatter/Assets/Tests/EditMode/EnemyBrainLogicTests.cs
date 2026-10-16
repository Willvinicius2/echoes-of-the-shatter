using System.Collections.Generic;
using Echoes.Gameplay;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    /// <summary>Máquina de estados base dos inimigos (RF-20): parado → perseguir → telegraph → atacar → recuperar.</summary>
    [Category("Gameplay")]
    public sealed class EnemyBrainLogicTests
    {
        const double Step = 1.0 / 60.0;

        sealed class FixedSelector : IAttackSelector
        {
            public int Next;
            public int Calls;

            public int SelectAttack()
            {
                Calls++;
                return Next;
            }
        }

        static EnemyBrainLogic NewBrain(FixedSelector selector = null)
        {
            var attacks = new[]
            {
                new EnemyAttackProfile(1.7f, 0.7, 0.1, 0.5),
                new EnemyAttackProfile(4.0f, 1.0, 0.15, 0.8),
            };
            return new EnemyBrainLogic(9f, attacks, selector ?? new FixedSelector());
        }

        static EnemyBrainInput Input(float distance, bool canAct = true, bool hasTarget = true)
        {
            return new EnemyBrainInput { HasTarget = hasTarget, DistanceToTarget = distance, CanAct = canAct };
        }

        static EnemyBrainEvents RunUntil(EnemyBrainLogic brain, EnemyBrainInput input, EnemyBrainState state, int maxSteps = 600)
        {
            var all = EnemyBrainEvents.None;
            for (var i = 0; i < maxSteps && brain.State != state; i++) all |= brain.Tick(Step, in input);
            return all;
        }

        [Test]
        public void StaysIdleOutsideAggro()
        {
            var brain = NewBrain();
            for (var i = 0; i < 60; i++) brain.Tick(Step, Input(20f));
            Assert.AreEqual(EnemyBrainState.Idle, brain.State);
            Assert.IsFalse(brain.WantsToMove);
        }

        [Test]
        public void ChasesInsideAggroAndWantsToMove()
        {
            var brain = NewBrain();
            var events = brain.Tick(Step, Input(8f));
            Assert.AreEqual(EnemyBrainState.Chase, brain.State);
            Assert.IsTrue((events & EnemyBrainEvents.StateChanged) != 0);
            Assert.IsTrue(brain.WantsToMove);
            Assert.AreEqual(0, brain.CurrentAttack, "escolhe o ataque ao entrar em perseguição");
        }

        [Test]
        public void TelegraphsWhenTargetInRangeOfChosenAttack()
        {
            var brain = NewBrain();
            brain.Tick(Step, Input(8f));
            brain.Tick(Step, Input(3f));
            Assert.AreEqual(EnemyBrainState.Chase, brain.State, "3 m está fora do alcance de 1,7 m");
            var events = brain.Tick(Step, Input(1.5f));
            Assert.AreEqual(EnemyBrainState.Telegraph, brain.State);
            Assert.IsTrue((events & EnemyBrainEvents.TelegraphStarted) != 0);
            Assert.IsFalse(brain.CanRotate, "direção travada no telegraph");
        }

        [Test]
        public void TelegraphLastsTheWindupThenImpacts()
        {
            var brain = NewBrain();
            brain.Tick(Step, Input(1f));
            brain.Tick(Step, Input(1f));
            Assert.AreEqual(EnemyBrainState.Telegraph, brain.State);
            var steps = 0;
            var events = EnemyBrainEvents.None;
            while (brain.State == EnemyBrainState.Telegraph && steps < 600)
            {
                events = brain.Tick(Step, Input(1f));
                steps++;
            }
            Assert.AreEqual(42, steps, "0,7 s de telegraph = 42 passos de 1/60");
            Assert.AreEqual(EnemyBrainState.Attack, brain.State);
            Assert.IsTrue((events & EnemyBrainEvents.AttackImpact) != 0);
        }

        [Test]
        public void PassesThroughAllFiveStatesInOrder()
        {
            var brain = NewBrain();
            var visited = new List<EnemyBrainState> { brain.State };
            for (var i = 0; i < 600; i++)
            {
                brain.Tick(Step, Input(1f));
                if (brain.State != visited[visited.Count - 1]) visited.Add(brain.State);
                if (visited.Count >= 6) break;
            }
            CollectionAssert.AreEqual(new[]
            {
                EnemyBrainState.Idle, EnemyBrainState.Chase, EnemyBrainState.Telegraph,
                EnemyBrainState.Attack, EnemyBrainState.Recover, EnemyBrainState.Chase,
            }, visited);
        }

        [Test]
        public void StunDuringTelegraphInterrupts()
        {
            var brain = NewBrain();
            brain.Tick(Step, Input(1f));
            brain.Tick(Step, Input(1f));
            Assert.AreEqual(EnemyBrainState.Telegraph, brain.State);
            var events = brain.Tick(Step, Input(1f, canAct: false));
            Assert.AreEqual(EnemyBrainState.Recover, brain.State);
            Assert.IsTrue((events & EnemyBrainEvents.Interrupted) != 0);
            Assert.IsFalse((events & EnemyBrainEvents.AttackImpact) != 0, "atordoado não ataca");
        }

        [Test]
        public void StaysInRecoverWhileStunned()
        {
            var brain = NewBrain();
            brain.Tick(Step, Input(1f));
            brain.Tick(Step, Input(1f));
            brain.Tick(Step, Input(1f, canAct: false));
            for (var i = 0; i < 120; i++) brain.Tick(Step, Input(1f, canAct: false));
            Assert.AreEqual(EnemyBrainState.Recover, brain.State);
            brain.Tick(Step, Input(1f));
            Assert.AreEqual(EnemyBrainState.Chase, brain.State);
        }

        [Test]
        public void RecoverPicksNextAttackFromSelector()
        {
            var selector = new FixedSelector { Next = 0 };
            var brain = NewBrain(selector);
            RunUntil(brain, Input(1f), EnemyBrainState.Recover);
            selector.Next = 1;
            RunUntil(brain, Input(1f), EnemyBrainState.Chase);
            Assert.AreEqual(1, brain.CurrentAttack);
            Assert.AreEqual(2, selector.Calls);
        }

        [Test]
        public void ReturnsToIdleWhenTargetIsGone()
        {
            var brain = NewBrain();
            brain.Tick(Step, Input(8f));
            Assert.AreEqual(EnemyBrainState.Chase, brain.State);
            brain.Tick(Step, Input(0f, hasTarget: false));
            Assert.AreEqual(EnemyBrainState.Idle, brain.State);
        }

        [Test]
        public void DeadBrainNeverActs()
        {
            var brain = NewBrain();
            brain.Kill();
            var events = brain.Tick(Step, Input(1f));
            Assert.AreEqual(EnemyBrainState.Dead, brain.State);
            Assert.AreEqual(EnemyBrainEvents.None, events);
        }
    }
}
