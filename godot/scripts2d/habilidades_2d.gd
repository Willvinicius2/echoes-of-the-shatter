extends RefCounted
## Árvore de habilidades da classe: pontos, pré-requisitos, 4 slots ativos, recarga e passivas.
## Toda regra mora no módulo `rogue` do ShatterCore (API 1.10, docs/tecnico/09 seção 17); este script guarda uma cópia
## de leitura para a UI e a HUD, chama os efeitos da classe e repassa as ações ao core.
## Dados em data2d/habilidades_<classe>.csv; classes em data2d/classes_2d.csv; efeitos ativos em
## scripts2d/efeitos_<classe>_2d.gd com `static func executar(efeito, jogador, def, nivel, mira) -> bool`.
## A mana e os efeitos ficam no cliente. Nenhum número de balanceamento mora aqui.

const Csv = preload("res://scripts2d/csv2d.gd")
const Nucleo = preload("res://scripts2d/nucleo_2d.gd")

const SLOTS := 4
## Save antigo (antes do core): {classe: {niveis, slots, pontos}}. O meta_2d.gd o migra para o save do core uma vez.
const LEGADO := "user://habilidades_2d.json"
const CAMPOS_NUM := ["tier", "pontos", "nivel_max", "cd", "custo", "dano", "qtd", "angulo", "raio", "duracao", "alcance", "valor", "escala"]

## Save de um núcleo próprio (sem o núcleo do meta). Vazio = não grava. Os testes apontam para um arquivo deles.
static var caminho := ""

signal mudou
signal usada(slot: int, id: String)

var classe := ""
var defs := {}            # id -> linha do CSV (só para exibir: nome, ramo, tier, ícone)
var ordem: Array = []     # ids na ordem do CSV
var niveis := {}          # id -> nível aprendido (cópia do core)
var slots: Array = ["", "", "", ""]
var recargas := {}        # id -> segundos restantes (cópia do core, atualizada nas ações)
var pontos := 0           # saldo de pontos de habilidade (cópia do core)
var persistir := true     # falso: o núcleo próprio não lê nem grava o save
## Núcleo do core. A corrida passa o do meta (mesmo save, pontos por sala limpa); sem ele, cria um núcleo próprio.
var nucleo: Object
var _proprio := false
var _efeitos: GDScript

## Linhas de data2d/classes_2d.csv por id.
static func classes() -> Dictionary:
	var out := {}
	for r in Csv.rows("res://data2d/classes_2d.csv"):
		out[r["id"]] = r
	return out

## Carrega a árvore da classe. Arquivo de dados ou de efeitos ausente deixa a árvore vazia (sem erro).
## `caminho_csv` fora de classes_2d.csv (fixture dos testes) cria um núcleo próprio que conhece essa classe.
func carregar_classe(id: String, caminho_csv := "", caminho_efeitos := "") -> void:
	classe = id
	defs.clear()
	ordem.clear()
	_efeitos = null
	var cl: Dictionary = classes().get(id, {})
	var csv: String = caminho_csv if caminho_csv != "" else cl.get("habilidades", "")
	if csv != "" and FileAccess.file_exists(csv):
		for r in Csv.rows(csv):
			var d: Dictionary = r.duplicate()
			for c in CAMPOS_NUM:
				d[c] = float(r.get(c, "")) if str(r.get(c, "")) != "" else 0.0
			defs[d["id"]] = d
			ordem.append(d["id"])
	var script_efeitos: String = caminho_efeitos if caminho_efeitos != "" else cl.get("efeitos", "")
	if script_efeitos != "" and ResourceLoader.exists(script_efeitos):
		_efeitos = load(script_efeitos)
	if caminho_csv != "" and caminho_csv != cl.get("habilidades", ""):
		_criar_nucleo({id: caminho_csv})
	elif nucleo == null:
		_criar_nucleo({})
	if nucleo != null:
		nucleo.classe_definir(id)
	sincronizar(false)
	mudou.emit()

func _criar_nucleo(extras: Dictionary) -> void:
	nucleo = Nucleo.criar(extras)
	_proprio = true
	if nucleo != null and persistir and caminho != "":
		nucleo.definir_save(ProjectSettings.globalize_path(caminho))
		nucleo.meta_carregar()

## Copia pontos, níveis, slots e recargas do core.
func sincronizar(avisar := true) -> void:
	niveis = {}
	recargas = {}
	slots = ["", "", "", ""]
	pontos = 0
	if nucleo == null:
		return
	var e: Dictionary = nucleo.habilidades_estado()
	pontos = int(e.get("points", 0))
	var sv: Array = e.get("slots", [])
	for i in mini(SLOTS, sv.size()):
		slots[i] = str(sv[i])
	for s in e.get("skills", []):
		if int(s["level"]) > 0:
			niveis[str(s["id"])] = int(s["level"])
		if float(s["cooldown"]) > 0.0:
			recargas[str(s["id"])] = float(s["cooldown"])
	if avisar:
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

## Linha da habilidade já escalonada pelo nível (n = 0 mostra o valor base), calculada pelo core.
func def_nivel(id: String, n := -1) -> Dictionary:
	if nucleo == null:
		return defs.get(id, {}).duplicate()
	return nucleo.habilidade_def(id, n)

func pode_aprender(id: String) -> bool:
	return nucleo != null and nucleo.habilidade_pode_aprender(id) == 0

func aprender(id: String) -> bool:
	return _acao(nucleo != null and nucleo.habilidade_aprender(id) == 0)

## Soma pontos ao saldo (testes e recompensas; a sala limpa e o chefe já dão pontos pelo core).
func ganhar_pontos(n: int) -> void:
	_acao(nucleo != null and nucleo.habilidades_ganhar_pontos(n) == 0)

## Redistribuição gratuita: devolve todos os pontos gastos e esvazia os slots.
func redistribuir() -> void:
	_acao(nucleo != null and nucleo.habilidades_redistribuir() == 0)

## Põe uma habilidade ativa aprendida no slot (id vazio limpa). Se já estava em outro slot, os dois trocam.
func equipar(slot: int, id: String) -> bool:
	return _acao(nucleo != null and nucleo.habilidade_equipar(slot, id) == 0)

func _acao(ok: bool) -> bool:
	if ok:
		sincronizar()
	return ok

func tick(delta: float) -> void:
	if nucleo != null and not recargas.is_empty():
		nucleo.habilidades_tick(delta)
		for id in recargas.keys():
			recargas[id] = maxf(0.0, recargas[id] - delta)
			if recargas[id] <= 0.0:
				recargas.erase(id)

## Fração 0..1 da recarga do slot (0 = pronto), para a HUD.
func recarga_slot(slot: int) -> float:
	if nucleo == null or slot < 0 or slot >= SLOTS:
		return 0.0
	return nucleo.habilidade_recarga(slot)

## Usa o slot: o core confere recarga e mana, o efeito da classe roda e só então o core inicia a recarga e diz o custo.
func usar(slot: int, jogador: Node2D, mira: Vector2) -> bool:
	if nucleo == null or slot < 0 or slot >= SLOTS or slots[slot] == "" or _efeitos == null:
		return false
	var mana: float = jogador.mana if "mana" in jogador else 0.0
	if nucleo.habilidade_pode_usar(slot, mana) != 0:
		return false
	var id: String = slots[slot]
	var d := def_nivel(id)
	if not _efeitos.executar(d["efeito"], jogador, d, nivel(id), mira.normalized()):
		return false
	var r: Dictionary = nucleo.habilidade_usar(slot, mana)
	if int(r["resultado"]) != 0:
		return false
	if "mana" in jogador:
		jogador.gastar_mana(float(r["custo"]))
	sincronizar(false)
	usada.emit(slot, id)
	return true

## Aplica as passivas aprendidas sobre os stats (idempotente: parte sempre de `base`), calculadas pelo core.
func aplicar_passivas(base: Dictionary) -> Dictionary:
	if nucleo == null:
		return base.duplicate()
	return nucleo.aplicar_passivas(base)

## Estado da árvore no formato do save ({niveis, slots, pontos}).
func para_dicionario() -> Dictionary:
	return {"niveis": niveis.duplicate(), "slots": slots.duplicate(), "pontos": pontos}

## Passa o save antigo (user://habilidades_2d.json, de antes do core) para o save do meta, uma vez: só se o save do core
## ainda não tem habilidades. O arquivo antigo é renomeado para .migrado.
static func migrar_legado(n: Object, caminho_meta: String) -> void:
	if n == null or not FileAccess.file_exists(LEGADO):
		return
	var antigo = JSON.parse_string(FileAccess.get_file_as_string(LEGADO))
	var save = JSON.parse_string(n.meta_texto_save())
	if typeof(antigo) == TYPE_DICTIONARY and not antigo.is_empty() and typeof(save) == TYPE_DICTIONARY \
			and (typeof(save.get("habilidades")) != TYPE_DICTIONARY or save["habilidades"].is_empty()):
		save["habilidades"] = antigo
		var f := FileAccess.open(caminho_meta, FileAccess.WRITE)
		if f != null:
			f.store_string(JSON.stringify(save))
			f.close()
			n.meta_carregar()
	DirAccess.rename_absolute(LEGADO, LEGADO + ".migrado")
