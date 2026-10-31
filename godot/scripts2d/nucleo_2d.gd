extends RefCounted
## Liga o cliente 2D ao ShatterCore: instancia o `ShatterRogue` da GDExtension (godot/gdextension) com os CSV de data2d.
## As regras de meta, Forja, cartas e fluxo da corrida moram no core; os scripts do cliente só chamam e apresentam.

const ARQUIVOS := ["meta", "receitas", "drops", "rota", "run", "run_settings", "upgrades"]
const PASTA := "user://dados_core"

## Cria um núcleo novo, ou null (com erro no log) se a extensão não foi compilada ou os dados não carregam.
## O core lê os CSV de uma pasta real; no jogo exportado res:// fica dentro do .pck, então os arquivos são copiados.
static func criar() -> Object:
	if not ClassDB.class_exists("ShatterRogue"):
		push_error("GDExtension ShatterRogue ausente: compile godot/gdextension (ver COMO_RODAR_2D.md)")
		return null
	DirAccess.make_dir_recursive_absolute(PASTA)
	for a in ARQUIVOS:
		var origem := "res://data2d/%s.csv" % a
		var destino := "%s/%s.csv" % [PASTA, a]
		var bytes := FileAccess.get_file_as_bytes(origem)
		var f := FileAccess.open(destino, FileAccess.WRITE)
		if bytes.is_empty() or f == null:
			push_error("Não foi possível preparar %s para o ShatterCore" % a)
			return null
		f.store_buffer(bytes)
		f.close()
	var n: Object = ClassDB.instantiate("ShatterRogue")
	var erro: String = n.carregar_dados(ProjectSettings.globalize_path(PASTA))
	if erro != "":
		push_error(erro)
		return null
	return n
