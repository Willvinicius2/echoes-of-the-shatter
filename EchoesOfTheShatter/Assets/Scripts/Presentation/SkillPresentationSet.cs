using System;
using System.Collections.Generic;
using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Conjunto de apresentação de uma classe ou família (docs/04_arquitetura.md, seção 3.3).
    /// Habilidade sem entrada cai no estado genérico de golpe ou conjuração. Dado de apresentação.
    /// Crie em Assets/Data/Presentation (Create ▸ Echoes ▸ Skill Presentation Set).
    /// </summary>
    [CreateAssetMenu(menuName = "Echoes/Skill Presentation Set", fileName = "SO_SkillPresentation_Warrior")]
    public sealed class SkillPresentationSet : ScriptableObject
    {
        [Header("Camadas e estados do Animator Controller")]
        public string actionLayer = "Action";
        public string emptyState = "Empty";
        public string strikeFallbackState = "SkillStrike";
        public string castFallbackState = "SkillCast";
        public string dodgeState = "Dodge";
        public string hitLayer = "Hit";
        public string hitState = "Hit";

        [Header("Clipe genérico (quando a habilidade não tem entrada)")]
        [Min(0.01f)] public float fallbackClipSeconds = 1f;
        [Range(0f, 1f)] public float fallbackWindupEnd = 0.3f;
        [Range(0f, 1f)] public float fallbackImpactEnd = 0.5f;

        [Header("Habilidades")]
        public List<SkillPresentationEntry> entries = new List<SkillPresentationEntry>();

        [NonSerialized] Dictionary<string, SkillPresentationEntry> lookup;

        public bool TryGet(string skillId, out SkillPresentationEntry entry)
        {
            entry = null;
            if (string.IsNullOrEmpty(skillId)) return false;
            if (lookup == null)
            {
                lookup = new Dictionary<string, SkillPresentationEntry>(StringComparer.Ordinal);
                for (var i = 0; i < entries.Count; i++)
                {
                    var e = entries[i];
                    if (e != null && !string.IsNullOrEmpty(e.skillId)) lookup[e.skillId] = e;
                }
            }
            return lookup.TryGetValue(skillId, out entry);
        }

        void OnValidate()
        {
            lookup = null;
        }
    }
}
