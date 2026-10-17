"""Modular (Blender): monta o heroi com o corpo base em 6 regioes e as 5 pecas, e liga ou desliga pecas por combinacao."""
import bpy, numpy as np
from mathutils import Matrix
from mdl_common import *

SLOTS = ["Head", "Chest", "Hands", "Legs", "Feet"]
REGIONS = ["Head", "Torso", "Arms", "Hands", "Legs", "Feet"]


def assemble(cfg):
    """Abre work/modular_body.blend e traz as pecas de work/modular_work.blend ligadas ao mesmo esqueleto. Devolve (arm, pecas, regioes)."""
    bpy.ops.wm.open_mainfile(filepath=wpath(cfg, "modular_body.blend"))
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    names = [f"SK_{cfg['hero']}_{s}_{cfg['set_name']}" for s in SLOTS]
    with bpy.data.libraries.load(wpath(cfg, "modular_work.blend")) as (src, dst):
        dst.objects = names
    pieces = {}
    for s, o in zip(SLOTS, dst.objects):
        bpy.context.scene.collection.objects.link(o)
        o.parent = arm; o.matrix_parent_inverse = Matrix.Identity(4)
        for m in list(o.modifiers):
            o.modifiers.remove(m)
        mod = o.modifiers.new("Armature", 'ARMATURE'); mod.object = arm
        pieces[s] = o
    regs = {r: bpy.data.objects[f"Body_{r}"] for r in REGIONS}
    return arm, pieces, regs


def set_combo(pieces, regs, worn, hides):
    """worn: lista de slots vestidos. Liga as pecas vestidas e as regioes do corpo que nenhuma delas esconde."""
    hidden = set()
    for s in worn:
        hidden |= set(hides[s])
    for s, o in pieces.items():
        o.hide_render = o.hide_viewport = s not in worn
    for r, o in regs.items():
        o.hide_render = o.hide_viewport = r in hidden
    return sorted(set(REGIONS) - hidden)


COMBOS = {"completo": SLOTS, "sem_elmo": ["Chest", "Hands", "Legs", "Feet"], "sem_luvas": ["Head", "Chest", "Legs", "Feet"],
          "sem_botas": ["Head", "Chest", "Hands", "Legs"], "so_corpo": []}
