extends Node2D
## Chão em brasa em pixel: manchas de 2 a 3 tons com borda dura, cobertura parcial e pausas entre elas (o fundo aparece);
## chamas quadradas sobem e apagam em ciclos. Some aos poucos no fim de `dur`. Usado pelo Meteoro do Mago.

const FxMago = preload("res://scripts2d/fx_mago_2d.gd")
const Vfx = preload("res://scripts2d/vfx_2d.gd")
const GRADE := 2.5

var raio := 150.0
var dur := 3.0
var _t := 0.0

func _ready() -> void:
	z_index = 0   # z -1 fica sob o piso nesta cena
	Vfx.registrar_decalque(self)

func _process(delta: float) -> void:
	_t += delta
	queue_redraw()
	if _t >= dur:
		queue_free()

func _draw() -> void:
	var pal: Array = FxMago.paleta("fogo")
	var fade := Vfx.fade_zona(_t, dur)
	for i in 9:   # manchas irregulares: cada uma é uma elipse pixelada pequena, longe das outras
		var a := float(i) * 2.399
		var c := ((Vector2(cos(a), sin(a) * 0.55) * raio * (0.2 + 0.7 * fmod(float(i) * 0.37, 1.0))) / GRADE).round() * GRADE
		var r := raio * (0.14 + 0.05 * float(i % 3)) * fade
		FxMago.elipse_pixel(self, c, r, pal[1])
		FxMago.elipse_pixel(self, c, r * 0.6, pal[2])
	for i in 12:   # chamas quadradas que sobem, encolhem e apagam
		var u := fmod(_t * (1.1 + 0.15 * float(i % 4)) + float(i) * 0.31, 1.0)
		var a := float(i) * 1.7
		var base := (Vector2(cos(a), sin(a) * 0.55) * raio * (0.15 + 0.75 * fmod(float(i) * 0.29, 1.0)) / GRADE).round() * GRADE
		var lado := GRADE * (2.0 if u < 0.6 else 1.0)
		var p := base + Vector2(0, -22.0 * u).snapped(Vector2(GRADE, GRADE))
		draw_rect(Rect2(p, Vector2(lado, lado * 1.5)), pal[3] if u < 0.35 else (pal[2] if u < 0.7 else pal[1]))
