extends RefCounted
## Runtime de habilidades da classe: árvore (pontos, pré-requisitos), 4 slots ativos, recarga e mana.
## Dados em data2d/habilidades_<classe>.csv; classes em data2d/classes_2d.csv; efeitos ativos em
## scripts2d/efeitos_<classe>_2d.gd com `static func executar(efeito, jogador, def, nivel, mira) -> bool`.
## Nenhum número de balanceamento mora aqui.

const Csv = preload("res://scripts2d/csv2d.gd")

const SLOTS := 4

static var caminho := "user://habilidades_2d.json"   # os testes apontam para outro arquivo
const CAMPOS_ESCALA := ["dano", "qtd", "raio", "duracao", "alcance", "valor"]
const CAMPOS_NUM := ["tier", "pontos", "nivel_max", "cd", "custo", "dano", "qtd", "angulo", "raio", "duracao", "alcance", "valor", "escala"]

signal mudou
signal usada(slot: int, id: String)

var classe := ""
var defs := {}            # id -> linha do CSV (números convertidos)
var ordem: Array = []     # ids na ordem do CSV
var niveis := {}          # id -> nível aprendido
var slots: Array = ["", "", "", ""]
var recargas := {}        # id -> segundos restantes
var pontos := 0           # saldo de pontos de habilidade
var persistir := true     # falso: não lê nem grava o save (testes de lógica)
var _efeitos: GDScript

## Linhas de data2d/classes_2d.csv por id.
static func classes() -> Dictionary:
	var out := {}
	for r in Csv.rows("res://data2d/classes_2d.csv"):
		out[r["id"]] = r
	return out

## Carrega a árvore da classe. Arquivo de dados ou de efeitos ausente deixa a árvore vazia (sem erro).
func carregar_classe(id: String, caminho_csv := "", caminho_efeitos := "") -> void:
	classe = id
	defs.clear()
	ordem.clear()
	niveis.clear()
	recargas.clear()
	slots = ["", "", "", ""]
	_efeitos = null
	var cl: Dictionary = classes().get(id, {})
	var csv: String = caminho_csv if caminho_csv != "" else cl.get("habilidades", "")
	if csv != "" and FileAccess.file_exists(csv):
		for r in Csv.rows(csv):
			var d: Dictionary = r.duplicate()
			for c in CAMPOS_NUM:
				d[c] = float(r.get(c, "")) if str(r.get(c, "")) != "" else 0.0
			d["nivel_max"] = maxi(1, int(d["nivel_max"]))
			d["pontos"] = maxi(1, int(d["pontos"]))
			defs[d["id"]] = d
			ordem.append(d["id"])
	var script_efeitos: String = caminho_efeitos if caminho_efeitos != "" else cl.get("efeitos", "")
	if script_efeitos != "" and ResourceLoader.exists(script_efeitos):
		_efeitos = load(script_efeitos)
	_restaurar()
	mudou.emit()

func nivel(id: String) -> int:
	return int(niveis.get(id, 0))

func ramos() -> Array:
	var out := []
	for id in ordem:
		if not out.has(defs[id]["ramo"]):
			out.append(defs[id]["ramo"])
	return out

func ids_do_ramo(ramo: String) -> Array:
	return ordem.filter(func(i): return defs[i]["ramo"] == ramo)

func eh_ativa(id: String) -> bool:
	return defs.has(id) and defs[id]["tipo"] == "ativa"

## Linha da habilidade já escalonada pelo nível (n = 0 usa o nível 1 para exibir o valor base).
func def_nivel(id: String, n := -1) -> Dictionary:
	var d: Dictionary = defs[id].duplicate()
	var lv := nivel(id) if n < 0 else n
	var f: float = 1.0 + d["escala"] * maxf(0.0, lv - 1.0)
	for c in CAMPOS_ESCALA:
		d[c] = d[c] * f
	d["qtd"] = maxf(1.0, roundf(d["qtd"])) if d["qtd"] > 0.0 else 0.0
	return d

func pode_aprender(id: String) -> bool:
	if not defs.has(id):
		return false
	var d: Dictionary = defs[id]
	if nivel(id) >= d["nivel_max"] or pontos < d["pontos"]:
		return false
	return d["pai"] == "" or nivel(d["pai"]) >= 1

func aprender(id: String) -> bool:
	if not pode_aprender(id):
		return false
	pontos -= int(defs[id]["pontos"])
	niveis[id] = nivel(id) + 1
	if nivel(id) == 1 and eh_ativa(id) and not slots.has(id):
		var livre := slots.find("")
		if livre >= 0:
			slots[livre] = id
	_salvar()
	mudou.emit()
	return true

## Soma pontos ao saldo (limpar sala, chefe, testes).
func ganhar_pontos(n: int) -> void:
	pontos += maxi(0, n)
	_salvar()
	mudou.emit()

## Redistribuição gratuita: devolve todos os pontos gastos e esvazia os slots.
func redistribuir() -> void:
	for id in niveis:
		pontos += int(defs[id]["pontos"]) * int(niveis[id])
	niveis.clear()
	slots = ["", "", "", ""]
	_salvar()
	mudou.emit()

## Põe uma habilidade ativa aprendida no slot (id vazio limpa). Se já estava em outro slot, os dois trocam.
func equipar(slot: int, id: String) -> bool:
	if slot < 0 or slot >= SLOTS:
		return false
	if id != "":
		if not eh_ativa(id) or nivel(id) < 1:
			return false
		var antigo := slots.find(id)
		if antigo >= 0:
			slots[antigo] = slots[slot]
	slots[slot] = id
	_salvar()
	mudou.emit()
	return true

func tick(delta: float) -> void:
	for id in recargas.keys():
		recargas[id] = maxf(0.0, recargas[id] - delta)
		if recargas[id] <= 0.0:
			recargas.erase(id)

## Fração 0..1 da recarga do slot (0 = pronto), para a HUD.
func recarga_slot(slot: int) -> float:
	var id: String = slots[slot]
	if id == "" or not recargas.has(id):
		return 0.0
	return clampf(recargas[id] / maxf(0.01, float(defs[id]["cd"])), 0.0, 1.0)

## Usa o slot: confere recarga e mana, chama o efeito da classe e cobra só se ele retornar true.
func usar(slot: int, jogador: Node2D, mira: Vector2) -> bool:
	if slot < 0 or slot >= SLOTS or slots[slot] == "" or _efeitos == null:
		return false
	var id: String = slots[slot]
	if recargas.has(id):
		return false
	var d := def_nivel(id)
	var mana: float = jogador.mana if "mana" in jogador else 0.0
	if mana < d["custo"]:
		return false
	if not _efeitos.executar(d["efeito"], jogador, d, nivel(id), mira.normalized()):
		return false
	if "mana" in jogador:
		jogador.gastar_mana(d["custo"])
	var mult: float = jogador.stats.get("skill_cd_mult", 1.0) if "stats" in jogador else 1.0
	if d["cd"] > 0.0:
		recargas[id] = d["cd"] * mult
	usada.emit(slot, id)
	return true

## Aplica as passivas aprendidas sobre os stats (idempotente: parte sempre de `base`).
func aplicar_passivas(base: Dictionary) -> Dictionary:
	var s := base.duplicate()
	for id in ordem:
		var d: Dictionary = defs[id]
		if d["tipo"] != "passiva" or d["stat"] == "":
			continue
		for _i in nivel(id):
			var atual: float = s.get(d["stat"], 0.0)
			s[d["stat"]] = atual * (1.0 + d["valor"]) if d["modo"] == "mult" else atual + d["valor"]
	return s

## Estado para o save (níveis, slots; os pontos ficam no saldo da meta).
func para_dicionario() -> Dictionary:
	return {"niveis": niveis.duplicate(), "slots": slots.duplicate(), "pontos": pontos}

func de_dicionario(d: Dictionary) -> void:
	niveis.clear()
	for id in d.get("niveis", {}):
		if defs.has(id):
			niveis[id] = clampi(int(d["niveis"][id]), 0, int(defs[id]["nivel_max"]))
	slots = ["", "", "", ""]
	var sv: Array = d.get("slots", [])
	for i in mini(SLOTS, sv.size()):
		if eh_ativa(str(sv[i])) and nivel(str(sv[i])) >= 1:
			slots[i] = str(sv[i])
	pontos = maxi(0, int(d.get("pontos", 0)))

func _restaurar() -> void:
	var tudo := _ler_tudo()
	if tudo.has(classe):
		de_dicionario(tudo[classe])

func _salvar() -> void:
	if not persistir:
		return
	var tudo := _ler_tudo()
	tudo[classe] = para_dicionario()
	var f := FileAccess.open(caminho, FileAccess.WRITE)
	if f == null:
		push_error("Não foi possível gravar as habilidades: " + caminho)
		return
	f.store_string(JSON.stringify(tudo))

## Save de todas as classes: {classe: {niveis, slots, pontos}}. Arquivo ausente ou inválido = vazio.
func _ler_tudo() -> Dictionary:
	if not persistir or not FileAccess.file_exists(caminho):
		return {}
	var d = JSON.parse_string(FileAccess.get_file_as_string(caminho))
	return d if typeof(d) == TYPE_DICTIONARY else {}
