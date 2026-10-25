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
        CriarColisaoProps();
        Definir(false);
        if (System.Array.Exists(OS.GetCmdlineUserArgs(), a => a == "--arqueiro-teste")) AddChild(new AutoTeste());
    }

    static readonly string[] PrefixosSolidos = { "Braseiro", "PilarParede", "PilarCobertura", "Pilar_", "Coluna", "Estatua", "Pedestal", "Altar" };

    // Os props da Cripta vieram sem colisao: cria uma caixa fixa (camada Mundo) em volta de cada prop solido.
    void CriarColisaoProps()
    {
        var props = GetNodeOrNull("Cripta/Props");
        if (props == null) return;
        foreach (var n in props.FindChildren("*", "Node3D", true, false))
        {
            if (n is not Node3D raiz || raiz.GetChildCount() == 0) continue;
            bool solido = false;
            foreach (var pf in PrefixosSolidos) if (raiz.Name.ToString().StartsWith(pf)) solido = true;
            if (!solido || raiz.GetParent().Name.ToString().StartsWith("Braseiro")) continue;
            bool temMalha = false; Aabb caixa = default;
            foreach (var m in raiz.FindChildren("*", "MeshInstance3D", true, false))
            {
                var mi = (MeshInstance3D)m;
                var a = mi.GlobalTransform * mi.GetAabb();
                caixa = temMalha ? caixa.Merge(a) : a; temMalha = true;
            }
            if (!temMalha || caixa.Size.Y < 0.3f) continue;
            var corpo = new StaticBody3D { CollisionLayer = Camadas.Mundo, CollisionMask = 0 };
            var forma = new CollisionShape3D { Shape = new BoxShape3D { Size = new Vector3(caixa.Size.X * 0.85f, caixa.Size.Y, caixa.Size.Z * 0.85f) } };
            corpo.AddChild(forma);
            AddChild(corpo);
            corpo.GlobalPosition = caixa.GetCenter();
        }
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
