using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Pool;

namespace Echoes.Presentation
{
    /// <summary>
    /// Pool de VFX por prefab (docs/04_arquitetura.md, seção 3.9: nada de Instantiate/Destroy por golpe).
    /// Devolve cada instância depois do tempo pedido; uma instância pode acompanhar um Transform (osso da mão, cristal do cajado) e ser
    /// encerrada antes (<see cref="Fade"/>: para de emitir e devolve quando as partículas morrerem). Uma instância por cena basta.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class VfxPool : MonoBehaviour
    {
        struct Live
        {
            public GameObject Instance;
            public ObjectPool<GameObject> Pool;
            public float TimeLeft;
            public Transform Follow;
            public Vector3 FollowOffset;
        }

        sealed class Cached
        {
            public ParticleSystem[] Systems;
            public TrailRenderer[] Trails;
            public VfxArcSwipe[] Arcs;
            public Vector3 PrefabScale;
        }

        readonly Dictionary<GameObject, ObjectPool<GameObject>> pools = new Dictionary<GameObject, ObjectPool<GameObject>>();
        readonly Dictionary<GameObject, Cached> cache = new Dictionary<GameObject, Cached>();
        readonly Dictionary<GameObject, Vector3> prefabScales = new Dictionary<GameObject, Vector3>();
        readonly List<Live> live = new List<Live>(32);

        public int ActiveCount => live.Count;

        public GameObject Play(GameObject prefab, Vector3 position, Quaternion rotation, float seconds)
        {
            return Play(prefab, position, rotation, seconds, 1f, null, Vector3.zero);
        }

        /// <summary>
        /// Toca <paramref name="prefab"/>. <paramref name="scale"/> multiplica a escala do prefab (sistemas com escala "Hierarchy");
        /// <paramref name="follow"/> faz a instância acompanhar o Transform (com <paramref name="followOffset"/> no espaço dele).
        /// Devolve a instância (para <see cref="Fade"/> e para configurar componentes como o rastro da lâmina).
        /// </summary>
        public GameObject Play(GameObject prefab, Vector3 position, Quaternion rotation, float seconds, float scale, Transform follow, Vector3 followOffset)
        {
            if (prefab == null) return null;
            if (!pools.TryGetValue(prefab, out var pool))
            {
                var source = prefab;
                pool = new ObjectPool<GameObject>(
                    () => Instantiate(source, transform),
                    go => go.SetActive(true),
                    go => go.SetActive(false),
                    go => Destroy(go),
                    false, 4, 32);
                pools.Add(prefab, pool);
                prefabScales[prefab] = prefab.transform.localScale;
            }
            var instance = pool.Get();
            instance.transform.SetPositionAndRotation(position, rotation);
            instance.transform.localScale = prefabScales[prefab] * scale;
            if (!cache.TryGetValue(instance, out var cached))
            {
                cached = new Cached
                {
                    Systems = instance.GetComponentsInChildren<ParticleSystem>(true), // uma vez por instância do pool
                    Trails = instance.GetComponentsInChildren<TrailRenderer>(true),
                    Arcs = instance.GetComponentsInChildren<VfxArcSwipe>(true),
                };
                cache.Add(instance, cached);
            }
            for (var i = 0; i < cached.Trails.Length; i++) cached.Trails[i].Clear();
            for (var i = 0; i < cached.Systems.Length; i++)
            {
                cached.Systems[i].Clear(true);
                cached.Systems[i].Play(true);
            }
            live.Add(new Live { Instance = instance, Pool = pool, TimeLeft = seconds, Follow = follow, FollowOffset = followOffset });
            return instance;
        }

        /// <summary>
        /// Encerra o efeito antes da hora: para de emitir e devolve ao pool em <paramref name="remainingSeconds"/> (o resto das partículas
        /// some sozinho). Ignora instância que já voltou ao pool.
        /// </summary>
        public void Fade(GameObject instance, float remainingSeconds)
        {
            if (instance == null) return;
            for (var i = 0; i < live.Count; i++)
            {
                if (live[i].Instance != instance) continue;
                var item = live[i];
                item.TimeLeft = Mathf.Min(item.TimeLeft, remainingSeconds);
                item.Follow = null;
                live[i] = item;
                if (cache.TryGetValue(instance, out var cached))
                {
                    for (var s = 0; s < cached.Systems.Length; s++) cached.Systems[s].Stop(true, ParticleSystemStopBehavior.StopEmitting);
                    for (var t = 0; t < cached.Trails.Length; t++) cached.Trails[t].emitting = false;
                    for (var a = 0; a < cached.Arcs.Length; a++) cached.Arcs[a].BeginFadeOut(remainingSeconds);
                }
                return;
            }
        }

        /// <summary>A instância ainda está tocando (não voltou ao pool).</summary>
        public bool IsPlaying(GameObject instance)
        {
            for (var i = 0; i < live.Count; i++)
            {
                if (live[i].Instance == instance) return true;
            }
            return false;
        }

        void LateUpdate()
        {
            // Acompanha o osso depois da animação do quadro (LateUpdate), senão o efeito fica um quadro atrás da mão.
            for (var i = 0; i < live.Count; i++)
            {
                var follow = live[i].Follow;
                if (follow == null) continue;
                live[i].Instance.transform.position = follow.TransformPoint(live[i].FollowOffset);
            }
        }

        void Update()
        {
            var dt = Time.deltaTime;
            for (var i = live.Count - 1; i >= 0; i--)
            {
                var item = live[i];
                item.TimeLeft -= dt;
                if (item.TimeLeft > 0f)
                {
                    live[i] = item;
                    continue;
                }
                live.RemoveAt(i);
                if (cache.TryGetValue(item.Instance, out var cached))
                {
                    for (var t = 0; t < cached.Trails.Length; t++) cached.Trails[t].emitting = true;
                }
                item.Pool.Release(item.Instance);
            }
        }

        void OnDestroy()
        {
            foreach (var pool in pools.Values) pool.Clear();
            pools.Clear();
            cache.Clear();
            prefabScales.Clear();
            live.Clear();
        }
    }
}
