namespace Echoes.Gameplay
{
    /// <summary>
    /// Esquiva (RF-15; docs/13, item 1): cargas com recarga em série, duração fixa e invulnerabilidade
    /// de 0 (inclusive) até <see cref="InvulnerableSeconds"/> (exclusive). Tempos vêm do motor de regras.
    /// </summary>
    public sealed class DodgeLogic
    {
        const double Epsilon = 1e-9;

        public DodgeLogic(int maxCharges, double rechargeSeconds, double durationSeconds, double invulnerableSeconds)
        {
            Charges = new ChargeTimer(maxCharges, rechargeSeconds);
            DurationSeconds = durationSeconds;
            InvulnerableSeconds = invulnerableSeconds;
        }

        public ChargeTimer Charges { get; }
        public double DurationSeconds { get; }
        public double InvulnerableSeconds { get; }
        public bool IsDodging { get; private set; }
        public double Elapsed { get; private set; }

        /// <summary>Recurso da esquiva perfeita já concedido nesta esquiva (no máximo 1 vez).</summary>
        public bool PerfectGranted { get; set; }

        public bool IsInvulnerable => IsDodging && Elapsed + Epsilon < InvulnerableSeconds;

        /// <summary>Gasta 1 carga e começa. Nega sem carga ou se já está esquivando.</summary>
        public bool TryStart()
        {
            if (IsDodging) return false;
            if (!Charges.TryConsume()) return false;
            IsDodging = true;
            Elapsed = 0.0;
            PerfectGranted = false;
            return true;
        }

        public void Tick(double dt)
        {
            Charges.Tick(dt);
            if (!IsDodging) return;
            Elapsed += dt;
            if (Elapsed + Epsilon >= DurationSeconds) IsDodging = false;
        }

        public void Stop()
        {
            IsDodging = false;
            Elapsed = 0.0;
        }

        public void Refill()
        {
            Stop();
            Charges.Refill();
        }
    }
}
