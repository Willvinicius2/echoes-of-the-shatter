extends Node2D
## Corrida 2D: salas em sequência (data2d/run.csv), chefe na última, morte reinicia em segundos.
## O cliente só apresenta; as regras da corrida migram para o módulo `run` do ShatterCore (pacote 2).

const Csv = preload("res://scripts2d/csv2d.gd")
const RoomScript = preload("res://scripts2d/room_2d.gd")
const PlayerScript = preload("res://scripts2d/player_2d.gd")
const EnemyScript = preload("res://scripts2d/enemy_2d.gd")
const BossScript = preload("res://scripts2d/boss_2d.gd")
const HudScript = preload("res://scripts2d/hud_2d.gd")
const UpgradesScript = preload("res://scripts2d/upgrades_2d.gd")
const UpgradeUiScript = preload("res://scripts2d/upgrade_ui_2d.gd")
const MenusScript = preload("res://scripts2d/menus_2d.gd")
const MetaScript = preload("res://scripts2d/meta_2d.gd")
const Audio = preload("res://scripts2d/audio_2d.gd")

enum Estado { LUTA, LIMPA, MORTO, VENCEU, ESCOLHA, MENU, PAUSA, TRANSICAO }

var config := {}
var salas: Array = []
var indice := 0
var estado := Estado.LUTA
var rng := RandomNumberGenerator.new()
var room: Node2D
var player: Node2D
var hud: CanvasLayer
var upgrades: RefCounted
var meta: RefCounted
var ganhos := {"fragmentos": 0, "materiais": {}}   # da corrida atual; vão ao save quando ela acaba
var ui: CanvasLayer
var menus: CanvasLayer
var com_menu := true   # false nos testes: começa direto na sala 1
var tempo := 0.0       # segundos da corrida atual (só conta luta e sala limpa)
var camera: Camera2D
var atores: Node2D
var vivos := 0
var corridas := 0
var _timer := 0.0
var _estado_antes := Estado.LUTA

func _ready() -> void:
	config = Csv.kv("res://data2d/run_settings.csv")
	salas = Csv.rows("res://data2d/run.csv")
	atores = Node2D.new()
	atores.y_sort_enabled = true
	add_child(atores)
	player = PlayerScript.new()
	player.died.connect(_on_player_died)
	atores.add_child(player)
	camera = Camera2D.new()
	camera.process_callback = Camera2D.CAMERA2D_PROCESS_PHYSICS
	add_child(camera)
	meta = MetaScript.new()
	meta.carregar()
	upgrades = UpgradesScript.new()
	upgrades.meta = meta
	hud = HudScript.new()
	hud.jogador = player
	hud.upgrades = upgrades
	hud.total_salas = salas.size()
	add_child(hud)
	ui = UpgradeUiScript.new()
	ui.upgrades = upgrades
	ui.escolhido.connect(_on_upgrade_escolhido)
	add_child(ui)
	menus = MenusScript.new()
	menus.meta = meta
	menus.jogar.connect(_on_jogar)
	menus.retomar.connect(_on_retomar)
	menus.ao_titulo.connect(_ir_titulo)
	menus.pausa_pedida.connect(_on_pausa_pedida)
	menus.sair.connect(get_tree().quit)
	add_child(menus)
	Audio.musica("music_cripta")
	iniciar_corrida()
	if com_menu:
		_ir_titulo()

func iniciar_corrida() -> void:
	_creditar_ganhos()  # corrida abandonada (reiniciar, título) também guarda o que já rendeu
	rng.seed = int(config["seed"]) + corridas
	corridas += 1
	indice = 0
	tempo = 0.0
	menus.limpar_fade()
	upgrades.restaurar(player)  # stats base de volta antes do reset do jogador
	player.reset()
	_carregar_sala(0)

func _carregar_sala(i: int) -> void:
	if room != null:
		room.queue_free()
	for n in get_tree().get_nodes_in_group("hurtable"):
		n.queue_free()
	for n in atores.get_children():
		if n != player:
			n.queue_free()
	room = RoomScript.new()
	add_child(room)
	move_child(room, 0)
	room.carregar(salas[i]["room"])
	room.colocar_props(atores)
	room.porta_usada.connect(_on_porta)
	player.global_position = room.spawn_jogador
	player.velocity = Vector2.ZERO
	hud.sala = i + 1
	hud.mensagem = ""
	hud.chefe = null
	_ajustar_camera()
	_spawn_inimigos(salas[i]["enemies"])
	estado = Estado.LUTA

func _ajustar_camera() -> void:
	var vp := get_viewport_rect().size
	var tam: Vector2 = room.tamanho_px()
	camera.position = tam / 2.0
	var z := minf(vp.x / tam.x, vp.y / tam.y)
	camera.zoom = Vector2(z, z)

func _spawn_inimigos(spec: String) -> void:
	var pontos: Array = room.spawns_inimigos.duplicate()
	for i in range(pontos.size() - 1, 0, -1):
		var j := rng.randi_range(0, i)
		var tmp = pontos[i]
		pontos[i] = pontos[j]
		pontos[j] = tmp
	var k := 0
	vivos = 0
	for parte in spec.split("|"):
		var p := parte.split(":")
		for n in int(p[1]):
			var e: Node2D = (BossScript if Csv.enemy(p[0])["kind"] == "boss" else EnemyScript).new()
			atores.add_child(e)
			e.setup(p[0], player, pontos[k % pontos.size()])
			e.died.connect(_on_inimigo_morto)
			k += 1
			vivos += 1

func _on_inimigo_morto(e) -> void:
	vivos -= 1
	var d: Dictionary = meta.drop_de(e.stats.get("id", ""))
	if not d.is_empty():
		ganhos["fragmentos"] += d["fragmentos"]
		ganhos["materiais"][d["material"]] = int(ganhos["materiais"].get(d["material"], 0)) + d["material_qtd"]
	if vivos <= 0 and estado == Estado.LUTA:
		estado = Estado.LIMPA
		_timer = config["clear_delay"]
		ganhos["fragmentos"] += int(config["room_clear_fragments"])

func _physics_process(delta: float) -> void:
	if estado == Estado.LUTA or estado == Estado.LIMPA:
		tempo += delta
	hud.tempo = tempo
	if _timer > 0.0:
		_timer -= delta
		if _timer <= 0.0:
			match estado:
				Estado.LIMPA:
					var cartas: Array = upgrades.sortear(rng, int(config["upgrade_cards"])) if indice + 1 < salas.size() else []
					if cartas.is_empty():
						_abrir_porta()
					else:
						estado = Estado.ESCOLHA
						ui.abrir(cartas)
				Estado.MORTO, Estado.VENCEU:
					_mostrar_fim()

func _abrir_porta() -> void:
	room.abrir_porta()
	Audio.tocar("door_open")
	hud.mensagem = Csv.t("hud.room_clear")
	estado = Estado.LIMPA

func _on_upgrade_escolhido(id: String) -> void:
	upgrades.escolher(id, player)
	_abrir_porta()

func _on_porta() -> void:
	if estado != Estado.LIMPA or _timer > 0.0 or not room.celulas_porta.size():
		return
	if indice + 1 >= salas.size():
		estado = Estado.VENCEU
		hud.mensagem = Csv.t("hud.victory")
		Audio.tocar("victory")
		ganhos["fragmentos"] += int(config["victory_fragments"])
		_timer = config["restart_delay"]
		return
	indice += 1
	estado = Estado.TRANSICAO
	menus.transicao(config["room_fade"], func(): _carregar_sala(indice))

func _on_player_died() -> void:
	estado = Estado.MORTO
	hud.mensagem = Csv.t("hud.dead")
	Audio.tocar("defeat")
	_timer = config["restart_delay"]

func _creditar_ganhos() -> void:
	if int(ganhos["fragmentos"]) == 0 and ganhos["materiais"].is_empty():
		return
	meta.creditar(ganhos)
	ganhos = {"fragmentos": 0, "materiais": {}}

func _mostrar_fim() -> void:
	hud.mensagem = ""
	var mats := []
	for m in ganhos["materiais"]:
		mats.append("%s x%d" % [Csv.t("material." + m), ganhos["materiais"][m]])
	var resumo := [
		Csv.t("menu.sum_time") % formatar_tempo(tempo),
		Csv.t("menu.sum_rooms") % [indice + 1, salas.size()],
		Csv.t("menu.sum_upgrades") % _total_upgrades(),
		Csv.t("menu.sum_fragments") % int(ganhos["fragmentos"]),
	]
	if not mats.is_empty():
		resumo.append(Csv.t("menu.sum_materials") % ", ".join(mats))
	_creditar_ganhos()
	menus.mostrar_fim(estado == Estado.VENCEU, resumo)
	get_tree().paused = true

func _total_upgrades() -> int:
	var n := 0
	for id in upgrades.niveis:
		n += int(upgrades.niveis[id])
	return n

static func formatar_tempo(seg: float) -> String:
	var total := int(seg)
	return "%02d:%02d" % [total / 60, total % 60]

func _ir_titulo() -> void:
	iniciar_corrida()
	estado = Estado.MENU
	get_tree().paused = true
	menus.mostrar_titulo()

func _on_jogar() -> void:
	menus.fechar()
	get_tree().paused = false
	meta.preparar_corrida()  # consumíveis da Forja valem a partir desta corrida
	iniciar_corrida()

func _on_pausa_pedida() -> void:
	if estado != Estado.LUTA and estado != Estado.LIMPA:
		return
	_estado_antes = estado
	estado = Estado.PAUSA
	get_tree().paused = true
	menus.mostrar_pausa()

func _on_retomar() -> void:
	menus.fechar()
	get_tree().paused = false
	estado = _estado_antes

## Atalho de teste/depuração: mata todos os inimigos vivos.
func matar_todos() -> void:
	for n in get_tree().get_nodes_in_group("hurtable"):
		n.take_damage(1.0e9)
