using Echoes.Gameplay;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    [Category("Gameplay")]
    public sealed class TimersTests
    {
        [Test]
        public void HitstopKeepsTheLongest()
        {
            var h = new HitstopTimer();
            h.Trigger(0.06);
            h.Trigger(0.04);
            Assert.AreEqual(0.06, h.Remaining, 1e-12);
            h.Trigger(0.08);
            Assert.AreEqual(0.08, h.Remaining, 1e-12);
        }

        [Test]
        public void HitstopRunsOut()
        {
            var h = new HitstopTimer();
            h.Trigger(0.05);
            for (var i = 0; i < 3; i++) h.Tick(1.0 / 60.0);
            Assert.IsFalse(h.IsActive);
        }

        [Test]
        public void InputBufferExpiresAfterWindow()
        {
            var b = new InputBuffer(0.1);
            b.Push(HeroCommand.Dodge);
            for (var i = 0; i < 6; i++) b.Tick(1.0 / 60.0);
            Assert.IsTrue(b.HasPending, "0,1 s ainda vale");
            b.Tick(1.0 / 60.0);
            Assert.IsFalse(b.HasPending);
        }

        [Test]
        public void InputBufferKeepsNewestCommand()
        {
            var b = new InputBuffer(0.1);
            b.Push(HeroCommand.BasicAttack);
            b.Push(HeroCommand.Skill2);
            Assert.AreEqual(HeroCommand.Skill2, b.Pending);
            b.Consume();
            Assert.IsFalse(b.HasPending);
        }
    }
}
