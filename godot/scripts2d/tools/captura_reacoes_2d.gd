extends SceneTree
## Captura em jogo (mapa real, pela Main2D) das reações elementais em pixel art e dos estados do braseiro e do pilar.
## Precisa de janela (xvfb): godot --path godot --resolution 1280x720 --script res://scripts2d/tools/captura_reacoes_2d.gd -- prefixo
## Salva prefixo_1_icones, _2_braseiro_aceso, _3_braseiro_apagado, _4_pilar_descarga, _5_vapor, _6_estilhaco, _7_gas.
const MainScene = preload("res://scenes2d/Main2D.tscn")
const EnemyScript = preload("res://scripts2d/enemy_2d.gd")
var run
var pref := "reacoes"
var meus: Array = []

func _frames(n: int) -> void:
	for i in n:
		await physics_frame

func _tirar(nome: String) -> void:
	await RenderingServer.frame_post_draw
	root.get_viewport().get_texture().get_image().save_png("%s_%s.png" % [pref, nome])

func _inimigo(id: String, pos: Vector2) -> Node2D:
	var e: Node2D = EnemyScript.new()
	run.atores.add_child(e)
	e.setup(id, run.player, pos)
	e.adormecer(1.0)   # parado: a captura mostra o efeito, não a luta
	meus.append(e)
	return e

func _perto(pos: Vector2) -> void:
	run.player.global_position = pos + Vector2(-120, 150)
	for i in 8:   # a onda da corrida segue nascendo: só ficam os inimigos da captura
		for n in get_nodes_in_group("hurtable"):
			if not meus.has(n):
				n.queue_free()
		await _frames(10)

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		pref = args[0]
	var main = MainScene.instantiate()
	root.add_child(main)
	await physics_frame
	run = main.run
	run.menus.fechar()
	run.estado = run.Estado.LUTA
	paused = false
	run.player.god_mode = true
	run.player.set_process(false)   # parado e sem atirar: a captura mostra só a reação
	run.player.set_physics_process(false)
	run.player.visible = false
	var room = run.room
	var br: Dictionary = {}
	var pl: Dictionary = {}
	for e in room._estruturas:
		if e["tipo"] == "braseiro" and br.is_empty():
			br = e
		elif e["tipo"] == "pilar" and pl.is_empty():
			pl = e
	print("braseiro=", br.get("pos"), " pilar=", pl.get("pos"))
	# 1. ícones de resistência: inimigos com a barra de vida visível (levam um golpe leve)
	var base: Vector2 = br["pos"]
	var ids := ["skeleton_soldier", "crypt_bat"]
	for id in ids_com_dica():
		ids.append(id)
	var k := 0
	for id in ids.slice(0, 4):
		var e := _inimigo(id, base + Vector2(-150 + 100 * k, 150))
		e.take_damage(3.0, Vector2.ZERO)
		k += 1
	await _perto(base + Vector2(0, 100))
	await _tirar("1_icones")
	# 2. braseiro aceso, 3. apagado por gelo
	var alvo := _inimigo("skeleton_soldier", base + Vector2(40, 36))
	await _perto(base)
	for n in get_nodes_in_group("hurtable"):
		n.global_position += Vector2(0, 600)   # braseiro isolado: tira os inimigos da frente
	await _frames(5)
	await _tirar("2_braseiro_aceso")
	br["apagado"] = Time.get_ticks_msec() + 30000
	await _frames(10)
	await _tirar("2b_braseiro_apagado_isolado")
	br["apagado"] = 0
	br["carga"] = Time.get_ticks_msec() + 30000
	await _frames(10)
	await _tirar("2c_braseiro_carregado")
	br["carga"] = 0
	await _frames(5)
	for n in get_nodes_in_group("hurtable"):
		n.global_position -= Vector2(0, 600)
	alvo.aplicar_status("lentidao", 3.0, 0.3)   # sem acúmulo de frio não conta como gelo
	alvo.set_meta("frio_acumulos", 1)
	alvo.aplicar_status("lentidao", 3.0, 0.3)
	await _frames(8)
	await _tirar("3_braseiro_apagado")
	# 4. pilar descarregando raio em dois inimigos
	var pp: Vector2 = pl["pos"]
	var a1 := _inimigo("skeleton_soldier", pp + Vector2(30, 40))
	_inimigo("skeleton_soldier", pp + Vector2(-70, 60))
	_inimigo("crypt_bat", pp + Vector2(90, 20))
	await _perto(pp)
	a1.aplicar_status("choque", 2.0, 0.15)
	print("pilar est=", pl.get("est"), " carga=", pl.get("carga"), " dist=", a1.global_position.distance_to(pp))
	await _frames(6)
	await _tirar("4_pilar_descarga")
	# 5. vapor (queimadura em alvo com frio), 6. estilhaço (choque em congelado), 7. gás (queimadura em envenenado)
	var o := base + Vector2(0, 220)
	var v := _inimigo("skeleton_soldier", o)
	_inimigo("crypt_bat", o + Vector2(60, 20))
	v.set_meta("frio_acumulos", 1)
	v.aplicar_status("lentidao", 3.0, 0.3)
	await _perto(o)
	v.aplicar_status("queimadura", 3.0, 3.0)
	await _frames(14)
	await _tirar("5_vapor")
	var g := _inimigo("skeleton_soldier", o + Vector2(260, 0))
	_inimigo("crypt_bat", o + Vector2(320, 20))
	g.aplicar_status("veneno", 4.0, 3.0)
	await _perto(o + Vector2(260, 0))
	g.aplicar_status("queimadura", 3.0, 3.0)
	await _frames(10)
	await _tirar("7_gas")
	var z := _inimigo("skeleton_soldier", o + Vector2(520, 0))
	_inimigo("crypt_bat", o + Vector2(580, 20))
	z.set_meta("congelado_ate", Time.get_ticks_msec() + 5000)
	await _perto(o + Vector2(520, 0))
	z.aplicar_status("choque", 2.0, 0.15)
	await _frames(12)
	await _tirar("6_estilhaco")
	quit()

func ids_com_dica() -> Array:
	var Reacoes = preload("res://scripts2d/reacoes_2d.gd")
	Reacoes.mult("skeleton_soldier", "fogo")
	var out: Array = []
	for id in Reacoes._resist.keys():
		if not Reacoes.dicas(id).is_empty() and DirAccess.dir_exists_absolute("res://art2d/sprites/" + id):   # só inimigo com folha completa
			out.append(id)
	return out
