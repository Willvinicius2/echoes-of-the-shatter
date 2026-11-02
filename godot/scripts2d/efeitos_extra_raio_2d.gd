extends RefCounted
## Segundo leque de RAIO do Arqueiro (docs/design/37_leque_skills_2.md): Trovoada (estrela radial), Tempestade de Raios
## (nuvem que derruba colunas do céu com aviso) e Orbes Tempestuosos (orbitam o arqueiro). Tudo desenhado por código (`_draw`),
## um nó por skill, sem partícula de GPU. Contrato igual ao de efeitos_arqueiro_2d.gd: executar(...) -> bool.

const U = preload("res://scripts2d/efeitos_extra_util_2d.gd")
const Raio = preload("res://scripts2d/efeitos_arqueiro_raio_2d.gd")
const Vfx = preload("res://scripts2d/vfx_2d.gd")
const COR := Color(0.45, 0.72, 1.0)
const EFEITOS := ["trovoada", "tempestade_raios", "orbes_tempestade"]

static func executar(efeito: String, jogador: Node2D, def: Dictionary, mira: Vector2) -> bool:
	var dir: Vector2 = mira.normalized() if mira != Vector2.ZERO else jogador.mira_atual()
	var dano: float = jogador.stats["arrow_damage"] * def.get("dano", 1.0)
	var cena: Node = jogador.get_parent()
	match efeito:
		"trovoada":
			var e := Estrela.new()
			e.raio = def.get("raio", 260.0)
			e.qtd = maxi(3, int(def.get("qtd", 8)))
			e.dano = dano
			e.dur_choque = def.get("duracao", 3.0)
			e.val = def.get("valor", 0.15)
			e.rot = dir.angle()
			cena.add_child(e)
			e.global_position = jogador.global_position
		"tempestade_raios":
			var alc: float = def.get("alcance", 600.0)
			var centro: Vector2 = U.ponto(jogador, dir, alc)
			var t := Tempestade.new()
			t.raio = def.get("raio", 280.0)
			t.golpes = maxi(1, int(def.get("qtd", 6)))
			t.dur = maxf(def.get("duracao", 3.0), 0.5)
			t.dano = dano
			t.val = def.get("valor", 0.15)
			cena.add_child(t)
			t.global_position = centro
		"orbes_tempestade":
			for c in jogador.get_children():
				if c.is_in_group("orbes_tempestade"):
					c.queue_free()
			var o := Orbes.new()
			o.n = maxi(1, int(def.get("qtd", 3)))
			o.raio_orb = def.get("raio", 90.0)
			o.dur = maxf(def.get("duracao", 6.0), 1.0)
			o.dano = dano
			o.val = def.get("valor", 0.15)
			jogador.add_child(o)
		_:
			push_error("Efeito de raio (leque 2) desconhecido: " + efeito)
			return false
	return true

## Trovoada: oito raios saem do arqueiro em estrela, em todas as direções; quem está no corredor de um raio (ou colado nele) leva dano e choque.
class Estrela extends Node2D:
	const VIDA := 0.5
	const CORREDOR := 34.0   # largura do corredor de cada raio (px)
	var raio := 260.0
	var qtd := 8
	var dano := 0.0
	var dur_choque := 3.0
	var val := 0.15
	var rot := 0.0
	var _t := 0.0
	var _bateu := false

	func _ready() -> void:
		z_index = 3
		Vfx.registrar_animado(self)

	func _physics_process(delta: float) -> void:
		_t += delta
		if not _bateu:
			_bateu = true
			_golpe()
		queue_redraw()
		if _t >= VIDA:
			queue_free()

	func _golpe() -> void:
		var o := global_position
		for n in U.no_raio(self, o, raio + CORREDOR):
			var p: Vector2 = n.global_position
			var acertou := p.distance_to(o) <= 60.0
			var i := 0
			while not acertou and i < qtd:
				var fim := o + Vector2.from_angle(rot + TAU * float(i) / float(qtd)) * raio
				acertou = U.dist_segmento(p, o, fim) <= CORREDOR
				i += 1
			if acertou:
				n.take_damage(dano, o)
				if is_instance_valid(n):
					Raio.aplicar_choque(n, dur_choque, val)

	func _draw() -> void:
		var cresce := clampf(_t / 0.08, 0.0, 1.0)
		var alfa := 1.0 - pow(clampf(_t / VIDA, 0.0, 1.0), 2.0)
		var org := Vector2(0, -26)
		for i in qtd:
			var d := Vector2.from_angle(rot + TAU * float(i) / float(qtd))
			var fim := org + d * raio * cresce
			U.raio_zz(self, org, fim, COR, 3.0, float(i) * 3.7 + floorf(_t * 30.0), alfa, 8)
			draw_circle(fim, 6.0 * alfa, Color(1, 1, 1, 0.8 * alfa))   # ponta do raio
		U.orbe(self, org, 14.0 * (1.0 - _t / VIDA * 0.5), COR, alfa)
		draw_arc(org, raio * cresce, 0.0, TAU, 48, Color(COR, 0.18 * alfa), 2.0)   # anel de alcance, discreto

## Tempestade de Raios: uma nuvem escura se forma sobre o ponto mirado e derruba `golpes` colunas de raio em inimigos da área,
## uma de cada vez, cada uma avisada por uma sombra no chão.
class Tempestade extends Node2D:
	const AVISO := 0.4      # só ritmo visual do aviso
	const AREA_GOLPE := 64.0
	var raio := 280.0
	var golpes := 6
	var dur := 3.0
	var dano := 0.0
	var val := 0.15
	var _t := 0.0
	var _prox := 0.25
	var _feitos := 0
	var _flash := 0.0
	var _rng := RandomNumberGenerator.new()

	func _ready() -> void:
		z_index = 6
		_rng.randomize()
		Vfx.registrar_animado(self)
		Vfx.anel_entrada(get_parent(), global_position, raio, COR)

	func _physics_process(delta: float) -> void:
		_t += delta
		_flash = maxf(_flash - delta * 4.0, 0.0)
		if _feitos < golpes and _t >= _prox:
			_feitos += 1
			_prox += (dur - 0.25) / float(golpes)
			_agendar()
		queue_redraw()
		if _t >= dur + AVISO + 0.3:
			queue_free()

	func _agendar() -> void:
		var alvos := U.no_raio(self, global_position, raio)
		var p: Vector2
		if alvos.is_empty():
			p = global_position + Vector2.from_angle(_rng.randf() * TAU) * raio * sqrt(_rng.randf())
		else:
			p = alvos[_rng.randi() % alvos.size()].global_position
		var cena := get_parent()
		Vfx.sombra_aviso(cena, p, AREA_GOLPE, COR, AVISO)
		get_tree().create_timer(AVISO).timeout.connect(func():
			if not is_instance_valid(self) or not is_inside_tree():
				return
			_cair(p))

	func _cair(p: Vector2) -> void:
		_flash = 1.0
		var col := Coluna.new()
		col.sem = p.x * 0.013 + p.y * 0.007
		get_parent().add_child(col)
		col.global_position = p
		for n in U.no_raio(self, p, AREA_GOLPE):
			n.take_damage(dano, p)
			if is_instance_valid(n):
				Raio.aplicar_choque(n, 3.0, val)

	func _draw() -> void:
		var f := clampf(_t / 0.35, 0.0, 1.0) * clampf((dur + AVISO - _t) / 0.4, 0.0, 1.0)
		var topo := Vector2(0, -300)
		for i in 7:   # nuvem: bolhas escuras sobrepostas, com o interior iluminado a cada raio
			var a := float(i) / 6.0 * TAU
			var p := topo + Vector2(cos(a) * raio * 0.38, sin(a) * raio * 0.1 + sin(_t * 1.3 + i) * 5.0)
			draw_circle(p, (raio * 0.2) * f, Color(0.14, 0.17, 0.3, 0.7 * f))
			draw_circle(p + Vector2(0, -6), (raio * 0.12) * f, Color(0.35, 0.45, 0.7, (0.35 + 0.5 * _flash) * f))
		draw_circle(topo, raio * 0.26 * f, Color(0.1, 0.12, 0.24, 0.8 * f))
		U.elipse_arco(self, Vector2.ZERO, raio, Color(COR, 0.22 * f), 2.0)   # limite da área sobre o chão

## Coluna de raio caindo do céu (curta). Nó solto no mundo, na posição do impacto.
class Coluna extends Node2D:
	const VIDA := 0.28
	var sem := 0.0
	var _t := 0.0
	func _ready() -> void:
		z_index = 5
	func _process(delta: float) -> void:
		_t += delta
		queue_redraw()
		if _t >= VIDA:
			queue_free()
	func _draw() -> void:
		var alfa := 1.0 - clampf(_t / VIDA, 0.0, 1.0)
		U.raio_zz(self, Vector2(sem * 0.0, -440), Vector2.ZERO, COR, 4.5, sem + floorf(_t * 40.0), alfa, 10)
		U.elipse(self, Vector2.ZERO, 54.0 * (0.5 + _t / VIDA), Color(0.7, 0.88, 1.0, 0.35 * alfa))
		draw_circle(Vector2(0, -4), 13.0 * alfa, Color(1, 1, 1, 0.9 * alfa))

## Orbes Tempestuosos: `n` esferas elétricas giram em volta do arqueiro, ligadas por arcos; ferem e chocam quem encosta.
class Orbes extends Node2D:
	const RAIO_TOQUE := 26.0
	var n := 3
	var raio_orb := 90.0
	var dur := 6.0
	var dano := 0.0
	var val := 0.15
	var _t := 0.0
	var _ultimo: Dictionary = {}

	func _ready() -> void:
		add_to_group("orbes_tempestade")
		z_index = 4
		Vfx.registrar_animado(self)

	func _pos(i: int) -> Vector2:
		return Vector2.from_angle(_t * 3.2 + TAU * float(i) / float(n)) * raio_orb

	func _physics_process(delta: float) -> void:
		_t += delta
		for i in n:
			var p := global_position + _pos(i)
			for e in U.no_raio(self, p, RAIO_TOQUE):
				if _t - float(_ultimo.get(e, -10.0)) >= 0.4:
					_ultimo[e] = _t
					e.take_damage(dano, p)
					if is_instance_valid(e):
						Raio.aplicar_choque(e, 2.0, val)
		queue_redraw()
		if _t >= dur:
			queue_free()

	func _draw() -> void:
		var k := clampf(minf(_t / 0.3, (dur - _t) / 0.4), 0.0, 1.0)
		var alt := Vector2(0, -22)
		U.elipse_arco(self, Vector2.ZERO, raio_orb, Color(COR, 0.14 * k), 2.0)   # trilho no chão
		var sem := floorf(_t * 18.0)
		for i in n:
			var a := _pos(i) + alt
			if n > 1:
				U.raio_zz(self, a, _pos((i + 1) % n) + alt, COR, 1.6, sem + i, 0.55 * k, 5)
		for i in n:
			U.orbe(self, _pos(i) + alt, 9.0 * k, COR, k)
