using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary><see cref="Applied"/> = false no início do gole; true quando o efeito entra.</summary>
    public struct PotionUsedEvent
    {
        public Combatant Owner;
        public PotionInfo Potion;
        public bool Applied;
        public double LifeGained;
    }
}
