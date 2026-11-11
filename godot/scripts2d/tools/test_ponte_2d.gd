extends RefCounted
## Testes da Ponte do Sino (área 3, data2d/rooms/fase_3.txt, gerada por tools/mapas/gerar_fase_3.py), chamados por test_2d.gd:
## o tema, as medidas pedidas pela direção visual (vãos com 8 células jogáveis ou mais, praças de sino de 16x12 ou mais, abismo só
## de cenário), o caminho do P ao G e ao X, os sinos, as folhas por código da Tecelã de Cascalho e do Filhote e as ondas da fase
## (sem o Arauto de Pedra e só com inimigos que têm arte). Ver docs/arte/37_ponte_do_sino.md.

const Csv = preload("res://scripts2d/csv2d.gd")
const RoomScript = preload("res://scripts2d/room_2d.gd")
const ArteInimigos = preload("res://scripts2d/tools/arte_inimigos_2d.gd")
const TestePedreira = preload("res://scripts2d/tools/test_pedreira_2d.gd")
const SALA := "res://data2d/rooms/fase_3.txt"
const BLOQUEIA := "mf#"   # massa, abismo e parede: o resto da grade é chão
## Praças de sino e arena, em células (x0, y0, largura, altura), como em gerar_fase_3.py.
const PRACAS := {"praça dos vigias": Rect2i(44, 15, 18, 15), "praça do sino caído": Rect2i(86, 14, 20, 14), "arena do Sino Maior": Rect2i(153, 12, 21, 24)}

var t: SceneTree
var check: Callable

func _init(arvore: SceneTree, verifica: Callable) -> void:
	t = arvore
	check = verifica

func rodar() -> void:
	var sala = RoomScript.new()
	if not sala.carregar(SALA):
		check.call(false, "carrega a Ponte do Sino (%s)" % SALA)
		sala.free()
		return
	_testar_mapa(sala)
	sala.free()
	_testar_grade()
	_testar_arte()
	_testar_ondas()
	_testar_tecela()

func _testar_mapa(sala) -> void:
	check.call(sala.tema == "ponte" and sala.piso_grama, "Ponte: `@piso ponte` liga o tema e o piso aberto")
	check.call(sala.aberta() and sala.colunas == 180 and sala.linhas == 50, "Ponte: fase aberta de %dx%d" % [sala.colunas, sala.linhas])
	check.call(sala.spawn_jogador != Vector2.ZERO and sala.posicao_chefe != Vector2.ZERO and sala.posicao_portal != Vector2.ZERO, "Ponte: P, G (a Tecelã) e X marcados")
	check.call(sala.bolsoes.size() == 1 and sala.guardas.size() >= 6, "Ponte: um bolsão com baú e os encontros adormecidos (%d)" % sala.guardas.size())
	var ok_props := true
	var n := {}
	for pr in sala.props:
		ok_props = ok_props and sala._props_def.has(pr["id"]) and sala._props_arte.has(pr["id"])
		ok_props = ok_props and FileAccess.file_exists(sala._props_arte[pr["id"]]["arquivo"])
		n[pr["id"]] = int(n.get(pr["id"], 0)) + 1
	check.call(ok_props, "Ponte: todo prop tem arte e definição (%d props)" % sala.props.size())
	check.call(n.get("ponte_sino", 0) == 1 and n.get("ponte_sino_caido", 0) == 1 and n.get("ponte_sino_maior", 0) == 1, "Ponte: um sino em cada praça e o Sino Maior na arena")
	check.call(int(n.get("ponte_teia_0", 0)) + int(n.get("ponte_teia_1", 0)) >= 12 and int(n.get("ponte_casulo", 0)) >= 8, "Ponte: teias e casulos avisam da Tecelã pelo caminho")
	var arquivos_ok := true
	for d in sala.decalques:
		arquivos_ok = arquivos_ok and FileAccess.file_exists(String(d["arquivo"]))
	check.call(sala.decalques.size() >= 20 and arquivos_ok, "Ponte: as bordas da ponte (parapeito, face e arcos) existem (%d)" % sala.decalques.size())
	var em_guarda := ""
	for g in sala.guardas:
		em_guarda += str(g)
	check.call(not em_guarda.contains("stone_herald"), "Ponte: nenhum encontro usa o Arauto de Pedra")

## A grade de texto do mapa: largura jogável, praças e caminho. O abismo (`f`) bloqueia quem anda e não mata ninguém: não existe
## queda no jogo, e a flecha passa por cima dele (camada 8, como o fosso da Pedreira).
func _testar_grade() -> void:
	var grade: Array[String] = []
	var arq := FileAccess.open(SALA, FileAccess.READ)
	while not arq.eof_reached():
		var l := arq.get_line()
		if l.begins_with("@") or l.is_empty():
			break
		grade.append(l)
	var p := Vector2i(-1, -1)
	var g := Vector2i(-1, -1)
	var x_saida := Vector2i(-1, -1)
	for y in grade.size():
		for x in grade[y].length():
			match grade[y][x]:
				"P": p = Vector2i(x, y)
				"G": g = Vector2i(x, y)
				"X": x_saida = Vector2i(x, y)
	# inundação de 4 vizinhos a partir do P
	var visto := {p: true}
	var fila: Array[Vector2i] = [p]
	while not fila.is_empty():
		var c: Vector2i = fila.pop_back()
		for d in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
			var v: Vector2i = c + d
			if v.y < 0 or v.y >= grade.size() or v.x < 0 or v.x >= grade[v.y].length() or visto.has(v) or BLOQUEIA.contains(grade[v.y][v.x]):
				continue
			visto[v] = true
			fila.append(v)
	check.call(visto.has(g) and visto.has(x_saida), "Ponte: do P se chega à Tecelã e ao portal")
	var estreito := 999
	var onde := -1
	for x in range(p.x, g.x + 1):
		var maior := 0
		var seguidos := 0
		for y in grade.size():
			seguidos = seguidos + 1 if visto.has(Vector2i(x, y)) else 0
			maior = maxi(maior, seguidos)
		if maior < estreito:
			estreito = maior
			onde = x
	check.call(estreito >= 8, "Ponte: o trecho mais estreito tem 8 células jogáveis ou mais (%d na coluna %d)" % [estreito, onde])
	for nome in PRACAS:
		var r: Rect2i = PRACAS[nome]
		var livres := 0
		for y in range(r.position.y, r.end.y):
			for x in range(r.position.x, r.end.x):
				if visto.has(Vector2i(x, y)):
					livres += 1
		check.call(r.size.x >= 16 and r.size.y >= 12 and livres == r.size.x * r.size.y, "Ponte: %s tem %dx%d células livres (16x12 ou mais)" % [nome, r.size.x, r.size.y])
	var abismo := 0
	for l in grade:
		abismo += l.count("f")
	check.call(abismo > 1000, "Ponte: o abismo cerca a ponte (%d células de `f`, só cenário e barreira)" % abismo)

## Tecelã de Cascalho e Filhote, feitos por código (tools/sprites2d/tecela_de_cascalho): mesma conferência das folhas da Pedreira.
func _testar_arte() -> void:
	var folhas = TestePedreira.new(t, check)
	folhas._conferir_folhas_por_codigo({"id": "bell_weaver", "nome": "tecelã de cascalho", "lado": 256, "pivo": Vector2i(128, 164), "cores": 24,
		"contato": 5, "pe": Vector2i(25, 70), "centro": 20})
	folhas._conferir_folhas_por_codigo({"id": "gravel_spiderling", "nome": "filhote de cascalho", "lado": 96, "pivo": Vector2i(48, 58), "cores": 24,
		"contato": 5, "pe": Vector2i(8, 22), "centro": 6})
	var manifesto := {}
	for r in Csv.rows("res://data2d/props_manifest.csv"):
		manifesto[r["id"]] = r
	for id in ["ponte_sino", "ponte_sino_caido", "ponte_sino_maior", "ponte_casulo", "ponte_teia_0", "ponte_teia_1", "ponte_entulho"]:
		var m: Dictionary = manifesto.get(id, {})
		check.call(not m.is_empty(), "%s: tem linha no manifesto" % id)
		if m.is_empty():
			continue
		var img := Image.load_from_file(ProjectSettings.globalize_path(m["arquivo"]))
		check.call(img != null and img.get_width() == int(m["largura"]) and img.get_height() == int(m["altura"]), "%s: PNG com o tamanho do manifesto (%sx%s)" % [id, m["largura"], m["altura"]])

func _testar_ondas() -> void:
	var usados := {}
	var n_ondas := 0
	for r in Csv.rows("res://data2d/ondas.csv"):
		if r["fase"] != "ponte":
			continue
		n_ondas += 1
		for parte in String(r["inimigos"]).split("|", false):
			usados[parte.split(":")[0]] = true
	var chefe := ""
	for r in Csv.rows("res://data2d/ondas_fases.csv"):
		if r["fase"] != "ponte":
			continue
		chefe = String(r["chefe"])
		for parte in String(r["enxame_inimigos"]).split("|", false):
			usados[parte.split(":")[0]] = true
	check.call(n_ondas == 7 and chefe == "bell_weaver", "ondas da Ponte: 7 ondas e a Tecelã de Cascalho como chefe (%d, %s)" % [n_ondas, chefe])
	check.call(usados.has("gravel_spiderling") and usados.has("ghost_archer") and usados.has("crypt_bat") and usados.has("wandering_ghost") and usados.has("hollow_sentinel"), "ondas da Ponte: filhotes, atiradores, morcegos, fantasmas e a sentinela de elite")
	check.call(not usados.has("stone_herald") and not usados.has("bell_weaver"), "ondas da Ponte: sem o Arauto de Pedra, e a Tecelã só aparece como chefe")
	usados[chefe] = true
	var sem_arte: Array = []
	for id in usados:
		if not ArteInimigos.pronto(id):
			sem_arte.append(id)
	check.call(sem_arte.is_empty(), "ondas da Ponte: só inimigos com arte e stats %s" % str(sem_arte))

## Alvo mínimo da Tecelã: conta dano e lentidão recebidos.
class AlvoFalso extends Node2D:
	var dano := 0.0
	var lentidao := 0.0
	func take_damage(n: float, _origem := Vector2.ZERO) -> void:
		dano += n
	func aplicar_lentidao(frac: float, _dur: float) -> void:
		lentidao = maxf(lentidao, frac)
	func esta_morto() -> bool:
		return false

## Golpes próprios da Tecelã (tecela_2d.gd, data2d/tecela_golpes_2d.csv): cada golpe avisa antes de sair, a teia desacelera quem está
## dentro, a badalada fere uma vez quem fica no anel e a ninhada respeita o máximo de filhotes vivos.
func _testar_tecela() -> void:
	var golpes := Csv.rows("res://data2d/tecela_golpes_2d.csv")
	var tipos := []
	var aviso_ok := true
	for g in golpes:
		tipos.append(g["golpe"])
		aviso_ok = aviso_ok and float(g["aviso"]) >= 0.8   # tempo de ler o aviso e reagir
	check.call(tipos.has("teia") and tipos.has("badalada") and tipos.has("filhotes"), "Tecelã: golpes teia, badalada e filhotes no CSV")
	check.call(aviso_ok, "Tecelã: todo golpe avisa por pelo menos 0,8 s")
	var cena := Node2D.new()
	t.root.add_child(cena)
	var jogador := AlvoFalso.new()
	cena.add_child(jogador)
	var chamados := []
	var tecela = load("res://scripts2d/tecela_2d.gd").new()
	cena.add_child(tecela)
	tecela.setup("bell_weaver", jogador, Vector2.ZERO)
	jogador.global_position = Vector2(400, 0)
	tecela._speed = 0.0   # parada: sem andar nem bater de perto, só os golpes especiais (e sem física fora da árvore)
	tecela.pontos_livres = func(c: Vector2, _r: float, n: int) -> Array:
		var out := []
		for i in n:
			out.append(c + Vector2(100 + 30 * i, 0))
		return out
	tecela.convocar = func(id: String, pontos: Array) -> Array:
		chamados.append([id, pontos.size()])
		return []
	var viu_teia := false
	var viu_onda := false
	for _q in 60 * 40:   # 40 s de luta, quadro a quadro (a árvore não anda sozinha aqui: o teste avança os efeitos também)
		tecela._physics_process(1.0 / 60.0)
		for f in cena.get_children():
			if f == tecela or f == jogador or not ("lentidao" in f or "raio_max" in f):
				continue
			viu_teia = viu_teia or "lentidao" in f
			viu_onda = viu_onda or "raio_max" in f
			f._physics_process(1.0 / 60.0)
		if not chamados.is_empty() and jogador.dano > 0.0 and jogador.lentidao > 0.0:
			break
	check.call(not chamados.is_empty() and chamados[0][0] == "gravel_spiderling" and chamados[0][1] == 3, "Tecelã: chama 3 Filhotes de Cascalho (%s)" % str(chamados))
	check.call(viu_teia and jogador.lentidao >= 0.5, "Tecelã: a teia sai e desacelera quem está dentro (%.2f)" % jogador.lentidao)
	check.call(viu_onda and jogador.dano > 0.0, "Tecelã: a badalada sai e fere quem fica no anel (dano %.1f)" % jogador.dano)
	cena.queue_free()
