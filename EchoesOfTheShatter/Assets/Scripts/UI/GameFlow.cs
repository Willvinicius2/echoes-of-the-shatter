using System;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Echoes.UI
{
    /// <summary>Fluxo de telas: tela inicial, Cripta, pausa e saída. Nada de regra de jogo aqui.</summary>
    public static class GameFlow
    {
        public const string MainMenuScene = "MainMenu";
        public const string CriptaScene = "Cripta";
        public const string AutoStartArg = "-autostart";

        /// <summary>Argumento de teste (-autostart): a tela inicial entra sozinha na Cripta, para o teste de fumaça do player.</summary>
        public static bool AutoStartRequested
        {
            get
            {
                foreach (var arg in Environment.GetCommandLineArgs())
                {
                    if (string.Equals(arg, AutoStartArg, StringComparison.OrdinalIgnoreCase)) return true;
                }
                return false;
            }
        }

        /// <summary>Valor do argumento de linha de comando que segue <paramref name="name"/> (ou null).</summary>
        public static string ArgValue(string name)
        {
            var args = Environment.GetCommandLineArgs();
            for (var i = 0; i < args.Length - 1; i++)
            {
                if (string.Equals(args[i], name, StringComparison.OrdinalIgnoreCase)) return args[i + 1];
            }
            return null;
        }

        public static void StartGame()
        {
            Time.timeScale = 1f;
            SceneManager.LoadScene(CriptaScene, LoadSceneMode.Single);
        }

        public static void ToMainMenu()
        {
            Time.timeScale = 1f;
            AudioListener.pause = false;
            SceneManager.LoadScene(MainMenuScene, LoadSceneMode.Single);
        }

        public static void Quit()
        {
#if UNITY_EDITOR
            UnityEditor.EditorApplication.isPlaying = false;
#else
            Application.Quit();
#endif
        }
    }
}
