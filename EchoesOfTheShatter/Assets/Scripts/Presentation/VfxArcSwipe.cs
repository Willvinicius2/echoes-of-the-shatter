using UnityEngine;
using UnityEngine.Rendering;

namespace Echoes.Presentation
{
    /// <summary>
    /// Arco de lâmina varrido à frente do herói (docs/18, <c>fx.trail.warrior_*</c>): uma faixa curva que a "cabeça" percorre em
    /// <see cref="sweepSeconds"/> deixando a cauda se apagar, grande o bastante para ler a 56 m (a fita da ponta da arma sozinha é fina
    /// demais naquela distância). Também serve de arco fixo no chão (modo <see cref="persistent"/>, <c>fx.guard.arc_hint</c>), que pulsa de leve
    /// e some em <see cref="BeginFadeOut"/>. O prefab aponta +Z para a direção do golpe; ângulos positivos vão para a direita. A malha é montada
    /// uma vez no Awake; por quadro só as cores (alfa e brilho) mudam, sem alocação. Em pool: reinicia a cada ativação.
    /// </summary>
    [RequireComponent(typeof(MeshFilter), typeof(MeshRenderer))]
    public sealed class VfxArcSwipe : MonoBehaviour
    {
        const int Segments = 28;

        [Header("Forma (metros e graus)")]
        [SerializeField, Min(0.05f)] float innerRadius = 0.8f;
        [SerializeField, Min(0.05f)] float outerRadius = 1.9f;
        [SerializeField] float startDegrees = -80f;
        [SerializeField] float endDegrees = 80f;
        [SerializeField] float height = 0.9f;
        [Tooltip("Metros que o arco sobe por metro de deslocamento lateral (golpe em diagonal).")]
        [SerializeField] float rise = 0.3f;
        [Tooltip("Metros que a borda de fora fica acima da de dentro: a faixa vira um cone baixo, que a câmera de 55 graus lê como golpe de lâmina e não como mancha no chão.")]
        [SerializeField] float lift = 0f;

        [Header("Tempo")]
        [SerializeField, Min(0.01f)] float sweepSeconds = 0.12f;
        [SerializeField, Min(0.01f)] float fadeSeconds = 0.18f;
        [Tooltip("Fração do arco que a cauda ocupa atrás da cabeça.")]
        [SerializeField, Range(0.1f, 1.5f)] float tail = 0.6f;

        [Header("Cor (0 = borda de dentro, 1 = borda de fora; o alfa multiplica)")]
        [SerializeField] Gradient colorAcross = new Gradient();
        [Tooltip("Brilho da cabeça: mistura com branco.")]
        [SerializeField, Range(0f, 1f)] float headWhite = 0.55f;

        [Header("Arco fixo (guarda)")]
        [SerializeField] bool persistent;
        [SerializeField] float pulseHz = 1.6f;
        [SerializeField, Range(0f, 1f)] float pulseDepth = 0.25f;

        Mesh mesh;
        Color[] colors;
        float time;
        bool fadingOut;
        float fadeOutTime;
        float fadeOutSeconds = 0.2f;

        public void Configure(float inner, float outer, float startDeg, float endDeg, float heightMeters, float risePerMeter,
            float sweep, float fade, float tailFraction, Gradient across, bool fixedArc, float headBrightness)
        {
            innerRadius = inner;
            outerRadius = outer;
            startDegrees = startDeg;
            endDegrees = endDeg;
            height = heightMeters;
            rise = risePerMeter;
            sweepSeconds = sweep;
            fadeSeconds = fade;
            tail = tailFraction;
            if (across != null) colorAcross = across;
            persistent = fixedArc;
            headWhite = headBrightness;
        }

        public void SetLift(float meters) => lift = meters;

        /// <summary>Apaga o arco fixo em <paramref name="seconds"/> (o pool devolve a instância logo depois).</summary>
        public void BeginFadeOut(float seconds)
        {
            fadingOut = true;
            fadeOutTime = 0f;
            fadeOutSeconds = Mathf.Max(0.02f, seconds);
        }

        void Awake()
        {
            BuildMesh();
            var renderer = GetComponent<MeshRenderer>();
            renderer.shadowCastingMode = ShadowCastingMode.Off;
            renderer.receiveShadows = false;
            renderer.lightProbeUsage = LightProbeUsage.Off;
        }

        void OnEnable()
        {
            time = 0f;
            fadingOut = false;
            Paint();
        }

        void OnDestroy()
        {
            if (mesh != null) Destroy(mesh);
        }

        void BuildMesh()
        {
            var vertices = new Vector3[(Segments + 1) * 2];
            var uvs = new Vector2[vertices.Length];
            colors = new Color[vertices.Length];
            var triangles = new int[Segments * 6];
            var middle = (innerRadius + outerRadius) * 0.5f;
            var half = (outerRadius - innerRadius) * 0.5f;
            for (var i = 0; i <= Segments; i++)
            {
                var p = i / (float)Segments;
                var angle = Mathf.Lerp(startDegrees, endDegrees, p) * Mathf.Deg2Rad;
                var width = Mathf.Pow(Mathf.Sin(Mathf.PI * p), 0.55f); // as pontas afinam, o meio engorda
                var rIn = middle - half * width;
                var rOut = middle + half * width;
                var x = Mathf.Sin(angle);
                var z = Mathf.Cos(angle);
                vertices[i * 2] = new Vector3(x * rIn, height + rise * x * rIn, z * rIn);
                vertices[i * 2 + 1] = new Vector3(x * rOut, height + rise * x * rOut + lift * width, z * rOut);
                var u = 0.25f + 0.75f * p;
                uvs[i * 2] = new Vector2(u, 0f);
                uvs[i * 2 + 1] = new Vector2(u, 1f);
            }
            for (var i = 0; i < Segments; i++)
            {
                var a = i * 2;
                var t = i * 6;
                triangles[t] = a;
                triangles[t + 1] = a + 1;
                triangles[t + 2] = a + 2;
                triangles[t + 3] = a + 1;
                triangles[t + 4] = a + 3;
                triangles[t + 5] = a + 2;
            }
            mesh = new Mesh { name = "VfxArcSwipe" };
            mesh.MarkDynamic();
            // Sem recalcular limites a cada atribuição (a malha vazia tem limites "invertidos" e a Unity reclama): os limites são fixos e folgados.
            const MeshUpdateFlags noBounds = MeshUpdateFlags.DontRecalculateBounds;
            mesh.SetVertices(vertices, 0, vertices.Length, noBounds);
            mesh.SetUVs(0, uvs, 0, uvs.Length, noBounds);
            mesh.SetIndices(triangles, MeshTopology.Triangles, 0, false);
            mesh.SetColors(colors, 0, colors.Length, noBounds);
            mesh.bounds = new Bounds(new Vector3(0f, height + lift * 0.5f, outerRadius * 0.5f), new Vector3(outerRadius * 2.4f, 3f + lift, outerRadius * 2.4f));
            GetComponent<MeshFilter>().sharedMesh = mesh;
        }

        void Update()
        {
            time += Time.deltaTime;
            if (fadingOut) fadeOutTime += Time.deltaTime;
            Paint();
        }

        void Paint()
        {
            if (mesh == null) return;
            // Cor de vértice é linear (não passa pela conversão sRGB do sistema de partículas): converte o degradê, que é autorado em sRGB.
            var inner = colorAcross.Evaluate(0f).linear;
            var outer = colorAcross.Evaluate(1f).linear;
            var head = persistent ? 2f : Mathf.Clamp01(time / sweepSeconds);
            var eased = 1f - (1f - head) * (1f - head);
            var afterSweep = persistent ? 0f : Mathf.Clamp01((time - sweepSeconds) / fadeSeconds);
            var headPosition = eased + afterSweep * tail;
            var global = 1f;
            if (persistent)
            {
                global = Mathf.Clamp01(time / 0.12f) * (1f - pulseDepth + pulseDepth * (0.5f + 0.5f * Mathf.Sin(time * pulseHz * Mathf.PI * 2f)));
                if (fadingOut) global *= 1f - Mathf.Clamp01(fadeOutTime / fadeOutSeconds);
            }
            for (var i = 0; i <= Segments; i++)
            {
                var p = i / (float)Segments;
                float alpha;
                var bright = 0f;
                if (persistent)
                {
                    alpha = Mathf.Pow(Mathf.Sin(Mathf.PI * p), 0.4f) * global;
                }
                else
                {
                    var behind = headPosition - p;
                    alpha = behind < 0f ? 0f : Mathf.Clamp01(1f - behind / tail);
                    alpha = alpha * alpha * (3f - 2f * alpha);
                    bright = behind < 0f ? 0f : Mathf.Clamp01(1f - behind / (tail * 0.3f)) * headWhite;
                }
                var ci = Color.Lerp(inner, Color.white, bright * 0.5f);
                var co = Color.Lerp(outer, Color.white, bright);
                ci.a = colorAcross.Evaluate(0f).a * alpha;
                co.a = colorAcross.Evaluate(1f).a * alpha;
                colors[i * 2] = ci;
                colors[i * 2 + 1] = co;
            }
            mesh.SetColors(colors, 0, colors.Length, MeshUpdateFlags.DontRecalculateBounds);
        }
    }
}
