using System.Collections.Generic;
using System.Linq;
using Echoes.EditorTools;
using Echoes.Gameplay;
using Echoes.Interop.Native;
using Echoes.Presentation;
using NUnit.Framework;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace Echoes.Tests.EditMode
{
    /// <summary>Kit de cenario pintado da Cripta: 26 pecas com material, json e pivo conferidos; a Cripta e o Refugio montados com o kit (sem graybox), piso por projecao no mundo, simbolos so em checkpoint e portal, Volume de pos, props que nao bloqueiam a rota, luzes de fogo em pool.</summary>
    [Category("Cenario")]
    public sealed class CriptaSceneryTests
    {
        [OneTimeSetUp]
        public void Build()
        {
            EnvironmentKit.Import();
        }

        // ------------------------------------------------------------------------------------------------ o kit

        [Test]
        public void KitHasTwentySixPiecesEachWithMaterialInEnvSceneryAndJson()
        {
            Assert.AreEqual(26, EnvironmentKit.Names.Length);
            foreach (var name in EnvironmentKit.Names)
            {
                Assert.IsNotNull(AssetDatabase.LoadAssetAtPath<GameObject>($"{EnvironmentKit.Dir}/SM_Cripta_{name}.fbx"), name + " fbx");
                Assert.IsNotNull(AssetDatabase.LoadAssetAtPath<TextAsset>($"{EnvironmentKit.Dir}/SM_Cripta_{name}.json"), name + " json");
                var piece = EnvironmentKit.Get(name);
                StringAssert.EndsWith("Env_Scenery", piece.Material.shader.name, name + ": material no Env_Scenery");
                Assert.IsNotNull(piece.Material.GetTexture("_BaseMap"), name + " albedo");
                Assert.IsNotNull(piece.Material.GetTexture("_MaskMap"), name + " mascara");
                Assert.IsNotNull(piece.Mesh, name + " malha");
            }
        }

        [Test]
        public void MaskTexturesAreLinearAndAlbedoIsSrgb()
        {
            foreach (var name in EnvironmentKit.Names)
            {
                Assert.IsFalse(((TextureImporter)AssetImporter.GetAtPath($"{EnvironmentKit.Dir}/T_Cripta_{name}_M.png")).sRGBTexture, name + " mascara linear");
                Assert.IsTrue(((TextureImporter)AssetImporter.GetAtPath($"{EnvironmentKit.Dir}/T_Cripta_{name}_BC.png")).sRGBTexture, name + " albedo sRGB");
            }
        }

        [Test]
        public void PieceBoundsAndPivotsMatchTheJson()
        {
            foreach (var name in EnvironmentKit.Names)
            {
                var piece = EnvironmentKit.Get(name);
                var go = (GameObject)PrefabUtility.InstantiatePrefab(piece.Model);
                try
                {
                    var rs = go.GetComponentsInChildren<Renderer>();
                    var b = rs[0].bounds;
                    foreach (var r in rs) b.Encapsulate(r.bounds);
                    Assert.AreEqual(piece.Size.x, b.size.x, 0.06f, name + " X");
                    Assert.AreEqual(piece.Size.y, b.size.y, 0.06f, name + " Y");
                    Assert.AreEqual(piece.Size.z, b.size.z, 0.06f, name + " Z");
                    switch (piece.Pivot)
                    {
                        case "base_center":
                            Assert.AreEqual(0f, b.min.y, 0.03f, name + ": base no chao");
                            Assert.AreEqual(0f, b.center.x, 0.03f, name);
                            Assert.AreEqual(0f, b.center.z, 0.03f, name);
                            break;
                        case "floor_top":
                            Assert.AreEqual(0f, b.max.y, 0.03f, name + ": topo do piso em y = 0");
                            Assert.AreEqual(0f, b.center.x, 0.03f, name);
                            Assert.AreEqual(0f, b.center.z, 0.03f, name);
                            break;
                        case "wall_outer":
                            Assert.AreEqual(0f, b.min.y, 0.03f, name);
                            Assert.AreEqual(0f, b.max.z, 0.03f, name + ": face interna em z = 0, corpo para tras");
                            break;
                        default:
                            Assert.Fail(name + ": pivo desconhecido " + piece.Pivot);
                            break;
                    }
                    foreach (var box in piece.Boxes)
                    {
                        var c = new Bounds(box.Center, box.Size);
                        Assert.IsTrue(b.Contains(c.min + Vector3.one * 0.02f) || Vector3.Distance(c.center, b.center) < 3f, name + ": colisor perto da malha");
                    }
                }
                finally
                {
                    Object.DestroyImmediate(go);
                }
            }
        }

        [Test]
        public void ColliderRulesFollowTheJson()
        {
            Assert.AreEqual(2, EnvironmentKit.Get("ArcoRuina").Boxes.Length, "arco: 2 boxes");
            Assert.AreEqual(2, EnvironmentKit.Get("PortalAberto").Boxes.Length, "portal aberto: 2 boxes");
            Assert.IsTrue(EnvironmentKit.Get("Escada").IsRamp, "escada: rampa");
            Assert.AreEqual(0, EnvironmentKit.Get("Velas").Boxes.Length);
            Assert.AreEqual(0, EnvironmentKit.Get("Ossos").Boxes.Length);
            foreach (var name in new[] { "ParedeReta", "PilarInteiro", "PisoLiso", "Braseiro", "SarcofagoAberto" }) Assert.AreEqual(1, EnvironmentKit.Get(name).Boxes.Length, name);
            var go = EnvironmentKit.Place("Escada", null, Vector3.zero, 0f);
            try
            {
                var mc = go.GetComponent<MeshCollider>();
                Assert.IsNotNull(mc);
                Assert.IsTrue(mc.convex);
                Assert.AreEqual(1f, mc.sharedMesh.bounds.size.y, 1e-3f, "cunha de 1 m de altura");
            }
            finally
            {
                Object.DestroyImmediate(go);
            }
        }

        [Test]
        public void FloorVariationUsesAFixedSeed()
        {
            var a = SceneryBuilder.Rng("room.crypt.r01_patrol_a");
            var b = SceneryBuilder.Rng("room.crypt.r01_patrol_a");
            for (var i = 0; i < 50; i++) Assert.AreEqual(a.NextDouble(), b.NextDouble());
            Assert.AreNotEqual(SceneryBuilder.Rng("a").NextDouble(), SceneryBuilder.Rng("b").NextDouble());
        }

        // ------------------------------------------------------------------------------------------------ a Cripta

        static IEnumerable<Renderer> Renderers(params string[] roots) =>
            roots.Select(GameObject.Find).Where(g => g != null).SelectMany(g => g.GetComponentsInChildren<Renderer>(true));

        [Test]
        public void CriptaUsesThePaintedKitWithoutGrayboxAndKeepsTheGameplayHooks()
        {
            var l = CriptaLayout.LoadFromDocument();
            CriptaBuilder.BuildScene();
            EditorSceneManager.OpenScene(CriptaBuilder.ScenePath, OpenSceneMode.Single);

            var level = Renderers("Level", "Decor").ToList();
            Assert.Greater(level.Count, 300);
            foreach (var r in level)
                Assert.IsFalse(r.sharedMaterial != null && r.sharedMaterial.name.StartsWith("M_Graybox"), r.name + " ainda usa graybox");
            var materials = level.Select(r => r.sharedMaterial.name).Distinct().ToList();
            foreach (var wanted in new[] { "M_Env_Piso", "M_Env_Glifo", "M_Cripta_ParedeReta", "M_Cripta_ParedeCantoA", "M_Cripta_PilarInteiro", "M_Cripta_ArcoRuina", "M_Cripta_Braseiro", "M_Cripta_SarcofagoFechado" })
                CollectionAssert.Contains(materials, wanted);

            foreach (var room in l.Rooms)
            {
                var go = GameObject.Find(room.Id);
                var floors = go.GetComponentsInChildren<MeshFilter>().Where(f => f.name.StartsWith("Floor_")).ToList();
                Assert.IsNotEmpty(floors, room.Id + ": piso");
                var cells = Mathf.RoundToInt(room.Rect.width / 2f) * Mathf.RoundToInt(room.Rect.height / 2f);
                var holes = l.Vistas.Where(v => v.Id.Contains("pit") && room.Rect.Overlaps(v.Rect)).Sum(v => Mathf.RoundToInt(v.Rect.width / 2f) * Mathf.RoundToInt(v.Rect.height / 2f));
                var tris = floors.Sum(f => f.sharedMesh.triangles.Length / 3);
                Assert.AreEqual((cells - holes) * 2, tris, room.Id + ": piso plano, 2 triangulos por celula de 2 m");
                Assert.AreEqual("M_Env_Piso", floors[0].GetComponent<Renderer>().sharedMaterial.name, room.Id);
            }
            foreach (var r in level) StringAssert.EndsWith("Env_Scenery", r.sharedMaterial.shader.name, r.name + ": todo o cenario no Env_Scenery");

            // Simbolos de bussola: so em checkpoint e portal (nunca sorteados), no maximo 2 por sala.
            var glyphs = Object.FindObjectsByType<MeshFilter>(FindObjectsSortMode.None).Where(f => f.name.EndsWith(".glyph")).ToList();
            Assert.AreEqual(l.Checkpoints.Count + l.Portals.Count, glyphs.Count, "um simbolo por checkpoint e por portal");
            foreach (var room in l.Rooms)
                Assert.LessOrEqual(glyphs.Count(g => room.Rect.Contains(new Vector2(g.transform.position.x, g.transform.position.z))), 2, room.Id + ": no maximo 2 simbolos");

            var arena = l.Room("room.crypt.r09_arena");
            Assert.IsNotNull(GameObject.Find("Props").transform.Cast<Transform>().FirstOrDefault(t => t.name.StartsWith(arena.Id) && t.name.EndsWith("brazier")), "braseiros na arena");
            var secret = GameObject.Find(l.Secrets[0].Id);
            Assert.IsNotNull(secret.GetComponent<SecretWall>());
            Assert.IsNotNull(secret.GetComponent<BoxCollider>());
            Assert.AreEqual("M_Cripta_ParedeRuina", secret.GetComponentInChildren<Renderer>().sharedMaterial.name);
            foreach (var portal in Object.FindObjectsByType<PortalZone>(FindObjectsInactive.Include, FindObjectsSortMode.None))
                Assert.IsNotNull(portal.transform.Find("PortalFrame"), portal.name + ": arco do portal");
        }

        [Test]
        public void PropsKeepTheRouteFreeAndTheNavMeshConnectsTheWholeRoute()
        {
            var l = CriptaLayout.LoadFromDocument();
            CriptaBuilder.BuildScene();
            EditorSceneManager.OpenScene(CriptaBuilder.ScenePath, OpenSceneMode.Single);
            var route = l.Route;
            Assert.GreaterOrEqual(route.Count, 6);

            float DistToRoute(Vector2 p)
            {
                var best = float.MaxValue;
                for (var i = 0; i + 1 < route.Count; i++)
                {
                    var a = route[i];
                    var ab = route[i + 1] - a;
                    var t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / Mathf.Max(1e-4f, ab.sqrMagnitude));
                    best = Mathf.Min(best, Vector2.Distance(p, a + ab * t));
                }
                return best;
            }

            // Colisores de props (fora arcos e braseiros de checkpoint, que ladeiam a rota de proposito) a pelo menos 2,2 m do eixo da rota.
            foreach (var c in GameObject.Find("Props").GetComponentsInChildren<Collider>())
            {
                if (c.name.EndsWith(".arch") || c.name.Contains("cp.crypt") || c.name.Contains("Pillar") || c.name.Contains("pil.")) continue;
                var p = new Vector2(c.bounds.center.x, c.bounds.center.z);
                Assert.GreaterOrEqual(DistToRoute(p) - Mathf.Max(c.bounds.extents.x, c.bounds.extents.z), 1.9f, c.name + " na rota");
            }

            for (var i = 0; i + 1 < route.Count; i++)
            {
                var path = new NavMeshPath();
                var from = new Vector3(route[i].x, 0f, route[i].y);
                var to = new Vector3(route[i + 1].x, 0f, route[i + 1].y);
                Assert.IsTrue(NavMesh.SamplePosition(from, out var f, 3f, NavMesh.AllAreas), "NavMesh em " + from);
                Assert.IsTrue(NavMesh.SamplePosition(to, out var t, 3f, NavMesh.AllAreas), "NavMesh em " + to);
                Assert.IsTrue(NavMesh.CalculatePath(f.position, t.position, NavMesh.AllAreas, path), "caminho " + i);
                Assert.AreEqual(NavMeshPathStatus.PathComplete, path.status, $"rota {from} -> {to}");
                var length = 0f;
                for (var k = 0; k + 1 < path.corners.Length; k++) length += Vector3.Distance(path.corners[k], path.corners[k + 1]);
                Assert.LessOrEqual(length, Vector3.Distance(from, to) * 1.15f + 3f, $"desvio grande na rota {from} -> {to}");
            }
        }

        [Test]
        public void FirePoolIsWiredWithAtMostSixLightsAndEnoughSources()
        {
            CriptaBuilder.BuildScene();
            EditorSceneManager.OpenScene(CriptaBuilder.ScenePath, OpenSceneMode.Single);
            var pool = Object.FindFirstObjectByType<FirePool>();
            Assert.IsNotNull(pool);
            var so = new SerializedObject(pool);
            Assert.LessOrEqual(so.FindProperty("maxActive").intValue, 6, "no maximo 6 luzes ativas");
            Assert.IsNotNull(so.FindProperty("flameMaterial").objectReferenceValue, "material da chama");
            Assert.IsNotNull(so.FindProperty("target").objectReferenceValue, "alvo (heroi)");
            var sources = Object.FindObjectsByType<FireSource>(FindObjectsSortMode.None);
            Assert.Greater(sources.Length, 20, "braseiros e velas pela Cripta");
            Assert.IsTrue(sources.Any(s => s.name.Contains("Braseiro") || s.name.Contains("brazier")));
            Assert.IsTrue(sources.Any(s => s.name.Contains("Velas")));
            // As luzes e as chamas sao do pool: nenhuma Light ou ParticleSystem nasce na cena montada alem do sol.
            Assert.AreEqual(0, Object.FindObjectsByType<Light>(FindObjectsSortMode.None).Count(l => l.type == LightType.Point), "luz pontual so em runtime, pelo pool");
        }

        [Test]
        public void RefugeUsesTheKitToo()
        {
            RefugioBuilder.BuildScene();
            EditorSceneManager.OpenScene(RefugioBuilder.ScenePath, OpenSceneMode.Single);
            var level = Renderers("Level", "Decor").ToList();
            Assert.Greater(level.Count, 40);
            foreach (var r in level) Assert.IsFalse(r.sharedMaterial.name.StartsWith("M_Graybox"), r.name);
            CollectionAssert.Contains(level.Select(r => r.sharedMaterial.name).ToList(), "M_Env_Piso");
            Assert.IsNotNull(Object.FindFirstObjectByType<FirePool>());
            Assert.IsNotEmpty(Object.FindObjectsByType<FireSource>(FindObjectsSortMode.None));
        }

        [Test]
        public void SceneHasTheGlobalPostVolumeAndTheCameraRendersPost()
        {
            CriptaBuilder.BuildScene();
            EditorSceneManager.OpenScene(CriptaBuilder.ScenePath, OpenSceneMode.Single);
            var volume = Object.FindFirstObjectByType<Volume>();
            Assert.IsNotNull(volume, "Volume global");
            Assert.IsTrue(volume.isGlobal);
            var profile = volume.sharedProfile;
            Assert.IsTrue(profile.TryGet(out Tonemapping tone) && tone.mode.value == TonemappingMode.ACES, "ACES");
            Assert.IsTrue(profile.TryGet(out Bloom bloom) && bloom.intensity.value > 0f && bloom.threshold.value >= 1f, "bloom");
            Assert.IsTrue(profile.TryGet(out Vignette _), "vinheta");
            Assert.IsTrue(profile.TryGet(out ColorAdjustments adjust) && adjust.saturation.value < 0f, "color grading");
            Assert.IsTrue(Camera.main.GetComponent<UniversalAdditionalCameraData>().renderPostProcessing, "a camera liga o pos-processamento");
            Assert.AreEqual(AmbientMode.Trilight, RenderSettings.ambientMode);
        }

        [Test]
        public void StubLogNoLongerClaimsSaveAndExpeditionAreMissing()
        {
            Assert.That(NativeRulesCore.StillInStub, Has.None.Contains("Salvar"));
            Assert.That(NativeRulesCore.StillInStub, Has.None.Contains("expedicao"));
        }
    }
}
