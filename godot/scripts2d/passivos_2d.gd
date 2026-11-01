extends RefCounted
## Árvore de passivos da classe (docs/design/33_arvore_passivos_arqueiro.md): um grafo de nós que modificam as
## habilidades (dano, quantidade, área, velocidade, forma...) ou os stats do jogador. Toda regra numérica mora nos CSV:
## nós em data2d/passivas_<classe>.csv, tags por habilidade em data2d/habilidades_tags.csv e tetos em
## data2d/passivas_limites.csv. Este script só resolve: `def` final = (base + add) × (1 + Σinc) × Π(1 + mais), e `set`.
## O estado (nós ativos e pontos) fica no cliente, em user://passivos_2d.json, por classe.

const Csv = preload("res://scripts2d/csv2d.gd")

const TAGS := "res://data2d/habilidades_tags.csv"
const LIMITES := "res://data2d/passivas_limites.csv"
const PARTIDA := "res://data2d/passivas_partida.csv"
const OPS := ["add", "inc", "mais", "set"]
const TIPOS := ["raiz", "pequeno", "notavel", "transforma", "keystone"]
## Campos do `def` que um nó pode mirar numa habilidade (`skill:` ou `tag:`). `projeteis` é virtual: vira `qtd` nas
## habilidades com a tag `multi` e `proj_extra` (cópias em leque do mesmo tiro) nas demais. `cd` e `custo` são do core
## e só mudam por `global` (skill_cd_mult).
const CAMPOS_SKILL := ["dano", "qtd", "projeteis", "angulo", "raio", "duracao", "alcance", "valor", "vel", "perfura", "forma"]
## Campos que a resolução acrescenta ao def mesmo sem nó (os efeitos leem com get e valor padrão).
const PADROES := {"vel": 1.0, "perfura": 0.0, "proj_extra": 0.0, "forma": ""}

## Save próprio (os testes apontam para outro arquivo). Vazio = não grava.
static var caminho := "user://passivos_2d.json"

signal mudou

var classe := ""
var defs := {}        # id -> {id, setor, tipo, custo, x, y, vizinhos: [], exclui: [], mods: [{alvo, campo, op, valor, forma}], icone}
var ordem: Array = []
var ativos := {}      # id -> true (a raiz está sempre ativa)
var pontos := 0
var persistir := true
var tags := {}        # id da habilidade -> [tags]
var limites := {}     # chave -> valor (passivas_limites.csv)
## Passivas da partida (cartas de nível e nós de preparo): `run_*` nos stats do jogador viram modificadores sintéticos.
var partida_defs: Array = []   # [{stat, alvo, campo, op, fator}] de passivas_partida.csv
var partida := {}              # stat run_* -> valor acumulado na corrida (só os diferentes de zero)

## Carrega os nós da classe (`caminho_csv` = fixture dos testes). Arquivo ausente deixa a árvore vazia, sem erro.
func carregar_classe(id: String, caminho_csv := "", caminho_tags := "") -> void:
	classe = id
	defs.clear()
	ordem.clear()
	ativos.clear()
	pontos = 0
	limites = Csv.kv(LIMITES) if FileAccess.file_exists(LIMITES) else {}
	tags = carregar_tags(id, caminho_tags)
	partida_defs = carregar_partida()
	partida.clear()
	var csv: String = caminho_csv if caminho_csv != "" else "res://data2d/passivas_%s.csv" % id
	if FileAccess.file_exists(csv):
		for r in Csv.rows(csv):
			var nid: String = r["id"]
			if not defs.has(nid):
				defs[nid] = {"id": nid, "setor": r.get("setor", ""), "tipo": r.get("tipo", "pequeno"),
					"custo": int(_num(r.get("custo", "0"))), "x": _num(r.get("x", "0")), "y": _num(r.get("y", "0")),
					"vizinhos": _lista(r.get("vizinhos", "")), "exclui": _lista(r.get("exclui", "")),
					"mods": [], "icone": r.get("icone", "")}
				ordem.append(nid)
			if str(r.get("campo", "")) != "":
				defs[nid]["mods"].append({"alvo": str(r.get("alvo", "global")), "campo": str(r["campo"]),
					"op": str(r.get("op", "inc")), "valor": _num(r.get("valor", "0")), "forma": str(r.get("forma", ""))})
	for nid in ordem:
		if defs[nid]["tipo"] == "raiz":
			ativos[nid] = true
	_carregar()
	mudou.emit()

## Tags de cada habilidade da classe (data2d/habilidades_tags.csv: classe,id,tags com `+`).
static func carregar_tags(classe_id: String, arquivo := "") -> Dictionary:
	var out := {}
	var csv: String = arquivo if arquivo != "" else TAGS
	if not FileAccess.file_exists(csv):
		return out
	for r in Csv.rows(csv):
		if r.get("classe", "") == classe_id:
			out[r["id"]] = _lista(r.get("tags", ""))
	return out

## Tabela que liga cada stat `run_*` a um modificador de habilidade (data2d/passivas_partida.csv).
static func carregar_partida(arquivo := "") -> Array:
	var out := []
	var csv: String = arquivo if arquivo != "" else PARTIDA
	if not FileAccess.file_exists(csv):
		return out
	for r in Csv.rows(csv):
		out.append({"stat": str(r["stat"]), "alvo": str(r["alvo"]), "campo": str(r["campo"]),
			"op": str(r.get("op", "inc")), "fator": _num(r.get("fator", "1"))})
	return out

static func _lista(s: String) -> Array:
	var out := []
	for p in s.split("+", false):
		if p.strip_edges() != "":
			out.append(p.strip_edges())
	return out

static func _num(s) -> float:
	return float(s) if str(s) != "" else 0.0

func limite(chave: String, padrao: float) -> float:
	return float(limites.get(chave, padrao))

# ---- estado ----------------------------------------------------------------------------------------------------------

func ativo(id: String) -> bool:
	return ativos.has(id)

func raiz() -> String:
	for id in ordem:
		if defs[id]["tipo"] == "raiz":
			return id
	return ""

func setores() -> Array:
	var out := []
	for id in ordem:
		if not out.has(defs[id]["setor"]):
			out.append(defs[id]["setor"])
	return out

func ids_do_setor(setor: String) -> Array:
	return ordem.filter(func(i): return defs[i]["setor"] == setor)

## Nós ativos do tipo (keystones contam para o teto `keystones_max`).
func contar_tipo(tipo: String) -> int:
	var n := 0
	for id in ativos:
		if defs.has(id) and defs[id]["tipo"] == tipo:
			n += 1
	return n

## Um vizinho ativo abre o nó (a raiz abre os seus); o próprio nó ainda não ativo; sem exclusão ativa; pontos bastam.
func pode_ativar(id: String) -> bool:
	if not defs.has(id) or ativos.has(id):
		return false
	var d: Dictionary = defs[id]
	var barrado: bool = d["tipo"] == "raiz" or pontos < int(d["custo"]) \
		or (d["tipo"] == "keystone" and contar_tipo("keystone") >= int(limite("keystones_max", 1.0)))
	return not barrado and not excluido(id) and alcancavel(id)

## Um nó ativo exclui este (ou este exclui um ativo)?
func excluido(id: String) -> bool:
	for e in defs[id]["exclui"]:
		if ativos.has(e):
			return true
	for outro in ativos:
		if defs.has(outro) and defs[outro]["exclui"].has(id):
			return true
	return false

## Algum vizinho já está ativo (ou o nó é vizinho de algum ativo).
func alcancavel(id: String) -> bool:
	for v in defs[id]["vizinhos"]:
		if ativos.has(v):
			return true
	for outro in ativos:
		if defs.has(outro) and defs[outro]["vizinhos"].has(id):
			return true
	return false

func ativar(id: String) -> bool:
	if not pode_ativar(id):
		return false
	pontos -= int(defs[id]["custo"])
	ativos[id] = true
	_salvar()
	mudou.emit()
	return true

func ganhar_pontos(n: int) -> void:
	if n <= 0:
		return
	pontos += n
	_salvar()
	mudou.emit()

## Redistribuição gratuita: devolve tudo e deixa só a raiz.
func redistribuir() -> void:
	for id in ativos.keys():
		if defs.has(id) and defs[id]["tipo"] != "raiz":
			pontos += int(defs[id]["custo"])
			ativos.erase(id)
	_salvar()
	mudou.emit()

func pontos_gastos() -> int:
	var n := 0
	for id in ativos:
		if defs.has(id):
			n += int(defs[id]["custo"])
	return n

# ---- resolução --------------------------------------------------------------------------------------------------------

## Tags da habilidade: as do CSV mais o ramo e o tipo da linha (`extras`).
func tags_de(id: String, extras: Array = []) -> Array:
	var out: Array = tags.get(id, []).duplicate()
	for e in extras:
		if str(e) != "" and not out.has(e):
			out.append(e)
	return out

## Lê os `run_*` dos stats do jogador (já com cartas e nós de preparo) e guarda o que vale na partida. Devolve true se
## mudou (a HUD e as habilidades releem o def).
func definir_partida(stats: Dictionary) -> bool:
	var novo := {}
	for d in partida_defs:
		var v: float = float(stats.get(d["stat"], 0.0))
		if v != 0.0:
			novo[d["stat"]] = v
	var mudou_algo: bool = novo != partida
	partida = novo
	return mudou_algo

## Modificadores sintéticos da partida (mesmo formato dos nós): valor = stat × fator.
func mods_partida() -> Array:
	var out := []
	for d in partida_defs:
		if partida.has(d["stat"]):
			out.append({"alvo": d["alvo"], "campo": d["campo"], "op": d["op"],
				"valor": float(partida[d["stat"]]) * float(d["fator"]), "forma": ""})
	return out

## Modificadores ativos que valem para a habilidade `id` com estas tags (`global` fica de fora).
func mods_para(id: String, tags_hab: Array, extra_ativos: Array = []) -> Array:
	var out := []
	for m in mods_partida():
		var a: String = m["alvo"]
		if a == "skill:" + id or (a.begins_with("tag:") and tags_hab.has(a.substr(4))):
			out.append(m)
	var lista: Array = ativos.keys()
	for e in extra_ativos:
		if not lista.has(e):
			lista.append(e)
	for nid in lista:
		if not defs.has(nid):
			continue
		for m in defs[nid]["mods"]:
			var alvo: String = m["alvo"]
			if alvo == "skill:" + id or (alvo.begins_with("tag:") and tags_hab.has(alvo.substr(4))):
				out.append(m)
	return out

## Aplica os nós ativos sobre a linha já escalonada pelo nível (`base`). Devolve um def novo, com os campos padrão
## (vel, perfura, proj_extra, forma) sempre presentes. `extra_ativos` = nós a mais, só para pré-visualizar.
func resolver(id: String, base: Dictionary, tags_hab: Array = [], extra_ativos: Array = []) -> Dictionary:
	var def: Dictionary = base.duplicate()
	for k in PADROES:
		if not def.has(k):
			def[k] = PADROES[k]
	var t: Array = tags_hab if not tags_hab.is_empty() else tags_de(id, [str(base.get("ramo", "")), str(base.get("tipo", ""))])
	var acc := {}   # campo -> {add, inc, mais, set, forma}
	for m in mods_para(id, t, extra_ativos):
		var campo: String = m["campo"]
		if campo == "projeteis":
			campo = "qtd" if t.has("multi") else "proj_extra"
		if not acc.has(campo):
			acc[campo] = {"add": 0.0, "inc": 0.0, "mais": 1.0, "set": null, "forma": ""}
		match m["op"]:
			"add":
				acc[campo]["add"] += float(m["valor"])
			"inc":
				acc[campo]["inc"] += float(m["valor"])
			"mais":
				acc[campo]["mais"] *= 1.0 + float(m["valor"])
			"set":
				if campo == "forma":
					acc[campo]["forma"] = str(m["forma"])
				else:
					acc[campo]["set"] = float(m["valor"])
	for campo in acc:
		var a: Dictionary = acc[campo]
		if campo == "forma":
			if a["forma"] != "":
				def["forma"] = a["forma"]
			continue
		var b: float = float(def.get(campo, 0.0))
		var add: float = a["add"]
		var inc: float = a["inc"]
		if campo == "qtd" or campo == "proj_extra":
			add = minf(add, limite("qtd_add_max", 6.0))
		if campo == "raio" or campo == "angulo":
			inc = minf(inc, limite("area_inc_max", 1.5))
		if campo == "vel":
			inc = minf(inc, limite("vel_inc_max", 1.0))
		var v: float = (b + add) * (1.0 + inc) * a["mais"]
		if a["set"] != null:
			v = float(a["set"])
		if campo == "angulo":
			v = minf(v, limite("angulo_max", 360.0))
		if campo == "qtd" or campo == "proj_extra" or campo == "perfura":
			v = float(maxi(0, int(round(v))))
		if campo == "vel":
			v = maxf(v, limite("vel_min", 0.25))
		if campo != "vel" and campo != "forma":
			v = maxf(v, 0.0)
		def[campo] = v
	return def

## Modificadores `global` sobre os stats do jogador (idempotente: parte de `base`).
func stats_globais(base: Dictionary, extra_ativos: Array = []) -> Dictionary:
	var s: Dictionary = base.duplicate()
	var acc := {}
	var lista: Array = ativos.keys()
	for e in extra_ativos:
		if not lista.has(e):
			lista.append(e)
	for nid in lista:
		if not defs.has(nid):
			continue
		for m in defs[nid]["mods"]:
			if m["alvo"] != "global":
				continue
			var campo: String = m["campo"]
			if not acc.has(campo):
				acc[campo] = {"add": 0.0, "inc": 0.0, "mais": 1.0, "set": null}
			match m["op"]:
				"add":
					acc[campo]["add"] += float(m["valor"])
				"inc":
					acc[campo]["inc"] += float(m["valor"])
				"mais":
					acc[campo]["mais"] *= 1.0 + float(m["valor"])
				"set":
					acc[campo]["set"] = float(m["valor"])
	for campo in acc:
		var a: Dictionary = acc[campo]
		var b: float = float(s.get(campo, 0.0))
		var v: float = (b + a["add"]) * (1.0 + a["inc"]) * a["mais"]
		if a["set"] != null:
			v = float(a["set"])
		if campo == "skill_cd_mult" or campo == "shoot_cooldown":
			v = maxf(v, b * limite("cd_min_frac", 0.35))
		s[campo] = v
	return s

## Pré-visualização "antes → depois" do nó `id` para a UI: lista de {skill, campo, antes, depois}. `defs_hab` = id da
## habilidade -> def escalonado (sem passivos) das habilidades aprendidas; `stats` = stats do jogador para os globais.
func previa(id: String, defs_hab: Dictionary, tags_por_hab: Dictionary, stats: Dictionary = {}) -> Array:
	var out := []
	if not defs.has(id):
		return out
	for hid in defs_hab:
		var t: Array = tags_por_hab.get(hid, [])
		var antes := resolver(hid, defs_hab[hid], t)
		var depois := resolver(hid, defs_hab[hid], t, [id])
		for campo in depois:
			if antes.get(campo) != depois[campo]:
				out.append({"skill": hid, "campo": campo, "antes": antes.get(campo), "depois": depois[campo]})
	if not stats.is_empty():
		var sa := stats_globais(stats)
		var sd := stats_globais(stats, [id])
		for campo in sd:
			if sa.get(campo) != sd[campo]:
				out.append({"skill": "", "campo": campo, "antes": sa.get(campo), "depois": sd[campo]})
	return out

# ---- validação (testes) -----------------------------------------------------------------------------------------------

## Problemas da tabela: vizinho/exclusão inexistente, nó fora do alcance da raiz, campo ou op inválido, alvo sem
## habilidade conhecida (`ids_hab`). Vazio = tudo certo.
func validar(ids_hab: Array) -> Array:
	var erros := []
	var r := raiz()
	if r == "":
		erros.append("sem nó raiz")
	for id in ordem:
		var d: Dictionary = defs[id]
		if not TIPOS.has(d["tipo"]):
			erros.append("%s: tipo %s" % [id, d["tipo"]])
		for v in d["vizinhos"]:
			if not defs.has(v):
				erros.append("%s: vizinho %s não existe" % [id, v])
		for e in d["exclui"]:
			if not defs.has(e):
				erros.append("%s: exclui %s que não existe" % [id, e])
		if d["tipo"] != "raiz" and d["mods"].is_empty():
			erros.append("%s: sem modificador" % id)
		for m in d["mods"]:
			if not OPS.has(m["op"]):
				erros.append("%s: op %s" % [id, m["op"]])
			var alvo: String = m["alvo"]
			if alvo.begins_with("skill:"):
				if not ids_hab.has(alvo.substr(6)):
					erros.append("%s: habilidade %s não existe" % [id, alvo.substr(6)])
				if not CAMPOS_SKILL.has(m["campo"]):
					erros.append("%s: campo %s não vale para habilidade" % [id, m["campo"]])
			elif alvo.begins_with("tag:"):
				if not CAMPOS_SKILL.has(m["campo"]):
					erros.append("%s: campo %s não vale para tag" % [id, m["campo"]])
			elif alvo != "global":
				erros.append("%s: alvo %s" % [id, alvo])
			if m["campo"] == "forma" and (m["op"] != "set" or m["forma"] == ""):
				erros.append("%s: forma exige op set e um nome" % id)
	# alcance a partir da raiz (vizinhança é simétrica)
	if r != "":
		var vistos := {r: true}
		var fila := [r]
		while not fila.is_empty():
			var atual: String = fila.pop_front()
			for id in ordem:
				if vistos.has(id):
					continue
				if defs[id]["vizinhos"].has(atual) or defs[atual]["vizinhos"].has(id):
					vistos[id] = true
					fila.append(id)
		for id in ordem:
			if not vistos.has(id):
				erros.append("%s: fora do alcance da raiz" % id)
	return erros

# ---- save ------------------------------------------------------------------------------------------------------------

func para_dicionario() -> Dictionary:
	var lista := []
	for id in ordem:
		if ativos.has(id) and defs[id]["tipo"] != "raiz":
			lista.append(id)
	return {"ativos": lista, "pontos": pontos}

func _salvar() -> void:
	if not persistir or caminho == "":
		return
	var tudo := _ler_arquivo()
	tudo[classe] = para_dicionario()
	var f := FileAccess.open(caminho, FileAccess.WRITE)
	if f != null:
		f.store_string(JSON.stringify(tudo))
		f.close()

func _carregar() -> void:
	if not persistir or caminho == "":
		return
	var d: Dictionary = _ler_arquivo().get(classe, {})
	pontos = int(d.get("pontos", 0))
	for id in d.get("ativos", []):
		if defs.has(str(id)):
			ativos[str(id)] = true

static func _ler_arquivo() -> Dictionary:
	if caminho == "" or not FileAccess.file_exists(caminho):
		return {}
	var j = JSON.parse_string(FileAccess.get_file_as_string(caminho))
	return j if typeof(j) == TYPE_DICTIONARY else {}
