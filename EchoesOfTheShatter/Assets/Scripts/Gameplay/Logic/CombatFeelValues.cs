using System;
using System.Collections.Generic;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Números de "juice" que mexem em tempo de entidade (hitstop) ou posição (knockback). São dados
    /// de apresentação (docs/arte/03_design_system.md, seção 6; tokens <c>juice</c>), não de balanceamento:
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
        /// <summary>Inimigos (rev5, só apresentação e agente de navegação, nada de regra): segundos de 0 à velocidade de perseguição e de volta a 0.</summary>
        public float EnemyAccelSeconds = 0.15f;
        public float EnemyDecelSeconds = 0.12f;
        /// <summary>Virada do corpo do inimigo em graus/s: calma ao perseguir e mais firme no telégrafo e no golpe (o chefe segue a direção exata do core).</summary>
        public float EnemyTurnDegreesPerSecond = 540f;
        public float EnemyAttackTurnDegreesPerSecond = 900f;
        /// <summary>Perseguição em grupo (rev6): cada inimigo mira num ponto do anel de alcance em volta do herói (fração do alcance do golpe), numa vaga fixa
        /// de até ±EnemySurroundSpreadDegrees em relação ao lado de onde veio, e o grupo se espalha em vez de enfileirar. 0 graus = mira o herói.</summary>
        public float EnemyApproachFraction = 0.9f;
        public float EnemySurroundSpreadDegrees = 70f;
        /// <summary>Prioridade de evasão do agente: base e variação por inimigo (quem cede passa por quem tem número menor).</summary>
        public int EnemyAvoidancePriorityBase = 40;
        public int EnemyAvoidancePrioritySpread = 20;
        /// <summary>Raio de evasão do agente (m; o chefe usa o próprio). Com o raio do corpo (0,5), o inimigo freava de 2,2 para 0,5 m/s a 3 m do herói por causa
        /// dos vizinhos; com 0,3 ele chega ao alcance do golpe sem desacelerar (medido, rev6). É só o raio de desvio, o corpo da lógica não muda.</summary>
        public float EnemyAvoidanceRadiusMeters = 0.3f;
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
