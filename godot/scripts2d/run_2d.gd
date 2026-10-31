extends Node2D
## Corrida 2D: salas em sequência (data2d/run.csv), chefe na última, morte reinicia em segundos.
## O cliente só apresenta: o fluxo da corrida (etapas, rotas, cartas, ganhos, vitória e derrota) é do módulo `rogue` do ShatterCore.

const Csv = preload("res://scripts2d/csv2d.gd")
const RoomScript = preload("res://scripts2d/room_2d.gd")
const PlayerScript = preload("res://scripts2d/player_2d.gd")
const EnemyScript = preload("res://scripts2d/enemy_2d.gd")
const BossScript = preload("res://scripts2d/boss_2d.gd")
const HudScript = preload("res://scripts2d/hud_2d.gd")
const UpgradesScript = preload("res://scripts2d/upgrades_2d.gd")
const WarriorScript = preload("res://scripts2d/warrior_2d.gd")
const ArvoreUiScript = preload("res://scripts2d/arvore_ui_2d.gd")
const SkillsGuerreiroScript = preload("res://scripts2d/skills_guerreiro_2d.gd")
const Classe = preload("res://scripts2d/classe_2d.gd")
const UpgradeUiScript = preload("res://scripts2d/upgrade_ui_2d.gd")
const MenusScript = preload("res://scripts2d/menus_2d.gd")
const MetaScript = preload("res://scripts2d/meta_2d.gd")
const Audio = preload("res://scripts2d/audio_2d.gd")

enum Estado { LUTA, LIMPA, MORTO, VENCEU, ESCOLHA, MENU, PAUSA, TRANSICAO, ROTA }

var config := {}
var salas: Array = []     # caminho padrão (combate) de cada etapa, vindo do core
var no_atual := {}        # nó da sala em curso: id, tipo, room, enemies
var opcoes_rota: Array = []
var indice := 0
var estado := Estado.LUTA
var rng := RandomNumberGenerator.new()
var room: Node2D
var player: Node2D
var hud: CanvasLayer
var upgrades: RefCounted
var _classe_montada := ""
var meta: RefCounted
var nucleo: Object         # ShatterRogue (mesmo núcleo do meta)
## Ganhos da corrida atual, guardados no core; vão ao saldo quando ela acaba. {"fragmentos": n, "materiais": {id: n}}
var ganhos: Dictionary:
	get:
		var g: Dictionary = nucleo.corrida_estado().get("gains", {})
		var mats := {}
		for m in g.get("materials", []):
			if int(m["qty"]) > 0:
				mats[str(m["id"])] = int(m["qty"])
		return {"fragmentos": int(g.get("fragments", 0)), "materiais": mats}
var ui: CanvasLayer
var menus: CanvasLayer
var com_menu := true   # false nos testes: começa direto na sala 1
var tempo := 0.0       # segundos da corrida atual (só conta luta e sala limpa)
var camera: Camera2D
var arvore: CanvasLayer   # árvore de habilidades (tecla T)
var atores: Node2D
var vivos := 0
var corridas := 0
var _timer := 0.0
var _estado_antes := Estado.LUTA

func _ready() -> void:
	config = Csv.kv("res://data2d/run_settings.csv")
	atores = Node2D.new()
	atores.y_sort_enabled = true
	add_child(atores)
	Classe.ler_argumentos()
	meta = MetaScript.new()
	meta.carregar()
	nucleo = meta.nucleo
	_criar_classe()
	camera = Camera2D.new()
	camera.process_callback = Camera2D.CAMERA2D_PROCESS_PHYSICS
	add_child(camera)
	var etapa := 0
	while not nucleo.corrida_caminhos(etapa).is_empty():
		salas.append(_no_do_core(nucleo.corrida_caminhos(etapa)[0]))
		etapa += 1
	hud = HudScript.new()
	hud.jogador = player
	hud.upgrades = upgrades
	hud.total_salas = salas.size()
	add_child(hud)
	ui = UpgradeUiScript.new()
	ui.upgrades = upgrades
	ui.escolhido.connect(_on_upgrade_escolhido)
	add_child(ui)
	arvore = ArvoreUiScript.new()
	arvore.definir(player.habilidades if "habilidades" in player else null)
	arvore.fechada.connect(func() -> void:
		if upgrades.has_method("reaplicar"):
			upgrades.reaplicar(player))
	add_child(arvore)
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

## Cria o jogador e a árvore de upgrades da classe escolhida (arqueiro: cartas do core; guerreiro: árvore de habilidades).
func _criar_classe() -> void:
	var guerreiro: bool = Classe.atual == "guerreiro"
	player = (WarriorScript if guerreiro else PlayerScript).new()
	player.died.connect(_on_player_died)
	atores.add_child(player)
	upgrades = (SkillsGuerreiroScript if guerreiro else UpgradesScript).new()
	upgrades.meta = meta
	if guerreiro:
		player.skills = upgrades
	else:  # arqueiro e mago: árvore de habilidades em habilidades_2d.gd (tecla T)
		player.definir_classe(Classe.atual)
		upgrades.habilidades = player.habilidades
	if arvore != null:
		arvore.definir(player.habilidades if "habilidades" in player else null)
	_classe_montada = Classe.atual

## Troca de classe entre corridas (botão do título): recria o jogador e religa HUD e cartas.
func _trocar_classe() -> void:
	player.queue_free()
	_criar_classe()
	hud.jogador = player
	hud.upgrades = upgrades
	ui.upgrades = upgrades

func iniciar_corrida() -> void:
	if Classe.atual != _classe_montada:
		_trocar_classe()
	# O core credita os ganhos pendentes de uma corrida abandonada (reiniciar, título) ao começar a próxima.
	rng.seed = int(config["seed"]) + corridas
	corridas += 1
	indice = 0
	tempo = 0.0
	menus.limpar_fade()
	var guerreiro: bool = Classe.atual == "guerreiro"
	# O guerreiro tem a árvore de habilidades no GDScript (ainda não migrada): o core só roda o fluxo da corrida, sem cartas.
	if nucleo.corrida_fase() != 0:
		nucleo.corrida_terminar()   # corrida abandonada: o modo de cartas só muda fora de corrida viva (credita os ganhos)
	nucleo.corrida_cartas_externas(guerreiro)
	if not guerreiro:
		upgrades.semente = int(rng.seed)
	upgrades.restaurar(player)  # stats base de volta antes do reset do jogador; o arqueiro também começa a corrida no core
	if guerreiro:
		nucleo.corrida_iniciar(int(rng.seed), upgrades.base_numerica())
	meta.sincronizar()
	player.reset()
	_carregar_sala(0)

## Cartas da sala limpa: o arqueiro recebe as que o core sorteou; o guerreiro sorteia na árvore dele.
func _cartas_da_sala() -> Array:
	if Classe.atual != "guerreiro":
		return upgrades.oferta()
	if indice + 1 >= salas.size() or no_atual["tipo"] == "descanso":
		return []
	var qtd := int(config["upgrade_cards"])
	if no_atual["tipo"] == "elite":
		qtd += int(config["elite_extra_cards"])
	return upgrades.sortear(rng, qtd)

## Nó do core ({id, kind, room, enemies: [{id, count}]}) no formato que o cliente usa: tipo e texto "inimigo:n|...".
func _no_do_core(c: Dictionary) -> Dictionary:
	var partes := []
	for e in c["enemies"]:
		partes.append("%s:%d" % [e["id"], int(e["count"])])
	return {"id": c["id"], "tipo": c["kind"], "room": c["room"], "enemies": "|".join(partes)}

## Caminhos oferecidos ao entrar na etapa `i` (índice 0): o padrão de run.csv mais as alternativas de rota.csv.
func caminhos_da_etapa(i: int) -> Array:
	var out := []
	for c in nucleo.corrida_caminhos(i):
		out.append(_no_do_core(c))
	return out

func _carregar_sala(i: int, no: Dictionary = {}) -> void:
	if no.is_empty():
		no = _no_do_core(nucleo.corrida_estado()["node"])
	no_atual = no
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
	room.carregar(no["room"])
	room.colocar_props(atores)
	room.porta_usada.connect(_on_porta)
	player.global_position = room.spawn_jogador
	player.velocity = Vector2.ZERO
	hud.sala = i + 1
	hud.mensagem = ""
	hud.chefe = null
	_ajustar_camera()
	_spawn_inimigos(no["enemies"])
	estado = Estado.LUTA
	if no["tipo"] == "descanso":
		_descansar()

## Sala de descanso: sem inimigos; o core diz quanto da vida volta e a porta abre sem cartas.
func _descansar() -> void:
	var r: Dictionary = nucleo.corrida_descansar(player.hp)
	player.hp = float(r["hp"])
	player.hp_changed.emit(player.hp, player.stats["hp_max"])
	estado = Estado.LIMPA
	_timer = config["clear_delay"]

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
	for parte in spec.split("|", false):
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
	var r: Dictionary = nucleo.corrida_inimigo_morto(e.stats.get("id", ""))   # drops, sala limpa e cartas: regras do core
	if r["sala_limpa"] and estado == Estado.LUTA:
		estado = Estado.LIMPA
		if "habilidades" in player:
			player.habilidades.ganhar_pontos(int(config["skill_points_room"]) + (int(config["skill_points_boss"]) if indice + 1 >= salas.size() else 0))
		_timer = config["clear_delay"]

func _physics_process(delta: float) -> void:
	if estado == Estado.LUTA or estado == Estado.LIMPA:
		tempo += delta
	hud.tempo = tempo
	if _timer > 0.0:
		_timer -= delta
		if _timer <= 0.0:
			match estado:
				Estado.LIMPA:
					var cartas: Array = _cartas_da_sala()
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
	hud.mensagem = Csv.t("hud.rest" if no_atual["tipo"] == "descanso" else "hud.room_clear")
	estado = Estado.LIMPA

func _on_upgrade_escolhido(id: String) -> void:
	upgrades.escolher(id, player)
	_abrir_porta()

func _on_porta() -> void:
	if estado != Estado.LIMPA or _timer > 0.0 or not room.celulas_porta.size():
		return
	match nucleo.corrida_porta():
		3:   # vitória na última sala
			estado = Estado.VENCEU
			hud.mensagem = Csv.t("hud.victory")
			Audio.tocar("victory")
			_timer = config["restart_delay"]
		1:   # entrou na etapa seguinte, sem bifurcação
			indice += 1
			_entrar_na_sala(_no_do_core(nucleo.corrida_estado()["node"]))
		2:   # bifurcação: o jogador escolhe o caminho
			indice += 1
			estado = Estado.ROTA
			opcoes_rota = caminhos_da_etapa(indice)
			var botoes := []
			for c in opcoes_rota:
				botoes.append(["route." + c["id"], func() -> void: escolher_rota(c)])
			get_tree().paused = true
			menus.mostrar_rota(botoes)

## Escolha de uma bifurcação (botão do menu ou teste): despausa e vai para a sala escolhida.
func escolher_rota(no: Dictionary) -> void:
	if estado != Estado.ROTA:
		return
	for i in opcoes_rota.size():
		if opcoes_rota[i]["id"] == no["id"]:
			nucleo.corrida_escolher_caminho(i)
	menus.fechar()
	get_tree().paused = false
	_entrar_na_sala(no)

func _entrar_na_sala(no: Dictionary) -> void:
	estado = Estado.TRANSICAO
	menus.transicao(config["room_fade"], func(): _carregar_sala(indice, no))

func _on_player_died() -> void:
	nucleo.corrida_jogador_morreu()
	estado = Estado.MORTO
	hud.mensagem = Csv.t("hud.dead")
	Audio.tocar("defeat")
	_timer = config["restart_delay"]

func _mostrar_fim() -> void:
	hud.mensagem = ""
	var r: Dictionary = nucleo.corrida_resumo()   # lido antes de terminar: terminar credita os ganhos e zera a corrida
	var mats := []
	for m in r.get("materials", []):
		if int(m["qty"]) > 0:
			mats.append("%s x%d" % [Csv.t("material." + m["id"]), int(m["qty"])])
	var resumo := [
		Csv.t("menu.sum_time") % formatar_tempo(tempo),
		Csv.t("menu.sum_rooms") % [int(r["stage_reached"]) + 1, int(r["stages_total"])],
		Csv.t("menu.sum_upgrades") % _total_upgrades(),
		Csv.t("menu.sum_fragments") % int(r["fragments"]),
	]
	if not mats.is_empty():
		resumo.append(Csv.t("menu.sum_materials") % ", ".join(mats))
	nucleo.corrida_terminar()
	meta.sincronizar()
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
