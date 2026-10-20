using System;

namespace Echoes.Interop
{
    public enum PotionUseStatus { Ok = 0, Unknown = 1, NoCharges = 2, LockedOut = 3 }

    /// <summary>Estado de uma poção no cinto (cargas, recarga em série): vem do core, o C# só lê.</summary>
    public readonly struct PotionBeltEntry
    {
        public readonly int Charges;
        public readonly int MaxCharges;
        /// <summary>Segundos até a próxima carga (0 se cheia).</summary>
        public readonly double RechargeRemaining;

        public PotionBeltEntry(int charges, int maxCharges, double rechargeRemaining)
        {
            Charges = charges;
            MaxCharges = maxCharges;
            RechargeRemaining = rechargeRemaining;
        }

        public bool IsFull => Charges >= MaxCharges;
        public bool IsEmpty => Charges <= 0;
    }

    /// <summary>
    /// Cinto de poções de um personagem (<c>shatter_potions</c>; docs/13 item 2, docs/04 seção 10.2): cargas, recarga em série,
    /// trava global e carga por elite. O C# só avança o tempo (passo fixo) e pede o uso; nenhuma conta de regra fica no cliente.
    /// A ordem das entradas é a do <c>potions.csv</c> (= <see cref="IRulesCore.Potions"/>).
    /// </summary>
    public interface IPotionBelt : IDisposable
    {
        int Count { get; }

        PotionBeltEntry GetEntry(int index);

        /// <summary>Trava global entre usos que ainda falta (s).</summary>
        double LockoutRemaining { get; }

        /// <summary>Avança a recarga e a trava (sempre o passo fixo).</summary>
        void Tick(double dt);

        /// <summary>
        /// Confere trava e cargas, gasta 1 carga e inicia a trava. O efeito (cura/barreira) é aplicado depois, ao fim do tempo de uso,
        /// por <see cref="IRulesCore.ResolvePotion"/>. Diferente de Ok: nada mudou.
        /// </summary>
        PotionUseStatus TryUse(int index, IStatBlock stats);

        /// <summary>Enche todas as cargas (Refúgio, checkpoint, reinício do Guardião).</summary>
        void Refill();

        /// <summary>Matar elite: +1 carga na poção refillOnEliteKill com menos cargas. false se estavam todas cheias.</summary>
        bool OnEliteKilled();
    }
}
