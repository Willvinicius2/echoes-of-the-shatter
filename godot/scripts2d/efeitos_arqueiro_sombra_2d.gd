extends RefCounted
## Ramo Sombra do Arqueiro com identidade própria (docs/design/39_leque_skills_fisico.md): Salto das Sombras (deixa um
## duplo de sombra que estoura), Bomba de Fumaça (nuvem que esconde o arqueiro e deixa os inimigos lentos) e
## Adrenalina (onda de choque ao ativar, vultos e vento enquanto dura). Tudo desenhado por código, paleta violeta.

const U = preload("res://scripts2d/efeitos_extra_util_2d.gd")
const Alvos = preload("res://scripts2d/alvos_2d.gd")
const Vfx = preload("res://scripts2d/vfx_2d.gd")
const Feel = preload("res://scripts2d/feel_2d.gd")
const F = preload("res://scripts2d/pixel_fisico_2d.gd")
const EFEITOS := ["salto", "fumaca", "furia"]
const VIOLETA := Color(0.62, 0.4, 0.95)
const BREU := Color(0.13, 0.08, 0.2)
const AMBAR := Color(1.0, 0.72, 0.3)

static func executar(efeito: String, jogador: Node2D, def: Dictionary, mira: Vector2) -> bool:
	var dir: Vector2 = mira.normalized() if mira != Vector2.ZERO else jogador.mira_atual()
	var base: float = jogador.stats["arrow_damage"]
	var cena: Node = jogador.get_parent()
	match efeito:
		"salto":
			var dano: float = def.get("dano", 1.0)
			if float(def.get("raio", 0.0)) > 0.0:
				var d := Duplo.new()
				d.raio = def["raio"]
				d.dano = base * dano * float(def.get("valor", 1.0))
				d.copiar(jogador)
				cena.add_child(d)
				d.global_position = jogador.global_position
			jogador.saltar(-dir, def.get("alcance", 280.0), def.get("duracao", 0.2))
			jogador.get_tree().create_timer(def.get("duracao", 0.2)).timeout.connect(func():
				if is_instance_valid(jogador) and not jogador.esta_morto():
					jogador.lancar_flecha(dir, dano, 0, 1.0, def).cor_fx = VIOLETA)
		"fumaca":
			var raio: float = def.get("raio", 150.0)
			var dur: float = def.get("duracao", 4.0)
			var valor: float = def.get("valor", 0.0)
			var boca: Dictionary = jogador.boca_do_arco(dir)
			Vfx.arco(cena, boca["chao"], boca["altura"], U.ponto(jogador, dir, def.get("alcance", 350.0)), 150.0, Fumaca.VOO, Granada.new(), VIOLETA, raio,
				func(ponto: Vector2):
					if not is_instance_valid(cena) or not cena.is_inside_tree():
						return
					var f := Fumaca.new()
					f.raio = raio
					f.dur = maxf(dur, 0.5)
					f.valor = valor
					f.jogador = jogador
					cena.add_child(f)
					f.global_position = ponto)
		"furia":
			var v: float = def.get("valor", 0.35)
			jogador.dar_buff(def.get("duracao", 5.0), 1.0 + v * 0.5, 1.0 / (1.0 - minf(v, 0.8)))
			for c in jogador.get_children():
				if c is Impeto:
					c.queue_free()
			var i := Impeto.new()
			i.dur = def.get("duracao", 5.0)
			i.raio = def.get("raio", 0.0)
			jogador.add_child(i)
		_:
			push_error("Efeito de sombra desconhecido: " + efeito)
			return false
	return true

## Duplo de sombra: a silhueta do arqueiro fica onde ele estava. Estoura quando um inimigo encosta ou ao fim da
## espera, ferindo todos no raio. Quem perseguia o arqueiro corre para dentro da explosão.
class Duplo extends Node2D:
	const ESPERA := 0.9
	const ESTOURO := 0.45
	var raio := 90.0
	var dano := 0.0
	var _t := 0.0
	var _estourou := -1.0
	var _spr: Sprite2D

	## Copia o quadro que o arqueiro mostra agora (mesma técnica do rastro da esquiva).
	func copiar(jogador: Node2D) -> void:
		var s = jogador.get("sprite")
		if s == null or s.sprite_frames == null:
			return
		var t: Texture2D = s.sprite_frames.get_frame_texture(s.animation, s.frame)
		if t == null:
			return
		_spr = Sprite2D.new()
		_spr.texture = t
		_spr.centered = s.centered
		_spr.offset = s.offset
		_spr.flip_h = s.flip_h
		_spr.scale = s.global_scale
		_spr.position = s.position
		_spr.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		_spr.modulate = Color(0.3, 0.16, 0.5, 0.9)
		add_child(_spr)

	func _ready() -> void:
		Vfx.registrar_animado(self)

	func _physics_process(delta: float) -> void:
		_t += delta
		queue_redraw()
		if _estourou >= 0.0:
			if _t - _estourou >= ESTOURO:
				queue_free()
			return
		if _spr != null:
			_spr.modulate.a = 0.75 + 0.15 * sin(_t * 18.0)
		if _t < ESPERA and (_t < 0.15 or Alvos.no_raio(get_tree(), global_position, raio * 0.5).is_empty()):
			return
		_estourou = _t
		if _spr != null:
			_spr.visible = false
		for e in Alvos.no_raio(get_tree(), global_position, raio, "take_damage"):
			e.take_damage(dano, global_position)
		Feel.shake(self, Feel.cfg()["shake_kill_amp"], Feel.cfg()["shake_kill_time"])

	func _draw() -> void:
		if _estourou < 0.0:
			U.elipse(self, Vector2.ZERO, 20.0, Color(BREU, 0.55))
			for i in 5:   # fiapos de sombra subindo do duplo
				var k := fmod(_t * 1.3 + float(i) * 0.21, 1.0)
				var p := Vector2(U.ruido(float(i), 1.0) * 18.0 + sin(_t * 5.0 + float(i)) * 4.0, -10.0 - 80.0 * k)
				draw_rect(Rect2(p, Vector2(7.5, 12.5)), Color(VIOLETA, 0.8 * (1.0 - k)))
			return
		var k := clampf((_t - _estourou) / ESTOURO, 0.0, 1.0)
		var sai := 1.0 - pow(1.0 - k, 3.0)
		U.elipse(self, Vector2.ZERO, raio * sai, Color(BREU, 0.5 * (1.0 - k)))
		U.elipse_arco(self, Vector2.ZERO, raio * sai, Color(VIOLETA, 1.0 - k), 9.0 * (1.0 - k) + 2.0)
		for i in 10:   # penas de corvo voando para fora
			var a := TAU * float(i) / 10.0 + 0.3
			var p := Vector2.from_angle(a) * Vector2(1.0, 0.6) * raio * sai * (0.7 + 0.3 * U.ruido(float(i), 2.0)) + Vector2(0, -34.0 + 30.0 * k)
			var f := Vector2.from_angle(a + k * 3.0) * 15.0
			draw_line(p - f, p + f, Color(BREU, 1.0 - k), 9.0)
			draw_line(p - f * 0.6, p + f * 0.6, Color(VIOLETA, 0.9 * (1.0 - k)), 4.0)
		draw_circle(Vector2(0, -34), 26.0 * (1.0 - k), Color(1, 1, 1, 0.8 * (1.0 - k)))

## Corpo da bomba de fumaça em voo (bolinha escura com pavio).
class Granada extends Node2D:
	func _draw() -> void:
		draw_circle(Vector2.ZERO, 13.0, Color(0.1, 0.08, 0.1))
		draw_circle(Vector2.ZERO, 9.5, Color(0.36, 0.3, 0.46))
		draw_rect(Rect2(Vector2(-2.5, -19.0), Vector2(7.5, 7.5)), Color(1.0, 0.8, 0.3))

## Bomba de Fumaça: nuvem espessa que rola no chão por `dur` s. Inimigos dentro ficam lentos (`valor`) e, enquanto o
## arqueiro estiver dentro dela, ninguém o acerta.
class Fumaca extends Node2D:
	const VOO := 0.4
	const BOLHAS := 30
	var raio := 150.0
	var dur := 4.0
	var valor := 0.5
	var jogador: Node2D
	var _t := 0.0

	func _ready() -> void:
		z_index = 3
		Vfx.registrar_animado(self)
		Feel.shake(self, Feel.cfg()["shake_hit_amp"], Feel.cfg()["shake_hit_time"])

	func _physics_process(delta: float) -> void:
		_t += delta
		if valor > 0.0:
			for e in Alvos.no_raio(get_tree(), global_position, raio, "aplicar_status"):
				e.aplicar_status("lentidao", 0.3, valor)
		if is_instance_valid(jogador) and jogador.global_position.distance_to(global_position) <= raio and "invencivel" in jogador:
			jogador.invencivel = maxf(jogador.invencivel, 0.15)
		queue_redraw()
		if _t >= dur:
			queue_free()

	func _draw() -> void:
		var abre := 1.0 - pow(1.0 - clampf(_t / 0.35, 0.0, 1.0), 3.0)
		var some := Vfx.fade_zona(_t, dur)
		U.elipse(self, Vector2.ZERO, raio * abre, Color(BREU, 0.3 * some))
		var tons := [Color(0.2, 0.17, 0.26), Color(0.38, 0.35, 0.46), Color(0.6, 0.57, 0.68)]
		for cam in 3:   # três tons: o escuro embaixo, o claro no topo de cada bolha
			for i in BOLHAS:
				var a := TAU * float(i) / float(BOLHAS) * 2.4 + _t * (0.25 + 0.1 * float(i % 3))
				var dist := raio * abre * sqrt(fmod(float(i) * 0.618, 1.0)) * 0.92
				var sobe := 24.0 + 16.0 * sin(_t * 1.4 + float(i))
				var p := Vector2(cos(a) * dist, sin(a) * dist * 0.7 - sobe)
				var r := (38.0 + 24.0 * fmod(float(i) * 0.37, 1.0)) * abre * (0.75 + 0.25 * some)
				draw_circle(p + Vector2(-float(cam) * 5.0, -float(cam) * 9.0), r * (1.0 - 0.26 * float(cam)), Color(tons[cam], (0.92 - 0.12 * float(cam)) * some))
		if _t < 0.25:   # clarão do estouro
			draw_circle(Vector2(0, -10), 40.0 * (1.0 - _t / 0.25), Color(1, 1, 1, 0.8 * (1.0 - _t / 0.25)))

## Adrenalina: ao ativar, uma onda de choque empurra quem está em volta (`raio`); enquanto dura, vento âmbar gira nos
## pés e o arqueiro deixa vultos para trás quando corre.
class Impeto extends Node2D:
	const ONDA := 0.35
	const VULTO_CADA := 0.07
	var dur := 5.0
	var raio := 0.0
	var _t := 0.0
	var _vulto := 0.0
	var _ultimo := Vector2.ZERO

	func _ready() -> void:
		show_behind_parent = true
		Vfx.registrar_animado(self)
		_ultimo = global_position
		if raio <= 0.0:
			return
		var c := Feel.cfg()
		for e in Alvos.no_raio(get_tree(), global_position, raio):
			F.empurrar(e, (e.global_position - global_position).normalized() * c["enemy_knockback"] * 2.5)
		Feel.shake(self, c["shake_kill_amp"], c["shake_kill_time"])

	func _physics_process(delta: float) -> void:
		_t += delta
		_vulto -= delta
		var dono := get_parent()
		if _vulto <= 0.0 and global_position.distance_to(_ultimo) > 6.0:
			_vulto = VULTO_CADA
			_deixar_vulto(dono)
		_ultimo = global_position
		queue_redraw()
		if _t >= dur or (dono.has_method("esta_morto") and dono.esta_morto()):
			queue_free()

	func _deixar_vulto(dono: Node) -> void:
		var s = dono.get("sprite")
		if s == null or s.sprite_frames == null:
			return
		var t: Texture2D = s.sprite_frames.get_frame_texture(s.animation, s.frame)
		if t == null:
			return
		var g := Sprite2D.new()
		g.texture = t
		g.centered = s.centered
		g.offset = s.offset
		g.flip_h = s.flip_h
		g.scale = s.global_scale
		g.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		g.modulate = Color(1.0, 0.6, 0.2, 0.5)
		dono.get_parent().add_child(g)
		g.global_position = s.global_position - Vector2(0, 0.5)
		var tw := g.create_tween()
		tw.tween_property(g, "modulate:a", 0.0, 0.25)
		tw.tween_callback(g.queue_free)

	func _draw() -> void:
		var k := clampf(minf(_t / 0.2, (dur - _t) / 0.4), 0.0, 1.0)
		if _t < ONDA and raio > 0.0:
			var o := _t / ONDA
			U.elipse_arco(self, Vector2.ZERO, raio * o, Color(1, 1, 1, 0.9 * (1.0 - o)), 9.0)
			U.elipse_arco(self, Vector2.ZERO, raio * o * 0.8, Color(AMBAR, 0.7 * (1.0 - o)), 3.0)
		U.elipse(self, Vector2(0, -4), 62.0, Color(AMBAR, 0.22 * k))
		draw_set_transform(Vector2(0, -4), 0.0, Vector2(1.0, 0.5))
		for i in 4:   # vento girando nos pés
			var a0 := _t * (7.0 + float(i)) + float(i) * 1.7
			draw_arc(Vector2.ZERO, 44.0 + 14.0 * float(i), a0, a0 + 1.6, 8, Color(AMBAR if i % 2 == 0 else Color(1, 0.95, 0.75), 0.9 * k), 8.0)
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
		for i in 6:   # faíscas subindo
			var f := fmod(_t * 1.8 + float(i) * 0.17, 1.0)
			var p := Vector2(U.ruido(float(i), 4.0) * 34.0, -8.0 - 110.0 * f)
			draw_rect(Rect2(p, Vector2(5.0, 10.0)), Color(AMBAR, 0.9 * (1.0 - f) * k))
