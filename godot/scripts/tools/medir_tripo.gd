extends SceneTree
func _init() -> void:
	var n: Node3D = load("res://scenes/arqueiro/ArqueiroAnimadoTripo.tscn").instantiate()
	root.add_child(n)
	await process_frame
	await process_frame
	var sk := n.find_child("Skeleton3D", true, false) as Skeleton3D
	var mn := Vector3(1e9, 1e9, 1e9); var mx := Vector3(-1e9, -1e9, -1e9)
	for m in n.find_children("*", "MeshInstance3D", true, false):
		if not (m as MeshInstance3D).visible: continue
		var a: AABB = (m as MeshInstance3D).global_transform * (m as MeshInstance3D).get_aabb()
		mn = mn.min(a.position); mx = mx.max(a.end)
	print("MEDIDA aabb min=", mn, " max=", mx, " altura=", mx.y - mn.y)
	for b in ["mixamorig_Hips", "mixamorig_Head", "mixamorig_LeftArm", "mixamorig_RightArm", "mixamorig_LeftToeBase"]:
		var i := sk.find_bone(b)
		print("MEDIDA ", b, " ", sk.global_transform * sk.get_bone_global_pose(i).origin if i >= 0 else "?")
	var l := sk.find_bone("mixamorig_LeftArm"); var r := sk.find_bone("mixamorig_RightArm")
	if l >= 0 and r >= 0:
		var d: Vector3 = (sk.get_bone_global_pose(r).origin - sk.get_bone_global_pose(l).origin)
		print("MEDIDA frente=", Vector3.UP.cross((sk.global_transform.basis * d)).normalized())
	quit()
