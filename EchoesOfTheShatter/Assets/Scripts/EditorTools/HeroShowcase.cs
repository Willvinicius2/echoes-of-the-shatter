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
    /// Capturas dos herois na Cripta (camera do jogo, sem Play): heroi ao lado de parede e piso, de perto (9 m) e a 56 m.
    /// <c>-executeMethod Echoes.EditorTools.HeroShowcase.Run</c> (sem -nographics). Variaveis: ECHOES_SHOT_TAG (prefixo, ex. antes/depois),
    /// ECHOES_CAPTURE_DIR (padrao D:\openclaude\_trabalho-claude\capturas), ECHOES_NO_AURA (sem aura, para o "antes").
    /// </summary>
    public static class HeroShowcase
    {
        public static void Run()
        {
            try
            {
                CharacterAssetPostprocessor.ReimportAll();
                CharacterPrefabBuilder.BuildAll();
                CriptaBuilder.BuildScene();
                var layout = CriptaLayout.LoadFromDocument();
                EditorSceneManager.OpenScene(CriptaBuilder.ScenePath, OpenSceneMode.Single);
                var dir = Environment.GetEnvironmentVariable("ECHOES_CAPTURE_DIR");
                if (string.IsNullOrEmpty(dir)) dir = @"D:\openclaude\_trabalho-claude\capturas";
                var tag = Environment.GetEnvironmentVariable("ECHOES_SHOT_TAG");
                if (string.IsNullOrEmpty(tag)) tag = "heroi";
                Directory.CreateDirectory(dir);
                var follow = UnityEngine.Object.FindAnyObjectByType<FollowCamera>();
                var cam = follow.GetComponentInChildren<Camera>();
                var hero = GameObject.Find("Hero");
                var which = Environment.GetEnvironmentVariable("ECHOES_HERO");
                if (!string.IsNullOrEmpty(which) && which != "Warrior")
                {
                    var prefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Art/Prefabs/P_Hero_" + which + ".prefab");
                    var inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                    inst.name = "Hero_" + which;
                    hero.SetActive(false);
                    hero = inst;
                }
                var mc = hero.GetComponentInChildren<ModularCharacter>();
                Debug.Log("[HeroShowcase] Hero=" + hero.name + " comps=" + string.Join(",", hero.GetComponents<Component>().Select(c => c.GetType().Name)) + " mc=" + (mc != null) + " catalog=" + (mc != null && mc.Catalog != null));
                if (mc != null)
                {
                    mc.Build();
                    var set = Environment.GetEnvironmentVariable("ECHOES_SET");
                    if (string.IsNullOrEmpty(set)) set = HeroPartCatalog.StarterSet;
                    foreach (HeroPartSlot slot in Enum.GetValues(typeof(HeroPartSlot))) Debug.Log("[HeroShowcase] equip " + slot + " -> " + (mc.Equip(slot, set) != null));
                }
                var aura = hero.GetComponentInChildren<HeroAura>(); Debug.Log("[HeroShowcase] aura=" + (aura != null));
                if (aura != null) { aura.BuildNow(); aura.SimulatePreview(2f); }

                var spawn = new Vector3(layout.HeroSpawn.x, 0f, layout.HeroSpawn.y);
                hero.transform.position = spawn;
                follow.transform.position = spawn + new Vector3(0f, 0.9f, 0f);
                follow.ApplySettings();
                var origPos = cam.transform.localPosition; var origFov = cam.fieldOfView;
                Capture(cam, Path.Combine(dir, tag + "_56m.png"), 1920, 1080);
                cam.transform.localPosition = new Vector3(0f, 0f, -9f);
                cam.fieldOfView = 35f;
                Capture(cam, Path.Combine(dir, tag + "_9m.png"), 1920, 1080);
                cam.transform.localPosition = new Vector3(0f, 0f, -5f);
                Capture(cam, Path.Combine(dir, tag + "_5m.png"), 1920, 1080);
                hero.transform.Rotate(0f, 180f, 0f);
                Capture(cam, Path.Combine(dir, tag + "_5m_frente.png"), 1920, 1080);
                cam.transform.localPosition = new Vector3(0f, 0f, -9f);
                Capture(cam, Path.Combine(dir, tag + "_9m_frente.png"), 1920, 1080);
                cam.transform.localPosition = origPos; cam.fieldOfView = origFov;
                Debug.Log("[HeroShowcase] Capturas em " + dir + " (" + tag + ")");
                if (Application.isBatchMode) EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Debug.LogError("[HeroShowcase] Falhou: " + e);
                if (Application.isBatchMode) EditorApplication.Exit(1);
            }
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
