using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Kit de cenario pintado da Cripta (26 pecas SM_Cripta_* na grade de 2 m, com T_Cripta_*_BC/_M e um json de colisor e pivo por peca).
    /// Importa de <c>modelos3d/cenario_final</c> para Assets/Art/Environment/Cripta, cria um material por peca (M_Cripta_&lt;Peca&gt;) no
    /// <c>SG_Character</c> (nao existe SG_Environment ainda: albedo + mascara R emissao, G rim, B tinta, igual aos personagens) e instancia as
    /// pecas na cena com os colisores do json (caixas simples; a rampa da escada e uma cunha convexa; nunca a malha visual).
    /// </summary>
    public static class EnvironmentKit
    {
        public const string Dir = "Assets/Art/Environment/Cripta";
        public const string MaterialDir = "Assets/Art/Materials/Environment";
        public const string GeneratedDir = "Assets/Art/Generated/Cripta";
        public const string ShaderUsed = "SG_Character";
        const string DefaultSource = "D:/openclaude/_trabalho-claude/modelos3d/cenario_final";

        public static readonly string[] Names =
        {
            "AbismoBordo", "ArcoRuina", "BlocoA", "BlocoB", "BlocoC", "BlocoD", "Braseiro", "Escada", "Estandarte", "Ossos",
            "ParedeCantoA", "ParedeReta", "ParedeRuina", "PedraE", "PedraF", "PilarInteiro", "PilarQuebrado", "PisoLiso", "PisoQuebrado", "PisoRuna",
            "PortalAberto", "PortalPorta", "RuinaGrande", "SarcofagoAberto", "SarcofagoFechado", "Velas",
        };

        [Serializable] sealed class BoundsJson { public float[] center; public float[] size; }
        [Serializable] sealed class ColliderJson { public string type; public float[] center; public float[] size; public BoundsJson bounds; }
        [Serializable] sealed class PieceJson { public string pivot; public float[] size_m_unity; public ColliderJson[] colliders; }

        public struct BoxDef { public Vector3 Center, Size; }

        public sealed class Piece
        {
            public string Name;
            public GameObject Model;
            public Material Material;
            public Vector3 Size;
            public string Pivot;
            public bool IsRamp;
            public BoxDef[] Boxes = Array.Empty<BoxDef>();
            public Mesh Mesh;               // malha da peca (MeshFilter) e a matriz dela relativa a raiz do FBX
            public Matrix4x4 MeshMatrix = Matrix4x4.identity;
        }

        static readonly Dictionary<string, Piece> cache = new Dictionary<string, Piece>();
        static Mesh wedge;

        static string SourceDir
        {
            get
            {
                var env = Environment.GetEnvironmentVariable("ECHOES_ENV_KIT");
                return string.IsNullOrEmpty(env) ? DefaultSource : env;
            }
        }

        /// <summary>Copia o que faltar (ou mudou de tamanho) do kit de origem e reimporta. Sem a origem, usa o que ja esta no projeto.</summary>
        public static void Import()
        {
            SandboxBuilder.EnsureDir(Dir);
            var changed = false;
            if (Directory.Exists(SourceDir))
            {
                foreach (var name in Names)
                {
                    foreach (var file in new[] { $"SM_Cripta_{name}.fbx", $"SM_Cripta_{name}.json", $"T_Cripta_{name}_BC.png", $"T_Cripta_{name}_M.png" })
                    {
                        var source = Path.Combine(SourceDir, file);
                        var target = Path.Combine(Application.dataPath, "../" + Dir, file);
                        if (!File.Exists(source)) continue;
                        if (File.Exists(target) && new FileInfo(target).Length == new FileInfo(source).Length) continue;
                        File.Copy(source, target, true);
                        changed = true;
                    }
                }
            }
            if (changed) AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            cache.Clear();
            wedge = null;
        }

        public static Piece Get(string name)
        {
            if (cache.TryGetValue(name, out var cached) && cached.Model != null) return cached;
            var piece = new Piece { Name = name };
            piece.Model = AssetDatabase.LoadAssetAtPath<GameObject>($"{Dir}/SM_Cripta_{name}.fbx");
            if (piece.Model == null) throw new InvalidOperationException($"Peca do kit ausente: {Dir}/SM_Cripta_{name}.fbx (rode Echoes > Importar kit de cenario).");
            piece.Material = EnsureMaterial(name);

            var json = AssetDatabase.LoadAssetAtPath<TextAsset>($"{Dir}/SM_Cripta_{name}.json");
            if (json != null)
            {
                var data = JsonUtility.FromJson<PieceJson>(json.text);
                piece.Pivot = data.pivot;
                if (data.size_m_unity != null && data.size_m_unity.Length == 3) piece.Size = new Vector3(data.size_m_unity[0], data.size_m_unity[1], data.size_m_unity[2]);
                var boxes = new List<BoxDef>();
                foreach (var c in data.colliders ?? Array.Empty<ColliderJson>())
                {
                    if (c.type != null && c.type.StartsWith("MeshCollider", StringComparison.Ordinal))
                    {
                        piece.IsRamp = true;
                        if (c.bounds != null && c.bounds.size != null) boxes.Add(new BoxDef { Center = V(c.bounds.center), Size = V(c.bounds.size) });
                        continue;
                    }
                    if (c.center != null && c.size != null) boxes.Add(new BoxDef { Center = V(c.center), Size = V(c.size) });
                }
                piece.Boxes = boxes.ToArray();
            }

            var temp = (GameObject)PrefabUtility.InstantiatePrefab(piece.Model);
            temp.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            var filter = temp.GetComponentInChildren<MeshFilter>();
            if (filter != null)
            {
                piece.Mesh = filter.sharedMesh;
                piece.MeshMatrix = temp.transform.worldToLocalMatrix * filter.transform.localToWorldMatrix;
            }
            Object.DestroyImmediate(temp);
            cache[name] = piece;
            return piece;
        }

        static Vector3 V(float[] a) => new Vector3(a[0], a[1], a[2]);

        /// <summary>M_Cripta_&lt;Peca&gt;: SG_Character com o albedo e a mascara da peca (sem tinta de raridade).</summary>
        public static Material EnsureMaterial(string name)
        {
            SandboxBuilder.EnsureDir(MaterialDir);
            var shader = AssetDatabase.LoadAssetAtPath<Shader>(CharacterPrefabBuilder.ShaderPath);
            if (shader == null) throw new InvalidOperationException("Shader ausente: " + CharacterPrefabBuilder.ShaderPath);
            var path = $"{MaterialDir}/M_Cripta_{name}.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(shader);
                AssetDatabase.CreateAsset(mat, path);
            }
            mat.shader = shader;
            mat.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>($"{Dir}/T_Cripta_{name}_BC.png"));
            mat.SetTexture("_MaskMap", AssetDatabase.LoadAssetAtPath<Texture2D>($"{Dir}/T_Cripta_{name}_M.png"));
            mat.SetFloat("_HitFlash", 0f);
            mat.SetFloat("_Dissolve", 0f);
            mat.SetFloat("_RimMaskInfluence", 1f);
            RarityTintBuilder.CreateOrUpdate().Apply(mat, Echoes.Presentation.RarityTier.Normal);
            EditorUtility.SetDirty(mat);
            return mat;
        }

        /// <summary>Instancia a peca na cena (pivo da peca em <paramref name="position"/>, giro em Y, escala opcional) com os colisores do json.</summary>
        public static GameObject Place(string name, Transform parent, Vector3 position, float yaw, Vector3? scale = null, bool colliders = true, bool castShadow = false, string instanceName = null)
        {
            var piece = Get(name);
            var go = (GameObject)PrefabUtility.InstantiatePrefab(piece.Model);
            go.name = instanceName ?? name;
            go.transform.SetParent(parent, false);
            go.transform.SetPositionAndRotation(position, Quaternion.Euler(0f, yaw, 0f));
            if (scale.HasValue) go.transform.localScale = scale.Value;
            foreach (var c in go.GetComponentsInChildren<Collider>()) Object.DestroyImmediate(c);
            foreach (var r in go.GetComponentsInChildren<Renderer>())
            {
                r.sharedMaterial = piece.Material;
                r.shadowCastingMode = castShadow ? ShadowCastingMode.On : ShadowCastingMode.Off; // json: cenario nao projeta sombra
                r.receiveShadows = true;
            }
            if (colliders) AddColliders(go, piece);
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);
            return go;
        }

        public static void AddColliders(GameObject go, Piece piece)
        {
            foreach (var box in piece.Boxes)
            {
                if (piece.IsRamp) continue;
                var c = go.AddComponent<BoxCollider>();
                c.center = box.Center;
                c.size = box.Size;
            }
            if (piece.IsRamp)
            {
                var mc = go.AddComponent<MeshCollider>();
                mc.convex = true;
                mc.sharedMesh = Wedge();
            }
        }

        /// <summary>Cunha de 2 m de base e 1 m de altura que sobe para +Z (rampa da escada; o topo fica na frente).</summary>
        static Mesh Wedge()
        {
            if (wedge != null) return wedge;
            SandboxBuilder.EnsureDir(GeneratedDir);
            var path = GeneratedDir + "/Cripta_StairRamp.asset";
            var mesh = new Mesh { name = "Cripta_StairRamp" };
            mesh.vertices = new[]
            {
                new Vector3(-1f, 0f, -1f), new Vector3(1f, 0f, -1f), new Vector3(-1f, 0f, 1f), new Vector3(1f, 0f, 1f),
                new Vector3(-1f, 1f, 1f), new Vector3(1f, 1f, 1f),
            };
            mesh.triangles = new[]
            {
                0, 2, 1, 1, 2, 3,          // base
                0, 1, 5, 0, 5, 4,          // rampa
                2, 4, 5, 2, 5, 3,          // face de tras (topo)
                0, 4, 2,                   // lado esquerdo
                1, 3, 5,                   // lado direito
            };
            mesh.RecalculateNormals();
            wedge = SandboxBuilder.SaveMesh(mesh, path);
            return wedge;
        }

        /// <summary>Escala do bloco do colisor sobre a peca: tamanho (m) do json sobre o tamanho nominal 1.</summary>
        public static Vector3 Size(string name) => Get(name).Size;

        [MenuItem("Echoes/Importar kit de cenario")]
        public static void ImportMenu()
        {
            Import();
            foreach (var name in Names) Get(name);
            AssetDatabase.SaveAssets();
            Debug.Log($"[EnvironmentKit] {Names.Length} pecas importadas em {Dir}; materiais em {MaterialDir} (shader {ShaderUsed}).");
        }
    }
}
