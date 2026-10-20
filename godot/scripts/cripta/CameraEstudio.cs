using Godot;

namespace EchoesOfTheShatter.Cripta;

/// <summary>Câmera de estudo do mapa: WASD move no chão, roda do mouse dá zoom, Q/E gira, botão do meio arrasta.</summary>
public partial class CameraEstudio : Camera3D
{
    [Export] public float Distancia = 26f;
    [Export] public float Yaw = 45f;
    [Export] public float Pitch = -52f;
    [Export] public float Velocidade = 14f;
    [Export] public Vector3 Alvo { get; set; } = Vector3.Zero;

    public override void _Ready() => Aplicar();

    public override void _Process(double delta)
    {
        var d = Vector2.Zero;
        if (Input.IsKeyPressed(Key.W)) d.Y -= 1;
        if (Input.IsKeyPressed(Key.S)) d.Y += 1;
        if (Input.IsKeyPressed(Key.A)) d.X -= 1;
        if (Input.IsKeyPressed(Key.D)) d.X += 1;
        if (Input.IsKeyPressed(Key.Q)) Yaw -= 60f * (float)delta;
        if (Input.IsKeyPressed(Key.E)) Yaw += 60f * (float)delta;
        var basis = Basis.FromEuler(new Vector3(0, Mathf.DegToRad(Yaw), 0));
        Alvo += basis * new Vector3(d.X, 0, d.Y) * Velocidade * (float)delta * (Distancia / 26f);
        Aplicar();
    }

    public override void _UnhandledInput(InputEvent e)
    {
        if (e is InputEventMouseButton mb && mb.Pressed)
        {
            if (mb.ButtonIndex == MouseButton.WheelUp) Distancia = Mathf.Max(6f, Distancia * 0.92f);
            if (mb.ButtonIndex == MouseButton.WheelDown) Distancia = Mathf.Min(120f, Distancia * 1.08f);
        }
    }

    public void Aplicar()
    {
        var rot = Basis.FromEuler(new Vector3(Mathf.DegToRad(Pitch), Mathf.DegToRad(Yaw), 0));
        Basis = rot;
        Position = Alvo + rot.Z * Distancia;
    }
}
