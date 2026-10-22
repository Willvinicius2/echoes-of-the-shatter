using System.Collections.Generic;
using System.Text;
using Godot;

namespace EchoesOfTheShatter.Arqueiro;

/// <summary>Leitor mínimo de CSV (vírgula, aspas duplas, linhas # ignoradas). A primeira linha é o cabeçalho e é devolvida à parte.</summary>
public static class CsvLeitor
{
    public static List<string[]> Ler(string caminho, out string[] cabecalho)
    {
        cabecalho = System.Array.Empty<string>();
        var linhas = new List<string[]>();
        using var f = Godot.FileAccess.Open(caminho, Godot.FileAccess.ModeFlags.Read);
        if (f == null)
        {
            GD.PushError($"CSV não encontrado: {caminho}");
            return linhas;
        }
        bool primeira = true;
        while (!f.EofReached())
        {
            string l = f.GetLine().TrimEnd('\r');
            if (l.Length == 0 || l[0] == '#') continue;
            var campos = Dividir(l);
            if (primeira) { cabecalho = campos; primeira = false; }
            else linhas.Add(campos);
        }
        return linhas;
    }

    static string[] Dividir(string l)
    {
        var r = new List<string>();
        var sb = new StringBuilder();
        bool aspas = false;
        foreach (char c in l)
        {
            if (c == '"') aspas = !aspas;
            else if (c == ',' && !aspas) { r.Add(sb.ToString()); sb.Clear(); }
            else sb.Append(c);
        }
        r.Add(sb.ToString());
        return r.ToArray();
    }
}
