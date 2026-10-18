using UnityEngine;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Dados de "juice" que afetam tempo e posição das entidades: hitstop e knockback
    /// (docs/03_design_system.md, seção 6; tokens <c>juice</c> de docs/03_design_tokens.json).
    /// É apresentação, não balanceamento; os padrões abaixo são os dos tokens.
    /// Crie em Assets/Data/Presentation (Create ▸ Echoes ▸ Combat Feel Settings).
    /// </summary>
    [CreateAssetMenu(menuName = "Echoes/Combat Feel Settings", fileName = "SO_CombatFeel")]
    public sealed class CombatFeelSettings : ScriptableObject
    {
        [Header("Hitstop em ms (juice.hitstop_ms)")]
        [SerializeField, Min(0f)] float hitstopHeavyMs = 60f;
        [SerializeField, Min(0f)] float hitstopCriticalMs = 80f;
        [SerializeField, Min(0f)] float hitstopBossHeavyMs = 80f;
        [SerializeField, Min(0f)] float hitstopPlayerHitMs = 40f;

        [Header("Inimigos (rev5): rampa do agente e virada do corpo")]
        [SerializeField, Min(0f)] float enemyAccelSeconds = 0.15f;
        [SerializeField, Min(0f)] float enemyDecelSeconds = 0.12f;
        [SerializeField, Min(1f)] float enemyTurnDegreesPerSecond = 540f;
        [SerializeField, Min(1f)] float enemyAttackTurnDegreesPerSecond = 900f;
        [Tooltip("Perseguição em grupo: o inimigo mira o anel de alcance do golpe (fração do alcance) numa vaga de até ± estes graus em volta do herói.")]
        [SerializeField, Range(0.5f, 1f)] float enemyApproachFraction = 0.9f;
        [SerializeField, Range(0f, 120f)] float enemySurroundSpreadDegrees = 70f;
        [SerializeField, Range(0, 99)] int enemyAvoidancePriorityBase = 40;
        [SerializeField, Range(0, 49)] int enemyAvoidancePrioritySpread = 20;
        [Tooltip("Raio de evasão do agente de navegação do inimigo (o chefe usa o próprio): menor que o corpo para os vizinhos não o frearem.")]
        [SerializeField, Range(0.1f, 0.6f)] float enemyAvoidanceRadiusMeters = 0.3f;

        [Header("Hitstop leve (golpe que não é pesado mas merece um tranco)")]
        [SerializeField, Min(0f)] float hitstopLightMs = 35f;
        [SerializeField] string[] lightHitstopSkills =
        {
            "skill.mage.fireball",
        };

        [Header("Knockback em cm (juice.knockback_cm)")]
        [SerializeField, Min(0f)] float knockbackCommonCm = 20f;
        [SerializeField, Min(0f)] float knockbackEliteCm = 6f;
        [SerializeField, Min(0f)] float knockbackBossCm = 0f;
        [SerializeField, Min(0f)] float knockbackDurationMs = 100f;

        [Header("Virada do corpo do herói em graus/s")]
        [Tooltip("Andando ou parado: o corpo gira suave até a direção do movimento.")]
        [SerializeField, Min(1f)] float turnDegreesPerSecond = 900f;
        [Tooltip("Ao iniciar golpe ou magia: giro mais rápido para encarar a mira.")]
        [SerializeField, Min(1f)] float castTurnDegreesPerSecond = 1200f;
        [Tooltip("Defendendo ou carregando: giro mais calmo, sem pressa.")]
        [SerializeField, Min(1f)] float aimTurnDegreesPerSecond = 720f;

        [Header("Golpes pesados (recebem o hitstop de golpe pesado)")]
        [SerializeField] string[] heavySkills =
        {
            "skill.warrior.heavy_slash",
            "skill.warrior.combo_3",
            "skill.warrior.charge",
            "skill.warrior.stone_rift",
            "skill.warrior.shield_bash",
            "skill.enemy.herald_slam",
            "skill.enemy.guardian_hammer",
            "skill.enemy.guardian_shield_bash",
        };

        public CombatFeelValues ToValues()
        {
            var values = new CombatFeelValues
            {
                HitstopHeavySeconds = hitstopHeavyMs / 1000.0,
                HitstopCriticalSeconds = hitstopCriticalMs / 1000.0,
                HitstopBossHeavySeconds = hitstopBossHeavyMs / 1000.0,
                HitstopPlayerHitSeconds = hitstopPlayerHitMs / 1000.0,
                KnockbackCommonMeters = knockbackCommonCm / 100f,
                KnockbackEliteMeters = knockbackEliteCm / 100f,
                KnockbackBossMeters = knockbackBossCm / 100f,
                KnockbackSeconds = knockbackDurationMs / 1000f,
                TurnDegreesPerSecond = turnDegreesPerSecond,
                CastTurnDegreesPerSecond = castTurnDegreesPerSecond,
                AimTurnDegreesPerSecond = aimTurnDegreesPerSecond,
            };
            values.HitstopLightSeconds = hitstopLightMs / 1000.0;
            values.EnemyAccelSeconds = enemyAccelSeconds;
            values.EnemyDecelSeconds = enemyDecelSeconds;
            values.EnemyTurnDegreesPerSecond = enemyTurnDegreesPerSecond;
            values.EnemyAttackTurnDegreesPerSecond = enemyAttackTurnDegreesPerSecond;
            values.EnemyApproachFraction = enemyApproachFraction;
            values.EnemySurroundSpreadDegrees = enemySurroundSpreadDegrees;
            values.EnemyAvoidancePriorityBase = enemyAvoidancePriorityBase;
            values.EnemyAvoidancePrioritySpread = enemyAvoidancePrioritySpread;
            values.EnemyAvoidanceRadiusMeters = enemyAvoidanceRadiusMeters;
            if (lightHitstopSkills != null)
            {
                for (var i = 0; i < lightHitstopSkills.Length; i++)
                {
                    if (!string.IsNullOrEmpty(lightHitstopSkills[i])) values.LightHitstopSkills.Add(lightHitstopSkills[i]);
                }
            }
            if (heavySkills != null)
            {
                for (var i = 0; i < heavySkills.Length; i++)
                {
                    if (!string.IsNullOrEmpty(heavySkills[i])) values.HeavySkills.Add(heavySkills[i]);
                }
            }
            return values;
        }

        /// <summary>Valores padrão dos tokens, para cenas de teste sem o asset.</summary>
        public static CombatFeelValues CreateDefaultValues()
        {
            var instance = CreateInstance<CombatFeelSettings>();
            var values = instance.ToValues();
            if (Application.isPlaying) Destroy(instance);
            else DestroyImmediate(instance);
            return values;
        }
    }
}
