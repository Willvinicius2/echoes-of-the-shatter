extends RefCounted
## Liga o cliente 2D ao ShatterCore: instancia o `ShatterRogue` da GDExtension (godot/gdextension) com os CSV de data2d.
## As regras de meta, Forja, cartas, fluxo da corrida, árvore de habilidades e ondas de horda moram no core; os scripts
## do cliente só chamam e apresentam.
##
## Hordas (API 1.11, docs/tecnico/09 seção 18): `ondas_iniciar(fase, semente)`, depois a cada quadro
## `ondas_tick(delta)` devolve os que nasceram agora ([{id, enemy, elite, boss, wave, angle, radius, hp_mult,
## damage_mult}]; nascem em `jogador + Vector2.from_angle(angle) * radius`, presos nas bordas do mapa) e
## `ondas_morto(id)` avisa cada morte ({resultado, completa}). `ondas_acordar_chefe()` acorda o Guardião no altar (a
## partir da onda despertar_onda; no prazo ele acorda sozinho, junto do enxame final). `ondas_estado()` alimenta a HUD
## (onda, enxame, tempo que falta, vivos, teto, chefe).

const ARQUIVOS := ["meta", "receitas", "drops", "rota", "run", "run_settings", "upgrades"]
## Tabelas que o core lê se existirem (ondas e ondas_fases: spawner de hordas).
const OPCIONAIS := ["ondas", "ondas_fases", "curva_horda"]
const CLASSES := "res://data2d/classes_2d.csv"
const PASTA := "user://dados_core"

## Cria um núcleo novo, ou null (com erro no log) se a extensão não foi compilada ou os dados não carregam.
## O core lê os CSV de uma pasta real; no jogo exportado res:// fica dentro do .pck, então os arquivos são copiados.
## `classes_extras` ({id: caminho do CSV da árvore}) acrescenta classes só a este núcleo (fixtures dos testes).
static func criar(classes_extras := {}) -> Object:
	if not ClassDB.class_exists("ShatterRogue"):
		push_error("GDExtension ShatterRogue ausente: compile godot/gdextension (ver COMO_RODAR_2D.md)")
		return null
	DirAccess.make_dir_recursive_absolute(PASTA)
	for a in ARQUIVOS:
		if not _copiar("res://data2d/%s.csv" % a, "%s/%s.csv" % [PASTA, a]):
			return null
	for a in OPCIONAIS:
		var origem := "res://data2d/%s.csv" % a
		var destino := "%s/%s.csv" % [PASTA, a]
		if FileAccess.file_exists(origem):
			if not _copiar(origem, destino):
				return null
		elif FileAccess.file_exists(destino):
			DirAccess.remove_absolute(destino)
	if not _copiar_classes(classes_extras):
		return null
	var n: Object = ClassDB.instantiate("ShatterRogue")
	var erro: String = n.carregar_dados(ProjectSettings.globalize_path(PASTA))
	if erro != "":
		push_error(erro)
		return null
	return n

static func _copiar(origem: String, destino: String) -> bool:
	var bytes := FileAccess.get_file_as_bytes(origem)
	var f := FileAccess.open(destino, FileAccess.WRITE)
	if bytes.is_empty() or f == null:
		push_error("Não foi possível preparar %s para o ShatterCore" % origem)
		return false
	f.store_buffer(bytes)
	f.close()
	return true

## classes_2d.csv e a árvore de cada classe (o core lê pelo nome do arquivo na coluna `habilidades`).
static func _copiar_classes(extras: Dictionary) -> bool:
	var texto := FileAccess.get_file_as_string(CLASSES)
	if texto == "":
		push_error("Não foi possível ler " + CLASSES)
		return false
	var linhas := texto.strip_edges(false, true).split("\n")
	var colunas := linhas[0].strip_edges().split(",")
	var col_hab := colunas.find("habilidades")
	var arvores := []
	for i in range(1, linhas.size()):
		var c := linhas[i].strip_edges().split(",")
		if col_hab >= 0 and c.size() > col_hab and c[col_hab] != "":
			arvores.append(c[col_hab])
	for id in extras:
		var cel := []
		for nome in colunas:
			cel.append(id if nome == "id" else (str(extras[id]) if nome == "habilidades" else ""))
		texto = texto.strip_edges(false, true) + "\n" + ",".join(cel) + "\n"
		arvores.append(str(extras[id]))
	var f := FileAccess.open(PASTA + "/classes_2d.csv", FileAccess.WRITE)
	if f == null:
		push_error("Não foi possível preparar classes_2d.csv para o ShatterCore")
		return false
	f.store_string(texto)
	f.close()
	for caminho in arvores:
		if FileAccess.file_exists(caminho) and not _copiar(caminho, PASTA + "/" + str(caminho).get_file()):
			return false
	return true
