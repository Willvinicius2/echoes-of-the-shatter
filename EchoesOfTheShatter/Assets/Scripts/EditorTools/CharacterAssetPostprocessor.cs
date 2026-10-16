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

        static bool IsManaged(string path) =>
            path.StartsWith(CharactersRoot, System.StringComparison.Ordinal) || path.StartsWith(WeaponsRoot, System.StringComparison.Ordinal);
        public const string RigPath = "Assets/Art/Characters/Rigs/Rig_Humanoid_Chibi.fbx";

        // Muda quando as regras abaixo mudam: força a reimportação.
        public override uint GetVersion() => 3;

        void OnPreprocessModel()
        {
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
            else if (assetPath == RigPath)
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
