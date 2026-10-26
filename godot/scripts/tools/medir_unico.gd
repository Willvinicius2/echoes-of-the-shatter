extends SceneTree
# Mede o GLB da malha unica: clipes, ossos e posicoes de repouso (uso interno de ajuste da pose).
func _init() -> void:
	var n: Node3D = load("res://scenes/arqueiro/ArqueiroUnico.tscn").instantiate()
	root.add_child(n)
	await process_frame
	var p: AnimationPlayer = n.call("player")
	for a in p.get_animation_list():
		print("CLIPE ", a, " ", snappedf(p.get_animation(a).length, 0.01))
	var sk := n.find_child("Skeleton3D", true, false) as Skeleton3D
	print("OSSOS ", sk.get_bone_count())
	for b in ["Hips", "Spine", "Spine1", "Spine2", "Neck", "Head", "HeadTop_End", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "RightArm", "RightForeArm", "RightHand", "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase", "RightUpLeg", "RightFoot"]:
		var i := sk.find_bone("mixamorig_" + b)
		print("OSSO ", b, " ", i, " ", sk.get_bone_global_rest(i).origin if i >= 0 else Vector3())
	for mi in n.find_children("*", "MeshInstance3D", true, false):
		print("MESH ", mi.name, " aabb ", (mi as MeshInstance3D).get_aabb())
	var a := p.get_animation("idle")
	var th := a.find_track(NodePath("Armature/Skeleton3D:mixamorig_Hips"), Animation.TYPE_POSITION_3D)
	print("HIPS idle t0 ", a.position_track_interpolate(th, 0.0) if th >= 0 else "sem track")
	quit()
