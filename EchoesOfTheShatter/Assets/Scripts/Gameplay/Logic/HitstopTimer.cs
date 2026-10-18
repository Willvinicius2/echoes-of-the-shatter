using System;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Hitstop de UMA entidade (RF-17; docs/tecnico/04_arquitetura.md, seções 3.3 e 6.2). Enquanto ativo, a
    /// entidade não avança timers no passo fixo e a apresentação congela o Animator dela.
    /// Nunca congela o jogo todo (sem Time.timeScale).
    /// </summary>
    public sealed class HitstopTimer
    {
        const double Epsilon = 1e-9;

        public double Remaining { get; private set; }
        public bool IsActive => Remaining > Epsilon;

        /// <summary>Liga por <paramref name="seconds"/>; se já estiver ativo, fica o maior.</summary>
        public void Trigger(double seconds)
        {
            if (seconds > Remaining) Remaining = seconds;
        }

        public void Tick(double dt)
        {
            Remaining = Math.Max(0.0, Remaining - dt);
        }

        public void Clear()
        {
            Remaining = 0.0;
        }
    }
}
