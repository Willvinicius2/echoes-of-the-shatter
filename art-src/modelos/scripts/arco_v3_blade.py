"""Arco v3, etapa 2b (venv do TripoSG, so CPU/numpy): constroi as DUAS lamina curvas das pontas.
A primeira secao de cada lamina e a propria borda do corte da haste (loops de cut.json, com os pontos medios das arestas
inseridos: sem fresta). Depois a secao vira um losango (aresta viva dos dois lados + nervura central) que afina ate a ponta
seguindo um arco que continua a curvatura do membro. Grava blades.npz (V, F, UV, por ponta) e blade_info.json (ancoras da corda).
Uso: python arco_v3_blade.py"""
import os, json, math, sys
import numpy as np
W3 = r"D:\openclaude\_trabalho-claude\modelos3d\arqueiro_dark\arco\work3"
cut = json.load(open(os.path.join(W3, "cut.json")))
P = dict(L=0.23, end_deg=-18.0, pw=1.6, grow=0.35, wp=1.3, bt=1.4, thick=1.15)
for a in sys.argv[1:]:
    k, v = a.split("="); P[k] = float(v)
TS = [0.0, 0.12, 0.26, 0.41, 0.56, 0.70, 0.83]
MS = [0.0, 0.6, 1.0, 1.0, 1.0, 1.0, 1.0]
UV_V0, UV_V1 = 0.88, 0.995

def centerline(c, th0, L, t):
    """integra o arco: angulo (a partir da vertical, + = para +X) cai de th0 ate end_deg; devolve centro e normal externa (+X)."""
    tt = np.linspace(0, 1, 401); e = math.radians(P["end_deg"])
    th = th0 + (e - th0) * tt ** P["pw"]
    ds = L / 400
    x = c[0] + np.concatenate([[0], np.cumsum(np.sin(th[:-1]) * ds)])
    z = c[1] + np.concatenate([[0], np.cumsum(np.cos(th[:-1]) * ds)])
    i = np.clip(np.round(np.asarray(t) * 400).astype(int), 0, 400)
    return np.stack([x[i], z[i]], -1), th[i]

blades = {}; info = {}
for sg_s, d in cut.items():
    sg = int(sg_s); th0 = d["theta"]; T0 = np.array(d["T"]); N0 = np.array([T0[1], -T0[0]])
    Lp = np.array(d["loop"]).copy(); Lp[:, 2] *= sg                       # espaco "topo": z' = sg * z
    c = np.array([Lp[:, 0].mean(), Lp[:, 2].mean()]); cy = Lp[:, 1].mean()
    rel = np.stack([Lp[:, 0] - c[0], Lp[:, 2] - c[1]], -1)
    a = rel @ N0; b = Lp[:, 1] - cy; dd = rel @ T0
    A0, B0 = np.abs(a).max(), np.abs(b).max()
    ang = np.arctan2(b / B0, a / A0); o = np.argsort(ang)
    a, b, dd, ang = a[o], b[o], dd[o], ang[o]
    # pontos medios nas arestas do loop (continuam exatamente sobre a borda)
    a2 = []; b2 = []; d2 = []
    for i in range(len(a)):
        j = (i + 1) % len(a)
        a2 += [a[i], (a[i] + a[j]) / 2]; b2 += [b[i], (b[i] + b[j]) / 2]; d2 += [dd[i], (dd[i] + dd[j]) / 2]
    a, b, dd = np.array(a2), np.array(b2), np.array(d2); n = len(a)
    ang = np.arctan2(b / B0, a / A0)
    ic = []
    for tgt in (0, math.pi / 2, math.pi, -math.pi / 2):
        dif = np.abs(np.angle(np.exp(1j * (ang - tgt)))); dif[ic] = 9; ic.append(int(dif.argmin()))
    # reordena para comecar na quina externa (psi=0) e ir em sentido anti-horario
    r0 = ic[0]; idx = [(r0 + k) % n for k in range(n)]
    a, b, dd = a[idx], b[idx], dd[idx]
    ic = [(i - r0) % n for i in ic]
    assert ic == sorted(ic), ic
    psi = np.zeros(n)
    bounds = ic + [n]
    for jq in range(4):
        i0, i1 = bounds[jq], bounds[jq + 1]
        for k in range(i0, i1): psi[k] = (jq + (k - i0) / (i1 - i0)) * math.pi / 2
    rr = 1.0 / (np.abs(np.cos(psi)) + np.abs(np.sin(psi)))
    qa, qb = rr * np.cos(psi), rr * np.sin(psi)
    ts = np.array(TS + [1.0]); Cc, th = centerline(c, th0, P["L"], ts)
    V3 = []; UV = []; rings = []
    nr = len(TS)
    for j in range(nr):
        t = ts[j]; Aj = A0 * (1 + P["grow"] * t) * (1 - t ** P["wp"]); Bj = B0 * P["thick"] * (1 - t ** P["bt"])
        if j == 0: Aj, Bj = A0, B0
        thj = th[j]; Nj = np.array([math.cos(thj), -math.sin(thj)]); Tj = np.array([math.sin(thj), math.cos(thj)])
        m = MS[j]
        aa = (1 - m) * a * (Aj / A0) + m * Aj * qa
        bb = (1 - m) * b * (Bj / B0) + m * Bj * qb
        dj = (1 - m) * dd if j == 0 else 0 * dd
        xz = Cc[j][None, :] + aa[:, None] * Nj[None, :] + dj[:, None] * Tj[None, :]
        ring = np.stack([xz[:, 0], cy + bb, xz[:, 1]], -1)
        rings.append(ring)
    # vertices: n+1 por anel (quina externa duplicada para a costura de UV)
    for j in range(nr):
        r = np.vstack([rings[j], rings[j][:1]])
        for k in range(n + 1):
            V3.append(r[k]); UV.append((ts[j] * 0.5 * 0.97 + 0.015, UV_V0 + (UV_V1 - UV_V0) * (k / n)))
    F = []; UVx = list(UV)
    W = n + 1
    for j in range(nr - 1):
        for k in range(n):
            p0, p1, p2, p3 = j * W + k, j * W + k + 1, (j + 1) * W + k + 1, (j + 1) * W + k
            F += [(p0, p1, p2), (p0, p2, p3)]
    tip = np.array([Cc[-1][0], cy, Cc[-1][1]]) + np.array([math.sin(th[-1]), 0, math.cos(th[-1])]) * 0.0
    for k in range(n):
        base = len(V3)
        V3.append(tip); UVx.append((0.5, UV_V0 + (UV_V1 - UV_V0) * ((k + 0.5) / n)))
        F.append(((nr - 1) * W + k, (nr - 1) * W + k + 1, base))
    V3 = np.array(V3); F = np.array(F)
    # orientacao: normais para fora (comparar com o centro do anel mais proximo)
    cen = V3[F].mean(1); fn = np.cross(V3[F[:, 1]] - V3[F[:, 0]], V3[F[:, 2]] - V3[F[:, 0]])
    ctr = np.array([[Cc[min(int(f[0] // W), nr - 1)][0], cy, Cc[min(int(f[0] // W), nr - 1)][1]] for f in F])
    if (np.einsum("ij,ij->i", fn, cen - ctr) < 0).sum() > len(F) / 2: F = F[:, ::-1]
    if P.get("flip", 0): F = F[:, ::-1]
    # volta ao espaco real (z = sg * z'); espelhar inverte a orientacao
    V3[:, 2] *= sg
    if sg < 0: F = F[:, ::-1]
    UVa = np.array(UVx)
    if sg < 0: UVa[:, 0] += 0.5
    blades[sg] = (V3, F, UVa)
    # ancora da corda: ponto da aresta externa com maior x (varre o comprimento)
    tf = np.linspace(0.05, 0.9, 200); Cf, thf = centerline(c, th0, P["L"], tf)
    Af = A0 * (1 + P["grow"] * tf) * (1 - tf ** P["wp"])
    xo = Cf[:, 0] + np.cos(thf) * Af; zo = Cf[:, 1] - np.sin(thf) * Af
    k = int(xo.argmax()); anc = np.array([xo[k] - 0.0015, 0.0, sg * zo[k]])
    info[sg] = dict(anchor=anc.tolist(), t=float(tf[k]), A0=float(A0), B0=float(B0), n=n,
                    tip=[float(tip[0]), float(tip[1]), float(sg * tip[2])], tris=int(len(F)))
    print("lamina", sg, "n", n, "tris", len(F), "ancora", anc.round(4), "t", round(tf[k], 2), "ponta", np.round([tip[0], sg * tip[2]], 3), "A0 B0", round(A0, 4), round(B0, 4))
np.savez(os.path.join(W3, "blades.npz"), **{f"V{s}": blades[s][0] for s in blades}, **{f"F{s}": blades[s][1] for s in blades},
         **{f"UV{s}": blades[s][2] for s in blades})
json.dump(info, open(os.path.join(W3, "blade_info.json"), "w"), indent=1)
