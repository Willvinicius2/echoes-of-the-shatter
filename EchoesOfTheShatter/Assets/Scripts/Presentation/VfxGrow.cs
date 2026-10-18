using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Faz o filho crescer de <see cref="from"/> a 1 (vezes a escala do prefab) ao ativar: brilho de carga que cresce com a carga do golpe
    /// forte (docs/18, fx.charge.glow: 10 a 70 cm). Em pool: reinicia a cada ativação. Sem alocação por quadro.
    /// </summary>
    public sealed class VfxGrow : MonoBehaviour
    {
        [SerializeField, Range(0.01f, 1f)] float from = 0.15f;
        [SerializeField, Min(0.01f)] float seconds = 0.8f;
        [SerializeField] AnimationCurve curve = AnimationCurve.EaseInOut(0f, 0f, 1f, 1f);

        Vector3 baseScale;
        bool captured;
        float time;

        public void Configure(float startFraction, float growSeconds)
        {
            from = startFraction;
            seconds = growSeconds;
        }

        void OnEnable()
        {
            if (!captured)
            {
                baseScale = transform.localScale;
                captured = true;
            }
            time = 0f;
            transform.localScale = baseScale * from;
        }

        void Update()
        {
            if (time >= seconds) return;
            time += Time.deltaTime;
            var t = Mathf.Clamp01(time / seconds);
            transform.localScale = baseScale * Mathf.Lerp(from, 1f, curve.Evaluate(t));
        }
    }
}
