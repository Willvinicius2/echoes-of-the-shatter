using Echoes.UI;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    /// <summary>Refúgio por estado: cada hub_state do core liga só o seu grupo de cenário.</summary>
    [Category("Historia")]
    public sealed class RefugeHubStatesTests
    {
        [Test]
        public void Village_state_shows_only_village() =>
            Assert.AreEqual((true, false), HubStateRule.Visible("hub.fortified_village"));

        [Test]
        public void Garrison_state_shows_only_garrison() =>
            Assert.AreEqual((false, true), HubStateRule.Visible("hub.fortified_garrison"));

        [TestCase("")]
        [TestCase(null)]
        [TestCase("hub.unknown")]
        public void No_verdict_shows_nothing(string state) =>
            Assert.AreEqual((false, false), HubStateRule.Visible(state));
    }
}
