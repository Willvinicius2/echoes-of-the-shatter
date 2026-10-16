using System;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Consultas de forma no plano XZ (cone, círculo, corredor) contra alvos circulares. Matemática
    /// pura e sem alocação, no lugar de Physics.Overlap*: os alvos do combate são poucos e ficam
    /// registrados no CombatSystem, então a consulta é determinística e testável sem física.
    /// O alcance e o ângulo são os mesmos do telegraph, para o aviso não mentir (docs/04, seção 3.10).
    /// </summary>
    public static class ShapeQuery
    {
        public static bool InCircle(PlanarVector center, float radius, PlanarVector target, float targetRadius)
        {
            var reach = radius + targetRadius;
            return (target - center).SqrMagnitude <= reach * reach;
        }

        /// <param name="forward">Direção do cone (normalizada).</param>
        /// <param name="halfAngleDegrees">Metade da abertura total.</param>
        public static bool InCone(PlanarVector origin, PlanarVector forward, float range, float halfAngleDegrees,
            PlanarVector target, float targetRadius)
        {
            var toTarget = target - origin;
            var distance = toTarget.Magnitude;
            if (distance > range + targetRadius) return false;
            if (distance <= targetRadius) return true; // alvo em cima da origem
            if (halfAngleDegrees >= 180f) return true;

            // O corpo do alvo conta: soma o ângulo que o raio dele ocupa visto da origem.
            var padding = (float)(Math.Asin(Math.Min(1.0, targetRadius / distance)) * (180.0 / Math.PI));
            var angle = PlanarVector.AngleDegrees(forward, toTarget);
            return angle <= halfAngleDegrees + padding;
        }

        /// <summary>Corredor de <paramref name="start"/> a <paramref name="end"/> com meia largura dada.</summary>
        public static bool InCorridor(PlanarVector start, PlanarVector end, float halfWidth, PlanarVector target, float targetRadius)
        {
            var reach = halfWidth + targetRadius;
            return DistanceToSegmentSquared(start, end, target) <= reach * reach;
        }

        public static float DistanceToSegmentSquared(PlanarVector a, PlanarVector b, PlanarVector p)
        {
            var ab = b - a;
            var lengthSq = ab.SqrMagnitude;
            if (lengthSq < 1e-8f) return (p - a).SqrMagnitude;
            var t = PlanarVector.Dot(p - a, ab) / lengthSq;
            if (t < 0f) t = 0f;
            if (t > 1f) t = 1f;
            var closest = a + ab * t;
            return (p - closest).SqrMagnitude;
        }
    }
}
