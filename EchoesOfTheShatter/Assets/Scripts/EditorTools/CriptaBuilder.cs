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
    /// encounters.csv (testes). Visual: kit de cenário pintado (SM_Cripta_*, ver EnvironmentKit e CriptaScenery) e os modelos dos inimigos.
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
            "SM_Enemy_AshHound.fbx", "T_Graybox_Palette_BC.png", "T_Graybox_Palette_E.png",
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

        internal sealed class Context
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
            SceneryBuilder.ApplyLook(null); // sol, ambiente em gradiente e Volume de pos (a camera liga o pos em BuildHero)

            // ---- Nivel: so a geometria andavel e as paredes entram no NavMesh
            var level = new GameObject("Level").transform;
            var decor = new GameObject("Decor").transform; // props sem colisor: fora do Level, fora da NavMesh
            CriptaScenery.Build(ctx, level, decor);

            // ---- Sistemas, heroi, camera, HUD
            BuildSystems(ctx, feel, projectile);
            ctx.Interactives = new GameObject("Interactives").transform;
            var hero = BuildHero(ctx, renderSettings, inputActions);
            SceneryBuilder.AddFirePool(hero != null ? hero.transform : null); // luzes e chamas em pool (ate 6)
            BuildHud(ctx, panel, hudUxml);
            BuildSessionObjects(ctx, panel, true);

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

        /// <summary>O cenario (pisos, paredes, pilares, props) e do <see cref="CriptaScenery"/>, com o kit pintado; aqui so o colisor de piso por sala.</summary>
        internal static void AddFloorCollider(Transform parent, Rect r)
        {
            var box = parent.gameObject.AddComponent<BoxCollider>();
            box.center = new Vector3(r.center.x, -0.1f, r.center.y);
            box.size = new Vector3(r.width, 0.2f, r.height);
        }

        // ============================================================================================== sistemas

        internal static void BuildSystems(Context ctx, CombatFeelSettings feel, GameObject projectile)
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

        internal static HeroController BuildHero(Context ctx, RenderSettingsAsset renderSettings, InputActionAsset inputActions, Vector3? spawnOverride = null)
        {
            var spawn = spawnOverride ?? new Vector3(ctx.Layout.HeroSpawn.x, 0f, ctx.Layout.HeroSpawn.y);

            var camGo = new GameObject("Main Camera") { tag = "MainCamera" };
            var cam = camGo.AddComponent<Camera>();
            camGo.AddComponent<AudioListener>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.059f, 0.043f, 0.078f);
            SceneryBuilder.EnablePostProcessing(cam);
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
            hero.AddComponent<ImpactSquash>();
            SandboxBuilder.SetRef(presentation, "root", ctx.GameRoot);
            SandboxBuilder.SetRef(presentation, "eliteTint", AssetDatabase.LoadAssetAtPath<RarityTintAsset>("Assets/Data/Presentation/SO_RarityTint.asset"));
            SandboxBuilder.SetRef(presentation, "skillSet", AssetDatabase.LoadAssetAtPath<SkillPresentationSet>(AnimatorControllerBuilder.WarriorSkillSetPath));
            SandboxBuilder.SetRef(heroController, "combatHost", ctx.Host);
            SandboxBuilder.SetRef(heroController, "input", inputHandler);
            SandboxBuilder.SetRef(heroController, "aimCamera", cam);
            SandboxBuilder.SetFloat(heroController, "respawnDelay", 1.5f);

            var heroPrefab = SandboxBuilder.BuildWarriorPrefab(ctx.Mats.Warrior);
            var visual = (GameObject)PrefabUtility.InstantiatePrefab(heroPrefab);
            visual.name = "Body";
            visual.transform.SetParent(hero.transform, false);

            var swap = hero.AddComponent<HeroVisualSwap>();
            SandboxBuilder.SetRef(swap, "warrior", heroPrefab);
            SandboxBuilder.SetRef(swap, "archer", CharacterPrefabBuilder.HeroPrefab("archer"));
            SandboxBuilder.SetRef(swap, "mage", CharacterPrefabBuilder.HeroPrefab("mage"));

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

        internal static void BuildHud(Context ctx, PanelSettings panel, VisualTreeAsset hudUxml)
        {
            panel = SandboxBuilder.CreatePanelSettings(); // recarrega: o asset carregado antes de NewScene pode ter sido descarregado (a referencia saia nula na cena)
            var hud = new GameObject("HUD");
            var uiDoc = hud.AddComponent<UIDocument>();
            uiDoc.panelSettings = panel;
            uiDoc.visualTreeAsset = hudUxml;
            var hudView = hud.AddComponent<HudView>();
            SandboxBuilder.SetRef(hudView, "root", ctx.GameRoot);
            SandboxBuilder.SetRef(hudView, "hero", ctx.Hero);
            SandboxBuilder.SetRef(hudView, "worldCamera", ctx.Camera);

            // Pausa (Esc): overlay acima do HUD; volta a tela inicial pelo menu.
            var pause = new GameObject("Pause");
            var pauseDoc = pause.AddComponent<UIDocument>();
            pauseDoc.panelSettings = panel;
            pauseDoc.sortingOrder = 100;
            var pauseController = pause.AddComponent<PauseController>();
            SandboxBuilder.SetRef(pauseController, "root", ctx.GameRoot);
        }

        /// <summary>Raiz de UI das cenas de jogo (toast), autosave e troca de area; na Cripta tambem o registro da vitoria (dominio e cargas).</summary>
        internal static void BuildSessionObjects(Context ctx, PanelSettings panel, bool crypt)
        {
            panel = SandboxBuilder.CreatePanelSettings();
            var go = new GameObject("Session");
            var doc = go.AddComponent<UIDocument>();
            doc.panelSettings = panel;
            doc.sortingOrder = 90;
            go.AddComponent<ScreenHost>();
            var autosave = go.AddComponent<AutosaveRunner>();
            SandboxBuilder.SetRef(autosave, "root", ctx.GameRoot);
            var travel = go.AddComponent<AreaTravel>();
            SandboxBuilder.SetRef(travel, "root", ctx.GameRoot);
            // Inventario (tecla I; botao no Refugio) com o boneco modular; o loot no chao so na Cripta.
            var inventory = go.AddComponent<InventoryController>();
            SandboxBuilder.SetRef(inventory, "root", ctx.GameRoot);
            SandboxBuilder.SetRef(inventory, "hero", ctx.Hero);
            SandboxBuilder.SetRef(inventory, "dollPrefab", CharacterPrefabBuilder.HeroPrefab("warrior"));
            if (crypt)
            {
                var ground = new GameObject("GroundLoot").AddComponent<GroundLootDirector>();
                SandboxBuilder.SetRef(ground, "root", ctx.GameRoot);
                SandboxBuilder.SetRef(ground, "hero", ctx.Hero);
                SandboxBuilder.SetRef(ground, "beam", LootBeamBuilder.CreateOrUpdate());
            }
            if (crypt)
            {
                var recorder = go.AddComponent<RunRecorder>();
                SandboxBuilder.SetRef(recorder, "root", ctx.GameRoot);
                var shot = go.AddComponent<BossShotRunner>();
                SandboxBuilder.SetRef(shot, "root", ctx.GameRoot);
                var perf = go.AddComponent<FramePerfRunner>();
                SandboxBuilder.SetRef(perf, "root", ctx.GameRoot);
                var bossBar = go.AddComponent<BossBarView>();
                SandboxBuilder.SetRef(bossBar, "root", ctx.GameRoot);
            }
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
            }
            if (firstCheckpoint != null) SandboxBuilder.SetRef(ctx.Hero, "checkpoint", firstCheckpoint);

            var victory = new List<GameObject>();
            foreach (var portal in layout.Portals)
            {
                var go = Marker(root, portal.Id, portal.Pos, ctx.Mats.Boss, 2.4f);
                var frame = EnvironmentKit.Place("PortalAberto", go.transform, go.transform.position, 0f, instanceName: "PortalFrame");
                SceneryBuilder.AddFire(frame, false, 2.2f, new Color(0.62f, 0.5f, 1f), 1.6f, 7f);
                var zone = go.AddComponent<PortalZone>();
                SandboxBuilder.SetRef(zone, "combatHost", ctx.Host);
                SandboxBuilder.SetRef(zone, "hero", ctx.Hero);
                SandboxBuilder.SetString(zone, "portalId", portal.Id);
                SandboxBuilder.SetString(zone, "targetArea", portal.Target);
                SandboxBuilder.SetBool(zone, "travels", true); // troca de cena pelo AreaTravel (Refugio)
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
            // Parede rachada: ParedeRuina (kit pintado) fechando o vao de 3 m; o SecretWall desliga o objeto inteiro ao abrir.
            var go = new GameObject(secret.Id);
            go.transform.SetParent(parent, false);
            var width = secret.Rect.width;
            var piece = EnvironmentKit.Get("ParedeRuina");
            go.transform.position = new Vector3(secret.Rect.center.x, 0f, secret.Rect.center.y);
            var box = go.AddComponent<BoxCollider>();
            box.center = new Vector3(0f, SandboxBuilder.WallHeight / 2f, -piece.Size.z * 0.5f);
            box.size = new Vector3(width, SandboxBuilder.WallHeight, piece.Size.z);
            var visual = EnvironmentKit.Place("ParedeRuina", go.transform, go.transform.position, 0f, new Vector3(width / piece.Size.x, SandboxBuilder.WallHeight / piece.Size.y, 1f), colliders: false, instanceName: "Visual");
            visual.transform.localPosition = Vector3.zero;
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
            if (g.Patrol.Count > 1)
            {
                var points = new List<Vector3>();
                foreach (var p in g.Patrol) points.Add(new Vector3(p.x, 0f, p.y));
                SetVector3Array(controller, "patrolPoints", points);
            }
            var presentation = go.AddComponent<PresentationController>();
            go.AddComponent<ImpactSquash>();
            SandboxBuilder.SetRef(presentation, "root", ctx.GameRoot);
            SandboxBuilder.SetRef(presentation, "eliteTint", AssetDatabase.LoadAssetAtPath<RarityTintAsset>("Assets/Data/Presentation/SO_RarityTint.asset"));
            var skillSetPath = AnimatorControllerBuilder.SkillSetPathFor(g.EnemyId);
            if (skillSetPath != null) SandboxBuilder.SetRef(presentation, "skillSet", AssetDatabase.LoadAssetAtPath<SkillPresentationSet>(skillSetPath));
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
            var painted = CharacterPrefabBuilder.PrefabForEnemy(enemyId); // modelo pintado aprovado (Sentinela, Arauto, Espectro, Guardiao)
            if (painted != null)
            {
                var paintedBody = (GameObject)PrefabUtility.InstantiatePrefab(painted);
                paintedBody.name = "Body";
                paintedBody.transform.SetParent(parent, false);
                return;
            }
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
