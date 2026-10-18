using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Mudança de fase de uma ação. A apresentação toca o estado do Animator e ajusta a velocidade
    /// para caber em <see cref="PhaseSeconds"/> (docs/tecnico/04_arquitetura.md, seção 3.3).
    /// <see cref="ActionPhase.None"/> = a ação terminou ou foi cancelada.
    /// </summary>
    public struct SkillPhaseEvent
    {
        public Combatant Owner;
        public SkillInfo Skill;
        public ActionPhase Phase;
        public double PhaseSeconds;
        public PlanarVector Direction;
    }
}
