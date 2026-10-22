using Godot;

namespace EchoesOfTheShatter.Arqueiro;

/// <summary>Cena de teste: Cripta + arqueiro + câmera 3/4 + alvos. Tecla toggle_camera alterna com a CameraEstudio.</summary>
public partial class CriptaJogavel : Node3D
{
    Camera3D _estudio;
    CameraArqueiro _jogo;
    ArqueiroController _heroi;
    ArqueiroHud _hud;

    public override void _Ready()
    {
        _heroi = GetNode<ArqueiroController>("Arqueiro");
        _jogo = GetNode<CameraArqueiro>("CameraArqueiro");
        _hud = GetNode<ArqueiroHud>("Hud");
        _heroi.GlobalPosition = new Vector3(ArqueiroStats.F("spawn_x"), ArqueiroStats.F("spawn_y"), ArqueiroStats.F("spawn_z"));
        _estudio = GetNodeOrNull<Camera3D>("Cripta/CameraEstudio");
        // o clima por andar segue a câmera do jogo (propriedade Alvo)
        var amb = GetNodeOrNull("Cripta/Ambiente");
        amb?.Set("alvo_path", amb.GetPathTo(_jogo));
        Definir(false);
        if (System.Array.Exists(OS.GetCmdlineUserArgs(), a => a == "--arqueiro-teste")) AddChild(new AutoTeste());
    }

    void Definir(bool estudio)
    {
        if (_estudio != null)
        {
            _estudio.Current = estudio;
            _estudio.SetProcess(estudio);
            _estudio.SetProcessUnhandledInput(estudio);
        }
        _jogo.Current = !estudio;
        _heroi.Ativo = !estudio;
        _hud.ChaveCamera = estudio ? "hud.camera.estudio" : "hud.camera.arqueiro";
    }

    public override void _UnhandledInput(InputEvent e)
    {
        if (e.IsActionPressed("toggle_camera") && _estudio != null)
        {
            bool paraEstudio = !_estudio.Current;
            if (paraEstudio) _estudio.Set("Alvo", _jogo.Alvo);
            Definir(paraEstudio);
        }
    }
}
