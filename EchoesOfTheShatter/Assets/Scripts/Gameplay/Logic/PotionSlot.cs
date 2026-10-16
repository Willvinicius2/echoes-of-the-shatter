using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Uma poção do herói: os dados de conteúdo (<see cref="Potion"/>) e o estado vindo do cinto do core
    /// (<see cref="IPotionBelt"/>: cargas, recarga em série). O C# só lê; nada de contagem de carga aqui.
    /// </summary>
    public sealed class PotionSlot
    {
        readonly IPotionBelt belt;
        readonly int index;

        public PotionSlot(PotionInfo potion, IPotionBelt belt, int index)
        {
            Potion = potion;
            this.belt = belt;
            this.index = index;
        }

        public PotionInfo Potion { get; }
        public PotionBeltEntry Entry => belt.GetEntry(index);
        public int Charges => Entry.Charges;
        public int MaxCharges => Entry.MaxCharges;
        public bool IsFull => Entry.IsFull;
        public bool IsEmpty => Entry.IsEmpty;

        /// <summary>0 a 1: quanto da próxima carga já recarregou (0 se cheia).</summary>
        public double RechargeFraction
        {
            get
            {
                var e = Entry;
                if (e.IsFull || Potion.RechargeSeconds <= 0.0) return 0.0;
                var f = 1.0 - e.RechargeRemaining / Potion.RechargeSeconds;
                return f < 0.0 ? 0.0 : f > 1.0 ? 1.0 : f;
            }
        }

        public double SecondsToNextCharge => Entry.RechargeRemaining;
    }
}
