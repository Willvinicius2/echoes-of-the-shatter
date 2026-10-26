extends SceneTree
# Capturas do arqueiro de malha unica. Uso: godot --path godot --script res://scripts/tools/captura_unico.gd -- pasta [escala]
var cam: Camera3D
var n: Node3D
var pasta := ""
func _init() -> void:
	var a := OS.get_cmdline_user_args()
	pasta = a[0] if a.size() > 0 else "D:/openclaude/_trabalho-claude/arqueiro-tripo/malha_unica/capturas"
	var esc := float(a[1]) if a.size() > 1 else 1.6
	DirAccess.make_dir_recursive_absolute(pasta)
	var raiz := Node3D.new(); root.add_child(raiz)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR; env.background_color = Color("5A5A60")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR; env.ambient_light_color = Color(0.7, 0.7, 0.75); env.ambient_light_energy = 0.8
	var we := WorldEnvironment.new(); we.environment = env; raiz.add_child(we)
	var sol := DirectionalLight3D.new(); sol.rotation_degrees = Vector3(-50, 30, 0); raiz.add_child(sol)
	var sol2 := DirectionalLight3D.new(); sol2.rotation_degrees = Vector3(-30, 200, 0); sol2.light_energy = 0.5; raiz.add_child(sol2)
	var chao := MeshInstance3D.new(); var pm := PlaneMesh.new(); pm.size = Vector2(12, 12); chao.mesh = pm
	var mc := StandardMaterial3D.new(); mc.albedo_color = Color(0.25, 0.25, 0.27); chao.material_override = mc; raiz.add_child(chao)
	n = load("res://scenes/arqueiro/ArqueiroUnico.tscn").instantiate()
	n.rotation_degrees = Vector3(0, -90, 0); n.scale = Vector3.ONE * esc
	n.set("escala_corpo", esc)
	raiz.add_child(n)
	cam = Camera3D.new(); cam.fov = 30; raiz.add_child(cam)
	n.set("vel_real", 0.0)
	await create_timer(0.50).timeout
	# vistas (yaw: 0 = camera em +Z, de frente; 90 = lado +X; arqueiro olha para +Z)
	await tira("idle_frente", 0, 0.8, 4.2, 0.9)
	await tira("idle_lado", 90, 0.8, 4.2, 0.9)
	await tira("idle_costas_arco", 180, 0.8, 3.2, 0.9)
	await tira("idle_mao_close", 60, 0.75, 1.3, 0.8)
	n.set("vel_real", 0.8)
	await create_timer(0.67).timeout
	await tira("walk_lado", 90, 0.8, 4.2, 0.9)
	n.set("vel_real", 4.0)
	await create_timer(0.67).timeout
	await tira("run_lado", 90, 0.8, 4.2, 0.9)
	await tira("run_34", 40, 0.8, 4.2, 1.1)
	n.set("vel_real", 0.0)
	await create_timer(0.50).timeout
	n.call("tocar", "shoot")
	n.call("mirar", 1.0, false)
	n.set("segurando", true)
	await create_timer(2.00).timeout
	n.call("mirar", 1.0, false)
	await tira("tiro_carga_lado", 90, 0.9, 3.2, 1.0)
	await tira("tiro_carga_34", 50, 0.9, 3.2, 1.2)
	await tira("tiro_carga_frente", 0, 0.9, 3.2, 1.0)
	await tira("tiro_maos_close", 70, 0.95, 1.5, 1.1)
	await tira("tiro_maos_close_lado", 90, 0.95, 1.5, 1.0)
	Engine.time_scale = 0.15   # camera lenta: pega o quadro do solto
	n.call("mirar", 1.0, true)
	var guarda := 0
	while not n.call("shoot_solta") and guarda < 3000:
		await process_frame
		guarda += 1
	print("SOLTO ", guarda, " ", n.call("estado_atual"), " ", n.get("_pos_shoot"))
	await process_frame
	await process_frame
	Engine.time_scale = 0.0001
	await tira("tiro_solto_lado", 90, 0.9, 3.2, 1.0)
	await tira("tiro_solto_34", 50, 0.9, 3.2, 1.2)
	Engine.time_scale = 1.0
	n.set("segurando", false)
	await create_timer(2.67).timeout
	n.call("tocar", "dash")
	await create_timer(0.23).timeout
	await tira("dash_lado", 90, 0.6, 3.5, 0.8)
	await create_timer(0.67).timeout
	n.call("tocar", "hurt")
	await create_timer(0.13).timeout
	await tira("hurt_lado", 90, 0.8, 4.2, 0.9)
	await create_timer(0.67).timeout
	n.call("tocar", "slash")
	await create_timer(0.60).timeout
	await tira("slash_lado", 90, 0.8, 4.2, 0.9)
	await create_timer(2.00).timeout
	n.call("tocar", "fall")
	await create_timer(1.50).timeout
	await tira("fall_lado", 90, 0.5, 4.2, 0.7)
	quit()
func tira(nome: String, yaw_g: float, alvo_y: float, dist: float, alt: float) -> void:
	var yaw := deg_to_rad(yaw_g)
	var alvo := Vector3(0, alvo_y, 0.0) * (n.scale.x / 1.6)
	cam.global_position = Vector3(sin(yaw) * dist, alt, cos(yaw) * dist)
	cam.look_at(alvo, Vector3.UP)
	await create_timer(0.10).timeout
	await RenderingServer.frame_post_draw
	get_root().get_viewport().get_texture().get_image().save_png("%s/%s.png" % [pasta, nome])
