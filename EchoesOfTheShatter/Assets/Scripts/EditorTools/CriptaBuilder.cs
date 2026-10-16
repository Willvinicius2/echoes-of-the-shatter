using System;
using System.Collections.Generic;
using System.IO;
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
using UnityEngine.UIElements;
using Object = UnityEngine.Object;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Monta a Cripta jogável da Etapa 2 (Assets/Scenes/Cripta/Cripta.unity) a partir do bloco JSON do docs/14_layout_cripta.md, na escala da
    /// zona A: 9 salas e o nicho secreto, corredores de 6 m, arena de 40 m com 8 pilares, portais, checkpoints, baús, segredo e atalho.
    /// Nenhum número do mapa mora aqui: salas, encontros, posições, pilares e raios vêm do JSON; os encontros ainda conferem com o
    /// encounters.csv (testes). Visual provisório: kit graybox aprovado (SM_Cripta_*, SM_Enemy_*) onde existir, primitivas onde faltar.
    /// Menu: Echoes ▸ Montar Cripta. Batchmode: -executeMethod Echoes.EditorTools.CriptaBuilder.BuildFromCommandLine
    /// </summary>
    public static class CriptaBuilder
    {
        public const string ScenePath = "Assets/Scenes/Cripta/Cripta.unity";
        const string KitDir = "Assets/Art/Environment/Cripta/Graybox";
        const string GeneratedDir = "Assets/Art/Generated/Cripta";
        const string KitSourceRelative = "art-src/graybox/fbx";

        static readonly string[] KitFiles =
        {
            "SM_Cripta_Pillar_A.fbx", "SM_Cripta_Wall_2m_A.fbx", "SM_Cripta_Brazier_A.fbx", "SM_Cripta_Sarcophagus_A.fbx",
            "SM_Enemy_HollowSentinel.fbx", "SM_Enemy_AshHound.fbx", "SM_Enemy_StoneHerald.fbx", "SM_Enemy_GhostArcher.fbx",
            "SM_Boss_CryptGuardian.fbx", "T_Graybox_Palette_BC.png", "T_Graybox_Palette_E.png",
        };

        static readonly Dictionary<string, string> EnemyModels = new Dictionary<string, string>
        {
            { "enemy.hollow_sentinel", "SM_Enemy_HollowSentinel.fbx" },
            { "enemy.shielded_sentinel", "SM_Enemy_HollowSentinel.fbx" },
            { "enemy.ash_hound", "SM_Enemy_AshHound.fbx" },
            { "enemy.swift_ash_hound", "SM_Enemy_AshHound.fbx" },
            { "enemy.stone_herald", "SM_Enemy_StoneHerald.fbx" },
            { "enemy.ghost_archer", "SM_Enemy_GhostArcher.fbx" },
            { "enemy.crypt_guardian", "SM_Boss_CryptGuardian.fbx" },
        };

        sealed class Context
        {
            public CriptaLayout Layout;
            public SandboxBuilder.Mats Mats;
            public Material Palette;
            public int MonsterLevel;
            public GameRoot GameRoot;
            public CombatSystemHost Host;
            public HeroController Hero;
            public Transform Interactives;
            public Camera Camera;
            public readonly List<EnemyController> Enemies = new List<EnemyController>();
        }

        [MenuItem("Echoes/Montar Cripta")]
        public static void Build()
        {
            BuildScene();
            Debug.Log($"[CriptaBuilder] Cena salva em {ScenePath}");
        }

        /// <summary>Para -executeMethod: sai com codigo 1 se algo falhar.</summary>
        public static void BuildFromCommandLine()
        {
            try
            {
                BuildScene();
                Debug.Log($"[CriptaBuilder] Cena salva em {ScenePath}");
                if (Application.isBatchMode) EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Debug.LogError("[CriptaBuilder] Falhou: " + e);
                if (Application.isBatchMode) EditorApplication.Exit(1);
            }
        }

        public static void BuildScene()
        {
            var layout = CriptaLayout.LoadFromDocument();
            SandboxBuilder.EnsureDir(SandboxBuilder.DataDir);
            SandboxBuilder.EnsureDir(SandboxBuilder.MaterialDir);
            SandboxBuilder.EnsureDir(SandboxBuilder.PrefabDir);
            SandboxBuilder.EnsureDir(SandboxBuilder.UiDir);
            SandboxBuilder.EnsureDir(GeneratedDir);
            SandboxBuilder.EnsureDir(Path.GetDirectoryName(ScenePath).Replace('\\', '/'));
            CopyKit();

            var renderSettings = SandboxBuilder.LoadOrCreate<RenderSettingsAsset>(SandboxBuilder.DataDir + "/SO_RenderSettings.asset");
            var feel = SandboxBuilder.LoadOrCreate<CombatFeelSettings>(SandboxBuilder.DataDir + "/SO_CombatFeel.asset");
            var panel = SandboxBuilder.CreatePanelSettings();
            var mats = SandboxBuilder.CreateMaterials();
            var projectile = SandboxBuilder.CreateProjectilePrefab(mats);
            var inputActions = AssetDatabase.LoadAssetAtPath<InputActionAsset>("Assets/Settings/Echoes.inputactions");
            var hudUxml = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(SandboxBuilder.UiDir + "/Views/HudView.uxml");
            if (inputActions == null) throw new InvalidOperationException("Assets/Settings/Echoes.inputactions nao encontrado.");
            if (hudUxml == null) throw new InvalidOperationException("Assets/UI/Views/HudView.uxml nao encontrado.");

            var ctx = new Context { Layout = layout, Mats = mats, Palette = CreatePaletteMaterial(), MonsterLevel = ReadMonsterLevel(layout.MapId) };

            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
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

            // ---- Nivel: so a geometria andavel e as paredes entram no NavMesh
            var level = new GameObject("Level").transform;
            BuildGeometry(ctx, level);

            // ---- Sistemas, heroi, camera, HUD
            BuildSystems(ctx, feel, projectile);
            ctx.Interactives = new GameObject("Interactives").transform;
            var hero = BuildHero(ctx, renderSettings, inputActions);
            BuildHud(ctx, panel, hudUxml);

            // ---- Interativos (checkpoints, portais, baus, segredo, atalho, arena)
            var arena = BuildInteractives(ctx);

            // ---- NavMesh (so o Level), depois os inimigos para os agentes nascerem sobre ele
            var surface = level.gameObject.AddComponent<NavMeshSurface>();
            surface.collectObjects = CollectObjects.Children;
            surface.useGeometry = NavMeshCollectGeometry.RenderMeshes;
            surface.BuildNavMesh();
            if (surface.navMeshData != null)
            {
                var navPath = GeneratedDir + "/NavMesh_Cripta.asset";
                if (AssetDatabase.LoadAssetAtPath<Object>(navPath) != null) AssetDatabase.DeleteAsset(navPath);
                AssetDatabase.CreateAsset(surface.navMeshData, navPath);
            }

            var enemies = new GameObject("Enemies").transform;
            SpawnEncounters(ctx, enemies, arena);

            var director = new GameObject("EncounterDirector").AddComponent<EncounterDirector>();
            SandboxBuilder.SetRef(director, "hero", hero);
            SandboxBuilder.SetRef(director, "arena", arena);
            SetObjectArray(director, "enemies", ctx.Enemies);
            if (arena != null) SetBossOf(arena, ctx);

            EditorSceneManager.SaveScene(scene, ScenePath);
            AddToBuildSettings();
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
        }

        // ============================================================================================== geometria

        static void BuildGeometry(Context ctx, Transform level)
        {
            var layout = ctx.Layout;
            var rooms = new GameObject("Rooms").transform; rooms.SetParent(level, false);
            var corridors = new GameObject("Corridors").transform; corridors.SetParent(level, false);
            var walls = new GameObject("Walls").transform; walls.SetParent(level, false);
            var pillars = new GameObject("Pillars").transform; pillars.SetParent(level, false);
            var floorRects = new List<Rect>();

            foreach (var room in layout.Rooms)
            {
                floorRects.Add(room.Rect);
                var go = new GameObject(room.Id);
                go.transform.SetParent(rooms, false);
                AddFloorCollider(go.transform, room.Rect);
            }
            foreach (var corridor in layout.Corridors)
            {
                floorRects.Add(corridor.Rect);
                var go = new GameObject(corridor.Id);
                go.transform.SetParent(corridors, false);
                AddFloorCollider(go.transform, corridor.Rect);
            }

            // Piso xadrez de 2 m (kit graybox de piso entra com o cenario pintado).
            var meshA = SandboxBuilder.SaveMesh(SandboxBuilder.BuildCheckerMesh(floorRects, 0), GeneratedDir + "/Cripta_FloorA.asset");
            var meshB = SandboxBuilder.SaveMesh(SandboxBuilder.BuildCheckerMesh(floorRects, 1), GeneratedDir + "/Cripta_FloorB.asset");
            SandboxBuilder.AddFloorVisual(level, "Floor_A", meshA, ctx.Mats.FloorA);
            SandboxBuilder.AddFloorVisual(level, "Floor_B", meshB, ctx.Mats.FloorB);

            foreach (var room in layout.Rooms) BuildRoomWalls(ctx, walls, room);
            foreach (var corridor in layout.Corridors) BuildCorridorWalls(ctx, walls, corridor);

            foreach (var pillar in layout.Pillars) BuildPillar(ctx, pillars, pillar);

            // Vistas nao caminhaveis (abismo, colunata, portao): bloco escuro com colisor, o cenario pintado troca depois.
            foreach (var vista in layout.Vistas)
            {
                var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
                go.name = vista.Id;
                go.transform.SetParent(level, false);
                go.transform.position = new Vector3(vista.Rect.center.x, 1.5f, vista.Rect.center.y);
                go.transform.localScale = new Vector3(vista.Rect.width, 3f, vista.Rect.height);
                SandboxBuilder.Apply(go, ctx.Mats.Pillar);
            }
        }

        static void AddFloorCollider(Transform parent, Rect r)
        {
            var box = parent.gameObject.AddComponent<BoxCollider>();
            box.center = new Vector3(r.center.x, -0.1f, r.center.y);
            box.size = new Vector3(r.width, 0.2f, r.height);
        }

        // Paredes: o perimetro de cada sala com vaos onde um corredor (ou o segredo) encosta; os corredores ganham as paredes laterais.
        static void BuildRoomWalls(Context ctx, Transform parent, CriptaLayout.RoomData room)
        {
            var r = room.Rect;
            var layout = ctx.Layout;
            const float eps = 0.01f;
            for (var side = 0; side < 4; side++)
            {
                // side: 0 sul (z = zMin, ao longo de X), 1 norte, 2 oeste (x = xMin, ao longo de Z), 3 leste
                var alongX = side < 2;
                var line = side == 0 ? r.yMin : side == 1 ? r.yMax : side == 2 ? r.xMin : r.xMax;
                var a = alongX ? r.xMin : r.yMin;
                var b = alongX ? r.xMax : r.yMax;
                var openings = new List<Vector2>();
                foreach (var c in layout.Corridors)
                {
                    var cr = c.Rect;
                    bool touches;
                    Vector2 span;
                    switch (side)
                    {
                        case 0: touches = Mathf.Abs(cr.yMax - line) < eps; span = new Vector2(cr.xMin, cr.xMax); break;
                        case 1: touches = Mathf.Abs(cr.yMin - line) < eps; span = new Vector2(cr.xMin, cr.xMax); break;
                        case 2: touches = Mathf.Abs(cr.xMax - line) < eps; span = new Vector2(cr.yMin, cr.yMax); break;
                        default: touches = Mathf.Abs(cr.xMin - line) < eps; span = new Vector2(cr.yMin, cr.yMax); break;
                    }
                    if (touches && span.y > a && span.x < b) openings.Add(span);
                }
                foreach (var s in layout.Secrets)
                {
                    // Parede rachada: vao no lado sul/norte onde o retangulo do segredo atravessa a linha.
                    if (!alongX) continue;
                    if (line >= s.Rect.yMin - eps && line <= s.Rect.yMax + eps && s.Rect.xMin >= a && s.Rect.xMax <= b) openings.Add(new Vector2(s.Rect.xMin, s.Rect.xMax));
                }
                openings.Sort((p, q) => p.x.CompareTo(q.x));
                var cursor = a;
                foreach (var o in openings)
                {
                    if (o.x > cursor + eps) WallRun(ctx, parent, room.Id, alongX, line, cursor, o.x, side == 1 || side == 3, cursor == a, false);
                    cursor = Mathf.Max(cursor, o.y);
                }
                if (b > cursor + eps) WallRun(ctx, parent, room.Id, alongX, line, cursor, b, side == 1 || side == 3, cursor == a, true);
            }
        }

        static void BuildCorridorWalls(Context ctx, Transform parent, CriptaLayout.CorridorData c)
        {
            var r = c.Rect;
            if (c.AlongX)
            {
                WallRun(ctx, parent, c.Id, true, r.yMin, r.xMin, r.xMax, false, false, false);
                WallRun(ctx, parent, c.Id, true, r.yMax, r.xMin, r.xMax, true, false, false);
            }
            else
            {
                WallRun(ctx, parent, c.Id, false, r.xMin, r.yMin, r.yMax, false, false, false);
                WallRun(ctx, parent, c.Id, false, r.xMax, r.yMin, r.yMax, true, false, false);
            }
        }

        // Um trecho reto de parede entre from e to (ao longo do eixo), deslocado para FORA do chao jogavel. extendStart/End cobrem o canto.
        static void WallRun(Context ctx, Transform parent, string owner, bool alongX, float line, float from, float to, bool positiveOutside, bool extendStart, bool extendEnd)
        {
            var t = SandboxBuilder.WallThickness;
            if (extendStart) from -= t;
            if (extendEnd) to += t;
            var length = to - from;
            if (length < 0.1f) return;
            var module = ModuleLength();
            var n = Mathf.Max(1, Mathf.RoundToInt(length / module));
            var tile = length / n;
            for (var i = 0; i < n; i++)
            {
                var center = from + tile * (i + 0.5f);
                var outside = (positiveOutside ? 1f : -1f) * t * 0.5f;
                var position = alongX ? new Vector3(center, 0f, line + outside) : new Vector3(line + outside, 0f, center);
                PlaceWallTile(ctx, parent, $"{owner}_wall", position, alongX, tile);
            }
        }

        static float cachedModule;

        static float ModuleLength()
        {
            if (cachedModule > 0f) return cachedModule;
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(KitDir + "/SM_Cripta_Wall_2m_A.fbx");
            cachedModule = 2f;
            if (model != null)
            {
                var bounds = RenderBounds(model);
                if (bounds.size.x > 0.1f) cachedModule = bounds.size.x;
            }
            return cachedModule;
        }

        static void PlaceWallTile(Context ctx, Transform parent, string name, Vector3 center, bool alongX, float tileLength)
        {
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(KitDir + "/SM_Cripta_Wall_2m_A.fbx");
            GameObject go;
            if (model != null)
            {
                go = (GameObject)PrefabUtility.InstantiatePrefab(model);
                go.name = name;
                go.transform.SetParent(parent, false);
                go.transform.rotation = alongX ? Quaternion.identity : Quaternion.Euler(0f, 90f, 0f);
                var native = RenderBounds(go).size;
                var scaleLength = native.x > 0.01f ? tileLength / (alongX ? native.x : native.z) : 1f;
                go.transform.localScale = new Vector3(scaleLength, 1f, 1f);
                // Escala so no comprimento do trecho: aplica no eixo local X (o comprimento do modulo).
                var bounds = RenderBounds(go);
                go.transform.position += new Vector3(center.x - bounds.center.x, -bounds.min.y, center.z - bounds.center.z);
                ApplyPalette(go, ctx.Palette, false);
            }
            else
            {
                go = GameObject.CreatePrimitive(PrimitiveType.Cube);
                go.name = name;
                go.transform.SetParent(parent, false);
                go.transform.position = new Vector3(center.x, SandboxBuilder.WallHeight / 2f, center.z);
                go.transform.localScale = alongX
                    ? new Vector3(tileLength, SandboxBuilder.WallHeight, SandboxBuilder.WallThickness)
                    : new Vector3(SandboxBuilder.WallThickness, SandboxBuilder.WallHeight, tileLength);
                SandboxBuilder.Apply(go, ctx.Mats.Wall);
            }
            AddWallCollider(go, alongX, tileLength);
        }

        // Colisor simples (04 secao 17.1): nunca o mesh visual.
        static void AddWallCollider(GameObject go, bool alongX, float length)
        {
            foreach (var c in go.GetComponentsInChildren<Collider>()) Object.DestroyImmediate(c);
            var bounds = RenderBounds(go);
            var box = go.AddComponent<BoxCollider>();
            box.center = go.transform.InverseTransformPoint(bounds.center);
            var size = bounds.size;
            box.size = new Vector3(size.x / Mathf.Max(0.0001f, go.transform.lossyScale.x), size.y / Mathf.Max(0.0001f, go.transform.lossyScale.y), size.z / Mathf.Max(0.0001f, go.transform.lossyScale.z));
        }

        static void BuildPillar(Context ctx, Transform parent, CriptaLayout.PillarData p)
        {
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(KitDir + "/SM_Cripta_Pillar_A.fbx");
            GameObject go;
            if (model != null)
            {
                go = (GameObject)PrefabUtility.InstantiatePrefab(model);
                go.name = p.Id;
                go.transform.SetParent(parent, false);
                var native = RenderBounds(go).size;
                go.transform.localScale = new Vector3(2f * p.Radius / Mathf.Max(0.01f, native.x), p.Height / Mathf.Max(0.01f, native.y), 2f * p.Radius / Mathf.Max(0.01f, native.z));
                var bounds = RenderBounds(go);
                go.transform.position += new Vector3(p.Pos.x - bounds.center.x, -bounds.min.y, p.Pos.y - bounds.center.z);
                ApplyPalette(go, ctx.Palette, false);
                foreach (var c in go.GetComponentsInChildren<Collider>()) Object.DestroyImmediate(c);
            }
            else
            {
                go = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                go.name = p.Id;
                go.transform.SetParent(parent, false);
                go.transform.position = new Vector3(p.Pos.x, p.Height / 2f, p.Pos.y);
                go.transform.localScale = new Vector3(2f * p.Radius, p.Height / 2f, 2f * p.Radius);
                SandboxBuilder.Apply(go, ctx.Mats.Pillar);
                Object.DestroyImmediate(go.GetComponent<Collider>());
            }
            var capsule = go.AddComponent<CapsuleCollider>(); // colisor solido simples, no mundo
            capsule.radius = p.Radius / Mathf.Max(0.0001f, go.transform.lossyScale.x);
            capsule.height = p.Height / Mathf.Max(0.0001f, go.transform.lossyScale.y);
            capsule.center = go.transform.InverseTransformPoint(new Vector3(p.Pos.x, p.Height / 2f, p.Pos.y));
        }

        // ============================================================================================== sistemas

        static void BuildSystems(Context ctx, CombatFeelSettings feel, GameObject projectile)
        {
            var gameRoot = new GameObject("GameRoot").AddComponent<GameRoot>();
            var combatGo = new GameObject("Combat");
            var host = combatGo.AddComponent<CombatSystemHost>();
            SandboxBuilder.SetRef(host, "root", gameRoot);
            SandboxBuilder.SetRef(host, "feel", feel);
            SandboxBuilder.SetInt(host, "maxStepsPerFrame", 8);

            var presentationGo = new GameObject("Presentation");
            presentationGo.AddComponent<VfxPool>();
            var telegraph = presentationGo.AddComponent<TelegraphPresenter>();
            SandboxBuilder.SetRef(telegraph, "root", gameRoot);
            SandboxBuilder.SetRef(telegraph, "fallbackMaterial", ctx.Mats.Telegraph);
            var projectiles = presentationGo.AddComponent<ProjectilePresenter>();
            SandboxBuilder.SetRef(projectiles, "root", gameRoot);
            SandboxBuilder.SetRef(projectiles, "combatHost", host);
            SandboxBuilder.SetRef(projectiles, "prefab", projectile);
            SandboxBuilder.SetFloat(projectiles, "height", 1f);
            ctx.GameRoot = gameRoot;
            ctx.Host = host;
        }

        static HeroController BuildHero(Context ctx, RenderSettingsAsset renderSettings, InputActionAsset inputActions)
        {
            var layout = ctx.Layout;
            var spawn = new Vector3(layout.HeroSpawn.x, 0f, layout.HeroSpawn.y);

            var camGo = new GameObject("Main Camera") { tag = "MainCamera" };
            var cam = camGo.AddComponent<Camera>();
            camGo.AddComponent<AudioListener>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.059f, 0.043f, 0.078f);
            ctx.Camera = cam;

            var hero = new GameObject("Hero");
            hero.transform.position = spawn;
            hero.transform.rotation = Quaternion.identity; // olha para +Z (docs/14: o heroi entra olhando para o norte)
            var cc = hero.AddComponent<CharacterController>();
            cc.radius = 0.3f; cc.height = SandboxBuilder.HeroHeight; cc.center = new Vector3(0f, 0.75f, 0f);
            cc.slopeLimit = 45f; cc.stepOffset = 0.3f;
            hero.AddComponent<AttributeComponent>();
            var heroController = hero.AddComponent<HeroController>();
            var inputHandler = hero.AddComponent<PlayerInputHandler>();
            SandboxBuilder.SetRef(inputHandler, "actions", inputActions);
            SandboxBuilder.SetBool(inputHandler, "loadSavedBindings", true);
            var presentation = hero.AddComponent<PresentationController>();
            SandboxBuilder.SetRef(presentation, "root", ctx.GameRoot);
            SandboxBuilder.SetRef(heroController, "combatHost", ctx.Host);
            SandboxBuilder.SetRef(heroController, "input", inputHandler);
            SandboxBuilder.SetRef(heroController, "aimCamera", cam);
            SandboxBuilder.SetFloat(heroController, "respawnDelay", 1.5f);

            var heroPrefab = SandboxBuilder.BuildWarriorPrefab(ctx.Mats.Warrior);
            var visual = (GameObject)PrefabUtility.InstantiatePrefab(heroPrefab);
            visual.name = "Body";
            visual.transform.SetParent(hero.transform, false);

            var rig = new GameObject("CameraRig");
            rig.transform.position = hero.transform.position + new Vector3(0f, 0.52f, 0f);
            camGo.transform.SetParent(rig.transform, false);
            var follow = rig.AddComponent<FollowCamera>();
            SandboxBuilder.SetRef(follow, "target", hero.transform);
            SandboxBuilder.SetRef(follow, "viewCamera", cam);
            SandboxBuilder.SetRef(follow, "settings", renderSettings);
            SandboxBuilder.SetRef(follow, "root", ctx.GameRoot);
            SandboxBuilder.SetBool(follow, "shakeEnabled", true);
            follow.ApplySettings();

            ctx.Hero = heroController;
            return heroController;
        }

        static void BuildHud(Context ctx, PanelSettings panel, VisualTreeAsset hudUxml)
        {
            var hud = new GameObject("HUD");
            var uiDoc = hud.AddComponent<UIDocument>();
            uiDoc.panelSettings = panel;
            uiDoc.visualTreeAsset = hudUxml;
            var hudView = hud.AddComponent<HudView>();
            SandboxBuilder.SetRef(hudView, "root", ctx.GameRoot);
            SandboxBuilder.SetRef(hudView, "hero", ctx.Hero);
            SandboxBuilder.SetRef(hudView, "worldCamera", ctx.Camera);
        }

        // ============================================================================================== interativos

        static ArenaController BuildInteractives(Context ctx)
        {
            var layout = ctx.Layout;
            var root = ctx.Interactives;
            Transform firstCheckpoint = null;

            foreach (var cp in layout.Checkpoints)
            {
                var go = Marker(root, cp.Id, cp.Pos, ctx.Mats.Checkpoint, 1.2f);
                var zone = go.AddComponent<CheckpointZone>();
                SandboxBuilder.SetRef(zone, "hero", ctx.Hero);
                SandboxBuilder.SetString(zone, "checkpointId", cp.Id);
                if (firstCheckpoint == null) firstCheckpoint = go.transform;
                AddBrazier(ctx, go.transform);
            }
            if (firstCheckpoint != null) SandboxBuilder.SetRef(ctx.Hero, "checkpoint", firstCheckpoint);

            var victory = new List<GameObject>();
            foreach (var portal in layout.Portals)
            {
                var go = Marker(root, portal.Id, portal.Pos, ctx.Mats.Boss, 2.4f);
                var zone = go.AddComponent<PortalZone>();
                SandboxBuilder.SetRef(zone, "combatHost", ctx.Host);
                SandboxBuilder.SetRef(zone, "hero", ctx.Hero);
                SandboxBuilder.SetString(zone, "portalId", portal.Id);
                SandboxBuilder.SetString(zone, "targetArea", portal.Target);
                if (portal.Active != "always") victory.Add(go);
            }
            foreach (var marker in layout.Markers)
            {
                var go = Marker(root, marker.Id, marker.Pos, ctx.Mats.Checkpoint, 1.6f);
                if (marker.Active != "always") victory.Add(go);
            }
            foreach (var chest in layout.Chests) BuildChest(ctx, root, chest);

            GateBarrier shortcutGate = null;
            GateBarrier arenaGate = null;
            foreach (var gate in layout.Gates)
            {
                var closedAtStart = string.IsNullOrEmpty(gate.ClosesOn); // atalho: fechado; porta da arena: aberta ate o gatilho
                var barrier = BuildGate(ctx, root, gate, closedAtStart);
                if (!string.IsNullOrEmpty(gate.OpensFrom))
                {
                    shortcutGate = barrier;
                    var room = layout.Room(gate.OpensFrom);
                    var lever = new GameObject("lever." + gate.Id);
                    lever.transform.SetParent(root, false);
                    // Do lado da sala de origem do atalho (a sala que abre): 3 m para dentro dela a partir do portao.
                    lever.transform.position = new Vector3(gate.Pos.x, 0f, room != null && gate.Pos.y <= room.Rect.yMin + 0.5f ? gate.Pos.y + 3f : gate.Pos.y - 3f);
                    var l = lever.AddComponent<ShortcutLever>();
                    SandboxBuilder.SetRef(l, "hero", ctx.Hero);
                    SandboxBuilder.SetRef(l, "gate", barrier);
                    var visual = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                    visual.name = "LeverMarker";
                    Object.DestroyImmediate(visual.GetComponent<Collider>());
                    visual.transform.SetParent(lever.transform, false);
                    visual.transform.localScale = new Vector3(0.6f, 0.9f, 0.6f);
                    visual.transform.localPosition = new Vector3(0f, 0.9f, 0f);
                    SandboxBuilder.Apply(visual, ctx.Mats.Crate);
                }
                else
                {
                    arenaGate = barrier;
                }
            }
            foreach (var secret in layout.Secrets) BuildSecret(ctx, root, secret);

            // Arena do Guardiao
            var arenaEncounter = layout.Encounters.Find(e => e.IsBoss);
            ArenaController arena = null;
            if (arenaEncounter != null)
            {
                var spawn = new GameObject("spawn.crypt.arena").transform;
                spawn.SetParent(root, false);
                spawn.position = new Vector3(arenaEncounter.Respawn.x, 0f, arenaEncounter.Respawn.y);
                spawn.rotation = Quaternion.identity;
                var arenaGo = new GameObject("ArenaController");
                arenaGo.transform.SetParent(root, false);
                arena = arenaGo.AddComponent<ArenaController>();
                SandboxBuilder.SetRef(arena, "combatHost", ctx.Host);
                SandboxBuilder.SetRef(arena, "hero", ctx.Hero);
                SandboxBuilder.SetRef(arena, "gate", arenaGate);
                SandboxBuilder.SetRef(arena, "arenaSpawn", spawn);
                SetRect(arena, "trigger", arenaEncounter.Trigger);
                SetObjectArray(arena, "revealOnVictory", victory);
                foreach (var go in victory) go.SetActive(false);
            }
            return arena;
        }

        static GameObject Marker(Transform parent, string id, Vector2 pos, Material mat, float diameter)
        {
            var go = new GameObject(id);
            go.transform.SetParent(parent, false);
            go.transform.position = new Vector3(pos.x, 0f, pos.y);
            var disc = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            disc.name = "Disc";
            Object.DestroyImmediate(disc.GetComponent<Collider>());
            disc.transform.SetParent(go.transform, false);
            disc.transform.localScale = new Vector3(diameter, 0.02f, diameter);
            disc.transform.localPosition = new Vector3(0f, 0.03f, 0f);
            SandboxBuilder.Apply(disc, mat);
            return go;
        }

        static void AddBrazier(Context ctx, Transform parent)
        {
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(KitDir + "/SM_Cripta_Brazier_A.fbx");
            if (model == null) return;
            var go = (GameObject)PrefabUtility.InstantiatePrefab(model);
            go.name = "Brazier";
            go.transform.SetParent(parent, false);
            go.transform.localPosition = new Vector3(1.8f, 0f, 0f);
            foreach (var c in go.GetComponentsInChildren<Collider>()) Object.DestroyImmediate(c);
            ApplyPalette(go, ctx.Palette, false);
        }

        static void BuildChest(Context ctx, Transform parent, CriptaLayout.PointData chest)
        {
            var go = new GameObject(chest.Id);
            go.transform.SetParent(parent, false);
            go.transform.position = new Vector3(chest.Pos.x, 0f, chest.Pos.y);
            var closed = GameObject.CreatePrimitive(PrimitiveType.Cube);
            closed.name = "Closed";
            Object.DestroyImmediate(closed.GetComponent<Collider>());
            closed.transform.SetParent(go.transform, false);
            closed.transform.localScale = new Vector3(1.2f, 0.8f, 0.8f);
            closed.transform.localPosition = new Vector3(0f, 0.4f, 0f);
            SandboxBuilder.Apply(closed, ctx.Mats.Crate);
            var opened = GameObject.CreatePrimitive(PrimitiveType.Cube);
            opened.name = "Opened";
            Object.DestroyImmediate(opened.GetComponent<Collider>());
            opened.transform.SetParent(go.transform, false);
            opened.transform.localScale = new Vector3(1.2f, 0.3f, 0.8f);
            opened.transform.localPosition = new Vector3(0f, 0.15f, 0f);
            SandboxBuilder.Apply(opened, ctx.Mats.Pillar);
            var pickup = go.AddComponent<ChestPickup>();
            SandboxBuilder.SetRef(pickup, "combatHost", ctx.Host);
            SandboxBuilder.SetRef(pickup, "hero", ctx.Hero);
            SandboxBuilder.SetString(pickup, "chestId", chest.Id);
            SandboxBuilder.SetString(pickup, "lootTableId", chest.LootTable);
            SandboxBuilder.SetRef(pickup, "closedVisual", closed);
            SandboxBuilder.SetRef(pickup, "openedVisual", opened);
        }

        static GateBarrier BuildGate(Context ctx, Transform parent, CriptaLayout.GateData gate, bool closedAtStart)
        {
            var go = new GameObject(gate.Id);
            go.transform.SetParent(parent, false);
            go.transform.position = new Vector3(gate.Pos.x, 0f, gate.Pos.y);
            var visual = GameObject.CreatePrimitive(PrimitiveType.Cube);
            visual.name = "Grid";
            Object.DestroyImmediate(visual.GetComponent<Collider>());
            visual.transform.SetParent(go.transform, false);
            visual.transform.localScale = new Vector3(gate.Width, SandboxBuilder.WallHeight, 0.5f);
            visual.transform.localPosition = new Vector3(0f, SandboxBuilder.WallHeight / 2f, 0f);
            SandboxBuilder.Apply(visual, ctx.Mats.Wall);
            var collider = go.AddComponent<BoxCollider>();
            collider.center = new Vector3(0f, SandboxBuilder.WallHeight / 2f, 0f);
            collider.size = new Vector3(gate.Width, SandboxBuilder.WallHeight, 0.5f);
            var obstacle = go.AddComponent<NavMeshObstacle>();
            obstacle.shape = NavMeshObstacleShape.Box;
            obstacle.center = collider.center;
            obstacle.size = collider.size;
            obstacle.carving = true;
            var barrier = go.AddComponent<GateBarrier>();
            SandboxBuilder.SetRef(barrier, "blocker", collider);
            SetObjectArray(barrier, "visuals", new List<Renderer> { visual.GetComponent<Renderer>() });
            SandboxBuilder.SetRef(barrier, "obstacle", obstacle);
            SandboxBuilder.SetBool(barrier, "startClosed", closedAtStart);
            collider.enabled = closedAtStart;
            visual.GetComponent<Renderer>().enabled = closedAtStart;
            obstacle.enabled = closedAtStart;
            return barrier;
        }

        static void BuildSecret(Context ctx, Transform parent, CriptaLayout.SecretData secret)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = secret.Id;
            go.transform.SetParent(parent, false);
            var width = secret.Rect.width;
            go.transform.position = new Vector3(secret.Rect.center.x, SandboxBuilder.WallHeight / 2f, secret.Rect.center.y);
            go.transform.localScale = new Vector3(width, SandboxBuilder.WallHeight, SandboxBuilder.WallThickness);
            SandboxBuilder.Apply(go, ctx.Mats.Crate); // dourado: a "rachadura clara" do roteiro de arte
            var wall = go.AddComponent<SecretWall>();
            SandboxBuilder.SetRef(wall, "combatHost", ctx.Host);
            SandboxBuilder.SetRef(wall, "hero", ctx.Hero);
            SandboxBuilder.SetString(wall, "secretId", secret.Id);
            SetStringArray(wall, "opensWithSkillIds", secret.OpensWith);
        }

        // ============================================================================================== encontros

        static void SpawnEncounters(Context ctx, Transform parent, ArenaController arena)
        {
            var layout = ctx.Layout;
            foreach (var encounter in layout.Encounters)
            {
                var group = new GameObject(encounter.Id).transform;
                group.SetParent(parent, false);
                foreach (var g in encounter.Groups)
                {
                    var count = Mathf.Min(g.Max, g.Slots.Count); // os n primeiros espacos (docs/14 secao 4); o maximo do CSV
                    for (var i = 0; i < count; i++)
                    {
                        var controller = SpawnEnemy(ctx, group, encounter, g, i);
                        ctx.Enemies.Add(controller);
                    }
                }
            }
        }

        static EnemyController SpawnEnemy(Context ctx, Transform parent, CriptaLayout.EncounterData encounter, CriptaLayout.GroupData g, int index)
        {
            var slot = g.Slots[index];
            var boss = g.EnemyId == "enemy.crypt_guardian";
            var go = new GameObject($"{g.EnemyId.Substring(g.EnemyId.LastIndexOf('.') + 1)}_{index + 1}");
            go.transform.SetParent(parent, false);
            go.transform.position = new Vector3(slot.x, 0f, slot.y);
            go.transform.rotation = FacingFor(ctx.Layout, g, slot);
            go.AddComponent<AttributeComponent>();
            var agent = go.AddComponent<NavMeshAgent>();
            agent.radius = 0.5f;
            agent.height = boss ? 3f : 1.8f;
            agent.acceleration = 50f;
            agent.stoppingDistance = 0f;
            agent.autoBraking = true;
            var controller = go.AddComponent<EnemyController>();
            SandboxBuilder.SetRef(controller, "combatHost", ctx.Host);
            SandboxBuilder.SetString(controller, "enemyId", g.EnemyId);
            SandboxBuilder.SetInt(controller, "level", ctx.MonsterLevel);
            if (boss)
            {
                SandboxBuilder.SetFloat(controller, "bodyRadius", 1f);
                SandboxBuilder.SetBool(controller, "startDormant", true); // so acorda no gatilho da arena
            }
            if (g.RequireOnScreen) SandboxBuilder.SetBool(controller, "requireOnScreen", true);
            if (g.Patrol.Count > 1)
            {
                var points = new List<Vector3>();
                foreach (var p in g.Patrol) points.Add(new Vector3(p.x, 0f, p.y));
                SetVector3Array(controller, "patrolPoints", points);
            }
            var presentation = go.AddComponent<PresentationController>();
            SandboxBuilder.SetRef(presentation, "root", ctx.GameRoot);
            BuildEnemyVisual(ctx, go.transform, g.EnemyId, boss);
            return controller;
        }

        static Quaternion FacingFor(CriptaLayout layout, CriptaLayout.GroupData g, Vector2 slot)
        {
            if (g.Facing == "-z") return Quaternion.Euler(0f, 180f, 0f);
            if (g.Facing == "+z") return Quaternion.identity;
            // Olha para o ponto da rota mais proximo (de onde o heroi chega).
            var best = Vector2.zero;
            var bestDistance = float.MaxValue;
            for (var i = 0; i + 1 < layout.Route.Count; i++)
            {
                var a = layout.Route[i];
                var b = layout.Route[i + 1];
                var ab = b - a;
                var t = ab.sqrMagnitude > 0f ? Mathf.Clamp01(Vector2.Dot(slot - a, ab) / ab.sqrMagnitude) : 0f;
                var p = a + ab * t;
                var d = (p - slot).sqrMagnitude;
                if (d < bestDistance) { bestDistance = d; best = p; }
            }
            var dir = best - slot;
            return dir.sqrMagnitude < 0.01f ? Quaternion.identity : Quaternion.LookRotation(new Vector3(dir.x, 0f, dir.y));
        }

        static void BuildEnemyVisual(Context ctx, Transform parent, string enemyId, bool boss)
        {
            GameObject model = null;
            if (EnemyModels.TryGetValue(enemyId, out var file)) model = AssetDatabase.LoadAssetAtPath<GameObject>(KitDir + "/" + file);
            if (model != null)
            {
                var visual = (GameObject)PrefabUtility.InstantiatePrefab(model);
                visual.name = "Body";
                visual.transform.SetParent(parent, false);
                foreach (var c in visual.GetComponentsInChildren<Collider>()) Object.DestroyImmediate(c);
                ApplyPalette(visual, ctx.Palette, true);
                return;
            }
            var body = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            body.name = "Body";
            Object.DestroyImmediate(body.GetComponent<Collider>());
            body.transform.SetParent(parent, false);
            body.transform.localPosition = new Vector3(0f, boss ? 1.5f : 0.9f, 0f);
            body.transform.localScale = boss ? new Vector3(2f, 1.5f, 2f) : new Vector3(1f, 0.9f, 1f);
            SandboxBuilder.Apply(body, boss ? ctx.Mats.Boss : ctx.Mats.Enemy, true);
        }

        static void SetBossOf(ArenaController arena, Context ctx)
        {
            var boss = ctx.Enemies.Find(e => e.EnemyId == "enemy.crypt_guardian");
            if (boss != null) SandboxBuilder.SetRef(arena, "boss", boss);
        }

        // ============================================================================================== assets e utilitarios

        static void CopyKit()
        {
            SandboxBuilder.EnsureDir(KitDir);
            var repoRoot = Path.GetFullPath(Path.Combine(Application.dataPath, "../.."));
            var changed = false;
            foreach (var file in KitFiles)
            {
                var target = KitDir + "/" + file;
                if (File.Exists(target)) continue;
                var source = Path.Combine(repoRoot, KitSourceRelative, file);
                if (!File.Exists(source))
                {
                    Debug.LogWarning("[CriptaBuilder] Peca do kit graybox ausente (usa primitiva): " + source);
                    continue;
                }
                File.Copy(source, target, false);
                changed = true;
            }
            if (changed) AssetDatabase.Refresh();
        }

        static Material CreatePaletteMaterial()
        {
            var path = SandboxBuilder.MaterialDir + "/M_Graybox_Palette.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                AssetDatabase.CreateAsset(mat, path);
            }
            var albedo = AssetDatabase.LoadAssetAtPath<Texture2D>(KitDir + "/T_Graybox_Palette_BC.png");
            var emission = AssetDatabase.LoadAssetAtPath<Texture2D>(KitDir + "/T_Graybox_Palette_E.png");
            if (albedo != null) mat.SetTexture("_BaseMap", albedo);
            mat.SetColor("_BaseColor", Color.white);
            mat.SetFloat("_Smoothness", 0.1f);
            mat.SetFloat("_Metallic", 0f);
            if (emission != null)
            {
                mat.SetTexture("_EmissionMap", emission);
                mat.SetColor("_EmissionColor", Color.white);
                mat.EnableKeyword("_EMISSION");
            }
            EditorUtility.SetDirty(mat);
            return mat;
        }

        static void ApplyPalette(GameObject go, Material material, bool castShadow)
        {
            foreach (var r in go.GetComponentsInChildren<Renderer>())
            {
                r.sharedMaterial = material;
                r.shadowCastingMode = castShadow ? ShadowCastingMode.On : ShadowCastingMode.Off;
                r.receiveShadows = true;
            }
        }

        static Bounds RenderBounds(GameObject go)
        {
            var renderers = go.GetComponentsInChildren<Renderer>();
            if (renderers.Length == 0) return new Bounds(go.transform.position, Vector3.zero);
            var bounds = renderers[0].bounds;
            for (var i = 1; i < renderers.Length; i++) bounds.Encapsulate(renderers[i].bounds);
            return bounds;
        }

        static int ReadMonsterLevel(string mapId)
        {
            var path = Path.GetFullPath(Path.Combine(Application.dataPath, "../Content/Data/maps.csv"));
            if (!File.Exists(path)) throw new FileNotFoundException("maps.csv nao encontrado", path);
            var lines = File.ReadAllLines(path);
            var header = lines[0].Split(',');
            var idCol = Array.IndexOf(header, "id");
            var levelCol = Array.IndexOf(header, "monsterLevel");
            for (var i = 1; i < lines.Length; i++)
            {
                var cells = lines[i].Split(',');
                if (cells.Length > Math.Max(idCol, levelCol) && cells[idCol] == mapId && int.TryParse(cells[levelCol], out var level)) return level;
            }
            throw new InvalidOperationException($"Mapa '{mapId}' sem monsterLevel em maps.csv");
        }

        static void AddToBuildSettings()
        {
            var list = new List<EditorBuildSettingsScene>(EditorBuildSettings.scenes);
            for (var i = 0; i < list.Count; i++)
            {
                if (list[i].path != ScenePath) continue;
                list[i] = new EditorBuildSettingsScene(ScenePath, true);
                EditorBuildSettings.scenes = list.ToArray();
                return;
            }
            list.Add(new EditorBuildSettingsScene(ScenePath, true));
            EditorBuildSettings.scenes = list.ToArray();
        }

        static void SetRect(Object target, string field, Rect value)
        {
            var so = new SerializedObject(target);
            var p = so.FindProperty(field) ?? throw new InvalidOperationException(field);
            p.rectValue = value;
            so.ApplyModifiedPropertiesWithoutUndo();
        }

        static void SetObjectArray<T>(Object target, string field, List<T> values) where T : Object
        {
            var so = new SerializedObject(target);
            var p = so.FindProperty(field) ?? throw new InvalidOperationException(field);
            p.arraySize = values.Count;
            for (var i = 0; i < values.Count; i++) p.GetArrayElementAtIndex(i).objectReferenceValue = values[i];
            so.ApplyModifiedPropertiesWithoutUndo();
        }

        static void SetStringArray(Object target, string field, List<string> values)
        {
            var so = new SerializedObject(target);
            var p = so.FindProperty(field) ?? throw new InvalidOperationException(field);
            p.arraySize = values.Count;
            for (var i = 0; i < values.Count; i++) p.GetArrayElementAtIndex(i).stringValue = values[i];
            so.ApplyModifiedPropertiesWithoutUndo();
        }

        static void SetVector3Array(Object target, string field, List<Vector3> values)
        {
            var so = new SerializedObject(target);
            var p = so.FindProperty(field) ?? throw new InvalidOperationException(field);
            p.arraySize = values.Count;
            for (var i = 0; i < values.Count; i++) p.GetArrayElementAtIndex(i).vector3Value = values[i];
            so.ApplyModifiedPropertiesWithoutUndo();
        }
    }
}
