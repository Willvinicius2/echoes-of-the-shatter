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
@"ECHOES OF THE SHATTER - build de desenvolvimento (menu, Refugio, Cripta e Guardiao)

Abra EchoesOfTheShatter.exe. O que da para testar hoje:

1. MENU
   Jogar (escolhe o save; sem save, pede o nome do heroi), Resolucao e Janela/Tela cheia (ficam salvas), Previa visual do heroi e Sair.
   Previa visual do heroi: o botao alterna Guerreiro, Arqueiro e Mago (ou abra com -hero warrior|archer|mage). E so uma PREVIA VISUAL:
   apenas o Guerreiro tem kit de habilidades; o Arqueiro (arco na mao esquerda, em pe) e o Mago (cajado na mao direita) usam o mesmo
   kit de teste do Guerreiro ate o design deles existir. Os tres vestem o conjunto de armadura inicial.

2. REFUGIO (Jogar leva para ca)
   Ilsa (esquerda, em cima): configura a rota da Cripta (objetivo, ate 6 regras de IA, duracao 1 a 12 h, limitada pelas Cargas do Marco) e inicia.
   Tico (esquerda, embaixo): mostra quanto falta e, quando acabar, entrega o relatorio (coleta uma vez so; selo Estimativa enquanto as
   habilidades nao forem calibradas). Fale com eles com F, chegando perto.
   Com a expedicao em andamento o heroi esta em rota: o portal da Cripta (a direita) fica fechado e a Ilsa avisa.
   A Ilsa so abre a rota depois da Cripta dominada (vencer o Guardiao). Para testar sem lutar:
   F8 domina a Cripta (+5 cargas); F9 avanca o relogio 1 h; F10 avanca 12 h (acelerador de debug, so no Refugio).
   Fluxo curto: F8, falar com a Ilsa, iniciar, F10, falar com o Tico e ver o relatorio.

3. CRIPTA (portal do Refugio) E GUARDIAO
   Cripta pintada com 9 salas, corredores, baus, checkpoints (braseiros), atalho e segredo (parede rachada: abre com Investida, Fenda de Pedra
   ou Escudada). Luzes e chamas de fogo acendem so perto do heroi. A arena do Guardiao fica no fim (porta fecha atras de voce, barra do chefe no topo).

CONTROLES
  WASD mover | mouse mira | botao esquerdo ataque basico | botao direito, Q, E habilidades | Espaco esquiva | 1 e 2 pocoes | F falar/interagir
  Esc ......... pausa (Continuar, opcoes, Voltar ao inicio; o jogo e salvo ao voltar)

PECAS DA ARMADURA (teclas de desenvolvimento, DESLIGADAS na build de release)
  Ligue abrindo com o argumento -devkeys (ex.: EchoesOfTheShatter.exe -devkeys, ou crie um atalho com isso no destino).
  F1 a F5 tiram e poem Head, Chest, Hands, Legs e Feet; F6 veste tudo; F7 tira tudo (corpo nu).

SAVE
  O jogo salva ao trocar de area, a cada 5 min, ao coletar e ao sair. O core mantem 3 backups (slot_1.bak1 a .bak3).
  Pasta dos saves: %USERPROFILE%\AppData\LocalLow\DefaultCompany\Echoes of the Shatter\saves
  Numero de slots: 1 (variavel de ambiente ECHOES_SAVE_SLOTS=3 para 3 slots).

DIAGNOSTICO
  Log: %USERPROFILE%\AppData\LocalLow\DefaultCompany\Echoes of the Shatter\Player.log
  -autostart | -smoke 1 | -savedir pasta | -logFile arquivo: entra sozinho, domina, expede, coleta e registra no log.
  -shots pasta: captura em runtime o Refugio, a entrada da Cripta, uma sala com encontro, a arena e o heroi de perto, e fecha.
  -bossshot arquivo.png: leva o heroi a arena e salva a captura com a barra do chefe.
  -perf arquivo.txt: mede o tempo de quadro (media e p95 de 10 s) com o heroi na arena.
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
            var expected = Directory.GetFiles(source, "*.csv", SearchOption.AllDirectories).Length;
            if (count != expected || !File.Exists(Path.Combine(target, "rules.csv")) || !File.Exists(Path.Combine(target, "Loc", "ui.csv")))
                throw new BuildFailedException("StreamingAssets/Data incompleto: o core recusa conteudo sem as tabelas e chaves obrigatorias.");
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
