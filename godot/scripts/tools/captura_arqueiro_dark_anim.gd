# godot --path godot --position 30000,30000 --resolution 320x240 --script res://scripts/tools/captura_arqueiro_dark_anim.gd -- pasta_saida
# Capturas do arqueiro dark animado: clipe e frame definidos abaixo, cada um em frente, lado e 3/4 do jogo.
# Tambem imprime a altura minima dos pes/dedos em cada clipe (pes nao afundam nem flutuam). Sai sozinho, tambem no erro.
extends SceneTree
# clipe, tempo (s) congelado
const CAPTURAS := [["Idle", 0.5], ["AimIdle", 1.0], ["Walk", 0.25], ["Dodge", 0.3]]
# indice da vista em ArqueiroDarkTeste.Vistas, nome
const VISTAS := [[2, "frente"], [4, "lado"], [0, "3q_jogo"], [3, "costas"]]
func _init() -> void:
	var a := OS.get_cmdline_user_args()
	var pasta: String = a[0] if a.size() > 0 else "D:/openclaude/_trabalho-claude/tmp/arq_anim"
	DirAccess.make_dir_recursive_absolute(pasta)
	var sv := SubViewport.new(); sv.size = Vector2i(1280, 960); sv.render_target_update_mode = SubViewport.UPDATE_ALWAYS; sv.msaa_3d = Viewport.MSAA_4X
	root.add_child(sv)
	var cena := load("res://scenes/teste/ArqueiroDarkTeste.tscn") as PackedScene
	if cena == null:
		push_error("cena de teste nao carregou"); quit(1); return
	var t := cena.instantiate()
	sv.add_child(t)
	for i in 30: await process_frame
	var arq = t.Arqueiro
	var ap: AnimationPlayer = arq.Animacoes
	var sk: Skeleton3D = arq.Esqueleto
	if ap == null or ap.get_animation_list().is_empty():
		push_error("sem clipes no corpo dark"); quit(1); return
	# pes: altura do mundo (y) de pe e dedos ao longo de cada clipe
	for nome in ["Idle", "Walk", "Run", "AimIdle", "Dodge", "Draw", "Release"]:
		var an := ap.get_animation("AN_Arqueiro_" + nome)
		var mn := {"LeftFoot": 9.0, "RightFoot": 9.0, "LeftToes": 9.0, "RightToes": 9.0}
		var mx := {"LeftFoot": -9.0, "RightFoot": -9.0, "LeftToes": -9.0, "RightToes": -9.0}
		var hips_mn := 9.0; var hips_mx := -9.0
		var tt := 0.0
		while tt <= an.length + 0.0001:
			ap.play("AN_Arqueiro_" + nome); ap.seek(tt, true); ap.pause()
			for b in mn.keys():
				var y := sk.get_bone_global_pose(sk.find_bone(b)).origin.y
				mn[b] = minf(mn[b], y); mx[b] = maxf(mx[b], y)
			var hy := sk.get_bone_global_pose(sk.find_bone("Hips")).origin.y
			hips_mn = minf(hips_mn, hy); hips_mx = maxf(hips_mx, hy)
			tt += 1.0 / 15.0
		print("PES ", nome, " hips y ", snappedf(hips_mn, 0.001), "..", snappedf(hips_mx, 0.001), " | pe E ", snappedf(mn["LeftFoot"], 0.001), "..", snappedf(mx["LeftFoot"], 0.001), " pe D ", snappedf(mn["RightFoot"], 0.001), "..", snappedf(mx["RightFoot"], 0.001), " dedos E min ", snappedf(mn["LeftToes"], 0.001), " D min ", snappedf(mn["RightToes"], 0.001))
	for c in CAPTURAS:
		t.Congelar(c[0], c[1])
		for v in VISTAS:
			t.DefinirVista(v[0])
			for i in 6: await process_frame
			var img := sv.get_texture().get_image()
			if img == null or img.is_empty():
				push_error("imagem vazia (driver dummy?)"); quit(1); return
			img.save_png("%s/godot_anim_%s_%s.png" % [pasta, String(c[0]).to_lower(), v[1]])
	# detalhe da mao do arco (mirar): camera junto da mao esquerda, de frente e de lado
	t.Congelar("AimIdle", 1.0)
	var mao := sk.global_transform * sk.get_bone_global_pose(sk.find_bone("LeftHand")).origin
	var cam: Camera3D = t.Camera
	cam.fov = 40.0
	for d in [["frente", Vector3(0, 0.1, 1.6)], ["lado", Vector3(1.6, 0.1, 0.0)], ["3q", Vector3(1.1, 0.4, 1.1)]]:
		cam.global_position = mao + d[1]
		cam.look_at(mao, Vector3.UP)
		for i in 6: await process_frame
		var img2 := sv.get_texture().get_image()
		img2.save_png("%s/godot_anim_mirar_mao_%s.png" % [pasta, d[0]])
	print("CAPTURA ANIM OK ", pasta)
	quit(0)
