extends RefCounted
## Aparência compartilhada das magias do mago: paletas por elemento, sprites pequenos de projétil gerados por código
## (pixel art, uma vez por forma e elemento), estouro de pixels na grade do mundo e as explosões por elemento
## (folhas que o jogo já tem). Só visual: nenhum número de balanceamento aqui.

const Px = preload("res://scripts2d/fx_pixel_2d.gd")
const Vfx = preload("res://scripts2d/vfx_2d.gd")
const GeloFx = preload("res://scripts2d/efeitos_arqueiro_gelo_2d.gd")

const GRADE := 2.5
## [contorno, escuro, corpo, claro, brilho]
const PALETAS := {
	"": [Color("1c0f3a"), Color("5a2fb0"), Color("9a5cf0"), Color("d2b0ff"), Color("ffffff")],
	"fogo": [Color("3a0c05"), Color("b02a0c"), Color("ff7a1f"), Color("ffd060"), Color("fff6c8")],
	"gelo": [Color("0c2848"), Color("2f6fb5"), Color("7fd3f2"), Color("d6f4ff"), Color("ffffff")],
	"raio": [Color("101c4a"), Color("3058d0"), Color("7fb0ff"), Color("e0ecff"), Color("ffffff")],
	"veneno": [Color("0c2a0a"), Color("2f7a14"), Color("6fd12b"), Color("c8f56a"), Color("f4ffd0")],
}

static var _tex := {}

static func paleta(elemento: String) -> Array:
	return PALETAS.get(elemento, PALETAS[""])

static func cor(elemento: String) -> Color:
	return paleta(elemento)[2]

## Sprite do projétil apontando para a direita. Formas: orbe, chama, lasca, bolha e faisca.
static func textura_projetil(forma: String, elemento: String) -> Texture2D:
	var chave := forma + "|" + elemento
	if _tex.has(chave):
		return _tex[chave]
	var tam := Vector2i(11, 11)
	if forma == "chama" or forma == "lasca":
		tam = Vector2i(17, 9)
	elif forma == "bolha":
		tam = Vector2i(13, 13)
	var nivel := []   # 0 vazio, 1 escuro, 2 corpo, 3 claro, 4 brilho
	for y in tam.y:
		var linha := []
		for x in tam.x:
			linha.append(_nivel(forma, Vector2(x, y), Vector2(tam)))
		nivel.append(linha)
	var pal := paleta(elemento)
	var img := Image.create(tam.x, tam.y, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	for y in tam.y:
		for x in tam.x:
			var n: int = nivel[y][x]
			if n > 0:
				var c: Color = pal[n]
				if forma == "bolha" and n == 2:
					c.a = 0.6   # miolo da bolha translúcido
				img.set_pixel(x, y, c)
			elif _vizinho_cheio(nivel, x, y, tam):
				img.set_pixel(x, y, pal[0])
	_tex[chave] = ImageTexture.create_from_image(img)
	return _tex[chave]

static func _vizinho_cheio(nivel: Array, x: int, y: int, tam: Vector2i) -> bool:
	for d in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
		var p: Vector2i = Vector2i(x, y) + d
		if p.x >= 0 and p.y >= 0 and p.x < tam.x and p.y < tam.y and int(nivel[p.y][p.x]) > 0:
			return true
	return false

static func _nivel(forma: String, p: Vector2, tam: Vector2) -> int:
	var c := (tam - Vector2.ONE) * 0.5
	match forma:
		"chama":   # cometa: cabeça redonda à direita, cauda que afina para a esquerda
			var cab := Vector2(tam.x - 5.0, c.y)
			var d := p.distance_to(cab)
			if d <= 1.2:
				return 4
			if d <= 2.3:
				return 3
			if d <= 3.4:
				return 2
			if p.x < cab.x:
				var u := p.x / cab.x
				var meia := 3.2 * pow(u, 1.4)
				var dy := absf(p.y - c.y)
				if dy <= meia * 0.4 and u > 0.45:
					return 3
				if dy <= meia:
					return 2 if u > 0.3 else 1
			return 0
		"lasca":   # losango alongado com faceta clara em cima e fio de brilho
			var k := absf(p.x - c.x) / (c.x - 0.5) + absf(p.y - c.y) / (c.y - 0.5)
			if k > 1.0:
				return 0
			if is_equal_approx(p.y, c.y) and p.x > c.x - 1.0:
				return 4
			if p.y < c.y:
				return 3
			return 2 if p.x > c.x - 3.0 else 1
		"bolha":   # casca fina, miolo translúcido, reflexo no alto à esquerda
			var d := p.distance_to(c)
			if d > 5.6:
				return 0
			if p.distance_to(c + Vector2(-2.0, -2.0)) <= 1.1:
				return 4
			if d > 4.5:
				return 3 if p.y < c.y else 1
			return 2
		"faisca":   # miolo branco com quatro pontas em cruz e quatro curtas na diagonal
			var v := p - c
			var d := v.length()
			if d <= 1.5:
				return 4
			if (absf(v.x) < 0.6 or absf(v.y) < 0.6) and d <= 5.0:
				return 3 if d <= 3.0 else 2
			if is_equal_approx(absf(v.x), absf(v.y)) and d <= 3.6:
				return 2
			return 0
	# orbe: esfera com volume (sombra embaixo à direita, reflexo no alto à esquerda)
	var d := p.distance_to(c)
	if d > 4.3:
		return 0
	var r := p.distance_to(c + Vector2(-1.3, -1.3))
	if r <= 1.0:
		return 4
	if r <= 2.4:
		return 3
	if d <= 3.3 and r <= 4.2:
		return 2
	return 1

# ---- impactos ----------------------------------------------------------------------------

## Estouro pequeno de pixels no ar (acerto de projétil). `escala` 1 = orbe básico.
static func impacto(cena: Node, pos: Vector2, elemento: String, escala := 1.0) -> void:
	if cena == null or not cena.is_inside_tree() or Vfx.lotado(cena.get_tree()):
		return
	var e := Estouro.new()
	e.pal = paleta(elemento)
	e.raio = 22.0 * escala
	e.z_index = 4
	cena.add_child(e)
	e.global_position = pos

## Explosão de área no chão, com a folha do elemento quando existe e um anel de pixels por cima.
static func explosao(cena: Node, pos: Vector2, elemento: String, raio: float) -> void:
	if cena == null or not cena.is_inside_tree():
		return
	match elemento:
		"fogo":
			Px.tocar(cena, "barrel_explosion", pos + Vector2(0, raio * 0.35), raio * 2.6 / maxf(Px.tamanho("barrel_explosion").x, 1.0))
		"gelo":
			GeloFx._anim(cena, "gelo_explosao", 8, pos, raio * 2.0, 0.55, 14.0)
		"raio":
			Px.tocar(cena, "thunderclap", pos + Vector2(0, -4), raio * 2.0 / maxf(Px.tamanho("thunderclap").x, 1.0), "centro")
		"veneno":
			Px.tocar(cena, "spore_burst", pos + Vector2(0, raio * 0.3), raio * 2.0 / maxf(Px.tamanho("spore_burst").x, 1.0))
	anel(cena, pos, elemento, raio)

## Anel de pixels que abre no chão (elipse da visão 3/4) até `raio` e some.
static func anel(cena: Node, pos: Vector2, elemento: String, raio: float, tempo := 0.35) -> void:
	if cena == null or not cena.is_inside_tree():
		return
	var e := Estouro.new()
	e.pal = paleta(elemento)
	e.raio = raio
	e.no_chao = true
	e.vida = tempo
	e.z_index = -1
	cena.add_child(e)
	e.global_position = pos

## Pixels que voam de um ponto (ou abrem em anel no chão), sempre encaixados na grade do mundo.
class Estouro extends Node2D:
	var pal: Array = []
	var raio := 22.0
	var vida := 0.28
	var no_chao := false
	var _t := 0.0

	func _process(delta: float) -> void:
		_t += delta
		queue_redraw()
		if _t >= vida:
			queue_free()

	func _draw() -> void:
		var k := clampf(_t / vida, 0.0, 1.0)
		var abre := 1.0 - pow(1.0 - k, 2.5)
		var n := 20 if no_chao else 8
		var achata := 0.5 if no_chao else 1.0
		for i in n:
			var a := TAU * float(i) / float(n) + (0.0 if no_chao else 0.4)
			var d := raio * abre * (1.0 if no_chao or i % 2 == 0 else 0.6)
			var p := ((Vector2(cos(a), sin(a) * achata) * d) / 2.5).round() * 2.5
			var lado := 2.5 * (2.0 if k < 0.5 else 1.0)
			var c: Color = pal[3] if (i % 3 == 0 or k < 0.25) else pal[2]
			draw_rect(Rect2(p - Vector2(lado, lado) * 0.5, Vector2(lado, lado)), Color(c, 1.0 - k * k))
		if k < 0.35 and not no_chao:   # clarão do miolo, em cruz
			var m := 2.5 * 2.0
			draw_rect(Rect2(Vector2(-m, -m * 0.5), Vector2(m * 2.0, m)), Color(pal[4], 0.9))
			draw_rect(Rect2(Vector2(-m * 0.5, -m), Vector2(m, m * 2.0)), Color(pal[4], 0.9))
