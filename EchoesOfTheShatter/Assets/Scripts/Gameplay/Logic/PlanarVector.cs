using System;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Vetor no plano do chão (XZ do Unity, em metros). A lógica de combate vive neste plano
    /// (docs/tecnico/04_arquitetura.md, seção 3.1) e não depende de UnityEngine, para rodar em teste puro.
    /// </summary>
    [Serializable]
    public struct PlanarVector : IEquatable<PlanarVector>
    {
        public float X;
        public float Z;

        public PlanarVector(float x, float z)
        {
            X = x;
            Z = z;
        }

        public static PlanarVector Zero => new PlanarVector(0f, 0f);
        public static PlanarVector Forward => new PlanarVector(0f, 1f);

        public float SqrMagnitude => X * X + Z * Z;
        public float Magnitude => (float)Math.Sqrt(X * X + Z * Z);
        public bool IsZero => X == 0f && Z == 0f;

        public PlanarVector Normalized
        {
            get
            {
                var m = Magnitude;
                return m > 1e-6f ? new PlanarVector(X / m, Z / m) : Zero;
            }
        }

        /// <summary>Normalizado, ou <paramref name="fallback"/> se o vetor é (quase) zero.</summary>
        public PlanarVector NormalizedOr(PlanarVector fallback)
        {
            var m = Magnitude;
            return m > 1e-6f ? new PlanarVector(X / m, Z / m) : fallback;
        }

        public PlanarVector ClampMagnitude(float max)
        {
            var sq = SqrMagnitude;
            if (sq <= max * max) return this;
            var m = (float)Math.Sqrt(sq);
            return new PlanarVector(X / m * max, Z / m * max);
        }

        public static float Dot(PlanarVector a, PlanarVector b) => a.X * b.X + a.Z * b.Z;

        public static float Distance(PlanarVector a, PlanarVector b) => (a - b).Magnitude;

        /// <summary>Ângulo em graus entre dois vetores (0 a 180).</summary>
        public static float AngleDegrees(PlanarVector a, PlanarVector b)
        {
            var den = a.Magnitude * b.Magnitude;
            if (den < 1e-6f) return 0f;
            var cos = Dot(a, b) / den;
            if (cos > 1f) cos = 1f;
            if (cos < -1f) cos = -1f;
            return (float)(Math.Acos(cos) * (180.0 / Math.PI));
        }

        /// <summary>Gira <paramref name="from"/> em direção a <paramref name="to"/> no máximo <paramref name="maxDegrees"/>.</summary>
        public static PlanarVector RotateTowards(PlanarVector from, PlanarVector to, float maxDegrees)
        {
            var a = from.NormalizedOr(Forward);
            var b = to.NormalizedOr(a);
            var angle = AngleDegrees(a, b);
            if (angle <= maxDegrees || angle < 1e-4f) return b;
            var cross = a.X * b.Z - a.Z * b.X; // sinal: sentido do giro
            var step = maxDegrees * (Math.PI / 180.0) * (cross >= 0f ? 1.0 : -1.0);
            var cos = Math.Cos(step);
            var sin = Math.Sin(step);
            // Rotação no plano: x' = x·cos − z·sin; z' = x·sin + z·cos (anti-horário visto de cima com +Z para a frente).
            return new PlanarVector((float)(a.X * cos - a.Z * sin), (float)(a.X * sin + a.Z * cos));
        }

        public static PlanarVector operator +(PlanarVector a, PlanarVector b) => new PlanarVector(a.X + b.X, a.Z + b.Z);
        public static PlanarVector operator -(PlanarVector a, PlanarVector b) => new PlanarVector(a.X - b.X, a.Z - b.Z);
        public static PlanarVector operator -(PlanarVector a) => new PlanarVector(-a.X, -a.Z);
        public static PlanarVector operator *(PlanarVector a, float s) => new PlanarVector(a.X * s, a.Z * s);
        public static PlanarVector operator *(float s, PlanarVector a) => new PlanarVector(a.X * s, a.Z * s);

        public bool Equals(PlanarVector other) => X == other.X && Z == other.Z;
        public override bool Equals(object obj) => obj is PlanarVector other && Equals(other);
        public override int GetHashCode() => (X.GetHashCode() * 397) ^ Z.GetHashCode();
        public override string ToString() => $"({X:0.###}, {Z:0.###})";
    }
}
