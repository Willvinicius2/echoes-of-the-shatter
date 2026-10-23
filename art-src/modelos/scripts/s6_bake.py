"""Etapa 6 (Blender, CPU): oclusao de ambiente e cavidade da malha ALTA assadas na UV da malha de jogo.

Cada texel da malha de jogo acha o ponto mais externo da malha alta (raio de fora para dentro ao longo da normal;
se errar, o ponto mais proximo) e a partir dele:
  AO       = 1 - fracao dos raios do hemisferio (cosseno, rotacionados por texel) que acertam a malha alta em ate
             ao_distance (so geometria da malha alta, sem a malha de jogo no caminho);
  cavidade = altura media da superficie alta em um anel de raio cav_radius ao redor do ponto (concavo > 0,5,
             convexo < 0,5): realca cantos e sulcos, escurece fendas.
O trabalho e repartido em processos do proprio Blender (variavel MDL_SHARD="i/N"). Grava work/bake_ao.png e
work/bake_cavity.png (cinza, 1024) e work/bake_report.json.
Nota: o bake de AO do Cycles (selecionado para ativo e por vertice) errou camadas (manchas pretas/binarias) na malha
de jogo, que corta entre armadura e corpo; por isso o raio e disparado direto da malha alta.
"""
import bpy, numpy as np, sys, os, time, math, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from mdl_blender import *
from mathutils import Vector
from mathutils.bvhtree import BVHTree

cfg = load_cfg()
SIZE = cfg.get("bake_size", cfg["tex_size"])      # AO/cavidade sao de baixa frequencia: bake_size 1024 mesmo com textura 2048 (s7 reamostra)
NSH = int(cfg.get("bake_shards", 1))
shard = os.environ.get("MDL_SHARD")

def run_shard(si, sn):
    bpy.ops.wm.open_mainfile(filepath=wpath(cfg, "game_uv.blend"))
    low = bpy.data.objects["game"]
    g = texel_geometry(low, SIZE)
    high = load_ply_obj(wpath(cfg, "high_ao.ply" if os.path.exists(wpath(cfg, "high_ao.ply")) else "high.ply"), "high")
    hv, hf = mesh_arrays(high)
    bvh = BVHTree.FromPolygons([tuple(v) for v in hv], [tuple(f) for f in hf])
    ys, xs = np.where(g["valid"])
    sel = np.arange(len(ys))[si::sn]
    NR = cfg.get("ao_rays", 24)
    K = cfg["size_scale"]
    dist = cfg.get("ao_distance", 0.25) * K
    rad = cfg.get("cav_radius", 0.012) * K
    NC = 8
    rng = np.random.default_rng(100 + si)
    # hemisferio com distribuicao de cosseno (espiral de Fibonacci), em espaco tangente
    k = (np.arange(NR) + 0.5) / NR
    ct, st = np.sqrt(1 - k), np.sqrt(k)
    ph = np.arange(NR) * 2.399963
    hemi = np.stack([st * np.cos(ph), st * np.sin(ph), ct], 1)
    ring = [(math.cos(2 * math.pi * j / NC), math.sin(2 * math.pi * j / NC)) for j in range(NC)]
    ao = np.empty(len(sel), np.float32); cav = np.empty(len(sel), np.float32)
    for m, s in enumerate(sel):
        y, x = ys[s], xs[s]
        p, n = Vector(g["pos"][y, x]), Vector(g["nrm"][y, x])
        h = bvh.ray_cast(p + n * 0.05 * K, -n, 0.12 * K)
        if h[0] is None:
            h = bvh.find_nearest(p, 0.08 * K)
        if h[0] is None:
            ao[m] = 1.0; cav[m] = 0.5
            continue
        o, hn = h[0], h[1]
        if hn.dot(n) < 0:
            hn = -hn
        o0 = o
        o = o + hn * 0.0015 * K
        t = hn.cross(Vector((0, 0, 1)) if abs(hn.z) < 0.9 else Vector((1, 0, 0))).normalized()
        b = hn.cross(t)
        a = rng.uniform(0, 2 * math.pi); ca, sa = math.cos(a), math.sin(a)
        t, b = t * ca + b * sa, b * ca - t * sa
        hit = 0
        for d in hemi:
            if bvh.ray_cast(o, t * d[0] + b * d[1] + hn * d[2], dist)[0] is not None:
                hit += 1
        ao[m] = 1.0 - hit / NR
        hs = 0.0
        for cx, cy in ring:
            q = o + (t * cx + b * cy) * rad + hn * 0.01 * K
            r = bvh.ray_cast(q, -hn, 0.04 * K)
            hs += (r[0] - o0).dot(hn) if r[0] is not None else -0.01 * K
        cav[m] = min(1.0, max(0.0, 0.5 + 0.5 * (hs / NC) / (rad * 0.5)))
    np.savez(wpath(cfg, f"_shard_{si}.npz"), ao=ao, cav=cav)

if shard is not None:
    run_shard(*[int(x) for x in shard.split("/")])
else:
    # processo principal = fragmento 0; lanca os demais (no maximo 2 processos do Blender ao mesmo tempo)
    wait_free_virtual(2.0)
    t0 = time.time()
    procs = []
    for i in range(1, NSH):
        env = dict(os.environ, MDL_SHARD=f"{i}/{NSH}")
        procs.append(subprocess.Popen([bpy.app.binary_path, "-b", "--factory-startup", "--python-exit-code", "1", "-P",
                                       os.path.abspath(__file__), "--", cfg["_cfg_path"]], env=env,
                                      stdout=open(wpath(cfg, f"_shard_{i}.log"), "w"), stderr=subprocess.STDOUT))
    run_shard(0, NSH)
    bad = [i + 1 for i, p in enumerate(procs) if p.wait() != 0]
    if bad:
        print(open(wpath(cfg, f"_shard_{bad[0]}.log")).read()[-1500:])
        raise SystemExit(f"fragmentos com erro: {bad}")
    bpy.ops.wm.open_mainfile(filepath=wpath(cfg, "game_uv.blend"))
    g = texel_geometry(bpy.data.objects["game"], SIZE)
    valid = g["valid"]
    ys, xs = np.where(valid)
    ao = np.ones((SIZE, SIZE), np.float32); cav = np.full((SIZE, SIZE), 0.5, np.float32)
    for i in range(NSH):
        with np.load(wpath(cfg, f"_shard_{i}.npz")) as d:
            sel = np.arange(len(ys))[i::NSH]
            ao[ys[sel], xs[sel]] = d["ao"]; cav[ys[sel], xs[sel]] = d["cav"]
        os.remove(wpath(cfg, f"_shard_{i}.npz"))
        if i: os.remove(wpath(cfg, f"_shard_{i}.log"))
    ao3, _ = dilate(np.repeat(ao[..., None], 3, -1), valid, 16)
    cav3, _ = dilate(np.repeat(cav[..., None], 3, -1), valid, 16)
    save_png(np.clip(ao3, 0, 1).astype(np.float32), wpath(cfg, "bake_ao.png"))
    save_png(np.clip(cav3, 0, 1).astype(np.float32), wpath(cfg, "bake_cavity.png"))
    rep = dict(ao_mean=float(ao[valid].mean()), ao_min=float(ao[valid].min()), cav_mean=float(cav[valid].mean()),
               cav_std=float(cav[valid].std()), texels=int(valid.sum()), seconds=round(time.time() - t0))
    save_json(wpath(cfg, "bake_report.json"), rep)
    print("S6", rep)
