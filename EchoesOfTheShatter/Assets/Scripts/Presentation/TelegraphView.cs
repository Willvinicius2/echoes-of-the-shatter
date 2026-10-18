using Echoes.Gameplay;
using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Mesh plano do telegraph no chão (docs/tecnico/04_arquitetura.md, seção 3.10): cone, círculo ou linha
    /// com as dimensões reais da consulta, a +0,02 m do piso. O material (SG_VFX variante Telegraph)
    /// recebe <c>_Progress</c> de 0 a 1 durante o windup. Em pool no <see cref="TelegraphPresenter"/>.
    /// </summary>
    [RequireComponent(typeof(MeshFilter))]
    [RequireComponent(typeof(MeshRenderer))]
    public sealed class TelegraphView : MonoBehaviour
    {
        static readonly int ProgressId = Shader.PropertyToID("_Progress");
        const float GroundOffset = 0.02f;
        const int MaxSegments = 48;

        Mesh mesh;
        Material material;
        readonly Vector3[] vertices = new Vector3[MaxSegments + 2];
        readonly int[] triangles = new int[MaxSegments * 3];
        readonly Vector2[] uvs = new Vector2[MaxSegments + 2];

        public int TelegraphId { get; set; }
        public float Elapsed { get; set; }
        public float Duration { get; set; }

        void Awake()
        {
            mesh = new Mesh { name = "Telegraph" };
            mesh.MarkDynamic();
            GetComponent<MeshFilter>().sharedMesh = mesh;
            var renderer = GetComponent<MeshRenderer>();
            renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            renderer.receiveShadows = false;
            material = renderer.material; // instância própria, criada uma vez por view do pool
        }

        void OnDestroy()
        {
            if (mesh != null) Destroy(mesh);
            if (material != null) Destroy(material);
        }

        public void Show(in TelegraphEvent evt, float groundY)
        {
            TelegraphId = evt.TelegraphId;
            Elapsed = 0f;
            Duration = (float)evt.DurationSeconds;
            transform.SetPositionAndRotation(evt.Origin.ToWorld(groundY + GroundOffset), evt.Direction.ToRotation(Quaternion.identity));
            switch (evt.Shape)
            {
                case TelegraphShape.Circle:
                    BuildFan(evt.RangeMeters, 180f);
                    break;
                case TelegraphShape.Line:
                    BuildLine(evt.RangeMeters, evt.WidthMeters);
                    break;
                default:
                    BuildFan(evt.RangeMeters, evt.HalfAngleDegrees);
                    break;
            }
            SetProgress(0f);
            gameObject.SetActive(true);
        }

        public void SetProgress(float progress)
        {
            if (material != null) material.SetFloat(ProgressId, Mathf.Clamp01(progress));
        }

        void BuildFan(float radius, float halfAngleDegrees)
        {
            var segments = Mathf.Clamp(Mathf.CeilToInt(halfAngleDegrees * 2f / 7.5f), 3, MaxSegments);
            vertices[0] = Vector3.zero;
            uvs[0] = new Vector2(0.5f, 0f);
            for (var i = 0; i <= segments; i++)
            {
                var t = (float)i / segments;
                var angle = Mathf.Deg2Rad * Mathf.Lerp(-halfAngleDegrees, halfAngleDegrees, t);
                vertices[i + 1] = new Vector3(Mathf.Sin(angle) * radius, 0f, Mathf.Cos(angle) * radius);
                uvs[i + 1] = new Vector2(t, 1f);
            }
            for (var i = 0; i < segments; i++)
            {
                triangles[i * 3] = 0;
                triangles[i * 3 + 1] = i + 1;
                triangles[i * 3 + 2] = i + 2;
            }
            Apply(segments + 2, segments * 3);
        }

        void BuildLine(float length, float width)
        {
            // Largura 0 no dado = projétil pontual; o aviso usa uma linha fina para ser visível.
            var half = Mathf.Max(width, 0.1f) * 0.5f;
            vertices[0] = new Vector3(-half, 0f, 0f);
            vertices[1] = new Vector3(half, 0f, 0f);
            vertices[2] = new Vector3(-half, 0f, length);
            vertices[3] = new Vector3(half, 0f, length);
            uvs[0] = new Vector2(0f, 0f);
            uvs[1] = new Vector2(1f, 0f);
            uvs[2] = new Vector2(0f, 1f);
            uvs[3] = new Vector2(1f, 1f);
            triangles[0] = 0;
            triangles[1] = 2;
            triangles[2] = 1;
            triangles[3] = 1;
            triangles[4] = 2;
            triangles[5] = 3;
            Apply(4, 6);
        }

        void Apply(int vertexCount, int indexCount)
        {
            mesh.Clear();
            mesh.SetVertices(vertices, 0, vertexCount);
            mesh.SetUVs(0, uvs, 0, vertexCount);
            mesh.SetTriangles(triangles, 0, indexCount, 0);
            mesh.RecalculateBounds();
        }
    }
}
