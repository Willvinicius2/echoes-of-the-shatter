extends RefCounted
## Opções do jogador: volume (geral, música, efeitos), vídeo (tela cheia, vsync) e teclas remapeáveis.
## Padrões em data2d/opcoes.csv; ações remapeáveis em data2d/teclas.csv. Save em JSON, separado do save da meta.
## Sem Steam e sem arquivo de opções o jogo usa os padrões.

const Csv = preload("res://scripts2d/csv2d.gd")

const VERSAO := 1
const BUS_MUSICA := "Musica"
const BUS_EFEITOS := "Efeitos"

static var caminho := "user://opcoes_2d.json"   # os testes apontam para outro arquivo

signal mudou

var padroes := {}
var vol := {"master": 1.0, "musica": 0.8, "efeitos": 1.0}
var tela_cheia := false
var vsync := true
var tutorial_visto := false
var acoes: Array = []        # ações remapeáveis, na ordem de teclas.csv
var teclas := {}             # ação -> physical_keycode escolhido pelo jogador
static var _padrao_teclas := {}   # ação -> physical_keycode que veio do InputMap (lido uma vez, antes de qualquer remapeamento)

func _init() -> void:
	padroes = Csv.kv("res://data2d/opcoes.csv")
	for r in Csv.rows("res://data2d/teclas.csv"):
		acoes.append(r["acao"])
	for a in acoes:
		if not _padrao_teclas.has(a):
			_padrao_teclas[a] = _tecla_atual(a)
	restaurar_padroes()
	garantir_barramentos()

func restaurar_padroes() -> void:
	vol = {"master": padroes["vol_master"], "musica": padroes["vol_musica"], "efeitos": padroes["vol_efeitos"]}
	tela_cheia = padroes["tela_cheia"] > 0.5
	vsync = padroes["vsync"] > 0.5
	tutorial_visto = padroes["tutorial_visto"] > 0.5
	restaurar_teclas()

## Cria os barramentos de música e efeitos (idempotente). O áudio dos players usa estes nomes.
static func garantir_barramentos() -> void:
	for nome in [BUS_MUSICA, BUS_EFEITOS]:
		if AudioServer.get_bus_index(nome) < 0:
			AudioServer.add_bus()
			var i := AudioServer.get_bus_count() - 1
			AudioServer.set_bus_name(i, nome)
			AudioServer.set_bus_send(i, "Master")

static func nome_barramento(tipo: String) -> String:
	return "Master" if tipo == "master" else (BUS_MUSICA if tipo == "musica" else BUS_EFEITOS)

# --- volume ---

func set_volume(tipo: String, v: float) -> void:
	vol[tipo] = clampf(snappedf(v, 0.01), 0.0, 1.0)
	_aplicar_volume(tipo)
	mudou.emit()

## Avança um passo (volta a 0 depois de 100%): botão único por volume, serve para teclado e controle.
func ciclar_volume(tipo: String) -> void:
	var passo: float = padroes["passo_volume"]
	var novo: float = vol[tipo] + passo
	set_volume(tipo, 0.0 if novo > 1.0 + 0.001 else novo)

func _aplicar_volume(tipo: String) -> void:
	var i := AudioServer.get_bus_index(nome_barramento(tipo))
	if i >= 0:
		AudioServer.set_bus_volume_db(i, linear_to_db(vol[tipo]) if vol[tipo] > 0.0 else -80.0)
		AudioServer.set_bus_mute(i, vol[tipo] <= 0.0)

# --- vídeo ---

func set_tela_cheia(v: bool) -> void:
	tela_cheia = v
	_aplicar_video()
	mudou.emit()

func set_vsync(v: bool) -> void:
	vsync = v
	_aplicar_video()
	mudou.emit()

func _aplicar_video() -> void:
	if DisplayServer.get_name() == "headless":
		return
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN if tela_cheia else DisplayServer.WINDOW_MODE_WINDOWED)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED if vsync else DisplayServer.VSYNC_DISABLED)

# --- teclas ---

func _tecla_atual(acao: String) -> int:
	for ev in InputMap.action_get_events(acao):
		if ev is InputEventKey:
			return ev.physical_keycode
	return KEY_NONE

func tecla(acao: String) -> int:
	return int(teclas.get(acao, _padrao_teclas.get(acao, KEY_NONE)))

func nome_tecla(acao: String) -> String:
	var code := tecla(acao)
	if DisplayServer.get_name() != "headless":   # o servidor headless não converte o código físico
		code = DisplayServer.keyboard_get_keycode_from_physical(code)
	return OS.get_keycode_string(code)

func eh_padrao(acao: String) -> bool:
	return tecla(acao) == int(_padrao_teclas.get(acao, KEY_NONE))

## Remapeia a ação para a tecla. Esc é reservado (pausa). Se outra ação já usa a tecla, as duas trocam.
func remapear(acao: String, keycode: int) -> bool:
	if not acoes.has(acao) or keycode == KEY_ESCAPE or keycode == KEY_NONE:
		return false
	var antiga := tecla(acao)
	for outra in acoes:
		if outra != acao and tecla(outra) == keycode:
			teclas[outra] = antiga
			_aplicar_tecla(outra)
	teclas[acao] = keycode
	_aplicar_tecla(acao)
	mudou.emit()
	return true

func restaurar_teclas() -> void:
	teclas = _padrao_teclas.duplicate()
	for a in acoes:
		_aplicar_tecla(a)

## Troca só o evento de teclado da ação; mouse e controle ficam como estão.
func _aplicar_tecla(acao: String) -> void:
	for ev in InputMap.action_get_events(acao):
		if ev is InputEventKey:
			InputMap.action_erase_event(acao, ev)
	if tecla(acao) != KEY_NONE:
		var novo := InputEventKey.new()
		novo.physical_keycode = tecla(acao) as Key
		InputMap.action_add_event(acao, novo)

# --- save ---

func aplicar() -> void:
	garantir_barramentos()
	for t in vol:
		_aplicar_volume(t)
	_aplicar_video()
	for a in acoes:
		_aplicar_tecla(a)

func salvar() -> bool:
	var f := FileAccess.open(caminho, FileAccess.WRITE)
	if f == null:
		return false
	f.store_string(JSON.stringify({"versao": VERSAO, "vol": vol, "tela_cheia": tela_cheia, "vsync": vsync,
		"tutorial_visto": tutorial_visto, "teclas": teclas}, "\t"))
	return true

## Lê o arquivo (se houver) e aplica. Arquivo ausente ou corrompido deixa os padrões.
func carregar() -> bool:
	restaurar_padroes()
	var ok := false
	if FileAccess.file_exists(caminho):
		var d = JSON.parse_string(FileAccess.get_file_as_string(caminho))
		if d is Dictionary and int(d.get("versao", 0)) == VERSAO:
			for t in vol:
				vol[t] = clampf(float(d.get("vol", {}).get(t, vol[t])), 0.0, 1.0)
			tela_cheia = bool(d.get("tela_cheia", tela_cheia))
			vsync = bool(d.get("vsync", vsync))
			tutorial_visto = bool(d.get("tutorial_visto", false))
			var salvas = d.get("teclas", {})
			if salvas is Dictionary:
				for a in acoes:
					if salvas.has(a) and int(salvas[a]) != KEY_ESCAPE and int(salvas[a]) != KEY_NONE:
						teclas[a] = int(salvas[a])
			ok = true
	aplicar()
	return ok
