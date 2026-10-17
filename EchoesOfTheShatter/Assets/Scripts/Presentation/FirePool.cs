using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Luz pontual e chama em pool para o fogo do cenario (docs/04 secao 18: ate 4 pontuais sem sombra no PC de entrada; aqui ate
    /// <see cref="maxActive"/> = 6, so as mais proximas do heroi). Um numero fixo de espacos (Light + ParticleSystem) e criado no Awake e
    /// reatribuido as <see cref="FireSource"/> mais proximas do alvo a cada <see cref="refreshSeconds"/>; sem alocacao em regime. As luzes sobem e
    /// descem suavemente (sem estalo) e tremem com ruido. Dado de apresentacao: nenhum numero de balanceamento.
    /// </summary>
    public sealed class FirePool : MonoBehaviour
    {
        [SerializeField] Transform target;
        [SerializeField] Material flameMaterial;
        [SerializeField, Range(1, 8)] int maxActive = 6;
        [SerializeField] float maxDistance = 30f;
        [SerializeField] float refreshSeconds = 0.3f;
        [SerializeField] float fadeSpeed = 4f;
        [SerializeField] float flickerAmount = 0.18f;
        [SerializeField] float flickerSpeed = 7f;

        sealed class Slot
        {
            public Light light;
            public ParticleSystem particles;
            public Transform transform;
            public FireSource source;
            public float level;
            public float seed;
        }

        FireSource[] sources = System.Array.Empty<FireSource>();
        Slot[] slots;
        float[] distances;
        int[] chosen;
        float nextRefresh;

        public int ActiveLightCount
        {
            get
            {
                var n = 0;
                if (slots == null) return 0;
                for (var i = 0; i < slots.Length; i++) if (slots[i].light.enabled) n++;
                return n;
            }
        }

        public int SourceCount => sources.Length;
        public int Capacity => maxActive;

        void Awake()
        {
            sources = FindObjectsByType<FireSource>(FindObjectsInactive.Exclude, FindObjectsSortMode.None);
            distances = new float[sources.Length];
            chosen = new int[maxActive];
            slots = new Slot[maxActive];
            for (var i = 0; i < maxActive; i++)
            {
                var go = new GameObject("FireSlot" + i);
                go.transform.SetParent(transform, false);
                var l = go.AddComponent<Light>();
                l.type = LightType.Point;
                l.shadows = LightShadows.None;
                l.renderMode = LightRenderMode.Auto;
                l.enabled = false;
                var psGo = new GameObject("Flame");
                psGo.transform.SetParent(go.transform, false);
                var ps = psGo.AddComponent<ParticleSystem>();
                Configure(ps);
                slots[i] = new Slot { light = l, particles = ps, transform = go.transform, seed = i * 13.37f };
            }
        }

        void Configure(ParticleSystem ps)
        {
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main;
            main.playOnAwake = false;
            main.loop = true;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.startLifetime = 0.8f;
            main.startSpeed = 0.9f;
            main.startSize = new ParticleSystem.MinMaxCurve(0.25f, 0.45f);
            main.maxParticles = 40;
            main.gravityModifier = -0.15f;
            var emission = ps.emission;
            emission.rateOverTime = 18f;
            var shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Circle;
            shape.radius = 0.28f;
            shape.rotation = new Vector3(-90f, 0f, 0f);
            var color = ps.colorOverLifetime;
            color.enabled = true;
            var gradient = new Gradient();
            gradient.SetKeys(
                new[] { new GradientColorKey(new Color(1f, 0.85f, 0.4f), 0f), new GradientColorKey(new Color(1f, 0.35f, 0.08f), 0.55f), new GradientColorKey(new Color(0.35f, 0.05f, 0.02f), 1f) },
                new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(0.9f, 0.15f), new GradientAlphaKey(0f, 1f) });
            color.color = gradient;
            var size = ps.sizeOverLifetime;
            size.enabled = true;
            size.size = new ParticleSystem.MinMaxCurve(1f, new AnimationCurve(new Keyframe(0f, 0.6f), new Keyframe(0.3f, 1f), new Keyframe(1f, 0f)));
            var renderer = ps.GetComponent<ParticleSystemRenderer>();
            renderer.renderMode = ParticleSystemRenderMode.Billboard;
            renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            renderer.receiveShadows = false;
            if (flameMaterial != null) renderer.sharedMaterial = flameMaterial;
        }

        void Update()
        {
            if (slots == null) return;
            var now = Time.unscaledTime;
            if (now >= nextRefresh)
            {
                nextRefresh = now + refreshSeconds;
                Reassign();
            }
            var dt = Time.unscaledDeltaTime;
            for (var i = 0; i < slots.Length; i++)
            {
                var s = slots[i];
                var goal = s.source != null ? 1f : 0f;
                s.level = Mathf.MoveTowards(s.level, goal, fadeSpeed * dt);
                if (s.level <= 0.001f && s.source == null)
                {
                    if (s.light.enabled) { s.light.enabled = false; s.particles.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear); }
                    continue;
                }
                if (!s.light.enabled) s.light.enabled = true;
                var flicker = 1f + (Mathf.PerlinNoise(s.seed, now * flickerSpeed) - 0.5f) * 2f * flickerAmount;
                var src = s.source;
                if (src != null)
                {
                    s.light.color = src.lightColor;
                    s.light.range = src.lightRange;
                    s.light.intensity = src.lightIntensity * s.level * flicker;
                }
                else
                {
                    s.light.intensity *= Mathf.Clamp01(s.level * 2f); // apagando
                }
            }
        }

        void Reassign()
        {
            var origin = target != null ? target.position : (Camera.main != null ? Camera.main.transform.position : Vector3.zero);
            var limit = maxDistance * maxDistance;
            var count = 0;
            for (var i = 0; i < sources.Length; i++)
            {
                var s = sources[i];
                if (s == null) { distances[i] = float.MaxValue; continue; }
                var d = s.transform.position - origin;
                d.y = 0f;
                var sq = d.sqrMagnitude;
                distances[i] = sq <= limit ? sq : float.MaxValue;
            }
            // Selecao dos maxActive menores (O(n * maxActive), sem alocacao).
            for (var k = 0; k < maxActive; k++)
            {
                var best = -1;
                var bestD = float.MaxValue;
                for (var i = 0; i < sources.Length; i++)
                {
                    if (distances[i] >= bestD) continue;
                    var taken = false;
                    for (var j = 0; j < count; j++) if (chosen[j] == i) { taken = true; break; }
                    if (taken) continue;
                    best = i;
                    bestD = distances[i];
                }
                if (best < 0) break;
                chosen[count++] = best;
            }
            // Mantem quem ja esta aceso; libera o que saiu; entrega os livres aos novos.
            for (var i = 0; i < slots.Length; i++)
            {
                var s = slots[i];
                if (s.source == null) continue;
                var keep = false;
                for (var j = 0; j < count; j++) if (sources[chosen[j]] == s.source) { keep = true; break; }
                if (!keep) { s.source = null; s.particles.Stop(true, ParticleSystemStopBehavior.StopEmitting); }
            }
            for (var j = 0; j < count; j++)
            {
                var src = sources[chosen[j]];
                var has = false;
                for (var i = 0; i < slots.Length; i++) if (slots[i].source == src) { has = true; break; }
                if (has) continue;
                for (var i = 0; i < slots.Length; i++)
                {
                    var s = slots[i];
                    if (s.source != null || s.level > 0.05f) continue; // so reusa espaco ja apagado
                    s.source = src;
                    s.transform.position = src.FirePoint;
                    s.light.enabled = true;
                    if (src.flame)
                    {
                        var main = s.particles.main;
                        main.startSizeMultiplier = src.flameScale;
                        s.particles.Play(true);
                    }
                    break;
                }
            }
        }
    }
}
