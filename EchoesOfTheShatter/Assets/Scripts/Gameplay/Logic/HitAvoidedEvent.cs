using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary>Um golpe não chegou ao motor de regras porque o alvo estava invulnerável (esquiva).</summary>
    public struct HitAvoidedEvent
    {
        public Combatant Attacker;
        public Combatant Target;
        public SkillInfo Skill;
    }
}
