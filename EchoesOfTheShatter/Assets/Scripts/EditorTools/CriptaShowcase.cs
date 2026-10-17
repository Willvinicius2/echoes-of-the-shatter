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
                // Atualiza os modelos pintados e remonta as duas cenas (Base_Escala e Cripta) com os prefabs novos.
                EnvironmentKit.Import();
                CharacterAssetPostprocessor.ReimportAll();
                CharacterPrefabBuilder.BuildAll();
                SandboxBuilder.Build();
                CriptaBuilder.BuildScene();

                var layout = CriptaLayout.LoadFromDocument();
                EditorSceneManager.OpenScene(CriptaBuilder.ScenePath, OpenSceneMode.Single);
                var dir = Environment.GetEnvironmentVariable("ECHOES_CAPTURE_DIR");
                if (string.IsNullOrEmpty(dir)) dir = @"D:\openclaude\_trabalho-claude\capturas";
                Directory.CreateDirectory(dir);

                var follow = UnityEngine.Object.FindAnyObjectByType<FollowCamera>();
                var cam = follow.GetComponentInChildren<Camera>();
                var hero = GameObject.Find("Hero");

                Shot(follow, cam, hero, new Vector3(layout.HeroSpawn.x, 0f, layout.HeroSpawn.y), Path.Combine(dir, "cripta3_entrada.png"));
                // Encontro 4 (Sentinelas e Arqueiros Espectrais): o heroi chega de leste.
                var e4 = layout.Encounters.First(e => e.Id == "enc.crypt.patrol_b");
                var slot = e4.Groups[0].Slots[0];
                Shot(follow, cam, hero, new Vector3(slot.x + 8f, 0f, slot.y), Path.Combine(dir, "cripta3_encontro_sentinelas_arqueiros.png"));
                var arena = layout.Room("room.crypt.r09_arena").Rect;
                Shot(follow, cam, hero, new Vector3(arena.center.x, 0f, arena.center.y + 2f), Path.Combine(dir, "cripta3_arena_guardiao.png"));

                // De perto (10 m): o Guardiao com martelo e escudo, camera aberta so para caber os 4,5 m do chefe.
                var boss = layout.Encounters.First(e => e.IsBoss).Groups[0].Slots[0];
                hero.transform.position = new Vector3(boss.x, 0f, boss.y - 6f);
                follow.transform.position = new Vector3(boss.x, 2.2f, boss.y);
                follow.ApplySettings();
                cam.transform.localPosition = new Vector3(0f, 0f, -10f);
                cam.fieldOfView = 35f;
                Capture(cam, Path.Combine(dir, "cripta3_guardiao_10m.png"), 1280, 720);

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
            Capture(cam, file, 1920, 1080);
        }

        static void Capture(Camera cam, string file, int width, int height)
        {
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
