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

        /// <summary>
        /// Tag de EFEITO de defesa (<c>effect.guarding.*</c>, docs/18 8.1): os modificadores de dano recebido de um efeito com esta
        /// tag só valem num golpe que veio de dentro do arco da defesa (<see cref="HitRequest.FromGuardArc"/>). Não é tag de habilidade.
        /// </summary>
        Guard = 1u << 9,
    }
}
