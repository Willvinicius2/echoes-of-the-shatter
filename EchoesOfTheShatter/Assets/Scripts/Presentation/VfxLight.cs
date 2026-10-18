using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Luz pontual de um VFX (bola de fogo em voo, clarão da explosão) com orçamento: no máximo <see cref="MaxConcurrent"/> luzes de VFX
    /// acesas ao mesmo tempo (o <see cref="FirePool"/> usa as outras; docs/03 seção 3.6 e 04 seção 18). Quem passa do teto fica apagada.
    /// Curva de intensidade ao longo de <see cref="duration"/> (0 = laço, com tremor de chama). Sem sombra, sem alocação por quadro.
    /// </summary>
    [RequireComponent(typeof(Light))]
    public sealed class VfxLight : MonoBehaviour
    {
        /// <summary>Teto de luzes de VFX simultâneas (dado de apresentação; o SkillVfxPresenter ajusta pelo inspetor).</summary>
        public static int MaxConcurrent = 2;
        static int active;

        [SerializeField] float peakIntensity = 3f;
        [SerializeField] AnimationCurve intensityOverTime = AnimationCurve.Linear(0f, 1f, 1f, 0f);
        [Tooltip("Duração da curva em segundos. 0 = laço (a curva é ignorada e a luz treme como chama).")]
        [SerializeField, Min(0f)] float duration = 0.4f;
        [SerializeField, Range(0f, 0.5f)] float flicker = 0.15f;
        [SerializeField] float flickerSpeed = 14f;

        Light lamp;
        float time;
        float seed;
        bool counted;

        public void Configure(float peak, float seconds, AnimationCurve curve, float flickerAmount)
        {
            peakIntensity = peak;
            duration = seconds;
            if (curve != null) intensityOverTime = curve;
            flicker = flickerAmount;
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void ResetStatics()
        {
            active = 0;
            MaxConcurrent = 2;
        }

        void Awake()
        {
            lamp = GetComponent<Light>();
            lamp.shadows = LightShadows.None;
            lamp.type = LightType.Point;
        }

        void OnEnable()
        {
            time = 0f;
            seed = Random.value * 100f;
            counted = active < MaxConcurrent;
            if (counted) active++;
            lamp.enabled = counted;
            lamp.intensity = 0f;
        }

        void OnDisable()
        {
            if (counted) active--;
            counted = false;
        }

        void Update()
        {
            if (!counted) return;
            time += Time.deltaTime;
            var level = 1f;
            if (duration > 0f)
            {
                var t = time / duration;
                if (t >= 1f)
                {
                    lamp.intensity = 0f;
                    return;
                }
                level = intensityOverTime.Evaluate(t);
            }
            var noise = 1f + (Mathf.PerlinNoise(seed, time * flickerSpeed) - 0.5f) * 2f * flicker;
            lamp.intensity = peakIntensity * level * noise;
        }
    }
}
