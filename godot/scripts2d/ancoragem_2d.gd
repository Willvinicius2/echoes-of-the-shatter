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
static var _tex_contato: Texture2D

## Classe visual do prop pelo id: árvore (raízes, sombra longa), raso (ossos, folhas: só contato leve),
## folhagem (arbustos: contato e terra curta) ou sólido (tumbas, pedras, pilares).
static func tipo(id: String) -> String:
	if id == "tree_stump":
		return "solido"
	if id.begins_with("tree_") or id.begins_with("sapling_"):
		return "arvore"
	for pre in ["leaves_", "bones_", "skeleton_", "skull_single", "skull_pair", "skull_teal", "branches_", "flowers_", "grass_", "roots_"]:
		if id.begins_with(pre):
			return "raso"
	for pre in ["bush_", "shrub_", "ferns_", "reeds_", "thistles_"]:
		if id.begins_with(pre):
			return "folhagem"
	return "solido"

## `chao`: nó da sala para os decalques. `atras` e `frente`: filhos do nó do prop antes e depois do sprite.
## `pe`: posição do pé do prop (mesma do nó). `def` vem de props_2d.csv, `arte` de props_manifest.csv.
static func prender(chao: Node2D, atras: Node2D, frente: Node2D, id: String, tex: Texture2D, def: Dictionary, arte: Dictionary, flip: bool, pe: Vector2, grama: bool, semente: int) -> void:
	var esc := float(def["escala"])
	var t := tipo(id)
	var larg_tex := tex.get_width() * esc
	var bl := float(def["solido_l"])
	var ba := float(def["solido_a"])
	if bl <= 0.0:
		bl = larg_tex * (0.5 if t == "raso" else 0.6)
	if ba <= 0.0:
		ba = bl * 0.36
	var centro := pe + Vector2(0, -ba * 0.45)  # centro da base desenhada no sprite (o pé é a aresta da frente)
	if t == "arvore":
		# nas árvores a folhagem caída desce abaixo do tronco: o pé do tronco é medido na própria textura
		centro = pe + Vector2(0, -_altura_pe_tronco(tex, float(arte["pivo_x"])) * esc - ba * 0.3)
	var h := hash(Vector2i(semente, 71))
	if grama and t != "raso":
		_terra(chao, centro, bl, ba, t, h)
	if t != "raso":
		_sombra_projetada(chao, tex, esc, arte, flip, centro, t)
	_sombra_contato(chao, centro, bl, ba, t)
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
	var f := 0.75 if t == "folhagem" else 1.0
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
	anel.call(1.45, Color(0.19, 0.15, 0.09, 0.22), Vector2(3, 2))
	anel.call(1.1, Color(0.2, 0.15, 0.09, 0.42), Vector2(2, 1))
	anel.call(0.8, Color(0.16, 0.12, 0.07, 0.55), Vector2(1, 0))

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
	var alfa := 0.3 if t == "raso" else 0.55
	var largo := Sprite2D.new()
	largo.texture = _tex_contato
	largo.position = centro + Vector2(4, 3)
	largo.scale = Vector2(bl * 1.5, ba * 1.9) / 128.0
	largo.modulate = Color(0.02, 0.03, 0.04, alfa * 0.8)
	chao.add_child(largo)
	var nucleo := Sprite2D.new()
	nucleo.texture = _tex_contato
	nucleo.position = centro + Vector2(1, 1)
	nucleo.scale = Vector2(bl * 1.05, ba * 1.25) / 128.0
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
