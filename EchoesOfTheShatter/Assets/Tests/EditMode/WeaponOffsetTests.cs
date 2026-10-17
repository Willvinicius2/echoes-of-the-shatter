using Echoes.EditorTools;
using Echoes.Presentation;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace Echoes.Tests.EditMode
{
    /// <summary>SO_WeaponOffset por arma (apresentacao): existe um por arma e e aplicado no socket; arco e cajado ficam em pe, escudo de frente, martelo inalterado.</summary>
    [Category("Weapons")]
    public sealed class WeaponOffsetTests
    {
        [OneTimeSetUp]
        public void Build()
        {
            CharacterPrefabBuilder.BuildAll();
        }

        [Test]
        public void EveryWeaponHasItsOwnOffsetAsset()
        {
            foreach (var name in WeaponOffsetBuilder.Names)
            {
                var so = AssetDatabase.LoadAssetAtPath<WeaponOffsetAsset>($"{WeaponOffsetBuilder.Dir}/SO_WeaponOffset_{name}.asset");
                Assert.IsNotNull(so, name);
                Assert.AreEqual(name, so.weaponName);
                Assert.Greater(so.uniformScale, 0f, name);
            }
        }

        static Transform Weapon(string prefab, string weapon)
        {
            var go = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>($"Assets/Art/Prefabs/{prefab}.prefab"));
            var t = CharacterPrefabBuilder.FindDeep(go.transform, "Weapon_" + weapon);
            Assert.IsNotNull(t, prefab + ": " + weapon);
            return t;
        }

        [TestCase("P_Hero_Archer", "Bow")]
        [TestCase("P_Hero_Mage", "Staff")]
        [TestCase("P_Hero_Warrior", "WarriorShield")]
        [TestCase("P_Hero_Warrior", "WarriorHammer")]
        [TestCase("P_Boss_CryptGuardian", "GuardianShield")]
        [TestCase("P_Boss_CryptGuardian", "GuardianHammer")]
        public void OffsetIsAppliedAtTheSocket(string prefab, string weapon)
        {
            var t = Weapon(prefab, weapon);
            try
            {
                var so = AssetDatabase.LoadAssetAtPath<WeaponOffsetAsset>($"{WeaponOffsetBuilder.Dir}/SO_WeaponOffset_{weapon}.asset");
                Assert.AreEqual(0f, Vector3.Distance(so.localPosition, t.localPosition), 1e-4f);
                Assert.AreEqual(0f, Quaternion.Angle(Quaternion.Euler(so.localEuler), t.localRotation), 0.01f);
                Assert.AreEqual(so.uniformScale, t.localScale.x, 1e-4f);
            }
            finally
            {
                Object.DestroyImmediate(t.root.gameObject);
            }
        }

        [TestCase("P_Hero_Archer", "Bow")]
        [TestCase("P_Hero_Mage", "Staff")]
        public void BowAndStaffLengthPointsAlongTheHandAxisNotAcrossIt(string prefab, string weapon)
        {
            // O comprimento do arco e do cajado e o eixo Y do FBX; em pe = esse eixo no eixo Z do socket (a mao pendurada, Z para cima).
            var t = Weapon(prefab, weapon);
            try
            {
                var inSocket = t.parent.InverseTransformDirection(t.up);
                Assert.Greater(Vector3.Dot(inSocket.normalized, Vector3.forward), 0.99f, prefab + ": comprimento ao longo do eixo Z da mao");
            }
            finally
            {
                Object.DestroyImmediate(t.root.gameObject);
            }
        }

        [Test]
        public void ShieldFaceNormalPointsOutAlongTheHandForwardAxis()
        {
            var t = Weapon("P_Hero_Warrior", "WarriorShield");
            try
            {
                var normal = t.parent.InverseTransformDirection(t.forward);
                Assert.Greater(Mathf.Abs(Vector3.Dot(normal.normalized, Vector3.up)), 0.99f, "a face do escudo aponta pelo eixo Y da mao (para fora), nao deitada");
            }
            finally
            {
                Object.DestroyImmediate(t.root.gameObject);
            }
        }
    }
}
