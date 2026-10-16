using UnityEngine;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Área do chão visível na câmera, centrada no herói e reduzida por uma margem (R-VIS-1, docs/14 seção 8.2). Sai do frustum da
    /// câmera (projeta os 4 cantos da viewport no plano do chão), nunca de números fixos: continua certa se o FOV ou a altura mudarem.
    /// </summary>
    public static class VisibleArea
    {
        /// <summary>
        /// Eixos da tela projetados no chão: "direita" (câmera para a direita) e "cima" (para onde a câmera olha, no plano). A câmera da
        /// Cripta tem yaw de 45° (docs/04 seção 3.2), então o retângulo da tela NÃO é alinhado aos eixos do mundo (o doc 14 supunha sem yaw).
        /// </summary>
        public static void GetScreenAxes(Camera camera, out Vector2 right, out Vector2 up)
        {
            var r = camera.transform.right;
            var f = camera.transform.forward;
            right = new Vector2(r.x, r.z).normalized;
            up = new Vector2(f.x, f.z).normalized;
        }

        /// <summary>
        /// Metade da largura ("direita") e da altura ("cima") do retângulo da tela, centrado em <paramref name="hero"/>, que cabe inteiro na
        /// viewport, menos <paramref name="margin"/>. Falso se a câmera não enxerga o chão.
        /// </summary>
        public static bool TryGetHalfExtents(Camera camera, PlanarVector hero, float margin, out float halfRight, out float halfUp)
        {
            halfRight = 0f;
            halfUp = 0f;
            if (camera == null) return false;
            GetScreenAxes(camera, out var right, out var up);
            var plane = new Plane(Vector3.up, Vector3.zero);
            var minRight = float.MaxValue;
            var minUp = float.MaxValue;
            var corners = new[] { new Vector2(0f, 0f), new Vector2(1f, 0f), new Vector2(0f, 1f), new Vector2(1f, 1f) };
            for (var i = 0; i < corners.Length; i++)
            {
                var ray = camera.ViewportPointToRay(corners[i]);
                if (!plane.Raycast(ray, out var distance)) return false;
                var p = ray.GetPoint(distance);
                var offset = new Vector2(p.x - hero.X, p.z - hero.Z);
                minRight = Mathf.Min(minRight, Mathf.Abs(Vector2.Dot(offset, right)));
                minUp = Mathf.Min(minUp, Mathf.Abs(Vector2.Dot(offset, up)));
            }
            halfRight = Mathf.Max(0f, minRight - margin);
            halfUp = Mathf.Max(0f, minUp - margin);
            return true;
        }

        public static bool Contains(Camera camera, PlanarVector hero, PlanarVector point, float margin)
        {
            if (!TryGetHalfExtents(camera, hero, margin, out var hr, out var hu)) return true;
            GetScreenAxes(camera, out var right, out var up);
            var offset = new Vector2(point.X - hero.X, point.Z - hero.Z);
            return Mathf.Abs(Vector2.Dot(offset, right)) <= hr && Mathf.Abs(Vector2.Dot(offset, up)) <= hu;
        }
    }
}
