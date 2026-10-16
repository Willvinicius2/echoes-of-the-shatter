namespace Echoes.UI
{
    /// <summary>Estilo do número de dano (docs/03_design_system.md, seção 4.1).</summary>
    public enum DamageNumberKind : byte
    {
        Normal = 0,
        Critical = 1,
        Taken = 2,
        Heal = 3,
        Muted = 4,
    }
}
