using Godot;

namespace EchoesOfTheShatter.Arqueiro;

/// <summary>Boneco de treino: vida, flash ao acertar, balanço, número de dano flutuante e renascimento.</summary>
public partial class Dummy : StaticBody3D
{
    float _hp, _hpMax;
    float _tFlash;
    float _tBalanco;
    Vector3 _dirBalanco;
    float _tRenasce;
    bool _morto;
    Node3D _visual;
    Label3D _rotuloHp;
    readonly System.Collections.Generic.List<(MeshInstance3D mi, StandardMaterial3D mat)> _mats = new();

    public bool Morto => _morto;
    public float Hp => _hp;

    public override void _Ready()
    {
        AddToGroup(Camadas.GrupoAlvo);
        CollisionLayer = Camadas.Alvo;
        CollisionMask = 0;
        _hpMax = _hp = ArqueiroStats.F("alvo_vida");
        _visual = GetNodeOrNull<Node3D>("Visual");
        _rotuloHp = GetNodeOrNull<Label3D>("RotuloHp");
        if (_visual != null)
            foreach (var n in _visual.FindChildren("*", "MeshInstance3D", true, false))
                if (n is MeshInstance3D mi)
                {
                    var baseMat = mi.GetActiveMaterial(0) as StandardMaterial3D ?? new StandardMaterial3D();
                    var mat = (StandardMaterial3D)baseMat.Duplicate();
                    mat.EmissionEnabled = true;
                    mat.Emission = Colors.White;
                    mat.EmissionEnergyMultiplier = 0f;
                    mi.MaterialOverride = mat;
                    _mats.Add((mi, mat));
                }
        AtualizarRotulo();
        CallDeferred(nameof(AssentarNoChao));
    }

    void AssentarNoChao()
    {
        var q = PhysicsRayQueryParameters3D.Create(GlobalPosition + Vector3.Up * 6f, GlobalPosition + Vector3.Down * 12f, Camadas.Mundo);
        var r = GetWorld3D().DirectSpaceState.IntersectRay(q);
        if (r.Count > 0) GlobalPosition = (Vector3)r["position"];
    }

    /// <summary>Chamado pela flecha: dano, direção do golpe e carga (0..1).</summary>
    public void Hurt(float dano, Vector3 dir, float carga)
    {
        if (_morto) return;
        _hp -= dano;
        _tFlash = ArqueiroStats.F("alvo_flash");
        _tBalanco = ArqueiroStats.F("alvo_balanco_tempo");
        _dirBalanco = dir;
        SpawnNumero(dano);
        AtualizarRotulo();
        // Feedback global: tremor de câmera e hit stop.
        var cam = GetTree().GetFirstNodeInGroup(Camadas.GrupoCamera);
        cam?.Call("AdicionarTrauma", ArqueiroStats.F("cam_trauma_acerto"));
        if (carga >= ArqueiroStats.F("fb_hitstop_min_carga")) HitStop.Disparar(GetTree());
        if (_hp <= 0f) { _morto = true; _tRenasce = ArqueiroStats.F("alvo_renasce"); if (_visual != null) _visual.Visible = false; }
    }

    public override void _Process(double delta)
    {
        float dt = (float)delta;
        if (_morto)
        {
            _tRenasce -= dt;
            if (_tRenasce <= 0f)
            {
                _morto = false; _hp = _hpMax;
                if (_visual != null) { _visual.Visible = true; }
                AtualizarRotulo();
            }
            return;
        }
        if (_tFlash > 0f)
        {
            _tFlash -= dt;
            float k = Mathf.Max(_tFlash, 0f) / ArqueiroStats.F("alvo_flash");
            foreach (var (_, mat) in _mats) mat.EmissionEnergyMultiplier = k;
        }
        if (_visual != null)
        {
            float k2 = _tBalanco > 0f ? _tBalanco / ArqueiroStats.F("alvo_balanco_tempo") : 0f;
            _tBalanco = Mathf.Max(_tBalanco - dt, 0f);
            float ang = Mathf.DegToRad(ArqueiroStats.F("alvo_balanco")) * k2 * Mathf.Sin(k2 * Mathf.Pi);
            var eixo = _dirBalanco.Cross(Vector3.Up);
            _visual.Basis = eixo.LengthSquared() > 0.0001f ? new Basis(eixo.Normalized(), -ang) : Basis.Identity;
        }
    }

    void AtualizarRotulo()
    {
        if (_rotuloHp != null) _rotuloHp.Text = $"{Mathf.Max(_hp, 0f):0}/{_hpMax:0}";
    }

    void SpawnNumero(float dano)
    {
        var l = new Label3D
        {
            Text = $"{dano:0}",
            Billboard = BaseMaterial3D.BillboardModeEnum.Enabled,
            NoDepthTest = true,
            FontSize = 96,
            OutlineSize = 24,
            Modulate = new Color(1f, 0.85f, 0.4f),
        };
        GetTree().CurrentScene.AddChild(l);
        l.GlobalPosition = GlobalPosition + Vector3.Up * 2f;
        var t = l.CreateTween().SetParallel();
        t.TweenProperty(l, "global_position:y", l.GlobalPosition.Y + ArqueiroStats.F("alvo_numero_sobe"), ArqueiroStats.F("alvo_numero_tempo"));
        t.TweenProperty(l, "modulate:a", 0f, ArqueiroStats.F("alvo_numero_tempo"));
        t.Chain().TweenCallback(Callable.From(l.QueueFree));
    }
}

/// <summary>Hit stop: desacelera o tempo por alguns frames reais (Engine.TimeScale).</summary>
public static class HitStop
{
    static bool _ativo;

    public static void Disparar(SceneTree arvore)
    {
        if (_ativo) return;
        _ativo = true;
        Engine.TimeScale = ArqueiroStats.F("fb_hitstop_escala");
        var t = arvore.CreateTimer(ArqueiroStats.F("fb_hitstop_tempo"), true, false, true);
        t.Timeout += () => { Engine.TimeScale = 1.0; _ativo = false; };
    }
}
