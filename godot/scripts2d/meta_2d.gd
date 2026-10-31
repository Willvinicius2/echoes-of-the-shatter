extends RefCounted
## Meta-progressão: fragmentos e materiais que sobrevivem à morte, melhorias permanentes e habilidades
## desbloqueáveis, com save em disco (JSON). Definições em data2d/meta.csv e data2d/drops.csv.
## O save guarda só o estado do jogador; nenhum número de balanceamento mora aqui.

const Csv = preload("res://scripts2d/csv2d.gd")

const VERSAO := 1

static var caminho := "user://save_2d.json"   # os testes apontam para outro arquivo

signal mudou

var defs := {}        # id -> {tipo, alvo, stat, modo, valor, custo, nivel_max}
var ordem: Array = []
var drops := {}       # id do inimigo -> {fragmentos, material, material_qtd}
var fragmentos := 0
var materiais := {}   # id do material -> quantidade
var niveis := {}      # id da melhoria -> nível comprado
var receitas := {}    # id -> {tipo, stat, modo, valor, custo: {material: qtd}, fragmentos, estoque_max}
var ordem_receitas: Array = []
var amuletos := {}    # id do amuleto criado -> true
var equipado := ""    # amuleto equipado (1 slot)
var estoque := {}     # id do consumível -> unidades guardadas
var habilidades := {} # classe -> {niveis, slots, pontos} (runtime em habilidades_2d.gd)
var classe := "arqueiro"   # classe escolhida para a próxima corrida
var ativos := {}      # consumíveis gastos ao partir; valem só para a corrida atual

func _init() -> void:
	for r in Csv.rows("res://data2d/meta.csv"):
		defs[r["id"]] = {"tipo": r["tipo"], "alvo": r["alvo"], "stat": r["stat"], "modo": r["modo"],
			"valor": float(r["valor"]) if r["valor"] != "" else 0.0, "custo": int(r["custo"]), "nivel_max": int(r["nivel_max"])}
		ordem.append(r["id"])
	for r in Csv.rows("res://data2d/drops.csv"):
		drops[r["inimigo"]] = {"fragmentos": int(r["fragmentos"]), "material": r["material"], "material_qtd": int(r["material_qtd"])}

	for r in Csv.rows("res://data2d/receitas.csv"):
		var custo := {}
		for k in ["1", "2"]:
			if r["mat" + k] != "":
				custo[r["mat" + k]] = int(r["qtd" + k])
		receitas[r["id"]] = {"tipo": r["tipo"], "stat": r["stat"], "modo": r["modo"], "valor": float(r["valor"]),
			"custo": custo, "fragmentos": int(r["fragmentos"]), "estoque_max": int(r["estoque_max"])}
		ordem_receitas.append(r["id"])

func nivel(id: String) -> int:
	return int(niveis.get(id, 0))

## Habilidade de corrida liberada? Habilidades sem entrada em meta.csv nascem liberadas.
func liberada(upgrade_id: String) -> bool:
	for id in ordem:
		if defs[id]["tipo"] == "habilidade" and defs[id]["alvo"] == upgrade_id:
			return nivel(id) > 0
	return true

func pode_comprar(id: String) -> bool:
	return defs.has(id) and nivel(id) < defs[id]["nivel_max"] and fragmentos >= defs[id]["custo"]

func comprar(id: String) -> bool:
	if not pode_comprar(id):
		return false
	fragmentos -= defs[id]["custo"]
	niveis[id] = nivel(id) + 1
	salvar()
	mudou.emit()
	return true

func tem(id: String) -> bool:
	return receitas[id]["tipo"] == "amuleto" and amuletos.has(id) or receitas[id]["tipo"] == "consumivel" and int(estoque.get(id, 0)) > 0

func pode_criar(id: String) -> bool:
	if not receitas.has(id):
		return false
	var r: Dictionary = receitas[id]
	if r["tipo"] == "amuleto" and amuletos.has(id):
		return false
	if r["tipo"] == "consumivel" and int(estoque.get(id, 0)) >= r["estoque_max"]:
		return false
	if fragmentos < r["fragmentos"]:
		return false
	for m in r["custo"]:
		if int(materiais.get(m, 0)) < r["custo"][m]:
			return false
	return true

func criar(id: String) -> bool:
	if not pode_criar(id):
		return false
	var r: Dictionary = receitas[id]
	fragmentos -= r["fragmentos"]
	for m in r["custo"]:
		materiais[m] = int(materiais[m]) - r["custo"][m]
	if r["tipo"] == "amuleto":
		amuletos[id] = true
		if equipado == "":
			equipado = id
	else:
		estoque[id] = int(estoque.get(id, 0)) + 1
	salvar()
	mudou.emit()
	return true

## Equipa o amuleto (troca o do slot) ou desequipa se já era ele.
func equipar(id: String) -> bool:
	if not amuletos.has(id):
		return false
	equipado = "" if equipado == id else id
	salvar()
	mudou.emit()
	return true

## Ao partir: gasta uma unidade de cada consumível guardado para esta corrida.
func preparar_corrida() -> void:
	ativos = {}
	for id in estoque.keys():
		if int(estoque[id]) > 0:
			estoque[id] = int(estoque[id]) - 1
			ativos[id] = true
	salvar()
	mudou.emit()

## Nomes de stat do arqueiro que valem para outras classes (o guerreiro usa `damage` e `attack_cooldown`).
const ALIAS_STAT := {"arrow_damage": "damage", "shoot_cooldown": "attack_cooldown"}

func _bonus(s: Dictionary, r: Dictionary) -> void:
	var k: String = r["stat"]
	if not s.has(k):
		k = ALIAS_STAT.get(k, "")
		if k == "" or not s.has(k):
			return  # stat que esta classe não tem (ex.: perfuração de flecha no guerreiro)
	if r["modo"] == "mult":
		s[k] = s[k] * (1.0 + r["valor"])
	else:
		s[k] = s[k] + r["valor"]

## Soma os bônus permanentes aos stats base da corrida.
func aplicar(base: Dictionary) -> Dictionary:
	var s := base.duplicate()
	if equipado != "":
		_bonus(s, receitas[equipado])
	for id in ativos:
		_bonus(s, receitas[id])
	for id in ordem:
		var d: Dictionary = defs[id]
		if d["tipo"] != "stat":
			continue
		for _i in nivel(id):
			_bonus(s, d)
	return s

## Ganho de um inimigo morto: {"fragmentos": n, "material": id, "material_qtd": n} (vazio se não dropa).
func drop_de(inimigo: String) -> Dictionary:
	return drops.get(inimigo, {})

## Passa os ganhos da corrida ({"fragmentos": n, "materiais": {id: n}}) para o saldo permanente e salva.
func creditar(ganhos: Dictionary) -> void:
	fragmentos += int(ganhos.get("fragmentos", 0))
	var mats: Dictionary = ganhos.get("materiais", {})
	for m in mats:
		materiais[m] = int(materiais.get(m, 0)) + int(mats[m])
	salvar()
	mudou.emit()

func salvar() -> bool:
	var f := FileAccess.open(caminho + ".tmp", FileAccess.WRITE)
	if f == null:
		push_error("Não foi possível gravar o save: " + caminho)
		return false
	f.store_string(JSON.stringify({"versao": VERSAO, "fragmentos": fragmentos, "materiais": materiais, "niveis": niveis,
		"amuletos": amuletos.keys(), "equipado": equipado, "estoque": estoque,
		"habilidades": habilidades, "classe": classe}))
	f.close()
	# Grava no temporário e troca: save corrompido por queda no meio da escrita não acontece.
	var dir := DirAccess.open(caminho.get_base_dir())
	if dir == null:
		return false
	return dir.rename(caminho.get_file() + ".tmp", caminho.get_file()) == OK or (dir.remove(caminho.get_file()) == OK and dir.rename(caminho.get_file() + ".tmp", caminho.get_file()) == OK)

## Carrega o save. Arquivo ausente ou inválido deixa o estado zerado. Retorna true se leu um save válido.
func carregar() -> bool:
	fragmentos = 0
	materiais = {}
	niveis = {}
	amuletos = {}
	equipado = ""
	estoque = {}
	ativos = {}
	habilidades = {}
	classe = "arqueiro"
	if not FileAccess.file_exists(caminho):
		return false
	var d = JSON.parse_string(FileAccess.get_file_as_string(caminho))
	if typeof(d) != TYPE_DICTIONARY or int(d.get("versao", 0)) != VERSAO:
		return false
	fragmentos = maxi(0, int(d.get("fragmentos", 0)))
	for m in d.get("materiais", {}):
		materiais[str(m)] = maxi(0, int(d["materiais"][m]))
	for id in d.get("niveis", {}):
		if defs.has(id):
			niveis[id] = clampi(int(d["niveis"][id]), 0, defs[id]["nivel_max"])
	for id in d.get("amuletos", []):
		if receitas.has(id) and receitas[id]["tipo"] == "amuleto":
			amuletos[str(id)] = true
	if amuletos.has(str(d.get("equipado", ""))):
		equipado = str(d["equipado"])
	for id in d.get("estoque", {}):
		if receitas.has(id) and receitas[id]["tipo"] == "consumivel":
			estoque[id] = clampi(int(d["estoque"][id]), 0, receitas[id]["estoque_max"])
	var hab = d.get("habilidades", {})
	if typeof(hab) == TYPE_DICTIONARY:
		habilidades = hab
	classe = str(d.get("classe", "arqueiro"))
	mudou.emit()
	return true
