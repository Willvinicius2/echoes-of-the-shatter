using Echoes.Gameplay;
using Echoes.Interop;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    /// <summary>Para onde o herói olha: andando = direção do movimento, golpe = mira, parado = última direção (sem deslizar de lado).</summary>
    [Category("Gameplay")]
    public sealed class HeroFacingTests
    {
        [Test]
        public void WalkingFacesTheMovementNotTheMouse()
        {
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                hero.logic.AimPoint = new PlanarVector(0f, 10f);      // mouse à frente (+Z)
                hero.logic.MoveInput = new PlanarVector(1f, 0f);      // WASD para o lado (+X)
                world.Run(0.2);
                var facing = hero.logic.FacingDirection();
                Assert.Greater(facing.X, 0.99f, "olha para onde anda");
                Assert.AreEqual(0f, facing.Z, 0.01f);
                Assert.Greater(hero.combatant.Forward.X, 0.99f, "o Forward da lógica acompanha");
            }
        }

        [Test]
        public void StandingStillKeepsTheLastDirection()
        {
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                hero.logic.MoveInput = new PlanarVector(-1f, 0f);
                world.Run(0.2);
                hero.logic.MoveInput = PlanarVector.Zero;
                hero.logic.AimPoint = new PlanarVector(5f, 5f);       // o mouse mexer não vira o corpo parado
                world.Run(0.2);
                var facing = hero.logic.FacingDirection();
                Assert.Less(facing.X, -0.99f);
            }
        }

        [Test]
        public void CastingFacesTheAimEvenWhileMoving()
        {
            using (var world = new TestWorld())
            {
                var hero = world.AddHero(PlanarVector.Zero);
                hero.logic.AimPoint = new PlanarVector(0f, 10f);
                hero.logic.MoveInput = new PlanarVector(1f, 0f);
                world.Run(0.1);
                hero.logic.Press(HeroCommand.BasicAttack);
                world.Run(world.Step * 2);
                Assert.IsTrue(hero.logic.IsCasting);
                var facing = hero.logic.FacingDirection();
                Assert.Greater(facing.Z, 0.99f, "durante o golpe olha para a mira");
            }
        }

        [Test]
        public void TurnSpeedsComeFromTheFeelValues()
        {
            var values = CombatFeelSettings.CreateDefaultValues();
            Assert.AreEqual(900f, values.TurnDegreesPerSecond);
            Assert.Greater(values.CastTurnDegreesPerSecond, values.TurnDegreesPerSecond, "mais rápido ao iniciar o golpe");
        }
    }
}
