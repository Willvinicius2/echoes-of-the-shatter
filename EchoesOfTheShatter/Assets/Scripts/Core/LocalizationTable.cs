using System;
using System.Collections.Generic;

namespace Echoes.Core
{
    /// <summary>
    /// Textos por chave e por cultura, lidos de <c>Loc/*.csv</c> (colunas <c>key, pt_BR, en, es, context, gender</c>).
    /// Classe pura (sem UnityEngine) para ser testável em EditMode.
    /// </summary>
    public sealed class LocalizationTable
    {
        public const string KeyColumn = "key";
        public const string FallbackCulture = "en";

        readonly Dictionary<string, Dictionary<string, string>> byCulture =
            new Dictionary<string, Dictionary<string, string>>(StringComparer.Ordinal);
        readonly List<string> duplicateKeys = new List<string>();

        public IReadOnlyList<string> DuplicateKeys => duplicateKeys;

        public int Count
        {
            get
            {
                var keys = new HashSet<string>(StringComparer.Ordinal);
                foreach (var culture in byCulture.Values)
                {
                    foreach (var key in culture.Keys) keys.Add(key);
                }
                return keys.Count;
            }
        }

        /// <summary>Acrescenta um arquivo de localização. Colunas de cultura são as que não são key/context/gender.</summary>
        public void AddCsv(string csvText)
        {
            var records = CsvReader.Parse(csvText);
            if (records.Count == 0) return;
            var header = records[0].Fields;
            var keyIndex = Array.IndexOf(header, KeyColumn);
            if (keyIndex < 0) return;

            for (var r = 1; r < records.Count; r++)
            {
                var fields = records[r].Fields;
                if (keyIndex >= fields.Length) continue;
                var key = fields[keyIndex];
                if (key.Length == 0) continue;
                for (var c = 0; c < header.Length && c < fields.Length; c++)
                {
                    var column = header[c];
                    if (c == keyIndex || column == "context" || column == "gender") continue;
                    var value = fields[c];
                    if (value.Length == 0) continue;
                    if (!byCulture.TryGetValue(column, out var table))
                    {
                        table = new Dictionary<string, string>(StringComparer.Ordinal);
                        byCulture.Add(column, table);
                    }
                    if (table.ContainsKey(key)) duplicateKeys.Add(key);
                    table[key] = value;
                }
            }
        }

        public bool HasCulture(string culture) => culture != null && byCulture.ContainsKey(culture);

        /// <summary>Texto na cultura pedida; senão em <see cref="FallbackCulture"/>; senão false.</summary>
        public bool TryGet(string culture, string key, out string value)
        {
            value = null;
            if (string.IsNullOrEmpty(key)) return false;
            if (culture != null && byCulture.TryGetValue(culture, out var table) && table.TryGetValue(key, out value)) return true;
            if (byCulture.TryGetValue(FallbackCulture, out var fallback) && fallback.TryGetValue(key, out value)) return true;
            return false;
        }

        /// <summary>Mapeia um código de idioma do sistema ("pt", "pt-BR", "en-US") para a coluna do CSV.</summary>
        public static string CultureColumnFor(string languageCode)
        {
            if (string.IsNullOrEmpty(languageCode)) return FallbackCulture;
            if (languageCode.StartsWith("pt", StringComparison.OrdinalIgnoreCase)) return "pt_BR";
            if (languageCode.StartsWith("es", StringComparison.OrdinalIgnoreCase)) return "es";
            return FallbackCulture;
        }
    }
}
