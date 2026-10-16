namespace Echoes.Interop
{
    /// <summary>
    /// Status devolvido pelas chamadas ao motor de regras. Espelha o <c>shatter_status</c>
    /// da API C (docs/04_arquitetura.md, seção 9.2), para a troca do stub pela DLL ser direta.
    /// </summary>
    public enum RulesStatus
    {
        Ok = 0,
        InvalidArgument = 1,
        BufferTooSmall = 2,
        ParseError = 3,
        ContentInvalid = 4,
        IoError = 5,
        VersionMismatch = 6,
        NotFound = 7,
        Internal = 8,
    }
}
