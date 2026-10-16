using Echoes.Gameplay;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    /// <summary>Passo fixo independente do FPS (RF-11; equivale ao Gameplay.FixedStep da seção 13.2 do 04).</summary>
    [Category("Gameplay")]
    public sealed class FixedStepAccumulatorTests
    {
        const double Step = 1.0 / 60.0;

        [TestCase(30)]
        [TestCase(60)]
        [TestCase(144)]
        [TestCase(240)]
        public void OneSecondIsAlwaysSixtySteps(int fps)
        {
            var acc = new FixedStepAccumulator(Step, 8);
            var total = 0;
            for (var i = 0; i < fps; i++) total += acc.Advance(1.0 / fps);
            Assert.AreEqual(60, total);
        }

        [Test]
        public void SmallFramesAccumulate()
        {
            var acc = new FixedStepAccumulator(Step, 8);
            Assert.AreEqual(0, acc.Advance(Step * 0.5));
            Assert.AreEqual(1, acc.Advance(Step * 0.5));
            Assert.AreEqual(0.0, acc.Alpha, 1e-6);
        }

        [Test]
        public void LongFrameIsCappedAndRemainderDropped()
        {
            var acc = new FixedStepAccumulator(Step, 5);
            Assert.AreEqual(5, acc.Advance(1.0));
            Assert.Greater(acc.DroppedSeconds, 0.0);
            Assert.AreEqual(0, acc.Advance(0.0), "não carrega a dívida para o próximo quadro");
        }

        [Test]
        public void IgnoresNegativeAndNaN()
        {
            var acc = new FixedStepAccumulator(Step, 8);
            Assert.AreEqual(0, acc.Advance(-1.0));
            Assert.AreEqual(0, acc.Advance(double.NaN));
            Assert.AreEqual(0L, acc.TotalSteps);
        }
    }
}
