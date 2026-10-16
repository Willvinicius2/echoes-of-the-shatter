using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary>Um projétil em voo (em pool dentro do <see cref="ProjectileSystem"/>).</summary>
    public sealed class ProjectileState
    {
        public int Id;
        public Combatant Owner;
        public SkillInfo Skill;
        public PlanarVector Position;
        public PlanarVector Direction;
        public float SpeedMetersPerSecond;
        public float RemainingMeters;
        public float RadiusMeters;
        public bool Active;
    }
}
