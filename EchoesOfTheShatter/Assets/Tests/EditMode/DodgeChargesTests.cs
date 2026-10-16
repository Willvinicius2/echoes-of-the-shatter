using Echoes.Gameplay;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    /// <summary>Esquiva e cargas (RF-15; docs/13, item 1). Lógica pura em passo fixo de 1/60 s.</summary>
    [Category("Gameplay")]
    public sealed class DodgeChargesTests
    {
        const double Step = 1.0 / 60.0;

        static DodgeLogic NewDodge() => new DodgeLogic(3, 1.5, 0.35, 0.2);

        static void Run(DodgeLogic dodge, double seconds)
        {
            var steps = (int)System.Math.Round(seconds / Step);
            for (var i = 0; i < steps; i++) dodge.Tick(Step);
        }

        [Test]
        public void StartsWithAllCharges()
        {
            var dodge = NewDodge();
            Assert.AreEqual(3, dodge.Charges.Charges);
            Assert.IsTrue(dodge.Charges.IsFull);
        }

        [Test]
        public void FourthDodgeInARowIsDenied()
        {
            var dodge = NewDodge();
            for (var i = 0; i < 3; i++)
            {
                Assert.IsTrue(dodge.TryStart(), $"esquiva {i + 1}");
                Run(dodge, 0.35);
                Assert.IsFalse(dodge.IsDodging);
            }
            Assert.IsFalse(dodge.TryStart(), "4ª esquiva seguida deveria ser negada");
        }

        [Test]
        public void CannotStartWhileDodging()
        {
            var dodge = NewDodge();
            Assert.IsTrue(dodge.TryStart());
            Run(dodge, 0.1);
            Assert.IsFalse(dodge.TryStart());
            Assert.AreEqual(2, dodge.Charges.Charges);
        }

        [Test]
        public void OneChargeReturnsAfterRechargeTime()
        {
            var dodge = NewDodge();
            dodge.TryStart();
            Run(dodge, 1.5 - Step);
            Assert.AreEqual(2, dodge.Charges.Charges, "ainda não voltou");
            Run(dodge, Step);
            Assert.AreEqual(3, dodge.Charges.Charges, "1 carga volta em 1,5 s");
        }

        [Test]
        public void RechargeIsSerialOneChargeAtATime()
        {
            var dodge = NewDodge();
            for (var i = 0; i < 3; i++)
            {
                dodge.TryStart();
                dodge.Stop();
            }
            Assert.AreEqual(0, dodge.Charges.Charges);
            Run(dodge, 1.5);
            Assert.AreEqual(1, dodge.Charges.Charges);
            Run(dodge, 1.5);
            Assert.AreEqual(2, dodge.Charges.Charges);
            Run(dodge, 1.5);
            Assert.AreEqual(3, dodge.Charges.Charges, "3 cargas vazias levam 4,5 s");
        }

        [Test]
        public void InvulnerableAt01sButNotAt03s()
        {
            var dodge = NewDodge();
            dodge.TryStart();
            Assert.IsTrue(dodge.IsInvulnerable, "invulnerável em 0,00 s (inclusive)");
            Run(dodge, 0.1);
            Assert.IsTrue(dodge.IsInvulnerable, "0,1 s: dentro da janela");
            Run(dodge, 0.2);
            Assert.IsTrue(dodge.IsDodging, "0,3 s: ainda esquivando");
            Assert.IsFalse(dodge.IsInvulnerable, "0,3 s: fora da janela");
        }

        [Test]
        public void InvulnerabilityWindowExcludesItsEnd()
        {
            var dodge = NewDodge();
            dodge.TryStart();
            Run(dodge, 0.2);
            Assert.IsFalse(dodge.IsInvulnerable, "0,20 s é exclusivo");
        }

        [Test]
        public void DodgeEndsAfterDuration()
        {
            var dodge = NewDodge();
            dodge.TryStart();
            Run(dodge, 0.35 - Step);
            Assert.IsTrue(dodge.IsDodging);
            Run(dodge, Step);
            Assert.IsFalse(dodge.IsDodging);
        }

        [Test]
        public void RefillRestoresChargesAndStops()
        {
            var dodge = NewDodge();
            dodge.TryStart();
            dodge.Refill();
            Assert.IsFalse(dodge.IsDodging);
            Assert.AreEqual(3, dodge.Charges.Charges);
        }
    }
}
