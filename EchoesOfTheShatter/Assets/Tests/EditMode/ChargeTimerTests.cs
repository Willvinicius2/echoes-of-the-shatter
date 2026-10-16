using Echoes.Gameplay;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    [Category("Gameplay")]
    public sealed class ChargeTimerTests
    {
        [Test]
        public void ConsumeUntilEmpty()
        {
            var timer = new ChargeTimer(2, 10.0);
            Assert.IsTrue(timer.TryConsume());
            Assert.IsTrue(timer.TryConsume());
            Assert.IsFalse(timer.TryConsume());
            Assert.IsTrue(timer.IsEmpty);
        }

        [Test]
        public void RechargeFractionAndTimeToNext()
        {
            var timer = new ChargeTimer(3, 40.0);
            timer.TryConsume();
            timer.Tick(10.0);
            Assert.AreEqual(0.25, timer.RechargeFraction, 1e-9);
            Assert.AreEqual(30.0, timer.SecondsToNextCharge, 1e-9);
        }

        [Test]
        public void LargeTickRechargesSeveralButNeverAboveMax()
        {
            var timer = new ChargeTimer(3, 1.0);
            timer.TryConsume();
            timer.TryConsume();
            timer.TryConsume();
            timer.Tick(10.0);
            Assert.AreEqual(3, timer.Charges);
            Assert.AreEqual(0.0, timer.RechargeFraction);
        }

        [Test]
        public void ProgressContinuesAfterConsumingWhileRecharging()
        {
            var timer = new ChargeTimer(3, 1.0);
            timer.TryConsume();       // 2
            timer.Tick(0.5);
            timer.TryConsume();       // 1, relógio segue em 0,5
            timer.Tick(0.5);
            Assert.AreEqual(2, timer.Charges, "a carga em recarga não reinicia o relógio");
        }

        [Test]
        public void AddChargesClampsAtMax()
        {
            var timer = new ChargeTimer(3, 40.0);
            timer.TryConsume();
            timer.AddCharges(5);
            Assert.AreEqual(3, timer.Charges);
        }

        [Test]
        public void ZeroRechargeRefillsImmediately()
        {
            var timer = new ChargeTimer(2, 0.0);
            timer.TryConsume();
            timer.Tick(0.0);
            Assert.AreEqual(2, timer.Charges);
        }
    }
}
