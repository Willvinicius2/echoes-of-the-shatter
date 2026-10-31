extends RefCounted
## Upgrades da corrida: definições em data2d/upgrades.csv, níveis escolhidos na corrida e
## aplicação sobre os stats do jogador (sempre recalculados a partir da base: `restaurar` é idempotente).

const Csv = preload("res://scripts2d/csv2d.gd")

signal mudou

var defs := {}       # id -> {stat, modo, valor, nivel_max}
var ordem: Array = []
var niveis := {}     # id -> nível atual
var _base := {}
var meta: RefCounted   # opcional: bônus permanentes e habilidades liberadas (meta_2d.gd)
var _base_bruta := {}
var _classe_base := ""
var habilidades: RefCounted   # opcional: passivas da árvore de habilidades (habilidades_2d.gd)

func _init() -> void:
	for r in Csv.rows("res://data2d/upgrades.csv"):
		defs[r["id"]] = {"stat": r["stat"], "modo": r["modo"], "valor": float(r["valor"]), "nivel_max": int(r["nivel_max"])}
		ordem.append(r["id"])

## Começa uma corrida: guarda os stats base do jogador (na 1ª vez) e zera os níveis.
func restaurar(jogador: Node) -> void:
	var cl: String = jogador.classe if "classe" in jogador else ""
	if _base_bruta.is_empty() or cl != _classe_base:
		_base_bruta = jogador.stats.duplicate()
		_classe_base = cl
	_base = meta.aplicar(_base_bruta) if meta != null else _base_bruta.duplicate()
	jogador.stats = _base.duplicate()
	if habilidades != null:
		jogador.stats = habilidades.aplicar_passivas(jogador.stats)
	niveis.clear()
	mudou.emit()

func nivel(id: String) -> int:
	return int(niveis.get(id, 0))

func disponiveis() -> Array:
	var out := []
	for id in ordem:
		if nivel(id) < defs[id]["nivel_max"] and (meta == null or meta.liberada(id)):
			out.append(id)
	return out

## Sorteia até `n` upgrades distintos ainda não no nível máximo (determinístico pelo rng da corrida).
func sortear(rng: RandomNumberGenerator, n: int) -> Array:
	var pool := disponiveis()
	for i in range(pool.size() - 1, 0, -1):
		var j := rng.randi_range(0, i)
		var tmp = pool[i]
		pool[i] = pool[j]
		pool[j] = tmp
	return pool.slice(0, n)

## Sobe um nível do upgrade e reaplica todos sobre a base. Falso se já está no máximo.
func escolher(id: String, jogador: Node) -> bool:
	if not defs.has(id) or nivel(id) >= defs[id]["nivel_max"]:
		return false
	niveis[id] = nivel(id) + 1
	var hp_antes: float = jogador.stats["hp_max"]
	_aplicar(jogador)
	var ganho: float = jogador.stats["hp_max"] - hp_antes
	if ganho > 0.0:
		jogador.hp += ganho
	jogador.hp_changed.emit(jogador.hp, jogador.stats["hp_max"])
	mudou.emit()
	return true

## Reaplica upgrades e passivas sobre a base (chamar depois de aprender uma passiva).
func reaplicar(jogador: Node) -> void:
	_aplicar(jogador)
	jogador.hp_changed.emit(jogador.hp, jogador.stats["hp_max"])

func _aplicar(jogador: Node) -> void:
	var s: Dictionary = _base.duplicate()
	for id in ordem:
		var d: Dictionary = defs[id]
		for _i in nivel(id):
			if d["modo"] == "mult":
				s[d["stat"]] = s[d["stat"]] * (1.0 + d["valor"])
			else:
				s[d["stat"]] = s[d["stat"]] + d["valor"]
	if habilidades != null:
		s = habilidades.aplicar_passivas(s)
	jogador.stats = s
