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

        /// <summary>Bases de item equipadas (a fonte e o save e o core; o visual modular le daqui o visualSetId pelo conjunto).</summary>
        public System.Collections.Generic.IReadOnlyList<string> EquipmentIds => equipment;
        [Tooltip("Botão esquerdo (ataque básico) e depois as habilidades na ordem Q, E, R, F. O botão direito é a defesa (docs/18) e não entra aqui: a lógica reserva o espaço 1 da barra.")]
        [SerializeField] string[] skillBar =
        {
            "skill.warrior.iron_cut",
            "skill.warrior.charge",
            "skill.warrior.stone_rift",
            "skill.warrior.shield_bash",
            "",
            "",
        };

        [Header("Arqueiro e Mago (-hero archer|mage; docs/18): barra (esquerdo, Q, E, R, F) e equipamento de teste")]
        [SerializeField] string[] archerBar = { "skill.archer.quick_shot", "skill.archer.back_leap", "skill.archer.arrow_rain", "", "" };
        [SerializeField] string[] archerEquipment = { "item_base.hunter_bow" };
        [SerializeField] string[] mageBar = { "skill.mage.arcane_dart", "skill.mage.frost_nova", "skill.mage.arcane_ray", "", "" };
        [SerializeField] string[] mageEquipment = { };

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

        /// <summary>Disparado quando o herói volta ao checkpoint (morte ou saída): inimigos mortos reaparecem, a luta do chefe reinicia.</summary>
        public event System.Action Respawned;

        public Transform Checkpoint => checkpoint;

        /// <summary>Define o checkpoint atual (as zonas de checkpoint e a arena chamam).</summary>
        public void SetCheckpoint(Transform point)
        {
            if (point != null) checkpoint = point;
        }

        /// <summary>Volta ao checkpoint sem morrer (portal de saída): vida e poções cheias, como na morte.</summary>
        public void ReturnToCheckpoint()
        {
            if (Logic == null) return;
            Respawn();
        }

        public HeroCombatLogic Logic { get; private set; }
        public Combatant Combatant => attributes != null ? attributes.Combatant : null;
        public PlayerInputHandler InputHandler => input;
        public float SecondsUntilRespawn => Combatant != null && Combatant.IsDead ? Mathf.Max(0f, respawnDelay - deadTime) : 0f;

        /// <summary>Desvio (m) entre a posição lógica e o corpo a partir do qual a lógica ressincroniza (2 cm).</summary>
        public const float ResyncMeters = 0.02f;

        /// <summary>Diagnóstico: quadros com desvio acima de 1 mm e ressincronizações feitas (modo de gravação e testes).</summary>
        public static int DeviationFrames, ResyncCount;

        PlanarVector lastSceneSync;
        bool hasSceneSync;

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
            // A classe escolhida (-hero ou tela inicial) manda; Arqueiro e Mago nao tem save ainda e jogam com a barra e o equipamento de teste daqui.
            var choice = Echoes.Core.HeroChoice.Id;
            var otherClass = choice == "archer" || choice == "mage";
            if (otherClass)
            {
                classId = Echoes.Core.HeroChoice.ClassId;
                skillBar = choice == "archer" ? archerBar : mageBar;
                equipment = choice == "archer" ? archerEquipment : mageEquipment;
            }
            var classInfo = rules.FindClass(classId);
            if (classInfo == null)
            {
                Debug.LogError($"[Hero] Classe '{classId}' não existe no CSV.", this);
                enabled = false;
                return;
            }

            ItemBaseInfo weapon = null;
            var equipped = new List<string>(equipment.Length);
            // Com save (jogo normal): equipamento e atributos vem do SAVE pelo core (itens com afixos). Sem save (cena aberta direto): as bases do inspetor.
            Echoes.Interop.Native.SaveGame saveSource = null;
            var native = rules as Echoes.Interop.Native.NativeRulesCore;
            if (!otherClass && native != null && Echoes.Core.GameSession.Save != null && Echoes.Core.GameSession.Save.HasSave)
            {
                saveSource = Echoes.Core.GameSession.Save.Current;
                foreach (var item in saveSource.Equipment(0))
                {
                    var info = item != null ? rules.FindItemBase(item.BaseId) : null;
                    if (info == null) continue;
                    equipped.Add(info.Id);
                    if (weapon == null && info.IsWeapon) weapon = info;
                }
            }
            else
            {
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
            }

            var build = new HeroBuild(classInfo.Id, level, equipped, saveSource, 0);
            var combatant = attributes.CreateHero(rules, in build, classInfo, weapon, controller.radius);
            Logic = new HeroCombatLogic(combatant, rules, BuildLogicBar(), BasicKitSource.For(rules, classInfo.Id));
            combat.Register(combatant, Logic, CombatOrderKey.Of(transform));
        }

        // A barra do inspetor lista o botão esquerdo e depois Q, E, R, F; a lógica tem 6 espaços e o 1 (botão direito) é a defesa, sem habilidade.
        string[] BuildLogicBar()
        {
            var bar = new string[HeroCombatLogic.SlotCount];
            for (var i = 0; i < bar.Length; i++) bar[i] = string.Empty;
            if (skillBar == null) return bar;
            if (skillBar.Length > 0) bar[0] = skillBar[0];
            for (var i = 1; i < skillBar.Length && i + 1 < bar.Length; i++) bar[i + 1] = skillBar[i];
            return bar;
        }

        /// <summary>
        /// Depois de equipar ou desequipar pelo inventario (o core ja atualizou o bloco de atributos do heroi): a arma das habilidades passa a ser a da
        /// mao principal do save.
        /// </summary>
        public void OnEquipmentChanged()
        {
            if (Logic == null || combat == null) return;
            var save = Echoes.Core.GameSession.Save;
            if (save == null || !save.HasSave) return;
            ItemBaseInfo weapon = null;
            var main = save.Current.Equipment(0)[0];
            if (main != null) weapon = combat.Rules.FindItemBase(main.BaseId);
            Logic.Self.Weapon = weapon != null && weapon.IsWeapon ? weapon : null;
        }

        // Sai do combate ao desligar (e antes do OnDestroy de qualquer componente), pela referência própria:
        // o AttributeComponent pode descartar os handles antes deste script no OnDestroy.
        void OnEnable()
        {
            if (Logic != null && combat != null && !Logic.Self.IsRegistered) combat.Register(Logic.Self, Logic, CombatOrderKey.Of(transform));
        }

        void OnDestroy()
        {
            Logic?.Dispose();
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

            if (TestSettings.HeroGodMode)
            {
                var vitals = combatant.Vitals;
                vitals.Life = combatant.MaxLife; // so teste: nunca vem do CSV
                combatant.SetVitals(in vitals);
            }
            Logic.MoveInput = CameraRelative(input.Move);
            if (TryGetAimPoint(out var aimPoint)) Logic.AimPoint = aimPoint;

            var hasKit = Logic.HasKit;
            var pressedAny = false;
            for (var c = HeroCommand.BasicAttack; c <= HeroCommand.Potion2; c++)
            {
                // Com kit (docs/18), o botão esquerdo e o direito entram por apertar/soltar (clique ou segurar, defesa); o resto, pelo buffer.
                if (hasKit && (c == HeroCommand.BasicAttack || c == HeroCombatLogic.GuardButton)) continue;
                if (!input.WasPressed(c)) continue;
                Logic.Press(c);
                pressedAny = true;
            }
            if (hasKit)
            {
                PumpButton(HeroCommand.BasicAttack, ref leftWasHeld);
                PumpButton(HeroCombatLogic.GuardButton, ref guardWasHeld);
            }
            // Sem kit (entrada antiga): segurar o botão do ataque básico repete o golpe assim que a ação anterior termina,
            // sem passar por cima de outro comando pedido neste quadro ou ainda no buffer.
            else if (!pressedAny && !Logic.HasPendingCommand && Logic.IsReadyForAction && input.IsHeld(HeroCommand.BasicAttack))
                Logic.Press(HeroCommand.BasicAttack);
        }

        bool leftWasHeld;
        bool guardWasHeld;

        // Transforma o estado do botão em eventos de apertar e soltar (um clique mais curto que o quadro dá os dois no mesmo quadro).
        void PumpButton(HeroCommand button, ref bool wasHeld)
        {
            var held = input.IsHeld(button);
            if (input.WasPressed(button))
            {
                Logic.ButtonDown(button);
                wasHeld = true;
            }
            if (wasHeld && !held)
            {
                Logic.ButtonUp(button);
                wasHeld = false;
            }
        }

        void LateUpdate()
        {
            if (Logic == null) return;
            var dt = Time.deltaTime;
            var combatant = Logic.Self;

            // A posição lógica avança só no passo fixo (A-04). Aqui a cena segue a posição interpolada entre
            // o passo anterior e o atual; o CharacterController resolve colisão e a gravidade (vertical).
            // Teleporte externo (DevZoneTeleport, cutscene): a cena mudou o corpo sozinha; a lógica acompanha.
            var sceneNow = transform.position.ToPlanar();
            if (hasSceneSync && PlanarVector.Distance(sceneNow, lastSceneSync) > 0.05f) combatant.Teleport(sceneNow);
            var wanted = combatant.InterpolatedPosition(combat != null ? combat.Clock.Alpha : 1.0);
            var delta = wanted - transform.position.ToPlanar();
            if (controller.isGrounded && verticalSpeed < 0f) verticalSpeed = 0f;
            verticalSpeed += Physics.gravity.y * dt;
            if (controller.enabled) controller.Move(delta.ToWorld(verticalSpeed * dt));

            // Virada suave (graus/s do SO_CombatFeel): rápida ao iniciar golpe ou esquiva, mais calma ao andar.
            var feel = combat != null ? combat.Feel : null;
            var turnSpeed = feel == null ? 900f : (Logic.IsCasting || Logic.Dodge.IsDodging ? feel.CastTurnDegreesPerSecond : Logic.IsAiming ? feel.AimTurnDegreesPerSecond : feel.TurnDegreesPerSecond);
            var targetRotation = Logic.FacingDirection().ToRotation(transform.rotation);
            transform.rotation = Quaternion.RotateTowards(transform.rotation, targetRotation, turnSpeed * dt);
            // Parede ou obstáculo: a lógica volta para onde o corpo realmente ficou (sem interpolar de volta).
            // Só resincroniza quando bateu de lado ou o desvio passa de ResyncMeters; o desvio pequeno (skin width, degrau, rampa)
            // some sozinho no passo seguinte e não pode zerar a interpolação a cada quadro.
            var actual = transform.position.ToPlanar();
            var deviation = PlanarVector.Distance(actual, wanted);
            if (deviation > 1e-3f) DeviationFrames++;
            if (deviation > ResyncMeters || (deviation > 1e-3f && (controller.collisionFlags & CollisionFlags.Sides) != 0))
            {
                combatant.Teleport(actual);
                ResyncCount++;
            }
            lastSceneSync = actual;
            hasSceneSync = true;
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
            Logic.Self.Teleport(position.ToPlanar());
            combat.Revive(Logic.Self);
            Respawned?.Invoke();
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
