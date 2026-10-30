#!/usr/bin/env python3
"""Gera os efeitos e a música do cliente 2D em godot/art2d/audio/ (WAV 16 bits, mono, 22050 Hz).

Tudo é sintetizado aqui, com semente fixa, sem amostra de terceiros: a saída é original do projeto
e dedicada ao domínio público (CC0). Rode `python3 tools/audio/gerar_audio.py` para regerar.
"""
import struct
import sys
import wave
from pathlib import Path

import numpy as np

SR = 22050
SAIDA = Path(__file__).resolve().parents[2] / "godot" / "art2d" / "audio"
rng = np.random.default_rng(20261030)


def t_(dur):
    return np.arange(int(SR * dur)) / SR


def env(n, ataque=0.005, queda=None):
    """Envelope: ataque linear curto e queda exponencial até o fim."""
    x = np.arange(n) / SR
    dur = n / SR
    queda = queda if queda is not None else dur / 4.0
    e = np.exp(-x / queda)
    a = np.minimum(1.0, x / ataque)
    fim = np.minimum(1.0, (dur - x) / 0.01)
    return e * a * fim


def lowpass(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def ruido(dur):
    return rng.uniform(-1, 1, int(SR * dur))


def tom(freq, dur, forma="sin", queda=None):
    t = t_(dur)
    fase = 2 * np.pi * freq * t
    if forma == "sin":
        s = np.sin(fase)
    elif forma == "saw":
        s = 2 * ((freq * t) % 1.0) - 1
    elif forma == "tri":
        s = 2 * np.abs(2 * ((freq * t) % 1.0) - 1) - 1
    else:
        s = np.sign(np.sin(fase))
    return s * env(len(t), queda=queda)


def varredura(f0, f1, dur, forma="sin", queda=None):
    t = t_(dur)
    f = f0 * (f1 / f0) ** (t / dur)
    fase = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(fase) if forma == "sin" else np.sign(np.sin(fase))
    return s * env(len(t), queda=queda)


def somar(*partes):
    n = max(len(p) for p in partes)
    out = np.zeros(n)
    for p in partes:
        out[: len(p)] += p
    return out


def nota(freq, dur=0.5, queda=0.15):
    return tom(freq, dur, "sin", queda) + 0.35 * tom(freq * 2, dur, "sin", queda * 0.6)


def seq(notas, passo, dur=0.5, queda=0.15):
    out = np.zeros(int(SR * (passo * len(notas) + dur)))
    for i, f in enumerate(notas):
        n = nota(f, dur, queda)
        i0 = int(SR * passo * i)
        out[i0:i0 + len(n)] += n
    return out


def gravar(nome, x, pico=0.8):
    x = np.asarray(x, dtype=np.float64)
    m = np.max(np.abs(x))
    if m > 0:
        x = x / m * pico
    pcm = (x * 32767).astype("<i2")
    with wave.open(str(SAIDA / f"{nome}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"{nome}.wav  {len(x) / SR:.2f}s")


def musica(dur=16.0):
    """Drone sombrio com sinos esparsos. Frequências com ciclos inteiros por volta: o laço não estala."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    base = 55.0  # Lá 1
    ciclos = lambda f: round(f * dur) / dur
    drone = np.zeros(n)
    for mult, amp in ((1, 1.0), (1.5, 0.55), (2, 0.4), (3, 0.15)):
        f = ciclos(base * mult)
        drone += amp * np.sin(2 * np.pi * f * t)
    lfo = 0.65 + 0.35 * np.sin(2 * np.pi * (2 / dur) * t)
    drone *= lfo
    pad = np.zeros(n)
    for f in (ciclos(110.0), ciclos(130.8), ciclos(164.8)):
        pad += np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * (1 / dur) * t))
    pad *= 0.12 * (0.5 + 0.5 * np.sin(2 * np.pi * (1 / dur) * t - 1.0))
    sinos = np.zeros(n)
    escala = [220.0, 261.6, 293.7, 329.6, 392.0, 440.0]  # Lá menor pentatônica+
    for i, inicio in enumerate((1.0, 4.5, 7.0, 10.5, 13.0)):
        n_s = nota(escala[(i * 2 + 1) % len(escala)], 2.4, 0.5)
        i0 = int(SR * inicio)
        fim = min(n, i0 + len(n_s))
        sinos[i0:fim] += 0.18 * n_s[: fim - i0]
    return drone + pad + sinos


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    gravar("shoot", somar(
        lowpass(ruido(0.16), 5000) * env(int(SR * 0.16), queda=0.04) * 0.6,
        varredura(1400, 380, 0.14, queda=0.05)))
    gravar("hit_enemy", somar(tom(150, 0.12, "sin", 0.03), lowpass(ruido(0.08), 3000) * env(int(SR * 0.08), queda=0.015) * 0.5))
    gravar("kill_enemy", somar(
        varredura(260, 55, 0.35, queda=0.1),
        lowpass(ruido(0.2), 2200) * env(int(SR * 0.2), queda=0.05) * 0.5))
    gravar("player_hurt", somar(tom(110, 0.28, "saw", 0.07), tom(78, 0.28, "square", 0.05) * 0.4))
    gravar("dodge", lowpass(ruido(0.24), 3500) * np.sin(np.linspace(0, np.pi, int(SR * 0.24))) ** 1.5)
    gravar("card_open", seq([392.0, 523.3, 659.3, 784.0], 0.07, 0.6, 0.2))
    gravar("card_pick", seq([523.3, 784.0], 0.09, 0.5, 0.15))
    gravar("door_open", somar(
        lowpass(ruido(0.9), 700) * np.sin(np.linspace(0, np.pi, int(SR * 0.9))) * 1.2,
        tom(52, 0.9, "sin", 0.35)))
    gravar("ui_click", somar(tom(900, 0.05, "tri", 0.015), tom(450, 0.05, "sin", 0.02) * 0.5))
    gravar("victory", seq([392.0, 523.3, 659.3, 784.0, 1046.5], 0.14, 1.0, 0.35))
    gravar("defeat", seq([392.0, 349.2, 311.1, 261.6], 0.28, 1.2, 0.4))
    gravar("music_cripta", musica(), pico=0.7)


if __name__ == "__main__":
    sys.exit(main())
