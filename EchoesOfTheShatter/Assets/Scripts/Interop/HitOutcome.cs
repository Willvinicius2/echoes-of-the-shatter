namespace Echoes.Interop
{
    /// <summary>Resultado de um golpe (<c>shatter::HitOutcome</c>, damage.h).</summary>
    public enum HitOutcome : byte
    {
        Hit = 0,
        Evaded = 1,
        Blocked = 2,
    }
}
