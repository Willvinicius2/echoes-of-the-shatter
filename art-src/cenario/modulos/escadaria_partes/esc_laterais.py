"""Parte 2: paredes laterais em blocos acompanhando a rampa, capeamento e pilares de ponta."""
import esc_lib as L


def _wall_x(lado):
    hw = L.W / 2
    return (hw, hw + L.WT) if lado > 0 else (-hw - L.WT, -hw)


def build(M):
    esc = M['escura']; pedra = M['pedra']; par = M['parede']
    for lado in (-1, 1):
        x0, x1 = _wall_x(lado)
        s = 'L' if lado < 0 else 'R'
        for i in range(L.N):
            r = L.rng(500 + i * 7 + (lado > 0))
            ya, yb = L.YF - (i + 1) * L.T, L.YF - i * L.T
            zt = (i + 1) * L.R
            # fiadas de baixo: duas pedras empilhadas com altura da junta variável
            zs = L.BAIXO + (zt - L.BAIXO) * r.uniform(0.3, 0.7)
            xa0, xb0 = x0 + r.uniform(-.012, .012), x1 + r.uniform(-.012, .012)
            L.bloco(f"par{s}{i}_a0", xa0, xb0, ya + 0.005, yb - 0.005, L.BAIXO, zs - 0.004, par, 600 + i + 40 * (lado > 0),
                    sub=(1, 1, 1), jit=0.008, lascas=3, tam=0.09, bis=0.014, tira=('-z',))
            L.bloco(f"par{s}{i}_a", xa0 + r.uniform(-.01, .01), xb0 + r.uniform(-.01, .01), ya + 0.005 + r.uniform(0, .01), yb - 0.005 - r.uniform(0, .01), zs, zt,
                    par, 650 + i + 40 * (lado > 0), sub=(1, 1, 1), jit=0.008, lascas=3, tam=0.09, bis=0.014)
            # fiada de cima, com topo inclinado paralelo à rampa (perfil y,z)
            za, zb = L.linha(ya) + L.H0, L.linha(yb) + L.H0
            perfil = [(ya + 0.005, zt + 0.003), (yb - 0.005, zt + 0.003), (yb - 0.005, zb), (ya + 0.005, za)]
            L.prisma(f"par{s}{i}_b", x0 + r.uniform(-.015, .01) if lado < 0 else x0 + 0.0, x1 + (0 if lado < 0 else r.uniform(-.01, .015)),
                     perfil, par, 700 + i + 40 * (lado > 0), jit=0.006, lascas=2, tam=0.07, bis=0.013)
        # parede do patamar (reta, mais alta, retém o terreno)
        zt = L.linha(L.YT) + L.H0
        L.bloco(f"par{s}_pat", x0, x1, L.YT - L.LAND, L.YT - 0.005, L.BAIXO, zt, par, 800 + (lado > 0),
                sub=(1, 3, 2), jit=0.008, lascas=4, tam=0.1, bis=0.015, tira=('-z',))
        # capeamento: lajes inclinadas, uma por dois degraus, com juntas e lascas
        for k in range(0, L.N, 2):
            r = L.rng(900 + k + 9 * (lado > 0))
            ya = L.YF - min(k + 2, L.N) * L.T; yb = L.YF - k * L.T
            base_a, base_b = L.linha(ya) + L.H0, L.linha(yb) + L.H0
            perfil = [(ya + 0.01, base_a), (yb - 0.01, base_b), (yb - 0.01, base_b + L.COPE), (ya + 0.01, base_a + L.COPE)]
            L.prisma(f"cap{s}{k}", x0 - 0.035, x1 + 0.035, perfil, pedra, 950 + k + 9 * (lado > 0), jit=0.004, lascas=2, tam=0.05, bis=0.012)
        L.bloco(f"cap{s}_pat", x0 - 0.035, x1 + 0.035, L.YT - L.LAND + 0.01, L.YT - 0.005, zt, zt + L.COPE, pedra, 980 + (lado > 0),
                sub=(1, 2, 0), jit=0.004, lascas=3, tam=0.06, bis=0.012, tira=('-z',))
        # pilares de ponta: base, fuste, cintas, capitel em pirâmide
        for nome, yc, zb in (("pe", L.YF + 0.24, L.BAIXO), ("alto", L.YT - L.LAND + 0.24, zt + L.COPE)):
            xc = (x0 + x1) / 2
            ph = L.POST / 2
            topo_fuste = (L.linha(L.YF) + L.H0 + L.COPE + L.RAIL_H + 0.28) if nome == "pe" else zb + L.RAIL_H + 0.56
            hh = L.rng(1100 + (lado > 0) + 3 * (nome == "alto"))
            L.bloco(f"pil{s}_{nome}_base", xc - ph - 0.05, xc + ph + 0.05, yc - ph - 0.05, yc + ph + 0.05, zb, zb + 0.34 if nome == "pe" else zb + 0.06,
                    esc, 1200 + (lado > 0), sub=(1, 1, 1), jit=0.007, lascas=3, tam=0.09, bis=0.018, tira=('-z',) if nome == "alto" else ())
            z0 = zb + 0.34 if nome == "pe" else zb + 0.06
            L.bloco(f"pil{s}_{nome}_fuste", xc - ph + 0.03, xc + ph - 0.03, yc - ph + 0.03, yc + ph - 0.03, z0, topo_fuste,
                    esc, 1210 + (lado > 0) + 3 * (nome == "alto"), sub=(1, 1, 3), jit=0.006, lascas=2, tam=0.07, bis=0.014, tira=('-z',))
            for fz in (z0 + 0.12, topo_fuste - 0.14):   # cintas salientes
                L.bloco(f"pil{s}_{nome}_cinta{fz:.2f}", xc - ph - 0.015, xc + ph + 0.015, yc - ph - 0.015, yc + ph + 0.015, fz, fz + 0.075,
                        pedra, 1230 + int(fz * 10), lascas=1, tam=0.04, bis=0.012)
            L.bloco(f"pil{s}_{nome}_capa", xc - ph - 0.04, xc + ph + 0.04, yc - ph - 0.04, yc + ph + 0.04, topo_fuste, topo_fuste + 0.085,
                    pedra, 1250 + (lado > 0), lascas=2, tam=0.05, bis=0.012)
            L.bloco(f"pil{s}_{nome}_ponta", xc - ph * 0.62, xc + ph * 0.62, yc - ph * 0.62, yc + ph * 0.62, topo_fuste + 0.085, topo_fuste + 0.22,
                    pedra, 1260 + (lado > 0), lascas=2, tam=0.04, bis=0.014)
            # entulho junto à base do pilar do pé
            if nome == "pe":
                for q in range(3):
                    hr = L.rng(1300 + q + 5 * (lado > 0))
                    ex = xc + hr.uniform(-.25, .25) + lado * 0.1; ey = yc + hr.uniform(.3, .55)
                    L.bloco(f"entulho{s}{q}", ex - hr.uniform(.06, .12), ex + hr.uniform(.06, .12), ey - hr.uniform(.05, .1), ey + hr.uniform(.05, .1), L.BAIXO, hr.uniform(.05, .14),
                            esc, 1300 + q, lascas=3, tam=0.04, bis=0.01, jit=0.01, tira=('-z',))
