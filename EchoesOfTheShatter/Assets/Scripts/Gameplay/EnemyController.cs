using UnityEngine;
using UnityEngine.AI;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Inimigo na cena: monta os atributos pelo motor de regras, registra no combate com a
    /// <see cref="EnemyCombatLogic"/> e aplica o movimento que ela pede. Usa o <see cref="NavMeshAgent"/>
    /// quando há NavMesh assada; sem NavMesh, anda direto até o alvo (cena de teste rápida).
    /// </summary>
    [DefaultExecutionOrder(-930)]
    [DisallowMultipleComponent]
    [RequireComponent(typeof(AttributeComponent))]
    public sealed class EnemyController : MonoBehaviour
    {
        [SerializeField] CombatSystemHost combatHost;
        [Tooltip("ID do enemies.csv (ex.: enemy.hollow_sentinel).")]
        [SerializeField] string enemyId = "enemy.hollow_sentinel";
        [Tooltip("Nível do monstro (Cripta Partida: 2 a 4).")]
        [SerializeField, Min(1)] int level = 3;
        [Tooltip("Raio do corpo no plano, em metros. 0 = raio do NavMeshAgent/CharacterController.")]
        [SerializeField, Min(0f)] float bodyRadius;
        [Tooltip("Segundos até desligar o corpo depois da morte (a apresentação dissolve antes).")]
        [SerializeField, Min(0f)] float corpseSeconds = 2.5f;
        [Tooltip("Intervalo de recálculo do caminho do agente, em segundos (técnico, não é balanceamento).")]
        [SerializeField, Min(0.05f)] float repathInterval = 0.2f;
        [Tooltip("Elite sorteado: o core sorteia o modificador no fluxo de eventos e aplica os multiplicadores (docs/13, item 5).")]
        [SerializeField] bool rolledElite;
        [Header("Cripta (docs/14)")]
        [Tooltip("Parado e sem IA até alguém ativar (o Guardião antes do gatilho da arena).")]
        [SerializeField] bool startDormant;
        [Tooltip("Pontos da patrulha (mundo); vazio = parado. Vai e volta enquanto a IA está em Idle.")]
        [SerializeField] Vector3[] patrolPoints;
        [Tooltip("Escreve no Console cada troca de estado da IA (roteiro RF-20).")]
        [SerializeField] bool logStateChanges;

        AttributeComponent attributes;
        NavMeshAgent agent;
        CharacterController body;
        CombatSystem combat;
        float repathTimer;
        float deadTime;
        Vector3 spawnPosition;
        Quaternion spawnRotation;
        int patrolIndex;
        float patrolSpeedMult = 1f;
        float onScreenMarginMeters;
        PlanarVector agentSyncedPosition;
        PlanarVector approachDirection;   // lado do herói por onde este inimigo chega (vaga fixa durante a perseguição)
        bool hasApproachDirection;
        float notChasingTime;
        Camera visibleAreaCamera;

        public EnemyCombatLogic Logic { get; private set; }
        public Combatant Combatant => attributes != null ? attributes.Combatant : null;
        public string EnemyId => enemyId;

        void Awake()
        {
            attributes = GetComponent<AttributeComponent>();
            agent = GetComponent<NavMeshAgent>();
            body = GetComponent<CharacterController>();
        }

        void Start()
        {
            combatHost = CombatSystemHost.Resolve(combatHost, this);
            combat = combatHost != null ? combatHost.Combat : null;
            if (combat == null)
            {
                enabled = false;
                return;
            }
            var rules = combat.Rules;
            var info = rules.FindEnemy(enemyId);
            if (info == null)
            {
                Debug.LogError($"[Enemy] Inimigo '{enemyId}' não existe no CSV.", this);
                enabled = false;
                return;
            }

            var radius = bodyRadius > 0f ? bodyRadius : agent != null ? agent.radius : body != null ? body.radius : 0.5f;
            // Elite sorteado (fluxo de eventos) ou elite fixo (modifierId do enemies.csv): o core aplica os multiplicadores.
            var elite = rolledElite
                ? combat.RollElite()
                : !string.IsNullOrEmpty(info.ModifierId) ? rules.GetEliteProfile(info.ModifierId, false) : default;
            var combatant = attributes.CreateEnemy(rules, info, level, radius, elite);
            Logic = new EnemyCombatLogic(combatant, rules);
            Logic.IntegratesMovement = agent == null || !agent.enabled;
            Logic.Dormant = startDormant;
            // R-VIS-1 e patrulha vêm dos dados pelo core (requireOnScreen do enemy_ai.csv, patrolSpeedMult do enemies.csv e
            // require_on_screen_margin do rules.csv); a área visível sai do frustum da câmera.
            patrolSpeedMult = (float)info.PatrolSpeedMult;
            onScreenMarginMeters = WorldUnits.ToMeters(rules.Combat.RequireOnScreenMarginUu);
            Logic.RequireOnScreen = info.RequireOnScreen;
            if (info.RequireOnScreen) Logic.IsInsideVisibleArea = IsInsideVisibleArea;
            Logic.IsDashBlocked = IsDashBlocked;
            spawnPosition = transform.position;
            spawnRotation = transform.rotation;
            agentSyncedPosition = combatant.Position;
            if (logStateChanges) Logic.StateChanged += LogStateChange;
            combat.Register(combatant, Logic, CombatOrderKey.Of(transform));

            if (agent != null)
            {
                agent.updateRotation = false; // o giro segue o dado (turnRate) na lógica
                agent.stoppingDistance = 0f;  // quem para é a IA (alcance do ataque)
                // Sem frenagem automatica do agente: ele freava ja a metros do destino (a posicao do heroi) e o inimigo se arrastava; quem para e a IA
                // (alcance do golpe) e a desaceleracao vem do EnemyDecelSeconds do feel.
                agent.autoBraking = false;
                // Evasao: prioridades diferentes quebram a simetria entre vizinhos (valores no SO_CombatFeel); o inimigo nao desacelera so para nao esbarrar no vizinho.
                var avoidFeel = combat.Feel;
                if (!combatant.IsBoss) agent.radius = Mathf.Min(agent.radius, avoidFeel.EnemyAvoidanceRadiusMeters);
                agent.avoidancePriority = Mathf.Clamp(avoidFeel.EnemyAvoidancePriorityBase + Mathf.Abs(GetInstanceID()) % Mathf.Max(1, avoidFeel.EnemyAvoidancePrioritySpread), 0, 99);
            }
        }

        /// <summary>Ativa a IA (o gatilho da arena acorda o Guardião).</summary>
        public void Activate()
        {
            if (Logic != null) Logic.Dormant = false;
        }

        /// <summary>
        /// Volta ao ponto de nascimento com vida cheia e a IA no início (checkpoint, saída, reinício da luta): inimigos mortos reaparecem.
        /// <paramref name="dormant"/>: volta parado (chefe, até o gatilho).
        /// </summary>
        public void ResetToSpawn(bool dormant)
        {
            if (Logic == null || combat == null) return;
            deadTime = 0f;
            patrolIndex = 0;
            if (!gameObject.activeSelf) gameObject.SetActive(true); // OnEnable registra de novo no combate
            if (agent != null && agent.enabled && agent.isOnNavMesh)
            {
                agent.ResetPath();
                agent.velocity = Vector3.zero;
                agent.Warp(spawnPosition);
            }
            else
            {
                transform.position = spawnPosition;
            }
            transform.rotation = spawnRotation;
            Logic.Self.Teleport(spawnPosition.ToPlanar());
            agentSyncedPosition = Logic.Self.Position;
            var facing = spawnRotation * Vector3.forward;
            Logic.Self.Forward = facing.ToPlanar().NormalizedOr(PlanarVector.Forward);
            combat.Revive(Logic.Self);
            Logic.Dormant = dormant;
        }

        void OnEnable()
        {
            if (Logic != null && combat != null && !Logic.Self.IsRegistered) combat.Register(Logic.Self, Logic, CombatOrderKey.Of(transform));
        }

        // Área visível do herói reduzida pela margem (frustum da câmera, não números fixos): R-VIS-1.
        bool IsInsideVisibleArea(PlanarVector position)
        {
            var heroCombatant = combat != null ? combat.Hero : null;
            if (heroCombatant == null) return true;
            if (visibleAreaCamera == null) visibleAreaCamera = Camera.main;
            if (visibleAreaCamera == null) return true;
            return VisibleArea.Contains(visibleAreaCamera, heroCombatant.Position, position, onScreenMarginMeters);
        }

        // A investida do chefe bateria em pilar ou parede? Varre uma esfera do corpo ao longo do passo, ignorando personagens.
        bool IsDashBlocked(PlanarVector from, PlanarVector to, float radius)
        {
            var delta = to - from;
            var distance = delta.Magnitude;
            if (distance < 1e-4f) return false;
            var direction = new Vector3(delta.X / distance, 0f, delta.Z / distance);
            var origin = new Vector3(from.X, radius + 0.6f, from.Z); // acima do piso
            var hits = Physics.SphereCastAll(origin, radius, direction, distance, ~0, QueryTriggerInteraction.Ignore);
            for (var i = 0; i < hits.Length; i++)
            {
                var c = hits[i].collider;
                if (c.GetComponentInParent<CharacterController>() != null || c.transform.IsChildOf(transform)) continue;
                return true;
            }
            return false;
        }

        // Sai do combate ao desligar (e antes do OnDestroy de qualquer componente), pela referência própria:
        // o AttributeComponent pode descartar os handles antes deste script no OnDestroy.
        void OnDisable()
        {
            if (Logic != null && combat != null) combat.Unregister(Logic.Self);
        }

        void OnDestroy()
        {
            if (Logic == null) return;
            Logic.StateChanged -= LogStateChange;
            Logic.Dispose();
        }

        void Update()
        {
            var combatant = Logic != null ? Logic.Self : null;
            if (combatant != null && TestSettings.EnemyGodMode && !combatant.IsDead)
            {
                var vitals = combatant.Vitals;
                vitals.Life = combatant.MaxLife; // so teste (gravacao): nunca vem do CSV
                combatant.SetVitals(in vitals);
            }
            if (combatant == null || !combatant.IsDead) return;
            deadTime += Time.deltaTime;
            if (deadTime < corpseSeconds) return;
            gameObject.SetActive(false); // OnDisable tira do combate
        }

        void LateUpdate()
        {
            if (Logic == null) return;
            var combatant = Logic.Self;
            var dt = Time.deltaTime;
            var dead = combatant.IsDead;
            // A posição lógica (perseguição sem agente e knockback) avança só no passo fixo (A-04).
            var wanted = combatant.InterpolatedPosition(combat != null ? combat.Clock.Alpha : 1.0);
            var delta = wanted - transform.position.ToPlanar();
            // knockback = tudo o que a lógica deslocou além de onde o agente está

            if (agent != null && agent.enabled && agent.isOnNavMesh)
            {
                var feel = combat != null ? combat.Feel : null;
                if (!dead && Logic.WantsToMove) notChasingTime = 0f;
                else if ((notChasingTime += dt) > 1f) hasApproachDirection = false; // a proxima perseguicao escolhe a vaga de novo
                if (!dead && Logic.WantsToMove)
                {
                    agent.isStopped = false;
                    agent.speed = Logic.ChaseSpeed;
                    agent.acceleration = RampAcceleration(Logic.ChaseSpeed, feel != null ? feel.EnemyAccelSeconds : 0f);
                    repathTimer -= dt;
                    if (repathTimer <= 0f)
                    {
                        repathTimer = repathInterval;
                        agent.SetDestination(ApproachPoint(feel).ToWorld(transform.position.y));
                    }
                }
                else if (!dead && !Logic.Dormant && patrolPoints != null && patrolPoints.Length > 1 && Logic.Brain.State == EnemyBrainState.Idle)
                {
                    Patrol(dt);
                }
                else if (!agent.isStopped)
                {
                    // Para frenando (EnemyDecelSeconds do feel), sem zerar a velocidade de uma vez: o pe nao trava de repente.
                    agent.acceleration = RampAcceleration(Mathf.Max(agent.speed, agent.velocity.magnitude), feel != null ? feel.EnemyDecelSeconds : 0f);
                    agent.isStopped = true;
                    repathTimer = 0f;
                }
                // Com agente, só o knockback (vindo da lógica) é deslocamento externo; o resto é do agente. O knockback é o que a lógica mexeu na posição
                // desde a última sincronia com o corpo (não "posição lógica menos corpo": o passo do próprio agente cancelaria o movimento todo).
                var pushed = combatant.Position - agentSyncedPosition;
                if (pushed.Magnitude > 1e-5f) agent.Move(pushed.ToWorld());
                combatant.Teleport(transform.position.ToPlanar());
                agentSyncedPosition = combatant.Position;
            }
            else
            {
                if (body != null && body.enabled) body.Move(delta.ToWorld(Physics.gravity.y * dt));
                else transform.position += delta.ToWorld();
                var actual = transform.position.ToPlanar();
                if (PlanarVector.Distance(actual, wanted) > 1e-3f) combatant.Teleport(actual);
            }

            if (!dead)
            {
                var wanted3 = combatant.Forward.ToRotation(transform.rotation);
                var feelTurn = combat != null ? combat.Feel : null;
                if (feelTurn == null || combatant.IsBoss) transform.rotation = wanted3; // o chefe usa a direcao exata do core (escudo frontal, travas)
                else
                {
                    var state = Logic.Brain.State;
                    var calm = state == EnemyBrainState.Idle || state == EnemyBrainState.Chase || state == EnemyBrainState.Recover;
                    var degrees = calm ? feelTurn.EnemyTurnDegreesPerSecond : feelTurn.EnemyAttackTurnDegreesPerSecond;
                    transform.rotation = Quaternion.RotateTowards(transform.rotation, wanted3, degrees * dt);
                }
            }
        }

        // Ponto de chegada da perseguicao: o anel de alcance do golpe em volta do alvo, na vaga deste inimigo (angulo fixo por inimigo dentro de
        // +-EnemySurroundSpreadDegrees a partir do lado de onde ele veio). Chefe, alvo ausente ou espalhamento 0: o proprio alvo.
        PlanarVector ApproachPoint(CombatFeelValues feel)
        {
            var target = Logic.MoveTarget;
            if (feel == null || feel.EnemySurroundSpreadDegrees <= 0f || Logic.Self.IsBoss) return target;
            if (!hasApproachDirection)
            {
                var fromTarget = (Logic.Self.Position - target).NormalizedOr(PlanarVector.Forward);
                var slot = (Mathf.Abs(GetInstanceID()) % 7 / 3f - 1f) * feel.EnemySurroundSpreadDegrees; // -spread..+spread, estavel por inimigo
                var radians = slot * Mathf.Deg2Rad;
                var cos = Mathf.Cos(radians);
                var sin = Mathf.Sin(radians);
                approachDirection = new PlanarVector(fromTarget.X * cos - fromTarget.Z * sin, fromTarget.X * sin + fromTarget.Z * cos);
                hasApproachDirection = true;
            }
            var heroRadius = combat != null && combat.Hero != null ? combat.Hero.RadiusMeters : 0.5f;
            var ring = Logic.StopDistance * feel.EnemyApproachFraction + heroRadius;
            return target + approachDirection * ring;
        }

        // NavMeshAgent.acceleration em m/s2 que leva a 'speed' em 'seconds' (0 s = praticamente instantaneo).
        static float RampAcceleration(float speed, float seconds) => seconds > 1e-4f ? Mathf.Max(1f, speed / seconds) : 1000f;

        // Vai e volta entre os pontos enquanto a IA está parada (Idle); ao ver o herói a IA assume.
        void Patrol(float dt)
        {
            agent.isStopped = false;
            agent.speed = Logic.FullMoveSpeedMeters * patrolSpeedMult;
            agent.acceleration = RampAcceleration(agent.speed, combat != null ? combat.Feel.EnemyAccelSeconds : 0f);
            var target = patrolPoints[patrolIndex];
            repathTimer -= dt;
            if (repathTimer <= 0f)
            {
                repathTimer = repathInterval;
                agent.SetDestination(target);
            }
            var flat = new Vector3(target.x - transform.position.x, 0f, target.z - transform.position.z);
            if (flat.sqrMagnitude < 0.5f * 0.5f)
            {
                patrolIndex = (patrolIndex + 1) % patrolPoints.Length;
                repathTimer = 0f;
            }
            if (agent.velocity.sqrMagnitude > 0.01f) Logic.Self.Forward = agent.velocity.ToPlanar().NormalizedOr(Logic.Self.Forward);
        }

        void LogStateChange(EnemyBrainState from, EnemyBrainState to)
        {
            Debug.Log($"[AI] {name} ({enemyId}): {from} → {to}", this);
        }
    }
}
