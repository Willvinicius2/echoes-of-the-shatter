namespace Echoes.Interop
{
    /// <summary>Resultado de beber uma poção, calculado pelo motor de regras.</summary>
    public readonly struct PotionOutcome
    {
        public readonly double LifeAfter;
        public readonly double BarrierAfter;
        public readonly double BarrierSeconds;
        public readonly double LifeGained;

        public PotionOutcome(double lifeAfter, double barrierAfter, double barrierSeconds, double lifeGained)
        {
            LifeAfter = lifeAfter;
            BarrierAfter = barrierAfter;
            BarrierSeconds = barrierSeconds;
            LifeGained = lifeGained;
        }
    }
}
