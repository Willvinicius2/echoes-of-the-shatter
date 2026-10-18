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
        /// <summary>Velocidade de virada do corpo do herói em graus/s (andando, sem ação).</summary>
        public float TurnDegreesPerSecond = 900f;
        /// <summary>Velocidade de virada ao iniciar um golpe ou magia (mais rápida, para o corpo encarar a mira).</summary>
        public float CastTurnDegreesPerSecond = 1200f;
        /// <summary>Defendendo ou carregando (sem golpe nem esquiva): o corpo acompanha a mira sem estalar, porque ali não há pressa.</summary>
        public float AimTurnDegreesPerSecond = 720f;
        /// <summary>Hitstop leve (s) de golpes que não são pesados mas merecem um tranco no acerto (ex.: a explosão da Bola de Fogo).</summary>
        public double HitstopLightSeconds = 0.035;
        public readonly HashSet<string> LightHitstopSkills = new HashSet<string>(StringComparer.Ordinal);
        public readonly HashSet<string> HeavySkills = new HashSet<string>(StringComparer.Ordinal);

        /// <summary>Hitstop leve da habilidade (0 = nenhum).</summary>
        public double LightHitstopFor(string skillId) => skillId != null && LightHitstopSkills.Contains(skillId) ? HitstopLightSeconds : 0.0;

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

        /// <summary>
        /// Empurrão de um golpe (docs/18, 2.1): o <c>knockback</c> da habilidade, na proporção do tipo de alvo (comum inteiro; elite e chefe na razão dos
        /// tokens de juice: 6/20 e 0). Habilidade sem empurrão próprio usa o do token do alvo.
        /// </summary>
        public float KnockbackFor(Combatant target, float skillKnockbackMeters)
        {
            if (skillKnockbackMeters <= 0f) return KnockbackFor(target);
            if (target.IsBoss) return skillKnockbackMeters * (KnockbackCommonMeters > 0f ? KnockbackBossMeters / KnockbackCommonMeters : 0f);
            if (target.IsElite) return skillKnockbackMeters * (KnockbackCommonMeters > 0f ? KnockbackEliteMeters / KnockbackCommonMeters : 0f);
            return skillKnockbackMeters;
        }

        public float KnockbackFor(Combatant target)
        {
            if (target.IsBoss) return KnockbackBossMeters;
            if (target.IsElite) return KnockbackEliteMeters;
            return KnockbackCommonMeters;
        }
    }
}
