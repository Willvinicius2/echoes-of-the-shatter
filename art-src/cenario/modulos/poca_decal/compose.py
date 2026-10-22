"""Junta as partes (mascara, bordas, gotas) em texturas de Decal do Godot, gera o .tscn e (com bpy) a prancha de revisão.
/tmp/venv/bin/python compose.py [A,B,C] [--render] [--pasta-previas dir]"""
import sys, os, math, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
TEX = os.path.join(RAIZ, "godot", "art", "textures"); CENA = os.path.join(RAIZ, "godot", "scenes", "cripta")
COR_UMIDO = np.array([0.13, 0.25, 0.31], np.float32)      # azul-ardósia frio, um pouco mais escuro que a laje

def texturas(nome):
    import mascara, bordas, gotas
    L = lib.contexto(nome)
    m = mascara.build(L); b = bordas.build(L, m); g = gotas.build(L, m)
    wet, water = np.clip(m["wet"], 0, 1), np.clip(m["water"], 0, 1)
    # albedo RGBA: escurece o piso (umidade) e escurece mais na água (o piso aparece por baixo)
    prof = np.clip(-m["signed"] / 0.25, 0, 1)                                    # 0 na borda, 1 a 25 cm para dentro
    a = np.clip(wet * 0.42 + water * (0.2 + 0.14 * prof), 0, 0.9)
    rgb = np.broadcast_to(COR_UMIDO * (1 - 0.5 * prof[..., None]), (L.H, L.W, 3)).copy()
    ba = b["rgba"][..., 3:4]; out_a = ba + a[..., None] * (1 - ba)
    out_rgb = (b["rgba"][..., :3] * ba + rgb * a[..., None] * (1 - ba)) / np.maximum(out_a, 1e-4)
    albedo = np.concatenate([out_rgb, out_a], -1)
    # ORM: R oclusão, G rugosidade (água ~0.02, piso úmido ~0.25, cascalho/musgo ~0.75), B metálico 0
    rough = 0.6 - 0.35 * wet; rough = rough * (1 - water) + 0.0 * water
    rough = rough * (1 - ba[..., 0]) + 0.75 * ba[..., 0]
    orm = np.stack([np.ones_like(rough), rough, np.zeros_like(rough)], -1)
    # normal (OpenGL): relevo da água (m) e dos detalhes
    h = g["altura"] * 1.0 + (b["altura"] - 0.5) * 0.004
    dz, dx = np.gradient(h, 1 / L.PPM)
    n = np.stack([-dx * 14, dz * 14, np.ones_like(h)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    normal = n * 0.5 + 0.5
    for suf, arr in (("albedo", albedo), ("orm", orm), ("n", normal)):
        from PIL import Image
        a8 = (np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8); Image.fromarray(a8).save(os.path.join(TEX, f"T_Poca_{nome}_{suf}.png"))
    return L

def tscn(L):
    n = L.nome
    s = f'''[gd_scene load_steps=7 format=3]

[ext_resource type="Texture2D" path="res://art/textures/T_Poca_{n}_albedo.png" id="1"]
[ext_resource type="Texture2D" path="res://art/textures/T_Poca_{n}_orm.png" id="2"]
[ext_resource type="Texture2D" path="res://art/textures/T_Poca_{n}_n.png" id="3"]
[ext_resource type="Material" path="res://art/materials/M_Cripta_Gotas.tres" id="4"]

[sub_resource type="PlaneMesh" id="PlaneMesh_gotas"]
size = Vector2({L.w:.3f}, {L.h:.3f})

[node name="Poca_{n}" type="Node3D"]

[node name="Decal" type="Decal" parent="."]
size = Vector3({L.w:.3f}, 1.0, {L.h:.3f})
texture_albedo = ExtResource("1")
texture_orm = ExtResource("2")
texture_normal = ExtResource("3")
upper_fade = 0.3
lower_fade = 0.3
normal_fade = 0.3

[node name="Gotas" type="MeshInstance3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0.004, 0)
mesh = SubResource("PlaneMesh_gotas")
surface_material_override/0 = ExtResource("4")
cast_shadow = 0
'''
    open(os.path.join(CENA, f"Poca_{n}.tscn"), "w").write(s)

if __name__ == "__main__":
    nomes = [x for x in (sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "A,B,C").split(",")]
    for nm in nomes:
        L = texturas(nm); tscn(L); print("texturas", nm, L.W, "x", L.H)
