using Godot;

namespace EchoesOfTheShatter.Arqueiro;

/// <summary>Teste automático (rodar com: -- --arqueiro-teste). Injeta ações, tira capturas e imprime TESTE: linhas.</summary>
public partial class AutoTeste : Node
{
    ArqueiroController _h;
    Dummy _alvo;
    string _dir;

    async System.Threading.Tasks.Task Espera(float s)
        => await ToSignal(GetTree().CreateTimer(s, true, false, true), SceneTreeTimer.SignalName.Timeout);

    void Foto(string nome)
    {
        GetViewport().GetTexture().GetImage().SavePng(_dir + nome + ".png");
        GD.Print("TESTE: captura " + nome);
    }

    public override async void _Ready()
    {
        _dir = ProjectSettings.GlobalizePath("res://capturas_arqueiro/");
        DirAccess.MakeDirRecursiveAbsolute(_dir);
        _h = GetParent().GetNode<ArqueiroController>("Arqueiro");
        _alvo = GetParent().GetNode<Dummy>("Alvos/Dummy1");
        await Espera(1.5f);
        for (int i = 0; i < 300 && !_h.IsOnFloor(); i++) await ToSignal(GetTree(), SceneTree.SignalName.PhysicsFrame);
        GD.Print($"TESTE: fps={Engine.GetFramesPerSecond()} corpo_real={_h.Modular.CorpoReal} clipe={_h.ClipeAtual} no_chao={_h.IsOnFloor()} pos={_h.GlobalPosition}");
        Foto("01_parado");

        var p0 = _h.GlobalPosition;
        Input.ActionPress("move_up");
        await Espera(1.2f);
        Foto("02_andando");
        GD.Print($"TESTE: andou {(_h.GlobalPosition - p0).Length():0.00} m clipe={_h.ClipeAtual} vel={_h.Velocity.Length():0.00}");
        Input.ActionRelease("move_up");
        await Espera(0.5f);

        p0 = _h.GlobalPosition;
        Input.ActionPress("move_right");
        Input.ActionPress("dodge");
        await Espera(0.05f);
        Input.ActionRelease("dodge");
        await Espera(0.12f);
        Foto("03_esquiva");
        GD.Print($"TESTE: esquiva estado={_h.EstadoAtual} iframe={_h.Invulneravel}");
        Input.ActionRelease("move_right");
        await Espera(0.6f);
        GD.Print($"TESTE: esquiva deslocou {(_h.GlobalPosition - p0).Length():0.00} m");
        Input.ActionPress("dodge");
        await Espera(0.05f);
        Input.ActionRelease("dodge");
        await Espera(0.1f);
        GD.Print($"TESTE: esquiva em recarga bloqueada={_h.EstadoAtual != Estado.Esquiva}");
        await Espera(1.0f);

        // mira no dummy 1 e atira com carga total
        _h.ForcarMira(_alvo.GlobalPosition + Vector3.Up * 0f);
        await Espera(0.3f);
        float hp0 = _alvo.Hp;
        Input.ActionPress("shoot");
        await Espera(0.5f);
        Foto("04_carregando");
        await Espera(0.6f);
        Input.ActionRelease("shoot");
        await Espera(0.12f);
        Foto("05_disparo");
        await Espera(1.5f);
        GD.Print($"TESTE: tiro disparos={_h.Disparos} dummy hp {hp0} -> {_alvo.Hp}");

        // tiro contra parede: mira na direção sul (fora da sala)
        _h.ForcarMira(_h.GlobalPosition + new Vector3(0, 0, 30));
        await Espera(0.3f);
        Input.ActionPress("shoot");
        await Espera(0.3f);
        Input.ActionRelease("shoot");
        await Espera(1.0f);
        Foto("06_flecha_parede");

        _h.ReceberDano(20f, _h.GlobalPosition + Vector3.Back);
        await Espera(0.15f);
        GD.Print($"TESTE: dano estado={_h.EstadoAtual} hp={_h.Hp}");
        Foto("07_dano");
        await Espera(1.0f);
        _h.ReceberDano(1000f, _h.GlobalPosition);
        await Espera(0.6f);
        GD.Print($"TESTE: morte estado={_h.EstadoAtual} hp={_h.Hp} clipe={_h.ClipeAtual}");
        Foto("08_morte");
        _h.Renascer();
        GD.Print("TESTE: FIM");
        GetTree().Quit();
    }
}
