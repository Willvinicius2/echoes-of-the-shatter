using System.Collections.Generic;
using Echoes.Core;
using Echoes.Gameplay;
using UnityEngine;
using UnityEngine.Pool;

namespace Echoes.Presentation
{
    /// <summary>
    /// Desenha os projéteis do <see cref="ProjectileSystem"/> com prefabs em pool. A posição vem da lógica (passo fixo); o visual só acompanha.
    /// Cada habilidade escolhe o seu visual em <see cref="SkillVfxEntry.projectile"/> (flecha, dardo, bola de fogo...); sem entrada cai no
    /// prefab padrão (o do inimigo). O projétil nasce na mão (<see cref="SkillVfxEntry.launchAnchor"/>), não no centro do corpo: o deslocamento
    /// até a trajetória do core some ao longo de <see cref="SkillVfxEntry.launchBlendMeters"/> de voo, então a magia sai da mão e chega no alvo
    /// exatamente onde o core o acerta. Ao acabar, o rastro continua por <see cref="SkillVfxEntry.lingerSeconds"/>.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class ProjectilePresenter : MonoBehaviour
    {
        struct Live
        {
            public int Id;
            public GameObject Instance;
            public ObjectPool<GameObject> Pool;
            public Vector3 LaunchOffset;
            public Vector2 StartPosition;
            public float BlendMeters;
            public Vector3 LastWorld;
            public bool HasLast;
        }

        struct Fading
        {
            public GameObject Instance;
            public ObjectPool<GameObject> Pool;
            public float TimeLeft;
        }

        [SerializeField] GameRoot root;
        [SerializeField] CombatSystemHost combatHost;
        [Tooltip("Prefab visual do projétil quando a habilidade não define o seu (FX_Enemies_Arrow).")]
        [SerializeField] GameObject prefab;
        [Tooltip("Altura do projétil acima do piso, em metros.")]
        [SerializeField] float height = 1f;

        readonly List<Live> live = new List<Live>(32);
        readonly List<Fading> fading = new List<Fading>(16);
        readonly Dictionary<GameObject, ObjectPool<GameObject>> pools = new Dictionary<GameObject, ObjectPool<GameObject>>();
        readonly Dictionary<GameObject, ParticleSystem[]> particles = new Dictionary<GameObject, ParticleSystem[]>();
        readonly Dictionary<GameObject, TrailRenderer[]> trails = new Dictionary<GameObject, TrailRenderer[]>();
        readonly Dictionary<GameObject, Light[]> lights = new Dictionary<GameObject, Light[]>();
        bool subscribed;
        SkillVfxPresenter skillVfx;

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            combatHost = CombatSystemHost.Resolve(combatHost, this);
            if (root == null || root.Events == null) return;
            root.Events.Subscribe<ProjectileEvent>(OnProjectile);
            subscribed = true;
        }

        void OnDestroy()
        {
            if (subscribed && root != null && root.Events != null) root.Events.Unsubscribe<ProjectileEvent>(OnProjectile);
            foreach (var pool in pools.Values) pool.Clear();
            pools.Clear();
            particles.Clear();
            trails.Clear();
            lights.Clear();
        }

        ObjectPool<GameObject> PoolFor(GameObject source)
        {
            if (!pools.TryGetValue(source, out var pool))
            {
                pool = new ObjectPool<GameObject>(
                    () => Instantiate(source, transform),
                    go => go.SetActive(true),
                    go => go.SetActive(false),
                    go => Destroy(go),
                    false, 8, ProjectileSystem.MaxActive);
                pools.Add(source, pool);
            }
            return pool;
        }

        void LateUpdate()
        {
            var combat = combatHost != null ? combatHost.Combat : null;
            if (combat != null)
            {
                var states = combat.Projectiles.Active;
                for (var i = 0; i < live.Count; i++)
                {
                    var item = live[i];
                    for (var s = 0; s < states.Count; s++)
                    {
                        var state = states[s];
                        if (state.Id != item.Id) continue;
                        var logical = state.Position.ToWorld(height);
                        var traveled = Mathf.Sqrt((state.Position.X - item.StartPosition.x) * (state.Position.X - item.StartPosition.x) +
                                                  (state.Position.Z - item.StartPosition.y) * (state.Position.Z - item.StartPosition.y));
                        var blend = VfxMath.LaunchBlend(traveled, item.BlendMeters); // sai da mão e assenta na trajetória sem quina
                        var world = logical + item.LaunchOffset * (1f - blend);
                        var rotation = state.Direction.ToRotation(Quaternion.identity);
                        if (item.HasLast)
                        {
                            var delta = world - item.LastWorld;
                            if (delta.sqrMagnitude > 1e-8f) rotation = Quaternion.LookRotation(delta.normalized, Vector3.up);
                        }
                        item.Instance.transform.SetPositionAndRotation(world, rotation);
                        item.LastWorld = world;
                        item.HasLast = true;
                        live[i] = item;
                        break;
                    }
                }
            }

            var dt = Time.deltaTime;
            for (var i = fading.Count - 1; i >= 0; i--)
            {
                var item = fading[i];
                item.TimeLeft -= dt;
                if (item.TimeLeft > 0f)
                {
                    fading[i] = item;
                    continue;
                }
                fading.RemoveAt(i);
                Rearm(item.Instance);
                item.Pool.Release(item.Instance);
            }
        }

        void OnProjectile(in ProjectileEvent evt)
        {
            if (evt.Spawned) Spawn(in evt);
            else End(in evt);
        }

        void Spawn(in ProjectileEvent evt)
        {
            var combat = combatHost != null ? combatHost.Combat : null;
            SkillVfxEntry entry = null;
            if (combat != null)
            {
                var states = combat.Projectiles.Active;
                for (var s = 0; s < states.Count; s++)
                {
                    if (states[s].Id != evt.ProjectileId) continue;
                    if (states[s].Skill != null) SkillVfx?.TryGetEntry(states[s].Skill.Id, out entry);
                    break;
                }
            }
            var source = entry != null && entry.projectile != null ? entry.projectile : prefab;
            if (source == null) return;

            var pool = PoolFor(source);
            var instance = pool.Get();
            var start = evt.Position.ToWorld(height);
            var offset = Vector3.zero;
            if (entry != null && !string.IsNullOrEmpty(entry.launchAnchor) && SkillVfx != null && SkillVfx.TryGetAnchor(evt.Owner, entry.launchAnchor, out var anchor))
                offset = anchor.position - start;
            var scale = entry != null ? entry.projectileScale : 1f;
            instance.transform.localScale = source.transform.localScale * scale;
            var rotation = evt.Direction.ToRotation(Quaternion.identity);
            instance.transform.SetPositionAndRotation(start + offset, rotation);
            Restart(instance);
            live.Add(new Live
            {
                Id = evt.ProjectileId, Instance = instance, Pool = pool, LaunchOffset = offset,
                StartPosition = new Vector2(evt.Position.X, evt.Position.Z),
                BlendMeters = entry != null ? entry.launchBlendMeters : 0f,
                LastWorld = start + offset, HasLast = false,
            });
        }

        void End(in ProjectileEvent evt)
        {
            for (var i = live.Count - 1; i >= 0; i--)
            {
                if (live[i].Id != evt.ProjectileId) continue;
                var item = live[i];
                live.RemoveAt(i);
                var linger = SkillVfx != null ? SkillVfx.LingerFor(evt.ProjectileId) : 0f;
                if (linger <= 0f)
                {
                    Rearm(item.Instance);
                    item.Pool.Release(item.Instance);
                    continue;
                }
                // Mantém o rastro vivo por um instante: para de emitir e deixa as partículas e a fita se apagarem.
                item.Instance.transform.position = evt.Position.ToWorld(height);
                Quench(item.Instance);
                fading.Add(new Fading { Instance = item.Instance, Pool = item.Pool, TimeLeft = linger });
            }
        }

        SkillVfxPresenter SkillVfx
        {
            get
            {
                if (skillVfx == null) skillVfx = SkillVfxPresenter.Instance;
                return skillVfx;
            }
        }

        void Restart(GameObject instance)
        {
            if (!particles.TryGetValue(instance, out var ps))
            {
                ps = instance.GetComponentsInChildren<ParticleSystem>(true);
                particles.Add(instance, ps);
                trails.Add(instance, instance.GetComponentsInChildren<TrailRenderer>(true));
                lights.Add(instance, instance.GetComponentsInChildren<Light>(true));
            }
            for (var i = 0; i < ps.Length; i++)
            {
                ps[i].Clear(true);
                ps[i].Play(true);
            }
            var tr = trails[instance];
            for (var i = 0; i < tr.Length; i++)
            {
                tr[i].Clear();
                tr[i].emitting = true;
            }
        }

        void Quench(GameObject instance)
        {
            if (particles.TryGetValue(instance, out var ps))
            {
                for (var i = 0; i < ps.Length; i++) ps[i].Stop(true, ParticleSystemStopBehavior.StopEmitting);
            }
            if (trails.TryGetValue(instance, out var tr))
            {
                for (var i = 0; i < tr.Length; i++) tr[i].emitting = false;
            }
            if (lights.TryGetValue(instance, out var lamps))
            {
                for (var i = 0; i < lamps.Length; i++) lamps[i].enabled = false;
            }
        }

        void Rearm(GameObject instance)
        {
            if (trails.TryGetValue(instance, out var tr))
            {
                for (var i = 0; i < tr.Length; i++) tr[i].emitting = true;
            }
        }
    }
}
