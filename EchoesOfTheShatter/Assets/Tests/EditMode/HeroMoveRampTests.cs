using Echoes.Gameplay;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    /// <summary>
    /// Rampa de movimento do herói (API C 1.7): <c>hero_move_accel_seconds</c> (0,10) e <c>hero_move_decel_seconds</c> (0,08) de CombatRules.
    /// A lógica aplica uma rampa linear (velocidade += máxima × dt ÷ tempo); tudo em passo fixo, sem número no C#.
    /// </summary>
    public sealed class HeroMoveRampTests
    {
        [Test]
        public void CoreRulesCarryTheRampTimes()
        {
            using (var world = new TestWorld(null, TestWorld.LoadNativeRules()))
            {
                Assert.AreEqual(0.10, world.Rules.Combat.HeroMoveAccelSeconds, 1e-9);
                Assert.AreEqual(0.08, world.Rules.Combat.HeroMoveDecelSeconds, 1e-9);
            }
        }

        [Test]
        public void SpeedRampsUpLinearlyAndReachesTheMaximumInAccelSeconds()
        {
            using (var world = new TestWorld(null, TestWorld.LoadNativeRules()))
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var accel = world.Rules.Combat.HeroMoveAccelSeconds;
                var max = hero.logic.WalkSpeed;
                hero.logic.MoveInput = new PlanarVector(1f, 0f);

                world.Run(world.Step);
                var first = hero.logic.CurrentVelocity().Magnitude;
                Assert.AreEqual(max * world.Step / accel, first, max * 1e-3, "um passo: máxima × dt ÷ accel");
                Assert.Less(first, max * 0.5f, "o primeiro passo não é a velocidade cheia");

                world.Run(accel / 2.0 - world.Step);
                Assert.AreEqual(max * 0.5f, hero.logic.CurrentVelocity().Magnitude, max * 0.05f, "no meio do tempo, metade da velocidade");

                world.Run(accel);
                Assert.AreEqual(max, hero.logic.CurrentVelocity().Magnitude, max * 1e-3, "depois de accel s, a velocidade máxima");
            }
        }

        [Test]
        public void SpeedRampsDownToZeroInDecelSecondsAndStaysStoppedWithoutInput()
        {
            using (var world = new TestWorld(null, TestWorld.LoadNativeRules()))
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var max = hero.logic.WalkSpeed;
                hero.logic.MoveInput = new PlanarVector(1f, 0f);
                world.Run(world.Rules.Combat.HeroMoveAccelSeconds * 2.0);
                Assert.AreEqual(max, hero.logic.CurrentVelocity().Magnitude, max * 1e-3);

                hero.logic.MoveInput = PlanarVector.Zero;
                world.Run(world.Step);
                var first = hero.logic.CurrentVelocity().Magnitude;
                Assert.Greater(first, 0f, "não para na hora");
                Assert.Less(first, max, "mas já começou a frear");

                world.Run(world.Rules.Combat.HeroMoveDecelSeconds);
                Assert.AreEqual(0f, hero.logic.CurrentVelocity().Magnitude, 1e-4f, "parado depois de decel s");
                var position = hero.combatant.Position;
                world.Run(0.5);
                Assert.AreEqual(position.X, hero.combatant.Position.X, 1e-5f, "sem entrada, fica parado");
                Assert.AreEqual(position.Z, hero.combatant.Position.Z, 1e-5f);
            }
        }

        [Test]
        public void TheRampDelaysTheDistanceTravelledByHalfOfAccelTime()
        {
            using (var world = new TestWorld(null, TestWorld.LoadNativeRules()))
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var accel = world.Rules.Combat.HeroMoveAccelSeconds;
                var max = hero.logic.WalkSpeed;
                hero.logic.MoveInput = new PlanarVector(1f, 0f);
                var total = 1.0;
                world.Run(total);
                // Distância com rampa = max × (total − accel/2) (triângulo no começo).
                var expected = max * (total - accel / 2.0);
                Assert.AreEqual(expected, hero.combatant.Position.X, max * world.Step * 2.0, "a rampa custa meio tempo de aceleração");
            }
        }
    }
}
