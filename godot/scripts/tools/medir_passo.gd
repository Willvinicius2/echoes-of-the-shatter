extends SceneTree
# velocidade do pe de apoio (m/s em escala 1) dos clipes walk e run do Tripo
func _init() -> void:
	var n: Node3D = load("res://scenes/arqueiro/ArqueiroAnimadoTripo.tscn").instantiate()
	root.add_child(n)
	await process_frame
	await process_frame
	n.get_node("Arvore").active = false
	var p: AnimationPlayer = n.player()
	var sk := n.find_child("Skeleton3D", true, false) as Skeleton3D
	for nome in ["walk", "run"]:
		var a := p.get_animation(nome)
		var passo := 1.0 / 60.0
		var vs: Array = []
		for pe in ["mixamorig_LeftFoot", "mixamorig_RightFoot"]:
			var i := sk.find_bone(pe)
			var ant := Vector3.ZERO
			var t := 0.0
			var ys: Array = []; var xs: Array = []
			while t < a.length:
				p.play(nome); p.seek(t, true); sk.force_update_all_bone_transforms()
				var pos := sk.get_bone_global_pose(i).origin
				ys.append(pos.y); xs.append(pos.x)
				t += passo
			var ymin: float = ys.min(); var ymax: float = ys.max()
			for k in range(1, ys.size()):
				if ys[k] < ymin + (ymax - ymin) * 0.12:
					vs.append(absf(xs[k] - xs[k - 1]) / passo)
		vs.sort()
		print("MEDIDA ", nome, " dur=", a.length, " vel_apoio_mediana=", vs[vs.size() / 2] if vs.size() > 0 else -1)
	quit()
