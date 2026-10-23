# godot --path godot --script res://scripts/tools/captura_arqueiro_dark_bracers.gd --position 30000,30000 --resolution 320x240 --quit-after N -- pasta_saida
# Capturas das bracadeiras do arqueiro dark (torso desligado para ver os bracos): mao em idle, mirando e montado com o torso. Sai sozinho, tambem no erro.
extends SceneTree
func _init() -> void:
	var a := OS.get_cmdline_user_args()
	var pasta: String = a[0] if a.size() > 0 else "D:/openclaude/_trabalho-claude/tmp/arq_dark_bracers"
	DirAccess.make_dir_recursive_absolute(pasta)
	var sv := SubViewport.new(); sv.size = Vector2i(1024, 1024); sv.render_target_update_mode = SubViewport.UPDATE_ALWAYS; sv.msaa_3d = Viewport.MSAA_4X
	root.add_child(sv)
	var cena := load("res://scenes/teste/ArqueiroDarkTeste.tscn") as PackedScene
	if cena == null:
		push_error("cena de teste nao carregou"); quit(1); return
	var t := cena.instantiate()
	sv.add_child(t)
	for i in 30: await process_frame
	for l in t.find_children("*", "Label", true, false):
		l.visible = false
	t.DefinirSlot("torso", false)
	t.DefinirSlot("aljava", false)
	var tiros := [
		["mao_34", "Idle", 0.0, Vector3(0.33, 0.96, 0.05), 40.0, 0.18, 1.05, 28.0],
		["mao_costas", "Idle", 0.0, Vector3(0.33, 0.96, 0.05), 150.0, 0.18, 1.05, 28.0],
		["corpo_idle", "Idle", 0.0, Vector3(0.0, 1.05, 0.0), 35.0, 0.12, 2.6, 30.0],
		["mirar", "AimIdle", 0.6, Vector3(0.0, 1.2, 0.0), 40.0, 0.12, 2.2, 30.0],
	]
	for s in tiros:
		t.Congelar(s[1], s[2])
		for i in 6: await process_frame
		var yaw: float = deg_to_rad(s[4])
		var alvo: Vector3 = s[3]
		var dir := Vector3(sin(yaw), float(s[5]), cos(yaw)).normalized()
		var pos: Vector3 = alvo + dir * float(s[6])
		t.Camera.fov = float(s[7])
		t.Camera.look_at_from_position(pos, alvo, Vector3.UP)
		for i in 8: await process_frame
		var img := sv.get_texture().get_image()
		if img == null or img.is_empty():
			push_error("imagem vazia"); quit(1); return
		img.save_png("%s/godot_bracers_%s.png" % [pasta, s[0]])
	t.DefinirSlot("torso", true)
	t.DefinirSlot("aljava", true)
	t.Congelar("Idle", 0.0)
	t.Camera.fov = 30.0
	t.Camera.look_at_from_position(Vector3(1.0, 1.4, 2.6), Vector3(0, 1.0, 0), Vector3.UP)
	for i in 8: await process_frame
	sv.get_texture().get_image().save_png("%s/godot_bracers_montado.png" % pasta)
	print("CAPTURA OK ", pasta)
	quit(0)
