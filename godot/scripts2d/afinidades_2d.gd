extends RefCounted
## Afinidades do ataque básico ("Ecos") por classe: tabela em data2d/afinidades_<classe>.csv, mesmas colunas para
## todas as classes (id, elemento, dano, vel, perfura, qtd, raio, duracao, valor, icone, nota) e ids únicos entre elas.
## Só leitura de dados; o que o Eco faz no golpe mora na classe (arqueiro: efeitos_arqueiro_afinidade_2d.gd).

const Csv = preload("res://scripts2d/csv2d.gd")

const CAMPOS_NUM := ["dano", "vel", "perfura", "qtd", "raio", "duracao", "valor"]

static var _defs := {}   # classe -> {id: linha}

## Linhas da classe por id (números já convertidos). Classe sem arquivo = vazio.
static func defs(classe: String) -> Dictionary:
	if not _defs.has(classe):
		var out := {}
		var caminho := "res://data2d/afinidades_%s.csv" % classe
		if FileAccess.file_exists(caminho):
			for r in Csv.rows(caminho):
				var d: Dictionary = r.duplicate()
				for c in CAMPOS_NUM:
					d[c] = float(r.get(c, "")) if str(r.get(c, "")) != "" else 0.0
				out[d["id"]] = d
		_defs[classe] = out
	return _defs[classe]

static func ids(classe: String) -> Array:
	return defs(classe).keys()

## Elemento do Eco `id`, procurado nas tabelas de todas as classes de classes_2d.csv ("" se não existe).
static func elemento(id: String) -> String:
	for r in Csv.rows("res://data2d/classes_2d.csv"):
		var d: Dictionary = defs(str(r["id"]))
		if d.has(id):
			return str(d[id].get("elemento", ""))
	return ""

## Classe dona do Eco `id` ("" se o id não é um Eco).
static func classe_de(id: String) -> String:
	for r in Csv.rows("res://data2d/classes_2d.csv"):
		if defs(str(r["id"])).has(id):
			return str(r["id"])
	return ""
