namespace Echoes.Gameplay
{
    public struct DodgeStartedEvent
    {
        public Combatant Owner;
        public PlanarVector Direction;
        public double DurationSeconds;
        public double InvulnerableSeconds;
    }
}
