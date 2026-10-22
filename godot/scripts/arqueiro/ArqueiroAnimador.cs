using System.Collections.Generic;
using Godot;

namespace EchoesOfTheShatter.Arqueiro;

public enum Estado { Locomocao, Esquiva, Carregando, Disparo, Dano, Morte }

/// <summary>
/// Máquina de estados de animação por cima do AnimationPlayer do corpo (AN_Arqueiro_*), com mistura entre clipes.
/// Sem os clipes (corpo placeholder), balança ossos/modelo por código só para dar leitura de movimento.
/// </summary>
public partial class ArqueiroAnimador : Node
{
    ArqueiroModular _mod;
    Node3D _raizModelo;
    readonly Dictionary<string, string> _nomes = new();
    string _atual = "";
    float _fase;
    float _tSemClipe;
    readonly Dictionary<int, Quaternion> _repouso = new();

    static readonly string[] Loops = { "Idle", "Walk", "Run", "AimIdle" };

    public string ClipeAtual => _atual;

    public void Iniciar(ArqueiroModular mod, Node3D raizModelo)
    {
        _mod = mod;
        _raizModelo = raizModelo;
        var ap = mod.Animacoes;
        if (ap != null)
        {
            foreach (var n in ap.GetAnimationList())
            {
                string s = n.ToString();
                int i = s.LastIndexOf("AN_Arqueiro_", System.StringComparison.Ordinal);
                string curto = i >= 0 ? s[(i + "AN_Arqueiro_".Length)..] : s;
                _nomes[curto] = s;
            }
            foreach (var l in Loops)
                if (_nomes.TryGetValue(l, out var full))
                    ap.GetAnimation(full).LoopMode = Animation.LoopModeEnum.Linear;
        }
        if (_mod.Esqueleto != null)
            for (int i = 0; i < _mod.Esqueleto.GetBoneCount(); i++) _repouso[i] = _mod.Esqueleto.GetBoneRest(i).Basis.GetRotationQuaternion();
    }

    public float Duracao(string curto, float padrao)
        => _mod?.Animacoes != null && _nomes.TryGetValue(curto, out var f) ? (float)_mod.Animacoes.GetAnimation(f).Length : padrao;

    public void Atualizar(Estado est, float velHoriz, float carga01, float delta)
    {
        string alvo;
        float escala = 1f;
        float mistura = ArqueiroStats.F("anim_mistura");
        switch (est)
        {
            case Estado.Esquiva:
                alvo = "Dodge";
                escala = Duracao(alvo, ArqueiroStats.F("esq_tempo")) / ArqueiroStats.F("esq_tempo");
                mistura = ArqueiroStats.F("anim_mistura_esquiva");
                break;
            case Estado.Carregando:
                if (carga01 >= ArqueiroStats.F("evt_corda_cheia_quadro") / ArqueiroStats.F("evt_draw_quadros") && _atual != "Draw") alvo = "AimIdle";
                else if (_atual == "AimIdle") alvo = "AimIdle";
                else
                {
                    alvo = "Draw";
                    escala = Duracao(alvo, ArqueiroStats.F("tiro_tempo_carga")) / ArqueiroStats.F("tiro_tempo_carga");
                }
                break;
            case Estado.Disparo:
                alvo = "Release";
                escala = Duracao(alvo, ArqueiroStats.F("tiro_tempo_solta")) / ArqueiroStats.F("tiro_tempo_solta");
                mistura = ArqueiroStats.F("anim_mistura_esquiva");
                break;
            case Estado.Dano:
                alvo = "Hit";
                escala = Duracao(alvo, ArqueiroStats.F("dano_atordoa")) / ArqueiroStats.F("dano_atordoa");
                break;
            case Estado.Morte:
                alvo = "Death";
                break;
            default:
                float ratio = velHoriz / ArqueiroStats.F("mov_vel_max");
                if (velHoriz < ArqueiroStats.F("anim_vel_parado")) alvo = "Idle";
                else if (ratio < ArqueiroStats.F("mov_razao_andar"))
                {
                    alvo = "Walk";
                    escala = Mathf.Min(velHoriz / ArqueiroStats.F("anim_ref_andar"), ArqueiroStats.F("anim_escala_max"));
                }
                else
                {
                    alvo = "Run";
                    escala = Mathf.Min(velHoriz / ArqueiroStats.F("anim_ref_correr"), ArqueiroStats.F("anim_escala_max_correr"));
                    escala = Mathf.Max(escala, ArqueiroStats.F("anim_escala_min_correr"));
                }
                break;
        }

        var ap = _mod.Animacoes;
        if (ap != null && _nomes.TryGetValue(alvo, out var full))
        {
            if (alvo != _atual) ap.Play(full, mistura, escala);
            else ap.SpeedScale = escala;
            _atual = alvo;
        }
        else
        {
            _atual = alvo;
            Procedural(est, alvo, velHoriz, carga01, delta);
        }
    }

    // Placeholder sem clipes: oscila coxas e braços; o eixo é o X local do osso (suficiente para ler o movimento).
    void Procedural(Estado est, string alvo, float vel, float carga, float delta)
    {
        var sk = _mod.Esqueleto;
        if (sk == null) return;
        _fase += delta * vel * 2.2f;
        float amp = alvo == "Run" ? 0.9f : alvo == "Walk" ? 0.5f : 0f;
        float s = Mathf.Sin(_fase) * amp;
        Pose(sk, "LeftUpperLeg", s); Pose(sk, "RightUpperLeg", -s);
        Pose(sk, "LeftUpperArm", -s); Pose(sk, "RightUpperArm", s);
        if (_raizModelo != null)
        {
            float inclina = est == Estado.Morte ? -Mathf.Pi / 2f : (alvo == "Run" ? 0.12f : 0f);
            var r = _raizModelo.Rotation;
            r.X = Mathf.Lerp(r.X, inclina, 1f - Mathf.Exp(-12f * delta));
            _raizModelo.Rotation = r;
        }
    }

    void Pose(Skeleton3D sk, string osso, float ang)
    {
        int i = sk.FindBone(osso);
        if (i < 0) return;
        sk.SetBonePoseRotation(i, _repouso[i] * new Quaternion(Vector3.Right, ang));
    }
}
