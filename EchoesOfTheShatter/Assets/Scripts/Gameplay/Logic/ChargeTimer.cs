using System;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Cargas com recarga EM SÉRIE: um relógio só, uma carga por vez (esquiva e poções;
    /// docs/13_design_pendencias.md, itens 1 e 2). Os números vêm do motor de regras.
    /// </summary>
    public sealed class ChargeTimer
    {
        const double Epsilon = 1e-9;
        double progress;

        public ChargeTimer(int maxCharges, double rechargeSeconds)
        {
            if (maxCharges < 0) throw new ArgumentOutOfRangeException(nameof(maxCharges));
            MaxCharges = maxCharges;
            RechargeSeconds = rechargeSeconds;
            Charges = maxCharges;
        }

        public int MaxCharges { get; }
        public double RechargeSeconds { get; }
        public int Charges { get; private set; }
        public bool IsFull => Charges >= MaxCharges;
        public bool IsEmpty => Charges <= 0;

        /// <summary>Progresso da carga que está recarregando (0 a 1); 0 quando cheio.</summary>
        public double RechargeFraction => IsFull || RechargeSeconds <= 0.0 ? 0.0 : Math.Min(1.0, progress / RechargeSeconds);

        /// <summary>Segundos até a próxima carga voltar; 0 quando cheio.</summary>
        public double SecondsToNextCharge => IsFull ? 0.0 : Math.Max(0.0, RechargeSeconds - progress);

        public bool TryConsume()
        {
            if (Charges <= 0) return false;
            Charges--;
            return true;
        }

        public void Tick(double dt)
        {
            if (IsFull)
            {
                progress = 0.0;
                return;
            }
            if (RechargeSeconds <= 0.0)
            {
                Charges = MaxCharges;
                progress = 0.0;
                return;
            }
            progress += dt;
            while (!IsFull && progress + Epsilon >= RechargeSeconds)
            {
                progress -= RechargeSeconds;
                Charges++;
            }
            if (progress < 0.0 || IsFull) progress = 0.0;
        }

        public void AddCharges(int count)
        {
            if (count <= 0) return;
            Charges = Math.Min(MaxCharges, Charges + count);
            if (IsFull) progress = 0.0;
        }

        public void Refill()
        {
            Charges = MaxCharges;
            progress = 0.0;
        }
    }
}
