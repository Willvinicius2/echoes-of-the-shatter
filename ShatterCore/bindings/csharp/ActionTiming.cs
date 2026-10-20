namespace Echoes.Interop
{
    /// <summary>
    /// Tempos efetivos das 3 fases de uma ação (preparação, impacto, recuperação), em segundos,
    /// já com velocidade de ataque aplicada pelo motor de regras.
    /// </summary>
    public readonly struct ActionTiming
    {
        public readonly double Windup;
        public readonly double Impact;
        public readonly double Recovery;

        public ActionTiming(double windup, double impact, double recovery)
        {
            Windup = windup;
            Impact = impact;
            Recovery = recovery;
        }

        public double Total => Windup + Impact + Recovery;
    }
}
