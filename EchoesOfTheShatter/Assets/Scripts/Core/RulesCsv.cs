using System.Collections.Generic;
using System.Globalization;
using System.IO;

namespace Echoes.Core
{
    /// <summary>
    /// Leitura de numeros do <c>rules.csv</c> (a fonte da verdade dos valores de regra) para a UI quando o core nao devolve o numero pela API
    /// (ex.: <c>polish_max_steps</c> para desenhar as bolinhas da Lapidar). So le; nenhuma regra e calculada aqui. Ausente: o padrao dado.
    /// </summary>
    public static class RulesCsv
    {
        static Dictionary<string, double> cache;
        static string cachedDirectory;

        public static double Number(string key, double fallback, string dataDirectory = null)
        {
            var dir = dataDirectory ?? ContentPaths.ResolveDataDirectory(string.Empty);
            if (cache == null || cachedDirectory != dir)
            {
                cache = new Dictionary<string, double>();
                cachedDirectory = dir;
                var path = Path.Combine(dir, "rules.csv");
                if (File.Exists(path))
                {
                    var records = CsvReader.Parse(File.ReadAllText(path));
                    for (var i = 1; i < records.Count; i++)
                    {
                        var f = records[i].Fields;
                        if (f.Length >= 2 && double.TryParse(f[1], NumberStyles.Float, CultureInfo.InvariantCulture, out var v)) cache[f[0]] = v;
                    }
                }
            }
            return cache.TryGetValue(key, out var value) ? value : fallback;
        }
    }
}
