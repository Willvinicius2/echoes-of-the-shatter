using Echoes.Interop;

namespace Echoes.Gameplay
{
    public enum BasicInputKind : byte
    {
        /// <summary>Passou o limiar de segurar: começou a carregar o golpe forte.</summary>
        ChargeStarted = 1,
        /// <summary>Chegou ao máximo da carga: o golpe solta sozinho.</summary>
        ChargeFull = 2,
        /// <summary>Esquiva, defesa, habilidade, atordoamento ou morte cancelaram a carga (sem custo, sem recarga).</summary>
        ChargeCancelled = 3,
        /// <summary>Soltou o golpe forte; <see cref="BasicInputEvent.Value"/> = progresso da carga, 0 a 1 (o multiplicador de dano é do core).</summary>
        HeavyReleased = 4,
        /// <summary>Levantou a defesa.</summary>
        GuardUp = 5,
        /// <summary>Baixou a defesa (soltou o botão, esquiva ou atordoamento).</summary>
        GuardDown = 6,
        /// <summary>A defesa caiu sozinha no tempo máximo (<c>guardMaxHold</c>).</summary>
        GuardBroke = 7,
        /// <summary>O combo voltou ao primeiro golpe (janela perdida, cancelamento ou golpe de fecho).</summary>
        ComboReset = 8,
        /// <summary>Apertou o botão esquerdo e o golpe leve é possível; <see cref="BasicInputEvent.Skill"/> = o próximo golpe do combo. Pode virar carga (ChargeStarted) em seguida.</summary>
        LightPressed = 9,
    }

    /// <summary>
    /// Mudança de estado da máquina de entrada do ataque básico (docs/18, seção 1.3), para a apresentação (Animator, anel de carga, HUD).
    /// A regra continua na lógica; isto só avisa.
    /// </summary>
    public struct BasicInputEvent
    {
        public Combatant Owner;
        public BasicInputKind Kind;
        public SkillInfo Skill;
        public double Value;
    }
}
