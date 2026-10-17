using UnityEngine;
using UnityEngine.Rendering;

namespace Echoes.Presentation
{
    /// <summary>
    /// Fita do rastro da arma (docs/18 seção 6, <c>fx.trail.warrior_*</c>): guarda a posição de dois pontos da arma (cabo e ponta) a cada
    /// quadro e desenha uma faixa que varre o arco do golpe e some pela idade. A malha é em coordenadas do mundo, por isso o objeto fica na origem.
    /// O TrailRenderer só faria uma linha da ponta; esta faixa cobre a lâmina inteira. Sem alocação por quadro (malha e vetores preparados no Awake).
    /// Em pool: reinicia a cada ativação.
    /// </summary>
    [RequireComponent(typeof(MeshFilter), typeof(MeshRenderer))]
    public sealed class BladeTrail : MonoBehaviour
    {
        [SerializeField, Min(0.02f)] float lifetime = 0.2f;
        [SerializeField, Range(4, 48)] int maxSamples = 28;
        [SerializeField, Range(1, 4)] int subdivisions = 3;
        [Tooltip("Cor ao longo da lâmina: 0 = cabo, 1 = ponta. O alfa do gradiente multiplica o alfa da idade.")]
        [SerializeField] Gradient colorAlongBlade = new Gradient();
        [Tooltip("Expoente do apagar pela idade (1 = linear; maior = a cauda some mais cedo).")]
        [SerializeField, Min(0.5f)] float fadePower = 1.4f;
        [SerializeField, Min(0f)] float minMoveMeters = 0.004f;

        Transform baseTransform;
        Transform tipTransform;
        float coverage = 1f;
        float emitUntil;
        bool emitting;

        Vector3[] baseSamples;
        Vector3[] tipSamples;
        float[] born;
        int head;
        int count;

        Mesh mesh;
        Vector3[] vertices;
        Color[] colors;
        Vector2[] uvs;
        int[] triangles;

        public void Configure(float lifetimeSeconds, Gradient gradient, int samples)
        {
            lifetime = lifetimeSeconds;
            if (gradient != null) colorAlongBlade = gradient;
            maxSamples = samples;
        }

        /// <summary>
        /// Liga a faixa aos pontos da arma. <paramref name="coverageOfBlade"/> = fração do comprimento (da ponta para o cabo) que a faixa cobre:
        /// o golpe de fecho do combo usa uma faixa mais larga.
        /// </summary>
        public void Bind(Transform bladeBase, Transform bladeTip, float coverageOfBlade, float emitSeconds)
        {
            baseTransform = bladeBase;
            tipTransform = bladeTip;
            coverage = Mathf.Clamp(coverageOfBlade, 0.05f, 1.5f);
            emitting = baseTransform != null && tipTransform != null;
            emitUntil = emitSeconds > 0f ? Time.time + emitSeconds : float.MaxValue;
        }

        public void StopEmitting() => emitting = false;

        void Awake()
        {
            var perSegment = subdivisions;
            var maxPoints = (maxSamples - 1) * perSegment + 1;
            baseSamples = new Vector3[maxSamples];
            tipSamples = new Vector3[maxSamples];
            born = new float[maxSamples];
            vertices = new Vector3[maxPoints * 2];
            colors = new Color[maxPoints * 2];
            uvs = new Vector2[maxPoints * 2];
            triangles = new int[(maxPoints - 1) * 6];
            mesh = new Mesh { name = "BladeTrail" };
            mesh.MarkDynamic();
            GetComponent<MeshFilter>().sharedMesh = mesh;
            var renderer = GetComponent<MeshRenderer>();
            renderer.shadowCastingMode = ShadowCastingMode.Off;
            renderer.receiveShadows = false;
            renderer.lightProbeUsage = LightProbeUsage.Off;
        }

        void OnEnable()
        {
            head = 0;
            count = 0;
            emitting = false;
            mesh.Clear();
        }

        void OnDestroy()
        {
            if (mesh != null) Destroy(mesh);
        }

        void LateUpdate()
        {
            transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            var now = Time.time;

            if (emitting && now > emitUntil) emitting = false;
            if (emitting && baseTransform != null && tipTransform != null) AddSample(now);

            // Remove as amostras vencidas (as mais antigas ficam atrás de head).
            while (count > 0 && now - born[Oldest()] > lifetime) count--;

            if (count < 2)
            {
                mesh.Clear();
                return;
            }
            Rebuild(now);
        }

        int Oldest() => (head - count + maxSamples * 2) % maxSamples;

        void AddSample(float now)
        {
            var tip = tipTransform.position;
            var hilt = Vector3.Lerp(tip, baseTransform.position, coverage);
            if (count > 0)
            {
                var last = (head - 1 + maxSamples) % maxSamples;
                if ((tip - tipSamples[last]).sqrMagnitude < minMoveMeters * minMoveMeters &&
                    (hilt - baseSamples[last]).sqrMagnitude < minMoveMeters * minMoveMeters) return;
            }
            baseSamples[head] = hilt;
            tipSamples[head] = tip;
            born[head] = now;
            head = (head + 1) % maxSamples;
            if (count < maxSamples) count++;
        }

        Vector3 Point(Vector3[] array, int logicalIndex)
        {
            // logicalIndex 0 = mais antiga; clamp nas pontas (Catmull-Rom).
            logicalIndex = Mathf.Clamp(logicalIndex, 0, count - 1);
            return array[(Oldest() + logicalIndex) % maxSamples];
        }

        static Vector3 CatmullRom(Vector3 p0, Vector3 p1, Vector3 p2, Vector3 p3, float t)
        {
            var t2 = t * t;
            var t3 = t2 * t;
            return 0.5f * (2f * p1 + (p2 - p0) * t + (2f * p0 - 5f * p1 + 4f * p2 - p3) * t2 + (3f * p1 - p0 - 3f * p2 + p3) * t3);
        }

        void Rebuild(float now)
        {
            var points = 0;
            for (var s = 0; s < count - 1; s++)
            {
                for (var k = 0; k < subdivisions; k++)
                {
                    var t = k / (float)subdivisions;
                    AddPoint(points++, s, t, now);
                }
            }
            AddPoint(points++, count - 2, 1f, now);

            var triangleCount = 0;
            for (var i = 0; i < points - 1; i++)
            {
                var a = i * 2;
                triangles[triangleCount++] = a;
                triangles[triangleCount++] = a + 1;
                triangles[triangleCount++] = a + 2;
                triangles[triangleCount++] = a + 1;
                triangles[triangleCount++] = a + 3;
                triangles[triangleCount++] = a + 2;
            }

            mesh.Clear();
            mesh.SetVertices(vertices, 0, points * 2);
            mesh.SetColors(colors, 0, points * 2);
            mesh.SetUVs(0, uvs, 0, points * 2);
            mesh.SetIndices(triangles, 0, triangleCount, MeshTopology.Triangles, 0);
            mesh.bounds = new Bounds(Vector3.zero, new Vector3(2000f, 2000f, 2000f)); // coordenadas do mundo: nunca corta pela câmera
        }

        void AddPoint(int index, int segment, float t, float now)
        {
            var bp = CatmullRom(Point(baseSamples, segment - 1), Point(baseSamples, segment), Point(baseSamples, segment + 1), Point(baseSamples, segment + 2), t);
            var tp = CatmullRom(Point(tipSamples, segment - 1), Point(tipSamples, segment), Point(tipSamples, segment + 1), Point(tipSamples, segment + 2), t);
            var age = Mathf.Lerp(now - born[(Oldest() + segment) % maxSamples], now - born[(Oldest() + Mathf.Min(segment + 1, count - 1)) % maxSamples], t);
            var life = Mathf.Clamp01(1f - age / lifetime);
            var fade = Mathf.Pow(life, fadePower);
            var v = index * 2;
            vertices[v] = bp;
            vertices[v + 1] = tp;
            var cb = colorAlongBlade.Evaluate(0f);
            var ct = colorAlongBlade.Evaluate(1f);
            cb.a *= fade;
            ct.a *= fade;
            colors[v] = cb;
            colors[v + 1] = ct;
            uvs[v] = new Vector2(life, 0f);
            uvs[v + 1] = new Vector2(life, 1f);
        }
    }
}
