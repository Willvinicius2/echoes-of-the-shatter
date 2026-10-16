using Echoes.Gameplay;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    [Category("Gameplay")]
    public sealed class ShapeQueryTests
    {
        static readonly PlanarVector Origin = PlanarVector.Zero;
        static readonly PlanarVector Ahead = PlanarVector.Forward;

        [Test]
        public void ConeHitsInFrontWithinRange()
        {
            Assert.IsTrue(ShapeQuery.InCone(Origin, Ahead, 2f, 45f, new PlanarVector(0f, 1.5f), 0.3f));
            Assert.IsFalse(ShapeQuery.InCone(Origin, Ahead, 2f, 45f, new PlanarVector(0f, 2.5f), 0.3f), "fora do alcance");
            Assert.IsFalse(ShapeQuery.InCone(Origin, Ahead, 2f, 45f, new PlanarVector(0f, -1f), 0.3f), "atrás");
        }

        [Test]
        public void ConeCountsTheTargetBody()
        {
            // Centro a 50° da frente, fora de um cone de ±45°, mas o corpo de 0,5 m a 1 m de distância entra.
            var target = PlanarVector.RotateTowards(Ahead, new PlanarVector(1f, 0f), 50f) * 1f;
            Assert.IsFalse(ShapeQuery.InCone(Origin, Ahead, 2f, 45f, target, 0f));
            Assert.IsTrue(ShapeQuery.InCone(Origin, Ahead, 2f, 45f, target, 0.5f));
        }

        [Test]
        public void CircleAndCorridor()
        {
            Assert.IsTrue(ShapeQuery.InCircle(Origin, 1.3f, new PlanarVector(1.5f, 0f), 0.3f));
            Assert.IsFalse(ShapeQuery.InCircle(Origin, 1.3f, new PlanarVector(2f, 0f), 0.3f));
            Assert.IsTrue(ShapeQuery.InCorridor(Origin, new PlanarVector(0f, 10f), 0.1f, new PlanarVector(0.3f, 5f), 0.3f));
            Assert.IsFalse(ShapeQuery.InCorridor(Origin, new PlanarVector(0f, 10f), 0.1f, new PlanarVector(1f, 5f), 0.3f));
        }

        [Test]
        public void RotateTowardsRespectsMaxDegrees()
        {
            var right = new PlanarVector(1f, 0f);
            var turned = PlanarVector.RotateTowards(Ahead, right, 30f);
            Assert.AreEqual(30f, PlanarVector.AngleDegrees(Ahead, turned), 1e-3f);
            Assert.Greater(turned.X, 0f, "girou para a direita");
            var full = PlanarVector.RotateTowards(Ahead, right, 120f);
            Assert.AreEqual(0f, PlanarVector.AngleDegrees(full, right), 1e-3f);
        }
    }
}
