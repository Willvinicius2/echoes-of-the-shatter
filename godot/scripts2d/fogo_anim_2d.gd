extends Node2D
## Folha de quadros em linha (ver FOLHAS em fogo_util_2d.gd).

const U = preload("res://scripts2d/fogo_util_2d.gd")

var nome: String
var loop: bool
var alvo_px: float
var _t := 0.0
var _tex: Texture2D
var _def: Dictionary

func _init(n: String, repete: bool, px: float = 0.0) -> void:
	nome = n
	loop = repete
	_def = U.FOLHAS[n]
	alvo_px = px if px > 0.0 else float(_def["tam"])
	z_index = 3

func _ready() -> void:
	_tex = U.textura(nome)
	material = _aditivo()

static func _aditivo() -> CanvasItemMaterial:
	var m := CanvasItemMaterial.new()
	m.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	return m

func _process(delta: float) -> void:
	_t += delta
	if not loop and _t * float(_def["fps"]) >= float(_def["n"]):
		queue_free()
		return
	queue_redraw()

func _draw() -> void:
	var n: int = _def["n"]
	var i: int = int(_t * float(_def["fps"]))
	i = i % n if loop else mini(i, n - 1)
	if _tex != null:
		var w: float = float(_tex.get_width()) / n
		var h: float = float(_tex.get_height())
		var k: float = alvo_px / maxf(w, h)
		var dst := Rect2(Vector2(-w, -h) * 0.5 * k, Vector2(w, h) * k)
		draw_texture_rect_region(_tex, dst, Rect2(w * i, 0.0, w, h))
	else:
		var r: float = alvo_px * 0.25 * (1.0 + 0.2 * sin(_t * 20.0 + i))
		draw_circle(Vector2.ZERO, r, Color(U.COR_BRASA.r, U.COR_BRASA.g, U.COR_BRASA.b, 0.5))
		draw_circle(Vector2.ZERO, r * 0.55, Color(1.0, 0.85, 0.35, 0.8))

