"""Parte 1: degraus gastos e lascados, avental no pé e patamar no alto."""
import esc_lib as L


def _lajes(i, x_ini, x_fim, r):
    """Divide a largura em 2 ou 3 lajes de tamanhos diferentes (juntas deslocadas de um degrau para outro)."""
    n = (4 if i % 2 == 0 else 3) if L.W > 3 else (3 if (i % 2 == 0 and L.W > 1.6) else 2)
    cortes = sorted(r.uniform(0.28, 0.72) if n == 2 else r.uniform(0.15, 0.85) for _ in range(n - 1))
    if n > 2 and min(b - a for a, b in zip(cortes, cortes[1:])) < 0.18: cortes = [(k + 1) / n + r.uniform(-.04, .04) for k in range(n - 1)]
    pts = [x_ini] + [x_ini + c * (x_fim - x_ini) for c in cortes] + [x_fim]
    return list(zip(pts[:-1], pts[1:]))


def build(M):
    pedra = M['pedra']; esc = M['escura']
    hw = L.W / 2
    for i in range(L.N):
        r = L.rng(100 + i)
        yf = L.YF - i * L.T
        topo = (i + 1) * L.R + r.uniform(-0.006, 0.006)
        for j, (xa, xb) in enumerate(_lajes(i, -hw - 0.02, hw + 0.02, r)):
            gap = 0.003
            L.bloco(f"deg{i}_{j}", xa + gap, xb - gap, yf - L.T, yf + 0.035, L.BAIXO, topo + r.uniform(-0.007, 0.007),
                    pedra, 1000 + i * 10 + j, sub=(2, 2, 0), jit=0.007, lascas=2, tam=0.07, bis=0.014,
                    tira=('-z', '-y', '-x', '+x'), desgaste=0.016 + 0.004 * r.random(), gira=r.uniform(-0.012, 0.012))
    # avental de pedra diante do primeiro degrau (nível do piso inferior), lajes maiores e irregulares
    r = L.rng(7)
    xs = [-hw - L.WT, -hw * 0.25 + r.uniform(-.1, .1), hw * 0.5 + r.uniform(-.1, .1), hw + L.WT]
    for j in range(3):
        L.bloco(f"avental{j}", xs[j] + 0.006, xs[j + 1] - 0.006, L.YF + 0.03, L.YF + 0.62, L.BAIXO, 0.045 + r.uniform(-.008, .008),
                M["parede"], 300 + j, sub=(2, 2, 0), jit=0.008, lascas=3, tam=0.09, bis=0.016, tira=('-z', '-y'), desgaste=0.012, gira=r.uniform(-.03, .03))
    # patamar: duas lajes grandes
    ztop = L.N * L.R
    for j, (xa, xb) in enumerate(((-hw - 0.02, -hw / 3), (-hw / 3, hw / 2.5), (hw / 2.5, hw + 0.02))):
        L.bloco(f"patamar{j}", xa + 0.006, xb - 0.006, L.YT - L.LAND, L.YT + 0.035, L.BAIXO, ztop + (0.004 if j == 1 else -0.004),
                pedra, 400 + j, sub=(2, 3, 0), jit=0.007, lascas=3, tam=0.09, bis=0.014, tira=('-z', '-y', '-x', '+x'),
                desgaste=0.012, gira=(-0.01, 0.015, -0.008)[j])
    # contenção atrás do patamar (face de trás visível de fora): três fiadas de blocos grandes
    par = M['parede']; r = L.rng(55)
    xs = [-hw - L.WT, -hw / 2 + r.uniform(-.2, .2), hw / 3 + r.uniform(-.2, .2), hw + L.WT]
    zs = [L.BAIXO, ztop * 0.38, ztop * 0.7, ztop]
    for k in range(3):
        for j in range(3):
            jj = (j + k) % 3
            L.bloco(f"conten{k}{j}", xs[j] + 0.004, xs[j + 1] - 0.004, L.YT - L.LAND - 0.34, L.YT - L.LAND + 0.01, zs[k] + 0.004, zs[k + 1] - 0.004,
                    par, 500 + k * 3 + j, sub=(1, 1, 1), jit=0.01, lascas=3, tam=0.1, bis=0.016, tira=('-z',))
