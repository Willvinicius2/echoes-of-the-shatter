extends SceneTree
func _init() -> void:
	var n: Node3D = load("res://art/models/SM_Cripta_Braseiro.glb").instantiate()
	root.add_child(n)
	await process_frame
	var mn := Vector3(1e9, 1e9, 1e9); var mx := Vector3(-1e9, -1e9, -1e9)
	for m in n.find_children("*", "MeshInstance3D", true, false):
		var a: AABB = (m as MeshInstance3D).global_transform * (m as MeshInstance3D).get_aabb()
		mn = mn.min(a.position); mx = mx.max(a.end)
	print("MEDIDA braseiro altura=", mx.y - mn.y, " largura=", mx.x - mn.x)
	quit()
