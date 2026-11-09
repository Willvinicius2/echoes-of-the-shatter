extends SceneTree
## Capturas do fluxo de fases para revisão (docs/design/34_fases_e_desbloqueio.md), pela cena principal (Main2D; precisa
## de janela, use xvfb):
##   godot --path godot --rendering-driver opengl3 --resolution 1600x900 --script res://scripts2d/tools/captura_fases_2d.gd -- <prefixo>
## Grava <prefixo>_a_titulo_cripta.png, _b_titulo_pedreira_trancada.png, _c_titulo_pedreira_em_breve.png (tabela real,
## Cripta vencida, sem fase_2.txt), _c2_titulo_pedreira_aberta.png (tabela de teste, a Pedreira na sala da fase_1),
## _d_fim_desbloqueio.png e, numa corrida da Pedreira na sala da fase_1 (data2d/testes/fases_teste.csv), o elite do
## portão no meio da entrada (_e1_elite_entrada.png) e depois com a barra grande (_e2_elite_barra.png).
## Usa saves próprios em user:// (não mexe no save do jogo).

const MainScene = preload("res://scenes2d/Main2D.tscn")
const MetaScript = preload("res://scripts2d/meta_2d.gd")
const OpcoesScript = preload("res://scripts2d/opcoes_2d.gd")
const Fase = preload("res://scripts2d/fase_2d.gd")
const TABELA_TESTE := "res://data2d/testes/fases_teste.csv"

var prefixo := "captura_fases"

func _foto(nome: String, quadros := 20) -> void:
	for i in quadros:
		await process_frame
	await RenderingServer.frame_post_draw
	root.get_viewport().get_texture().get_image().save_png("%s_%s.png" % [prefixo, nome])
	print("captura: ", nome)

func _escolher_tudo(run) -> void:
	var n := 0
	while run.ui.aberta and n < 50:
		run.ui.escolher(0)
		n += 1

func _initialize() -> void:
	create_timer(240.0).timeout.connect(func():
		push_error("captura_fases_2d: tempo esgotado (240 s)")
		quit(2))
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		prefixo = args[0]
	MetaScript.caminho = "user://captura_fases_meta.json"
	OpcoesScript.caminho = "user://captura_fases_opcoes.json"
	for p in [MetaScript.caminho, MetaScript.caminho_fases(), OpcoesScript.caminho]:
		DirAccess.remove_absolute(p)
	var o = OpcoesScript.new()
	o.prologo_visto = true
	o.tutorial_visto = true
	o.salvar()
	Fase.tabela = "res://data2d/fases_2d.csv"
	var main = MainScene.instantiate()
	root.add_child(main)
	await physics_frame
	var run = main.run
	var m = run.menus
	m.mostrar_titulo()
	await _foto("a_titulo_cripta")
	m.trocar_fase(1)
	await _foto("b_titulo_pedreira_trancada")
	run.meta.vencer_fase("cripta")
	m.mostrar_titulo()
	await _foto("c_titulo_pedreira_em_breve")
	Fase.tabela = TABELA_TESTE
	m.mostrar_titulo()
	await _foto("c2_titulo_pedreira_aberta")
	# Tela de fim da primeira vitória na Cripta (o aviso sai uma vez).
	run._fases_novas = ["pedreira"]
	run.estado = run.Estado.VENCEU
	run.tempo = 412.0
	run._mostrar_fim()
	await _foto("d_fim_desbloqueio")
	# Corrida da Pedreira na sala da fase_1: ondas até o portão poder despertar, depois o elite.
	m.fechar()
	paused = false
	Fase.definir("pedreira")
	run._on_jogar()
	await physics_frame
	var p = run.player
	p.god_mode = true
	p.autocast = false
	var t0 := Time.get_ticks_msec()
	while int(run.nucleo.ondas_estado()["can_wake"]) != 0 and Time.get_ticks_msec() - t0 < 60000:
		run._tick_horda(2.0)
		run.matar_todos()
		_escolher_tudo(run)
		await physics_frame
	run.matar_todos()
	await physics_frame
	_escolher_tudo(run)
	for g in get_nodes_in_group("coletaveis"):
		if not g.fixo:
			g.queue_free()   # sem gemas no chão: nada de carta abrindo no meio da foto
	paused = false
	run.camera.limit_top = -100000   # o portão G fica na borda de cima do mapa: solta a câmera para enquadrar a entrada
	p.global_position = run.room.posicao_chefe + Vector2(-110, 70)
	p.velocity = Vector2.ZERO
	run.camera.position = p.global_position
	run.camera.reset_smoothing()
	for i in 20:
		await physics_frame
	run.acordar_chefe()
	await _foto("e1_elite_entrada", 2)   # com janela virtual cada quadro demora: 2 quadros já pegam o clarão no alto
	# Depois da entrada: sem a horda em volta (foto limpa), o capitão vem atrás do jogador com a barra grande.
	for n in get_nodes_in_group("hurtable"):
		if not n.has_meta("chefe_portao"):
			n.queue_free()
	await create_timer(float(run.config.get("gate_elite_intro", 1.4))).timeout
	await _foto("e2_elite_barra", 2)
	quit()
