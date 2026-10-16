namespace Echoes.Interop
{
    /// <summary>Saída de um golpe (<c>shatter::HitResult</c>, damage.h).</summary>
    public struct HitResult
    {
        public HitOutcome Outcome;
        public bool Critical;
        public bool Landed;
        public DamageByType AfterModifiers;
        public DamageByType AfterMitigation;
        public double TotalDamage;
        public double AbsorbedByBarrier;
        public double LifeLost;
        public double DefenderLifeAfter;
        public double DefenderBarrierAfter;
        public bool Killed;
    }
}
