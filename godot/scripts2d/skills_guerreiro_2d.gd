extends RefCounted
## Árvore de habilidades do Guerreiro (data2d/habilidades_guerreiro.csv, contrato do sistema de habilidades), com a mesma interface do upgrades_2d.gd
## (defs, ordem, niveis, nivel, disponiveis, sortear, escolher, restaurar) para a tela de cartas e o HUD.
## Uma habilidade só é oferecida quando o pai da árvore já foi aprendido; as ativas ocupam até `slots_max` teclas.

const Csv = preload("res://scripts2d/csv2d.gd")

signal mudou

var defs := {}       # id -> linha do CSV com números convertidos (+ "nivel_max")
var ordem: Array = []
var niveis := {}     # id -> nível atual
var slots: Array = []  # ids das ativas, na ordem em que foram aprendidas (tecla 1..n)
var slots_max := 4
var meta: RefCounted   # opcional: bônus permanentes e habilidades liberadas (meta_2d.gd)
var _base := {}
var _base_bruta := {}

const NUM := ["nivel_max", "tier", "pontos", "valor", "cd", "custo", "dano", "qtd", "angulo", "raio", "duracao", "alcance", "escala", "espera", "recup"]
# campos que crescem com o nível das ativas: valor_n = base * (1 + escala * (n - 1))
const ESCALADOS := ["dano", "qtd", "raio", "duracao", "alcance", "valor"]

func _init() -> void:
	for r in Csv.rows("res://data2d/habilidades_guerreiro.csv"):
		var d: Dictionary = r.duplicate()
		for k in NUM:
			d[k] = float(r[k]) if r[k] != "" else 0.0
		d["nivel_max"] = int(d["nivel_max"])
		defs[r["id"]] = d
		ordem.append(r["id"])

## Começa uma corrida: guarda os stats base (na 1ª vez) e zera a árvore.
func restaurar(jogador: Node) -> void:
	if _base_bruta.is_empty():
		_base_bruta = jogador.stats.duplicate()
	_base = meta.aplicar(_base_bruta) if meta != null else _base_bruta.duplicate()
	jogador.stats = _base.duplicate()
	niveis.clear()
	slots.clear()
	mudou.emit()

## Stats base numéricos (sem o meta) que o core usa na corrida: cura do descanso e bônus permanentes.
func base_numerica() -> Dictionary:
	var out := {}
	for k in _base_bruta:
		if typeof(_base_bruta[k]) in [TYPE_INT, TYPE_FLOAT]:
			out[k] = _base_bruta[k]
	return out

func nivel(id: String) -> int:
	return int(niveis.get(id, 0))

func eh_ativa(id: String) -> bool:
	return defs[id]["tipo"] == "ativa"

## Pode ser oferecida: não está no máximo, o pai já foi aprendido, a corrida a libera e há tecla livre (ativas novas).
func disponivel(id: String) -> bool:
	var d: Dictionary = defs[id]
	if nivel(id) >= d["nivel_max"]:
		return false
	if d["pai"] != "" and nivel(d["pai"]) <= 0:
		return false
	if meta != null and not meta.liberada(id):
		return false
	if nivel(id) == 0 and eh_ativa(id) and slots.size() >= slots_max:
		return false
	return true

func disponiveis() -> Array:
	var out := []
	for id in ordem:
		if disponivel(id):
			out.append(id)
	return out

## Sorteia até `n` habilidades distintas (determinístico pelo rng da corrida).
func sortear(rng: RandomNumberGenerator, n: int) -> Array:
	var pool := disponiveis()
	for i in range(pool.size() - 1, 0, -1):
		var j := rng.randi_range(0, i)
		var tmp = pool[i]
		pool[i] = pool[j]
		pool[j] = tmp
	return pool.slice(0, n)

## Sobe um nível (ou aprende) e reaplica as passivas sobre a base. Falso se não pode.
func escolher(id: String, jogador: Node) -> bool:
	if not defs.has(id) or not disponivel(id):
		return false
	if nivel(id) == 0 and eh_ativa(id):
		slots.append(id)
	niveis[id] = nivel(id) + 1
	var hp_antes: float = jogador.stats["hp_max"]
	_aplicar(jogador)
	var ganho: float = jogador.stats["hp_max"] - hp_antes
	if ganho > 0.0:
		jogador.hp += ganho
	jogador.hp_changed.emit(jogador.hp, jogador.stats["hp_max"])
	mudou.emit()
	return true

func _aplicar(jogador: Node) -> void:
	var s: Dictionary = _base.duplicate()
	for id in ordem:
		var d: Dictionary = defs[id]
		if d["tipo"] != "passiva":
			continue
		for _i in nivel(id):
			if d["modo"] == "mult":
				s[d["stat"]] = s[d["stat"]] * (1.0 + d["valor"])
			else:
				s[d["stat"]] = s[d["stat"]] + d["valor"]
	jogador.stats = s

## Definição de uma ativa já escalonada pelo nível atual (o que `efeitos_guerreiro_2d.gd` recebe).
func def(id: String) -> Dictionary:
	var d: Dictionary = defs[id].duplicate()
	var n := maxi(nivel(id), 1)
	if d["tipo"] == "ativa" and n > 1:
		for k in ESCALADOS:
			d[k] = d[k] * (1.0 + d["escala"] * (n - 1))
	return d

## Recarga (s) de uma ativa.
func recarga(id: String) -> float:
	return defs[id]["cd"]
