extends RefCounted
## Aquecimento de recursos: pede ao carregador, em segundo plano, as texturas de efeitos, de personagens e os
## scripts de habilidade logo na abertura da corrida. Sem isso, o primeiro uso de cada habilidade ou inimigo
## chamava load() no meio da partida e travava o quadro (picos de dezenas de ms). Só pede; não bloqueia.

const PASTAS := ["res://art2d/fx", "res://art2d/sprites", "res://art2d/props", "res://art2d/ui"]
const SCRIPTS := ["res://scripts2d/efeitos_arqueiro_raio_2d.gd", "res://scripts2d/efeitos_arqueiro_veneno_2d.gd",
	"res://scripts2d/efeitos_arqueiro_gelo_2d.gd", "res://scripts2d/efeitos_arqueiro_fogo_2d.gd",
	"res://scripts2d/efeito_2d.gd", "res://scripts2d/fogo_util_2d.gd", "res://scripts2d/vfx_identidade_2d.gd"]

static var _pedido := false

static func iniciar() -> int:
	if _pedido or DisplayServer.get_name() == "headless":
		return 0   # uma vez por processo; testes sem tela não precisam
	_pedido = true
	var n := 0
	for pasta in PASTAS:
		n += _pedir_pasta(pasta)
	for s in SCRIPTS:
		if ResourceLoader.exists(s):
			ResourceLoader.load_threaded_request(s)
			n += 1
	return n

static func _pedir_pasta(pasta: String) -> int:
	var n := 0
	for f in DirAccess.get_files_at(pasta):
		var nome := f.trim_suffix(".import").trim_suffix(".remap")
		if nome.get_extension() in ["png", "webp", "jpg"]:
			var caminho := pasta + "/" + nome
			if ResourceLoader.exists(caminho):
				ResourceLoader.load_threaded_request(caminho)
				n += 1
	for d in DirAccess.get_directories_at(pasta):
		n += _pedir_pasta(pasta + "/" + d)
	return n
