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
    /// Refugio do Marco (docs/16, S-04) com o kit de cenario pintado da Cripta, pequeno (40 x 30 m): o heroi nasce perto do portal da Cripta, a Ilsa
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
        // S-04: Vendedor, Encantador e Bau compartilhado a poucos passos (ate 12 m uns dos outros). Capsulas com rotulo ate os modelos chegarem.
        public static readonly Vector3 VendorPosition = new Vector3(3f, 0f, 9f);
        public static readonly Vector3 EnchanterPosition = new Vector3(3f, 0f, -9f);
        public static readonly Vector3 StashPosition = new Vector3(-3f, 0f, -3.5f);

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
            SceneryBuilder.AddFirePool(hero != null ? hero.transform : null);
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
            var gate = EnvironmentKit.Place("PortalAberto", portal.transform, portal.transform.position + new Vector3(1.4f, 0f, 0f), 90f, instanceName: "Gate");
            SceneryBuilder.AddFire(gate, false, 2.2f, new Color(0.62f, 0.5f, 1f), 1.6f, 7f);
            var zone = portal.AddComponent<PortalZone>();
            SandboxBuilder.SetRef(zone, "combatHost", ctx.Host);
            SandboxBuilder.SetRef(zone, "hero", hero);
            SandboxBuilder.SetString(zone, "portalId", "portal.refuge.crypt");
            SandboxBuilder.SetString(zone, "targetArea", AreaTravel.CryptArea);
            SandboxBuilder.SetBool(zone, "travels", true);
            MakeLabel(portal.transform, "Cripta", new Vector3(0f, 3.4f, 0f));

            MakeNpc("Ilsa", InteractableNpc.Ilsa, IlsaPosition, mats.Checkpoint, 1.8f);
            MakeNpc("Tico", InteractableNpc.Tico, TicoPosition, mats.Crate, 1.3f);
            // TODO(asset npc.vendor, npc.enchanter): modelos dos NPCs em producao; ate la, capsulas com rotulo.
            MakeNpc("Vendedor", InteractableNpc.Vendor, VendorPosition, mats.Crate, 1.5f);
            MakeNpc("Encantador", InteractableNpc.Enchanter, EnchanterPosition, mats.Boss, 1.7f);
            MakeNpc("Bau", InteractableNpc.Stash, StashPosition, mats.Pillar, 1.0f);

            // Sessao: toast, autosave, troca de area e o controlador do Refugio (Ilsa e Tico).
            CriptaBuilder.BuildSessionObjects(ctx, panel, false);
            var session = GameObject.Find("Session");
            var refuge = session.AddComponent<RefugeController>();
            SandboxBuilder.SetRef(refuge, "root", ctx.GameRoot);
            SandboxBuilder.SetRef(refuge, "hero", hero);

            EditorSceneManager.SaveScene(scene, ScenePath);
            Echoes.EditorTools.Build.AddSceneToBuildSettings(ScenePath);
        }

        /// <summary>Refugio com o kit pintado da Cripta (pisos de 2 m, paredes de 2 m, postes de canto, pilares, blocos, sarcofago como mesa, braseiros e entulho).</summary>
        static void BuildLevel(SandboxBuilder.Mats mats)
        {
            EnvironmentKit.Import();
            var level = new GameObject("Level").transform;
            var decor = new GameObject("Decor").transform;
            var floor = new GameObject("Floor");
            floor.transform.SetParent(level, false);
            var rect = new Rect(-Width / 2f, -Depth / 2f, Width, Depth);
            var box = floor.AddComponent<BoxCollider>();
            box.center = new Vector3(0f, -0.1f, 0f);
            box.size = new Vector3(Width, 0.2f, Depth);
            SceneryBuilder.BuildFloor(floor.transform, "refuge", rect, null);
            var walls = new GameObject("Walls").transform;
            walls.SetParent(level, false);
            SceneryBuilder.WallRun(walls, "refuge_s", true, rect.yMin, rect.xMin, rect.xMax, false);
            SceneryBuilder.WallRun(walls, "refuge_n", true, rect.yMax, rect.xMin, rect.xMax, true);
            SceneryBuilder.WallRun(walls, "refuge_w", false, rect.xMin, rect.yMin, rect.yMax, false);
            SceneryBuilder.WallRun(walls, "refuge_e", false, rect.xMax, rect.yMin, rect.yMax, true);
            SceneryBuilder.CornerPosts(walls, "refuge", rect);
            var props = new GameObject("Props").transform;
            props.SetParent(level, false);
            foreach (var corner in new[] { new Vector3(-17f, 0f, 12f), new Vector3(17f, 0f, 12f), new Vector3(-17f, 0f, -12f), new Vector3(17f, 0f, -12f) })
                EnvironmentKit.Place("PilarInteiro", props, corner, 0f, instanceName: "Pillar");
            EnvironmentKit.Place("BlocoA", props, new Vector3(-11f, 0f, 7.5f), 20f, instanceName: "Crate_A");
            EnvironmentKit.Place("BlocoB", props, new Vector3(-11f, 0f, -7.5f), -15f, instanceName: "Crate_B");
            EnvironmentKit.Place("SarcofagoFechado", props, new Vector3(-5f, 0f, 0f), 90f, instanceName: "Table");
            foreach (var pos in new[] { new Vector3(12f, 0f, 5f), new Vector3(12f, 0f, -5f), new Vector3(-14f, 0f, 0f), new Vector3(-6f, 0f, 10f), new Vector3(-6f, 0f, -10f) })
            {
                var brazier = EnvironmentKit.Place("Braseiro", props, pos, 0f, instanceName: "Brazier");
                SceneryBuilder.AddBrazierFire(brazier);
            }
            var rng = SceneryBuilder.Rng("refuge.decor");
            foreach (var name in new[] { "Velas", "Velas", "Ossos", "PedraE", "PedraF", "PedraE", "Ossos", "PedraF" })
            {
                var p = new Vector3((float)(rng.NextDouble() * 30.0 - 15.0), 0f, (float)(rng.NextDouble() * 20.0 - 10.0));
                if (Mathf.Abs(p.x) < 4f && Mathf.Abs(p.z) < 3f) continue;                         // longe do ponto de chegada e do caminho ate o portal
                if (Mathf.Abs(p.z) < 2.5f && p.x > 0f) continue;
                var go = EnvironmentKit.Place(name, decor, p, (float)rng.NextDouble() * 360f, colliders: false, instanceName: name);
                if (name == "Velas") SceneryBuilder.AddCandleFire(go);
            }
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
