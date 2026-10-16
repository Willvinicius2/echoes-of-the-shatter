using System;
using System.Collections.Generic;
using Echoes.Presentation;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Prefabs dos personagens pintados aprovados (Guerreiro, Sentinela Oca, Arauto de Pedra, Arqueiro Espectral e Guardião da Cripta) e das
    /// armas presas nos sockets das mãos (<c>socket_weapon_r</c> = RightHand, <c>socket_weapon_l</c> = LeftHand). Materiais <c>M_*</c> no
    /// <c>SG_Character</c> com albedo e máscara (R = emissão, G = rim, B = tinta), raridade Normal do SO_RarityTint. Sem animação ainda: os
    /// modelos ficam na pose de repouso e o Animator fica preparado (avatar Humanoid nos humanoides, Generic no Arqueiro) sem controlador.
    /// TODO(animação): ligar o AC_* e os clipes na etapa de animação (docs/04, seção 3.3).
    /// </summary>
    public static class CharacterPrefabBuilder
    {
        public const string MaterialDir = "Assets/Art/Materials/Characters";
        public const string PrefabDir = "Assets/Art/Prefabs";
        public const string ShaderPath = "Assets/Art/Materials/Masters/SG_Character.shader";
        const string CharactersDir = "Assets/Art/Characters";
        const string WeaponsDir = "Assets/Art/Weapons";

        public sealed class WeaponSpec
        {
            public string Name;   // SM_Weapon_<Name>.fbx
            public string[] Sockets; // em ordem de preferencia
        }

        public sealed class Spec
        {
            public string Folder, Model, Textures, Prefab, Material;
            public string Controller; // AC_* (null = sem animacao ainda: Arqueiro Espectral)
            public WeaponSpec[] Weapons = Array.Empty<WeaponSpec>();
        }

        static readonly string[] RightSockets = { "socket_weapon_r", "RightHand" };
        static readonly string[] LeftSockets = { "socket_weapon_l", "LeftHand" };

        public static readonly Spec Warrior = new Spec
        {
            Folder = "Warrior", Model = "SK_Warrior", Textures = "T_Warrior", Prefab = "P_Hero_Warrior", Material = "M_Warrior", Controller = "AC_Warrior",
            Weapons = new[] { new WeaponSpec { Name = "WarriorHammer", Sockets = RightSockets }, new WeaponSpec { Name = "WarriorShield", Sockets = LeftSockets } },
        };

        static readonly Dictionary<string, Spec> EnemySpecs = new Dictionary<string, Spec>
        {
            { "enemy.hollow_sentinel", new Spec { Folder = "HollowSentinel", Model = "SK_Enemy_HollowSentinel", Textures = "T_Enemy_HollowSentinel", Prefab = "P_Enemy_HollowSentinel", Material = "M_Enemy_HollowSentinel", Controller = "AC_EnemyHumanoid" } },
            { "enemy.shielded_sentinel", null },
            { "enemy.stone_herald", new Spec { Folder = "StoneHerald", Model = "SK_Enemy_StoneHerald", Textures = "T_Enemy_StoneHerald", Prefab = "P_Enemy_StoneHerald", Material = "M_Enemy_StoneHerald", Controller = "AC_EnemyHumanoid" } },
            { "enemy.ghost_archer", new Spec { Folder = "GhostArcher", Model = "SK_Enemy_GhostArcher", Textures = "T_Enemy_GhostArcher", Prefab = "P_Enemy_GhostArcher", Material = "M_Enemy_GhostArcher" } },
            {
                "enemy.crypt_guardian", new Spec
                {
                    Folder = "CryptGuardian", Model = "SK_Boss_CryptGuardian", Textures = "T_Boss_CryptGuardian", Prefab = "P_Boss_CryptGuardian", Material = "M_Boss_CryptGuardian", Controller = "AC_Boss",
                    Weapons = new[] { new WeaponSpec { Name = "GuardianHammer", Sockets = RightSockets }, new WeaponSpec { Name = "GuardianShield", Sockets = LeftSockets } },
                }
            },
        };

        [MenuItem("Echoes/Montar prefabs de personagens")]
        public static void BuildAll()
        {
            // 1) clipes KayKit e controllers; 2) prefabs (com o controller); 3) SO_SkillPresentation_* com o tempo do golpe medido no clipe.
            AnimatorControllerBuilder.BuildAll();
            var warrior = Build(Warrior);
            GameObject sentinel = null, boss = null;
            foreach (var pair in EnemySpecs)
            {
                if (pair.Value == null) continue;
                var prefab = Build(pair.Value);
                if (pair.Key == "enemy.hollow_sentinel") sentinel = prefab;
                if (pair.Key == "enemy.crypt_guardian") boss = prefab;
            }
            AnimatorControllerBuilder.BuildSkillSet(AnimatorControllerBuilder.Warrior, warrior);
            AnimatorControllerBuilder.BuildSkillSet(AnimatorControllerBuilder.EnemyHumanoid, sentinel);
            var bossSet = AnimatorControllerBuilder.BuildSkillSet(AnimatorControllerBuilder.Boss, boss);
            bossSet.roarClipSeconds = KayKitAnimationImport.FindClip(AnimatorControllerBuilder.Boss.Actions.Find(a => a.State == "Roar").Fbx, "Flexing").length;
            EditorUtility.SetDirty(bossSet);
            AssetDatabase.SaveAssets();
        }

        public static GameObject BuildWarrior() => Build(Warrior);

        /// <summary>Prefab pintado do inimigo (o elite Escudado usa o da Sentinela); null para os que ainda sao graybox (Cao, Lanceira).</summary>
        public static GameObject PrefabForEnemy(string enemyId)
        {
            if (enemyId == "enemy.shielded_sentinel") enemyId = "enemy.hollow_sentinel";
            if (!EnemySpecs.TryGetValue(enemyId, out var spec) || spec == null) return null;
            var path = $"{PrefabDir}/{spec.Prefab}.prefab";
            return AssetDatabase.LoadAssetAtPath<GameObject>(path) ?? Build(spec);
        }

        public static string PrefabPathFor(string enemyId)
        {
            if (enemyId == "enemy.shielded_sentinel") enemyId = "enemy.hollow_sentinel";
            return EnemySpecs.TryGetValue(enemyId, out var spec) && spec != null ? $"{PrefabDir}/{spec.Prefab}.prefab" : null;
        }

        public static GameObject Build(Spec spec)
        {
            SandboxBuilder.EnsureDir(MaterialDir);
            SandboxBuilder.EnsureDir(PrefabDir);
            var folder = $"{CharactersDir}/{spec.Folder}";
            var model = AssetDatabase.LoadAssetAtPath<GameObject>($"{folder}/{spec.Model}.fbx");
            if (model == null) throw new InvalidOperationException($"FBX ausente: {folder}/{spec.Model}.fbx");
            var material = EnsureMaterial(spec.Material, $"{folder}/{spec.Textures}_BC.png", $"{folder}/{spec.Textures}_M.png");

            var instance = UnityEngine.Object.Instantiate(model);
            instance.name = spec.Prefab;
            // Animator com o avatar Humanoid (copiado do Rig_Humanoid_Chibi) ou Generic (Arqueiro Espectral, sem animacao ainda: sem controller)
            // e o AC_* do KayKit (animacoes CC0); o PresentationController toca os estados a partir dos eventos do combate.
            var animator = instance.GetComponent<Animator>();
            if (animator == null) animator = instance.AddComponent<Animator>();
            animator.applyRootMotion = false; // sem root motion: a logica move o personagem
            animator.runtimeAnimatorController = spec.Controller != null ? AnimatorControllerBuilder.Load(spec.Controller) : null;
            if (animator.avatar == null) animator.avatar = AvatarOf($"{folder}/{spec.Model}.fbx");
            foreach (var smr in instance.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                smr.sharedMaterial = material;
                smr.shadowCastingMode = ShadowCastingMode.On; // personagens projetam sombra (docs/04, secao 3.6)
                smr.receiveShadows = true;
                smr.updateWhenOffscreen = false;
            }
            foreach (var weapon in spec.Weapons) AttachWeapon(instance.transform, weapon);

            var prefab = PrefabUtility.SaveAsPrefabAsset(instance, $"{PrefabDir}/{spec.Prefab}.prefab");
            UnityEngine.Object.DestroyImmediate(instance);
            return prefab;
        }

        static Avatar AvatarOf(string fbxPath)
        {
            var importer = AssetImporter.GetAtPath(fbxPath) as ModelImporter;
            if (importer != null && importer.avatarSetup == ModelImporterAvatarSetup.CopyFromOther && importer.sourceAvatar != null) return importer.sourceAvatar;
            foreach (var asset in AssetDatabase.LoadAllAssetRepresentationsAtPath(fbxPath))
            {
                if (asset is Avatar avatar) return avatar;
            }
            return null;
        }

        static void AttachWeapon(Transform root, WeaponSpec weapon)
        {
            var model = AssetDatabase.LoadAssetAtPath<GameObject>($"{WeaponsDir}/SM_Weapon_{weapon.Name}.fbx");
            if (model == null)
            {
                Debug.LogWarning($"[CharacterPrefabBuilder] Arma ausente: SM_Weapon_{weapon.Name}.fbx");
                return;
            }
            Transform socket = null;
            foreach (var name in weapon.Sockets)
            {
                socket = FindDeep(root, name);
                if (socket != null) break;
            }
            if (socket == null)
            {
                Debug.LogWarning($"[CharacterPrefabBuilder] Socket de {weapon.Name} nao encontrado em {root.name}");
                return;
            }
            var material = EnsureMaterial($"M_Weapon_{weapon.Name}", $"{WeaponsDir}/T_Weapon_{weapon.Name}_BC.png", $"{WeaponsDir}/T_Weapon_{weapon.Name}_M.png");
            var go = UnityEngine.Object.Instantiate(model);
            go.name = "Weapon_" + weapon.Name;
            go.transform.SetParent(socket, false);
            go.transform.localPosition = Vector3.zero; // pivo na empunhadura (m09)
            go.transform.localRotation = Quaternion.identity;
            go.transform.localScale = Vector3.one;
            foreach (var c in go.GetComponentsInChildren<Collider>()) UnityEngine.Object.DestroyImmediate(c);
            foreach (var r in go.GetComponentsInChildren<Renderer>())
            {
                r.sharedMaterial = material;
                r.shadowCastingMode = ShadowCastingMode.On;
                r.receiveShadows = true;
            }
        }

        public static Transform FindDeep(Transform root, string name)
        {
            if (root.name == name) return root;
            for (var i = 0; i < root.childCount; i++)
            {
                var found = FindDeep(root.GetChild(i), name);
                if (found != null) return found;
            }
            return null;
        }

        /// <summary>M_*: SG_Character com albedo e mascara, raridade Normal do SO_RarityTint (os canais seguem R emissao, G rim, B tinta).</summary>
        public static Material EnsureMaterial(string name, string baseMapPath, string maskMapPath)
        {
            SandboxBuilder.EnsureDir(MaterialDir);
            var shader = AssetDatabase.LoadAssetAtPath<Shader>(ShaderPath);
            if (shader == null) throw new InvalidOperationException("Shader ausente: " + ShaderPath);
            var path = $"{MaterialDir}/{name}.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(shader);
                AssetDatabase.CreateAsset(mat, path);
            }
            mat.shader = shader;
            mat.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(baseMapPath));
            mat.SetTexture("_MaskMap", AssetDatabase.LoadAssetAtPath<Texture2D>(maskMapPath));
            mat.SetFloat("_HitFlash", 0f);
            mat.SetFloat("_Dissolve", 0f);
            mat.SetFloat("_RimMaskInfluence", 1f); // G da mascara = rim
            RarityTintBuilder.CreateOrUpdate().Apply(mat, RarityTier.Normal);
            EditorUtility.SetDirty(mat);
            return mat;
        }
    }
}
