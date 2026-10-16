using System;
using System.Collections.Generic;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Números de "juice" que mexem em tempo de entidade (hitstop) ou posição (knockback). São dados
    /// de apresentação (docs/03_design_system.md, seção 6; tokens <c>juice</c>), não de balanceamento:
    /// vêm do ScriptableObject <see cref="CombatFeelSettings"/>.
    /// </summary>
    public sealed class CombatFeelValues
    {
        public double HitstopHeavySeconds;
        public double HitstopCriticalSeconds;
        public double HitstopBossHeavySeconds;
        public double HitstopPlayerHitSeconds;
        public float KnockbackCommonMeters;
        public float KnockbackEliteMeters;
        public float KnockbackBossMeters;
        public float KnockbackSeconds;
        public readonly HashSet<string> HeavySkills = new HashSet<string>(StringComparer.Ordinal);

        public bool IsHeavy(string skillId) => skillId != null && HeavySkills.Contains(skillId);

        /// <summary>Hitstop de um golpe que acertou (0 = golpe leve, sem hitstop).</summary>
        public double HitstopFor(bool critical, bool heavy, bool attackerIsBoss, bool targetIsHero)
        {
            var seconds = 0.0;
            if (critical) seconds = Math.Max(seconds, HitstopCriticalSeconds);
            if (heavy) seconds = Math.Max(seconds, attackerIsBoss ? HitstopBossHeavySeconds : HitstopHeavySeconds);
            if (targetIsHero) seconds = Math.Max(seconds, HitstopPlayerHitSeconds);
            return seconds;
        }

        public float KnockbackFor(Combatant target)
        {
            if (target.IsBoss) return KnockbackBossMeters;
            if (target.IsElite) return KnockbackEliteMeters;
            return KnockbackCommonMeters;
        }
    }
}
