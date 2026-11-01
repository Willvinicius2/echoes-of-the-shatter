extends SceneTree
## Sonda do autocast na fase aberta: joga cada classe com o autocast ligado (sem mira forçada), andando até o inimigo
## mais próximo, e imprime o que disparou, o que acertou, o que saiu sem linha de visão e onde travou.
##   godot --headless --fixed-fps 240 --path godot --script res://scripts2d/tools/sonda_autocast_2d.gd -- 120 arqueiro mago guerreiro
## Primeiro argumento: segundos de física por classe. Os demais: classes (padrão: as 3).

const RunScene = preload("res://scenes2d/Run2D.tscn")
const Classe = preload("res://scripts2d/classe_2d.gd")
const Alvos = preload("res://scripts2d/alvos_2d.gd")
const ArrowScript = preload("res://scripts2d/arrow_2d.gd")
const OrbeScript = preload("res://scripts2d/orbe_2d.gd")

var run
var p
var usos := {}
var sem_visao := {}
var longe := {}
var tiros := 0
var tiros_sem_alvo := 0
var golpes := 0
var presos := 0
var mortes := 0
var _estado_antes := -1

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var dur: float = float(args[0]) if args.size() > 0 else 120.0
	var classes: Array = args.slice(1) if args.size() > 1 else Classe.CLASSES
	for c in classes:
		await _sondar(c, dur)
	quit()

func _sondar(c: String, dur: float) -> void:
	usos = {}
	sem_visao = {}
	longe = {}
	tiros = 0
	tiros_sem_alvo = 0
	golpes = 0
	presos = 0
	mortes = 0
	Classe.atual = c
	run = RunScene.instantiate()
	run.com_menu = false
	root.add_child(run)
	await physics_frame
	p = run.player
	p.god_mode = true
	var h = p.habilidades
	h.ganhar_pontos(200)
	var ativas: Array = h.ordem.filter(func(id): return h.eh_ativa(id))
	var equipadas := []
	for id in ativas:
		if equipadas.size() >= 4:
			break
		if h.eh_ult(id) or h.mira_de(id) == "manual":
			continue
		_aprender(h, id)
		if h.nivel(id) > 0:
			equipadas.append(id)
	for i in equipadas.size():
		h.equipar(i, equipadas[i])
	print("\n=== %s: slots %s" % [c, str(h.slots)])
	if "usada" in h:
		h.usada.connect(func(slot: int, id: String): _registrar_uso(id))
	run.atores.child_entered_tree.connect(_on_novo_ator)
	var recargas_antes := {}
	var t := 0.0
	var dt := 1.0 / 240.0
	var ultima_pos: Vector2 = p.global_position
	var parado := 0.0
	var proximo_log := 0.0
	while t < dur and run.estado != run.Estado.VENCEU:
		if run.estado == run.Estado.ESCOLHA and run.ui.aberta:
			run.ui.escolher(0)
		elif run.estado == run.Estado.ROTA:
			run.escolher_rota(run.opcoes_rota[0])
		elif run.estado == run.Estado.LIMPA and run._timer <= 0.0 and run.posicao_saida() != Vector2.ZERO:
			p.global_position = run.posicao_saida()
			p.auto_move = Vector2.UP
		elif run.estado == run.Estado.MORTO:
			mortes += 1
		else:
			_andar()
		# guerreiro: usos pelas recargas (não passa por usar() do runtime)
		if c == "guerreiro":
			for id in h.recargas:
				if not recargas_antes.has(id):
					_registrar_uso(id)
			recargas_antes = h.recargas.duplicate()
			if p.estado == p.Estado.ATACANDO and _estado_antes != p.Estado.ATACANDO:
				golpes += 1
			_estado_antes = p.estado
		if p.global_position.distance_to(ultima_pos) < 0.5 and run.estado == run.Estado.LUTA:
			parado += dt
			if parado > 3.0:
				presos += 1
				var alvo := _mais_proximo()
				if alvo != null:
					p.global_position = run.room.empurrar_para_dentro(alvo.global_position + (p.global_position - alvo.global_position).normalized() * 400.0)
				parado = 0.0
		else:
			parado = 0.0
		ultima_pos = p.global_position
		if t >= proximo_log:
			proximo_log += 10.0
			var alvo := _mais_proximo()
			print("t=%3.0f onda %d estado %s vivos %d pos %s mira %s dist %s %s" % [t, run.indice + 1, run.Estado.keys()[run.estado], run.vivos,
				str(p.global_position.round()), str(p.mira_atual().snapped(Vector2(0.01, 0.01))),
				"%.0f" % alvo.global_position.distance_to(p.global_position) if alvo != null else "-",
				("vê" if _ve(alvo.global_position) else "SEM VISÃO") + (" hp %.0f ciclo %s" % [alvo.hp, alvo.Ciclo.keys()[alvo.ciclo]] if "ciclo" in alvo else "") if alvo != null else ""])
		await physics_frame
		t += dt
	print("--- %s em %.0fs: chegou à onda %d, %s; mortes %d, travou %d vez(es)" % [c, t, run.indice + 1, run.Estado.keys()[run.estado], mortes, presos])
	print("    básico: %d disparos (%d sem alvo), golpes %d" % [tiros, tiros_sem_alvo, golpes])
	for id in usos:
		print("    %-28s usos %3d  sem linha de visão %3d  alvo fora do alcance %3d" % [id, usos[id], sem_visao.get(id, 0), longe.get(id, 0)])
	for id in h.slots:
		if id != "" and not usos.has(id):
			print("    %-28s NUNCA USADA (mira %s, alcance %s)" % [id, h.mira_de(id), str(h.miras.get(id, {}).get("alcance", "?"))])
	run.queue_free()
	await physics_frame

func _aprender(h, id: String) -> void:
	var pai: String = h.defs[id]["pai"]
	if pai != "" and h.nivel(pai) == 0:
		_aprender(h, pai)
	if h.nivel(id) == 0:
		h.aprender(id)

func _mais_proximo() -> Node2D:
	var melhor: Node2D = null
	var md := INF
	for n in get_nodes_in_group("hurtable"):
		if is_instance_valid(n):
			var d: float = n.global_position.distance_to(p.global_position)
			if d < md:
				md = d
				melhor = n
	return melhor

## Anda até o inimigo mais próximo; a mira e os disparos ficam por conta do autocast.
func _andar() -> void:
	var alvo := _mais_proximo()
	if alvo == null:
		p.auto_move = Vector2.ZERO
		return
	var para: Vector2 = alvo.global_position - p.global_position
	p.auto_move = para.normalized() if para.length() > 260.0 else Vector2.ZERO

func _registrar_uso(id: String) -> void:
	usos[id] = usos.get(id, 0) + 1
	var h = p.habilidades
	var alc: float = h.miras.get(id, {}).get("alcance", 0.0)
	var alvo := _mais_proximo()
	if alvo == null or (alc > 0.0 and alvo.global_position.distance_to(p.global_position) - Alvos.raio_de(alvo) > alc + 1.0):
		longe[id] = longe.get(id, 0) + 1
	if alvo != null and not _ve(alvo.global_position):
		sem_visao[id] = sem_visao.get(id, 0) + 1

func _ve(ponto: Vector2) -> bool:
	var q := PhysicsRayQueryParameters2D.create(p.global_position, ponto, 1)
	return p.get_world_2d().direct_space_state.intersect_ray(q).is_empty()

func _on_novo_ator(n: Node) -> void:
	if n is ArrowScript and n.team == "player" or n is OrbeScript:
		tiros += 1
		var alvo := _mais_proximo()
		var alc: float = p.habilidades.miras.get("basico", {}).get("alcance", 0.0)
		if alvo == null or alvo.global_position.distance_to(p.global_position) > alc + 60.0:
			tiros_sem_alvo += 1
