using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary>Uma poção do herói (tecla própria, cargas com recarga em série; docs/13, item 2).</summary>
    public sealed class PotionSlot
    {
        public PotionSlot(PotionInfo potion)
        {
            Potion = potion;
            Charges = new ChargeTimer(potion.MaxCharges, potion.RechargeSeconds);
        }

        public PotionInfo Potion { get; }
        public ChargeTimer Charges { get; }
    }
}
