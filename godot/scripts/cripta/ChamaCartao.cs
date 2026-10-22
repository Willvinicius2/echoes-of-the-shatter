using Godot;

namespace EchoesOfTheShatter.Cripta;

/// <summary>Chama feita de cartões billboard sobrepostos que oscilam em altura e largura.</summary>
public partial class ChamaCartao : Node3D
{
    private float _t, _fase;
    public override void _Ready() => _fase = GD.Randf() * 50f;
    public override void _Process(double delta)
    {
        _t += (float)delta;
        int i = 0;
        foreach (var c in GetChildren())
        {
            if (c is not Node3D n) continue;
            float f = _t * (7f + i * 3.1f) + _fase + i * 1.7f;
            float h = 1f + 0.18f * Mathf.Sin(f) + 0.10f * Mathf.Sin(f * 2.3f);
            float w = 1f - 0.10f * Mathf.Sin(f * 1.3f);
            n.Scale = new Vector3(w * (1f - 0.18f * i), h * (1f - 0.12f * i), 1f);
            n.Position = new Vector3(0.06f * Mathf.Sin(f * 0.7f), n.Position.Y, 0.06f * Mathf.Cos(f * 0.9f));
            i++;
        }
    }
}
