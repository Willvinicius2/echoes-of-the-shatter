namespace Echoes.Interop
{
    /// <summary>Dados de classe (<c>shatter::ClassData</c>, classes.csv + class_stats.csv).</summary>
    public sealed class ClassInfo
    {
        public string Id { get; internal set; } = string.Empty;
        public string ResourceId { get; internal set; } = string.Empty;
        public string StartingSkill { get; internal set; } = string.Empty;
        /// <summary>Recurso ganho por golpe que acerta.</summary>
        public double ResourceOnHit { get; internal set; }
        /// <summary>Recurso ganho ao bloquear.</summary>
        public double ResourceOnBlock { get; internal set; }
        /// <summary>Recurso perdido por segundo fora de combate.</summary>
        public double ResourceDecayOutOfCombat { get; internal set; }
        public double RegenMultWhileMoving { get; internal set; } = 1.0;
        /// <summary>Velocidade base de movimento em uu/s (multiplicada pelo atributo MoveSpeed).</summary>
        public double MoveSpeedUu { get; internal set; }

        public string NameKey => Id + ".name";

        public override string ToString() => Id;
    }
}
