using Godot;

namespace EchoesOfTheShatter.Cripta;

/// <summary>Tremulação da luz âmbar do braseiro (OmniLight3D).</summary>
public partial class BraseiroLuz : OmniLight3D
{
    [Export] public float EnergiaBase = 3.2f;
    [Export] public float Variacao = 0.35f;
    private float _t;
    private float _fase;

    public override void _Ready()
    {
        _fase = GD.Randf() * 100f;
        EnergiaBase = LightEnergy;
    }

    public override void _Process(double delta)
    {
        _t += (float)delta;
        float n = Mathf.Sin((_t + _fase) * 9.1f) * 0.5f + Mathf.Sin((_t + _fase) * 23.7f) * 0.3f + Mathf.Sin((_t + _fase) * 4.3f) * 0.2f;
        LightEnergy = EnergiaBase * (1f + Variacao * n);
    }
}
