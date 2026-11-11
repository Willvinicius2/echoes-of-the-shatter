extends SceneTree
## Vídeo das habilidades físicas do Arqueiro (doc 39) no jogo real: cena principal (mundo no SubViewport de pixel art),
## fase aberta com a horda de verdade. Uma habilidade por vez no slot 1, com o nome na legenda. Precisa de janela (xvfb):
##   godot --rendering-driver opengl3 --path godot --write-movie saida.avi --fixed-fps 30 --resolution 1280x720 \
##         --script res://scripts2d/tools/video_fisico_2d.gd -- 5 power_shot sniper_shot
## Primeiro argumento: segundos por habilidade. Os demais: ids (padrão: as 11 dos ramos Precisão, Caçada e Sombra).
## A palavra `horda` entre os ids deixa a horda real vir junto (padrão: só alvos de treino parados).
## Com `--` e a palavra `foto` no lugar dos segundos, grava PNGs em vez de filme: foto pasta id [id...].
const MainScene = preload("res://scenes2d/Main2D.tscn")
const Csv = preload("res://scripts2d/csv2d.gd")
const Efeitos = preload("res://scripts2d/efeitos_arqueiro_2d.gd")
const IDS := ["power_shot", "sniper_shot", "rapid_volley", "fan_of_arrows", "arrow_rain", "spike_trap", "explosive_arrow",
	"hunters_mark", "backstep_shot", "smoke_bomb", "adrenaline"]

var run
var p
var legenda: Label
var _treino: Array = []
var horda := false   # argumento `horda` no fim: deixa a horda de verdade vir junto

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var foto: bool = args.size() > 0 and args[0] == "foto"
	var pasta: String = args[1] if foto and args.size() > 1 else ""
	var dur: float = 5.0 if foto or args.is_empty() else float(args[0])
	var ids: Array = args.slice(2 if foto else 1)
	if ids.has("horda"):
		horda = true
		ids.erase("horda")
	if ids.is_empty():
		ids = IDS
	var main = MainScene.instantiate()
	root.add_child(main)
	await physics_frame
	run = main.run
	run.menus.fechar()
	run.estado = run.Estado.LUTA
	paused = false
	p = run.player
	p.god_mode = true
	p.autocast = false   # sem o tiro básico: só a habilidade em cena
	var ui := CanvasLayer.new()
	ui.layer = 50
	root.add_child(ui)
	legenda = Label.new()
	legenda.position = Vector2(40, 24)
	legenda.add_theme_font_size_override("font_size", 34)
	legenda.add_theme_color_override("font_color", Color(1, 0.95, 0.8))
	legenda.add_theme_color_override("font_outline_color", Color(0, 0, 0))
	legenda.add_theme_constant_override("outline_size", 8)
	ui.add_child(legenda)
	if foto:
		DirAccess.make_dir_recursive_absolute(pasta)
	for i in 60:   # a primeira onda chega
		await _passo()
	for id in ids:
		await _mostrar(id, dur, pasta)
	quit()

func _passo() -> void:
	if run.ui.aberta:
		run.ui.escolher(0)
	if not horda:   # palco limpo: só os alvos de treino, sem XP nem cartas no meio da demonstração
		for e in get_nodes_in_group("hurtable"):
			if not _treino.has(e):
				e.queue_free()
	await physics_frame

func _aprender(h: RefCounted, id: String) -> void:
	var pai: String = h.defs[id]["pai"]
	if pai != "" and h.nivel(pai) == 0:
		_aprender(h, pai)
	if h.nivel(id) == 0:
		h.ganhar_pontos(int(h.defs[id].get("pontos", 1)))
		h.aprender(id)

func _mostrar(id: String, dur: float, pasta: String) -> void:
	var h: RefCounted = p.habilidades
	_aprender(h, id)
	for s in h.SLOTS:   # slots vazios: a habilidade é disparada daqui, uma vez a cada 2,5 s, sem depender da recarga
		h.equipar(s, "")
	legenda.text = Csv.t("skill.%s.name" % id)
	_alvos()
	var passos := int(dur * float(Engine.physics_ticks_per_second))
	for i in passos:
		if i % 150 == 2:
			var d: Dictionary = h.def_nivel(id)
			var alvo: Dictionary = h.alvo_auto(id, self, p.global_position, 700.0)
			var dir: Vector2 = alvo.get("dir", Vector2.RIGHT)
			p.alvo_ponto = alvo.get("ponto", Vector2.INF)
			p.facing = dir
			Efeitos.executar(d["efeito"], p, d, 1, dir)
			p.alvo_ponto = Vector2.INF
		await _passo()
		if pasta != "" and i % 3 == 0 and i >= 3:
			await RenderingServer.frame_post_draw
			root.get_viewport().get_texture().get_image().save_png("%s/%s_%02d.png" % [pasta, id, i / 3])

## Alvos de treino resistentes à direita do arqueiro, para a habilidade ter em quem acertar desde o primeiro quadro.
func _alvos() -> void:
	for e in _treino:
		if is_instance_valid(e):
			e.queue_free()
	_treino.clear()
	for q in [Vector2(200, -90), Vector2(280, 40), Vector2(380, -40), Vector2(460, 90), Vector2(330, 150), Vector2(540, -10)]:
		var e = load("res://scripts2d/enemy_2d.gd").new()
		p.get_parent().add_child(e)
		e.setup("skeleton_soldier", p, p.global_position + q)
		e.hp_max = 99999.0
		e.hp = 99999.0
		e.stats["damage"] = 0.0
		e._speed = 0.0   # parados: dá para ler a habilidade
		_treino.append(e)
