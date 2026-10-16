using System;
using System.Collections.Generic;

namespace Echoes.Interop
{
    /// <summary>Dados de inimigo (<c>shatter::EnemyData</c>, enemies.csv + enemy_attacks.csv).</summary>
    public sealed class EnemyInfo
    {
        static readonly EnemyAttackInfo[] NoAttacks = Array.Empty<EnemyAttackInfo>();

        public string Id { get; internal set; } = string.Empty;
        public string FamilyId { get; internal set; } = string.Empty;
        public bool IsBoss { get; internal set; }
        public bool IsElite { get; internal set; }
        public double MoveSpeedUu { get; internal set; }
        public double AggroRangeUu { get; internal set; }
        /// <summary>Giro máximo em graus por segundo (docs/13, item 4.2).</summary>
        public double TurnRateDegreesPerSecond { get; internal set; }
        public double XpBase { get; internal set; }
        public double XpPerLevel { get; internal set; }
        public string LootTableId { get; internal set; } = string.Empty;
        public IReadOnlyList<EnemyAttackInfo> Attacks { get; internal set; } = NoAttacks;

        public string NameKey => Id + ".name";

        public override string ToString() => Id;
    }
}
