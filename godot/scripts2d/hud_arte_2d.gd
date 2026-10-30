extends RefCounted
## Peças desenhadas por código da HUD de ARPG sombrio: globos de vida e recurso, molduras de ferro e pedra,
## slots de habilidade, barra do chefe e plaquetas. Arte original (sem texturas externas); quando houver arte
## pintada, estes desenhos viram o fallback. Cores em data2d/tema.csv, medidas em data2d/hud_layout.csv.

const Tema = preload("res://scripts2d/tema_2d.gd")

const PASSOS_LIQUIDO := 14

static func _c(chave: String) -> Color:
	return Tema.cor(chave)

## Texto com sombra dura, para ler sobre qualquer chão.
static func texto(c: CanvasItem, pos: Vector2, s: String, tam: int, cor: Color, alinh := HORIZONTAL_ALIGNMENT_LEFT, larg := -1.0) -> void:
	var f := ThemeDB.fallback_font
	c.draw_string(f, pos + Vector2(1, 2), s, alinh, larg, tam, Color(0, 0, 0, 0.85))
	c.draw_string(f, pos, s, alinh, larg, tam, cor)

static func _arco(centro: Vector2, r: float, a0: float, a1: float, n := 24) -> PackedVector2Array:
	var p := PackedVector2Array()
	for i in n + 1:
		var a := lerpf(a0, a1, float(i) / n)
		p.append(centro + Vector2(cos(a), sin(a)) * r)
	return p

## Rebite de ferro: disco com brilho no canto superior esquerdo.
static func rebite(c: CanvasItem, p: Vector2, r := 2.5) -> void:
	c.draw_circle(p + Vector2(0.6, 1.0), r + 0.6, Color(0, 0, 0, 0.6))
	c.draw_circle(p, r, _c("metal_medio"))
	c.draw_circle(p + Vector2(-r * 0.3, -r * 0.3), r * 0.5, _c("metal_claro"))

## Placa de ferro/pedra com chanfro: aro escuro, luz em cima e à esquerda, sombra embaixo e à direita.
static func placa(c: CanvasItem, r: Rect2, fundo: Color, chanfro := 2.0, cantos := true) -> void:
	c.draw_rect(r.grow(2), Color(0, 0, 0, 0.55))
	c.draw_rect(r, _c("metal_escuro"))
	var i := r.grow(-1.0)
	c.draw_rect(i, fundo)
	c.draw_rect(Rect2(i.position, Vector2(i.size.x, chanfro)), Color(1, 1, 1, 0.13))
	c.draw_rect(Rect2(i.position, Vector2(chanfro, i.size.y)), Color(1, 1, 1, 0.08))
	c.draw_rect(Rect2(i.position.x, i.end.y - chanfro, i.size.x, chanfro), Color(0, 0, 0, 0.35))
	c.draw_rect(Rect2(i.end.x - chanfro, i.position.y, chanfro, i.size.y), Color(0, 0, 0, 0.25))
	c.draw_rect(r, _c("metal_medio"), false, 1.0)
	if cantos:
		for q in [r.position + Vector2(5, 5), Vector2(r.end.x - 5, r.position.y + 5), Vector2(r.position.x + 5, r.end.y - 5), r.end - Vector2(5, 5)]:
			rebite(c, q, 1.8)

## Líquido dentro de um disco: polígono com gradiente, superfície ondulada, brilho e bolhas.
static func liquido(c: CanvasItem, centro: Vector2, raio: float, frac: float, escura: Color, clara: Color, t: float, fase := 0.0) -> void:
	frac = clampf(frac, 0.0, 1.0)
	if frac <= 0.01:
		return
	var y_s := centro.y + raio - 2.0 * raio * frac
	var amp := 2.6 if frac < 0.995 else 0.0
	var pts := PackedVector2Array()
	var cores := PackedColorArray()
	var base := y_s + amp
	var lados: Array = []
	for k in PASSOS_LIQUIDO + 1:
		var y := lerpf(base, centro.y + raio, float(k) / PASSOS_LIQUIDO)
		var dy := y - centro.y
		lados.append([y, sqrt(maxf(raio * raio - dy * dy, 0.0))])
	var alt := 2.0 * raio * maxf(frac, 0.05)
	for l in lados:
		pts.append(Vector2(centro.x - l[1], l[0]))
		cores.append(clara.lerp(escura, clampf((l[0] - y_s) / alt, 0.0, 1.0)))
	for k in range(lados.size() - 1, -1, -1):
		var l: Array = lados[k]
		pts.append(Vector2(centro.x + l[1], l[0]))
		cores.append(clara.lerp(escura, clampf((l[0] - y_s) / alt, 0.0, 1.0)))
	c.draw_polygon(pts, cores)
	if amp > 0.0:
		var hw := sqrt(maxf(raio * raio - (y_s - centro.y) * (y_s - centro.y), 0.0))
		var topo := PackedVector2Array()
		var n := 28
		for i in n + 1:
			var u := float(i) / n
			var x := centro.x - hw + 2.0 * hw * u
			topo.append(Vector2(x, y_s + amp * sin(t * 2.4 + fase + u * 7.0) * 0.9))
		var cap := PackedVector2Array(topo)
		cap.append(Vector2(centro.x + hw, base + 1.0))
		cap.append(Vector2(centro.x - hw, base + 1.0))
		c.draw_colored_polygon(cap, clara)
		c.draw_polyline(topo, clara.lightened(0.45), 1.5)
	# bolhas subindo
	for b in 4:
		var u := fmod(t * 0.18 + b * 0.27 + fase, 1.0)
		var bx := centro.x + sin(b * 2.1 + fase) * raio * 0.45
		var by := centro.y + raio * 0.85 - u * (centro.y + raio * 0.85 - y_s - 4.0)
		if by > y_s + 4.0:
			c.draw_circle(Vector2(bx, by), 1.6 + b * 0.35, Color(1, 1, 1, 0.16 * (1.0 - u)))

## Globo completo: sombra, vidro, líquido, reflexo, aro de ferro com rebites e chifres.
## `pulso` (0..1) acende o aro em vermelho (vida baixa); `fantasma` é a fração antiga, em perda.
static func globo(c: CanvasItem, centro: Vector2, raio: float, frac: float, fantasma: float, escura: Color, clara: Color, t: float, pulso := 0.0, vazio := false) -> void:
	var r_in := raio - 9.0
	c.draw_circle(centro + Vector2(0, 5), raio + 12.0, Color(0, 0, 0, 0.45))
	# chifres de ferro curvos atrás do aro, com ponta dourada
	for lado in [-1.0, 1.0]:
		var curva := PackedVector2Array()
		var n := 14
		for i in n + 1:
			var u := float(i) / n
			# da base no aro até a ponta que sobe e se abre para fora
			var x := lerpf(raio * 0.62, raio * 1.28, u) + sin(u * PI) * raio * 0.06
			var y := -raio * 0.80 - pow(u, 1.6) * raio * 0.55
			curva.append(centro + Vector2(lado * x, y))
		var espessura := PackedVector2Array()
		for i in curva.size():
			var u := float(i) / n
			espessura.append(curva[i] + Vector2(0, raio * 0.2 * (1.0 - u)))
		var forma := PackedVector2Array(curva)
		for i in range(espessura.size() - 1, -1, -1):
			forma.append(espessura[i])
		c.draw_colored_polygon(forma, _c("metal_escuro"))
		c.draw_polyline(curva, _c("metal_claro"), 1.5)
		c.draw_polyline(espessura, _c("metal_medio"), 1.0)
		c.draw_circle(curva[n], 3.0, _c("destaque"))
	c.draw_circle(centro, raio, _c("metal_escuro"))
	c.draw_circle(centro, r_in, Color(0.035, 0.02, 0.03))
	if not vazio:
		if fantasma > frac:
			liquido(c, centro, r_in, fantasma, Color(0.45, 0.12, 0.1), Color(0.95, 0.62, 0.45), t, 1.7)
		liquido(c, centro, r_in, frac, escura, clara, t)
	else:
		c.draw_circle(centro, r_in, Color(escura.r, escura.g, escura.b, 0.55))
		c.draw_circle(centro + Vector2(0, r_in * 0.25), r_in * 0.62, Color(clara.r, clara.g, clara.b, 0.07))
	# profundidade do vidro: sombra interna em anéis e reflexo
	for k in 6:
		c.draw_arc(centro, r_in - k * 1.6, 0.0, TAU, 48, Color(0, 0, 0, 0.30 - k * 0.045), 2.0)
	var brilho := PackedVector2Array()
	for i in 20:
		var a := TAU * i / 20.0
		brilho.append(centro + Vector2(-r_in * 0.36, -r_in * 0.5) + Vector2(cos(a) * r_in * 0.34, sin(a) * r_in * 0.18).rotated(-0.7))
	c.draw_colored_polygon(brilho, Color(1, 1, 1, 0.12))
	# aro de ferro: base, luz no arco superior esquerdo, sombra no inferior direito
	c.draw_arc(centro, raio - 4.5, 0.0, TAU, 72, _c("metal_medio"), 9.0)
	c.draw_arc(centro, raio - 2.0, PI * 0.9, PI * 1.75, 40, _c("metal_claro"), 3.0)
	c.draw_arc(centro, raio - 7.0, -PI * 0.1, PI * 0.75, 40, Color(0, 0, 0, 0.45), 3.0)
	c.draw_arc(centro, raio, 0.0, TAU, 72, Color(0, 0, 0, 0.7), 1.5)
	c.draw_arc(centro, r_in + 1.0, 0.0, TAU, 72, _c("destaque").darkened(0.2), 2.0)
	for i in 12:
		var a := TAU * i / 12.0 + 0.26
		rebite(c, centro + Vector2(cos(a), sin(a)) * (raio - 4.5), 2.2)
	if pulso > 0.0:
		c.draw_arc(centro, raio + 1.0, 0.0, TAU, 72, Color(1.0, 0.15, 0.1, 0.55 * pulso), 4.0)

## Marcador cortado em losango (ponta de moldura).
static func losango(c: CanvasItem, p: Vector2, r: float, cor: Color) -> void:
	var v := PackedVector2Array([p + Vector2(0, -r), p + Vector2(r, 0), p + Vector2(0, r), p + Vector2(-r, 0)])
	c.draw_colored_polygon(v, cor)
	v.append(v[0])
	c.draw_polyline(v, Color(0, 0, 0, 0.6), 1.0)

## Barra horizontal ornamentada (chefe e estamina): ferro, vão fundo, líquido com brilho e pontas.
static func barra(c: CanvasItem, r: Rect2, frac: float, escura: Color, clara: Color, enfeite := true) -> void:
	c.draw_rect(r.grow(5), Color(0, 0, 0, 0.5))
	c.draw_rect(r.grow(4), _c("metal_escuro"))
	c.draw_rect(r.grow(4), _c("metal_medio"), false, 1.0)
	c.draw_rect(Rect2(r.position + Vector2(-3, -3), Vector2(r.size.x + 6, 1.5)), Color(1, 1, 1, 0.16))
	c.draw_rect(r, Color(0.02, 0.015, 0.03))
	frac = clampf(frac, 0.0, 1.0)
	if frac > 0.0:
		var w := r.size.x * frac
		var cores := PackedColorArray([clara, clara, escura, escura])
		c.draw_polygon(PackedVector2Array([r.position, r.position + Vector2(w, 0), r.position + Vector2(w, r.size.y), r.position + Vector2(0, r.size.y)]), cores)
		c.draw_rect(Rect2(r.position + Vector2(0, 1), Vector2(w, maxf(r.size.y * 0.22, 1.0))), Color(1, 1, 1, 0.2))
		c.draw_rect(Rect2(r.position.x + w - 1.5, r.position.y, 1.5, r.size.y), clara.lightened(0.5))
	for k in range(1, 10):
		c.draw_rect(Rect2(r.position.x + r.size.x * k / 10.0 - 0.5, r.position.y, 1.0, r.size.y), Color(0, 0, 0, 0.28))
	c.draw_rect(r, Color(0, 0, 0, 0.7), false, 1.0)
	if enfeite:
		var cy := r.position.y + r.size.y * 0.5
		for lado in [-1.0, 1.0]:
			var x: float = r.position.x - 12.0 if lado < 0.0 else r.end.x + 12.0
			losango(c, Vector2(x, cy), 8.0, _c("destaque").darkened(0.15))
			var asa := PackedVector2Array([Vector2(x + lado * 8, cy), Vector2(x + lado * 26, cy - 5), Vector2(x + lado * 40, cy), Vector2(x + lado * 26, cy + 5)])
			c.draw_colored_polygon(asa, _c("metal_escuro"))
			asa.append(asa[0])
			c.draw_polyline(asa, _c("metal_medio"), 1.2)

## Slot de habilidade: baixo-relevo de pedra, ícone, varredura radial de recarga e plaquinha da tecla.
static func slot(c: CanvasItem, r: Rect2, icone: Texture2D, recarga: float, tecla: String, ativo: bool, brilho: Color) -> void:
	placa(c, r, _c("pedra") if ativo else Color(0.07, 0.07, 0.09), 3.0)
	var vao := r.grow(-7)
	c.draw_rect(vao, Color(0.03, 0.03, 0.045))
	if ativo:
		c.draw_circle(vao.get_center(), vao.size.x * 0.42, Color(brilho.r, brilho.g, brilho.b, 0.16))
	c.draw_rect(vao, Color(0, 0, 0, 0.8), false, 1.5)
	var ic := vao.grow(-4)
	c.draw_texture_rect(icone, ic, false, Color(1, 1, 1, 1) if ativo else Color(1, 1, 1, 0.35))
	if not ativo:
		return
	c.draw_rect(r.grow(-1), Color(brilho.r, brilho.g, brilho.b, 0.55), false, 1.0)
	if recarga > 0.0:
		var ctr := vao.get_center()
		var ini := -PI * 0.5
		var fim := ini + TAU * recarga
		var arco := PackedVector2Array([ctr])
		for p in _arco(ctr, vao.size.x * 0.72, ini, fim, 28):
			arco.append(Vector2(clampf(p.x, vao.position.x, vao.end.x), clampf(p.y, vao.position.y, vao.end.y)))
		c.draw_colored_polygon(arco, Color(0, 0, 0, 0.66))
	var pl := Rect2(r.position.x + r.size.x * 0.5 - 24, r.end.y - 7, 48, 17)
	placa(c, pl, _c("metal_escuro"), 1.0, false)
	texto(c, Vector2(pl.position.x, pl.position.y + 13), tecla, 12, _c("texto"), HORIZONTAL_ALIGNMENT_CENTER, pl.size.x)

## Plaqueta de pedra com texto de destaque (sala atual) e linha de apoio (tempo).
static func plaqueta(c: CanvasItem, r: Rect2, titulo: String, apoio: String) -> void:
	placa(c, r, _c("pedra"), 2.0)
	c.draw_rect(r.grow(-6), _c("destaque").darkened(0.55), false, 1.0)
	texto(c, Vector2(r.position.x, r.position.y + 26), titulo, 20, _c("destaque"), HORIZONTAL_ALIGNMENT_CENTER, r.size.x)
	texto(c, Vector2(r.position.x, r.position.y + 46), apoio, 14, _c("texto_suave"), HORIZONTAL_ALIGNMENT_CENTER, r.size.x)
