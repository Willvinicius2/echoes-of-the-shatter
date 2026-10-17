using System;
using System.Collections.Generic;
using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Heroi modular (docs/04, 17.4): corpo base em 6 malhas de regiao mais ate 5 pecas de armadura, todas no mesmo esqueleto
    /// (Rig_Humanoid_Chibi). Equipar uma peca instancia o prefab, passa o SkinnedMeshRenderer para este heroi apontando para os OSSOS DESTE heroi
    /// (por nome, dicionario montado uma vez) e liga ou desliga as regioes do corpo que a peca esconde. O Animator do heroi anima tudo; nada
    /// de osso novo. Peca sem o conjunto pedido cai em vset.starter (com aviso). So apresentacao: nao decide regra.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class ModularCharacter : MonoBehaviour
    {
        static readonly string[] RegionMeshNames = { "Body_Head", "Body_Torso", "Body_Arms", "Body_Hands", "Body_Legs", "Body_Feet" };
        static readonly BodyRegion[] RegionOrder = { BodyRegion.Head, BodyRegion.Torso, BodyRegion.Arms, BodyRegion.Hands, BodyRegion.Legs, BodyRegion.Feet };

        [SerializeField] HeroPartCatalog catalog;
        [Tooltip("Conjunto vestido por slot ao iniciar (vazio = vset.starter em todos).")]
        [SerializeField] string[] initialSets = new string[5];
        [SerializeField] bool equipStarterOnStart = true;

        readonly Dictionary<string, Transform> bones = new Dictionary<string, Transform>();
        readonly SkinnedMeshRenderer[] regionRenderers = new SkinnedMeshRenderer[RegionOrder.Length];
        readonly GameObject[] partInstances = new GameObject[5];
        readonly HeroPart[] equipped = new HeroPart[5];
        bool built;

        public HeroPartCatalog Catalog { get => catalog; set => catalog = value; }

        /// <summary>Regioes do corpo base visiveis agora.</summary>
        public BodyRegion VisibleRegions
        {
            get
            {
                var visible = BodyRegion.None;
                for (var i = 0; i < regionRenderers.Length; i++)
                {
                    if (regionRenderers[i] != null && regionRenderers[i].enabled) visible |= RegionOrder[i];
                }
                return visible;
            }
        }

        public HeroPart Equipped(HeroPartSlot slot) => equipped[(int)slot];

        void Awake()
        {
            Build();
        }

        void Start()
        {
            if (!equipStarterOnStart) return;
            for (var i = 0; i < equipped.Length; i++)
            {
                if (equipped[i] != null) continue; // algo ja vestiu (conjunto do equipamento)
                var set = initialSets != null && i < initialSets.Length && !string.IsNullOrEmpty(initialSets[i]) ? initialSets[i] : HeroPartCatalog.StarterSet;
                Equip((HeroPartSlot)i, set);
            }
        }

        /// <summary>Indexa os ossos (por nome) e as malhas das regioes. Idempotente.</summary>
        public void Build()
        {
            if (built) return;
            built = true;
            foreach (var t in GetComponentsInChildren<Transform>(true))
            {
                if (!bones.ContainsKey(t.name)) bones.Add(t.name, t);
            }
            foreach (var smr in GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                var index = Array.IndexOf(RegionMeshNames, smr.name);
                if (index >= 0) regionRenderers[index] = smr;
            }
        }

        /// <summary>Veste o conjunto no slot (peca com fallback para o starter). Devolve a peca vestida ou null.</summary>
        public HeroPart Equip(HeroPartSlot slot, string visualSetId)
        {
            Build();
            var part = catalog != null ? catalog.Resolve(slot, visualSetId, message => Debug.LogWarning(message, this)) : null;
            return Wear(slot, part);
        }

        /// <summary>Tira a peca do slot: a regiao do corpo base volta a aparecer (corpo nu).</summary>
        public void Unequip(HeroPartSlot slot)
        {
            Build();
            Wear(slot, null);
        }

        public bool IsEquipped(HeroPartSlot slot) => equipped[(int)slot] != null;

        HeroPart Wear(HeroPartSlot slot, HeroPart part)
        {
            var index = (int)slot;
            if (partInstances[index] != null)
            {
                Discard(partInstances[index]);
                partInstances[index] = null;
            }
            equipped[index] = part;
            if (part != null && part.prefab != null) partInstances[index] = Attach(part.prefab);
            RefreshRegions();
            return part;
        }

        // Instancia o prefab da peca, move os SkinnedMeshRenderer para este heroi apontando para os ossos dele e descarta o resto do FBX.
        GameObject Attach(GameObject prefab)
        {
            var temp = Instantiate(prefab);
            var holder = new GameObject("Part_" + prefab.name);
            holder.transform.SetParent(transform, false);
            var reference = FirstBodyRenderer();
            foreach (var smr in temp.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                var source = smr.bones;
                var mapped = new Transform[source.Length];
                for (var i = 0; i < source.Length; i++)
                {
                    mapped[i] = source[i] != null && bones.TryGetValue(source[i].name, out var bone) ? bone : null;
                    if (mapped[i] == null && source[i] != null) Debug.LogWarning($"[Modular] Osso '{source[i].name}' da peca {prefab.name} nao existe no heroi.", this);
                }
                smr.transform.SetParent(holder.transform, false);
                smr.bones = mapped;
                smr.rootBone = smr.rootBone != null && bones.TryGetValue(smr.rootBone.name, out var root) ? root : (reference != null ? reference.rootBone : null);
                smr.updateWhenOffscreen = false;
                if (reference != null) smr.localBounds = reference.localBounds;
            }
            Discard(temp);
            return holder;
        }

        // No editor (EditMode, ferramentas de captura) Destroy nao vale; la o objeto sai na hora.
        static void Discard(GameObject go)
        {
            if (Application.isPlaying) Destroy(go);
            else DestroyImmediate(go);
        }

        SkinnedMeshRenderer FirstBodyRenderer()
        {
            for (var i = 0; i < regionRenderers.Length; i++)
            {
                if (regionRenderers[i] != null) return regionRenderers[i];
            }
            return null;
        }

        /// <summary>Uniao das mascaras das pecas vestidas: liga/desliga o Renderer de cada regiao do corpo.</summary>
        void RefreshRegions()
        {
            var hidden = BodyRegion.None;
            for (var i = 0; i < equipped.Length; i++)
            {
                if (equipped[i] != null) hidden |= equipped[i].hidesRegions;
            }
            for (var i = 0; i < regionRenderers.Length; i++)
            {
                if (regionRenderers[i] != null) regionRenderers[i].enabled = (hidden & RegionOrder[i]) == 0;
            }
        }
    }
}
