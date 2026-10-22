# godot --path godot --script res://scripts/tools/captura_arqueiro.gd -- pasta_saida
# Pranchas do arqueiro: fundo cinza neutro, luz neutra, camera perspectiva baixa, heroi em Idle.
extends SceneTree
func _init() -> void:
	var a := OS.get_cmdline_user_args()
	var pasta: String = a[0] if a.size() > 0 else "D:/openclaude/_trabalho-claude/tmp/arq"
	DirAccess.make_dir_recursive_absolute(pasta)
	var sv := SubViewport.new(); sv.size = Vector2i(1024, 1024); sv.render_target_update_mode = SubViewport.UPDATE_ALWAYS; sv.msaa_3d = Viewport.MSAA_4X
	root.add_child(sv)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("C8C8C8")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.75, 0.75, 0.78)
	env.ambient_light_energy = 0.8
	var we := WorldEnvironment.new(); we.environment = env; sv.add_child(we)
	var sol := DirectionalLight3D.new(); sol.rotation_degrees = Vector3(-50, -30, 0); sol.light_energy = 1.0; sv.add_child(sol)
	var sol2 := DirectionalLight3D.new(); sol2.rotation_degrees = Vector3(-30, 150, 0); sol2.light_energy = 0.45; sv.add_child(sol2)
	var chao := StaticBody3D.new(); chao.collision_layer = 0xFFFFF; chao.collision_mask = 0
	var cs := CollisionShape3D.new(); var bx := BoxShape3D.new(); bx.size = Vector3(20, 1, 20); cs.shape = bx; cs.position = Vector3(0, -0.5, 0)
	chao.add_child(cs); sv.add_child(chao)
	var heroi := (load("res://scenes/arqueiro/Arqueiro.tscn") as PackedScene).instantiate()
	sv.add_child(heroi)
	heroi.velocity = Vector3.ZERO
	var cam := Camera3D.new(); cam.fov = 30; sv.add_child(cam); cam.current = true
	for i in 90:
		await process_frame
	# vistas: nome, yaw (graus, 0 = camera na frente do heroi, +Z), alvo, distancia, altura da camera
	var anim: String = a[1] if a.size() > 1 else ""
	if anim != "":
		heroi.set_process(false); heroi.set_physics_process(false)
		var ap := heroi.find_child("AnimationPlayer", true, false) as AnimationPlayer
		for n in ap.get_animation_list():
			if n.ends_with(anim): ap.play(n)
		for i in 10: await process_frame
	var vistas := [
		["frente", 0.0, Vector3(0, 0.75, 0), 3.8, 0.55],
		["tres_quartos", 40.0, Vector3(0, 0.75, 0), 3.8, 0.55],
		["lado", 90.0, Vector3(0, 0.75, 0), 3.8, 0.55],
		["costas", 180.0, Vector3(0, 0.75, 0), 3.8, 0.55],
		["capuz", 20.0, Vector3(0, 1.22, 0), 1.9, 1.25],
		["mao", 90.0, Vector3(0, 0.9, 0.5), 1.4, 0.9],
		["mao3q", 60.0, Vector3(0, 0.9, 0.5), 1.4, 1.0],
		["capa_costas", 180.0, Vector3(0, 0.95, 0), 2.2, 0.95],
	]
	for v in vistas:
		var yaw := deg_to_rad(v[1])
		var alvo: Vector3 = heroi.global_position + v[2]
		cam.global_position = heroi.global_position + Vector3(sin(yaw) * v[3], v[4], cos(yaw) * v[3])
		cam.look_at(alvo, Vector3.UP)
		for i in 6:
				await process_frame
		sv.get_texture().get_image().save_png("%s/%s.png" % [pasta, v[0]])
	quit()
