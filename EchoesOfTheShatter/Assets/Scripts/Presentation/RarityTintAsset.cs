using System;
using UnityEngine;

namespace Echoes.Presentation
{
    public enum RarityTier
    {
        Normal,
        Magic,
        Rare,
        Unique,
    }

    /// <summary>
    /// SO_RarityTint (docs/03 seção 3.11; tokens em <c>art3d.rarity_tint</c> do 03_design_tokens.json; mecanismo no 04, 17.4): os valores de
    /// tinta, rim e acento por raridade, iguais em qualquer herói e slot. Mágico e Raro são variação de material do <c>SG_Character</c>
    /// (sem malha nova); o Único tem malha própria, sem tinta, com acento laranja pulsando devagar. Dado de apresentação: os valores NÃO
    /// são balanceamento; o asset é gerado dos tokens pelo menu Echoes ▸ Criar SO_RarityTint.
    /// </summary>
    [CreateAssetMenu(menuName = "Echoes/Rarity Tint", fileName = "SO_RarityTint")]
    public sealed class RarityTintAsset : ScriptableObject
    {
        [Serializable]
        public struct Entry
        {
            public Color tintColor;
            [Range(0f, 1f)] public float tintStrength;
            [Range(0f, 1f)] public float tintDesat;
            public float tintGain;
            public Color rimTint;
            [Range(0f, 1f)] public float rimTintMix;
            public float rimIntensity;
            [Range(0f, 1f)] public float accentEmissive;
            public Color accentColor;
            [Tooltip("Pulso lento do acento (só o Único); desligado em Reduzir movimento.")]
            public bool pulse;
            public float pulsePeriodSeconds;
            [Range(0f, 1f)] public float pulseVariation;
        }

        public Entry normal;
        public Entry magic;
        public Entry rare;
        public Entry unique;

        static readonly int TintColorId = Shader.PropertyToID("_TintColor");
        static readonly int TintStrengthId = Shader.PropertyToID("_TintStrength");
        static readonly int TintDesatId = Shader.PropertyToID("_TintDesat");
        static readonly int TintGainId = Shader.PropertyToID("_TintGain");
        static readonly int RimTintId = Shader.PropertyToID("_RimTint");
        static readonly int RimTintMixId = Shader.PropertyToID("_RimTintMix");
        static readonly int RimIntensityId = Shader.PropertyToID("_RimIntensity");
        static readonly int AccentEmissiveId = Shader.PropertyToID("_AccentEmissive");
        static readonly int AccentColorId = Shader.PropertyToID("_AccentColor");
        static readonly int AccentPulseId = Shader.PropertyToID("_AccentPulse");
        static readonly int AccentPulsePeriodId = Shader.PropertyToID("_AccentPulsePeriod");
        static readonly int AccentPulseVariationId = Shader.PropertyToID("_AccentPulseVariation");

        public Entry Get(RarityTier tier)
        {
            switch (tier)
            {
                case RarityTier.Magic: return magic;
                case RarityTier.Rare: return rare;
                case RarityTier.Unique: return unique;
                default: return normal;
            }
        }

        /// <summary>Aplica a raridade na instância do material da peça (SetColor/SetFloat, sem MaterialPropertyBlock; 04 17.4).</summary>
        public void Apply(Material material, RarityTier tier, bool reducedMotion = false)
        {
            if (material == null) return;
            var e = Get(tier);
            material.SetColor(TintColorId, e.tintColor);
            material.SetFloat(TintStrengthId, e.tintStrength);
            material.SetFloat(TintDesatId, e.tintDesat);
            material.SetFloat(TintGainId, e.tintGain);
            material.SetColor(RimTintId, e.rimTint);
            material.SetFloat(RimTintMixId, e.rimTintMix);
            material.SetFloat(RimIntensityId, e.rimIntensity);
            material.SetFloat(AccentEmissiveId, e.accentEmissive);
            material.SetColor(AccentColorId, e.accentColor);
            material.SetFloat(AccentPulseId, e.pulse && !reducedMotion ? 1f : 0f);
            material.SetFloat(AccentPulsePeriodId, e.pulsePeriodSeconds);
            material.SetFloat(AccentPulseVariationId, e.pulseVariation);
        }
    }
}
