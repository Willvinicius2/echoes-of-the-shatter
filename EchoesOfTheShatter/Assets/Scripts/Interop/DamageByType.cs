using System;

namespace Echoes.Interop
{
    /// <summary>
    /// Dano separado por tipo (equivale a <c>DamageArray</c> do damage.h). Struct de 4 doubles,
    /// sem array gerenciado, para não alocar no caminho quente.
    /// </summary>
    public struct DamageByType
    {
        public double Physical;
        public double Fire;
        public double Cold;
        public double Lightning;

        public const int Count = 4;

        public double this[int index]
        {
            get
            {
                switch (index)
                {
                    case 0: return Physical;
                    case 1: return Fire;
                    case 2: return Cold;
                    case 3: return Lightning;
                    default: throw new ArgumentOutOfRangeException(nameof(index));
                }
            }
            set
            {
                switch (index)
                {
                    case 0: Physical = value; break;
                    case 1: Fire = value; break;
                    case 2: Cold = value; break;
                    case 3: Lightning = value; break;
                    default: throw new ArgumentOutOfRangeException(nameof(index));
                }
            }
        }

        public double this[DamageType type]
        {
            get => this[(int)type];
            set => this[(int)type] = value;
        }

        public double Total => Physical + Fire + Cold + Lightning;

        public bool IsZero => Physical == 0.0 && Fire == 0.0 && Cold == 0.0 && Lightning == 0.0;

        /// <summary>Tipo com a maior parcela (usado para a cor do número de dano).</summary>
        public DamageType Dominant
        {
            get
            {
                var best = DamageType.Physical;
                var bestValue = Physical;
                for (var i = 1; i < Count; i++)
                {
                    if (this[i] > bestValue)
                    {
                        bestValue = this[i];
                        best = (DamageType)i;
                    }
                }
                return best;
            }
        }
    }
}
