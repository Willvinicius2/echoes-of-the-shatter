using UnityEditor;
using UnityEngine;

namespace Echoes.EditorTools
{
    /// <summary>Importacao dos recortes da UI (Assets/Resources/UiArt): sem mipmap, sem compressao, borda presa e alfa como transparencia (9-slice limpo).</summary>
    public sealed class UiArtImporter : AssetPostprocessor
    {
        public const string Folder = "Assets/Resources/UiArt/";

        void OnPreprocessTexture()
        {
            if (!assetPath.StartsWith(Folder, System.StringComparison.Ordinal)) return;
            var importer = (TextureImporter)assetImporter;
            importer.textureType = TextureImporterType.Default;
            importer.mipmapEnabled = false;
            importer.alphaIsTransparency = true;
            importer.wrapMode = TextureWrapMode.Clamp;
            importer.filterMode = FilterMode.Bilinear;
            importer.npotScale = TextureImporterNPOTScale.None;
            importer.textureCompression = TextureImporterCompression.Uncompressed;
            importer.maxTextureSize = 1024;
            importer.isReadable = false;
        }
    }
}
