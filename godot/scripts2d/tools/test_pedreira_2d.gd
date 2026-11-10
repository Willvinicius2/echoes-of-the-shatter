extends RefCounted
## Testes da Pedreira dos Ecos (área 2, data2d/rooms/fase_2.txt, gerada por tools/mapas/gerar_fase_2.py), chamados por
## test_2d.gd: o tema e o piso, os fossos e a ponte (camada 8), o portão de pedra (pés, vão, âncora aérea, rocha que fecha a
## clareira), as lascas, a orla de terra da rocha, a espinha da estrada (sem fosso na estrada fora da ponte, ritmo e tamanho
## dos encontros, G, X, bolsão e encontros alcançáveis com os colisores de verdade) e as ondas só com inimigos que têm arte.

const Csv = preload("res://scripts2d/csv2d.gd")
const RoomScript = preload("res://scripts2d/room_2d.gd")
const Terreno = preload("res://scripts2d/terreno_2d.gd")
const Ancoragem = preload("res://scripts2d/ancoragem_2d.gd")
const ArteInimigos = preload("res://scripts2d/tools/arte_inimigos_2d.gd")
const SALA := "res://data2d/rooms/fase_2.txt"
const SALA_1 := "res://data2d/rooms/fase_1.txt"
const RAIO_JOGADOR := 12.0   # px: o colisor do arqueiro é um círculo de ~10 px (sobra de 2 px)

var t: SceneTree
var check: Callable

## Grade de passagem de 32 px montada com os colisores reais da sala (camada 1: parede, rocha, props; camada 8: fosso), cada
## retângulo alargado pelo raio do jogador; `alcance` é uma inundação de 4 vizinhos a partir de um ponto em px.
class Passagem:
	const PASSO := 32.0
	var cols := 0
	var lins := 0
	var livre := PackedByteArray()

	func _init(largura_px: float, altura_px: float) -> void:
		cols = int(ceil(largura_px / PASSO))
		lins = int(ceil(altura_px / PASSO))
		livre.resize(cols * lins)
		livre.fill(1)

	func bloquear(r: Rect2, raio: float) -> void:
		var c := r.grow(raio)
		var i0 := maxi(0, int(ceil(c.position.x / PASSO - 0.5)))
		var i1 := mini(cols - 1, int(floor(c.end.x / PASSO - 0.5)))
		var j0 := maxi(0, int(ceil(c.position.y / PASSO - 0.5)))
		var j1 := mini(lins - 1, int(floor(c.end.y / PASSO - 0.5)))
		for j in range(j0, j1 + 1):
			for i in range(i0, i1 + 1):
				livre[j * cols + i] = 0

	func indice(p: Vector2) -> int:
		return clampi(int(p.y / PASSO), 0, lins - 1) * cols + clampi(int(p.x / PASSO), 0, cols - 1)

	func esta_livre(p: Vector2) -> bool:
		return livre[indice(p)] == 1

	## A célula livre mais perto de `p` (até 3 células de distância), ou -1.
	func _inicio(p: Vector2) -> int:
		var c := indice(p)
		var cx := c % cols
		var cy := c / cols
		for r in range(0, 4):
			for dy in range(-r, r + 1):
				for dx in range(-r, r + 1):
					var x := cx + dx
					var y := cy + dy
					if x >= 0 and y >= 0 and x < cols and y < lins and livre[y * cols + x] == 1:
						return y * cols + x
		return -1

	func alcance(de: Vector2) -> PackedByteArray:
		var visto := PackedByteArray()
		visto.resize(livre.size())
		var ini := _inicio(de)
		if ini < 0:
			return visto
		var fila := PackedInt32Array([ini])
		visto[ini] = 1
		var k := 0
		while k < fila.size():
			var c: int = fila[k]
			k += 1
			var x := c % cols
			if x > 0 and livre[c - 1] == 1 and visto[c - 1] == 0:
				visto[c - 1] = 1
				fila.append(c - 1)
			if x < cols - 1 and livre[c + 1] == 1 and visto[c + 1] == 0:
				visto[c + 1] = 1
				fila.append(c + 1)
			if c >= cols and livre[c - cols] == 1 and visto[c - cols] == 0:
				visto[c - cols] = 1
				fila.append(c - cols)
			if c + cols < livre.size() and livre[c + cols] == 1 and visto[c + cols] == 0:
				visto[c + cols] = 1
				fila.append(c + cols)
		return visto

	## `p` foi alcançado (ou uma das 8 células em volta, por causa dos 32 px de passo).
	func chegou(visto: PackedByteArray, p: Vector2) -> bool:
		var c := indice(p)
		var cx := c % cols
		var cy := c / cols
		for dy in range(-1, 2):
			for dx in range(-1, 2):
				var x := cx + dx
				var y := cy + dy
				if x >= 0 and y >= 0 and x < cols and y < lins and visto[y * cols + x] == 1:
					return true
		return false

func _init(arvore: SceneTree, verifica: Callable) -> void:
	t = arvore
	check = verifica

func rodar() -> void:
	var sala = RoomScript.new()
	if not sala.carregar(SALA):
		check.call(false, "carrega a Pedreira (%s)" % SALA)
		sala.free()
		return
	_testar_mapa(sala)
	_testar_fossos_e_ponte(sala)
	_testar_portao(sala)
	_testar_orla(sala)
	_testar_estrada(sala)
	_testar_passagem(sala)
	sala.free()
	_testar_arte_dos_props()
	_testar_arte_do_cao()
	_testar_ondas()

func _def(id: String) -> Dictionary:
	for r in Csv.rows("res://data2d/props_2d.csv"):
		if r["id"] == id:
			return r
	return {}

func _n_inimigos(spec: String) -> int:
	var n := 0
	for parte in spec.split("|", false):
		var q := parte.split(":")
		n += int(q[1]) if q.size() > 1 else 1
	return n

func _testar_mapa(sala) -> void:
	check.call(sala.tema == "pedreira" and sala.piso_grama, "Pedreira: `@piso pedreira` liga o tema e o piso aberto")
	check.call(sala.aberta() and sala.colunas == 160 and sala.linhas == 72, "Pedreira: fase aberta de %dx%d" % [sala.colunas, sala.linhas])
	check.call(sala.spawn_jogador != Vector2.ZERO and sala.posicao_chefe != Vector2.ZERO and sala.posicao_portal != Vector2.ZERO, "Pedreira: P, G (o elite do portão) e X marcados")
	check.call(sala.bolsoes.size() == 1 and sala.guardas.size() >= 8, "Pedreira: um bolsão com baú e os encontros adormecidos (%d)" % sala.guardas.size())
	var ok_props := true
	var n_arco := 0
	var n_lascas := 0
	for pr in sala.props:
		ok_props = ok_props and sala._props_def.has(pr["id"]) and sala._props_arte.has(pr["id"])
		ok_props = ok_props and FileAccess.file_exists(sala._props_arte[pr["id"]]["arquivo"])
		if pr["id"] == "arco_portal":
			n_arco += 1
		elif String(pr["id"]).begins_with("pedreira_lasca_"):
			n_lascas += 1
	check.call(ok_props, "Pedreira: todo prop tem arte e definição (%d props)" % sala.props.size())
	check.call(n_arco == 0, "Pedreira: o portão do fim não repete o arco da área 1")
	check.call(n_lascas >= 100, "Pedreira: lascas de bloco cortado no lugar das pedrinhas redondas (%d)" % n_lascas)
	var arquivos_ok := true
	for d in sala.decalques:
		arquivos_ok = arquivos_ok and FileAccess.file_exists(String(d["arquivo"]))
	check.call(sala.decalques.size() >= 7 and arquivos_ok, "Pedreira: decalques dos fossos e da ponte existem (%d)" % sala.decalques.size())
	# luz própria do elite: um poço laranja nos pés do G, mais largo que o do braseiro comum e sem estourar o osso do sprite (a
	# intensidade cai de 0,4 para 0,28 na revisão do crítico: o sprite do elite recebe só metade do vermelho)
	var luz_elite := false
	for l in sala.luzes:
		if l["pos"].distance_to(sala.posicao_chefe) <= 1.5 * sala.tile and float(l["raio"]) >= 3.0 * sala.tile and l["cor"].a >= 0.25 and l["cor"].a <= 0.34 and l["cor"].r > l["cor"].b * 3.0:
			luz_elite = true
	check.call(luz_elite, "Pedreira: o elite do portão espera dentro de um poço de luz quente (@luz sobre o G)")
	# a luz dos braseiros e lampiões é laranja (nada de verde/branco estourado): vermelho e verde no halo, azul bem menor
	var luzes_frias := 0
	for l in sala.luzes:
		var c: Color = l["cor"]
		if c.r < c.g or c.b > c.r * 0.5:
			luzes_frias += 1
	check.call(luzes_frias == 0, "Pedreira: todas as luzes do mapa são quentes (%d fora do laranja)" % luzes_frias)

func _testar_fossos_e_ponte(sala) -> void:
	var corpo: StaticBody2D = sala.get_node_or_null("CorpoFossos")
	check.call(corpo != null and corpo.collision_layer == 8 and corpo.collision_mask == 0, "fossos: corpo na camada 8 (a flecha e a magia passam por cima)")
	check.call(sala.rects_fosso().size() >= 6, "fossos: ao menos seis retângulos (%d)" % sala.rects_fosso().size())
	var n_f := 0
	var n_ponte := 0
	var ponte_livre := true
	var fosso_bloqueia := true
	if corpo != null:
		for y in sala.linhas:
			for x in sala.colunas:
				var c: String = sala._grade[y][x]
				if c != "f" and c != "=":
					continue
				var centro := Vector2((x + 0.5) * sala.tile, (y + 0.5) * sala.tile)
				var coberto := false
				for cs in corpo.get_children():
					if cs is CollisionShape2D and Rect2(cs.position - cs.shape.size * 0.5, cs.shape.size).has_point(centro):
						coberto = true
						break
				if c == "f":
					n_f += 1
					fosso_bloqueia = fosso_bloqueia and coberto
				else:
					n_ponte += 1
					ponte_livre = ponte_livre and not coberto
	check.call(n_f >= 100 and fosso_bloqueia, "fossos: toda célula `f` bloqueia o passo (%d células)" % n_f)
	check.call(n_ponte >= 6 and ponte_livre, "ponte: as células `=` ficam andáveis dentro do fosso (%d células)" % n_ponte)
	# o fundo do fosso não tem lascas nem prop algum (a arte pintada é o fundo) e nenhum prop cai sobre `f`/`=`
	var sobre_fosso := 0
	for pr in sala.props:
		var cx := int(pr["pos"].x / sala.tile)
		var cy := int(pr["pos"].y / sala.tile)
		if sala._grade[cy][cx] == "f" or sala._grade[cy][cx] == "=":
			sobre_fosso += 1
	check.call(sobre_fosso == 0, "fossos: nenhum prop sobre o fosso ou a ponte (%d)" % sobre_fosso)

func _testar_portao(sala) -> void:
	var def := _def("pedreira_portao")
	var pes: Array = RoomScript.pes_do_prop(def)
	check.call(pes.size() == 2, "portão de pedra: dois pés (os bastiões); o vão entre eles fica livre")
	if pes.size() == 2:
		pes.sort_custom(func(a, b): return a.position.x < b.position.x)
		var vao: float = pes[1].position.x - pes[0].end.x
		check.call(vao >= 96.0 and vao <= 160.0, "portão de pedra: vão de %.0f px (cabe o arqueiro, 2 tiles no máximo)" % vao)
		check.call(absf(pes[0].end.x + pes[1].position.x) < 8.0, "portão de pedra: o vão fica no centro do sprite (no pivô)")
	check.call(float(def.get("solido_l", "1")) == 0.0 and float(def.get("solido_a", "1")) == 0.0, "portão de pedra: sem colisor central (só os pés bloqueiam)")
	check.call(Ancoragem.tipo("pedreira_portao") == "aereo" and Ancoragem.ocultavel("pedreira_portao"), "portão de pedra: é aéreo (y-sort pelo pé) e some quando o arqueiro passa atrás")
	check.call(Ancoragem.tipo("pedreira_portico") == "aereo" and Ancoragem.ocultavel("pedreira_portico"), "pórtico: continua aéreo e oculto quando alguém passa atrás")
	var portoes: Array = []
	for pr in sala.props:
		if pr["id"] == "pedreira_portao":
			portoes.append(pr["pos"])
	check.call(portoes.size() == 1, "portão de pedra: um só no mapa")
	if portoes.size() == 1:
		var base: Vector2 = portoes[0] + Vector2(0, sala.tile * 0.5)
		var distancia_g: float = sala.posicao_chefe.y - base.y   # o portão fica ao norte: o elite espera ao sul dele, de frente para o arqueiro
		check.call(distancia_g > 0.0 and distancia_g <= 3.5 * sala.tile and absf(base.x - sala.posicao_chefe.x) <= sala.tile, "portão de pedra: o elite (G) espera na frente dele, a até 3 tiles (%.1f)" % (distancia_g / sala.tile))
		check.call(sala.posicao_portal.y < base.y - 3.0 * sala.tile and absf(base.x - sala.posicao_portal.x) <= sala.tile, "portão de pedra: o portal (X) fica atrás dele")
		# a rocha liga os bastiões às paredes: nas linhas do pé do portão só o vão (5 células no máximo) fica aberto
		var linha := int(portoes[0].y / sala.tile)
		var abertas := 0
		for x in sala.colunas:
			if sala._grade[linha][x] != "m":
				abertas += 1
		check.call(abertas <= 8, "portão de pedra: a rocha fecha a clareira dos dois lados dele (%d células abertas na linha)" % abertas)

func _testar_orla(sala) -> void:
	var orla: Node = sala.get_node_or_null("OrlaTerra")
	check.call(orla is ColorRect and orla.material is ShaderMaterial, "orla de terra: a Pedreira tem o retângulo com o shader da rocha")
	if orla is ColorRect and orla.material is ShaderMaterial:
		check.call(orla.size == sala.tamanho_px() and orla.mouse_filter == Control.MOUSE_FILTER_IGNORE, "orla de terra: cobre o mapa inteiro e não pega o mouse")
		var mat: ShaderMaterial = orla.material
		var img: Image = (mat.get_shader_parameter("mascara") as Texture2D).get_image()
		var rocha := 0
		var marcadas := 0
		var coerente: bool = img.get_width() == sala.colunas and img.get_height() == sala.linhas
		if coerente:
			for y in sala.linhas:
				for x in sala.colunas:
					var eh_m: bool = sala._grade[y][x] == "m"
					var marca: bool = img.get_pixel(x, y).r > 0.5
					rocha += 1 if eh_m else 0
					marcadas += 1 if marca else 0
					coerente = coerente and eh_m == marca
		check.call(coerente and rocha > 1000 and rocha == marcadas, "orla de terra: a máscara de 1 px por célula marca só a rocha (%d células)" % rocha)
		check.call(mat.get_shader_parameter("grade_tam") == Vector2i(sala.colunas, sala.linhas) and float(mat.get_shader_parameter("tile")) == float(sala.tile), "orla de terra: o shader recebe o tamanho da grade e do tile")
	# o chão da rocha é o tile do piso em marrom-escuro: nem preto (a mata) nem igual ao ocre
	var cor: Color = RoomScript.COR_MASSA_PEDREIRA
	check.call(cor.r >= 0.35 and cor.g >= 0.35 and cor.b >= 0.35 and cor.r <= 0.8 and cor.g <= 0.8 and cor.b <= 0.8, "rocha: o chão dela fica em marrom-escuro, sem virar preto")
	check.call(sala._mata.modulate.is_equal_approx(cor), "rocha: a camada da massa usa esse marrom")
	# a Cripta (área 1) continua com a sombra da mata e sem a orla de terra
	var sala1 = RoomScript.new()
	if sala1.carregar(SALA_1):
		check.call(sala1.tema == "" and sala1.get_node_or_null("OrlaTerra") == null and not sala1._mata.modulate.is_equal_approx(cor), "área 1: sem orla de terra nem o marrom da rocha")
	else:
		check.call(false, "carrega a área 1 (%s)" % SALA_1)
	sala1.free()

## A distância andada pela linha da estrada (px) até o ponto dela mais perto de `p`, ou -1 se `p` fica a mais de `maximo` px dela.
func _s_na_estrada(linha: PackedVector2Array, p: Vector2, maximo: float) -> float:
	var d_min := INF
	var s_min := 0.0
	var andado := 0.0
	for k in linha.size():
		if k > 0:
			andado += linha[k - 1].distance_to(linha[k])
		var d: float = linha[k].distance_to(p)
		if d < d_min:
			d_min = d
			s_min = andado
	return s_min if d_min <= maximo else -1.0

func _testar_estrada(sala) -> void:
	var tile := float(sala.tile)
	check.call(sala.caminhos.size() >= 2, "estrada: a principal e a trilha do bolsão")
	if sala.caminhos.size() < 2:
		return
	var estrada: Dictionary = sala.caminhos[0]
	var pts: Array = estrada["pts"]
	check.call(float(estrada["larg"]) >= 2.0 and absf(float(sala.brilho_estrada) - 1.16) < 0.001, "estrada: larga (%.1f tiles) e com as lajes mais claras que o piso (%.2f)" % [estrada["larg"], sala.brilho_estrada])
	check.call(pts[0].distance_to(sala.spawn_jogador) <= 8.0 * tile and pts[pts.size() - 1].distance_to(sala.posicao_chefe) <= 6.0 * tile, "estrada: vai do arqueiro até o elite do portão")
	var linha := Terreno.spline(PackedVector2Array(pts), 16.0)
	var comprimento := 0.0
	for k in range(1, linha.size()):
		comprimento += linha[k - 1].distance_to(linha[k])
	check.call(comprimento / tile >= 130.0 and comprimento / tile <= 190.0, "estrada: %.0f tiles do início ao portão" % (comprimento / tile))
	# nenhum fosso na estrada, só a ponte; e ela atravessa o fosso maior pela ponte
	var em_fosso := 0
	var em_ponte := 0
	for q in linha:
		var c: String = sala._grade[clampi(int(q.y / tile), 0, sala.linhas - 1)][clampi(int(q.x / tile), 0, sala.colunas - 1)]
		if c == "f":
			em_fosso += 1
		elif c == "=":
			em_ponte += 1
	check.call(em_fosso == 0 and em_ponte >= 5, "estrada: passa pela ponte (%d pontos) e nunca por cima de um fosso (%d)" % [em_ponte, em_fosso])
	# a reta da ponte (pontos de controle com o mesmo y que cruzam a ponte) tem 12 a 16 tiles (5 de chegada, 7 de ponte, 3 de
	# saída) e a estrada faz uma curva logo depois, nada de uma reta de 30 tiles
	var k_ponte := -1
	for k in pts.size():
		var qc: String = sala._grade[clampi(int(pts[k].y / tile), 0, sala.linhas - 1)][clampi(int(pts[k].x / tile), 0, sala.colunas - 1)]
		if qc == "=":
			k_ponte = k
			break
	check.call(k_ponte >= 0, "estrada: um ponto de controle cai sobre a ponte")
	if k_ponte >= 0:
		var k0 := k_ponte
		while k0 > 0 and absf(pts[k0 - 1].y - pts[k_ponte].y) <= 1.0:
			k0 -= 1
		var k1 := k_ponte
		while k1 < pts.size() - 1 and absf(pts[k1 + 1].y - pts[k_ponte].y) <= 1.0:
			k1 += 1
		var trecho_reto: float = pts[k1].x - pts[k0].x
		var desvio := 0.0
		for q in linha:
			if q.x > pts[k1].x and q.x <= pts[k1].x + 10.0 * tile:
				desvio = maxf(desvio, absf(q.y - pts[k_ponte].y))
		check.call(trecho_reto / tile >= 12.0 and trecho_reto / tile <= 16.0 and desvio >= 1.5 * tile, "estrada: a reta da ponte tem %.1f tiles e uma curva logo depois (desvio de %.1f tiles nos 10 seguintes)" % [trecho_reto / tile, desvio / tile])
	# a trilha do bolsão sai da estrada, é mais estreita e leva ao baú
	var trilha: Dictionary = sala.caminhos[1]
	var tpts: Array = trilha["pts"]
	var d_boca := INF
	for q in linha:
		d_boca = minf(d_boca, q.distance_to(tpts[0]))
	check.call(d_boca <= 0.5 * tile and float(trilha["larg"]) < float(estrada["larg"]), "bolsão: a trilha sai da estrada, mais estreita")
	check.call(tpts[tpts.size() - 1].distance_to(sala.bolsoes[0]["pos"]) <= 5.0 * tile, "bolsão: a trilha leva ao baú")
	# marcos da bifurcação: lampiões e luz na boca da trilha, para ela ser vista de longe
	var postes := 0
	for pr in sala.props:
		if pr["id"] == "pedreira_poste_lanterna" and pr["pos"].distance_to(tpts[0]) <= 7.0 * tile:
			postes += 1
	var luzes_perto := 0
	for l in sala.luzes:
		if l["pos"].distance_to(tpts[0]) <= 7.0 * tile:
			luzes_perto += 1
	check.call(postes >= 2 and luzes_perto >= 2, "bolsão: a boca da trilha tem dois lampiões e luz (%d, %d)" % [postes, luzes_perto])
	# encontros e marcos ao longo da estrada: nenhum trecho sem encontro nem marco passa de 6 s (24 tiles a 4 tiles/s), o primeiro
	# encontro vem cedo e tem de 2 a 3 inimigos e só 2 a 3 nos 34 tiles iniciais
	var achados: Array = []   # [s em tiles, inimigos] (só os encontros)
	var marcos: Array = []    # s em tiles de cada encontro e de cada marco (bifurcação, ponte, pórticos)
	for g in sala.guardas:
		var s_g := _s_na_estrada(linha, g["pos"], 4.0 * tile)
		if s_g >= 0.0:
			achados.append([s_g / tile, _n_inimigos(String(g["spec"]))])
			marcos.append(s_g / tile)
	var s_fork := _s_na_estrada(linha, tpts[0], 1.0 * tile)
	check.call(s_fork >= 0.0, "estrada: a bifurcação do bolsão fica na estrada")
	marcos.append(s_fork / tile)
	for k in linha.size():
		var qc2: String = sala._grade[clampi(int(linha[k].y / tile), 0, sala.linhas - 1)][clampi(int(linha[k].x / tile), 0, sala.colunas - 1)]
		if qc2 == "=":
			marcos.append(_s_na_estrada(linha, linha[k], 1.0) / tile)   # a ponte: o primeiro ponto da estrada sobre ela
			break
	for pr in sala.props:
		if pr["id"] == "pedreira_portico":
			var s_p := _s_na_estrada(linha, pr["pos"], 6.0 * tile)
			if s_p >= 0.0:
				marcos.append(s_p / tile)
	achados.sort_custom(func(a, b): return a[0] < b[0])
	marcos.sort()
	var maior_vazio := 0.0
	for k in range(1, marcos.size()):
		maior_vazio = maxf(maior_vazio, float(marcos[k]) - float(marcos[k - 1]))
	check.call(achados.size() >= 7 and maior_vazio <= 24.0, "encontros: ao longo da estrada, sem trecho vazio maior que 6 s (%d encontros, %d marcos, maior vazio %.1f tiles)" % [achados.size(), marcos.size(), maior_vazio])
	check.call(not achados.is_empty() and achados[0][1] >= 2 and achados[0][1] <= 3 and float(achados[0][0]) <= 24.0, "encontros: o primeiro vem cedo e tem de 2 a 3 inimigos")
	var rampa_ok := true
	for a in achados:
		if float(a[0]) < 34.0 and int(a[1]) > 3:
			rampa_ok = false
	check.call(rampa_ok, "encontros: a rampa (trecho 1) não tem matilha de mais de 3; as maiores ficam nos trechos 2 e 3")
	for g in sala.guardas:
		var com_arte := true
		for parte in String(g["spec"]).split("|", false):
			var id: String = parte.split(":")[0]
			com_arte = com_arte and _inimigo_pronto(id)
		check.call(com_arte, "encontro %s: só inimigos com arte e stats" % g["spec"])

## Os colisores de verdade da sala (camada 1 e fosso na camada 8) numa grade de 32 px: do início ao elite, ao portal (só pelo
## vão do portão), ao baú do bolsão e a cada encontro, e a linha central da estrada toda livre para o arqueiro.
func _testar_passagem(sala) -> void:
	var g := Passagem.new(sala.colunas * sala.tile, sala.linhas * sala.tile)
	for no in sala.get_children():
		if not (no is StaticBody2D) or not (no.collision_layer == 1 or no.collision_layer == 8):
			continue
		for cs in no.get_children():
			if cs is CollisionShape2D and cs.shape is RectangleShape2D:
				g.bloquear(Rect2(cs.position - cs.shape.size * 0.5, cs.shape.size), RAIO_JOGADOR)
	var visto := g.alcance(sala.spawn_jogador)
	check.call(g.chegou(visto, sala.posicao_chefe), "passagem: o elite do portão (G) é alcançável do início")
	check.call(g.chegou(visto, sala.posicao_portal), "passagem: o portal (X) é alcançável do início (pelo vão do portão)")
	check.call(g.chegou(visto, sala.bolsoes[0]["pos"]), "passagem: o baú do bolsão é alcançável do início")
	var inalcancaveis := 0
	for guarda in sala.guardas:
		if not g.chegou(visto, guarda["pos"]):
			inalcancaveis += 1
	check.call(inalcancaveis == 0, "passagem: todos os encontros ficam em chão alcançável (%d fora)" % inalcancaveis)
	var linha := Terreno.spline(PackedVector2Array(sala.caminhos[0]["pts"]), 16.0)
	var presa := 0
	for k in range(0, linha.size(), 2):
		if not g.esta_livre(linha[k]) or not g.chegou(visto, linha[k]):
			presa += 1
	check.call(presa == 0, "passagem: a linha central da estrada inteira fica livre para o arqueiro (%d pontos presos)" % presa)
	# sem o vão o portal some: nada contorna os bastiões (a rocha liga os pés deles às paredes)
	var def := _def("pedreira_portao")
	var pes: Array = RoomScript.pes_do_prop(def)
	if pes.size() == 2:
		pes.sort_custom(func(a, b): return a.position.x < b.position.x)
		for pr in sala.props:
			if pr["id"] == "pedreira_portao":
				var base: Vector2 = pr["pos"] + Vector2(0, sala.tile * 0.5)
				var vao := Rect2(base + Vector2(pes[0].end.x, -36.0), Vector2(pes[1].position.x - pes[0].end.x, 36.0))
				g.bloquear(vao, 0.0)
		var sem_vao := g.alcance(sala.spawn_jogador)
		check.call(g.chegou(sem_vao, sala.posicao_chefe) and not g.chegou(sem_vao, sala.posicao_portal), "passagem: tapando o vão, o portal fica fechado (o portão é o único caminho)")

## O inimigo tem arte quando passa em `ArteInimigos` (stats em enemies.csv, as 5 animações do manifesto com as folhas, as 5
## direções e o tamanho certo). O stone_herald tem linha no manifesto mas ainda não tem as folhas, e também serve ao
## ossuary_warden.
func _inimigo_pronto(id: String) -> bool:
	return ArteInimigos.pronto(id)

## Props novos da Pedreira: arquivo no tamanho do manifesto, pivô no pé, lascas sem colisor e portão só com pés.
func _testar_arte_dos_props() -> void:
	var manifesto := {}
	for r in Csv.rows("res://data2d/props_manifest.csv"):
		manifesto[r["id"]] = r
	for id in ["pedreira_portao", "pedreira_lasca_0", "pedreira_lasca_1", "pedreira_lasca_2"]:
		var m: Dictionary = manifesto.get(id, {})
		var def := _def(id)
		check.call(not m.is_empty() and not def.is_empty(), "%s: tem linha no manifesto e em props_2d.csv" % id)
		if m.is_empty():
			continue
		var img := Image.load_from_file(ProjectSettings.globalize_path(m["arquivo"]))
		check.call(img != null and img.get_width() == int(m["largura"]) and img.get_height() == int(m["altura"]), "%s: PNG com o tamanho do manifesto (%sx%s)" % [id, m["largura"], m["altura"]])
		check.call(int(m["pivo_y"]) == int(m["altura"]) and absi(int(m["pivo_x"]) * 2 - int(m["largura"])) <= 1, "%s: pivô no centro do pé" % id)
		if id.begins_with("pedreira_lasca_"):
			check.call(float(def["solido_l"]) == 0.0 and float(def["solido_a"]) == 0.0 and String(def.get("pes", "")) == "", "%s: lasca sem colisor (o arqueiro passa por cima)" % id)

## Cão de Cinza, animado por código a partir da base aprovada (tools/sprites2d/cao_de_cinza): quadro de 92 px com o pé no pivô
## nas 5 direções, alfa binário, paleta curta (a base tem 22 cores; boca, dentes e brasa apagando somam poucas), nenhum quadro
## vazio e nenhum pixel colado na borda do quadro (o bote e a morte não podem ser cortados).
func _testar_arte_do_cao() -> void:
	var linhas := {}
	for r in Csv.rows("res://data2d/sprites_manifest.csv"):
		if r["id"] == "ash_hound":
			linhas[r["anim"]] = r
	check.call(linhas.size() == 5, "cão de cinza: 5 animações no manifesto (%d)" % linhas.size())
	if linhas.size() != 5:
		return
	var cores := {}
	var alfa_binario := true
	var vazios := 0
	var cortados := 0
	var pe_fora: Array[String] = []
	for anim in linhas:
		var m: Dictionary = linhas[anim]
		var img := Image.load_from_file(ProjectSettings.globalize_path(m["arquivo"]))
		if img == null:
			check.call(false, "cão de cinza: carrega a folha %s" % anim)
			continue
		img.convert(Image.FORMAT_RGBA8)
		var lado := int(m["quadro"])
		var n := int(m["quadros"])
		check.call(lado == 92 and int(m["pivo_x"]) == 46 and int(m["pivo_y"]) == 74, "cão de cinza %s: quadro de 92 px com o pivô em (46, 74)" % anim)
		var d := img.get_data()
		var larg := img.get_width()
		for i in range(larg * img.get_height()):
			var a := d[i * 4 + 3]
			if a == 0:
				continue
			if a != 255:
				alfa_binario = false
			else:
				cores[(d[i * 4] << 16) | (d[i * 4 + 1] << 8) | d[i * 4 + 2]] = true
		for dir in 5:
			for q in n:
				var x0 := q * lado
				var y0 := dir * lado
				var algum := false
				for k in range(lado):
					for borda in [Vector2i(k, 0), Vector2i(k, lado - 1), Vector2i(0, k), Vector2i(lado - 1, k)]:
						if d[((y0 + borda.y) * larg + x0 + borda.x) * 4 + 3] != 0:
							cortados += 1
				for y in range(lado):
					for x in range(lado):
						if d[((y0 + y) * larg + x0 + x) * 4 + 3] != 0:
							algum = true
							break
					if algum:
						break
				if not algum:
					vazios += 1
				if anim == "idle" and q == 0:
					var pe := -1
					for y in range(lado - 1, -1, -1):
						for x in range(lado):
							if d[((y0 + y) * larg + x0 + x) * 4 + 3] != 0:
								pe = y
								break
						if pe >= 0:
							break
					if absi(pe - int(m["pivo_y"])) > 1:
						pe_fora.append("dir %d: pé na linha %d" % [dir, pe])
	check.call(alfa_binario, "cão de cinza: alfa binário (pixel art sem meio-tom)")
	check.call(cores.size() <= 26, "cão de cinza: paleta curta (%d cores, no máximo 26)" % cores.size())
	check.call(vazios == 0, "cão de cinza: nenhum quadro vazio (%d)" % vazios)
	check.call(cortados == 0, "cão de cinza: nenhum pixel colado na borda do quadro (%d)" % cortados)
	check.call(pe_fora.is_empty(), "cão de cinza: o pé do idle fica no pivô nas 5 direções %s" % str(pe_fora))
	check.call(int(linhas["attack"]["evento_quadro"]) == 4 and int(linhas["attack"]["quadros"]) == 8, "cão de cinza: o bote tem 8 quadros e o contato é o quadro 4")

## Ondas da Pedreira só com inimigos que já têm folha de sprite e stats: nada de caixa marrom provisória no jogo.
func _testar_ondas() -> void:
	var usados := {}
	for r in Csv.rows("res://data2d/ondas.csv"):
		if r["fase"] != "pedreira":
			continue
		for parte in String(r["inimigos"]).split("|", false):
			usados[parte.split(":")[0]] = true
	for r in Csv.rows("res://data2d/ondas_fases.csv"):
		if r["fase"] != "pedreira":
			continue
		usados[String(r["chefe"])] = true
		for parte in String(r["enxame_inimigos"]).split("|", false):
			usados[parte.split(":")[0]] = true
	check.call(usados.size() >= 5, "ondas da Pedreira: %d tipos de inimigo no total" % usados.size())
	var sem_arte: Array = []
	for id in usados:
		if not _inimigo_pronto(id):
			sem_arte.append(id)
	check.call(sem_arte.is_empty(), "ondas da Pedreira: só inimigos com arte e stats %s" % str(sem_arte))
