using System.Collections.Generic;
using Echoes.Core;
using Echoes.Gameplay;
using UnityEngine;
using UnityEngine.Pool;

namespace Echoes.Presentation
{
    /// <summary>
    /// Mostra e esconde os telegraphs dos inimigos a partir dos <see cref="TelegraphEvent"/>, com
    /// <see cref="TelegraphView"/> em pool. O progresso enche pelo tempo do windup vindo do dado.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class TelegraphPresenter : MonoBehaviour
    {
        [SerializeField] GameRoot root;
        [Tooltip("Prefab com TelegraphView + material M_Telegraph (SG_VFX, variante Telegraph).")]
        [SerializeField] TelegraphView prefab;
        [Tooltip("Sem prefab: material usado nas views criadas por código.")]
        [SerializeField] Material fallbackMaterial;
        [Tooltip("Altura do piso quando o dono não tem objeto na cena (o telegraph fica 2 cm acima).")]
        [SerializeField] float fallbackGroundY;

        readonly List<TelegraphView> active = new List<TelegraphView>(16);
        readonly Dictionary<int, Combatant> owners = new Dictionary<int, Combatant>();
        ObjectPool<TelegraphView> pool;
        bool subscribed;

        void Awake()
        {
            pool = new ObjectPool<TelegraphView>(Create, null, view => view.gameObject.SetActive(false), view => Destroy(view.gameObject), false, 8, 64);
        }

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (root != null && root.Events != null)
            {
                root.Events.Subscribe<TelegraphEvent>(OnTelegraph);
                subscribed = true;
            }
            if (prefab == null && fallbackMaterial == null)
                Debug.LogWarning("[Telegraph] Sem prefab nem material: os avisos no chão ficam com o material padrão.", this);
        }

        void OnDestroy()
        {
            if (subscribed && root != null && root.Events != null) root.Events.Unsubscribe<TelegraphEvent>(OnTelegraph);
            pool?.Clear();
        }

        void Update()
        {
            var dt = Time.deltaTime;
            for (var i = 0; i < active.Count; i++)
            {
                var view = active[i];
                view.Elapsed += OwnerFrozen(view) ? 0f : dt; // o windup do dono também para no hitstop
                view.SetProgress(view.Duration > 0f ? view.Elapsed / view.Duration : 1f);
            }
        }

        bool OwnerFrozen(TelegraphView view)
        {
            return owners.TryGetValue(view.TelegraphId, out var owner) && owner != null && owner.Hitstop.IsActive;
        }

        void OnTelegraph(in TelegraphEvent evt)
        {
            if (evt.Started)
            {
                if (!evt.ShowOnGround || TelegraphHints.IsHidden(evt.SkillId)) return;
                var view = pool.Get();
                var ownerObject = evt.Owner != null ? evt.Owner.Owner as Component : null;
                var groundY = ownerObject != null ? ownerObject.transform.position.y : fallbackGroundY;
                view.Show(in evt, groundY);
                active.Add(view);
                owners[evt.TelegraphId] = evt.Owner;
                return;
            }

            for (var i = active.Count - 1; i >= 0; i--)
            {
                if (active[i].TelegraphId != evt.TelegraphId) continue;
                pool.Release(active[i]);
                active.RemoveAt(i);
            }
            owners.Remove(evt.TelegraphId);
        }

        TelegraphView Create()
        {
            TelegraphView view;
            if (prefab != null)
            {
                view = Instantiate(prefab, transform);
            }
            else
            {
                var go = new GameObject("Telegraph", typeof(MeshFilter), typeof(MeshRenderer));
                go.transform.SetParent(transform, false);
                if (fallbackMaterial != null) go.GetComponent<MeshRenderer>().sharedMaterial = fallbackMaterial;
                view = go.AddComponent<TelegraphView>();
            }
            view.gameObject.SetActive(false);
            return view;
        }
    }
}
