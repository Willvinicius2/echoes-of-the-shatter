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

        [Header("Heróis: camada de tronco e braços (defesa e carga, BasicInputEvent); vazio = sem a camada")]
        public string upperLayer = string.Empty;
        [Tooltip("Estado ao levantar a defesa (ele mesmo passa para o estado de segurar, se o controller tiver).")]
        public string guardRaiseState = "GuardRaise";
        [Tooltip("Reação ao golpe absorvido na defesa (vazio = usa a camada Hit, o corpo todo).")]
        public string guardHitState = "GuardHit";
        [Tooltip("Primeiro estado da carga do golpe forte.")]
        public string chargeState = "ChargeHold";
        [Tooltip("Transição de entrada e de saída dos estados da camada de tronco e braços, em segundos.")]
        [Min(0f)] public float upperBlendSeconds = 0.1f;
        [Tooltip("Carga do golpe forte: a pose congelada vai se armando devagar, do holdAt até esta fração do caminho até o fim da preparação, conforme a carga do core. 0 = pose parada.")]
        [Range(0f, 1f)] public float chargeCreep = 0.7f;

        [Header("Preparação, recuperação e saída do golpe (rev3: nunca congelar no último quadro)")]
        [Tooltip("Velocidade máxima do clipe na preparação. Se o trecho autoral não couber, o clipe começa mais adiante em vez de acelerar mais.")]
        [Range(1f, 4f)] public float maxWindupSpeed = 2.5f;
        [Tooltip("Fração do trecho de preparação que o aperto toca antes de o core iniciar o golpe (o resto fecha na preparação do core). Segurar o botão vira carga: o leve não toca inteiro antes.")]
        [Range(0.2f, 1f)] public float preRollHoldFraction = 0.6f;
        [Tooltip("Velocidade do acompanhamento (cauda do clipe) na recuperação: entre o mínimo e o máximo; natural = 1.")]
        [Range(0.5f, 1.5f)] public float recoveryMinSpeed = 1f;
        [Range(1f, 4f)] public float recoveryMaxSpeed = 1.2f;
        [Tooltip("O clipe acabou antes de a recuperação do core: mistura para a pose de combate ou para a locomoção em tanto tempo, em vez de congelar no último quadro.")]
        [Min(0.02f)] public float clipEndBlendSeconds = 0.12f;
        [Tooltip("A lógica liberou antes de o clipe acabar: sai para o próximo golpe ou para o movimento em tanto tempo.")]
        [Min(0.02f)] public float actionExitBlendSeconds = 0.1f;

        [Header("Chefe: rugido de fase (BossStateEvent.PhaseStart)")]
        public string roarState = "Roar";
        [Tooltip("Duração autoral do clipe de rugido; a velocidade é ajustada ao rugido do core (transitionSeconds).")]
        [Min(0.01f)] public float roarClipSeconds = 1f;

        [Header("Clipe genérico (quando a habilidade não tem entrada)")]
        [Min(0.01f)] public float fallbackClipSeconds = 1f;
        [Range(0f, 1f)] public float fallbackWindupEnd = 0.3f;
        [Range(0f, 1f)] public float fallbackImpactEnd = 0.5f;

        [Header("Habilidades")]
        public List<SkillPresentationEntry> entries = new List<SkillPresentationEntry>();

        [Header("VFX das habilidades (SkillVfxPresenter; VfxLibraryBuilder). Separado de entries, que o AnimatorControllerBuilder regenera")]
        public List<SkillVfxEntry> vfx = new List<SkillVfxEntry>();

        [NonSerialized] Dictionary<string, SkillPresentationEntry> lookup;
        [NonSerialized] Dictionary<string, SkillVfxEntry> vfxLookup;

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

        public bool TryGetVfx(string skillId, out SkillVfxEntry entry)
        {
            entry = null;
            if (string.IsNullOrEmpty(skillId)) return false;
            if (vfxLookup == null)
            {
                vfxLookup = new Dictionary<string, SkillVfxEntry>(StringComparer.Ordinal);
                for (var i = 0; i < vfx.Count; i++)
                {
                    var e = vfx[i];
                    if (e != null && !string.IsNullOrEmpty(e.skillId)) vfxLookup[e.skillId] = e;
                }
            }
            return vfxLookup.TryGetValue(skillId, out entry);
        }

        void OnValidate()
        {
            lookup = null;
            vfxLookup = null;
        }
    }
}
