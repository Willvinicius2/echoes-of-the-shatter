using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Números da câmera 3/4 e do tremor (docs/tecnico/04_arquitetura.md, seção 3.2; tokens juice.shake).
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
        [Tooltip("Distância da câmera ao alvo: 56 m por decisão do dono em 16/10/2026 (faixa permitida 48 a 66 m).")]
        [Range(48f, 66f)] public float distance = 56f;
        [Tooltip("Ponto mirado = posição do herói + este deslocamento (enquadra o tronco).")]
        public Vector3 targetOffset = new Vector3(0f, 0.52f, 0f);
        [Tooltip("Suavização exponencial independente de FPS: Lerp(pos, alvo, 1 − exp(−k·dt)).")]
        public float smoothing = 7f;
        [Tooltip("Atraso máximo da câmera em metros (não perde o herói na esquiva).")]
        public float maxLagMeters = 2f;
        public float nearClip = 1f;
        public float farClip = 150f;

        [Header("Oclusão (seção 3.7)")]
        [Tooltip("Raio do buraco no fade de oclusão (_EchoesFadeRadius), em metros: ~4 m a 56 m (era ~3 m a 42 m; escala por 56/42 para cobrir a mesma fração da tela).")]
        public float occlusionFadeRadiusMeters = 4f;

        [Header("Tremor (juice.shake; desligável nas opções)")]
        [Tooltip("Distância da câmera em que as amplitudes abaixo (em metros) foram definidas: 42 m. A amplitude aplicada é escalada por distância/42, para o tremor ocupar a mesma fração da tela em qualquer zoom.")]
        public float shakeReferenceDistance = 42f;
        [Tooltip("Teto do deslocamento aditivo do rig, em metros, medido na distância de referência (42 m).")]
        public float shakeMaxMeters = 0.08f;
        public float shakeHeavyMeters = 0.03f;
        public float shakeBossMeters = 0.05f;
        public float shakeSeconds = 0.2f;
        [Tooltip("Golpe pesado do herói (forte, fecho do combo): tremor curto.")]
        public float shakeHeroHeavySeconds = 0.12f;
        public float shakeFrequencyHz = 30f;
    }
}
