# godot --path godot --script res://scripts/tools/captura.gd -- saida.png alvoX alvoZ distancia yaw pitch [cena]
extends SceneTree
func _init() -> void:
	var a := OS.get_cmdline_user_args()
	var cena: String = a[6] if a.size() > 6 else "res://scenes/cripta/Cripta.tscn"
	var inst := (load(cena) as PackedScene).instantiate()
	root.add_child(inst)
	var cam := inst.get_node("CameraEstudio")
	cam.set("Alvo", Vector3(float(a[1]), 0, -float(a[2]))); cam.set("Distancia", float(a[3])); cam.set("Yaw", float(a[4])); cam.set("Pitch", float(a[5]))
	root.size = Vector2i(1600, 900)
	for i in 40: await process_frame
	root.get_texture().get_image().save_png(a[0])
	quit()
