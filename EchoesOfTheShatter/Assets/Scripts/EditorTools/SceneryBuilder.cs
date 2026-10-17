using System;
using System.Collections.Generic;
using Echoes.Presentation;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
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

        /// <summary>Piso na grade de 2 m a partir do canto minimo do retangulo, alternando PisoLiso / PisoQuebrado / PisoRuna. Uma malha por variante (CombineMeshes).</summary>
        public static void BuildFloor(Transform parent, string owner, Rect rect, IList<Rect> holes)
        {
            var rng = Rng(owner);
            var names = new[] { "PisoLiso", "PisoQuebrado", "PisoRuna" };
            var lists = new[] { new List<CombineInstance>(), new List<CombineInstance>(), new List<CombineInstance>() };
            var nx = Mathf.Max(1, Mathf.RoundToInt(rect.width / Module));
            var nz = Mathf.Max(1, Mathf.RoundToInt(rect.height / Module));
            var cellX = rect.width / nx;
            var cellZ = rect.height / nz;
            for (var ix = 0; ix < nx; ix++)
            {
                for (var iz = 0; iz < nz; iz++)
                {
                    var center = new Vector3(rect.xMin + cellX * (ix + 0.5f), 0f, rect.yMin + cellZ * (iz + 0.5f));
                    var roll = rng.NextDouble(); // sempre consome 1 sorteio por celula: um buraco nao desloca o resto
                    if (Inside(holes, center)) continue;
                    var v = roll < 0.72 ? 0 : roll < 0.90 ? 1 : 2;
                    var piece = EnvironmentKit.Get(names[v]);
                    var scale = new Vector3(cellX / Module, 1f, cellZ / Module);
                    lists[v].Add(new CombineInstance { mesh = piece.Mesh, transform = Matrix4x4.TRS(center, Quaternion.identity, scale) * piece.MeshMatrix });
                }
            }
            for (var v = 0; v < 3; v++)
            {
                if (lists[v].Count == 0) continue;
                var mesh = new Mesh { name = $"Floor_{owner}_{names[v]}", indexFormat = IndexFormat.UInt32 };
                mesh.CombineMeshes(lists[v].ToArray(), true, true);
                mesh.RecalculateBounds();
                SandboxBuilder.EnsureDir(EnvironmentKit.GeneratedDir + "/Floor");
                mesh = SandboxBuilder.SaveMesh(mesh, $"{EnvironmentKit.GeneratedDir}/Floor/{Sanitize(owner)}_{names[v]}.asset");
                var go = new GameObject($"Floor_{names[v]}");
                go.transform.SetParent(parent, false);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var mr = go.AddComponent<MeshRenderer>();
                mr.sharedMaterial = EnvironmentKit.Get(names[v]).Material;
                mr.shadowCastingMode = ShadowCastingMode.Off;
                mr.receiveShadows = true;
                GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);
            }
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
        public static void WallRun(Transform parent, string owner, bool alongX, float line, float from, float to, bool positiveOutside)
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
        public static void CornerPosts(Transform parent, string owner, Rect r)
        {
            foreach (var sx in new[] { -1, 1 })
            {
                foreach (var sz in new[] { -1, 1 })
                {
                    var corner = new Vector3(sx < 0 ? r.xMin : r.xMax, 0f, sz < 0 ? r.yMin : r.yMax);
                    var go = EnvironmentKit.Place("ParedeCantoA", parent, corner + new Vector3(sx * 0.5f, 0f, sz * 0.5f), 0f, instanceName: owner + "_corner");
                    go.name = owner + "_corner";
                }
            }
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
            AddFire(brazier, true, 1.45f, new Color(1f, 0.55f, 0.2f), 2.2f, 9f, 1f);

        public static void AddCandleFire(GameObject candles) =>
            AddFire(candles, true, 0.55f, new Color(1f, 0.78f, 0.42f), 0.9f, 5f, 0.35f);

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
