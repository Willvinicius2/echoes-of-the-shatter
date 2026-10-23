using Godot;

namespace EchoesOfTheShatter.Arqueiro;

/// <summary>
/// Reaproveita os clipes do arqueiro atual (Arqueiro_Corpo.glb) no ArcherDark_Body, que tem os mesmos 27 nomes de osso
/// mas proporcoes e poses de repouso diferentes. Retarget por nome de osso, feito uma vez ao montar o corpo:
/// para cada quadro do clipe, a rotacao de cada osso vira um delta no espaco do mundo (pose animada x repouso, no rig de origem)
/// e e aplicada ao repouso do rig dark; a translacao do quadril e escalada (o rig dark tem pernas mais longas).
/// </summary>
public static class ArqueiroDarkAnimacoes
{
    public const string CenaOrigem = "res://art/models/personagens/arqueiro/Arqueiro_Corpo.glb";
    const float Fps = 30f;
    static readonly string[] Loops = { "Idle", "Walk", "Run", "AimIdle" };

    /// <param name="escalaTransl">fator da translacao do quadril (1,2 = razao das alturas 1,80/1,50).</param>
    public static AnimationPlayer Gerar(Node3D raizDestino, Skeleton3D sb, float escalaTransl = 1.2f)
    {
        if (!ResourceLoader.Exists(CenaOrigem)) return null;
        var origem = GD.Load<PackedScene>(CenaOrigem).Instantiate<Node3D>();
        var sa = origem.FindChild("Skeleton3D", true, false) as Skeleton3D;
        var apa = origem.FindChild("AnimationPlayer", true, false) as AnimationPlayer;
        if (sa == null || apa == null) { origem.QueueFree(); return null; }

        var qa = new Mundo(MundoBasis(sa, origem));
        var qb = new Mundo(MundoBasis(sb, raizDestino));
        var basisA = MundoBasis(sa, origem);
        int n = sa.GetBoneCount();
        var mapa = new int[n]; // osso de origem -> osso de destino (-1 = ausente)
        for (int i = 0; i < n; i++) mapa[i] = sb.FindBone(sa.GetBoneName(i));

        var ap = new AnimationPlayer { Name = "AnimationPlayer" };
        raizDestino.AddChild(ap);
        ap.RootNode = ap.GetPathTo(raizDestino);
        var lib = new AnimationLibrary();
        string caminhoSk = raizDestino.GetPathTo(sb);

        foreach (string nome in apa.GetAnimationList())
        {
            var ana = apa.GetAnimation(nome);
            var rotTrack = new int[n]; var posTrack = new int[n];
            System.Array.Fill(rotTrack, -1); System.Array.Fill(posTrack, -1);
            for (int t = 0; t < ana.GetTrackCount(); t++)
            {
                string p = ana.TrackGetPath(t).ToString();
                int c = p.LastIndexOf(':');
                if (c < 0) continue;
                int b = sa.FindBone(p[(c + 1)..]);
                if (b < 0) continue;
                var tipo = ana.TrackGetType(t);
                if (tipo == Animation.TrackType.Rotation3D) rotTrack[b] = t;
                else if (tipo == Animation.TrackType.Position3D) posTrack[b] = t;
            }

            var dest = new Animation { Length = ana.Length };
            var novoRot = new int[n]; var novoPos = new int[n];
            for (int i = 0; i < n; i++)
            {
                novoRot[i] = novoPos[i] = -1;
                if (mapa[i] < 0) continue;
                string path = $"{caminhoSk}:{sb.GetBoneName(mapa[i])}";
                if (rotTrack[i] >= 0) { novoRot[i] = dest.AddTrack(Animation.TrackType.Rotation3D); dest.TrackSetPath(novoRot[i], path); }
                if (posTrack[i] >= 0) { novoPos[i] = dest.AddTrack(Animation.TrackType.Position3D); dest.TrackSetPath(novoPos[i], path); }
            }

            int quadros = Mathf.Max(1, Mathf.CeilToInt(ana.Length * Fps));
            for (int q = 0; q <= quadros; q++)
            {
                double tempo = System.Math.Min(ana.Length, q / Fps);
                // pose de origem (espaco do esqueleto)
                var gpA = new Transform3D[n];
                for (int i = 0; i < n; i++)
                {
                    var rep = sa.GetBoneRest(i);
                    var rot = rotTrack[i] >= 0 ? ana.RotationTrackInterpolate(rotTrack[i], tempo) : rep.Basis.GetRotationQuaternion();
                    var pos = posTrack[i] >= 0 ? ana.PositionTrackInterpolate(posTrack[i], tempo) : rep.Origin;
                    var loc = new Transform3D(new Basis(rot), pos);
                    int pai = sa.GetBoneParent(i);
                    gpA[i] = pai >= 0 ? gpA[pai] * loc : loc;
                }
                // destino: alvo global por osso
                var gB = new Transform3D[sb.GetBoneCount()];
                var tgt = new Transform3D[sb.GetBoneCount()];
                var tem = new bool[sb.GetBoneCount()];
                for (int i = 0; i < n; i++)
                {
                    int j = mapa[i];
                    if (j < 0) continue;
                    var restA = sa.GetBoneGlobalRest(i);
                    var restB = sb.GetBoneGlobalRest(j);
                    // delta de rotacao no mundo: (pose animada) * (repouso)^-1
                    var dMundo = qa.Rot(gpA[i]) * qa.Rot(restA).Inverse();
                    var rotAlvo = qb.Inv * dMundo * qb.Rot(restB);
                    var origemAlvo = restB.Origin;
                    if (posTrack[i] >= 0)
                    {
                        var dpos = basisA * (gpA[i].Origin - restA.Origin);
                        origemAlvo += qb.InvBasis * (dpos * escalaTransl);
                    }
                    tgt[j] = new Transform3D(new Basis(rotAlvo), origemAlvo);
                    tem[j] = true;
                }
                // alvo global de ossos sem equivalente = repouso
                for (int j = 0; j < sb.GetBoneCount(); j++) if (!tem[j]) tgt[j] = sb.GetBoneGlobalRest(j);
                for (int i = 0; i < n; i++)
                {
                    int j = mapa[i];
                    if (j < 0) continue;
                    int pai = sb.GetBoneParent(j);
                    var local = pai >= 0 ? tgt[pai].AffineInverse() * tgt[j] : tgt[j];
                    if (novoRot[i] >= 0) dest.RotationTrackInsertKey(novoRot[i], tempo, local.Basis.GetRotationQuaternion().Normalized());
                    if (novoPos[i] >= 0) dest.PositionTrackInsertKey(novoPos[i], tempo, local.Origin);
                }
                if (tempo >= ana.Length) break;
            }
            string curto = nome.ToString();
            int k = curto.LastIndexOf("AN_Arqueiro_", System.StringComparison.Ordinal);
            if (k >= 0) curto = curto[(k + "AN_Arqueiro_".Length)..];
            if (System.Array.IndexOf(Loops, curto) >= 0) dest.LoopMode = Animation.LoopModeEnum.Linear;
            lib.AddAnimation("AN_Arqueiro_" + curto, dest);
        }
        ap.AddAnimationLibrary("", lib);
        origem.QueueFree();
        return ap;
    }

    // ---- ajudantes: rotacao do mundo de cada no (soma das transformacoes dos ancestrais, sem o proprio esqueleto) ----
    readonly struct Mundo
    {
        public readonly Quaternion Q;
        public readonly Quaternion Inv;
        public readonly Basis InvBasis;
        public Mundo(Basis b) { Q = b.Orthonormalized().GetRotationQuaternion(); Inv = Q.Inverse(); InvBasis = new Basis(Inv); }
        public Quaternion Rot(Transform3D g) => Q * g.Basis.Orthonormalized().GetRotationQuaternion();
    }

    static Basis MundoBasis(Skeleton3D sk, Node raiz)
    {
        var b = Basis.Identity;
        for (Node n = sk; n != null; n = n.GetParent())
        {
            if (n is Node3D n3) b = n3.Transform.Basis * b;
            if (n == raiz) break;
        }
        return b;
    }
}
