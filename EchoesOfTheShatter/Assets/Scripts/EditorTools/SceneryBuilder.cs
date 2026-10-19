using System;
using System.Collections.Generic;
using Echoes.Presentation;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using Object = UnityEngine.Object;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Pisos, paredes e cantos com o kit pintado (<see cref="EnvironmentKit"/>), comuns a Cripta e Refugio. Tudo determinista: a variacao das pecas
    /// vem de uma seed fixa por dono (sala/corredor), entao a mesma montagem gera sempre o mesmo cenario.
    /// </summary>
    public static class SceneryBuilder
    {
        public const int Seed = 20261017;
        public const float Module = 2f; // grade do kit

        public static System.Random Rng(string owner)
        {
            var hash = 2166136261u; // FNV-1a: estavel entre execucoes (string.GetHashCode nao e)
            foreach (var ch in owner) hash = (hash ^ ch) * 16777619u;
            return new System.Random(Seed ^ (int)hash);
        }

        // ------------------------------------------------------------------------------------------------ pisos

        /// <summary>
        /// Piso do retangulo: UMA malha plana por dono (sala/corredor), em celulas de 2 m (as que caem num buraco ficam de fora) com UV no mundo.
        /// A textura vem do shader (2 lajotas A e B misturadas por ruido de baixa frequencia, projecao planar no mundo, 8 m por tile): nao ha
        /// peca de piso com rachadura nem simbolo sorteado, e a emenda nunca cai numa borda de peca.
        /// </summary>
        public static void BuildFloor(Transform parent, string owner, Rect rect, IList<Rect> holes)
        {
            var nx = Mathf.Max(1, Mathf.RoundToInt(rect.width / Module));
            var nz = Mathf.Max(1, Mathf.RoundToInt(rect.height / Module));
            var cellX = rect.width / nx;
            var cellZ = rect.height / nz;
            var vertices = new List<Vector3>();
            var normals = new List<Vector3>();
            var uvs = new List<Vector2>();
            var triangles = new List<int>();
            for (var ix = 0; ix < nx; ix++)
            {
                for (var iz = 0; iz < nz; iz++)
                {
                    var x0 = rect.xMin + cellX * ix;
                    var z0 = rect.yMin + cellZ * iz;
                    if (Inside(holes, new Vector3(x0 + cellX * 0.5f, 0f, z0 + cellZ * 0.5f))) continue;
                    var i = vertices.Count;
                    foreach (var c in new[] { new Vector2(x0, z0), new Vector2(x0, z0 + cellZ), new Vector2(x0 + cellX, z0 + cellZ), new Vector2(x0 + cellX, z0) })
                    {
                        vertices.Add(new Vector3(c.x, 0f, c.y));
                        normals.Add(Vector3.up);
                        uvs.Add(c / 8f);
                    }
                    triangles.AddRange(new[] { i, i + 1, i + 2, i, i + 2, i + 3 });
                }
            }
            if (vertices.Count == 0) return;
            var mesh = new Mesh { name = $"Floor_{owner}", indexFormat = IndexFormat.UInt32 };
            mesh.SetVertices(vertices);
            mesh.SetNormals(normals);
            mesh.SetUVs(0, uvs);
            mesh.SetTriangles(triangles, 0);
            mesh.RecalculateBounds();
            SandboxBuilder.EnsureDir(EnvironmentKit.GeneratedDir + "/Floor");
            mesh = SandboxBuilder.SaveMesh(mesh, $"{EnvironmentKit.GeneratedDir}/Floor/{Sanitize(owner)}.asset");
            var go = new GameObject("Floor_Piso");
            go.transform.SetParent(parent, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = EnvironmentKit.EnsureFloorMaterial();
            mr.shadowCastingMode = ShadowCastingMode.Off;
            mr.receiveShadows = true;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);
        }

        /// <summary>Simbolo de bussola no chao (decalque dourado, 2,6 m). So onde marca algo de jogo (checkpoint, portal); no maximo 2 por sala.</summary>
        public static GameObject Glyph(Transform parent, Vector2 pos, float yaw, string name, float height = 0.012f, float size = 2.6f)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.SetPositionAndRotation(new Vector3(pos.x, height, pos.y), Quaternion.Euler(90f, yaw, 0f));
            var mf = go.AddComponent<MeshFilter>();
            mf.sharedMesh = Resources.GetBuiltinResource<Mesh>("Quad.fbx");
            go.transform.localScale = new Vector3(size, size, 1f);
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = EnvironmentKit.EnsureGlyphMaterial();
            mr.shadowCastingMode = ShadowCastingMode.Off;
            mr.receiveShadows = false;
            return go;
        }

        // ------------------------------------------------------------------------------------------------ circulo de pedra e portao

        static void AddQuad(List<Vector3> v, List<Vector3> n, List<Vector2> uv, List<int> t, Vector3 c, Vector3 u, Vector3 w)
        {
            var i = v.Count;
            v.Add(c - u - w); v.Add(c - u + w); v.Add(c + u + w); v.Add(c + u - w);
            for (var k = 0; k < 4; k++) { n.Add(Vector3.up); uv.Add(Vector2.zero); }
            var cross = Vector3.Cross(v[i + 1] - v[i], v[i + 2] - v[i]);
            if (cross.y >= 0f) t.AddRange(new[] { i, i + 1, i + 2, i, i + 2, i + 3 });
            else t.AddRange(new[] { i, i + 2, i + 1, i, i + 3, i + 2 });
        }

        /// <summary>
        /// Circulo de pedra no chao (checkpoint, portal de saida): anel chanfrado de pedra (projecao no mundo, igual a parede) com runas na face de
        /// cima que acendem (material de emissao com pulso; o bloom faz o brilho). So visual: sem colisor, sem gatilho.
        /// </summary>
        public static GameObject StoneCircle(Transform parent, Vector3 center, float outerRadius, float ringWidth, string name, bool portal, int runes = 8)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.position = center;
            var inner = outerRadius - ringWidth;
            const int segments = 56;
            const float top = 0.1f;
            const float bevel = 0.06f;
            var profile = new[] { new Vector2(inner, 0f), new Vector2(inner + bevel, top), new Vector2(outerRadius - bevel, top), new Vector2(outerRadius, 0f) };
            Vector2 EdgeNormal(int a) { var d = profile[a + 1] - profile[a]; return new Vector2(-d.y, d.x).normalized; }
            // Normal de cada ponta do perfil: media das arestas vizinhas (o chanfro fica arredondado).
            var pn = new[] { EdgeNormal(0), (EdgeNormal(0) + EdgeNormal(1)).normalized, (EdgeNormal(1) + EdgeNormal(2)).normalized, EdgeNormal(2) };
            var v = new List<Vector3>(); var n = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
            for (var s = 0; s <= segments; s++)
            {
                var a = s * Mathf.PI * 2f / segments;
                var dir = new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a));
                for (var k = 0; k < 4; k++)
                {
                    v.Add(dir * profile[k].x + Vector3.up * profile[k].y);
                    n.Add((dir * pn[k].x + Vector3.up * pn[k].y).normalized);
                    uv.Add(Vector2.zero);
                }
            }
            for (var s = 0; s < segments; s++)
            {
                for (var k = 0; k < 3; k++)
                {
                    var a0 = s * 4 + k;
                    var a1 = (s + 1) * 4 + k;
                    // Enrola de modo que a face aponte para a normal do perfil (cima / fora).
                    var cross = Vector3.Cross(v[a0 + 1] - v[a0], v[a1] - v[a0]);
                    if (Vector3.Dot(cross, n[a0] + n[a0 + 1]) >= 0f) t.AddRange(new[] { a0, a0 + 1, a1, a1, a0 + 1, a1 + 1 });
                    else t.AddRange(new[] { a0, a1, a0 + 1, a1, a1 + 1, a0 + 1 });
                }
            }
            var ringMesh = new Mesh { name = "Ring_" + name };
            ringMesh.SetVertices(v); ringMesh.SetNormals(n); ringMesh.SetUVs(0, uv); ringMesh.SetTriangles(t, 0);
            ringMesh.RecalculateBounds();

            // Runas: marcas na face de cima (losango, par de barras, chevron), todas pequenas.
            v = new List<Vector3>(); n = new List<Vector3>(); uv = new List<Vector2>(); t = new List<int>();
            var mid = (inner + outerRadius) * 0.5f;
            var y = top + 0.004f;
            for (var k = 0; k < runes; k++)
            {
                var a = (k + 0.5f) * Mathf.PI * 2f / runes;
                var radial = new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a));
                var tangent = new Vector3(-radial.z, 0f, radial.x);
                var c = radial * mid + Vector3.up * y;
                // Marca uniforme: uma barra radial curta por runa (sem losango nem chevron soltos no anel).
                AddQuad(v, n, uv, t, c, radial * 0.2f, tangent * 0.03f);
            }
            var runeMesh = new Mesh { name = "Runes_" + name };
            runeMesh.SetVertices(v); runeMesh.SetNormals(n); runeMesh.SetUVs(0, uv); runeMesh.SetTriangles(t, 0);
            runeMesh.RecalculateBounds();

            SandboxBuilder.EnsureDir(EnvironmentKit.GeneratedDir + "/Props");
            ringMesh = SandboxBuilder.SaveMesh(ringMesh, $"{EnvironmentKit.GeneratedDir}/Props/Ring_{Sanitize(name)}.asset");
            runeMesh = SandboxBuilder.SaveMesh(runeMesh, $"{EnvironmentKit.GeneratedDir}/Props/Runes_{Sanitize(name)}.asset");

            var ring = new GameObject("Ring");
            ring.transform.SetParent(go.transform, false);
            ring.AddComponent<MeshFilter>().sharedMesh = ringMesh;
            var rr = ring.AddComponent<MeshRenderer>();
            rr.sharedMaterial = EnvironmentKit.EnsureStoneMaterial();
            rr.shadowCastingMode = ShadowCastingMode.Off;
            var rune = new GameObject("Runes");
            rune.transform.SetParent(go.transform, false);
            rune.AddComponent<MeshFilter>().sharedMesh = runeMesh;
            var mr = rune.AddComponent<MeshRenderer>();
            mr.sharedMaterial = EnvironmentKit.EnsureRuneMaterial(portal);
            mr.shadowCastingMode = ShadowCastingMode.Off;
            mr.receiveShadows = false;
            return go;
        }

        /// <summary>
        /// Portao de pedra com grade (arena do Guardiao, atalho): dois pilares e um arco do kit e, entre eles, a grade de ferro (barras e travessas numa
        /// malha so). O arco e os pilares ficam sempre; so a grade (devolvida em <paramref name="grille"/>) some quando o GateBarrier abre. O colisor e o
        /// NavMeshObstacle continuam os do CriptaBuilder.
        /// </summary>
        public static void StoneGate(Transform gate, float width, float wallHeight, out Renderer grille)
        {
            var pillar = EnvironmentKit.Get("PilarInteiro");
            var arch = EnvironmentKit.Get("ArcoRuina");
            var px = width * 0.5f - 0.45f;
            var pillarScale = new Vector3(1f, (wallHeight + 0.7f) / Mathf.Max(0.01f, pillar.Size.y), 1f);
            foreach (var sx in new[] { -1f, 1f })
                EnvironmentKit.Place("PilarInteiro", gate, gate.position + new Vector3(sx * px, 0f, 0f), 0f, pillarScale, colliders: false, instanceName: "Pillar");
            var clear = (px - pillar.Size.x * 0.5f) * 2f;
            EnvironmentKit.Place("ArcoRuina", gate, gate.position, 0f, new Vector3(clear / Mathf.Max(0.01f, arch.Size.x), 1f, 1f), colliders: false, instanceName: "Arch");

            var v = new List<Vector3>(); var n = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
            void Box(Vector3 c, Vector3 h)
            {
                // Seis faces com normais proprias (a grade e fina: aresta viva de ferro).
                var axes = new[] { Vector3.right, Vector3.up, Vector3.forward };
                for (var a = 0; a < 3; a++)
                {
                    var b = (a + 1) % 3;
                    var d = (a + 2) % 3;
                    foreach (var sign in new[] { -1f, 1f })
                    {
                        var nrm = axes[a] * sign;
                        var i = v.Count;
                        var center = c + Vector3.Scale(nrm, h);
                        var ub = axes[b] * Mathf.Abs(Vector3.Dot(h, axes[b]));
                        var ud = axes[d] * Mathf.Abs(Vector3.Dot(h, axes[d]));
                        v.Add(center - ub - ud); v.Add(center - ub + ud); v.Add(center + ub + ud); v.Add(center + ub - ud);
                        for (var k = 0; k < 4; k++) { n.Add(nrm); uv.Add(Vector2.zero); }
                        var cross = Vector3.Cross(v[i + 1] - v[i], v[i + 2] - v[i]);
                        if (Vector3.Dot(cross, nrm) >= 0f) t.AddRange(new[] { i, i + 1, i + 2, i, i + 2, i + 3 });
                        else t.AddRange(new[] { i, i + 2, i + 1, i, i + 3, i + 2 });
                    }
                }
            }
            var half = clear * 0.5f - 0.08f;
            var bars = Mathf.Max(3, Mathf.RoundToInt(half * 2f / 0.3f));
            var top = wallHeight - 0.45f;
            for (var k = 0; k <= bars; k++)
            {
                var x = Mathf.Lerp(-half, half, k / (float)bars);
                Box(new Vector3(x, top * 0.5f, 0f), new Vector3(0.045f, top * 0.5f, 0.045f));
            }
            foreach (var ry in new[] { 0.35f, top * 0.5f, top - 0.1f }) Box(new Vector3(0f, ry, 0f), new Vector3(half + 0.05f, 0.05f, 0.05f));
            var mesh = new Mesh { name = "Grille_" + gate.name, indexFormat = IndexFormat.UInt32 };
            mesh.SetVertices(v); mesh.SetNormals(n); mesh.SetUVs(0, uv); mesh.SetTriangles(t, 0);
            mesh.RecalculateBounds();
            SandboxBuilder.EnsureDir(EnvironmentKit.GeneratedDir + "/Props");
            mesh = SandboxBuilder.SaveMesh(mesh, $"{EnvironmentKit.GeneratedDir}/Props/Grille_{Sanitize(gate.name)}.asset");
            var go = new GameObject("Grid");
            go.transform.SetParent(gate, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            grille = go.AddComponent<MeshRenderer>();
            grille.sharedMaterial = EnvironmentKit.EnsureGrateMaterial();
            grille.shadowCastingMode = ShadowCastingMode.Off;
        }

        static bool Inside(IList<Rect> holes, Vector3 p)
        {
            if (holes == null) return false;
            for (var i = 0; i < holes.Count; i++) if (holes[i].Contains(new Vector2(p.x, p.z))) return true;
            return false;
        }

        public static string Sanitize(string id) => id.Replace('.', '_').Replace('/', '_');

        // ------------------------------------------------------------------------------------------------ paredes

        /// <summary>
        /// Um trecho reto de parede (ParedeReta, de vez em quando ParedeRuina) sobre a linha <paramref name="line"/>, de <paramref name="from"/> a
        /// <paramref name="to"/>, com o corpo para FORA do chao jogavel (<paramref name="positiveOutside"/>: o lado de fora e o positivo do eixo
        /// perpendicular). O pivo do kit e a face interna; 2 m por peca (escala so no comprimento, para fechar trechos que nao sao multiplos de 2).
        /// Um colisor de caixa por trecho.
        /// </summary>
        public static void WallRun(Transform parent, string owner, bool alongX, float line, float from, float to, bool positiveOutside, bool clean = false)
        {
            var length = to - from;
            if (length < 0.1f) return;
            var rng = Rng(owner + (alongX ? "X" : "Z") + line.ToString("F1", System.Globalization.CultureInfo.InvariantCulture) + from.ToString("F1", System.Globalization.CultureInfo.InvariantCulture));
            var yaw = alongX ? (positiveOutside ? 180f : 0f) : (positiveOutside ? 270f : 90f);
            var n = Mathf.Max(1, Mathf.RoundToInt(length / Module));
            var tile = length / n;
            var run = new GameObject($"{owner}_wall");
            run.transform.SetParent(parent, false);
            var mid = from + length * 0.5f;
            run.transform.SetPositionAndRotation(alongX ? new Vector3(mid, 0f, line) : new Vector3(line, 0f, mid), Quaternion.Euler(0f, yaw, 0f));
            var reta = EnvironmentKit.Get("ParedeReta");
            var box = run.AddComponent<BoxCollider>(); // colisor simples do trecho (nunca a malha visual)
            box.center = new Vector3(0f, reta.Size.y * 0.5f, -reta.Size.z * 0.5f);
            box.size = new Vector3(length, reta.Size.y, reta.Size.z);
            if (clean)
            {
                CriptaStructure.WallVisual(run.transform, Sanitize(owner) + (alongX ? "X" : "Z") + line.ToString("F1", System.Globalization.CultureInfo.InvariantCulture) + "_" + from.ToString("F1", System.Globalization.CultureInfo.InvariantCulture), length, reta.Size.y, reta.Size.z);
                GameObjectUtility.SetStaticEditorFlags(run, StaticEditorFlags.BatchingStatic);
                return;
            }
            for (var i = 0; i < n; i++)
            {
                var local = (i + 0.5f) * tile - length * 0.5f;
                var ruin = n >= 3 && i > 0 && i < n - 1 && rng.NextDouble() < 0.12;
                var go = EnvironmentKit.Place(ruin ? "ParedeRuina" : "ParedeReta", run.transform, Vector3.zero, 0f, new Vector3(tile / Module, 1f, 1f), colliders: false);
                go.transform.localPosition = new Vector3(local, 0f, 0f);
                go.transform.localRotation = Quaternion.identity;
            }
            GameObjectUtility.SetStaticEditorFlags(run, StaticEditorFlags.BatchingStatic);
        }

        /// <summary>Poste de canto (ParedeCantoA, 1 x 3 x 1) fora de cada canto convexo do retangulo: fecha a quina onde duas paredes de 0,6 m se encontram.</summary>
        public static void CornerPosts(Transform parent, string owner, Rect r, bool clean = false)
        {
            foreach (var sx in new[] { -1, 1 })
            {
                foreach (var sz in new[] { -1, 1 })
                {
                    var corner = new Vector3(sx < 0 ? r.xMin : r.xMax, 0f, sz < 0 ? r.yMin : r.yMax);
                    if (clean) { CriptaStructure.CornerPost(parent, owner, corner + new Vector3(sx * 0.5f, 0f, sz * 0.5f), 3f); continue; }
                    var go = EnvironmentKit.Place("ParedeCantoA", parent, corner + new Vector3(sx * 0.5f, 0f, sz * 0.5f), 0f, instanceName: owner + "_corner");
                    go.name = owner + "_corner";
                }
            }
        }


        // ------------------------------------------------------------------------------------------------ luz, ambiente e pos-processamento

        public const string VolumePath = "Assets/Art/Environment/VP_Cripta.asset";

        public static Color Hex(string html)
        {
            ColorUtility.TryParseHtmlString(html, out var c);
            return c;
        }

        /// <summary>
        /// Luz direcional, ambiente em gradiente e o Volume global (spec_cenario.md): sol #FFE2B8 a 0,9; ambiente topo #5A5078, equador #403A58, chao
        /// #2A2538; tonemapping ACES, ajuste de cor (contraste +8, saturacao -8), split toning (sombras violeta, realces ambar), bloom, vinheta.
        /// Chamado pelos builders da Cripta e do Refugio (cena nova ja aberta). O SSAO e do renderer (PC_Renderer), nao do Volume.
        /// </summary>
        public static void ApplyLook(Camera camera)
        {
            RenderSettings.skybox = null;
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = Hex("#4E5C74");
            RenderSettings.ambientEquatorColor = Hex("#37424F");
            RenderSettings.ambientGroundColor = Hex("#232B36");
            RenderSettings.fog = false;

            var lightGo = new GameObject("Directional Light");
            lightGo.transform.rotation = Quaternion.Euler(50f, -25f, 0f);
            var light = lightGo.AddComponent<Light>();
            light.type = LightType.Directional;
            light.color = Hex("#FFE2B8");
            light.intensity = 0.9f;
            light.shadows = LightShadows.Soft;

            var volume = new GameObject("PostProcess").AddComponent<Volume>();
            volume.isGlobal = true;
            volume.priority = 1f;
            volume.sharedProfile = EnsureVolumeProfile();
            if (camera != null) EnablePostProcessing(camera);
        }

        public static void EnablePostProcessing(Camera camera)
        {
            var data = camera.GetComponent<UniversalAdditionalCameraData>();
            if (data == null) data = camera.gameObject.AddComponent<UniversalAdditionalCameraData>();
            data.renderPostProcessing = true;
        }

        public static VolumeProfile EnsureVolumeProfile()
        {
            SandboxBuilder.EnsureDir("Assets/Art/Environment");
            if (AssetDatabase.LoadAssetAtPath<VolumeProfile>(VolumePath) != null) AssetDatabase.DeleteAsset(VolumePath);
            var profile = ScriptableObject.CreateInstance<VolumeProfile>();
            profile.name = "VP_Cripta";
            AssetDatabase.CreateAsset(profile, VolumePath);

            T Add<T>() where T : VolumeComponent
            {
                var c = profile.Add<T>(true);
                c.name = typeof(T).Name;
                AssetDatabase.AddObjectToAsset(c, profile);
                return c;
            }

            Add<Tonemapping>().mode.Override(TonemappingMode.ACES);
            var adjust = Add<ColorAdjustments>();
            // O ACES + a cena escura da paleta (albedo ~0,07 linear) comem ~2 EV: a exposicao de +1,4 EV devolve o piso ao tom do alvo
            // (sombra ~#4E4257 a #5A5078) e as poças quentes ficam por cima. O balanco de branco tira o magenta que a luz quente sobre o ambiente
            // violeta cria no piso (tinta -22, temperatura -5), e o split toning das sombras e mais claro que o do spec (#5A4C8C escureceria a cena).
            adjust.postExposure.Override(1.6f);
            adjust.contrast.Override(16f);
            adjust.saturation.Override(-2f);
            var balance = Add<WhiteBalance>();
            balance.temperature.Override(10f); // rev2: mais quente, menos roxo
            balance.tint.Override(-24f);
            var split = Add<SplitToning>();
            split.shadows.Override(Hex("#9BA6B4"));
            split.highlights.Override(Hex("#FFC88A"));
            split.balance.Override(-20f);
            var bloom = Add<Bloom>();
            bloom.threshold.Override(1.1f);
            bloom.intensity.Override(0.25f);
            bloom.scatter.Override(0.6f);
            bloom.downscale.Override(BloomDownscaleMode.Half);
            var vignette = Add<Vignette>();
            vignette.intensity.Override(0.22f);
            vignette.smoothness.Override(0.6f);
            vignette.rounded.Override(true);
            EditorUtility.SetDirty(profile);
            AssetDatabase.SaveAssets();
            return profile;
        }

        // ------------------------------------------------------------------------------------------------ fogo

        public static FireSource AddFire(GameObject go, bool flame, float height, Color color, float intensity, float range, float scale = 1f)
        {
            var f = go.AddComponent<FireSource>();
            f.flame = flame;
            f.flameHeight = height;
            f.lightColor = color;
            f.lightIntensity = intensity;
            f.lightRange = range;
            f.flameScale = scale;
            return f;
        }

        public static void AddBrazierFire(GameObject brazier) =>
            AddFire(brazier, true, 1.45f, Hex("#FFB86B"), 7f, 7f, 1f);

        public static void AddCandleFire(GameObject candles) =>
            AddFire(candles, true, 0.55f, Hex("#FFC882"), 2.2f, 4f, 0.35f);

        /// <summary>Cria o pool de luzes e chamas (ate 6 pontuais, as mais proximas do alvo) ligado ao alvo (heroi) dado.</summary>
        public static FirePool AddFirePool(Transform target)
        {
            var go = new GameObject("FirePool");
            var pool = go.AddComponent<FirePool>();
            SandboxBuilder.SetRef(pool, "flameMaterial", EnsureFlameMaterial());
            if (target != null) SandboxBuilder.SetRef(pool, "target", target);
            return pool;
        }

        public static Material EnsureFlameMaterial()
        {
            SandboxBuilder.EnsureDir(EnvironmentKit.MaterialDir);
            var texPath = EnvironmentKit.MaterialDir + "/T_FireSoft.png";
            if (AssetDatabase.LoadAssetAtPath<Texture2D>(texPath) == null)
            {
                const int size = 32;
                var tex = new Texture2D(size, size, TextureFormat.RGBA32, false);
                for (var y = 0; y < size; y++)
                {
                    for (var x = 0; x < size; x++)
                    {
                        var d = new Vector2(x - (size - 1) * 0.5f, y - (size - 1) * 0.5f).magnitude / (size * 0.5f);
                        var a = Mathf.Clamp01(1f - d);
                        a = a * a * (3f - 2f * a);
                        tex.SetPixel(x, y, new Color(1f, 1f, 1f, a));
                    }
                }
                System.IO.File.WriteAllBytes(System.IO.Path.GetFullPath(System.IO.Path.Combine(Application.dataPath, "../" + texPath)), tex.EncodeToPNG());
                Object.DestroyImmediate(tex);
                AssetDatabase.ImportAsset(texPath, ImportAssetOptions.ForceSynchronousImport);
            }
            var path = EnvironmentKit.MaterialDir + "/M_Cripta_Flame.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Particles/Unlit"));
                AssetDatabase.CreateAsset(mat, path);
            }
            mat.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(texPath));
            mat.SetColor("_BaseColor", Color.white);
            mat.SetFloat("_Surface", 1f);       // transparente
            mat.SetFloat("_Blend", 2f);         // aditivo
            mat.SetFloat("_SrcBlend", 5f);      // SrcAlpha
            mat.SetFloat("_DstBlend", 1f);      // One
            mat.SetFloat("_ZWrite", 0f);
            mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            mat.renderQueue = (int)RenderQueue.Transparent;
            EditorUtility.SetDirty(mat);
            return mat;
        }
    }
}
