using System;
using System.IO;
using System.Linq;
using Echoes.Gameplay;
using Echoes.Presentation;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Capturas da Cripta com a camera do jogo a 56 m (Camera.Render para PNG, sem Play): da entrada e da arena.
    /// <c>-executeMethod Echoes.EditorTools.CriptaShowcase.Run</c> (sem -nographics: precisa de GPU). Saida em
    /// <c>D:\openclaude\_trabalho-claude\capturas</c> ou na pasta de <c>ECHOES_CAPTURE_DIR</c>.
    /// </summary>
    public static class CriptaShowcase
    {
        public static void Run()
        {
            try
            {
                var layout = CriptaLayout.LoadFromDocument();
                EditorSceneManager.OpenScene(CriptaBuilder.ScenePath, OpenSceneMode.Single);
                var dir = Environment.GetEnvironmentVariable("ECHOES_CAPTURE_DIR");
                if (string.IsNullOrEmpty(dir)) dir = @"D:\openclaude\_trabalho-claude\capturas";
                Directory.CreateDirectory(dir);

                var follow = UnityEngine.Object.FindAnyObjectByType<FollowCamera>();
                var cam = follow.GetComponentInChildren<Camera>();
                var hero = GameObject.Find("Hero");

                Shot(follow, cam, hero, new Vector3(layout.HeroSpawn.x, 0f, layout.HeroSpawn.y), Path.Combine(dir, "cripta_entrada.png"));
                var arena = layout.Room("room.crypt.r09_arena").Rect;
                Shot(follow, cam, hero, new Vector3(arena.center.x, 0f, arena.center.y + 3f), Path.Combine(dir, "cripta_arena.png"));
                var antechamber = layout.Room("room.crypt.r01_patrol_a").Rect;
                Shot(follow, cam, hero, new Vector3(antechamber.center.x - 6f, 0f, antechamber.center.y), Path.Combine(dir, "cripta_encontro1.png"));

                Debug.Log("[CriptaShowcase] Capturas em " + dir);
                if (Application.isBatchMode) EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Debug.LogError("[CriptaShowcase] Falhou: " + e);
                if (Application.isBatchMode) EditorApplication.Exit(1);
            }
        }

        static void Shot(FollowCamera follow, Camera cam, GameObject hero, Vector3 heroPosition, string file)
        {
            hero.transform.position = heroPosition;
            follow.transform.position = heroPosition + new Vector3(0f, 0.52f, 0f);
            follow.ApplySettings();
            const int width = 1920;
            const int height = 1080;
            var rt = new RenderTexture(width, height, 24, RenderTextureFormat.ARGB32) { antiAliasing = 4 };
            var previous = RenderTexture.active;
            cam.targetTexture = rt;
            cam.Render();
            cam.Render();
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
