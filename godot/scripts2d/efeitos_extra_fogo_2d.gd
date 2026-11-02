extends RefCounted
## Segundo leque de FOGO do Arqueiro (docs/design/37_leque_skills_2.md): Sopro Flamejante (cone que segue a mira),
## Anel de Fogo (círculo de chamas parado no chão) e Bomba-Rastilho (flecha que vira bomba e explode em cadeia).
## A queimadura usa fogo_util_2d.gd (status "queimadura"). Tudo vetorial.

const U = preload("res://scripts2d/efeitos_extra_util_2d.gd")
const Fu = preload("res://scripts2d/fogo_util_2d.gd")
const Vfx = preload("res://scripts2d/vfx_2d.gd")
const Px = preload("res://scripts2d/fx_pixel_2d.gd")
const EFEITOS := ["sopro_chamas", "anel_fogo", "bomba_rastilho"]
const MAX_CADEIA := 14   # teto de bombas vivas numa mesma reação em cadeia (orçamento de FPS)

static func executar(efeito: String, jogador: Node2D, def: Dictionary, mira: Vector2) -> bool:
	var dir: Vector2 = mira.normalized() if mira != Vector2.ZERO else jogador.mira_atual()
	var dano: float = jogador.stats["arrow_damage"] * def.get("dano", 1.0)
	var cena: Node = jogador.get_parent()
	match efeito:
		"sopro_chamas":
			var s := Sopro.new()
			s.jogador = jogador
			s.dir = dir
			s.meio_ang = deg_to_rad(def.get("angulo", 70.0)) * 0.5
			s.comp = def.get("alcance", 260.0)
			s.dur = maxf(def.get("duracao", 1.2), 0.3)
			s.dano = dano
			s.queima_s = def.get("qtd", 3.0)
			s.dps = def.get("valor", 4.0)
			cena.add_child(s)
			s.global_position = jogador.global_position
		"anel_fogo":
			var a := Anel.new()
			a.raio = def.get("raio", 150.0)
			a.banda = def.get("alcance", 52.0)
			a.dur = maxf(def.get("duracao", 5.0), 1.0)
			a.dano = dano
			a.queima_s = def.get("qtd", 3.0)
			a.dps = def.get("valor", 4.0)
			cena.add_child(a)
			a.global_position = jogador.global_position
		"bomba_rastilho":
			var f = jogador.lancar_flecha(dir, def.get("dano", 1.0), 0, 1.0, def)
			f.cor_fx = Color(1.0, 0.5, 0.15)
			f.body_entered.connect(func(corpo: Node):
				if is_instance_valid(corpo) and corpo is Node2D and corpo.has_method("take_damage") and corpo.is_inside_tree():
					var ctx := {"vistos": {}, "vivas": 0}
					Bomba.armar(cena, corpo, def, dano, 0, def.get("duracao", 1.2), ctx), CONNECT_ONE_SHOT)
		_:
			push_error("Efeito de fogo (leque 2) desconhecido: " + efeito)
			return false
	return true

## Sopro Flamejante: cone de chamas na frente do arqueiro, que acompanha a mira por `duracao` s e queima quem está dentro.
class Sopro extends Node2D:
	const PULSO := 0.15     # só ritmo visual do dano em pulsos
	var jogador: Node2D
	var dir := Vector2.RIGHT
	var meio_ang := 0.6
	var comp := 260.0
	var dur := 1.2
	var dano := 0.0
	var queima_s := 3.0
	var dps := 4.0
	var _t := 0.0
	var _acc := 0.0

	var _chama: Node2D

	func _ready() -> void:
		z_index = 3
		Vfx.registrar_animado(self)
		_chama = Node2D.new()   # três chamas em leque (centro e ±16°) formam um cone largo
		add_child(_chama)
		for a in [-0.28, 0.0, 0.28]:
			var f := Px.criar("fire_breath", comp / maxf(Px.tamanho("fire_breath").x, 1.0), true, "ponta", a)
			if a != 0.0:
				f.modulate.a = 0.8
			_chama.add_child(f)

	func _physics_process(delta: float) -> void:
		if not is_instance_valid(jogador) or not jogador.is_inside_tree():
			queue_free()
			return
		_t += delta
		_acc += delta
		global_position = jogador.global_position
		var quer: Vector2 = jogador.mira_atual()
		if quer != Vector2.ZERO:
			dir = dir.slerp(quer.normalized(), minf(1.0, 8.0 * delta)).normalized()
		if _acc >= PULSO:
			_acc = 0.0
			for e in U.no_raio(self, global_position, comp):
				var v: Vector2 = e.global_position - global_position
				if v.length() < 24.0 or absf(dir.angle_to(v)) <= meio_ang:
					e.take_damage(dano, global_position)
					if is_instance_valid(e):
						Fu.queimar(e, queima_s, dps)
		_chama.position = dir * 26.0 + Vector2(0, -26)
		_chama.rotation = dir.angle()
		_chama.modulate.a = clampf(minf(_t / 0.12, (dur + 0.3 - _t) / 0.3), 0.0, 1.0)
		if _t >= dur + 0.3:
			queue_free()

## Anel de Fogo: círculo de chamas parado no chão; quem está na faixa do anel queima e leva dano em pulsos.
class Anel extends Node2D:
	const PULSO := 0.4      # só ritmo visual do dano em pulsos
	var raio := 150.0
	var banda := 52.0
	var dur := 5.0
	var dano := 0.0
	var queima_s := 3.0
	var dps := 4.0
	var _t := 0.0
	var _acc := 0.0

	var _anel: Node2D

	func _ready() -> void:
		z_index = -1
		Vfx.registrar_animado(self)
		Vfx.registrar_decalque(self)
		_anel = Node2D.new()   # dois anéis de chamas, o de dentro 14% menor, dobram a espessura da faixa
		add_child(_anel)
		var esc := (raio * 2.0 + banda) / maxf(Px.tamanho("fire_ring").x, 1.0)
		for k in [1.0, 0.86]:
			var r := Px.criar("fire_ring", esc * k, true, "centro")
			_anel.add_child(r)

	func _physics_process(delta: float) -> void:
		_t += delta
		_acc += delta
		if _acc >= PULSO:
			_acc = 0.0
			for e in U.no_raio(self, global_position, raio + banda * 0.5):
				var v: Vector2 = e.global_position - global_position
				v.y *= 2.0   # o anel pintado é uma elipse (visão 3/4): a faixa que queima é a mesma elipse
				if absf(v.length() - raio) <= banda * 0.5:
					e.take_damage(dano, global_position)
					if is_instance_valid(e):
						Fu.queimar(e, queima_s, dps)
		queue_redraw()
		if _t >= dur:
			queue_free()

	func _draw() -> void:
		var cresce := 1.0 - pow(1.0 - clampf(_t / 0.35, 0.0, 1.0), 3.0)
		var k := clampf((dur - _t) / 0.5, 0.0, 1.0)
		var r := raio * cresce
		_anel.modulate.a = k
		_anel.scale = Vector2.ONE * maxf(cresce, 0.05)

## Bomba-Rastilho: esfera com pavio aceso presa ao inimigo; quando o pavio acaba, explode e arma as bombas dos vizinhos.
class Bomba extends Node2D:
	const PAVIO_CADEIA := 0.5   # só ritmo visual da propagação
	const DPS_QUEIMA := 4.0     # queimadura que a explosão deixa
	var alvo: Node2D
	var def: Dictionary = {}
	var geracao := 0
	var pavio := 1.2
	var dano := 0.0
	var dano_base := 0.0
	var ctx: Dictionary = {}
	var raio := 90.0
	var max_ger := 2
	var _t := 0.0
	var _ultimo := Vector2.ZERO

	## Prende uma bomba num inimigo. `geracao` 0 é a da flecha; cada explosão arma as vizinhas (geração + 1) até `qtd` gerações,
	## cada geração com `valor` do dano da anterior. `ctx` evita bomba repetida no mesmo inimigo e limita o total.
	static func armar(cena: Node, alvo: Node2D, def: Dictionary, dano_base: float, geracao: int, pavio: float, ctx: Dictionary) -> void:
		if not is_instance_valid(alvo) or ctx["vistos"].has(alvo.get_instance_id()) or int(ctx["vivas"]) >= MAX_CADEIA:
			return
		ctx["vistos"][alvo.get_instance_id()] = true
		ctx["vivas"] = int(ctx["vivas"]) + 1
		var b := Bomba.new()
		b.alvo = alvo
		b.def = def
		b.geracao = geracao
		b.pavio = pavio
		b.dano = dano_base * pow(clampf(def.get("valor", 0.6), 0.1, 1.0), float(geracao))
		b.dano_base = dano_base
		b.ctx = ctx
		b.raio = def.get("raio", 90.0)
		b.max_ger = int(def.get("qtd", 2))
		cena.add_child(b)
		b.global_position = alvo.global_position

	func _ready() -> void:
		z_index = 5
		scale = Vector2(1.6, 1.6)   # bomba legível a 640x360
		_ultimo = global_position

	func _physics_process(delta: float) -> void:
		_t += delta
		if is_instance_valid(alvo) and alvo.is_inside_tree():
			_ultimo = alvo.global_position
		global_position = _ultimo
		queue_redraw()
		if _t >= pavio:
			_explodir()

	func _explodir() -> void:
		var cena := get_parent()
		var fx := Explosao.new()
		fx.raio = raio
		cena.add_child(fx)
		fx.global_position = global_position
		var atingidos := U.no_raio(self, global_position, raio)
		for e in atingidos:
			e.take_damage(dano, global_position)
			if is_instance_valid(e):
				Fu.queimar(e, 3.0, DPS_QUEIMA)
		if geracao < max_ger:
			for e in atingidos:
				if is_instance_valid(e):
					Bomba.armar(cena, e, def, dano_base, geracao + 1, PAVIO_CADEIA, ctx)
		ctx["vivas"] = maxi(int(ctx["vivas"]) - 1, 0)
		queue_free()

	func _draw() -> void:
		var f := clampf(_t / pavio, 0.0, 1.0)
		var c := Vector2(0, -50)
		var pisca := 0.5 + 0.5 * sin(_t * (8.0 + 30.0 * f))
		draw_circle(c + Vector2(0, 3), 11.0, Color(0, 0, 0, 0.25))
		draw_circle(c, 10.0, Color(0.12, 0.1, 0.1))
		draw_circle(c, 10.0, Color(1.0, 0.25, 0.05, 0.6 * pisca * f))   # esquenta perto de explodir
		draw_circle(c + Vector2(-3, -4), 3.5, Color(0.55, 0.5, 0.5, 0.8))
		var topo := c + Vector2(3, -10)
		var fim := topo + Vector2(5, -8 - 8.0 * (1.0 - f))   # o pavio encurta
		draw_polyline(PackedVector2Array([topo, topo.lerp(fim, 0.5) + Vector2(2, 0), fim]), Color(0.75, 0.6, 0.35), 2.0)
		U.chama(self, fim, 10.0 + 4.0 * pisca, 4.0, _t * 25.0)
		draw_circle(fim, 7.0, Color(1.0, 0.8, 0.3, 0.25 + 0.2 * pisca))

## Clarão da explosão (curto): bola de fogo que abre até o raio, anel e faíscas radiais.
class Explosao extends Node2D:
	const VIDA := 0.45
	var raio := 90.0
	var _t := 0.0
	func _ready() -> void:
		z_index = 6
		var s := Px.criar("barrel_explosion", raio * 2.6 / maxf(Px.tamanho("barrel_explosion").x, 1.0), false, "base")
		s.position = Vector2(0, 14)
		add_child(s)
		if s is AnimatedSprite2D:
			s.animation_finished.connect(queue_free)
		else:
			queue_free()
