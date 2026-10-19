using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary>Um golpe resolvido pelo motor de regras (acertou, evadiu ou foi bloqueado).</summary>
    public struct HitEvent
    {
        public Combatant Attacker;
        public Combatant Target;
        public SkillInfo Skill;
        public HitResult Result;
        public bool IsHeavy;
        /// <summary>Acertou com hitstop leve (golpe não pesado que merece um tranco, ex.: golpe 2 do combo).</summary>
        public bool IsLightHitstop;
        public bool IsDamageOverTime;
        public PlanarVector Position;
    }
}
