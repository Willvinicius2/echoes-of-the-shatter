using System.IO;
using UnityEngine;

namespace Echoes.Core
{
    /// <summary>
    /// Onde ficam os CSV. Destino final: <c>StreamingAssets/Data</c> (docs/04_arquitetura.md, seção 4.2).
    /// Enquanto os CSV não forem movidos, o editor lê direto de <c>EchoesOfTheShatter/Content/Data</c>.
    /// </summary>
    public static class ContentPaths
    {
        const string RulesFile = "rules.csv";

        public static string ResolveDataDirectory(string overridePath)
        {
            if (!string.IsNullOrEmpty(overridePath)) return overridePath;

            var streaming = Path.Combine(Application.streamingAssetsPath, "Data");
            if (File.Exists(Path.Combine(streaming, RulesFile))) return streaming;

            // Projeto: <raiz>/Assets → <raiz>/Content/Data (só existe no editor e em builds de desenvolvimento locais).
            var projectRoot = Path.GetDirectoryName(Application.dataPath) ?? string.Empty;
            var content = Path.Combine(projectRoot, "Content", "Data");
            if (File.Exists(Path.Combine(content, RulesFile))) return content;

            return streaming;
        }

        public static string LocalizationDirectory(string dataDirectory)
        {
            return Path.Combine(dataDirectory, "Loc");
        }
    }
}
