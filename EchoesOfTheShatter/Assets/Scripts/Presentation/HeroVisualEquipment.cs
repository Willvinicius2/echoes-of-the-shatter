using System.Collections.Generic;
using System.IO;
using Echoes.Core;
using Echoes.Gameplay;
using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Resolve o visualSetId dos itens (docs/04, 17.4): uniques.csv.visualSetId, depois item_bases.csv.visualSetId, depois vset.starter.
    /// O core ainda nao expoe o getter (9.6), entao le as colunas dos CSV direto; trocar pelo getter quando existir. Dado de apresentacao.
    /// </summary>
    public static class VisualSetResolver
    {
        public readonly struct Entry
        {
            public readonly string CoreSlot;
            public readonly string VisualSetId;

            public Entry(string coreSlot, string visualSetId)
            {
                CoreSlot = coreSlot;
                VisualSetId = visualSetId;
            }
        }

        static Dictionary<string, Entry> bases;
        static Dictionary<string, string> uniques;
        static string loadedFrom;

        public static void Reload(string dataDirectory)
        {
            loadedFrom = dataDirectory;
            bases = new Dictionary<string, Entry>();
            uniques = new Dictionary<string, string>();
            Read(Path.Combine(dataDirectory, "item_bases.csv"), (get) => bases[get("id")] = new Entry(get("slot"), get("visualSetId")));
            Read(Path.Combine(dataDirectory, "uniques.csv"), (get) =>
            {
                var set = get("visualSetId");
                if (!string.IsNullOrEmpty(set)) uniques[get("id")] = set;
            });
        }

        static void Read(string path, System.Action<System.Func<string, string>> row)
        {
            if (!File.Exists(path)) return;
            var records = CsvReader.Parse(File.ReadAllText(path));
            if (records.Count == 0) return;
            var header = records[0].Fields;
            for (var r = 1; r < records.Count; r++)
            {
                var fields = records[r].Fields;
                if (fields.Length < 2) continue;
                row(name =>
                {
                    var column = System.Array.IndexOf(header, name);
                    return column >= 0 && column < fields.Length ? fields[column] : string.Empty;
                });
            }
        }

        /// <summary>Slot do core e conjunto visual de um item base (e do Unico, se informado). Conjunto vazio = starter.</summary>
        public static bool TryResolve(string dataDirectory, string baseId, string uniqueIdOrNull, out HeroPartSlot slot, out string visualSetId)
        {
            if (bases == null || loadedFrom != dataDirectory) Reload(dataDirectory);
            slot = HeroPartSlot.Head;
            visualSetId = HeroPartCatalog.StarterSet;
            if (!bases.TryGetValue(baseId ?? string.Empty, out var entry)) return false;
            if (!HeroPart.TryFromCoreSlot(entry.CoreSlot, out slot)) return false;
            if (!string.IsNullOrEmpty(uniqueIdOrNull) && uniques.TryGetValue(uniqueIdOrNull, out var unique)) visualSetId = unique;
            else if (!string.IsNullOrEmpty(entry.VisualSetId)) visualSetId = entry.VisualSetId;
            return true;
        }
    }

    /// <summary>
    /// Liga o equipamento do heroi (HeroController.EquipmentIds, que vem do save e do core) ao ModularCharacter pelo visualSetId:
    /// cada item de slot visual veste a peca do seu conjunto; o resto fica em vset.starter (a armadura inicial aprovada).
    /// </summary>
    [DefaultExecutionOrder(-10)]
    [DisallowMultipleComponent]
    public sealed class HeroVisualEquipment : MonoBehaviour
    {
        [SerializeField] HeroController hero;
        [SerializeField] ModularCharacter modular;
        [SerializeField] GameRoot root;

        void Start()
        {
            if (hero == null) hero = GetComponentInParent<HeroController>();
            if (modular == null) modular = GetComponentInChildren<ModularCharacter>();
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (hero == null || modular == null) return;
            Apply(hero.EquipmentIds, ContentPaths.ResolveDataDirectory(string.Empty));
        }

        /// <summary>Veste os itens (item bases) nos slots visuais; slots sem item ficam no starter.</summary>
        public void Apply(IReadOnlyList<string> baseIds, string dataDirectory)
        {
            if (modular == null) modular = GetComponentInChildren<ModularCharacter>();
            modular.Build();
            var dressed = new HashSet<HeroPartSlot>();
            if (baseIds != null)
            {
                foreach (var id in baseIds)
                {
                    if (string.IsNullOrEmpty(id)) continue;
                    if (!VisualSetResolver.TryResolve(dataDirectory, id, null, out var slot, out var set)) continue; // arma, anel...: sem visual modular
                    modular.Equip(slot, set);
                    dressed.Add(slot);
                }
            }
            for (var i = 0; i <= (int)HeroPartSlot.Feet; i++)
            {
                if (!dressed.Contains((HeroPartSlot)i)) modular.Equip((HeroPartSlot)i, HeroPartCatalog.StarterSet);
            }
        }
    }
}
