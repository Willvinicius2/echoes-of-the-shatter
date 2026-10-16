using UnityEditor;
using UnityEngine;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Importação reproduzível de personagens (docs/04_arquitetura.md, seções 17.1 e 17.4), para tudo em
    /// <c>Assets/Art/Characters/</c>: escala 1 (Convert Units ligado), Humanoid com o avatar do
    /// <c>Rig_Humanoid_Chibi</c>, Optimize Game Objects desligado (heróis modulares), normais importadas, sem tangentes
    /// (sem normal map), UV0 só, sem malha legível; albedo <c>_BC</c> sRGB 1024 em alta qualidade, máscara <c>_M</c> linear 512.
    /// Menu: Echoes ▸ Reimportar personagens (reimporta o rig primeiro, para os demais copiarem o avatar dele).
    /// </summary>
    public sealed class CharacterAssetPostprocessor : AssetPostprocessor
    {
        public const string CharactersRoot = "Assets/Art/Characters/";
        public const string WeaponsRoot = "Assets/Art/Weapons/";

        /// <summary>Modelos sem pernas ou sem o conjunto humanoide: Generic (o avatar Humanoid falharia). O Arqueiro Espectral flutua.</summary>
        static bool IsGeneric(string path) => path.IndexOf("GhostArcher", System.StringComparison.Ordinal) >= 0;

        /// <summary>
        /// Modelos de escala bem diferente da do rig (Arauto e Guardiao, 2x a 3x maiores): avatar Humanoid proprio. Com o avatar do rig o
        /// retarget escala a altura do quadril pela proporcao do rig e o corpo grande afunda (achatado). Heroi e Sentinela, na escala do rig, copiam o avatar dele.
        /// </summary>
        public static bool OwnsAvatar(string path) =>
            path.IndexOf("StoneHerald", System.StringComparison.Ordinal) >= 0 || path.IndexOf("CryptGuardian", System.StringComparison.Ordinal) >= 0;

        static bool IsManaged(string path) =>
            path.StartsWith(CharactersRoot, System.StringComparison.Ordinal) || path.StartsWith(WeaponsRoot, System.StringComparison.Ordinal);
        public const string RigPath = "Assets/Art/Characters/Rigs/Rig_Humanoid_Chibi.fbx";

        // Muda quando as regras abaixo mudam: força a reimportação.
        public override uint GetVersion() => 8;

        void OnPreprocessModel()
        {
            if (assetPath.StartsWith(KayKitAnimationImport.Root, System.StringComparison.Ordinal))
            {
                ConfigureAnimationSource((ModelImporter)assetImporter);
                return;
            }
            if (assetPath.StartsWith(EchoesAnimationImport.Root, System.StringComparison.Ordinal))
            {
                ConfigureEchoesClip((ModelImporter)assetImporter);
                return;
            }
            if (!IsManaged(assetPath)) return;
            var importer = (ModelImporter)assetImporter;
            var isWeapon = assetPath.StartsWith(WeaponsRoot, System.StringComparison.Ordinal);

            importer.globalScale = 1f;
            importer.useFileScale = true;           // Convert Units: o FBX vem em cm (fator 100), o Unity converte para 1 unidade = 1 m
            importer.bakeAxisConversion = false;
            importer.importNormals = ModelImporterNormals.Import;
            importer.importTangents = ModelImporterTangents.None;
            importer.importBlendShapes = false;
            importer.importCameras = false;
            importer.importLights = false;
            importer.importVisibility = false;
            importer.generateSecondaryUV = false;
            importer.isReadable = false;
            importer.meshCompression = ModelImporterMeshCompression.Off;
            importer.weldVertices = true;
            importer.skinWeights = ModelImporterSkinWeights.Standard; // até 4 influências por vértice
            importer.optimizeGameObjects = false;                      // heróis modulares expõem os 55 ossos (17.4)
            importer.materialImportMode = ModelImporterMaterialImportMode.None; // materiais são os M_ do projeto (17.1)
            importer.importAnimation = false;                          // sem clipes até a etapa de animação
            if (isWeapon)
            {
                // Arma estatica (SM_Weapon_*): pivo na empunhadura, sem esqueleto nem avatar.
                importer.animationType = ModelImporterAnimationType.None;
                return;
            }
            importer.animationType = IsGeneric(assetPath) ? ModelImporterAnimationType.Generic : ModelImporterAnimationType.Human;

            if (IsGeneric(assetPath))
            {
                importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            }
            else if (assetPath == RigPath || OwnsAvatar(assetPath))
            {
                importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            }
            else
            {
                var rigAvatar = AssetDatabase.LoadAssetAtPath<Avatar>(RigPath);
                if (rigAvatar != null)
                {
                    importer.avatarSetup = ModelImporterAvatarSetup.CopyFromOther;
                    importer.sourceAvatar = rigAvatar;
                }
                else
                {
                    importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
                }
            }
        }

        // Fonte de clipes (KayKit, CC0): Humanoid com o avatar do proprio FBX; os clipes, o loop e o "sem root motion" saem de
        // KayKitAnimationImport (so os clipes necessarios). Nenhuma malha dessas fontes entra no jogo.
        static void ConfigureAnimationSource(ModelImporter importer)
        {
            importer.globalScale = 1f;
            importer.useFileScale = true;
            importer.importAnimation = true;
            importer.animationType = ModelImporterAnimationType.Human;
            importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            importer.materialImportMode = ModelImporterMaterialImportMode.None;
            importer.importBlendShapes = false;
            importer.importCameras = false;
            importer.importLights = false;
            importer.isReadable = false;
            importer.optimizeGameObjects = false;
            importer.importTangents = ModelImporterTangents.None;
            importer.generateSecondaryUV = false;
        }

        // Golpes do Blender (Echoes): so armature, um clipe por FBX. O avatar vem do modelo dono do esqueleto (retarget Humanoid ou Generic).
        void ConfigureEchoesClip(ModelImporter importer)
        {
            importer.globalScale = 1f;
            importer.useFileScale = true;
            importer.importAnimation = true;
            importer.materialImportMode = ModelImporterMaterialImportMode.None;
            importer.importBlendShapes = false;
            importer.importCameras = false;
            importer.importLights = false;
            importer.isReadable = false;
            importer.optimizeGameObjects = false;
            importer.importTangents = ModelImporterTangents.None;
            importer.generateSecondaryUV = false;

            var name = System.IO.Path.GetFileNameWithoutExtension(assetPath);
            if (name.StartsWith("AN_GhostArcher", System.StringComparison.Ordinal))
            {
                // Generic: o clipe anima por caminho de Transform; avatar proprio (sem depender da ordem de importacao do modelo).
                importer.animationType = ModelImporterAnimationType.Generic;
                importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            }
            else if (name.StartsWith("AN_Guardian", System.StringComparison.Ordinal))
            {
                // Esqueleto do m08: avatar Humanoid proprio do Guardiao (o retarget para o prefab usa o avatar do modelo).
                importer.animationType = ModelImporterAnimationType.Human;
                importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            }
            else
            {
                // Stun compartilhado: Rig_Humanoid_Chibi.
                importer.animationType = ModelImporterAnimationType.Human;
                var rigAvatar = AssetDatabase.LoadAssetAtPath<Avatar>(RigPath);
                importer.avatarSetup = rigAvatar != null ? ModelImporterAvatarSetup.CopyFromOther : ModelImporterAvatarSetup.CreateFromThisModel;
                if (rigAvatar != null) importer.sourceAvatar = rigAvatar;
            }
        }

        // Os clipes Generic do Espectro vieram do Blender com a escala do osso Hips gravada em 0,12 (o modelo tem 1): o corpo encolhia.
        // Escala nao e animada no jogo; as curvas de escala dos clipes Echoes saem na importacao.
        void OnPostprocessAnimation(GameObject root, AnimationClip clip)
        {
            if (!assetPath.StartsWith(EchoesAnimationImport.Root, System.StringComparison.Ordinal)) return;
            foreach (var binding in AnimationUtility.GetCurveBindings(clip))
            {
                if (binding.propertyName.StartsWith("m_LocalScale", System.StringComparison.Ordinal)) AnimationUtility.SetEditorCurve(clip, binding, null);
            }
        }

        void OnPreprocessTexture()
        {
            if (!IsManaged(assetPath)) return;
            var importer = (TextureImporter)assetImporter;
            var isMask = System.IO.Path.GetFileNameWithoutExtension(assetPath).EndsWith("_M", System.StringComparison.Ordinal);

            importer.textureType = TextureImporterType.Default; // nunca NormalMap
            importer.sRGBTexture = !isMask;                     // albedo sRGB, máscara linear
            importer.isReadable = false;
            importer.mipmapEnabled = true;
            importer.streamingMipmaps = true;
            importer.alphaSource = TextureImporterAlphaSource.None;
            importer.maxTextureSize = isMask ? 512 : 1024;
            importer.textureCompression = isMask ? TextureImporterCompression.Compressed : TextureImporterCompression.CompressedHQ;
            importer.wrapMode = TextureWrapMode.Clamp;
        }

        [MenuItem("Echoes/Reimportar personagens")]
        public static void ReimportAll()
        {
            AssetDatabase.ImportAsset(RigPath, ImportAssetOptions.ForceUpdate);
            foreach (var filter in new[] { "t:Model", "t:Texture" })
            {
                foreach (var guid in AssetDatabase.FindAssets(filter, new[] { "Assets/Art/Characters", "Assets/Art/Weapons" }))
                {
                    var path = AssetDatabase.GUIDToAssetPath(guid);
                    if (path != RigPath) AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
                }
            }
        }
    }
}
