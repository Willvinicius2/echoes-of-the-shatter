using System;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Acumulador explícito do passo fixo do combate (RF-11; docs/tecnico/04_arquitetura.md, seção 6.2).
    /// Converte o tempo real de cada quadro em N passos de tamanho fixo, com teto de passos por quadro
    /// para não entrar em espiral quando um quadro demora demais (o excesso é descartado e contado).
    /// </summary>
    public sealed class FixedStepAccumulator
    {
        const double Epsilon = 1e-9;
        double accumulated;

        public FixedStepAccumulator(double step, int maxStepsPerFrame)
        {
            if (step <= 0.0) throw new ArgumentOutOfRangeException(nameof(step));
            if (maxStepsPerFrame < 1) throw new ArgumentOutOfRangeException(nameof(maxStepsPerFrame));
            Step = step;
            MaxStepsPerFrame = maxStepsPerFrame;
        }

        public double Step { get; }
        public int MaxStepsPerFrame { get; }
        public long TotalSteps { get; private set; }
        /// <summary>Tempo real descartado pelo teto de passos (quadros muito longos, depurador).</summary>
        public double DroppedSeconds { get; private set; }

        /// <summary>Fração do próximo passo já acumulada (0 a 1), para interpolar o visual.</summary>
        public double Alpha => accumulated / Step;

        /// <summary>Soma o tempo do quadro e devolve quantos passos fixos executar agora.</summary>
        public int Advance(double deltaTime)
        {
            if (deltaTime > 0.0 && !double.IsNaN(deltaTime) && !double.IsInfinity(deltaTime)) accumulated += deltaTime;

            var steps = 0;
            while (accumulated + Epsilon >= Step && steps < MaxStepsPerFrame)
            {
                accumulated -= Step;
                steps++;
            }
            if (accumulated < 0.0) accumulated = 0.0;

            if (steps == MaxStepsPerFrame && accumulated + Epsilon >= Step)
            {
                var whole = Math.Floor((accumulated + Epsilon) / Step);
                DroppedSeconds += whole * Step;
                accumulated -= whole * Step;
                if (accumulated < 0.0) accumulated = 0.0;
            }

            TotalSteps += steps;
            return steps;
        }

        public void Reset()
        {
            accumulated = 0.0;
            TotalSteps = 0;
            DroppedSeconds = 0.0;
        }
    }
}
