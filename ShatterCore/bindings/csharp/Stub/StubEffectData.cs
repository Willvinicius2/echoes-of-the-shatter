using System.Collections.Generic;

namespace Echoes.Interop
{
    /// <summary>PROVISÓRIO (stub). Dados de efeito (<c>shatter::EffectData</c>, effects.csv).</summary>
    internal sealed class StubEffectData
    {
        public string Id = string.Empty;
        public double Duration;
        public double TickInterval;
        public StubStackRule StackRule;
        public int MaxStacks = 1;
        public DamageByType DamagePerTick;
        public readonly List<StubModifier> Modifiers = new List<StubModifier>();
        public double Barrier;
        public bool Triggered;
        public double InternalCooldown;
        public SkillTags Tags;
        /// <summary>Atordoamento: interrompe a ação; respeita imunidades (docs/13, item 3).</summary>
        public bool IsStun;
    }
}
