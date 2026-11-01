extends Node2D
## Corrida 2D: etapas em sequência (data2d/run.csv), chefe na última, morte reinicia em segundos.
## Fase aberta (data2d/rooms/fase_*.txt, sem portas): um mapa grande para a corrida toda, a câmera segue o jogador,
## cada etapa é uma onda que nasce fora da vista e, depois do chefe, um portal leva à vitória.
## Salas antigas com porta `D` (24 x 13) continuam com câmera fixa e porta.
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
const MagoScript = preload("res://scripts2d/mago_2d.gd")
const CorridaGuerreiroScript = preload("res://scripts2d/corrida_guerreiro_2d.gd")
const Classe = preload("res://scripts2d/classe_2d.gd")
const UpgradeUiScript = preload("res://scripts2d/upgrade_ui_2d.gd")
const MenusScript = preload("res://scripts2d/menus_2d.gd")
const MetaScript = preload("res://scripts2d/meta_2d.gd")
const Audio = preload("res://scripts2d/audio_2d.gd")
const PortalScript = preload("res://scripts2d/portal_2d.gd")
const ConsoleDev = preload("res://scripts2d/console_dev_2d.gd")

enum Estado { LUTA, LIMPA, MORTO, VENCEU, ESCOLHA, MENU, PAUSA, TRANSICAO, ROTA, PROXIMA }

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
var portal: Area2D          # saída da fase aberta, aberta depois do chefe
var _pos_chefe := Vector2.ZERO

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
	if OS.is_debug_build():
		ConsoleDev.new(self).registrar()   # comandos de playtest no console ` (LimboConsole)
	elif has_node("/root/LimboConsole"):
		get_node("/root/LimboConsole").enabled = false   # build de release: sem console
	iniciar_corrida()
	if com_menu:
		_ir_titulo()

## Cria o jogador e a árvore de upgrades da classe escolhida (arqueiro e mago: cartas do core; guerreiro: só a árvore comum).
func _criar_classe() -> void:
	var guerreiro: bool = Classe.atual == "guerreiro"
	player = (WarriorScript if guerreiro else (MagoScript if Classe.atual == "mago" else PlayerScript)).new()
	player.died.connect(_on_player_died)
	atores.add_child(player)
	upgrades = (CorridaGuerreiroScript if guerreiro else UpgradesScript).new()
	upgrades.meta = meta
	player.habilidades.nucleo = nucleo   # árvore de habilidades com as regras no core do meta (as 3 classes)
	if guerreiro:
		player.habilidades.carregar_classe("guerreiro")
	else:  # arqueiro e mago: stats da classe e a árvore
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
	if nucleo.corrida_fase() != 0:
		nucleo.corrida_terminar()   # corrida abandonada: classe e modo de cartas só mudam fora de corrida viva (credita os ganhos)
	if Classe.atual != _classe_montada:
		_trocar_classe()
	# O core credita os ganhos pendentes de uma corrida abandonada (reiniciar, título) ao começar a próxima.
	rng.seed = int(config["seed"]) + corridas
	corridas += 1
	indice = 0
	tempo = 0.0
	menus.limpar_fade()
	var guerreiro: bool = Classe.atual == "guerreiro"
	# O guerreiro não usa as cartas do core (só a árvore comum): o core roda o fluxo da corrida sem cartas.
	nucleo.classe_definir(Classe.atual)   # pontos por sala e passivas da árvore vão para esta classe
	nucleo.corrida_cartas_externas(guerreiro)
	if not guerreiro:
		upgrades.semente = int(rng.seed)
	upgrades.restaurar(player)  # stats base de volta antes do reset do jogador; o arqueiro também começa a corrida no core
	if guerreiro:
		nucleo.corrida_iniciar(int(rng.seed), upgrades.base_numerica())
	meta.sincronizar()
	player.reset()
	_carregar_sala(0)

## Cartas da sala limpa: as que o core sorteou (o guerreiro não recebe cartas, só pontos da árvore).
func _cartas_da_sala() -> Array:
	return upgrades.oferta()

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
	for n in get_tree().get_nodes_in_group("hurtable"):
		n.queue_free()
	# Fase aberta: o mapa fica de uma etapa para a outra (a onda seguinte nasce no mesmo mapa).
	var manter: bool = i > 0 and room != null and is_instance_valid(room) and room.aberta()
	if not manter:
		if room != null:
			room.queue_free()
		for n in atores.get_children():
			if n != player:
				n.queue_free()
		portal = null
		_pos_chefe = Vector2.ZERO
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
	_ajustar_camera(not manter)
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

## Sala com porta: câmera fixa que cabe a sala inteira. Fase aberta: zoom do CSV, segue o jogador e para na borda do mapa.
func _ajustar_camera(cortar := true) -> void:
	var vp := get_viewport_rect().size
	var tam: Vector2 = room.tamanho_px()
	var cabe := minf(vp.x / tam.x, vp.y / tam.y)
	if not room.aberta():
		camera.position_smoothing_enabled = false
		camera.limit_left = -10000000
		camera.limit_top = -10000000
		camera.limit_right = 10000000
		camera.limit_bottom = 10000000
		camera.position = tam / 2.0
		camera.zoom = Vector2(cabe, cabe)
		return
	var z := maxf(float(config.get("camera_zoom", 1.0)), cabe)   # nunca mostra além da borda do mapa
	camera.zoom = Vector2(z, z)
	camera.limit_left = 0
	camera.limit_top = 0
	camera.limit_right = int(tam.x)
	camera.limit_bottom = int(tam.y)
	camera.position_smoothing_speed = float(config.get("camera_smoothing", 6.0))
	camera.position_smoothing_enabled = camera.position_smoothing_speed > 0.0
	camera.position = player.global_position
	if cortar:
		camera.reset_smoothing()

## Área do mapa que o jogador vê agora (px), centrada nele e presa à borda como a câmera.
func vista() -> Rect2:
	var tam: Vector2 = get_viewport_rect().size / camera.zoom
	var mapa: Vector2 = room.tamanho_px()
	var canto := player.global_position - tam / 2.0
	canto = Vector2(clampf(canto.x, 0.0, maxf(0.0, mapa.x - tam.x)), clampf(canto.y, 0.0, maxf(0.0, mapa.y - tam.y)))
	return Rect2(canto, tam)

func _spawn_inimigos(spec: String) -> void:
	var total := 0
	for parte in spec.split("|", false):
		total += int(parte.split(":")[1])
	var pontos: Array = room.spawns_inimigos.duplicate()
	# Fase aberta: a primeira onda usa os pontos E (adormecida, perto do início); as outras nascem fora da vista.
	if room.aberta() and (indice > 0 or pontos.is_empty()):
		var t := float(room.tile)
		pontos = room.pontos_fora_da_vista(vista(), float(config.get("spawn_margem_min", 1.0)) * t, float(config.get("spawn_margem_max", 4.0)) * t, maxi(total, 1), rng)
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
			var chefe: bool = Csv.enemy(p[0])["kind"] == "boss"
			var e: Node2D = (BossScript if chefe else EnemyScript).new()
			atores.add_child(e)
			# Fase aberta: o chefe espera no lugar dele (G, na arena); o jogador vai até lá.
			var onde: Vector2 = room.posicao_chefe if chefe and room.aberta() and room.posicao_chefe != Vector2.ZERO else pontos[k % pontos.size()]
			e.setup(p[0], player, onde)
			if chefe and room.aberta() and room.posicao_chefe != Vector2.ZERO:
				_avisar(Csv.t("hud.boss_awaits"), float(config.get("boss_hint_time", 3.0)))
			if indice == 0 and e.has_method("adormecer") and config.get("first_room_wake_radius", 0.0) > 0.0:
				e.adormecer(config["first_room_wake_radius"])   # entrada calma: a sala só luta quando o jogador avança
			e.died.connect(_on_inimigo_morto)
			k += 1
			vivos += 1

func _on_inimigo_morto(e) -> void:
	vivos -= 1
	if e.stats.get("kind", "") == "boss":
		_pos_chefe = e.global_position
	var r: Dictionary = nucleo.corrida_inimigo_morto(e.stats.get("id", ""))   # drops, sala limpa e cartas: regras do core
	if r["sala_limpa"] and estado == Estado.LUTA:
		estado = Estado.LIMPA
		if "habilidades" in player and player.habilidades != null:
			player.habilidades.sincronizar()   # o core deu os pontos de habilidade da sala (e do chefe)
		_timer = config["clear_delay"]

func _physics_process(delta: float) -> void:
	if estado == Estado.LUTA or estado == Estado.LIMPA or estado == Estado.PROXIMA:
		tempo += delta
	if hud:
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
				Estado.PROXIMA:
					estado = Estado.LIMPA
					_on_porta()
	if room != null and room.aberta() and estado != Estado.MENU:
		camera.position = player.global_position
		var v := vista()
		room.seguir_vinheta(v.get_center(), v.size)

func _abrir_porta() -> void:
	if room.aberta():
		_fim_da_onda()
		return
	room.abrir_porta()
	Audio.tocar("door_open")
	hud.mensagem = Csv.t("hud.rest" if no_atual["tipo"] == "descanso" else "hud.room_clear")
	estado = Estado.LIMPA

## Fase aberta: onda vencida leva à seguinte depois de uma pausa curta; depois do chefe, abre o portal.
func _fim_da_onda() -> void:
	if indice < salas.size() - 1:
		hud.mensagem = Csv.t("hud.rest_open" if no_atual["tipo"] == "descanso" else "hud.wave_clear")
		estado = Estado.PROXIMA
		_timer = float(config.get("next_wave_delay", 1.5))
		return
	_abrir_portal()
	hud.mensagem = Csv.t("hud.portal_open")
	estado = Estado.LIMPA

## Mensagem central que some sozinha depois de `tempo` s (se outra não tomou o lugar).
func _avisar(texto: String, tempo: float) -> void:
	hud.mensagem = texto
	get_tree().create_timer(tempo, false).timeout.connect(func() -> void:
		if is_instance_valid(hud) and hud.mensagem == texto:
			hud.mensagem = "")

func _abrir_portal() -> void:
	if portal != null and is_instance_valid(portal):
		return
	var pos: Vector2 = room.posicao_portal if room.posicao_portal != Vector2.ZERO else _pos_chefe
	if pos == Vector2.ZERO:
		pos = player.global_position + Vector2(0, -room.tile * 3)
	portal = Area2D.new()
	portal.set_script(PortalScript)
	portal.position = pos
	portal.body_entered.connect(func(_c): _on_porta())
	room.add_child.call_deferred(portal)
	Audio.tocar("door_open")

func _on_upgrade_escolhido(id: String) -> void:
	upgrades.escolher(id, player)
	_abrir_porta()

## Posição da saída aberta (porta ou portal); Vector2.ZERO enquanto não há saída. Usada pelo bot e pelos testes.
func posicao_saida() -> Vector2:
	if room.aberta():
		return portal.position if portal != null and is_instance_valid(portal) else Vector2.ZERO
	return room._centro(room.celulas_porta[0].x, room.celulas_porta[0].y + 3) if room.celulas_porta.size() else Vector2.ZERO

func _on_porta() -> void:
	if estado != Estado.LIMPA or _timer > 0.0:
		return
	if room.aberta() and indice == salas.size() - 1 and (portal == null or not is_instance_valid(portal)):
		return
	if not room.aberta() and not room.celulas_porta.size():
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
	if room.aberta():   # fase aberta: a próxima onda chega no mesmo mapa, sem fade
		_carregar_sala(indice, no)
		return
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
	if estado != Estado.LUTA and estado != Estado.LIMPA and estado != Estado.PROXIMA:
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
