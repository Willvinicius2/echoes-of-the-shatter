using System;

namespace Echoes.Gameplay
{
    /// <summary>Recarga simples de habilidade ou trava (duração vinda do motor de regras).</summary>
    public sealed class CooldownTimer
    {
        const double Epsilon = 1e-9;

        public double Duration { get; private set; }
        public double Remaining { get; private set; }
        public bool IsReady => Remaining <= Epsilon;

        /// <summary>Fração restante (1 = acabou de começar, 0 = pronta).</summary>
        public double FractionRemaining => Duration > 0.0 ? Math.Min(1.0, Remaining / Duration) : 0.0;

        public void Start(double duration)
        {
            Duration = Math.Max(0.0, duration);
            Remaining = Duration;
        }

        public void Tick(double dt)
        {
            if (Remaining <= 0.0) return;
            Remaining = Math.Max(0.0, Remaining - dt);
        }

        public void Reset()
        {
            Remaining = 0.0;
        }
    }
}
