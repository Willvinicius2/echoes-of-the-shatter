using System.Collections.Generic;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Reage aos eventos do combate para UMA entidade (docs/04_arquitetura.md, seções 3.3 e 10.4):
    /// hitstop congela o Animator e as partículas presas a ela, flash de dano (<c>_HitFlash</c>),
    /// dissolução da morte (<c>_Dissolve</c>), estados de ação ajustados aos tempos do CSV e VFX do
    /// impacto. Nunca decide regra. Cada material é instanciado uma vez; sem MaterialPropertyBlock
    /// (quebra o SRP Batcher). Funciona sem Animator e sem materiais (graybox).
    /// </summary>
    [DisallowMultipleComponent]
    [RequireComponent(typeof(AttributeComponent))]
    public sealed class PresentationController : MonoBehaviour
    {
        static readonly int SpeedParam = Animator.StringToHash("Speed");
        static readonly int IsDeadParam = Animator.StringToHash("IsDead");
        static readonly int IsStaggeredParam = Animator.StringToHash("IsStaggered");
        static readonly int ActionSpeedParam = Animator.StringToHash("ActionSpeed");
        static readonly int HitFlashId = Shader.PropertyToID("_HitFlash");
        static readonly int DissolveId = Shader.PropertyToID("_Dissolve");

        [SerializeField] GameRoot root;
        [SerializeField] Animator animator;
        [SerializeField] SkillPresentationSet skillSet;
        [SerializeField] VfxPool vfxPool;
        [Tooltip("Renderers que piscam e dissolvem. Vazio = todos os filhos.")]
        [SerializeField] Renderer[] renderers;
        [Tooltip("Flash de dano (juice.hit_flash_ms = 83 ms).")]
        [SerializeField, Min(0f)] float hitFlashSeconds = 0.083f;
        [Tooltip("Opção \"Reduzir flashes\": intensidade do flash (1 = normal, 0,5 = reduzido).")]
        [SerializeField, Range(0f, 1f)] float hitFlashIntensity = 1f;
        [Tooltip("Duração da dissolução na morte (docs/03, seção 6: 500 ms).")]
        [SerializeField, Min(0.01f)] float dissolveSeconds = 0.5f;

        AttributeComponent attributes;
        readonly List<Material> ownedMaterials = new List<Material>();
        readonly List<Material> flashMaterials = new List<Material>();
        readonly List<Material> dissolveMaterials = new List<Material>();
        ParticleSystem[] attachedParticles;
        bool frozen;
        float flashTimeLeft;
        float lastFlashValue = -1f;
        float dissolveProgress = -1f;
        float actionSpeed = 1f;
        Vector3 lastPosition;
        int actionLayerIndex = -1;
        int hitLayerIndex = -1;
        bool hasSpeed;
        bool hasIsDead;
        bool hasIsStaggered;
        bool hasActionSpeed;
        bool subscribed;

        Combatant Self => attributes != null ? attributes.Combatant : null;

        void Awake()
        {
            attributes = GetComponent<AttributeComponent>();
            if (animator == null) animator = GetComponentInChildren<Animator>();
            if (renderers == null || renderers.Length == 0) renderers = GetComponentsInChildren<Renderer>();
            attachedParticles = GetComponentsInChildren<ParticleSystem>();
            CacheMaterials();
            lastPosition = transform.position;
        }

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (vfxPool == null) vfxPool = FindAnyObjectByType<VfxPool>();
            if (HasAnimator)
            {
                if (skillSet != null)
                {
                    actionLayerIndex = animator.GetLayerIndex(skillSet.actionLayer);
                    hitLayerIndex = animator.GetLayerIndex(skillSet.hitLayer);
                }
                // Só escreve parâmetros que existem (o Animator avisa no Console a cada chamada sem parâmetro).
                var parameters = animator.parameters;
                for (var i = 0; i < parameters.Length; i++)
                {
                    var hash = parameters[i].nameHash;
                    if (hash == SpeedParam) hasSpeed = true;
                    else if (hash == IsDeadParam) hasIsDead = true;
                    else if (hash == IsStaggeredParam) hasIsStaggered = true;
                    else if (hash == ActionSpeedParam) hasActionSpeed = true;
                }
            }
            var events = root != null ? root.Events : null;
            if (events == null) return;
            events.Subscribe<HitEvent>(OnHit);
            events.Subscribe<SkillPhaseEvent>(OnSkillPhase);
            events.Subscribe<DodgeStartedEvent>(OnDodge);
            events.Subscribe<CombatantDiedEvent>(OnDied);
            events.Subscribe<CombatantRevivedEvent>(OnRevived);
            subscribed = true;
        }

        void OnDestroy()
        {
            for (var i = 0; i < ownedMaterials.Count; i++)
            {
                if (ownedMaterials[i] != null) Destroy(ownedMaterials[i]);
            }
            ownedMaterials.Clear();
            if (!subscribed || root == null || root.Events == null) return;
            var events = root.Events;
            events.Unsubscribe<HitEvent>(OnHit);
            events.Unsubscribe<SkillPhaseEvent>(OnSkillPhase);
            events.Unsubscribe<DodgeStartedEvent>(OnDodge);
            events.Unsubscribe<CombatantDiedEvent>(OnDied);
            events.Unsubscribe<CombatantRevivedEvent>(OnRevived);
        }

        void Update()
        {
            var self = Self;
            if (self == null) return;
            var dt = Time.deltaTime;

            // Hitstop por entidade: congela Animator e partículas presas (o VFX do impacto não pausa).
            var shouldFreeze = self.Hitstop.IsActive;
            if (shouldFreeze != frozen)
            {
                frozen = shouldFreeze;
                for (var i = 0; i < attachedParticles.Length; i++)
                {
                    var main = attachedParticles[i].main;
                    main.simulationSpeed = frozen ? 0f : 1f;
                }
            }

            if (HasAnimator)
            {
                animator.speed = frozen ? 0f : 1f;
                var moved = (transform.position - lastPosition) / Mathf.Max(dt, 1e-5f);
                moved.y = 0f;
                if (hasSpeed) animator.SetFloat(SpeedParam, frozen ? 0f : moved.magnitude);
                if (hasActionSpeed) animator.SetFloat(ActionSpeedParam, actionSpeed);
                if (hasIsStaggered)
                {
                    var rules = root != null && root.Rules != null ? root.Rules.Core : null;
                    animator.SetBool(IsStaggeredParam, rules != null && !self.IsDead && !rules.CanAct(self.Stats));
                }
            }
            lastPosition = transform.position;

            if (flashTimeLeft > 0f) flashTimeLeft -= dt;
            SetFlash(flashTimeLeft > 0f ? hitFlashIntensity : 0f);

            if (dissolveProgress >= 0f && dissolveProgress < 1f)
            {
                dissolveProgress = Mathf.Min(1f, dissolveProgress + dt / dissolveSeconds);
                for (var i = 0; i < dissolveMaterials.Count; i++) dissolveMaterials[i].SetFloat(DissolveId, dissolveProgress);
            }
        }

        bool HasAnimator => animator != null && animator.runtimeAnimatorController != null;

        void OnHit(in HitEvent evt)
        {
            if (!ReferenceEquals(evt.Target, Self)) return;
            if (!evt.Result.Landed || evt.Result.TotalDamage <= 0.0) return;
            flashTimeLeft = hitFlashSeconds;
            if (HasAnimator && hitLayerIndex >= 0 && skillSet != null) PlayIfExists(skillSet.hitState, hitLayerIndex, 0f);
        }

        void OnSkillPhase(in SkillPhaseEvent evt)
        {
            if (!ReferenceEquals(evt.Owner, Self) || evt.Skill == null) return;
            if (evt.Phase == ActionPhase.None)
            {
                actionSpeed = 1f;
                if (HasAnimator && skillSet != null && actionLayerIndex >= 0) PlayIfExists(skillSet.emptyState, actionLayerIndex, 0f);
                return;
            }
            if (skillSet == null) return;

            string state;
            float clip, windupEnd, impactEnd;
            SkillPresentationEntry entry;
            if (skillSet.TryGet(evt.Skill.Id, out entry) && !string.IsNullOrEmpty(entry.animatorState))
            {
                state = entry.animatorState;
                clip = entry.clipSeconds;
                windupEnd = entry.windupEnd;
                impactEnd = Mathf.Max(entry.windupEnd, entry.impactEnd);
            }
            else
            {
                state = (evt.Skill.Tags & SkillTags.Spell) != 0 ? skillSet.castFallbackState : skillSet.strikeFallbackState;
                clip = skillSet.fallbackClipSeconds;
                windupEnd = skillSet.fallbackWindupEnd;
                impactEnd = Mathf.Max(skillSet.fallbackWindupEnd, skillSet.fallbackImpactEnd);
            }

            float start, authored;
            switch (evt.Phase)
            {
                case ActionPhase.Windup:
                    start = 0f;
                    authored = windupEnd * clip;
                    break;
                case ActionPhase.Impact:
                    start = windupEnd;
                    authored = (impactEnd - windupEnd) * clip;
                    if (entry != null && entry.impactVfx != null && vfxPool != null)
                    {
                        var anchor = FindAnchor(entry.anchor);
                        vfxPool.Play(entry.impactVfx, anchor.position, transform.rotation, entry.vfxSeconds);
                    }
                    break;
                default:
                    start = impactEnd;
                    authored = (1f - impactEnd) * clip;
                    break;
            }

            // velocidade = duração autoral da fase / duração da fase no CSV (seção 3.3).
            actionSpeed = evt.PhaseSeconds > 1e-4 && authored > 0f ? authored / (float)evt.PhaseSeconds : 1f;
            if (HasAnimator && actionLayerIndex >= 0) PlayIfExists(state, actionLayerIndex, start);
        }

        void OnDodge(in DodgeStartedEvent evt)
        {
            if (!ReferenceEquals(evt.Owner, Self) || !HasAnimator || skillSet == null || actionLayerIndex < 0) return;
            actionSpeed = 1f;
            PlayIfExists(skillSet.dodgeState, actionLayerIndex, 0f);
        }

        void OnDied(in CombatantDiedEvent evt)
        {
            if (!ReferenceEquals(evt.Target, Self)) return;
            flashTimeLeft = 0f;
            actionSpeed = 1f;
            if (HasAnimator && hasIsDead) animator.SetBool(IsDeadParam, true);
            dissolveProgress = dissolveMaterials.Count > 0 ? 0f : -1f;
        }

        void OnRevived(in CombatantRevivedEvent evt)
        {
            if (!ReferenceEquals(evt.Target, Self)) return;
            if (HasAnimator && hasIsDead) animator.SetBool(IsDeadParam, false);
            dissolveProgress = -1f;
            for (var i = 0; i < dissolveMaterials.Count; i++) dissolveMaterials[i].SetFloat(DissolveId, 0f);
        }

        void PlayIfExists(string state, int layer, float normalizedTime)
        {
            if (string.IsNullOrEmpty(state)) return;
            var hash = Animator.StringToHash(state);
            if (animator.HasState(layer, hash)) animator.Play(hash, layer, normalizedTime);
        }

        Transform FindAnchor(string anchorName)
        {
            if (string.IsNullOrEmpty(anchorName)) return transform;
            var found = FindChildRecursive(transform, anchorName);
            return found != null ? found : transform;
        }

        static Transform FindChildRecursive(Transform parent, string childName)
        {
            for (var i = 0; i < parent.childCount; i++)
            {
                var child = parent.GetChild(i);
                if (child.name == childName) return child;
                var deeper = FindChildRecursive(child, childName);
                if (deeper != null) return deeper;
            }
            return null;
        }

        void CacheMaterials()
        {
            for (var r = 0; r < renderers.Length; r++)
            {
                var renderer = renderers[r];
                if (renderer == null || renderer is ParticleSystemRenderer) continue;
                // .materials cria UMA instância por renderer (uma vez), não por golpe; destruídas no OnDestroy.
                var materials = renderer.materials;
                for (var m = 0; m < materials.Length; m++)
                {
                    var material = materials[m];
                    if (material == null) continue;
                    ownedMaterials.Add(material);
                    if (material.HasProperty(HitFlashId)) flashMaterials.Add(material);
                    if (material.HasProperty(DissolveId)) dissolveMaterials.Add(material);
                }
            }
        }

        void SetFlash(float value)
        {
            if (Mathf.Approximately(value, lastFlashValue)) return;
            lastFlashValue = value;
            for (var i = 0; i < flashMaterials.Count; i++) flashMaterials[i].SetFloat(HitFlashId, value);
        }
    }
}
