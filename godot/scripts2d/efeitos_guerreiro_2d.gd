extends RefCounted
## Efeitos das habilidades ativas do Guerreiro (contrato do sistema de habilidades).
## `executar` começa a habilidade; as com tempo de preparo, investida e salto rodam como estado do jogador
## (warrior_2d.gd) e chamam `aplicar` no momento do efeito. Números vêm de data2d/habilidades_guerreiro.csv.
## Cada habilidade tem mecânica e desenho próprios (design fixo de 01/11): as de aço cortam, giram, rasgam o chão e
## empurram; as dos quatro elementos chamam um raio do céu, põem lâminas em órbita, lançam uma meia-lua de fogo,
## abrem colunas de fogo, fazem brotar um anel de gelo, arremessam o escudo que ricocheteia, deixam poças de veneno
## e fincam um estandarte que pulsa. As folhas em pixel art estão em art2d/fx/guerreiro (fx_guerreiro_2d.gd).

const Feel = preload("res://scripts2d/feel_2d.gd")
const Fx = preload("res://scripts2d/fx_guerreiro_2d.gd")
const FxPixel = preload("res://scripts2d/fx_pixel_2d.gd")
const Alvos = preload("res://scripts2d/alvos_2d.gd")
const Vfx = preload("res://scripts2d/vfx_2d.gd")
const VfxIdent = preload("res://scripts2d/vfx_identidade_2d.gd")
const Raio = preload("res://scripts2d/efeitos_arqueiro_raio_2d.gd")
const Gelo = preload("res://scripts2d/efeitos_arqueiro_gelo_2d.gd")
const FogoAnim = preload("res://scripts2d/fogo_anim_2d.gd")
const Afinidades = preload("res://scripts2d/afinidades_2d.gd")

const COR_LAMINA := Color(0.95, 0.92, 0.8)
const COR_PESADO := Color(1.0, 0.74, 0.46)
const COR_ESCUDO := Color(0.35, 0.65, 0.95)
const COR_FURIA := Color(1.0, 0.42, 0.3)
const COR_GRITO := Color(1.0, 0.78, 0.36)
const COR_PEDRA := Color(0.86, 0.72, 0.52)
const CORES := {"raio": Color("5FA8FF"), "veneno": Color("5CD12B"), "gelo": Color("7FD3F2"), "fogo": Color("FF7A1F")}
## Tinta dos cortes em marfim para cada elemento (clara o bastante para a folha continuar com três tons).
const TINTAS := {"raio": Color(0.62, 0.8, 1.0), "veneno": Color(0.62, 0.95, 0.4), "gelo": Color(0.66, 0.92, 1.0), "fogo": Color(1.0, 0.62, 0.3)}
const PEITO := Vector2(0, -30)
const COM_PREPARO := ["golpe_pesado", "redemoinho", "fenda_pedra", "escudada", "grito_guerra", "furia", "golpe_trovao",
	"laminas_tempestade", "onda_flamejante", "erupcao", "cravar_gelido", "escudo_geada", "talho_pestilento", "estandarte_peste"]

## true = consumiu recarga e custo; false = cancelou.
static func executar(efeito: String, jogador: Node2D, def: Dictionary, nivel: int, mira: Vector2) -> bool:
	if jogador.estado != jogador.Estado.LIVRE:
		return false
	def = _crescer_com_nivel(jogador, def)
	match efeito:
		"investida":
			jogador.comecar_investida(def, mira, nivel)
		"salto_sismico":
			jogador.comecar_salto(def, mira, nivel)
		"golpe_trovao", "estandarte_peste":
			var ponto := _ponto_alvo(jogador, mira, def.get("alcance", 300.0), def.get("raio", 90.0))
			if efeito == "golpe_trovao":
				Vfx.sombra_aviso(jogador.get_parent(), ponto, def.get("raio", 90.0), CORES["raio"], def.get("espera", 0.3))
			jogador.comecar_conjuracao(efeito, def, mira, nivel, ponto)
		_:
			if not COM_PREPARO.has(efeito):
				return false
			jogador.comecar_conjuracao(efeito, def, mira, nivel)
	return true

## Cada nível de partida acrescenta alvos, raio e duração às habilidades ativas (o nível da gema continua valendo à parte).
static func _crescer_com_nivel(j: Node2D, def: Dictionary) -> Dictionary:
	var np: int = maxi(int(j.get("nivel_partida")) - 1, 0)
	if np <= 0:
		return def
	var d := def.duplicate()
	if d.has("qtd") and str(d.get("ramo", "")) != "lamina":
		d["qtd"] = d["qtd"] + floorf(np * j.stats.get("hab_qtd_por_nivel", 0.15))
	if d.has("raio"):
		d["raio"] = d["raio"] * (1.0 + np * j.stats.get("hab_raio_por_nivel", 0.02))
	if d.has("duracao") and str(d.get("ramo", "")) != "lamina":
		d["duracao"] = d["duracao"] * (1.0 + np * j.stats.get("hab_duracao_por_nivel", 0.02))
	return d

## Onde a habilidade de ponto cai: no maior grupo ao alcance; sem ninguém, um pouco à frente na mira.
static func _ponto_alvo(j: Node2D, mira: Vector2, alcance: float, raio: float) -> Vector2:
	var alvo: Node2D = Alvos.centro_de_grupo(j.get_tree(), j.global_position, alcance, raio)
	return alvo.global_position if alvo != null else j.global_position + mira * minf(alcance * 0.5, 160.0)

static func _vivo(n) -> bool:
	return is_instance_valid(n) and n.has_method("take_damage") and not (n.has_method("esta_morto") and n.esta_morto())

static func _perto(j: Node2D, centro: Vector2, r: float) -> Array:
	return Alvos.no_raio(j.get_tree(), centro, r, "take_damage")

## Efeito preso ao guerreiro (acompanha o corpo): giro, auras.
static func _no_jogador(j: Node2D, id: String, pos: Vector2, tam: float, cor := Color.WHITE) -> Node2D:
	var s := Fx.criar(id, tam, 0.0, cor)
	s.position = pos
	s.z_index = 1
	j.add_child(s)
	if s is AnimatedSprite2D and not s.sprite_frames.get_animation_loop("default"):
		s.animation_finished.connect(s.queue_free)
	return s

static func _poeira(j: Node2D, centro: Vector2, raio: float, n: int) -> void:
	for i in n:
		var a := TAU * float(i) / float(n) + 0.4
		Fx.tocar(j.get_parent(), "poeira", centro + Vector2(cos(a), sin(a) * 0.55) * raio, 0.0, 0.0, Color.WHITE, 0)

## Aplica o efeito no instante certo (fim do preparo, ou ao pousar no salto). `ponto` só vale para as de ponto.
static func aplicar(efeito: String, j: Node2D, d: Dictionary, nivel: int, mira: Vector2, ponto := Vector2.INF) -> void:
	var cena: Node = j.get_parent()
	var pos: Vector2 = j.global_position
	match efeito:
		"golpe_pesado":
			for a in j.alvos_cone(pos, mira, d["raio"], d["angulo"]):
				j.acertar(a, d["dano"])
			Fx.tocar(cena, "corte_pesado", pos + PEITO, d["raio"], mira.angle(), COR_PESADO)
			_poeira(j, pos + mira * d["raio"] * 0.55, 26.0, 3)
			Feel.shake(j, 4.0, 0.15)
		"redemoinho":
			for a in j.alvos_cone(pos, mira, d["raio"], 360.0):
				j.acertar(a, d["dano"])
			_no_jogador(j, "giro", Vector2(0, -22), d["raio"], COR_LAMINA)
			Feel.shake(j, 3.0, 0.12)
		"fenda_pedra":
			for a in j.alvos_retangulo(pos, mira, d["alcance"], d["raio"]):
				j.acertar(a, d["dano"], 0.4)
			var f := Fx.tocar(cena, "fenda", pos + mira * 18.0, d["alcance"], mira.angle(), Color.WHITE, 0)
			f.scale.y = maxf(f.scale.y, Fx.ESCALA)   # a fenda estica no comprimento; as lascas não ficam menores que a grade
			Feel.shake(j, 5.0, 0.2)
		"escudada":
			for a in j.alvos_cone(pos, mira, d["raio"], d["angulo"]):
				j.acertar(a, d["dano"], d["duracao"])
			j.velocity += mira * 220.0
			Fx.tocar(cena, "escudada", pos + PEITO + mira * 22.0, d["raio"] * 0.8, mira.angle())
			Feel.shake(j, 3.0, 0.1)
		"grito_guerra":
			j.buff_grito(d["duracao"], d["valor"])
			for a in j.alvos_cone(pos, mira, d["raio"], 360.0):
				j.aplicar_status(a, "atordoamento", 0.5)
				a.take_damage(1.0, pos)  # só empurra: o dano é simbólico
			Fx.tocar(cena, "onda", pos, d["raio"], 0.0, COR_GRITO, 0)
			Feel.shake(j, 3.0, 0.15)
		"furia":
			j.buff_furia(d["duracao"], d["valor"])
			if j.has_node("AuraFuria"):
				j.get_node("AuraFuria").free()
			var aura := _no_jogador(j, "furia", Vector2(0, 4), 0.0)
			aura.name = "AuraFuria"
			aura.z_index = -1
			j.get_tree().create_timer(d["duracao"], false).timeout.connect(func():
				if is_instance_valid(aura):
					aura.queue_free())
			Fx.tocar(cena, "onda", pos, 110.0, 0.0, COR_FURIA, 0)
			Feel.shake(j, 6.0, 0.25)
		"investida":
			Fx.tocar(cena, "escudada", pos + PEITO + mira * 20.0, 44.0, mira.angle(), COR_PESADO)
		"salto_sismico":
			for a in j.alvos_cone(pos, mira, d["raio"], 360.0):
				j.acertar(a, d["dano"], maxf(d["valor"], 1.0))
			Fx.tocar(cena, "onda", pos, d["raio"], 0.0, COR_PEDRA, 0)
			_poeira(j, pos, d["raio"] * 0.5, 6)
			Feel.shake(j, 7.0, 0.25)
		"golpe_trovao":
			_golpe_trovao(j, d, ponto if ponto != Vector2.INF else pos + mira * 120.0)
		"laminas_tempestade":
			if j.has_node("LaminasTempestade"):
				j.get_node("LaminasTempestade").free()
			var l := LaminasOrbitais.new()
			l.name = "LaminasTempestade"
			l.preparar(j, d)
			j.add_child(l)
		"onda_flamejante":
			var n := 1 + int(d.get("proj_extra", 0))
			for i in n:
				var o := OndaFogo.new()
				o.preparar(j, d, mira.rotated(deg_to_rad(16.0) * (i - (n - 1) * 0.5)))
				cena.add_child(o)
				o.global_position = pos + mira * 30.0
			Fx.tocar(cena, "corte", pos + PEITO, 84.0, mira.angle(), TINTAS["fogo"])
		"erupcao":
			_erupcao(j, d, mira)
		"cravar_gelido":
			for a in _perto(j, pos, d["raio"]):
				j.acertar(a, d["dano"])
				Gelo.acumular_frio(a, int(d.get("qtd", 2)), d)
			Fx.tocar(cena, "anel_gelo", pos, d["raio"], 0.0, Color.WHITE, 0)
			Feel.shake(j, 4.0, 0.15)
		"escudo_geada":
			var e := EscudoVoador.new()
			e.preparar(j, d, mira)
			cena.add_child(e)
			e.global_position = pos + mira * 24.0
		"talho_pestilento":
			for a in j.alvos_cone(pos, mira, d["raio"], d["angulo"]):
				j.acertar(a, d["dano"])
				j.aplicar_status(a, "veneno", d["duracao"], d["valor"])
			Fx.tocar(cena, "corte_pesado", pos + PEITO, d["raio"], mira.angle(), TINTAS["veneno"])
			var meio: float = deg_to_rad(d["angulo"]) * 0.32
			for k in [-1.0, 0.0, 1.0]:
				zona_chao(j, pos + mira.rotated(meio * k) * d["raio"] * 0.62, d["raio"] * 0.36, d["duracao"], "veneno", d["valor"])
		"estandarte_peste":
			var b := Estandarte.new()
			b.preparar(j, d)
			cena.add_child(b)
			b.global_position = ponto if ponto != Vector2.INF else pos + mira * 80.0

# ---------------------------------------------------------------- Eco da lâmina (afinidade do golpe básico)

## Chamado pelo guerreiro depois de cada golpe básico com Eco: `alvos` = quem o corte acertou, `combo` = 1, 2 ou 3.
static func eco_golpe(j: Node2D, alvos: Array, combo: int, def: Dictionary, mira: Vector2, alcance: float) -> void:
	var el := str(def.get("elemento", ""))
	var cena: Node = j.get_parent()
	var vistos := 0
	for a in alvos:
		if not _vivo(a):
			continue
		match el:
			"raio":
				if combo == 3:
					Raio.aplicar_choque(a, def.get("duracao", 2.0), 0.15)
			"veneno":
				j.aplicar_status(a, "veneno", def.get("duracao", 4.0), def.get("valor", 4.0))
			"gelo":
				Gelo.acumular_frio(a, int(def.get("qtd", 1)), def)
			"fogo":
				j.aplicar_status(a, "queimadura", def.get("duracao", 2.5), def.get("valor", 3.0))
		if vistos < 3 and is_instance_valid(a):
			VfxIdent.impacto(cena, a.global_position + PEITO, el, mira, 0.8)
			vistos += 1
	if combo != 3:
		return
	var vivos: Array = alvos.filter(func(a): return _vivo(a))
	if el == "raio":
		if not vivos.is_empty():
			_saltar(j, vivos[0], alvos, j.dano_base(def.get("valor", 0.5)), def.get("raio", 150.0), int(def.get("qtd", 2)), def.get("duracao", 2.0))
	elif el == "fogo":
		zona_chao(j, j.global_position + mira * alcance * 0.6, def.get("raio", 44.0), 1.5, "queimadura", def.get("valor", 3.0))
		if not vivos.is_empty():
			_contagiar(j, vivos[0], alvos, def, "fogo")
	elif not vivos.is_empty():   # peste e gelo: o efeito pula para quem estava fora do corte
		_contagiar(j, vivos[0], alvos, def, el)

## Contágio: o status do Eco pula do alvo para até `qtd` vizinhos fora do corte (peste espalha veneno, gelo soma frio, fogo acende).
static func _contagiar(j: Node2D, de: Node2D, ja: Array, def: Dictionary, el: String) -> void:
	var visitados: Array = ja.duplicate()
	var atual: Node2D = de
	var cena: Node = j.get_parent()
	var raio: float = maxf(def.get("raio", 0.0), j.stats.get("proc_contagio_raio", 140.0))
	for _i in int(def.get("qtd", 1)):
		var prox: Node2D = Raio.mais_proximo_de(j, atual.global_position, raio, visitados)
		if prox == null:
			break
		visitados.append(prox)
		VfxIdent.impacto(cena, prox.global_position + PEITO, el, Vector2.ZERO, 0.8)
		match el:
			"veneno":
				j.aplicar_status(prox, "veneno", def.get("duracao", 4.0), def.get("valor", 4.0))
			"gelo":
				Gelo.acumular_frio(prox, 1, def)
			"fogo":
				j.aplicar_status(prox, "queimadura", def.get("duracao", 2.5), def.get("valor", 3.0))
		prox.take_damage(j.dano_base(0.35), atual.global_position)
		atual = prox

## Fúria elemental: cada golpe do combo ativa, por sorte, o Eco de todo elemento que o jogador aprendeu na árvore (além do Eco
## escolhido). Mais níveis em habilidades de um elemento = mais chance e mais saltos, então a tela vai enchendo de raio,
## veneno, gelo e brasa conforme a partida avança.
static func furia_elemental(j: Node2D, alvos: Array, mira: Vector2, alcance: float, eco: Dictionary) -> void:
	if alvos.is_empty():
		return
	var ecos: Dictionary = Afinidades.defs("guerreiro")
	var nivel_p: int = j.nivel_partida
	for id in ecos:
		var d: Dictionary = ecos[id].duplicate()
		var el := str(d.get("elemento", ""))
		var ranks: int = j.habilidades.pontos_do_ramo(el)
		if ranks <= 0:
			continue
		var chance: float = clampf(j.stats.get("proc_base", 0.0) + j.stats.get("proc_por_rank", 0.0) * ranks, 0.0, j.stats.get("proc_max", 0.9))
		if j._rng.randf() > chance:
			continue
		d["qtd"] = d.get("qtd", 1.0) + floorf(ranks * j.stats.get("proc_qtd_por_rank", 0.0)) + floorf(nivel_p * j.stats.get("proc_qtd_por_nivel", 0.0))
		d["raio"] = d.get("raio", 0.0) * (1.0 + 0.04 * ranks)
		eco_golpe(j, alvos, 3, d, mira, alcance)

## Arco que pula do alvo `de` para vizinhos ainda não atingidos (até `saltos`), com dano `dano` e choque.
static func _saltar(j: Node2D, de: Node2D, ja: Array, dano: float, raio: float, saltos: int, dur: float) -> void:
	var visitados: Array = ja.duplicate()
	var atual: Node2D = de
	var cena: Node = j.get_parent()
	for _i in saltos:
		var prox: Node2D = Raio.mais_proximo_de(j, atual.global_position, raio, visitados)
		if prox == null:
			break
		visitados.append(prox)
		Raio.arco_entre(cena, atual.global_position + Vector2(0, -24), prox.global_position + Vector2(0, -24))
		prox.take_damage(dano, atual.global_position)
		if _vivo(prox):
			Raio.aplicar_choque(prox, dur, 0.15)
			VfxIdent.impacto(cena, prox.global_position + Vector2(0, -24), "raio", Vector2.ZERO, 0.7)
		atual = prox

# ---------------------------------------------------------------- raio

static func _golpe_trovao(j: Node2D, d: Dictionary, ponto: Vector2) -> void:
	var cena: Node = j.get_parent()
	FxPixel.tocar(cena, "lightning_strike", ponto, 1.6, "base")
	FxPixel.tocar(cena, "thunderclap", ponto, d["raio"] * 2.0 / maxf(FxPixel.tamanho("thunderclap").x, 1.0), "centro", 0.0, 0)
	Feel.shake(j, 6.0, 0.2)
	var atingidos: Array = _perto(j, ponto, d["raio"])
	for a in atingidos:
		j.acertar(a, d["dano"])
		if _vivo(a):
			Raio.aplicar_choque(a, d["duracao"], 0.15)
	var vivos: Array = atingidos.filter(func(a): return _vivo(a))
	if not vivos.is_empty():
		_saltar(j, vivos[0], atingidos, j.dano_base(d["dano"] * d.get("valor", 0.5)), 170.0, int(d.get("qtd", 2)), d["duracao"])

## Lâminas da Tempestade: `qtd` espadas elétricas em órbita por `duracao` s; cada toque fere e deixa em choque.
class LaminasOrbitais extends Node2D:
	const Fxg = preload("res://scripts2d/fx_guerreiro_2d.gd")
	const AlvosG = preload("res://scripts2d/alvos_2d.gd")
	const RaioG = preload("res://scripts2d/efeitos_arqueiro_raio_2d.gd")
	var j: Node2D
	var d: Dictionary
	var resta := 0.0
	var ang := 0.0
	var laminas: Array = []
	var bateu := {}   # id do inimigo -> instante (ms) do último toque
	var _arco_t := 0.0

	func preparar(jogador: Node2D, def: Dictionary) -> void:
		j = jogador
		d = def
		resta = def.get("duracao", 6.0)
		for i in maxi(1, int(def.get("qtd", 3))):
			var s := Fxg.criar("lamina", 0.0, 0.0)
			add_child(s)
			laminas.append(s)

	func _physics_process(delta: float) -> void:
		resta -= delta
		if resta <= 0.0 or not is_instance_valid(j) or j.esta_morto():
			queue_free()
			return
		ang += delta * 4.2
		var r: float = d.get("raio", 78.0)
		var agora := Time.get_ticks_msec()
		for i in laminas.size():
			var a: float = ang + TAU * float(i) / float(laminas.size())
			var chao := Vector2(cos(a), sin(a) * 0.6) * r
			var s: Node2D = laminas[i]
			s.position = chao + Vector2(0, -24)
			s.rotation = Vector2(-sin(a), cos(a) * 0.6).angle()
			s.z_index = 1 if sin(a) > 0.0 else -1   # atrás do corpo na metade de cima da órbita
			for n in AlvosG.no_raio(get_tree(), j.global_position + chao, 34.0, "take_damage"):
				var id: int = n.get_instance_id()
				if agora - int(bateu.get(id, -100000)) < 600:
					continue
				bateu[id] = agora
				j.acertar(n, d.get("dano", 0.7))
				if is_instance_valid(n) and (n.get("hp") == null or n.hp > 0.0):
					RaioG.aplicar_choque(n, 2.0, d.get("valor", 0.15))
		_arco_t -= delta
		if _arco_t <= 0.0 and laminas.size() >= 2:   # faísca que corre de uma lâmina à outra
			_arco_t = 0.45
			var k := randi() % laminas.size()
			RaioG.arco_entre(j.get_parent(), laminas[k].global_position, laminas[(k + 1) % laminas.size()].global_position, 0.6)

## Espadas espectrais: orbitam o herói o tempo todo e cortam quem encosta. A quantidade cresce com o nível de XP da corrida
## (data2d/guerreiro.csv: espadas_por_nivel, espadas_max), então quem olha vê o herói ficando mais forte a cada nível.
class EspadasEspectrais extends Node2D:
	const Fxg = preload("res://scripts2d/fx_guerreiro_2d.gd")
	const AlvosG = preload("res://scripts2d/alvos_2d.gd")
	var j: Node2D
	var ang := 0.0
	var espadas: Array = []
	var bateu := {}   # id do inimigo -> instante (ms) do último toque
	var _pulso := 0.0

	func _ready() -> void:
		show_behind_parent = true

	func _draw() -> void:
		if espadas.is_empty():
			return
		# aura no chão (anel de aço tracejado, cores chapadas): fica sob o herói e cresce com as espadas
		var r: float = j.stats.get("espadas_raio", 74.0) * (1.0 + 0.04 * sin(_pulso * 2.0))
		draw_set_transform(Vector2(0, -2), 0.0, Vector2(1.0, 0.6))
		var n := 24
		for i in n:
			if i % 2 == 0:
				draw_arc(Vector2.ZERO, r, TAU * i / n + _pulso * 0.3, TAU * (i + 1) / n + _pulso * 0.3, 6, Color(0.55, 0.78, 1.0), 2.0)
		draw_arc(Vector2.ZERO, r * 0.55, 0.0, TAU, 24, Color(0.35, 0.5, 0.75), 1.0)

	func _physics_process(delta: float) -> void:
		if not is_instance_valid(j) or j.esta_morto():
			return
		_pulso += delta
		queue_redraw()
		var alvo := mini(int(j.nivel_partida * j.stats.get("espadas_por_nivel", 0.0)), int(j.stats.get("espadas_max", 0.0)))
		while espadas.size() < alvo:
			var s := Fxg.criar("lamina", 46.0, 0.0, Color(0.75, 0.9, 1.0))
			add_child(s)
			espadas.append(s)
		ang += delta * j.stats.get("espadas_vel", 3.0)
		var r: float = j.stats.get("espadas_raio", 74.0)
		var agora := Time.get_ticks_msec()
		for i in espadas.size():
			var a: float = ang + TAU * float(i) / float(espadas.size())
			var chao := Vector2(cos(a), sin(a) * 0.6) * r
			var s: Node2D = espadas[i]
			s.position = chao + Vector2(0, -24)
			s.rotation = Vector2(-sin(a), cos(a) * 0.6).angle()
			s.z_index = 1 if sin(a) > 0.0 else -1
			for n in AlvosG.no_raio(get_tree(), j.global_position + chao, 30.0, "take_damage"):
				var id: int = n.get_instance_id()
				if agora - int(bateu.get(id, -100000)) < 600:
					continue
				bateu[id] = agora
				j.acertar(n, j.stats.get("espadas_dano", 0.35))

# ---------------------------------------------------------------- fogo

## Meia-lua de fogo que anda em linha reta, atravessa os inimigos (queima cada um uma vez) e deixa brasas.
class OndaFogo extends Node2D:
	const Fxg = preload("res://scripts2d/fx_guerreiro_2d.gd")
	const AlvosG = preload("res://scripts2d/alvos_2d.gd")
	var j: Node2D
	var d: Dictionary
	var dir := Vector2.RIGHT
	var andou := 0.0
	var brasa := 0.0
	var feridos := {}

	func preparar(jogador: Node2D, def: Dictionary, direcao: Vector2) -> void:
		j = jogador
		d = def
		dir = direcao.normalized()
		var s := Fxg.criar("onda_fogo", maxf(def.get("raio", 46.0) * 2.6, 110.0), dir.angle())
		s.position = Vector2(0, -24)
		add_child(s)

	func _physics_process(delta: float) -> void:
		if not is_instance_valid(j):
			queue_free()
			return
		var passo: float = 520.0 * maxf(d.get("vel", 1.0), 0.25) * delta
		global_position += dir * passo
		andou += passo
		brasa += passo
		for n in AlvosG.no_raio(get_tree(), global_position, d.get("raio", 46.0) + 14.0, "take_damage"):
			if feridos.has(n.get_instance_id()):
				continue
			feridos[n.get_instance_id()] = true
			j.acertar(n, d.get("dano", 1.8))
			j.aplicar_status(n, "queimadura", d.get("duracao", 2.5), d.get("valor", 4.0))
		if brasa >= 80.0:
			brasa = 0.0
			j.Efeitos.zona_chao(j, global_position, 34.0, 1.6, "queimadura", d.get("valor", 4.0))
		if andou >= d.get("alcance", 380.0):
			queue_free()

## Onda de corte: meia-lua que sai da lâmina no 3º golpe e atravessa quem está na frente (cresce com o nível de XP).
class OndaCorte extends Node2D:
	const Fxg = preload("res://scripts2d/fx_guerreiro_2d.gd")
	const AlvosG = preload("res://scripts2d/alvos_2d.gd")
	var j: Node2D
	var dir := Vector2.RIGHT
	var dano := 0.8
	var raio := 40.0
	var alcance := 300.0
	var cor := Color.WHITE
	var andou := 0.0
	var rastro := 0.0
	var feridos := {}

	func _physics_process(delta: float) -> void:
		if not is_instance_valid(j):
			queue_free()
			return
		var passo := 620.0 * delta
		global_position += dir * passo
		andou += passo
		rastro += passo
		if rastro >= 36.0:
			rastro = 0.0
			Fxg.tocar(get_parent(), "corte", global_position + Vector2(0, -30), raio * 1.6, dir.angle(), cor, 1)
		for n in AlvosG.no_raio(get_tree(), global_position, raio, "take_damage"):
			if feridos.has(n.get_instance_id()):
				continue
			feridos[n.get_instance_id()] = true
			j.acertar(n, dano)
		if andou >= alcance:
			queue_free()

## Lança `qtd` ondas de corte em leque a partir do herói.
static func ondas_de_corte(j: Node2D, mira: Vector2, qtd: int, cor: Color) -> void:
	var cena: Node = j.get_parent()
	for i in qtd:
		var o := OndaCorte.new()
		o.j = j
		o.dir = mira.rotated(deg_to_rad(j.stats.get("onda_leque", 14.0)) * (i - (qtd - 1) * 0.5))
		o.dano = j.stats.get("onda_dano", 0.8)
		o.raio = j.stats.get("onda_raio", 40.0)
		o.alcance = j.stats.get("onda_alcance", 300.0)
		o.cor = cor
		cena.add_child(o)
		o.global_position = j.global_position + mira * 28.0

## Erupção: `qtd` colunas de fogo em linha, uma depois da outra, cada uma com aviso no chão; o chão fica em brasa.
static func _erupcao(j: Node2D, d: Dictionary, mira: Vector2) -> void:
	var cena: Node = j.get_parent()
	var n := maxi(1, int(d.get("qtd", 3)))
	var origem: Vector2 = j.global_position
	for i in n:
		var p: Vector2 = origem + mira * d["alcance"] * float(i + 1) / float(n)
		var atraso := 0.22 * i
		j.get_tree().create_timer(maxf(atraso, 0.01), false).timeout.connect(func():
			if not is_instance_valid(j) or not is_instance_valid(cena):
				return
			Vfx.sombra_aviso(cena, p, d["raio"], CORES["fogo"], 0.2)
			j.get_tree().create_timer(0.2, false).timeout.connect(func():
				if is_instance_valid(j) and is_instance_valid(cena):
					_pilar(j, d, p)))

## Coluna de fogo no ponto `p`: fere, queima e deixa brasas.
static func _pilar(j: Node2D, d: Dictionary, p: Vector2) -> void:
	var cena: Node = j.get_parent()
	Fx.tocar(cena, "pilar_fogo", p, d["raio"] * 2.0, 0.0, Color(1, 1, 1, 0.8), -1)   # atrás dos atores e translúcido: o herói não some na chama
	for a in _perto(j, p, d["raio"]):
		j.acertar(a, d["dano"])
		j.aplicar_status(a, "queimadura", d["duracao"], d["valor"])
	zona_chao(j, p, d["raio"] * 0.8, d["duracao"], "queimadura", d["valor"])
	Feel.shake(j, 4.0, 0.12)

## Reverberação: o eco de uma ativa já aprendida cai em `p` (do céu, anel no chão, poça ou cadeia de raios), sem animação do herói.
static func reverberar(j: Node2D, d: Dictionary, p: Vector2) -> void:
	var cena: Node = j.get_parent()
	match str(d.get("efeito", "")):
		"golpe_trovao", "laminas_tempestade":
			_golpe_trovao(j, d, p)
		"erupcao", "onda_flamejante":
			Vfx.sombra_aviso(cena, p, d["raio"], CORES["fogo"], 0.2)
			j.get_tree().create_timer(0.2, false).timeout.connect(func():
				if is_instance_valid(j) and is_instance_valid(cena):
					_pilar(j, d, p))
		"cravar_gelido", "escudo_geada":
			for a in _perto(j, p, d["raio"]):
				j.acertar(a, d["dano"])
				Gelo.acumular_frio(a, int(d.get("qtd", 2)), d)
			Fx.tocar(cena, "anel_gelo", p, d["raio"], 0.0, Color.WHITE, 0)
		"talho_pestilento", "estandarte_peste":
			for a in _perto(j, p, d["raio"]):
				j.acertar(a, d["dano"])
				j.aplicar_status(a, "veneno", d["duracao"], d["valor"])
			Fx.tocar(cena, "onda", p, d["raio"], 0.0, TINTAS["veneno"], 0)
			zona_chao(j, p, d["raio"] * 0.8, d["duracao"], "veneno", d["valor"])

## Reverberações: de tempos em tempos cada ativa elemental aprendida ecoa sobre inimigos aleatórios. Quanto maior o nível da
## partida, mais seguidas e mais numerosas (data2d/guerreiro.csv: rev_*). Habilidade no nível máximo conta em dobro e ecoa maior.
class Reverberacoes extends Node2D:
	const Efeitos = preload("res://scripts2d/efeitos_guerreiro_2d.gd")
	const ELEMENTAIS := ["golpe_trovao", "laminas_tempestade", "erupcao", "onda_flamejante", "cravar_gelido", "escudo_geada", "talho_pestilento", "estandarte_peste"]
	var j: Node2D
	var _t := 1.0

	func _physics_process(delta: float) -> void:
		if not is_instance_valid(j) or j.esta_morto():
			return
		var np: int = j.nivel_partida
		if np < int(j.stats.get("rev_nivel_min", 5.0)):
			return
		_t -= delta
		if _t > 0.0:
			return
		_t = maxf(j.stats.get("rev_intervalo_min", 0.3), j.stats.get("rev_intervalo", 1.6) - j.stats.get("rev_intervalo_por_nivel", 0.08) * np)
		var sk = j.habilidades
		var ids: Array = []
		for id in sk.niveis:
			if sk.eh_ativa(id) and ELEMENTAIS.has(sk.defs[id]["efeito"]):
				ids.append(id)
				if sk.nivel(id) >= int(sk.defs[id]["nivel_max"]):
					ids.append(id)
		if ids.is_empty():
			return
		var alvos: Array = Efeitos._perto(j, j.global_position, j.stats.get("rev_alcance", 460.0)).filter(func(a): return Efeitos._vivo(a))
		if alvos.is_empty():
			return
		var n := mini(1 + int(np * j.stats.get("rev_por_nivel", 0.15)), int(j.stats.get("rev_max", 6.0)))
		for i in n:
			var id: String = ids[randi() % ids.size()]
			var d: Dictionary = Efeitos._crescer_com_nivel(j, sk.def_nivel(id))
			d["dano"] = d["dano"] * j.stats.get("rev_dano", 0.5)
			if sk.nivel(id) >= int(sk.defs[id]["nivel_max"]):
				d["raio"] = d["raio"] * 1.35
			var p: Vector2 = alvos[randi() % alvos.size()].global_position
			get_tree().create_timer(0.08 * i + 0.01, false).timeout.connect(func():
				if is_instance_valid(j) and not j.esta_morto():
					Efeitos.reverberar(j, d, p))

# ---------------------------------------------------------------- zonas no chão (brasa e poça de veneno)

## Zona que fica no chão por `dur` s e aplica o status (`queimadura` ou `veneno`, `dps` por segundo) a quem pisa.
static func zona_chao(j: Node2D, pos: Vector2, raio: float, dur: float, status: String, dps: float) -> void:
	if not is_instance_valid(j) or not Vfx.decalque_cabe(j.get_tree()):
		return
	var z := ZonaChao.new()
	z.raio = raio
	z.resta = dur
	z.status = status
	z.dps = dps
	j.get_parent().add_child(z)
	z.global_position = pos
	Vfx.registrar_decalque(z)

class ZonaChao extends Node2D:
	const Fxg = preload("res://scripts2d/fx_guerreiro_2d.gd")
	const AlvosG = preload("res://scripts2d/alvos_2d.gd")
	const Anim = preload("res://scripts2d/fogo_anim_2d.gd")
	var raio := 40.0
	var resta := 2.0
	var status := "veneno"
	var dps := 3.0
	var _tick := 0.0

	func _ready() -> void:
		z_index = -1
		if status == "veneno":
			add_child(Fxg.criar("poca", raio * 2.0))
		else:
			var b := Anim.new("brasas_chao", true, raio * 2.6)
			b.z_index = 0
			add_child(b)

	func _physics_process(delta: float) -> void:
		resta -= delta
		_tick -= delta
		modulate.a = clampf(resta / 0.4, 0.0, 1.0)
		if _tick <= 0.0:
			_tick = 0.5
			for n in AlvosG.no_raio(get_tree(), global_position, raio, "aplicar_status"):
				n.aplicar_status(status, 1.2, dps)
		if resta <= 0.0:
			queue_free()

# ---------------------------------------------------------------- gelo

## Escudo de Geada: voa até o alvo mais perto na mira, ricocheteia em até `qtd` inimigos somando frio e volta à mão.
class EscudoVoador extends Node2D:
	const Fxg = preload("res://scripts2d/fx_guerreiro_2d.gd")
	const AlvosG = preload("res://scripts2d/alvos_2d.gd")
	const RaioG = preload("res://scripts2d/efeitos_arqueiro_raio_2d.gd")
	const GeloG = preload("res://scripts2d/efeitos_arqueiro_gelo_2d.gd")
	const Ident = preload("res://scripts2d/vfx_identidade_2d.gd")
	var j: Node2D
	var d: Dictionary
	var dir := Vector2.RIGHT
	var alvo: Node2D
	var visitados: Array = []
	var toques := 0
	var voltando := false
	var andou := 0.0
	var vida := 6.0

	func preparar(jogador: Node2D, def: Dictionary, mira: Vector2) -> void:
		j = jogador
		d = def
		dir = mira.normalized()
		toques = maxi(1, int(def.get("qtd", 4)) + int(def.get("perfura", 0)) + int(def.get("proj_extra", 0)))
		var s := Fxg.criar("escudo", 0.0)
		s.position = Vector2(0, -28)
		add_child(s)
		z_index = 2

	func _vale(n) -> bool:
		return is_instance_valid(n) and (n.get("hp") == null or n.hp > 0.0)

	func _physics_process(delta: float) -> void:
		vida -= delta
		if not is_instance_valid(j) or vida <= 0.0:
			queue_free()
			return
		var passo: float = 620.0 * maxf(d.get("vel", 1.0), 0.25) * delta
		if voltando:
			var v: Vector2 = j.global_position - global_position
			if v.length() <= passo + 16.0:
				queue_free()
				return
			global_position += v.normalized() * passo
			return
		if not _vale(alvo):
			alvo = _proximo()
		if alvo == null:
			# sem alvo: segue reto até o alcance e volta
			global_position += dir * passo
			andou += passo
			if andou >= d.get("alcance", 360.0):
				voltando = true
			return
		var para: Vector2 = alvo.global_position - global_position
		if para.length() <= passo + 14.0:
			global_position = alvo.global_position
			visitados.append(alvo)
			j.acertar(alvo, d.get("dano", 1.3))
			if _vale(alvo):
				GeloG.acumular_frio(alvo, 1, d)
			Ident.impacto(get_parent(), global_position + Vector2(0, -28), "gelo", para.normalized(), 0.8)
			toques -= 1
			alvo = null
			if toques <= 0:
				voltando = true
			return
		dir = para.normalized()
		global_position += dir * passo
		andou += passo

	## Primeiro alvo: o mais perto do escudo ainda dentro do alcance do arremesso; depois, o vizinho a até `raio`.
	func _proximo() -> Node2D:
		var alcance: float = d.get("raio", 170.0) if not visitados.is_empty() else maxf(d.get("alcance", 360.0) - andou, 0.0)
		var n: Node2D = RaioG.mais_proximo_de(j, global_position, alcance, visitados)
		if n == null and not visitados.is_empty():
			voltando = true
		return n

# ---------------------------------------------------------------- veneno

## Estandarte da Peste: fica `duracao` s no chão e pulsa a cada segundo: dano, veneno e lentidão em quem está perto.
class Estandarte extends Node2D:
	const Fxg = preload("res://scripts2d/fx_guerreiro_2d.gd")
	const AlvosG = preload("res://scripts2d/alvos_2d.gd")
	var j: Node2D
	var d: Dictionary
	var resta := 6.0
	var _pulso := 0.3

	func preparar(jogador: Node2D, def: Dictionary) -> void:
		j = jogador
		d = def
		resta = def.get("duracao", 6.0)
		add_child(Fxg.criar("estandarte", 0.0))
		add_to_group("estandarte_peste")

	func _physics_process(delta: float) -> void:
		resta -= delta
		_pulso -= delta
		modulate.a = clampf(resta / 0.4, 0.0, 1.0)
		if resta <= 0.0 or not is_instance_valid(j):
			queue_free()
			return
		if _pulso <= 0.0:
			_pulso = 1.0
			var r: float = d.get("raio", 120.0)
			Fxg.tocar(get_parent(), "onda", global_position, r, 0.0, Color(0.62, 0.95, 0.4), 0)
			for n in AlvosG.no_raio(get_tree(), global_position, r, "take_damage"):
				n.take_damage(j.dano_base(d.get("dano", 0.5)), global_position)
				if is_instance_valid(n) and (n.get("hp") == null or n.hp > 0.0):
					n.aplicar_status("veneno", 2.5, d.get("valor", 5.0))
					n.aplicar_status("lentidao", 1.2, 0.25)
