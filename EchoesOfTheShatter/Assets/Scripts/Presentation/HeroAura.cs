using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Aura sutil do heroi (so apresentacao): anel suave no chao que pulsa devagar e particulas finas subindo ao redor, na cor do heroi.
    /// Sem brilho de borda no corpo: o efeito fica no chao e em volta, nunca no contorno do modelo. Materiais aditivos vem do VFX (anel e ponto).
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class HeroAura : MonoBehaviour
    {
        [SerializeField] Color color = new Color(1f, 0.35f, 0.25f, 1f);
        [SerializeField] Material ringMaterial;
        [SerializeField] Material moteMaterial;
        [SerializeField, Range(0.3f, 2f)] float ringRadius = 0.85f;
        [SerializeField, Range(0f, 1f)] float ringAlpha = 0.45f;
        [SerializeField, Range(0f, 30f)] float motesPerSecond = 10f;

        Transform ring;
        Material ringInstance;
        float t;

        public void Configure(Color c, Material ringMat, Material moteMat) { color = c; ringMaterial = ringMat; moteMaterial = moteMat; }

        ParticleSystem motes;

        void Awake() => BuildNow();

        /// <summary>Monta anel e particulas (idempotente). Publico para as capturas no Editor, onde o Awake nao roda.</summary>
        public void BuildNow()
        {
            if (ring == null && ringMaterial != null) BuildRing();
            if (motes == null && moteMaterial != null) BuildMotes();
        }

        /// <summary>Avanca as particulas sem Play (captura no Editor).</summary>
        public void SimulatePreview(float seconds)
        {
            if (motes != null) motes.Simulate(seconds, true, true);
        }

        void BuildRing()
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Quad);
            Destroy(go.GetComponent<Collider>());
            go.name = "Aura_Ring";
            ring = go.transform;
            ring.SetParent(transform, false);
            ring.localPosition = new Vector3(0f, 0.03f, 0f);
            ring.localRotation = Quaternion.Euler(90f, 0f, 0f);
            ring.localScale = Vector3.one * ringRadius * 2f;
            var r = go.GetComponent<MeshRenderer>();
            ringInstance = new Material(ringMaterial);
            Tint(ringInstance, ringAlpha);
            r.sharedMaterial = ringInstance;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            r.receiveShadows = false;
        }

        void Tint(Material m, float alpha)
        {
            var c = new Color(color.r * alpha, color.g * alpha, color.b * alpha, 1f);
            if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", c);
            if (m.HasProperty("_Color")) m.SetColor("_Color", c);
        }

        void BuildMotes()
        {
            var go = new GameObject("Aura_Motes");
            go.transform.SetParent(transform, false);
            go.transform.localPosition = new Vector3(0f, 0.05f, 0f);
            var ps = go.AddComponent<ParticleSystem>();
            motes = ps;
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main;
            main.loop = true;
            main.startLifetime = new ParticleSystem.MinMaxCurve(1.1f, 1.8f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(0.25f, 0.5f);
            main.startSize = new ParticleSystem.MinMaxCurve(0.04f, 0.09f);
            main.startColor = new Color(color.r, color.g, color.b, 0.9f);
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.gravityModifier = -0.02f;
            var em = ps.emission; em.rateOverTime = motesPerSecond;
            var sh = ps.shape; sh.shapeType = ParticleSystemShapeType.Circle; sh.radius = ringRadius * 0.6f; sh.rotation = new Vector3(-90f, 0f, 0f);
            var col = ps.colorOverLifetime; col.enabled = true;
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
                      new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(0.9f, 0.2f), new GradientAlphaKey(0f, 1f) });
            col.color = g;
            var rend = go.GetComponent<ParticleSystemRenderer>();
            rend.sharedMaterial = moteMaterial;
            rend.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            ps.Play();
        }

        void Update()
        {
            if (ring == null) return;
            t += Time.deltaTime;
            float k = 1f + 0.05f * Mathf.Sin(t * 1.6f);
            ring.localScale = Vector3.one * ringRadius * 2f * k;
            ring.localRotation = Quaternion.Euler(90f, t * 12f, 0f);
        }

        void OnDestroy() { if (ringInstance != null) Destroy(ringInstance); }
    }
}
