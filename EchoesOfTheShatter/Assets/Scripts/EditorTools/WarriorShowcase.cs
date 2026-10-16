using System;
using System.IO;
using Echoes.Presentation;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Reimporta os personagens, recria a cena base e tira capturas da câmera do jogo (Camera.Render para PNG, sem Play).
    /// <c>-executeMethod Echoes.EditorTools.WarriorShowcase.Run</c> (sem -nographics: precisa de GPU). Saída em
    /// <c>D:\openclaude\_trabalho-claude\capturas</c> ou na pasta de <c>ECHOES_CAPTURE_DIR</c>.
    /// </summary>
    public static class WarriorShowcase
    {
        const string ScenePath = "Assets/Scenes/Sandbox/Base_Escala.unity";

        public static void Run()
        {
            try
            {
                CharacterAssetPostprocessor.ReimportAll();
                SandboxBuilder.Build();
                var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
                var dir = Environment.GetEnvironmentVariable("ECHOES_CAPTURE_DIR");
                if (string.IsNullOrEmpty(dir)) dir = @"D:\openclaude\_trabalho-claude\capturas";
                Directory.CreateDirectory(dir);

                var follow = UnityEngine.Object.FindAnyObjectByType<FollowCamera>();
                var cam = follow.GetComponentInChildren<Camera>();
                var hero = GameObject.Find("Hero");
                var rig = follow.transform;
                rig.position = hero.transform.position + new Vector3(0f, 0.52f, 0f);
                follow.ApplySettings();

                Capture(cam, Path.Combine(dir, "warrior_56m.png"), 1920, 1080);

                // Conferência de perto (mesma câmera, 10 m): só para inspecionar o acabamento.
                cam.transform.localPosition = new Vector3(0f, 0f, -10f);
                cam.farClipPlane = 150f;
                Capture(cam, Path.Combine(dir, "warrior_close.png"), 1280, 720);

                Debug.Log("[WarriorShowcase] Capturas em " + dir + " (cena " + scene.path + ")");
                if (Application.isBatchMode) EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Debug.LogError("[WarriorShowcase] Falhou: " + e);
                if (Application.isBatchMode) EditorApplication.Exit(1);
            }
        }

        static void Capture(Camera cam, string file, int width, int height)
        {
            var rt = new RenderTexture(width, height, 24, RenderTextureFormat.ARGB32) { antiAliasing = 4 };
            var previous = RenderTexture.active;
            cam.targetTexture = rt;
            cam.Render();
            cam.Render(); // a segunda passada já tem os shaders compilados
            RenderTexture.active = rt;
            var tex = new Texture2D(width, height, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, width, height), 0, 0);
            tex.Apply();
            File.WriteAllBytes(file, tex.EncodeToPNG());
            cam.targetTexture = null;
            RenderTexture.active = previous;
            UnityEngine.Object.DestroyImmediate(tex);
            rt.Release();
            UnityEngine.Object.DestroyImmediate(rt);
        }
    }
}
