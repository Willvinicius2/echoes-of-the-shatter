extends RefCounted
## Meta-progressão: fragmentos e materiais que sobrevivem à morte, melhorias permanentes, habilidades desbloqueáveis e Forja.
## Toda regra mora no módulo `rogue` do ShatterCore (nucleo_2d.gd); este script só guarda uma cópia para a UI ler e repassa
## as ações. O save é gravado pelo core (JSON versionado, mesmo formato de antes). Números em data2d/*.csv.

const Nucleo = preload("res://scripts2d/nucleo_2d.gd")

static var caminho := "user://save_2d.json"   # os testes apontam para outro arquivo

signal mudou

var nucleo: Object
var defs := {}        # id -> {tipo, alvo, stat, modo, valor, custo, nivel_max}
var ordem: Array = []
var fragmentos := 0
var materiais := {}   # id do material -> quantidade
var niveis := {}      # id da melhoria -> nível comprado
var receitas := {}    # id -> {tipo, stat, modo, valor, custo: {material: qtd}, fragmentos, estoque_max}
var ordem_receitas: Array = []
var amuletos := {}    # id do amuleto criado -> true
var equipado := ""    # amuleto equipado (1 slot)
var estoque := {}     # id do consumível -> unidades guardadas
var ativos := {}      # consumíveis gastos ao partir; valem só para a corrida atual

func _init() -> void:
	nucleo = Nucleo.criar()
	if nucleo != null:
		nucleo.definir_save(ProjectSettings.globalize_path(caminho))
		sincronizar(false)

## Copia o estado do core para os campos de leitura da UI.
func sincronizar(avisar := true) -> void:
	if nucleo == null:
		return
	var e: Dictionary = nucleo.meta_estado()
	fragmentos = int(e.get("fragments", 0))
	equipado = str(e.get("equipped", ""))
	materiais = {}
	for m in e.get("materials", []):
		materiais[str(m["id"])] = int(m["qty"])
	defs = {}
	ordem = []
	niveis = {}
	for u in e.get("upgrades", []):
		var id := str(u["id"])
		defs[id] = {"tipo": "habilidade" if u["kind"] == "ability" else "stat", "alvo": str(u["target"]), "stat": str(u["stat"]),
			"modo": str(u["mode"]), "valor": float(u["value"]), "custo": int(u["cost"]), "nivel_max": int(u["max_level"])}
		ordem.append(id)
		niveis[id] = int(u["level"])
	receitas = {}
	ordem_receitas = []
	amuletos = {}
	estoque = {}
	ativos = {}
	for r in e.get("recipes", []):
		var id := str(r["id"])
		var custo := {}
		for c in r["cost"]:
			custo[str(c["id"])] = int(c["qty"])
		var amuleto: bool = r["kind"] == "amulet"
		receitas[id] = {"tipo": "amuleto" if amuleto else "consumivel", "stat": str(r["stat"]), "modo": str(r["mode"]),
			"valor": float(r["value"]), "custo": custo, "fragmentos": int(r["fragments"]), "estoque_max": int(r["max_stock"])}
		ordem_receitas.append(id)
		if amuleto and r["owned"]:
			amuletos[id] = true
		if not amuleto:
			estoque[id] = int(r["stock"])
		if r["active"]:
			ativos[id] = true
	if avisar:
		mudou.emit()

func nivel(id: String) -> int:
	return int(niveis.get(id, 0))

## Habilidade de corrida liberada? Habilidades sem entrada em meta.csv nascem liberadas.
func liberada(upgrade_id: String) -> bool:
	return nucleo.habilidade_liberada(upgrade_id) != 0

func pode_comprar(id: String) -> bool:
	return nucleo.meta_pode_comprar(id) == 0

func comprar(id: String) -> bool:
	var ok: bool = nucleo.meta_comprar(id) == 0
	sincronizar(ok)
	return ok

func tem(id: String) -> bool:
	return nucleo.meta_pode_criar(id) == 5 or int(estoque.get(id, 0)) > 0   # 5 = amuleto já criado

func pode_criar(id: String) -> bool:
	return nucleo.meta_pode_criar(id) == 0

func criar(id: String) -> bool:
	var ok: bool = nucleo.meta_criar(id) == 0
	sincronizar(ok)
	return ok

## Equipa o amuleto (troca o do slot) ou desequipa se já era ele.
func equipar(id: String) -> bool:
	var ok: bool = nucleo.meta_equipar(id) == 0
	sincronizar(ok)
	return ok

## Ao partir: gasta uma unidade de cada consumível guardado para esta corrida.
func preparar_corrida() -> void:
	nucleo.meta_preparar_corrida()
	sincronizar()

## Nomes de stat do arqueiro que valem para outras classes (o guerreiro usa `damage` e `attack_cooldown`).
const ALIAS_STAT := {"damage": "arrow_damage", "attack_cooldown": "shoot_cooldown"}

## Soma os bônus permanentes aos stats base da corrida (o core usa os nomes do arqueiro; só traduzimos os nomes).
func aplicar(base: Dictionary) -> Dictionary:
	var entrada := {}
	for k in base:
		entrada[ALIAS_STAT[k] if ALIAS_STAT.has(k) and not base.has(ALIAS_STAT[k]) else k] = base[k]
	var saida: Dictionary = nucleo.aplicar_stats(entrada, false)
	var s := {}
	for k in base:
		var nome: String = ALIAS_STAT[k] if ALIAS_STAT.has(k) and not base.has(ALIAS_STAT[k]) else k
		s[k] = saida[nome]
	return s

## Ganho de um inimigo morto: {"fragments": n, "material": id, "material_qty": n} (vazio se não dropa).
func drop_de(inimigo: String) -> Dictionary:
	return nucleo.drop_de(inimigo)

## Passa os ganhos ({"fragmentos": n, "materiais": {id: n}}) para o saldo permanente; o core grava o save.
func creditar(ganhos: Dictionary) -> void:
	nucleo.meta_creditar(ganhos)
	sincronizar()

func salvar() -> bool:
	return nucleo.meta_salvar()

## Carrega o save. Arquivo ausente ou inválido deixa o estado zerado. Retorna true se leu um save válido.
func carregar() -> bool:
	var r: int = nucleo.meta_carregar()
	preload("res://scripts2d/habilidades_2d.gd").migrar_legado(nucleo, caminho)   # árvore de antes do core (uma vez)
	sincronizar()
	return r == 0
