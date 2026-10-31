extends RefCounted
## Upgrades da corrida. Níveis, cartas oferecidas e stats finais vêm do módulo `rogue` do ShatterCore; este script guarda uma
## cópia para a HUD e aplica os stats calculados no jogador. Definições de exibição em data2d/upgrades.csv.

const Csv = preload("res://scripts2d/csv2d.gd")
const Nucleo = preload("res://scripts2d/nucleo_2d.gd")

signal mudou

var defs := {}       # id -> {stat, modo, valor, nivel_max} (só para exibir)
var ordem: Array = []
var niveis := {}     # id -> nível atual (cópia do core)
var semente := 1     # semente da próxima corrida (run_settings seed + nº da corrida)
var meta: RefCounted:   # opcional: compartilha o núcleo (meta, bônus permanentes e habilidades liberadas)
	set(v):
		meta = v
		if v != null:
			nucleo = v.nucleo
var nucleo: Object
var _base_bruta := {}
var habilidades: RefCounted   # opcional: árvore de habilidades da classe (as passivas já vêm nos stats do core)

func _init() -> void:
	for r in Csv.rows("res://data2d/upgrades.csv"):
		defs[r["id"]] = {"stat": r["stat"], "modo": r["modo"], "valor": float(r["valor"]), "nivel_max": int(r["nivel_max"])}
		ordem.append(r["id"])

func _nucleo() -> Object:
	if nucleo == null:
		nucleo = Nucleo.criar()
	return nucleo

## Começa uma corrida no core: guarda os stats base do jogador (na 1ª vez), zera os níveis e aplica o meta.
func restaurar(jogador: Node) -> void:
	if _base_bruta.is_empty():
		_base_bruta = jogador.stats.duplicate()
	_nucleo().corrida_iniciar(semente, _base_bruta)
	jogador.stats = nucleo.corrida_stats()   # base + meta + upgrades + passivas da árvore (core)
	sincronizar(false)
	mudou.emit()

## Copia os níveis da corrida do core.
func sincronizar(avisar := true) -> void:
	niveis = {}
	for u in _nucleo().corrida_estado().get("upgrades", []):
		if int(u["level"]) > 0:
			niveis[str(u["id"])] = int(u["level"])
	if avisar:
		mudou.emit()

func nivel(id: String) -> int:
	return int(niveis.get(id, 0))

## Cartas que o core ofereceu ao limpar a sala (fase de escolha).
func oferta() -> Array:
	return _nucleo().corrida_estado().get("offer", [])

## Upgrades que ainda podem sair: liberados e abaixo do nível máximo.
func disponiveis() -> Array:
	var out := []
	for u in _nucleo().corrida_estado().get("upgrades", []):
		if u["unlocked"] and int(u["level"]) < int(u["max_level"]):
			out.append(str(u["id"]))
	return out

## Escolhe uma das cartas oferecidas: o core sobe o nível e devolve a vida; aplica os stats novos no jogador.
func escolher(id: String, jogador: Node) -> bool:
	var r: Dictionary = _nucleo().corrida_escolher_carta(id, jogador.hp)
	if int(r["resultado"]) != 0:
		return false
	jogador.stats = nucleo.corrida_stats()
	jogador.hp = float(r["hp"])
	jogador.hp_changed.emit(jogador.hp, jogador.stats["hp_max"])
	sincronizar()
	return true

## Relê os stats da corrida do core, que já incluem as passivas (chamar depois de aprender ou redistribuir na árvore).
func reaplicar(jogador: Node) -> void:
	var s: Dictionary = _nucleo().corrida_stats()
	if s.is_empty():
		return   # sem corrida: os stats voltam com a próxima corrida_iniciar
	jogador.stats = s
	jogador.hp_changed.emit(jogador.hp, jogador.stats["hp_max"])
