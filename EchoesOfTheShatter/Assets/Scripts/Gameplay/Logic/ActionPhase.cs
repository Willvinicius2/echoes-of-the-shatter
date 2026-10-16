namespace Echoes.Gameplay
{
    /// <summary>Fase de uma ação (habilidade ou ataque): preparação, impacto, recuperação.</summary>
    public enum ActionPhase : byte
    {
        None = 0,
        Windup = 1,
        Impact = 2,
        Recovery = 3,
    }
}
