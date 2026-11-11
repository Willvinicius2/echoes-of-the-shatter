extends RefCounted
## Habilidades físicas do Arqueiro com identidade própria (docs/design/39_leque_skills_fisico.md), ramos Precisão e Caçada:
## Virote de Cerco (atravessa e arrasta), Tiro Certeiro (mira travada no mais forte), Revoada (flechas teleguiadas),
## Leque de Lâminas (vai e volta), Chuva de Flechas (flechas que cravam e prendem), Armadilha de Mandíbulas (fecha e puxa),
## Flecha de Estilhaços (estoura no ar e semeia bombas) e Marca do Caçador (falcão que marca e a marca salta).
## Cada skill é um nó que se desenha (`_draw`) mais sprites pequenos de pixel art feitos por código (sem folha nova).
## Números de balanceamento só em data2d/habilidades_arqueiro.csv; as constantes daqui são ritmo visual.

const U = preload("res://scripts2d/efeitos_extra_util_2d.gd")
const Alvos = preload("res://scripts2d/alvos_2d.gd")
const Vfx = preload("res://scripts2d/vfx_2d.gd")
const Feel = preload("res://scripts2d/feel_2d.gd")
const Px = preload("res://scripts2d/fx_pixel_2d.gd")
const F = preload("res://scripts2d/pixel_fisico_2d.gd")
const EFEITOS := ["tiro_forte", "tiro_certeiro", "rajada", "leque", "chuva", "armadilha", "explosiva", "marca"]
const ALT := 28.0                      # altura de voo do desenho sobre o chão
const OURO := Color(1.0, 0.82, 0.42)
const ACO := Color(0.78, 0.84, 0.92)

static func executar(efeito: String, jogador: Node2D, def: Dictionary, mira: Vector2) -> bool:
	var dir: Vector2 = mira.normalized() if mira != Vector2.ZERO else jogador.mira_atual()
	var base: float = jogador.stats["arrow_damage"]
	var dano: float = base * def.get("dano", 1.0)
	var cena: Node = jogador.get_parent()
	var boca: Dictionary = jogador.boca_do_arco(dir)
	var saida: Vector2 = boca["chao"] + Vector2(0, -boca["altura"])
	match efeito:
		"tiro_forte":
			var v := Virote.new()
			v.dir = dir
			v.vel = jogador.stats["arrow_speed"] * def.get("valor", 1.0) * float(def.get("vel", 1.0))
			v.alcance = def.get("alcance", 0.0) if def.get("alcance", 0.0) > 0.0 else jogador.stats["arrow_range"]
			v.dano = F.dano_critico(jogador, def.get("dano", 1.0))
			v.restam = int(def.get("qtd", 0)) + int(def.get("perfura", 0)) + int(jogador.stats.get("arrow_pierce", 0))
			v.raio_onda = def.get("raio", 0.0)
			v.atordoa = def.get("duracao", 0.0)
			cena.add_child(v)
			v.global_position = boca["origem"]
			Vfx.flash_boca(cena, saida, dir)
			jogador.recuar_sprite(dir, Feel.cfg()["shot_recoil_px"] * 2.0, Feel.cfg()["shot_recoil_time"])
		"tiro_certeiro":
			var c := Certeiro.new()
			c.jogador = jogador
			c.dir = dir
			c.alcance = def.get("alcance", 0.0) if def.get("alcance", 0.0) > 0.0 else jogador.stats["arrow_range"]
			c.mira_t = maxf(def.get("duracao", 0.4) / maxf(float(def.get("vel", 1.0)), 0.1), 0.05)
			c.dano = dano
			c.crit = maxf(float(jogador.stats.get("crit_mult", 1.0)), 1.0)
			c.alvo = _mais_forte(jogador, c.alcance)
			cena.add_child(c)
			c.global_position = jogador.global_position
		"rajada":
			var r := Revoada.new()
			r.jogador = jogador
			r.dir = dir
			r.n = maxi(1, int(def.get("qtd", 5)) + int(def.get("proj_extra", 0)))
			r.passo = def.get("duracao", 0.09)
			r.dano_mult = def.get("dano", 1.0)
			r.alcance = def.get("alcance", 0.0) if def.get("alcance", 0.0) > 0.0 else jogador.stats["arrow_range"]
			r.vel = jogador.stats["arrow_speed"] * float(def.get("vel", 1.0))
			cena.add_child(r)
		"leque":
			var n := maxi(1, int(def.get("qtd", 3)))
			var abertura: float = deg_to_rad(def.get("angulo", 40.0))
			var volta: bool = def.get("forma", "") == "espiral" or abertura >= TAU - 0.01
			for i in n:
				var a := 0.0 if n == 1 else (TAU * i / float(n) if volta else -abertura * 0.5 + abertura * i / float(n - 1))
				var l := Lamina.new()
				l.jogador = jogador
				l.dir = dir.rotated(a)
				l.alcance = def.get("alcance", 380.0)
				if not volta and n > 1:   # a lâmina do centro vai mais longe: o conjunto lê como leque (V), não como coluna
					l.alcance *= 1.0 - 0.3 * absf(a) / maxf(abertura * 0.5, 0.01)
				l.vel = jogador.stats["arrow_speed"] * float(def.get("vel", 1.0))
				l.dano = dano
				l.position = jogador.global_position   # antes do add_child: o _ready guarda a origem
				cena.add_child(l)
			Vfx.flash_boca(cena, saida, dir)
		"chuva":
			var ch := Chuva.new()
			ch.raio = def.get("raio", 120.0)
			ch.dur = maxf(def.get("duracao", 2.0), 0.2)
			ch.pulsos = maxi(1, int(def.get("qtd", 5)))
			ch.dano = dano
			ch.lento = def.get("valor", 0.0)
			ch.origem = saida
			cena.add_child(ch)
			ch.global_position = U.ponto(jogador, dir, def.get("alcance", 400.0))
			Vfx.flash_boca(cena, saida, Vector2.UP)
		"armadilha":
			var m := Mandibula.new()
			m.raio = def.get("raio", 90.0)
			m.atordoa = def.get("duracao", 1.0)
			m.dano = dano
			m.origem = saida
			cena.add_child(m)
			m.global_position = U.ponto(jogador, dir, def.get("alcance", 400.0))
		"explosiva":
			var destino := U.ponto(jogador, dir, def.get("alcance", 600.0))
			var raio: float = def.get("raio", 120.0)
			var frag: float = dano * float(def.get("valor", 0.4))
			var qtd := maxi(0, int(def.get("qtd", 6)))
			Vfx.flash_boca(cena, saida, dir)
			Vfx.arco(cena, boca["chao"], boca["altura"], destino, 200.0, Estilhacos.VOO, F.sprite("pote", 1.6), Color(1.0, 0.5, 0.2), raio,
				func(ponto: Vector2):
					if not is_instance_valid(cena) or not cena.is_inside_tree():
						return
					var e := Estilhacos.new()
					e.raio = raio
					e.dano = dano
					e.dano_frag = frag
					e.n = qtd
					cena.add_child(e)
					e.global_position = ponto, true)
		"marca":
			var alvo := _alvo_na_mira(jogador, dir, def.get("alcance", 600.0))
			if alvo == null:
				return false   # sem alvo perto da mira: não gasta a recarga
			Falcao.soltar(cena, jogador.global_position + Vector2(-dir.x * 60.0, -150.0), alvo,
				{"dano": base * float(def.get("dano", 0.0)), "dur": def.get("duracao", 6.0), "valor": def.get("valor", 0.3), "raio": def.get("raio", 0.0)})
		_:
			push_error("Efeito físico de arqueiro desconhecido: " + efeito)
			return false
	return true

## Inimigo mais alinhado com a mira (até 20 graus) dentro do alcance.
static func _alvo_na_mira(jogador: Node2D, dir: Vector2, alcance: float) -> Node2D:
	var melhor: Node2D = null
	var melhor_a := deg_to_rad(20.0)
	for n in jogador.get_tree().get_nodes_in_group("hurtable"):
		if n is Node2D and n.has_method("aplicar_status"):
			var v: Vector2 = n.global_position - jogador.global_position
			if v.length() <= alcance and absf(dir.angle_to(v)) <= melhor_a:
				melhor_a = absf(dir.angle_to(v))
				melhor = n
	return melhor

## Inimigo de maior vida máxima à vista dentro do alcance (o Tiro Certeiro caça o elite ou o chefe).
static func _mais_forte(jogador: Node2D, alcance: float) -> Node2D:
	var arv := jogador.get_tree()
	var melhor: Node2D = null
	var melhor_hp := -1.0
	for n in Alvos.em_circulo(arv, jogador.global_position, alcance):
		if not (n is Node2D) or not n.has_method("take_damage") or n.get("hp_max") == null:
			continue
		if float(n.hp_max) > melhor_hp and Alvos.na_tela(arv, n.global_position) and Alvos.ve(arv, jogador.global_position, n.global_position):
			melhor_hp = float(n.hp_max)
			melhor = n
	return melhor

## Virote de Cerco: dardo de balista que atravessa `restam`+1 corpos, ARRASTA cada um na direção do voo e, ao parar
## (último corpo, parede ou fim do alcance), crava no chão e solta uma onda que atordoa quem está em volta.
class Virote extends Node2D:
	const LARG := 30.0
	const ARRASTO := 6.0      # teto do arrasto, em vezes o empurrão comum (sensação do golpe)
	const TRECHO := 150.0     # até onde o virote leva o corpo atravessado
	const VIDA_CRAVADO := 0.9
	var dir := Vector2.RIGHT
	var vel := 900.0
	var alcance := 900.0
	var dano := 0.0
	var restam := 2
	var raio_onda := 0.0
	var atordoa := 0.0
	var _andou := 0.0
	var _t := 0.0
	var _cravado := false
	var _feridos: Array = []
	var _spr: Sprite2D

	func _ready() -> void:
		z_index = 4
		Vfx.registrar_animado(self)
		_spr = F.sprite("virote", 2.3)
		_spr.rotation = dir.angle()
		_spr.position = Vector2(0, -ALT)
		add_child(_spr)

	func _physics_process(delta: float) -> void:
		_t += delta
		queue_redraw()
		if _cravado:
			_spr.modulate.a = 1.0 - clampf((_t - VIDA_CRAVADO * 0.6) / (VIDA_CRAVADO * 0.4), 0.0, 1.0)
			if _t >= VIDA_CRAVADO:
				queue_free()
			return
		var a := global_position
		var b := a + dir * vel * delta
		if not Alvos.ve(get_tree(), a, b):
			_cravar()
			return
		var forca: float = Feel.cfg()["enemy_knockback"] * ARRASTO
		for e in Alvos.em_segmento(get_tree(), a, b, LARG):
			if _feridos.has(e) or not e.has_method("take_damage"):
				continue
			_feridos.append(e)
			e.take_damage(dano, a)
			restam -= 1
			if restam < 0:
				global_position = e.global_position if is_instance_valid(e) else b
				_cravar()
				return
		for e in _feridos:   # arrasto: quem foi atravessado é levado junto por um trecho
			if is_instance_valid(e) and e.global_position.distance_to(b) <= TRECHO:
				F.empurrar(e, dir * minf(vel * 0.8, forca))
		global_position = b
		_andou += vel * delta
		if _andou >= alcance:
			_cravar()

	func _cravar() -> void:
		_cravado = true
		_t = 0.0
		z_index = 0
		_spr.rotation = dir.angle() + (0.5 if dir.x >= 0.0 else -0.5)
		_spr.position = Vector2(0, -18.0) - dir * 36.0
		Feel.shake(self, Feel.cfg()["shake_kill_amp"], Feel.cfg()["shake_kill_time"])
		if raio_onda <= 0.0:
			return
		for e in U.no_raio(self, global_position, raio_onda):
			if atordoa > 0.0 and e.has_method("aplicar_status"):
				e.aplicar_status("atordoamento", atordoa)
			F.empurrar(e, (e.global_position - global_position).normalized() * Feel.cfg()["enemy_knockback"])

	func _draw() -> void:
		var o := dir.orthogonal()
		if not _cravado:
			var ponta := Vector2(0, -ALT) + dir * 90.0
			for i in 3:   # cunhas de ar na frente da ponta
				var k := fmod(_t * 6.0 + float(i) / 3.0, 1.0)
				var p := ponta - dir * (10.0 + 80.0 * k)
				var w := 16.0 + 36.0 * k
				var c := Color(1.0, 0.95, 0.8, 0.9 * (1.0 - k))
				draw_line(p, p - dir * 22.0 + o * w, c, 6.0)
				draw_line(p, p - dir * 22.0 - o * w, c, 6.0)
			for i in 6:   # poeira levantada no chão atrás do virote
				var u := float(i) / 6.0
				U.elipse(self, -dir * (40.0 + 170.0 * u) + o * U.ruido(float(i), _t * 3.0) * 8.0, 12.0 + 16.0 * u, Color(0.85, 0.78, 0.62, 0.45 * (1.0 - u)))
			draw_line(Vector2(0, -ALT) - dir * 260.0, Vector2(0, -ALT) - dir * 60.0, Color(OURO, 0.4), 12.0)
			draw_line(Vector2(0, -ALT) - dir * 180.0, Vector2(0, -ALT) - dir * 60.0, Color(1, 1, 1, 0.6), 5.0)
			return
		var k := clampf(_t / 0.35, 0.0, 1.0)
		var alfa := 1.0 - clampf(_t / VIDA_CRAVADO, 0.0, 1.0)
		var r := maxf(raio_onda, 40.0) * 1.3
		U.elipse(self, Vector2.ZERO, 16.0, Color(0, 0, 0, 0.35 * alfa))
		U.elipse_arco(self, Vector2.ZERO, r * k, Color(1.0, 0.95, 0.8, 0.9 * (1.0 - k)), 7.0)
		U.elipse_arco(self, Vector2.ZERO, r * k * 0.7, Color(OURO, 0.7 * (1.0 - k)), 4.0)
		for i in 7:   # rachaduras no chão em volta do ponto cravado
			var ang := TAU * float(i) / 7.0 + 0.4
			var fim := Vector2.from_angle(ang) * Vector2(r, r * 0.5) * (0.35 + 0.2 * U.ruido(float(i), 1.0)) * minf(k * 2.0, 1.0)
			draw_line(Vector2.ZERO, fim, Color(0.1, 0.08, 0.08, 0.8 * alfa), 5.0)
		for i in 8:   # pedrinhas que saltam
			var ang := TAU * float(i) / 8.0
			var p := Vector2.from_angle(ang) * Vector2(1.0, 0.5) * r * 0.6 * k + Vector2(0, -30.0 * sin(k * PI))
			draw_rect(Rect2(p - Vector2(5, 5), Vector2(10, 10)), Color(0.75, 0.7, 0.6, 1.0 - k))

## Tiro Certeiro: o arqueiro trava a mira no inimigo de maior vida (retículo fecha, linha de mira treme), e então
## solta um tiro instantâneo que atravessa a linha inteira; o alvo travado leva o dano crítico garantido.
class Certeiro extends Node2D:
	const LARG := 16.0
	const RASTRO := 0.45
	var jogador: Node2D
	var alvo: Node2D
	var dir := Vector2.RIGHT
	var alcance := 900.0
	var mira_t := 0.4
	var dano := 0.0
	var crit := 1.0
	var _t := 0.0
	var _feito := false
	var _fim := Vector2.ZERO      # local: onde o tiro parou
	var _marca := Vector2.ZERO    # local: onde estava o alvo

	func _ready() -> void:
		z_index = 4
		Vfx.registrar_animado(self)

	func _physics_process(delta: float) -> void:
		_t += delta
		queue_redraw()
		if _feito:
			if _t >= mira_t + RASTRO:
				queue_free()
			return
		if not is_instance_valid(jogador) or jogador.esta_morto():
			queue_free()
			return
		global_position = jogador.global_position
		if _vivo(alvo):
			dir = (alvo.global_position - global_position).normalized()
			_marca = alvo.global_position - global_position
		else:
			_marca = dir * alcance * 0.6
		if _t >= mira_t:
			_atirar()

	static func _vivo(e: Variant) -> bool:
		return is_instance_valid(e) and e.is_inside_tree() and e.is_in_group("hurtable")

	func _atirar() -> void:
		_feito = true
		var a := global_position
		var b := a + dir * alcance
		var bate := get_world_2d().direct_space_state.intersect_ray(PhysicsRayQueryParameters2D.create(a, b, 1))
		if not bate.is_empty():
			b = bate["position"]
		for e in Alvos.em_segmento(get_tree(), a, b, LARG):
			if e.has_method("take_damage"):
				e.take_damage(dano * (crit if e == alvo else 1.0), a)
		_fim = b - a
		var c := Feel.cfg()
		Feel.shake(self, c["shake_kill_amp"], c["shake_kill_time"])
		jogador.recuar_sprite(dir, c["shot_recoil_px"] * 2.5, c["shot_recoil_time"])
		Vfx.flash_boca(get_parent(), a + Vector2(0, -ALT), dir)

	func _draw() -> void:
		var org := Vector2(0, -ALT)
		if not _feito:
			var k := clampf(_t / mira_t, 0.0, 1.0)
			var alvo_p := _marca + Vector2(0, -ALT)
			var passos := 14
			for i in passos:   # linha de mira tracejada que corre para o alvo
				var u0 := (float(i) + fmod(_t * 4.0, 1.0)) / float(passos)
				var u1 := minf(u0 + 0.5 / float(passos), 1.0)
				draw_line(org.lerp(alvo_p, u0), org.lerp(alvo_p, u1), Color(1.0, 0.35, 0.25, 0.45 + 0.5 * k), 5.0)
			var r := lerpf(90.0, 30.0, k)
			var gira := (1.0 - k) * 1.6
			for i in 4:   # retículo: quatro cantoneiras fechando no alvo
				var a0 := gira + TAU * float(i) / 4.0
				draw_arc(alvo_p, r, a0 - 0.45, a0 + 0.45, 6, Color(OURO, 0.95), 6.0)
				draw_line(alvo_p + Vector2.from_angle(a0) * r, alvo_p + Vector2.from_angle(a0) * (r + 18.0), Color(OURO, 0.95), 6.0)
			draw_rect(Rect2(alvo_p - Vector2(5, 5), Vector2(10, 10)), Color(1.0, 0.35, 0.25))
			return
		var k := clampf((_t - mira_t) / RASTRO, 0.0, 1.0)
		var fim := _fim + Vector2(0, -ALT)
		var o := dir.orthogonal()
		draw_line(org, fim, Color(OURO, 0.6 * (1.0 - k)), 30.0 * (1.0 - k) + 3.0)
		draw_line(org, fim, Color(1, 1, 1, 1.0 - k), 13.0 * (1.0 - k) + 2.0)
		var n := int(_fim.length() / 110.0)
		for i in n:   # anéis de ar rasgado ao longo do tiro
			var p := org.lerp(fim, (float(i) + 0.6) / float(maxi(n, 1)))
			var w := 14.0 + 44.0 * k
			draw_line(p - o * w, p + o * w, Color(1, 1, 1, 0.8 * (1.0 - k)), 5.0)
			draw_line(p - o * w * 0.6 - dir * 6.0, p + o * w * 0.6 - dir * 6.0, Color(OURO, 0.6 * (1.0 - k)), 4.0)
		var x := _marca + Vector2(0, -ALT)   # corte em X onde o alvo travado foi atingido
		var tam := 28.0 + 50.0 * k
		draw_line(x - Vector2(tam, tam), x + Vector2(tam, tam), Color(1, 1, 1, 1.0 - k), 10.0 * (1.0 - k) + 2.0)
		draw_line(x - Vector2(tam, -tam), x + Vector2(tam, -tam), Color(1, 1, 1, 1.0 - k), 10.0 * (1.0 - k) + 2.0)

## Revoada: `n` flechas saem uma a uma para os lados e fazem a curva sozinhas, cada uma atrás de um inimigo diferente
## (do mais perto ao mais longe; com menos inimigos que flechas, elas se repartem entre os que existem).
class Revoada extends Node:
	var jogador: Node2D
	var dir := Vector2.RIGHT
	var n := 5
	var passo := 0.09
	var dano_mult := 1.0
	var alcance := 700.0
	var vel := 900.0
	var _t := 0.0
	var _saiu := 0

	func _physics_process(delta: float) -> void:
		if not is_instance_valid(jogador) or jogador.esta_morto():
			queue_free()
			return
		_t += delta
		while _saiu < n and _t >= passo * float(_saiu):
			_lancar(_saiu)
			_saiu += 1
		if _saiu >= n:
			queue_free()

	func _lancar(i: int) -> void:
		var arv := jogador.get_tree()
		var alvos: Array = U.mais_proximos(jogador, jogador.global_position, alcance, n).filter(
			func(e): return Alvos.ve(arv, jogador.global_position, e.global_position))
		var mira: Vector2 = jogador.mira_atual() if alvos.is_empty() else dir
		var boca: Dictionary = jogador.boca_do_arco(mira)
		var a := Andorinha.new()
		a.origem = boca["chao"] + Vector2(0, -boca["altura"])
		a.dano = F.dano_critico(jogador, dano_mult)
		var lado := 1.0 if i % 2 == 0 else -1.0
		if alvos.is_empty():
			a.destino = jogador.global_position + mira.rotated(lado * 0.12 * float(i / 2 + 1)) * alcance * 0.7
		else:
			a.alvo = alvos[i % alvos.size()]
			a.destino = a.alvo.global_position
		var d := a.destino - jogador.global_position
		a.ctrl = jogador.global_position + d * 0.25 + d.orthogonal().normalized() * lado * (130.0 + 55.0 * float(i / 2)) + Vector2(0, -ALT)
		a.dur = clampf(d.length() / maxf(vel, 1.0) * 1.3, 0.28, 0.75)
		jogador.get_parent().add_child(a)
		Vfx.flash_boca(jogador.get_parent(), a.origem, mira)

## Uma flecha teleguiada da Revoada: curva de Bézier que persegue o alvo, rastro dourado e penas no acerto.
class Andorinha extends Node2D:
	const RAIO_ACERTO := 26.0
	var alvo: Node2D
	var origem := Vector2.ZERO    # já na altura do arco
	var ctrl := Vector2.ZERO
	var destino := Vector2.ZERO   # no chão
	var dur := 0.4
	var dano := 0.0
	var _t := 0.0
	var _spr: Sprite2D
	var _rastro := PackedVector2Array()

	func _ready() -> void:
		z_index = 4
		top_level = true
		Vfx.registrar_animado(self)
		_spr = F.sprite("flecha", 2.0)
		add_child(_spr)
		_spr.global_position = origem

	func _physics_process(delta: float) -> void:
		_t += delta
		if is_instance_valid(alvo) and alvo.is_inside_tree() and alvo.is_in_group("hurtable"):
			destino = alvo.global_position
		var f := clampf(_t / dur, 0.0, 1.0)
		var fim := destino + Vector2(0, -ALT)
		var p := origem.lerp(ctrl, f).lerp(ctrl.lerp(fim, f), f)
		var v := p - _spr.global_position
		if v.length_squared() > 0.01:
			_spr.rotation = v.angle()
		_spr.global_position = p
		_rastro.append(p)
		if _rastro.size() > 12:
			_rastro.remove_at(0)
		queue_redraw()
		if f >= 1.0:
			var feridos: Array = [alvo] if (is_instance_valid(alvo) and alvo.is_in_group("hurtable")) else U.no_raio(self, destino, RAIO_ACERTO).slice(0, 1)
			for e in feridos:
				e.take_damage(dano, destino - v.normalized() * 12.0)
			Feel.impacto(get_parent(), p, OURO, -v.normalized())
			queue_free()

	func _draw() -> void:
		for i in range(1, _rastro.size()):
			var k := float(i) / float(_rastro.size())
			draw_line(_rastro[i - 1], _rastro[i], Color(OURO, 0.85 * k), 3.0 + 6.0 * k)

## Leque de Lâminas: a lâmina gira para fora desacelerando até `alcance`, para um instante e VOLTA para o arqueiro
## (onde ele estiver), ferindo na ida e de novo na volta. Parede no caminho faz voltar antes.
class Lamina extends Node2D:
	const LARG := 30.0
	var jogador: Node2D
	var dir := Vector2.RIGHT
	var alcance := 380.0
	var vel := 900.0
	var dano := 0.0
	var _origem := Vector2.ZERO
	var _t := 0.0
	var _volta := false
	var _feridos: Array = []
	var _spr: Sprite2D

	func _ready() -> void:
		z_index = 4
		Vfx.registrar_animado(self)
		_origem = global_position
		_spr = F.sprite("lamina", 3.6)
		_spr.position = Vector2(0, -ALT)
		add_child(_spr)

	func _physics_process(delta: float) -> void:
		_t += delta
		_spr.rotation += delta * (26.0 if not _volta else -26.0)
		var antes := global_position
		var novo := antes
		if not _volta:
			var ida := maxf(alcance / maxf(vel * 0.75, 1.0), 0.15)
			var f := clampf(_t / ida, 0.0, 1.0)
			novo = _origem + dir * alcance * sin(f * PI * 0.5)
			if f >= 1.0 or not Alvos.ve(get_tree(), antes, novo):
				novo = antes if f < 1.0 else novo
				_volta = true
				_t = 0.0
				_feridos.clear()
		else:
			if not is_instance_valid(jogador):
				queue_free()
				return
			var para: Vector2 = jogador.global_position
			var passo := vel * minf(0.35 + _t * 2.2, 1.4) * delta
			if antes.distance_to(para) <= passo + 18.0:
				queue_free()
				return
			novo = antes.move_toward(para, passo)
		for e in Alvos.em_segmento(get_tree(), antes, novo, LARG):
			if not _feridos.has(e) and e.has_method("take_damage"):
				_feridos.append(e)
				e.take_damage(dano, antes)
		global_position = novo
		queue_redraw()

	func _draw() -> void:
		U.elipse(self, Vector2.ZERO, 20.0, Color(0, 0, 0, 0.3))
		var c := Vector2(0, -ALT)
		var a0 := _spr.rotation
		var s := -1.0 if not _volta else 1.0
		draw_arc(c, 34.0, a0, a0 + s * 2.4, 8, Color(1, 1, 1, 0.6), 6.0)       # borrão do giro
		draw_arc(c, 42.0, a0 + PI, a0 + PI + s * 1.6, 6, Color(ACO, 0.5), 4.0)

## Chuva de Flechas: uma salva sobe do arco e, a cada pulso, flechas de verdade caem em diagonal, cravam no chão e
## ficam lá; quem é atingido fica cravado (lento) por um instante. Sem disco chapado: só o contorno fino da área.
class Chuva extends Node2D:
	const ATRASO := 0.4       # a salva sobe antes de cair
	const QUEDA := 0.16
	const POR_PULSO := 9
	const MAX_CRAVADAS := 54
	const PRESO_S := 0.7
	var raio := 150.0
	var dur := 2.4
	var pulsos := 6
	var dano := 0.0
	var lento := 0.0
	var origem := Vector2.ZERO
	var _t := 0.0
	var _prox := 0
	var _flechas: Array = []   # [posição local no chão, instante em que crava, espelhada]
	var _rng := RandomNumberGenerator.new()

	func _ready() -> void:
		z_index = 1
		texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		Vfx.registrar_animado(self)
		_rng.seed = 11
		Vfx.sombra_aviso(get_parent(), global_position, raio, OURO, ATRASO)

	func _physics_process(delta: float) -> void:
		_t += delta
		while _prox < pulsos and _t >= ATRASO + dur * float(_prox) / float(pulsos):
			_prox += 1
			for i in POR_PULSO:
				var p := Vector2.from_angle(_rng.randf() * TAU) * raio * sqrt(_rng.randf()) * 0.95
				_flechas.append([p, _t + QUEDA + _rng.randf() * 0.12, _rng.randf() < 0.5])
			while _flechas.size() > MAX_CRAVADAS:
				_flechas.remove_at(0)
			for e in Alvos.no_raio(get_tree(), global_position, raio, "take_damage"):
				e.take_damage(dano, global_position)
				if lento > 0.0 and is_instance_valid(e) and e.has_method("aplicar_status"):
					e.aplicar_status("lentidao", PRESO_S, lento)
		queue_redraw()
		if _t >= ATRASO + dur + 0.8:
			queue_free()

	func _draw() -> void:
		var some := 1.0 - clampf((_t - ATRASO - dur) / 0.8, 0.0, 1.0)
		if _t < ATRASO:   # a salva subindo do arco
			var k := _t / ATRASO
			var de := origem - global_position
			for i in 5:
				var p := de + Vector2((float(i) - 2.0) * 9.0, -520.0 * k - float(i % 2) * 30.0)
				draw_line(p, p + Vector2(0, 80.0), Color(OURO, 0.9 * (1.0 - k * 0.5)), 5.0)
		for i in 24:   # contorno tracejado da área (tamanho exato do dano)
			if i % 2 == 0:
				draw_arc(Vector2.ZERO, raio, TAU * float(i) / 24.0, TAU * float(i + 1) / 24.0, 3, Color(OURO, 0.5 * some), 4.0)
		var t := F.tex("cravada")
		var tam := t.get_size() * F.ESC * 2.2
		for f in _flechas:
			var p: Vector2 = f[0]
			var cai: float = f[1]
			var lado := -1.0 if f[2] else 1.0
			if _t < cai:
				var k := clampf(1.0 - (cai - _t) / QUEDA, 0.0, 1.0)
				var topo := p + Vector2(lado * 70.0, -420.0) * (1.0 - k)
				draw_line(topo + Vector2(lado * 15.0, -90.0), topo, Color(1.0, 0.95, 0.8, 0.9), 5.0)
				U.elipse(self, p, 3.0 + 5.0 * k, Color(0, 0, 0, 0.3 * k))
				continue
			var idade := _t - cai
			if idade < 0.18:   # poeira do impacto
				U.elipse_arco(self, p, 8.0 + 110.0 * idade, Color(0.9, 0.85, 0.7, 0.8 * (1.0 - idade / 0.18)), 4.0)
			U.elipse(self, p, 9.0, Color(0, 0, 0, 0.3 * some))
			var treme := sin(idade * 60.0) * 2.0 * maxf(0.0, 1.0 - idade / 0.25)
			draw_set_transform(p + Vector2(treme, 0), 0.0, Vector2(lado, 1.0))
			draw_texture_rect(t, Rect2(Vector2(-tam.x * 0.14, -tam.y), tam), false, Color(1, 1, 1, some))
			draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)

## Armadilha de Mandíbulas: voa do arco até o ponto, abre os dentes no chão e espera. Quem pisa no miolo faz as
## mandíbulas fecharem: fere, atordoa e PUXA para o centro todos dentro do raio.
class Mandibula extends Node2D:
	const VOO := 0.32
	const VIDA := 18.0        # vida máxima se ninguém pisar
	const PUXAO := 2.2        # vezes o empurrão comum, para dentro
	const PLACA := 46.0       # raio do desenho da armadilha (a área de efeito é o `raio`)
	var tipo := "armadilha"   # os testes acham a armadilha por este campo (como a zona antiga)
	var raio := 90.0
	var atordoa := 1.2
	var dano := 0.0
	var origem := Vector2.ZERO
	var _t := 0.0
	var _fechou := -1.0

	func _ready() -> void:
		z_index = 0
		Vfx.registrar_animado(self)

	func _physics_process(delta: float) -> void:
		_t += delta
		queue_redraw()
		if _fechou >= 0.0:
			if _t - _fechou >= atordoa + 0.4:
				queue_free()
			return
		if _t < VOO:
			return
		if Alvos.no_raio(get_tree(), global_position, raio * 0.45).is_empty():
			if _t >= VIDA:
				queue_free()
			return
		_fechou = _t
		var c := Feel.cfg()
		for e in Alvos.no_raio(get_tree(), global_position, raio, "take_damage"):
			var para: Vector2 = (global_position - e.global_position)
			e.take_damage(dano, global_position)
			if not is_instance_valid(e):
				continue
			if e.has_method("aplicar_status"):
				e.aplicar_status("atordoamento", atordoa, 0.0)
			F.empurrar(e, para.normalized() * minf(c["enemy_knockback"] * PUXAO, para.length() * 8.0))
		Feel.shake(self, c["shake_kill_amp"], c["shake_kill_time"])
		Feel.impacto(get_parent(), global_position + Vector2(0, -16), ACO, Vector2.ZERO, 1.6)

	func _dente(base: Vector2, ponta: Vector2, larg: float, cor: Color) -> void:
		var o := (ponta - base).orthogonal().normalized() * larg
		draw_colored_polygon(PackedVector2Array([base + o, ponta, base - o]), cor)
		draw_line(base + o, ponta, Color(0.1, 0.08, 0.1), 3.0)

	func _draw() -> void:
		if _t < VOO:   # voando fechada, em parábola, do arco ao ponto
			var k := _t / VOO
			var p := (origem - global_position).lerp(Vector2.ZERO, k) + Vector2(0, -90.0 * sin(k * PI))
			U.elipse(self, Vector2.ZERO, 6.0 + 14.0 * k, Color(0, 0, 0, 0.3 * k))
			draw_circle(p, 15.0, Color(0.1, 0.08, 0.1))
			draw_circle(p, 11.0, F.PALETA["S"])
			draw_rect(Rect2(p + Vector2(-2.5, -5.0), Vector2(5, 2.5)), F.PALETA["s"])
			return
		var some := 1.0
		var abre := 1.0 - pow(1.0 - clampf((_t - VOO) / 0.18, 0.0, 1.0), 3.0)   # 0 = fechada, 1 = aberta no chão
		if _fechou >= 0.0:
			var d := _t - _fechou
			abre = 1.0 - clampf(d / 0.05, 0.0, 1.0)
			some = 1.0 - clampf((d - atordoa) / 0.4, 0.0, 1.0)
			var k := clampf(d / 0.3, 0.0, 1.0)
			U.elipse_arco(self, Vector2.ZERO, raio * (1.0 - 0.6 * k), Color(1, 1, 1, 0.8 * (1.0 - k)), 6.0)   # o ar puxado para dentro
		elif int(_t * 2.0) % 2 == 0:
			for i in 12:   # área que a armadilha alcança, só enquanto espera
				draw_arc(Vector2.ZERO, raio, TAU * float(i) / 12.0, TAU * (float(i) + 0.35) / 12.0, 2, Color(ACO, 0.4), 4.0)
		modulate.a = some
		U.elipse(self, Vector2(0, 3), PLACA * 1.15, Color(0, 0, 0, 0.35))
		U.elipse(self, Vector2.ZERO, PLACA, F.PALETA["H"])
		U.elipse(self, Vector2.ZERO, PLACA * 0.72, F.PALETA["B"])
		U.elipse(self, Vector2.ZERO, PLACA * 0.3, F.PALETA["S"])          # o gatilho no meio
		draw_rect(Rect2(Vector2(-5, -5), Vector2(10, 5)), F.PALETA["s"] if int(_t * 3.0) % 2 == 0 else F.PALETA["Y"])
		var alto := 56.0 * (1.0 - abre)
		for lado in [-1.0, 1.0]:   # duas mandíbulas: abertas ficam deitadas para fora, fechadas se encontram em cima
			for i in 5:
				var u := (float(i) - 2.0) / 2.0
				var base := Vector2(u * PLACA * 0.85, lado * PLACA * 0.42 * sqrt(maxf(1.0 - u * u * 0.8, 0.0)) * (0.25 + 0.75 * abre))
				var ponta := base + Vector2(0.0, lado * 22.0 * abre - alto - 8.0 * (1.0 - abre))
				_dente(base, ponta, 9.0, F.PALETA["s"] if i % 2 == 0 else F.PALETA["S"])

## Flecha de Estilhaços: o pote da flecha estoura ao cair (dano no miolo) e semeia `n` bombinhas que quicam para fora
## em anel e explodem uma depois da outra, cada uma com a sua área pequena.
class Estilhacos extends Node2D:
	const VOO := 0.42
	const QUIQUE := 0.3
	const PASSO := 0.07
	var raio := 130.0
	var dano := 0.0
	var dano_frag := 0.0
	var n := 6
	var _t := 0.0
	var _feitas: Array = []
	var _giro := 0.0

	func _ready() -> void:
		z_index = 4
		Vfx.registrar_animado(self)
		_giro = randf() * TAU
		_feitas.resize(n)
		_feitas.fill(false)
		_estourar(global_position, raio * 0.5, dano, 1.0)

	func _alvo(i: int) -> Vector2:
		return Vector2.from_angle(_giro + TAU * float(i) / float(maxi(n, 1))) * raio * (0.62 + 0.1 * U.ruido(float(i), 3.0))

	func _estourar(p: Vector2, r: float, d: float, forca: float) -> void:
		for e in Alvos.no_raio(get_tree(), p, r, "take_damage"):
			e.take_damage(d, p)
		var t := Px.tamanho("barrel_explosion")
		Px.tocar(get_parent(), "barrel_explosion", p + Vector2(0, r * 0.45), r * 3.0 / maxf(t.x, 1.0), "base")
		Feel.shake(self, Feel.cfg()["shake_kill_amp"] * forca, Feel.cfg()["shake_kill_time"])

	func _physics_process(delta: float) -> void:
		_t += delta
		for i in n:
			if not _feitas[i] and _t >= QUIQUE + PASSO * float(i):
				_feitas[i] = true
				_estourar(global_position + _alvo(i), raio * 0.45, dano_frag, 0.5)
		queue_redraw()
		if _t >= QUIQUE + PASSO * float(n) + 0.9:
			queue_free()

	func _draw() -> void:
		var some := 1.0 - clampf((_t - QUIQUE - PASSO * float(n)) / 0.9, 0.0, 1.0)
		U.elipse(self, Vector2.ZERO, raio * 0.4, Color(0.08, 0.06, 0.05, 0.45 * some))   # chão chamuscado do miolo
		for i in n:
			var alvo := _alvo(i)
			var fim := QUIQUE + PASSO * float(i)
			if _t >= fim:
				U.elipse(self, alvo, raio * 0.3, Color(0.08, 0.06, 0.05, 0.4 * some))
				continue
			var k := _t / fim
			var p := alvo * k + Vector2(0, -110.0 * sin(k * PI))
			U.elipse(self, alvo * k, 6.0, Color(0, 0, 0, 0.3))
			draw_circle(p, 28.0, Color(0.1, 0.08, 0.1))
			draw_circle(p, 22.0, F.PALETA["R"])
			draw_rect(Rect2(p + Vector2(-13.0, -13.0), Vector2(10, 10)), Color(1.0, 0.6, 0.45))
			draw_rect(Rect2(p + Vector2(-6.0, -40.0), Vector2(12, 12)), F.PALETA["Y"] if int(_t * 30.0) % 2 == 0 else Color.WHITE)

## Falcão do caçador: mergulha do céu até o alvo, fere, e deixa a Marca. Também leva a marca de um morto ao próximo.
class Falcao extends Node2D:
	const VOO := 0.36
	const SAIDA := 0.5
	var alvo: Node2D
	var cfg := {}
	var _de := Vector2.ZERO
	var _para := Vector2.ZERO
	var _t := 0.0
	var _pousou := false
	var _spr: Sprite2D

	static func soltar(cena: Node, de: Vector2, alvo_: Node2D, cfg_: Dictionary) -> void:
		var f := Falcao.new()
		f.alvo = alvo_
		f.cfg = cfg_
		f._de = de
		f._para = alvo_.global_position
		cena.add_child(f)
		f.global_position = de

	func _ready() -> void:
		z_index = 5
		Vfx.registrar_animado(self)
		_spr = F.sprite("falcao_a", 2.6)
		_spr.modulate = Color(1.0, 0.95, 0.8, 0.95)
		add_child(_spr)

	func _physics_process(delta: float) -> void:
		_t += delta
		_spr.texture = F.tex("falcao_a" if int(_t * 14.0) % 2 == 0 else "falcao_b")
		queue_redraw()
		if not _pousou:
			if is_instance_valid(alvo) and alvo.is_in_group("hurtable"):
				_para = alvo.global_position
			var f := clampf(_t / VOO, 0.0, 1.0)
			var fim := _para + Vector2(0, -40.0)
			var meio := _de.lerp(fim, 0.5) + Vector2(0, 60.0)   # mergulho: afunda antes de chegar
			var p := _de.lerp(meio, f).lerp(meio.lerp(fim, f), f)
			_spr.flip_h = fim.x < _de.x
			global_position = p
			if f >= 1.0:
				_pousar()
			return
		var k := (_t - VOO) / SAIDA
		global_position += Vector2((-1.0 if _spr.flip_h else 1.0) * 260.0, -520.0) * delta
		_spr.modulate.a = 0.95 * (1.0 - k)
		if k >= 1.0:
			queue_free()

	func _pousar() -> void:
		_pousou = true
		if not (is_instance_valid(alvo) and alvo.is_in_group("hurtable")):
			return
		if float(cfg.get("dano", 0.0)) > 0.0:
			alvo.take_damage(cfg["dano"], _de)
		if not (is_instance_valid(alvo) and alvo.is_in_group("hurtable") and alvo.has_method("aplicar_status")):
			return
		alvo.aplicar_status("marca", cfg["dur"], cfg["valor"])
		for c in alvo.get_children():
			if c is Marca:
				c.queue_free()
		var m := Marca.new()
		m.cfg = cfg
		m.resta = cfg["dur"]
		alvo.add_child(m)
		Feel.impacto(get_parent(), _para + Vector2(0, -40), OURO, Vector2.ZERO, 1.4)

	func _draw() -> void:
		if not _pousou:   # risco dourado do mergulho
			var v := (_para + Vector2(0, -40.0) - _de).normalized()
			draw_line(-v * 110.0, -v * 24.0, Color(OURO, 0.55), 8.0)

## Marca do Caçador sobre o inimigo: retículo dourado girando acima da cabeça enquanto dura. Se o marcado morre com
## tempo sobrando, o falcão leva a marca ao inimigo mais perto (até `raio`), com o tempo que restava.
class Marca extends Node2D:
	var cfg := {}
	var resta := 6.0
	var _t := 0.0
	var _passou := false

	func _ready() -> void:
		z_index = 3
		Vfx.registrar_status(self)
		var dono := get_parent()
		position = Vector2(0, (dono.topo_visual() if dono.has_method("topo_visual") else -90.0) - 14.0)

	func _physics_process(delta: float) -> void:
		_t += delta
		resta -= delta
		var dono := get_parent()
		if not _passou and not dono.is_in_group("hurtable"):   # o marcado morreu
			_passou = true
			var raio := float(cfg.get("raio", 0.0))
			var prox: Node2D = Alvos.centro_mais_proximo(get_tree(), dono.global_position, raio, "aplicar_status", [dono]) if raio > 0.0 and resta > 0.4 else null
			if prox != null:
				var c := cfg.duplicate()
				c["dur"] = resta
				c["dano"] = 0.0
				Falcao.soltar(dono.get_parent(), global_position, prox, c)
			queue_free()
			return
		if resta <= 0.0:
			queue_free()
			return
		queue_redraw()

	func _draw() -> void:
		var pisca := 1.0 if resta > 1.0 or int(resta * 10.0) % 2 == 0 else 0.35
		var entra := 1.0 - pow(1.0 - clampf(_t / 0.2, 0.0, 1.0), 3.0)
		var r := lerpf(60.0, 22.0, entra)
		for i in 4:
			var a := _t * 2.0 + TAU * float(i) / 4.0
			var p := Vector2.from_angle(a) * r
			draw_colored_polygon(PackedVector2Array([p, p + Vector2.from_angle(a + 0.5) * 16.0, p + Vector2.from_angle(a - 0.5) * 16.0]), Color(OURO, pisca))
		draw_colored_polygon(PackedVector2Array([Vector2(0, -10), Vector2(7.5, 0), Vector2(0, 10), Vector2(-7.5, 0)]), Color(1.0, 0.3, 0.2, pisca))
		draw_arc(Vector2.ZERO, r + 7.0, 0.0, TAU, 16, Color(OURO, 0.5 * pisca), 3.0)
