extends Node2D
## Lâminas espectrais que giram em volta do herói; a quantidade cresce com o nível (poder_nivel_2d.gd).
## Ferem quem encostam (com um refresco por inimigo) e dão presença de poder: 1 a 6 lâminas em órbita achatada,
## as de trás ficam atrás do herói. Pixel art por código: polígonos chapados, sem alfa suave.
const Poder = preload("res://scripts2d/poder_nivel_2d.gd")
const Alvos = preload("res://scripts2d/alvos_2d.gd")
const OURO := Color(1.0, 0.82, 0.42)
const ACO := Color(0.82, 0.9, 1.0)
var n := 0
var cor := OURO
var _t := 0.0
var _ferido := {}   # inimigo -> instante em que pode ser ferido de novo

func _ready() -> void:
	z_index = 0
	y_sort_enabled = false

func definir(qtd: int) -> void:
	n = qtd

func _physics_process(delta: float) -> void:
	_t += delta
	var dono: Node2D = get_parent()
	if n > 0 and dono.has_method("esta_morto") and not dono.esta_morto():
		var c := Poder.cfg()
		var dano: float = dono.stats["arrow_damage"] * c["orbital_dano"]
		for i in n:
			var p := _pos(i)
			for e in Alvos.no_raio(get_tree(), dono.global_position + p, 34.0, "take_damage"):
				if float(_ferido.get(e, 0.0)) <= _t:
					_ferido[e] = _t + c["orbital_refresco"]
					e.take_damage(dano, dono.global_position + p)
	queue_redraw()

func _pos(i: int) -> Vector2:
	var r: float = Poder.cfg()["orbital_raio"]
	var a := _t * 2.6 + TAU * float(i) / float(maxi(n, 1))
	return Vector2(cos(a) * r, sin(a) * r * 0.5 - 40.0)

func _draw() -> void:
	if n <= 0:
		return
	var r: float = Poder.cfg()["orbital_raio"]
	draw_set_transform(Vector2(0, -40.0), 0.0, Vector2(1.0, 0.5))   # aura discreta: anel tracejado no plano da órbita
	for k in 16:
		if k % 2 == 0:
			draw_arc(Vector2.ZERO, r, TAU * float(k) / 16.0 + _t * 0.4, TAU * (float(k) + 0.6) / 16.0 + _t * 0.4, 3, Color(cor, 0.5), 3.0)
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	for i in n:
		var p := _pos(i)
		var a := _t * 2.6 + TAU * float(i) / float(maxi(n, 1))
		var f := Vector2(-sin(a), cos(a) * 0.5).normalized()   # direção do movimento: a lâmina aponta para onde vai
		var o := f.orthogonal()
		draw_colored_polygon(PackedVector2Array([p + f * 22.0, p + o * 7.0, p - f * 10.0, p - o * 7.0]), Color(0.1, 0.08, 0.1))
		draw_colored_polygon(PackedVector2Array([p + f * 17.0, p + o * 4.5, p - f * 6.0, p - o * 4.5]), ACO)
		draw_colored_polygon(PackedVector2Array([p + f * 17.0, p + o * 1.5, p - f * 2.0]), Color.WHITE)
