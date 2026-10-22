using Godot;

namespace EchoesOfTheShatter.Arqueiro;

/// <summary>
/// Controle do arqueiro: movimento WASD/analógico relativo à câmera, esquiva com i-frames e cooldown,
/// mira (mouse no plano do chão ou analógico direito), carga e disparo de flecha. Números em arqueiro.csv.
/// </summary>
public partial class ArqueiroController : CharacterBody3D
{
    [Export] public PackedScene CenaFlecha;
    [Export] public NodePath CaminhoModelo = new("Modelo");

    public bool Ativo { get; set; } = true;
    public Estado EstadoAtual { get; private set; } = Estado.Locomocao;
    public float Hp { get; private set; }
    public float HpMax => ArqueiroStats.F("vida_max");
    public float Carga01 { get; private set; }
    public float RecargaEsquiva01 => Mathf.Clamp(_cdEsquiva / ArqueiroStats.F("esq_recarga"), 0f, 1f);
    public bool Invulneravel => _iframe > 0f;
    public Vector3 DirMira { get; private set; } = Vector3.Forward;
    public Vector3 PontoMira { get; private set; }
    public Node3D Modelo { get; private set; }
    public ArqueiroModular Modular { get; private set; }
    public int Disparos { get; private set; }
    public string ClipeAtual => _anim?.ClipeAtual ?? "";

    ArqueiroAnimador _anim;
    CameraArqueiro _cam;
    float _tEstado, _cdEsquiva, _cdTiro, _iframe, _iframeAtraso;
    Vector3 _dirEsquiva;
    float _yawModelo;
    Vector2 _mouse;
    bool _usaMouse;
    Vector3? _mouseForcado;

    public override void _Ready()
    {
        AddToGroup(Camadas.GrupoJogador);
        CollisionLayer = Camadas.Jogador;
        CollisionMask = Camadas.Mundo;
        Modelo = GetNode<Node3D>(CaminhoModelo);
        Modular = Modelo.GetNode<ArqueiroModular>("Corpo");
        _anim = new ArqueiroAnimador { Name = "Animador" };
        AddChild(_anim);
        _anim.Iniciar(Modular, Modelo);
        FloorSnapLength = ArqueiroStats.F("mov_snap_chao");
        FloorMaxAngle = Mathf.DegToRad(ArqueiroStats.F("mov_inclinacao_max"));
        FloorStopOnSlope = true;
        Hp = HpMax;
        DirMira = Vector3.Forward;
    }

    public override void _Input(InputEvent e)
    {
        if (e is InputEventMouseMotion mm) { _mouse = mm.Position; _usaMouse = true; }
        else if (e is InputEventMouseButton mb) _mouse = mb.Position;
    }

    /// <summary>Usado por testes automáticos: força o ponto de mira no mundo (anula o mouse).</summary>
    public void ForcarMira(Vector3? ponto) => _mouseForcado = ponto;

    public override void _PhysicsProcess(double delta)
    {
        float dt = (float)delta;
        _cam ??= GetTree().GetFirstNodeInGroup(Camadas.GrupoCamera) as CameraArqueiro;
        _tEstado += dt;
        _cdEsquiva = Mathf.Max(_cdEsquiva - dt, 0f);
        _cdTiro = Mathf.Max(_cdTiro - dt, 0f);
        _iframe = Mathf.Max(_iframe - dt, 0f);

        Vector2 entrada = Ativo ? Input.GetVector("move_left", "move_right", "move_up", "move_down") : Vector2.Zero;
        Vector3 dirMov = DirecaoMundo(entrada);
        if (Ativo) AtualizarMira();
        bool atira = Ativo && Input.IsActionPressed("shoot");
        bool atiraPress = Ativo && Input.IsActionJustPressed("shoot");
        bool esquiva = Ativo && Input.IsActionJustPressed("dodge");

        var horiz = new Vector3(Velocity.X, 0, Velocity.Z);
        float velMax = ArqueiroStats.F("mov_vel_max");
        Vector3 alvoGiro = Vector3.Zero;

        switch (EstadoAtual)
        {
            case Estado.Morte:
                horiz = Atrito(horiz, dt);
                if (_tEstado >= ArqueiroStats.F("morte_renasce")) Renascer();
                break;

            case Estado.Dano:
                horiz = Atrito(horiz, dt);
                if (_tEstado >= ArqueiroStats.F("dano_atordoa")) Mudar(Estado.Locomocao);
                break;

            case Estado.Esquiva:
            {
                float T = ArqueiroStats.F("esq_tempo");
                float k = ArqueiroStats.F("esq_curva");
                float media = ArqueiroStats.F("esq_distancia") / T;
                float vel = media * Mathf.Lerp(1f + k, 1f - k, Mathf.Clamp(_tEstado / T, 0f, 1f));
                horiz = _dirEsquiva * vel;
                alvoGiro = _dirEsquiva;
                if (_iframeAtraso > 0f) { _iframeAtraso -= dt; if (_iframeAtraso <= 0f) _iframe = ArqueiroStats.F("esq_iframe_tempo"); }
                if (_tEstado >= T) Mudar(Estado.Locomocao);
                break;
            }

            case Estado.Carregando:
                Carga01 = Mathf.Clamp(_tEstado / ArqueiroStats.F("tiro_tempo_carga"), 0f, 1f);
                horiz = Mover(horiz, dirMov, velMax * ArqueiroStats.F("mov_mult_mirando"), dt);
                alvoGiro = DirMira;
                if (esquiva && _cdEsquiva <= 0f) IniciarEsquiva(dirMov);
                else if (!atira) Disparar();
                break;

            case Estado.Disparo:
                horiz = Mover(horiz, dirMov, velMax * ArqueiroStats.F("mov_mult_disparo"), dt);
                alvoGiro = DirMira;
                if (esquiva && _cdEsquiva <= 0f) IniciarEsquiva(dirMov);
                else if (_tEstado >= ArqueiroStats.F("tiro_tempo_solta")) Mudar(Estado.Locomocao);
                break;

            default: // Locomocao
                horiz = Mover(horiz, dirMov, velMax, dt);
                alvoGiro = dirMov.LengthSquared() > 0.0001f ? dirMov : Vector3.Zero;
                if (esquiva && _cdEsquiva <= 0f) IniciarEsquiva(dirMov);
                else if (atiraPress && _cdTiro <= 0f) { Mudar(Estado.Carregando); Carga01 = 0f; }
                break;
        }
        if (EstadoAtual != Estado.Carregando && EstadoAtual != Estado.Disparo) Carga01 = 0f;

        float vy = Velocity.Y;
        vy = IsOnFloor() ? 0f : vy - ArqueiroStats.F("mov_gravidade") * dt;
        Velocity = new Vector3(horiz.X, vy, horiz.Z);
        MoveAndSlide();

        Girar(alvoGiro, dt);
        var h = new Vector3(Velocity.X, 0, Velocity.Z);
        _anim.Atualizar(EstadoAtual, h.Length(), Carga01, dt);
    }

    // ---------- movimento
    Vector3 DirecaoMundo(Vector2 e)
    {
        if (e.LengthSquared() < 0.0001f) return Vector3.Zero;
        Vector3 frente, direita;
        if (_cam != null)
        {
            var b = _cam.GlobalBasis;
            frente = -b.Z; frente.Y = 0; frente = frente.Normalized();
            direita = b.X; direita.Y = 0; direita = direita.Normalized();
        }
        else { frente = Vector3.Forward; direita = Vector3.Right; }
        return (direita * e.X + frente * -e.Y).LimitLength(1f);
    }

    Vector3 Mover(Vector3 horiz, Vector3 dirMov, float velMax, float dt)
    {
        if (dirMov.LengthSquared() > 0.0001f)
            return horiz.MoveToward(dirMov * velMax, ArqueiroStats.F("mov_aceleracao") * dt);
        return Atrito(horiz, dt);
    }

    Vector3 Atrito(Vector3 horiz, float dt) => horiz.MoveToward(Vector3.Zero, ArqueiroStats.F("mov_atrito") * dt);

    void Girar(Vector3 alvo, float dt)
    {
        if (alvo.LengthSquared() < 0.0001f) return;
        bool mira = EstadoAtual == Estado.Carregando || EstadoAtual == Estado.Disparo;
        float giro = mira ? ArqueiroStats.F("mira_giro") : ArqueiroStats.F("mov_giro");
        float yawAlvo = Mathf.Atan2(alvo.X, alvo.Z);
        _yawModelo = Mathf.LerpAngle(_yawModelo, yawAlvo, 1f - Mathf.Exp(-giro * dt));
        var r = Modelo.Rotation;
        r.Y = _yawModelo + Mathf.DegToRad(ArqueiroStats.F("modelo_yaw_extra"));
        Modelo.Rotation = r;
    }

    // ---------- esquiva
    void IniciarEsquiva(Vector3 dirMov)
    {
        _dirEsquiva = dirMov.LengthSquared() > 0.0001f ? dirMov.Normalized()
            : new Vector3(Mathf.Sin(_yawModelo), 0, Mathf.Cos(_yawModelo));
        _cdEsquiva = ArqueiroStats.F("esq_recarga");
        _iframeAtraso = ArqueiroStats.F("esq_iframe_inicio");
        if (_iframeAtraso <= 0f) _iframe = ArqueiroStats.F("esq_iframe_tempo");
        Carga01 = 0f;
        Mudar(Estado.Esquiva);
        Efeitos.Poeira(GetTree().CurrentScene, GlobalPosition);
        _cam?.AdicionarTrauma(ArqueiroStats.F("cam_trauma_esquiva"));
    }

    // ---------- mira e tiro
    void AtualizarMira()
    {
        var st = Input.GetVector("aim_left", "aim_right", "aim_up", "aim_down");
        if (st.Length() > ArqueiroStats.F("mira_deadzone_stick") && _cam != null)
        {
            _usaMouse = false;
            var b = _cam.GlobalBasis;
            var f = -b.Z; f.Y = 0; f = f.Normalized();
            var r = b.X; r.Y = 0; r = r.Normalized();
            DirMira = (r * st.X + f * -st.Y).Normalized();
            PontoMira = GlobalPosition + DirMira * ArqueiroStats.F("cam_adianta_max");
            return;
        }
        Vector3? alvo = _mouseForcado;
        if (alvo == null && _usaMouse && _cam != null)
        {
            var o = _cam.ProjectRayOrigin(_mouse);
            var d = _cam.ProjectRayNormal(_mouse);
            var plano = new Plane(Vector3.Up, GlobalPosition.Y + ArqueiroStats.F("tiro_altura"));
            alvo = plano.IntersectsRay(o, d);
        }
        if (alvo is Vector3 p)
        {
            PontoMira = new Vector3(p.X, GlobalPosition.Y, p.Z);
            var v = PontoMira - GlobalPosition; v.Y = 0;
            if (v.Length() > ArqueiroStats.F("mira_dist_min")) DirMira = v.Normalized();
        }
        else if (!_usaMouse)
        {
            // sem mouse nem analógico: mira para onde o corpo olha
            DirMira = new Vector3(Mathf.Sin(_yawModelo), 0, Mathf.Cos(_yawModelo));
            PontoMira = GlobalPosition + DirMira * ArqueiroStats.F("cam_adianta_max");
        }
    }

    void Disparar()
    {
        float c = Mathf.Max(Carga01, ArqueiroStats.F("tiro_carga_min"));
        float vel = Mathf.Lerp(ArqueiroStats.F("flecha_vel_min"), ArqueiroStats.F("flecha_vel_max"), c);
        float dano = Mathf.Lerp(ArqueiroStats.F("flecha_dano_min"), ArqueiroStats.F("flecha_dano_max"), c);
        float alc = Mathf.Lerp(ArqueiroStats.F("flecha_alcance_min"), ArqueiroStats.F("flecha_alcance_max"), c);
        var origem = GlobalPosition + Vector3.Up * ArqueiroStats.F("tiro_altura") + DirMira * ArqueiroStats.F("tiro_frente");
        var f = CenaFlecha.Instantiate<Arrow>();
        GetTree().CurrentScene.AddChild(f);
        f.Lancar(origem, DirMira, vel, dano, alc, c, GetRid());
        _cdTiro = ArqueiroStats.F("tiro_recarga");
        Disparos++;
        _cam?.AdicionarTrauma(Mathf.Lerp(ArqueiroStats.F("cam_trauma_tiro_min"), ArqueiroStats.F("cam_trauma_tiro_max"), c));
        _cam?.Recuo(-DirMira * ArqueiroStats.F("cam_recuo") * c);
        Mudar(Estado.Disparo);
    }

    // ---------- dano / morte
    public void ReceberDano(float dano, Vector3 deOnde)
    {
        if (EstadoAtual == Estado.Morte || Invulneravel) return;
        Hp -= dano;
        _cam?.AdicionarTrauma(ArqueiroStats.F("cam_trauma_dano"));
        var empurrao = GlobalPosition - deOnde; empurrao.Y = 0;
        if (Hp <= 0f)
        {
            Hp = 0f;
            Mudar(Estado.Morte);
            Velocity = Vector3.Zero;
            return;
        }
        _iframe = ArqueiroStats.F("dano_iframe");
        if (empurrao.LengthSquared() > 0.0001f) Velocity = empurrao.Normalized() * ArqueiroStats.F("dano_empurrao");
        Mudar(Estado.Dano);
    }

    public void Renascer()
    {
        Hp = HpMax;
        _iframe = ArqueiroStats.F("dano_iframe");
        Mudar(Estado.Locomocao);
    }

    public override void _UnhandledInput(InputEvent e)
    {
        if (!Ativo) return;
        if (e.IsActionPressed("debug_dano"))
        {
            var atras = GlobalPosition - new Vector3(Mathf.Sin(_yawModelo), 0, Mathf.Cos(_yawModelo));
            ReceberDano(ArqueiroStats.F("dano_teste"), atras);
        }
        if (e.IsActionPressed("renascer")) Renascer();
    }

    void Mudar(Estado e)
    {
        EstadoAtual = e;
        _tEstado = 0f;
    }

    public string ChaveEstado() => "hud.estado." + EstadoAtual.ToString().ToLowerInvariant();
}
