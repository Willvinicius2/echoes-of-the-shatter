using Godot;

namespace EchoesOfTheShatter.Arqueiro;

/// <summary>Partículas simples (GpuParticles3D) criadas por código: faísca de impacto, poeira de esquiva e rastro da flecha.</summary>
public static class Efeitos
{
    static readonly Color CorFaisca = new(1f, 0.78f, 0.35f);
    static readonly Color CorPoeira = new(0.55f, 0.5f, 0.45f, 0.5f);
    static readonly Color CorRastro = new(0.8f, 0.9f, 1f, 0.7f);

    static StandardMaterial3D MatQuad(Color c, bool emissivo)
    {
        var m = new StandardMaterial3D
        {
            ShadingMode = BaseMaterial3D.ShadingModeEnum.Unshaded,
            BillboardMode = BaseMaterial3D.BillboardModeEnum.Particles,
            Transparency = BaseMaterial3D.TransparencyEnum.Alpha,
            VertexColorUseAsAlbedo = true,
            AlbedoColor = c,
        };
        if (emissivo) m.BlendMode = BaseMaterial3D.BlendModeEnum.Add;
        m.BillboardKeepScale = true;
        return m;
    }

    static GpuParticles3D Base(int qtd, float vida, float tamanho, Color cor, bool emissivo, bool umaVez)
    {
        var mat = new ParticleProcessMaterial();
        var g = new GpuParticles3D
        {
            Amount = qtd,
            Lifetime = vida,
            OneShot = umaVez,
            Explosiveness = umaVez ? 1f : 0f,
            Emitting = false,
            ProcessMaterial = mat,
            DrawPass1 = new QuadMesh { Size = Vector2.One * tamanho, Material = MatQuad(cor, emissivo) },
            VisibilityAabb = new Aabb(new Vector3(-6, -6, -6), new Vector3(12, 12, 12)),
        };
        var rampa = new Gradient();
        rampa.SetColor(0, Colors.White);
        rampa.SetColor(1, new Color(1, 1, 1, 0));
        mat.ColorRamp = new GradientTexture1D { Gradient = rampa };
        return g;
    }

    static void LiberarDepois(Node n, float t)
    {
        var timer = n.GetTree().CreateTimer(t);
        timer.Timeout += () => { if (GodotObject.IsInstanceValid(n)) n.QueueFree(); };
    }

    public static void Faisca(Node pai, Vector3 pos, Vector3 normal)
    {
        float vida = ArqueiroStats.F("fx_faisca_vida");
        var g = Base((int)ArqueiroStats.F("fx_faisca_qtd"), vida, ArqueiroStats.F("fx_faisca_tamanho"), CorFaisca, true, true);
        var m = (ParticleProcessMaterial)g.ProcessMaterial;
        m.Direction = normal;
        m.Spread = ArqueiroStats.F("fx_faisca_abertura");
        m.InitialVelocityMin = ArqueiroStats.F("fx_faisca_vel") * ArqueiroStats.F("fx_vel_min_razao");
        m.InitialVelocityMax = ArqueiroStats.F("fx_faisca_vel");
        m.Gravity = new Vector3(0, -ArqueiroStats.F("fx_gravidade"), 0);
        pai.AddChild(g);
        g.GlobalPosition = pos;
        g.Restart();
        g.Emitting = true;
        LiberarDepois(g, vida + ArqueiroStats.F("fx_folga"));
    }

    public static void Poeira(Node pai, Vector3 pos)
    {
        float vida = ArqueiroStats.F("fx_poeira_vida");
        var g = Base((int)ArqueiroStats.F("fx_poeira_qtd"), vida, ArqueiroStats.F("fx_poeira_tamanho"), CorPoeira, false, true);
        var m = (ParticleProcessMaterial)g.ProcessMaterial;
        m.Direction = Vector3.Up;
        m.Spread = ArqueiroStats.F("fx_poeira_abertura");
        m.InitialVelocityMin = ArqueiroStats.F("fx_poeira_vel") * ArqueiroStats.F("fx_vel_min_razao");
        m.InitialVelocityMax = ArqueiroStats.F("fx_poeira_vel");
        m.Gravity = Vector3.Zero;
        m.ScaleMin = ArqueiroStats.F("fx_poeira_escala_min");
        m.ScaleMax = ArqueiroStats.F("fx_poeira_escala_max");
        pai.AddChild(g);
        g.GlobalPosition = pos;
        g.Restart();
        g.Emitting = true;
        LiberarDepois(g, vida + ArqueiroStats.F("fx_folga"));
    }

    /// <summary>Rastro contínuo; fica no mundo (coordenadas globais) enquanto a flecha avança.</summary>
    public static GpuParticles3D Rastro(Node pai)
    {
        float vida = ArqueiroStats.F("fx_rastro_vida");
        var g = Base((int)ArqueiroStats.F("fx_rastro_qtd"), vida, ArqueiroStats.F("fx_rastro_tamanho"), CorRastro, true, false);
        var m = (ParticleProcessMaterial)g.ProcessMaterial;
        m.Gravity = Vector3.Zero;
        m.InitialVelocityMax = ArqueiroStats.F("fx_rastro_deriva");
        g.LocalCoords = false;
        pai.AddChild(g);
        g.Emitting = true;
        return g;
    }
}
