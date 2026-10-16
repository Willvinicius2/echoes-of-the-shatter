using System.Collections.Generic;
using Echoes.Interop;
using UnityEngine;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Herói jogável (Guerreiro): monta os atributos pelo motor de regras, registra no combate,
    /// entrega a entrada (WASD relativo à câmera, mira no mouse pelo plano do chão) à
    /// <see cref="HeroCombatLogic"/> e move o <see cref="CharacterController"/> com a velocidade que
    /// a lógica devolve. Morte: volta ao checkpoint com vida e poções cheias (RF-18).
    /// </summary>
    [DefaultExecutionOrder(-940)]
    [DisallowMultipleComponent]
    [RequireComponent(typeof(CharacterController))]
    [RequireComponent(typeof(AttributeComponent))]
    public sealed class HeroController : MonoBehaviour
    {
        [SerializeField] CombatSystemHost combatHost;
        [SerializeField] PlayerInputHandler input;
        [Tooltip("Câmera usada para a mira. Vazio = Camera.main.")]
        [SerializeField] Camera aimCamera;

        [Header("Personagem (IDs de conteúdo; virão do save)")]
        [SerializeField] string classId = "class.warrior";
        [Tooltip("Nível do herói. Libera as habilidades pelo unlockLevel do skills.csv.")]
        [SerializeField, Min(1)] int level = 5;
        [Tooltip("Bases de item equipadas (a arma define o dano das habilidades que escalam com arma).")]
        [SerializeField] string[] equipment = { "item_base.iron_sword" };
        [Tooltip("Barra: botão esquerdo (ataque básico), botão direito, Q, E, R, F.")]
        [SerializeField] string[] skillBar =
        {
            "skill.warrior.iron_cut",
            "skill.warrior.charge",
            "skill.warrior.stone_rift",
            "skill.warrior.shield_bash",
            "",
            "",
        };

        [Header("Checkpoint (RF-18)")]
        [Tooltip("Onde o herói volta ao morrer. Vazio = posição inicial.")]
        [SerializeField] Transform checkpoint;
        [Tooltip("Segundos entre a morte e a volta (RF-18 pede menos de 2 s no chefe).")]
        [SerializeField, Min(0f)] float respawnDelay = 1.5f;

        CharacterController controller;
        AttributeComponent attributes;
        CombatSystem combat;
        Vector3 spawnPosition;
        Quaternion spawnRotation;
        float verticalSpeed;
        float deadTime;

        public HeroCombatLogic Logic { get; private set; }
        public Combatant Combatant => attributes != null ? attributes.Combatant : null;
        public PlayerInputHandler InputHandler => input;
        public float SecondsUntilRespawn => Combatant != null && Combatant.IsDead ? Mathf.Max(0f, respawnDelay - deadTime) : 0f;

        void Awake()
        {
            controller = GetComponent<CharacterController>();
            attributes = GetComponent<AttributeComponent>();
            spawnPosition = transform.position;
            spawnRotation = transform.rotation;
        }

        void Start()
        {
            combatHost = CombatSystemHost.Resolve(combatHost, this);
            if (input == null) input = GetComponent<PlayerInputHandler>();
            if (input == null) input = FindAnyObjectByType<PlayerInputHandler>();
            if (aimCamera == null) aimCamera = Camera.main;
            combat = combatHost != null ? combatHost.Combat : null;
            if (combat == null || input == null)
            {
                Debug.LogError("[Hero] Falta CombatSystemHost ativo ou PlayerInputHandler; herói desligado.", this);
                enabled = false;
                return;
            }

            var rules = combat.Rules;
            var classInfo = rules.FindClass(classId);
            if (classInfo == null)
            {
                Debug.LogError($"[Hero] Classe '{classId}' não existe no CSV.", this);
                enabled = false;
                return;
            }

            ItemBaseInfo weapon = null;
            var equipped = new List<string>(equipment.Length);
            for (var i = 0; i < equipment.Length; i++)
            {
                var item = rules.FindItemBase(equipment[i]);
                if (item == null)
                {
                    if (!string.IsNullOrEmpty(equipment[i])) Debug.LogWarning($"[Hero] Base de item '{equipment[i]}' não existe; ignorada.", this);
                    continue;
                }
                equipped.Add(item.Id);
                if (weapon == null && item.IsWeapon) weapon = item;
            }

            var build = new HeroBuild(classInfo.Id, level, equipped);
            var combatant = attributes.CreateHero(rules, in build, classInfo, weapon, controller.radius);
            Logic = new HeroCombatLogic(combatant, rules, skillBar);
            combat.Register(combatant, Logic, CombatOrderKey.Of(transform));
        }

        // Sai do combate ao desligar (e antes do OnDestroy de qualquer componente), pela referência própria:
        // o AttributeComponent pode descartar os handles antes deste script no OnDestroy.
        void OnEnable()
        {
            if (Logic != null && combat != null && !Logic.Self.IsRegistered) combat.Register(Logic.Self, Logic, CombatOrderKey.Of(transform));
        }

        void OnDisable()
        {
            if (Logic != null && combat != null) combat.Unregister(Logic.Self);
        }

        void Update()
        {
            if (Logic == null) return;
            var combatant = Logic.Self;

            if (combatant.IsDead)
            {
                deadTime += Time.deltaTime;
                if (deadTime >= respawnDelay) Respawn();
                return;
            }
            deadTime = 0f;

            Logic.MoveInput = CameraRelative(input.Move);
            if (TryGetAimPoint(out var aimPoint)) Logic.AimPoint = aimPoint;

            var pressedAny = false;
            for (var c = HeroCommand.BasicAttack; c <= HeroCommand.Potion2; c++)
            {
                if (!input.WasPressed(c)) continue;
                Logic.Press(c);
                pressedAny = true;
            }
            // Segurar o botão do ataque básico repete o golpe assim que a ação anterior termina,
            // sem passar por cima de outro comando pedido neste quadro ou ainda no buffer.
            if (!pressedAny && !Logic.HasPendingCommand && Logic.IsReadyForAction && input.IsHeld(HeroCommand.BasicAttack))
                Logic.Press(HeroCommand.BasicAttack);
        }

        void LateUpdate()
        {
            if (Logic == null) return;
            var dt = Time.deltaTime;
            var velocity = Logic.CurrentVelocity();

            if (controller.isGrounded && verticalSpeed < 0f) verticalSpeed = 0f;
            verticalSpeed += Physics.gravity.y * dt;
            var motion = velocity.ToWorld(verticalSpeed) * dt;
            if (controller.enabled) controller.Move(motion);

            var combatant = Logic.Self;
            transform.rotation = Logic.FacingDirection().ToRotation(transform.rotation);
            combatant.Position = transform.position.ToPlanar();
        }

        void Respawn()
        {
            deadTime = 0f;
            var position = checkpoint != null ? checkpoint.position : spawnPosition;
            var rotation = checkpoint != null ? checkpoint.rotation : spawnRotation;
            controller.enabled = false; // o CharacterController ignora teleporte com ele ligado
            transform.SetPositionAndRotation(position, rotation);
            controller.enabled = true;
            verticalSpeed = 0f;
            Logic.Self.Position = position.ToPlanar();
            combat.Revive(Logic.Self);
        }

        /// <summary>WASD → direção no chão relativa à câmera (W sobe na tela).</summary>
        PlanarVector CameraRelative(Vector2 move)
        {
            if (move.sqrMagnitude < 1e-6f) return PlanarVector.Zero;
            if (aimCamera == null) return move.ToPlanar();
            var forward = aimCamera.transform.forward.ToPlanar().NormalizedOr(PlanarVector.Forward);
            var right = aimCamera.transform.right.ToPlanar().NormalizedOr(new PlanarVector(1f, 0f));
            return (right * move.x + forward * move.y).ClampMagnitude(1f);
        }

        /// <summary>Raio do mouse × plano horizontal na altura do herói (docs/04, seção 3.1). Sem raycast na malha.</summary>
        bool TryGetAimPoint(out PlanarVector point)
        {
            point = default;
            if (aimCamera == null) return false;
            var ray = aimCamera.ScreenPointToRay(input.AimScreenPosition);
            var ground = new Plane(Vector3.up, transform.position);
            if (!ground.Raycast(ray, out var distance)) return false;
            point = ray.GetPoint(distance).ToPlanar();
            return true;
        }
    }
}
