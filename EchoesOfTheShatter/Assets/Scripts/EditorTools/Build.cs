using System;
using System.IO;
using Echoes.Gameplay;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;
using UnityEngine.InputSystem;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Build do jogador Windows (docs/04, secao 14): <c>-executeMethod Echoes.EditorTools.Build.Windows</c> (ou o menu). Mono x64, sem Development
    /// Build, Release; saida fora do repositorio. Monta as duas cenas (tela inicial e Cripta), poe o Echoes.inputactions nos Preloaded Assets,
    /// copia os CSV para StreamingAssets/Data (BuildContentPreprocess) e escreve o LEIA-ME.txt. A DLL shattercore vem de Assets/Plugins/x86_64.
    /// </summary>
    public static class Build
    {
        public const string OutputDir = @"D:\openclaude\Builds\Echoes_Cripta_dev";
        public const string ExeName = "EchoesOfTheShatter.exe";
        public const string ActionsPath = "Assets/Settings/Echoes.inputactions";

        public static readonly string[] Scenes = { MenuBuilder.ScenePath, RefugioBuilder.ScenePath, CriptaBuilder.ScenePath };

        [MenuItem("Echoes/Build Windows (jogavel)")]
        public static void Windows()
        {
            try
            {
                var output = Environment.GetEnvironmentVariable("ECHOES_BUILD_DIR");
                if (string.IsNullOrEmpty(output)) output = OutputDir;
                var exe = Path.Combine(output, ExeName);

                MenuBuilder.BuildScene();
                RefugioBuilder.BuildScene();
                CriptaBuilder.BuildScene();
                ConfigurePlayerSettings();
                EnsureBuildScenes();

                Directory.CreateDirectory(output);
                var options = new BuildPlayerOptions
                {
                    scenes = Scenes,
                    locationPathName = exe,
                    target = BuildTarget.StandaloneWindows64,
                    targetGroup = BuildTargetGroup.Standalone,
                    subtarget = (int)StandaloneBuildSubtarget.Player,
                    options = BuildOptions.None, // sem Development Build
                };
                var report = BuildPipeline.BuildPlayer(options);
                if (report.summary.result != BuildResult.Succeeded) throw new Exception("Build falhou: " + report.summary.result + ", erros: " + report.summary.totalErrors);
                WriteReadme(output);
                Debug.Log($"[Build] OK: {exe} ({report.summary.totalSize / (1024 * 1024)} MB, {report.summary.totalTime.TotalSeconds:F0} s)");
                if (Application.isBatchMode) EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Debug.LogError("[Build] Falhou: " + e);
                if (Application.isBatchMode) EditorApplication.Exit(1);
            }
        }

        static void ConfigurePlayerSettings()
        {
            EditorUserBuildSettings.development = false;
            EditorUserBuildSettings.allowDebugging = false;
            EditorUserBuildSettings.connectProfiler = false;
            PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, ScriptingImplementation.Mono2x);
            PlayerSettings.fullScreenMode = FullScreenMode.Windowed;
            PlayerSettings.defaultScreenWidth = 1280;
            PlayerSettings.defaultScreenHeight = 720;
            PlayerSettings.resizableWindow = true;
            PlayerSettings.runInBackground = true;
            PlayerSettings.productName = "Echoes of the Shatter";
            PlayerSettings.SetManagedStrippingLevel(NamedBuildTarget.Standalone, ManagedStrippingLevel.Disabled);

            // Echoes.inputactions nos Preloaded Assets: o player o encontra por nome (PlayerInputHandler).
            var actions = AssetDatabase.LoadAssetAtPath<InputActionAsset>(ActionsPath);
            if (actions == null) throw new InvalidOperationException(ActionsPath + " nao encontrado.");
            var preloaded = new System.Collections.Generic.List<UnityEngine.Object>(PlayerSettings.GetPreloadedAssets());
            preloaded.RemoveAll(o => o == null);
            if (!preloaded.Contains(actions)) preloaded.Add(actions);
            PlayerSettings.SetPreloadedAssets(preloaded.ToArray());
        }

        /// <summary>Acrescenta a cena aos Build Settings se faltar (os testes de Play e o jogo carregam por nome).</summary>
        public static void AddSceneToBuildSettings(string path)
        {
            var list = new System.Collections.Generic.List<EditorBuildSettingsScene>(EditorBuildSettings.scenes);
            if (list.Exists(s => s.path == path)) return;
            list.Add(new EditorBuildSettingsScene(path, true));
            EditorBuildSettings.scenes = list.ToArray();
        }

        static void EnsureBuildScenes()
        {
            var list = new EditorBuildSettingsScene[Scenes.Length];
            for (var i = 0; i < Scenes.Length; i++) list[i] = new EditorBuildSettingsScene(Scenes[i], true);
            EditorBuildSettings.scenes = list;
        }

        static void WriteReadme(string output)
        {
            const string text =
@"ECHOES OF THE SHATTER - build de desenvolvimento (Refugio e Cripta)

Abra EchoesOfTheShatter.exe. Tela inicial: Jogar (escolhe o save; sem save, pede o nome do heroi), Resolucao e Janela/Tela cheia
(ficam salvas) e Sair. Jogar leva ao Refugio; o portal vermelho a direita leva a Cripta e o da Cripta traz de volta.

CONTROLES
  WASD ........................ mover
  Mouse ....................... mirar (o heroi olha para o ponteiro)
  Botao esquerdo .............. ataque basico
  Botao direito / Q / E ....... habilidades
  Espaco ...................... esquiva
  1 e 2 ....................... pocoes
  F ........................... falar com a Ilsa e o Tico (no Refugio, perto deles)
  Esc ......................... pausa (Continuar, opcoes, Voltar ao inicio; o jogo e salvo ao voltar)
  Dev: F1 a F5 tiram e poem as pecas da armadura (so em Development Build)

EXPEDICAO (Refugio)
  Ilsa: configura a rota da Cripta (objetivo, ate 6 regras de IA, duracao 1 a 12 h; a duracao e limitada pelas Cargas do Marco) e inicia.
  Enquanto a expedicao roda o heroi esta em rota: o portal da Cripta fica fechado (a Ilsa avisa).
  Tico: mostra quanto falta e, quando acabar, entrega o relatorio (coleta uma vez so). O selo Estimativa aparece enquanto as habilidades nao forem calibradas.
  A Ilsa so abre a rota depois de a Cripta estar dominada (vencer o Guardiao). Para testar sem lutar:
  F8 domina a Cripta (+5 cargas); F9 avanca o relogio 1 h; F10 avanca 12 h (acelerador de debug, so no Refugio).

SAVE
  O jogo salva ao trocar de area, a cada 5 min, ao coletar e ao sair. O core mantem 3 backups (slot_1.bak1 a .bak3).
  Pasta dos saves: %USERPROFILE%\AppData\LocalLow\DefaultCompany\Echoes of the Shatter\saves
  Numero de slots: 1 (variavel de ambiente ECHOES_SAVE_SLOTS=3 para 3 slots).

Log do jogo: %USERPROFILE%\AppData\LocalLow\DefaultCompany\Echoes of the Shatter\Player.log
Teste de fumaca: EchoesOfTheShatter.exe -autostart -smoke 1 -savedir pasta -logFile player.log (entra, domina, expede, coleta e registra no log).
";
            File.WriteAllText(Path.Combine(output, "LEIA-ME.txt"), text.Replace("\r\n", "\n").Replace("\n", "\r\n"), new System.Text.UTF8Encoding(false));
        }
    }

    /// <summary>
    /// Copia os CSV de Content/Data (e Loc) para Assets/StreamingAssets/Data antes do build (docs/04, secao 4.2) e remove a copia depois:
    /// a fonte da verdade continua em Content/Data e StreamingAssets fica fora do repositorio.
    /// </summary>
    public sealed class BuildContentPreprocess : IPreprocessBuildWithReport, IPostprocessBuildWithReport
    {
        public int callbackOrder => 0;
        const string Target = "Assets/StreamingAssets/Data";

        public void OnPreprocessBuild(BuildReport report)
        {
            var projectRoot = Path.GetDirectoryName(Application.dataPath);
            var source = Path.Combine(projectRoot, "Content", "Data");
            if (!File.Exists(Path.Combine(source, "rules.csv"))) throw new BuildFailedException("Content/Data/rules.csv nao encontrado.");
            var target = Path.Combine(projectRoot, Target);
            if (Directory.Exists(target)) Directory.Delete(target, true);
            Directory.CreateDirectory(target);
            var count = 0;
            foreach (var file in Directory.GetFiles(source, "*.csv", SearchOption.AllDirectories))
            {
                var relative = Path.GetRelativePath(source, file);
                var destination = Path.Combine(target, relative);
                Directory.CreateDirectory(Path.GetDirectoryName(destination));
                File.Copy(file, destination, true);
                count++;
            }
            AssetDatabase.Refresh();
            Debug.Log($"[Build] {count} CSV copiados para {Target}");
        }

        public void OnPostprocessBuild(BuildReport report)
        {
            var projectRoot = Path.GetDirectoryName(Application.dataPath);
            var streaming = Path.Combine(projectRoot, "Assets", "StreamingAssets");
            if (Directory.Exists(streaming)) Directory.Delete(streaming, true);
            var meta = streaming + ".meta";
            if (File.Exists(meta)) File.Delete(meta);
            AssetDatabase.Refresh();
        }
    }
}
