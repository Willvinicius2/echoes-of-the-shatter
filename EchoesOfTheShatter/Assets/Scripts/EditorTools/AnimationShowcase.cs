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
                    ("anim_2_preparacao_56m", strike.windupEnd * 0.9f, chop.windupEnd * 0.9f, 0f, false),
                    ("anim_3_impacto_56m", strike.impactEnd, chop.impactEnd, 0.25f, false),
                    ("anim_4_recuperacao_56m", Mathf.Min(1f, strike.impactEnd + 0.2f), 0.9f, 0.85f, false),
                    ("anim_5_preparacao_perto", strike.windupEnd * 0.9f, chop.windupEnd * 0.9f, 0f, true),
                    ("anim_6_impacto_perto", strike.impactEnd, chop.impactEnd, 0.3f, true),
                };

                var idle = KayKitAnimationImport.FindClip($"{KayKitAnimationImport.Root}/Medium/Rig_Medium_General.fbx", "Idle_A");
                var slice = KayKitAnimationImport.FindClip($"{KayKitAnimationImport.Root}/Medium/Rig_Medium_CombatMelee.fbx", "Melee_1H_Attack_Slice_Horizontal");
                var chopClip = KayKitAnimationImport.FindClip($"{KayKitAnimationImport.Root}/Medium/Rig_Medium_CombatMelee.fbx", "Melee_1H_Attack_Chop");
                var hitClip = KayKitAnimationImport.FindClip($"{KayKitAnimationImport.Root}/Medium/Rig_Medium_General.fbx", "Hit_A");

                // Um passo por tick do editor: o skinning so atualiza entre quadros (amostra num tick, captura no seguinte).
                var steps = new System.Collections.Generic.Queue<Action>();
                foreach (var view in views)
                {
                    var (name, heroT, enemyT, hitT, near) = view;
                    steps.Enqueue(() =>
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
                    });
                    steps.Enqueue(() => Capture(cam, Path.Combine(dir, name + ".png"), near ? 1280 : 1920, near ? 720 : 1080));
                }

                EditorApplication.CallbackFunction tick = null;
                tick = () =>
                {
                    try
                    {
                        if (steps.Count > 0)
                        {
                            steps.Dequeue()();
                            return;
                        }
                        EditorApplication.update -= tick;
                        Debug.Log("[AnimationShowcase] Capturas em " + dir);
                        if (Application.isBatchMode) EditorApplication.Exit(0);
                    }
                    catch (Exception e)
                    {
                        EditorApplication.update -= tick;
                        Debug.LogError("[AnimationShowcase] Falhou: " + e);
                        if (Application.isBatchMode) EditorApplication.Exit(1);
                    }
                };
                EditorApplication.update += tick;
                return;
            }
            catch (Exception e)
            {
                Debug.LogError("[AnimationShowcase] Falhou: " + e);
                if (Application.isBatchMode) EditorApplication.Exit(1);
            }
        }


        // ---------------------------------------------------------------------------------------------
        // anim2_*: de perto, 3/4 frontal a ~4 m (FOV 35), cada personagem sozinho nos estados Idle, Walk, preparação, impacto e Hit.
        // ---------------------------------------------------------------------------------------------

        public static void RunClose()
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
                follow.enabled = false;
                var hero = GameObject.Find("Hero");
                if (hero != null) hero.SetActive(false);
                var origin = new Vector3(layout.HeroSpawn.x, 0f, layout.HeroSpawn.y);
                // Os inimigos da cena (parados em pe, na pose de repouso) nao podem ficar no quadro.
                foreach (var enemy in UnityEngine.Object.FindObjectsByType<Echoes.Gameplay.EnemyController>(FindObjectsSortMode.None)) enemy.gameObject.SetActive(false);

                string medium = KayKitAnimationImport.Root + "/Medium/", large = KayKitAnimationImport.Root + "/Large/";
                AnimationClip M(string fbx, string clip) => KayKitAnimationImport.FindClip($"{medium}Rig_Medium_{fbx}.fbx", clip);
                AnimationClip L(string fbx, string clip) => KayKitAnimationImport.FindClip($"{large}Rig_Large_{fbx}.fbx", clip);
                var warriorSet = AssetDatabase.LoadAssetAtPath<SkillPresentationSet>(AnimatorControllerBuilder.WarriorSkillSetPath);
                var enemySet = AssetDatabase.LoadAssetAtPath<SkillPresentationSet>($"{AnimatorControllerBuilder.SkillSetDir}/{AnimatorControllerBuilder.EnemyHumanoid.SkillSet}.asset");
                var bossSet = AssetDatabase.LoadAssetAtPath<SkillPresentationSet>($"{AnimatorControllerBuilder.SkillSetDir}/{AnimatorControllerBuilder.Boss.SkillSet}.asset");
                warriorSet.TryGet("skill.warrior.iron_cut", out var basic);
                enemySet.TryGet("skill.enemy.sentinel_strike", out var strike);
                bossSet.TryGet("skill.enemy.guardian_hammer", out var hammer);

                // Um passo por tick do editor: o skinning so atualiza entre quadros, entao amostra num tick e captura no seguinte.
                var steps = new System.Collections.Generic.Queue<Action>();
                void Cast(string prefabName, float distance, float lookHeight, (string, AnimationClip, float)[] poses, float yaw = 35f)
                {
                    GameObject go = null;
                    Animator animator = null;
                    steps.Enqueue(() =>
                    {
                        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>($"Assets/Art/Prefabs/{prefabName}.prefab");
                        go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                        go.transform.SetPositionAndRotation(origin, Quaternion.identity);
                        animator = go.GetComponentInChildren<Animator>(true);
                    });
                    foreach (var pose in poses)
                    {
                        var (label, clip, t) = pose;
                        steps.Enqueue(() =>
                        {
                            clip.SampleAnimation(animator.gameObject, Mathf.Clamp(t, 0f, clip.length));
                            var target = origin + Vector3.up * lookHeight;
                            var direction = Quaternion.Euler(0f, yaw, 0f) * Vector3.forward;
                            cam.transform.position = target + direction * distance + Vector3.up * (distance * 0.22f);
                            cam.transform.LookAt(target);
                            cam.fieldOfView = 35f;
                        });
                        steps.Enqueue(() => Capture(cam, Path.Combine(dir, $"anim2_{label}.png"), 1280, 720));
                    }
                    steps.Enqueue(() => UnityEngine.Object.DestroyImmediate(go));
                }

                Cast("P_Hero_Warrior", 4f, 0.8f, new[]
                {
                    ("guerreiro_1_idle", M("General", "Idle_A"), 0.3f),
                    ("guerreiro_2_walk", M("MovementBasic", "Walking_A"), 0.25f),
                    ("guerreiro_3_preparacao", M("CombatMelee", "Melee_1H_Attack_Slice_Horizontal"), basic.windupEnd * 0.9f * M("CombatMelee", "Melee_1H_Attack_Slice_Horizontal").length),
                    ("guerreiro_4_impacto", M("CombatMelee", "Melee_1H_Attack_Slice_Horizontal"), basic.impactEnd * M("CombatMelee", "Melee_1H_Attack_Slice_Horizontal").length),
                    ("guerreiro_5_hit", M("General", "Hit_A"), 0.25f * M("General", "Hit_A").length),
                });
                Cast("P_Enemy_HollowSentinel", 4f, 0.8f, new[]
                {
                    ("sentinela_1_idle", M("General", "Idle_A"), 0.3f),
                    ("sentinela_2_walk", M("MovementBasic", "Walking_A"), 0.25f),
                    ("sentinela_3_preparacao", M("CombatMelee", "Melee_1H_Attack_Chop"), strike.windupEnd * 0.9f * M("CombatMelee", "Melee_1H_Attack_Chop").length),
                    ("sentinela_4_impacto", M("CombatMelee", "Melee_1H_Attack_Chop"), strike.impactEnd * M("CombatMelee", "Melee_1H_Attack_Chop").length),
                    ("sentinela_5_hit", M("General", "Hit_A"), 0.25f * M("General", "Hit_A").length),
                });
                Cast("P_Boss_CryptGuardian", 12f, 2.0f, new[]
                {
                    ("guardiao_1_idle", L("General", "Idle_A"), 0.3f),
                    ("guardiao_2_martelo", M("CombatMelee", "Melee_2H_Attack_Chop"), hammer.impactEnd * M("CombatMelee", "Melee_2H_Attack_Chop").length),
                }, 60f);

                EditorApplication.CallbackFunction tick = null;
                tick = () =>
                {
                    try
                    {
                        if (steps.Count > 0)
                        {
                            steps.Dequeue()();
                            return;
                        }
                        EditorApplication.update -= tick;
                        Debug.Log("[AnimationShowcase] Capturas anim2 em " + dir);
                        if (Application.isBatchMode) EditorApplication.Exit(0);
                    }
                    catch (Exception e)
                    {
                        EditorApplication.update -= tick;
                        Debug.LogError("[AnimationShowcase] Falhou: " + e);
                        if (Application.isBatchMode) EditorApplication.Exit(1);
                    }
                };
                EditorApplication.update += tick;
            }
            catch (Exception e)
            {
                Debug.LogError("[AnimationShowcase] Falhou: " + e);
                if (Application.isBatchMode) EditorApplication.Exit(1);
            }
        }



        /// <summary>anim3_*: golpes do Blender de perto (Espectro atirando, Guardiao rugindo, Guerreiro atordoado), 3/4 frontal, FOV 35.</summary>
        public static void RunClose3()
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
                follow.enabled = false;
                var hero = GameObject.Find("Hero");
                if (hero != null) hero.SetActive(false);
                foreach (var enemy in UnityEngine.Object.FindObjectsByType<Echoes.Gameplay.EnemyController>(FindObjectsSortMode.None)) enemy.gameObject.SetActive(false);
                var origin = new Vector3(layout.HeroSpawn.x, 0f, layout.HeroSpawn.y);

                var steps = new System.Collections.Generic.Queue<Action>();
                void Cast(string prefabName, float distance, float lookHeight, float yaw, (string, AnimationClip, float)[] poses)
                {
                    GameObject go = null;
                    Animator animator = null;
                    steps.Enqueue(() =>
                    {
                        go = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>($"Assets/Art/Prefabs/{prefabName}.prefab"));
                        go.transform.SetPositionAndRotation(origin, Quaternion.identity);
                        animator = go.GetComponentInChildren<Animator>(true);
                    });
                    foreach (var pose in poses)
                    {
                        var (label, clip, t) = pose;
                        steps.Enqueue(() =>
                        {
                            clip.SampleAnimation(animator.gameObject, Mathf.Clamp(t, 0f, clip.length));
                            var target = origin + Vector3.up * lookHeight;
                            var direction = Quaternion.Euler(0f, yaw, 0f) * Vector3.forward;
                            cam.transform.position = target + direction * distance + Vector3.up * (distance * 0.22f);
                            cam.transform.LookAt(target);
                            cam.fieldOfView = 35f;
                        });
                        steps.Enqueue(() => Capture(cam, Path.Combine(dir, $"anim3_{label}.png"), 1280, 720));
                    }
                    steps.Enqueue(() => UnityEngine.Object.DestroyImmediate(go));
                }

                var shoot = EchoesAnimationImport.Clip("AN_GhostArcher_Shoot");
                var roar = EchoesAnimationImport.Clip(EchoesAnimationImport.RoarName);
                var stun = EchoesAnimationImport.Clip(EchoesAnimationImport.StunName);
                var run = EchoesAnimationImport.Clip(EchoesAnimationImport.ChargeRunName);
                var windup = EchoesAnimationImport.Clip(EchoesAnimationImport.ChargeWindupName);
                Cast("P_Enemy_GhostArcher", 4f, 1.0f, 35f, new[]
                {
                    ("espectro_1_mira", shoot, 12 / EchoesAnimationImport.Fps),
                    ("espectro_2_disparo", shoot, EchoesAnimationImport.ShootReleaseFrame / EchoesAnimationImport.Fps),
                    ("espectro_3_recuperacao", shoot, 30 / EchoesAnimationImport.Fps),
                    ("espectro_corrigido", shoot, EchoesAnimationImport.ShootReleaseFrame / EchoesAnimationImport.Fps),
                });
                Cast("P_Boss_CryptGuardian", 12f, 2.0f, 35f, new[]
                {
                    ("guardiao_1_rugido_abrindo", roar, 18 / EchoesAnimationImport.Fps),
                    ("guardiao_2_rugido_apice", roar, 36 / EchoesAnimationImport.Fps),
                    ("guardiao_3_investida_preparacao", windup, 20 / EchoesAnimationImport.Fps),
                    ("guardiao_4_investida_corrida", run, 5 / EchoesAnimationImport.Fps),
                });
                Cast("P_Hero_Warrior", 4f, 0.8f, 35f, new[]
                {
                    ("guerreiro_atordoado", stun, 6 / EchoesAnimationImport.Fps),
                });

                EditorApplication.CallbackFunction tick = null;
                tick = () =>
                {
                    try
                    {
                        if (steps.Count > 0)
                        {
                            steps.Dequeue()();
                            return;
                        }
                        EditorApplication.update -= tick;
                        Debug.Log("[AnimationShowcase] Capturas anim3 em " + dir);
                        if (Application.isBatchMode) EditorApplication.Exit(0);
                    }
                    catch (Exception e)
                    {
                        EditorApplication.update -= tick;
                        Debug.LogError("[AnimationShowcase] Falhou: " + e);
                        if (Application.isBatchMode) EditorApplication.Exit(1);
                    }
                };
                EditorApplication.update += tick;
            }
            catch (Exception e)
            {
                Debug.LogError("[AnimationShowcase] Falhou: " + e);
                if (Application.isBatchMode) EditorApplication.Exit(1);
            }
        }


        /// <summary>Diagnostico do Espectro: o mesmo quadro com rim, emissao e tinta ligados e desligados, uma imagem por variante em tmp.</summary>
        public static void RunArcherDebug()
        {
            try
            {
                CriptaBuilder.BuildScene();
                EditorSceneManager.OpenScene(CriptaBuilder.ScenePath, OpenSceneMode.Single);
                var layout = CriptaLayout.LoadFromDocument();
                var follow = UnityEngine.Object.FindAnyObjectByType<FollowCamera>();
                var cam = follow.GetComponentInChildren<Camera>();
                follow.enabled = false;
                var hero = GameObject.Find("Hero");
                if (hero != null) hero.SetActive(false);
                foreach (var enemy in UnityEngine.Object.FindObjectsByType<Echoes.Gameplay.EnemyController>(FindObjectsSortMode.None)) enemy.gameObject.SetActive(false);
                var origin = new Vector3(layout.HeroSpawn.x, 0f, layout.HeroSpawn.y);
                var go = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Art/Prefabs/P_Enemy_GhostArcher.prefab"));
                go.transform.SetPositionAndRotation(origin, Quaternion.identity);
                var animator = go.GetComponentInChildren<Animator>(true);
                var clip = EchoesAnimationImport.Clip("AN_GhostArcher_Shoot");
                var renderers = go.GetComponentsInChildren<SkinnedMeshRenderer>();
                var material = new Material(renderers[0].sharedMaterial);
                foreach (var r in renderers) r.sharedMaterial = material;
                var variants = new (string, System.Action)[]
                {
                    ("a_atual", () => { }),
                    ("b_sem_rim", () => material.SetFloat("_RimIntensity", 0f)),
                    ("c_sem_emissao", () => { material.SetFloat("_RimIntensity", 0.5f); material.SetFloat("_EmissionIntensity", 0f); }),
                    ("d_sem_nada", () => { material.SetFloat("_RimIntensity", 0f); material.SetFloat("_EmissionIntensity", 0f); }),
                };
                var steps = new System.Collections.Generic.Queue<Action>();
                foreach (var variant in variants)
                {
                    var (label, apply) = variant;
                    steps.Enqueue(() =>
                    {
                        apply();
                        clip.SampleAnimation(animator.gameObject, 20 / 30f);
                        var target = origin + Vector3.up * 1.0f;
                        cam.transform.position = target + Quaternion.Euler(0f, 35f, 0f) * Vector3.forward * 4f + Vector3.up * 0.9f;
                        cam.transform.LookAt(target);
                        cam.fieldOfView = 35f;
                    });
                    steps.Enqueue(() => Capture(cam, "D:/openclaude/_trabalho-claude/tmp/dbg_" + label + ".png", 640, 640));
                }
                EditorApplication.CallbackFunction tick = null;
                tick = () =>
                {
                    try
                    {
                        if (steps.Count > 0) { steps.Dequeue()(); return; }
                        EditorApplication.update -= tick;
                        if (Application.isBatchMode) EditorApplication.Exit(0);
                    }
                    catch (Exception e)
                    {
                        EditorApplication.update -= tick;
                        Debug.LogError("[AnimationShowcase] Falhou: " + e);
                        if (Application.isBatchMode) EditorApplication.Exit(1);
                    }
                };
                EditorApplication.update += tick;
            }
            catch (Exception e)
            {
                Debug.LogError("[AnimationShowcase] Falhou: " + e);
                if (Application.isBatchMode) EditorApplication.Exit(1);
            }
        }

        /// <summary>Folha de contato (diagnostico): o clipe amostrado em N instantes, numa grade, para ajustar tempos e musculos.</summary>
        public static void RunSheet()
        {
            try
            {
                KayKitAnimationImport.Apply();
                CriptaBuilder.BuildScene();
                EditorSceneManager.OpenScene(CriptaBuilder.ScenePath, OpenSceneMode.Single);
                var dir = Environment.GetEnvironmentVariable("ECHOES_CAPTURE_DIR");
                if (string.IsNullOrEmpty(dir)) dir = @"D:\openclaude\_trabalho-claude\tmp";
                var layout = CriptaLayout.LoadFromDocument();
                var follow = UnityEngine.Object.FindAnyObjectByType<FollowCamera>();
                var cam = follow.GetComponentInChildren<Camera>();
                follow.enabled = false;
                var hero = GameObject.Find("Hero");
                if (hero != null) hero.SetActive(false);
                var origin = new Vector3(layout.HeroSpawn.x, 0f, layout.HeroSpawn.y);
                var prefabName = Environment.GetEnvironmentVariable("SHEET_PREFAB") ?? "P_Hero_Warrior";
                var fbx = Environment.GetEnvironmentVariable("SHEET_FBX") ?? "Medium/Rig_Medium_CombatMelee";
                var clipName = Environment.GetEnvironmentVariable("SHEET_CLIP") ?? "Melee_1H_Attack_Slice_Horizontal";
                var clip = KayKitAnimationImport.FindClip($"{KayKitAnimationImport.Root}/{fbx}.fbx", clipName);
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>($"Assets/Art/Prefabs/{prefabName}.prefab");
                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                go.transform.SetPositionAndRotation(origin, Quaternion.identity);
                var animator = go.GetComponentInChildren<Animator>(true);
                const int cols = 4, rows = 3, w = 480, h = 360;
                var sheet = new Texture2D(cols * w, rows * h, TextureFormat.RGB24, false);
                var distance = prefabName.Contains("Boss") ? 12f : 4f;
                var look = prefabName.Contains("Boss") ? 2f : 0.8f;
                var yaw = float.Parse(Environment.GetEnvironmentVariable("SHEET_YAW") ?? "35", System.Globalization.CultureInfo.InvariantCulture);
                var index = 0;
                var sampled = false;
                EditorApplication.CallbackFunction tick = null;
                tick = () =>
                {
                    try
                    {
                        if (!sampled)
                        {
                            clip.SampleAnimation(animator.gameObject, clip.length * index / (cols * rows - 1));
                            var target = origin + Vector3.up * look;
                            var direction = Quaternion.Euler(0f, yaw, 0f) * Vector3.forward;
                            cam.transform.position = target + direction * distance + Vector3.up * (distance * 0.22f);
                            cam.transform.LookAt(target);
                            cam.fieldOfView = 35f;
                            sampled = true;
                            return;
                        }
                        sampled = false;
                        var rt = new RenderTexture(w, h, 24, RenderTextureFormat.ARGB32);
                        cam.targetTexture = rt;
                        cam.Render();
                        cam.Render();
                        RenderTexture.active = rt;
                        var tile = new Texture2D(w, h, TextureFormat.RGB24, false);
                        tile.ReadPixels(new Rect(0, 0, w, h), 0, 0);
                        sheet.SetPixels((index % cols) * w, (rows - 1 - index / cols) * h, w, h, tile.GetPixels());
                        cam.targetTexture = null;
                        RenderTexture.active = null;
                        UnityEngine.Object.DestroyImmediate(tile);
                        rt.Release();
                        UnityEngine.Object.DestroyImmediate(rt);
                        index++;
                        if (index < cols * rows) return;
                        EditorApplication.update -= tick;
                        File.WriteAllBytes(Path.Combine(dir, $"sheet_{prefabName}_{clipName}.png"), sheet.EncodeToPNG());
                        Debug.Log($"[AnimationShowcase] folha {clipName}: {clip.length}s");
                        if (Application.isBatchMode) EditorApplication.Exit(0);
                    }
                    catch (Exception e)
                    {
                        EditorApplication.update -= tick;
                        Debug.LogError("[AnimationShowcase] Falhou: " + e);
                        if (Application.isBatchMode) EditorApplication.Exit(1);
                    }
                };
                EditorApplication.update += tick;
                return;
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
