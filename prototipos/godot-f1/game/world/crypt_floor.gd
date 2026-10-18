class_name CryptFloor
extends Node2D
## Desenha o chão isométrico (losangos 2:1), as paredes e as portas da Cripta.

var floors: Array[Rect2] = []
var walls: Array[Rect2] = []
var doors: Array[Rect2] = []
var door_closed: Array[bool] = []


func _ready() -> void:
	z_index = -10


func _draw() -> void:
	for r in floors:
		draw_rect(r, Palette.CHAO)
		_iso_grid(r, 32.0)
		_speckles(r)
	for w in walls:
		draw_rect(w, Palette.PAREDE)
		draw_rect(Rect2(w.position, Vector2(w.size.x, minf(4.0, w.size.y))), Palette.PAREDE_TOPO)
		draw_rect(Rect2(w.position, Vector2(minf(3.0, w.size.x), w.size.y)), Palette.PAREDE_TOPO.darkened(0.35))
	for i in range(doors.size()):
		var d: Rect2 = doors[i]
		if door_closed[i]:
			draw_rect(d, Palette.CARVAO)
			draw_rect(d.grow(-2.0), Palette.CARMESIM.darkened(0.3))
			for y in range(int(d.position.y) + 8, int(d.end.y), 16):
				draw_line(Vector2(d.position.x, y), Vector2(d.end.x, y), Palette.OCRE, 2.0)
		else:
			draw_rect(Rect2(d.position, Vector2(d.size.x, 3)), Palette.OCRE)
			draw_rect(Rect2(d.position + Vector2(0, d.size.y - 3), Vector2(d.size.x, 3)), Palette.OCRE)


func _iso_grid(r: Rect2, step: float) -> void:
	# Linhas com inclinação +-0,5 (projeção isométrica 2:1), recortadas ao retângulo.
	var x: float = r.position.x - r.size.y * 2.0
	while x < r.end.x + r.size.y * 2.0:
		_clipped(Vector2(x, r.position.y), Vector2(x + r.size.y * 2.0, r.end.y), r)
		_clipped(Vector2(x, r.end.y), Vector2(x + r.size.y * 2.0, r.position.y), r)
		x += step * 2.0


func _clipped(a: Vector2, b: Vector2, r: Rect2) -> void:
	var seg: PackedVector2Array = clip_line(a, b, r)
	if seg.size() == 2:
		draw_line(seg[0], seg[1], Palette.CHAO_LINHA, 1.0)


func _speckles(r: Rect2) -> void:
	var n: int = int(r.size.x * r.size.y / 900.0)
	for i in range(n):
		var h1: float = fmod(float(i) * 0.7548776662, 1.0)
		var h2: float = fmod(float(i) * 0.5698402909 + 0.31, 1.0)
		var p: Vector2 = r.position + Vector2(h1 * r.size.x, h2 * r.size.y)
		draw_rect(Rect2(p.round(), Vector2(2, 1)), Palette.CHAO_LINHA.lightened(0.1))


## Recorte de segmento por retângulo (Liang-Barsky). Retorna 2 pontos ou vazio.
static func clip_line(a: Vector2, b: Vector2, r: Rect2) -> PackedVector2Array:
	var t0: float = 0.0
	var t1: float = 1.0
	var d: Vector2 = b - a
	var p: Array[float] = [-d.x, d.x, -d.y, d.y]
	var q: Array[float] = [a.x - r.position.x, r.end.x - a.x, a.y - r.position.y, r.end.y - a.y]
	for i in range(4):
		if is_zero_approx(p[i]):
			if q[i] < 0.0:
				return PackedVector2Array()
			continue
		var t: float = q[i] / p[i]
		if p[i] < 0.0:
			if t > t1:
				return PackedVector2Array()
			t0 = maxf(t0, t)
		else:
			if t < t0:
				return PackedVector2Array()
			t1 = minf(t1, t)
	return PackedVector2Array([a + d * t0, a + d * t1])
