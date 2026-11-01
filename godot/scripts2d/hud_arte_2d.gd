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

static var _texturas := {}

## Peça de arte pintada da HUD (art2d/ui/<nome>.png, ver docs/arte/29_arte_ui_gpt_image.md); null se faltar.
static func tex(nome: String) -> Texture2D:
	if not _texturas.has(nome):
		var caminho := "res://art2d/ui/%s.png" % nome
		_texturas[nome] = load(caminho) if ResourceLoader.exists(caminho) else null
	return _texturas[nome]

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
static func runa(c: CanvasItem, p: Vector2, _tipo: int, acesa: bool, r := 7.0) -> void:
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
	var moldura := tex("hud_globo_moldura")
	var r_in := raio * 0.859 if moldura != null else raio - 15.0   # o vidro da moldura pintada vai até 0,859 do raio externo
	c.draw_circle(centro + Vector2(0, 6), raio + 6.0 if moldura != null else raio + 14.0, Color(0, 0, 0, 0.5))
	# chifres de ferro curvos atrás do aro, com ponta dourada (só no desenho de reserva)
	for lado in ([] if moldura != null else [-1.0, 1.0]):
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
	if moldura != null:
		c.draw_texture_rect(moldura, Rect2(centro - Vector2(raio, raio), Vector2(raio, raio) * 2.0), false)
	else:
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

## Slot de habilidade: ícone, moldura, varredura radial de recarga com os segundos restantes, tinta azul quando falta
## recurso e plaquinha da tecla. `segundos` < 0 esconde o número; `pequeno` = slot de ataque/esquiva (tecla menor).
static func slot(c: CanvasItem, r: Rect2, icone: Texture2D, recarga: float, tecla: String, ativo: bool, brilho: Color, segundos := -1.0, sem_recurso := false, pequeno := false) -> void:
	var moldura := tex("hud_slot_moldura")
	if moldura == null:
		placa(c, r, _c("pedra") if ativo else Color(0.07, 0.07, 0.09), 3.0)
	var vao := r.grow(-(r.size.x * 0.067) if moldura != null else -7.0)
	c.draw_rect(vao, Color(0.03, 0.03, 0.045))
	if ativo and not sem_recurso:
		for k in 3:
			c.draw_circle(vao.get_center() - Vector2(0, 4), vao.size.x * (0.36 - k * 0.07), Color(brilho.r, brilho.g, brilho.b, 0.07 + k * 0.03))
	var ic := vao if moldura != null else Rect2(vao.position + Vector2(5, 3), vao.size - Vector2(10, 17))
	var tinta := Color(1, 1, 1, 1) if ativo else Color(1, 1, 1, 0.35)
	if sem_recurso:
		tinta = Color(0.45, 0.55, 1.0, 0.75)
	c.draw_texture_rect(icone, ic, false, tinta)
	if sem_recurso:
		c.draw_rect(vao, Color(_c("sem_recurso").r, _c("sem_recurso").g, _c("sem_recurso").b, 0.45))
	if recarga > 0.0:
		var ctr := vao.get_center()
		var ini := -PI * 0.5
		var fim := ini + TAU * recarga
		var arco := PackedVector2Array([ctr])
		for p in _arco(ctr, vao.size.x * 0.72, ini, fim, 28):
			arco.append(Vector2(clampf(p.x, vao.position.x, vao.end.x), clampf(p.y, vao.position.y, vao.end.y)))
		c.draw_colored_polygon(arco, Color(0, 0, 0, 0.72))
	if moldura != null:
		c.draw_texture_rect(moldura, r, false, Color(1, 1, 1, 1) if ativo else Color(1, 1, 1, 0.6))
	elif ativo:
		c.draw_rect(r.grow(-1), Color(brilho.r, brilho.g, brilho.b, 0.8), false, 1.5)
	if ativo and recarga <= 0.0 and not sem_recurso:
		c.draw_rect(r.grow(-3), Color(brilho.r, brilho.g, brilho.b, 0.35), false, 1.0)   # pronto: fio fino da cor da habilidade
	if recarga > 0.0 and segundos > 0.0:
		var txt := ("%d" % ceili(segundos)) if segundos >= 1.0 else ("%.1f" % segundos)
		var tam := 15 if pequeno else 22
		texto(c, Vector2(vao.position.x, vao.get_center().y + tam * 0.36), txt, tam, _c("texto"), HORIZONTAL_ALIGNMENT_CENTER, vao.size.x, true)
	if tecla != "":
		tecla_placa(c, r, tecla, pequeno)

## Encaixe de habilidade ainda vazio: vão escuro e rebaixado, sem cadeado, só com a letra da tecla.
static func encaixe_vazio(c: CanvasItem, r: Rect2, tecla: String) -> void:
	var vao := r.grow(-r.size.x * 0.067)
	c.draw_rect(vao, Color(0.02, 0.02, 0.03, 0.75))
	c.draw_rect(Rect2(vao.position, Vector2(vao.size.x, 3)), Color(0, 0, 0, 0.5))   # sombra interna em cima
	var moldura := tex("hud_slot_moldura")
	if moldura != null:
		c.draw_texture_rect(moldura, r, false, Color(0.8, 0.8, 0.85, 0.72))
	else:
		c.draw_rect(r, _c("metal_medio").darkened(0.3), false, 1.5)
	if tecla != "":
		texto(c, Vector2(r.position.x, r.get_center().y + 8), tecla, 20, Color(_c("texto_suave").r, _c("texto_suave").g, _c("texto_suave").b, 0.85), HORIZONTAL_ALIGNMENT_CENTER, r.size.x, true)

## 9-slice de uma textura com margens (em pixels do arquivo) e escala: cantos fixos, bordas e miolo esticados.
static func nove_fatias(c: CanvasItem, t: Texture2D, r: Rect2, esq: float, dir: float, topo: float, base: float, esc: float) -> void:
	var w := float(t.get_width())
	var h := float(t.get_height())
	var xs := [0.0, esq, w - dir, w]
	var ys := [0.0, topo, h - base, h]
	var dx := [r.position.x, r.position.x + esq * esc, r.end.x - dir * esc, r.end.x]
	var dy := [r.position.y, r.position.y + topo * esc, r.end.y - base * esc, r.end.y]
	for j in 3:
		for i in 3:
			var src := Rect2(xs[i], ys[j], xs[i + 1] - xs[i], ys[j + 1] - ys[j])
			var dst := Rect2(dx[i], dy[j], dx[i + 1] - dx[i], dy[j + 1] - dy[j])
			if dst.size.x > 0.0 and dst.size.y > 0.0:
				c.draw_texture_rect_region(t, dst, src)

## Sombra suave atrás de um retângulo (camadas de alfa baixo), para slots soltos lerem sobre qualquer chão.
static func sombra(c: CanvasItem, r: Rect2, raio := 8.0, alfa := 0.35) -> void:
	for k in 4:
		c.draw_rect(r.grow(raio * (1.0 - k * 0.25)), Color(0, 0, 0, alfa * 0.25))

## Friso fino de ferro com fio dourado e losangos nas pontas (fundo mínimo da barra de slots).
static func friso(c: CanvasItem, x0: float, x1: float, y: float) -> void:
	c.draw_rect(Rect2(x0, y - 1, x1 - x0, 6), Color(0, 0, 0, 0.55))
	c.draw_rect(Rect2(x0, y, x1 - x0, 4), _c("metal_medio"))
	c.draw_rect(Rect2(x0, y, x1 - x0, 1), _c("metal_claro"))
	c.draw_rect(Rect2(x0, y + 4, x1 - x0, 1), _c("destaque").darkened(0.25))
	losango(c, Vector2(x0, y + 2), 6.0, _c("destaque").darkened(0.1))
	losango(c, Vector2(x1, y + 2), 6.0, _c("destaque").darkened(0.1))

## Plaquinha de tecla no canto de baixo do slot, sem sair dele.
static func tecla_placa(c: CanvasItem, r: Rect2, tecla: String, pequeno := false) -> void:
	var tam := 10 if pequeno else 12
	var larg := minf(r.size.x - 4.0, maxf(22.0, 8.0 + tecla.length() * (tam * 0.6)))
	var pl := Rect2(Vector2(r.position.x + 2.0, r.end.y - 16.0), Vector2(larg, 14))
	if larg < 30.0:   # letra única: plaquinha centrada embaixo
		pl.position.x = r.get_center().x - larg * 0.5
	placa(c, pl, _c("pedra_clara"), 1.5, false)
	texto(c, Vector2(pl.position.x, pl.position.y + 11), tecla, tam, _c("destaque").lightened(0.25), HORIZONTAL_ALIGNMENT_CENTER, pl.size.x)

## Moldura pintada da barra do chefe, em tamanho fixo (a caveira não deforma). Retorna o canal interno onde vai a
## barra; sem a arte, retorna um canal desenhado pelo reserva `barra`. cx = centro x da caveira.
static func canal_chefe(cx: float, y: float) -> Rect2:
	var esc := 0.625   # 1240 px do arquivo = 775 px na tela de 1600
	return Rect2(cx - 620.0 * esc + 58.0 * esc, y + 84.0 * esc, (1182.0 - 58.0) * esc, 34.0 * esc)

static func moldura_chefe(c: CanvasItem, cx: float, y: float) -> void:
	var m := tex("hud_barra_chefe_moldura")
	if m != null:
		c.draw_texture_rect(m, Rect2(cx - 620.0 * 0.625, y, 775.0, 91.25), false)

## Plaqueta de pedra (alvenaria) com texto serifado de destaque e linha de apoio.
static func plaqueta(c: CanvasItem, r: Rect2, titulo: String, apoio: String) -> void:
	placa(c, r, _c("pedra"), 2.0)
	alvenaria(c, r.grow(-3), Vector2(34, 14))
	c.draw_rect(r.grow(-6), _c("destaque").darkened(0.3), false, 1.0)
	texto(c, Vector2(r.position.x, r.position.y + 26), titulo, 20, _c("destaque").lightened(0.2), HORIZONTAL_ALIGNMENT_CENTER, r.size.x, true)
	texto(c, Vector2(r.position.x, r.position.y + 46), apoio, 14, _c("texto"), HORIZONTAL_ALIGNMENT_CENTER, r.size.x)

# ---------------------------------------------------------------- formas recortadas (HUD v4: nada de caixa reta)

## Octógono chanfrado dentro do retângulo `r`; `corte` = fração do lado cortada em cada canto.
static func octogono(r: Rect2, corte := 0.24) -> PackedVector2Array:
	var k := minf(r.size.x, r.size.y) * corte
	return PackedVector2Array([
		Vector2(r.position.x + k, r.position.y), Vector2(r.end.x - k, r.position.y),
		Vector2(r.end.x, r.position.y + k), Vector2(r.end.x, r.end.y - k),
		Vector2(r.end.x - k, r.end.y), Vector2(r.position.x + k, r.end.y),
		Vector2(r.position.x, r.end.y - k), Vector2(r.position.x, r.position.y + k)])

## Círculo como polígono (medalhão).
static func circulo(centro: Vector2, raio: float, n := 32) -> PackedVector2Array:
	var p := PackedVector2Array()
	for i in n:
		var a := TAU * i / n
		p.append(centro + Vector2(cos(a), sin(a)) * raio)
	return p

static func _fechar(p: PackedVector2Array) -> PackedVector2Array:
	var q := PackedVector2Array(p)
	q.append(p[0])
	return q

## Encolhe (d < 0) ou cresce um polígono convexo pelo centro do retângulo que o contém.
static func _deslocar(p: PackedVector2Array, d: float) -> PackedVector2Array:
	var res := Geometry2D.offset_polygon(p, d, Geometry2D.JOIN_MITER)
	return res[0] if res.size() > 0 else p

## Textura recortada por um polígono (uv pelo retângulo `r`).
static func textura_em(c: CanvasItem, t: Texture2D, forma: PackedVector2Array, r: Rect2, tinta := Color.WHITE) -> void:
	if t == null:
		return
	var uvs := PackedVector2Array()
	var cores := PackedColorArray()
	for v in forma:
		uvs.append((v - r.position) / r.size)
		cores.append(tinta)
	c.draw_polygon(forma, cores, uvs, t)

## Aro de ferro forjado em volta de uma forma: sombra, ferro grosso com luz em cima, fio dourado por dentro.
static func aro(c: CanvasItem, forma: PackedVector2Array, espessura := 4.0, ouro := true, alfa := 1.0) -> void:
	var fora := _fechar(_deslocar(forma, espessura * 0.5))
	var dentro := _fechar(_deslocar(forma, -espessura * 0.5))
	c.draw_polyline(_fechar(_deslocar(forma, espessura + 1.0)), Color(0, 0, 0, 0.55 * alfa), 3.0)
	c.draw_polyline(_fechar(forma), Color(_c("metal_escuro").r, _c("metal_escuro").g, _c("metal_escuro").b, alfa), espessura + 2.0)
	c.draw_polyline(_fechar(forma), Color(_c("metal_medio").r, _c("metal_medio").g, _c("metal_medio").b, alfa), espessura)
	# luz no alto: só os segmentos da metade de cima
	var cy := 0.0
	for v in forma:
		cy += v.y
	cy /= forma.size()
	for i in fora.size() - 1:
		var a := fora[i]
		var b := fora[i + 1]
		if (a.y + b.y) * 0.5 < cy - 2.0:
			c.draw_line(a, b, Color(_c("metal_claro").r, _c("metal_claro").g, _c("metal_claro").b, 0.7 * alfa), 1.2)
	if ouro:
		c.draw_polyline(dentro, Color(_c("destaque").r, _c("destaque").g, _c("destaque").b, 0.75 * alfa).darkened(0.15), 1.2)

## Garra de ferro (triângulo curto) apontando para fora a partir de `base` na direção `dir`.
static func garra(c: CanvasItem, base: Vector2, dir: Vector2, tam := 7.0) -> void:
	var t := Vector2(-dir.y, dir.x)
	var g := PackedVector2Array([base + t * tam * 0.55, base + dir * tam, base - t * tam * 0.55])
	c.draw_colored_polygon(g, _c("metal_medio"))
	c.draw_polyline(_fechar(g), Color(0, 0, 0, 0.8), 1.2)
	c.draw_line(base, base + dir * tam * 0.85, _c("metal_claro"), 1.0)

## Slot recortado: `forma` = "octo" (ativas, com garras nos chanfros) ou "medalhao" (ataque e esquiva, redondo).
## Mesmo contrato do `slot` retangular: recarga 0..1, segundos (< 0 esconde), tinta de falta de recurso, tecla.
static func slot_forma(c: CanvasItem, r: Rect2, forma_id: String, icone: Texture2D, recarga: float, tecla: String, ativo: bool, brilho: Color, segundos := -1.0, sem_recurso := false) -> void:
	var redondo := forma_id == "medalhao"
	var ctr := r.get_center()
	var forma := circulo(ctr, r.size.x * 0.5) if redondo else octogono(r)
	var vao := _deslocar(forma, -3.0)
	c.draw_colored_polygon(_deslocar(forma, 4.0), Color(0, 0, 0, 0.35))
	c.draw_colored_polygon(vao, Color(0.03, 0.03, 0.045))
	if ativo and not sem_recurso:
		c.draw_colored_polygon(_deslocar(vao, -r.size.x * 0.12), Color(brilho.r, brilho.g, brilho.b, 0.12))
	var tinta := Color(1, 1, 1, 1) if ativo else Color(1, 1, 1, 0.35)
	if sem_recurso:
		tinta = Color(0.45, 0.55, 1.0, 0.75)
	textura_em(c, icone, vao, r.grow(-2.0), tinta)
	if sem_recurso:
		c.draw_colored_polygon(vao, Color(_c("sem_recurso").r, _c("sem_recurso").g, _c("sem_recurso").b, 0.45))
	if recarga > 0.0:
		var arco := PackedVector2Array([ctr])
		for p in _arco(ctr, r.size.x, -PI * 0.5, -PI * 0.5 + TAU * recarga, 28):
			arco.append(p)
		for parte in Geometry2D.intersect_polygons(arco, vao):
			c.draw_colored_polygon(parte, Color(0, 0, 0, 0.72))
	aro(c, forma, 4.0 if not redondo else 3.5)
	if not redondo:   # garras de ferro nos quatro chanfros
		for i in [1, 3, 5, 7]:
			var a := forma[i]
			var b := forma[(i + 1) % 8]
			var meio := (a + b) * 0.5
			garra(c, meio, (meio - ctr).normalized(), 6.0)
	else:
		rebite(c, ctr + Vector2(0, -r.size.y * 0.5), 2.2)
	if ativo and recarga <= 0.0 and not sem_recurso:
		c.draw_polyline(_fechar(_deslocar(forma, -5.0)), Color(brilho.r, brilho.g, brilho.b, 0.45), 1.2)
	if recarga > 0.0 and segundos > 0.0:
		var txt := ("%d" % ceili(segundos)) if segundos >= 1.0 else ("%.1f" % segundos)
		var tam := 15 if redondo else 22
		texto(c, Vector2(r.position.x, ctr.y + tam * 0.36), txt, tam, _c("texto"), HORIZONTAL_ALIGNMENT_CENTER, r.size.x, true)
	if tecla != "":
		tecla_escudo(c, Vector2(ctr.x, r.end.y + (1.0 if redondo else 0.0)), tecla, redondo)

## Encaixe vazio recortado: vão octogonal escuro com aro apagado e a letra da tecla.
static func encaixe_forma(c: CanvasItem, r: Rect2, tecla: String) -> void:
	var forma := octogono(r)
	c.draw_colored_polygon(_deslocar(forma, 4.0), Color(0, 0, 0, 0.35))
	c.draw_colored_polygon(_deslocar(forma, -3.0), Color(0.02, 0.02, 0.03, 0.85))
	aro(c, forma, 4.0, true, 0.9)
	for i in [1, 3, 5, 7]:
		var a := forma[i]
		var b := forma[(i + 1) % 8]
		var meio := (a + b) * 0.5
		garra(c, meio, (meio - r.get_center()).normalized(), 6.0)
	if tecla != "":
		texto(c, Vector2(r.position.x, r.get_center().y + 8), tecla, 20, Color(_c("texto_suave").r, _c("texto_suave").g, _c("texto_suave").b, 0.85), HORIZONTAL_ALIGNMENT_CENTER, r.size.x, true)

## Plaquinha de tecla em forma de escudinho (topo reto, base em ponta), centrada em `topo_centro` (borda do slot).
static func tecla_escudo(c: CanvasItem, topo_centro: Vector2, tecla: String, pequeno := false) -> void:
	var tam := 13 if pequeno else 13
	var larg := maxf(24.0, 12.0 + tecla.length() * tam * 0.62)
	var h := 17.0
	var y := topo_centro.y - h * 0.7
	var x := topo_centro.x
	var e := PackedVector2Array([Vector2(x - larg * 0.5, y), Vector2(x + larg * 0.5, y), Vector2(x + larg * 0.5, y + h * 0.65),
		Vector2(x, y + h + 3.0), Vector2(x - larg * 0.5, y + h * 0.65)])
	c.draw_colored_polygon(_deslocar(e, 1.5), Color(0, 0, 0, 0.7))
	c.draw_colored_polygon(e, _c("pedra_clara"))
	c.draw_polyline(_fechar(e), _c("metal_medio"), 1.2)
	texto(c, Vector2(x - larg * 0.5, y + 13.0), tecla, tam, _c("destaque").lightened(0.25), HORIZONTAL_ALIGNMENT_CENTER, larg)

## Base de pedra em arco atrás dos slots: sobe das pontas para um pico central com gema, topo em ondas suaves,
## aro de ferro e fio dourado acompanhando a curva. x0..x1 na base da tela (y_base); `alt` = altura nas pontas,
## `pico` = altura no centro.
static func base_arco(c: CanvasItem, x0: float, x1: float, y_base: float, alt: float, pico: float) -> void:
	var topo := PackedVector2Array()
	var n := 48
	for i in n + 1:
		var u := float(i) / n
		var s := sin(u * PI)                       # 0 nas pontas, 1 no meio
		var crista := pow(maxf(0.0, 1.0 - absf(u - 0.5) * 9.0), 1.5) * 16.0   # pico estreito no centro
		var onda := sin(u * TAU * 5.0) * 1.6 * s    # pedra irregular
		topo.append(Vector2(lerpf(x0, x1, u), y_base - alt - (pico - alt) * pow(s, 0.6) - crista + onda))
	var forma := PackedVector2Array(topo)
	forma.append(Vector2(x1, y_base))
	forma.append(Vector2(x0, y_base))
	var cores := PackedColorArray()
	for v in forma:
		cores.append(_c("pedra_clara").lightened(0.05).lerp(Color(0.05, 0.05, 0.06), clampf((v.y - (y_base - pico)) / pico, 0.0, 1.0) * 0.7))
	c.draw_polygon(forma, cores)
	# juntas de alvenaria: fileiras horizontais com blocos desencontrados, recortadas pela curva
	for j in 4:
		var yj := y_base - 14.0 - j * 15.0
		var desloc := (j % 2) * 23.0
		var xj := x0 + desloc
		while xj < x1:
			var u := (xj - x0) / (x1 - x0)
			var y_topo := y_base - alt - (pico - alt) * pow(sin(u * PI), 0.6)
			if yj > y_topo + 6.0:
				c.draw_line(Vector2(xj, yj), Vector2(xj, yj + 13.0), Color(0, 0, 0, 0.35), 1.5)
				c.draw_line(Vector2(xj, yj), Vector2(minf(xj + 46.0, x1), yj), Color(0, 0, 0, 0.28), 1.0)
				c.draw_line(Vector2(xj + 1, yj + 1), Vector2(minf(xj + 44.0, x1), yj + 1), Color(1, 1, 1, 0.05), 1.0)
			xj += 46.0
	# lajes com luz: blocos alternados mais claros e rebites nas juntas
	for j in 3:
		var yj2 := y_base - 22.0 - j * 15.0
		for k in 40:
			var xk := x0 + 20.0 + k * 46.0 + (j % 2) * 23.0
			if xk > x1 - 20.0:
				break
			var uk := (xk - x0) / (x1 - x0)
			var topo_k := y_base - alt - (pico - alt) * pow(sin(uk * PI), 0.6)
			if yj2 > topo_k + 10.0 and (k + j) % 2 == 0:
				c.draw_rect(Rect2(xk + 2.0, yj2 + 2.0, 40.0, 11.0), Color(1, 1, 1, 0.045))
				c.draw_rect(Rect2(xk + 2.0, yj2 + 11.0, 40.0, 2.0), Color(0, 0, 0, 0.22))
			if yj2 > topo_k + 10.0 and k % 3 == 1:
				rebite(c, Vector2(xk, yj2 + 7.0), 1.8)
	# veios de pedra (determinísticos)
	for k in 9:
		var u := 0.08 + k * 0.105
		var xa := lerpf(x0, x1, u)
		c.draw_line(Vector2(xa, y_base - 6), Vector2(xa + 10, y_base - alt * 0.7), Color(0, 0, 0, 0.25), 1.0)
	c.draw_polyline(topo, Color(0, 0, 0, 0.6), 8.0)
	c.draw_polyline(topo, _c("metal_medio"), 5.0)
	c.draw_polyline(topo, _c("metal_claro").darkened(0.1), 1.0)
	var fio := PackedVector2Array()
	for p in topo:
		fio.append(p + Vector2(0, 4))
	c.draw_polyline(fio, _c("destaque").darkened(0.3), 1.0)
	var meio := topo[n / 2]
	losango(c, meio + Vector2(0, 1), 7.0, _c("destaque"))
	for u in [0.18, 0.82]:
		rebite(c, topo[int(u * n)] + Vector2(0, 3), 2.2)

## Placa gótica em forma de estandarte: topo em arco ogival, laterais côncavas (cintura) e base em ponta central
## com ombros curvos, aro de ferro e gema no ápice.
static func placa_gotica(c: CanvasItem, r: Rect2, titulo: String, apoio: String) -> void:
	var forma := PackedVector2Array()
	var n := 16
	var arco_h := 15.0
	for i in n + 1:   # topo: ogiva
		var u := float(i) / n
		var d := absf(u - 0.5) * 2.0
		forma.append(Vector2(lerpf(r.position.x, r.end.x, u), r.position.y + arco_h * (1.0 - sqrt(maxf(0.0, 1.0 - d * d))) + arco_h * d * 0.25))
	for i in 1 + 8:   # lateral direita côncava, descendo até a base
		var u := float(i) / 8.0
		var y := lerpf(r.position.y + arco_h + 4.0, r.end.y - 14.0, u)
		forma.append(Vector2(r.end.x - sin(u * PI) * 7.0, y))
	forma.append(Vector2(r.end.x - 14.0, r.end.y - 4.0))
	forma.append(Vector2(r.get_center().x + 22.0, r.end.y - 6.0))
	forma.append(Vector2(r.get_center().x, r.end.y + 6.0))   # ponta central
	forma.append(Vector2(r.get_center().x - 22.0, r.end.y - 6.0))
	forma.append(Vector2(r.position.x + 14.0, r.end.y - 4.0))
	for i in range(8, -1, -1):   # lateral esquerda côncava, subindo
		var u := float(i) / 8.0
		var y := lerpf(r.position.y + arco_h + 4.0, r.end.y - 14.0, u)
		forma.append(Vector2(r.position.x + sin(u * PI) * 7.0, y))
	c.draw_colored_polygon(_deslocar(forma, 3.0), Color(0, 0, 0, 0.5))
	c.draw_colored_polygon(forma, _c("pedra"))
	c.draw_colored_polygon(_deslocar(forma, -5.0), _c("pedra").darkened(0.25))
	aro(c, forma, 3.5)
	losango(c, Vector2(r.get_center().x, r.position.y + 3), 5.5, _c("destaque"))
	losango(c, Vector2(r.get_center().x, r.end.y + 1), 4.0, _c("destaque"))
	texto(c, Vector2(r.position.x, r.position.y + arco_h + 22), titulo, 20, _c("destaque").lightened(0.2), HORIZONTAL_ALIGNMENT_CENTER, r.size.x, true)
	texto(c, Vector2(r.position.x, r.position.y + arco_h + 40), apoio, 14, _c("texto"), HORIZONTAL_ALIGNMENT_CENTER, r.size.x)

## Moldura de buff em losango (ícone recortado em losango) com etiqueta de nível.
static func buff_losango(c: CanvasItem, centro: Vector2, raio: float, icone: Texture2D, nivel: int, destaque := false) -> void:
	var f := PackedVector2Array([centro + Vector2(0, -raio), centro + Vector2(raio, 0), centro + Vector2(0, raio), centro + Vector2(-raio, 0)])
	c.draw_colored_polygon(_deslocar(f, 3.0), Color(0, 0, 0, 0.45))
	c.draw_colored_polygon(f, Color(0.04, 0.04, 0.05))
	var caixa := Rect2(centro - Vector2(raio, raio) * 0.72, Vector2(raio, raio) * 1.44)
	textura_em(c, icone, _deslocar(f, -3.0), caixa)
	aro(c, f, 3.0, true)
	if destaque:
		c.draw_polyline(_fechar(_deslocar(f, 3.0)), _c("destaque"), 2.0)
	if nivel > 1:
		texto(c, centro + Vector2(raio * 0.25, raio + 2), "x%d" % nivel, 12, _c("destaque").lightened(0.25))

## Ornamento de ferro sobre o aro do globo: crista com gema no topo e garras curvas nas diagonais de cima.
static func ornamento_globo(c: CanvasItem, centro: Vector2, raio: float) -> void:
	for ang in [-PI * 0.75, -PI * 0.25, PI * 0.82, PI * 0.18]:
		var dir := Vector2(cos(ang), sin(ang))
		garra(c, centro + dir * (raio - 2.0), dir, 11.0)
	var topo := centro + Vector2(0, -raio)
	var crista := PackedVector2Array([topo + Vector2(-14, 4), topo + Vector2(-6, -6), topo + Vector2(0, -15), topo + Vector2(6, -6), topo + Vector2(14, 4)])
	c.draw_colored_polygon(_deslocar(crista, 2.0), Color(0, 0, 0, 0.6))
	c.draw_colored_polygon(crista, _c("metal_medio"))
	c.draw_polyline(_fechar(crista), _c("metal_claro").darkened(0.1), 1.2)
	losango(c, topo + Vector2(0, -4), 4.5, _c("destaque"))

## Barra do chefe em forma de lâmina: canal com pontas afiadas, aro de ferro, chifres curvos nas extremidades e
## crista central com caveira. `y` = topo da crista; retorna o retângulo útil do canal (texto e fases vão dentro).
## `pcts` = porcentagens de vida em que cada fase começa (marcas douradas).
static func barra_chefe(c: CanvasItem, cx: float, y: float, frac: float, cor: Color, pcts: Array) -> Rect2:
	var larg := 640.0
	var alt := 24.0
	var cy := y + 46.0
	var x0 := cx - larg * 0.5
	var x1 := cx + larg * 0.5
	var ponta := 34.0
	var forma := PackedVector2Array([
		Vector2(x0 - ponta, cy), Vector2(x0 + 4.0, cy - alt * 0.5), Vector2(cx - 40.0, cy - alt * 0.5),
		Vector2(cx - 18.0, cy - alt * 0.5 - 7.0), Vector2(cx + 18.0, cy - alt * 0.5 - 7.0), Vector2(cx + 40.0, cy - alt * 0.5),
		Vector2(x1 - 4.0, cy - alt * 0.5), Vector2(x1 + ponta, cy), Vector2(x1 - 4.0, cy + alt * 0.5),
		Vector2(cx + 40.0, cy + alt * 0.5), Vector2(cx + 18.0, cy + alt * 0.5 + 7.0), Vector2(cx - 18.0, cy + alt * 0.5 + 7.0),
		Vector2(cx - 40.0, cy + alt * 0.5), Vector2(x0 + 4.0, cy + alt * 0.5)])
	var canal := Rect2(x0, cy - alt * 0.5, larg, alt)
	# chifres curvos nas extremidades, atrás do aro
	for lado in [-1.0, 1.0]:
		var base := Vector2(x1 if lado > 0 else x0, cy)
		var curva := PackedVector2Array()
		for i in 13:
			var u := float(i) / 12.0
			curva.append(base + Vector2(lado * (ponta * 0.5 + u * 30.0), -u * u * 34.0 - sin(u * PI) * 4.0))
		c.draw_polyline(curva, Color(0, 0, 0, 0.7), 11.0)
		c.draw_polyline(curva, _c("metal_medio"), 7.5)
		c.draw_polyline(curva, _c("metal_claro"), 1.2)
		losango(c, curva[12], 4.0, _c("destaque"))
	c.draw_colored_polygon(_deslocar(forma, 3.0), Color(0, 0, 0, 0.5))
	c.draw_colored_polygon(forma, Color(0.02, 0.015, 0.03))
	var f := clampf(frac, 0.0, 1.0)
	if f > 0.0:
		var enche := Rect2(x0 - ponta, cy - alt, larg + ponta * 2.0, alt * 2.0)
		enche.size.x = (larg + ponta * 2.0) * f
		var rect := PackedVector2Array([enche.position, Vector2(enche.end.x, enche.position.y), enche.end, Vector2(enche.position.x, enche.end.y)])
		for parte in Geometry2D.intersect_polygons(rect, forma):
			var cores := PackedColorArray()
			for v in parte:
				cores.append(cor.lightened(0.2).lerp(cor.darkened(0.5), clampf((v.y - (cy - alt * 0.5)) / alt, 0.0, 1.0)))
			c.draw_polygon(parte, cores)
		c.draw_rect(Rect2(x0, cy - alt * 0.5 + 1.0, larg * f, 3.0), Color(1, 1, 1, 0.18))
	for p in pcts:
		var xm := x0 + larg * float(p) / 100.0
		c.draw_rect(Rect2(xm - 1.5, cy - alt * 0.5, 3.0, alt), _c("destaque"))
	aro(c, forma, 5.0)
	# crista central com caveira
	var crista := PackedVector2Array([Vector2(cx - 30.0, cy - alt * 0.5 - 4.0), Vector2(cx - 14.0, cy - alt * 0.5 - 26.0), Vector2(cx, cy - alt * 0.5 - 40.0),
		Vector2(cx + 14.0, cy - alt * 0.5 - 26.0), Vector2(cx + 30.0, cy - alt * 0.5 - 4.0)])
	c.draw_colored_polygon(_deslocar(crista, 2.0), Color(0, 0, 0, 0.55))
	c.draw_colored_polygon(crista, _c("metal_escuro"))
	c.draw_polyline(_fechar(crista), _c("metal_medio"), 3.0)
	caveira(c, Vector2(cx, cy - alt * 0.5 - 17.0), 10.0)
	return canal

## Chifres de ferro curvos que sobem pelos lados do globo (por trás do aro), com ponta dourada.
static func chifres_globo(c: CanvasItem, centro: Vector2, raio: float) -> void:
	for lado in [-1.0, 1.0]:
		var curva := PackedVector2Array()
		for i in 15:
			var u := float(i) / 14.0
			var ang := lerpf(-PI * 0.12, -PI * 0.62, u) if lado > 0 else lerpf(-PI * 0.88, -PI * 0.38, u)
			var rr := raio * (1.04 + 0.16 * sin(u * PI * 0.9)) + u * 8.0
			curva.append(centro + Vector2(cos(ang), sin(ang)) * rr)
		c.draw_polyline(curva, Color(0, 0, 0, 0.7), 9.0)
		c.draw_polyline(curva, _c("metal_medio"), 6.0)
		c.draw_polyline(curva, _c("metal_claro").darkened(0.15), 1.4)
		losango(c, curva[14], 3.5, _c("destaque"))

# ---------------------------------------------------------------------------------------------------------------
# HUD v6 compacta: formas retas com poucos chanfros, moldura fina de ferro, sem faixa de fundo.
# ---------------------------------------------------------------------------------------------------------------

## Moldura fina de ferro (2 px) com um fio de luz em cima; o vão fica escuro e opaco o bastante para ler sobre o chão.
static func _moldura_fina(c: CanvasItem, forma: PackedVector2Array, ativo := true) -> void:
	c.draw_colored_polygon(_deslocar(forma, 2.0), Color(0, 0, 0, 0.35))
	c.draw_polyline(_fechar(forma), _c("metal_claro") if ativo else _c("metal_medio"), 2.0)
	c.draw_polyline(_fechar(_deslocar(forma, -2.0)), Color(0, 0, 0, 0.55), 1.0)

## Slot compacto (octógono suave): ícone, varredura de recarga, tinta azul sem recurso e tecla pequena no canto.
static func slot_mini(c: CanvasItem, r: Rect2, icone: Texture2D, recarga: float, tecla: String, brilho: Color, segundos := -1.0, sem_recurso := false) -> void:
	var forma := octogono(r, 0.16)
	var vao := _deslocar(forma, -2.0)
	c.draw_colored_polygon(_deslocar(forma, 2.0), Color(0, 0, 0, 0.35))
	c.draw_colored_polygon(vao, Color(0.03, 0.03, 0.045, 0.92))
	var tinta := Color(0.45, 0.55, 1.0, 0.75) if sem_recurso else Color.WHITE
	textura_em(c, icone, vao, r.grow(-2.0), tinta)
	if recarga > 0.0:
		var arco := PackedVector2Array([r.get_center()])
		for p in _arco(r.get_center(), r.size.x, -PI * 0.5, -PI * 0.5 + TAU * recarga, 24):
			arco.append(p)
		for parte in Geometry2D.intersect_polygons(arco, vao):
			c.draw_colored_polygon(parte, Color(0, 0, 0, 0.72))
	_moldura_fina(c, forma, recarga <= 0.0 and not sem_recurso)
	if recarga <= 0.0 and not sem_recurso:
		c.draw_polyline(_fechar(_deslocar(forma, -3.0)), Color(brilho.r, brilho.g, brilho.b, 0.35), 1.0)
	if recarga > 0.0 and segundos > 0.0:
		var txt := ("%d" % ceili(segundos)) if segundos >= 1.0 else ("%.1f" % segundos)
		texto(c, Vector2(r.position.x, r.get_center().y + 6.0), txt, 16, _c("texto"), HORIZONTAL_ALIGNMENT_CENTER, r.size.x)
	if tecla != "":
		tecla_canto(c, r, tecla)

## Tecla no canto do slot: plaquinha escura com letra clara de 12 px.
static func tecla_canto(c: CanvasItem, r: Rect2, tecla: String) -> void:
	var larg := ThemeDB.fallback_font.get_string_size(tecla, HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x + 6.0
	c.draw_rect(Rect2(r.position + Vector2(2, r.size.y - 16.0), Vector2(larg, 14.0)), Color(0, 0, 0, 0.75))
	texto(c, r.position + Vector2(5, r.size.y - 4.0), tecla, 12, Color(1, 0.95, 0.8))

## Encaixe vazio: vão escuro com moldura apagada e a tecla.
static func encaixe_mini(c: CanvasItem, r: Rect2, tecla: String) -> void:
	var forma := octogono(r, 0.16)
	c.draw_colored_polygon(_deslocar(forma, -2.0), Color(0.02, 0.02, 0.03, 0.7))
	_moldura_fina(c, forma, true)
	if tecla != "":
		cadeado(c, r.get_center() + Vector2(0, -8), 12.0)
		tecla_canto(c, r, tecla)

## Globo pequeno: vidro com líquido e aro fino de ferro, sem chifres.
static func globo_mini(c: CanvasItem, centro: Vector2, raio: float, frac: float, fantasma: float, escura: Color, clara: Color, t: float, pulso := 0.0, vazio := false) -> void:
	if pulso > 0.0:
		clara = clara.lightened(0.3 * pulso)
		escura = escura.lightened(0.18)
	var r_in := raio - 3.0
	c.draw_circle(centro + Vector2(0, 2), raio + 1.0, Color(0, 0, 0, 0.4))
	c.draw_circle(centro, raio, _c("metal_escuro"))
	c.draw_circle(centro, r_in, Color(0.02, 0.012, 0.02, 0.95))
	if not vazio:
		if fantasma > frac:
			liquido(c, centro, r_in, fantasma, Color(0.45, 0.12, 0.1), Color(0.95, 0.62, 0.45), t, 1.7)
		liquido(c, centro, r_in, frac, escura, clara, t)
	else:
		liquido(c, centro, r_in, 0.14, escura.darkened(0.5), clara.darkened(0.6), t, 0.9)
	for k in 3:
		c.draw_arc(centro, r_in - k * 1.2, 0.0, TAU, 32, Color(0, 0, 0, 0.3 - k * 0.08), 1.6)
	c.draw_arc(centro, r_in * 0.7, PI * 1.1, PI * 1.5, 12, Color(1, 1, 1, 0.22), 2.0)
	c.draw_arc(centro, raio - 1.0, 0.0, TAU, 40, _c("metal_claro"), 2.0)
	c.draw_arc(centro, raio, 0.0, TAU, 40, Color(0, 0, 0, 0.7), 1.0)
	if pulso > 0.0:
		c.draw_arc(centro, raio + 1.0, 0.0, TAU, 40, Color(1.0, 0.25, 0.2, 0.9 * pulso), 2.5)

## Plaquinha da sala e do tempo: retângulo com cantos chanfrados e duas linhas pequenas.
static func placa_mini(c: CanvasItem, r: Rect2, titulo: String, apoio: String) -> void:
	var forma := octogono(r, 0.2)
	c.draw_colored_polygon(forma, Color(0.04, 0.035, 0.05, 0.8))
	c.draw_polyline(_fechar(forma), _c("metal_medio"), 1.5)
	texto(c, Vector2(r.position.x, r.position.y + 15.0), titulo, 12, _c("texto"), HORIZONTAL_ALIGNMENT_CENTER, r.size.x)
	texto(c, Vector2(r.position.x, r.position.y + 29.0), apoio, 12, _c("texto_suave"), HORIZONTAL_ALIGNMENT_CENTER, r.size.x)

## Barra do chefe fina e curta: trilho escuro, preenchimento, marcas finas nas fases. Devolve o retângulo da barra.
static func barra_chefe_fina(c: CanvasItem, cx: float, y: float, largura: float, altura: float, frac: float, cor: Color, pcts: Array) -> Rect2:
	var r := Rect2(cx - largura * 0.5, y, largura, altura)
	var forma := octogono(r.grow(2.0), 0.25)
	c.draw_colored_polygon(forma, Color(0.03, 0.02, 0.04, 0.9))
	frac = clampf(frac, 0.0, 1.0)
	if frac > 0.0:
		c.draw_rect(Rect2(r.position, Vector2(r.size.x * frac, r.size.y)), cor)
		c.draw_rect(Rect2(r.position, Vector2(r.size.x * frac, 2.0)), Color(1, 1, 1, 0.22))
	for p in pcts:
		var x := r.position.x + r.size.x * (float(p) / 100.0 if float(p) > 1.0 else float(p))
		c.draw_line(Vector2(x, r.position.y - 1.0), Vector2(x, r.end.y + 1.0), Color(1, 1, 1, 0.6), 1.0)
	c.draw_polyline(_fechar(forma), _c("metal_claro"), 1.5)
	return r
