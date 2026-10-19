using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary>Um espaço da barra de habilidades do herói.</summary>
    public sealed class SkillSlot
    {
        public SkillSlot(int index, SkillInfo skill, bool unlocked)
        {
            Index = index;
            Skill = skill;
            Unlocked = unlocked;
        }

        public int Index { get; }
        public SkillInfo Skill { get; internal set; }
        public bool Unlocked { get; internal set; }
        public CooldownTimer Cooldown { get; } = new CooldownTimer();
        public bool IsEmpty => Skill == null;

        /// <summary>Custo efetivo no momento (para a UI tingir o ícone sem recurso).</summary>
        public double EffectiveCost { get; internal set; }
    }
}
