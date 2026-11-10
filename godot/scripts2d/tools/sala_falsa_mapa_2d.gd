extends Node2D
## Sala de mentira dos testes: um braseiro e um pilar em posições fixas (estruturas_perto como a room_2d).
var _estruturas: Array = []

func _init() -> void:
	_estruturas = [{"tipo": "braseiro", "pos": Vector2(900, 4000), "ate": 0}, {"tipo": "pilar", "pos": Vector2(900, 4400), "ate": 0}]

func estruturas_perto(p: Vector2, dist: float) -> Array:
	return _estruturas.filter(func(e): return e["pos"].distance_to(p) <= dist)

func perto_agua(_p: Vector2, _d: float) -> bool:
	return false
