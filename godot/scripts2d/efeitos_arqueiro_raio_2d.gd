extends RefCounted
## Árvore de Raio do Arqueiro (doc 32_raio): Flecha Elétrica, Raio Encadeado, Tornado de Tempestade e Arauto do Trovão.
## Mesmo contrato de efeitos_arqueiro_2d.gd: executar(efeito, jogador, def, nivel, mira) -> bool. Números só no CSV (`def`).
## A integradora delega daqui por `match` (efeitos "flecha_eletrica", "raio_encadeado", "tornado") e chama
## `ao_morrer(inimigo)` na morte do inimigo para o Arauto do Trovão. Folhas em res://art2d/fx/raio/.

const Vfx = preload("res://scripts2d/vfx_2d.gd")
const Placeholders = preload("res://scripts2d/placeholders.gd")
const PASTA := "res://art2d/fx/raio/"
const COR := Color(0.55, 0.8, 1.0)
const ALTURA_TORNADO := 380.0   # altura visual da flecha que sobe antes de cair como tornado
const ATRASO_TORNADO := 0.55   # só tempo visual da flecha subindo e caindo (não é balanceamento)

const ALTURA_HASTE := 240.0     # altura visual da flecha que vira haste (doc 36: Haste Elétrica)
const VOO_HASTE := 0.45
const EFEITOS := ["flecha_eletrica", "raio_encadeado", "tornado", "haste_eletrica"]

static func executar(efeito: String, jogador: Node2D, def: Dictionary, _nivel: int, mira: Vector2) -> bool:
	if jogador == null or not jogador.is_inside_tree() or jogador.esta_morto():
		return false
	var dir: Vector2 = mira.normalized() if mira != Vector2.ZERO else jogador.mira_atual()
	var dano: float = def.get("dano", 1.0)
	match efeito:
		"flecha_eletrica":
			var f = jogador.lancar_flecha(dir, dano, 0, 1.0, def)
			f.cor_fx = COR
			var dur: float = def.get("duracao", 3.0)
			var val: float = def.get("valor", 0.15)
			f.body_entered.connect(func(corpo):
				if is_instance_valid(corpo) and corpo.has_method("aplicar_status") and corpo.has_method("take_damage"):
					aplicar_choque(corpo, dur, val))
			var sp := Quadros.new()
			sp.preparar(_tex("flecha_eletrica_proj"), 6, 14.0, true, Vector2.ZERO)
			f.vis.add_child(sp)
		"raio_encadeado":
			var alvo := _mais_proximo(jogador, jogador.global_position, dir, def.get("alcance", 600.0), [])
			if alvo == null:
				return false   # sem alvo: não gasta a recarga
			_encadear(jogador, alvo, def)
		"tornado":
			var p := _ponto(jogador, dir, def.get("alcance", 600.0))
			var cena: Node = jogador.get_parent()
			# A flecha sai do arco, sobe em arco (sombra no chão, aviso no ponto de queda) e cai: no chão vira o tornado.
			var boca: Dictionary = jogador.boca_do_arco(dir) if jogador.has_method("boca_do_arco") \
					else {"chao": jogador.global_position, "altura": 50.0}
			var corpo := Node2D.new()
			var sp := Quadros.new()
			sp.preparar(_tex("flecha_eletrica_proj"), 6, 14.0, true, Vector2.ZERO)
			if sp.tex == null:
				var seta := Sprite2D.new()
				seta.texture = load("res://art2d/fx/arrow.png") if ResourceLoader.exists("res://art2d/fx/arrow.png") else Placeholders.seta(Vector2i(64, 16))
				corpo.add_child(seta)
			corpo.add_child(sp)
			Vfx.flash_boca(cena, boca["chao"] + Vector2(0, -boca["altura"]), dir)
			Vfx.arco(cena, boca["chao"], boca["altura"], p, ALTURA_TORNADO, ATRASO_TORNADO, corpo, COR, def.get("raio", 150.0),
				func(ponto: Vector2):
					if not is_instance_valid(cena) or not cena.is_inside_tree():
						return
					var marca := Quadros.new()   # coluna de raio curta no ponto em que a flecha caiu
					marca.preparar(_tex("raio_coluna"), 6, 14.0, false, Vector2(0, -96))
					marca.global_position = ponto
					cena.add_child(marca)
					var t := Tornado.new()
					t.setup(ponto, def, jogador.stats["arrow_damage"])
					cena.add_child(t), true)
		"haste_eletrica":
			# Doc 36 (família zona): a flecha voa em arco e FINCA no ponto; vira um para-raios que descarrega nos vizinhos.
			var p := _ponto(jogador, dir, def.get("alcance", 600.0))
			var cena: Node = jogador.get_parent()
			var boca: Dictionary = jogador.boca_do_arco(dir) if jogador.has_method("boca_do_arco") \
					else {"chao": jogador.global_position, "altura": 50.0}
			var corpo := Node2D.new()
			var seta := Sprite2D.new()
			seta.texture = load("res://art2d/fx/arrow.png") if ResourceLoader.exists("res://art2d/fx/arrow.png") else Placeholders.seta(Vector2i(64, 16))
			corpo.add_child(seta)
			var sp := Quadros.new()
			sp.preparar(_tex("flecha_eletrica_proj"), 6, 14.0, true, Vector2.ZERO)
			corpo.add_child(sp)
			Vfx.flash_boca(cena, boca["chao"] + Vector2(0, -boca["altura"]), dir)
			Vfx.arco(cena, boca["chao"], boca["altura"], p, ALTURA_HASTE, VOO_HASTE, corpo, COR, 0.0,
				func(ponto: Vector2):
					if not is_instance_valid(cena) or not cena.is_inside_tree() or not is_instance_valid(jogador):
						return
					var h := Haste.new()
					h.setup(ponto, def, jogador.stats["arrow_damage"], jogador)
					cena.add_child(h), true)
		_:
			push_error("Efeito de raio desconhecido: " + efeito)
			return false
	return true

## Choque: o inimigo recebe mais dano por pouco tempo (`valor` = fração extra) e ganha o overlay. O status "choque" é
## reconhecido pelo enemy_2d depois da integração; até lá fica só como marca visual (tem_status("choque")).
static func aplicar_choque(inimigo: Node2D, dur: float, valor: float) -> void:
	inimigo.aplicar_status("choque", dur, valor)
	if inimigo.has_node("OverlayChoque"):
		inimigo.get_node("OverlayChoque").reiniciar(dur)
		return
	var ov := Overlay.new()
	ov.name = "OverlayChoque"
	ov.dur = dur
	inimigo.add_child(ov)

## Forma "bifurcado" (passivo Raio Bifurcado): depois do primeiro alvo a corrente se divide em dois ramos, cada um
## com os saltos restantes, sem repetir alvo.
static func _encadear(jogador: Node2D, primeiro: Node2D, def: Dictionary) -> void:
	var saltos := int(def.get("qtd", 4))
	var visitados: Array = []
	var origem: Vector2 = jogador.global_position + Vector2(0, -30)
	_cadeia(jogador, primeiro, origem, def, saltos, 0, visitados)
	if def.get("forma", "") == "bifurcado" and is_instance_valid(primeiro) and primeiro.is_inside_tree():
		var raio: float = def.get("raio", 220.0)
		var ponto: Vector2 = primeiro.global_position + Vector2(0, -24)
		var outro := _mais_proximo(jogador, primeiro.global_position, Vector2.ZERO, raio, visitados)
		_cadeia(jogador, outro, ponto, def, saltos - 1, 1, visitados)

static func _cadeia(jogador: Node2D, primeiro: Node2D, origem: Vector2, def: Dictionary, saltos: int, salto_inicial: int, visitados: Array) -> void:
	var raio: float = def.get("raio", 220.0)      # distância máxima entre um alvo e o próximo
	var queda: float = def.get("valor", 0.2)      # fração de dano perdida a cada salto
	var dano: float = jogador.stats["arrow_damage"] * def.get("dano", 1.0)
	var dur_choque: float = def.get("duracao", 3.0)
	var cena: Node = jogador.get_parent()
	var atual: Node2D = primeiro
	for i in saltos:
		if atual == null:
			break
		visitados.append(atual)
		var ponto: Vector2 = atual.global_position + Vector2(0, -24)
		_arco(cena, origem, ponto)
		var d := dano * pow(1.0 - clampf(queda, 0.0, 0.9), i + salto_inicial)
		atual.take_damage(d, origem)
		if is_instance_valid(atual) and atual.has_method("aplicar_status"):
			aplicar_choque(atual, dur_choque, 0.15)
		var imp := Quadros.new()
		imp.preparar(_tex("raio_impacto"), 8, 24.0, false, Vector2.ZERO)
		imp.global_position = ponto
		cena.add_child(imp)
		origem = ponto
		atual = _mais_proximo(jogador, atual.global_position, Vector2.ZERO, raio, visitados)

static func _arco(cena: Node, a: Vector2, b: Vector2) -> void:
	var arco := Arco.new()
	arco.ligar(_tex("raio_arco"), a, b)
	cena.add_child(arco)

## Segmento de raio entre dois pontos, para outros módulos (Eco do Trovão, Haste). `forca` < 1 = salto secundário mais fraco.
static func arco_entre(cena: Node, a: Vector2, b: Vector2, forca := 1.0) -> void:
	if cena == null or not cena.is_inside_tree():
		return
	var arco := Arco.new()
	arco.ligar(_tex("raio_arco"), a, b)
	arco.modulate.a = clampf(forca, 0.2, 1.0)
	cena.add_child(arco)

## Inimigo vivo mais perto de `de` dentro de `alcance`, fora de `excluir` (sem cone de mira).
static func mais_proximo_de(jogador: Node2D, de: Vector2, alcance: float, excluir: Array) -> Node2D:
	return _mais_proximo(jogador, de, Vector2.ZERO, alcance, excluir)

## Arauto do Trovão: chamado quando um inimigo morre. Se estava em choque e o jogador tem o Arauto ativo
## (meta "arauto_trovao" = def da gema), cai um raio e fere os vizinhos.
static func ao_morrer(inimigo: Node2D) -> void:
	if inimigo == null or not inimigo.is_inside_tree() or not inimigo.has_method("tem_status") or not inimigo.tem_status("choque"):
		return
	var tree := inimigo.get_tree()
	for j in tree.get_nodes_in_group("arqueiro"):
		if j.has_meta("arauto_trovao"):
			var def: Dictionary = j.get_meta("arauto_trovao")
			var raio: float = def.get("raio", 180.0)
			var dano: float = j.stats["arrow_damage"] * def.get("dano", 1.0)
			var pos: Vector2 = inimigo.global_position
			var cena: Node = inimigo.get_parent()
			var col := Quadros.new()
			col.preparar(_tex("raio_coluna"), 6, 18.0, false, Vector2(0, -96))
			col.global_position = pos
			cena.add_child(col)
			var imp := Quadros.new()
			imp.preparar(_tex("raio_impacto"), 8, 24.0, false, Vector2.ZERO)
			imp.global_position = pos
			cena.add_child(imp)
			for n in tree.get_nodes_in_group("hurtable"):
				if n != inimigo and n is Node2D and n.global_position.distance_to(pos) <= raio:
					n.take_damage(dano, pos)
					if is_instance_valid(n) and n.has_method("aplicar_status"):
						aplicar_choque(n, def.get("duracao", 3.0), 0.15)

## Liga o Arauto do Trovão (gema equipada): guarda a linha do CSV no jogador e põe a aura. Desliga com def vazio.
static func ativar_arauto(jogador: Node2D, def: Dictionary) -> void:
	if jogador.has_node("AuraArauto"):
		jogador.get_node("AuraArauto").queue_free()
	if def.is_empty():
		jogador.remove_meta("arauto_trovao")
		return
	jogador.set_meta("arauto_trovao", def)
	var aura := Quadros.new()   # aura na camada C1 (elipse no chão, atrás do arqueiro; regra única em vfx_2d.gd)
	aura.preparar(_tex("arauto_trovao_aura"), 6, 10.0, true, Vector2.ZERO)
	var natural: float = float(aura.tex.get_width()) / 6.0 if aura.tex != null else 96.0
	Vfx.aura_c1(jogador, aura, natural, "AuraArauto")

# ---- ajudas ----
static func _tex(nome: String) -> Texture2D:
	var c := PASTA + nome + ".png"
	return load(c) if ResourceLoader.exists(c) else null

static func _ponto(jogador: Node2D, dir: Vector2, alcance: float) -> Vector2:
	if jogador.has_method("tem_alvo_auto") and jogador.tem_alvo_auto():
		return jogador.ponto_mira(alcance)
	return jogador.global_position + dir * 0.7 * alcance

## Inimigo vivo mais perto de `de` (dentro de `alcance`); com `dir` != 0 só aceita quem está até 60° da mira.
static func _mais_proximo(jogador: Node2D, de: Vector2, dir: Vector2, alcance: float, excluir: Array) -> Node2D:
	var melhor: Node2D = null
	var melhor_d := alcance
	for n in jogador.get_tree().get_nodes_in_group("hurtable"):
		if n is Node2D and n.has_method("take_damage") and not excluir.has(n):
			var v: Vector2 = n.global_position - de
			if v.length() <= melhor_d and (dir == Vector2.ZERO or absf(dir.angle_to(v)) <= deg_to_rad(60.0)):
				melhor_d = v.length()
				melhor = n
	return melhor

## Folha em linha (quadros quadrados ou largos iguais), anima por tempo; `loop` falso = some no último quadro.
class Quadros extends Node2D:
	var tex: Texture2D
	var n := 1
	var fps := 12.0
	var loop := false
	var desloc := Vector2.ZERO
	var _t := 0.0
	func preparar(t: Texture2D, quadros: int, f: float, em_loop: bool, d: Vector2) -> void:
		tex = t; n = maxi(quadros, 1); fps = f; loop = em_loop; desloc = d
		material = preload("res://scripts2d/feel_2d.gd").aditivo()
	func _process(delta: float) -> void:
		_t += delta
		if not loop and _t * fps >= n:
			queue_free()
			return
		queue_redraw()
	func _draw() -> void:
		if tex == null:
			return
		var qi := int(_t * fps) % n
		var w := float(tex.get_width()) / n
		var h := float(tex.get_height())
		draw_texture_rect_region(tex, Rect2(desloc - Vector2(w, h) * 0.5, Vector2(w, h)), Rect2(qi * w, 0, w, h))

## Segmento de raio entre dois pontos (a folha tem o raio na horizontal, ponta a ponta).
class Arco extends Node2D:
	var tex: Texture2D
	var a := Vector2.ZERO
	var b := Vector2.ZERO
	var _t := 0.0
	func ligar(t: Texture2D, de: Vector2, para: Vector2) -> void:
		tex = t; a = de; b = para
		global_position = de
		material = preload("res://scripts2d/feel_2d.gd").aditivo()
	func _process(delta: float) -> void:
		_t += delta
		if _t >= 0.22:
			queue_free()
			return
		queue_redraw()
	func _draw() -> void:
		var v := b - a
		draw_set_transform(Vector2.ZERO, v.angle(), Vector2.ONE)
		if tex == null:
			draw_line(Vector2.ZERO, Vector2(v.length(), 0), Color(0.7, 0.9, 1.0), 3.0)
			return
		var w := float(tex.get_width()) / 4.0
		var h := float(tex.get_height())
		draw_texture_rect_region(tex, Rect2(Vector2(0, -h * 0.5), Vector2(v.length(), h)), Rect2(int(_t * 30.0) % 4 * w, 0, w, h))

## Faíscas em cima do inimigo enquanto durar o choque.
class Overlay extends Node2D:
	var dur := 3.0
	var tex: Texture2D
	var _t := 0.0
	func _ready() -> void:
		z_index = 5
		position = Vector2(0, -24)
		material = preload("res://scripts2d/feel_2d.gd").aditivo()
		var c := "res://art2d/fx/raio/choque_overlay.png"
		tex = load(c) if ResourceLoader.exists(c) else null
	func reiniciar(d: float) -> void:
		dur = d
		_t = 0.0
	func _process(delta: float) -> void:
		_t += delta
		if _t >= dur:
			queue_free()
			return
		queue_redraw()
	func _draw() -> void:
		if tex == null:
			return
		var w := float(tex.get_width()) / 6.0
		var h := float(tex.get_height())
		draw_texture_rect_region(tex, Rect2(Vector2(-w, -h) * 0.5, Vector2(w, h)), Rect2(int(_t * 14.0) % 6 * w, 0, w, h))

## Tornado: puxa os inimigos para o centro e fere em pulsos por `duracao` s. Números vêm do CSV (def).
## Forma "errante" (passivo Tornado Errante): o tornado anda atrás do inimigo mais próximo (`valor` px/s).
class Tornado extends Node2D:
	var raio := 150.0
	var duracao := 4.0
	var dano := 0.0
	var puxa := 90.0      # px/s
	var pulso := 0.5
	var errante := false
	var tex: Texture2D
	var _t := 0.0
	var _acc := 0.0
	func setup(pos: Vector2, def: Dictionary, base_dano: float) -> void:
		global_position = pos
		raio = def.get("raio", 150.0)
		duracao = def.get("duracao", 4.0)
		puxa = def.get("valor", 90.0)
		errante = def.get("forma", "") == "errante"
		dano = base_dano * def.get("dano", 1.0)
		var c := "res://art2d/fx/raio/tornado_tempestade.png"
		tex = load(c) if ResourceLoader.exists(c) else null
		material = preload("res://scripts2d/feel_2d.gd").aditivo()
		z_index = 3
	func _physics_process(delta: float) -> void:
		_t += delta
		_acc += delta
		if errante:
			var alvo: Node2D = null
			var melhor := INF
			for n in get_tree().get_nodes_in_group("hurtable"):
				if n is Node2D and n.global_position.distance_squared_to(global_position) < melhor:
					melhor = n.global_position.distance_squared_to(global_position)
					alvo = n
			if alvo != null and sqrt(melhor) > raio * 0.3:
				global_position += (alvo.global_position - global_position).normalized() * puxa * delta
		for n in get_tree().get_nodes_in_group("hurtable"):
			if n is Node2D and n.global_position.distance_to(global_position) <= raio:
				var v: Vector2 = global_position - n.global_position
				if v.length() > 8.0:
					n.global_position += v.normalized() * minf(puxa * delta, v.length())
		if _acc >= pulso:
			_acc = 0.0
			for n in get_tree().get_nodes_in_group("hurtable"):
				if n is Node2D and n.has_method("take_damage") and n.global_position.distance_to(global_position) <= raio:
					n.take_damage(dano, global_position)
		if _t >= duracao:
			queue_free()
			return
		queue_redraw()
	func _draw() -> void:
		draw_arc(Vector2.ZERO, raio, 0.0, TAU, 48, Color(0.5, 0.75, 1.0, 0.35), 2.0)
		if tex == null:
			return
		var w := float(tex.get_width()) / 8.0
		var h := float(tex.get_height())
		var esc := raio / 60.0
		var qi := int(_t * 12.0) % 8
		draw_texture_rect_region(tex, Rect2(Vector2(-w * 0.5, -h + 12.0) * esc, Vector2(w, h) * esc), Rect2(qi * w, 0, w, h))

## Haste Elétrica (doc 36 seção 4): flecha fincada no chão que vira para-raios. A cada `valor` s descarrega em `qtd`
## inimigos a até `raio` px (arco de raio até cada um, dano, choque), por `duracao` s. Um nó desenha o glifo no chão (C0)
## e um filho desenha a haste e as faíscas (C4). Antes de cada descarga o anel do glifo encolhe (telégrafo de leitura).
class Haste extends Node2D:
	const PAL := [Color("F4FBFF"), Color("5FA8FF"), Color("14284F")]
	var raio := 220.0
	var duracao := 5.0
	var intervalo := 0.4
	var alvos := 2
	var dano := 0.0
	var dur_choque := 2.0
	var jogador: Node2D
	var _t := 0.0
	var _acc := 0.0
	var _pulso := 0.0      # 1 logo depois da descarga, decai
	var _corpo: Node2D
	var _rng := RandomNumberGenerator.new()
	var _faiscas: Array = []   # [ang, comp]

	func setup(pos: Vector2, def: Dictionary, base_dano: float, j: Node2D) -> void:
		global_position = pos
		raio = def.get("raio", 220.0)
		duracao = def.get("duracao", 5.0)
		intervalo = maxf(def.get("valor", 0.4), 0.1)
		alvos = maxi(1, int(def.get("qtd", 2)))
		dano = base_dano * def.get("dano", 0.8)
		dur_choque = 2.0
		jogador = j
		z_index = -1
		_rng.randomize()

	func _ready() -> void:
		Vfx.registrar_animado(self)
		_corpo = HasteCorpo.new()
		_corpo.dona = self
		_corpo.z_index = 5   # relativo: -1 + 5 = 4 (C4)
		add_child(_corpo)
		Vfx.anel_entrada(get_parent(), global_position, raio, PAL[1])
		var imp := Quadros.new()
		imp.preparar(load(PASTA + "raio_impacto.png") if ResourceLoader.exists(PASTA + "raio_impacto.png") else null, 8, 24.0, false, Vector2(0, -8))
		imp.global_position = global_position
		get_parent().add_child(imp)

	func _physics_process(delta: float) -> void:
		_t += delta
		_acc += delta
		_pulso = maxf(0.0, _pulso - delta * 3.0)
		if _acc >= intervalo:
			_acc = 0.0
			_descarregar()
		queue_redraw()
		_corpo.queue_redraw()
		if _t >= duracao:
			queue_free()

	func _descarregar() -> void:
		if jogador == null or not is_instance_valid(jogador):
			return
		var cena: Node = get_parent()
		var visitados: Array = []
		var ponta: Vector2 = global_position + Vector2(0, -88)
		for i in alvos:
			var n: Node2D = _mais_perto(visitados)
			if n == null:
				break
			visitados.append(n)
			var alvo: Vector2 = n.global_position + Vector2(0, -24)
			var arco := Arco.new()
			arco.ligar(load(PASTA + "raio_arco.png") if ResourceLoader.exists(PASTA + "raio_arco.png") else null, ponta, alvo)
			arco.modulate.a = 1.0 if i == 0 else 0.6   # hierarquia: só o 1º alvo com brilho cheio
			cena.add_child(arco)
			n.take_damage(dano, global_position)
			if is_instance_valid(n) and n.has_method("aplicar_status"):
				n.aplicar_status("choque", dur_choque, 0.15)
			if i == 0 and not Vfx.lotado(get_tree()):
				var imp := Quadros.new()
				imp.preparar(load(PASTA + "raio_impacto.png") if ResourceLoader.exists(PASTA + "raio_impacto.png") else null, 8, 24.0, false, Vector2.ZERO)
				imp.global_position = alvo
				cena.add_child(imp)
		if not visitados.is_empty():
			_pulso = 1.0
			_faiscas.clear()
			for i in 6:
				_faiscas.append([_rng.randf() * TAU, _rng.randf_range(10.0, 24.0)])

	func _mais_perto(excluir: Array) -> Node2D:
		var melhor: Node2D = null
		var melhor_d := raio
		for n in get_tree().get_nodes_in_group("hurtable"):
			if n is Node2D and n.has_method("take_damage") and not excluir.has(n):
				var d: float = n.global_position.distance_to(global_position)
				if d <= melhor_d:
					melhor_d = d
					melhor = n
		return melhor

	## Glifo no chão (C0): área real (raio do CSV) tênue, anel interno que encolhe até a próxima descarga e acende nela.
	func _draw() -> void:
		var apaga: float = Vfx.fade_zona(_t, duracao)
		var carga: float = clampf(_acc / intervalo, 0.0, 1.0)
		draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.55))
		draw_arc(Vector2.ZERO, raio, 0.0, TAU, 56, Color(PAL[2], 0.35 * apaga), 4.0)
		draw_arc(Vector2.ZERO, raio, 0.0, TAU, 56, Color(PAL[1], (0.18 + 0.35 * _pulso) * apaga), 2.0)
		var r_in := lerpf(46.0, 24.0, carga) + 12.0 * _pulso
		draw_circle(Vector2.ZERO, r_in * 1.3, Color(PAL[1], 0.14 * apaga))
		draw_arc(Vector2.ZERO, r_in, 0.0, TAU, 32, Color(PAL[2], 0.8 * apaga), 4.0)
		draw_arc(Vector2.ZERO, r_in, 0.0, TAU, 32, Color(PAL[1], (0.7 + 0.3 * _pulso) * apaga), 2.2)
		for i in 6:
			var a := _t * 1.2 + TAU * i / 6.0
			var p1 := Vector2.from_angle(a) * (r_in - 4.0)
			var p2 := Vector2.from_angle(a) * (r_in + 10.0 + 6.0 * _pulso)
			draw_line(p1, p2, Color(PAL[0], (0.6 + 0.4 * _pulso) * apaga), 2.2)

## Desenho da haste (filho da Haste, C4): flecha fincada com contorno escuro, núcleo claro, cristal na ponta,
## halo que pulsa e faíscas curtas depois da descarga. Só aparência.
class HasteCorpo extends Node2D:
	var dona: Node2D
	func _draw() -> void:
		if dona == null:
			return
		var pal: Array = dona.PAL
		var apaga: float = Vfx.fade_zona(dona._t, dona.duracao)
		var pulso: float = dona._pulso
		var base := Vector2(0, -4)
		var ponta := Vector2(0, -88)
		var halo_r := 16.0 + 12.0 * pulso + 2.0 * sin(dona._t * 9.0)
		draw_circle(ponta, halo_r * 1.8, Color(pal[1], 0.10 * apaga))
		draw_circle(ponta, halo_r, Color(pal[1], (0.22 + 0.25 * pulso) * apaga))
		# haste: contorno, corpo e fio de luz (espessura variável: mais grossa embaixo)
		draw_line(base, ponta, Color(pal[2], 0.95 * apaga), 9.0)
		draw_line(base, ponta + Vector2(0, 4), Color(pal[1], 0.9 * apaga), 5.0)
		draw_line(base + Vector2(0, -12), ponta + Vector2(0, 8), Color(pal[0], (0.7 + 0.3 * pulso) * apaga), 2.0)
		# empenas da flecha
		for lado in [-1.0, 1.0]:
			var pe := base + Vector2(0, -6)
			draw_line(pe, pe + Vector2(9.0 * lado, 10.0), Color(pal[2], 0.9 * apaga), 3.5)
			draw_line(pe, pe + Vector2(9.0 * lado, 10.0), Color(pal[1], 0.8 * apaga), 1.6)
		# cristal da ponta (losango) com miolo branco
		var c := PackedVector2Array([ponta + Vector2(0, -18), ponta + Vector2(8, 0), ponta + Vector2(0, 12), ponta + Vector2(-8, 0)])
		draw_colored_polygon(c, Color(pal[1], apaga))
		draw_polyline(c + PackedVector2Array([c[0]]), Color(pal[2], apaga), 2.0)
		draw_line(c[0], c[2], Color(pal[0], apaga), 2.0)
		# faíscas depois da descarga: tracinhos que saem da ponta e somem
		for f in dona._faiscas:
			var d := Vector2.from_angle(f[0])
			var a0: Vector2 = ponta + d * 6.0
			var a1: Vector2 = ponta + d * (6.0 + float(f[1]) * (0.4 + 0.6 * pulso))
			draw_line(a0, a1, Color(pal[1], 0.8 * pulso * apaga), 2.2)
			draw_line(a0, a1, Color(pal[0], pulso * apaga), 1.0)
