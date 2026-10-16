using Echoes.Presentation;
using NUnit.Framework;
using UnityEngine;

namespace Echoes.Tests.EditMode
{
    /// <summary>Tremor definido a 42 m e escalado por distância/42; raio de oclusão ~4 m (docs/04, seções 3.2 e 3.7).</summary>
    [Category("Presentation")]
    public sealed class CameraShakeScaleTests
    {
        [Test]
        public void FactorIsOneAtTheReferenceDistance()
        {
            Assert.AreEqual(1f, CameraShakeScale.Factor(42f, 42f), 1e-6f);
        }

        [Test]
        public void FactorScalesWithDistance()
        {
            Assert.AreEqual(56f / 42f, CameraShakeScale.Factor(56f, 42f), 1e-6f);
            Assert.AreEqual(66f / 42f, CameraShakeScale.Factor(66f, 42f), 1e-6f);
            Assert.AreEqual(48f / 42f, CameraShakeScale.Factor(48f, 42f), 1e-6f);
        }

        [Test]
        public void InvalidInputsFallBackToNoScaling()
        {
            Assert.AreEqual(1f, CameraShakeScale.Factor(56f, 0f));
            Assert.AreEqual(1f, CameraShakeScale.Factor(0f, 42f));
        }

        [Test]
        public void RenderSettingsDefaultsFollowTheDocument()
        {
            var settings = ScriptableObject.CreateInstance<RenderSettingsAsset>();
            try
            {
                Assert.AreEqual(42f, settings.shakeReferenceDistance);
                Assert.AreEqual(4f, settings.occlusionFadeRadiusMeters);
                Assert.AreEqual(56f, settings.distance);
                // Raio de oclusão escala por 56/42 em relação ao antigo ~3 m.
                Assert.AreEqual(3f * 56f / 42f, settings.occlusionFadeRadiusMeters, 0.05f);
            }
            finally
            {
                Object.DestroyImmediate(settings);
            }
        }
    }
}
