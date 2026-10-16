using System.Collections.Generic;
using Echoes.Core;
using Echoes.Gameplay;
using UnityEngine;
using UnityEngine.Pool;

namespace Echoes.Presentation
{
    /// <summary>
    /// Desenha os projéteis do <see cref="ProjectileSystem"/> com um prefab em pool. A posição vem da
    /// lógica (passo fixo); o visual só acompanha. Sem prefab, os projéteis existem mas não aparecem.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class ProjectilePresenter : MonoBehaviour
    {
        struct Live
        {
            public int Id;
            public GameObject Instance;
        }

        [SerializeField] GameRoot root;
        [SerializeField] CombatSystemHost combatHost;
        [Tooltip("Prefab visual do projétil inimigo (FX_Enemies_Arrow).")]
        [SerializeField] GameObject prefab;
        [Tooltip("Altura do projétil acima do piso, em metros.")]
        [SerializeField] float height = 1f;

        readonly List<Live> live = new List<Live>(32);
        ObjectPool<GameObject> pool;
        bool subscribed;

        void Awake()
        {
            pool = new ObjectPool<GameObject>(
                () => Instantiate(prefab, transform),
                go => go.SetActive(true),
                go => go.SetActive(false),
                go => Destroy(go),
                false, 8, ProjectileSystem.MaxActive);
        }

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            combatHost = CombatSystemHost.Resolve(combatHost, this);
            if (prefab == null || root == null || root.Events == null) return;
            root.Events.Subscribe<ProjectileEvent>(OnProjectile);
            subscribed = true;
        }

        void OnDestroy()
        {
            if (subscribed && root != null && root.Events != null) root.Events.Unsubscribe<ProjectileEvent>(OnProjectile);
            pool?.Clear();
        }

        void LateUpdate()
        {
            var combat = combatHost != null ? combatHost.Combat : null;
            if (combat == null) return;
            var states = combat.Projectiles.Active;
            for (var i = 0; i < live.Count; i++)
            {
                for (var s = 0; s < states.Count; s++)
                {
                    if (states[s].Id != live[i].Id) continue;
                    live[i].Instance.transform.SetPositionAndRotation(
                        states[s].Position.ToWorld(height), states[s].Direction.ToRotation(Quaternion.identity));
                    break;
                }
            }
        }

        void OnProjectile(in ProjectileEvent evt)
        {
            if (evt.Spawned)
            {
                var instance = pool.Get();
                instance.transform.SetPositionAndRotation(evt.Position.ToWorld(height), evt.Direction.ToRotation(Quaternion.identity));
                live.Add(new Live { Id = evt.ProjectileId, Instance = instance });
                return;
            }
            for (var i = live.Count - 1; i >= 0; i--)
            {
                if (live[i].Id != evt.ProjectileId) continue;
                pool.Release(live[i].Instance);
                live.RemoveAt(i);
            }
        }
    }
}
