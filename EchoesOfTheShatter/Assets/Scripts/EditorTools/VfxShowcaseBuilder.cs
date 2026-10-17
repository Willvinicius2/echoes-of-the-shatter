using System;
using System.Collections.Generic;
using System.IO;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Presentation;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Monta a cena da vitrine de VFX (Assets/Scenes/Sandbox/VfxShowcase.unity): piso da Cripta, luz como a do jogo, o GameRoot e o combate de
    /// verdade, os presenters do jogo (VfxPool, ProjectilePresenter, SkillVfxPresenter) e os modelos dos bonecos de treino. O componente
    /// <see cref="VfxShowcase"/> faz o resto em Play quando o argumento <c>-vfxshow PASTA</c> está na linha de comando.
    /// Linha de comando (sem -nographics, a vitrine renderiza):
    /// <c>Unity.exe -batchmode -projectPath ... -executeMethod Echoes.EditorTools.VfxShowcaseLauncher.Run -vfxshow D:\pasta [-vfxonly id] [-vfxviews perto,56m]</c>
    /// </summary>
    public static class VfxShowcaseBuilder
    {
        public const string ScenePath = "Assets/Scenes/Sandbox/VfxShowcase.unity";
        public const string ScriptPath = "Assets/Data/Presentation/VfxShowcase.json";

        [MenuItem("Echoes/Montar cena da vitrine de VFX")]
        public static void Build()
        {
            VfxLibraryBuilder.Build();
            BuildScene();
        }

        public static void BuildScene()
        {
            SandboxBuilder.EnsureDir(Path.GetDirectoryName(ScenePath).Replace('\\', '/'));
            var feel = SandboxBuilder.LoadOrCreate<CombatFeelSettings>(SandboxBuilder.DataDir + "/SO_CombatFeel.asset");
            var renderSettings = SandboxBuilder.LoadOrCreate<RenderSettingsAsset>(SandboxBuilder.DataDir + "/SO_RenderSettings.asset");
            var library = AssetDatabase.LoadAssetAtPath<SkillVfxLibrary>(VfxLibraryBuilder.LibraryPath);
            var script = AssetDatabase.LoadAssetAtPath<TextAsset>(ScriptPath);
            if (library == null || script == null) throw new InvalidOperationException("Biblioteca de VFX ou roteiro ausente: rode Echoes > Construir biblioteca de VFX.");

            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            RenderSettings.skybox = null;
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.55f, 0.52f, 0.58f); // a mesma ambiência da Cripta
            RenderSettings.fog = false;

            var lightGo = new GameObject("Directional Light");
            lightGo.transform.rotation = Quaternion.Euler(50f, -25f, 0f);
            var light = lightGo.AddComponent<Light>();
            light.type = LightType.Directional;
            light.color = new Color(1f, 0.95f, 0.88f);
            light.intensity = 1.1f;
            light.shadows = LightShadows.Soft;

            BuildFloor();

            var gameRootGo = new GameObject("GameRoot");
            var gameRoot = gameRootGo.AddComponent<GameRoot>();
            var rootObject = new SerializedObject(gameRoot);
            rootObject.FindProperty("fixedRunSeed").longValue = 12345;
            rootObject.ApplyModifiedPropertiesWithoutUndo();

            var combatGo = new GameObject("Combat");
            var host = combatGo.AddComponent<CombatSystemHost>();
            SandboxBuilder.SetRef(host, "root", gameRoot);
            SandboxBuilder.SetRef(host, "feel", feel);
            SandboxBuilder.SetInt(host, "maxStepsPerFrame", 8);

            var presentationGo = new GameObject("Presentation");
            var pool = presentationGo.AddComponent<VfxPool>();
            var projectiles = presentationGo.AddComponent<ProjectilePresenter>();
            SandboxBuilder.SetRef(projectiles, "root", gameRoot);
            SandboxBuilder.SetRef(projectiles, "combatHost", host);
            SandboxBuilder.SetRef(projectiles, "prefab", AssetDatabase.LoadAssetAtPath<GameObject>(SandboxBuilder.PrefabDir + "/P_Projectile_Placeholder.prefab"));
            SandboxBuilder.SetFloat(projectiles, "height", 1f);
            var presenter = presentationGo.AddComponent<SkillVfxPresenter>();
            SandboxBuilder.SetRef(presenter, "root", gameRoot);
            SandboxBuilder.SetRef(presenter, "combatHost", host);
            SandboxBuilder.SetRef(presenter, "vfxPool", pool);
            SandboxBuilder.SetRef(presenter, "library", library);

            var camGo = new GameObject("Main Camera") { tag = "MainCamera" };
            var cam = camGo.AddComponent<Camera>();
            camGo.AddComponent<AudioListener>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.059f, 0.043f, 0.078f);
            cam.allowHDR = true;

            var templates = new GameObject("Templates");
            var warrior = Template(templates.transform, "Template_Warrior", CharacterPrefabBuilder.HeroPrefab("warrior"), AnimatorControllerBuilder.WarriorSkillSetPath, gameRoot);
            var archer = Template(templates.transform, "Template_Archer", CharacterPrefabBuilder.HeroPrefab("archer"), VfxLibraryBuilder.ArcherSetPath, gameRoot);
            var mage = Template(templates.transform, "Template_Mage", CharacterPrefabBuilder.HeroPrefab("mage"), VfxLibraryBuilder.MageSetPath, gameRoot);
            var dummy = Template(templates.transform, "Template_Dummy", LoadPrefab("P_Enemy_HollowSentinel"),
                $"{AnimatorControllerBuilder.SkillSetDir}/{AnimatorControllerBuilder.EnemyHumanoid.SkillSet}.asset", gameRoot);
            var ghost = Template(templates.transform, "Template_Ghost", LoadPrefab("P_Enemy_GhostArcher"), VfxLibraryBuilder.GhostArcherSetPath, gameRoot);
            templates.SetActive(false);

            var showGo = new GameObject("VfxShowcase");
            var show = showGo.AddComponent<VfxShowcase>();
            SandboxBuilder.SetRef(show, "root", gameRoot);
            SandboxBuilder.SetRef(show, "host", host);
            SandboxBuilder.SetRef(show, "pool", pool);
            SandboxBuilder.SetRef(show, "presenter", presenter);
            SandboxBuilder.SetRef(show, "viewCamera", cam);
            SandboxBuilder.SetRef(show, "renderSettings", renderSettings);
            SandboxBuilder.SetRef(show, "script", script);
            SandboxBuilder.SetRef(show, "warriorTemplate", warrior);
            SandboxBuilder.SetRef(show, "archerTemplate", archer);
            SandboxBuilder.SetRef(show, "mageTemplate", mage);
            SandboxBuilder.SetRef(show, "dummyTemplate", dummy);
            SandboxBuilder.SetRef(show, "ghostTemplate", ghost);

            EditorSceneManager.SaveScene(scene, ScenePath);
            Debug.Log("[VfxShowcase] Cena montada em " + ScenePath);
        }

        static GameObject LoadPrefab(string name)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>($"{SandboxBuilder.PrefabDir}/{name}.prefab");
            if (prefab == null) throw new InvalidOperationException("Prefab ausente: " + name);
            return prefab;
        }

        // Modelo de boneco: AttributeComponent + PresentationController (a apresentação de verdade) com o corpo pintado como filho.
        static GameObject Template(Transform parent, string name, GameObject body, string skillSetPath, GameRoot gameRoot)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.AddComponent<AttributeComponent>();
            var presentation = go.AddComponent<PresentationController>();
            SandboxBuilder.SetRef(presentation, "root", gameRoot);
            var set = AssetDatabase.LoadAssetAtPath<SkillPresentationSet>(skillSetPath);
            if (set != null) SandboxBuilder.SetRef(presentation, "skillSet", set);
            var visual = (GameObject)PrefabUtility.InstantiatePrefab(body);
            visual.name = "Body";
            visual.transform.SetParent(go.transform, false);
            return go;
        }

        // Piso: ladrilhos de 2 m com o material do piso liso da Cripta (UV 0..1 por ladrilho, como o módulo do kit).
        static void BuildFloor()
        {
            var material = AssetDatabase.LoadAssetAtPath<Material>("Assets/Art/Materials/Environment/M_Cripta_PisoLiso.mat");
            const int cells = 24; // 48 m x 48 m
            const float module = 2f;
            var vertices = new List<Vector3>();
            var uvs = new List<Vector2>();
            var triangles = new List<int>();
            for (var ix = 0; ix < cells; ix++)
            {
                for (var iz = 0; iz < cells; iz++)
                {
                    var x0 = (ix - cells / 2) * module;
                    var z0 = (iz - cells / 2) * module;
                    var first = vertices.Count;
                    vertices.Add(new Vector3(x0, 0f, z0));
                    vertices.Add(new Vector3(x0, 0f, z0 + module));
                    vertices.Add(new Vector3(x0 + module, 0f, z0 + module));
                    vertices.Add(new Vector3(x0 + module, 0f, z0));
                    uvs.Add(new Vector2(0f, 0f));
                    uvs.Add(new Vector2(0f, 1f));
                    uvs.Add(new Vector2(1f, 1f));
                    uvs.Add(new Vector2(1f, 0f));
                    triangles.AddRange(new[] { first, first + 1, first + 2, first, first + 2, first + 3 });
                }
            }
            var mesh = new Mesh { name = "SM_VfxShowcase_Floor", indexFormat = IndexFormat.UInt32 };
            mesh.SetVertices(vertices);
            mesh.SetUVs(0, uvs);
            mesh.SetTriangles(triangles, 0);
            mesh.RecalculateNormals();
            mesh.RecalculateTangents();
            mesh.RecalculateBounds();
            mesh = SandboxBuilder.SaveMesh(mesh, VfxLibraryBuilder.MeshDir + "/SM_VfxShowcase_Floor.asset");
            var floor = new GameObject("Floor");
            floor.AddComponent<MeshFilter>().sharedMesh = mesh;
            var renderer = floor.AddComponent<MeshRenderer>();
            renderer.sharedMaterial = material;
            renderer.shadowCastingMode = ShadowCastingMode.Off;
            renderer.receiveShadows = true;
        }
    }

    /// <summary>
    /// Ponto de entrada de linha de comando da vitrine (<c>-executeMethod Echoes.EditorTools.VfxShowcaseLauncher.Run</c>): constrói a biblioteca e a cena,
    /// entra em Play e, quando a vitrine termina, fecha o Editor com o código de saída dela.
    /// </summary>
    public static class VfxShowcaseLauncher
    {
        public const string SessionKey = "echoes.vfxshow.active";
        public const string ExitKey = "echoes.vfxshow.exit";

        public static void Run()
        {
            try
            {
                VfxShowcaseBuilder.Build();
                EditorSceneManager.OpenScene(VfxShowcaseBuilder.ScenePath, OpenSceneMode.Single);
                SessionState.SetBool(SessionKey, true);
                SessionState.SetInt(ExitKey, 0);
                EditorApplication.isPlaying = true;
            }
            catch (Exception e)
            {
                Debug.LogError("[VfxShowcase] Falhou ao preparar: " + e);
                if (Application.isBatchMode) EditorApplication.Exit(1);
            }
        }
    }

    [InitializeOnLoad]
    static class VfxShowcaseExit
    {
        static VfxShowcaseExit()
        {
            EditorApplication.playModeStateChanged += state =>
            {
                if (state != PlayModeStateChange.EnteredEditMode || !SessionState.GetBool(VfxShowcaseLauncher.SessionKey, false)) return;
                SessionState.SetBool(VfxShowcaseLauncher.SessionKey, false);
                if (Application.isBatchMode) EditorApplication.Exit(SessionState.GetInt(VfxShowcaseLauncher.ExitKey, 0));
            };
        }
    }
}
