extends RefCounted
## Ícones geométricos (placeholders) de habilidades e cartas, desenhados por código a partir de data2d/icones.csv.
## A arte final entra no passe visual: basta o PNG em art2d/ui/icone_<id>.png, que tem prioridade.

const Csv = preload("res://scripts2d/csv2d.gd")

const LADO := 64   # resolução interna; a tela escala

# Polígonos em coordenadas 0..1 (y para baixo)
const POLIGONOS := {
	"seta": [[[0.5, 0.06], [0.82, 0.42], [0.58, 0.42], [0.58, 0.94], [0.42, 0.94], [0.42, 0.42], [0.18, 0.42]]],
	"raio": [[[0.60, 0.04], [0.22, 0.56], [0.46, 0.56], [0.36, 0.96], [0.80, 0.40], [0.56, 0.40]]],
	"bota": [[[0.30, 0.10], [0.58, 0.10], [0.58, 0.52], [0.86, 0.66], [0.86, 0.88], [0.30, 0.88]]],
	"leque": [[[0.50, 0.92], [0.44, 0.10], [0.56, 0.10]], [[0.50, 0.92], [0.08, 0.28], [0.18, 0.20]], [[0.50, 0.92], [0.92, 0.28], [0.82, 0.20]]],
	"lanca": [[[0.50, 0.04], [0.68, 0.30], [0.54, 0.30], [0.54, 0.96], [0.46, 0.96], [0.46, 0.30], [0.32, 0.30]]],
	"passo": [[[0.10, 0.50], [0.40, 0.18], [0.40, 0.38], [0.90, 0.38], [0.90, 0.62], [0.40, 0.62], [0.40, 0.82]]],
	"espada": [[[0.5, 0.04], [0.62, 0.2], [0.58, 0.62], [0.42, 0.62], [0.38, 0.2]], [[0.22, 0.62], [0.78, 0.62], [0.78, 0.72], [0.22, 0.72]], [[0.45, 0.72], [0.55, 0.72], [0.55, 0.94], [0.45, 0.94]]],
	"escudo": [[[0.18, 0.12], [0.82, 0.12], [0.82, 0.5], [0.5, 0.94], [0.18, 0.5]]],
	"chama": [[[0.5, 0.04], [0.7, 0.34], [0.84, 0.6], [0.7, 0.9], [0.3, 0.9], [0.16, 0.6], [0.34, 0.4], [0.4, 0.22]]],
	"impacto": [[[0.5, 0.06], [0.6, 0.36], [0.92, 0.3], [0.7, 0.54], [0.88, 0.84], [0.56, 0.7], [0.4, 0.94], [0.36, 0.62], [0.08, 0.5], [0.38, 0.4]]],
	"onda": [[[0.06, 0.8], [0.3, 0.3], [0.5, 0.6], [0.7, 0.2], [0.94, 0.8]]],
	"cadeado": [[[0.24, 0.46], [0.76, 0.46], [0.76, 0.90], [0.24, 0.90]], [[0.32, 0.46], [0.32, 0.30], [0.40, 0.14], [0.60, 0.14], [0.68, 0.30], [0.68, 0.46], [0.60, 0.46], [0.60, 0.30], [0.40, 0.30], [0.40, 0.46]]],
}

static var _cache := {}

static func textura(id: String) -> Texture2D:
	if _cache.has(id):
		return _cache[id]
	var tex: Texture2D = null
	var caminho := "res://art2d/ui/icone_%s.png" % id
	if ResourceLoader.exists(caminho):
		tex = load(caminho)
	else:
		for r in Csv.rows("res://data2d/icones.csv"):
			if r["id"] == id:
				tex = _desenhar(r["forma"], Color.html(r["cor"]))
				break
	_cache[id] = tex
	return tex

static func _desenhar(forma: String, cor: Color) -> ImageTexture:
	var img := Image.create(LADO, LADO, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	if forma == "coracao":
		_coracao(img, cor)
	else:
		for poli in POLIGONOS.get(forma, []):
			_poligono(img, poli, cor)
	return ImageTexture.create_from_image(img)

static func _poligono(img: Image, pts: Array, cor: Color) -> void:
	var v := PackedVector2Array()
	for p in pts:
		v.append(Vector2(p[0], p[1]) * LADO)
	var contorno := cor.darkened(0.45)
	for y in LADO:
		for x in LADO:
			var q := Vector2(x + 0.5, y + 0.5)
			if Geometry2D.is_point_in_polygon(q, v):
				img.set_pixel(x, y, cor)
	# borda escura de 1 px: pixel preenchido com vizinho vazio
	for y in range(1, LADO - 1):
		for x in range(1, LADO - 1):
			if img.get_pixel(x, y).a > 0.0 and (img.get_pixel(x - 1, y).a == 0.0 or img.get_pixel(x + 1, y).a == 0.0 or img.get_pixel(x, y - 1).a == 0.0 or img.get_pixel(x, y + 1).a == 0.0):
				img.set_pixel(x, y, contorno)

static func _coracao(img: Image, cor: Color) -> void:
	for y in LADO:
		for x in LADO:
			var px := ((x + 0.5) / LADO - 0.5) * 2.6
			var py := -((y + 0.5) / LADO - 0.55) * 2.6
			var a := px * px + py * py - 1.0
			if a * a * a - px * px * py * py * py <= 0.0:
				img.set_pixel(x, y, cor)
	for y in range(1, LADO - 1):
		for x in range(1, LADO - 1):
			if img.get_pixel(x, y).a > 0.0 and (img.get_pixel(x - 1, y).a == 0.0 or img.get_pixel(x + 1, y).a == 0.0 or img.get_pixel(x, y - 1).a == 0.0 or img.get_pixel(x, y + 1).a == 0.0):
				img.set_pixel(x, y, cor.darkened(0.45))
