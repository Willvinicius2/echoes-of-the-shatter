using Godot;

namespace EchoesOfTheShatter.Arqueiro;

/// <summary>
/// Flecha: varredura por raycast a cada passo físico (não atravessa paredes em alta velocidade).
/// Acerta alvos do grupo "hurtable" (método Hurt) e crava em paredes.
/// </summary>
public partial class Arrow : Node3D
{
    Vector3 _dir;
    float _vel, _dano, _alcance, _percorrido, _carga;
    bool _viva;
    Rid _excluir;
    float _tCravada;
    bool _cravada;
    GpuParticles3D _rastro;

    public bool Cravada => _cravada;

    public void Lancar(Vector3 origem, Vector3 dir, float vel, float dano, float alcance, float carga, Rid excluir)
    {
        GlobalPosition = origem;
        ResetPhysicsInterpolation(); // sem isto a interpolação desenha a flecha vindo da origem do mundo
        _dir = dir.Normalized();
        _vel = vel; _dano = dano; _alcance = alcance; _carga = carga; _excluir = excluir;
        _viva = true;
        LookAt(origem + _dir, Vector3.Up);
        ResetPhysicsInterpolation();
        _rastro = Efeitos.Rastro(this);
    }

    public override void _PhysicsProcess(double delta)
    {
        float dt = (float)delta;
        if (_cravada)
        {
            _tCravada += dt;
            if (_tCravada >= ArqueiroStats.F("flecha_cravada_tempo")) QueueFree();
            return;
        }
        if (!_viva) return;

        _dir.Y -= ArqueiroStats.F("flecha_gravidade") * dt / Mathf.Max(_vel, 0.01f);
        _dir = _dir.Normalized();
        float passo = _vel * dt;
        var de = GlobalPosition;
        var para = de + _dir * passo;
        var q = PhysicsRayQueryParameters3D.Create(de, para, Camadas.Mundo | Camadas.Alvo);
        q.CollideWithAreas = false;
        if (_excluir.IsValid) q.Exclude = new Godot.Collections.Array<Rid> { _excluir };
        var r = GetWorld3D().DirectSpaceState.IntersectRay(q);
        if (r.Count > 0)
        {
            var pos = (Vector3)r["position"];
            var normal = (Vector3)r["normal"];
            var col = (Node)r["collider"];
            Impacto(pos, normal, col);
            return;
        }
        GlobalPosition = para;
        if (_dir.LengthSquared() > 0f) LookAt(para + _dir, Vector3.Up);
        _percorrido += passo;
        if (_percorrido >= _alcance) { _viva = false; _rastro.Emitting = false; Cair(); }
    }

    void Impacto(Vector3 pos, Vector3 normal, Node col)
    {
        Efeitos.Faisca(GetTree().CurrentScene, pos, normal);
        if (col.IsInGroup(Camadas.GrupoAlvo) && col.HasMethod("Hurt"))
        {
            col.Call("Hurt", _dano, _dir, _carga);
            QueueFree();
            return;
        }
        _viva = false;
        _cravada = true;
        _rastro.Emitting = false;
        GlobalPosition = pos + _dir * ArqueiroStats.F("flecha_cravada_fundo");
        ResetPhysicsInterpolation();
    }

    // Alcance esgotado: a flecha cai e some (some depois do tempo de cravada, sem física).
    void Cair()
    {
        var t = CreateTween();
        t.TweenProperty(this, "global_position:y", GlobalPosition.Y - ArqueiroStats.F("flecha_queda_altura"), ArqueiroStats.F("flecha_queda_tempo"));
        t.TweenCallback(Callable.From(QueueFree)).SetDelay(ArqueiroStats.F("flecha_queda_tempo"));
    }
}
