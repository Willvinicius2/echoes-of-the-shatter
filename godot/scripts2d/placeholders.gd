extends RefCounted
## Folhas e tiles provisórios no mesmo formato da arte final (docs/arte/25_formato_folhas_sprites_2d.md).
## Servem só até as folhas aprovadas chegarem em res://art2d/.

const COR := {
	"arqueiro": Color(0.25, 0.65, 0.3),
	"guerreiro": Color(0.6, 0.65, 0.75),
	"hollow_sentinel": Color(0.6, 0.6, 0.65),
	"ash_hound": Color(0.55, 0.4, 0.3),
	"ghost_archer": Color(0.5, 0.75, 0.85),
	"stone_herald": Color(0.45, 0.45, 0.5),
	"crypt_guardian": Color(0.7, 0.25, 0.25),
}
# Deslocamento do "nariz" por linha: S, SE, E, NE, N, NW, W, SW
const NARIZ := [Vector2(0, 1), Vector2(1, 1), Vector2(1, 0), Vector2(1, -1), Vector2(0, -1), Vector2(-1, -1), Vector2(-1, 0), Vector2(-1, 1)]

static func sheet(id: String, anim: String, lado: int, quadros: int, dirs: int, pivo: Vector2i) -> ImageTexture:
	var img := Image.create(lado * quadros, lado * dirs, false, Image.FORMAT_RGBA8)
	var cor: Color = COR.get(id, Color(0.8, 0.2, 0.8))
	var esc := lado / 128.0
	for d in dirs:
		for q in quadros:
			var t := float(q) / float(quadros)
			var bob := 0.0
			match anim:
				"idle": bob = sin(t * TAU) * 2.0
				"run": bob = absf(sin(t * TAU * 2.0)) * -6.0
				"attack": bob = 4.0 if q < quadros / 2 else -2.0
				"dodge": bob = 10.0
				"hit": bob = -3.0
			var morto := anim == "death"
			var progresso := t if morto else 0.0
			var ox := d_col(q, lado)
			var oy := d * lado
			var px := ox + pivo.x
			var py := oy + pivo.y
			var c := cor
			if anim == "hit":
				c = c.lerp(Color.WHITE, 0.6)
			var alt := (1.0 - progresso * 0.7)
			var corpo := Rect2(px - 18 * esc, py - (50 * alt + bob) * esc, 36 * esc, 50 * alt * esc)
			img.fill_rect(Rect2i(corpo), c)
			img.fill_rect(Rect2i(Rect2(corpo.position + Vector2(2, 2), corpo.size - Vector2(4, 4))), c.darkened(0.15))
			var cab := Rect2(px - 11 * esc, py - (72 * alt + bob) * esc + (progresso * 30 * esc), 22 * esc, 22 * esc)
			img.fill_rect(Rect2i(cab), c.lightened(0.25))
			var n: Vector2 = NARIZ[_idx_nariz(d, dirs)]
			var nc := Rect2(cab.get_center() + n * 9 * esc - Vector2(4, 4) * esc, Vector2(8, 8) * esc)
			img.fill_rect(Rect2i(nc), Color(0.05, 0.05, 0.08))
			if anim == "run" and q % 2 == 0:
				img.fill_rect(Rect2i(Rect2(px - 14 * esc, py - 4 * esc, 10 * esc, 6 * esc)), c.darkened(0.4))
			elif anim == "run":
				img.fill_rect(Rect2i(Rect2(px + 4 * esc, py - 4 * esc, 10 * esc, 6 * esc)), c.darkened(0.4))
	return ImageTexture.create_from_image(img)

static func d_col(q: int, lado: int) -> int:
	return q * lado

static func _idx_nariz(linha: int, dirs: int) -> int:
	return linha  # 5 linhas usam S,SE,E,NE,N e 8 linhas a ordem completa: os 5 primeiros coincidem

static func tiles(tile: int, colunas: int, linhas: int) -> ImageTexture:
	var img := Image.create(tile * colunas, tile * linhas, false, Image.FORMAT_RGBA8)
	for i in colunas * linhas:
		var c := Color(0.2, 0.2, 0.24)
		var borda := Color(0.12, 0.12, 0.15)
		match i:
			0, 1, 2, 3: c = Color(0.2, 0.2, 0.24).lightened(0.03 * i)
			4: c = Color(0.18, 0.18, 0.22)
			5: c = Color(0.35, 0.15, 0.15)
			6: c = Color(0.22, 0.17, 0.17)
			7: c = Color(0.3, 0.2, 0.1)
			8: c = Color(0.32, 0.3, 0.36)
			9: c = Color(0.4, 0.38, 0.45)
			10, 11: c = Color(0.36, 0.34, 0.4)
			12: c = Color(0.5, 0.48, 0.55)
			13: c = Color(0.1, 0.08, 0.06)
			14: c = Color(0.25, 0.2, 0.2)
			15: c = Color(0.9, 0.5, 0.15)
		var r := Rect2i((i % colunas) * tile, (i / colunas) * tile, tile, tile)
		img.fill_rect(r, borda)
		img.fill_rect(Rect2i(r.position + Vector2i(1, 1), r.size - Vector2i(2, 2)), c)
	return ImageTexture.create_from_image(img)

static func seta(lado: Vector2i) -> ImageTexture:
	var img := Image.create(lado.x, lado.y, false, Image.FORMAT_RGBA8)
	img.fill_rect(Rect2i(0, lado.y / 2 - 2, lado.x - 8, 4), Color(0.85, 0.75, 0.5))
	img.fill_rect(Rect2i(lado.x - 10, lado.y / 2 - 5, 10, 10), Color(0.95, 0.9, 0.7))
	return ImageTexture.create_from_image(img)
