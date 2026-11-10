#!/usr/bin/env python3
"""Peças de pixel art da HUD desenhadas por código (arte original): aro e vidro do globo de vida e de recurso.

O aro é de ferro com fio de bronze, quatro cravos e luz vinda do alto à esquerda; o vidro traz o reflexo e a
sombra interna em pixels translúcidos. O líquido é desenhado pelo jogo por baixo (hud_arte_2d.gd, globo_pixel).
Desenho em 50 px (raio do vidro 20,5) e saída em 2x, para ficar na mesma grade de pixels do mundo em 720p.

Uso: python3 tools/arte/gerar_hud_pixel.py
"""
import math
from pathlib import Path

from PIL import Image

DESTINO = Path(__file__).resolve().parents[2] / "godot" / "art2d" / "ui"
N = 50
R_VIDRO = 20.5
PRETO = (9, 8, 12, 255)
FERRO = [(34, 32, 40, 255), (62, 58, 70, 255), (104, 98, 112, 255), (150, 144, 160, 255)]   # sombra .. luz
BRONZE = [(92, 68, 38, 255), (150, 116, 62, 255), (214, 178, 104, 255)]


def luz(dx, dy, d):
    """-1 (sombra, embaixo à direita) .. 1 (luz, no alto à esquerda)."""
    return (-dx - dy) / (d * math.sqrt(2)) if d > 0 else 0.0


def globo():
    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    c = (N - 1) / 2
    for y in range(N):
        for x in range(N):
            dx, dy = x - c, y - c
            d = math.hypot(dx, dy)
            k = luz(dx, dy, d)
            ang = math.degrees(math.atan2(dy, dx)) % 360
            if d > 24.6:
                continue
            if d > 23.6:
                p = PRETO
            elif d > 21.6:
                p = FERRO[3] if k > 0.75 else FERRO[2] if k > 0.2 else FERRO[1] if k > -0.5 else FERRO[0]
            elif d > R_VIDRO:
                p = BRONZE[2] if k > 0.5 else BRONZE[1] if k > -0.4 else BRONZE[0]
            else:   # vidro: só brilho e sombra translúcidos sobre o líquido
                p = (0, 0, 0, 0)
                if d > 19.4:
                    p = (0, 0, 0, 110)
                elif d > 17.6 and k < -0.25:
                    p = (0, 0, 0, 70)
                if 14.6 < d < 17.4 and 198 < ang < 252:
                    p = (255, 255, 255, 120 if 15.4 < d < 16.8 and 206 < ang < 244 else 60)
                if abs(dx - 6) <= 0.6 and abs(dy + 15) <= 0.6:
                    p = (255, 255, 255, 150)
            img.putpixel((x, y), p)
    # cravos de bronze nos quatro pontos cardeais do aro (losango de 5 px com contorno)
    for ax, ay in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
        cx, cy = c + ax * 22.5, c + ay * 22.5
        for y in range(N):
            for x in range(N):
                m = abs(x - cx) + abs(y - cy)
                if m <= 3.1:
                    img.putpixel((x, y), PRETO if m > 2.1 else BRONZE[2] if (x - cx) + (y - cy) < 0 else BRONZE[1])
    return img


def main():
    globo().resize((N * 2, N * 2), Image.NEAREST).save(DESTINO / "hud_globo_pixel.png", optimize=True)
    print("hud_globo_pixel.png em", DESTINO)


if __name__ == "__main__":
    main()
