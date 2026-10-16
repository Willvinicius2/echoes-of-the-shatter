using System.Collections.Generic;
using System.Text;

namespace Echoes.Core
{
    /// <summary>
    /// Leitor de CSV próprio (RFC 4180: vírgula, aspas duplas com "" de escape, quebra de linha dentro
    /// de aspas, UTF-8 com ou sem BOM). Usado pela localização (docs/04_arquitetura.md, seção 7).
    /// Não interpreta números: a localização só lê texto.
    /// </summary>
    public static class CsvReader
    {
        /// <summary>Divide o texto em registros; cada registro é a lista de campos e a linha (1-based) onde começa.</summary>
        public static List<CsvRecord> Parse(string text)
        {
            var records = new List<CsvRecord>();
            if (string.IsNullOrEmpty(text)) return records;

            var cells = new List<string>();
            var field = new StringBuilder();
            var inQuotes = false;
            var line = 1;
            var recordLine = 1;
            var i = text[0] == '﻿' ? 1 : 0;

            for (; i < text.Length; i++)
            {
                var c = text[i];
                if (inQuotes)
                {
                    if (c == '"')
                    {
                        if (i + 1 < text.Length && text[i + 1] == '"')
                        {
                            field.Append('"');
                            i++;
                        }
                        else
                        {
                            inQuotes = false;
                        }
                    }
                    else
                    {
                        if (c == '\n') line++;
                        field.Append(c);
                    }
                    continue;
                }

                if (c == '"')
                {
                    inQuotes = true;
                }
                else if (c == ',')
                {
                    cells.Add(field.ToString());
                    field.Clear();
                }
                else if (c == '\n')
                {
                    cells.Add(field.ToString());
                    field.Clear();
                    AddRecord(records, cells, recordLine);
                    line++;
                    recordLine = line;
                }
                else if (c != '\r')
                {
                    field.Append(c);
                }
            }

            if (field.Length > 0 || cells.Count > 0)
            {
                cells.Add(field.ToString());
                AddRecord(records, cells, recordLine);
            }
            return records;
        }

        static void AddRecord(List<CsvRecord> records, List<string> cells, int line)
        {
            var isEmpty = cells.Count == 1 && cells[0].Length == 0;
            if (!isEmpty) records.Add(new CsvRecord(cells.ToArray(), line));
            cells.Clear();
        }
    }
}
