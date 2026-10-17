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

        [Header("Knockback em cm (juice.knockback_cm)")]
        [SerializeField, Min(0f)] float knockbackCommonCm = 20f;
        [SerializeField, Min(0f)] float knockbackEliteCm = 6f;
        [SerializeField, Min(0f)] float knockbackBossCm = 0f;
        [SerializeField, Min(0f)] float knockbackDurationMs = 100f;

        [Header("Virada do corpo do herói em graus/s")]
        [Tooltip("Andando ou parado: o corpo gira suave até a direção do movimento.")]
        [SerializeField, Min(1f)] float turnDegreesPerSecond = 900f;
        [Tooltip("Ao iniciar golpe ou magia: giro mais rápido para encarar a mira.")]
        [SerializeField, Min(1f)] float castTurnDegreesPerSecond = 1800f;

        [Header("Golpes pesados (recebem o hitstop de golpe pesado)")]
        [SerializeField] string[] heavySkills =
        {
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
            };
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
