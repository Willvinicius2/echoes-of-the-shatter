using System;
using System.Collections.Generic;

namespace Echoes.Interop
{
    /// <summary>
    /// PROVISÓRIO (stub). Valores que o design já decidiu mas que AINDA NÃO ESTÃO nos CSV
    /// (pedidos ao Data Engineer em docs/design/13_design_pendencias.md). Regra: o CSV sempre vence; estes
    /// números só preenchem chave ou coluna ausente, e cada uso é registrado em
    /// <see cref="StubRulesCore.LoadWarnings"/> para aparecer no log.
    ///
    /// Este é o único arquivo do C# com números de balanceamento, e existe só porque os dados
    /// ainda não chegaram. Quando as chaves entrarem em rules.csv, potions.csv, skills.csv,
    /// enemies.csv e class_stats.csv, apague as entradas daqui (e o arquivo, com a DLL).
    /// </summary>
    internal static class StubPendingRules
    {
        /// <summary>Chaves novas de rules.csv (docs/13, "Para o Data Engineer", item 1).</summary>
        public static readonly IReadOnlyDictionary<string, double> RuleKeys = new Dictionary<string, double>(StringComparer.Ordinal)
        {
            { "dodge_max_charges", 3 },          // docs/13 item 1 (plano, seção 5)
            { "dodge_recharge", 1.5 },           // docs/13 item 1
            { "dodge_duration", 0.35 },          // docs/13 item 1
            { "dodge_iframes", 0.2 },            // docs/13 item 1
            { "dodge_distance", 400 },           // docs/13 item 1 [HIPÓTESE]
            { "dodge_cost_resource", 0 },        // docs/13 item 1
            { "dodge_buffer", 0.15 },             // docs/13 item 1 [HIPÓTESE]
            { "dodge_perfect_resource", 10 },    // docs/13 item 1 [HIPÓTESE]
            { "dodge_cancel_recovery_fraction", 0.35 }, // docs/13 item 1: "metade final da recuperação" [HIPÓTESE]
            { "potion_lockout", 1.0 },           // docs/13 item 2
            { "out_of_combat_seconds", 3.0 },    // RF-14 pede o valor em dados; nenhum documento fixa. [HIPÓTESE do stub]
        };

        /// <summary>Velocidade de movimento da classe em uu/s (docs/13, item 12: class_stats move_speed 450).</summary>
        public const double ClassMoveSpeedUu = 450;

        /// <summary>Abertura do cone quando skills.csv não tem a coluna coneAngle (docs/13, item 4.3: frontal 90°).</summary>
        public const double DefaultConeAngleDegrees = 90;

        /// <summary>Aberturas por habilidade decididas em docs/13 (item 4.3).</summary>
        public static readonly IReadOnlyDictionary<string, double> ConeAngleBySkill = new Dictionary<string, double>(StringComparer.Ordinal)
        {
            { "skill.enemy.guardian_hammer", 100 },
            { "skill.enemy.guardian_shield_bash", 90 },
        };

        /// <summary>Velocidade de projétil por habilidade em uu/s (docs/13, item 6.2) [HIPÓTESE].</summary>
        public static readonly IReadOnlyDictionary<string, double> ProjectileSpeedBySkill = new Dictionary<string, double>(StringComparer.Ordinal)
        {
            { "skill.enemy.ghost_arrow", 1400 },
        };

        /// <summary>Giro do Guardião na fase 1 (docs/13, item 4.2).</summary>
        public static readonly IReadOnlyDictionary<string, double> TurnRateByEnemy = new Dictionary<string, double>(StringComparer.Ordinal)
        {
            { "enemy.crypt_guardian", 60 },
        };

        /// <summary>Giro dos demais inimigos: quase imediato. Nenhum documento fixa. [HIPÓTESE do stub]</summary>
        public const double DefaultTurnRateDegreesPerSecond = 720;

        /// <summary>Efeitos que atordoam (coluna interruptsAction pedida em docs/13, item 3).</summary>
        public static readonly HashSet<string> StunEffects = new HashSet<string>(StringComparer.Ordinal)
        {
            "effect.stun",
        };

        /// <summary>Família imune a atordoamento (Arauto de Pedra; coluna stunImmune pedida em docs/13, item 3).</summary>
        public const string StunImmuneFamily = "family.construct";

        /// <summary>Tabela potions.csv pedida em docs/13 (item 2), com os valores provisórios do documento.</summary>
        public static PotionInfo[] CreatePotions()
        {
            return new[]
            {
                new PotionInfo
                {
                    Id = "potion.life", Kind = PotionKind.Heal, FractionOfMaxLife = 0.4, Duration = 0,
                    MaxCharges = 3, RechargeSeconds = 40, UseTime = 0.4, MoveSpeedWhileUsing = 0.5,
                    EliteKillRefillCharges = 1, HotkeySlot = 1,
                },
                new PotionInfo
                {
                    Id = "potion.ward", Kind = PotionKind.Barrier, FractionOfMaxLife = 0.3, Duration = 6,
                    MaxCharges = 2, RechargeSeconds = 60, UseTime = 0.4, MoveSpeedWhileUsing = 0.5,
                    EliteKillRefillCharges = 1, HotkeySlot = 2,
                },
            };
        }
    }
}
