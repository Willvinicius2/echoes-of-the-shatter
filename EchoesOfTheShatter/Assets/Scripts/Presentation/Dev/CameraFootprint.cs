using System;

namespace Echoes.Presentation
{
    /// <summary>
    /// Conta geométrica da câmera 3/4 (docs/tecnico/04_arquitetura.md, seção 3.2), sem UnityEngine para testar
    /// fora da engine. Largura e altura perpendiculares ao eixo da câmera, à distância do alvo; a
    /// profundidade no chão é a altura perpendicular dividida pelo seno do pitch (42 m dá ~18,6 × 10,5 m
    /// e ~12,8 m de chão, ou 6,4 módulos de 2 m).
    /// </summary>
    public static class CameraFootprint
    {
        public static float PerpendicularHeight(float distance, float verticalFovDegrees)
        {
            return 2f * distance * (float)Math.Tan(verticalFovDegrees * Math.PI / 360.0);
        }

        /// <summary>Largura visível em metros, para o aspecto dado (16:9 = 1,7778).</summary>
        public static float VisibleWidth(float distance, float verticalFovDegrees, float aspect)
        {
            return PerpendicularHeight(distance, verticalFovDegrees) * aspect;
        }

        /// <summary>Profundidade de chão visível em metros (chão plano, câmera olhando para o alvo com este pitch).</summary>
        public static float VisibleGroundDepth(float distance, float verticalFovDegrees, float pitchDegrees)
        {
            var sin = (float)Math.Sin(pitchDegrees * Math.PI / 180.0);
            return sin > 1e-4f ? PerpendicularHeight(distance, verticalFovDegrees) / sin : 0f;
        }

        /// <summary>Próxima distância um passo acima (direction &gt; 0) ou abaixo, alinhada à grade do passo e presa à faixa.</summary>
        public static float StepDistance(float current, int direction, float step, float min, float max)
        {
            if (step <= 0f) return Clamp(current, min, max);
            var snapped = (float)Math.Round(current / step) * step;
            if (direction > 0 && snapped <= current + 1e-4f) snapped += step;
            else if (direction < 0 && snapped >= current - 1e-4f) snapped -= step;
            return Clamp(snapped, min, max);
        }

        public static float FarClip(float distance, float margin) => distance + margin;

        static float Clamp(float v, float min, float max) => v < min ? min : v > max ? max : v;
    }
}
