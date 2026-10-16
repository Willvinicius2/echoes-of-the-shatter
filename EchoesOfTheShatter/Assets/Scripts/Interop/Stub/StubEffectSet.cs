using System;
using System.Collections.Generic;

namespace Echoes.Interop
{
    /// <summary>
    /// PROVISÓRIO (stub). Porte simplificado do <c>shatter::EffectContainer</c> (effects.h): regras de
    /// acúmulo Refresh / StackN / StrongestOnly, recarga interna mínima para efeitos disparados,
    /// modificadores escritos no StatBlock com source <c>fx:&lt;id&gt;</c> e removidos ao expirar.
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
            if (!content.Effects.TryGetValue(effectId, out var data)) return false;
            if (data.IsStun && stunImmune) return false;
            if (internalCooldowns.TryGetValue(effectId, out var cd) && cd > 0.0) return false;
            if (data.Duration <= 0.0) return true; // instantâneo: nada a manter ativo

            switch (data.StackRule)
            {
                case StubStackRule.Refresh:
                {
                    var existing = Find(effectId);
                    if (existing != null)
                    {
                        existing.Remaining = data.Duration;
                        existing.Magnitude = magnitude;
                    }
                    else
                    {
                        Add(data, magnitude, sourceId);
                    }
                    break;
                }
                case StubStackRule.StackN:
                {
                    var count = StackCount(effectId);
                    if (count >= Math.Max(1, data.MaxStacks)) RemoveOldest(effectId);
                    Add(data, magnitude, sourceId);
                    break;
                }
                case StubStackRule.StrongestOnly:
                {
                    var existing = Find(effectId);
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
                        existing.Remaining = data.Duration;
                    }
                    break;
                }
            }

            if (data.Triggered || data.InternalCooldown > 0.0)
            {
                var icd = Math.Max(data.InternalCooldown, content.Rules.TriggerInternalCooldown);
                internalCooldowns[effectId] = icd;
            }
            RebuildModifiers(data);
            return true;
        }

        public void Tick(double dt, List<EffectTickEvent> outEvents)
        {
            // 1) ticks de dano, na ordem de aplicação.
            for (var i = 0; i < active.Count; i++)
            {
                var a = active[i];
                if (a.Data.TickInterval <= 0.0 || a.Data.DamagePerTick.IsZero) continue;
                a.TickAccumulator += dt;
                while (a.TickAccumulator >= a.Data.TickInterval)
                {
                    a.TickAccumulator -= a.Data.TickInterval;
                    var dmg = a.Data.DamagePerTick;
                    for (var t = 0; t < DamageByType.Count; t++) dmg[t] = dmg[t] * a.Magnitude;
                    outEvents?.Add(new EffectTickEvent { Expired = false, EffectId = a.Data.Id, Damage = dmg, Tags = a.Data.Tags });
                }
            }

            // 2) expiração.
            for (var i = 0; i < active.Count; i++)
            {
                var a = active[i];
                a.Remaining -= dt;
                if (a.Remaining > 0.0) continue;
                var data = a.Data;
                active.RemoveAt(i);
                pool.Add(a);
                i--;
                outEvents?.Add(new EffectTickEvent { Expired = true, EffectId = data.Id });
                RebuildModifiers(data);
            }

            // 3) recargas internas (chaves em lista reaproveitada: sem alocação por passo).
            cooldownKeys.Clear();
            foreach (var pair in internalCooldowns)
            {
                if (pair.Value > 0.0) cooldownKeys.Add(pair.Key);
            }
            for (var i = 0; i < cooldownKeys.Count; i++)
            {
                var key = cooldownKeys[i];
                internalCooldowns[key] = Math.Max(0.0, internalCooldowns[key] - dt);
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

        void RemoveOldest(string effectId)
        {
            for (var i = 0; i < active.Count; i++)
            {
                if (!string.Equals(active[i].Data.Id, effectId, StringComparison.Ordinal)) continue;
                pool.Add(active[i]);
                active.RemoveAt(i);
                return;
            }
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
