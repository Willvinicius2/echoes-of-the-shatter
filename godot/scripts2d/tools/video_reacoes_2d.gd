extends SceneTree
## Vídeo das reações elementais, das resistências e do mapa (doc 38) numa arena limpa, uma cena por reação com legenda.
## Precisa de janela (xvfb):
##   godot --rendering-driver opengl3 --path godot --write-movie saida.avi --fixed-fps 30 --resolution 1280x720 \
##         --script res://scripts2d/tools/video_reacoes_2d.gd
const Reacoes = preload("res://scripts2d/reacoes_2d.gd")
const Gelo = preload("res://scripts2d/efeitos_arqueiro_gelo_2d.gd")
const Arena = preload("res://scripts2d/tools/arena_reacoes_2d.gd")

var mundo: Node2D
var arena: Node2D
var legenda: Label
var sub: Label
var jogador: Node2D
var vivos: Array = []
var _n := 0         # cena atual (1 = primeira)
var _desde := 1     # primeiro argumento depois de `--`: pula as cenas anteriores (conferir só o fim do vídeo)

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	_desde = int(args[0]) if args.size() > 0 else 1
	mundo = Node2D.new()
	root.add_child(mundo)
	arena = Arena.new()
	arena.add_to_group("sala_2d")
	mundo.add_child(arena)
	jogador = load("res://scripts2d/player_2d.gd").new()
	jogador.god_mode = true
	jogador.autocast = false
	jogador.global_position = Vector2(-3000, -3000)
	mundo.add_child(jogador)
	var cam := Camera2D.new()
	cam.position = Vector2(640, 400)
	cam.zoom = Vector2(1.2, 1.2)
	mundo.add_child(cam)
	var ui := CanvasLayer.new()
	root.add_child(ui)
	legenda = _rotulo(ui, 34, Vector2(40, 24))
	sub = _rotulo(ui, 22, Vector2(40, 74))
	await _roteiro()
	quit()

func _rotulo(ui: CanvasLayer, tam: int, pos: Vector2) -> Label:
	var l := Label.new()
	l.position = pos
	l.add_theme_font_size_override("font_size", tam)
	l.add_theme_color_override("font_color", Color(1, 0.95, 0.8))
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0))
	l.add_theme_constant_override("outline_size", 8)
	ui.add_child(l)
	return l

func _inim(id: String, pos: Vector2, ferido := true) -> Node2D:
	var e = load("res://scripts2d/enemy_2d.gd").new()
	mundo.add_child(e)
	e.setup(id, jogador, pos)
	e.stats["aggro"] = 0.0
	e.hp_max = 100000.0
	e.hp = 80000.0 if ferido else 100000.0   # ferido: a barra de vida (e os ícones de resistência) aparece
	vivos.append(e)
	return e

func _limpar() -> void:
	for e in vivos:
		if is_instance_valid(e):
			e.free()
	vivos.clear()

func _esperar(s: float) -> void:
	if _n < _desde:
		await physics_frame
		return
	for i in int(s * float(Engine.physics_ticks_per_second)):
		await physics_frame

func _cena(titulo: String, texto: String) -> void:
	_n += 1
	_limpar()
	for est in arena._estruturas:
		est["apagado"] = 0
		est["ate"] = 0
	legenda.text = titulo
	sub.text = texto
	await _esperar(0.4)

func _roteiro() -> void:
	await _esperar(0.5)
	# 1 resistências
	await _cena("Resistências: o ícone ao lado da barra de vida", "seta vermelha = sofre mais · seta cinza = resiste · corte vermelho = imune")
	var cao := _inim("ash_hound", Vector2(470, 330))
	var esq := _inim("skeleton_soldier", Vector2(640, 330))
	var fan := _inim("wandering_ghost", Vector2(810, 330))
	await _esperar(0.6)
	cao.aplicar_status("queimadura", 3.0, 10.0)
	esq.aplicar_status("veneno", 3.0, 5.0)
	fan.aplicar_status("choque", 3.0, 0.15)
	await _esperar(2.8)
	# 2 vapor
	await _cena("Vapor", "fogo em alvo com frio: nuvem que fere em volta e apaga o frio")
	var a := _inim("hollow_sentinel", Vector2(600, 320))
	_inim("hollow_sentinel", Vector2(690, 330))
	a.set_meta("frio_acumulos", 2)
	a.aplicar_status("lentidao", 4.0, 0.3)
	await _esperar(1.0)
	a.aplicar_status("queimadura", 3.0, 2.0)
	await _esperar(2.0)
	# 3 gás inflamado
	await _cena("Gás Inflamado", "fogo em alvo envenenado: explosão proporcional ao veneno")
	a = _inim("hollow_sentinel", Vector2(600, 320))
	_inim("hollow_sentinel", Vector2(700, 340))
	a.aplicar_status("veneno", 4.0, 6.0)
	await _esperar(1.0)
	a.aplicar_status("queimadura", 3.0, 2.0)
	await _esperar(2.0)
	# 4 quebra gélida
	await _cena("Quebra Gélida", "raio em alvo congelado: o gelo estilhaça e congela os vizinhos")
	a = _inim("hollow_sentinel", Vector2(600, 320))
	_inim("hollow_sentinel", Vector2(700, 340))
	Gelo.congelar(a, 4.0)
	await _esperar(1.0)
	a.aplicar_status("choque", 3.0, 0.15)
	await _esperar(2.0)
	# 5 corrente tóxica
	await _cena("Corrente Tóxica", "raio em alvo envenenado: o veneno salta por arcos")
	a = _inim("hollow_sentinel", Vector2(560, 320))
	_inim("hollow_sentinel", Vector2(690, 300))
	_inim("hollow_sentinel", Vector2(700, 370))
	_inim("hollow_sentinel", Vector2(790, 330))
	a.aplicar_status("veneno", 4.0, 6.0)
	await _esperar(1.0)
	a.aplicar_status("choque", 3.0, 0.15)
	await _esperar(2.0)
	# 6 condução na água
	await _cena("Condução na Água", "raio em alvo na margem do riacho: a corrente corre pela água")
	a = _inim("hollow_sentinel", Vector2(500, 520))
	_inim("hollow_sentinel", Vector2(650, 530))
	_inim("hollow_sentinel", Vector2(800, 520))
	_inim("hollow_sentinel", Vector2(650, 330))   # fora da água: não conduz
	await _esperar(1.0)
	a.aplicar_status("choque", 3.0, 0.15)
	await _esperar(2.2)
	# 7 apagar fogo
	await _cena("Apagar Fogo", "a água apaga a chama: a queimadura não pega (à esquerda, em terra seca, pega)")
	a = _inim("hollow_sentinel", Vector2(520, 520))
	var seco := _inim("hollow_sentinel", Vector2(800, 340))
	await _esperar(1.0)
	a.aplicar_status("queimadura", 3.0, 2.0)
	seco.aplicar_status("queimadura", 3.0, 2.0)
	await _esperar(2.2)
	# 8 braseiro + fogo
	await _cena("Braseiro + fogo: labareda", "o braseiro do mapa se alimenta da chama e queima quem está em volta")
	a = _inim("hollow_sentinel", Vector2(390, 340))
	_inim("hollow_sentinel", Vector2(300, 360))
	_inim("hollow_sentinel", Vector2(470, 360))
	await _esperar(1.0)
	a.aplicar_status("queimadura", 3.0, 2.0)
	await _esperar(2.2)
	# 9 braseiro + raio
	await _cena("Braseiro + raio: descarga", "a brasa solta arcos e choca os 2 inimigos mais perto")
	a = _inim("hollow_sentinel", Vector2(390, 340))
	_inim("hollow_sentinel", Vector2(300, 360))
	_inim("hollow_sentinel", Vector2(470, 360))
	await _esperar(1.0)
	a.aplicar_status("choque", 3.0, 0.15)
	await _esperar(2.2)
	# 10 braseiro + gelo
	await _cena("Braseiro + gelo: apaga", "o frio apaga o braseiro por 5 s; sem chama, o fogo não faz labareda")
	a = _inim("hollow_sentinel", Vector2(390, 340))
	var b := _inim("hollow_sentinel", Vector2(470, 360))
	await _esperar(1.0)
	a.set_meta("frio_acumulos", 1)
	a.aplicar_status("lentidao", 3.0, 0.2)
	await _esperar(1.2)
	b.aplicar_status("queimadura", 3.0, 2.0)   # braseiro apagado: nada de labareda
	await _esperar(1.8)
	# 11 pilar + raio
	await _cena("Pilar + raio: para-raios", "o pilar atrai o raio e descarrega nos inimigos próximos")
	a = _inim("hollow_sentinel", Vector2(960, 340))
	_inim("hollow_sentinel", Vector2(880, 360))
	_inim("hollow_sentinel", Vector2(1040, 360))
	await _esperar(1.0)
	a.aplicar_status("choque", 3.0, 0.15)
	await _esperar(2.4)
	_limpar()
