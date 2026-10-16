using System;
using System.IO;
using System.Linq;
using Echoes.Presentation;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Sequência de capturas (anim_*.png) do Guerreiro atacando uma Sentinela, com a câmera do jogo a 56 m e de perto. Sem Play: os clipes do
    /// KayKit são amostrados nos instantes da preparação, do impacto e da recuperação (lidos do SO_SkillPresentation_*, os mesmos que a
    /// apresentação usa). <c>-executeMethod Echoes.EditorTools.AnimationShowcase.Run</c> (sem -nographics). Saída em
    /// <c>D:\openclaude\_trabalho-claude\capturas</c> ou na pasta de <c>ECHOES_CAPTURE_DIR</c>.
    /// </summary>
    public static class AnimationShowcase
    {
        public static void Run()
        {
            try
            {
                CharacterPrefabBuilder.BuildAll();
                SandboxBuilder.Build();
                CriptaBuilder.BuildScene();
                EditorSceneManager.OpenScene(CriptaBuilder.ScenePath, OpenSceneMode.Single);

                var dir = Environment.GetEnvironmentVariable("ECHOES_CAPTURE_DIR");
                if (string.IsNullOrEmpty(dir)) dir = @"D:\openclaude\_trabalho-claude\capturas";
                Directory.CreateDirectory(dir);

                var layout = CriptaLayout.LoadFromDocument();
                var follow = UnityEngine.Object.FindAnyObjectByType<FollowCamera>();
                var cam = follow.GetComponentInChildren<Camera>();
                var hero = GameObject.Find("Hero");
                var heroAnimator = hero.GetComponentInChildren<Animator>(true);

                var origin = new Vector3(layout.HeroSpawn.x, 0f, layout.HeroSpawn.y);
                hero.transform.SetPositionAndRotation(origin, Quaternion.identity);
                var sentinelPrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Art/Prefabs/P_Enemy_HollowSentinel.prefab");
                var sentinel = (GameObject)PrefabUtility.InstantiatePrefab(sentinelPrefab);
                sentinel.transform.SetPositionAndRotation(origin + Vector3.forward * 1.7f, Quaternion.LookRotation(Vector3.back));
                var sentinelAnimator = sentinel.GetComponentInChildren<Animator>(true);

                var warriorSet = AssetDatabase.LoadAssetAtPath<SkillPresentationSet>(AnimatorControllerBuilder.WarriorSkillSetPath);
                warriorSet.TryGet("skill.warrior.iron_cut", out var strike);
                var enemySet = AssetDatabase.LoadAssetAtPath<SkillPresentationSet>($"{AnimatorControllerBuilder.SkillSetDir}/{AnimatorControllerBuilder.EnemyHumanoid.SkillSet}.asset");
                enemySet.TryGet("skill.enemy.sentinel_strike", out var chop);

                var mid = new Vector3(origin.x, 0f, origin.z + 0.85f);
                var views = new[]
                {
                    ("anim_1_repouso_56m", 0.0f, 0.0f, 0f, false),
                    ("anim_2_preparacao_56m", strike.windupEnd * 0.6f, chop.windupEnd * 0.6f, 0f, false),
                    ("anim_3_impacto_56m", (strike.windupEnd + strike.impactEnd) * 0.5f, chop.impactEnd, 0.25f, false),
                    ("anim_4_recuperacao_56m", Mathf.Min(1f, strike.impactEnd + 0.2f), 0.9f, 0.85f, false),
                    ("anim_5_preparacao_perto", strike.windupEnd * 0.8f, chop.windupEnd * 0.6f, 0f, true),
                    ("anim_6_impacto_perto", (strike.windupEnd + strike.impactEnd) * 0.5f, chop.impactEnd, 0.3f, true),
                };

                var idle = KayKitAnimationImport.FindClip($"{KayKitAnimationImport.Root}/Medium/Rig_Medium_General.fbx", "Idle_A");
                var slice = KayKitAnimationImport.FindClip($"{KayKitAnimationImport.Root}/Medium/Rig_Medium_CombatMelee.fbx", "Melee_1H_Attack_Slice_Horizontal");
                var chopClip = KayKitAnimationImport.FindClip($"{KayKitAnimationImport.Root}/Medium/Rig_Medium_CombatMelee.fbx", "Melee_1H_Attack_Chop");
                var hitClip = KayKitAnimationImport.FindClip($"{KayKitAnimationImport.Root}/Medium/Rig_Medium_General.fbx", "Hit_A");

                foreach (var (name, heroT, enemyT, hitT, near) in views)
                {
                    if (name.EndsWith("repouso_56m"))
                    {
                        idle.SampleAnimation(heroAnimator.gameObject, 0.3f);
                        idle.SampleAnimation(sentinelAnimator.gameObject, 0.1f);
                    }
                    else
                    {
                        slice.SampleAnimation(heroAnimator.gameObject, heroT * slice.length);
                        if (hitT > 0f) hitClip.SampleAnimation(sentinelAnimator.gameObject, hitT * hitClip.length);
                        else chopClip.SampleAnimation(sentinelAnimator.gameObject, enemyT * chopClip.length);
                    }
                    if (near)
                    {
                        follow.transform.position = mid + new Vector3(0f, 1.0f, 0f);
                        follow.ApplySettings();
                        cam.transform.localPosition = new Vector3(0f, 0f, -6f);
                        cam.fieldOfView = 35f;
                    }
                    else
                    {
                        follow.transform.position = mid + new Vector3(0f, 0.52f, 0f);
                        follow.ApplySettings();
                    }
                    Capture(cam, Path.Combine(dir, name + ".png"), near ? 1280 : 1920, near ? 720 : 1080);
                }

                Debug.Log("[AnimationShowcase] Capturas em " + dir);
                if (Application.isBatchMode) EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Debug.LogError("[AnimationShowcase] Falhou: " + e);
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
