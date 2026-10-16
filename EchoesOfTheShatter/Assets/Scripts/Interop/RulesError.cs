namespace Echoes.Interop
{
    /// <summary>
    /// Detalhe de um erro do motor de regras (equivalente ao <c>shatter_error</c> da API C).
    /// A mensagem é técnica, em inglês, só para log; nunca vai para a tela do jogador.
    /// </summary>
    public readonly struct RulesError
    {
        public readonly RulesStatus Status;
        public readonly string Table;
        public readonly int Line;
        public readonly string Message;

        public RulesError(RulesStatus status, string table, int line, string message)
        {
            Status = status;
            Table = table ?? string.Empty;
            Line = line;
            Message = message ?? string.Empty;
        }

        public override string ToString()
        {
            return Line > 0 ? $"{Table}:{Line} [{Status}] {Message}" : $"{Table} [{Status}] {Message}";
        }
    }
}
