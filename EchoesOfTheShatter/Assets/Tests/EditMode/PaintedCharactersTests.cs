using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Echoes.EditorTools;
using Echoes.Presentation;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace Echoes.Tests.EditMode
{
    /// <summary>
    /// Modelos pintados aprovados (Guerreiro, Sentinela Oca, Arauto de Pedra, Arqueiro Espectral, Guardião da Cripta) e armas: importação
    /// reproduzível, materiais no SG_Character, sockets das mãos e o SO_RarityTint com os valores dos tokens.
    /// </summary>
    [Category("Art")]
    public sealed class PaintedCharactersTests
    {
        static readonly (string folder, string model, string textures, string prefab, bool humanoid)[] Characters =
        {
            ("Warrior", "SK_Warrior", "T_Warrior", "P_Hero_Warrior", true),
            ("HollowSentinel", "SK_Enemy_HollowSentinel", "T_Enemy_HollowSentinel", "P_Enemy_HollowSentinel", true),
            ("StoneHerald", "SK_Enemy_StoneHerald", "T_Enemy_StoneHerald", "P_Enemy_StoneHerald", true),
            ("GhostArcher", "SK_Enemy_GhostArcher", "T_Enemy_GhostArcher", "P_Enemy_GhostArcher", false),
            ("CryptGuardian", "SK_Boss_CryptGuardian", "T_Boss_CryptGuardian", "P_Boss_CryptGuardian", true),
        };

        static readonly string[] Weapons = { "WarriorHammer", "WarriorShield", "GuardianHammer", "GuardianShield", "Quiver", "Staff", "Bow" };

        [OneTimeSetUp]
        public void BuildPrefabs()
        {
            CharacterPrefabBuilder.BuildAll(); // idempotente: monta materiais e prefabs (com as armas nos sockets) pelos mesmos caminhos
        }

        [Test]
        public void CharactersAreImportedAtScaleOneWithTheRightAvatarKind()
        {
            foreach (var c in Characters)
            {
                var path = $"Assets/Art/Characters/{c.folder}/{c.model}.fbx";
                var importer = (ModelImporter)AssetImporter.GetAtPath(path);
                Assert.IsNotNull(importer, path);
                Assert.AreEqual(1f, importer.globalScale, path);
                Assert.IsFalse(importer.optimizeGameObjects, path);
                Assert.AreEqual(ModelImporterTangents.None, importer.importTangents, path + ": sem normal map");
                Assert.AreEqual(c.humanoid ? ModelImporterAnimationType.Human : ModelImporterAnimationType.Generic, importer.animationType, path);
                if (c.humanoid)
                {
                    var own = CharacterAssetPostprocessor.OwnsAvatar(path); // escala propria (Arauto, Guardiao): avatar proprio, senao o corpo afunda
                    Assert.AreEqual(own ? ModelImporterAvatarSetup.CreateFromThisModel : ModelImporterAvatarSetup.CopyFromOther, importer.avatarSetup, path + ": avatar do Rig_Humanoid_Chibi ou proprio");
                }
            }
        }

        [Test]
        public void TexturesFollowTheMaskContract()
        {
            var paths = Characters.SelectMany(c => new[] { $"Assets/Art/Characters/{c.folder}/{c.textures}_BC.png", $"Assets/Art/Characters/{c.folder}/{c.textures}_M.png" })
                .Concat(Weapons.SelectMany(w => new[] { $"Assets/Art/Weapons/T_Weapon_{w}_BC.png", $"Assets/Art/Weapons/T_Weapon_{w}_M.png" }));
            foreach (var path in paths)
            {
                var importer = (TextureImporter)AssetImporter.GetAtPath(path);
                Assert.IsNotNull(importer, path);
                Assert.AreEqual(TextureImporterType.Default, importer.textureType, path + ": nunca normal map");
                Assert.AreEqual(!path.EndsWith("_M.png"), importer.sRGBTexture, path + ": albedo sRGB, mascara linear (R emissao, G rim, B tinta)");
                Assert.IsFalse(importer.isReadable, path);
            }
        }

        [Test]
        public void WeaponsAreStaticModelsWithoutRigOrAvatar()
        {
            foreach (var w in Weapons)
            {
                var path = $"Assets/Art/Weapons/SM_Weapon_{w}.fbx";
                var importer = (ModelImporter)AssetImporter.GetAtPath(path);
                Assert.IsNotNull(importer, path);
                Assert.AreEqual(ModelImporterAnimationType.None, importer.animationType, path);
                Assert.AreEqual(1f, importer.globalScale, path);
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                Assert.IsEmpty(model.GetComponentsInChildren<SkinnedMeshRenderer>(true), path + ": malha estatica");
            }
        }

        [Test]
        public void PrefabsUseTheCharacterShaderAndKeepTheAnimatorReady()
        {
            foreach (var c in Characters)
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>($"Assets/Art/Prefabs/{c.prefab}.prefab");
                Assert.IsNotNull(prefab, c.prefab + " (menu Echoes/Montar prefabs de personagens)");
                var animator = prefab.GetComponentInChildren<Animator>();
                Assert.IsNotNull(animator, c.prefab);
                Assert.IsNotNull(animator.avatar, c.prefab);
                Assert.AreEqual(c.humanoid, animator.avatar.isHuman, c.prefab + ": Humanoid so onde ha pernas");
                foreach (var renderer in prefab.GetComponentsInChildren<Renderer>(true))
                    Assert.AreEqual("Echoes/SG_Character", renderer.sharedMaterial.shader.name, c.prefab + "/" + renderer.name);
            }
        }

        [Test]
        public void HammerAndShieldAreAttachedToTheHandSockets()
        {
            foreach (var (prefabName, hammer, shield) in new[] { ("P_Hero_Warrior", "WarriorHammer", "WarriorShield"), ("P_Boss_CryptGuardian", "GuardianHammer", "GuardianShield") })
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>($"Assets/Art/Prefabs/{prefabName}.prefab");
                var right = CharacterPrefabBuilder.FindDeep(prefab.transform, "Weapon_" + hammer);
                var left = CharacterPrefabBuilder.FindDeep(prefab.transform, "Weapon_" + shield);
                Assert.IsNotNull(right, prefabName + ": martelo");
                Assert.IsNotNull(left, prefabName + ": escudo");
                Assert.IsTrue(right.parent.name == "socket_weapon_r" || right.parent.name == "RightHand", prefabName + ": martelo na mao direita (" + right.parent.name + ")");
                Assert.IsTrue(left.parent.name == "socket_weapon_l" || left.parent.name == "LeftHand", prefabName + ": escudo na mao esquerda (" + left.parent.name + ")");
                Assert.AreEqual(Vector3.zero, right.localPosition, "pivo na empunhadura");
                Assert.IsEmpty(right.GetComponentsInChildren<Collider>(), "arma sem colisor");
            }
        }

        [Test]
        public void CharacterShaderHasTheRarityProperties()
        {
            var shader = Shader.Find("Echoes/SG_Character");
            Assert.IsNotNull(shader);
            foreach (var name in new[] { "_TintDesat", "_TintGain", "_RimTint", "_RimTintMix", "_RimIntensity", "_AccentColor", "_AccentEmissive", "_AccentPulse", "_AccentPulsePeriod", "_HitFlash", "_Dissolve" })
                Assert.GreaterOrEqual(shader.FindPropertyIndex(name), 0, name);
        }

        [Test]
        public void RarityTintAssetMatchesTheTokens()
        {
            var tokens = RarityTintBuilder.ReadTokens();
            var asset = RarityTintBuilder.CreateOrUpdate();
            foreach (var (tier, key) in new[] { (RarityTier.Normal, "normal"), (RarityTier.Magic, "magic"), (RarityTier.Rare, "rare"), (RarityTier.Unique, "unique") })
            {
                var t = (Dictionary<string, object>)tokens[key];
                var e = asset.Get(tier);
                Assert.AreEqual(Num(t, "tint_strength"), e.tintStrength, 1e-6f, key);
                Assert.AreEqual(Num(t, "rim_intensity"), e.rimIntensity, 1e-6f, key);
                Assert.AreEqual(Num(t, "accent_emissive"), e.accentEmissive, 1e-6f, key);
                if (t.ContainsKey("tint_desat")) Assert.AreEqual(Num(t, "tint_desat"), e.tintDesat, 1e-6f, key);
                if (t.ContainsKey("tint_gain")) Assert.AreEqual(Num(t, "tint_gain"), e.tintGain, 1e-6f, key);
                if (t.ContainsKey("rim_tint_mix")) Assert.AreEqual(Num(t, "rim_tint_mix"), e.rimTintMix, 1e-6f, key);
                if (t.TryGetValue("tint_color", out var hex) && hex is string h && ColorUtility.TryParseHtmlString(h, out var color)) Assert.AreEqual(color, e.tintColor, key + " tint_color");
                if (t.TryGetValue("accent_color", out var ahex) && ahex is string ah && ColorUtility.TryParseHtmlString(ah, out var accent)) Assert.AreEqual(accent, e.accentColor, key + " accent_color");
            }
            Assert.IsTrue(asset.unique.pulse, "o Unico pulsa");
            Assert.AreEqual(2.4f, asset.unique.pulsePeriodSeconds, 1e-6f, "pulse_ms 2400");
            Assert.AreEqual(0f, asset.unique.tintStrength, "o Unico nao usa tinta de raridade");
        }

        [Test]
        public void RarityApplyWritesTheMaterialProperties()
        {
            var asset = RarityTintBuilder.CreateOrUpdate();
            var material = new Material(Shader.Find("Echoes/SG_Character"));
            try
            {
                asset.Apply(material, RarityTier.Rare);
                Assert.AreEqual(asset.rare.tintStrength, material.GetFloat("_TintStrength"), 1e-6f);
                Assert.AreEqual(asset.rare.tintDesat, material.GetFloat("_TintDesat"), 1e-6f);
                Assert.AreEqual(asset.rare.accentEmissive, material.GetFloat("_AccentEmissive"), 1e-6f);
                asset.Apply(material, RarityTier.Unique, reducedMotion: true);
                Assert.AreEqual(0f, material.GetFloat("_AccentPulse"), "Reduzir movimento: sem pulso");
                asset.Apply(material, RarityTier.Unique);
                Assert.AreEqual(1f, material.GetFloat("_AccentPulse"));
            }
            finally
            {
                Object.DestroyImmediate(material);
            }
        }

        static float Num(Dictionary<string, object> o, string key) => o.TryGetValue(key, out var v) && v is double d ? (float)d : 0f;
    }
}
