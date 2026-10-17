using System;
using System.IO;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Presentation;
using Echoes.UI;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.UIElements;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Refugio do Marco (docs/16, S-04) com primitivas e o kit graybox, pequeno (40 x 30 m): o heroi nasce perto do portal da Cripta, a Ilsa
    /// (configurar e iniciar a expedicao) e o Tico (coletar e ver o relatorio) ficam a poucos passos. Sem inimigos. Cena: Assets/Scenes/Refugio/Refugio.unity.
    /// </summary>
    public static class RefugioBuilder
    {
        public const string ScenePath = "Assets/Scenes/Refugio/Refugio.unity";
        public const float Width = 40f, Depth = 30f;
        public static readonly Vector3 HeroSpawn = new Vector3(0f, 0f, 0f);
        public static readonly Vector3 PortalPosition = new Vector3(15f, 0f, 0f);
        public static readonly Vector3 IlsaPosition = new Vector3(-8f, 0f, 6f);
        public static readonly Vector3 TicoPosition = new Vector3(-8f, 0f, -6f);

        [MenuItem("Echoes/Montar Refugio")]
        public static void Build()
        {
            BuildScene();
            Debug.Log("[RefugioBuilder] Cena salva em " + ScenePath);
        }

        public static void BuildScene()
        {
            SandboxBuilder.EnsureDir(SandboxBuilder.DataDir);
            SandboxBuilder.EnsureDir(SandboxBuilder.MaterialDir);
            SandboxBuilder.EnsureDir(SandboxBuilder.PrefabDir);
            SandboxBuilder.EnsureDir(SandboxBuilder.UiDir);
            SandboxBuilder.EnsureDir(Path.GetDirectoryName(ScenePath).Replace('\\', '/'));

            var renderSettings = SandboxBuilder.LoadOrCreate<RenderSettingsAsset>(SandboxBuilder.DataDir + "/SO_RenderSettings.asset");
            var feel = SandboxBuilder.LoadOrCreate<CombatFeelSettings>(SandboxBuilder.DataDir + "/SO_CombatFeel.asset");
            var panel = SandboxBuilder.CreatePanelSettings();
            var mats = SandboxBuilder.CreateMaterials();
            var projectile = SandboxBuilder.CreateProjectilePrefab(mats);
            var inputActions = AssetDatabase.LoadAssetAtPath<InputActionAsset>("Assets/Settings/Echoes.inputactions");
            var hudUxml = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(SandboxBuilder.UiDir + "/Views/HudView.uxml");
            if (inputActions == null) throw new InvalidOperationException("Assets/Settings/Echoes.inputactions nao encontrado.");
            if (hudUxml == null) throw new InvalidOperationException("Assets/UI/Views/HudView.uxml nao encontrado.");

            var ctx = new CriptaBuilder.Context { Mats = mats };
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            RenderSettings.skybox = null;
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.6f, 0.56f, 0.62f);
            var lightGo = new GameObject("Directional Light");
            lightGo.transform.rotation = Quaternion.Euler(50f, -25f, 0f);
            var light = lightGo.AddComponent<Light>();
            light.type = LightType.Directional;
            light.color = new Color(1f, 0.93f, 0.82f);
            light.intensity = 1.1f;
            light.shadows = LightShadows.Soft;

            BuildLevel(mats);
            CriptaBuilder.BuildSystems(ctx, feel, projectile);
            var hero = CriptaBuilder.BuildHero(ctx, renderSettings, inputActions, HeroSpawn);
            CriptaBuilder.BuildHud(ctx, panel, hudUxml);

            // Portal para a Cripta (PortalZone avisa, AreaTravel troca a cena; heroi ocupado numa expedicao fica retido com dlg.ilsa.busy).
            var portal = new GameObject("portal.refuge.crypt");
            portal.transform.position = PortalPosition;
            var ring = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            ring.name = "Ring";
            UnityEngine.Object.DestroyImmediate(ring.GetComponent<Collider>());
            ring.transform.SetParent(portal.transform, false);
            ring.transform.localScale = new Vector3(3.6f, 0.04f, 3.6f);
            ring.transform.localPosition = new Vector3(0f, 0.04f, 0f);
            SandboxBuilder.Apply(ring, mats.Boss);
            var pillar = GameObject.CreatePrimitive(PrimitiveType.Cube);
            pillar.name = "Gate";
            UnityEngine.Object.DestroyImmediate(pillar.GetComponent<Collider>());
            pillar.transform.SetParent(portal.transform, false);
            pillar.transform.localScale = new Vector3(0.4f, 3f, 3f);
            pillar.transform.localPosition = new Vector3(1.4f, 1.5f, 0f);
            SandboxBuilder.Apply(pillar, mats.Boss);
            var zone = portal.AddComponent<PortalZone>();
            SandboxBuilder.SetRef(zone, "combatHost", ctx.Host);
            SandboxBuilder.SetRef(zone, "hero", hero);
            SandboxBuilder.SetString(zone, "portalId", "portal.refuge.crypt");
            SandboxBuilder.SetString(zone, "targetArea", AreaTravel.CryptArea);
            SandboxBuilder.SetBool(zone, "travels", true);
            MakeLabel(portal.transform, "Cripta", new Vector3(0f, 3.4f, 0f));

            MakeNpc("Ilsa", InteractableNpc.Ilsa, IlsaPosition, mats.Checkpoint, 1.8f);
            MakeNpc("Tico", InteractableNpc.Tico, TicoPosition, mats.Crate, 1.3f);

            // Sessao: toast, autosave, troca de area e o controlador do Refugio (Ilsa e Tico).
            CriptaBuilder.BuildSessionObjects(ctx, panel, false);
            var session = GameObject.Find("Session");
            var refuge = session.AddComponent<RefugeController>();
            SandboxBuilder.SetRef(refuge, "root", ctx.GameRoot);
            SandboxBuilder.SetRef(refuge, "hero", hero);

            EditorSceneManager.SaveScene(scene, ScenePath);
            Echoes.EditorTools.Build.AddSceneToBuildSettings(ScenePath);
        }

        static void BuildLevel(SandboxBuilder.Mats mats)
        {
            var level = new GameObject("Level").transform;
            Block(level, "Floor", new Vector3(0f, -0.1f, 0f), new Vector3(Width, 0.2f, Depth), mats.FloorA);
            const float h = 3f, t = 0.6f;
            Block(level, "Wall_N", new Vector3(0f, h / 2f, Depth / 2f), new Vector3(Width + t, h, t), mats.Wall);
            Block(level, "Wall_S", new Vector3(0f, h / 2f, -Depth / 2f), new Vector3(Width + t, h, t), mats.Wall);
            Block(level, "Wall_E", new Vector3(Width / 2f, h / 2f, 0f), new Vector3(t, h, Depth), mats.Wall);
            Block(level, "Wall_W", new Vector3(-Width / 2f, h / 2f, 0f), new Vector3(t, h, Depth), mats.Wall);
            // Cenario simples com o kit graybox: pilares nos cantos e caixas perto dos NPCs.
            foreach (var corner in new[] { new Vector3(-17f, 0f, 12f), new Vector3(17f, 0f, 12f), new Vector3(-17f, 0f, -12f), new Vector3(17f, 0f, -12f) })
                Block(level, "Pillar", corner + new Vector3(0f, 1.5f, 0f), new Vector3(1.2f, 3f, 1.2f), mats.Pillar);
            Block(level, "Crate_A", new Vector3(-11f, 0.5f, 7.5f), new Vector3(1f, 1f, 1f), mats.Crate);
            Block(level, "Crate_B", new Vector3(-11f, 0.5f, -7.5f), new Vector3(1f, 1f, 1f), mats.Crate);
            Block(level, "Table", new Vector3(-5f, 0.45f, 0f), new Vector3(2.4f, 0.9f, 1.2f), mats.Crate);
        }

        static void Block(Transform parent, string name, Vector3 position, Vector3 scale, Material material)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = name;
            go.transform.SetParent(parent, false);
            go.transform.position = position;
            go.transform.localScale = scale;
            SandboxBuilder.Apply(go, material);
        }

        static void MakeNpc(string name, string npcId, Vector3 position, Material material, float height)
        {
            var go = new GameObject(name);
            go.transform.position = position;
            var body = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            body.name = "Body";
            UnityEngine.Object.DestroyImmediate(body.GetComponent<Collider>());
            body.transform.SetParent(go.transform, false);
            body.transform.localScale = new Vector3(0.8f, height / 2f, 0.8f);
            body.transform.localPosition = new Vector3(0f, height / 2f, 0f);
            SandboxBuilder.Apply(body, material);
            var npc = go.AddComponent<InteractableNpc>();
            npc.npcId = npcId;
            MakeLabel(go.transform, name, new Vector3(0f, height + 0.5f, 0f));
        }

        static void MakeLabel(Transform parent, string text, Vector3 localPosition)
        {
            var go = new GameObject("Label");
            go.transform.SetParent(parent, false);
            go.transform.localPosition = localPosition;
            go.transform.localRotation = Quaternion.Euler(50f, 0f, 0f); // de frente para a camera 3/4
            var mesh = go.AddComponent<TextMesh>();
            mesh.text = text;
            mesh.characterSize = 0.18f;
            mesh.fontSize = 48;
            mesh.anchor = TextAnchor.MiddleCenter;
            mesh.alignment = TextAlignment.Center;
            mesh.color = new Color(0.95f, 0.85f, 0.55f);
        }
    }
}
