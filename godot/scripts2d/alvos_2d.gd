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
## Com `visivel`, só conta quem aparece na tela e tem linha de visão a partir de `pos` (sem muro, água ou prop no caminho).
static func mais_proximo(arvore: SceneTree, pos: Vector2, max_dist: float, excluir: Array = [], visivel := false) -> Node2D:
	var lista: Array = []
	for n in vivos(arvore):
		if excluir.has(n):
			continue
		var d: float = n.global_position.distance_to(pos) - raio_de(n)
		if d <= max_dist:
			lista.append([d, n])
	lista.sort_custom(func(a, b): return a[0] < b[0])
	for par in lista:
		if not visivel or (na_tela(arvore, par[1].global_position) and ve(arvore, pos, par[1].global_position)):
			return par[1]
	return null

## O ponto aparece na tela (com uma margem)? Sem câmera ativa (testes, menus) tudo conta como na tela: o jogador não
## pode ver o herói atirar em quem está fora do quadro, senão parece que ele atira no nada.
static func na_tela(arvore: SceneTree, ponto: Vector2, margem := 32.0) -> bool:
	if arvore == null or arvore.root == null:
		return true
	var vp: Viewport = arvore.root.get_viewport()
	if vp == null or vp.get_camera_2d() == null:
		return true
	var r: Rect2 = vp.get_canvas_transform().affine_inverse() * vp.get_visible_rect()
	return r.grow(margem).has_point(ponto)

## Linha de visão entre dois pontos: nada da camada 1 (paredes, água funda, props sólidos) no caminho.
static func ve(arvore: SceneTree, de: Vector2, para: Vector2) -> bool:
	if arvore == null or arvore.root == null:
		return true
	var espaco := arvore.root.get_world_2d().direct_space_state
	if espaco == null:
		return true
	return espaco.intersect_ray(PhysicsRayQueryParameters2D.create(de, para, 1)).is_empty()

## Dano + status opcionais. `status` = {tipo, dur, valor} (tipos do inimigo: queimadura, lentidao, atordoamento) ou vazio.
static func golpear(alvo: Node, dano: float, origem: Vector2, status: Dictionary = {}) -> void:
	if not is_instance_valid(alvo) or not alvo.has_method("take_damage"):
		return
	alvo.take_damage(dano, origem)
	if not status.is_empty() and is_instance_valid(alvo) and alvo.has_method("aplicar_status"):
		alvo.aplicar_status(status["tipo"], status["dur"], status["valor"])

# ---- autocast: escolha de alvo das habilidades (coluna `mira` de data2d/habilidades_mira.csv) ----------------

## Acessibilidade: com true, o básico e as habilidades disparam sozinhos mas miram no cursor (ou no analógico).
static var mira_mouse := false

## Quantos inimigos vivos estão a até `raio` de `centro` (com o raio deles descontado).
static func contar_em(arvore: SceneTree, centro: Vector2, raio: float) -> int:
	return em_circulo(arvore, centro, raio).size()

## Inimigo, dentro de `alcance`, com mais vizinhos a até `raio_grupo`; empate fica com o mais próximo.
## Só inimigos com linha de visão a partir de `pos` podem ser o centro (a área cai neles).
static func centro_de_grupo(arvore: SceneTree, pos: Vector2, alcance: float, raio_grupo: float) -> Node2D:
	var perto := em_circulo(arvore, pos, alcance).filter(func(n): return na_tela(arvore, n.global_position) and ve(arvore, pos, n.global_position))
	var melhor: Node2D = null
	var melhor_n := -1
	var melhor_d := INF
	for a in perto:
		var n := 0
		for b in perto:
			if a.global_position.distance_to(b.global_position) <= raio_grupo:
				n += 1
		var d: float = a.global_position.distance_to(pos)
		if n > melhor_n or (n == melhor_n and d < melhor_d):
			melhor = a
			melhor_n = n
			melhor_d = d
	return melhor

## Decide se uma habilidade com autocast dispara agora e para onde.
## `mira`: proximo (no inimigo mais próximo que dá para ver), grupo (no maior grupo), si (em volta do jogador),
## fuga (para longe do mais próximo). `alcance`: distância em que precisa haver inimigo. `min_alvos`: quantos inimigos no alcance.
## `raio_grupo`: raio da área da habilidade, usado pelo `grupo`. Devolve {} (não dispara) ou {dir, ponto}.
static func escolher(arvore: SceneTree, pos: Vector2, mira: String, alcance: float, min_alvos: int, raio_grupo: float) -> Dictionary:
	if arvore == null or mira == "" or mira == "manual":
		return {}
	# `si` (em volta do jogador) acerta quem está perto mesmo sem linha de visão; o resto precisa ver o alvo,
	# senão a flecha ou a bola de fogo morre no muro, na árvore ou na água e a recarga vai embora à toa.
	var perto := mais_proximo(arvore, pos, alcance, [], mira != "si")
	if perto == null:
		return {}
	if min_alvos > 1 and contar_em(arvore, pos, alcance) < min_alvos:
		return {}
	var alvo: Node2D = perto
	if mira == "grupo":
		var g := centro_de_grupo(arvore, pos, alcance, maxf(raio_grupo, 1.0))
		if g != null:
			alvo = g
	var v: Vector2 = alvo.global_position - pos
	var dir := v.normalized() if v.length() > 0.5 else Vector2.DOWN
	if mira == "fuga":
		return {"dir": -dir, "ponto": pos - dir * 1.0e4}   # quem usa limita ao alcance da habilidade
	return {"dir": dir, "ponto": alvo.global_position}
