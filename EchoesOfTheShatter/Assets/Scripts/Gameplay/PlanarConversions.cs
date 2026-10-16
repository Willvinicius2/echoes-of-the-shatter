using UnityEngine;

namespace Echoes.Gameplay
{
    /// <summary>Conversão entre o plano da lógica (<see cref="PlanarVector"/>) e o mundo Unity (XZ, Y para cima).</summary>
    public static class PlanarConversions
    {
        public static PlanarVector ToPlanar(this Vector3 v) => new PlanarVector(v.x, v.z);

        public static PlanarVector ToPlanar(this Vector2 v) => new PlanarVector(v.x, v.y);

        public static Vector3 ToWorld(this PlanarVector v, float y = 0f) => new Vector3(v.X, y, v.Z);

        /// <summary>Rotação que olha para a direção no plano (identidade se a direção é zero).</summary>
        public static Quaternion ToRotation(this PlanarVector direction, Quaternion fallback)
        {
            if (direction.SqrMagnitude < 1e-8f) return fallback;
            return Quaternion.LookRotation(new Vector3(direction.X, 0f, direction.Z), Vector3.up);
        }
    }
}
