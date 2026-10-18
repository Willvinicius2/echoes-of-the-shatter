using System;
using System.Collections.Generic;
using System.Text;

namespace Echoes.Interop.Native
{
    /// <summary>
    /// Texto UTF-8 e o padrao de duas chamadas da API C (docs/tecnico/04_arquitetura.md, secao 9.2): a primeira
    /// chamada devolve <c>BUFFER_TOO_SMALL</c> com <c>needed</c>, o C# aloca e repete. Nada muda no
    /// lado nativo entre as duas chamadas.
    /// </summary>
    internal static unsafe class NativeBuffers
    {
        public const int BufferTooSmall = 2;

        public delegate int BufferCall(byte* output, nuint cap, nuint* needed);

        /// <summary>
        /// Chama <paramref name="call"/> com um buffer de <paramref name="initialCapacity"/> bytes e repete com o
        /// tamanho pedido. Devolve o status final; em OK, <paramref name="length"/> tem os bytes validos.
        /// </summary>
        public static int ReadBytes(BufferCall call, out byte[] data, out int length, int initialCapacity = 1024)
        {
            var buffer = new byte[Math.Max(1, initialCapacity)];
            for (var attempt = 0; attempt < 3; attempt++)
            {
                nuint needed = 0;
                int status;
                fixed (byte* p = buffer) status = call(p, (nuint)buffer.Length, &needed);
                if (status == BufferTooSmall)
                {
                    buffer = new byte[Math.Max(1, checked((int)needed))];
                    continue;
                }
                data = buffer;
                length = status == 0 ? checked((int)needed) : 0;
                return status;
            }
            data = buffer;
            length = 0;
            return (int)RulesStatus.Internal; // o tamanho pedido mudou entre as chamadas: nao deveria acontecer
        }

        public static int ReadString(BufferCall call, out string text, int initialCapacity = 1024)
        {
            var status = ReadBytes(call, out var data, out var length, initialCapacity);
            text = status == 0 ? Encoding.UTF8.GetString(data, 0, length) : string.Empty;
            return status;
        }

        /// <summary>Copia <paramref name="text"/> como UTF-8 sem NUL (comprimento explicito).</summary>
        public static byte[] Utf8(string text)
        {
            return string.IsNullOrEmpty(text) ? Array.Empty<byte>() : Encoding.UTF8.GetBytes(text);
        }

        /// <summary>Mensagem do <c>shatter_error</c> (UTF-8 terminado em NUL).</summary>
        public static string ErrorMessage(ref ShatterError err)
        {
            fixed (ShatterError* e = &err)
            {
                var n = 0;
                while (n < 256 && e->message[n] != 0) n++;
                return Encoding.UTF8.GetString(e->message, n);
            }
        }
    }

    /// <summary>Leitor minimo do JSON de <c>shatter_db_errors_json</c>: lista de objetos planos table/line/message.</summary>
    internal static class NativeErrorJson
    {
        public static void Parse(string json, RulesStatus status, List<RulesError> errors)
        {
            if (string.IsNullOrEmpty(json)) return;
            var i = 0;
            while (i < json.Length)
            {
                var open = json.IndexOf('{', i);
                if (open < 0) break;
                string table = string.Empty;
                string message = string.Empty;
                var line = 0;
                i = open + 1;
                while (i < json.Length && json[i] != '}')
                {
                    if (json[i] != '"') { i++; continue; }
                    var key = ReadString(json, ref i);
                    while (i < json.Length && (json[i] == ':' || char.IsWhiteSpace(json[i]))) i++;
                    if (i < json.Length && json[i] == '"')
                    {
                        var value = ReadString(json, ref i);
                        if (key == "table") table = value;
                        else if (key == "message") message = value;
                    }
                    else
                    {
                        var start = i;
                        while (i < json.Length && json[i] != ',' && json[i] != '}') i++;
                        if (key == "line") int.TryParse(json.Substring(start, i - start).Trim(), out line);
                    }
                }
                errors.Add(new RulesError(status, table, line, message));
                i++;
            }
        }

        // Le uma string JSON a partir da aspa de abertura; deixa o indice depois da aspa de fechamento.
        static string ReadString(string json, ref int i)
        {
            var sb = new StringBuilder();
            i++;
            while (i < json.Length && json[i] != '"')
            {
                var c = json[i++];
                if (c != '\\' || i >= json.Length) { sb.Append(c); continue; }
                var esc = json[i++];
                switch (esc)
                {
                    case 'n': sb.Append('\n'); break;
                    case 't': sb.Append('\t'); break;
                    case 'r': sb.Append('\r'); break;
                    case 'b': sb.Append('\b'); break;
                    case 'f': sb.Append('\f'); break;
                    case 'u':
                        if (i + 4 <= json.Length && ushort.TryParse(json.Substring(i, 4), System.Globalization.NumberStyles.HexNumber, null, out var code))
                        {
                            sb.Append((char)code);
                            i += 4;
                        }
                        break;
                    default: sb.Append(esc); break;
                }
            }
            i++;
            return sb.ToString();
        }
    }
}
