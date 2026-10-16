using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Balanço leve e procedural do Arqueiro Espectral somado ao Idle do clipe (o espectro flutua): uma pequena rotação lenta no quadril, aplicada
    /// no LateUpdate por cima da pose do Animator (que reescreve o osso a cada quadro, então não acumula). Sem IA: só senoides.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class SpectralSway : MonoBehaviour
    {
        public static bool GlobalEnabled = true;

        [SerializeField] Animator animator;
        [Tooltip("Osso do quadril (Generic: nome do Transform).")]
        [SerializeField] string boneName = "Hips";
        [Tooltip("Inclinação máxima em graus (lado e frente).")]
        [SerializeField, Range(0f, 8f)] float degrees = 2.5f;
        [Tooltip("Frequência do balanço em Hz.")]
        [SerializeField, Range(0.05f, 2f)] float hertz = 0.35f;

        Transform bone;
        float phase;

        void Awake()
        {
            if (animator == null) animator = GetComponentInChildren<Animator>();
            if (animator != null) bone = Find(animator.transform, boneName);
            phase = Random.value * Mathf.PI * 2f;
        }

        public static Quaternion OffsetAt(float time, float phase, float degrees, float hertz)
        {
            var w = time * hertz * Mathf.PI * 2f + phase;
            return Quaternion.Euler(Mathf.Sin(w * 0.8f + 1.3f) * degrees * 0.6f, 0f, Mathf.Sin(w) * degrees);
        }

        void LateUpdate()
        {
            if (!GlobalEnabled || bone == null) return;
            bone.localRotation *= OffsetAt(Time.time, phase, degrees, hertz);
        }

        static Transform Find(Transform parent, string name)
        {
            if (parent.name == name) return parent;
            for (var i = 0; i < parent.childCount; i++)
            {
                var found = Find(parent.GetChild(i), name);
                if (found != null) return found;
            }
            return null;
        }
    }
}
