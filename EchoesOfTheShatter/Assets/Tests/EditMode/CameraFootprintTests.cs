using Echoes.Presentation;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    /// <summary>Conta de largura e profundidade visíveis do CameraDistanceTuner (docs/04, seção 3.2).</summary>
    public sealed class CameraFootprintTests
    {
        const float Fov = 14.2f;
        const float Pitch = 55f;
        const float Aspect16By9 = 16f / 9f;

        [Test]
        public void At42m_MatchesDocumentedFootprint()
        {
            // docs/04, seção 3.2: ~18,6 × 10,5 m perpendiculares; ~6,4 módulos de 2 m de chão.
            Assert.AreEqual(10.46f, CameraFootprint.PerpendicularHeight(42f, Fov), 0.05f);
            Assert.AreEqual(18.6f, CameraFootprint.VisibleWidth(42f, Fov, Aspect16By9), 0.1f);
            Assert.AreEqual(12.8f, CameraFootprint.VisibleGroundDepth(42f, Fov, Pitch), 0.1f);
        }

        [TestCase(56f, 24.8f)]
        [TestCase(66f, 29.2f)]
        [TestCase(80f, 35.4f)]
        public void Width_ScalesLinearlyWithDistance(float distance, float expected)
        {
            Assert.AreEqual(expected, CameraFootprint.VisibleWidth(distance, Fov, Aspect16By9), 0.1f);
        }

        [Test]
        public void WiderAspect_ShowsMoreWidth()
        {
            var narrow = CameraFootprint.VisibleWidth(66f, Fov, 16f / 10f);
            var wide = CameraFootprint.VisibleWidth(66f, Fov, 21f / 9f);
            Assert.Greater(wide, narrow);
        }

        [Test]
        public void StepDistance_MovesByStepAndClamps()
        {
            Assert.AreEqual(44f, CameraFootprint.StepDistance(42f, 1, 2f, 30f, 100f), 1e-4f);
            Assert.AreEqual(40f, CameraFootprint.StepDistance(42f, -1, 2f, 30f, 100f), 1e-4f);
            Assert.AreEqual(100f, CameraFootprint.StepDistance(100f, 1, 2f, 30f, 100f), 1e-4f);
            Assert.AreEqual(30f, CameraFootprint.StepDistance(30f, -1, 2f, 30f, 100f), 1e-4f);
        }

        [Test]
        public void StepDistance_SnapsOffGridValues()
        {
            Assert.AreEqual(44f, CameraFootprint.StepDistance(42.6f, 1, 2f, 30f, 100f), 1e-4f);
            Assert.AreEqual(42f, CameraFootprint.StepDistance(42.6f, -1, 2f, 30f, 100f), 1e-4f);
        }

        [Test]
        public void FarClip_FollowsDistancePlusMargin()
        {
            Assert.AreEqual(160f, CameraFootprint.FarClip(80f, 80f), 1e-4f);
            Assert.AreEqual(122f, CameraFootprint.FarClip(42f, 80f), 1e-4f);
        }
    }
}
