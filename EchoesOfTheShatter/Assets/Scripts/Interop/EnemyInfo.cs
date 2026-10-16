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

        /// <summary>Fração da velocidade de perseguição usada na patrulha, em (0,1] (<c>patrolSpeedMult</c> do enemies.csv, lida pelo core).</summary>
        public double PatrolSpeedMult { get; internal set; } = 1.0;

        /// <summary>R-VIS-1: o atirador só mira dentro da área visível menos a margem (<c>requireOnScreen</c> do enemy_ai.csv, lida pelo core).</summary>
        public bool RequireOnScreen { get; internal set; }

        /// <summary>Elite fixo: modificador de <c>elite_modifiers.csv</c> aplicado sempre (vazio = nenhum). Coluna <c>modifierId</c> do enemies.csv.</summary>
        public string ModifierId { get; internal set; } = string.Empty;

        /// <summary>Tabela de loot do elite (coluna opcional <c>eliteLootTableId</c>); vazio = a do inimigo.</summary>
        public string EliteLootTableId { get; internal set; } = string.Empty;
        public IReadOnlyList<EnemyAttackInfo> Attacks { get; internal set; } = NoAttacks;

        public string NameKey => Id + ".name";

        public override string ToString() => Id;
    }
}
