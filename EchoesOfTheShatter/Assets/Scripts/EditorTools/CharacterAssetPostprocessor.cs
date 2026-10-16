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
        public const string RigPath = "Assets/Art/Characters/Rigs/Rig_Humanoid_Chibi.fbx";

        // Muda quando as regras abaixo mudam: força a reimportação.
        public override uint GetVersion() => 2;

        void OnPreprocessModel()
        {
            if (!assetPath.StartsWith(CharactersRoot, System.StringComparison.Ordinal)) return;
            var importer = (ModelImporter)assetImporter;

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
            importer.animationType = ModelImporterAnimationType.Human;

            if (assetPath == RigPath)
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
            if (!assetPath.StartsWith(CharactersRoot, System.StringComparison.Ordinal)) return;
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
                foreach (var guid in AssetDatabase.FindAssets(filter, new[] { "Assets/Art/Characters" }))
                {
                    var path = AssetDatabase.GUIDToAssetPath(guid);
                    if (path != RigPath) AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
                }
            }
        }
    }
}
