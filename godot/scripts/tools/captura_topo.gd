# Vista de cima ortográfica com grade de 3 m.
# godot --path godot --script res://scripts/tools/captura_topo.gd -- saida.png alvoX alvoZ tamanho largura altura
extends SceneTree
func _init() -> void:
	var a := OS.get_cmdline_user_args()
	var inst := (load("res://scenes/cripta/Cripta.tscn") as PackedScene).instantiate()
	root.add_child(inst)
	var old := inst.get_node_or_null("CameraEstudio")
	if old: old.queue_free()
	var ax := float(a[1]); var az := float(a[2]); var tam := float(a[3])
	var cam := Camera3D.new(); cam.projection = Camera3D.PROJECTION_ORTHOGONAL; cam.size = tam; cam.far = 200.0
	cam.position = Vector3(ax, 40.0, -az); cam.rotation_degrees = Vector3(-90, 0, 0); root.add_child(cam); cam.current = true
	var im := ImmediateMesh.new(); im.surface_begin(Mesh.PRIMITIVE_LINES)
	var x0 := floorf((ax - tam) / 3.0) * 3.0; var z0 := floorf((az - tam) / 3.0) * 3.0
	for k in int(tam * 2.0 / 3.0) + 2:
		var v := x0 + k * 3.0
		im.surface_add_vertex(Vector3(v, 12.0, -(az - tam))); im.surface_add_vertex(Vector3(v, 12.0, -(az + tam)))
		var w := z0 + k * 3.0
		im.surface_add_vertex(Vector3(ax - tam, 12.0, -w)); im.surface_add_vertex(Vector3(ax + tam, 12.0, -w))
	im.surface_end()
	var mi := MeshInstance3D.new(); mi.mesh = im
	var m := StandardMaterial3D.new(); m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED; m.albedo_color = Color(1, 1, 0, 0.5); m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mi.material_override = m; root.add_child(mi)
	root.size = Vector2i(int(a[4]), int(a[5]))
	for i in 20: await process_frame
	root.get_texture().get_image().save_png(a[0])
	quit()
