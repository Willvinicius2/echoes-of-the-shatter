extends RefCounted
## Segundo leque de GELO do Arqueiro (docs/design/37_leque_skills_2.md): Lança de Gelo (feixe que atravessa a linha),
## Espinhos de Gelo (onda de espinhos que brotam do chão em linha) e Nevasca (tempestade de neve que acompanha o arqueiro).
## O frio usa as regras do ramo (Gelo.acumular_frio: lentidão por acúmulo, congela no 4º). Tudo vetorial.

const U = preload("res://scripts2d/efeitos_extra_util_2d.gd")
const Gelo = preload("res://scripts2d/efeitos_arqueiro_gelo_2d.gd")
const Vfx = preload("res://scripts2d/vfx_2d.gd")
const Px = preload("res://scripts2d/fx_pixel_2d.gd")
const COR := Color(0.6, 0.88, 1.0)
const EFEITOS := ["lanca_gelo", "espinhos_gelo", "nevasca"]

static func executar(efeito: String, jogador: Node2D, def: Dictionary, mira: Vector2) -> bool:
	var dir: Vector2 = mira.normalized() if mira != Vector2.ZERO else jogador.mira_atual()
	var dano: float = jogador.stats["arrow_damage"] * def.get("dano", 1.0)
	var cena: Node = jogador.get_parent()
	match efeito:
		"lanca_gelo":
			var l := Lanca.new()
			l.dir = dir
			l.comp = def.get("alcance", 640.0)
			l.larg = def.get("raio", 30.0)
			l.dano = dano
			l.frio = maxi(1, int(def.get("qtd", 2)))
			l.def = def
			cena.add_child(l)
			l.global_position = jogador.global_position
		"espinhos_gelo":
			var e := Espinhos.new()
			e.dir = dir
			e.n = maxi(2, int(def.get("qtd", 7)))
			e.comp = def.get("alcance", 520.0)
			e.raio = def.get("raio", 46.0)
			e.dano = dano
			e.def = def
			cena.add_child(e)
			e.global_position = jogador.global_position
		"nevasca":
			for c in jogador.get_children():
				if c.is_in_group("nevasca"):
					c.queue_free()
			var nv := Nevasca.new()
			nv.raio = def.get("raio", 220.0)
			nv.dur = maxf(def.get("duracao", 6.0), 1.0)
			nv.dano = dano
			nv.def = def
			jogador.add_child(nv)
		_:
			push_error("Efeito de gelo (leque 2) desconhecido: " + efeito)
			return false
	return true

## Lança de Gelo: uma lança de cristal cruza a linha à frente num instante, fere e gela (qtd acúmulos) tudo no caminho
## e se estilhaça em lascas que voam para os lados. Deixa uma trilha de geada que some em ~1 s.
class Lanca extends Node2D:
	const VOO := 0.18       # só ritmo visual
	const VIDA := 1.0
	var dir := Vector2.RIGHT
	var comp := 640.0
	var larg := 30.0
	var dano := 0.0
	var frio := 2
	var def: Dictionary = {}
	var _t := 0.0
	var _feito := false
	var _lanca: Node2D

	func _ready() -> void:
		z_index = 3
		Vfx.registrar_animado(self)
		_lanca = Px.criar("ice_lance", 1.8, false, "centro", dir.angle())
		_lanca.position = Vector2(0, -24)
		add_child(_lanca)

	func _physics_process(_delta: float) -> void:
		if _feito:
			return
		_feito = true
		var fim := global_position + dir * comp
		for e in U.no_raio(self, global_position, comp + larg):
			if U.dist_segmento(e.global_position, global_position, fim) <= larg:
				e.take_damage(dano, global_position)
				if is_instance_valid(e):
					Gelo.acumular_frio(e, frio, def)

	func _process(delta: float) -> void:
		_t += delta
		_lanca.position = Vector2(0, -24) + dir * comp * clampf(_t / VOO, 0.0, 1.0)
		_lanca.modulate.a = 1.0 - clampf((_t - VOO) / 0.25, 0.0, 1.0)
		queue_redraw()
		if _t >= VIDA:
			queue_free()

	func _draw() -> void:
		var org := Vector2(0, -24)
		var ang := dir.angle()
		var o := dir.orthogonal()
		var voo := clampf(_t / VOO, 0.0, 1.0)
		var alfa := 1.0 - clampf((_t - VOO) / (VIDA - VOO), 0.0, 1.0)
		for i in 12:   # geada no chão ao longo da linha, nasce atrás da ponta
			var u := (float(i) + 0.5) / 12.0
			if u <= voo:
				U.elipse(self, dir * comp * u + Vector2(0, 0), larg * 1.1, Color(0.85, 0.96, 1.0, 0.35 * alfa))
		if _t >= VOO:   # estilhaços saindo da linha para os dois lados
			var k := (_t - VOO) / (VIDA - VOO)
			for i in 14:
				var u := (float(i) + 0.5) / 14.0
				var lado := 1.0 if i % 2 == 0 else -1.0
				var base := org + dir * comp * u
				var desl := o * lado * (24.0 + 120.0 * k) * (0.6 + 0.4 * U.ruido(float(i), 2.0))
				U.cristal(self, base + desl, ang + lado * (0.6 + k * 2.0), 20.0 + 8.0 * U.ruido(float(i), 5.0), 5.0, alfa)

## Espinhos de Gelo: `n` grupos de espinhos brotam do chão em fila, um depois do outro (a onda anda), cada um fere e gela quem está em cima.
class Espinhos extends Node2D:
	const PASSO := 0.06     # só ritmo visual da onda
	const ALTURA := 78.0
	var dir := Vector2.RIGHT
	var n := 7
	var comp := 520.0
	var raio := 46.0
	var dano := 0.0
	var def: Dictionary = {}
	var _t := 0.0
	var _feito: Array = []

	func _ready() -> void:
		z_index = 2
		Vfx.registrar_animado(self)
		_feito.resize(n)
		_feito.fill(false)

	func _pos(i: int) -> Vector2:
		var u := float(i + 1) / float(n)
		return dir * comp * u + dir.orthogonal() * U.ruido(float(i), 7.0) * 14.0

	func _physics_process(delta: float) -> void:
		_t += delta
		for i in n:
			if not _feito[i] and _t >= float(i) * PASSO:
				_feito[i] = true
				if i % 2 == 0:   # um cacho de espinhos pintado a cada dois pontos da fila
					var cacho := Px.criar("ice_spikes", raio * 4.6 / maxf(Px.tamanho("ice_spikes").x, 1.0), false, "base")
					cacho.position = _pos(i)
					add_child(cacho)
					if cacho is AnimatedSprite2D:
						cacho.animation_finished.connect(cacho.queue_free)
				var p := global_position + _pos(i)
				for e in U.no_raio(self, p, raio):
					e.take_damage(dano, p)
					if is_instance_valid(e):
						Gelo.acumular_frio(e, 1, def)
						e.aplicar_status("atordoamento", 0.4)
		queue_redraw()
		if _t >= float(n) * PASSO + 1.0:
			queue_free()

	func _draw() -> void:
		for i in n:
			var idade := _t - float(i) * PASSO
			if idade < 0.0:
				continue
			var p := _pos(i)
			var sobe := 1.0 - pow(1.0 - minf(idade / 0.1, 1.0), 3.0)
			var alfa := 1.0 - clampf((idade - 0.6) / 0.4, 0.0, 1.0)
			U.elipse(self, p, raio * 0.8, Color(0.85, 0.96, 1.0, 0.4 * alfa))
			for j in 5:   # rachaduras no chão
				var a := TAU * float(j) / 5.0 + float(i)
				draw_line(p, p + Vector2.from_angle(a) * Vector2(raio, raio * 0.5) * 0.9, Color(0.4, 0.6, 0.9, 0.55 * alfa), 1.5)
			var h := ALTURA * sobe * (1.0 - 0.18 * float(i) / float(n))
			if h < 0.0:
				U.cristal(self, p, -PI / 2, h, 8.0, alfa)

## Nevasca: tempestade de neve gira em volta do arqueiro por `duracao` s; a cada pulso fere e soma 1 de frio em quem está dentro.
class Nevasca extends Node2D:
	const PULSO := 0.8      # só ritmo visual do pulso
	const FRIO_S := 2.5     # duração do frio aplicado por pulso
	var raio := 220.0
	var dur := 6.0
	var dano := 0.0
	var def: Dictionary = {}
	var _t := 0.0
	var _acc := 0.0
	var _onda := 1.0   # 0..1: anel do último pulso

	var _vortices: Array = []

	func _ready() -> void:
		add_to_group("nevasca")
		z_index = -1
		Vfx.registrar_animado(self)
		for i in 5:   # 1 funil no centro e 4 em volta, girando devagar
			var v := Px.criar("blizzard_vortex", 1.6 if i == 0 else 1.1, true, "base")
			add_child(v)
			_vortices.append(v)

	func _physics_process(delta: float) -> void:
		_t += delta
		_acc += delta
		_onda = minf(_onda + delta * 2.5, 1.0)
		if _acc >= PULSO:
			_acc = 0.0
			_onda = 0.0
			var d := def.duplicate()
			d["duracao"] = FRIO_S
			for e in U.no_raio(self, global_position, raio):
				e.take_damage(dano, global_position)
				if is_instance_valid(e):
					Gelo.acumular_frio(e, 1, d)
		var kk := clampf(minf(_t / 0.4, (dur - _t) / 0.5), 0.0, 1.0)
		for i in _vortices.size():
			var v: Node2D = _vortices[i]
			v.modulate.a = kk
			if i > 0:
				var a := _t * 0.9 + TAU * float(i - 1) / 4.0
				v.position = Vector2(cos(a), sin(a) * 0.6) * raio * 0.62 * kk
			v.z_index = int(v.position.y)
		queue_redraw()
		if _t >= dur:
			queue_free()

	func _draw() -> void:
		var k := clampf(minf(_t / 0.4, (dur - _t) / 0.5), 0.0, 1.0)
		U.elipse(self, Vector2.ZERO, raio * k, Color(0.88, 0.96, 1.0, 0.16))
		U.elipse_arco(self, Vector2.ZERO, raio * k, Color(COR, 0.45), 2.0)
		U.elipse_arco(self, Vector2.ZERO, raio * k * _onda, Color(1, 1, 1, 0.6 * (1.0 - _onda)), 3.0)
		for i in 3:   # rajadas de vento: arcos que giram
			draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.55))
			var a0 := _t * (2.2 + float(i) * 0.5) + float(i) * 2.1
			draw_arc(Vector2.ZERO, raio * k * (0.45 + 0.22 * float(i)), a0, a0 + 1.2, 12, Color(0.9, 0.98, 1.0, 0.5), 3.0)
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
		for i in 30:   # flocos: giram, se afastam do centro e caem
			var fase := fmod(_t * 0.35 + float(i) * 0.0371 * 7.0, 1.0)
			var a := _t * (1.0 + 0.4 * float(i % 3)) + float(i) * 0.71
			var r := raio * k * (0.2 + 0.8 * fmod(float(i) * 0.37 + _t * 0.12, 1.0))
			var p := Vector2(cos(a) * r, sin(a) * r * 0.55) + Vector2(0, -80.0 * (1.0 - fase))
			var s := 2.0 + float(i % 3)
			var c := Color(1, 1, 1, 0.9 * k)
			draw_line(p - Vector2(s, 0), p + Vector2(s, 0), c, 1.2)
			draw_line(p - Vector2(0, s), p + Vector2(0, s), c, 1.2)
			draw_line(p - Vector2(s, s) * 0.7, p + Vector2(s, s) * 0.7, c, 1.0)
