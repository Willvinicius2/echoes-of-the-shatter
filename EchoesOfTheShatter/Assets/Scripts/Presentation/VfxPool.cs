using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Pool;

namespace Echoes.Presentation
{
    /// <summary>
    /// Pool de VFX por prefab (docs/04_arquitetura.md, seção 3.9: nada de Instantiate/Destroy por golpe).
    /// Devolve cada instância depois do tempo pedido. Uma instância por cena basta.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class VfxPool : MonoBehaviour
    {
        struct Live
        {
            public GameObject Instance;
            public ObjectPool<GameObject> Pool;
            public float TimeLeft;
        }

        readonly Dictionary<GameObject, ObjectPool<GameObject>> pools = new Dictionary<GameObject, ObjectPool<GameObject>>();
        readonly List<Live> live = new List<Live>(32);

        public void Play(GameObject prefab, Vector3 position, Quaternion rotation, float seconds)
        {
            if (prefab == null) return;
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
            }
            var instance = pool.Get();
            instance.transform.SetPositionAndRotation(position, rotation);
            var systems = instance.GetComponentsInChildren<ParticleSystem>();
            for (var i = 0; i < systems.Length; i++) systems[i].Play(true);
            live.Add(new Live { Instance = instance, Pool = pool, TimeLeft = seconds });
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
                item.Pool.Release(item.Instance);
            }
        }

        void OnDestroy()
        {
            foreach (var pool in pools.Values) pool.Clear();
            pools.Clear();
            live.Clear();
        }
    }
}
