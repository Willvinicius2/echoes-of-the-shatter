extends RefCounted
## Peças desenhadas por código da HUD de ARPG sombrio: globos de vida e recurso, molduras de ferro e pedra,
## slots de habilidade, barra do chefe e plaquetas. Arte original (sem texturas externas); quando houver arte
## pintada, estes desenhos viram o fallback. Cores em data2d/tema.csv, medidas em data2d/hud_layout.csv.

const Tema = preload("res://scripts2d/tema_2d.gd")

const PASSOS_LIQUIDO := 14

static var _serifa: Font

## Fonte serifada dos títulos (DejaVu Serif Bold, art2d/ui/LICENCA.md); sem o arquivo, cai na fonte padrão.
static func serifa() -> Font:
	if _serifa == null:
		var caminho := "res://art2d/ui/DejaVuSerif-Bold.ttf"
		_serifa = load(caminho) if ResourceLoader.exists(caminho) else ThemeDB.fallback_font
	return _serifa

static func _c(chave: String) -> Color:
	return Tema.cor(chave)

## Texto com sombra dura, para ler sobre qualquer chão.
static func texto(c: CanvasItem, pos: Vector2, s: String, tam: int, cor: Color, alinh := HORIZONTAL_ALIGNMENT_LEFT, larg := -1.0, serif := false) -> void:
	var f: Font = serifa() if serif else ThemeDB.fallback_font
	var d := 2.0 if tam >= 20 else 1.0
	c.draw_string(f, pos + Vector2(d, d + 1.0), s, alinh, larg, tam, Color(0, 0, 0, 1.0))
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

## Caveira de ferro (cantos da faixa e pontas da barra do chefe): crânio, órbitas e dentes.
static func caveira(c: CanvasItem, p: Vector2, r := 9.0) -> void:
	c.draw_circle(p + Vector2(0, 1.5), r + 1.0, Color(0, 0, 0, 0.6))
	c.draw_circle(p, r, _c("metal_claro").darkened(0.15))
	c.draw_rect(Rect2(p.x - r * 0.55, p.y + r * 0.45, r * 1.1, r * 0.8), _c("metal_claro").darkened(0.15))
	c.draw_circle(p + Vector2(-r * 0.38, -r * 0.05), r * 0.27, Color(0.02, 0.02, 0.03))
	c.draw_circle(p + Vector2(r * 0.38, -r * 0.05), r * 0.27, Color(0.02, 0.02, 0.03))
	c.draw_colored_polygon(PackedVector2Array([p + Vector2(0, r * 0.15), p + Vector2(-r * 0.12, r * 0.4), p + Vector2(r * 0.12, r * 0.4)]), Color(0.02, 0.02, 0.03))
	for k in 3:
		c.draw_line(p + Vector2(-r * 0.3 + k * r * 0.3, r * 0.75), p + Vector2(-r * 0.3 + k * r * 0.3, r * 1.2), Color(0, 0, 0, 0.7), 1.0)

## Corrente reta entre dois pontos: elos ovais de frente (anel) alternados com elos de perfil (barra), contínuos.
static func corrente(c: CanvasItem, p0: Vector2, p1: Vector2, elos := 13) -> void:
	var dir := (p1 - p0).normalized()
	var ang := dir.angle()
	for i in elos:
		var p := p0.lerp(p1, float(i) / (elos - 1))
		if i % 2 == 0:
			var oval := PackedVector2Array()
			for k in 17:
				var a := TAU * k / 16.0
				oval.append(p + Vector2(cos(a) * 7.5, sin(a) * 3.8).rotated(ang))
			c.draw_polyline(oval, Color(0, 0, 0, 0.85), 4.5)
			c.draw_polyline(oval, _c("metal_claro"), 2.2)
		else:
			c.draw_line(p - dir * 4.5, p + dir * 4.5, Color(0, 0, 0, 0.85), 5.0)
			c.draw_line(p - dir * 4.5, p + dir * 4.5, _c("metal_medio").lightened(0.15), 3.0)

## Cadeado de ferro com argola e fechadura.
static func cadeado(c: CanvasItem, p: Vector2, lado := 28.0) -> void:
	var corpo := Rect2(p - Vector2(lado * 0.5, 0), Vector2(lado, lado * 0.78))
	c.draw_arc(p + Vector2(0, 1), lado * 0.32, PI, TAU, 16, _c("metal_claro"), 4.0)
	c.draw_rect(corpo.grow(2), Color(0, 0, 0, 0.7))
	c.draw_rect(corpo, _c("destaque").darkened(0.35))
	c.draw_rect(Rect2(corpo.position, Vector2(corpo.size.x, 3)), Color(1, 1, 1, 0.2))
	c.draw_circle(corpo.get_center() + Vector2(0, -1), lado * 0.1, Color(0.04, 0.03, 0.03))
	c.draw_rect(Rect2(corpo.get_center() + Vector2(-1.2, 0), Vector2(2.4, lado * 0.22)), Color(0.04, 0.03, 0.03))

## Marca de fase do chefe: losango dourado cheio (fase atual ou já passada) ou vazado (próximas).
static func runa(c: CanvasItem, p: Vector2, _tipo: int, acesa: bool) -> void:
	var r := 7.0
	var v := PackedVector2Array([p + Vector2(0, -r), p + Vector2(r, 0), p + Vector2(0, r), p + Vector2(-r, 0)])
	if acesa:
		c.draw_circle(p, r * 1.5, Color(_c("destaque").r, _c("destaque").g, _c("destaque").b, 0.18))
		c.draw_colored_polygon(v, _c("destaque").lightened(0.1))
	else:
		c.draw_colored_polygon(v, Color(0.03, 0.025, 0.03))
	v.append(v[0])
	c.draw_polyline(v, Color(0, 0, 0, 0.85), 3.0)
	c.draw_polyline(v, _c("destaque") if acesa else _c("metal_medio"), 1.5)

## Alvenaria de pedra escura: fileiras de blocos com juntas, variação de tom e rachaduras (determinística).
static func alvenaria(c: CanvasItem, r: Rect2, bloco := Vector2(46, 18)) -> void:
	var linhas := int(ceil(r.size.y / bloco.y))
	for j in linhas:
		var y := r.position.y + j * bloco.y
		var h := minf(bloco.y, r.end.y - y)
		var desloc := (j % 2) * bloco.x * 0.5
		var x := r.position.x - desloc
		var k := 0
		while x < r.end.x:
			var tom := 0.55 + 0.45 * fmod(abs(sin(float(j * 31 + k * 17) * 12.9898) * 43758.5453), 1.0)
			var larg := bloco.x * (0.8 + 0.4 * fmod(abs(sin(float(k * 7 + j) * 4.1) * 1000.0), 1.0))
			var x0 := maxf(x, r.position.x)
			var x1 := minf(x + larg, r.end.x)
			if x1 > x0:
				var base := _c("pedra").lightened(0.06 * tom)
				c.draw_rect(Rect2(x0, y, x1 - x0, h), base)
				c.draw_rect(Rect2(x0, y, x1 - x0, 1.5), Color(1, 1, 1, 0.07 * tom))
				c.draw_rect(Rect2(x0, y + h - 2, x1 - x0, 2), Color(0, 0, 0, 0.35))
				c.draw_rect(Rect2(x1 - 1.5, y, 1.5, h), Color(0, 0, 0, 0.4))
				# veios claros e escuros e manchas de desgaste, diferentes em cada laje
				var v := fmod(abs(sin(float(j * 13 + k * 29) * 3.7) * 977.0), 1.0)
				c.draw_line(Vector2(x0 + 4 + v * 10, y + 3), Vector2(x0 + 16 + v * 14, y + h * 0.55), Color(1, 1, 1, 0.05 + 0.05 * v), 1.0)
				c.draw_line(Vector2(x0 + 10 + v * 20, y + h - 4), Vector2(x0 + 24 + v * 14, y + h * 0.4), Color(0, 0, 0, 0.3), 1.0)
				if tom > 0.9:
					c.draw_line(Vector2(x0 + 6, y + 4), Vector2(x0 + 12, y + h - 4), Color(0, 0, 0, 0.4), 1.0)
					c.draw_rect(Rect2(x0 + larg * 0.3, y + h * 0.5, 6, 3), Color(0, 0, 0, 0.22))
				elif tom < 0.62:
					c.draw_rect(Rect2(x0 + 2, y + 2, (x1 - x0) * 0.5, 2.5), Color(0.2, 0.22, 0.18, 0.28))
			x += larg
			k += 1

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

## Globo completo: sombra, vidro, líquido com brilho interno que reage à vida, reflexo curvo, aro de ferro forjado
## grosso com rebites e quatro garras sobre o vidro. `pulso` (0..1) acende o aro em vermelho (vida baixa);
## `fantasma` é a fração antiga, em perda. `vazio` = vidro escuro sem líquido (recurso trancado).
static func globo(c: CanvasItem, centro: Vector2, raio: float, frac: float, fantasma: float, escura: Color, clara: Color, t: float, pulso := 0.0, vazio := false) -> void:
	if pulso > 0.0:   # vida baixa: o líquido clareia e pulsa para não sumir
		clara = clara.lightened(0.3 * pulso)
		escura = escura.lightened(0.18)
	var r_in := raio - 15.0
	c.draw_circle(centro + Vector2(0, 6), raio + 14.0, Color(0, 0, 0, 0.5))
	# chifres de ferro curvos atrás do aro, com ponta dourada
	for lado in [-1.0, 1.0]:
		var curva := PackedVector2Array()
		var n := 14
		for i in n + 1:
			var u := float(i) / n
			var x := lerpf(raio * 0.62, raio * 1.28, u) + sin(u * PI) * raio * 0.06
			var y := -raio * 0.80 - pow(u, 1.6) * raio * 0.55
			curva.append(centro + Vector2(lado * x, y))
		var espessura := PackedVector2Array()
		for i in curva.size():
			espessura.append(curva[i] + Vector2(0, raio * 0.2 * (1.0 - float(i) / n)))
		var forma := PackedVector2Array(curva)
		for i in range(espessura.size() - 1, -1, -1):
			forma.append(espessura[i])
		c.draw_colored_polygon(forma, _c("metal_escuro"))
		c.draw_polyline(curva, _c("metal_claro"), 1.5)
		c.draw_polyline(espessura, _c("metal_medio"), 1.0)
		c.draw_circle(curva[n], 3.0, _c("destaque"))
	c.draw_circle(centro, raio, _c("metal_escuro"))
	c.draw_circle(centro, r_in, Color(0.02, 0.012, 0.02))
	if not vazio:
		if fantasma > frac:
			liquido(c, centro, r_in, fantasma, Color(0.45, 0.12, 0.1), Color(0.95, 0.62, 0.45), t, 1.7)
		liquido(c, centro, r_in, frac, escura, clara, t)
		# brilho interno: cheio brilha firme; vida baixa pulsa
		var forca := 0.10 + 0.22 * frac + 0.22 * pulso
		c.draw_circle(centro + Vector2(0, r_in * 0.3), r_in * 0.7, Color(clara.r, clara.g, clara.b, forca * 0.35))
		c.draw_circle(centro + Vector2(0, r_in * 0.3), r_in * 0.4, Color(1, 0.8, 0.7, forca * 0.25))
	else:
		liquido(c, centro, r_in, 0.14, escura.darkened(0.5), clara.darkened(0.6), t, 0.9)
	# profundidade do vidro: sombra interna em anéis
	for k in 7:
		c.draw_arc(centro, r_in - k * 1.6, 0.0, TAU, 48, Color(0, 0, 0, 0.34 - k * 0.045), 2.0)
	# reflexo curvo (crescente) no alto à esquerda e ponto de luz
	c.draw_arc(centro, r_in * 0.82, PI * 1.05, PI * 1.55, 24, Color(1, 1, 1, 0.22), 5.0)
	c.draw_arc(centro, r_in * 0.82, PI * 1.12, PI * 1.35, 24, Color(1, 1, 1, 0.3), 2.5)
	c.draw_circle(centro + Vector2(cos(PI * 1.62), sin(PI * 1.62)) * r_in * 0.82, 2.6, Color(1, 1, 1, 0.45))
	c.draw_arc(centro, r_in * 0.84, PI * 0.1, PI * 0.35, 12, Color(1, 1, 1, 0.1), 3.0)
	# aro de ferro forjado: camada grossa, luz no arco superior esquerdo, sombra no inferior direito, friso dourado
	c.draw_arc(centro, raio - 7.0, 0.0, TAU, 72, _c("metal_medio"), 14.0)
	c.draw_arc(centro, raio - 2.5, PI * 0.85, PI * 1.8, 40, _c("metal_claro"), 4.0)
	c.draw_arc(centro, raio - 12.0, -PI * 0.15, PI * 0.8, 40, Color(0, 0, 0, 0.5), 4.0)
	c.draw_arc(centro, raio - 7.0, 0.0, TAU, 72, Color(0, 0, 0, 0.22), 1.5)
	c.draw_arc(centro, raio, 0.0, TAU, 72, Color(0, 0, 0, 0.75), 1.8)
	c.draw_arc(centro, r_in + 1.0, 0.0, TAU, 72, _c("destaque").darkened(0.25), 2.5)
	for i in 12:
		var a := TAU * i / 12.0 + 0.26
		rebite(c, centro + Vector2(cos(a), sin(a)) * (raio - 7.0), 2.8)
	# garras de ferro sobre o vidro (topo, base e laterais)
	for g in 4:
		var ang := -PI * 0.5 + g * PI * 0.5
		var dir := Vector2(cos(ang), sin(ang))
		var tang := Vector2(-dir.y, dir.x)
		var base := centro + dir * (raio - 3.0)
		var ponta := centro + dir * (r_in - 10.0)
		var garra := PackedVector2Array([base + tang * 8.0, base - tang * 8.0, ponta + tang * 0.5])
		c.draw_colored_polygon(garra, _c("metal_medio"))
		garra.append(garra[0])
		c.draw_polyline(garra, Color(0, 0, 0, 0.75), 1.5)
		c.draw_line(base + tang * 5.0, ponta, _c("metal_claro"), 1.0)
	if pulso > 0.0:
		c.draw_arc(centro, raio + 2.0, 0.0, TAU, 72, Color(1.0, 0.1, 0.08, 0.35 * pulso), 9.0)
		c.draw_arc(centro, raio, 0.0, TAU, 72, Color(1.0, 0.25, 0.2, 0.9 * pulso), 4.0)
		c.draw_arc(centro, r_in + 1.0, 0.0, TAU, 72, Color(1.0, 0.3, 0.25, 0.7 * pulso), 3.0)

## Marcador cortado em losango (ponta de moldura).
static func losango(c: CanvasItem, p: Vector2, r: float, cor: Color) -> void:
	var v := PackedVector2Array([p + Vector2(0, -r), p + Vector2(r, 0), p + Vector2(0, r), p + Vector2(-r, 0)])
	c.draw_colored_polygon(v, cor)
	v.append(v[0])
	c.draw_polyline(v, Color(0, 0, 0, 0.6), 1.0)

## Barra horizontal ornamentada (chefe e estamina): ferro, vão fundo, líquido com brilho e pontas.
static func barra(c: CanvasItem, r: Rect2, frac: float, escura: Color, clara: Color, enfeite := 1) -> void:
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
	if enfeite > 0:
		var cy := r.position.y + r.size.y * 0.5
		for lado in [-1.0, 1.0]:
			var x: float = r.position.x - 12.0 if lado < 0.0 else r.end.x + 12.0
			if enfeite == 2:
				caveira(c, Vector2(x + lado * 14.0, cy), 11.0)
				var chifre := PackedVector2Array([Vector2(x + lado * 26, cy - 8), Vector2(x + lado * 44, cy - 22), Vector2(x + lado * 36, cy - 4)])
				c.draw_colored_polygon(chifre, _c("metal_medio"))
				c.draw_polyline(chifre, _c("metal_claro"), 1.2)
				continue
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
		for k in 4:
			c.draw_circle(vao.get_center() - Vector2(0, 6), vao.size.x * (0.40 - k * 0.06), Color(brilho.r, brilho.g, brilho.b, 0.10 + k * 0.04))
	c.draw_rect(vao, Color(0, 0, 0, 0.8), false, 1.5)
	var ic := Rect2(vao.position + Vector2(5, 3), vao.size - Vector2(10, 17))
	c.draw_texture_rect(icone, ic, false, Color(1, 1, 1, 1) if ativo else Color(1, 1, 1, 0.35))
	if not ativo:
		return
	c.draw_rect(r.grow(-1), Color(brilho.r, brilho.g, brilho.b, 0.8), false, 1.5)
	c.draw_rect(Rect2(r.position + Vector2(2, 2), Vector2(r.size.x - 4, 2)), Color(brilho.r, brilho.g, brilho.b, 0.45))
	if recarga > 0.0:
		var ctr := vao.get_center()
		var ini := -PI * 0.5
		var fim := ini + TAU * recarga
		var arco := PackedVector2Array([ctr])
		for p in _arco(ctr, vao.size.x * 0.72, ini, fim, 28):
			arco.append(Vector2(clampf(p.x, vao.position.x, vao.end.x), clampf(p.y, vao.position.y, vao.end.y)))
		c.draw_colored_polygon(arco, Color(0, 0, 0, 0.78))
	if tecla != "":
		tecla_placa(c, Vector2(r.position.x + 4 + maxf(36.0, 10.0 + tecla.length() * 7.0) * 0.5, r.end.y - 13), tecla)

## Plaquinha de tecla (abaixo do slot, sem tocar a borda dele).
static func tecla_placa(c: CanvasItem, centro: Vector2, tecla: String) -> void:
	var larg := maxf(36.0, 10.0 + tecla.length() * 7.0)
	var pl := Rect2(centro - Vector2(larg * 0.5, 8), Vector2(larg, 16))
	placa(c, pl, _c("pedra_clara"), 1.5, false)
	c.draw_rect(pl.grow(-2), Color(0, 0, 0, 0.3), false, 1.0)
	texto(c, Vector2(pl.position.x, pl.position.y + 13), tecla, 12, _c("destaque").lightened(0.25), HORIZONTAL_ALIGNMENT_CENTER, pl.size.x)

## Plaqueta de pedra (alvenaria) com texto serifado de destaque e linha de apoio.
static func plaqueta(c: CanvasItem, r: Rect2, titulo: String, apoio: String) -> void:
	placa(c, r, _c("pedra"), 2.0)
	alvenaria(c, r.grow(-3), Vector2(34, 14))
	c.draw_rect(r.grow(-6), _c("destaque").darkened(0.3), false, 1.0)
	texto(c, Vector2(r.position.x, r.position.y + 26), titulo, 20, _c("destaque").lightened(0.2), HORIZONTAL_ALIGNMENT_CENTER, r.size.x, true)
	texto(c, Vector2(r.position.x, r.position.y + 46), apoio, 14, _c("texto"), HORIZONTAL_ALIGNMENT_CENTER, r.size.x)
