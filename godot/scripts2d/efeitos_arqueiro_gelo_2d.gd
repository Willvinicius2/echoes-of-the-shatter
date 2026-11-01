extends RefCounted
## Árvore de GELO do Arqueiro (docs/design/32_gelo.md): Flecha Gélida, Estilhaço Glacial, Prisão de Gelo e Arauto do Gelo.
## Autossuficiente: não depende de edição em enemy_2d.gd. O "frio" acumula em meta do inimigo e usa os status
## existentes (lentidao, atordoamento). Sem arte em res://art2d/fx/gelo/ cai em desenho por código (Feel.ponto).
## Contrato igual ao de efeitos_arqueiro_2d.gd: executar(efeito, jogador, def, nivel, mira) -> bool.

const Feel = preload("res://scripts2d/feel_2d.gd")
const Vfx = preload("res://scripts2d/vfx_2d.gd")
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
		"cometa_gelo":
			_cometa(jogador, dir, def)
		"nova_gelo":
			_nova(jogador, def)
		_:
			push_error("Efeito de gelo desconhecido: " + efeito)
			return false
	return true

## Flecha Gélida: dano normal; cada acerto soma 1 acúmulo de frio (valor = lentidão por acúmulo, duracao = tempo do frio).
## Forma "anel" (passivo Anel Gélido): no acerto, `qtd` lascas saem para os inimigos em volta (`raio`), em vez de
## `qtd` valer como perfuração.
static func _flecha_gelida(jogador: Node2D, dir: Vector2, def: Dictionary) -> void:
	var anel: bool = def.get("forma", "") == "anel"
	var f = jogador.lancar_flecha(dir, def.get("dano", 1.0), 0 if anel else int(def.get("qtd", 0)), 1.0, def)
	f.cor_fx = COR
	_vestir_flecha(f)
	var dano_lasca: float = jogador.stats["arrow_damage"] * def.get("dano", 1.0) * 0.5
	f.body_entered.connect(func(corpo: Node):
		if corpo.has_method("aplicar_status"):
			acumular_frio(corpo, 1, def)
			if anel and corpo.is_inside_tree():
				_lascas(corpo, dano_lasca, int(def.get("qtd", 6)), def.get("raio", 200.0), def))

## Estilhaço Glacial: o acerto racha em `qtd` lascas que vão para os outros alvos mais próximos (`raio` de busca).
static func _estilhaco(jogador: Node2D, dir: Vector2, def: Dictionary) -> void:
	var f = jogador.lancar_flecha(dir, def.get("dano", 1.0), 0, 1.0, def)
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

## Aura do Arauto do Gelo na camada C1 (elipse no chão, atrás do arqueiro; regra única em vfx_2d.gd). Nó "AuraGelo".
static func aura(jogador: Node2D) -> Node2D:
	var caminho := PASTA + "gelo_aura.png"
	var s: Node2D
	var natural := 64.0
	if ResourceLoader.exists(caminho):
		var tex: Texture2D = load(caminho)
		var sp := Sprite2D.new()
		sp.texture = tex
		sp.hframes = 6
		sp.material = Feel.aditivo()
		natural = tex.get_width() / 6.0
		var tw := sp.create_tween().set_loops()
		tw.tween_method(func(q: float): sp.frame = clampi(int(q), 0, 5), 0.0, 5.999, 6.0 / 8.0)
		s = sp
	else:
		var sp := Sprite2D.new()
		sp.texture = Feel.ponto()
		sp.material = Feel.aditivo()
		sp.modulate = Color(COR.r, COR.g, COR.b, 0.7)
		natural = 32.0
		s = sp
	return Vfx.aura_c1(jogador, s, natural, "AuraGelo")

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

## Veste a flecha básica com a folha do gelo (Eco do Gelo).
static func vestir_flecha(f: Node) -> void:
	_vestir_flecha(f)

## Cometa Gélido (doc 36, família queda do céu): sombra de aviso, bola de gelo cai em 0,6 s, explode (dano + `qtd`
## acúmulos de frio no `raio`) e deixa CHÃO GELADO por `duracao` s (lentidão `valor`, rachaduras hexagonais).
static func _cometa(jogador: Node2D, dir: Vector2, def: Dictionary) -> void:
	var alcance: float = def.get("alcance", 600.0)
	var centro: Vector2 = jogador.global_position + dir * 0.7 * alcance
	if jogador.has_method("tem_alvo_auto") and jogador.tem_alvo_auto():
		centro = jogador.ponto_mira(alcance)
	var c := Cometa.new()
	c.configurar(def, jogador.stats["arrow_damage"] * def.get("dano", 2.6))
	c.global_position = centro
	jogador.get_parent().add_child(c)

## Nova Gélida (doc 36, família nova): anel de gelo cresce do arqueiro até `raio` em 0,3 s e fere quem alcança
## (dano + 2 acúmulos de frio); `qtd` lascas voam para fora.
static func _nova(jogador: Node2D, def: Dictionary) -> void:
	var n := Nova.new()
	n.configurar(def, jogador.stats["arrow_damage"] * def.get("dano", 1.8))
	n.global_position = jogador.global_position
	jogador.get_parent().add_child(n)
	Feel.shake(jogador, 3.0, 0.15)

## Deixa o brilho/rastro da flecha azul e troca o desenho se houver folha.
static func _vestir_flecha(f: Node) -> void:
	if f.has_method("add_child") and ResourceLoader.exists(PASTA + "gelo_flecha.png"):
		var s := _sprite(f.vis, "gelo_flecha", 6, Vector2.ZERO, 72.0, 14.0)   # f.vis: nó do desenho, já no peito e girado
		s.position = Vector2.ZERO

static func _overlay(inimigo: Node, congelado := false) -> void:
	var nome := "FrioFx"
	var folha := "gelo_congelado" if congelado else "gelo_status_frio"
	var antigo := inimigo.get_node_or_null(nome)
	if antigo != null:
		if antigo.get_meta("folha", "") == folha or antigo.get_meta("folha", "") == "gelo_congelado":
			return
		antigo.queue_free()
	# Teto de overlays grandes (doc 36 seção 6.1): com a tela cheia, o frio vira um floco pequeno sobre a cabeça;
	# o anel completo fica só para o congelado (4º acúmulo).
	var pequeno: bool = not congelado and not Vfx.status_cabe(inimigo.get_tree())
	var s := _sprite(inimigo, folha, 6 if not congelado else 4, Vector2(0, -62) if pequeno else Vector2(0, -22),
		26.0 if pequeno else (80.0 if not congelado else 96.0), 8.0)
	if not pequeno:
		Vfx.registrar_status(s)
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

## Cometa Gélido: um nó (C0) com sombra de aviso própria e o chão gelado; o corpo que cai é um filho em C5.
## Silhueta própria (não é o meteoro recolorido): núcleo facetado que gira e cauda de cristais, sem chama.
class Cometa extends Node2D:
	const PAL := [Color("F0FBFF"), Color("7FD3F2"), Color("123A5C")]
	const QUEDA := 0.6
	const ALTURA := 460.0
	const FADE_CHAO := 0.6
	var raio := 130.0
	var dur_chao := 3.0
	var dano := 0.0
	var acumulos := 2
	var lentidao := 0.35
	var def := {}
	var _t := 0.0
	var _caiu := false
	var _acc := 0.0
	var _corpo: Node2D
	var _rachas: Array = []   # [ang, comp, ramo]

	func configurar(d: Dictionary, dn: float) -> void:
		def = d
		raio = d.get("raio", 130.0)
		dur_chao = d.get("duracao", 3.0)
		acumulos = maxi(1, int(d.get("qtd", 2)))
		lentidao = d.get("valor", 0.35)
		dano = dn
		z_index = -1

	func _ready() -> void:
		Vfx.registrar_animado(self)
		Vfx.sombra_aviso(get_parent(), global_position, raio, PAL[1], QUEDA)
		_corpo = CometaCorpo.new()
		_corpo.dona = self
		_corpo.z_index = 6   # -1 + 6 = 5 (C5, céu)
		_corpo.position = Vector2(0, -ALTURA)
		add_child(_corpo)
		var rng := RandomNumberGenerator.new()
		rng.randomize()
		for i in 7:
			_rachas.append([TAU * i / 7.0 + rng.randf_range(-0.25, 0.25), rng.randf_range(0.55, 1.0), rng.randf_range(0.3, 0.7)])

	func _physics_process(delta: float) -> void:
		_t += delta
		if not _caiu:
			var f := clampf(_t / QUEDA, 0.0, 1.0)
			_corpo.position.y = lerpf(-ALTURA, -16.0, f * f)   # cai acelerando
			_corpo.queue_redraw()
			if _t >= QUEDA:
				_caiu = true
				_t = 0.0
				_corpo.queue_free()
				_explodir()
			return
		_acc += delta
		if _acc >= 0.4:
			_acc = 0.0
			for n in get_tree().get_nodes_in_group("hurtable"):
				if n is Node2D and n.has_method("aplicar_status") and n.global_position.distance_to(global_position) <= raio:
					n.aplicar_status("lentidao", 0.5, lentidao)
		queue_redraw()
		if _t >= dur_chao:
			queue_free()

	func _explodir() -> void:
		var pai: Node = get_parent()
		if pai == null:
			return
		Vfx.registrar_decalque(self)
		var folha := PASTA + "gelo_explosao.png"
		if ResourceLoader.exists(folha):
			var tex: Texture2D = load(folha)
			var sp := Sprite2D.new()
			sp.texture = tex
			sp.hframes = 8
			sp.material = Feel.aditivo()
			sp.scale = Vector2.ONE * (raio * 2.0 / (tex.get_width() / 8.0))
			sp.z_index = 5
			sp.position = Vector2(0, -10)
			add_child(sp)
			var tw := sp.create_tween()
			tw.tween_method(func(q: float): sp.frame = clampi(int(q), 0, 7), 0.0, 7.999, 0.55)
			tw.tween_callback(sp.queue_free)
		Feel.impacto(pai, global_position + Vector2(0, -10), PAL[1], Vector2.ZERO, raio / 40.0)
		Feel.shake(self, 4.0, 0.18)
		for n in get_tree().get_nodes_in_group("hurtable"):
			if n is Node2D and n.has_method("take_damage") and n.global_position.distance_to(global_position) <= raio:
				n.take_damage(dano, global_position)
				if is_instance_valid(n):
					load("res://scripts2d/efeitos_arqueiro_gelo_2d.gd").acumular_frio(n, acumulos, def)

	## Chão gelado (C0): placa branca-azulada achatada, rachaduras hexagonais que escurecem, borda que respira.
	func _draw() -> void:
		if not _caiu:
			return
		var apaga: float = clampf((dur_chao - _t) / FADE_CHAO, 0.0, 1.0)   # some nos últimos 0,6 s (ajuste do Jev)
		var cresce := minf(1.0, _t * 6.0)
		draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.55))
		var r := raio * cresce
		draw_circle(Vector2.ZERO, r, Color(PAL[1], 0.15 * apaga))
		draw_circle(Vector2.ZERO, r * 0.6, Color(PAL[0], 0.12 * apaga))
		draw_arc(Vector2.ZERO, r, 0.0, TAU, 6, Color(PAL[0], (0.4 + 0.1 * sin(_t * 5.0)) * apaga), 2.0)   # hexágono
		draw_arc(Vector2.ZERO, r * 0.98, 0.0, TAU, 6, Color(PAL[2], 0.35 * apaga), 1.0)
		for rc in _rachas:
			var d := Vector2.from_angle(rc[0])
			var fim: Vector2 = d * r * float(rc[1])
			var meio: Vector2 = d * r * float(rc[2]) * float(rc[1])
			var ramo: Vector2 = meio + d.rotated(0.9) * r * 0.22
			draw_line(Vector2.ZERO, fim, Color(PAL[2], 0.5 * apaga), 2.0)
			draw_line(Vector2.ZERO, fim, Color(PAL[0], 0.55 * apaga), 0.9)
			draw_line(meio, ramo, Color(PAL[2], 0.4 * apaga), 1.5)
			draw_line(meio, ramo, Color(PAL[0], 0.5 * apaga), 0.8)

## Corpo do cometa (filho em C5 enquanto cai): núcleo facetado que gira, halo frio e cauda de cristais para cima.
class CometaCorpo extends Node2D:
	var dona: Node2D
	func _ready() -> void:
		material = Feel.aditivo()
	func _draw() -> void:
		if dona == null:
			return
		var pal: Array = dona.PAL
		var t: float = dona._t
		var r: float = clampf(dona.raio * 0.22, 14.0, 34.0)
		draw_circle(Vector2.ZERO, r * 2.2, Color(pal[1], 0.18))
		draw_circle(Vector2.ZERO, r * 1.4, Color(pal[1], 0.35))
		# cauda: cristais menores subindo atrás do núcleo
		for i in 6:
			var k := float(i + 1) / 6.0
			var p := Vector2(sin(t * 13.0 + i) * r * 0.5, -r * (1.2 + 2.6 * k))
			var tam := r * (0.45 - 0.3 * k)
			var rot := t * 6.0 + i
			var pts := PackedVector2Array([p + Vector2(0, -tam * 1.8).rotated(rot), p + Vector2(tam, 0).rotated(rot), p + Vector2(0, tam * 1.8).rotated(rot), p + Vector2(-tam, 0).rotated(rot)])
			draw_colored_polygon(pts, Color(pal[1], 0.8 * (1.0 - k)))
			draw_line(pts[0], pts[2], Color(pal[0], 1.0 - k), 1.0)
		# núcleo facetado (hexágono girando) com miolo branco
		var rot0 := t * 2.5
		var nuc := PackedVector2Array()
		for i in 6:
			nuc.append(Vector2.from_angle(rot0 + TAU * i / 6.0) * r * (0.85 if i % 2 == 0 else 1.0))
		draw_colored_polygon(nuc, Color(pal[1], 0.95))
		draw_polyline(nuc + PackedVector2Array([nuc[0]]), Color(pal[2], 0.9), 2.0)
		draw_circle(Vector2.ZERO, r * 0.45, Color(pal[0], 1.0))
		for i in 3:
			draw_line(nuc[i], nuc[i + 3], Color(pal[0], 0.7), 1.0)

## Nova Gélida: anel no chão (C0) que cresce até `raio` em 0,3 s; cada inimigo é golpeado quando a borda o alcança.
## `qtd` lascas (folha gelo_lasca, ou losangos) voam para fora até 1,6 × raio e giram.
class Nova extends Node2D:
	const PAL := [Color("F0FBFF"), Color("7FD3F2"), Color("123A5C")]
	const EXPANDE := 0.3
	const VIDA := 0.8
	var raio := 200.0
	var dano := 0.0
	var lascas := 8
	var def := {}
	var _t := 0.0
	var _atingidos: Array = []
	var _pontas: Array = []   # [ang, tam]

	func configurar(d: Dictionary, dn: float) -> void:
		def = d
		raio = d.get("raio", 200.0)
		lascas = maxi(0, int(d.get("qtd", 8)))
		dano = dn
		z_index = -1

	func _ready() -> void:
		Vfx.registrar_animado(self)
		var rng := RandomNumberGenerator.new()
		rng.randomize()
		for i in 18:
			_pontas.append([TAU * i / 18.0 + rng.randf_range(-0.1, 0.1), rng.randf_range(0.5, 1.0)])
		var pai: Node = get_parent()
		var folha := PASTA + "gelo_lasca.png"
		var tex: Texture2D = load(folha) if ResourceLoader.exists(folha) else null
		for i in lascas:
			var ang := TAU * i / float(lascas)
			var s: Node2D
			if tex != null:
				var sp := Sprite2D.new()
				sp.texture = tex
				sp.hframes = 4
				sp.frame = i % 4
				sp.material = Feel.aditivo()
				sp.scale = Vector2.ONE * (72.0 / (tex.get_width() / 4.0))
				s = sp
			else:
				s = Lasca.new()
			s.z_index = 4
			s.rotation = ang
			pai.add_child(s)
			s.global_position = global_position + Vector2(0, -20)
			var tw := s.create_tween().set_parallel(true)
			tw.tween_property(s, "global_position", global_position + Vector2.from_angle(ang) * raio * 1.6 + Vector2(0, -20), 0.38).set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_QUAD)
			tw.tween_property(s, "rotation", ang + TAU * 1.5, 0.38)
			tw.tween_property(s, "modulate:a", 0.0, 0.2).set_delay(0.22)
			tw.chain().tween_callback(s.queue_free)

	func _physics_process(delta: float) -> void:
		_t += delta
		var r := raio * clampf(_t / EXPANDE, 0.0, 1.0)
		for n in get_tree().get_nodes_in_group("hurtable"):
			if n is Node2D and n.has_method("take_damage") and not _atingidos.has(n) and n.global_position.distance_to(global_position) <= r:
				_atingidos.append(n)
				n.take_damage(dano, global_position)
				if is_instance_valid(n):
					load("res://scripts2d/efeitos_arqueiro_gelo_2d.gd").acumular_frio(n, 2, def)
					Feel.impacto(get_parent(), n.global_position + Vector2(0, -24), PAL[1], Vector2.ZERO, 0.8)
		queue_redraw()
		if _t >= VIDA:
			queue_free()

	func _draw() -> void:
		var k := clampf(_t / EXPANDE, 0.0, 1.0)
		var r := raio * (1.0 - pow(1.0 - k, 2.0))
		var apaga := clampf((VIDA - _t) / 0.35, 0.0, 1.0)
		draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.55))
		# gradiente radial: centro quase vazio, faixa clara perto da borda (nada de disco chapado)
		draw_circle(Vector2.ZERO, r, Color(PAL[1], 0.05 * apaga))
		for i in 4:
			var f := 0.55 + 0.11 * i
			draw_arc(Vector2.ZERO, r * f, 0.0, TAU, 64, Color(PAL[1], (0.06 + 0.07 * i) * apaga), r * 0.12)
		draw_arc(Vector2.ZERO, r * 0.97, 0.0, TAU, 64, Color(PAL[0], 0.3 * apaga), 8.0)   # brilho da borda
		draw_arc(Vector2.ZERO, r, 0.0, TAU, 64, Color(PAL[1], 0.45 * apaga), 10.0)   # halo
		draw_arc(Vector2.ZERO, r, 0.0, TAU, 64, Color(PAL[0], 0.95 * apaga), 2.5)    # borda clara
		draw_arc(Vector2.ZERO, r * 0.9, 0.0, TAU, 64, Color(PAL[2], 0.5 * apaga), 1.0)
		for pt in _pontas:   # pontas de cristal na borda (silhueta angular)
			var d := Vector2.from_angle(pt[0])
			var b := d * r
			var alt: float = (10.0 + 18.0 * float(pt[1])) * (0.6 + 0.4 * k)
			var tri := PackedVector2Array([b + d.orthogonal() * 5.0, b + d * alt, b - d.orthogonal() * 5.0])
			draw_colored_polygon(tri, Color(PAL[1], 0.85 * apaga))
			draw_line(b, b + d * alt, Color(PAL[0], apaga), 1.0)

## Lasca desenhada em código quando a folha não existe.
class Lasca extends Node2D:
	func _ready() -> void:
		material = Feel.aditivo()
	func _draw() -> void:
		var pts := PackedVector2Array([Vector2(16, 0), Vector2(0, 5), Vector2(-14, 0), Vector2(0, -5)])
		draw_colored_polygon(pts, Color("7FD3F2"))
		draw_line(pts[0], pts[2], Color("F0FBFF"), 1.2)
