namespace Echoes.Interop
{
    /// <summary>
    /// Forma espacial da habilidade (<c>shatter::SkillShape</c>, content.h). O gameplay escolhe
    /// o comportamento de consulta no plano XZ por este valor.
    /// </summary>
    public enum SkillShape : byte
    {
        Melee = 0,
        Cone = 1,
        Projectile = 2,
        Area = 3,
        Dash = 4,
        Self = 5,
        Channel = 6,
        Trap = 7,
    }
}
