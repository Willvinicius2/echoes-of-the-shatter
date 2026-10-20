namespace Echoes.Interop
{
    /// <summary>
    /// PROVISÓRIO (stub). Porte fiel do <c>ShatterCore/include/shatter/rng.h</c> (SplitMix64 +
    /// PCG32 XSH-RR) sobre <see cref="RngState"/>. Os testes de EditMode comparam com valores
    /// gerados pelo próprio header C++, então a sequência é a mesma do core.
    /// </summary>
    public static class StubPcg32
    {
        const ulong DefaultSeed = 0x853C49E6748FEA9BUL;
        const ulong DefaultSequence = 0xDA3E39CB94B95BDBUL;

        public static ulong SplitMix64Next(ref ulong state)
        {
            unchecked
            {
                state += 0x9E3779B97F4A7C15UL;
                var z = state;
                z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9UL;
                z = (z ^ (z >> 27)) * 0x94D049BB133111EBUL;
                return z ^ (z >> 31);
            }
        }

        public static ulong Mix64(ulong x)
        {
            var s = x;
            return SplitMix64Next(ref s);
        }

        public static ulong DeriveSeed(ulong seed, RngStream stream, ulong index)
        {
            unchecked
            {
                var h = Mix64(seed ^ 0x45434F534F465348UL);
                h = Mix64(h ^ ((ulong)(uint)stream * 0xD6E8FEB86659FD93UL));
                h = Mix64(h ^ (index + 0x632BE59BD9B4E019UL));
                return h;
            }
        }

        public static RngState Create(ulong seed, ulong sequence)
        {
            var rng = new RngState();
            Seed(ref rng, seed, sequence);
            return rng;
        }

        public static RngState CreateDefault() => Create(DefaultSeed, DefaultSequence);

        public static RngState CreateWithSeed(ulong seed) => Create(seed, DefaultSequence);

        public static RngState ForStream(ulong expeditionSeed, RngStream stream, ulong index)
        {
            var s = DeriveSeed(expeditionSeed, stream, index);
            return Create(s, Mix64(s ^ 0xA5A5A5A5A5A5A5A5UL));
        }

        public static void Seed(ref RngState rng, ulong seed, ulong sequence)
        {
            unchecked
            {
                rng.State = 0UL;
                rng.Increment = (sequence << 1) | 1UL;
                NextU32(ref rng);
                rng.State += seed;
                NextU32(ref rng);
            }
        }

        public static uint NextU32(ref RngState rng)
        {
            unchecked
            {
                var old = rng.State;
                rng.State = old * 6364136223846793005UL + rng.Increment;
                var xorshifted = (uint)(((old >> 18) ^ old) >> 27);
                var rot = (int)(old >> 59);
                return (xorshifted >> rot) | (xorshifted << ((32 - rot) & 31));
            }
        }

        public static ulong NextU64(ref RngState rng)
        {
            ulong hi = NextU32(ref rng);
            return (hi << 32) | NextU32(ref rng);
        }

        public static uint NextBelow(ref RngState rng, uint bound)
        {
            if (bound == 0) return 0;
            unchecked
            {
                var threshold = (0u - bound) % bound;
                for (;;)
                {
                    var r = NextU32(ref rng);
                    if (r >= threshold) return r % bound;
                }
            }
        }

        /// <summary>Real uniforme em [0, 1) com 24 bits de mantissa.</summary>
        public static double NextUnit(ref RngState rng)
        {
            return (NextU32(ref rng) >> 8) * (1.0 / 16777216.0);
        }

        /// <summary>Sorteio com probabilidade p. Sempre consome 1 número.</summary>
        public static bool Chance(ref RngState rng, double p)
        {
            var u = NextUnit(ref rng);
            return u < p;
        }
    }
}
