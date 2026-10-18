using System;
using System.Collections.Generic;

namespace Echoes.Core
{
    /// <summary>
    /// Barramento de eventos tipado e sem alocação no <see cref="Publish{T}"/> (docs/tecnico/04_arquitetura.md,
    /// seção 10.4). É uma instância guardada pelo GameRoot, nunca estática: com "Enter Play Mode
    /// Options" sem recarga de domínio, nada sobrevive entre sessões de Play.
    /// Assinar e desassinar durante uma publicação é seguro.
    /// </summary>
    public sealed class EventBus
    {
        sealed class Channel<T> where T : struct
        {
            public readonly List<GameEventHandler<T>> Handlers = new List<GameEventHandler<T>>();
            public int PublishDepth;
            public bool HasRemovals;
        }

        readonly Dictionary<Type, object> channels = new Dictionary<Type, object>();

        public void Subscribe<T>(GameEventHandler<T> handler) where T : struct
        {
            if (handler == null) throw new ArgumentNullException(nameof(handler));
            GetOrCreate<T>().Handlers.Add(handler);
        }

        public void Unsubscribe<T>(GameEventHandler<T> handler) where T : struct
        {
            if (handler == null) return;
            if (!channels.TryGetValue(typeof(T), out var boxed)) return;
            var channel = (Channel<T>)boxed;
            var index = channel.Handlers.IndexOf(handler);
            if (index < 0) return;
            if (channel.PublishDepth > 0)
            {
                channel.Handlers[index] = null;
                channel.HasRemovals = true;
            }
            else
            {
                channel.Handlers.RemoveAt(index);
            }
        }

        public void Publish<T>(in T evt) where T : struct
        {
            if (!channels.TryGetValue(typeof(T), out var boxed)) return;
            var channel = (Channel<T>)boxed;
            var count = channel.Handlers.Count; // assinantes novos entram na próxima publicação
            channel.PublishDepth++;
            try
            {
                for (var i = 0; i < count; i++)
                {
                    var handler = channel.Handlers[i];
                    handler?.Invoke(in evt);
                }
            }
            finally
            {
                channel.PublishDepth--;
                if (channel.PublishDepth == 0 && channel.HasRemovals)
                {
                    channel.Handlers.RemoveAll(h => h == null);
                    channel.HasRemovals = false;
                }
            }
        }

        public int SubscriberCount<T>() where T : struct
        {
            if (!channels.TryGetValue(typeof(T), out var boxed)) return 0;
            var handlers = ((Channel<T>)boxed).Handlers;
            var count = 0;
            for (var i = 0; i < handlers.Count; i++)
            {
                if (handlers[i] != null) count++;
            }
            return count;
        }

        public void Clear()
        {
            channels.Clear();
        }

        Channel<T> GetOrCreate<T>() where T : struct
        {
            if (channels.TryGetValue(typeof(T), out var boxed)) return (Channel<T>)boxed;
            var channel = new Channel<T>();
            channels.Add(typeof(T), channel);
            return channel;
        }
    }
}
