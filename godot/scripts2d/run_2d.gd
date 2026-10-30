extends Node2D
## Corrida 2D: salas em sequência (data2d/run.csv), chefe na última, morte reinicia em segundos.
## O cliente só apresenta; as regras da corrida migram para o módulo `run` do ShatterCore (pacote 2).

const Csv = preload("res://scripts2d/csv2d.gd")
const RoomScript = preload("res://scripts2d/room_2d.gd")
const PlayerScript = preload("res://scripts2d/player_2d.gd")
const EnemyScript = preload("res://scripts2d/enemy_2d.gd")
const HudScript = preload("res://scripts2d/hud_2d.gd")
const UpgradesScript = preload("res://scripts2d/upgrades_2d.gd")
const UpgradeUiScript = preload("res://scripts2d/upgrade_ui_2d.gd")

enum Estado { LUTA, LIMPA, MORTO, VENCEU, ESCOLHA }

var config := {}
var salas: Array = []
var indice := 0
var estado := Estado.LUTA
var rng := RandomNumberGenerator.new()
var room: Node2D
var player: Node2D
var hud: CanvasLayer
var upgrades: RefCounted
var ui: CanvasLayer
var camera: Camera2D
var atores: Node2D
var vivos := 0
var corridas := 0
var _timer := 0.0

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
	upgrades = UpgradesScript.new()
	hud = HudScript.new()
	hud.jogador = player
	hud.upgrades = upgrades
	hud.total_salas = salas.size()
	add_child(hud)
	ui = UpgradeUiScript.new()
	ui.upgrades = upgrades
	ui.escolhido.connect(_on_upgrade_escolhido)
	add_child(ui)
	iniciar_corrida()

func iniciar_corrida() -> void:
	rng.seed = int(config["seed"]) + corridas
	corridas += 1
	indice = 0
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
			var e := EnemyScript.new()
			atores.add_child(e)
			e.setup(p[0], player, pontos[k % pontos.size()])
			e.died.connect(_on_inimigo_morto)
			if e.stats["kind"] == "boss":
				hud.chefe = e
			k += 1
			vivos += 1

func _on_inimigo_morto(_e) -> void:
	vivos -= 1
	if vivos <= 0 and estado == Estado.LUTA:
		estado = Estado.LIMPA
		_timer = config["clear_delay"]

func _physics_process(delta: float) -> void:
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
					iniciar_corrida()
	if estado == Estado.MORTO and Input.is_action_just_pressed("renascer"):
		iniciar_corrida()

func _abrir_porta() -> void:
	room.abrir_porta()
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
		_timer = config["restart_delay"]
		return
	indice += 1
	_carregar_sala.call_deferred(indice)

func _on_player_died() -> void:
	estado = Estado.MORTO
	hud.mensagem = Csv.t("hud.dead")
	_timer = config["restart_delay"]

## Atalho de teste/depuração: mata todos os inimigos vivos.
func matar_todos() -> void:
	for n in get_tree().get_nodes_in_group("hurtable"):
		n.take_damage(1.0e9)
