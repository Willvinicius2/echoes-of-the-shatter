extends RefCounted
## Ramo de VENENO do mago: três magias de controle de área, cada uma com um jeito próprio de espalhar a peste.
##   nuvem_peste = Nuvem Pestilenta: uma nuvem baixa sai do mago e ANDA devagar na direção da mira, envenenando o que cobre;
##   esporos     = Esporos Vorazes: marca os `qtd` inimigos mais perto; depois do pavio (ou se o hospedeiro morrer antes)
##                 cada esporo estoura em área e envenena os vizinhos;
##   poco_acido  = Poço Ácido: um jato de ácido estoura no ponto mirado e deixa um poço que fere e envenena quem pisa.
## Usa o status "veneno" do jogo (o Arauto da Peste e as reações valem). Números só do `def` (habilidades_mago.csv).

const Alvos = preload("res://scripts2d/alvos_2d.gd")
const U = preload("res://scripts2d/efeitos_extra_util_2d.gd")
const Vfx = preload("res://scripts2d/vfx_2d.gd")
const Px = preload("res://scripts2d/fx_pixel_2d.gd")
const FxMago = preload("res://scripts2d/fx_mago_2d.gd")
const VERDE := Color(0.44, 0.82, 0.17)
const TINTA := Color(0.75, 1.15, 0.5)   # puxa as folhas turquesa para o verde-ácido do veneno

static func executar(efeito: String, jogador: Node2D, def: Dictionary, dir: Vector2) -> bool:
	var cena: Node = jogador.get_parent()
	var poder: float = jogador.poder() if jogador.has_method("poder") else 1.0
	var dano: float = float(def.get("dano", 0.0)) * poder
	var dps: float = float(def.get("valor", 4.0)) * poder
	match efeito:
		"nuvem_peste":
			var n := Nuvem.new()
			n.dir = dir
			n.raio = float(def.get("raio", 100.0))
			n.dur = maxf(float(def.get("duracao", 5.0)), 0.5)
			n.vel = float(def.get("alcance", 420.0)) / n.dur
			n.dano = dano
			n.dps = dps
			cena.add_child(n)
			n.global_position = jogador.global_position + dir * 40.0
		"esporos":
			var alvos := U.mais_proximos(jogador, jogador.global_position, float(def.get("alcance", 520.0)), maxi(1, int(round(float(def.get("qtd", 3))))))
			if alvos.is_empty():
				return false
			for a in alvos:
				var e := Esporo.new()
				e.raio = float(def.get("raio", 100.0))
				e.pavio = maxf(float(def.get("duracao", 1.5)), 0.2)
				e.dano = dano
				e.dps = dps
				e.cena = cena
				a.add_child(e)
				var de: Vector2 = jogador.ponta_do_cajado(dir) if jogador.has_method("ponta_do_cajado") else jogador.global_position
				FxMago.impacto(cena, de, "veneno", 0.7)
		"poco_acido":
			var p := Poco.new()
			p.raio = float(def.get("raio", 130.0))
			p.dur = maxf(float(def.get("duracao", 6.0)), 0.5)
			p.dano = dano
			p.dps = dps
			cena.add_child(p)
			p.global_position = jogador.ponto_mira(float(def.get("alcance", 600.0))) if jogador.has_method("ponto_mira") else jogador.global_position + dir * 200.0
		_:
			push_error("Efeito de veneno do mago desconhecido: " + efeito)
			return false
	return true

## Nuvem Pestilenta: anda `vel` px/s na direção da mira; a cada pulso fere de leve e envenena quem está debaixo dela.
class Nuvem extends Node2D:
	const PULSO := 0.5   # só ritmo do dano em pulsos
	var dir := Vector2.RIGHT
	var raio := 100.0
	var dur := 5.0
	var vel := 80.0
	var dano := 0.0
	var dps := 4.0
	var _t := 0.0
	var _acc := PULSO
	var _folhas: Array = []

	func _ready() -> void:
		z_index = 2
		Vfx.registrar_animado(self)
		for i in 2:   # duas camadas da folha, a de trás maior e mais apagada: a nuvem ganha corpo
			var f := Px.criar("poison_cloud", raio * (2.3 - 0.5 * float(i)) / maxf(Px.tamanho("poison_cloud").x, 1.0), true, "centro")
			f.modulate = Color(TINTA, 0.6 + 0.35 * float(i))
			f.position = Vector2(0, -10.0 - 14.0 * float(i))
			if f is AnimatedSprite2D:
				f.frame = i * 20
			add_child(f)
			_folhas.append(f)

	func _physics_process(delta: float) -> void:
		_t += delta
		_acc += delta
		global_position += dir * vel * delta
		if _acc >= PULSO:
			_acc = 0.0
			for e in U.no_raio(self, global_position, raio):
				e.take_damage(dano, Vector2.ZERO)
				if is_instance_valid(e):
					e.aplicar_status("veneno", 3.0, dps)
		var k := clampf(minf(_t / 0.3, (dur - _t) / 0.5), 0.0, 1.0)
		for i in _folhas.size():
			_folhas[i].modulate.a = k * (0.6 + 0.35 * float(i))
		queue_redraw()
		if _t >= dur:
			queue_free()

	func _draw() -> void:
		var k := clampf(minf(_t / 0.3, (dur - _t) / 0.5), 0.0, 1.0)
		FxMago.elipse_pixel(self, Vector2.ZERO, raio * k, Color(0.12, 0.3, 0.06))
		U.elipse_arco(self, Vector2.ZERO, raio * k, Color(VERDE, 0.5), 2.0)

## Esporo preso a um inimigo: pulsa cada vez mais rápido e estoura no fim do pavio, ou na hora se o hospedeiro morrer.
class Esporo extends Node2D:
	var raio := 100.0
	var pavio := 1.5
	var dano := 0.0
	var dps := 4.0
	var cena: Node
	var _t := 0.0
	var _feito := false

	func _ready() -> void:
		z_index = 3
		position = Vector2(0, -48)
		var dono := get_parent()
		if dono.has_signal("died"):
			dono.died.connect(_ao_morrer_dono, CONNECT_ONE_SHOT)

	func _physics_process(delta: float) -> void:
		_t += delta
		queue_redraw()
		if _t >= pavio:
			_estourar()

	func _ao_morrer_dono(_e = null) -> void:
		_estourar()

	func _estourar() -> void:
		if _feito or not is_inside_tree():
			return
		_feito = true
		var pos: Vector2 = (get_parent() as Node2D).global_position
		if is_instance_valid(cena) and cena.is_inside_tree():
			var s := Px.tocar(cena, "spore_burst", pos + Vector2(0, raio * 0.3), raio * 2.0 / maxf(Px.tamanho("spore_burst").x, 1.0))
			s.modulate = TINTA
			FxMago.anel(cena, pos, "veneno", raio)
		for e in U.no_raio(self, pos, raio):
			e.take_damage(dano, pos)
			if is_instance_valid(e):
				e.aplicar_status("veneno", 3.0, dps)
		queue_free()

	func _draw() -> void:
		var k := clampf(_t / pavio, 0.0, 1.0)
		var pulso := 0.5 + 0.5 * sin(_t * (8.0 + 22.0 * k))
		var pal: Array = FxMago.paleta("veneno")
		var g := 2.5
		var lado := g * (3.0 + roundf(2.0 * k + pulso))   # bulbo quadrado na grade, que incha até estourar
		draw_rect(Rect2(Vector2(-lado, -lado) * 0.5 - Vector2(g, g) * 0.5, Vector2(lado + g, lado + g)), pal[0])
		draw_rect(Rect2(Vector2(-lado, -lado) * 0.5, Vector2(lado, lado)), pal[1].lerp(pal[3], pulso * k))
		draw_rect(Rect2(Vector2(-lado, -lado) * 0.5, Vector2(g, g)), pal[4])
		draw_arc(Vector2(0, 48), raio, 0.0, TAU, 32, Color(pal[2], 0.12 + 0.2 * k), 1.5)

## Poço Ácido: o jato estoura (dano na hora) e fica um poço borbulhando; quem pisa leva veneno renovado a cada pulso.
class Poco extends Node2D:
	const PULSO := 0.5   # só ritmo do dano em pulsos
	var raio := 130.0
	var dur := 6.0
	var dano := 0.0
	var dps := 5.0
	var _t := 0.0
	var _acc := 0.0

	func _ready() -> void:
		z_index = -1
		Vfx.registrar_decalque(self)
		Vfx.anel_entrada(get_parent(), global_position, raio, VERDE)
		var s := Px.criar("acid_splash", raio * 2.2 / maxf(Px.tamanho("acid_splash").x, 1.0), false, "base")
		s.position = Vector2(0, raio * 0.3)
		s.z_index = 5
		add_child(s)
		if s is AnimatedSprite2D:
			s.animation_finished.connect(s.queue_free)
		for e in U.no_raio(self, global_position, raio):
			e.take_damage(dano, global_position)
			if is_instance_valid(e):
				e.aplicar_status("veneno", 3.0, dps)

	func _physics_process(delta: float) -> void:
		_t += delta
		_acc += delta
		if _acc >= PULSO:
			_acc = 0.0
			for e in U.no_raio(self, global_position, raio):
				if is_instance_valid(e):
					e.aplicar_status("veneno", 2.0, dps)
		queue_redraw()
		if _t >= dur:
			queue_free()

	func _draw() -> void:
		var k := clampf(_t / 0.25, 0.0, 1.0) * Vfx.fade_zona(_t, dur)
		var pal: Array = FxMago.paleta("veneno")
		FxMago.elipse_pixel(self, Vector2.ZERO, raio * k, pal[0])
		FxMago.elipse_pixel(self, Vector2.ZERO, raio * 0.84 * k, pal[1])
		FxMago.elipse_pixel(self, Vector2(-raio * 0.15, -raio * 0.04), raio * 0.46 * k, pal[2])
		for i in 7:   # bolhas quadradas que nascem, crescem e estouram
			var u := fmod(_t * (0.7 + 0.13 * float(i)) + float(i) * 0.37, 1.0)
			var a := float(i) * 2.4
			var p := ((Vector2(cos(a), sin(a) * 0.5) * raio * (0.25 + 0.09 * float(i))) / 2.5).round() * 2.5
			var lado := 2.5 * (1.0 + roundf(u * 2.0))
			draw_rect(Rect2(p - Vector2(lado, lado) * 0.5 + Vector2(0, -6.0 * u), Vector2(lado, lado)), Color(pal[3] if u < 0.8 else pal[4], k * (1.0 - u * u)))
