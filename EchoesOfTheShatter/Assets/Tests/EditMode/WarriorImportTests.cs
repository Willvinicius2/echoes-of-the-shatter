using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace Echoes.Tests.EditMode
{
    /// <summary>Importação do Guerreiro conforme docs/04, seções 17.1 e 17.4, e o mestre SG_Character.</summary>
    [Category("Art")]
    public sealed class WarriorImportTests
    {
        const string Fbx = "Assets/Art/Characters/Warrior/SK_Warrior.fbx";
        const string Rig = "Assets/Art/Characters/Rigs/Rig_Humanoid_Chibi.fbx";

        [Test]
        public void ModelIsImportedAsHumanoidAtScaleOneWithoutOptimization()
        {
            var importer = (ModelImporter)AssetImporter.GetAtPath(Fbx);
            Assert.IsNotNull(importer);
            Assert.AreEqual(1f, importer.globalScale);
            Assert.IsTrue(importer.useFileScale, "Convert Units");
            Assert.AreEqual(ModelImporterAnimationType.Human, importer.animationType);
            Assert.IsFalse(importer.optimizeGameObjects, "heróis modulares expõem os ossos (17.4)");
            Assert.AreEqual(ModelImporterTangents.None, importer.importTangents, "sem normal map");
            Assert.IsFalse(importer.isReadable);
            Assert.IsFalse(importer.generateSecondaryUV);
        }

        [Test]
        public void WarriorUsesTheRigAvatar()
        {
            var importer = (ModelImporter)AssetImporter.GetAtPath(Fbx);
            var rigAvatar = AssetDatabase.LoadAssetAtPath<Avatar>(Rig);
            Assert.IsNotNull(rigAvatar, "avatar do Rig_Humanoid_Chibi");
            Assert.IsTrue(rigAvatar.isHuman, "o rig deve ser um humanoide válido");
            Assert.AreEqual(ModelImporterAvatarSetup.CopyFromOther, importer.avatarSetup);
            Assert.AreEqual(rigAvatar, importer.sourceAvatar);
        }

        [Test]
        public void TexturesHaveTheRightColorSpaceAndNoNormalMap()
        {
            var albedo = (TextureImporter)AssetImporter.GetAtPath("Assets/Art/Characters/Warrior/T_Warrior_BC.png");
            var mask = (TextureImporter)AssetImporter.GetAtPath("Assets/Art/Characters/Warrior/T_Warrior_M.png");
            Assert.IsTrue(albedo.sRGBTexture);
            Assert.IsFalse(mask.sRGBTexture, "máscara é linear");
            Assert.AreEqual(TextureImporterType.Default, albedo.textureType);
            Assert.AreEqual(TextureImporterType.Default, mask.textureType);
            Assert.AreEqual(TextureImporterCompression.CompressedHQ, albedo.textureCompression);
            Assert.LessOrEqual(albedo.maxTextureSize, 1024);
            Assert.LessOrEqual(mask.maxTextureSize, 512);
            Assert.IsFalse(albedo.isReadable);
        }

        [Test]
        public void ModelIsAboutTheApprovedHeightAndWithinTheTriangleBudget()
        {
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(Fbx);
            var renderers = model.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            Assert.IsNotEmpty(renderers);
            var triangles = renderers.Sum(r => r.sharedMesh.triangles.Length / 3);
            Assert.LessOrEqual(triangles, 10000, "teto duro do herói (17.2)");
            var bounds = renderers[0].sharedMesh.bounds;
            Assert.That(bounds.size.y, Is.InRange(1.4f, 2.0f), "altura em metros (escala 1)");
        }

        [Test]
        public void CharacterShaderExposesTheContractProperties()
        {
            var shader = Shader.Find("Echoes/SG_Character");
            Assert.IsNotNull(shader);
            foreach (var name in new[] { "_BaseMap", "_MaskMap", "_HitFlash", "_Dissolve", "_TintColor", "_TintStrength", "_FresnelStrength", "_EmissionColor" })
                Assert.GreaterOrEqual(shader.FindPropertyIndex(name), 0, name);
            var material = new Material(shader);
            Assert.AreEqual(2.5f, material.GetFloat("_FresnelStrength"));
            Object.DestroyImmediate(material);
        }

        [Test]
        public void HeroPrefabKeepsTheRestPoseWithAnAnimatorReadyForTheAnimationStage()
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Art/Prefabs/P_Hero_Warrior.prefab");
            Assert.IsNotNull(prefab, "rode Echoes/Montar prefabs de personagens");
            var animator = prefab.GetComponentInChildren<Animator>();
            Assert.IsNotNull(animator, "Animator preparado");
            Assert.IsTrue(animator.avatar != null && animator.avatar.isHuman, "avatar Humanoid");
            var material = AssetDatabase.LoadAssetAtPath<Material>("Assets/Art/Materials/Characters/M_Warrior_Body.mat");
            Assert.IsNotNull(material);
            Assert.AreEqual("Echoes/SG_Character", material.shader.name);
            foreach (var smr in prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                Assert.AreEqual(material, smr.sharedMaterial);
        }
    }
}
