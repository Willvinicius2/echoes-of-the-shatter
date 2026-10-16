namespace Echoes.Interop
{
    /// <summary>
    /// Poção (tabela <c>potions.csv</c> pedida em docs/13, item 2). Enquanto a tabela não existe,
    /// o stub preenche com os valores provisórios do documento.
    /// </summary>
    public sealed class PotionInfo
    {
        public string Id { get; internal set; } = string.Empty;
        public PotionKind Kind { get; internal set; }
        public double FractionOfMaxLife { get; internal set; }
        /// <summary>Duração da barreira em segundos (só <see cref="PotionKind.Barrier"/>).</summary>
        public double Duration { get; internal set; }
        public int MaxCharges { get; internal set; }
        public double RechargeSeconds { get; internal set; }
        public double UseTime { get; internal set; }
        public double MoveSpeedWhileUsing { get; internal set; } = 1.0;
        /// <summary>Cargas devolvidas ao matar uma elite (docs/13, item 2: +1 na poção com menos cargas; 0 = não enche).</summary>
        public int EliteKillRefillCharges { get; internal set; }
        /// <summary>1 = tecla Potion1, 2 = tecla Potion2.</summary>
        public int HotkeySlot { get; internal set; }

        public string NameKey => Id + ".name";

        public override string ToString() => Id;
    }
}
