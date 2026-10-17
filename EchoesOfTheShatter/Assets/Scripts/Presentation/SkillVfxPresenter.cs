using System;
using System.Collections.Generic;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Echoes.Presentation
{
    /// <summary>
    /// Toca os VFX das habilidades a partir dos eventos do core (docs/18 seção 6): <see cref="SkillPhaseEvent"/> (brilho de lançamento na
    /// preparação, clarão de saída, nova e chuva no impacto, rastro da arma), <see cref="HitEvent"/> (faísca no alvo) e
    /// <see cref="ProjectileEvent"/> (explosão onde o projétil acabou; o voo em si é do <see cref="ProjectilePresenter"/>, que pergunta aqui
    /// qual é o visual da habilidade). Tudo vem do <see cref="SkillPresentationSet.vfx"/> dos SO_SkillPresentation_*; nenhum tamanho, cor ou
    /// duração mora no código. Nunca decide regra: a posição e a velocidade vêm da lógica, aqui só se desenha. Os VFX saem do
    /// <see cref="VfxPool"/>. Se a cena não o tiver, instala-se sozinho (ver <see cref="AutoInstall"/>).
    /// </summary>
    [DisallowMultipleComponent]
    public sealed partial class SkillVfxPresenter : MonoBehaviour
    {
        struct HitMark
        {
            public int OwnerId;
            public string SkillId;
        }

        sealed class ProjectileInfo
        {
            public SkillVfxEntry Entry;
            public SkillInfo Skill;
            public Combatant Owner;
        }

        struct Context
        {
            public Combatant Owner;
            public Transform OwnerTransform;
            public SkillInfo Skill;
            public Quaternion Facing;
            public Vector3 Point;
            public bool HasPoint;
            public float RadiusOverrideMeters; // raio da explosao vindo do evento do projetil (0 = usa o da habilidade)
        }

        /// <summary>Opção "Reduzir efeitos do jogador" (docs/03 seção 3.8): 0 desliga os efeitos do herói; o valor entre 0 e 1 fica para o menu de opções.</summary>
        public static float PlayerEffectsIntensity = 1f;

        /// <summary>Quem informa o ponto mirado no chão (Chuva de Flechas). Padrão: o ponto de mira da lógica do herói.</summary>
        public Func<Combatant, PlanarVector?> AimResolver;

        public static SkillVfxPresenter Instance { get; private set; }

        [SerializeField] GameRoot root;
        [SerializeField] CombatSystemHost combatHost;
        [SerializeField] VfxPool vfxPool;
        [SerializeField] SkillVfxLibrary library;
        [Tooltip("Conjuntos extras (além dos da biblioteca).")]
        [SerializeField] List<SkillPresentationSet> extraSets = new List<SkillPresentationSet>();
        [Tooltip("Altura do projétil acima do piso (m), a mesma do ProjectilePresenter.")]
        [SerializeField] float projectileHeight = 1f;

        readonly Dictionary<string, SkillVfxEntry> entries = new Dictionary<string, SkillVfxEntry>(StringComparer.Ordinal);
        readonly Dictionary<int, ProjectileInfo> projectiles = new Dictionary<int, ProjectileInfo>();
        readonly List<int> endedProjectiles = new List<int>(8);
        readonly List<HitMark> hitMarks = new List<HitMark>(8);
        readonly Dictionary<int, List<GameObject>> windupLive = new Dictionary<int, List<GameObject>>();
        readonly Dictionary<int, List<GameObject>> chargeLive = new Dictionary<int, List<GameObject>>();
        readonly Dictionary<GameObject, BladeTrail> trailCache = new Dictionary<GameObject, BladeTrail>();
        readonly SkillAnchors anchors = new SkillAnchors();
        bool subscribed;

        public int EntryCount => entries.Count;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void ResetStatics()
        {
            Instance = null;
            PlayerEffectsIntensity = 1f;
        }

        // ----------------------------------------------------------------------------------------------------------------- instalação

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void AutoInstallBoot()
        {
            SceneManager.sceneLoaded -= OnSceneLoaded;
            SceneManager.sceneLoaded += OnSceneLoaded;
            AutoInstall();
        }

        static void OnSceneLoaded(Scene scene, LoadSceneMode mode) => AutoInstall();

        /// <summary>
        /// Cenas de jogo (Refúgio, Cripta) já têm VfxPool e ProjectilePresenter e ainda não conhecem este componente: ele entra sozinho no
        /// objeto do VfxPool, com a biblioteca de Resources, sem mudar os builders das cenas. Cena sem VfxPool (menu) fica de fora.
        /// </summary>
        public static void AutoInstall()
        {
            if (Instance != null) return;
            var existing = FindAnyObjectByType<SkillVfxPresenter>();
            if (existing != null) return;
            var pool = FindAnyObjectByType<VfxPool>();
            if (pool == null) return;
            if (Resources.Load<SkillVfxLibrary>(SkillVfxLibrary.ResourcePath) == null) return;
            pool.gameObject.AddComponent<SkillVfxPresenter>();
        }

        void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(this);
                return;
            }
            Instance = this;
            if (library == null) library = Resources.Load<SkillVfxLibrary>(SkillVfxLibrary.ResourcePath);
            if (library != null)
            {
                VfxLight.MaxConcurrent = library.maxVfxLights;
                projectileHeight = library.projectileHeight;
                for (var i = 0; i < library.sets.Count; i++) Register(library.sets[i]);
            }
            for (var i = 0; i < extraSets.Count; i++) Register(extraSets[i]);
        }

        /// <summary>Acrescenta um conjunto à tabela (a vitrine registra os seus).</summary>
        public void Register(SkillPresentationSet set)
        {
            if (set == null) return;
            for (var i = 0; i < set.vfx.Count; i++)
            {
                var entry = set.vfx[i];
                if (entry != null && !string.IsNullOrEmpty(entry.skillId)) entries[entry.skillId] = entry;
            }
        }

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (vfxPool == null) vfxPool = FindAnyObjectByType<VfxPool>();
            combatHost = combatHost != null ? combatHost : FindAnyObjectByType<CombatSystemHost>();
            var events = root != null ? root.Events : null;
            if (events == null) return;
            events.Subscribe<SkillPhaseEvent>(OnSkillPhase);
            events.Subscribe<HitEvent>(OnHit);
            events.Subscribe<ProjectileEvent>(OnProjectile);
            SubscribeBasicInput(events);
            subscribed = true;
        }

        void OnDestroy()
        {
            if (Instance == this) Instance = null;
            if (!subscribed || root == null || root.Events == null) return;
            var events = root.Events;
            events.Unsubscribe<SkillPhaseEvent>(OnSkillPhase);
            events.Unsubscribe<HitEvent>(OnHit);
            events.Unsubscribe<ProjectileEvent>(OnProjectile);
            UnsubscribeBasicInput(events);
        }

        // Os dois lados de BasicInputEvent (carga e defesa) ficam em SkillVfxPresenter.BasicInput.cs.
        partial void SubscribeBasicInput(EventBus events);
        partial void UnsubscribeBasicInput(EventBus events);

        void LateUpdate()
        {
            hitMarks.Clear();
            if (endedProjectiles.Count > 0)
            {
                for (var i = 0; i < endedProjectiles.Count; i++) projectiles.Remove(endedProjectiles[i]);
                endedProjectiles.Clear();
            }
        }

        // ----------------------------------------------------------------------------------------------------------------- consultas

        public bool TryGetEntry(string skillId, out SkillVfxEntry entry)
        {
            entry = null;
            return !string.IsNullOrEmpty(skillId) && entries.TryGetValue(skillId, out entry);
        }

        public bool TryGetAnchor(Combatant owner, string anchorName, out Transform anchor)
        {
            anchor = null;
            var t = TransformOf(owner);
            if (t == null) return false;
            anchor = anchors.Get(t, anchorName);
            return anchor != null;
        }

        /// <summary>Quanto o rastro do projétil dura depois que ele acaba (0 = devolve já).</summary>
        public float LingerFor(int projectileId)
        {
            return projectiles.TryGetValue(projectileId, out var info) ? info.Entry.lingerSeconds : 0f;
        }

        static Transform TransformOf(Combatant c)
        {
            return c != null && c.Owner is Component component && component != null ? component.transform : null;
        }

        bool Muted(Combatant owner) => owner != null && owner.Team == CombatTeam.Hero && PlayerEffectsIntensity <= 0.001f;

        // ----------------------------------------------------------------------------------------------------------------- eventos

        void OnSkillPhase(in SkillPhaseEvent evt)
        {
            var owner = evt.Owner;
            if (owner == null) return;
            if (evt.Phase == ActionPhase.None || evt.Skill == null)
            {
                Fade(windupLive, owner, 0.25f);
                return;
            }
            if (!TryGetEntry(evt.Skill.Id, out var entry) || Muted(owner)) return;
            var ownerT = TransformOf(owner);
            if (ownerT == null) return;
            var ctx = new Context
            {
                Owner = owner, OwnerTransform = ownerT, Skill = evt.Skill,
                Facing = evt.Direction.ToRotation(ownerT.rotation),
            };
            switch (evt.Phase)
            {
                case ActionPhase.Windup:
                    Fade(windupLive, owner, 0.2f);
                    PlayAll(entry.windupFx, in ctx, Track(windupLive, owner));
                    break;
                case ActionPhase.Impact:
                    Fade(windupLive, owner, 0.2f);
                    PlayAll(entry.releaseFx, in ctx, null);
                    StartTrail(entry, in ctx);
                    break;
                default:
                    Fade(windupLive, owner, 0.2f);
                    break;
            }
        }

        void OnHit(in HitEvent evt)
        {
            if (evt.Skill == null || evt.IsDamageOverTime || evt.Attacker == null) return;
            hitMarks.Add(new HitMark { OwnerId = evt.Attacker.Id, SkillId = evt.Skill.Id });
            if (!evt.Result.Landed || Muted(evt.Attacker)) return;
            if (!TryGetEntry(evt.Skill.Id, out var entry)) return;
            var specs = evt.IsHeavy && entry.hitHeavyFx.Length > 0 ? entry.hitHeavyFx : entry.hitFx;
            if (specs.Length == 0) return;
            var targetT = TransformOf(evt.Target);
            var attackerT = TransformOf(evt.Attacker);
            var point = targetT != null ? targetT.position : evt.Position.ToWorld(0f);
            var toAttacker = attackerT != null ? attackerT.position - point : Vector3.back;
            toAttacker.y = 0f;
            var ctx = new Context
            {
                Owner = evt.Attacker, OwnerTransform = attackerT, Skill = evt.Skill,
                Facing = toAttacker.sqrMagnitude > 1e-6f ? Quaternion.LookRotation(toAttacker.normalized, Vector3.up) : Quaternion.identity,
                Point = point, HasPoint = true,
            };
            PlayAll(specs, in ctx, null);
        }

        void OnProjectile(in ProjectileEvent evt)
        {
            if (evt.Spawned)
            {
                var combat = combatHost != null ? combatHost.Combat : null;
                if (combat == null) return;
                var states = combat.Projectiles.Active;
                for (var s = 0; s < states.Count; s++)
                {
                    var state = states[s];
                    if (state.Id != evt.ProjectileId) continue;
                    if (state.Skill != null && TryGetEntry(state.Skill.Id, out var entry))
                        projectiles[evt.ProjectileId] = new ProjectileInfo { Entry = entry, Skill = state.Skill, Owner = evt.Owner };
                    break;
                }
                return;
            }

            if (!projectiles.TryGetValue(evt.ProjectileId, out var info)) return;
            endedProjectiles.Add(evt.ProjectileId);
            if (Muted(info.Owner)) return;
            var hit = evt.ExplosionRadiusMeters > 0f;
            for (var i = 0; i < hitMarks.Count; i++)
            {
                if (info.Owner != null && hitMarks[i].OwnerId == info.Owner.Id && string.Equals(hitMarks[i].SkillId, info.Skill.Id, StringComparison.Ordinal))
                {
                    hit = true;
                    break;
                }
            }
            var specs = hit ? info.Entry.endFx : info.Entry.missFx;
            if (specs.Length == 0) return;
            var ownerT = TransformOf(info.Owner);
            var groundY = ownerT != null ? ownerT.position.y : 0f;
            var dir = evt.Direction.ToRotation(Quaternion.identity);
            var ctx = new Context
            {
                Owner = info.Owner, OwnerTransform = ownerT, Skill = info.Skill, Facing = dir,
                Point = new Vector3(evt.Position.X, groundY, evt.Position.Z), HasPoint = true,
                RadiusOverrideMeters = evt.ExplosionRadiusMeters,
            };
            PlayAll(specs, in ctx, null);
        }

        // ----------------------------------------------------------------------------------------------------------------- reprodução

        List<GameObject> Track(Dictionary<int, List<GameObject>> live, Combatant owner)
        {
            if (!live.TryGetValue(owner.Id, out var list))
            {
                list = new List<GameObject>(4);
                live.Add(owner.Id, list);
            }
            return list;
        }

        void Fade(Dictionary<int, List<GameObject>> live, Combatant owner, float seconds)
        {
            if (owner == null || vfxPool == null || !live.TryGetValue(owner.Id, out var list)) return;
            for (var i = 0; i < list.Count; i++) vfxPool.Fade(list[i], seconds);
            list.Clear();
        }

        void PlayAll(VfxSpec[] specs, in Context ctx, List<GameObject> track)
        {
            for (var i = 0; i < specs.Length; i++)
            {
                var instance = Play(specs[i], in ctx);
                if (instance != null && track != null) track.Add(instance);
            }
        }

        GameObject Play(VfxSpec spec, in Context ctx)
        {
            if (spec == null || !spec.IsSet || vfxPool == null) return null;
            var ownerT = ctx.OwnerTransform;
            Vector3 position;
            var rotation = spec.alignToDirection ? ctx.Facing : Quaternion.identity;
            Transform follow = null;
            switch (spec.place)
            {
                case VfxPlace.Anchor:
                {
                    if (ownerT == null) return null;
                    var a = anchors.Get(ownerT, spec.anchor);
                    position = a.position;
                    if (spec.follow) follow = a;
                    break;
                }
                case VfxPlace.OwnerFeet:
                    if (ownerT == null) return null;
                    position = ownerT.position;
                    if (spec.follow) follow = ownerT;
                    break;
                case VfxPlace.AimGround:
                    if (!TryAimGround(in ctx, out position)) return null;
                    break;
                default:
                    if (!ctx.HasPoint) return null;
                    position = ctx.Point;
                    break;
            }
            position.y += spec.yOffset;

            var scale = VfxMath.RadiusScale(ctx.RadiusOverrideMeters > 0f ? ctx.RadiusOverrideMeters : ctx.Skill != null ? WorldUnits.ToMeters(ctx.Skill.RadiusUu) : 0f, spec.authoredRadiusMeters, spec.scale);
            var instance = vfxPool.Play(spec.prefab, position, rotation, spec.seconds, scale, follow, Vector3.zero);
            if (instance != null && spec.lengthFromRange && ctx.Skill != null)
            {
                // Feixe: o prefab tem 1 m de comprimento em Z; estica até o alcance real da habilidade.
                instance.transform.localScale = new Vector3(spec.scale, spec.scale, WorldUnits.ToMeters(ctx.Skill.RangeUu));
            }
            return instance;
        }

        bool TryAimGround(in Context ctx, out Vector3 point)
        {
            point = default;
            var ownerT = ctx.OwnerTransform;
            if (ownerT == null || ctx.Owner == null) return false;
            PlanarVector aim;
            var resolved = AimResolver != null ? AimResolver(ctx.Owner) : null;
            if (resolved.HasValue) aim = resolved.Value;
            else if (ownerT.TryGetComponent<HeroController>(out var hero) && hero.Logic != null) aim = hero.Logic.AimPoint;
            else aim = ctx.Owner.Position + ctx.Owner.Forward * (ctx.Skill != null ? WorldUnits.ToMeters(ctx.Skill.RangeUu) : 5f);
            if (ctx.Skill != null)
            {
                // Mesma conta do HitArea do herói: o centro da área é o ponto mirado limitado ao alcance.
                var toAim = aim - ctx.Owner.Position;
                aim = ctx.Owner.Position + toAim.ClampMagnitude(WorldUnits.ToMeters(ctx.Skill.RangeUu));
            }
            point = new Vector3(aim.X, ownerT.position.y, aim.Z);
            return true;
        }

        void StartTrail(SkillVfxEntry entry, in Context ctx)
        {
            var spec = entry.trail;
            if (spec == null || !spec.IsSet || vfxPool == null || ctx.OwnerTransform == null) return;
            var instance = vfxPool.Play(spec.prefab, Vector3.zero, Quaternion.identity, spec.seconds);
            if (instance == null) return;
            if (!trailCache.TryGetValue(instance, out var trail))
            {
                trail = instance.GetComponentInChildren<BladeTrail>(true);
                trailCache.Add(instance, trail);
            }
            if (trail == null) return;
            var tip = anchors.Get(ctx.OwnerTransform, entry.trailTip);
            var hilt = anchors.Get(ctx.OwnerTransform, entry.trailBase);
            trail.Bind(hilt, tip, entry.trailWidth, entry.trailEmitSeconds);
        }

        // ----------------------------------------------------------------------------------------------------------------- API do kit básico

        /// <summary>Carga do golpe forte começou: brilho na arma e anel no chão até soltar ou cancelar.</summary>
        public void BeginCharge(Combatant owner, string heavySkillId)
        {
            if (owner == null || Muted(owner) || !TryGetEntry(heavySkillId, out var entry)) return;
            var ownerT = TransformOf(owner);
            if (ownerT == null) return;
            Fade(chargeLive, owner, 0.1f);
            var ctx = new Context { Owner = owner, OwnerTransform = ownerT, Facing = ownerT.rotation };
            PlayAll(entry.chargeFx, in ctx, Track(chargeLive, owner));
        }

        /// <summary>Carga no máximo: o golpe solta sozinho; pisca no máximo (docs/18, fx.charge.glow).</summary>
        public void ChargeFull(Combatant owner, string heavySkillId)
        {
            if (owner == null || Muted(owner) || !TryGetEntry(heavySkillId, out var entry)) return;
            var ownerT = TransformOf(owner);
            if (ownerT == null) return;
            var ctx = new Context { Owner = owner, OwnerTransform = ownerT, Facing = ownerT.rotation };
            PlayAll(entry.chargeFullFx, in ctx, null);
        }

        /// <summary>Soltou, cancelou ou esquivou: o brilho e o anel somem.</summary>
        public void EndCharge(Combatant owner) => Fade(chargeLive, owner, 0.15f);

        /// <summary>Defesa levantada: o efeito da classe (<c>&lt;classe&gt;#guard</c>) fica até <see cref="GuardDown"/>.</summary>
        public void GuardUp(Combatant owner)
        {
            if (owner == null || Muted(owner) || !TryGetEntry(owner.ContentId + "#guard", out var entry)) return;
            var ownerT = TransformOf(owner);
            if (ownerT == null) return;
            Fade(windupLive, owner, 0.1f);
            var ctx = new Context { Owner = owner, OwnerTransform = ownerT, Facing = ownerT.rotation };
            PlayAll(entry.windupFx, in ctx, Track(windupLive, owner));
        }

        public void GuardDown(Combatant owner) => Fade(windupLive, owner, 0.2f);

        /// <summary>A defesa caiu (limite de tempo ou Mana acabou): estilhaça.</summary>
        public void GuardBroke(Combatant owner)
        {
            GuardDown(owner);
            if (owner == null || Muted(owner) || !TryGetEntry(owner.ContentId + "#guard_break", out var entry)) return;
            var ownerT = TransformOf(owner);
            if (ownerT == null) return;
            var ctx = new Context { Owner = owner, OwnerTransform = ownerT, Facing = ownerT.rotation };
            PlayAll(entry.releaseFx, in ctx, null);
        }

        /// <summary>Golpe absorvido pela defesa comum: faíscas no ponto de contato (ou onda na cúpula do Mago).</summary>
        public void GuardBlock(Combatant owner, Vector3 contact)
        {
            if (owner == null || Muted(owner) || !TryGetEntry(owner.ContentId + "#guard", out var entry) || entry.hitFx.Length == 0) return;
            var ownerT = TransformOf(owner);
            var toAttacker = ownerT != null ? ownerT.forward : Vector3.forward;
            var ctx = new Context { Owner = owner, OwnerTransform = ownerT, Facing = Quaternion.LookRotation(toAttacker, Vector3.up), Point = contact, HasPoint = true };
            PlayAll(entry.hitFx, in ctx, null);
        }

        /// <summary>Defesa perfeita do Guerreiro: anel dourado, estrela e clarão (<c>&lt;classe&gt;#perfect</c>).</summary>
        public void GuardPerfect(Combatant owner, Vector3 contact)
        {
            if (owner == null || Muted(owner) || !TryGetEntry(owner.ContentId + "#perfect", out var entry)) return;
            var ownerT = TransformOf(owner);
            var ctx = new Context { Owner = owner, OwnerTransform = ownerT, Facing = ownerT != null ? ownerT.rotation : Quaternion.identity, Point = contact, HasPoint = true };
            PlayAll(entry.releaseFx, in ctx, null);
        }
    }
}
