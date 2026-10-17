using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;

namespace Echoes.Core
{
    /// <summary>
    /// Textos visíveis ao jogador por chave (docs/04_arquitetura.md, seção 7; RF-61, RF-62).
    /// Fallback: cultura atual → en → a própria chave (com aviso uma vez por chave).
    /// Nenhum texto visível mora no C# nem no UXML: só chaves.
    /// </summary>
    public sealed class LocalizationService
    {
        readonly LocalizationTable table = new LocalizationTable();
        readonly HashSet<string> warnedKeys = new HashSet<string>(StringComparer.Ordinal);
        readonly Action<string> warn;
        CultureInfo numberCulture = CultureInfo.InvariantCulture;

        public LocalizationService(Action<string> warningSink)
        {
            warn = warningSink;
            Culture = LocalizationTable.FallbackCulture;
        }

        /// <summary>Coluna de cultura ativa ("pt_BR", "en", "es").</summary>
        public string Culture { get; private set; }

        public LocalizationTable Table => table;

        /// <summary>Disparado depois de trocar o idioma: telas reaplicam os textos.</summary>
        public event Action CultureChanged;

        /// <summary>Lê todos os *.csv da pasta Loc. Devolve quantos arquivos leu.</summary>
        public int LoadDirectory(string locDirectory)
        {
            if (string.IsNullOrEmpty(locDirectory) || !Directory.Exists(locDirectory))
            {
                warn?.Invoke($"Localization directory not found: {locDirectory}");
                return 0;
            }
            var files = Directory.GetFiles(locDirectory, "*.csv");
            Array.Sort(files, StringComparer.Ordinal);
            for (var i = 0; i < files.Length; i++) table.AddCsv(File.ReadAllText(files[i], Encoding.UTF8));
            for (var i = 0; i < table.DuplicateKeys.Count; i++) warn?.Invoke($"Duplicate localization key: {table.DuplicateKeys[i]}");
            return files.Length;
        }

        public void SetCulture(string cultureColumn)
        {
            var column = string.IsNullOrEmpty(cultureColumn) ? LocalizationTable.FallbackCulture : cultureColumn;
            if (!table.HasCulture(column))
            {
                warn?.Invoke($"Culture '{column}' has no texts; using {LocalizationTable.FallbackCulture}");
                column = LocalizationTable.FallbackCulture;
            }
            Culture = column;
            numberCulture = CreateNumberCulture(column);
            CultureChanged?.Invoke();
        }

        public string Get(string key)
        {
            if (table.TryGet(Culture, key, out var value)) return value;
            if (key != null && warnedKeys.Add(key)) warn?.Invoke($"Missing localization key: {key}");
            return key ?? string.Empty;
        }

        /// <summary>Nota de contexto da chave (coluna context do CSV).</summary>
        public string ContextOf(string key) => table.ContextOf(key);

        /// <summary>Texto da chave sem fallback para a própria chave (para avisos opcionais).</summary>
        public bool TryGet(string key, out string value)
        {
            return table.TryGet(Culture, key, out value);
        }

        /// <summary>Substitui <c>{nome}</c> no texto da chave. Nunca concatena pedaços de frase.</summary>
        public string Format(string key, string name, string value)
        {
            var text = Get(key);
            return text.Replace("{" + name + "}", value);
        }

        /// <summary>Inteiro com separador de milhar da cultura ("1.234" em pt-BR).</summary>
        public string FormatInteger(long value)
        {
            return value.ToString("N0", numberCulture);
        }

        /// <summary>Número com casas decimais na cultura ("0,8" em pt-BR).</summary>
        public string FormatDecimal(double value, int decimals)
        {
            return value.ToString("F" + decimals.ToString(CultureInfo.InvariantCulture), numberCulture);
        }

        static CultureInfo CreateNumberCulture(string column)
        {
            try
            {
                return CultureInfo.GetCultureInfo(column.Replace('_', '-'));
            }
            catch (CultureNotFoundException)
            {
                return CultureInfo.InvariantCulture;
            }
        }
    }
}
