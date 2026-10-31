extends RefCounted
## Stats da corrida do Guerreiro. Ele não recebe cartas do core: a progressão vem da árvore comum (habilidades_2d.gd, tecla T),
## então aqui só ficam a base com o meta e as passivas. Mesma interface mínima do upgrades_2d.gd para a HUD e o run_2d.

signal mudou

var defs := {}
var ordem: Array = []
var niveis := {}
var semente := 1
var meta: RefCounted
var habilidades: RefCounted   # passivas da árvore (habilidades_2d.gd)
var _base_bruta := {}
var _base := {}

## Começa uma corrida: guarda os stats base (na 1ª vez), soma o meta e as passivas já aprendidas.
func restaurar(jogador: Node) -> void:
	if _base_bruta.is_empty():
		_base_bruta = jogador.stats.duplicate()
	_base = meta.aplicar(_base_bruta) if meta != null else _base_bruta.duplicate()
	jogador.stats = _com_passivas()
	mudou.emit()

## Reaplica meta e passivas (depois de aprender ou redistribuir); vida máxima nova cura a diferença.
func reaplicar(jogador: Node) -> void:
	var antes: float = jogador.stats["hp_max"]
	jogador.stats = _com_passivas()
	var ganho: float = jogador.stats["hp_max"] - antes
	if ganho > 0.0:
		jogador.hp += ganho
	jogador.hp = minf(jogador.hp, jogador.stats["hp_max"])
	jogador.hp_changed.emit(jogador.hp, jogador.stats["hp_max"])

func _com_passivas() -> Dictionary:
	return habilidades.aplicar_passivas(_base) if habilidades != null else _base.duplicate()

## Stats base numéricos (sem o meta) que o core usa na corrida: cura do descanso e bônus permanentes.
func base_numerica() -> Dictionary:
	var out := {}
	for k in _base_bruta:
		if typeof(_base_bruta[k]) in [TYPE_INT, TYPE_FLOAT]:
			out[k] = _base_bruta[k]
	return out

func nivel(_id: String) -> int:
	return 0

func oferta() -> Array:
	return []

func escolher(_id: String, _jogador: Node) -> bool:
	return false
