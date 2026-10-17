using System.IO;
using System.Linq;
using Echoes.EditorTools;
using Echoes.Presentation;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.TestTools;

namespace Echoes.Tests.EditMode
{
    /// <summary>Herois modulares (docs/04, 17.4): catalogos, pecas, mascara de regioes, ossos compartilhados e resolucao do visualSetId com fallback.</summary>
    [Category("Modular")]
    public sealed class ModularHeroTests
    {
        [OneTimeSetUp]
        public void Build()
        {
            CharacterPrefabBuilder.BuildAll();
        }

        static GameObject InstantiateHero(string hero)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>($"Assets/Art/Prefabs/P_Hero_{hero}.prefab");
            Assert.IsNotNull(prefab, hero);
            var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            go.GetComponent<ModularCharacter>().Build();
            return go;
        }

        [Test]
        public void CatalogsHaveTheFiveStarterPartsWithTheRegionMasksFromTheArt()
        {
            foreach (var hero in HeroModularBuilder.Heroes)
            {
                var catalog = AssetDatabase.LoadAssetAtPath<HeroPartCatalog>(HeroModularBuilder.CatalogPath(hero));
                Assert.IsNotNull(catalog, hero);
                Assert.AreEqual(5, catalog.parts.Count, hero);
                var hides = HeroModularBuilder.ReadHides(hero);
                for (var i = 0; i < 5; i++)
                {
                    Assert.IsTrue(catalog.TryGet((HeroPartSlot)i, HeroPartCatalog.StarterSet, out var part), $"{hero}/{(HeroPartSlot)i}");
                    Assert.IsNotNull(part.prefab, part.name);
                    Assert.AreEqual(hides[HeroModularBuilder.SlotNames[i]], part.hidesRegions, part.name + ": regioes escondidas do hides_regions.json");
                    StringAssert.StartsWith($"SO_HeroPart_{hero}_{HeroModularBuilder.SlotNames[i]}_", part.name);
                }
            }
            var chest = AssetDatabase.LoadAssetAtPath<HeroPart>($"{HeroModularBuilder.PartsDir("Warrior")}/SO_HeroPart_Warrior_Chest_Starter.asset");
            Assert.AreEqual(BodyRegion.Torso | BodyRegion.Arms, chest.hidesRegions, "o peitoral esconde tronco e bracos (17.4)");
        }

        [Test]
        public void HeroPrefabsHaveTheSixBodyRegionsAndTheModularComponents()
        {
            foreach (var hero in HeroModularBuilder.Heroes)
            {
                var go = InstantiateHero(hero);
                try
                {
                    var names = go.GetComponentsInChildren<SkinnedMeshRenderer>(true).Select(s => s.name).ToList();
                    foreach (var region in new[] { "Body_Head", "Body_Torso", "Body_Arms", "Body_Hands", "Body_Legs", "Body_Feet" })
                        CollectionAssert.Contains(names, region, hero);
                    Assert.IsNotNull(go.GetComponent<HeroVisualEquipment>());
                    Assert.IsNotNull(go.GetComponent<ModularDevKeys>());
                    Assert.AreEqual(BodyRegion.All, go.GetComponent<ModularCharacter>().VisibleRegions, "corpo nu antes de vestir");
                    var animator = go.GetComponent<Animator>();
                    Assert.IsTrue(animator.avatar.isHuman, hero + ": Humanoid");
                    Assert.IsTrue(animator.hasTransformHierarchy, "Optimize desligado: os ossos existem como Transform");
                }
                finally
                {
                    Object.DestroyImmediate(go);
                }
            }
            // O controller AC_Warrior no prefab e conferido em AnimationTests.PrefabsCarryTheirController (a recriacao dos controllers entre
            // fixtures faz a referencia em memoria variar com a ordem; no disco o prefab sempre sai com o controller).
        }

        [Test]
        public void EquippingHidesRegionsAndSharesTheHeroBones()
        {
            foreach (var hero in HeroModularBuilder.Heroes)
            {
                var go = InstantiateHero(hero);
                try
                {
                    var modular = go.GetComponent<ModularCharacter>();
                    Assert.IsNotNull(modular.Catalog, hero + ": catalogo ligado no prefab");
                    Assert.AreEqual(5, modular.Catalog.parts.Count, hero);
                    for (var i = 0; i < 5; i++) modular.Equip((HeroPartSlot)i, HeroPartCatalog.StarterSet);
                    Assert.AreEqual(BodyRegion.None, modular.VisibleRegions, hero + ": armadura completa cobre o corpo todo");

                    var hips = go.GetComponentsInChildren<Transform>(true).First(t => t.name == "Hips");
                    var partRenderers = go.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(s => !s.name.StartsWith("Body_")).ToList();
                    Assert.AreEqual(5, partRenderers.Count, hero + ": uma malha por peca");
                    foreach (var smr in partRenderers)
                    {
                        Assert.IsNotNull(smr.rootBone, smr.name);
                        Assert.IsTrue(smr.rootBone.IsChildOf(go.transform), smr.name + ": osso raiz do heroi");
                        foreach (var bone in smr.bones)
                        {
                            Assert.IsNotNull(bone, smr.name);
                            Assert.IsTrue(bone.IsChildOf(go.transform), smr.name + ": osso " + bone.name + " e do heroi (compartilhado)");
                        }
                    }
                    Assert.AreEqual(1, go.GetComponentsInChildren<Transform>(true).Count(t => t.name == "Hips"), "nenhum osso duplicado");

                    modular.Unequip(HeroPartSlot.Head);
                    Assert.AreEqual(BodyRegion.Head, modular.VisibleRegions, "sem elmo, a cabeca do corpo aparece");
                    modular.Unequip(HeroPartSlot.Feet);
                    Assert.AreEqual(BodyRegion.Head | BodyRegion.Feet, modular.VisibleRegions);
                    modular.Equip(HeroPartSlot.Head, HeroPartCatalog.StarterSet);
                    Assert.AreEqual(BodyRegion.Feet, modular.VisibleRegions);
                    Assert.AreEqual(4, go.GetComponentsInChildren<SkinnedMeshRenderer>(true).Count(s => !s.name.StartsWith("Body_")), "pecas nao se acumulam");
                    Assert.IsNotNull(hips);
                }
                finally
                {
                    Object.DestroyImmediate(go);
                }
            }
        }

        [Test]
        public void UnknownVisualSetFallsBackToStarterWithAWarning()
        {
            var go = InstantiateHero("Warrior");
            try
            {
                var modular = go.GetComponent<ModularCharacter>();
                LogAssert.Expect(LogType.Warning, new System.Text.RegularExpressions.Regex("vset.inexistente"));
                var part = modular.Equip(HeroPartSlot.Chest, "vset.inexistente");
                Assert.IsNotNull(part);
                Assert.AreEqual(HeroPartCatalog.StarterSet, part.visualSetId, "fallback vset.starter");
            }
            finally
            {
                Object.DestroyImmediate(go);
            }
        }

        [Test]
        public void VisualSetComesFromTheCoreAndTheSlotFromTheItemBase()
        {
            using (var rules = TestWorld.LoadNativeRules())
            {
                var native = (Echoes.Interop.Native.NativeRulesCore)rules;
                Assert.IsFalse(VisualSetResolver.TryResolve(rules, "item_base.iron_sword", null, out _, out _), "arma: sem visual modular");
                Assert.IsTrue(VisualSetResolver.TryResolve(rules, "item_base.iron_helm", null, out var slot, out var set));
                Assert.AreEqual(HeroPartSlot.Head, slot);
                Assert.AreEqual(HeroPartCatalog.StarterSet, set, "base com vset.starter");
                Assert.IsTrue(VisualSetResolver.TryResolve(rules, "item_base.worn_trousers", null, out slot, out set));
                Assert.AreEqual(HeroPartSlot.Legs, slot, "slot legs do core");
                Assert.AreEqual("vset.starter", native.ItemVisualSetId("item_base.leather_vest", string.Empty), "pelo shatter_item_visual_set_id");
                Assert.AreEqual("vset.starter", native.ItemVisualSetId("item_base.stone_maul", "unique.empty_throne_maul"), "Unico sem conjunto proprio: cai no starter");
                Assert.IsFalse(VisualSetResolver.TryResolve(rules, "item_base.nao_existe", null, out _, out _));
            }
        }

        [Test]
        public void EquipmentFromTheCoreDrivesTheModularParts()
        {
            var go = InstantiateHero("Warrior");
            try
            {
                var equipment = go.GetComponent<HeroVisualEquipment>();
                // Hoje so ha a espada (arma): nenhuma peca vem do item; tudo cai no starter.
                using (var rules = TestWorld.LoadNativeRules()) equipment.Apply(new[] { ("item_base.iron_sword", string.Empty) }, rules);
                var modular = go.GetComponent<ModularCharacter>();
                for (var i = 0; i < 5; i++) Assert.IsTrue(modular.IsEquipped((HeroPartSlot)i), ((HeroPartSlot)i).ToString());
                Assert.AreEqual(BodyRegion.None, modular.VisibleRegions);
            }
            finally
            {
                Object.DestroyImmediate(go);
            }
        }

        [Test]
        public void ModularAssetsFollowTheImportRules()
        {
            var body = (ModelImporter)AssetImporter.GetAtPath($"{HeroModularBuilder.BodyDir("Warrior")}/SK_Warrior_Body.fbx");
            Assert.AreEqual(ModelImporterAnimationType.Human, body.animationType);
            Assert.IsFalse(body.optimizeGameObjects, "ossos como Transform");
            var part = (ModelImporter)AssetImporter.GetAtPath($"{HeroModularBuilder.PartsDir("Warrior")}/SK_Warrior_Chest_Starter.fbx");
            Assert.IsFalse(part.optimizeGameObjects);
            Assert.AreEqual(ModelImporterAnimationType.Generic, part.animationType, "peca continua SkinnedMeshRenderer");
            var mask = (TextureImporter)AssetImporter.GetAtPath($"{HeroModularBuilder.PartsDir("Warrior")}/T_Warrior_Starter_M.png");
            Assert.IsFalse(mask.sRGBTexture, "mascara linear");
        }
    }
}
