class_name Geo
extends RefCounted
## Geometria pura usada por regras e cenas.


## `to_other` está dentro do arco frontal de `facing`?
static func in_front(facing: Vector2, to_other: Vector2, arc_degrees: float) -> bool:
	if to_other.length_squared() < 0.0001 or facing.length_squared() < 0.0001:
		return true
	var half: float = deg_to_rad(arc_degrees * 0.5)
	return facing.normalized().dot(to_other.normalized()) >= cos(half)


## Pontos de um setor (origem + arco) apontando para +X. Convexo se arc <= 180.
static func sector_points(range_px: float, arc_degrees: float, steps: int = 10) -> PackedVector2Array:
	var pts: PackedVector2Array = PackedVector2Array()
	pts.append(Vector2.ZERO)
	var half: float = deg_to_rad(arc_degrees * 0.5)
	for i in range(steps + 1):
		var a: float = lerpf(-half, half, float(i) / float(steps))
		pts.append(Vector2.RIGHT.rotated(a) * range_px)
	return pts
