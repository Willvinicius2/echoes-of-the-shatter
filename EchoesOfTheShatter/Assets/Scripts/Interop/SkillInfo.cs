using System;
using System.Collections.Generic;

namespace Echoes.Interop
{
    /// <summary>
    /// Dados de uma habilidade lidos pelo motor de regras (<c>shatter::SkillData</c>, content.h,
    /// tabela skills.csv). Somente leitura fora do Interop. Distâncias em uu (1 uu = 1 cm),
    /// como no CSV; o gameplay converte para metros.
    /// </summary>
    public sealed class SkillInfo
    {
        static readonly string[] NoEffects = Array.Empty<string>();

        public string Id { get; internal set; } = string.Empty;
        public string ClassId { get; internal set; } = string.Empty;
        public SkillTags Tags { get; internal set; }
        public SkillShape Shape { get; internal set; }
        public bool ScalesWithWeapon { get; internal set; }
        public DamageByType BaseDamage { get; internal set; }
        public double CoefficientRank1 { get; internal set; } = 1.0;
        public double CoefficientRank2 { get; internal set; } = 1.0;
        public double CoefficientRank3 { get; internal set; } = 1.0;
        public double Cost { get; internal set; }
        public double Cooldown { get; internal set; }
        public double Windup { get; internal set; }
        public double Impact { get; internal set; }
        public double Recovery { get; internal set; }
        public double RangeUu { get; internal set; }
        public double RadiusUu { get; internal set; }
        /// <summary>Abertura total do cone em graus (formas Cone e Melee).</summary>
        public double ConeAngleDegrees { get; internal set; }
        /// <summary>Velocidade do projétil em uu/s (forma Projectile).</summary>
        public double ProjectileSpeedUu { get; internal set; }
        public int Projectiles { get; internal set; } = 1;
        public IReadOnlyList<string> OnHitEffects { get; internal set; } = NoEffects;
        public IReadOnlyList<string> SelfEffects { get; internal set; } = NoEffects;
        public int UnlockLevel { get; internal set; } = 1;

        /// <summary>Chave de localização do nome (convenção <c>&lt;id&gt;.name</c> do Loc/content.csv).</summary>
        public string NameKey => Id + ".name";

        /// <summary>Chave de localização da descrição.</summary>
        public string DescriptionKey => Id + ".desc";

        public double Coefficient(int rank)
        {
            switch (rank)
            {
                case 2: return CoefficientRank2;
                case 3: return CoefficientRank3;
                default: return CoefficientRank1;
            }
        }

        public override string ToString() => Id;
    }
}
