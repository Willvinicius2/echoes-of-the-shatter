using System.Collections.Generic;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Reage aos eventos do combate para UMA entidade (docs/tecnico/04_arquitetura.md, seções 3.3 e 10.4):
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
        static readonly int PhaseParam = Animator.StringToHash("Phase");
        static readonly int IsFleeingParam = Animator.StringToHash("IsFleeing");
        static readonly int HoldAtParam = Animator.StringToHash("HoldAt");
        static readonly int AimingParam = Animator.StringToHash("Aiming");
        static readonly int MoveXParam = Animator.StringToHash("MoveX");
        static readonly int MoveYParam = Animator.StringToHash("MoveY");
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
        [Tooltip("Amortecimento do parâmetro Speed do Animator (s): evita a troca seca entre parado, andar e correr.")]
        [SerializeField, Min(0f)] float speedDampSeconds = 0.08f;
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
        int upperLayerIndex = -1;
        bool hasHoldAt;
        // Antecipacao no aperto (LightPressed): o clipe da preparacao comeca ao apertar e segura na pose "armada" ate o core iniciar o golpe.
        sealed class PreRoll
        {
            public SkillPresentationEntry Entry;
            public float Pos;      // posicao atual no clipe (s)
            public float HoldPos;  // ate aqui toca no aperto; o resto fecha na preparacao do core
            public float EndPos;   // fim do trecho de preparacao (s)
            public float Rate;     // velocidade para cobrir o trecho na preparacao do core
            public float Elapsed;
        }
        PreRoll preRoll;
        float clipEndTimer = -1f;   // o clipe da recuperacao acaba antes do core: faltam tantos segundos para misturar com a pose de combate
        bool actionClipEnded;
        // Peso: avanco visual do corpo (so o filho visual do heroi) no impacto, de volta na recuperacao.
        Transform modelRoot;
        Vector3 modelBaseLocal;
        float lunge, lungeTarget, lungeRate;
        // Impacto legivel: o swing continua um pouco dentro da recuperacao; a posicao no clipe segue a velocidade aplicada.
        bool trackAction;
        float actionPos;
        SkillPresentationEntry trackedEntry;
        FollowCamera followCamera;
        float windupHoldTimer = -1f;          // preparacao longa: depois deste tempo, a pose armada segura devagar
        float dissolveDelayLeft;
        Vector3 hitKick;                      // empurrao visual do golpe recebido (mundo), decai sozinho
        UnityEngine.AI.NavMeshAgent enemyAgent;
        bool lungeApplied;
        SkillPresentationEntry chargeEntry; // golpe forte em carga (a pose congelada avanca devagar com a carga do core)
        float chargeHoldAt;                 // ponto normalizado atual da pose de carga; o golpe solta daqui
        bool hasAiming;
        bool hasSpeed;
        bool hasIsDead;
        bool hasIsStaggered;
        bool hasActionSpeed;
        bool hasPhase;
        bool hasFleeing;
        EnemyController enemyController;
        HeroController heroController;
        bool eliteApplied;
        [Tooltip("SO_RarityTint: o elite (modificador do core) ganha a tinta de Raro nos materiais do corpo.")]
        [SerializeField] RarityTintAsset eliteTint;
        bool subscribed;

        Combatant Self => attributes != null ? attributes.Combatant : null;

        void Awake()
        {
            attributes = GetComponent<AttributeComponent>();
            enemyController = GetComponent<EnemyController>();
            heroController = GetComponent<HeroController>();
            enemyAgent = GetComponent<UnityEngine.AI.NavMeshAgent>();
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
            if (HasAnimator && animator.transform != transform)
            {
                modelRoot = animator.transform;
                modelBaseLocal = modelRoot.localPosition;
            }
            if (HasAnimator)
            {
                if (skillSet != null)
                {
                    actionLayerIndex = animator.GetLayerIndex(skillSet.actionLayer);
                    hitLayerIndex = animator.GetLayerIndex(skillSet.hitLayer);
                    if (!string.IsNullOrEmpty(skillSet.upperLayer)) upperLayerIndex = animator.GetLayerIndex(skillSet.upperLayer);
                    if (hitLayerIndex >= 0 && enemyController != null) animator.SetLayerWeight(hitLayerIndex, skillSet.hitFlinchWeight);
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
                    else if (hash == PhaseParam) hasPhase = true;
                    else if (hash == IsFleeingParam) hasFleeing = true;
                    else if (hash == HoldAtParam) hasHoldAt = true;
                    else if (hash == AimingParam) hasAiming = true;
                }
            }
            var events = root != null ? root.Events : null;
            if (events == null) return;
            events.Subscribe<HitEvent>(OnHit);
            events.Subscribe<SkillPhaseEvent>(OnSkillPhase);
            events.Subscribe<DodgeStartedEvent>(OnDodge);
            events.Subscribe<CombatantDiedEvent>(OnDied);
            events.Subscribe<CombatantRevivedEvent>(OnRevived);
            events.Subscribe<BossStateEvent>(OnBossState);
            events.Subscribe<BasicInputEvent>(OnBasicInput);
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
            events.Unsubscribe<BossStateEvent>(OnBossState);
            events.Unsubscribe<BasicInputEvent>(OnBasicInput);
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
                // Herói: velocidade da lógica (estável, sem o ruído do deslocamento por quadro). Inimigo: deslocamento medido.
                float speed;
                if (heroController != null && heroController.Logic != null) speed = heroController.Logic.CurrentVelocity().Magnitude;
                else if (enemyController != null && enemyAgent != null && enemyAgent.enabled && enemyAgent.isOnNavMesh)
                {
                    // O agente tem a rampa de aceleracao (valores de feel): o pe acompanha a velocidade dele e o knockback nao vira corrida.
                    var velocity = enemyAgent.velocity;
                    velocity.y = 0f;
                    speed = velocity.magnitude;
                }
                else
                {
                    var moved = (transform.position - lastPosition) / Mathf.Max(dt, 1e-5f);
                    moved.y = 0f;
                    speed = moved.magnitude;
                }
                if (hasSpeed)
                {
                    if (frozen) animator.SetFloat(SpeedParam, 0f);
                    else animator.SetFloat(SpeedParam, speed, speedDampSeconds, dt);
                }
                var stepDt = frozen ? 0f : dt;
                if (trackAction) actionPos += actionSpeed * stepDt;
                if (windupHoldTimer > 0f)
                {
                    windupHoldTimer -= stepDt;
                    if (windupHoldTimer <= 0f)
                    {
                        windupHoldTimer = -1f;
                        actionSpeed = skillSet != null ? skillSet.windupHoldSpeed : 0.1f; // pose armada segura, viva, ate o impacto
                    }
                }
                if (preRoll != null) TickPreRoll(stepDt);
                if (clipEndTimer > 0f)
                {
                    clipEndTimer -= stepDt;
                    if (clipEndTimer <= 0f) EndActionClip();
                }
                if (hasActionSpeed) animator.SetFloat(ActionSpeedParam, actionSpeed);
                if (chargeEntry != null && hasHoldAt && heroController != null && heroController.Logic != null && heroController.Logic.IsCharging)
                {
                    // A carga nao e uma foto: a pose vai se armando devagar (pouco, de holdAt ate chargeCreep do caminho ao fim da preparacao).
                    var progress = Mathf.Clamp01((float)heroController.Logic.ChargeProgress);
                    var limit = Mathf.Lerp(chargeEntry.holdAt, chargeEntry.windupEnd, skillSet != null ? skillSet.chargeCreep : 0f);
                    chargeHoldAt = Mathf.Lerp(chargeEntry.holdAt, limit, progress);
                    animator.SetFloat(HoldAtParam, chargeHoldAt);
                }
                if (hasAiming && heroController != null && heroController.Logic != null) UpdateAiming(heroController.Logic, frozen, dt);
                if (hasFleeing && enemyController != null && enemyController.Logic != null) animator.SetBool(IsFleeingParam, enemyController.Logic.IsFleeing);
                if (hasIsStaggered)
                {
                    var rules = root != null && root.Rules != null ? root.Rules.Core : null;
                    animator.SetBool(IsStaggeredParam, rules != null && !self.IsDead && !rules.CanAct(self.Stats));
                }
            }
            lastPosition = transform.position;
            ApplyLunge(frozen ? 0f : dt);

            // Tinta de elite (uma vez, quando o combatente existe): so o tecido, pelo mesmo mecanismo da raridade.
            if (!eliteApplied && eliteTint != null && !self.Elite.IsNone)
            {
                eliteApplied = true;
                foreach (var material in ownedMaterials) eliteTint.Apply(material, RarityTier.Rare);
            }

            if (flashTimeLeft > 0f) flashTimeLeft -= dt;
            SetFlash(flashTimeLeft > 0f ? hitFlashIntensity : 0f);

            if (dissolveDelayLeft > 0f) dissolveDelayLeft -= dt;
            else if (dissolveProgress >= 0f && dissolveProgress < 1f)
            {
                dissolveProgress = Mathf.Min(1f, dissolveProgress + dt / dissolveSeconds);
                for (var i = 0; i < dissolveMaterials.Count; i++) dissolveMaterials[i].SetFloat(DissolveId, dissolveProgress);
            }
        }

        bool HasAnimator => animator != null && animator.runtimeAnimatorController != null;

        /// <summary>Troca o conjunto de apresentação antes do Start (a classe escolhida: o HeroVisualSwap chama no Awake).</summary>
        public void UseSkillSet(SkillPresentationSet set)
        {
            if (set != null) skillSet = set;
        }

        // Defendendo ou carregando o corpo encara a mira e as pernas andam para qualquer lado: o blend 2D de AimLocomotion recebe a velocidade
        // no referencial do corpo (MoveX = direita, MoveY = frente, em m/s).
        void UpdateAiming(HeroCombatLogic logic, bool isFrozen, float dt)
        {
            var aiming = logic.IsAiming;
            animator.SetBool(AimingParam, aiming);
            if (!aiming || isFrozen)
            {
                animator.SetFloat(MoveXParam, 0f, speedDampSeconds, dt);
                animator.SetFloat(MoveYParam, 0f, speedDampSeconds, dt);
                return;
            }
            var velocity = logic.CurrentVelocity();
            var facing = logic.FacingDirection();
            var forward = velocity.X * facing.X + velocity.Z * facing.Z;
            var right = velocity.X * facing.Z - velocity.Z * facing.X; // direita do corpo no plano XZ (frente = +Z)
            animator.SetFloat(MoveXParam, right, speedDampSeconds, dt);
            animator.SetFloat(MoveYParam, forward, speedDampSeconds, dt);
        }

        void OnHit(in HitEvent evt)
        {
            if (!ReferenceEquals(evt.Target, Self)) return;
            if (!evt.Result.Landed || evt.Result.TotalDamage <= 0.0) return;
            flashTimeLeft = hitFlashSeconds;
            if (!HasAnimator || skillSet == null) return;
            if (enemyController != null && modelRoot != null && evt.Attacker != null && skillSet.hitKickMeters > 0f)
            {
                // Empurrao visual coerente com o do core: na direcao do golpe (do atacante para o alvo), mais forte se a habilidade tem knockback proprio.
                var away = (Self.Position - evt.Attacker.Position).NormalizedOr(Self.Forward * -1f);
                hitKick = new Vector3(away.X, 0f, away.Z) * skillSet.hitKickMeters * (evt.Skill != null && evt.Skill.KnockbackUu > 0.0 ? 1.6f : 1f);
            }
            // Defendendo: o golpe absorvido mexe só o tronco e os braços (camada Upper), as pernas seguem andando; sem reação própria, o corpo todo.
            var guarding = heroController != null && heroController.Logic != null && heroController.Logic.IsGuarding;
            if (guarding && upperLayerIndex >= 0 && !string.IsNullOrEmpty(skillSet.guardHitState) && animator.HasState(upperLayerIndex, Animator.StringToHash(skillSet.guardHitState)))
                PlayIfExists(skillSet.guardHitState, upperLayerIndex, 0f, skillSet.upperBlendSeconds);
            else if (hitLayerIndex >= 0) PlayIfExists(skillSet.hitState, hitLayerIndex, 0f);
        }

        // Máquina de entrada do ataque básico (docs/18): carga e defesa tocam na camada de tronco e braços; o golpe forte solta na camada Action.
        void OnBasicInput(in BasicInputEvent evt)
        {
            if (!ReferenceEquals(evt.Owner, Self) || !HasAnimator || skillSet == null || upperLayerIndex < 0) return;
            var blend = skillSet.upperBlendSeconds;
            switch (evt.Kind)
            {
                case BasicInputKind.LightPressed:
                    BeginPreRoll(evt.Skill);
                    break;
                case BasicInputKind.ChargeStarted:
                    CancelPreRoll();
                    // A pose congelada da carga é o quadro "arma atrás" do golpe forte (holdAt, medido no clipe).
                    chargeEntry = null;
                    if (hasHoldAt && evt.Skill != null && skillSet.TryGet(evt.Skill.Id, out var heavy))
                    {
                        chargeEntry = heavy;
                        chargeHoldAt = heavy.holdAt;
                        animator.SetFloat(HoldAtParam, heavy.holdAt);
                    }
                    PlayIfExists(skillSet.chargeState, upperLayerIndex, 0f, blend);
                    break;
                case BasicInputKind.GuardUp:
                    CancelPreRoll();
                    PlayIfExists(skillSet.guardRaiseState, upperLayerIndex, 0f, blend);
                    break;
                case BasicInputKind.ChargeCancelled:
                case BasicInputKind.HeavyReleased:
                    if (evt.Kind == BasicInputKind.ChargeCancelled) chargeEntry = null; // solto: chargeEntry segue valendo ate o golpe sair (a preparacao parte de chargeHoldAt)
                    PlayIfExists(skillSet.emptyState, upperLayerIndex, 0f, blend);
                    break;
                case BasicInputKind.GuardDown:
                case BasicInputKind.GuardBroke:
                    PlayIfExists(skillSet.emptyState, upperLayerIndex, 0f, blend);
                    break;
            }
        }

        void OnSkillPhase(in SkillPhaseEvent evt)
        {
            if (!ReferenceEquals(evt.Owner, Self) || evt.Skill == null) return;
            if (evt.Phase == ActionPhase.None)
            {
                actionSpeed = 1f;
                clipEndTimer = -1f;
                windupHoldTimer = -1f;
                trackAction = false;
                LungeTo(0f, 0.08f);
                if (!actionClipEnded && HasAnimator && skillSet != null && actionLayerIndex >= 0) PlayIfExists(skillSet.emptyState, actionLayerIndex, 0f, ExitBlendSeconds);
                actionClipEnded = false;
                return;
            }
            if (skillSet == null) return;
            if (evt.Phase != ActionPhase.Recovery) clipEndTimer = -1f;
            if (evt.Phase == ActionPhase.Windup)
            {
                actionClipEnded = false;
                trackAction = false;
            }

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

            // Golpe em estados separados: cada fase toca o seu clipe, com a velocidade ajustada a duracao da fase no core.
            if (entry != null && entry.HasPhaseStates && !string.IsNullOrEmpty(state))
            {
                string phaseState;
                float phaseClip;
                var windupOffset = 0f;
                var phaseSeconds = (float)evt.PhaseSeconds;
                if (evt.Phase == ActionPhase.Windup && ContinuePreRoll(entry, phaseSeconds)) return;
                switch (evt.Phase)
                {
                    case ActionPhase.Windup:
                        phaseState = entry.windupState;
                        phaseClip = entry.windupClipSeconds * Mathf.Max(0.01f, entry.windupTo - entry.windupFrom);
                        windupOffset = entry.windupFrom * entry.windupClipSeconds;
                        if (phaseSeconds > 1e-4f && phaseClip > phaseSeconds * skillSet.maxWindupSpeed)
                        {
                            // Nao acelera alem do teto: comeca mais adiante no clipe (so o final do puxar).
                            phaseClip = phaseSeconds * skillSet.maxWindupSpeed;
                            windupOffset = entry.windupTo * entry.windupClipSeconds - phaseClip;
                        }
                        break;
                    case ActionPhase.Impact:
                        phaseState = string.IsNullOrEmpty(entry.impactState) ? entry.windupState : entry.impactState;
                        phaseClip = entry.impactClipSeconds; // 0 = laco: velocidade 1
                        // Sem estado de recuperacao, o clipe do impacto cobre impacto e recuperacao (ex.: Release do arco): a velocidade segue as duas fases do core.
                        if (phaseClip > 0f && string.IsNullOrEmpty(entry.recoveryState)) phaseSeconds += (float)RecoverySecondsOf(evt.Skill);
                        break;
                    default:
                        if (string.IsNullOrEmpty(entry.recoveryState) && entry.impactClipSeconds > 0f) return; // o clipe do impacto segue tocando
                        phaseState = string.IsNullOrEmpty(entry.recoveryState) ? entry.windupState : entry.recoveryState;
                        phaseClip = entry.recoveryClipSeconds;
                        break;
                }
                actionSpeed = phaseClip > 0f && phaseSeconds > 1e-4f ? phaseClip / phaseSeconds : 1f;
                // Acompanhamento em velocidade natural (1,0 a 1,2x); se o clipe acabar antes do core, mistura com a pose de combate em vez de congelar.
                if (evt.Phase != ActionPhase.Windup && phaseClip > 0f)
                    actionSpeed = RecoverySpeed(phaseClip, phaseSeconds);
                if (evt.Phase == ActionPhase.Impact) StartLunge(entry, (float)evt.PhaseSeconds);
                else if (evt.Phase != ActionPhase.Windup) LungeTo(0f, Mathf.Max(0.05f, (float)evt.PhaseSeconds * 0.9f));
                if (HasAnimator && actionLayerIndex >= 0) PlayIfExists(phaseState, actionLayerIndex, windupOffset);
                if (evt.Phase == ActionPhase.Impact && entry.impactVfx != null && vfxPool != null)
                    vfxPool.Play(entry.impactVfx, FindAnchor(entry.anchor).position, transform.rotation, entry.vfxSeconds);
                return;
            }

            float start, authored;
            var impactPhase = false;
            var continuing = false;
            switch (evt.Phase)
            {
                case ActionPhase.Windup:
                    if (ContinuePreRoll(entry, (float)evt.PhaseSeconds)) return;
                    // Golpe carregado: a preparação parte do quadro "arma atrás" (holdAt), onde a camada Upper congelou a pose.
                    start = entry != null && entry.holdAt > 0f && entry.holdAt < windupEnd ? entry.holdAt : 0f;
                    if (start > 0f && ReferenceEquals(entry, chargeEntry) && chargeHoldAt > start && chargeHoldAt < windupEnd) start = chargeHoldAt; // continua da pose em que a carga parou
                    authored = (windupEnd - start) * clip;
                    windupHoldTimer = -1f;
                    if (evt.PhaseSeconds > 1e-4 && authored < (float)evt.PhaseSeconds * 0.999f)
                    {
                        // Telegrafo longo: o trecho autoral toca em velocidade natural e a pose armada segura (windupHoldSpeed) ate o impacto do core.
                        windupHoldTimer = authored;
                        authored = (float)evt.PhaseSeconds; // so para a velocidade sair 1,0 abaixo
                    }
                    else if (evt.PhaseSeconds > 1e-4 && authored > (float)evt.PhaseSeconds * skillSet.maxWindupSpeed)
                    {
                        // Preparacao legivel: no maximo maxWindupSpeed; o que nao couber fica para tras (comeca mais adiante no clipe).
                        authored = (float)evt.PhaseSeconds * skillSet.maxWindupSpeed;
                        start = windupEnd - authored / clip;
                    }
                    break;
                case ActionPhase.Impact:
                    start = windupEnd;
                    authored = (impactEnd - windupEnd) * clip;
                    StartLunge(entry, (float)evt.PhaseSeconds);
                    impactPhase = true;
                    if (entry != null && entry.impactVfx != null && vfxPool != null)
                    {
                        var anchor = FindAnchor(entry.anchor);
                        vfxPool.Play(entry.impactVfx, anchor.position, transform.rotation, entry.vfxSeconds);
                    }
                    break;
                default:
                    start = impactEnd;
                    authored = (1f - impactEnd) * clip;
                    LungeTo(0f, Mathf.Max(0.05f, (float)evt.PhaseSeconds * 0.9f));
                    if (trackAction && ReferenceEquals(trackedEntry, entry) && entry != null)
                    {
                        // O swing do impacto continuou dentro da recuperacao: segue de onde o clipe esta, sem voltar ao ponto de impactEnd.
                        continuing = true;
                        authored = Mathf.Max(0f, clip - actionPos);
                    }
                    break;
            }

            // velocidade = duração autoral da fase / duração da fase no CSV (seção 3.3).
            actionSpeed = evt.PhaseSeconds > 1e-4 && authored > 0f ? authored / (float)evt.PhaseSeconds : 1f;
            // Recuperacao: acompanhamento em velocidade natural (cauda do clipe de 1,0 a 1,2x); clipe curto = mistura no fim, clipe longo = saida da logica.
            if (evt.Phase == ActionPhase.Recovery) actionSpeed = RecoverySpeed(authored, (float)evt.PhaseSeconds);
            if (impactPhase && entry != null)
            {
                // Impacto legivel (4 a 5 quadros): o swing termina impactCarrySeconds depois do fim da fase de impacto, em velocidade natural no minimo.
                // O quadro de impacto do core nao muda (a fase comeca aqui); o resto vira acompanhamento.
                var stretched = authored / ((float)evt.PhaseSeconds + skillSet.impactCarrySeconds);
                actionSpeed = Mathf.Min(actionSpeed, Mathf.Max(1f, stretched));
                trackAction = true;
                trackedEntry = entry;
                actionPos = start * clip;
            }
            if (!continuing && HasAnimator && actionLayerIndex >= 0) PlayIfExists(state, actionLayerIndex, start * clip);
        }

        // ---- acompanhamento, saida do clipe e peso (rev3)

        float ExitBlendSeconds => skillSet != null ? skillSet.actionExitBlendSeconds : ActionExitBlendSeconds;

        // Velocidade do acompanhamento: a cauda do clipe (tail, s) em velocidade natural, entre recoveryMinSpeed e recoveryMaxSpeed; se ainda assim
        // acabar antes da recuperacao do core, agenda a mistura com a pose de combate (clipEndBlendSeconds) em vez de congelar no ultimo quadro.
        float RecoverySpeed(float tail, float phaseSeconds)
        {
            clipEndTimer = -1f;
            if (tail <= 0f) return 1f;
            var ratio = phaseSeconds > 1e-4f ? tail / phaseSeconds : 1f;
            var speed = Mathf.Clamp(ratio, skillSet.recoveryMinSpeed, skillSet.recoveryMaxSpeed);
            if (tail / speed < phaseSeconds - 0.03f) clipEndTimer = tail / speed;
            return speed;
        }

        void EndActionClip()
        {
            actionSpeed = 1f;
            actionClipEnded = true;
            if (HasAnimator && skillSet != null && actionLayerIndex >= 0) PlayIfExists(skillSet.emptyState, actionLayerIndex, 0f, skillSet.clipEndBlendSeconds);
        }

        void StartLunge(SkillPresentationEntry entry, float impactSeconds)
        {
            if (entry == null) return;
            if (entry.shakeMeters > 0f)
            {
                if (followCamera == null) followCamera = FindAnyObjectByType<FollowCamera>();
                if (followCamera != null) followCamera.AddHeroShake(entry.shakeMeters);
            }
            if (modelRoot == null || Mathf.Abs(entry.lungeMeters) < 1e-4f) return;
            lungeTarget = entry.lungeMeters;
            lungeRate = Mathf.Abs(entry.lungeMeters - lunge) / Mathf.Max(0.04f, impactSeconds);
        }

        void LungeTo(float target, float seconds)
        {
            if (modelRoot == null) return;
            lungeTarget = target;
            lungeRate = Mathf.Abs(lunge - target) / Mathf.Max(0.02f, seconds);
        }

        void ApplyLunge(float dt)
        {
            if (modelRoot == null) return;
            if (hitKick.sqrMagnitude > 1e-8f) hitKick = Vector3.MoveTowards(hitKick, Vector3.zero, hitKick.magnitude / Mathf.Max(0.02f, skillSet != null ? skillSet.hitKickSeconds : 0.18f) * dt);
            if (lunge == 0f && lungeTarget == 0f && hitKick.sqrMagnitude < 1e-8f)
            {
                if (lungeApplied)
                {
                    modelRoot.localPosition = modelBaseLocal;
                    lungeApplied = false;
                }
                return;
            }
            lunge = Mathf.MoveTowards(lunge, lungeTarget, lungeRate * dt);
            var forward = modelRoot.parent != null ? modelRoot.parent.InverseTransformDirection(transform.forward) : transform.forward;
            var kick = modelRoot.parent != null ? modelRoot.parent.InverseTransformDirection(hitKick) : hitKick;
            modelRoot.localPosition = modelBaseLocal + forward.normalized * lunge + kick;
            lungeApplied = true;
        }

        // ---- antecipacao no aperto

        void BeginPreRoll(Echoes.Interop.SkillInfo skill)
        {
            preRoll = null;
            if (!HasAnimator || actionLayerIndex < 0 || skill == null || skillSet == null || !skillSet.TryGet(skill.Id, out var entry)) return;
            string state;
            float start, end;
            if (entry.HasPhaseStates)
            {
                state = entry.windupState;
                start = entry.windupFrom * entry.windupClipSeconds;
                end = entry.windupTo * entry.windupClipSeconds;
            }
            else
            {
                state = entry.animatorState;
                start = 0f;
                end = entry.windupEnd * entry.clipSeconds;
            }
            var windup = WindupSecondsOf(skill);
            if (string.IsNullOrEmpty(state) || end - start < 0.02f || windup < 1e-3) return;
            // Teto de velocidade da preparacao: o que nao couber fica para tras (comeca mais adiante no clipe).
            var maxSpan = (float)windup * skillSet.maxWindupSpeed;
            if (end - start > maxSpan) start = end - maxSpan;
            var hold = start + (end - start) * skillSet.preRollHoldFraction;
            preRoll = new PreRoll { Entry = entry, Pos = start, HoldPos = hold, EndPos = end, Rate = (end - start) / (float)windup };
            actionSpeed = preRoll.Rate;
            PlayIfExists(state, actionLayerIndex, start);
        }

        void TickPreRoll(float dt)
        {
            preRoll.Elapsed += dt;
            preRoll.Pos += actionSpeed * dt;
            if (preRoll.Pos >= preRoll.HoldPos) actionSpeed = 0f; // armado: segura a pose ate o core iniciar o golpe (o leve nao toca inteiro: segurar vira carga)
            if (preRoll.Elapsed > PreRollMaxSeconds) CancelPreRoll();
        }

        void CancelPreRoll()
        {
            if (preRoll == null) return;
            preRoll = null;
            actionSpeed = 1f;
            if (HasAnimator && skillSet != null && actionLayerIndex >= 0) PlayIfExists(skillSet.emptyState, actionLayerIndex, 0f, ExitBlendSeconds);
        }

        /// <summary>Tempo maximo de espera da pose armada sem o core iniciar o golpe (segurar vira carga em 0,35 s; mais que isso e um aperto que nao virou golpe).</summary>
        public const float PreRollMaxSeconds = 0.8f;

        // A preparacao do core chegou: se a antecipacao deste golpe ja esta tocando, so ajusta a velocidade para fechar o resto na preparacao que falta.
        bool ContinuePreRoll(SkillPresentationEntry entry, float phaseSeconds)
        {
            var current = preRoll;
            if (current == null || !ReferenceEquals(current.Entry, entry)) return false;
            preRoll = null;
            var remaining = Mathf.Max(0f, current.EndPos - current.Pos);
            actionSpeed = phaseSeconds > 1e-4f ? remaining / phaseSeconds : 1f;
            return true;
        }

        double WindupSecondsOf(Echoes.Interop.SkillInfo skill)
        {
            var rules = root != null && root.Rules != null ? root.Rules.Core : null;
            var self = Self;
            if (rules == null || self == null || skill == null) return skill != null ? skill.Windup : 0.0;
            return rules.GetActionTiming(self.Stats, skill).Windup;
        }

        // Recuperação da habilidade com a velocidade de ataque do herói (o core), para o clipe do impacto cobrir impacto + recuperação.
        double RecoverySecondsOf(Echoes.Interop.SkillInfo skill)
        {
            var rules = root != null && root.Rules != null ? root.Rules.Core : null;
            var self = Self;
            if (rules == null || self == null || skill == null) return skill != null ? skill.Recovery : 0.0;
            return rules.GetActionTiming(self.Stats, skill).Recovery;
        }

        /// <summary>Evento de clipe (AnimationEventRelay): "release" do Espectro no quadro 20, "summon_marks" e "slam" do rugido do Guardiao.</summary>
        public event System.Action<string> ClipEvent;

        public void HandleClipEvent(string clipEvent) => ClipEvent?.Invoke(clipEvent);

        // Fase do chefe (core): o rugido toca na camada Action com a velocidade ajustada a transitionSeconds; o parametro Phase acompanha.
        void OnBossState(in BossStateEvent evt)
        {
            if (!ReferenceEquals(evt.Owner, Self) || evt.Kind != Echoes.Interop.BossEventKind.PhaseStart || !HasAnimator) return;
            if (hasPhase) animator.SetInteger(PhaseParam, evt.Phase);
            if (skillSet == null || actionLayerIndex < 0) return;
            actionSpeed = evt.Seconds > 1e-4 ? skillSet.roarClipSeconds / (float)evt.Seconds : 1f;
            PlayIfExists(skillSet.roarState, actionLayerIndex, 0f);
        }

        void OnDodge(in DodgeStartedEvent evt)
        {
            if (ReferenceEquals(evt.Owner, Self)) CancelPreRoll();
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
            dissolveDelayLeft = enemyController != null && skillSet != null ? skillSet.deathDissolveDelaySeconds : 0f;
            trackAction = false;
            clipEndTimer = -1f;
            windupHoldTimer = -1f;
            LungeTo(0f, 0.1f);
        }

        void OnRevived(in CombatantRevivedEvent evt)
        {
            if (!ReferenceEquals(evt.Target, Self)) return;
            if (HasAnimator && hasIsDead) animator.SetBool(IsDeadParam, false);
            dissolveProgress = -1f;
            for (var i = 0; i < dissolveMaterials.Count; i++) dissolveMaterials[i].SetFloat(DissolveId, 0f);
        }

        /// <summary>Entrada curta na camada Action/Hit (fade fixo): sem o corte seco do Play, e o quadro de impacto continua nos tempos do core.</summary>
        public const float ActionBlendSeconds = 0.06f;

        /// <summary>Saída da ação para o repouso: fade mais longo, para o corpo voltar à locomoção sem tranco.</summary>
        public const float ActionExitBlendSeconds = 0.15f;

        // offsetSeconds: início dentro do estado, em segundos do clipe (CrossFadeInFixedTime).
        void PlayIfExists(string state, int layer, float offsetSeconds, float blendSeconds = ActionBlendSeconds)
        {
            if (string.IsNullOrEmpty(state)) return;
            var hash = Animator.StringToHash(state);
            if (animator.HasState(layer, hash)) animator.CrossFadeInFixedTime(hash, blendSeconds, layer, offsetSeconds);
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
