using System;
using System.Collections.Generic;

namespace Echoes.Interop
{
    /// <summary>
    /// PROVISÓRIO (stub). Porte do <c>shatter::StatBlock</c> (stats.h): fórmula única
    /// <c>max(0, (base + Σflat) × (1 + Σincreased) × Π(1 + more))</c>, mods em ordem de inserção,
    /// cache por (atributo, tags) invalidado a cada mudança.
    /// </summary>
    internal sealed class StubStatBlock : IStatBlock
    {
        readonly double[] bases = new double[(int)StatId.Count];
        readonly List<StubModifier> modifiers = new List<StubModifier>();
        readonly Dictionary<ulong, double> cache = new Dictionary<ulong, double>();
        ulong revision;
        bool disposed;

        public StubStatBlock()
        {
            // Atributos que são multiplicadores têm base 1 (stats.h).
            bases[(int)StatId.AttackSpeed] = 1.0;
            bases[(int)StatId.CastSpeed] = 1.0;
            bases[(int)StatId.MoveSpeed] = 1.0;
            bases[(int)StatId.CooldownRecovery] = 1.0;
            bases[(int)StatId.AreaOfEffect] = 1.0;
            bases[(int)StatId.DamageTaken] = 1.0;
            bases[(int)StatId.PotionEffect] = 1.0;
        }

        public ulong Revision => revision;

        /// <summary>Quantas vezes um valor foi recalculado (RF-03: leitura repetida não recalcula).</summary>
        public int RecomputeCount { get; private set; }

        public void SetBase(StatId stat, double value)
        {
            bases[(int)stat] = value;
            Invalidate();
        }

        public double GetBase(StatId stat) => bases[(int)stat];

        public void AddModifier(in StubModifier modifier)
        {
            modifiers.Add(modifier);
            Invalidate();
        }

        public int RemoveModifiersFrom(string source)
        {
            var removed = 0;
            for (var i = modifiers.Count - 1; i >= 0; i--)
            {
                if (string.Equals(modifiers[i].Source, source, StringComparison.Ordinal))
                {
                    modifiers.RemoveAt(i);
                    removed++;
                }
            }
            if (removed > 0) Invalidate();
            return removed;
        }

        public double Get(StatId stat) => GetTagged(stat, SkillTags.None);

        public double GetTagged(StatId stat, SkillTags contextTags)
        {
            ThrowIfDisposed();
            var key = ((ulong)stat << 32) | (uint)contextTags;
            if (cache.TryGetValue(key, out var cached)) return cached;
            var value = Compute(stat, contextTags, bases[(int)stat]);
            cache[key] = value;
            return value;
        }

        /// <summary>Mesmo cálculo com outra base (dano: base = dano da habilidade daquele tipo). Sem cache.</summary>
        public double ApplyTagged(StatId stat, SkillTags contextTags, double baseOverride)
        {
            ThrowIfDisposed();
            return Compute(stat, contextTags, baseOverride);
        }

        public static double ComputeStatValue(double baseValue, double sumFlat, double sumIncreased, double productMore)
        {
            var v = (baseValue + sumFlat) * (1.0 + sumIncreased) * productMore;
            return v > 0.0 ? v : 0.0;
        }

        double Compute(StatId stat, SkillTags contextTags, double baseValue)
        {
            RecomputeCount++;
            var sumFlat = 0.0;
            var sumIncreased = 0.0;
            var productMore = 1.0;
            for (var i = 0; i < modifiers.Count; i++)
            {
                var mod = modifiers[i];
                if (mod.Stat != stat) continue;
                if ((contextTags & mod.RequiredTags) != mod.RequiredTags) continue;
                switch (mod.Kind)
                {
                    case StubModKind.Flat: sumFlat += mod.Value; break;
                    case StubModKind.Increased: sumIncreased += mod.Value; break;
                    case StubModKind.More: productMore *= 1.0 + mod.Value; break;
                }
            }
            return ComputeStatValue(baseValue, sumFlat, sumIncreased, productMore);
        }

        void Invalidate()
        {
            cache.Clear();
            revision++;
        }

        void ThrowIfDisposed()
        {
            if (disposed) throw new ObjectDisposedException(nameof(StubStatBlock));
        }

        public void Dispose()
        {
            disposed = true;
            modifiers.Clear();
            cache.Clear();
        }
    }
}
