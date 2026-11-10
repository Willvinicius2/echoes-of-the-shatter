extends RefCounted
## Confere se um inimigo tem arte pronta no jogo, para nenhuma fase mostrar a caixa provisória (regra da direção de arte): stats
## em enemies.csv, as 5 animações no manifesto (idle, run, attack, hit e death), cada folha existe, tem as 5 direções e o PNG bate
## com o manifesto (largura = quadros x lado, altura = direções x lado). Usado pelos testes das fases e da Pedreira.

const Csv = preload("res://scripts2d/csv2d.gd")
const MANIFESTO := "res://data2d/sprites_manifest.csv"
const ANIMACOES: Array[String] = ["idle", "run", "attack", "hit", "death"]
const DIRECOES_MIN := 5

## "" quando o inimigo está pronto; senão, o motivo (entra na mensagem do teste).
static func motivo(id: String) -> String:
	if Csv.enemy(id).is_empty():
		return "sem stats em enemies.csv"
	var achadas: Array[String] = []
	for r in Csv.rows(MANIFESTO):
		if r["id"] != id:
			continue
		achadas.append(r["anim"])
		if not FileAccess.file_exists(r["arquivo"]):
			return "falta a folha %s" % r["anim"]
		if int(r["direcoes"]) < DIRECOES_MIN:
			return "a folha %s tem %s direções (o mínimo é %d)" % [r["anim"], r["direcoes"], DIRECOES_MIN]
		var img := Image.load_from_file(ProjectSettings.globalize_path(r["arquivo"]))
		if img == null or img.get_width() != int(r["quadro"]) * int(r["quadros"]) or img.get_height() != int(r["quadro"]) * int(r["direcoes"]):
			return "a folha %s não bate com o tamanho do manifesto" % r["anim"]
	for a in ANIMACOES:
		if not achadas.has(a):
			return "sem a animação %s no manifesto" % a
	return ""

static func pronto(id: String) -> bool:
	return motivo(id) == ""

## Todo inimigo que a fase pode pôr na tela: as ondas (`ondas.csv`, fase `onda_fase`), o chefe e o enxame (`ondas_fases.csv`) e os
## encontros do mapa (`@guarda x,y raio forca id:n|id:n` em `sala`). Cada id uma vez, na ordem em que aparece.
static func usados_na_fase(onda_fase: String, sala: String) -> Array[String]:
	var ids: Array[String] = []
	for r in Csv.rows("res://data2d/ondas.csv"):
		if r["fase"] == onda_fase:
			_somar(ids, String(r["inimigos"]))
	for r in Csv.rows("res://data2d/ondas_fases.csv"):
		if r["fase"] == onda_fase:
			_somar(ids, String(r["chefe"]))
			_somar(ids, String(r["enxame_inimigos"]))
	for linha in FileAccess.get_file_as_string(sala).split("\n", false):
		if linha.begins_with("@guarda "):
			var q := linha.strip_edges().split(" ", false)
			if q.size() >= 5:
				_somar(ids, q[4])
	return ids

## `id:peso|id:peso:custo` (ondas e enxame), `id:n|id:n` (encontros) ou um id só (chefe).
static func _somar(ids: Array[String], spec: String) -> void:
	for parte in spec.split("|", false):
		var id := parte.split(":")[0]
		if id != "" and not ids.has(id):
			ids.append(id)
