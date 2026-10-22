using System.Collections.Generic;
using System.Globalization;
using Godot;

namespace EchoesOfTheShatter.Arqueiro;

/// <summary>
/// Monta o corpo do arqueiro (Arqueiro_Corpo.glb) e os mÃ³dulos de equipamento por ID (equipamento.csv).
/// MÃ³dulos "pele" tÃªm o mesmo esqueleto do corpo: a malha skinada Ã© reparentada sob o Skeleton3D do corpo.
/// MÃ³dulos "anexo" (arco, aljava) vÃ£o num BoneAttachment3D.
/// Sem o corpo no disco, usa o esqueleto de um mÃ³dulo (sem animaÃ§Ãµes) para o jogo continuar jogÃ¡vel.
/// </summary>
public partial class ArqueiroModular : Node3D
{
    const string CorpoCena = "res://art/models/personagens/arqueiro/Arqueiro_Corpo.glb";
    const string CaminhoEquip = "res://data/arqueiro/equipamento.csv";
    const string CaminhoLoadout = "res://data/arqueiro/loadout.csv";

    public Skeleton3D Esqueleto { get; private set; }
    public AnimationPlayer Animacoes { get; private set; }
    public bool CorpoReal { get; private set; }

    readonly Dictionary<string, Node> _porSlot = new();

    public override void _Ready()
    {
        MontarCorpo();
        var ids = new List<string>();
        foreach (var c in CsvLeitor.Ler(CaminhoLoadout, out _)) ids.Add(c[0]);
        Equipar(ids);
    }

    void MontarCorpo()
    {
        if (ResourceLoader.Exists(CorpoCena))
        {
            var corpo = GD.Load<PackedScene>(CorpoCena).Instantiate<Node3D>();
            AddChild(corpo);
            Esqueleto = corpo.FindChild("Skeleton3D", true, false) as Skeleton3D;
            Animacoes = corpo.FindChild("AnimationPlayer", true, false) as AnimationPlayer;
            CorpoReal = Esqueleto != null;
            return;
        }
        GD.PushWarning("Arqueiro_Corpo.glb ausente: usando esqueleto de um mÃ³dulo (sem animaÃ§Ãµes de clipe).");
        var rig = GD.Load<PackedScene>("res://art/models/personagens/arqueiro/Arqueiro_Capuz.glb").Instantiate<Node3D>();
        AddChild(rig);
        Esqueleto = rig.FindChild("Skeleton3D", true, false) as Skeleton3D;
        foreach (var m in Esqueleto.GetChildren())
            if (m is MeshInstance3D) m.QueueFree();
    }

    /// <summary>Troca todo o equipamento pela lista de IDs (a ordem decide: o Ãºltimo ID sobrescreve o slot).</summary>
    public void Equipar(IEnumerable<string> ids)
    {
        foreach (var n in _porSlot.Values) n.QueueFree();
        _porSlot.Clear();
        _escondePorSlot.Clear();
        if (Esqueleto == null) return;
        var linhas = CsvLeitor.Ler(CaminhoEquip, out _);
        foreach (var id in ids)
            foreach (var l in linhas)
                if (l[0] == id) EquiparLinha(l);
        AplicarEsconde();
    }

    // Partes do corpo base escondidas por cada modulo (coluna esconde do CSV, nomes de malha separados por |).
    readonly Dictionary<string, string[]> _escondePorSlot = new();

    void AplicarEsconde()
    {
        if (Esqueleto == null) return;
        var ocultas = new HashSet<string>();
        foreach (var v in _escondePorSlot.Values) foreach (var n in v) ocultas.Add(n);
        foreach (var m in Esqueleto.GetChildren())
            if (m is MeshInstance3D mi) mi.Visible = !ocultas.Contains(mi.Name.ToString());
    }

    void EquiparLinha(string[] l)
    {
        string slot = l[1], tipo = l[2], osso = l[3], cena = l[4];
        if (!ResourceLoader.Exists(cena)) { GD.PushWarning($"MÃ³dulo ausente: {cena}"); return; }
        if (_porSlot.TryGetValue(slot, out var antigo)) antigo.QueueFree();
        _escondePorSlot[slot] = l.Length > 12 && l[12].Length > 0 ? l[12].Split('|') : System.Array.Empty<string>();
        _escondePorSlot[slot] = l.Length > 12 && l[12].Length > 0 ? l[12].Split('|') : System.Array.Empty<string>();
        var inst = GD.Load<PackedScene>(cena).Instantiate<Node3D>();
        if (tipo == "pele")
        {
            var sk = inst.FindChild("Skeleton3D", true, false);
            var grupo = new Node3D { Name = "Mod_" + slot };
            Esqueleto.AddChild(grupo);
            if (sk != null)
                foreach (var m in sk.GetChildren())
                    if (m is MeshInstance3D mi)
                    {
                        sk.RemoveChild(mi);
                        mi.Owner = null;
                        grupo.AddChild(mi);
                        mi.Skeleton = new NodePath("../.."); // grupo -> Skeleton3D
                    }
            inst.QueueFree();
            _porSlot[slot] = grupo;
        }
        else
        {
            var att = new BoneAttachment3D { Name = "Att_" + slot, BoneName = osso };
            Esqueleto.AddChild(att);
            inst.Position = new Vector3(F(l[5]), F(l[6]), F(l[7]));
            inst.RotationDegrees = new Vector3(F(l[8]), F(l[9]), F(l[10]));
            inst.Scale = Vector3.One * F(l[11]);
            inst.Owner = null;
            att.AddChild(inst);
            _porSlot[slot] = att;
        }
    }

    static float F(string s) => float.Parse(s, CultureInfo.InvariantCulture);
}

