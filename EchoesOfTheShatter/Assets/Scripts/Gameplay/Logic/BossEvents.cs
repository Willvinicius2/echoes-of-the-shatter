using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Evento de estado do chefe vindo do core (fase, rugido, invocação, stagger, escudo caído/de volta), para a apresentação e o
    /// spawner. O C# não decide nada daqui: só repassa. <see cref="Seconds"/>: rugido, tempo até surgirem, duração do stagger/escudo.
    /// </summary>
    public struct BossStateEvent
    {
        public Combatant Owner;
        public BossEventKind Kind;
        public int Phase;
        public double Seconds;
        public int Count;
        public string EnemyId;
    }

    /// <summary>Golpe que o escudo frontal do chefe (ou o rugido da transição) anulou: 0 de dano, sem Ímpeto, sem empurrão.</summary>
    public struct ShieldBlockedEvent
    {
        public Combatant Attacker;
        public Combatant Target;
        public SkillInfo Skill;
        /// <summary>true = rugido (invulnerável); false = escudo frontal.</summary>
        public bool Invulnerable;
    }
}
