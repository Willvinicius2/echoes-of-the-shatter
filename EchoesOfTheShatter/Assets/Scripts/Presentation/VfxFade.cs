using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Anima um MeshRenderer de VFX por <see cref="MaterialPropertyBlock"/> (não instancia material): alfa/brilho pela curva e
    /// largura/comprimento pela escala. Usado no feixe do Raio Arcano, na cúpula da Barreira e nas ondas de choque em malha.
    /// Reinicia a cada ativação (efeito em pool).
    /// </summary>
    [RequireComponent(typeof(MeshRenderer))]
    public sealed class VfxFade : MonoBehaviour
    {
        static readonly int BaseColorId = Shader.PropertyToID("_BaseColor");
        static readonly int AlphaId = Shader.PropertyToID("_Alpha");

        [SerializeField, Min(0.01f)] float duration = 0.33f;
        [SerializeField] bool loop;
        [Tooltip("Multiplicador do alfa/brilho ao longo da vida.")]
        [SerializeField] AnimationCurve alpha = AnimationCurve.Linear(0f, 1f, 1f, 0f);
        [Tooltip("Multiplicador da escala X/Y (largura) ao longo da vida.")]
        [SerializeField] AnimationCurve width = AnimationCurve.Constant(0f, 1f, 1f);
        [Tooltip("Multiplicador da escala Z (comprimento) ao longo da vida.")]
        [SerializeField] AnimationCurve length = AnimationCurve.Constant(0f, 1f, 1f);
        [SerializeField] Color color = Color.white;
        [Tooltip("Usa a propriedade _Alpha (shader da cúpula) em vez do alfa de _BaseColor.")]
        [SerializeField] bool useAlphaProperty;
        [SerializeField] Vector2 scroll;

        MeshRenderer meshRenderer;
        MaterialPropertyBlock block;
        Vector3 baseScale;
        bool captured;
        float time;

        public void Configure(float seconds, bool looping, AnimationCurve alphaCurve, AnimationCurve widthCurve, AnimationCurve lengthCurve, Color tint, bool alphaProperty)
        {
            duration = seconds;
            loop = looping;
            if (alphaCurve != null) alpha = alphaCurve;
            if (widthCurve != null) width = widthCurve;
            if (lengthCurve != null) length = lengthCurve;
            color = tint;
            useAlphaProperty = alphaProperty;
        }

        void Awake()
        {
            meshRenderer = GetComponent<MeshRenderer>();
            block = new MaterialPropertyBlock();
        }

        void OnEnable()
        {
            if (!captured)
            {
                baseScale = transform.localScale; // escala local do filho; o VfxPool escala a raiz
                captured = true;
            }
            time = 0f;
            meshRenderer.enabled = true;
            Apply(0f);
        }

        void Update()
        {
            time += Time.deltaTime;
            var t = time / duration;
            if (t >= 1f)
            {
                if (!loop)
                {
                    meshRenderer.enabled = false;
                    return;
                }
                t -= Mathf.Floor(t);
            }
            if (!meshRenderer.enabled) meshRenderer.enabled = true;
            Apply(t);
        }

        void Apply(float t)
        {
            meshRenderer.GetPropertyBlock(block);
            var a = Mathf.Max(0f, alpha.Evaluate(t));
            if (useAlphaProperty) block.SetFloat(AlphaId, a);
            else block.SetColor(BaseColorId, new Color(color.r, color.g, color.b, color.a * a));
            if (scroll != Vector2.zero) block.SetVector("_BaseMap_ST", new Vector4(1f, 1f, scroll.x * time, scroll.y * time));
            meshRenderer.SetPropertyBlock(block);
            var w = width.Evaluate(t);
            var l = length.Evaluate(t);
            transform.localScale = new Vector3(baseScale.x * w, baseScale.y * w, baseScale.z * l);
        }
    }
}
