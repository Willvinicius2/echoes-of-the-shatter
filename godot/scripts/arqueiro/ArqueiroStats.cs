using System.Collections.Generic;
using System.Globalization;
using Godot;

namespace EchoesOfTheShatter.Arqueiro;

/// <summary>Todos os números de balanceamento e feel do arqueiro vêm de res://data/arqueiro/arqueiro.csv.</summary>
public static class ArqueiroStats
{
    const string Caminho = "res://data/arqueiro/arqueiro.csv";
    static Dictionary<string, float> _v;

    public static void Recarregar() => _v = null;

    public static float F(string chave)
    {
        _v ??= Carregar();
        if (_v.TryGetValue(chave, out var x)) return x;
        GD.PushError($"ArqueiroStats: chave ausente '{chave}' em {Caminho}");
        return 0f;
    }

    static Dictionary<string, float> Carregar()
    {
        var d = new Dictionary<string, float>();
        foreach (var c in CsvLeitor.Ler(Caminho, out _))
        {
            if (c.Length >= 2 && float.TryParse(c[1], NumberStyles.Float, CultureInfo.InvariantCulture, out var v)) d[c[0]] = v;
        }
        return d;
    }
}

/// <summary>Textos visíveis por chave (res://data/loc/arqueiro.csv).</summary>
public static class Loc
{
    static Dictionary<string, string> _t;

    public static string T(string chave)
    {
        if (_t == null)
        {
            _t = new Dictionary<string, string>();
            foreach (var c in CsvLeitor.Ler("res://data/loc/arqueiro.csv", out _))
                if (c.Length >= 2) _t[c[0]] = c[1];
        }
        return _t.TryGetValue(chave, out var s) ? s : chave;
    }
}

/// <summary>Camadas de colisão: 1 mundo, 2 jogador, 3 alvos (hurtable).</summary>
public static class Camadas
{
    public const uint Mundo = 1;
    public const uint Jogador = 2;
    public const uint Alvo = 4;
    public const string GrupoAlvo = "hurtable";
    public const string GrupoJogador = "arqueiro";
    public const string GrupoCamera = "camera_jogo";
}
