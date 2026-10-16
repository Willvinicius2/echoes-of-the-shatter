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
        /// <summary>Trava global entre usos de poção.</summary>
        public double PotionLockoutSeconds { get; internal set; }
    }
}
