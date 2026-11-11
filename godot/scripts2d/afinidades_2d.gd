extends RefCounted
## Tabelas de afinidade do ataque básico ("Ecos") por classe: res://data2d/afinidades_<classe>.csv, todas com as colunas
## id,elemento,dano,vel,perfura,qtd,raio,duracao,valor,icone,nota. Aqui só a leitura (cartas, HUD e escolha da corrida);
## o que cada Eco faz no golpe fica no script da classe. Ids são únicos entre as classes.

const Csv = preload("res://scripts2d/csv2d.gd")
const CLASSES := "res://data2d/classes_2d.csv"
const NUMEROS := ["dano", "vel", "perfura", "qtd", "raio", "duracao", "valor"]

static var _cache := {}   # classe -> {id: linha com os números já convertidos}

## Linhas da tabela da classe por id (vazio quando a classe não tem tabela).
static func defs(classe: String) -> Dictionary:
	if not _cache.has(classe):
		var d := {}
		var arq := "res://data2d/afinidades_%s.csv" % classe
		if FileAccess.file_exists(arq):
			for r in Csv.rows(arq):
				var linha: Dictionary = r.duplicate()
				for k in NUMEROS:
					linha[k] = float(r.get(k, "0")) if str(r.get(k, "")) != "" else 0.0
				d[str(r["id"])] = linha
		_cache[classe] = d
	return _cache[classe]

static func ids(classe: String) -> Array:
	return defs(classe).keys()

## Classe dona do Eco `id` ("" se o id não é um Eco).
static func classe_de(id: String) -> String:
	for r in Csv.rows(CLASSES):
		if defs(str(r["id"])).has(id):
			return str(r["id"])
	return ""

## Elemento (raio, veneno, gelo, fogo) do Eco `id`, de qualquer classe; "" se o id não é um Eco.
static func elemento(id: String) -> String:
	return str(defs(classe_de(id)).get(id, {}).get("elemento", ""))
