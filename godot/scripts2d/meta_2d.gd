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

func _init() -> void:
	for r in Csv.rows("res://data2d/meta.csv"):
		defs[r["id"]] = {"tipo": r["tipo"], "alvo": r["alvo"], "stat": r["stat"], "modo": r["modo"],
			"valor": float(r["valor"]) if r["valor"] != "" else 0.0, "custo": int(r["custo"]), "nivel_max": int(r["nivel_max"])}
		ordem.append(r["id"])
	for r in Csv.rows("res://data2d/drops.csv"):
		drops[r["inimigo"]] = {"fragmentos": int(r["fragmentos"]), "material": r["material"], "material_qtd": int(r["material_qtd"])}

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

## Soma os bônus permanentes aos stats base da corrida.
func aplicar(base: Dictionary) -> Dictionary:
	var s := base.duplicate()
	for id in ordem:
		var d: Dictionary = defs[id]
		if d["tipo"] != "stat":
			continue
		for _i in nivel(id):
			if d["modo"] == "mult":
				s[d["stat"]] = s[d["stat"]] * (1.0 + d["valor"])
			else:
				s[d["stat"]] = s[d["stat"]] + d["valor"]
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
	f.store_string(JSON.stringify({"versao": VERSAO, "fragmentos": fragmentos, "materiais": materiais, "niveis": niveis}))
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
	mudou.emit()
	return true
