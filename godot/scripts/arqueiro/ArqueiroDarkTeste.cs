using System.Collections.Generic;
using Godot;

namespace EchoesOfTheShatter.Arqueiro;

/// <summary>
/// Cena de teste do Arqueiro Dark: piso neutro, camera 3/4 do jogo (valores de arqueiro.csv), luz da Cripta.
/// 1..6 liga/desliga cada slot, V alterna variante, C alterna a camera (3/4 do jogo, 3/4 perto, frente, costas, lado).
/// </summary>
public partial class ArqueiroDarkTeste : Node3D
{
    public static readonly string[] Slots = { "corpo", "torso", "bracadeiras", "botas", "arco", "aljava" };
    // nome, yaw (graus), pitch (graus), distancia, fov, altura do alvo
    static readonly (string nome, float yaw, float pitch, float dist, float fov, float alvoY)[] Vistas =
    {
        ("3/4 do jogo", 0, 0, 0, 0, 0.9f), // valores vem de arqueiro.csv
        ("3/4 perto", 45, -20, 4.2f, 30, 0.95f),
        ("frente", 0, -8, 4.2f, 30, 0.95f),
        ("costas", 180, -8, 4.2f, 30, 0.95f),
        ("lado", 90, -8, 4.2f, 30, 0.95f),
    };

    public ArqueiroDarkModular Arqueiro { get; private set; }
    public Camera3D Camera { get; private set; }
    public int Vista { get; private set; }
    public int Variante { get; private set; }
    readonly List<string> _variantes = new() { "" };
    Label _legenda;

    public override void _Ready()
    {
        MontarAmbiente();
        MontarPiso();
        Arqueiro = new ArqueiroDarkModular { Name = "ArqueiroDark" };
        AddChild(Arqueiro);
        foreach (var c in CsvLeitor.Ler("res://data/arqueiro_dark/equipamento.csv", out _))
            if (c[0] != "starter" && !_variantes.Contains(c[0])) _variantes.Add(c[0]);
        Camera = new Camera3D { Far = 500f, Current = true };
        AddChild(Camera);
        var ui = new CanvasLayer();
        _legenda = new Label { Position = new Vector2(16, 12) };
        _legenda.AddThemeFontSizeOverride("font_size", 18);
        _legenda.AddThemeColorOverride("font_color", new Color(0.9f, 0.92f, 1f));
        _legenda.AddThemeColorOverride("font_outline_color", Colors.Black);
        _legenda.AddThemeConstantOverride("outline_size", 6);
        ui.AddChild(_legenda);
        AddChild(ui);
        AplicarVista(0);
        AplicarVariante(0);
        Tocar("Idle");
        if (Arqueiro.Animacoes != null) Arqueiro.Animacoes.AnimationFinished += AoTerminarClipe;
        AtualizarLegenda();
    }

    void MontarAmbiente()
    {
        // mesma luz/ambiente da Cripta (scenes/cripta/Cripta.tscn): luar frio + ambiente azul + braseiros quentes
        var env = new Godot.Environment
        {
            BackgroundMode = Godot.Environment.BGMode.Color,
            BackgroundColor = new Color(0.015f, 0.02f, 0.04f),
            AmbientLightSource = Godot.Environment.AmbientSource.Color,
            AmbientLightColor = new Color(0.2f, 0.25f, 0.38f),
            AmbientLightEnergy = 0.55f,
            TonemapMode = Godot.Environment.ToneMapper.Aces,
            TonemapExposure = 1.15f,
            SsaoEnabled = true,
            SsaoRadius = 1.5f,
            GlowEnabled = true,
            GlowIntensity = 0.15f,
            GlowBloom = 0.02f,
            GlowHdrThreshold = 1.8f,
            FogEnabled = true,
            FogLightColor = new Color(0.09f, 0.13f, 0.24f),
            FogDensity = 0.003f,
        };
        AddChild(new WorldEnvironment { Environment = env });
        var luar = new DirectionalLight3D
        {
            Transform = new Transform3D(new Basis(
                new Vector3(0.81915206f, 0, 0.57357645f), new Vector3(0.50643796f, 0.4694716f, -0.72326833f), new Vector3(-0.26927787f, 0.88294756f, 0.38456863f)), Vector3.Zero),
            LightColor = new Color(0.55f, 0.65f, 1f),
            LightEnergy = 0.5f,
            ShadowEnabled = true,
            DirectionalShadowMaxDistance = 90f,
        };
        AddChild(luar);
        AddChild(new OmniLight3D { Position = new Vector3(-2.2f, 1.6f, 2.2f), LightColor = new Color(1f, 0.68f, 0.36f), LightEnergy = 1.2f, OmniRange = 7f, ShadowEnabled = true });
        AddChild(new OmniLight3D { Position = new Vector3(2.5f, 1.2f, -2.5f), LightColor = new Color(1f, 0.45f, 0.12f), LightEnergy = 0.6f, OmniRange = 6f });
    }

    void MontarPiso()
    {
        var mat = new StandardMaterial3D { AlbedoColor = new Color(0.32f, 0.33f, 0.36f), Roughness = 0.9f };
        AddChild(new MeshInstance3D { Mesh = new PlaneMesh { Size = new Vector2(40, 40), Material = mat }, Name = "Piso" });
    }

    void AplicarVista(int i)
    {
        Vista = (i + Vistas.Length) % Vistas.Length;
        var v = Vistas[Vista];
        float yaw = v.yaw, pitch = v.pitch, dist = v.dist, fov = v.fov;
        if (Vista == 0)
        {
            yaw = ArqueiroStats.F("cam_yaw"); pitch = ArqueiroStats.F("cam_pitch");
            dist = ArqueiroStats.F("cam_dist"); fov = ArqueiroStats.F("cam_fov");
        }
        var rot = Basis.FromEuler(new Vector3(Mathf.DegToRad(pitch), Mathf.DegToRad(yaw), 0));
        var alvo = new Vector3(0, v.alvoY, 0);
        Camera.Fov = fov;
        Camera.Basis = rot;
        Camera.Position = alvo + rot.Z * dist;
    }

    // tecla -> clipe (nome curto do AnimationPlayer: AN_Arqueiro_<nome>). Loop: Idle, Walk, Run, AimIdle; os demais voltam ao Idle.
    static readonly (Key tecla, string clipe, string rotulo)[] Clipes =
    {
        (Key.Z, "Idle", "idle"), (Key.X, "Walk", "andar"), (Key.N, "Run", "correr"), (Key.M, "AimIdle", "mirar"),
        (Key.B, "Draw", "disparar"), (Key.E, "Dodge", "esquiva"),
    };
    string _clipe = "";
    bool _disparando;

    public string ClipeAtual => _clipe;

    public void Tocar(string curto, double mistura = 0.12)
    {
        var ap = Arqueiro?.Animacoes;
        if (ap == null) return;
        string nome = "AN_Arqueiro_" + curto;
        if (!ap.HasAnimation(nome)) return;
        _disparando = curto == "Draw";
        _clipe = curto;
        ap.SpeedScale = 1f;
        ap.Play(nome, mistura);
        if (_legenda != null) AtualizarLegenda();
    }

    // captura: toca o clipe, vai para o tempo t (s) e congela
    public void Congelar(string curto, float t)
    {
        var ap = Arqueiro.Animacoes;
        Tocar(curto, 0);
        ap.Seek(t, true);
        ap.SpeedScale = 0f; // velocidade 0 em vez de Pause: os BoneAttachment3D continuam seguindo o osso
    }

    void AoTerminarClipe(StringName nome)
    {
        if (nome == "AN_Arqueiro_Draw" && _disparando) { _disparando = false; _clipe = "Release"; Arqueiro.Animacoes.Play("AN_Arqueiro_Release", 0.05); AtualizarLegenda(); }
        else if (nome == "AN_Arqueiro_Release" || nome == "AN_Arqueiro_Dodge") Tocar("Idle");
    }

    public void DefinirVista(int i) { AplicarVista(i); AtualizarLegenda(); }

    void AplicarVariante(int i)
    {
        Variante = (i + _variantes.Count) % _variantes.Count;
        var ids = new List<string> { "starter" };
        if (_variantes[Variante] != "") ids.Add(_variantes[Variante]);
        Arqueiro.EquiparLimpo(ids);
    }

    public void DefinirVariante(int i) { AplicarVariante(i); AtualizarLegenda(); }

    public void DefinirSlot(string slot, bool visivel)
    {
        if (Arqueiro.Visivel(slot) != visivel) Arqueiro.Alternar(slot);
        AtualizarLegenda();
    }

    void AtualizarLegenda()
    {
        var sb = new System.Text.StringBuilder("ARQUEIRO DARK - teste de modulos\n");
        for (int i = 0; i < Slots.Length; i++)
        {
            string estado = !Arqueiro.Existe(Slots[i]) ? "(arquivo ausente)" : Arqueiro.Visivel(Slots[i]) ? "ligado" : "oculto";
            sb.Append($"[{i + 1}] {Slots[i]}: {estado}\n");
        }
        string var = _variantes[Variante] == "" ? "starter" : _variantes[Variante];
        sb.Append($"[V] variante: {var}   [C] camera: {Vistas[Vista].nome}   [Esc] sair\n");
        sb.Append("Animacao: ");
        foreach (var c in Clipes) sb.Append($"[{c.tecla}] {c.rotulo}  ");
        sb.Append($"(atual: {_clipe})");
        _legenda.Text = sb.ToString();
    }

    public override void _UnhandledKeyInput(InputEvent e)
    {
        if (e is not InputEventKey { Pressed: true, Echo: false } k) return;
        int n = (int)k.Keycode - (int)Key.Key1;
        if (n >= 0 && n < Slots.Length) { Arqueiro.Alternar(Slots[n]); AtualizarLegenda(); }
        else if (System.Array.Find(Clipes, c => c.tecla == k.Keycode) is { clipe: not null } cl) Tocar(cl.clipe);
        else if (k.Keycode == Key.V) DefinirVariante(Variante + 1);
        else if (k.Keycode == Key.C) DefinirVista(Vista + 1);
        else if (k.Keycode == Key.Escape) GetTree().Quit();
    }
}
