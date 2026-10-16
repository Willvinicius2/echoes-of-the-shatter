using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace Echoes.Interop
{
    /// <summary>
    /// PROVISÓRIO (stub). Leitor de CSV (RFC 4180: vírgula, aspas duplas, quebra de linha dentro de
    /// aspas, UTF-8) usado só pelo <see cref="StubRulesCore"/>. Números sempre com
    /// <see cref="CultureInfo.InvariantCulture"/> (ponto decimal), como o <c>from_chars</c> do core.
    /// </summary>
    internal sealed class StubCsvTable
    {
        internal readonly struct Row
        {
            public readonly string[] Cells;
            public readonly int Line;

            public Row(string[] cells, int line)
            {
                Cells = cells;
                Line = line;
            }
        }

        readonly Dictionary<string, int> columns = new Dictionary<string, int>(StringComparer.Ordinal);

        public string Name { get; }
        public string[] Header { get; private set; } = Array.Empty<string>();
        public List<Row> Rows { get; } = new List<Row>();

        StubCsvTable(string name)
        {
            Name = name;
        }

        public bool HasColumn(string column) => columns.ContainsKey(column);

        public static StubCsvTable Parse(string name, string text, List<RulesError> errors)
        {
            var table = new StubCsvTable(name);
            var records = SplitRecords(text, name, errors);
            if (records.Count == 0)
            {
                errors.Add(new RulesError(RulesStatus.ParseError, name, 0, "empty file"));
                return table;
            }

            table.Header = records[0].Cells;
            for (var i = 0; i < table.Header.Length; i++)
            {
                var col = table.Header[i].Trim();
                table.Header[i] = col;
                if (!table.columns.ContainsKey(col)) table.columns.Add(col, i);
            }

            for (var r = 1; r < records.Count; r++)
            {
                var rec = records[r];
                if (rec.Cells.Length == 1 && rec.Cells[0].Length == 0) continue; // linha vazia
                if (rec.Cells.Length != table.Header.Length)
                {
                    errors.Add(new RulesError(RulesStatus.ParseError, name, rec.Line,
                        $"expected {table.Header.Length} columns, got {rec.Cells.Length}"));
                    continue;
                }
                table.Rows.Add(rec);
            }
            return table;
        }

        public string GetString(in Row row, string column, string fallback = "")
        {
            if (!columns.TryGetValue(column, out var index)) return fallback;
            var value = row.Cells[index];
            return value.Length == 0 ? fallback : value;
        }

        public double GetDouble(in Row row, string column, double fallback, List<RulesError> errors)
        {
            var text = GetString(row, column);
            if (text.Length == 0) return fallback;
            if (TryParseDouble(text, out var value)) return value;
            errors.Add(new RulesError(RulesStatus.ParseError, Name, row.Line, $"column '{column}': '{text}' is not a number"));
            return fallback;
        }

        public int GetInt(in Row row, string column, int fallback, List<RulesError> errors)
        {
            var text = GetString(row, column);
            if (text.Length == 0) return fallback;
            if (int.TryParse(text, NumberStyles.Integer, CultureInfo.InvariantCulture, out var value)) return value;
            errors.Add(new RulesError(RulesStatus.ParseError, Name, row.Line, $"column '{column}': '{text}' is not an integer"));
            return fallback;
        }

        public bool GetBool(in Row row, string column, bool fallback, List<RulesError> errors)
        {
            var text = GetString(row, column);
            if (text.Length == 0) return fallback;
            if (text == "true") return true;
            if (text == "false") return false;
            errors.Add(new RulesError(RulesStatus.ParseError, Name, row.Line, $"column '{column}': '{text}' is not true/false"));
            return fallback;
        }

        public static bool TryParseDouble(string text, out double value)
        {
            return double.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out value);
        }

        static List<Row> SplitRecords(string text, string name, List<RulesError> errors)
        {
            var records = new List<Row>();
            var cells = new List<string>();
            var field = new StringBuilder();
            var inQuotes = false;
            var line = 1;
            var recordLine = 1;
            var i = 0;
            if (text.Length > 0 && text[0] == '﻿') i = 1; // BOM

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

                switch (c)
                {
                    case '"':
                        inQuotes = true;
                        break;
                    case ',':
                        cells.Add(field.ToString());
                        field.Clear();
                        break;
                    case '\r':
                        break;
                    case '\n':
                        cells.Add(field.ToString());
                        field.Clear();
                        records.Add(new Row(cells.ToArray(), recordLine));
                        cells.Clear();
                        line++;
                        recordLine = line;
                        break;
                    default:
                        field.Append(c);
                        break;
                }
            }

            if (inQuotes)
            {
                errors.Add(new RulesError(RulesStatus.ParseError, name, recordLine, "unterminated quoted field"));
            }
            if (field.Length > 0 || cells.Count > 0)
            {
                cells.Add(field.ToString());
                records.Add(new Row(cells.ToArray(), recordLine));
            }
            return records;
        }
    }
}
