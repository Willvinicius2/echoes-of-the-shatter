using System;
using System.Collections.Generic;

namespace Echoes.Interop
{
    /// <summary>
    /// PROVISÓRIO (stub). Recarga em série de cargas: o mínimo para os testes sem a DLL. A fonte da regra é o core
    /// (<c>shatter_potions_*</c>, <c>shatter_dodge_*</c>); isto só existe enquanto o stub existir.
    /// </summary>
    internal sealed class StubChargeTimer
    {
        const double Epsilon = 1e-9;
        double progress;

        public StubChargeTimer(int maxCharges, double rechargeSeconds)
        {
            MaxCharges = maxCharges;
            RechargeSeconds = rechargeSeconds;
            Charges = maxCharges;
        }

        public int MaxCharges { get; }
        public double RechargeSeconds { get; }
        public int Charges { get; private set; }
        public bool IsFull => Charges >= MaxCharges;
        public double RechargeFraction => IsFull || RechargeSeconds <= 0.0 ? 0.0 : Math.Min(1.0, progress / RechargeSeconds);
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

    /// <summary>PROVISÓRIO (stub). Cinto de poções mínimo; ver <see cref="IPotionBelt"/>.</summary>
    internal sealed class StubPotionBelt : IPotionBelt
    {
        readonly IReadOnlyList<PotionInfo> potions;
        readonly StubChargeTimer[] timers;
        readonly double lockoutSeconds;
        double lockout;

        public StubPotionBelt(IReadOnlyList<PotionInfo> potions, double lockoutSeconds)
        {
            this.potions = potions;
            this.lockoutSeconds = lockoutSeconds;
            timers = new StubChargeTimer[potions.Count];
            for (var i = 0; i < timers.Length; i++) timers[i] = new StubChargeTimer(potions[i].MaxCharges, potions[i].RechargeSeconds);
        }

        public int Count => timers.Length;

        public PotionBeltEntry GetEntry(int index)
        {
            if (index < 0 || index >= timers.Length) return default;
            var t = timers[index];
            return new PotionBeltEntry(t.Charges, t.MaxCharges, t.SecondsToNextCharge);
        }

        public double LockoutRemaining => lockout;

        public void Tick(double dt)
        {
            for (var i = 0; i < timers.Length; i++) timers[i].Tick(dt);
            lockout = Math.Max(0.0, lockout - dt);
        }

        public PotionUseStatus TryUse(int index, IStatBlock stats)
        {
            if (index < 0 || index >= timers.Length) return PotionUseStatus.Unknown;
            if (lockout > 1e-9) return PotionUseStatus.LockedOut;
            if (!timers[index].TryConsume()) return PotionUseStatus.NoCharges;
            lockout = lockoutSeconds;
            return PotionUseStatus.Ok;
        }

        public void Refill()
        {
            for (var i = 0; i < timers.Length; i++) timers[i].Refill();
            lockout = 0.0;
        }

        public bool OnEliteKilled()
        {
            StubChargeTimer best = null;
            var refill = 0;
            for (var i = 0; i < timers.Length; i++)
            {
                if (potions[i].EliteKillRefillCharges <= 0 || timers[i].IsFull) continue;
                if (best == null || timers[i].Charges < best.Charges)
                {
                    best = timers[i];
                    refill = potions[i].EliteKillRefillCharges;
                }
            }
            if (best == null) return false;
            best.AddCharges(refill);
            return true;
        }

        public void Dispose()
        {
        }
    }

    /// <summary>PROVISÓRIO (stub). Esquiva mínima; ver <see cref="IDodgeCharges"/>.</summary>
    internal sealed class StubDodge : IDodgeCharges
    {
        const double Epsilon = 1e-9;
        readonly CombatRules rules;
        StubChargeTimer charges;
        bool dodging;
        double elapsed;

        public StubDodge(CombatRules rules)
        {
            this.rules = rules;
            Reset();
        }

        public int Charges => charges.Charges;
        public int MaxCharges => charges.MaxCharges;
        public bool IsFull => charges.IsFull;
        public bool IsEmpty => charges.Charges <= 0;
        public bool IsDodging => dodging;
        public double Elapsed => elapsed;
        public double RechargeFraction => charges.RechargeFraction;
        public bool IsInvulnerable => dodging && elapsed + Epsilon < rules.DodgeInvulnerableSeconds;
        public double PerfectReward => IsInvulnerable ? rules.DodgePerfectResource : 0.0;

        public void Tick(double dt)
        {
            charges.Tick(dt);
            if (!dodging) return;
            elapsed += dt;
            if (elapsed + Epsilon >= rules.DodgeDurationSeconds) dodging = false;
        }

        public DodgeStartStatus TryStart(double resourceAvailable)
        {
            if (dodging) return DodgeStartStatus.Active;
            if (charges.Charges <= 0) return DodgeStartStatus.NoCharges;
            if (resourceAvailable + 1e-9 < rules.DodgeResourceCost) return DodgeStartStatus.NotEnoughResource;
            charges.TryConsume();
            dodging = true;
            elapsed = 0.0;
            return DodgeStartStatus.Ok;
        }

        public void Reset()
        {
            charges = new StubChargeTimer(rules.DodgeMaxCharges, rules.DodgeRechargeSeconds);
            dodging = false;
            elapsed = 0.0;
        }

        public void Dispose()
        {
        }
    }
}
