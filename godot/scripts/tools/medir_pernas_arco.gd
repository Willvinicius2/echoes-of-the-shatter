extends SceneTree
# mede a oscilacao do pe esquerdo (m, escala 1) nos estados de arco com e sem velocidade real
func _init() -> void:
	for vel in [0.0, 1.5]:
		var n: Node3D = load("res://scenes/arqueiro/ArqueiroAnimadoTripo.tscn").instantiate()
		root.add_child(n)
		await process_frame
		var sk := n.find_child("Skeleton3D", true, false) as Skeleton3D
		var i := sk.find_bone("mixamorig_LeftFoot")
		n.set("vel_real", vel)
		n.tocar("sacar_arco")
		var xs: Array = []
		for k in 100:
			await process_frame
			if k > 40:
				xs.append(sk.get_bone_global_pose(i).origin.z)
		print("MEDIDA vel=", vel, " estado=", n.estado_atual(), " oscilacao_pe_z=", snappedf(float(xs.max()) - float(xs.min()), 0.001), " mistura=", snappedf(n.get("_mist"), 0.01))
		n.queue_free()
		await process_frame
	quit()
