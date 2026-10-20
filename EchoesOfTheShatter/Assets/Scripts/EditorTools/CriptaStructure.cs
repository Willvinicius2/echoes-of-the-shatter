using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Estrutura limpa da Cripta, em malha procedural com a pedra projetada no mundo (M_Env_Pedra): paredes com rodape, cornija e pilastras,
    /// postes de canto em pedra e colunas octogonais com base e capitel. Substitui as pecas pintadas "amassadas" do kit nas paredes e pilares
    /// da Cripta (o Refugio continua no kit). Sem rachadura, sem ruina, sem UV: textura uniforme vinda do shader.
    /// </summary>
    internal static class CriptaStructure
    {
        const float Plinth = 0.35f;       // altura do rodape
        const float Cornice = 0.30f;      // altura da cornija
        const float PilasterEvery = 6f;   // uma pilastra a cada ~6 m de parede
        const float PilasterWidth = 0.7f;
        const float PilasterDepth = 0.22f;

        sealed class MeshData
        {
            public readonly List<Vector3> V = new List<Vector3>();
            public readonly List<Vector3> N = new List<Vector3>();
            public readonly List<Vector2> Uv = new List<Vector2>();
            public readonly List<int> T = new List<int>();

            /// <summary>Caixa alinhada aos eixos (min, max), 24 vertices, normais planas.</summary>
            public void Box(Vector3 min, Vector3 max)
            {
                Face(new Vector3(min.x, min.y, max.z), new Vector3(max.x, min.y, max.z), new Vector3(max.x, max.y, max.z), new Vector3(min.x, max.y, max.z), Vector3.forward);
                Face(new Vector3(max.x, min.y, min.z), new Vector3(min.x, min.y, min.z), new Vector3(min.x, max.y, min.z), new Vector3(max.x, max.y, min.z), Vector3.back);
                Face(new Vector3(max.x, min.y, max.z), new Vector3(max.x, min.y, min.z), new Vector3(max.x, max.y, min.z), new Vector3(max.x, max.y, max.z), Vector3.right);
                Face(new Vector3(min.x, min.y, min.z), new Vector3(min.x, min.y, max.z), new Vector3(min.x, max.y, max.z), new Vector3(min.x, max.y, min.z), Vector3.left);
                Face(new Vector3(min.x, max.y, max.z), new Vector3(max.x, max.y, max.z), new Vector3(max.x, max.y, min.z), new Vector3(min.x, max.y, min.z), Vector3.up);
                Face(new Vector3(min.x, min.y, min.z), new Vector3(max.x, min.y, min.z), new Vector3(max.x, min.y, max.z), new Vector3(min.x, min.y, max.z), Vector3.down);
            }

            /// <summary>Prisma de <paramref name="sides"/> lados, de y0 a y1, com raio ao vertice; normais planas por face.</summary>
            public void Prism(Vector3 center, float radius, float y0, float y1, int sides, float yaw)
            {
                for (var i = 0; i < sides; i++)
                {
                    var a0 = (i / (float)sides) * Mathf.PI * 2f + yaw;
                    var a1 = ((i + 1) / (float)sides) * Mathf.PI * 2f + yaw;
                    var p0 = center + new Vector3(Mathf.Cos(a0), 0f, Mathf.Sin(a0)) * radius;
                    var p1 = center + new Vector3(Mathf.Cos(a1), 0f, Mathf.Sin(a1)) * radius;
                    var nrm = new Vector3(Mathf.Cos((a0 + a1) * 0.5f), 0f, Mathf.Sin((a0 + a1) * 0.5f));
                    Face(new Vector3(p1.x, y0, p1.z), new Vector3(p0.x, y0, p0.z), new Vector3(p0.x, y1, p0.z), new Vector3(p1.x, y1, p1.z), nrm);
                    var c = new Vector3(center.x, y1, center.z);
                    var top = new Vector3(p0.x, y1, p0.z);
                    var top1 = new Vector3(p1.x, y1, p1.z);
                    var k = V.Count;
                    V.Add(c); V.Add(top1); V.Add(top);
                    for (var j = 0; j < 3; j++) { N.Add(Vector3.up); Uv.Add(Vector2.zero); }
                    T.Add(k); T.Add(k + 2); T.Add(k + 1);
                }
            }

            /// <summary>Quad com a ordem dos vertices escolhida para a face apontar para <paramref name="normal"/>.</summary>
            void Face(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector3 normal)
            {
                var k = V.Count;
                V.Add(a); V.Add(b); V.Add(c); V.Add(d);
                for (var i = 0; i < 4; i++) { N.Add(normal); Uv.Add(Vector2.zero); }
                var cross = Vector3.Cross(b - a, c - a);
                if (Vector3.Dot(cross, normal) >= 0f) { T.Add(k); T.Add(k + 1); T.Add(k + 2); T.Add(k); T.Add(k + 2); T.Add(k + 3); }
                else { T.Add(k); T.Add(k + 2); T.Add(k + 1); T.Add(k); T.Add(k + 3); T.Add(k + 2); }
            }

            public Mesh ToMesh(string name)
            {
                var m = new Mesh { name = name, indexFormat = IndexFormat.UInt32 };
                m.SetVertices(V); m.SetNormals(N); m.SetUVs(0, Uv); m.SetTriangles(T, 0);
                m.RecalculateBounds();
                return m;
            }
        }

        static GameObject Make(Transform parent, string name, Mesh mesh, string assetName)
        {
            SandboxBuilder.EnsureDir(EnvironmentKit.GeneratedDir + "/Structure");
            mesh = SandboxBuilder.SaveMesh(mesh, $"{EnvironmentKit.GeneratedDir}/Structure/{assetName}.asset");
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = EnvironmentKit.EnsureStoneMaterial();
            mr.shadowCastingMode = ShadowCastingMode.Off; // decisao do kit: cenario nao projeta sombra (piso uniforme)
            mr.receiveShadows = true;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);
            return go;
        }

        /// <summary>
        /// Visual de um trecho de parede. Coordenadas locais: x ao longo do trecho (centrado), z=0 na face interna, corpo para -z, y para cima.
        /// Corpo de <paramref name="thickness"/>, rodape e cornija um pouco mais largos e uma pilastra a cada ~6 m (nunca nas pontas).
        /// </summary>
        public static void WallVisual(Transform run, string key, float length, float height, float thickness)
        {
            var d = new MeshData();
            var hl = length * 0.5f;
            d.Box(new Vector3(-hl, 0f, -thickness), new Vector3(hl, height, 0f));
            d.Box(new Vector3(-hl, 0f, -thickness), new Vector3(hl, Plinth, 0.06f));                          // rodape
            d.Box(new Vector3(-hl, height - Cornice, -thickness), new Vector3(hl, height, 0.08f));            // cornija
            var count = Mathf.FloorToInt(length / PilasterEvery);
            for (var i = 0; i < count; i++)
            {
                var cx = -hl + (i + 0.5f) * length / count;
                if (cx - PilasterWidth * 0.5f < -hl + 0.8f || cx + PilasterWidth * 0.5f > hl - 0.8f) continue;
                d.Box(new Vector3(cx - PilasterWidth * 0.5f, Plinth, 0f), new Vector3(cx + PilasterWidth * 0.5f, height - Cornice, PilasterDepth));
            }
            var go = Make(run, "Visual", d.ToMesh("Wall_" + key), "Wall_" + key);
            go.transform.localPosition = Vector3.zero;
            go.transform.localRotation = Quaternion.identity;
        }

        /// <summary>Poste de canto: coluna quadrada de 1 x 1 m com rodape e capitel, no lugar do ParedeCantoA.</summary>
        public static void CornerPost(Transform parent, string owner, Vector3 position, float height)
        {
            var d = new MeshData();
            d.Box(new Vector3(-0.5f, 0f, -0.5f), new Vector3(0.5f, height, 0.5f));
            d.Box(new Vector3(-0.6f, 0f, -0.6f), new Vector3(0.6f, Plinth, 0.6f));
            d.Box(new Vector3(-0.62f, height - Cornice, -0.62f), new Vector3(0.62f, height + 0.05f, 0.62f));
            var go = Make(parent, owner + "_corner", d.ToMesh("Post"), "Post_" + SceneryBuilder.Sanitize(owner) + "_" + Mathf.RoundToInt(position.x * 10f) + "_" + Mathf.RoundToInt(position.z * 10f));
            go.transform.position = position;
        }

        /// <summary>Coluna octogonal: base e capitel quadrados, fuste de 8 lados. O colisor e posto por quem chama.</summary>
        public static GameObject Pillar(Transform parent, string id, Vector3 position, float radius, float height)
        {
            var d = new MeshData();
            var b = radius * 1.3f;
            d.Box(new Vector3(-b, 0f, -b), new Vector3(b, 0.4f, b));                                   // base
            d.Prism(Vector3.zero, radius * 1.05f, 0.4f, height - 0.4f, 8, Mathf.PI / 8f);              // fuste
            d.Box(new Vector3(-b, height - 0.4f, -b), new Vector3(b, height, b));                       // capitel
            var go = Make(parent, id, d.ToMesh("Pillar"), "Pillar_" + SceneryBuilder.Sanitize(id) + "_" + Mathf.RoundToInt(position.x * 10f) + "_" + Mathf.RoundToInt(position.z * 10f));
            go.transform.position = position;
            go.GetComponent<MeshRenderer>().sharedMaterial = EnvironmentKit.EnsurePillarMaterial();
            return go;
        }

        /// <summary>
        /// Tapete cerimonial ao longo da rota principal: faixa vermelha escura de 2 m com borda dourada, a 0,7 cm do piso (abaixo dos simbolos dos checkpoints). So visual (sem colisor):
        /// da vida ao chao e mostra o caminho ate o chefe.
        /// </summary>
        public static void Carpet(Transform parent, IList<Vector2> route, float width = 2.0f)
        {
            var trim = new MeshData();
            var cloth = new MeshData();
            for (var i = 0; i + 1 < route.Count; i++)
            {
                var a = route[i]; var b = route[i + 1];
                var dir = (b - a).normalized;
                var half = width * 0.5f;
                if (i > 0) a -= dir * half; // so as juntas internas se estendem (fecha a quina); as pontas ficam onde a rota comeca e termina
                if (i + 2 < route.Count) b += dir * half;
                var n = new Vector2(-dir.y, dir.x);
                Strip(trim, a, b, n, half + 0.16f, 0.004f);
                Strip(cloth, a, b, n, half, 0.007f);
            }
            var trimGo = Make(parent, "Carpet_Trim", trim.ToMesh("Carpet_Trim"), "Carpet_Trim");
            trimGo.GetComponent<MeshRenderer>().sharedMaterial = EnsureCarpetMaterial("M_Cripta_TapeteBorda", new Color(0.55f, 0.40f, 0.14f));
            trimGo.GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.Off;
            var clothGo = Make(parent, "Carpet", cloth.ToMesh("Carpet"), "Carpet");
            clothGo.GetComponent<MeshRenderer>().sharedMaterial = EnsureCarpetMaterial("M_Cripta_Tapete", new Color(0.36f, 0.07f, 0.12f));
        }

        /// <summary>
        /// Medalhao do checkpoint e do portal: so um aro fino rente ao piso (dourado no checkpoint, violeta no portal), sem anel de pedra nem
        /// barras de runa. O simbolo (Glyph) fica dentro do aro.
        /// </summary>
        public static void Medallion(Transform parent, Vector3 center, string id, bool portal, float radius = 1.45f)
        {
            var d = new MeshData();
            const int seg = 72;
            const float w = 0.09f;
            const float y = 0.010f;
            for (var i = 0; i < seg; i++)
            {
                var a0 = i * Mathf.PI * 2f / seg;
                var a1 = (i + 1) * Mathf.PI * 2f / seg;
                var k = d.V.Count;
                foreach (var (a, r) in new[] { (a0, radius), (a0, radius - w), (a1, radius - w), (a1, radius) })
                {
                    d.V.Add(new Vector3(Mathf.Cos(a) * r, y, Mathf.Sin(a) * r));
                    d.N.Add(Vector3.up); d.Uv.Add(Vector2.zero);
                }
                var up = Vector3.Cross(d.V[k + 1] - d.V[k], d.V[k + 2] - d.V[k]).y >= 0f;
                if (up) { d.T.Add(k); d.T.Add(k + 1); d.T.Add(k + 2); d.T.Add(k); d.T.Add(k + 2); d.T.Add(k + 3); }
                else { d.T.Add(k); d.T.Add(k + 2); d.T.Add(k + 1); d.T.Add(k); d.T.Add(k + 3); d.T.Add(k + 2); }
            }
            var go = Make(parent, "Medallion", d.ToMesh("Medallion"), "Medallion_" + SceneryBuilder.Sanitize(id));
            go.transform.position = center;
            var mr = go.GetComponent<MeshRenderer>();
            mr.sharedMaterial = portal ? EnsureCarpetMaterial("M_Cripta_AroPortal", new Color(0.45f, 0.33f, 0.85f)) : EnsureCarpetMaterial("M_Cripta_AroCheckpoint", new Color(0.78f, 0.56f, 0.18f));
            mr.shadowCastingMode = ShadowCastingMode.Off;
        }

        static void Strip(MeshData d, Vector2 a, Vector2 b, Vector2 n, float half, float y)
        {
            var k = d.V.Count;
            d.V.Add(new Vector3(a.x + n.x * half, y, a.y + n.y * half));
            d.V.Add(new Vector3(a.x - n.x * half, y, a.y - n.y * half));
            d.V.Add(new Vector3(b.x - n.x * half, y, b.y - n.y * half));
            d.V.Add(new Vector3(b.x + n.x * half, y, b.y + n.y * half));
            for (var i = 0; i < 4; i++) { d.N.Add(Vector3.up); d.Uv.Add(Vector2.zero); }
            var up = Vector3.Cross(d.V[k + 1] - d.V[k], d.V[k + 2] - d.V[k]).y >= 0f;
            if (up) { d.T.Add(k); d.T.Add(k + 1); d.T.Add(k + 2); d.T.Add(k); d.T.Add(k + 2); d.T.Add(k + 3); }
            else { d.T.Add(k); d.T.Add(k + 2); d.T.Add(k + 1); d.T.Add(k); d.T.Add(k + 3); d.T.Add(k + 2); }
        }

        static Material EnsureCarpetMaterial(string name, Color color)
        {
            SandboxBuilder.EnsureDir(EnvironmentKit.MaterialDir);
            var path = EnvironmentKit.MaterialDir + "/" + name + ".mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                AssetDatabase.CreateAsset(mat, path);
            }
            mat.SetColor("_BaseColor", color);
            mat.SetFloat("_Smoothness", 0.05f);
            mat.SetFloat("_Metallic", 0f);
            mat.SetFloat("_ReceiveShadows", 1f);
            EditorUtility.SetDirty(mat);
            return mat;
        }
    }
}
