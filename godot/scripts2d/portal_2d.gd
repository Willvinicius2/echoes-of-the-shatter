extends Area2D
## Portal do fim da fase aberta: abre depois do chefe e leva à vitória quando o jogador entra.
## Visual em código (anel de runas em neon girando sobre um poço de luz) até a arte final do pacote H6.

const RAIO := 46.0

var _t := 0.0
var _brilho: Sprite2D

func _ready() -> void:
	collision_layer = 0
	collision_mask = 2   # jogador
	var cs := CollisionShape2D.new()
	var c := CircleShape2D.new()
	c.radius = RAIO * 0.7
	cs.shape = c
	add_child(cs)
	var g := Gradient.new()
	g.set_color(0, Color(0.55, 0.9, 1.0, 0.85))
	g.set_color(1, Color(0.35, 0.2, 0.9, 0.0))
	var tex := GradientTexture2D.new()
	tex.gradient = g
	tex.fill = GradientTexture2D.FILL_RADIAL
	tex.fill_from = Vector2(0.5, 0.5)
	tex.fill_to = Vector2(1.0, 0.5)
	tex.width = 128
	tex.height = 128
	_brilho = Sprite2D.new()
	_brilho.texture = tex
	_brilho.scale = Vector2(2.4, 1.3)
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	_brilho.material = mat
	add_child(_brilho)
	scale = Vector2(0.2, 0.2)
	create_tween().set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT).tween_property(self, "scale", Vector2.ONE, 0.6)

func _process(delta: float) -> void:
	_t += delta
	_brilho.modulate.a = 0.75 + 0.25 * sin(_t * 3.0)
	queue_redraw()

func _draw() -> void:
	draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.5))   # elipse no chão, na perspectiva top-down
	draw_circle(Vector2.ZERO, RAIO * 0.92, Color(0.05, 0.03, 0.12, 0.85))
	draw_circle(Vector2.ZERO, RAIO * 0.62, Color(0.3, 0.75, 1.0, 0.35 + 0.15 * sin(_t * 4.0)))
	draw_arc(Vector2.ZERO, RAIO, 0.0, TAU, 48, Color(0.55, 0.9, 1.0, 0.95), 4.0, true)
	for k in 8:
		var a := _t * 0.9 + k * TAU / 8.0
		draw_arc(Vector2.ZERO, RAIO * 0.8, a, a + 0.42, 8, Color(0.75, 0.55, 1.0, 0.9), 3.0, true)
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	for k in 5:   # faíscas subindo do poço
		var f := fmod(_t * 0.6 + k * 0.2, 1.0)
		var x := sin(k * 2.3 + _t) * RAIO * 0.5
		draw_circle(Vector2(x, -f * 70.0), 3.0 * (1.0 - f), Color(0.7, 0.95, 1.0, 1.0 - f))
