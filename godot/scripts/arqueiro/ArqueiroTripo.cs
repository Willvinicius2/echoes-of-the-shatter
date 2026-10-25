using Godot;

namespace EchoesOfTheShatter.Arqueiro;

/// <summary>
/// Corpo do arqueiro modelado no Tripo (GLB animado + AnimationTree em arqueiro_animado.gd).
/// Fica no lugar do ArqueiroModular. O ArqueiroAnimadorTripo traduz o Estado do controlador
/// para a velocidade (0 idle, 0.5 andar, 1 correr) e para os one-shots do script GDScript.
/// </summary>
public partial class ArqueiroTripo : Node3D
{
    [Export] public float Escala = 2.2f;
    public Node3D Animado { get; private set; }

    public override void _Ready()
    {
        Animado = GD.Load<PackedScene>("res://scenes/arqueiro/ArqueiroAnimadoTripo.tscn").Instantiate<Node3D>();
        // o GLB mede ~1,0 m e olha para +X; o jogo usa +Z para frente e uma capsula de 1,8 m
        Animado.RotationDegrees = new Vector3(0, -90, 0);
        Animado.Scale = Vector3.One * Escala;
        AddChild(Animado);
    }
}

public partial class ArqueiroAnimadorTripo : Node
{
    Node3D _a;
    Estado _ant = Estado.Locomocao;
    string _clipe = "locomocao";
    public string ClipeAtual => _clipe;

    public void Iniciar(ArqueiroTripo corpo) => _a = corpo.Animado;

    public void Atualizar(Estado est, float velHoriz, float carga01, float delta)
    {
        if (_a == null) return;
        float vel = 0f;
        if (est == Estado.Locomocao)
        {
            float ratio = velHoriz / ArqueiroStats.F("mov_vel_max");
            if (velHoriz >= ArqueiroStats.F("anim_vel_parado"))
                vel = ratio < ArqueiroStats.F("mov_razao_andar")
                    ? 0.5f * ratio / ArqueiroStats.F("mov_razao_andar")
                    : Mathf.Clamp(0.5f + 0.5f * (ratio - ArqueiroStats.F("mov_razao_andar")) / (1f - ArqueiroStats.F("mov_razao_andar")), 0.5f, 1f);
        }
        _a.Set("velocidade", vel);
        if (est != _ant)
        {
            switch (est)
            {
                case Estado.Esquiva: _a.Call("tocar", "dash"); break;
                case Estado.Carregando: _a.Call("tocar", "sacar_arco"); break;
                case Estado.Disparo: _a.Call("tocar", "shoot"); break;
                case Estado.Dano: _a.Call("tocar", "hurt"); break;
                case Estado.Morte: _a.Call("tocar", "fall"); break;
                case Estado.Locomocao:
                    if (_ant == Estado.Carregando) _a.Call("tocar", "guardar_arco");
                    break;
            }
            _ant = est;
        }
        _clipe = _a.Call("estado_atual").AsString();
    }
}
