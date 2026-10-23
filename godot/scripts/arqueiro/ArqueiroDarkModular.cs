using System.Collections.Generic;
using Godot;

namespace EchoesOfTheShatter.Arqueiro;

/// <summary>
/// Arqueiro Dark montado por modulos (data/arqueiro_dark/*.csv, mesmas colunas do arqueiro atual).
/// O corpo dark (ArcherDark_Body.glb, linha tipo "base") traz o esqueleto; sem ele, usa o corpo atual como apoio.
/// Qualquer GLB ausente e pulado com aviso, entao cada modulo novo aparece assim que o arquivo entra.
/// Nao altera o ArqueiroModular: so troca caminhos e ganha liga/desliga por slot.
/// </summary>
public partial class ArqueiroDarkModular : ArqueiroModular
{
    const string CorpoDark = "res://art/models/personagens/arqueiro_dark/ArcherDark_Body.glb";

    readonly Dictionary<string, Node3D> _base = new();
    readonly HashSet<string> _ocultos = new();
    Node3D _malhaBase;

    public bool CorpoDarkReal { get; private set; }

    public ArqueiroDarkModular()
    {
        CaminhoEquip = "res://data/arqueiro_dark/equipamento.csv";
        CaminhoLoadout = "res://data/arqueiro_dark/loadout.csv";
    }

    protected override void MontarCorpo()
    {
        if (ResourceLoader.Exists(CorpoDark))
        {
            var corpo = GD.Load<PackedScene>(CorpoDark).Instantiate<Node3D>();
            AddChild(corpo);
            Esqueleto = corpo.FindChild("Skeleton3D", true, false) as Skeleton3D;
            Animacoes = corpo.FindChild("AnimationPlayer", true, false) as AnimationPlayer;
            if (Esqueleto != null)
            {
                CorpoReal = true;
                CorpoDarkReal = true;
                foreach (var m in Esqueleto.GetChildren())
                    if (m is MeshInstance3D mi) { _malhaBase = mi; break; }
                return;
            }
            corpo.QueueFree();
        }
        GD.PushWarning("ArcherDark_Body.glb ausente: usando o corpo atual como apoio (so na cena de teste).");
        base.MontarCorpo();
    }

    protected override bool EquiparEspecial(string[] l)
    {
        if (l[2] != "base") return false;
        if (CorpoDarkReal && _malhaBase != null) _base[l[1]] = _malhaBase;
        return true;
    }

    protected override void AposEquipar() => Reaplicar();

    public bool Existe(string slot) => _base.ContainsKey(slot) || _porSlot.ContainsKey(slot);

    public bool Visivel(string slot) => !_ocultos.Contains(slot);

    public void Alternar(string slot)
    {
        if (!_ocultos.Add(slot)) _ocultos.Remove(slot);
        Reaplicar();
    }

    void Reaplicar()
    {
        foreach (var kv in _base) kv.Value.Visible = !_ocultos.Contains(kv.Key);
        foreach (var kv in _porSlot)
            if (kv.Value is Node3D n) n.Visible = !_ocultos.Contains(kv.Key);
    }
}
