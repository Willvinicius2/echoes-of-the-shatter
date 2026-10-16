namespace Echoes.Gameplay
{
    public struct ActionDeniedEvent
    {
        public Combatant Owner;
        public HeroCommand Command;
        public DenyReason Reason;
    }
}
