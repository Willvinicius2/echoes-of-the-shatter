using UnityEditor;
using UnityEngine;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Fixa o Plugin Inspector da <c>shattercore.dll</c> como em docs/tecnico/04_arquitetura.md, secao 9.3: so Windows x64
    /// ("Any Platform" desligado), Editor Windows x64, carregada na inicializacao. Idempotente: so reimporta se algo mudar.
    /// Menu Echoes/Configurar plugin nativo, ou <c>-executeMethod Echoes.EditorTools.NativePluginSetup.Apply</c>.
    /// </summary>
    public static class NativePluginSetup
    {
        public const string AssetPath = "Assets/Plugins/x86_64/shattercore.dll";

        [MenuItem("Echoes/Configurar plugin nativo")]
        public static void Apply()
        {
            var importer = AssetImporter.GetAtPath(AssetPath) as PluginImporter;
            if (importer == null)
            {
                Debug.LogError("[NativePluginSetup] Plugin nao encontrado em " + AssetPath + " (rode tools\core\build_core.cmd Release e copie a DLL).");
                return;
            }
            if (IsConfigured(importer))
            {
                Debug.Log("[NativePluginSetup] Plugin ja configurado.");
                return;
            }
            importer.SetCompatibleWithAnyPlatform(false);
            importer.SetCompatibleWithEditor(false);
            foreach (BuildTarget target in System.Enum.GetValues(typeof(BuildTarget)))
            {
                if (target <= 0) continue;
                try { importer.SetCompatibleWithPlatform(target, false); } catch { /* alvo obsoleto */ }
            }
            importer.SetCompatibleWithEditor(true);
            importer.SetEditorData("CPU", "x86_64");
            importer.SetEditorData("OS", "Windows");
            importer.SetCompatibleWithPlatform(BuildTarget.StandaloneWindows64, true);
            importer.SetPlatformData(BuildTarget.StandaloneWindows64, "CPU", "x86_64");
            importer.isPreloaded = true;
            importer.SaveAndReimport();
            Debug.Log("[NativePluginSetup] Plugin configurado: Windows x64 + Editor, carregado na inicializacao.");
        }

        public static bool IsConfigured(PluginImporter importer)
        {
            return importer != null
                && !importer.GetCompatibleWithAnyPlatform()
                && importer.GetCompatibleWithEditor()
                && importer.GetCompatibleWithPlatform(BuildTarget.StandaloneWindows64)
                && !importer.GetCompatibleWithPlatform(BuildTarget.StandaloneLinux64)
                && !importer.GetCompatibleWithPlatform(BuildTarget.StandaloneOSX)
                && !importer.GetCompatibleWithPlatform(BuildTarget.Android)
                && importer.isPreloaded;
        }
    }
}
