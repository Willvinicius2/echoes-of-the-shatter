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
        [Tooltip("Escreve no Console cada troca de estado da IA (roteiro RF-20).")]
        [SerializeField] bool logStateChanges;

        AttributeComponent attributes;
        NavMeshAgent agent;
        CharacterController body;
        CombatSystem combat;
        float repathTimer;
        float deadTime;

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
            var combatant = attributes.CreateEnemy(rules, info, level, radius);
            Logic = new EnemyCombatLogic(combatant, rules);
            if (logStateChanges) Logic.StateChanged += LogStateChange;
            combat.Register(combatant, Logic, CombatOrderKey.Of(transform));

            if (agent != null)
            {
                agent.updateRotation = false; // o giro segue o dado (turnRate) na lógica
                agent.stoppingDistance = 0f;  // quem para é a IA (alcance do ataque)
                agent.autoBraking = true;
            }
        }

        // Sai do combate ao desligar (e antes do OnDestroy de qualquer componente), pela referência própria:
        // o AttributeComponent pode descartar os handles antes deste script no OnDestroy.
        void OnDisable()
        {
            if (Logic != null && combat != null) combat.Unregister(Logic.Self);
        }

        void OnDestroy()
        {
            if (Logic != null) Logic.StateChanged -= LogStateChange;
        }

        void Update()
        {
            var combatant = Logic != null ? Logic.Self : null;
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
            var knockback = combatant.ConsumeKnockback(dt);
            var dead = combatant.IsDead;

            if (agent != null && agent.enabled && agent.isOnNavMesh)
            {
                if (!dead && Logic.WantsToMove)
                {
                    agent.isStopped = false;
                    agent.speed = Logic.ChaseSpeed;
                    repathTimer -= dt;
                    if (repathTimer <= 0f)
                    {
                        repathTimer = repathInterval;
                        agent.SetDestination(Logic.MoveTarget.ToWorld(transform.position.y));
                    }
                }
                else if (!agent.isStopped)
                {
                    agent.isStopped = true;
                    agent.velocity = Vector3.zero;
                    repathTimer = 0f;
                }
                if (!knockback.IsZero) agent.Move(knockback.ToWorld());
            }
            else
            {
                var motion = (dead ? PlanarVector.Zero : Logic.DirectVelocity() * dt) + knockback;
                if (body != null && body.enabled) body.Move(motion.ToWorld(Physics.gravity.y * dt));
                else transform.position += motion.ToWorld();
            }

            if (!dead) transform.rotation = combatant.Forward.ToRotation(transform.rotation);
            combatant.Position = transform.position.ToPlanar();
        }

        void LogStateChange(EnemyBrainState from, EnemyBrainState to)
        {
            Debug.Log($"[AI] {name} ({enemyId}): {from} → {to}", this);
        }
    }
}
