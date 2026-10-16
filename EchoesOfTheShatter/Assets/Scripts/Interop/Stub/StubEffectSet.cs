using System;
using System.Collections.Generic;

namespace Echoes.Interop
{
    /// <summary>
    /// PROVISÓRIO (stub). Porte do <c>shatter::EffectContainer</c> (effects.h, src/effects.cpp) para
    /// aplicação direta: Refresh / StackN / StrongestOnly, recarga interna só para efeitos disparados,
    /// tolerância de tempo do core, modificadores no StatBlock com source <c>fx:&lt;id&gt;</c>.
    /// Barreira concedida por efeito ainda não é aplicada (nenhum efeito do protótipo usa).
    /// </summary>
    internal sealed class StubEffectSet : IEffectSet
    {
        sealed class Active
        {
            public StubEffectData Data;
            public double Magnitude;
            public double Remaining;
            public double TickAccumulator;
            public uint ApplyOrder;
            public string Source;
        }

        /// <summary>Tolerância de tempo do core (kTimeEps em src/effects.cpp): passos de 1/60 não são exatos em binário.</summary>
        const double TimeEps = 1e-9;

        readonly StubContent content;
        readonly StubStatBlock target;
        readonly bool stunImmune;
        readonly List<Active> active = new List<Active>();
        readonly List<Active> pool = new List<Active>();
        readonly Dictionary<string, double> internalCooldowns = new Dictionary<string, double>(StringComparer.Ordinal);
        readonly List<string> cooldownKeys = new List<string>();
        uint nextApplyOrder;

        public StubEffectSet(StubContent content, StubStatBlock target, bool stunImmune)
        {
            this.content = content;
            this.target = target;
            this.stunImmune = stunImmune;
        }

        public int ActiveCount => active.Count;

        public bool Apply(string effectId, double magnitude, string sourceId)
        {
            // Porte de EffectContainer::Apply (src/effects.cpp) para aplicação direta (TriggerKind::None).
            if (!content.Effects.TryGetValue(effectId, out var data)) return false;
            if (data.IsStun && stunImmune) return false; // imunidade pendente no core (docs/13, item 3)

            var gated = data.Triggered;
            if (gated && internalCooldowns.TryGetValue(effectId, out var cd) && cd > TimeEps) return false;

            var applied = true;
            if (data.Duration > 0.0)
            {
                Active existing = null;
                Active oldest = null;
                var count = 0;
                for (var i = 0; i < active.Count; i++)
                {
                    var a = active[i];
                    if (!string.Equals(a.Data.Id, effectId, StringComparison.Ordinal)) continue;
                    count++;
                    if (existing == null) existing = a;
                    if (oldest == null || a.ApplyOrder < oldest.ApplyOrder) oldest = a;
                }

                switch (data.StackRule)
                {
                    case StubStackRule.Refresh:
                        if (existing != null)
                        {
                            existing.Magnitude = magnitude;
                            existing.Remaining = data.Duration;
                            existing.Source = sourceId;
                        }
                        else
                        {
                            Add(data, magnitude, sourceId);
                        }
                        break;
                    case StubStackRule.StackN:
                        if (count >= Math.Max(1, data.MaxStacks) && oldest != null)
                        {
                            active.Remove(oldest);
                            pool.Add(oldest);
                        }
                        Add(data, magnitude, sourceId);
                        break;
                    case StubStackRule.StrongestOnly:
                        if (existing == null)
                        {
                            Add(data, magnitude, sourceId);
                        }
                        else if (magnitude > existing.Magnitude)
                        {
                            existing.Magnitude = magnitude;
                            existing.Remaining = data.Duration;
                            existing.Source = sourceId;
                        }
                        else if (magnitude == existing.Magnitude)
                        {
                            existing.Remaining = data.Duration; // empate renova a duração
                        }
                        else
                        {
                            applied = false; // mais fraco que o ativo: ignorado
                        }
                        break;
                }
                if (applied) RebuildModifiers(data);
            }

            if (applied && gated)
                internalCooldowns[effectId] = Math.Max(data.InternalCooldown, content.Rules.TriggerInternalCooldown);
            return applied;
        }

        public void Tick(double dt, List<EffectTickEvent> outEvents)
        {
            // Porte de EffectContainer::Tick (src/effects.cpp).
            if (dt <= 0.0) return;

            // 1) ticks de dano, na ordem de aplicação; o passo do DoT não passa do tempo restante.
            for (var i = 0; i < active.Count; i++)
            {
                var a = active[i];
                var data = a.Data;
                var step = Math.Min(dt, a.Remaining > 0.0 ? a.Remaining : 0.0);
                a.Remaining -= dt;
                if (data.TickInterval <= 0.0 || step <= 0.0) continue;
                a.TickAccumulator += step;
                while (a.TickAccumulator + TimeEps >= data.TickInterval)
                {
                    a.TickAccumulator -= data.TickInterval;
                    var dmg = data.DamagePerTick;
                    var any = false;
                    for (var t = 0; t < DamageByType.Count; t++)
                    {
                        dmg[t] = dmg[t] * a.Magnitude;
                        any = any || dmg[t] > 0.0;
                    }
                    if (any) outEvents?.Add(new EffectTickEvent { Expired = false, EffectId = data.Id, Damage = dmg, Tags = data.Tags });
                }
            }

            // 2) expiração.
            for (var i = 0; i < active.Count; i++)
            {
                var a = active[i];
                if (a.Remaining > TimeEps) continue;
                var data = a.Data;
                active.RemoveAt(i);
                pool.Add(a);
                i--;
                outEvents?.Add(new EffectTickEvent { Expired = true, EffectId = data.Id });
                RebuildModifiers(data);
            }

            // 3) recargas internas (chaves em lista reaproveitada: sem alocação por passo).
            cooldownKeys.Clear();
            foreach (var pair in internalCooldowns) cooldownKeys.Add(pair.Key);
            for (var i = 0; i < cooldownKeys.Count; i++)
            {
                var key = cooldownKeys[i];
                var left = internalCooldowns[key] - dt;
                if (left <= TimeEps) internalCooldowns.Remove(key);
                else internalCooldowns[key] = left;
            }
        }

        public int StackCount(string effectId)
        {
            var count = 0;
            for (var i = 0; i < active.Count; i++)
            {
                if (string.Equals(active[i].Data.Id, effectId, StringComparison.Ordinal)) count++;
            }
            return count;
        }

        public void Clear()
        {
            for (var i = active.Count - 1; i >= 0; i--)
            {
                var data = active[i].Data;
                pool.Add(active[i]);
                active.RemoveAt(i);
                target.RemoveModifiersFrom(SourceOf(data.Id));
            }
            internalCooldowns.Clear();
        }

        public void Dispose()
        {
            Clear();
        }

        Active Find(string effectId)
        {
            for (var i = 0; i < active.Count; i++)
            {
                if (string.Equals(active[i].Data.Id, effectId, StringComparison.Ordinal)) return active[i];
            }
            return null;
        }

        void Add(StubEffectData data, double magnitude, string sourceId)
        {
            Active a;
            if (pool.Count > 0)
            {
                a = pool[pool.Count - 1];
                pool.RemoveAt(pool.Count - 1);
            }
            else
            {
                a = new Active();
            }
            a.Data = data;
            a.Magnitude = magnitude;
            a.Remaining = data.Duration;
            a.TickAccumulator = 0.0;
            a.ApplyOrder = nextApplyOrder++;
            a.Source = sourceId;
            active.Add(a);
        }

        void RebuildModifiers(StubEffectData data)
        {
            var source = SourceOf(data.Id);
            target.RemoveModifiersFrom(source);
            for (var i = 0; i < active.Count; i++)
            {
                var a = active[i];
                if (!ReferenceEquals(a.Data, data)) continue;
                for (var m = 0; m < data.Modifiers.Count; m++)
                {
                    var mod = data.Modifiers[m];
                    mod.Value *= a.Magnitude;
                    mod.Source = source;
                    target.AddModifier(mod);
                }
            }
        }

        static string SourceOf(string effectId) => "fx:" + effectId;
    }
}
