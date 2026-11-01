extends RefCounted
## Árvore de GELO do Arqueiro (docs/design/32_gelo.md): Flecha Gélida, Estilhaço Glacial, Prisão de Gelo e Arauto do Gelo.
## Autossuficiente: não depende de edição em enemy_2d.gd. O "frio" acumula em meta do inimigo e usa os status
## existentes (lentidao, atordoamento). Sem arte em res://art2d/fx/gelo/ cai em desenho por código (Feel.ponto).
## Contrato igual ao de efeitos_arqueiro_2d.gd: executar(efeito, jogador, def, nivel, mira) -> bool.

const Feel = preload("res://scripts2d/feel_2d.gd")
const PASTA := "res://art2d/fx/gelo/"
const COR := Color(0.6, 0.88, 1.0)
const COR_FUNDO := Color(0.35, 0.65, 0.95)

# ---------- ativas ----------
static func executar(efeito: String, jogador: Node2D, def: Dictionary, nivel: int, mira: Vector2) -> bool:
	if jogador == null or not jogador.is_inside_tree() or jogador.esta_morto():
		return false
	var dir: Vector2 = mira.normalized() if mira != Vector2.ZERO else jogador.mira_atual()
	match efeito:
		"gelo_flecha":
			_flecha_gelida(jogador, dir, def)
		"gelo_estilhaco":
			_estilhaco(jogador, dir, def)
		"gelo_prisao":
			_prisao(jogador, dir, def)
		_:
			push_error("Efeito de gelo desconhecido: " + efeito)
			return false
	return true

## Flecha Gélida: dano normal; cada acerto soma 1 acúmulo de frio (valor = lentidão por acúmulo, duracao = tempo do frio).
static func _flecha_gelida(jogador: Node2D, dir: Vector2, def: Dictionary) -> void:
	var f = jogador.lancar_flecha(dir, def.get("dano", 1.0), int(def.get("qtd", 0)))
	f.cor_fx = COR
	_vestir_flecha(f)
	f.body_entered.connect(func(corpo: Node):
		if corpo.has_method("aplicar_status"):
			acumular_frio(corpo, 1, def))

## Estilhaço Glacial: o acerto racha em `qtd` lascas que vão para os outros alvos mais próximos (`raio` de busca).
static func _estilhaco(jogador: Node2D, dir: Vector2, def: Dictionary) -> void:
	var f = jogador.lancar_flecha(dir, def.get("dano", 1.0))
	f.cor_fx = COR
	_vestir_flecha(f)
	var dano_lasca: float = jogador.stats["arrow_damage"] * def.get("dano", 1.0) * def.get("valor", 0.5)
	f.body_entered.connect(func(corpo: Node):
		if not corpo.has_method("aplicar_status") or not corpo.is_inside_tree():
			return
		acumular_frio(corpo, 1, def)
		_lascas(corpo, dano_lasca, int(def.get("qtd", 3)), def.get("raio", 260.0), def))

## Prisão de Gelo: área (raio) no ponto mirado; congela tudo por `duracao` segundos e causa um golpe de dano.
static func _prisao(jogador: Node2D, dir: Vector2, def: Dictionary) -> void:
	var alcance: float = def.get("alcance", 450.0)
	var centro: Vector2 = jogador.global_position + dir * minf(alcance, 0.7 * alcance)
	if jogador.has_method("tem_alvo_auto") and jogador.tem_alvo_auto():
		centro = jogador.ponto_mira(alcance)
	var raio: float = def.get("raio", 170.0)
	var dano: float = jogador.stats["arrow_damage"] * def.get("dano", 1.0)
	_anim(jogador.get_parent(), "gelo_prisao", 8, centro, raio * 2.0, 0.9, 12.0)
	for n in jogador.get_tree().get_nodes_in_group("hurtable"):
		if n is Node2D and n.has_method("aplicar_status") and n.global_position.distance_to(centro) <= raio:
			n.take_damage(dano, centro)
			if is_instance_valid(n):
				congelar(n, def.get("duracao", 2.0))

# ---------- frio, congelamento ----------
const MAX_ACUMULOS := 4   # no máximo de acúmulos o inimigo congela

## Soma acúmulos de frio. Cada acúmulo lentifica (def.valor) por def.duracao s; no máximo congela.
static func acumular_frio(inimigo: Node, qtd: int, def: Dictionary) -> void:
	if not is_instance_valid(inimigo) or not inimigo.has_method("aplicar_status"):
		return
	if inimigo.has_method("esta_morto") and inimigo.esta_morto():
		return
	var n: int = mini(int(inimigo.get_meta("frio_acumulos", 0)) + qtd, MAX_ACUMULOS)
	inimigo.set_meta("frio_acumulos", n)
	inimigo.aplicar_status("lentidao", def.get("duracao", 3.0), minf(def.get("valor", 0.15) * n, 0.7))
	_overlay(inimigo)
	if n >= MAX_ACUMULOS:
		inimigo.set_meta("frio_acumulos", 0)
		congelar(inimigo, def.get("duracao", 3.0) * 0.5)

## Congela: atordoamento + marca de congelado (o Arauto lê a meta). Dura `dur` s.
static func congelar(inimigo: Node, dur: float) -> void:
	if not is_instance_valid(inimigo) or not inimigo.has_method("aplicar_status"):
		return
	inimigo.aplicar_status("atordoamento", dur)
	inimigo.set_meta("congelado_ate", Time.get_ticks_msec() + int(dur * 1000.0))
	_overlay(inimigo, true)

static func esta_congelado(inimigo: Node) -> bool:
	return inimigo.has_meta("congelado_ate") and Time.get_ticks_msec() < int(inimigo.get_meta("congelado_ate"))

# ---------- passiva: Arauto do Gelo ----------
## Liga o Arauto ao inimigo (chamar quando o inimigo nasce, ou varrer o grupo "hurtable" ao equipar a gema).
## Inimigo congelado que morre explode em `qtd` lascas e dano em `raio` (def da passiva: dano, qtd, raio, duracao).
static func arauto_vigiar(inimigo: Node, jogador: Node2D, def: Dictionary) -> void:
	if inimigo.has_meta("arauto_gelo") or not inimigo.has_signal("died"):
		return
	inimigo.set_meta("arauto_gelo", true)
	inimigo.died.connect(func(e):
		if not is_instance_valid(e) or not esta_congelado(e) or not is_instance_valid(jogador):
			return
		var pai: Node = e.get_parent()
		if pai == null:
			return
		var pos: Vector2 = e.global_position
		var raio: float = def.get("raio", 150.0)
		var dano: float = jogador.stats["arrow_damage"] * def.get("dano", 1.0)
		_anim(pai, "gelo_explosao", 8, pos, raio * 2.0, 0.55, 14.0)
		for n in jogador.get_tree().get_nodes_in_group("hurtable"):
			if n != e and n is Node2D and n.global_position.distance_to(pos) <= raio:
				n.take_damage(dano, pos)
				if is_instance_valid(n):
					acumular_frio(n, 1, def)
		, CONNECT_ONE_SHOT)

## Aplica o Arauto a todos os inimigos vivos; chamar de tempos em tempos (ex.: a cada 0,5 s) enquanto a gema estiver equipada.
static func arauto_varrer(jogador: Node2D, def: Dictionary) -> void:
	for n in jogador.get_tree().get_nodes_in_group("hurtable"):
		if n != jogador:
			arauto_vigiar(n, jogador, def)

# ---------- visual ----------
static func _lascas(origem: Node2D, dano: float, qtd: int, raio: float, def: Dictionary) -> void:
	var alvos := []
	for n in origem.get_tree().get_nodes_in_group("hurtable"):
		if n != origem and n is Node2D and n.has_method("aplicar_status") and n.global_position.distance_to(origem.global_position) <= raio:
			alvos.append(n)
	alvos.sort_custom(func(a, b): return a.global_position.distance_squared_to(origem.global_position) < b.global_position.distance_squared_to(origem.global_position))
	var pai: Node = origem.get_parent()
	for i in mini(qtd, alvos.size()):
		var alvo: Node2D = alvos[i]
		var de: Vector2 = origem.global_position + Vector2(0, -30)
		var para: Vector2 = alvo.global_position + Vector2(0, -30)
		var s := _sprite(pai, "gelo_lasca", 4, de, 56.0, 12.0)
		s.rotation = de.angle_to_point(para)
		var tw := s.create_tween()
		tw.tween_property(s, "global_position", para, de.distance_to(para) / 900.0)
		tw.tween_callback(func():
			s.queue_free()
			if is_instance_valid(alvo):
				alvo.take_damage(dano, de)
				if is_instance_valid(alvo):
					acumular_frio(alvo, 1, def)
			_anim(pai, "gelo_impacto", 8, para, 90.0, 0.35, 16.0))

## Deixa o brilho/rastro da flecha azul e troca o desenho se houver folha.
static func _vestir_flecha(f: Node) -> void:
	if f.has_method("add_child") and ResourceLoader.exists(PASTA + "gelo_flecha.png"):
		var s := _sprite(f, "gelo_flecha", 6, Vector2(0, -30), 72.0, 14.0)
		s.position = Vector2(0, -30)

static func _overlay(inimigo: Node, congelado := false) -> void:
	var nome := "FrioFx"
	var folha := "gelo_congelado" if congelado else "gelo_status_frio"
	var antigo := inimigo.get_node_or_null(nome)
	if antigo != null:
		if antigo.get_meta("folha", "") == folha or antigo.get_meta("folha", "") == "gelo_congelado":
			return
		antigo.queue_free()
	var s := _sprite(inimigo, folha, 6 if not congelado else 4, Vector2(0, -22), 80.0 if not congelado else 96.0, 8.0)
	s.name = nome
	s.set_meta("folha", folha)
	s.z_index = 1
	s.modulate.a = 0.8 if congelado else 1.0   # o inimigo ainda aparece por baixo do gelo
	inimigo.get_tree().create_timer(2.5 if congelado else 3.0).timeout.connect(func():
		if is_instance_valid(s):
			s.queue_free())

static func _anim(pai: Node, folha: String, quadros: int, pos: Vector2, tam: float, dur: float, fps: float) -> void:
	var s := _sprite(pai, folha, quadros, pos, tam, fps, false)
	s.get_tree().create_timer(dur).timeout.connect(func():
		if is_instance_valid(s):
			s.queue_free())

## Sprite animado a partir de uma folha em linha (N quadros iguais). Sem a folha, desenha um brilho azul do tamanho pedido.
static func _sprite(pai: Node, folha: String, quadros: int, pos: Vector2, tam: float, fps: float, loop := true) -> Node2D:
	var caminho := PASTA + folha + ".png"
	var n: Node2D
	if ResourceLoader.exists(caminho):
		var tex: Texture2D = load(caminho)
		var s := Sprite2D.new()
		s.texture = tex
		s.hframes = quadros
		var larg: float = tex.get_width() / float(quadros)
		s.scale = Vector2.ONE * (tam / larg)
		n = s
		var tw := s.create_tween().set_loops() if loop else s.create_tween()
		tw.tween_method(func(q: float): s.frame = clampi(int(q), 0, quadros - 1), 0.0, float(quadros) - 0.001, quadros / fps)
	else:
		var s := Sprite2D.new()
		s.texture = Feel.ponto()
		s.material = Feel.aditivo()
		s.modulate = Color(COR.r, COR.g, COR.b, 0.7)
		s.scale = Vector2.ONE * (tam / 64.0)
		n = s
	pai.add_child(n)
	if pai is CharacterBody2D or pai is Area2D:
		n.position = pos       # filho de um ator: posição local
	else:
		n.global_position = pos
	return n
