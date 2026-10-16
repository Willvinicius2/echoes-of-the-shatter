namespace Echoes.Core
{
    /// <summary>Um registro de CSV: campos e linha do arquivo (1-based) onde começa.</summary>
    public readonly struct CsvRecord
    {
        public readonly string[] Fields;
        public readonly int Line;

        public CsvRecord(string[] fields, int line)
        {
            Fields = fields;
            Line = line;
        }
    }
}
