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
            return go;
        }
    }
}
