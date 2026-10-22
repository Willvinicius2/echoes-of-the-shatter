"""Parte 3: corrimão de ferro forjado: barra martelada, balaústres torcidos, barra baixa, cintas, ponteiras e volutas."""
import math
import esc_lib as L


def _zrail(y):
    return L.linha(min(y, L.YF)) + L.H0 + L.COPE + L.RAIL_H


def build(M):
    fe = M['ferro']; fx = M['ferro_escuro']
    hw = L.W / 2
    for lado in (-1, 1):
        s = 'L' if lado < 0 else 'R'
        xc = lado * (hw + L.WT / 2)
        y_pe = L.YF + 0.24; y_alto = L.YT - L.LAND + 0.24
        n = 30
        ys = [y_pe + (y_alto - y_pe) * k / n for k in range(n + 1)]
        zs = [_zrail(y) for y in ys]
        zs = [sum(zs[max(0, k - 2):k + 3]) / len(zs[max(0, k - 2):k + 3]) for k in range(n + 1)]   # curva suave nas quinas
        pts = [(xc, y, z) for y, z in zip(ys, zs)]
        L.tubo(f"corrimao{s}", pts, 0.04, fe, lados=12, jit=0.004, seed=11 + (lado > 0))
        # barra baixa (estrutura) seguindo a rampa, sempre dentro dos pilares
        zb = lambda y: L.linha(min(y, L.YF)) + L.H0 + L.COPE + 0.2
        pb = [(xc, y, zb(y)) for y in ys]
        L.tubo(f"barra_baixa{s}", pb, 0.017, fx, lados=4, quadrado=True, seed=21 + (lado > 0))
        # balaústres torcidos: um por degrau + dois no patamar
        yb = [L.YF - (i + 0.5) * L.T for i in range(L.N)] + [L.YT - 0.3, L.YT - 0.65]
        for i, y in enumerate(yb):
            r = L.rng(2000 + i + 20 * (lado > 0))
            z0 = L.linha(y) + L.H0 + L.COPE - 0.01
            z1 = zs[min(range(n + 1), key=lambda k: abs(ys[k] - y))] - 0.02
            L.bloco(f"colar{s}{i}", xc - 0.05, xc + 0.05, y - 0.05, y + 0.05, z0, z0 + 0.07, fx, 2100 + i, lascas=0, bis=0.012, jit=0.003)
            ra = [0.019 + 0.017 * math.exp(-((k / 8 - c) / 0.07) ** 2) for k in range(9) for c in (0.5,)]   # barra redonda com nó no meio
            L.tubo(f"bal{s}{i}", [(xc, y, z0 + 0.07 + (z1 - z0 - 0.07) * k / 8) for k in range(9)], ra, fe, lados=6, seed=2200 + i)
            L.bloco(f"cinta{s}{i}", xc - 0.04, xc + 0.04, y - 0.04, y + 0.04, z1 - 0.045, z1 + 0.02, fx, 2300 + i, lascas=0, bis=0.008, jit=0.002)
        # cintas de ferro e ponteiras nos pilares; volutas na face voltada para a escada
        for nome, yc, zb0, ztop in (("pe", y_pe, L.BAIXO, L.linha(L.YF) + L.H0 + L.COPE + L.RAIL_H + 0.28),
                                    ("alto", y_alto, L.linha(L.YT) + L.H0 + L.COPE, L.linha(L.YT) + L.H0 + L.COPE + L.RAIL_H + 0.56)):
            ph = L.POST / 2
            zr = _zrail(yc)
            for dz in (-0.1, 0.1):
                L.bloco(f"cintaf{s}{nome}{dz}", xc - ph - 0.0, xc + ph + 0.0, yc - ph - 0.0, yc + ph + 0.0, zr + dz - 0.03, zr + dz + 0.03,
                        fx, 2400 + int(dz * 100) + 7 * (lado > 0), lascas=0, bis=0.008, jit=0.002)
            ztc = ztop + 0.22
            L.tubo(f"ponteira{s}{nome}", [(xc, yc, ztc + 0.02 * k) for k in range(1)] + [(xc, yc, ztc + 0.15), (xc, yc, ztc + 0.30)],
                   [0.05, 0.038, 0.002], fe, lados=4, quadrado=True, seed=2500)
            xi = xc - lado * (ph + 0.012)
            zc = zr - 0.34
            sp = [(xi, yc + (0.1 - 0.085 * t / 30) * math.cos(t / 30 * 2.7 * math.pi) * 1, zc + (0.1 - 0.085 * t / 30) * math.sin(t / 30 * 2.7 * math.pi))
                  for t in range(31)]
            L.tubo(f"voluta{s}{nome}", sp, 0.012, fe, lados=6, jit=0.04, seed=2600)
