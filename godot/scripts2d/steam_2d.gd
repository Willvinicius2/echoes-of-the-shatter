extends RefCounted
## Integração com a Steam atrás de uma interface. O jogo nunca depende dela: sem o plugin GodotSteam, sem o
## cliente da Steam aberto ou com a inicialização falhando, `disponivel` fica falso e tudo vira no-op.
## Conquistas desbloqueadas ficam registradas em disco e são reenviadas quando a Steam estiver ativa.
## Nuvem de saves: Steam Auto-Cloud configurado no Steamworks (ver docs/steam/integracao_godotsteam.md);
## o código só consulta se a nuvem está ligada. Eventos e IDs das conquistas ficam em data2d/conquistas.csv.

const Csv = preload("res://scripts2d/csv2d.gd")

static var caminho := "user://steam_2d.json"   # os testes apontam para outro arquivo

signal conquista_desbloqueada(id: String)

var disponivel := false
var conquistas: Array = []        # linhas de conquistas.csv
var desbloqueadas := {}           # id -> true (registro local, vale com ou sem Steam)
var _api: Object = null           # singleton "Steam" do GodotSteam; nulo sem o plugin

func _init() -> void:
	conquistas = Csv.rows("res://data2d/conquistas.csv")
	_ler()

## Tenta ligar a Steam. Seguro sem plugin: devolve falso e o jogo segue normalmente.
func iniciar() -> bool:
	disponivel = false
	_api = null
	if not Engine.has_singleton("Steam"):
		return false
	var api := Engine.get_singleton("Steam")
	if api == null or not api.has_method("steamInitEx"):
		return false
	var r = api.call("steamInitEx")
	# GodotSteam 4.x devolve {"status": 0, ...} quando conectou (0 = OK); versões antigas devolvem bool/dicionário.
	var ok: bool = (r is Dictionary and int(r.get("status", 1)) == 0) or (r is bool and r)
	if not ok:
		return false
	_api = api
	disponivel = true
	_reenviar_pendentes()
	return true

## Chamar a cada quadro enquanto a Steam estiver ativa (callbacks do plugin).
func tick() -> void:
	if disponivel and _api != null and _api.has_method("run_callbacks"):
		_api.call("run_callbacks")

## Um acontecimento do jogo (`corrida_fim`, `vitoria`, ...): desbloqueia as conquistas ligadas a ele.
func evento(nome: String) -> Array:
	var novas := []
	for c in conquistas:
		if c["evento"] == nome and not desbloqueadas.has(c["id"]):
			desbloqueadas[c["id"]] = true
			novas.append(c["id"])
			_enviar(c)
			conquista_desbloqueada.emit(c["id"])
	if not novas.is_empty():
		_gravar()
	return novas

func _enviar(c: Dictionary) -> void:
	if not disponivel or _api == null or not _api.has_method("setAchievement"):
		return
	_api.call("setAchievement", c["steam_id"])
	if _api.has_method("storeStats"):
		_api.call("storeStats")

func _reenviar_pendentes() -> void:
	for c in conquistas:
		if desbloqueadas.has(c["id"]):
			_enviar(c)

## A nuvem (Auto-Cloud) só vale com o cliente Steam e a opção ligada pelo jogador na Steam.
func nuvem_ativa() -> bool:
	if not disponivel or _api == null:
		return false
	for m in ["isCloudEnabledForAccount", "isCloudEnabledForApp"]:
		if not _api.has_method(m) or not _api.call(m):
			return false
	return true

func _ler() -> void:
	desbloqueadas = {}
	if FileAccess.file_exists(caminho):
		var d = JSON.parse_string(FileAccess.get_file_as_string(caminho))
		if d is Dictionary and d.get("conquistas") is Array:
			for id in d["conquistas"]:
				desbloqueadas[str(id)] = true

func _gravar() -> void:
	var f := FileAccess.open(caminho, FileAccess.WRITE)
	if f != null:
		f.store_string(JSON.stringify({"versao": 1, "conquistas": desbloqueadas.keys()}))
