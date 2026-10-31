extends RefCounted
## Consultas de alvos e golpe para habilidades: inimigos vivos estão no grupo "hurtable".
## Distâncias descontam o raio do inimigo para o golpe acertar quem toca a borda da área.

static func raio_de(n: Node) -> float:
	return float(n.stats.get("radius", 14.0)) if n.get("stats") != null else 14.0

static func vivos(arvore: SceneTree) -> Array:
	return arvore.get_nodes_in_group("hurtable")

static func em_circulo(arvore: SceneTree, centro: Vector2, raio: float) -> Array:
	var out := []
	for n in vivos(arvore):
		if n.global_position.distance_to(centro) - raio_de(n) <= raio:
			out.append(n)
	return out

## Cone com vértice em `origem`, abertura total `angulo` (graus) e comprimento `compr`.
static func em_cone(arvore: SceneTree, origem: Vector2, dir: Vector2, compr: float, angulo: float) -> Array:
	var out := []
	for n in vivos(arvore):
		var v: Vector2 = n.global_position - origem
		var d := v.length()
		if d - raio_de(n) > compr:
			continue
		if d <= raio_de(n) + 16.0 or absf(rad_to_deg(dir.angle_to(v))) <= angulo * 0.5:
			out.append(n)
	return out

static func em_segmento(arvore: SceneTree, a: Vector2, b: Vector2, espessura: float) -> Array:
	var out := []
	for n in vivos(arvore):
		var p := Geometry2D.get_closest_point_to_segment(n.global_position, a, b)
		if p.distance_to(n.global_position) - raio_de(n) <= espessura:
			out.append(n)
	return out

## Inimigo vivo mais próximo de `pos` dentro de `max_dist`, ignorando os de `excluir`.
static func mais_proximo(arvore: SceneTree, pos: Vector2, max_dist: float, excluir: Array = []) -> Node2D:
	var melhor: Node2D = null
	var md := max_dist
	for n in vivos(arvore):
		if excluir.has(n):
			continue
		var d: float = n.global_position.distance_to(pos) - raio_de(n)
		if d <= md:
			md = d
			melhor = n
	return melhor

## Dano + status opcionais. `status` = {tipo, dur, valor} (tipos do inimigo: queimadura, lentidao, atordoamento) ou vazio.
static func golpear(alvo: Node, dano: float, origem: Vector2, status: Dictionary = {}) -> void:
	if not is_instance_valid(alvo) or not alvo.has_method("take_damage"):
		return
	alvo.take_damage(dano, origem)
	if not status.is_empty() and is_instance_valid(alvo) and alvo.has_method("aplicar_status"):
		alvo.aplicar_status(status["tipo"], status["dur"], status["valor"])
