namespace Echoes.Interop
{
    /// <summary>
    /// Constantes de regra que o combate em tempo real lê (subconjunto de <c>RulesConstants</c>,
    /// constants.h, mais as chaves novas pedidas em docs/13). Valores sempre vindos do motor de
    /// regras (rules.csv); o C# nunca tem um padrão próprio.
    /// </summary>
    public sealed class CombatRules
    {
        /// <summary>Passo fixo do combate em segundos (<c>realtime_step</c>).</summary>
        public double FixedStep { get; internal set; }
        public double MinCooldown { get; internal set; }

        public int DodgeMaxCharges { get; internal set; }
        /// <summary>Segundos para recarregar UMA carga (recarga em série).</summary>
        public double DodgeRechargeSeconds { get; internal set; }
        public double DodgeDurationSeconds { get; internal set; }
        /// <summary>Invulnerável de 0 (inclusive) até este tempo (exclusive) desde o início da esquiva.</summary>
        public double DodgeInvulnerableSeconds { get; internal set; }
        public double DodgeDistanceUu { get; internal set; }
        public double DodgeResourceCost { get; internal set; }
        public double DodgePerfectResource { get; internal set; }
        /// <summary>Janela do buffer de entrada (ação pedida antes de a atual terminar).</summary>
        public double InputBufferSeconds { get; internal set; }
        /// <summary>Fração da recuperação a partir da qual a esquiva cancela a ação (0,5 = metade final).</summary>
        public double DodgeCancelRecoveryFraction { get; internal set; }

        /// <summary>Segundos sem dar nem levar golpe para contar como "fora de combate" (RF-14).</summary>
        public double OutOfCombatSeconds { get; internal set; }
        /// <summary>R-VIS-1 (docs/14 8.2): margem interna (uu) da área visível do atirador (<c>require_on_screen_margin</c>, rules.csv).</summary>
        public double RequireOnScreenMarginUu { get; internal set; }

        /// <summary>Dano físico base sem arma (<c>unarmed_weapon_damage_physical</c>); o golpe desarmado vem do core.</summary>
        public double UnarmedWeaponDamagePhysical { get; internal set; }

        /// <summary>Trava global entre usos de poção.</summary>
        public double PotionLockoutSeconds { get; internal set; }

        // --- Combate básico (docs/18 1.2, API C 1.5): as máquinas de combo, carga e defesa rodam no C#; os números vêm do rules.csv. ---

        /// <summary><c>combo_window</c>: segundos depois do fim da recuperação de um golpe em que um clique ainda continua o combo.</summary>
        public double ComboWindowSeconds { get; internal set; }

        /// <summary><c>combo_window_after_dodge</c>: janela que reabre ao fim da esquiva.</summary>
        public double ComboWindowAfterDodgeSeconds { get; internal set; }

        /// <summary><c>attack_buffer</c>: um clique nos últimos segundos da recuperação (ou depois) entra na fila.</summary>
        public double AttackBufferSeconds { get; internal set; }

        /// <summary><c>heavy_hold_threshold</c>: botão apertado por mais que isto vira ataque forte carregado.</summary>
        public double HeavyHoldThresholdSeconds { get; internal set; }

        /// <summary><c>light_windup_credit_max</c>: fração máxima (0 a 1) da preparação do golpe leve descontada pelo tempo apertado.</summary>
        public double LightWindupCreditMax { get; internal set; }

        /// <summary><c>guard_lower_time</c>: segundos sem atacar depois de soltar a defesa.</summary>
        public double GuardLowerTimeSeconds { get; internal set; }

        /// <summary><c>dash_shot_range</c>: alcance em uu do tiro de uma habilidade dash com tag projétil (Salto do Arqueiro).</summary>
        public double DashShotRangeUu { get; internal set; }

        // --- Movimento do herói (API C 1.7): rampa de aceleração e desaceleração. O core guarda e valida (0 a 0,5 s); o C# aplica. ---

        /// <summary><c>hero_move_accel_seconds</c>: segundos de 0 até a velocidade máxima (0 = instantâneo). Rampa linear: velocidade += max x dt / este tempo.</summary>
        public double HeroMoveAccelSeconds { get; internal set; }

        /// <summary><c>hero_move_decel_seconds</c>: segundos da velocidade máxima até 0 (0 = para na hora).</summary>
        public double HeroMoveDecelSeconds { get; internal set; }
    }
}
