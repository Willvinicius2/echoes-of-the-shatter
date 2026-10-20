using System;
using System.Collections.Generic;

namespace Echoes.Interop
{
    public enum BossEventKind
    {
        PatternStart = 0, PatternImpact, PatternEnd, PatternInterrupted, PhaseStart, SummonMarker, SummonSpawn, PhaseEnd,
        StaggerStart, StaggerEnd, ShieldDown, ShieldUp, Died,
    }

    /// <summary>Evento do passo do chefe. <see cref="Seconds"/>: telegraph (PatternStart), impacto, rugido (PhaseStart), tempo até as invocadas (SummonMarker), duração do stagger/escudo caído.</summary>
    public struct BossEvent
    {
        public BossEventKind Kind;
        public double Seconds;
        public int Phase;
        public int Count;
        public string PatternId;
        public string SkillId;
        public string EnemyId;
    }

    public enum BossState { Idle = 0, Waiting, Telegraph, Impact, Recovery, Stagger, Transition, Dead }

    public struct BossInfo
    {
        public double Life, MaxLife, ShieldDownRemaining, TurnRateDegPerSec, FacingX, FacingZ, StaggerRemaining, StunRemaining;
        public int Phase;
        public BossState State;
        public bool ShieldUp, Invulnerable;
    }

    public struct BossDamageResult
    {
        public double Applied, LifeAfter;
        /// <summary>Escudo frontal: 0 de dano, sem Ímpeto, sem knockback.</summary>
        public bool ShieldBlocked;
        /// <summary>Rugido da transição de fase.</summary>
        public bool Invulnerable;
        public bool ClampedByPhase, Killed;
    }

    /// <summary>
    /// Máquina de fases do chefe (<c>shatter_boss</c>; docs/13 itens 4 e 6): escudo frontal por ângulo, fases por limiar de vida, rugido,
    /// invocação, padrões por seed, Guarda Quebrada. O C# entrega posições e o passo fixo e reage aos eventos (telegraph, impacto, invocados).
    /// </summary>
    public interface IBossController : IDisposable
    {
        BossInfo Info { get; }

        void Start();

        /// <summary>Reinício total (morte do jogador); <paramref name="statsOrNull"/> perde o bônus de dano do stagger.</summary>
        void Reset(IStatBlock statsOrNull);

        /// <summary>Passo fixo; acrescenta os eventos do passo em <paramref name="events"/>.</summary>
        void Step(double dt, double bossX, double bossZ, double playerX, double playerZ, IStatBlock stats, List<BossEvent> events);

        /// <summary>Dano já calculado por <see cref="IRulesCore.ResolveHit"/>: aplica escudo frontal, rugido e limiar de fase.</summary>
        BossDamageResult ApplyDamage(double amount, double bossX, double bossZ, double originX, double originZ);

        bool ShieldCovers(double bossX, double bossZ, double originX, double originZ);

        /// <summary>
        /// A investida bateu em pilar ou parede (<c>shatter_boss_wall_hit</c>): com <c>wallStaggerSeconds</c> na habilidade o chefe entra em
        /// stagger, o padrão é interrompido e o escudo cai. false se nada mudou (fora do impacto, sem tempo de stagger, já em stagger).
        /// </summary>
        bool WallHit(IStatBlock stats);
    }
}
