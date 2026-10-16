using System;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Presentation;
using Echoes.UI;
using Unity.AI.Navigation;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.InputSystem;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using UnityEngine.UIElements;
using Object = UnityEngine.Object;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Monta a cena base de escala (Assets/Scenes/Sandbox/Base_Escala.unity) seguindo a seção 3 e 4 de
    /// Assets/Scripts/README.md: assets de apresentação, materiais de graybox, duas zonas do mesmo traçado
    /// em escalas diferentes (A = ARPG de PC, B = MMO), sistemas, herói, inimigos, câmera, HUD e NavMesh.
    /// Só primitivas da Unity. Idempotente: recria a cena e atualiza os assets pelos mesmos caminhos.
    /// Menu: Echoes ▸ Montar cena base. Batchmode: -executeMethod Echoes.EditorTools.SandboxBuilder.BuildFromCommandLine
    /// </summary>
    public static class SandboxBuilder
    {
        internal const string ScenePath = "Assets/Scenes/Sandbox/Base_Escala.unity";
        internal const string DataDir = "Assets/Data/Presentation";
        internal const string MaterialDir = "Assets/Art/Materials/Graybox";
        internal const string GeneratedDir = "Assets/Art/Generated/Sandbox";
        internal const string PrefabDir = "Assets/Art/Prefabs";
        internal const string UiDir = "Assets/UI";
        internal const string WarriorFbx = "Assets/Art/Characters/Warrior/SK_Warrior.fbx";
        internal const string WarriorBaseMap = "Assets/Art/Characters/Warrior/T_Warrior_BC.png";
        internal const string WarriorMaskMap = "Assets/Art/Characters/Warrior/T_Warrior_M.png";
        internal const string CharacterShaderPath = "Assets/Art/Materials/Masters/SG_Character.shader";
        internal const string CharacterMaterialDir = "Assets/Art/Materials/Characters";
        internal const string WarriorPrefabPath = "Assets/Art/Prefabs/P_Hero_Warrior.prefab";

        internal const float WallHeight = 3f;
        internal const float WallThickness = 0.6f;
        internal const float Tile = 2f;
        internal const float ZoneBOffsetX = 300f;
        internal const float HeroHeight = 1.5f;

        internal struct ZoneSpec
        {
            public string Name;
            public Vector3 Origin;
            public float RoomA;
            public float RoomB;
            public float Arena;
            public float CorridorWidth;
            public float CorridorLength;
        }

        internal sealed class ZoneResult
        {
            public Transform Spawn;
            public readonly List<Rect> FloorRects = new List<Rect>();
            public float[] Centers;
        }

        internal sealed class Mats
        {
            public Material FloorA, FloorB, Wall, Pillar, Crate, Hero, Enemy, Boss, Checkpoint, Telegraph, Warrior;
        }

        [MenuItem("Echoes/Montar cena base")]
        public static void Build()
        {
            BuildScene();
            Debug.Log($"[SandboxBuilder] Cena salva em {ScenePath}");
        }

        /// <summary>Para -executeMethod: falha com código de saída 1 se algo der errado.</summary>
        public static void BuildFromCommandLine()
        {
            try
            {
                BuildScene();
                Debug.Log($"[SandboxBuilder] Cena salva em {ScenePath}");
                if (Application.isBatchMode) EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Debug.LogError("[SandboxBuilder] Falhou: " + e);
                if (Application.isBatchMode) EditorApplication.Exit(1);
            }
        }

        internal static void BuildScene()
        {
            EnsureDir(DataDir); EnsureDir(MaterialDir); EnsureDir(GeneratedDir); EnsureDir(PrefabDir); EnsureDir(UiDir);
            EnsureDir(Path.GetDirectoryName(ScenePath).Replace('\\', '/'));

            var renderSettings = LoadOrCreate<RenderSettingsAsset>(DataDir + "/SO_RenderSettings.asset");
            var feel = LoadOrCreate<CombatFeelSettings>(DataDir + "/SO_CombatFeel.asset");
            var presets = LoadOrCreate<CameraDistancePresetsAsset>(DataDir + "/SO_CameraDistancePresets.asset");
            var panel = CreatePanelSettings();
            var mats = CreateMaterials();
            var projectile = CreateProjectilePrefab(mats);
            var inputActions = AssetDatabase.LoadAssetAtPath<InputActionAsset>("Assets/Settings/Echoes.inputactions");
            var hudUxml = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(UiDir + "/Views/HudView.uxml");
            if (inputActions == null) throw new InvalidOperationException("Assets/Settings/Echoes.inputactions não encontrado.");
            if (hudUxml == null) throw new InvalidOperationException("Assets/UI/Views/HudView.uxml não encontrado.");

            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            // ---- Ambiente e luz
            RenderSettings.skybox = null;
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.55f, 0.52f, 0.58f);
            RenderSettings.fog = false;
            var lightGo = new GameObject("Directional Light");
            lightGo.transform.rotation = Quaternion.Euler(50f, -25f, 0f);
            var light = lightGo.AddComponent<Light>();
            light.type = LightType.Directional;
            light.color = new Color(1f, 0.95f, 0.88f);
            light.intensity = 1.1f;
            light.shadows = LightShadows.Soft;

            // ---- Nível: duas zonas
            var level = new GameObject("Level").transform;
            var zoneA = BuildZone(level, mats, new ZoneSpec
            {
                Name = "ZoneA_ARPG", Origin = Vector3.zero,
                RoomA = 24f, RoomB = 32f, Arena = 40f, CorridorWidth = 6f, CorridorLength = 20f,
            });
            var zoneB = BuildZone(level, mats, new ZoneSpec
            {
                Name = "ZoneB_MMO", Origin = new Vector3(ZoneBOffsetX, 0f, 0f),
                RoomA = 32f, RoomB = 40f, Arena = 56f, CorridorWidth = 8f, CorridorLength = 20f,
            });

            // ---- Sistemas
            var gameRootGo = new GameObject("GameRoot");
            var gameRoot = gameRootGo.AddComponent<GameRoot>();
            var combatGo = new GameObject("Combat");
            var combatHost = combatGo.AddComponent<CombatSystemHost>();
            SetRef(combatHost, "root", gameRoot);
            SetRef(combatHost, "feel", feel);
            SetInt(combatHost, "maxStepsPerFrame", 8);

            var presentationGo = new GameObject("Presentation");
            presentationGo.AddComponent<VfxPool>();
            var telegraph = presentationGo.AddComponent<TelegraphPresenter>();
            SetRef(telegraph, "root", gameRoot);
            SetRef(telegraph, "fallbackMaterial", mats.Telegraph);
            var projectiles = presentationGo.AddComponent<ProjectilePresenter>();
            SetRef(projectiles, "root", gameRoot);
            SetRef(projectiles, "combatHost", combatHost);
            SetRef(projectiles, "prefab", projectile);
            SetFloat(projectiles, "height", 1f);

            // ---- Checkpoint
            var checkpoint = new GameObject("Checkpoint").transform;
            checkpoint.position = zoneA.Spawn.position + new Vector3(3f, 0f, 0f);
            var marker = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            marker.name = "CheckpointMarker";
            Object.DestroyImmediate(marker.GetComponent<Collider>());
            marker.transform.SetParent(checkpoint, false);
            marker.transform.localScale = new Vector3(1.2f, 0.02f, 1.2f);
            marker.transform.localPosition = new Vector3(0f, 0.03f, 0f);
            Apply(marker, mats.Checkpoint);

            // ---- Herói (README 4.3)
            var camGo = new GameObject("Main Camera") { tag = "MainCamera" };
            var cam = camGo.AddComponent<Camera>();
            camGo.AddComponent<AudioListener>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.059f, 0.043f, 0.078f); // pedra_noite #0F0B14

            var hero = new GameObject("Hero");
            hero.transform.position = zoneA.Spawn.position;
            var cc = hero.AddComponent<CharacterController>();
            cc.radius = 0.3f; cc.height = HeroHeight; cc.center = new Vector3(0f, 0.75f, 0f);
            cc.slopeLimit = 45f; cc.stepOffset = 0.3f;
            hero.AddComponent<AttributeComponent>();
            var heroController = hero.AddComponent<HeroController>();
            var inputHandler = hero.AddComponent<PlayerInputHandler>();
            SetRef(inputHandler, "actions", inputActions);
            SetBool(inputHandler, "loadSavedBindings", true);
            var heroPresentation = hero.AddComponent<PresentationController>();
            SetRef(heroPresentation, "root", gameRoot);
            SetRef(heroController, "combatHost", combatHost);
            SetRef(heroController, "input", inputHandler);
            SetRef(heroController, "aimCamera", cam);
            SetRef(heroController, "checkpoint", checkpoint);
            SetFloat(heroController, "respawnDelay", 1.5f);
            // Visual do herói: P_Hero_Warrior com o SK_Warrior aprovado (substitui a cápsula do graybox).
            // O CharacterController de 1,5 m acima continua sendo o corpo de jogo; a malha não tem colisor.
            var heroPrefab = BuildWarriorPrefab(mats.Warrior);
            var visual = (GameObject)PrefabUtility.InstantiatePrefab(heroPrefab);
            visual.name = "Body";
            visual.transform.SetParent(hero.transform, false);

            // ---- Câmera (README 4.5) + ferramentas de desenvolvimento
            var rig = new GameObject("CameraRig");
            rig.transform.position = hero.transform.position + new Vector3(0f, 0.52f, 0f);
            camGo.transform.SetParent(rig.transform, false);
            var follow = rig.AddComponent<FollowCamera>();
            SetRef(follow, "target", hero.transform);
            SetRef(follow, "viewCamera", cam);
            SetRef(follow, "settings", renderSettings);
            SetRef(follow, "root", gameRoot);
            SetBool(follow, "shakeEnabled", true);
            var tuner = rig.AddComponent<CameraDistanceTuner>();
            SetRef(tuner, "viewCamera", cam);
            SetRef(tuner, "presets", presets);
            SetRef(tuner, "measured", hero.transform);
            follow.ApplySettings();

            var dev = new GameObject("DevTools");
            var teleport = dev.AddComponent<DevZoneTeleport>();
            SetRef(teleport, "hero", hero.transform);
            SetRef(teleport, "followCamera", follow);
            SetRef(teleport, "checkpoint", checkpoint);
            SetRef(teleport, "zoneA", zoneA.Spawn);
            SetRef(teleport, "zoneB", zoneB.Spawn);

            // ---- HUD (README 4.7)
            var hud = new GameObject("HUD");
            var uiDoc = hud.AddComponent<UIDocument>();
            uiDoc.panelSettings = panel;
            uiDoc.visualTreeAsset = hudUxml;
            var hudView = hud.AddComponent<HudView>();
            SetRef(hudView, "root", gameRoot);
            SetRef(hudView, "hero", heroController);
            SetRef(hudView, "worldCamera", cam);

            // ---- NavMesh: só a geometria do Level entra (personagens ficam fora)
            var surface = level.gameObject.AddComponent<NavMeshSurface>();
            surface.collectObjects = CollectObjects.Children;
            surface.useGeometry = NavMeshCollectGeometry.RenderMeshes;
            surface.BuildNavMesh();
            if (surface.navMeshData != null)
            {
                var navPath = GeneratedDir + "/NavMesh_Base_Escala.asset";
                if (AssetDatabase.LoadAssetAtPath<Object>(navPath) != null) AssetDatabase.DeleteAsset(navPath);
                AssetDatabase.CreateAsset(surface.navMeshData, navPath);
            }

            // ---- Inimigos (README 4.4), depois do NavMesh para os agentes nascerem sobre ele
            var enemies = new GameObject("Enemies").transform;
            SpawnZoneEnemies(enemies, mats, combatHost, gameRoot, zoneA, "A", 24f, 32f, 40f);
            SpawnZoneEnemies(enemies, mats, combatHost, gameRoot, zoneB, "B", 32f, 40f, 56f);

            EditorSceneManager.SaveScene(scene, ScenePath);
            AddToBuildSettings();
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
        }

        // ------------------------------------------------------------------ zonas

        internal static ZoneResult BuildZone(Transform parent, Mats mats, ZoneSpec z)
        {
            var result = new ZoneResult();
            var root = new GameObject(z.Name).transform;
            root.SetParent(parent, false);
            var walls = new GameObject("Walls").transform; walls.SetParent(root, false);
            var props = new GameObject("Props").transform; props.SetParent(root, false);

            var rooms = new[] { z.RoomA, z.RoomB, z.Arena };
            var names = new[] { "Room1", "Room2", "Arena" };
            var centers = new float[3];
            var x = z.Origin.x;
            var w = z.CorridorWidth;
            var cz = z.Origin.z;

            // Posição X dos centros: sala 1 começa em Origin.x - S/2 + S/2 = Origin.x (o herói nasce nela).
            centers[0] = x;
            for (var i = 1; i < 3; i++)
                centers[i] = centers[i - 1] + rooms[i - 1] / 2f + z.CorridorLength + rooms[i] / 2f;

            for (var i = 0; i < 3; i++)
            {
                var s = rooms[i];
                var c = centers[i];
                result.FloorRects.Add(new Rect(c - s / 2f, cz - s / 2f, s, s));
                var hasWest = i > 0;
                var hasEast = i < 2;
                BuildRoomWalls(walls, mats.Wall, names[i], c, cz, s, w, hasWest, hasEast);
                AddFloorCollider(root, names[i] + "_FloorCollider", c, cz, s, s);
                BuildRoomProps(props, mats, names[i], c, cz, s, i == 2);
            }
            for (var i = 0; i < 2; i++)
            {
                var x0 = centers[i] + rooms[i] / 2f;
                var x1 = centers[i + 1] - rooms[i + 1] / 2f;
                var len = x1 - x0;
                var cx = (x0 + x1) / 2f;
                result.FloorRects.Add(new Rect(x0, cz - w / 2f, len, w));
                AddFloorCollider(root, $"Corridor{i + 1}_FloorCollider", cx, cz, len, w);
                // Paredes laterais do corredor, por fora do vão livre.
                AddWall(walls, mats.Wall, $"Corridor{i + 1}_N", new Vector3(cx, WallHeight / 2f, cz + w / 2f + WallThickness / 2f), new Vector3(len, WallHeight, WallThickness));
                AddWall(walls, mats.Wall, $"Corridor{i + 1}_S", new Vector3(cx, WallHeight / 2f, cz - w / 2f - WallThickness / 2f), new Vector3(len, WallHeight, WallThickness));
            }

            // Piso xadrez de 2 m: dois materiais alternados, uma malha por material.
            var meshA = BuildCheckerMesh(result.FloorRects, 0);
            var meshB = BuildCheckerMesh(result.FloorRects, 1);
            meshA = SaveMesh(meshA, $"{GeneratedDir}/{z.Name}_FloorA.asset");
            meshB = SaveMesh(meshB, $"{GeneratedDir}/{z.Name}_FloorB.asset");
            AddFloorVisual(root, "Floor_A", meshA, mats.FloorA);
            AddFloorVisual(root, "Floor_B", meshB, mats.FloorB);

            // Ponto de chegada: 30% da sala 1 para o lado oeste (longe do primeiro grupo).
            var spawn = new GameObject("Spawn").transform;
            spawn.SetParent(root, false);
            spawn.position = new Vector3(centers[0] - rooms[0] * 0.3f, 0f, cz);
            result.Spawn = spawn;

            result.Centers = centers;
            return result;
        }

        internal static void BuildRoomWalls(Transform parent, Material mat, string name, float cx, float cz, float s, float doorWidth, bool westDoor, bool eastDoor)
        {
            var half = s / 2f;
            var t = WallThickness;
            var h = WallHeight;
            var full = s + 2f * t;
            // Norte e sul (ao longo de X).
            AddWall(parent, mat, name + "_N", new Vector3(cx, h / 2f, cz + half + t / 2f), new Vector3(full, h, t));
            AddWall(parent, mat, name + "_S", new Vector3(cx, h / 2f, cz - half - t / 2f), new Vector3(full, h, t));
            // Oeste e leste (ao longo de Z), com vão para o corredor.
            AddSideWall(parent, mat, name + "_W", cx - half - t / 2f, cz, full, doorWidth, westDoor);
            AddSideWall(parent, mat, name + "_E", cx + half + t / 2f, cz, full, doorWidth, eastDoor);
        }

        internal static void AddSideWall(Transform parent, Material mat, string name, float x, float cz, float length, float doorWidth, bool hasDoor)
        {
            var h = WallHeight;
            var t = WallThickness;
            if (!hasDoor)
            {
                AddWall(parent, mat, name, new Vector3(x, h / 2f, cz), new Vector3(t, h, length));
                return;
            }
            var segment = (length - doorWidth) / 2f;
            var offset = doorWidth / 2f + segment / 2f;
            AddWall(parent, mat, name + "_1", new Vector3(x, h / 2f, cz + offset), new Vector3(t, h, segment));
            AddWall(parent, mat, name + "_2", new Vector3(x, h / 2f, cz - offset), new Vector3(t, h, segment));
        }

        internal static void AddWall(Transform parent, Material mat, string name, Vector3 center, Vector3 size)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = name;
            go.transform.SetParent(parent, false);
            go.transform.position = center;
            go.transform.localScale = size;
            Apply(go, mat);
        }

        internal static void AddFloorCollider(Transform parent, string name, float cx, float cz, float sx, float sz)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            var box = go.AddComponent<BoxCollider>();
            box.center = new Vector3(cx, -0.1f, cz);
            box.size = new Vector3(sx, 0.2f, sz);
        }

        internal static void AddFloorVisual(Transform parent, string name, Mesh mesh, Material mat)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = mat;
            mr.shadowCastingMode = ShadowCastingMode.Off;
        }

        internal static void BuildRoomProps(Transform parent, Mats mats, string name, float cx, float cz, float s, bool arena)
        {
            // Caixas do tamanho de um sarcófago (1 × 1 × 2 m, deitado) nos cantos, para dar escala.
            var edge = s / 2f - 3f;
            var corners = new[] { new Vector2(-edge, edge), new Vector2(edge, -edge), new Vector2(-edge, -edge) };
            var yaw = new[] { 15f, -20f, 90f };
            for (var i = 0; i < corners.Length; i++)
            {
                var crate = GameObject.CreatePrimitive(PrimitiveType.Cube);
                crate.name = $"{name}_Sarcophagus{i + 1}";
                crate.transform.SetParent(parent, false);
                crate.transform.position = new Vector3(cx + corners[i].x, 0.5f, cz + corners[i].y);
                crate.transform.rotation = Quaternion.Euler(0f, yaw[i], 0f);
                crate.transform.localScale = new Vector3(1f, 1f, 2f);
                Apply(crate, mats.Crate);
            }
            if (!arena) return;
            // 8 pilares de 1,2 × 4 × 1,2 m em anel: quatro cantos e quatro meios de lado.
            var o = s * 0.3f;
            var spots = new[]
            {
                new Vector2(o, o), new Vector2(-o, o), new Vector2(o, -o), new Vector2(-o, -o),
                new Vector2(o, 0f), new Vector2(-o, 0f), new Vector2(0f, o), new Vector2(0f, -o),
            };
            for (var i = 0; i < spots.Length; i++)
            {
                var pillar = GameObject.CreatePrimitive(PrimitiveType.Cube);
                pillar.name = $"{name}_Pillar{i + 1}";
                pillar.transform.SetParent(parent, false);
                pillar.transform.position = new Vector3(cx + spots[i].x, 2f, cz + spots[i].y);
                pillar.transform.localScale = new Vector3(1.2f, 4f, 1.2f);
                Apply(pillar, mats.Pillar);
            }
        }

        internal static Mesh BuildCheckerMesh(List<Rect> rects, int parity)
        {
            var vertices = new List<Vector3>();
            var triangles = new List<int>();
            var normals = new List<Vector3>();
            var uvs = new List<Vector2>();
            foreach (var r in rects)
            {
                var nx = Mathf.RoundToInt(r.width / Tile);
                var nz = Mathf.RoundToInt(r.height / Tile);
                for (var ix = 0; ix < nx; ix++)
                {
                    for (var iz = 0; iz < nz; iz++)
                    {
                        if (((ix + iz) & 1) != parity) continue;
                        var x0 = r.xMin + ix * Tile;
                        var z0 = r.yMin + iz * Tile;
                        var x1 = x0 + Tile;
                        var z1 = z0 + Tile;
                        var b = vertices.Count;
                        vertices.Add(new Vector3(x0, 0f, z0));
                        vertices.Add(new Vector3(x0, 0f, z1));
                        vertices.Add(new Vector3(x1, 0f, z1));
                        vertices.Add(new Vector3(x1, 0f, z0));
                        for (var k = 0; k < 4; k++) normals.Add(Vector3.up);
                        uvs.Add(new Vector2(0f, 0f)); uvs.Add(new Vector2(0f, 1f)); uvs.Add(new Vector2(1f, 1f)); uvs.Add(new Vector2(1f, 0f));
                        triangles.Add(b); triangles.Add(b + 1); triangles.Add(b + 2);
                        triangles.Add(b); triangles.Add(b + 2); triangles.Add(b + 3);
                    }
                }
            }
            var mesh = new Mesh { name = "CheckerFloor", indexFormat = IndexFormat.UInt32 };
            mesh.SetVertices(vertices);
            mesh.SetNormals(normals);
            mesh.SetUVs(0, uvs);
            mesh.SetTriangles(triangles, 0);
            mesh.RecalculateBounds();
            return mesh;
        }

        internal static Mesh SaveMesh(Mesh mesh, string path)
        {
            if (AssetDatabase.LoadAssetAtPath<Object>(path) != null) AssetDatabase.DeleteAsset(path);
            AssetDatabase.CreateAsset(mesh, path);
            return AssetDatabase.LoadAssetAtPath<Mesh>(path);
        }

        // ------------------------------------------------------------------ inimigos

        internal static void SpawnZoneEnemies(Transform parent, Mats mats, CombatSystemHost host, GameRoot gameRoot, ZoneResult zone, string tag, float r1, float r2, float arena)
        {
            var c = zone.Centers;
            var z0 = zone.Spawn.position.z;
            // Sala 1
            Enemy(parent, mats, host, gameRoot, $"Hound_{tag}1", "enemy.ash_hound", 3, P(c[0], z0, r1, 0.30f, 0.25f), false);
            Enemy(parent, mats, host, gameRoot, $"Sentinel_{tag}1", "enemy.hollow_sentinel", 3, P(c[0], z0, r1, 0.30f, -0.25f), false);
            // Sala 2
            Enemy(parent, mats, host, gameRoot, $"Hound_{tag}2", "enemy.ash_hound", 3, P(c[1], z0, r2, 0.20f, 0.20f), false);
            Enemy(parent, mats, host, gameRoot, $"Sentinel_{tag}2", "enemy.hollow_sentinel", 3, P(c[1], z0, r2, 0.25f, -0.20f), false);
            Enemy(parent, mats, host, gameRoot, $"Archer_{tag}1", "enemy.ghost_archer", 3, P(c[1], z0, r2, 0.30f, 0f), false);
            // Arena
            Enemy(parent, mats, host, gameRoot, $"Hound_{tag}3", "enemy.ash_hound", 3, P(c[2], z0, arena, -0.10f, 0.15f), false);
            Enemy(parent, mats, host, gameRoot, $"Archer_{tag}2", "enemy.ghost_archer", 3, P(c[2], z0, arena, 0.10f, -0.35f), false);
            Enemy(parent, mats, host, gameRoot, $"Guardian_{tag}", "enemy.crypt_guardian", 4, P(c[2], z0, arena, 0.25f, 0f), true);
        }

        internal static Vector3 P(float cx, float cz, float size, float fx, float fz) => new Vector3(cx + size * fx, 0f, cz + size * fz);

        internal static void Enemy(Transform parent, Mats mats, CombatSystemHost host, GameRoot gameRoot, string name, string enemyId, int level, Vector3 position, bool boss)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.position = position;
            go.transform.rotation = Quaternion.Euler(0f, -90f, 0f); // olha para o oeste, de onde o herói chega
            go.AddComponent<AttributeComponent>();
            var agent = go.AddComponent<NavMeshAgent>();
            agent.radius = 0.5f;
            agent.height = boss ? 3f : 1.8f;
            agent.acceleration = 50f;
            agent.stoppingDistance = 0f;
            agent.autoBraking = true;
            var controller = go.AddComponent<EnemyController>();
            SetRef(controller, "combatHost", host);
            SetString(controller, "enemyId", enemyId);
            SetInt(controller, "level", level);
            if (boss) SetFloat(controller, "bodyRadius", 1f);
            var presentation = go.AddComponent<PresentationController>();
            SetRef(presentation, "root", gameRoot);
            var painted = CharacterPrefabBuilder.PrefabForEnemy(enemyId);
            if (painted != null)
            {
                var visual = (GameObject)PrefabUtility.InstantiatePrefab(painted);
                visual.name = "Body";
                visual.transform.SetParent(go.transform, false);
                return;
            }
            var body = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            body.name = "Body";
            Object.DestroyImmediate(body.GetComponent<Collider>());
            body.transform.SetParent(go.transform, false);
            body.transform.localPosition = new Vector3(0f, boss ? 1.5f : 0.9f, 0f);
            body.transform.localScale = boss ? new Vector3(2f, 1.5f, 2f) : new Vector3(1f, 0.9f, 1f);
            Apply(body, boss ? mats.Boss : mats.Enemy, true);
        }

        // ------------------------------------------------------------------ assets

        internal static Mats CreateMaterials()
        {
            var tokens = ReadTokens();
            return new Mats
            {
                FloorA = LitMaterial("M_Graybox_Floor_A", Token(tokens, "pedra_media", "#2A222F")),
                FloorB = LitMaterial("M_Graybox_Floor_B", Token(tokens, "panel_hover", "#3A2F42")),
                Wall = LitMaterial("M_Graybox_Wall", Token(tokens, "pedra_clara", "#6A606E")),
                Pillar = LitMaterial("M_Graybox_Pillar", Token(tokens, "muted", "#9A8D97")),
                Crate = LitMaterial("M_Graybox_Crate", Token(tokens, "dourado", "#D9A441")),
                Hero = LitMaterial("M_Graybox_Hero", Token(tokens, "carmesim", "#B82A1E")),
                Enemy = LitMaterial("M_Graybox_Enemy", Token(tokens, "pergaminho", "#F0E6D6")),
                Boss = LitMaterial("M_Graybox_Boss", Token(tokens, "perigo", "#E0301E")),
                Checkpoint = LitMaterial("M_Graybox_Checkpoint", Token(tokens, "dourado_claro", "#FCD58A")),
                Warrior = WarriorMaterial(),
                Telegraph = TelegraphMaterial("M_Telegraph_Placeholder", new Color(0.847f, 0.263f, 0.184f, 0.4f)), // #D8432F, token telegraph.fill
            };
        }

        /// <summary>M_Warrior: SG_Character com o albedo pintado e a mascara (R emissao, G rim, B tinta) do Guerreiro aprovado.</summary>
        internal static Material WarriorMaterial()
        {
            return CharacterPrefabBuilder.EnsureMaterial("M_Warrior", WarriorBaseMap, WarriorMaskMap);
        }

        /// <summary>
        /// P_Hero_Warrior: SK_Warrior refeito em pose de repouso, com martelo e escudo nos sockets das maos (CharacterPrefabBuilder).
        /// TODO(animacao): ligar o Animator com o AC_Hero_Warrior na etapa de animacao (docs/04, secao 3.3); o avatar Humanoid ja esta ligado.
        /// </summary>
        internal static GameObject BuildWarriorPrefab(Material material)
        {
            return CharacterPrefabBuilder.BuildWarrior();
        }

        internal static string ReadTokens()
        {
            // O arquivo mora em docs/ ao lado da pasta do repositório do projeto Unity.
            var path = Path.GetFullPath(Path.Combine(Application.dataPath, "../../docs/03_design_tokens.json"));
            return File.Exists(path) ? File.ReadAllText(path) : string.Empty;
        }

        internal static Color Token(string json, string key, string fallback)
        {
            var m = Regex.Match(json, "\"" + Regex.Escape(key) + "\"\\s*:\\s*\"(#[0-9A-Fa-f]{6})\"");
            var hex = m.Success ? m.Groups[1].Value : fallback;
            return ColorUtility.TryParseHtmlString(hex, out var c) ? c : Color.magenta;
        }

        internal static Material LitMaterial(string name, Color color)
        {
            var path = $"{MaterialDir}/{name}.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                AssetDatabase.CreateAsset(mat, path);
            }
            mat.SetColor("_BaseColor", color);
            mat.SetFloat("_Smoothness", 0.1f);
            mat.SetFloat("_Metallic", 0f);
            EditorUtility.SetDirty(mat);
            return mat;
        }

        internal static Material TelegraphMaterial(string name, Color color)
        {
            var path = $"{MaterialDir}/{name}.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Unlit"));
                AssetDatabase.CreateAsset(mat, path);
            }
            mat.SetColor("_BaseColor", color);
            mat.SetFloat("_Surface", 1f);   // Transparent
            mat.SetFloat("_Blend", 0f);     // Alpha
            mat.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
            mat.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
            mat.SetFloat("_ZWrite", 0f);
            mat.SetOverrideTag("RenderType", "Transparent");
            mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            mat.renderQueue = (int)RenderQueue.Transparent;
            mat.SetShaderPassEnabled("ShadowCaster", false);
            EditorUtility.SetDirty(mat);
            return mat;
        }

        internal static GameObject CreateProjectilePrefab(Mats mats)
        {
            var path = PrefabDir + "/P_Projectile_Placeholder.prefab";
            var temp = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            temp.name = "P_Projectile_Placeholder";
            Object.DestroyImmediate(temp.GetComponent<Collider>());
            temp.transform.localScale = Vector3.one * 0.2f;
            temp.GetComponent<MeshRenderer>().sharedMaterial = mats.Boss; // TODO: VFX do projétil quando houver arte aprovada
            var prefab = PrefabUtility.SaveAsPrefabAsset(temp, path);
            Object.DestroyImmediate(temp);
            return prefab;
        }

        internal static PanelSettings CreatePanelSettings()
        {
            var themePath = UiDir + "/ShatterRuntimeTheme.tss";
            if (!File.Exists(themePath))
            {
                File.WriteAllText(themePath, "@import url(\"unity-theme://default\");\n");
                AssetDatabase.ImportAsset(themePath);
            }
            var panel = LoadOrCreate<PanelSettings>(UiDir + "/ShatterPanelSettings.asset");
            panel.scaleMode = PanelScaleMode.ScaleWithScreenSize;
            panel.referenceResolution = new Vector2Int(1920, 1080);
            panel.screenMatchMode = PanelScreenMatchMode.MatchWidthOrHeight;
            panel.match = 1f;
            var theme = AssetDatabase.LoadAssetAtPath<ThemeStyleSheet>(themePath);
            if (theme != null) panel.themeStyleSheet = theme;
            EditorUtility.SetDirty(panel);
            return panel;
        }

        internal static void AddToBuildSettings()
        {
            var list = new List<EditorBuildSettingsScene>(EditorBuildSettings.scenes);
            for (var i = 0; i < list.Count; i++)
                if (list[i].path == ScenePath) { list[i] = new EditorBuildSettingsScene(ScenePath, true); EditorBuildSettings.scenes = list.ToArray(); return; }
            list.Insert(0, new EditorBuildSettingsScene(ScenePath, true));
            EditorBuildSettings.scenes = list.ToArray();
        }

        // ------------------------------------------------------------------ utilitários

        internal static void Apply(GameObject go, Material mat, bool castShadow = false)
        {
            var mr = go.GetComponent<MeshRenderer>();
            mr.sharedMaterial = mat;
            // Docs/04, seção 3.6: só os personagens projetam sombra; o cenário só recebe.
            mr.shadowCastingMode = castShadow ? ShadowCastingMode.On : ShadowCastingMode.Off;
        }

        internal static T LoadOrCreate<T>(string path) where T : ScriptableObject
        {
            var asset = AssetDatabase.LoadAssetAtPath<T>(path);
            if (asset != null) return asset;
            asset = ScriptableObject.CreateInstance<T>();
            AssetDatabase.CreateAsset(asset, path);
            return asset;
        }

        internal static void EnsureDir(string dir)
        {
            if (AssetDatabase.IsValidFolder(dir)) return;
            var parent = Path.GetDirectoryName(dir).Replace('\\', '/');
            if (!AssetDatabase.IsValidFolder(parent)) EnsureDir(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(dir));
        }

        internal static SerializedProperty Prop(Object target, string field, out SerializedObject so)
        {
            so = new SerializedObject(target);
            var p = so.FindProperty(field);
            if (p == null) throw new InvalidOperationException($"Campo '{field}' não existe em {target.GetType().Name}.");
            return p;
        }

        internal static void SetRef(Object target, string field, Object value)
        {
            var p = Prop(target, field, out var so);
            p.objectReferenceValue = value;
            so.ApplyModifiedPropertiesWithoutUndo();
        }

        internal static void SetInt(Object target, string field, int value)
        {
            var p = Prop(target, field, out var so);
            p.intValue = value;
            so.ApplyModifiedPropertiesWithoutUndo();
        }

        internal static void SetFloat(Object target, string field, float value)
        {
            var p = Prop(target, field, out var so);
            p.floatValue = value;
            so.ApplyModifiedPropertiesWithoutUndo();
        }

        internal static void SetBool(Object target, string field, bool value)
        {
            var p = Prop(target, field, out var so);
            p.boolValue = value;
            so.ApplyModifiedPropertiesWithoutUndo();
        }

        internal static void SetString(Object target, string field, string value)
        {
            var p = Prop(target, field, out var so);
            p.stringValue = value;
            so.ApplyModifiedPropertiesWithoutUndo();
        }
    }
}
