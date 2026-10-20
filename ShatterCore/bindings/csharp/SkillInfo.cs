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
        /// <summary>
        /// Raio em uu. Em habilidade de área é o raio da área; em PROJÉTIL é só a largura de colisão do corredor (a explosão no impacto é
        /// <see cref="ExplosionRadiusUu"/>, coluna <c>explosionRadius</c>). Não use este valor como raio de explosão.
        /// </summary>
        public double RadiusUu { get; internal set; }

        /// <summary>Raio da explosão no impacto de um projétil (coluna <c>explosionRadius</c>, docs/18 8.3 a); 0 = sem explosão (<see cref="SkillBehavior.Explodes"/>).</summary>
        public double ExplosionRadiusUu { get; internal set; }

        /// <summary>Empurrão em uu aplicado no alvo por golpe (coluna <c>knockback</c>); 0 = nenhum. Elites e chefes aplicam o fator deles no gameplay.</summary>
        public double KnockbackUu { get; internal set; }
        /// <summary>Abertura total do cone em graus (formas Cone e Melee).</summary>
        public double ConeAngleDegrees { get; internal set; }
        /// <summary>Velocidade do projétil em uu/s (forma Projectile).</summary>
        public double ProjectileSpeedUu { get; internal set; }
        public int Projectiles { get; internal set; } = 1;

        /// <summary>Valor de <see cref="Pierce"/> que atravessa todos os alvos (<c>shatter::kPierceAll</c>).</summary>
        public const int PierceAll = 99;

        /// <summary>
        /// Perfuração do projétil (coluna <c>pierce</c>, docs/18 8.2): 0 = nenhuma; N = atravessa N alvos além do primeiro;
        /// <see cref="PierceAll"/> = todos. Cada projétil acerta o mesmo alvo uma vez (RF-16); vários projéteis do mesmo leque
        /// podem acertar o mesmo alvo.
        /// </summary>
        public int Pierce { get; internal set; }

        /// <summary>Comportamento determinado pelos dados (explosão, leque, área, dash com tiro), classificado pelo core. Só o núcleo nativo preenche.</summary>
        public SkillBehavior Behavior { get; internal set; }
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
