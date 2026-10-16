using System;

namespace Echoes.Interop
{
    /// <summary>Tags de habilidade e de modificador. Mesmos bits de <c>shatter::Tag</c> (types.h).</summary>
    [Flags]
    public enum SkillTags : uint
    {
        None = 0,
        Attack = 1u << 0,
        Spell = 1u << 1,
        Melee = 1u << 2,
        Projectile = 1u << 3,
        Area = 1u << 4,
        Fire = 1u << 5,
        Cold = 1u << 6,
        Lightning = 1u << 7,
        Physical = 1u << 8,
    }
}
