using System.Collections.Generic;
using Echoes.Core;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    [Category("Core")]
    public sealed class EventBusTests
    {
        struct Ping
        {
            public int Value;
        }

        [Test]
        public void DeliversToSubscribersInOrder()
        {
            var bus = new EventBus();
            var log = new List<string>();
            bus.Subscribe((in Ping p) => log.Add("a" + p.Value));
            bus.Subscribe((in Ping p) => log.Add("b" + p.Value));
            var evt = new Ping { Value = 1 };
            bus.Publish(in evt);
            CollectionAssert.AreEqual(new[] { "a1", "b1" }, log);
        }

        [Test]
        public void UnsubscribeDuringPublishIsSafe()
        {
            var bus = new EventBus();
            var calls = 0;
            GameEventHandler<Ping> second = (in Ping p) => calls++;
            GameEventHandler<Ping> first = null;
            first = (in Ping p) =>
            {
                calls++;
                bus.Unsubscribe(first);
                bus.Unsubscribe(second);
            };
            bus.Subscribe(first);
            bus.Subscribe(second);
            var evt = new Ping();
            bus.Publish(in evt);
            Assert.AreEqual(1, calls, "o segundo saiu antes de ser chamado");
            bus.Publish(in evt);
            Assert.AreEqual(1, calls);
            Assert.AreEqual(0, bus.SubscriberCount<Ping>());
        }

        [Test]
        public void PublishWithoutSubscribersDoesNothing()
        {
            var bus = new EventBus();
            var evt = new Ping { Value = 3 };
            Assert.DoesNotThrow(() => bus.Publish(in evt));
        }
    }
}
