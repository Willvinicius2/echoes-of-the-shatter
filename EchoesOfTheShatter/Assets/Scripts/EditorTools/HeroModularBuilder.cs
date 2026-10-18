using System;
using System.Collections.Generic;
using System.IO;
using Echoes.Presentation;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Herois modulares (docs/04, 17.4): para cada heroi (Warrior, Archer) monta os materiais (corpo e conjunto starter), os prefabs das 5 pecas
    /// (P_Heroi_Slot_Conjunto), os SO_HeroPart_* com as regioes escondidas (de hides_regions.json, gerado pela arte) e o SO_HeroPartCatalog_*.
    /// Fontes em Assets/Content/Heroes/Heroi/{Body,Parts}. O prefab do heroi (corpo em 6 regioes + ModularCharacter) sai do CharacterPrefabBuilder.
    /// </summary>
    public static class HeroModularBuilder
    {
        public const string Root = "Assets/Content/Heroes";
        public static readonly string[] Heroes = { "Warrior", "Archer", "Mage" };
        public static readonly string[] SlotNames = { "Head", "Chest", "Hands", "Legs", "Feet" };
        public const string StarterSet = "Starter"; // vset.starter em PascalCase para o nome dos assets

        /// <summary>Conjuntos visuais por sufixo de arquivo: Starter (todos os herois) e Rare (2o conjunto do Guerreiro, vset.warrior_rare_01). Conjunto sem FBX para o heroi e ignorado.</summary>
        public static readonly (string suffix, string visualSetId)[] Sets =
        {
            (StarterSet, HeroPartCatalog.StarterSet),
            ("Rare", HeroPartCatalog.WarriorRareSet),
        };

        public static string CatalogPath(string hero) => $"{Root}/{hero}/SO_HeroPartCatalog_{hero}.asset";
        public static string BodyDir(string hero) => $"{Root}/{hero}/Body";
        public static string PartsDir(string hero) => $"{Root}/{hero}/Parts";

        [MenuItem("Echoes/Montar herois modulares")]
        public static void BuildAll()
        {
            foreach (var hero in Heroes) BuildHero(hero);
            AssetDatabase.SaveAssets();
        }

        /// <summary>Regioes que cada slot esconde, lidas de hides_regions.json (chaves Head, Chest, Hands, Legs, Feet).</summary>
        public static Dictionary<string, BodyRegion> ReadHides(string hero)
        {
            var path = Path.Combine(Path.GetDirectoryName(Application.dataPath), Root, hero, "hides_regions.json");
            var result = new Dictionary<string, BodyRegion>();
            var text = File.ReadAllText(path);
            // Formato fixo e pequeno: {"Slot": ["Regiao", ...], ...}. Le sem dependencia de JSON.
            foreach (var slot in SlotNames)
            {
                var start = text.IndexOf("\"" + slot + "\"", StringComparison.Ordinal);
                if (start < 0) continue;
                var open = text.IndexOf('[', start);
                var close = text.IndexOf(']', open);
                var flags = BodyRegion.None;
                foreach (var raw in text.Substring(open + 1, close - open - 1).Split(','))
                {
                    var name = raw.Trim().Trim('"');
                    if (name.Length > 0) flags |= (BodyRegion)Enum.Parse(typeof(BodyRegion), name);
                }
                result[slot] = flags;
            }
            return result;
        }

        public static HeroPartCatalog BuildHero(string hero)
        {
            var bodyMaterial = CharacterPrefabBuilder.EnsureMaterial($"M_{hero}_Body", $"{BodyDir(hero)}/T_{hero}_Body_BC.png", $"{BodyDir(hero)}/T_{hero}_Body_M.png");
            var hides = ReadHides(hero);

            var catalog = SandboxBuilder.LoadOrCreate<HeroPartCatalog>(CatalogPath(hero));
            catalog.heroId = hero;
            catalog.parts.Clear();
            foreach (var (suffix, visualSetId) in Sets)
            {
                if (!File.Exists(Path.Combine(Path.GetDirectoryName(Application.dataPath), PartsDir(hero), $"SK_{hero}_Head_{suffix}.fbx"))) continue;
                // Mesmo shader (SG_Character, pelo EnsureMaterial) e mesma mascara; so muda o atlas do conjunto.
                var material = CharacterPrefabBuilder.EnsureMaterial($"M_{hero}_{suffix}", $"{PartsDir(hero)}/T_{hero}_{suffix}_BC.png", $"{PartsDir(hero)}/T_{hero}_{suffix}_M.png");
                for (var i = 0; i < SlotNames.Length; i++)
                {
                    var slotName = SlotNames[i];
                    var fbx = $"{PartsDir(hero)}/SK_{hero}_{slotName}_{suffix}.fbx";
                    var model = AssetDatabase.LoadAssetAtPath<GameObject>(fbx);
                    if (model == null) throw new InvalidOperationException("FBX da peca ausente: " + fbx);

                    var instance = (GameObject)UnityEngine.Object.Instantiate(model);
                    instance.name = $"P_{hero}_{slotName}_{suffix}";
                    foreach (var smr in instance.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                    {
                        smr.sharedMaterial = material;
                        smr.shadowCastingMode = ShadowCastingMode.On;
                        smr.receiveShadows = true;
                        smr.updateWhenOffscreen = false;
                    }
                    var prefab = PrefabUtility.SaveAsPrefabAsset(instance, $"{PartsDir(hero)}/{instance.name}.prefab");
                    UnityEngine.Object.DestroyImmediate(instance);

                    var part = SandboxBuilder.LoadOrCreate<HeroPart>($"{PartsDir(hero)}/SO_HeroPart_{hero}_{slotName}_{suffix}.asset");
                    part.slot = (HeroPartSlot)i;
                    part.visualSetId = visualSetId;
                    part.hidesRegions = hides.TryGetValue(slotName, out var flags) ? flags : BodyRegion.None;
                    part.prefab = prefab;
                    EditorUtility.SetDirty(part);
                    catalog.parts.Add(part);
                }
            }
            EditorUtility.SetDirty(catalog);
            return catalog;
        }

        /// <summary>Liga o ModularCharacter, o HeroVisualEquipment e o atalho de desenvolvimento ao prefab do heroi.</summary>
        public static void AddModularComponents(GameObject instance, string hero)
        {
            var catalog = AssetDatabase.LoadAssetAtPath<HeroPartCatalog>(CatalogPath(hero));
            if (catalog == null) catalog = BuildHero(hero); // prefab do heroi montado antes do BuildAll (ex.: pela Cripta)
            var modular = instance.GetComponent<ModularCharacter>();
            if (modular == null) modular = instance.AddComponent<ModularCharacter>();
            SandboxBuilder.SetRef(modular, "catalog", catalog);
            if (instance.GetComponent<HeroVisualEquipment>() == null) instance.AddComponent<HeroVisualEquipment>();
            if (instance.GetComponent<ModularDevKeys>() == null) instance.AddComponent<ModularDevKeys>();
        }
    }
}
