using System;
using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Habilidade → clipe e VFX (docs/04_arquitetura.md, seção 3.3). As frações dividem o clipe nas
    /// 3 fases; a velocidade de cada fase é ajustada aos tempos do CSV (a animação se adapta).
    /// </summary>
    [Serializable]
    public sealed class SkillPresentationEntry
    {
        [Tooltip("ID de conteúdo (ex.: skill.warrior.iron_cut).")]
        public string skillId = string.Empty;
        [Tooltip("Estado na camada Action do Animator Controller.")]
        public string animatorState = string.Empty;
        [Tooltip("Duração autoral do clipe, em segundos.")]
        [Min(0.01f)] public float clipSeconds = 1f;
        [Tooltip("Fração do clipe onde termina a preparação.")]
        [Range(0f, 1f)] public float windupEnd = 0.3f;
        [Tooltip("Fração do clipe onde termina o impacto.")]
        [Range(0f, 1f)] public float impactEnd = 0.5f;
        [Tooltip("Golpe carregado: fração do clipe onde a pose \"arma atrás\" fica congelada na carga (camada Upper). A preparação do golpe começa neste ponto.")]
        [Range(0f, 1f)] public float holdAt;
        [Header("Golpe em estados separados (opcional; ex.: Investida do Guardião: preparação, corrida em laço, recuperação)")]
        [Tooltip("Estado da preparação. Vazio = o golpe usa só animatorState, dividido por windupEnd e impactEnd.")]
        public string windupState = string.Empty;
        [Min(0.01f)] public float windupClipSeconds = 1f;
        [Tooltip("Estado do impacto (laço): toca com velocidade 1 enquanto durar a fase de impacto.")]
        public string impactState = string.Empty;
        [Tooltip("Duração autoral do clipe do estado de impacto. Com recoveryState vazio, o clipe cobre impacto e recuperação (a velocidade é ajustada às duas fases).")]
        [Min(0f)] public float impactClipSeconds;
        public string recoveryState = string.Empty;
        [Min(0.01f)] public float recoveryClipSeconds = 1f;
        public bool HasPhaseStates => !string.IsNullOrEmpty(windupState);

        [Header("VFX e âncora")]
        [Tooltip("VFX tocado no início do impacto (em pool).")]
        public GameObject impactVfx;
        [Tooltip("Segundos até devolver o VFX ao pool.")]
        [Min(0f)] public float vfxSeconds = 1f;
        [Tooltip("Nome do Transform âncora (socket_weapon_r, socket_fx_ground...). Vazio = raiz.")]
        public string anchor = string.Empty;
    }
}
