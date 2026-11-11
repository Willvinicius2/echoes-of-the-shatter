extends SceneTree
## Capturas da luta com a Tecelã de Cascalho (golpes próprios, doc 37): o aviso de cada golpe pouco antes de sair e o efeito logo depois,
## pela cena principal, como o jogador vê. Precisa de janela (xvfb):
##   godot --path godot --resolution 1280x720 --script res://scripts2d/tools/captura_tecela_2d.gd -- pasta
## O jogador fica parado e invulnerável a uns 300 px da chefe; os outros inimigos da sala são removidos para o quadro ficar limpo.
const MainScene = preload("res://scenes2d/Main2D.tscn")
const Fase = preload("res://scripts2d/fase_2d.gd")

var pasta := "tecela"
var run
var _n := 0

func _initialize() -> void:
	create_timer(600.0).timeout.connect(func():
		push_error("captura_tecela_2d: tempo esgotado")
		quit(2))
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		pasta = args[0]
	DirAccess.make_dir_recursive_absolute(pasta)
	Fase.todas_abertas = true
	Fase.atual = "ponte"
	var main = MainScene.instantiate()
	root.add_child(main)
	await physics_frame
	run = main.run
	Fase.definir("ponte")
	run.menus.trocar_fase(0)
	await _quadros(30)
	run.menus._jogar_do_titulo()
	await _quadros(30)
	if run.menus.prologo != null and run.menus.prologo.ativo:
		var k := 0
		while run.menus.prologo.ativo and k < 40:
			await _quadros(5)
			run.menus.prologo.avancar()
			run.menus.prologo.avancar()
			k += 1
	await _quadros(20)
	var p = run.player
	p.god_mode = true
	while int(run.nucleo.ondas_estado().get("wave", 0)) < 6:
		for s in run.nucleo.ondas_tick(0.5):
			run.nucleo.ondas_morto(int(s["id"]))
	p.global_position = run.room.empurrar_para_dentro(run.room.posicao_chefe + Vector2(0, 220))
	var longe: Vector2 = run.room.empurrar_para_dentro(run.room.posicao_chefe + Vector2(0, 520))   # onde o jogador espera depois de a chefe acordar
	var chefe = null
	var t := 0.0
	while chefe == null and t < 30.0:
		await physics_frame
		t += 1.0 / 60.0
		if run.hud.chefe != null and is_instance_valid(run.hud.chefe):
			chefe = run.hud.chefe
	if chefe == null:
		push_error("captura_tecela_2d: a Tecelã não nasceu")
		quit(1)
		return
	chefe._speed = 0.0   # parada: o quadro mostra o golpe e não a perseguição
	p.global_position = longe
	var feitos := {}
	t = 0.0
	var primeiro := true
	while t < 120.0 and feitos.size() < 6:
		await physics_frame
		t += 1.0 / 60.0
		for n in get_nodes_in_group("hurtable"):
			if n != chefe and not n.has_meta("convocado") and (n.get("estado") != null) and n.global_position.distance_to(chefe.global_position) > 0.0:
				if not n.is_in_group("filhote_tecela") and str(n.stats.get("id", "")) != "gravel_spiderling":
					n.queue_free()
		if run.estado == run.Estado.VENCEU or run.estado == run.Estado.MORTO or not is_instance_valid(chefe):
			break
		if primeiro and chefe.entrada_t <= 0.0:
			primeiro = false
			await _foto("0_chefe_enquadrada")
		if chefe._golpe.is_empty():
			continue
		var g: String = chefe._golpe["golpe"]
		var p_aviso: float = 1.0 - chefe._t / maxf(chefe._aviso, 0.01) if not chefe._solto else 1.0
		if not feitos.has("aviso_" + g) and not chefe._solto and p_aviso > 0.75:
			feitos["aviso_" + g] = true
			await _foto("aviso_" + g)
		if not feitos.has("golpe_" + g) and chefe._efeito_feito:
			await _quadros(24)
			feitos["golpe_" + g] = true
			await _foto("golpe_" + g)
	print("[captura_tecela] feitos: ", feitos.keys())
	quit()

func _quadros(n: int) -> void:
	for i in n:
		await process_frame

func _foto(nome: String) -> void:
	await RenderingServer.frame_post_draw
	root.get_viewport().get_texture().get_image().save_png("%s/%02d_%s.png" % [pasta, _n, nome])
	_n += 1
