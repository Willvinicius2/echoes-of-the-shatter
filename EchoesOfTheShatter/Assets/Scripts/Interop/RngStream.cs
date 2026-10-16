namespace Echoes.Interop
{
    /// <summary>Fluxos de RNG separados (<c>shatter::RngStream</c>, rng.h): mudar o combate não muda o loot.</summary>
    public enum RngStream : uint
    {
        Combat = 1,
        Loot = 2,
        Events = 3,
    }
}
