extends RefCounted
## Áudio do cliente 2D: efeitos e música por evento. Tabela em data2d/audio.csv (evento, arquivo, volume, variação de pitch).
## Os WAV são lidos direto do disco (sem importação do editor), então funcionam no teste headless.

const Csv = preload("res://scripts2d/csv2d.gd")

const VOZES := 12   # efeitos simultâneos

static var _tabela := {}
static var _fluxos := {}
static var _rng := RandomNumberGenerator.new()   # fora do rng da corrida: o áudio não muda o resultado
static var _prox := 0
static var silencio := false   # testes e depuração

static func tabela() -> Dictionary:
	if _tabela.is_empty():
		for r in Csv.rows("res://data2d/audio.csv"):
			_tabela[r["evento"]] = r
	return _tabela

## Carrega o WAV (16 bits, mono ou estéreo) como AudioStreamWAV. Música entra em laço.
static func fluxo(evento: String) -> AudioStreamWAV:
	if _fluxos.has(evento):
		return _fluxos[evento]
	var linha: Dictionary = tabela().get(evento, {})
	var s: AudioStreamWAV = null
	if not linha.is_empty():
		s = _ler_wav(linha["arquivo"])
		if s != null and linha["tipo"] == "musica":
			s.loop_mode = AudioStreamWAV.LOOP_FORWARD
			s.loop_end = s.data.size() / (2 * (2 if s.stereo else 1))
	_fluxos[evento] = s
	return s

static func _ler_wav(caminho: String) -> AudioStreamWAV:
	var b := FileAccess.get_file_as_bytes(caminho)
	if b.size() < 44 or b.slice(0, 4).get_string_from_ascii() != "RIFF":
		push_error("WAV invalido ou ausente: " + caminho)
		return null
	var canais := 1
	var taxa := 22050
	var i := 12
	while i + 8 <= b.size():
		var id := b.slice(i, i + 4).get_string_from_ascii()
		var tam := b.decode_u32(i + 4)
		if id == "fmt ":
			canais = b.decode_u16(i + 10)
			taxa = b.decode_u32(i + 12)
		elif id == "data":
			var s := AudioStreamWAV.new()
			s.format = AudioStreamWAV.FORMAT_16_BITS
			s.mix_rate = taxa
			s.stereo = canais == 2
			s.data = b.slice(i + 8, i + 8 + tam)
			return s
		i += 8 + tam + (tam & 1)
	return null

static func _raiz() -> Node:
	var tree := Engine.get_main_loop() as SceneTree
	return tree.root if tree != null else null

static func _voz(nome: String) -> AudioStreamPlayer:
	var raiz := _raiz()
	if raiz == null:
		return null
	var p := raiz.get_node_or_null(nome) as AudioStreamPlayer
	if p == null:
		p = AudioStreamPlayer.new()
		p.name = nome
		p.process_mode = Node.PROCESS_MODE_ALWAYS   # toca com o jogo pausado (menus)
		raiz.add_child.call_deferred(p)   # a raiz pode estar ocupada montando filhos
	return p

static func _play(p: AudioStreamPlayer) -> void:
	if p.is_inside_tree():
		p.play()
	else:
		p.ready.connect(p.play, CONNECT_ONE_SHOT)

## Toca o efeito do evento. Evento desconhecido ou áudio ausente não faz nada.
static func tocar(evento: String) -> void:
	if silencio:
		return
	var s := fluxo(evento)
	if s == null:
		return
	var p := _voz("Sfx%d" % _prox)
	if p == null:
		return
	_prox = (_prox + 1) % VOZES
	var linha: Dictionary = tabela()[evento]
	var v := float(linha["variacao_pitch"])
	p.stream = s
	p.volume_db = float(linha["volume_db"])
	p.pitch_scale = 1.0 + _rng.randf_range(-v, v)
	_play(p)

## Começa a música do evento (laço). Se já toca a mesma, não reinicia.
static func musica(evento: String) -> void:
	if silencio:
		return
	var s := fluxo(evento)
	var p := _voz("Musica")
	if s == null or p == null:
		return
	if p.playing and p.stream == s:
		return
	p.stream = s
	p.volume_db = float(tabela()[evento]["volume_db"])
	_play(p)

static func parar_musica() -> void:
	var raiz := _raiz()
	var p := raiz.get_node_or_null("Musica") as AudioStreamPlayer if raiz != null else null
	if p != null:
		p.stop()
