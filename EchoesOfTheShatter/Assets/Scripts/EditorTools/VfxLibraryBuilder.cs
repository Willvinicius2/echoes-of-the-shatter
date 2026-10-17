using System;
using System.Collections.Generic;
using System.IO;
using Echoes.Presentation;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Biblioteca de VFX das habilidades (docs/18 seção 6), reproduzível: texturas de efeito, materiais, malhas e prefabs em
    /// Assets/Art/VFX, e as entradas <see cref="SkillPresentationSet.vfx"/> dos SO_SkillPresentation_* (Guerreiro, Arqueiro, Mago, Arqueiro
    /// Fantasma) mais o <see cref="SkillVfxLibrary"/> em Resources. Idempotente: roda de novo e regrava tudo mantendo os GUIDs.
    /// Menu: Echoes ▸ Construir biblioteca de VFX. Linha de comando: <c>-executeMethod Echoes.EditorTools.VfxLibraryBuilder.BuildBatch</c>.
    /// Os valores de apresentação (tamanho, duração, cor) estão aqui só como dado de autoria dos prefabs e dos SO; nenhum é balanceamento.
    /// </summary>
    public static partial class VfxLibraryBuilder
    {
        public const string Root = "Assets/Art/VFX";
        public const string PrefabDir = Root + "/Skills";
        public const string MaterialDir = Root + "/Materials";
        public const string MeshDir = Root + "/Meshes";
        public const string ShaderPath = Root + "/Shaders/EchoesVfxFresnelDome.shader";
        public const string LibraryPath = "Assets/Resources/Echoes/SO_SkillVfxLibrary.asset";

        [MenuItem("Echoes/Construir biblioteca de VFX")]
        public static void Build()
        {
            EnsureDir(Root);
            EnsureDir(TextureDir);
            EnsureDir(MaterialDir);
            EnsureDir(MeshDir);
            EnsureDir(PrefabDir);
            EnsureDir("Assets/Resources/Echoes");
            AssetDatabase.Refresh();

            BuildTextures();
            BuildMaterials();
            BuildMeshes();
            BuildPrefabs();
            BuildSets();
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log("[VfxLibrary] Biblioteca de VFX construida em " + Root);
        }

        public static void BuildBatch()
        {
            try
            {
                Build();
                if (Application.isBatchMode) EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Debug.LogError("[VfxLibrary] Falhou: " + e);
                if (Application.isBatchMode) EditorApplication.Exit(1);
            }
        }

        static void EnsureDir(string assetPath)
        {
            var full = Path.GetFullPath(Path.Combine(Application.dataPath, "..", assetPath));
            if (!Directory.Exists(full)) Directory.CreateDirectory(full);
        }

        // ------------------------------------------------------------------------------------------------ texturas

        static Texture2D tSoft, tCore, tRing, tRingSoft, tStar4, tStar6, tStreak, tSmoke, tFlame, tSlash, tSlashGold, tScorch, tHex, tBeam, tRune, tNoise, tSpark, tTrail;

        static void BuildTextures()
        {
            tSoft = TexSoft();
            tCore = TexCore();
            tRing = TexRing();
            tRingSoft = TexRingSoft();
            tStar4 = TexStar4();
            tStar6 = TexStar6();
            tStreak = TexStreak();
            tSmoke = TexSmoke();
            tFlame = TexFlame();
            tSlash = TexSlash("T_VFX_Slash", false);
            tSlashGold = TexSlash("T_VFX_SlashGold", true);
            tScorch = TexScorch();
            tHex = TexHex();
            tBeam = TexBeam();
            tRune = TexRune();
            tNoise = TexNoise();
            tSpark = TexSpark();
            tTrail = TexTrail();
        }

        // ------------------------------------------------------------------------------------------------ materiais

        enum Blend { Additive, Alpha, Opaque }

        static Material mAddSoft, mAddCore, mAddRing, mAddRingSoft, mAddStar4, mAddStar6, mAddStreak, mAddFlame, mAddSmoke, mAddHex, mAddSlash, mAddSlashGold,
            mAddBeam, mAddRune, mAddSpark, mAddTrail, mAlphaSmoke, mAlphaScorch, mAlphaGhostWisp, mAlphaGhostTrail, mMeshArrow, mMeshGhost, mMeshOutline, mMeshCrystal, mMeshBeam, mDome, mFloor;

        static Material MakeMaterial(string name, Texture2D texture, Blend blend, float hdr = 1.4f, bool cullFront = false, Color? tint = null)
        {
            var path = $"{MaterialDir}/{name}.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            var shader = Shader.Find("Universal Render Pipeline/Particles/Unlit");
            if (mat == null)
            {
                mat = new Material(shader);
                AssetDatabase.CreateAsset(mat, path);
            }
            mat.shader = shader;
            mat.SetTexture("_BaseMap", texture);
            var baseColor = tint ?? Color.white;
            mat.SetColor("_BaseColor", new Color(baseColor.r * hdr, baseColor.g * hdr, baseColor.b * hdr, baseColor.a));
            mat.SetFloat("_Cull", cullFront ? 1f : 0f);
            switch (blend)
            {
                case Blend.Additive:
                    mat.SetFloat("_Surface", 1f);
                    mat.SetFloat("_Blend", 2f);
                    mat.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
                    mat.SetFloat("_DstBlend", (float)BlendMode.One);
                    mat.SetFloat("_ZWrite", 0f);
                    mat.SetOverrideTag("RenderType", "Transparent");
                    mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                    mat.renderQueue = (int)RenderQueue.Transparent;
                    break;
                case Blend.Alpha:
                    mat.SetFloat("_Surface", 1f);
                    mat.SetFloat("_Blend", 0f);
                    mat.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
                    mat.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
                    mat.SetFloat("_ZWrite", 0f);
                    mat.SetOverrideTag("RenderType", "Transparent");
                    mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                    mat.renderQueue = (int)RenderQueue.Transparent;
                    break;
                default:
                    mat.SetFloat("_Surface", 0f);
                    mat.SetFloat("_Blend", 0f);
                    mat.SetFloat("_SrcBlend", (float)BlendMode.One);
                    mat.SetFloat("_DstBlend", (float)BlendMode.Zero);
                    mat.SetFloat("_ZWrite", 1f);
                    mat.SetOverrideTag("RenderType", "Opaque");
                    mat.DisableKeyword("_SURFACE_TYPE_TRANSPARENT");
                    mat.renderQueue = (int)RenderQueue.Geometry;
                    break;
            }
            mat.SetShaderPassEnabled("ShadowCaster", false);
            EditorUtility.SetDirty(mat);
            return mat;
        }

        static void BuildMaterials()
        {
            mAddSoft = MakeMaterial("M_VFX_AddSoft", tSoft, Blend.Additive);
            mAddCore = MakeMaterial("M_VFX_AddCore", tCore, Blend.Additive, 1.6f);
            mAddRing = MakeMaterial("M_VFX_AddRing", tRing, Blend.Additive);
            mAddRingSoft = MakeMaterial("M_VFX_AddRingSoft", tRingSoft, Blend.Additive);
            mAddStar4 = MakeMaterial("M_VFX_AddStar4", tStar4, Blend.Additive, 1.6f);
            mAddStar6 = MakeMaterial("M_VFX_AddStar6", tStar6, Blend.Additive, 1.6f);
            mAddStreak = MakeMaterial("M_VFX_AddStreak", tStreak, Blend.Additive, 1.6f);
            mAddFlame = MakeMaterial("M_VFX_AddFlame", tFlame, Blend.Additive, 1.5f);
            mAddSmoke = MakeMaterial("M_VFX_AddSmoke", tSmoke, Blend.Additive, 1.3f);
            mAddHex = MakeMaterial("M_VFX_AddHex", tHex, Blend.Additive, 1.5f);
            mAddSlash = MakeMaterial("M_VFX_AddSlash", tSlash, Blend.Additive, 1.6f);
            mAddSlashGold = MakeMaterial("M_VFX_AddSlashGold", tSlashGold, Blend.Additive, 1.6f);
            mAddBeam = MakeMaterial("M_VFX_AddBeam", tBeam, Blend.Additive, 1.7f);
            mAddRune = MakeMaterial("M_VFX_AddRune", tRune, Blend.Additive, 1.4f);
            mAddSpark = MakeMaterial("M_VFX_AddSpark", tSpark, Blend.Additive, 1.8f);
            mAddTrail = MakeMaterial("M_VFX_AddTrail", tTrail, Blend.Additive, 1.7f);
            mAlphaSmoke = MakeMaterial("M_VFX_AlphaSmoke", tSmoke, Blend.Alpha, 1f);
            mAlphaScorch = MakeMaterial("M_VFX_AlphaScorch", tScorch, Blend.Alpha, 1f);
            mAlphaGhostWisp = MakeMaterial("M_VFX_AlphaGhostWisp", tSmoke, Blend.Alpha, 1f);
            mAlphaGhostTrail = MakeMaterial("M_VFX_AlphaGhostTrail", tTrail, Blend.Alpha, 1f);
            mMeshArrow = MakeMaterial("M_VFX_MeshArrow", null, Blend.Opaque, 1.25f);
            mMeshGhost = MakeMaterial("M_VFX_MeshGhost", null, Blend.Opaque, 1f);
            mMeshOutline = MakeMaterial("M_VFX_MeshOutline", null, Blend.Opaque, 1f, true, Hex("#2A0F3A"));
            mMeshCrystal = MakeMaterial("M_VFX_MeshCrystal", null, Blend.Alpha, 1.3f, false, new Color(1f, 1f, 1f, 0.86f));
            mMeshBeam = MakeMaterial("M_VFX_MeshBeam", tBeam, Blend.Additive, 1.8f);
            mDome = MakeDomeMaterial();
            mFloor = null;
        }

        static Material MakeDomeMaterial()
        {
            var path = $"{MaterialDir}/M_VFX_Dome.mat";
            var shader = AssetDatabase.LoadAssetAtPath<Shader>(ShaderPath);
            if (shader == null) throw new InvalidOperationException("Shader da cupula nao encontrado: " + ShaderPath);
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(shader);
                AssetDatabase.CreateAsset(mat, path);
            }
            mat.shader = shader;
            mat.SetTexture("_HexMap", tHex);
            // Raio do docs/03: borda #3A4FB8 e preenchimento #7FA8FF a 25%; os HDR levam o brilho acima de 1.
            var fill = BoltMid;
            var rim = BoltCore;
            mat.SetColor("_FillColor", new Color(fill.r * 1.2f, fill.g * 1.2f, fill.b * 1.2f, 1f));
            mat.SetColor("_RimColor", new Color(rim.r * 1.6f, rim.g * 1.6f, rim.b * 1.8f, 1f));
            mat.SetColor("_HexColor", new Color(BoltMid.r * 1.8f, BoltMid.g * 1.8f, BoltMid.b * 2.0f, 1f));
            mat.SetFloat("_FillAlpha", 0.25f);
            mat.SetFloat("_RimPower", 2.6f);
            mat.SetFloat("_HexTiling", 5f);
            mat.SetFloat("_Alpha", 1f);
            mat.renderQueue = (int)RenderQueue.Transparent;
            EditorUtility.SetDirty(mat);
            return mat;
        }

        // ------------------------------------------------------------------------------------------------ malhas

        sealed class MeshKit
        {
            public readonly List<Vector3> V = new List<Vector3>();
            public readonly List<Color> C = new List<Color>();
            public readonly List<Vector2> UV = new List<Vector2>();
            public readonly List<int> T = new List<int>();

            public int Add(Vector3 p, Color c, Vector2 uv)
            {
                V.Add(p);
                C.Add(c);
                UV.Add(uv);
                return V.Count - 1;
            }

            public void Tri(int a, int b, int c)
            {
                T.Add(a);
                T.Add(b);
                T.Add(c);
            }

            public void Quad(int a, int b, int c, int d)
            {
                Tri(a, b, c);
                Tri(a, c, d);
            }

            // Cilindro/cone ao longo de +Z, de z0 (raio r0) a z1 (raio r1).
            public void Tube(float z0, float z1, float r0, float r1, int sides, Color c0, Color c1, bool capEnd)
            {
                var first = V.Count;
                for (var i = 0; i <= sides; i++)
                {
                    var a = i / (float)sides * Mathf.PI * 2f;
                    var dx = Mathf.Cos(a);
                    var dy = Mathf.Sin(a);
                    Add(new Vector3(dx * r0, dy * r0, z0), c0, new Vector2(i / (float)sides, 0f));
                    Add(new Vector3(dx * r1, dy * r1, z1), c1, new Vector2(i / (float)sides, 1f));
                }
                for (var i = 0; i < sides; i++)
                {
                    var a = first + i * 2;
                    Quad(a, a + 2, a + 3, a + 1); // normal para fora (o contorno do inimigo usa Cull Front)
                }
                if (!capEnd) return;
                var center = Add(new Vector3(0f, 0f, z0), c0, new Vector2(0.5f, 0.5f));
                for (var i = 0; i < sides; i++)
                {
                    var a = first + i * 2;
                    Tri(center, a + 2, a);
                }
            }

            public Mesh ToMesh(string name)
            {
                var mesh = new Mesh { name = name };
                mesh.SetVertices(V);
                mesh.SetColors(C);
                mesh.SetUVs(0, UV);
                mesh.SetTriangles(T, 0);
                mesh.RecalculateNormals();
                mesh.RecalculateBounds();
                return mesh;
            }
        }

        static Mesh SaveMesh(string name, Mesh mesh)
        {
            var path = $"{MeshDir}/{name}.asset";
            var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (existing == null)
            {
                AssetDatabase.CreateAsset(mesh, path);
                return mesh;
            }
            existing.Clear();
            EditorUtility.CopySerialized(mesh, existing);
            UnityEngine.Object.DestroyImmediate(mesh);
            EditorUtility.SetDirty(existing);
            return existing;
        }

        static Mesh meshArrow, meshGhostArrow, meshCrystal, meshBeam;

        // Flecha de 1 m, ponta em +Z. Fina na haste, grossa o bastante para ler a 56 m (docs/03: piso de 10 cm de espessura visual).
        static Mesh MakeArrowMesh(string name, float shaft, float head, Color shaftColor, Color headColor, Color vaneColor)
        {
            var k = new MeshKit();
            k.Tube(-0.46f, 0.34f, shaft, shaft, 6, shaftColor, shaftColor, true);
            k.Tube(0.34f, 0.56f, head, 0.001f, 6, headColor, headColor, true);
            // penas: 3 aletas em cruz (planos duplos) no fim da haste
            for (var v = 0; v < 3; v++)
            {
                var a = v * Mathf.PI / 3f;
                var dir = new Vector3(Mathf.Cos(a), Mathf.Sin(a), 0f);
                var i0 = k.Add(-dir * head * 1.1f + new Vector3(0f, 0f, -0.46f), vaneColor, Vector2.zero);
                var i1 = k.Add(dir * head * 1.1f + new Vector3(0f, 0f, -0.46f), vaneColor, Vector2.zero);
                var i2 = k.Add(dir * head * 1.1f + new Vector3(0f, 0f, -0.27f), vaneColor, Vector2.zero);
                var i3 = k.Add(-dir * head * 1.1f + new Vector3(0f, 0f, -0.27f), vaneColor, Vector2.zero);
                k.Quad(i0, i1, i2, i3);
            }
            return k.ToMesh(name);
        }

        // Cristal de gelo (hexágono): base escura, corpo azul, ponta clara. Altura 1, raio 0.25.
        static Mesh MakeCrystalMesh()
        {
            var k = new MeshKit();
            const int sides = 6;
            const float radius = 0.25f, bodyHeight = 0.55f, height = 1f;
            var baseRing = new int[sides];
            var topRing = new int[sides];
            for (var i = 0; i < sides; i++)
            {
                var a = i / (float)sides * Mathf.PI * 2f;
                var d = new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a));
                baseRing[i] = k.Add(d * radius, IceEdge, new Vector2(i / (float)sides, 0f));
                topRing[i] = k.Add(d * radius * 0.92f + Vector3.up * bodyHeight, IceMid, new Vector2(i / (float)sides, 0.5f));
            }
            var apex = k.Add(Vector3.up * height, IceCore, new Vector2(0.5f, 1f));
            for (var i = 0; i < sides; i++)
            {
                var j = (i + 1) % sides;
                k.Quad(baseRing[i], topRing[i], topRing[j], baseRing[j]);
                k.Tri(topRing[i], apex, topRing[j]);
            }
            return k.ToMesh("SM_VFX_Crystal");
        }

        // Feixe: dois planos em cruz (XZ e YZ) de 1 m de comprimento em Z e 1 m de largura; a largura real vem da escala.
        static Mesh MakeBeamMesh()
        {
            var k = new MeshKit();
            var white = Color.white;
            // plano horizontal
            var a0 = k.Add(new Vector3(-0.5f, 0f, 0f), white, new Vector2(0f, 0f));
            var a1 = k.Add(new Vector3(0.5f, 0f, 0f), white, new Vector2(1f, 0f));
            var a2 = k.Add(new Vector3(0.5f, 0f, 1f), white, new Vector2(1f, 1f));
            var a3 = k.Add(new Vector3(-0.5f, 0f, 1f), white, new Vector2(0f, 1f));
            k.Quad(a0, a1, a2, a3);
            // plano vertical
            var b0 = k.Add(new Vector3(0f, -0.5f, 0f), white, new Vector2(0f, 0f));
            var b1 = k.Add(new Vector3(0f, 0.5f, 0f), white, new Vector2(1f, 0f));
            var b2 = k.Add(new Vector3(0f, 0.5f, 1f), white, new Vector2(1f, 1f));
            var b3 = k.Add(new Vector3(0f, -0.5f, 1f), white, new Vector2(0f, 1f));
            k.Quad(b0, b1, b2, b3);
            return k.ToMesh("SM_VFX_BeamCross");
        }

        static void BuildMeshes()
        {
            meshArrow = SaveMesh("SM_VFX_Arrow", MakeArrowMesh("SM_VFX_Arrow", 0.022f, 0.065f, Hex("#E8DCC0"), AcidCore, AcidMid));
            meshGhostArrow = SaveMesh("SM_VFX_GhostArrow", MakeArrowMesh("SM_VFX_GhostArrow", 0.032f, 0.095f, Hex("#5B2B73"), ThreatShadowCore, ThreatShadowMid));
            meshCrystal = SaveMesh("SM_VFX_Crystal", MakeCrystalMesh());
            meshBeam = SaveMesh("SM_VFX_BeamCross", MakeBeamMesh());
        }
    }
}
