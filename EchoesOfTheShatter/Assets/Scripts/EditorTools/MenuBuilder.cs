using System.IO;
using Echoes.Core;
using Echoes.UI;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UIElements;

namespace Echoes.EditorTools
{
    /// <summary>Monta a cena da tela inicial (Assets/Scenes/MainMenu.unity): camera, GameRoot (localizacao) e o MainMenuController.</summary>
    public static class MenuBuilder
    {
        public const string ScenePath = "Assets/Scenes/MainMenu.unity";

        [MenuItem("Echoes/Montar tela inicial")]
        public static void BuildScene()
        {
            SandboxBuilder.EnsureDir(Path.GetDirectoryName(ScenePath).Replace('\\', '/'));
            var panel = SandboxBuilder.CreatePanelSettings();
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            var cameraGo = new GameObject("Main Camera") { tag = "MainCamera" };
            var camera = cameraGo.AddComponent<Camera>();
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = new Color(0.02f, 0.02f, 0.04f);
            cameraGo.AddComponent<AudioListener>();

            var rootGo = new GameObject("GameRoot");
            var gameRoot = rootGo.AddComponent<GameRoot>();

            var menu = new GameObject("MainMenu");
            var document = menu.AddComponent<UIDocument>();
            document.panelSettings = panel;
            var controller = menu.AddComponent<MainMenuController>();
            SandboxBuilder.SetRef(controller, "root", gameRoot);

            EditorSceneManager.SaveScene(scene, ScenePath);
            Debug.Log("[MenuBuilder] Cena salva em " + ScenePath);
        }
    }
}
