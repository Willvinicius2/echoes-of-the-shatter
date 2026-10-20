using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace Echoes.Interop
{
    /// <summary>
    /// Leitor minimo de JSON para os resultados do core (relatorio de expedicao, personagem): objetos viram Dictionary&lt;string, object&gt;,
    /// arrays List&lt;object&gt;, numeros double, alem de string, bool e null. So leitura: o C# nunca monta o save, so le o que o core devolve.
    /// </summary>
    public static class MiniJson
    {
        public static object Parse(string json)
        {
            var i = 0;
            var value = ReadValue(json, ref i);
            SkipSpace(json, ref i);
            if (i != json.Length) throw new FormatException("JSON com texto sobrando na posicao " + i);
            return value;
        }

        public static Dictionary<string, object> AsObject(object value) => value as Dictionary<string, object> ?? new Dictionary<string, object>();

        public static List<object> AsArray(object value) => value as List<object> ?? new List<object>();

        public static double Num(Dictionary<string, object> o, string key, double fallback = 0.0) =>
            o != null && o.TryGetValue(key, out var v) && v is double d ? d : fallback;

        public static int Int(Dictionary<string, object> o, string key, int fallback = 0) => (int)Math.Round(Num(o, key, fallback));

        public static string Str(Dictionary<string, object> o, string key, string fallback = "") =>
            o != null && o.TryGetValue(key, out var v) && v is string s ? s : fallback;

        public static bool Bool(Dictionary<string, object> o, string key, bool fallback = false) =>
            o != null && o.TryGetValue(key, out var v) && v is bool b ? b : fallback;

        /// <summary>Texto JSON entre aspas, com escapes (para montar parametros que o core le).</summary>
        public static string Quote(string text)
        {
            var sb = new StringBuilder(text.Length + 2);
            sb.Append('"');
            foreach (var c in text)
            {
                switch (c)
                {
                    case '"': sb.Append("\\\""); break;
                    case '\\': sb.Append("\\\\"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    default:
                        if (c < 0x20) sb.Append("\\u").Append(((int)c).ToString("x4", CultureInfo.InvariantCulture));
                        else sb.Append(c);
                        break;
                }
            }
            sb.Append('"');
            return sb.ToString();
        }

        /// <summary>Como <see cref="Quote"/>, mas escapa tudo que nao e ASCII (\uXXXX).</summary>
        public static string QuoteAscii(string text)
        {
            var sb = new StringBuilder(text.Length + 2);
            foreach (var c in Quote(text))
            {
                if (c > 0x7e) sb.Append("\\u").Append(((int)c).ToString("x4", CultureInfo.InvariantCulture));
                else sb.Append(c);
            }
            return sb.ToString();
        }

        static void SkipSpace(string s, ref int i)
        {
            while (i < s.Length && char.IsWhiteSpace(s[i])) i++;
        }

        static object ReadValue(string s, ref int i)
        {
            SkipSpace(s, ref i);
            if (i >= s.Length) throw new FormatException("JSON incompleto");
            var c = s[i];
            if (c == '{') return ReadObject(s, ref i);
            if (c == '[') return ReadArray(s, ref i);
            if (c == '"') return ReadString(s, ref i);
            if (Match(s, i, "true")) { i += 4; return true; }
            if (Match(s, i, "false")) { i += 5; return false; }
            if (Match(s, i, "null")) { i += 4; return null; }
            var start = i;
            while (i < s.Length && "+-0123456789.eE".IndexOf(s[i]) >= 0) i++;
            if (start == i) throw new FormatException("JSON invalido na posicao " + i);
            return double.Parse(s.Substring(start, i - start), CultureInfo.InvariantCulture);
        }

        static bool Match(string s, int i, string word) => string.CompareOrdinal(s, i, word, 0, word.Length) == 0;

        static Dictionary<string, object> ReadObject(string s, ref int i)
        {
            var result = new Dictionary<string, object>();
            i++;
            SkipSpace(s, ref i);
            if (s[i] == '}') { i++; return result; }
            while (true)
            {
                SkipSpace(s, ref i);
                var key = ReadString(s, ref i);
                SkipSpace(s, ref i);
                if (s[i] != ':') throw new FormatException("esperava ':' na posicao " + i);
                i++;
                result[key] = ReadValue(s, ref i);
                SkipSpace(s, ref i);
                if (s[i] == ',') { i++; continue; }
                if (s[i] == '}') { i++; return result; }
                throw new FormatException("esperava ',' ou '}' na posicao " + i);
            }
        }

        static List<object> ReadArray(string s, ref int i)
        {
            var result = new List<object>();
            i++;
            SkipSpace(s, ref i);
            if (s[i] == ']') { i++; return result; }
            while (true)
            {
                result.Add(ReadValue(s, ref i));
                SkipSpace(s, ref i);
                if (s[i] == ',') { i++; continue; }
                if (s[i] == ']') { i++; return result; }
                throw new FormatException("esperava ',' ou ']' na posicao " + i);
            }
        }

        static string ReadString(string s, ref int i)
        {
            if (s[i] != '"') throw new FormatException("esperava '\"' na posicao " + i);
            i++;
            var sb = new StringBuilder();
            while (i < s.Length && s[i] != '"')
            {
                var c = s[i++];
                if (c != '\\') { sb.Append(c); continue; }
                var esc = s[i++];
                switch (esc)
                {
                    case 'n': sb.Append('\n'); break;
                    case 't': sb.Append('\t'); break;
                    case 'r': sb.Append('\r'); break;
                    case 'b': sb.Append('\b'); break;
                    case 'f': sb.Append('\f'); break;
                    case 'u':
                        sb.Append((char)int.Parse(s.Substring(i, 4), NumberStyles.HexNumber, CultureInfo.InvariantCulture));
                        i += 4;
                        break;
                    default: sb.Append(esc); break;
                }
            }
            i++;
            return sb.ToString();
        }
    }
}
