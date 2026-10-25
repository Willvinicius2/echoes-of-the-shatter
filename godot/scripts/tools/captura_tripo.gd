extends SceneTree
# Verifica escala e frente do arqueiro Tripo: caixa vermelha em +Z, camera alta em -Z olhando para +Z... (uso: -- saida.png)
func _init() -> void:
	var args := OS.get_cmdline_user_args()
	var saida: String = args[0] if args.size() > 0 else "tripo.png"
	var raiz := Node3D.new(); root.add_child(raiz)
	var n: Node3D = load("res://scenes/arqueiro/ArqueiroAnimadoTripo.tscn").instantiate()
	n.rotation_degrees = Vector3(0, -90, 0); n.scale = Vector3.ONE * (float(args[1]) if args.size() > 1 else 2.2)
	raiz.add_child(n); n.set("velocidade", 1.0)
	var br: Node3D = load("res://art/models/SM_Cripta_Braseiro.glb").instantiate(); br.scale = Vector3.ONE * 0.75; br.position = Vector3(0, 0, 1.6); raiz.add_child(br)
	var chao := MeshInstance3D.new(); var pm := PlaneMesh.new(); pm.size = Vector2(12, 12); chao.mesh = pm; raiz.add_child(chao)
	var cx := MeshInstance3D.new(); var bm := BoxMesh.new(); bm.size = Vector3(0.3, 0.3, 0.3); cx.mesh = bm; cx.position = Vector3(0, 0.15, 3.0)
	var mat := StandardMaterial3D.new(); mat.albedo_color = Color.RED; cx.material_override = mat; raiz.add_child(cx)
	var l := DirectionalLight3D.new(); l.rotation_degrees = Vector3(-50, 30, 0); raiz.add_child(l)
	var cam := Camera3D.new(); raiz.add_child(cam)
	cam.look_at_from_position(Vector3(6.0, 1.2, 0.8), Vector3(0, 0.9, 0.8))
	for i in 40: await process_frame
	await create_timer(0.9).timeout
	get_root().get_viewport().get_texture().get_image().save_png(saida)
	quit()
