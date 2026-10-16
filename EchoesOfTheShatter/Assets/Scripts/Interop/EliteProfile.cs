using Echoes.Interop.Native;

namespace Echoes.Interop
{
    /// <summary>
    /// Multiplicadores finais de um elite (base de rules.csv x modificador), de <c>shatter_elite_roll</c> (sorteado no fluxo de
    /// eventos) ou <c>shatter_elite_profile</c> (elite fixo). O C# só guarda e entrega ao core (<see cref="IRulesCore.ApplyElite"/>).
    /// </summary>
    public readonly struct EliteProfile
    {
        public readonly double LifeMult, DamageMult, XpMult, BarrierFractionOfLife, MoveSpeedMult, AttackSpeedMult, RecoveryMult;
        public readonly double DeathExplosionRadius, DeathExplosionDamage, DeathExplosionFuse;
        public readonly string ModifierId;
        /// <summary>true = elite sorteado (imune ao stun).</summary>
        public readonly bool Rolled;
        internal readonly ShatterEliteInfo Raw;

        internal EliteProfile(in ShatterEliteInfo raw, string modifierId)
        {
            Raw = raw;
            LifeMult = raw.life_mult;
            DamageMult = raw.damage_mult;
            XpMult = raw.xp_mult;
            BarrierFractionOfLife = raw.barrier_fraction_of_life;
            MoveSpeedMult = raw.move_speed_mult;
            AttackSpeedMult = raw.attack_speed_mult;
            RecoveryMult = raw.recovery_mult;
            DeathExplosionRadius = raw.death_explosion_radius;
            DeathExplosionDamage = raw.death_explosion_damage;
            DeathExplosionFuse = raw.death_explosion_fuse;
            ModifierId = modifierId ?? string.Empty;
            Rolled = raw.rolled != 0;
        }

        public bool IsNone => string.IsNullOrEmpty(ModifierId) && !Rolled;
    }
}
