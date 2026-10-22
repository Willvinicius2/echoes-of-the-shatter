"""Parte 4: musgo e sujeira em calotas baixas (cantos úmidos, pé da escada, juntas)."""
import esc_lib as L


def build(M):
    mu = M['musgo']; hw = L.W / 2
    r = L.rng(77)
    k = 0
    def m(c, rx, ry, rz):
        nonlocal k; k += 1
        L.calota(f"musgo{k}", c, rx, ry, rz, mu, 3000 + k)
    for i in range(min(L.N, 5)):                       # degraus de baixo, mais úmidos
        yf = L.YF - i * L.T; zt = (i + 1) * L.R
        for lado in (-1, 1):
            m((lado * (hw - r.uniform(.05, .25)), yf - L.T + r.uniform(.04, .12), zt - 0.004), r.uniform(.12, .26), r.uniform(.05, .1), 0.05)
        if i < 3:
            m((r.uniform(-hw * .7, hw * .7), yf + 0.02, zt - 0.03), r.uniform(.1, .2), 0.04, 0.045)   # beira do focinho
    for lado in (-1, 1):
        xc = lado * (hw + L.WT / 2)
        for j in range(4):                              # pé das paredes
            y = L.YF - j * L.T * 1.4 - 0.15
            m((lado * (hw + L.WT * r.uniform(.3, .85)), y, L.BAIXO + 0.09 + (L.linha(y) - L.R) * 0.2), r.uniform(.12, .22), r.uniform(.1, .2), 0.14)
        m((xc, L.YF + 0.3, L.BAIXO + 0.05), 0.25, 0.22, 0.13)                       # base do pilar
        m((xc + lado * 0.05, L.YF - 0.35, L.linha(L.YF - 0.35) + L.H0 + L.COPE), 0.1, 0.2, 0.05)  # capeamento
        m((lado * (hw - 0.04), L.YT - 0.4, L.N * L.R), 0.14, 0.2, 0.05)             # canto do patamar
    for j in range(3):                                  # avental
        m((r.uniform(-hw, hw), L.YF + r.uniform(.2, .55), 0.04), r.uniform(.15, .3), r.uniform(.1, .2), 0.05)
