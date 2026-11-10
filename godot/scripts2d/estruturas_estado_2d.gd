extends RefCounted
## Estados visuais do braseiro e do pilar do mapa (reações do mapa, reacoes_2d.gd), tirados da MESMA arte aprovada
## do atlas da Cripta: nada de arte nova, só recolorir os pixels que já existem.
##   braseiro apagado   a chama vira cinza e brasa fraca (o topo da chama some)
##   braseiro carregado a chama vira azul e branco (descarga de raio)
##   pilar carregado    as runas douradas viram azul-gelo e branco (para-raios)
## A faixa devolvida tem 3 tiles lado a lado, na ordem ESTADO_*.

const ESTADO_BRASEIRO_APAGADO := 0
const ESTADO_BRASEIRO_CARREGADO := 1
const ESTADO_PILAR_CARREGADO := 2
const LINHA_TOPO_CHAMA := 14   # acima disto, pixel de chama é a ponta que sai do cálice: some quando apaga

static func _luma(c: Color) -> float:
	return c.r * 0.3 + c.g * 0.59 + c.b * 0.11

static func _chama(c: Color) -> bool:
	return c.a > 0.04 and c.r > c.g + 0.15 and c.r > c.b + 0.23

static func _runa(c: Color) -> bool:
	return c.a > 0.04 and c.r > 0.55 and c.g > 0.36 and c.b < 0.38 and c.r > c.b + 0.3

static func _cinza(l: float, ponto: int) -> Color:
	if ponto % 7 == 0:
		return Color(0.55, 0.16, 0.1)   # brasa fraca que sobrou
	if l > 0.62:
		return Color(0.42, 0.4, 0.43)
	if l > 0.42:
		return Color(0.3, 0.29, 0.32)
	return Color(0.19, 0.18, 0.21)

static func _azul(l: float) -> Color:
	if l > 0.72:
		return Color(0.96, 1.0, 1.0)
	if l > 0.5:
		return Color(0.62, 0.9, 1.0)
	return Color(0.28, 0.55, 0.95)

## `atlas`: imagem RGBA8 do atlas da Cripta; `idx_braseiro`/`idx_pilar`: índices dos tiles; `tile`: lado em px.
static func faixa(atlas: Image, idx_braseiro: int, idx_pilar: int, tile: int) -> ImageTexture:
	var cols: int = atlas.get_width() / tile
	var out := Image.create(tile * 3, tile, false, Image.FORMAT_RGBA8)
	var br := Rect2i((idx_braseiro % cols) * tile, (idx_braseiro / cols) * tile, tile, tile)
	var pl := Rect2i((idx_pilar % cols) * tile, (idx_pilar / cols) * tile, tile, tile)
	for y in tile:
		for x in tile:
			var c := atlas.get_pixel(br.position.x + x, br.position.y + y)
			var ca := c
			var cb := c
			if _chama(c):
				if y < LINHA_TOPO_CHAMA * tile / 64:
					ca = Color(0, 0, 0, 0)
				else:
					ca = _cinza(_luma(c), x * 3 + y)
				cb = _azul(_luma(c))
			out.set_pixel(x, y, ca)
			out.set_pixel(tile + x, y, cb)
			var p := atlas.get_pixel(pl.position.x + x, pl.position.y + y)
			if _runa(p):
				p = _azul(_luma(p) + 0.18)
			out.set_pixel(tile * 2 + x, y, p)
	return ImageTexture.create_from_image(out)

## O pilar rúnico da estrada (props/pillar_runes): a mesma arte com o dourado das runas trocado por azul-gelo e branco.
static func runas_azuis(tex: Texture2D) -> ImageTexture:
	var img: Image = tex.get_image()
	img.convert(Image.FORMAT_RGBA8)
	for y in img.get_height():
		for x in img.get_width():
			var c := img.get_pixel(x, y)
			if _runa(c):
				img.set_pixel(x, y, _azul(_luma(c) + 0.18))
	return ImageTexture.create_from_image(img)
