extends RefCounted
## Segundo leque de VENENO do Arqueiro (docs/design/37_leque_skills_2.md): Contágio (o veneno pula de inimigo em inimigo),
## Minas Tóxicas (armadilhas que estouram em nuvem) e Gêiser Ácido (jatos de ácido do chão sob os inimigos). Tudo vetorial.

const U = preload("res://scripts2d/efeitos_extra_util_2d.gd")
const Vfx = preload("res://scripts2d/vfx_2d.gd")
const Px = preload("res://scripts2d/fx_pixel_2d.gd")
const VERDE := Color(0.45, 0.9, 0.25)
const EFEITOS := ["contagio", "minas_toxicas", "geiser_acido"]
const DUR_VENENO := 3.0   # tempo de cada aplicação de veneno das nuvens e jatos (renovado a cada pulso)

static func executar(efeito: String, jogador: Node2D, def: Dictionary, mira: Vector2) -> bool:
	var dir: Vector2 = mira.normalized() if mira != Vector2.ZERO else jogador.mira_atual()
	var dano: float = jogador.stats["arrow_damage"] * def.get("dano", 1.0)
	var cena: Node = jogador.get_parent()
	var alc: float = def.get("alcance", 600.0)
	match efeito:
		"contagio":
			var f = jogador.lancar_flecha(dir, def.get("dano", 1.0), 0, 1.0, def)
			f.cor_fx = VERDE
			f.body_entered.connect(func(corpo: Node):
				if not is_instance_valid(corpo) or not corpo.has_method("aplicar_status") or not corpo.is_inside_tree():
					return
				var foco := Foco.new()
				foco.alvo = corpo
				foco.raio = def.get("raio", 150.0)
				foco.dur = def.get("duracao", 4.0)
				foco.dps = def.get("valor", 5.0)
				cena.add_child(foco)
				foco.global_position = corpo.global_position, CONNECT_ONE_SHOT)
		"minas_toxicas":
			var centro: Vector2 = U.ponto(jogador, dir, alc)
			var n := maxi(1, int(def.get("qtd", 3)))
			for i in n:
				var m := Mina.new()
				m.raio = def.get("raio", 110.0)
				m.vida = def.get("duracao", 8.0)
				m.dano = dano
				m.dps = def.get("valor", 5.0)
				cena.add_child(m)
				var a := dir.angle() + TAU * float(i) / float(n) + 0.5
				m.global_position = centro + (Vector2.ZERO if n == 1 else Vector2.from_angle(a) * 64.0)
		"geiser_acido":
			var centro: Vector2 = U.ponto(jogador, dir, alc)
			var alvos := U.mais_proximos(jogador, centro, def.get("raio", 260.0), maxi(1, int(def.get("qtd", 4))))
			if alvos.is_empty():
				return false   # sem inimigo na área: não gasta a recarga
			var dps: float = def.get("valor", 5.0)
			for i in alvos.size():
				var p: Vector2 = alvos[i].global_position
				var espera := float(i) * 0.15 + Geiser.AVISO
				Vfx.sombra_aviso(cena, p, Geiser.AREA, VERDE, espera)
				jogador.get_tree().create_timer(espera).timeout.connect(func():
					if not is_instance_valid(cena) or not cena.is_inside_tree():
						return
					var g := Geiser.new()
					g.dano = dano
					g.dps = dps
					cena.add_child(g)
					g.global_position = p)
		_:
			push_error("Efeito de veneno (leque 2) desconhecido: " + efeito)
			return false
	return true

## Foco do Contágio: segue o primeiro inimigo atingido e, a cada meio segundo, passa o veneno (dps) a todos num raio.
## Se o foco morre, o contágio salta para o inimigo vivo mais perto (até 1,5x o raio) e continua até acabar o tempo.
class Foco extends Node2D:
	var alvo: Node2D
	var raio := 150.0
	var dur := 4.0
	var dps := 5.0
	var _t := 0.0
	var _acc := 0.4
	var _ligados: Array = []   # posições globais dos contaminados no último pulso

	var _prox_esporo := 0.0

	func _ready() -> void:
		z_index = 2
		Vfx.registrar_animado(self)

	func _physics_process(delta: float) -> void:
		_t += delta
		_acc += delta
		if _t >= _prox_esporo:   # cogumelo de esporos estoura sobre o foco a cada 1,3 s
			_prox_esporo = _t + 1.3
			Px.tocar(get_parent(), "spore_burst", global_position + Vector2(0, 4), 0.9, "base", 0.0, 3)
		var vivo: bool = is_instance_valid(alvo) and alvo.is_inside_tree() and not (alvo.has_method("esta_morto") and alvo.esta_morto())
		if vivo:
			global_position = alvo.global_position
		elif _acc >= 0.1:
			var prox := U.mais_proximos(self, global_position, raio * 1.5, 1)
			if prox.is_empty():
				queue_free()
				return
			alvo = prox[0]
		if _acc >= 0.5 and is_instance_valid(alvo):
			_acc = 0.0
			_ligados.clear()
			alvo.aplicar_status("veneno", DUR_VENENO, dps)
			for e in U.no_raio(self, global_position, raio):
				if e != alvo:
					e.aplicar_status("veneno", DUR_VENENO, dps)
					_ligados.append(e.global_position)
		queue_redraw()
		if _t >= dur:
			queue_free()

	func _draw() -> void:
		var k := clampf(minf(_t / 0.25, (dur - _t) / 0.4), 0.0, 1.0)
		U.elipse(self, Vector2.ZERO, raio * k, Color(0.3, 0.6, 0.15, 0.13))
		U.elipse_arco(self, Vector2.ZERO, raio * k, Color(VERDE, 0.4), 2.0)
		for p in _ligados:   # filetes de esporos do foco até cada contaminado (curva com barriga para cima)
			var b: Vector2 = to_local(p) + Vector2(0, -14)
			var a := Vector2(0, -22)
			var meio := (a + b) * 0.5 + Vector2(0, -22)
			var pts := PackedVector2Array()
			for i in 9:
				var u := float(i) / 8.0
				pts.append(a.lerp(meio, u).lerp(meio.lerp(b, u), u))
			draw_polyline(pts, Color(VERDE, 0.28 * k), 7.0)
			draw_polyline(pts, Color(0.75, 1.0, 0.45, 0.8 * k), 2.0)
		for i in 10:   # esporos que giram e sobem em volta do foco
			var a := _t * 1.6 + float(i) * 0.63
			var h := fmod(_t * 0.6 + float(i) * 0.37, 1.0)
			var p := Vector2(cos(a), sin(a) * 0.55) * raio * 0.7 * k + Vector2(0, -h * 46.0)
			draw_circle(p, 3.2 * (1.0 - h) + 1.2, Color(0.75, 1.0, 0.4, 0.8 * (1.0 - h) * k))
		U.orbe(self, Vector2(0, -34), 8.0 * k, VERDE, k)   # marca de foco sobre a cabeça

## Mina Tóxica: arma em 0,6 s e estoura em nuvem quando um inimigo chega perto (ou quando acaba a vida).
class Mina extends Node2D:
	const ARMA := 0.6          # só ritmo visual da armação
	const GATILHO := 56.0      # distância que dispara (px)
	var raio := 110.0
	var vida := 8.0
	var dano := 0.0
	var dps := 5.0
	var _t := 0.0

	func _ready() -> void:
		z_index = -1
		Vfx.registrar_decalque(self)

	func _physics_process(delta: float) -> void:
		_t += delta
		if _t >= ARMA and not U.no_raio(self, global_position, GATILHO).is_empty():
			_estourar()
		elif _t >= vida:
			_estourar()
		queue_redraw()

	func _estourar() -> void:
		var cena := get_parent()
		var nuvem := Nuvem.new()
		nuvem.raio = raio
		cena.add_child(nuvem)
		nuvem.global_position = global_position
		for e in U.no_raio(self, global_position, raio):
			e.take_damage(dano, global_position)
			if is_instance_valid(e):
				e.aplicar_status("veneno", DUR_VENENO, dps)
		queue_free()

	func _draw() -> void:
		var surgir := clampf(_t / 0.15, 0.0, 1.0)
		var armada := _t >= ARMA
		var m := 2.0   # mina grande o bastante para ler a 640x360
		U.elipse(self, Vector2.ZERO, 22.0 * m * surgir, Color(0.1, 0.25, 0.05, 0.6))
		U.elipse_arco(self, Vector2.ZERO, 22.0 * m * surgir, Color(0.7, 1.0, 0.3, 0.7), 2.0)   # poça verde clara sob a mina
		for i in 8:   # espinhos em volta do casco
			var a := TAU * float(i) / 8.0
			var d := Vector2.from_angle(a)
			draw_colored_polygon(PackedVector2Array([d.orthogonal() * 4.0 * m + d * 8.0 * m, d * 17.0 * m * surgir + Vector2(0, -6.0 * m), -d.orthogonal() * 4.0 * m + d * 8.0 * m]), Color(0.45, 0.75, 0.2, 0.95))
		draw_circle(Vector2(0, -4.0 * m), 10.0 * m * surgir, Color(0.2, 0.42, 0.12, 1.0))
		draw_circle(Vector2(-2.0 * m, -6.0 * m), 5.0 * m * surgir, Color(0.5, 0.8, 0.3, 1.0))
		var pisca := 0.5 + 0.5 * sin(_t * (14.0 if armada else 4.0))
		draw_circle(Vector2(0, -5.0 * m), 4.0 * m * surgir, Color(0.85, 1.0, 0.4, (0.55 + 0.45 * pisca) if armada else 0.3))
		if armada:
			U.elipse_arco(self, Vector2.ZERO, GATILHO, Color(VERDE, 0.1 + 0.08 * pisca), 1.5)

## Nuvem do estouro da mina: bolhas verdes que sobem e abrem, ~0,9 s.
class Nuvem extends Node2D:
	const VIDA := 0.9
	var raio := 110.0
	var _t := 0.0
	func _ready() -> void:
		z_index = 3
		var s := Px.criar("spore_burst", raio * 1.6 / maxf(Px.tamanho("spore_burst").x, 1.0), false, "base")
		add_child(s)
		if s is AnimatedSprite2D:
			s.animation_finished.connect(queue_free)
		else:
			queue_free()
	func _process(delta: float) -> void:
		_t += delta
		queue_redraw()
	func _draw() -> void:
		var f := clampf(_t / 0.5, 0.0, 1.0)   # área do estouro: disco verde que abre até o raio e some
		U.elipse(self, Vector2.ZERO, raio * (0.3 + 0.7 * f), Color(0.4, 0.8, 0.15, 0.35 * (1.0 - f)))
		U.elipse_arco(self, Vector2.ZERO, raio * (0.3 + 0.7 * f), Color(0.8, 1.0, 0.4, 0.8 * (1.0 - f)), 3.0)

## Jato de ácido do chão: fere e envenena quem está em cima, com um empurrão curto (atordoamento).
class Geiser extends Node2D:
	const AVISO := 0.5   # só ritmo visual do aviso
	const AREA := 62.0
	const VIDA := 0.75
	var dano := 0.0
	var dps := 5.0
	var _t := 0.0
	var _bateu := false

	func _ready() -> void:
		z_index = 3
		Vfx.registrar_animado(self)
		add_child(Px.criar("acid_splash", AREA * 2.4 / maxf(Px.tamanho("acid_splash").x, 1.0), false, "base"))

	func _physics_process(delta: float) -> void:
		_t += delta
		if not _bateu:
			_bateu = true
			for e in U.no_raio(self, global_position, AREA):
				e.take_damage(dano, global_position)
				if is_instance_valid(e):
					e.aplicar_status("veneno", DUR_VENENO, dps)
					e.aplicar_status("atordoamento", 0.4)
		queue_redraw()
		if _t >= VIDA:
			queue_free()

	func _draw() -> void:
		var f := clampf(_t / VIDA, 0.0, 1.0)
		var h := 210.0 * (1.0 - pow(1.0 - minf(_t / 0.14, 1.0), 2.0))
		var alfa := 1.0 - maxf((f - 0.5) * 2.0, 0.0)
		U.elipse(self, Vector2.ZERO, AREA * 0.9, Color(0.2, 0.45, 0.1, 0.5 * alfa))
		var l := 30.0 * (1.0 - f * 0.4)
		var oco := sin(_t * 30.0) * 3.0
		draw_colored_polygon(PackedVector2Array([Vector2(-l, 0), Vector2(-l * 0.6 + oco, -h * 0.5), Vector2(-l * 0.4, -h), Vector2(l * 0.4, -h),
			Vector2(l * 0.6 - oco, -h * 0.5), Vector2(l, 0)]), Color(0.3, 0.65, 0.12, 0.5 * alfa))
		draw_colored_polygon(PackedVector2Array([Vector2(-l * 0.5, 0), Vector2(-l * 0.25, -h * 0.55), Vector2(0, -h * 0.97), Vector2(l * 0.25, -h * 0.55), Vector2(l * 0.5, 0)]),
			Color(0.7, 1.0, 0.35, 0.8 * alfa))
		for i in 9:   # gotas que sobem e caem em parábola
			var vx := U.ruido(float(i), 1.0) * 70.0
			var vy := -(190.0 + float(i) * 14.0)
			var p := Vector2(vx * _t, vy * _t + 560.0 * _t * _t) + Vector2(0, -h * 0.75)
			draw_circle(p, 4.5 - float(i % 3), Color(0.7, 1.0, 0.35, 0.9 * alfa))
