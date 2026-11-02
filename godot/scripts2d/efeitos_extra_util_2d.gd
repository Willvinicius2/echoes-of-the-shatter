extends RefCounted
## Utilidades de desenho e de alvo das skills do segundo leque (doc 37): tudo vetorial, sem sprite sheet nova.
## Desenho "pintado" em três camadas (contorno/halo escuro, corpo na cor do elemento, miolo claro) para nada ficar chapado.

## Inimigos vivos num círculo.
static func no_raio(arvore: Node, centro: Vector2, r: float) -> Array:
	var out := []
	for n in arvore.get_tree().get_nodes_in_group("hurtable"):
		if n is Node2D and n.has_method("take_damage") and n.global_position.distance_to(centro) <= r:
			if n.has_method("esta_morto") and n.esta_morto():
				continue
			out.append(n)
	return out

## Inimigos vivos mais perto de `centro` (até `max_n`), dentro de `alcance`, do mais perto ao mais longe.
static func mais_proximos(arvore: Node, centro: Vector2, alcance: float, max_n: int) -> Array:
	var todos := no_raio(arvore, centro, alcance)
	todos.sort_custom(func(a: Node2D, b: Node2D): return a.global_position.distance_squared_to(centro) < b.global_position.distance_squared_to(centro))
	return todos.slice(0, max_n)

## Distância de um ponto ao segmento a-b.
static func dist_segmento(p: Vector2, a: Vector2, b: Vector2) -> float:
	var ab := b - a
	var t := 0.0
	if ab.length_squared() > 0.001:
		t = clampf((p - a).dot(ab) / ab.length_squared(), 0.0, 1.0)
	return p.distance_to(a + ab * t)

## Ruído barato e determinístico em [-1, 1] a partir de dois números (sem RandomNumberGenerator por quadro).
static func ruido(a: float, b: float) -> float:
	return sin(a * 12.9898 + b * 78.233) * 0.5 + sin(a * 4.1414 + b * 9.1313) * 0.5

## Raio em zigue-zague entre dois pontos locais: halo largo, corpo na cor, miolo branco. `sem` muda o desenho.
static func raio_zz(ci: CanvasItem, a: Vector2, b: Vector2, cor: Color, larg: float, sem: float, alfa := 1.0, passos := 7) -> void:
	var dir := b - a
	if dir.length() < 2.0:
		return
	var n := dir.orthogonal().normalized()
	var pts := PackedVector2Array([a])
	for i in range(1, passos):
		var k := float(i) / float(passos)
		pts.append(a + dir * k + n * ruido(sem, float(i)) * minf(dir.length() * 0.09, 22.0))
	pts.append(b)
	ci.draw_polyline(pts, Color(cor.r, cor.g, cor.b, 0.22 * alfa), larg * 3.4)
	ci.draw_polyline(pts, Color(cor.r, cor.g, cor.b, 0.85 * alfa), larg * 1.4)
	ci.draw_polyline(pts, Color(1, 1, 1, 0.95 * alfa), maxf(larg * 0.55, 1.0))

## Cristal de gelo (losango alongado) em `pos`, apontando para `ang`, com faceta clara. `comp` é o comprimento total.
static func cristal(ci: CanvasItem, pos: Vector2, ang: float, comp: float, larg: float, alfa := 1.0) -> void:
	var f := Vector2.from_angle(ang)
	var o := f.orthogonal()
	var topo := pos + f * comp
	var corpo := PackedVector2Array([pos + o * larg, pos + f * comp * 0.25 + o * larg * 1.1, topo, pos + f * comp * 0.25 - o * larg * 1.1, pos - o * larg])
	ci.draw_colored_polygon(corpo, Color(0.35, 0.65, 0.95, 0.92 * alfa))
	ci.draw_colored_polygon(PackedVector2Array([pos, pos + f * comp * 0.25 + o * larg * 1.1, topo]), Color(0.75, 0.95, 1.0, 0.9 * alfa))
	ci.draw_polyline(PackedVector2Array([pos + o * larg, pos + f * comp * 0.25 + o * larg * 1.1, topo, pos + f * comp * 0.25 - o * larg * 1.1, pos - o * larg]), Color(0.12, 0.28, 0.55, 0.9 * alfa), 1.5)

## Língua de chama (gota) com base em `pos`, altura `h`, três camadas de cor (vermelho, laranja, amarelo).
static func chama(ci: CanvasItem, pos: Vector2, h: float, w: float, sem: float, alfa := 1.0) -> void:
	var bal := ruido(sem, 3.0) * w * 0.6   # a ponta balança
	var camadas := [[1.0, Color(0.75, 0.16, 0.05, 0.85)], [0.72, Color(1.0, 0.5, 0.1, 0.92)], [0.42, Color(1.0, 0.9, 0.4, 0.95)]]
	for c in camadas:
		var k: float = c[0]
		var cor: Color = c[1]
		cor.a *= alfa
		var ww := w * k
		var hh := h * (0.55 + 0.45 * k)
		ci.draw_colored_polygon(PackedVector2Array([
			pos + Vector2(-ww, 0), pos + Vector2(-ww * 0.8, -hh * 0.4), pos + Vector2(bal * k, -hh),
			pos + Vector2(ww * 0.8, -hh * 0.4), pos + Vector2(ww, 0), pos + Vector2(0, ww * 0.45)]), cor)

## Esfera brilhante (halo + corpo + ponto claro).
static func orbe(ci: CanvasItem, pos: Vector2, r: float, cor: Color, alfa := 1.0) -> void:
	ci.draw_circle(pos, r * 2.2, Color(cor.r, cor.g, cor.b, 0.16 * alfa))
	ci.draw_circle(pos, r * 1.35, Color(cor.r, cor.g, cor.b, 0.4 * alfa))
	ci.draw_circle(pos, r, Color(cor.r, cor.g, cor.b, 0.95 * alfa))
	ci.draw_circle(pos + Vector2(-r * 0.25, -r * 0.3), r * 0.45, Color(1, 1, 1, 0.9 * alfa))

## Elipse achatada no chão (visão 3/4): círculo desenhado com escala vertical 0.5. Restaura a transformação no fim.
static func elipse(ci: CanvasItem, centro: Vector2, r: float, cor: Color) -> void:
	ci.draw_set_transform(centro, 0.0, Vector2(1.0, 0.5))
	ci.draw_circle(Vector2.ZERO, r, cor)
	ci.draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)

static func elipse_arco(ci: CanvasItem, centro: Vector2, r: float, cor: Color, larg: float) -> void:
	ci.draw_set_transform(centro, 0.0, Vector2(1.0, 0.5))
	ci.draw_arc(Vector2.ZERO, r, 0.0, TAU, 40, cor, larg)
	ci.draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)

## Ponto no chão mirado: o alvo do autocast (limitado ao alcance) ou 70% do alcance na direção da mira.
static func ponto(jogador: Node2D, dir: Vector2, alcance: float) -> Vector2:
	if jogador.has_method("tem_alvo_auto") and jogador.tem_alvo_auto():
		return jogador.ponto_mira(alcance)
	return jogador.global_position + dir * 0.7 * alcance
