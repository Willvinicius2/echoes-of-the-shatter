extends Node2D
## Animações leves do cenário: oscilação do halo das tochas e velas, névoa em deriva e folhas na água.
## O clima vivo (vento, fogo, fumaça, folhas, nuvens) fica no filho `clima_2d.gd`, criado aqui.

const Clima = preload("res://scripts2d/clima_2d.gd")

var _t := 0.0
var _halos: Array = []
var _nevoa: Array = []
var _folhas: Array = []

func _ready() -> void:
	add_child(Clima.new())

func add_halo(sp: Sprite2D) -> void:
	_halos.append({"sp": sp, "escala": sp.scale, "alpha": sp.modulate.a, "fase": randf() * TAU})

func add_nevoa(sp: Sprite2D, amplitude: float) -> void:
	_nevoa.append({"sp": sp, "x0": sp.position.x, "amp": amplitude, "fase": randf() * TAU})

## Folha que desliza pela linha do riacho, devagar, e recomeça no começo.
func add_folha(sp: Sprite2D, linha: PackedVector2Array, vel: float, inicio: float) -> void:
	_folhas.append({"sp": sp, "linha": linha, "vel": vel, "u": inicio})

func _process(delta: float) -> void:
	_t += delta
	for h in _halos:
		# tremor de fogo: lento + rápido + estalo curto, para a luz não pulsar como um metrônomo
		var fa: float = h["fase"]
		var f := 0.5 + 0.5 * (sin(_t * 2.7 + fa) * 0.45 + sin(_t * 7.9 + fa * 1.7) * 0.35 + sin(_t * 17.3 + fa * 2.3) * 0.2)
		h["sp"].scale = h["escala"] * (0.95 + 0.08 * f)
		h["sp"].modulate.a = h["alpha"] * (0.74 + 0.26 * f)
	for n in _nevoa:
		n["sp"].position.x = n["x0"] + sin(_t * 0.18 + n["fase"]) * n["amp"]
	for fo in _folhas:
		var u: float = fposmod(float(fo["u"]) + delta * float(fo["vel"]), 1.0)
		fo["u"] = u
		var linha: PackedVector2Array = fo["linha"]
		var k: float = u * (linha.size() - 1)
		var i := int(k)
		var p: Vector2 = linha[i].lerp(linha[mini(i + 1, linha.size() - 1)], k - i)
		fo["sp"].position = p + Vector2(0, sin(_t * 1.7 + u * 20.0) * 5.0)
		fo["sp"].rotation = sin(_t * 0.8 + u * 9.0) * 0.5
		fo["sp"].modulate.a = clampf(minf(u, 1.0 - u) * 8.0, 0.0, 0.85)
