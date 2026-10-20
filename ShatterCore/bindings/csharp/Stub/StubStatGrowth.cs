namespace Echoes.Interop
{
    /// <summary>PROVISÓRIO (stub). Atributo por nível: base + porNível × (nível − 1) (<c>shatter::StatGrowth</c>).</summary>
    internal struct StubStatGrowth
    {
        public StatId Stat;
        public double Base;
        public double PerLevel;

        public double At(int level) => Base + PerLevel * (level - 1);
    }
}
