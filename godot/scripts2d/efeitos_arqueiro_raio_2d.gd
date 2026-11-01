extends RefCounted
## Árvore de Raio do Arqueiro (doc 32_raio): Flecha Elétrica, Raio Encadeado, Tornado de Tempestade e Arauto do Trovão.
## Mesmo contrato de efeitos_arqueiro_2d.gd: executar(efeito, jogador, def, nivel, mira) -> bool. Números só no CSV (`def`).
## A integradora delega daqui por `match` (efeitos "flecha_eletrica", "raio_encadeado", "tornado") e chama
## `ao_morrer(inimigo)` na morte do inimigo para o Arauto do Trovão. Folhas em res://art2d/fx/raio/.

const PASTA := "res://art2d/fx/raio/"
const COR := Color(0.55, 0.8, 1.0)
const ATRASO_TORNADO := 0.55   # só tempo visual da flecha subindo e caindo (não é balanceamento)

const EFEITOS := ["flecha_eletrica", "raio_encadeado", "tornado"]

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
			sp.preparar(_tex("flecha_eletrica_proj"), 6, 14.0, true, Vector2(0, -30))
			f.add_child(sp)
		"raio_encadeado":
			var alvo := _mais_proximo(jogador, jogador.global_position, dir, def.get("alcance", 600.0), [])
			if alvo == null:
				return false   # sem alvo: não gasta a recarga
			_encadear(jogador, alvo, def)
		"tornado":
			var p := _ponto(jogador, dir, def.get("alcance", 600.0))
			var cena: Node = jogador.get_parent()
			var marca := Quadros.new()   # a flecha cai do alto: coluna de raio curta sobre o ponto
			marca.preparar(_tex("raio_coluna"), 6, 14.0, false, Vector2(0, -96))
			marca.global_position = p
			cena.add_child(marca)
			jogador.get_tree().create_timer(ATRASO_TORNADO).timeout.connect(func():
				if is_instance_valid(cena) and cena.is_inside_tree():
					var t := Tornado.new()
					t.setup(p, def, jogador.stats["arrow_damage"])
					cena.add_child(t))
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
	var aura := Quadros.new()
	aura.name = "AuraArauto"
	aura.preparar(_tex("arauto_trovao_aura"), 6, 10.0, true, Vector2(0, -20))
	aura.modulate.a = 0.7
	jogador.add_child(aura)

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
