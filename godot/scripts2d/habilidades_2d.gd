extends RefCounted
## Árvore de habilidades da classe: pontos, pré-requisitos, 4 slots ativos, recarga e passivas.
## Toda regra mora no módulo `rogue` do ShatterCore (API 1.10, docs/tecnico/09 seção 17); este script guarda uma cópia
## de leitura para a UI e a HUD, chama os efeitos da classe e repassa as ações ao core.
## Dados em data2d/habilidades_<classe>.csv; classes em data2d/classes_2d.csv; efeitos ativos em
## scripts2d/efeitos_<classe>_2d.gd com `static func executar(efeito, jogador, def, nivel, mira) -> bool`.
## A mana e os efeitos ficam no cliente. Nenhum número de balanceamento mora aqui.

const Csv = preload("res://scripts2d/csv2d.gd")
const Nucleo = preload("res://scripts2d/nucleo_2d.gd")
const Alvos = preload("res://scripts2d/alvos_2d.gd")
const Passivos = preload("res://scripts2d/passivos_2d.gd")

const SLOTS := 4
## Autocast: como cada ativa (e o ataque básico, id `basico`) escolhe o alvo e se é a ult manual. Ver alvos_2d.escolher.
const MIRAS := "res://data2d/habilidades_mira.csv"
## Save antigo (antes do core): {classe: {niveis, slots, pontos}}. O meta_2d.gd o migra para o save do core uma vez.
const LEGADO := "user://habilidades_2d.json"
const CAMPOS_NUM := ["tier", "pontos", "nivel_max", "cd", "custo", "dano", "qtd", "angulo", "raio", "duracao", "alcance", "valor", "escala", "espera", "recup"]

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
var miras := {}           # id -> {mira, ult, alcance, min_alvos} da classe (data2d/habilidades_mira.csv)
## Árvore de passivos da classe (passivos_2d.gd, doc 33): modifica o def das ativas e os stats do jogador.
var passivos: RefCounted

## Linhas de data2d/classes_2d.csv por id.
static func classes() -> Dictionary:
	var out := {}
	for r in Csv.rows("res://data2d/classes_2d.csv"):
		out[r["id"]] = r
	return out

## Carrega a árvore da classe. Arquivo de dados ou de efeitos ausente deixa a árvore vazia (sem erro).
## `caminho_csv` fora de classes_2d.csv (fixture dos testes) cria um núcleo próprio que conhece essa classe.
func carregar_classe(id: String, caminho_csv := "", caminho_efeitos := "", caminho_passivos := "", caminho_tags := "") -> void:
	classe = id
	defs.clear()
	ordem.clear()
	_efeitos = null
	passivos = Passivos.new()
	passivos.persistir = persistir
	passivos.carregar_classe(id, caminho_passivos, caminho_tags)
	passivos.mudou.connect(func() -> void: mudou.emit())
	var cl: Dictionary = classes().get(id, {})
	miras = carregar_miras(id)
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

## Tecla da ult (botão direito do mouse, X e o botão Y do controle), criada na hora se o projeto não a tiver.
static func registrar_tecla_ult() -> void:
	if InputMap.has_action("ult"):
		return
	InputMap.add_action("ult")
	var m := InputEventMouseButton.new()
	m.button_index = MOUSE_BUTTON_RIGHT
	InputMap.action_add_event("ult", m)
	var k := InputEventKey.new()
	k.physical_keycode = KEY_X
	InputMap.action_add_event("ult", k)
	var j := InputEventJoypadButton.new()
	j.button_index = JOY_BUTTON_Y
	InputMap.action_add_event("ult", j)

## Linhas de habilidades_mira.csv da classe `id`, por id de habilidade.
static func carregar_miras(id: String) -> Dictionary:
	var out := {}
	if not FileAccess.file_exists(MIRAS):
		return out
	for r in Csv.rows(MIRAS):
		if r.get("classe", "") == id:
			out[r["id"]] = {"mira": str(r.get("mira", "")), "ult": str(r.get("ult", "0")) == "1",
				"alcance": float(r["alcance"]) if str(r.get("alcance", "")) != "" else 0.0,
				"min_alvos": maxi(1, int(str(r.get("min_alvos", "1"))))}
	return out

## Como a ativa `id` mira no autocast; vazio = sem autocast (só pela tecla).
func mira_de(id: String) -> String:
	return str(miras.get(id, {}).get("mira", ""))

## A ult não dispara sozinha: só na tecla de ult (ou na do slot).
func eh_ult(id: String) -> bool:
	return bool(miras.get(id, {}).get("ult", false))

## Slot que guarda a ult equipada (-1 se nenhuma).
func slot_ult() -> int:
	for i in SLOTS:
		if slots[i] != "" and eh_ult(slots[i]):
			return i
	return -1

## A ativa `id` dispara sozinha (equipada, com mira definida, não manual e não ult)?
func automatica(id: String) -> bool:
	var m := mira_de(id)
	return id != "" and m != "" and m != "manual" and not eh_ult(id)

## Alvo do autocast para `id` (ou `basico`) a partir de `pos`: {} = não há o que acertar agora; senão {dir, ponto}.
## `alcance_padrao` vale quando o CSV de miras deixa o alcance vazio.
func alvo_auto(id: String, arvore: SceneTree, pos: Vector2, alcance_padrao := 0.0) -> Dictionary:
	var m: Dictionary = miras.get(id, {})
	if m.is_empty():
		return {}
	var alcance: float = m["alcance"] if m["alcance"] > 0.0 else alcance_padrao
	var raio := 0.0
	if defs.has(id):
		raio = float(def_nivel(id).get("raio", 0.0))
	return Alvos.escolher(arvore, pos, m["mira"], alcance, m["min_alvos"], raio)

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

## Linha da habilidade já escalonada pelo nível (n = 0 mostra o valor base), calculada pelo core, e depois passada
## pela árvore de passivos (dano, qtd, raio, vel, perfura, forma...).
func def_nivel(id: String, n := -1) -> Dictionary:
	var d := def_base(id, n)
	if passivos == null or d.is_empty():
		return d
	return passivos.resolver(id, d, tags_de(id))

## Linha escalonada pelo nível sem os passivos (para a pré-visualização da árvore).
func def_base(id: String, n := -1) -> Dictionary:
	if nucleo == null:
		return defs.get(id, {}).duplicate()
	return nucleo.habilidade_def(id, n)

## Tags da habilidade para os passivos: as de habilidades_tags.csv mais o ramo e o tipo.
func tags_de(id: String) -> Array:
	var d: Dictionary = defs.get(id, {})
	return passivos.tags_de(id, [str(d.get("ramo", "")), str(d.get("tipo", ""))]) if passivos != null else []

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

## Zera as recargas da classe (reset do jogador; o core também zera ao começar uma corrida). O tick longo é a mesma
## regra do core, sem caminho novo na API.
func limpar_recargas() -> void:
	if nucleo != null:
		nucleo.habilidades_tick(1.0e9)
	recargas.clear()

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

## Inicia a recarga da ativa `id` sem passar por usar(): para classes que pagam com outro recurso (o ímpeto do Guerreiro)
## e já rodaram o efeito. `recurso` é o que a classe tem para pagar; o core confere slot, recarga e custo.
func iniciar_recarga(id: String, recurso: float) -> bool:
	var slot := slots.find(id)
	if nucleo == null or id == "" or slot < 0:
		return false
	var ok: bool = int(nucleo.habilidade_usar(slot, recurso)["resultado"]) == 0
	sincronizar(false)
	return ok

## Aplica as passivas aprendidas sobre os stats (idempotente: parte sempre de `base`), calculadas pelo core.
func aplicar_passivas(base: Dictionary) -> Dictionary:
	var s: Dictionary = base.duplicate() if nucleo == null else nucleo.aplicar_passivas(base)
	return passivos.stats_globais(s) if passivos != null else s

## Modificadores `global` da árvore de passivos sobre stats que o core já calculou (idempotente).
func aplicar_passivos_globais(stats: Dictionary) -> Dictionary:
	return passivos.stats_globais(stats) if passivos != null else stats.duplicate()

## Estado da árvore no formato do save ({niveis, slots, pontos}).
func para_dicionario() -> Dictionary:
	return {"niveis": niveis.duplicate(), "slots": slots.duplicate(), "pontos": pontos,
		"passivos": passivos.para_dicionario() if passivos != null else {}}

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
