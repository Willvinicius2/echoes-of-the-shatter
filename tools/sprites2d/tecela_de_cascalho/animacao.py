"""Poses e animações das aranhas da Ponte do Sino (idle 6, run 8, attack 8, hit 3, death 8 quadros; 5 direções).

Uma `Aranha(variante)` guarda o modelo (aranha.py) e devolve o estado de cada quadro: dict(pose=juntas, t=deslocamento da raiz no
referencial da aranha, tilt=(rx, rz) do corpo todo, olho, apagar (fio de teia), fx). O quadro desenhado sai de `quadro(estado, yaw)`.
As pernas andam em dois grupos alternados (L0, R1, L2, R3 e os outros quatro), como uma aranha de verdade.
"""
import math
import zlib
import numpy as np
import render as R
import aranha as G

YAW = {'S': 0.0, 'SE': 45.0, 'E': 90.0, 'NE': 135.0, 'N': 180.0}
ORDEM = ['S', 'SE', 'E', 'NE', 'N']
I3 = np.eye(3)


def suave(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


class Aranha:
    def __init__(self, variante):
        self.variante = variante
        self.cfg = G.CONFIG[variante]
        self.partes, self.juntas, self.pernas = G.construir(variante)
        self.anims = {
            'idle': (self.idle, 6, 8, True),
            'run': (self.run, 8, 12, True),
            'attack': (self.ataque, 8, 12, False),
            'hit': (self.ferido, 3, 12, False),
            'death': (self.morte, 8, 10, False),
        }

    # ---------------- pernas ----------------
    def perna(self, pose, nome, giro=0.0, erguer=0.0, joelho=0.0):
        """`giro`: graus para a frente (+) no chão; `erguer`: a perna inteira sobe pelo quadril; `joelho`: a tíbia abre (+) ou dobra para dentro (-)."""
        p = self.pernas[nome]
        pose['q' + nome] = R.rot_y(-p['lado'] * giro) @ R.eixo(p['eixo'], erguer)
        if joelho:
            pose['j' + nome] = R.eixo(p['eixo'], joelho)

    def compensar(self, dy):
        """Graus que o quadril precisa girar para o pé continuar no chão quando o corpo desce `dy` metros (negativo = desce)."""
        return {n: math.degrees(-dy / p['alcance']) for n, p in self.pernas.items()}

    def estado(self, pose, t=(0, 0, 0), tilt=(0, 0), olho=0, apagar=None, fx=None):
        return dict(pose=pose, t=t, tilt=tilt, olho=olho, apagar=apagar, fx=fx)

    @staticmethod
    def grupo_a(nome):
        return (nome[0] == 'L') == (int(nome[1]) % 2 == 0)

    # ---------------- idle ----------------
    def idle(self, f, n=6):
        p = 2 * math.pi * f / n
        s = math.sin(p)
        dy = 0.045 * s
        comp = self.compensar(dy)
        pose = {'abd': (2.5 * s, 0, 0), 'cabeca': (-1.5 * s, 0, 0), 'presa': (6 + 6 * math.sin(2 * p), 0, 0)}
        for nome in self.pernas:
            tap = 0.0
            if nome == 'R0' and f in (3, 4):      # a pata da frente tateia
                tap = 14.0 if f == 3 else 7.0
            self.perna(pose, nome, erguer=comp[nome] + tap, joelho=-tap * 0.6)
        return self.estado(pose, t=(0, dy, 0), olho=1 if f == 5 else 0)

    # ---------------- run ----------------
    def run(self, f, n=8):
        p = 2 * math.pi * f / n
        pose = {'abd': (2.0 * math.cos(2 * p), 3.5 * math.sin(p), 0), 'presa': (8, 0, 0)}
        amp = 15.0 if self.variante == 'tecela' else 19.0
        for nome in self.pernas:
            ph = p + (0.0 if self.grupo_a(nome) else math.pi) + 0.25 * int(nome[1])
            sobe = max(0.0, math.cos(ph))
            self.perna(pose, nome, giro=amp * math.sin(ph), erguer=17.0 * sobe ** 1.2, joelho=-9.0 * sobe)
        return self.estado(pose, t=(0, 0.035 * math.cos(2 * p), 0), tilt=(0, 2.0 * math.sin(p)))

    # ---------------- ataque: empina, ergue as patas da frente e crava as presas (contato no quadro 5) ----------------
    ATAQUE = [
        # z e y da raiz, inclinação do corpo (rx: negativo empina), patas da frente (erguer, joelho, giro), presas, abdômen
        dict(z=-0.04, y=0.00, rx=-3, er=10, jo=-6, gi=4, pr=10, ab=-3),
        dict(z=-0.14, y=0.05, rx=-10, er=34, jo=-22, gi=10, pr=22, ab=-8),
        dict(z=-0.24, y=0.10, rx=-16, er=58, jo=-34, gi=16, pr=34, ab=-12),
        dict(z=-0.28, y=0.12, rx=-18, er=66, jo=-40, gi=18, pr=38, ab=-13),
        dict(z=0.10, y=0.02, rx=-2, er=30, jo=-4, gi=24, pr=30, ab=4),
        dict(z=0.26, y=-0.12, rx=11, er=-4, jo=0, gi=12, pr=-6, ab=10),
        dict(z=0.25, y=-0.13, rx=12, er=-4, jo=0, gi=11, pr=-4, ab=8),
        dict(z=0.16, y=-0.05, rx=5, er=2, jo=0, gi=12, pr=6, ab=3),
    ]

    def ataque(self, f, n=8):
        a = self.ATAQUE[f]
        comp = self.compensar(a['y'])
        pose = {'abd': (a['ab'], 0, 0), 'presa': (a['pr'], 0, 0), 'cabeca': (-a['rx'] * 0.3, 0, 0)}
        for nome, p in self.pernas.items():
            i = p['i']
            if i == 0:
                self.perna(pose, nome, giro=a['gi'], erguer=a['er'], joelho=a['jo'])
            else:
                # as outras seis seguram o chão: o corpo vai e vem, os pés ficam (giro contrário ao avanço)
                giro = -math.degrees(a['z'] / p['alcance']) * (0.9 if i < 3 else 0.6) * abs(p['h'][0])
                self.perna(pose, nome, giro=giro, erguer=comp[nome] + (a['rx'] * 0.35 if i == 1 else -a['rx'] * 0.25 if i == 3 else 0.0))
        fx = ('impacto', f) if f >= 5 else None
        return self.estado(pose, t=(0, a['y'], a['z']), tilt=(a['rx'], 0), fx=fx)

    # ---------------- ferido ----------------
    HIT = [dict(z=-0.14, y=-0.06, rx=-7, ab=8, ab_y=6), dict(z=-0.22, y=-0.12, rx=-11, ab=13, ab_y=-5), dict(z=-0.09, y=-0.04, rx=-4, ab=5, ab_y=0)]

    def ferido(self, f, n=3):
        a = self.HIT[f]
        comp = self.compensar(a['y'])
        pose = {'abd': (a['ab'], a['ab_y'], 0), 'presa': (20, 0, 0), 'cabeca': (6, 0, 0)}
        for nome, p in self.pernas.items():
            abre = (5 + 3 * f) * (1 if p['i'] < 2 else -1)
            self.perna(pose, nome, giro=abre + math.degrees(-a['z'] / p['alcance']) * 0.6, erguer=comp[nome] + (9 if p['i'] == 0 else 0), joelho=4)
        return self.estado(pose, t=(0, a['y'], a['z']), tilt=(a['rx'], 0), olho=1)

    # ---------------- morte: cai de barriga, as pernas se encolhem e o brilho apaga ----------------
    def morte(self, f, n=8):
        w = suave(f / 5.0)
        treme = math.sin(f * 2.4) * (1 - w) * 5.0
        desce = -0.62 * w if self.variante == 'tecela' else -0.50 * w
        pose = {'abd': (-16 * w, 7 * w + treme * 0.4, -10 * w), 'presa': (30 * (1 - w) + 4, 0, 0), 'cabeca': (12 * w, 0, 0)}
        for nome, p in self.pernas.items():
            atraso = suave((f - 0.6 * p['i']) / 5.0)
            enc = suave((f - 2.0 - 0.4 * p['i']) / 4.5)
            lado = 1 if self.grupo_a(nome) else -1
            self.perna(pose, nome, giro=(10 * (1 if p['i'] < 2 else -1) + treme * lado) * atraso,
                       erguer=math.degrees(-desce / p['alcance']) * 0.9 + 26 * enc + treme * lado * 0.5,
                       joelho=-58 * enc)
        olho = 0 if f == 0 else (1 if f <= 2 else (2 if f <= 4 else 3))
        apagar = 0.0 if f < 3 else (0.5 if f < 6 else 1.0)
        return self.estado(pose, t=(0, desce, -0.06 * w), tilt=(4 * w, 9 * w), olho=olho, apagar=apagar)

    # ---------------- quadro ----------------
    def quadro(self, est, yaw):
        R.configurar(self.cfg['quadro'], self.cfg['pivo'], self.cfg['esc'])
        Ry = R.rot_y(yaw)
        rx, rz = est['tilt']
        if rx or rz:
            # a inclinação gira em torno do centro do corpo (não dos pés): empinar não afunda as patas de trás no chão
            c = np.array(self.juntas['corpo'])
            Rt = R.euler(rx, 0, rz)
            desloc = c - Rt @ c
        else:
            Rt, desloc = I3, np.zeros(3)
        raiz_R = Ry @ Rt
        t = Ry @ (np.array(est['t'], float) + desloc)
        pose = dict(est['pose'])
        if rx or rz:
            # as pernas desfazem a inclinação do corpo para os pés ficarem onde estavam
            Rinv = Rt.T
            for nome in self.pernas:
                q = self.juntas['q' + nome]
                atual = pose.get('q' + nome, I3)
                atual = atual if isinstance(atual, np.ndarray) else R.euler(*atual)
                pose['q' + nome] = Rinv @ atual
        cena = R.montar_cena(self.partes, self.juntas, pose, raiz_R, t)
        img = R.sombrear(cena, olho=est['olho'], cinza=est['apagar'])
        fx = est.get('fx')
        if fx and fx[0] == 'impacto':
            f = fx[1]
            seed = zlib.crc32(('%s-%d-%d' % (self.variante, f, int(yaw))).encode())
            d = {c['nome']: c['cen'] for c in cena}
            pts = []
            for nome in ('garraL0', 'garraR0'):
                c = d[nome].copy()
                c[1] = 0.0
                pts.append(_px(c))
            k = self.cfg['esc'] / 42.0
            if f == 5:
                _poeira(img, pts, 4.6 * k, 6 * k, 3, seed)
            elif f == 6:
                _poeira(img, pts, 6.4 * k, 11 * k, 4, seed)
            elif f == 7:
                _poeira(img, pts, 5.2 * k, 14 * k, 3, seed, claro=1)
        return img


# ---------------- poeira do golpe (2D, só nos pixels vazios; tons do fio de teia: pó claro e frio) ----------------
def _px(p):
    return (R.PIVO[0] + float(p @ R.RX) * R.ESC, R.PIVO[1] - float(p @ R.U) * R.ESC)


def _bolha(img, cx, cy, r, rng, claro=0):
    H, W = img.shape[:2]
    r = max(r, 1.2)
    cy = min(cy, H - 4 - r * 1.35)
    cx = min(max(cx, 4 + r * 1.3), W - 4 - r * 1.3)
    ys, xs = np.mgrid[0:H, 0:W]
    tons = [R.PALETA_NP[i] for i in R.IDX['fio']]
    livre = img[..., 3] == 0
    lobos = [(0.0, 0.0, 1.0)]
    for _ in range(2):
        a = rng.uniform(0, 2 * math.pi)
        lobos.append((math.cos(a) * r * 0.55, math.sin(a) * r * 0.35, rng.uniform(0.55, 0.8)))
    corpo = np.zeros((H, W), bool)
    luz = np.zeros((H, W), bool)
    for dx, dy, k in lobos:
        corpo |= ((xs + 0.5 - cx - dx) ** 2 + ((ys + 0.5 - cy - dy) * 1.15) ** 2) <= (r * k) ** 2
        luz |= ((xs + 0.5 - cx - dx + r * 0.28) ** 2 + ((ys + 0.5 - cy - dy + r * 0.3) * 1.15) ** 2) <= (r * k * 0.62) ** 2
    m = corpo & livre
    img[m, :3] = tons[min(1 + claro, 2)]
    img[m, 3] = 255
    ml = luz & corpo & livre
    img[ml, :3] = tons[min(claro, 2)]
    return img


def _poeira(img, pontos, tam, espalha, n, seed, claro=0):
    rng = np.random.RandomState(seed)
    for (cx, cy) in pontos:
        for _ in range(n):
            a = rng.uniform(0, 2 * math.pi)
            d = rng.uniform(0.3, 1.0) * espalha
            _bolha(img, cx + math.cos(a) * d, cy + math.sin(a) * d * 0.55, tam * rng.uniform(0.7, 1.15), rng, claro)
    return img


_CACHE = {}


def aranha(variante):
    if variante not in _CACHE:
        _CACHE[variante] = Aranha(variante)
    return _CACHE[variante]
