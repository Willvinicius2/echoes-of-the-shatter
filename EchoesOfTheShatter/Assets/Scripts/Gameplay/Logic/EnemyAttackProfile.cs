namespace Echoes.Gameplay
{
    /// <summary>
    /// Ataque já convertido para a IA: alcance em metros e tempos das fases (o windup do inimigo é o
    /// telegraph). Montado a partir do <c>SkillInfo</c> e do <c>ActionTiming</c> do motor de regras.
    /// </summary>
    public readonly struct EnemyAttackProfile
    {
        public readonly float RangeMeters;
        public readonly double Windup;
        public readonly double Impact;
        public readonly double Recovery;

        public EnemyAttackProfile(float rangeMeters, double windup, double impact, double recovery)
        {
            RangeMeters = rangeMeters;
            Windup = windup;
            Impact = impact;
            Recovery = recovery;
        }
    }
}
