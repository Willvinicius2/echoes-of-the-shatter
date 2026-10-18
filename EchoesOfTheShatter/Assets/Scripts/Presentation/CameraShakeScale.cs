namespace Echoes.Presentation
{
    /// <summary>
    /// Escala do tremor de câmera (docs/tecnico/04_arquitetura.md, seção 3.2): as amplitudes de <c>juice.shake</c> são
    /// definidas em metros a 42 m e valem <c>distância / 42</c> vezes isso na distância real, para o tremor
    /// ocupar a mesma fração da tela em qualquer zoom (a 56 m, ×1,333). Lógica pura, testável fora da cena.
    /// </summary>
    public static class CameraShakeScale
    {
        /// <summary>Distância (m) em que as amplitudes dos tokens foram definidas.</summary>
        public const float DefaultReferenceDistance = 42f;

        public static float Factor(float cameraDistanceMeters, float referenceDistanceMeters)
        {
            if (referenceDistanceMeters <= 0f || cameraDistanceMeters <= 0f) return 1f;
            return cameraDistanceMeters / referenceDistanceMeters;
        }
    }
}
