using Godot;

namespace EchoesOfTheShatter.Arqueiro;

/// <summary>HUD mínimo: estado, vida, carga do arco, recarga da esquiva e dica de controles (tudo por chave de loc).</summary>
public partial class ArqueiroHud : CanvasLayer
{
    ArqueiroController _h;
    Label _estado, _camera;
    ProgressBar _vida, _carga, _esq;
    public string ChaveCamera { get; set; } = "hud.camera.arqueiro";

    public override void _Ready()
    {
        var caixa = new VBoxContainer { Position = new Vector2(16, 12), CustomMinimumSize = new Vector2(260, 0) };
        AddChild(caixa);
        _estado = new Label(); caixa.AddChild(_estado);
        _vida = Barra(caixa, "hud.vida", new Color(0.8f, 0.2f, 0.2f));
        _carga = Barra(caixa, "hud.carga", new Color(0.95f, 0.75f, 0.3f));
        _esq = Barra(caixa, "hud.esquiva", new Color(0.4f, 0.7f, 1f));
        _camera = new Label(); caixa.AddChild(_camera);
        var dica = new Label { Text = Loc.T("hud.dica"), AnchorTop = 1, AnchorBottom = 1, Position = new Vector2(16, -34) };
        dica.SetAnchorsPreset(Control.LayoutPreset.BottomLeft);
        dica.Position = new Vector2(16, -36);
        AddChild(dica);
    }

    ProgressBar Barra(Container pai, string chave, Color cor)
    {
        var l = new Label { Text = Loc.T(chave) }; pai.AddChild(l);
        var b = new ProgressBar { MaxValue = 1, ShowPercentage = false, CustomMinimumSize = new Vector2(240, 14) };
        b.AddThemeStyleboxOverride("fill", new StyleBoxFlat { BgColor = cor });
        pai.AddChild(b);
        return b;
    }

    public override void _Process(double delta)
    {
        _h ??= GetTree().GetFirstNodeInGroup(Camadas.GrupoJogador) as ArqueiroController;
        if (_h == null) return;
        _estado.Text = Loc.T(_h.ChaveEstado());
        _vida.Value = _h.Hp / _h.HpMax;
        _carga.Value = _h.Carga01;
        _esq.Value = 1f - _h.RecargaEsquiva01;
        _camera.Text = Loc.T(ChaveCamera);
    }
}
