extends Node2D
## Animações leves do cenário: oscilação do halo das tochas e velas, névoa em deriva e folhas na água.
## Tudo em _process com poucos nós; sem partículas além das folhas e vaga-lumes do terreno.

var _t := 0.0
var _halos: Array = []
var _nevoa: Array = []
var _folhas: Array = []

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
		var f := 0.5 + 0.5 * sin(_t * 3.1 + h["fase"]) * sin(_t * 1.3 + h["fase"] * 0.5)
		h["sp"].scale = h["escala"] * (0.96 + 0.06 * f)
		h["sp"].modulate.a = h["alpha"] * (0.82 + 0.18 * f)
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
