extends RefCounted
## Prende um prop ao chão (pacote H5, decisão do Jev em 31/10/2026): sombra projetada com a silhueta do
## próprio sprite (luz de cima-esquerda, sombra para baixo-direita), sombra de contato escura sob a base,
## terra pisada e tufos de capim encostados no pé quando o piso é gramado, e raízes nas árvores.
## Os decalques de chão vão num nó da sala (sob todos os atores); só os tufos ficam no nó do prop,
## atrás e à frente do sprite, para o y-sort continuar valendo.

const Terreno = preload("res://scripts2d/terreno_2d.gd")

const SOMBRA_SHADER := """
shader_type canvas_item;
uniform vec4 cor : source_color = vec4(0.0, 0.0, 0.0, 0.4);
void fragment() {
	COLOR = vec4(cor.rgb, texture(TEXTURE, UV).a * cor.a);
}
"""

static var _mat_sombra: ShaderMaterial
static var _linhas_base := {}
static var _tex_contato: Texture2D

## Classe visual do prop pelo id: árvore (raízes, sombra longa), raso (ossos, folhas, capim, samambaia:
## só contato leve e fica no chão, fora do y-sort), folhagem (arbustos: contato, terra curta, y-sort pelo
## centro da base e semitransparente quando alguém passa atrás) ou sólido (tumbas, pedras, pilares).
static func tipo(id: String) -> String:
	if id == "tree_stump":
		return "solido"
	if id.begins_with("tree_") or id.begins_with("sapling_"):
		return "arvore"
	for pre in ["leaves_", "bones_", "skeleton_", "skull_single", "skull_pair", "skull_teal", "branches_", "flowers_", "grass_", "roots_", "ferns_", "reeds_", "thistles_"]:
		if id.begins_with(pre):
			return "raso"
	for pre in ["bush_", "shrub_"]:
		if id.begins_with(pre):
			return "folhagem"
	return "solido"

## Base que toca o chão, em px já na escala do prop: [largura, profundidade]. Vem de solido_l/solido_a do
## props_2d.csv; sem sólido, uma fração da largura do sprite.
static func base(id: String, tex: Texture2D, def: Dictionary) -> Array:
	var esc := float(def["escala"])
	var t := tipo(id)
	var bl := float(def["solido_l"])
	var ba := float(def["solido_a"])
	if bl <= 0.0:
		bl = tex.get_width() * esc * (0.5 if t == "raso" else 0.6)
	if ba <= 0.0:
		# arbusto visto de cima em 3/4: a base ocupa boa parte da silhueta, então o centro dela fica bem
		# acima da borda de baixo (decisão do Jev, 1/11: y-sort pelo centro da base + transparência)
		ba = tex.get_height() * esc * 0.55 if t == "folhagem" else bl * 0.36
	return [bl, ba]

## Altura (px acima do pé do sprite) do ponto de apoio: o centro da base que toca o chão. É por esse ponto
## que o prop entra no y-sort com os atores e onde fica a colisão. Nas árvores a folhagem caída desce
## abaixo do tronco, então a base do tronco é medida na própria textura; sem isso a copa cobria a cabeça
## de quem passava ao lado.
static func apoio(id: String, tex: Texture2D, def: Dictionary, arte: Dictionary) -> float:
	var b := base(id, tex, def)
	var a: float = b[1] * 0.5
	if tipo(id) == "arvore":
		a += _altura_pe_tronco(tex, float(arte["pivo_x"])) * float(def["escala"])
	return a

## Linha de baixo opaca da textura (fração 0..1 da altura): onde a base realmente toca o chão.
static func _linha_base(tex: Texture2D) -> float:
	var chave := tex.get_rid()
	if _linhas_base.has(chave):
		return _linhas_base[chave]
	var r := 1.0
	var img := tex.get_image()
	if img != null:
		for y in range(img.get_height() - 1, -1, -1):
			var achou := false
			for x in range(0, img.get_width(), 2):
				if img.get_pixel(x, y).a > 0.5:
					achou = true
					break
			if achou:
				r = float(y + 1) / float(img.get_height())
				break
	_linhas_base[chave] = r
	return r

## Altura da faixa de contato em fração da textura: ~metade da profundidade da base, no mínimo 8 px do sprite.
static func _faixa(id: String, tex: Texture2D, def: Dictionary) -> float:
	var b := base(id, tex, def)
	var px := maxf(float(b[1]) / float(def["escala"]) * 1.7, 28.0)
	return clampf(px / float(tex.get_height()), 0.02, 0.3)

## Textura do sprite do prop com a faixa colada ao contorno de baixo escurecida (a base "afunda" no chão).
## Props sólidos e arbustos; árvores (folhas caídas abaixo do tronco) e rasos ficam com a textura original.
## Devolve null quando não se aplica.
static func textura_base(id: String, tex: Texture2D, def: Dictionary) -> Texture2D:
	var t := tipo(id)
	if t == "arvore" or t == "raso":
		return null
	var c := contorno(id, tex, def)
	return c.get("base", null)


static var _cont_cache := {}

## Contorno de apoio da base: para cada coluna do sprite, a linha de baixo opaca. Devolve
## {"base": textura igual à do sprite com a faixa colada ao contorno escurecida, "sombra": textura só de alfa
## preta que sai do contorno para baixo (a sombra de contato com a forma real da base)}. A elipse de antes ficava
## sob a ponta da frente e deixava as arestas diagonais da base sem contato; agora o escuro segue cada aresta.
static func contorno(id: String, tex: Texture2D, def: Dictionary) -> Dictionary:
	if _cont_cache.has(id):
		return _cont_cache[id]
	var img := tex.get_image()
	if img == null:
		_cont_cache[id] = {}
		return {}
	if img.is_compressed():
		img.decompress()
	img.convert(Image.FORMAT_RGBA8)
	var w := img.get_width()
	var h := img.get_height()
	var prof := float(base(id, tex, def)[1]) / float(def["escala"])
	var faixa := clampf(prof * 0.9, 10.0, 34.0)      # px da textura acima do contorno que escurecem
	var queda := clampf(prof * 0.55, 6.0, 18.0)       # px da textura abaixo do contorno com sombra
	var yb := PackedFloat32Array()
	yb.resize(w)
	for x in w:
		yb[x] = -1.0
		for y in range(h - 1, -1, -1):
			if img.get_pixel(x, y).a > 0.5:
				yb[x] = float(y)
				break
	var pad := int(queda) + 6
	var base_img := img.duplicate() as Image
	var sombra := Image.create(w + 12, h + pad, false, Image.FORMAT_RGBA8)
	var col := PackedFloat32Array()
	col.resize(w + 12)
	for x in w:
		if yb[x] < 0.0:
			continue
		for y in range(maxi(int(yb[x] - faixa), 0), int(yb[x]) + 1):
			var px := base_img.get_pixel(x, y)
			if px.a < 0.05:
				continue
			var k := 1.0 - (yb[x] - float(y)) / faixa
			k = k * k * (3.0 - 2.0 * k)
			var f := 1.0 - 0.6 * k
			base_img.set_pixel(x, y, Color(px.r * f * 0.95, px.g * f * 0.95, px.b * f, px.a))
	# sombra: por coluna, alfa cai do contorno para baixo; depois espalha 5 px para os lados (borrão leve)
	for x in w:
		if yb[x] < 0.0:
			continue
		for d in range(-2, int(queda) + 1):
			var y := int(yb[x]) + d
			if y < 0 or y >= h + pad:
				continue
			var a := 0.85 * pow(1.0 - clampf(float(d) / queda, 0.0, 1.0), 1.4)
			for dx in range(-5, 6):
				var xx := x + dx + 6
				var aa := a * (1.0 - absf(float(dx)) / 6.0)
				if xx >= 0 and xx < w + 12 and aa > sombra.get_pixel(xx, y).a:
					sombra.set_pixel(xx, y, Color(0.0, 0.0, 0.01, aa))
	col.clear()
	var r := {"base": ImageTexture.create_from_image(base_img), "sombra": ImageTexture.create_from_image(sombra)}
	_cont_cache[id] = r
	return r

## `chao`: nó da sala para os decalques. `atras` e `frente`: filhos do nó do prop antes e depois do sprite.
## `pe`: posição do pé do prop (mesma do nó). `def` vem de props_2d.csv, `arte` de props_manifest.csv.
static func prender(chao: Node2D, atras: Node2D, frente: Node2D, id: String, tex: Texture2D, def: Dictionary, arte: Dictionary, flip: bool, pe: Vector2, grama: bool, semente: int) -> void:
	var esc := float(def["escala"])
	var t := tipo(id)
	var b := base(id, tex, def)
	var bl: float = b[0]
	var ba: float = b[1]
	var centro := pe + Vector2(0, -apoio(id, tex, def, arte))  # centro da base que toca o chão (mesmo ponto do y-sort)
	var h := hash(Vector2i(semente, 71))
	if grama:
		_terra(chao, centro, bl, ba, t, h)
	if t != "raso":
		_sombra_projetada(chao, tex, esc, arte, flip, centro, t)
	_sombra_contato(chao, centro, bl, ba, t)
	if t == "solido" or t == "folhagem":
		_sombra_borda(chao, tex, id, def, arte, flip, pe, t)
	if not grama and t == "solido":
		_entulho(chao, centro, bl, ba, h)
	if t == "arvore":
		_raizes(chao, centro, bl, esc, h)
	if grama and (t == "solido" or t == "arvore"):
		_tufos(atras, frente, bl, ba, h)

static var _cache_pe := {}

## Quantos px (da textura) acima da borda de baixo fica a base do tronco: primeira linha, de baixo para cima,
## em que a faixa central (±7% da largura em volta do pivô) está quase toda opaca.
static func _altura_pe_tronco(tex: Texture2D, pivo_x: float) -> float:
	var chave := tex.get_rid()
	if _cache_pe.has(chave):
		return _cache_pe[chave]
	var img := tex.get_image()
	var alt := 0.0
	if img != null:
		var meia := maxi(int(img.get_width() * 0.07), 3)
		var x0 := maxi(int(pivo_x) - meia, 0)
		var x1 := mini(int(pivo_x) + meia, img.get_width() - 1)
		for y in range(img.get_height() - 1, int(img.get_height() * 0.5), -1):
			var opacos := 0
			for x in range(x0, x1 + 1):
				if img.get_pixel(x, y).a > 0.5:
					opacos += 1
			if opacos >= (x1 - x0 + 1) * 0.8:
				alt = float(img.get_height() - 1 - y)
				break
	_cache_pe[chave] = alt
	return alt

## Anel de terra pisada irregular, mais escuro perto da base e esmaecido fora, para o pé não encostar
## direto na grama chapada.
static func _terra(chao: Node2D, centro: Vector2, bl: float, ba: float, t: String, h: int) -> void:
	var f := 0.75 if t == "folhagem" else (0.6 if t == "raso" else 1.0)
	var rx := (bl * 0.7 + 8.0) * f
	var ry := (ba * 0.9 + 6.0) * f
	var anel := func(k: float, cor: Color, desloc: Vector2) -> void:
		var pts := PackedVector2Array()
		for a in 14:
			var ang := TAU * a / 14.0
			var r := 0.82 + 0.36 * float(posmod(h / (a + 2) + int(k * 10.0), 100)) / 100.0
			pts.append(centro + desloc + Vector2(cos(ang) * rx * k * r, sin(ang) * ry * k * r))
		var pg := Polygon2D.new()
		pg.polygon = pts
		pg.color = cor
		chao.add_child(pg)
	anel.call(1.45, Color(0.15, 0.12, 0.07, 0.3), Vector2(3, 2))
	anel.call(1.1, Color(0.15, 0.11, 0.07, 0.55), Vector2(2, 1))
	anel.call(0.8, Color(0.1, 0.08, 0.05, 0.7), Vector2(1, 0))

## Sombra com a silhueta do sprite deitada no chão: espelhada no pé, achatada e inclinada para a direita.
static func _sombra_projetada(chao: Node2D, tex: Texture2D, esc: float, arte: Dictionary, flip: bool, centro: Vector2, t: String) -> void:
	if _mat_sombra == null:
		_mat_sombra = ShaderMaterial.new()
		_mat_sombra.shader = Shader.new()
		_mat_sombra.shader.code = SOMBRA_SHADER
		_mat_sombra.set_shader_parameter("cor", Color(0.02, 0.03, 0.05, 0.34))
	var sp := Sprite2D.new()
	sp.texture = tex
	sp.centered = false
	sp.flip_h = flip
	sp.offset = -Vector2(float(arte["pivo_x"]), float(arte["pivo_y"]))
	if flip:
		sp.offset.x = -(tex.get_width() - float(arte["pivo_x"]))
	sp.material = _mat_sombra
	var achata := 0.46 if t == "arvore" else (0.3 if t == "folhagem" else 0.4)
	var inclina := 0.6 if t == "arvore" else 0.5
	# ponto local (x, y) com y <= 0 acima do pé vira (x*esc - y*esc*inclina, -y*esc*achata): deitado e para baixo-direita
	sp.transform = Transform2D(Vector2(esc, 0.0), Vector2(-inclina * esc, -achata * esc), centro)
	sp.self_modulate.a = 0.8 if t == "folhagem" else 1.0
	chao.add_child(sp)

## Sombra de contato com a forma real da base (ver `contorno`): sai de cada aresta de baixo do sprite, então as
## diagonais da base de um pilar ou tumba encostam no chão em vez de só a ponta da frente.
static func _sombra_borda(chao: Node2D, tex: Texture2D, id: String, def: Dictionary, arte: Dictionary, flip: bool, pe: Vector2, t: String) -> void:
	var c := contorno(id, tex, def)
	if c.is_empty():
		return
	var esc := float(def["escala"])
	var sp := Sprite2D.new()
	sp.texture = c["sombra"]
	sp.centered = false
	sp.flip_h = flip
	var ox := float(arte["pivo_x"]) + 6.0   # a textura de sombra tem 6 px de folga de cada lado
	sp.offset = -Vector2(ox, float(arte["pivo_y"]))
	if flip:
		sp.offset.x = -(float(c["sombra"].get_width()) - ox)
	sp.position = pe + Vector2(1.0, 1.5)
	sp.scale = Vector2.ONE * esc
	sp.modulate.a = 0.6 if t == "folhagem" else 1.0
	chao.add_child(sp)

## Lascas de pedra e poeira soltas junto da base em piso de pedra (no gramado quem faz isso são terra e capim).
static func _entulho(chao: Node2D, centro: Vector2, bl: float, ba: float, h: int) -> void:
	var n := 5 + posmod(h / 3, 3)
	for k in n:
		var hh := hash(Vector2i(h, k + 90))
		var ang := TAU * float(posmod(hh, 360)) / 360.0
		var raio := 0.62 + 0.3 * float(posmod(hh / 7, 10)) / 10.0
		var p := centro + Vector2(cos(ang) * (bl * 0.5 + 3.0) * raio * 1.15, sin(ang) * (ba * 0.5 + 3.0) * raio * 1.1 + 2.0)
		var w := 3.0 + float(posmod(hh / 5, 5))
		var sombra := Polygon2D.new()
		sombra.polygon = PackedVector2Array([Vector2(-w, 0.5), Vector2(0, -w * 0.5 + 0.5), Vector2(w + 1.5, 1.0), Vector2(w * 0.4, w * 0.6 + 1.5), Vector2(-w * 0.6, w * 0.5 + 1.0)])
		sombra.position = p + Vector2(1.0, 1.0)
		sombra.color = Color(0.0, 0.0, 0.01, 0.5)
		chao.add_child(sombra)
		var lasca := Polygon2D.new()
		lasca.polygon = PackedVector2Array([Vector2(-w, 0.0), Vector2(-w * 0.3, -w * 0.55), Vector2(w * 0.8, -w * 0.3), Vector2(w, w * 0.2), Vector2(0, w * 0.5)])
		lasca.position = p
		var v := 0.22 + 0.1 * float(posmod(hh / 11, 10)) / 10.0
		lasca.color = Color(v + 0.03, v, v - 0.02)
		chao.add_child(lasca)
		var luz := Polygon2D.new()
		luz.polygon = PackedVector2Array([Vector2(-w * 0.8, -0.2), Vector2(-w * 0.3, -w * 0.5), Vector2(w * 0.5, -w * 0.3), Vector2(0, -w * 0.05)])
		luz.position = p
		luz.color = Color(v + 0.14, v + 0.12, v + 0.08, 0.8)
		chao.add_child(luz)

## Sombra de contato: oclusão escura e macia colada à base, mais um núcleo mais fechado.
static func _sombra_contato(chao: Node2D, centro: Vector2, bl: float, ba: float, t: String) -> void:
	if _tex_contato == null:
		var g := Gradient.new()
		g.set_color(0, Color(0, 0, 0, 1))
		g.add_point(0.55, Color(0, 0, 0, 0.55))
		g.set_color(g.get_point_count() - 1, Color(0, 0, 0, 0))
		var tx := GradientTexture2D.new()
		tx.gradient = g
		tx.width = 128
		tx.height = 128
		tx.fill = GradientTexture2D.FILL_RADIAL
		tx.fill_from = Vector2(0.5, 0.5)
		tx.fill_to = Vector2(1.0, 0.5)
		_tex_contato = tx
	var alfa := 0.4 if t == "raso" else 0.75
	var largo := Sprite2D.new()
	largo.texture = _tex_contato
	largo.position = centro + Vector2(4, 3 + ba * 0.22)
	largo.scale = Vector2(bl * 1.6, ba * 2.0) / 128.0
	largo.modulate = Color(0.02, 0.03, 0.04, alfa * 0.8)
	chao.add_child(largo)
	var nucleo := Sprite2D.new()
	nucleo.texture = _tex_contato
	nucleo.position = centro + Vector2(1, 1 + ba * 0.3)
	nucleo.scale = Vector2(bl * 1.15, ba * 1.4) / 128.0
	nucleo.modulate = Color(0.02, 0.02, 0.03, alfa)
	chao.add_child(nucleo)

## Raízes: abas curtas e largas que saem do pé do tronco em 4 direções e afinam no chão, na cor da casca,
## com um fio de luz em cima e sombra fina embaixo (nada de lâminas soltas).
static func _raizes(chao: Node2D, centro: Vector2, bl: float, esc: float, h: int) -> void:
	var angulos := [-30.0, 25.0, 155.0, 210.0]
	for i in angulos.size():
		var hh := hash(Vector2i(h, i))
		var ang := deg_to_rad(angulos[i] + float(posmod(hh, 20)) - 10.0)
		var dir := Vector2(cos(ang), sin(ang) * 0.45).normalized()
		var perp := Vector2(-dir.y, dir.x)
		var comp := (bl * 0.4 + 4.0 + float(posmod(hh / 7, 6))) * clampf(esc / 0.6, 0.7, 1.2)
		var ini := centro + dir * bl * 0.12
		var fim := ini + dir * comp
		var meio := ini.lerp(fim, 0.45) + perp * (float(posmod(hh / 13, 5)) - 2.0)
		var l0 := 3.0 + bl * 0.16
		var pts := PackedVector2Array([ini + perp * l0, meio + perp * l0 * 0.5, fim + perp * 0.5, fim - perp * 0.5, meio - perp * l0 * 0.5, ini - perp * l0])
		var sombra := Polygon2D.new()
		sombra.polygon = pts
		sombra.position = Vector2(1.0, 1.5)
		sombra.color = Color(0.03, 0.03, 0.03, 0.35)
		chao.add_child(sombra)
		var raiz := Polygon2D.new()
		raiz.polygon = pts
		raiz.color = Color(0.25, 0.17, 0.11)
		chao.add_child(raiz)
		var luz := Polygon2D.new()
		luz.polygon = PackedVector2Array([ini + perp * l0 * 0.45, meio + perp * l0 * 0.15, fim, meio - perp * l0 * 0.1, ini - perp * l0 * 0.1])
		luz.position = Vector2(-0.6, -1.0)
		luz.color = Color(0.4, 0.29, 0.18)
		chao.add_child(luz)

## Dois ou três tufos de capim seco e folhas encostados na base: os de trás ficam sob o sprite, o da frente
## cobre um pouco o pé, que é o que mais vende o contato com o chão.
static func _tufos(atras: Node2D, frente: Node2D, bl: float, ba: float, h: int) -> void:
	var ids := ["grass_dry_patch", "grass_dry_tall", "leaves_scattered", "thistles_dry"]
	var n := 2 + posmod(h / 5, 2)
	for k in n:
		var hh := hash(Vector2i(h, k + 40))
		var arte := Terreno._arte_prop(ids[posmod(hh, ids.size())])
		if arte.is_empty():
			continue
		var sp := Sprite2D.new()
		sp.texture = arte[0]
		sp.centered = false
		sp.offset = -Vector2(arte[1], arte[2])
		sp.scale = Vector2.ONE * (0.13 + 0.05 * float(posmod(hh / 7, 10)) / 10.0)
		sp.flip_h = posmod(hh / 3, 2) == 0
		sp.modulate = Color(0.85, 0.82, 0.78)
		var lado := -1.0 if k % 2 == 0 else 1.0
		var na_frente: bool = k == n - 1
		sp.position = Vector2(lado * (bl * 0.42 + float(posmod(hh / 11, 10))), (ba * 0.15 + 2.0) if na_frente else (-ba * 0.7 - 2.0))
		if na_frente:
			sp.position.x = lado * (bl * 0.25 + float(posmod(hh / 11, 8)))
			frente.add_child(sp)
		else:
			atras.add_child(sp)
