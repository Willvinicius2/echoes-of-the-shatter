using Godot;

namespace EchoesOfTheShatter.Arqueiro;

/// <summary>Câmera fixa 3/4 que segue o arqueiro, com suavização, avanço para a mira, recuo e tremor por trauma.</summary>
public partial class CameraArqueiro : Camera3D
{
    public Vector3 Alvo { get; set; }
    ArqueiroController _heroi;
    float _trauma;
    Vector3 _recuo;
    float _t;
    readonly FastNoiseLite _ruido = new();
    bool _iniciada;

    public override void _Ready()
    {
        AddToGroup(Camadas.GrupoCamera);
        Fov = ArqueiroStats.F("cam_fov");
        Far = 500f;
        _ruido.Seed = 7;
    }

    public void AdicionarTrauma(float v) => _trauma = Mathf.Clamp(_trauma + v, 0f, 1f);
    public void Recuo(Vector3 deslocamento) => _recuo += deslocamento;

    public override void _Process(double delta)
    {
        float dt = (float)delta;
        _heroi ??= GetTree().GetFirstNodeInGroup(Camadas.GrupoJogador) as ArqueiroController;
        if (_heroi == null) return;

        // posição interpolada: o corpo anda no passo físico (60 Hz) e a câmera desenha em taxa maior; sem isso há tranco
        var foco = _heroi.GetGlobalTransformInterpolated().Origin;
        var lead = _heroi.PontoMira - foco; lead.Y = 0;
        if (_heroi.EstadoAtual == Estado.Carregando || _heroi.EstadoAtual == Estado.Disparo)
            foco += (lead * ArqueiroStats.F("cam_adianta_mira")).LimitLength(ArqueiroStats.F("cam_adianta_max"));
        Alvo = _iniciada ? Alvo.Lerp(foco, 1f - Mathf.Exp(-ArqueiroStats.F("cam_atraso") * dt)) : foco;
        _iniciada = true;
        _recuo = _recuo.Lerp(Vector3.Zero, 1f - Mathf.Exp(-ArqueiroStats.F("cam_recuo_volta") * dt));

        float pitch = Mathf.DegToRad(ArqueiroStats.F("cam_pitch"));
        float yaw = Mathf.DegToRad(ArqueiroStats.F("cam_yaw"));
        var rot = Basis.FromEuler(new Vector3(pitch, yaw, 0));

        _t += dt * ArqueiroStats.F("cam_tremor_freq");
        float s = _trauma * _trauma;
        var off = new Vector3(_ruido.GetNoise2D(_t, 0f), _ruido.GetNoise2D(_t, 100f), _ruido.GetNoise2D(_t, 200f)) * s * ArqueiroStats.F("cam_tremor_pos");
        float giro = Mathf.DegToRad(ArqueiroStats.F("cam_tremor_rot")) * s * _ruido.GetNoise2D(_t, 300f);
        _trauma = Mathf.Max(_trauma - ArqueiroStats.F("cam_trauma_queda") * dt, 0f);

        Basis = rot * new Basis(Vector3.Forward, giro);
        Position = Alvo + rot.Z * ArqueiroStats.F("cam_dist") + rot * off + _recuo;
    }
}
