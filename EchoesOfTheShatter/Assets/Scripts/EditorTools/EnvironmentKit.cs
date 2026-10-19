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
    /// Importa de <c>modelos3d/cenario_final</c> (ou, quando existe, da peca com chanfro em <c>art-src/modelos/cenario_chanfro</c>, gerada por
    /// <c>env_bevel_kit.py</c>) para Assets/Art/Environment/Cripta, cria um material por peca (M_Cripta_&lt;Peca&gt;) no <c>Env_Scenery</c> e instancia as
    /// pecas na cena com os colisores do json (caixas simples; a rampa da escada e uma cunha convexa; nunca a malha visual). O piso nao usa mais as
    /// pecas PisoLiso/PisoQuebrado/PisoRuna: e uma malha plana por sala com as 2 lajotas projetadas no mundo (<see cref="SceneryBuilder.BuildFloor"/>).
    /// Alvenaria (parede, canto, pilar, bloco, arco, ruina) usa as texturas novas projetadas no mundo; o resto (braseiro, sarcofago, estandarte...) segue
    /// com o albedo pintado da peca.
    /// </summary>
    public static class EnvironmentKit
    {
        public const string Dir = "Assets/Art/Environment/Cripta";
        public const string MaterialDir = "Assets/Art/Materials/Environment";
        public const string GeneratedDir = "Assets/Art/Generated/Cripta";
        public const string ShaderUsed = "Env_Scenery";
        public const string ShaderPath = "Assets/Art/Materials/Masters/Env_Scenery.shader";
        public const string TextureDir = "Assets/Art/Environment/Textures";
        const string DefaultSource = "D:/openclaude/_trabalho-claude/modelos3d/cenario_final";

        /// <summary>Pecas com chanfro e normais suaves (saida do env_bevel_kit.py), versionadas no repositorio; vencem a peca de origem.</summary>
        public static string BeveledDir => Path.GetFullPath(Path.Combine(Application.dataPath, "../../art-src/modelos/cenario_chanfro"));

        public enum Look { Kit, Floor, Wall, Band, Decal, Rune }

        /// <summary>Como cada peca recebe o albedo: faixa (parede reta), alvenaria (projecao no mundo) ou o albedo pintado da peca (kit).</summary>
        public static Look LookOf(string name)
        {
            switch (name)
            {
                case "ParedeReta":
                case "ParedeRuina":
                    return Look.Band;
                case "ParedeCantoA":
                case "PilarInteiro":
                case "PilarQuebrado":
                case "BlocoA":
                case "BlocoB":
                case "BlocoC":
                case "BlocoD":
                case "ArcoRuina":
                case "RuinaGrande":
                case "AbismoBordo":
                    return Look.Wall;
                default:
                    return Look.Kit;
            }
        }

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
                        var beveled = Path.Combine(BeveledDir, file);
                        if (File.Exists(beveled)) source = beveled;
                        var target = Path.Combine(Application.dataPath, "../" + Dir, file);
                        if (!File.Exists(source)) continue;
                        if (File.Exists(target) && new FileInfo(target).Length == new FileInfo(source).Length) continue;
                        File.Copy(source, target, true);
                        changed = true;
                    }
                }
            }
            if (changed) AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            EnsureTextures();
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

        /// <summary>Texturas do cenario: sRGB, mipmap, aniso 4x, repeat (glifo: clamp, com alfa); 2048 no PC.</summary>
        public static void EnsureTextures()
        {
            foreach (var file in new[] { "T_Env_PisoA", "T_Env_PisoB", "T_Env_Parede", "T_Env_Faixa", "T_Env_Glifo" })
            {
                var path = $"{TextureDir}/{file}.png";
                if (!(AssetImporter.GetAtPath(path) is TextureImporter importer)) continue;
                var glyph = file == "T_Env_Glifo";
                var wantWrap = glyph ? TextureWrapMode.Clamp : TextureWrapMode.Repeat;
                if (importer.sRGBTexture && importer.mipmapEnabled && importer.anisoLevel == 4 && importer.wrapMode == wantWrap && importer.maxTextureSize == 2048 && importer.alphaIsTransparency == glyph) continue;
                importer.textureType = TextureImporterType.Default;
                importer.sRGBTexture = true;
                importer.mipmapEnabled = true;
                importer.anisoLevel = 4;
                importer.wrapMode = wantWrap;
                importer.filterMode = FilterMode.Trilinear;
                importer.maxTextureSize = 2048;
                importer.alphaSource = glyph ? TextureImporterAlphaSource.FromInput : TextureImporterAlphaSource.None;
                importer.alphaIsTransparency = glyph;
                importer.textureCompression = TextureImporterCompression.Compressed;
                importer.SaveAndReimport();
            }
        }

        static Texture2D Tex(string file) => AssetDatabase.LoadAssetAtPath<Texture2D>($"{TextureDir}/{file}.png");

        static Shader EnvShader()
        {
            var shader = AssetDatabase.LoadAssetAtPath<Shader>(ShaderPath);
            if (shader == null) throw new InvalidOperationException("Shader ausente: " + ShaderPath);
            return shader;
        }

        static Material LoadOrCreate(string path)
        {
            SandboxBuilder.EnsureDir(MaterialDir);
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(EnvShader());
                AssetDatabase.CreateAsset(mat, path);
            }
            mat.shader = EnvShader();
            return mat;
        }

        static void SetLook(Material mat, Look look)
        {
            foreach (var k in new[] { "_ENV_FLOOR", "_ENV_WALL", "_ENV_BAND", "_ENV_DECAL", "_ENV_RUNE" }) mat.DisableKeyword(k);
            switch (look)
            {
                case Look.Floor: mat.EnableKeyword("_ENV_FLOOR"); break;
                case Look.Wall: mat.EnableKeyword("_ENV_WALL"); break;
                case Look.Band: mat.EnableKeyword("_ENV_BAND"); break;
                case Look.Decal: mat.EnableKeyword("_ENV_DECAL"); break;
                case Look.Rune: mat.EnableKeyword("_ENV_RUNE"); break;
            }
            mat.SetFloat("_PoolStrength", look == Look.Kit ? 1.0f : 1.5f); // pecas pintadas (pilares ao lado do braseiro) estouravam com 1,5
            mat.SetFloat("_PoolSoftClip", look == Look.Kit ? 1.2f : look == Look.Wall || look == Look.Band ? 0.7f : 0.3f); // pedra clara comprime mais perto da fonte
            // As faces verticais pegam pouco do sol de cima-esquerda: parede, faixa e pecas pintadas sobem na tinta para ler como pedra clara do alvo.
            var gain = look == Look.Wall || look == Look.Band ? 1.4f : look == Look.Floor || look == Look.Decal || look == Look.Rune ? 1f : 1.0f;
            var cool = look == Look.Wall || look == Look.Band; // pedra cinza-azulada fria: a textura pintada da parede ainda e violeta, a tinta tira o roxo
            mat.SetColor("_Tint", cool ? new Color(gain * 1.0f, gain * 1.12f, gain * 0.80f, 1f) : new Color(gain, gain, gain, 1f));
            mat.SetColor("_ShadowTint", new Color(0.28f, 0.34f, 0.50f, 1f));
            // Piso limpo e uniforme: uma lajota so (sem celulas A/B, giro ou espelho), contraste e manchas de brilho baixos.
            mat.SetFloat("_CellSize", look == Look.Floor ? 0f : 12f);
            mat.SetFloat("_FloorTile", 8f);
            mat.SetFloat("_WallTile", 2.5f); // alvenaria mais fina: o heroi (chibi) nao parece pequeno ao lado dos blocos
            mat.SetFloat("_FloorContrast", look == Look.Floor ? 1.0f : 1.35f);
            mat.SetFloat("_Variation", look == Look.Floor ? 0.0f : 0.07f);
            mat.SetTexture("_MapA", Tex("T_Env_PisoA"));
            mat.SetTexture("_MapB", Tex("T_Env_PisoB"));
            mat.SetTexture("_WallMap", Tex("T_Env_Parede"));
            mat.SetTexture("_BandMap", Tex("T_Env_Faixa"));
            var decal = look == Look.Decal;
            mat.SetFloat("_SrcBlend", decal ? (float)BlendMode.SrcAlpha : (float)BlendMode.One);
            mat.SetFloat("_DstBlend", decal ? (float)BlendMode.OneMinusSrcAlpha : (float)BlendMode.Zero);
            mat.SetFloat("_ZWrite", decal ? 0f : 1f);
            mat.renderQueue = decal ? (int)RenderQueue.Geometry + 50 : (int)RenderQueue.Geometry;
            mat.SetOverrideTag("RenderType", decal ? "Transparent" : "Opaque");
        }

        /// <summary>M_Env_Piso: o piso das salas e corredores (lajotas A e B projetadas no mundo, mistura por ruido de baixa frequencia).</summary>
        public static Material EnsureFloorMaterial()
        {
            EnsureTextures();
            var mat = LoadOrCreate(MaterialDir + "/M_Env_Piso.mat");
            SetLook(mat, Look.Floor);
            EditorUtility.SetDirty(mat);
            return mat;
        }

        /// <summary>M_Env_Pedra: pedra clara em projecao no mundo (circulos de checkpoint e de portal, como a parede).</summary>
        public static Material EnsureStoneMaterial()
        {
            EnsureTextures();
            var mat = LoadOrCreate(MaterialDir + "/M_Env_Pedra.mat");
            SetLook(mat, Look.Wall);
            mat.SetColor("_Tint", new Color(0.84f, 0.88f, 0.84f, 1f)); // paredes e pilares da Cripta: cinza-azulado frio, sem estourar
            EditorUtility.SetDirty(mat);
            return mat;
        }

        /// <summary>M_Env_Runa / M_Env_RunaPortal: runas que acendem (emissao pura com pulso). Ambar no checkpoint, violeta no portal.</summary>
        public static Material EnsureRuneMaterial(bool portal)
        {
            EnsureTextures();
            var mat = LoadOrCreate(MaterialDir + (portal ? "/M_Env_RunaPortal.mat" : "/M_Env_Runa.mat"));
            SetLook(mat, Look.Rune);
            // Emissao baixa de proposito: com +1,6 EV e o ACES, acima de ~1,3 a cor desatura para branco; abaixo disso le ambar depois do bloom.
            mat.SetColor("_RuneColor", portal ? new Color(0.55f, 0.4f, 1f, 1f) : new Color(1f, 0.52f, 0.1f, 1f));
            mat.SetFloat("_RuneIntensity", portal ? 0.7f : 0.55f);
            EditorUtility.SetDirty(mat);
            return mat;
        }

        /// <summary>M_Env_Grade: ferro escuro da grade do portao da arena (modo kit, sem textura: so a tinta).</summary>
        public static Material EnsureGrateMaterial()
        {
            EnsureTextures();
            var mat = LoadOrCreate(MaterialDir + "/M_Env_Grade.mat");
            SetLook(mat, Look.Kit);
            mat.SetColor("_Tint", new Color(0.34f, 0.32f, 0.4f, 1f));
            EditorUtility.SetDirty(mat);
            return mat;
        }

        /// <summary>M_Env_Glifo: simbolo de bussola dourado no chao (so em checkpoint e portal).</summary>
        public static Material EnsureGlyphMaterial()
        {
            EnsureTextures();
            var mat = LoadOrCreate(MaterialDir + "/M_Env_Glifo.mat");
            mat.SetTexture("_BaseMap", Tex("T_Env_Glifo"));
            SetLook(mat, Look.Decal);
            EditorUtility.SetDirty(mat);
            return mat;
        }

        /// <summary>M_Cripta_&lt;Peca&gt;: Env_Scenery, em modo faixa/alvenaria (texturas novas no mundo) ou kit (albedo e mascara da peca).</summary>
        public static Material EnsureMaterial(string name)
        {
            EnsureTextures();
            var mat = LoadOrCreate($"{MaterialDir}/M_Cripta_{name}.mat");
            mat.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>($"{Dir}/T_Cripta_{name}_BC.png"));
            mat.SetTexture("_MaskMap", AssetDatabase.LoadAssetAtPath<Texture2D>($"{Dir}/T_Cripta_{name}_M.png"));
            SetLook(mat, LookOf(name));
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
