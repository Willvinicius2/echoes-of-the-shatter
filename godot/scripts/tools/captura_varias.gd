# Várias capturas numa só execução (carrega a cena uma vez).
# godot --path godot --script res://scripts/tools/captura_varias.gd -- pasta largura altura "nome:alvoX:alvoZ:distancia:yaw:pitch[:fov]" ...
# Alvo em coordenadas doc (X leste, Z norte).
extends SceneTree
func _init() -> void:
	var a := OS.get_cmdline_user_args()
	var inst := (load("res://scenes/cripta/Cripta.tscn") as PackedScene).instantiate()
	root.add_child(inst)
	root.size = Vector2i(int(a[1]), int(a[2]))
	var cam := inst.get_node("CameraEstudio") as Camera3D
	for k in range(3, a.size()):
		var p := String(a[k]).split(":")
		cam.set("Alvo", Vector3(float(p[1]), float(p[6]) if p.size() > 7 else 0.0, -float(p[2])))
		cam.set("Distancia", float(p[3])); cam.set("Yaw", float(p[4])); cam.set("Pitch", float(p[5]))
		if p.size() > 7: cam.fov = float(p[7])
		cam.call("aplicar")
		for i in 6: await process_frame
		root.get_texture().get_image().save_png("%s/%s.png" % [a[0], p[0]])
		print("ok ", p[0])
	quit()
