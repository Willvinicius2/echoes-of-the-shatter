# Captura do corpo base do Arqueiro (sem cena): carrega o GLB, posiciona a camera e salva PNG.
# godot --path godot --script res://scripts/tools/captura_corpo.gd -- saida.png yaw_graus distancia alvoY
# yaw 0 = frente (+Z no glTF), 180 = costas.
extends SceneTree

func _init() -> void:
	var a := OS.get_cmdline_user_args()
	var doc := GLTFDocument.new()
	var st := GLTFState.new()
	var err := doc.append_from_file("res://art/models/personagens/arqueiro/Arqueiro_Corpo.glb", st)
	if err != OK:
		push_error("GLB nao carregou: %d" % err)
		quit(1)
		return
	var corpo := doc.generate_scene(st)
	root.add_child(corpo)
	var luz := DirectionalLight3D.new()
	luz.rotation_degrees = Vector3(-40, 35, 0)
	luz.light_energy = 1.1
	root.add_child(luz)
	var amb := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.36, 0.37, 0.44)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.62, 0.62, 0.66)
	env.ambient_light_energy = 0.8
	amb.environment = env
	root.add_child(amb)
	var yaw := deg_to_rad(float(a[1]))
	var dist := float(a[2])
	var alvo_y := float(a[3])
	var cam := Camera3D.new()
	root.add_child(cam)
	var alvo := Vector3(0, alvo_y, 0)
	var pos := alvo + Vector3(sin(yaw), 0.05, cos(yaw)) * dist
	cam.look_at_from_position(pos, alvo, Vector3.UP)
	cam.current = true
	root.size = Vector2i(800, 1200)
	for i in 30:
		await process_frame
	root.get_texture().get_image().save_png(a[0])
	print("CAPTURA ", a[0])
	quit()
