extends RefCounted
## Árvore de FOGO do Arqueiro (doc 32_fogo): Flecha Ardente, Flecha Meteoro, Muralha de Brasas e Arauto das Cinzas.
## Contrato igual ao de efeitos_arqueiro_2d.gd: executar(efeito, jogador, def, nivel, mira) -> bool.
## Sem arte (PNG ausente) cada efeito cai num desenho de código, para o jogo e o teste headless nunca quebrarem.
## Nenhum número de balanceamento aqui: tudo vem do `def` (data2d/habilidades_arqueiro.csv).

const VfxIdent = preload("res://scripts2d/vfx_identidade_2d.gd")
const U = preload("res://scripts2d/fogo_util_2d.gd")
const Anim = preload("res://scripts2d/fogo_anim_2d.gd")
const COR_FOGO := Color(1.0, 0.55, 0.15)
const COR_BRASA := Color(1.0, 0.35, 0.1)
const TEMPO_QUEDA := 0.55   # só ritmo visual do meteoro

static func executar(efeito: String, jogador: Node2D, def: Dictionary, nivel: int, mira: Vector2) -> bool:
	if jogador == null or not jogador.is_inside_tree() or jogador.esta_morto():
		return false
	var dir: Vector2 = mira.normalized() if mira != Vector2.ZERO else jogador.mira_atual()
	var dano: float = jogador.stats["arrow_damage"] * def.get("dano", 1.0)
	match efeito:
		"tiro_ardente":
			var f = jogador.lancar_flecha(dir, def.get("dano", 1.0), 0, 1.0, def)
			f.cor_fx = COR_FOGO
			VfxIdent.anexar(f, "fogo")
			f.add_child(_VigiaImpacto.new(def.get("duracao", 3.0), def.get("valor", 4.0)))
			var pr := Anim.new("flecha_proj", true)
			pr.position = Vector2.ZERO
			f.vis.add_child(pr)
		"meteoro":
			var alvo: Vector2 = _ponto(jogador, dir, def.get("alcance", 600.0))
			# Forma "brasas" (passivo Chuva de Brasas): `qtd` quedas menores em linha na direção da mira, uma atrás da outra.
			var quedas: int = maxi(1, int(def.get("qtd", 1))) if def.get("forma", "") == "brasas" else 1
			var raio: float = def.get("raio", 140.0)
			for i in quedas:
				var p: Vector2 = alvo + dir * raio * 1.6 * float(i - (quedas - 1) / 2.0)
				var m := _Meteoro.new()
				m.preparar(p, raio, dano, def.get("duracao", 3.0), def.get("valor", 3.0))
				m.atraso = 0.15 * i
				jogador.get_parent().add_child(m)
				m.global_position = p
		"muralha":
			var m := _Muralha.new()
			var ini: Vector2 = jogador.global_position + dir * 60.0
			m.preparar(ini, dir, def.get("alcance", 320.0), def.get("raio", 44.0), dano, def.get("duracao", 5.0), def.get("qtd", 10), def.get("valor", 4.0))
			jogador.get_parent().add_child(m)
			m.global_position = ini
		_:
			push_error("Efeito de fogo desconhecido: " + efeito)
			return false
	return true

## Arauto das Cinzas (passiva): chamado pelo gatilho de abate (integradora). `sobra` = dano que passou da vida do inimigo.
## `def` traz valor = fração da sobra que vira explosão, raio, duracao da queimadura; `minimo` evita explodir por sobra irrisória.
static func ao_abate(jogador: Node2D, pos: Vector2, sobra: float, def: Dictionary) -> void:
	if jogador == null or not jogador.is_inside_tree() or sobra <= def.get("minimo", 0.0):
		return
	var raio: float = def.get("raio", 110.0)
	var dano: float = sobra * def.get("valor", 0.5)
	var cena: Node = jogador.get_parent()
	var e := Anim.new("arauto_explosao", false, raio * 2.0)
	e.global_position = pos
	e.z_index = 4
	cena.add_child(e)
	for n in cena.get_tree().get_nodes_in_group("hurtable"):
		if n is Node2D and n.global_position.distance_to(pos) <= raio and n.has_method("take_damage"):
			n.take_damage(dano, pos)
			if n.has_method("aplicar_status"):
				n.aplicar_status("queimadura", def.get("duracao", 3.0), def.get("dps", 3.0))

## Aura leve no arqueiro enquanto o Arauto está equipado. Devolve o nó para a integradora guardar e remover.
static func aura(jogador: Node2D) -> Node2D:
	var a := Anim.new("arauto_aura", true, 110.0)
	a.modulate.a = 0.55
	a.position = Vector2(0, -4)   # no chão, aos pés, atrás do arqueiro
	a.scale = Vector2(1.0, 0.5)
	a.show_behind_parent = true
	jogador.add_child(a)
	return a

## Overlay de queimadura sobre o inimigo (a integradora liga isto ao status "queimadura" em enemy_2d.gd).
static func overlay_queimadura(inimigo: Node2D) -> Node2D:
	var o := Anim.new("queimadura", true, 70.0)
	o.position = Vector2(0, -34)
	o.modulate.a = 0.9
	inimigo.add_child(o)
	return o

static func _ponto(jogador: Node2D, dir: Vector2, alcance: float) -> Vector2:
	if jogador.has_method("tem_alvo_auto") and jogador.tem_alvo_auto():
		return jogador.ponto_mira(alcance)
	return jogador.global_position + dir * 0.7 * alcance

## Preso à flecha ardente: quando ela some (acerto ou parede), queima quem estiver colado e solta o impacto.
class _VigiaImpacto extends Node:
	var dur: float
	var dps: float

	func _init(d: float, v: float) -> void:
		dur = d
		dps = v

	func _ready() -> void:
		get_parent().tree_exiting.connect(_ao_sair)

	func _ao_sair() -> void:
		var flecha: Node2D = get_parent()
		var cena: Node = flecha.get_parent()
		if cena == null or not flecha.is_inside_tree():
			return
		var pos: Vector2 = flecha.global_position
		var atingidos := U.no_raio(flecha, pos, 36.0)
		var e := Anim.new("flecha_impacto", false, 90.0)
		e.position = pos + Vector2(0, -30)
		cena.add_child.call_deferred(e)   # o pai está ocupado montando filhos durante o tree_exiting
		for n in atingidos:
			U.queimar(n, dur, dps)

## Flecha Meteoro: marca o chão, a bola cai, explode em área e deixa brasas que queimam por `duracao`.
class _Meteoro extends Node2D:
	var raio: float
	var dano: float
	var dur: float
	var dps: float
	var atraso := 0.0   # forma "brasas": cada queda espera um pouco mais (só ritmo visual)
	var _t := 0.0
	var _caiu := false
	var _queda: Node2D

	func preparar(_p: Vector2, r: float, d: float, du: float, v: float) -> void:
		raio = r
		dano = d
		dur = du
		dps = v
		z_index = -1

	func _ready() -> void:
		_queda = Anim.new("meteoro_queda", true, 150.0)
		_queda.position = Vector2(0, -420)
		add_child(_queda)

	func _physics_process(delta: float) -> void:
		if atraso > 0.0:
			atraso -= delta
			return
		_t += delta
		queue_redraw()
		if not _caiu:
			_queda.position.y = lerpf(-420.0, -20.0, clampf(_t / TEMPO_QUEDA, 0.0, 1.0))
			if _t >= TEMPO_QUEDA:
				_caiu = true
				_queda.queue_free()
				var e := Anim.new("meteoro_impacto", false, raio * 2.2)
				e.position = Vector2(0, -20)
				add_child(e)
				var b := Anim.new("brasas_chao", true, raio * 2.0)
				b.z_index = -1
				add_child(b)
				for n in U.no_raio(self, global_position, raio):
					n.take_damage(dano, global_position)
					U.queimar(n, dur, dps)
				_t = 0.0
		else:
			if fmod(_t, 0.5) < delta:
				for n in U.no_raio(self, global_position, raio):
					U.queimar(n, 1.0, dps)
			if _t >= dur:
				queue_free()

	func _draw() -> void:
		if not _caiu:   # telégrafo no chão
			var a := 0.15 + 0.35 * clampf(_t / TEMPO_QUEDA, 0.0, 1.0)
			draw_circle(Vector2.ZERO, raio, Color(COR_BRASA.r, COR_BRASA.g, COR_BRASA.b, a * 0.6))
			draw_arc(Vector2.ZERO, raio, 0.0, TAU, 40, Color(1.0, 0.6, 0.2, a + 0.2), 2.0)

## Muralha de Brasas: linha de chamas no chão; fere e queima quem cruza, em pulsos.
class _Muralha extends Node2D:
	var dir: Vector2
	var comp: float
	var larg: float
	var dano: float
	var dur: float
	var segmentos: int
	var dps: float
	var _t := 0.0
	var _prox := 0.0

	func preparar(_i: Vector2, d: Vector2, c: float, l: float, dm: float, du: float, seg: int, v: float) -> void:
		dir = d
		comp = c
		larg = l
		dano = dm
		dur = du
		segmentos = maxi(seg, 1)
		dps = v
		z_index = -1

	func _ready() -> void:
		for i in segmentos:
			var a := Anim.new("muralha_chama", true, larg * 2.4)
			a.position = dir * comp * (i + 0.5) / segmentos + Vector2(0, -larg * 0.5)
			a._t = randf() * 2.0   # chamas fora de fase
			add_child(a)

	func _physics_process(delta: float) -> void:
		_t += delta
		if _t >= _prox:
			_prox += 0.5
			for n in get_tree().get_nodes_in_group("hurtable"):
				if n is Node2D and _dist_linha(n.global_position) <= larg:
					n.take_damage(dano, global_position)
					U.queimar(n, 1.5, dps)
		if _t >= dur:
			queue_free()

	func _dist_linha(p: Vector2) -> float:
		var v := p - global_position
		var s := clampf(v.dot(dir), 0.0, comp)
		return (v - dir * s).length()
