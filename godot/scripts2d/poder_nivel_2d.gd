extends RefCounted
## Escalada de poder pelo nível do jogador (pedido do Will, 11/11/2026): subir de nível tem de mudar a tela.
## Três degraus visíveis, todos com números em data2d/poder_nivel.csv:
##  - Ecos: a cada ativa disparada, 1, 2 ou 3 cópias saem sozinhas sobre OUTROS inimigos (níveis 6, 12 e 18);
##  - Ricochete: as flechas pulam de inimigo em inimigo, mais pulos a cada N níveis;
##  - Recarga: todas as ativas voltam mais depressa a cada nível.
const Csv = preload("res://scripts2d/csv2d.gd")
const Alvos = preload("res://scripts2d/alvos_2d.gd")
const Feel = preload("res://scripts2d/feel_2d.gd")
const CSV := "res://data2d/poder_nivel.csv"
## Efeitos que não fazem sentido repetidos (movem o arqueiro, são buff ou substituem a própria aura).
const SEM_ECO := ["salto", "furia", "nevasca", "tiro_certeiro"]
static var _cfg := {}

static func cfg() -> Dictionary:
	if _cfg.is_empty():
		for r in Csv.rows(CSV):
			_cfg[r["chave"]] = float(r["valor"])
	return _cfg

## Nível usado pela escalada: o do jogador (ou o forçado por ferramentas de captura, meta `nivel_forcado`).
static func nivel_de(jogador: Object) -> int:
	if jogador == null:
		return 1
	if jogador.has_meta("nivel_forcado"):
		return int(jogador.get_meta("nivel_forcado"))
	return int(jogador.get("nivel_jogador")) if jogador.get("nivel_jogador") != null else 1

static func orbitais(nivel: int) -> int:
	var c := cfg()
	return mini(int(floor(float(nivel) / c["orbital_cada"])), int(c["orbital_max"]))

static func ecos(nivel: int) -> int:
	var c := cfg()
	return int(nivel >= int(c["eco_nivel_1"])) + int(nivel >= int(c["eco_nivel_2"])) + int(nivel >= int(c["eco_nivel_3"]))

static func ricochetes(nivel: int) -> int:
	var c := cfg()
	return mini(int(floor(float(nivel) / c["ricochete_cada"])), int(c["ricochete_max"]))

## Fator no tempo de recarga (1 = normal). Entra no tick das ativas como multiplicador de velocidade.
static func velocidade_recarga(nivel: int) -> float:
	var c := cfg()
	var corte := minf(c["recarga_por_nivel"] * float(maxi(nivel - 1, 0)), c["recarga_max"])
	return 1.0 / (1.0 - corte)

## Agenda os ecos da ativa `id` que acabou de sair. `executar` roda o efeito (jogador, def, dir) e devolve se gastou.
static func ecoar(jogador: Node2D, def: Dictionary, executar: Callable) -> void:
	var n := ecos(nivel_de(jogador))
	if n <= 0 or SEM_ECO.has(str(def.get("efeito", ""))):
		return
	var c := cfg()
	var arv := jogador.get_tree()
	var eu: WeakRef = weakref(jogador)
	var usados: Array = []
	for i in n:
		arv.create_timer(c["eco_atraso"] * float(i + 1)).timeout.connect(func():
			var j: Node2D = eu.get_ref()
			if j == null or not j.is_inside_tree() or j.esta_morto():
				return
			var alvos := Alvos.em_circulo(arv, j.global_position, c["eco_alcance"]).filter(func(e): return not usados.has(e) and e.has_method("take_damage"))
			if alvos.is_empty():
				alvos = Alvos.em_circulo(arv, j.global_position, c["eco_alcance"])
			if alvos.is_empty():
				return
			var e: Node2D = alvos[randi() % alvos.size()]
			usados.append(e)
			var d := def.duplicate()
			d["dano"] = float(d.get("dano", 1.0)) * c["eco_dano"]
			var dir: Vector2 = (e.global_position - j.global_position).normalized()
			j.alvo_ponto = e.global_position
			executar.call(j, d, dir)
			j.alvo_ponto = Vector2.INF
			Feel.impacto(j.get_parent(), j.global_position + Vector2(0, -50), Color(1.0, 0.9, 0.55), Vector2.ZERO, 0.8))

## Próximo inimigo de um ricochete a partir de `pos`, sem repetir os de `ja`. Nulo se não houver.
static func proximo_ricochete(arv: SceneTree, pos: Vector2, ja: Array) -> Node2D:
	return Alvos.mais_proximo(arv, pos, cfg()["ricochete_alcance"], ja, false)

static func dano_ricochete() -> float:
	return cfg()["ricochete_dano"]
