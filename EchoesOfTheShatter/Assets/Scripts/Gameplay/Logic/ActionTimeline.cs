using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Linha do tempo das 3 fases de uma ação, com os tempos que o motor de regras devolve
    /// (<see cref="ActionTiming"/>). O golpe acontece na fase de impacto do passo fixo
    /// (docs/04_arquitetura.md, seção 3.3: animação nunca causa dano). Sobra de tempo passa para a
    /// fase seguinte, então a duração total não depende do FPS.
    /// </summary>
    public sealed class ActionTimeline
    {
        const double Epsilon = 1e-9;

        public ActionPhase Phase { get; private set; }
        public double PhaseElapsed { get; private set; }
        public double TotalElapsed { get; private set; }
        public ActionTiming Timing { get; private set; }
        public bool IsActive => Phase != ActionPhase.None;

        public double PhaseDuration
        {
            get
            {
                switch (Phase)
                {
                    case ActionPhase.Windup: return Timing.Windup;
                    case ActionPhase.Impact: return Timing.Impact;
                    case ActionPhase.Recovery: return Timing.Recovery;
                    default: return 0.0;
                }
            }
        }

        /// <summary>Fração já passada da recuperação (0 fora dela).</summary>
        public double RecoveryFraction =>
            Phase == ActionPhase.Recovery && Timing.Recovery > 0.0 ? PhaseElapsed / Timing.Recovery : 0.0;

        public void Begin(in ActionTiming timing)
        {
            Timing = timing;
            Phase = ActionPhase.Windup;
            PhaseElapsed = 0.0;
            TotalElapsed = 0.0;
        }

        public void Cancel()
        {
            Phase = ActionPhase.None;
            PhaseElapsed = 0.0;
        }

        /// <summary>Avança <paramref name="dt"/>; fases de duração zero passam no mesmo avanço.</summary>
        public ActionTimelineEvents Tick(double dt)
        {
            var events = ActionTimelineEvents.None;
            if (Phase == ActionPhase.None) return events;
            TotalElapsed += dt;
            var remaining = dt;
            while (Phase != ActionPhase.None)
            {
                var left = PhaseDuration - PhaseElapsed;
                if (remaining + Epsilon < left)
                {
                    PhaseElapsed += remaining;
                    break;
                }
                remaining -= left > 0.0 ? left : 0.0;
                if (remaining < 0.0) remaining = 0.0;
                PhaseElapsed = 0.0;
                switch (Phase)
                {
                    case ActionPhase.Windup:
                        Phase = ActionPhase.Impact;
                        events |= ActionTimelineEvents.ImpactStarted;
                        break;
                    case ActionPhase.Impact:
                        Phase = ActionPhase.Recovery;
                        events |= ActionTimelineEvents.ImpactEnded;
                        break;
                    case ActionPhase.Recovery:
                        Phase = ActionPhase.None;
                        events |= ActionTimelineEvents.Finished;
                        break;
                }
            }
            return events;
        }
    }
}
