using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Números da câmera 3/4 e do tremor (docs/04_arquitetura.md, seção 3.2; tokens juice.shake).
    /// Dado de apresentação, fora do CSV de balanceamento. Os padrões são os do documento.
    /// Crie em Assets/Data/Presentation (Create ▸ Echoes ▸ Render Settings).
    /// </summary>
    [CreateAssetMenu(menuName = "Echoes/Render Settings", fileName = "SO_RenderSettings")]
    public sealed class RenderSettingsAsset : ScriptableObject
    {
        [Header("Câmera (seção 3.2)")]
        [Tooltip("Rotação X do rig, olhando para baixo.")]
        [Range(50f, 60f)] public float pitchDegrees = 55f;
        [Tooltip("Rotação Y fixa; o jogador não gira.")]
        public float yawDegrees = 45f;
        [Tooltip("Camera.fieldOfView é vertical: 14,2° ≡ 25° horizontal em 16:9.")]
        public float verticalFieldOfView = 14.2f;
        [Tooltip("Distância da câmera ao alvo (faixa permitida 36 a 50 m).")]
        [Range(36f, 50f)] public float distance = 42f;
        [Tooltip("Ponto mirado = posição do herói + este deslocamento (enquadra o tronco).")]
        public Vector3 targetOffset = new Vector3(0f, 0.52f, 0f);
        [Tooltip("Suavização exponencial independente de FPS: Lerp(pos, alvo, 1 − exp(−k·dt)).")]
        public float smoothing = 7f;
        [Tooltip("Atraso máximo da câmera em metros (não perde o herói na esquiva).")]
        public float maxLagMeters = 2f;
        public float nearClip = 1f;
        public float farClip = 150f;

        [Header("Tremor (juice.shake; desligável nas opções)")]
        [Tooltip("Teto do deslocamento aditivo do rig, em metros.")]
        public float shakeMaxMeters = 0.08f;
        public float shakeHeavyMeters = 0.03f;
        public float shakeBossMeters = 0.05f;
        public float shakeSeconds = 0.2f;
        public float shakeFrequencyHz = 30f;
    }
}
