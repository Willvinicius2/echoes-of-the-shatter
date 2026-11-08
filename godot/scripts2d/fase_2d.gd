extends RefCounted
## Fase escolhida para a próxima corrida (data2d/fases_2d.csv: sala, fase do spawner, nome e descrição por chave de loc,
## fase que precisa ser vencida antes). O título alterna; o run usa a sala e a `onda_fase` da fase atual.
## As fases vencidas vêm do save (meta_2d.gd grava; aqui fica só a cópia que a UI e o run leem).
## Os testes apontam `tabela` para data2d/testes/fases_teste.csv.

const Csv = preload("res://scripts2d/csv2d.gd")

static var tabela := "res://data2d/fases_2d.csv"
static var atual := ""
static var vencidas: Array = []          # ids das fases já vencidas (cópia do save)
static var todas_abertas := false        # atalho de dev (console `fases_abertas`, run_settings `dev_fases_abertas`): não grava
static var _linhas: Array = []
static var _lidas_de := ""

## `-- --fase=<id>` escolhe a fase (bot e capturas); `-- --fases-abertas` liga o atalho de dev.
static func ler_argumentos() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--fase=") and not dados(a.trim_prefix("--fase=")).is_empty():
			atual = a.trim_prefix("--fase=")
		elif a == "--fases-abertas":
			todas_abertas = true

static func lista() -> Array:
	if _lidas_de != tabela:
		_lidas_de = tabela
		_linhas = Csv.rows(tabela) if FileAccess.file_exists(tabela) else []
	return _linhas

static func ids() -> Array:
	return lista().map(func(r): return str(r["id"]))

static func dados(id: String) -> Dictionary:
	for r in lista():
		if r["id"] == id:
			return r
	return {}

static func sala(id: String) -> String:
	return str(dados(id).get("sala", ""))

static func onda_fase(id: String) -> String:
	return str(dados(id).get("onda_fase", ""))

static func requer(id: String) -> String:
	return str(dados(id).get("requer", ""))

## Aberta: sem requisito, com a fase exigida vencida, ou com o atalho de dev ligado.
static func desbloqueada(id: String) -> bool:
	if dados(id).is_empty():
		return false
	var r := requer(id)
	return todas_abertas or r == "" or vencidas.has(r)

## O mapa da fase existe (a Pedreira ainda não tem mapa: aparece como "em breve").
static func disponivel(id: String) -> bool:
	var s := sala(id)
	return s != "" and FileAccess.file_exists(s)

static func pode_jogar(id: String) -> bool:
	return desbloqueada(id) and disponivel(id)

## Fase que vale para a corrida: a atual, se dá para jogar; senão a primeira jogável da tabela ("" se nenhuma).
static func jogavel() -> String:
	if pode_jogar(atual):
		return atual
	for id in ids():
		if pode_jogar(id):
			return id
	return ""

## Garante uma fase válida em `atual` (a do save, se existir na tabela; senão a primeira).
static func definir(id: String) -> void:
	var l := ids()
	atual = id if l.has(id) else (l[0] if not l.is_empty() else "")

static func alternar(passo := 1) -> void:
	var l := ids()
	if l.is_empty():
		atual = ""
		return
	var i := l.find(atual)
	atual = l[posmod((i if i >= 0 else 0) + passo, l.size())]

## Fases que passam a abrir quando `id` é vencida agora (antes não estavam abertas). Não muda nada.
static func abertas_por(id: String) -> Array:
	var out := []
	if vencidas.has(id):
		return out
	for r in lista():
		if str(r["requer"]) == id:
			out.append(str(r["id"]))
	return out
