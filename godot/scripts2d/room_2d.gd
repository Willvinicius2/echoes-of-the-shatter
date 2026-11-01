extends Node2D
## Sala da Cripta montada de um texto (data2d/rooms/*.txt) com TileMapLayer.
## Legenda: # parede, . piso, r piso com runas, q piso escuro, s laje de pedra (ruínas sobre o gramado),
## B braseiro, O pilar, D porta, P início do jogador, E ponto de inimigo, G lugar do chefe, X portal do fim da fase,
## p laje de caminho (só com `@piso grama`), m mata fechada (bloqueia; chão escuro, a orla de árvores vem dos props).
## `@lajes claro|escuro raio x,y` (células) desenha uma mancha de laje de pedra de contorno orgânico (ruínas, arena). Fase aberta (data2d/rooms/fase_*.txt): mapa grande sem `D`,
## câmera seguindo o jogador e um portal em `X` depois do chefe.
## `@caminho largura x,y x,y ...` e `@riacho largura x,y ...` (células; curva suave) desenham caminho de pedra
## e riacho; o riacho bloqueia jogador e inimigos (camada 8) menos onde o caminho o cruza.
## A linha `@piso grama` antes de `@props` troca o piso padrão por gramado (atlas cripta_grama.png).
## Depois da grade, a linha `@props` abre a lista de props: `id coluna linha [flip]` (coluna e linha
## podem ser fracionárias; ids em data2d/props_2d.csv, arte em props_manifest.csv).

signal porta_usada

const Csv = preload("res://scripts2d/csv2d.gd")
const Placeholders = preload("res://scripts2d/placeholders.gd")
const Terreno = preload("res://scripts2d/terreno_2d.gd")
const ATLAS := "res://art2d/tiles/cripta_tiles.png"
const ATLAS_GRAMA := "res://art2d/tiles/cripta_grama.png"
const T_PISO := 0
const T_PISO_ESCURO := 6
const T_PORTA_FECHADA := 7
const T_PAREDE_FACE := 8
const T_PAREDE_TOPO := 9
const T_PILAR := 12
const T_PORTA_ABERTA := 13
const T_BRASEIRO := 15
const T_RUNAS := [4, 41, 42, 43, 44, 45, 46, 47]

var tile := 64
var colunas := 0
var linhas := 0
var spawn_jogador := Vector2.ZERO
var posicao_portal := Vector2.ZERO   # célula X (fase aberta); vazio = sem X
var posicao_chefe := Vector2.ZERO    # célula G (fase aberta): o chefe espera aqui; vazio = nasce como os outros
var celulas_livres: Array[Vector2i] = []   # chão andável, longe de muro, água e prop sólido (spawn nas bordas da tela)
var spawns_inimigos: Array[Vector2] = []
var celulas_porta: Array[Vector2i] = []
var props: Array = []  # {id, pos (pé do prop em px), flip}
var _props_def := {}
var _props_arte := {}
var _layer: TileMapLayer
var _piso: TileMapLayer
var aneis: Array = []   # [{laje, fator}]
var _brilho_runas: TileMapLayer
var piso_grama := false
var braseiros: Array[Vector2] = []
var caminhos: Array = []  # {larg (células), pts (px)}
var riachos: Array = []
var lajes: Array = []  # {tom, raio (px), centro (px)}
var _mata: TileMapLayer
var _porta_area: Area2D
var _porta_corpo: StaticBody2D
var _grade: Array = []

func tamanho_px() -> Vector2:
	return Vector2(colunas * tile, linhas * tile)

func carregar(caminho: String) -> bool:
	tile = int(Csv.kv("res://data2d/run_settings.csv")["tile"])
	var f := FileAccess.open(caminho, FileAccess.READ)
	if f == null:
		push_error("Sala ausente: " + caminho)
		return false
	var em_props := false
	while not f.eof_reached():
		var l := f.get_line().strip_edges(false, true)
		if l == "":
			continue
		if l == "@props":
			em_props = true
		elif l == "@piso grama":
			piso_grama = true
		elif l.begins_with("@lajes "):
			var q := l.split(" ", false)
			var xy := q[3].split(",")
			lajes.append({"tom": q[1], "raio": float(q[2]) * tile, "centro": Vector2((float(xy[0]) + 0.5) * tile, (float(xy[1]) + 0.5) * tile)})
		elif l.begins_with("@anel "):
			var q := l.split(" ", false)   # @anel índice_da_laje fator: anel de runas que acompanha o contorno da laje
			aneis.append({"laje": int(q[1]), "fator": float(q[2]), "sigilo": q.size() > 3 and q[3] == "sigilo"})
		elif l.begins_with("@caminho ") or l.begins_with("@riacho "):
			var q := l.split(" ", false)
			var pts: Array = []
			for ponto in q.slice(2):
				var xy := ponto.split(",")
				pts.append(Vector2((float(xy[0]) + 0.5) * tile, (float(xy[1]) + 0.5) * tile))
			(caminhos if q[0] == "@caminho" else riachos).append({"larg": float(q[1]), "pts": pts})
		elif em_props:
			var p := l.split(" ", false)
			props.append({"id": p[0], "pos": Vector2((float(p[1]) + 0.5) * tile, (float(p[2]) + 0.5) * tile), "flip": p.size() > 3 and p[3] == "flip"})
		else:
			_grade.append(l)
	linhas = _grade.size()
	colunas = _grade[0].length()
	for l in _grade:
		if l.length() != colunas:
			push_error("Sala com linhas de tamanhos diferentes: " + caminho)
			return false
	for r in Csv.rows("res://data2d/props_2d.csv"):
		_props_def[r["id"]] = r
	for r in Csv.rows("res://data2d/props_manifest.csv"):
		_props_arte[r["id"]] = r
	_montar()
	return true

func _centro(x: int, y: int) -> Vector2:
	return Vector2((x + 0.5) * tile, (y + 0.5) * tile)

func _eh_parede(x: int, y: int) -> bool:
	if x < 0 or y < 0 or x >= colunas or y >= linhas:
		return true
	return _grade[y][x] in ["#", "D"]

func _montar() -> void:
	var ts := _tileset()
	_piso = TileMapLayer.new()  # piso sob os objetos, para o fundo transparente de braseiro e pilar não ficar preto
	_piso.tile_set = ts
	if piso_grama:
		# Gramado: um pouco mais escuro que o atlas para caminho e inimigos se destacarem; na fase aberta, mais claro
		# (a revisão achou o mapa grande escuro demais) e com variação de tom em _tons_do_gramado.
		_piso.modulate = Color(0.94, 0.96, 0.88) if colunas * linhas > 2000 else Color(0.8, 0.83, 0.78)
	add_child(_piso)
	_mata = TileMapLayer.new()  # chão da mata fechada, bem mais escuro que o gramado
	_mata.tile_set = ts
	if piso_grama:
		_mata.modulate = _piso.modulate   # o escuro da mata vem das manchas suaves de _sombra_da_mata, sem degrau de tile
	add_child(_mata)
	_layer = TileMapLayer.new()
	_layer.tile_set = ts
	add_child(_layer)
	_brilho_runas = TileMapLayer.new()  # runas douradas reforçados com brilho aditivo
	_brilho_runas.tile_set = ts
	var mat_brilho := CanvasItemMaterial.new()
	mat_brilho.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	_brilho_runas.material = mat_brilho
	_brilho_runas.modulate = Color(1.3, 0.95, 0.45, 1.0)
	add_child(_brilho_runas)
	var corpo := StaticBody2D.new()
	corpo.collision_layer = 1
	corpo.collision_mask = 0
	add_child(corpo)
	for y in linhas:
		var inicio := -1
		for x in colunas + 1:
			var bloqueia: bool = x < colunas and (_grade[y][x] in ["#", "O", "m"])
			if bloqueia and inicio < 0:
				inicio = x
			elif not bloqueia and inicio >= 0:
				var cs := CollisionShape2D.new()
				var r := RectangleShape2D.new()
				r.size = Vector2((x - inicio) * tile, tile)
				cs.shape = r
				cs.position = Vector2((inicio + (x - inicio) / 2.0) * tile, (y + 0.5) * tile)
				corpo.add_child(cs)
				inicio = -1
		for x in colunas:
			var c: String = _grade[y][x]
			var idx := T_PISO + posmod(hash(Vector2i(x, y)), 4)
			match c:
				"#":
					idx = T_PAREDE_TOPO if _eh_parede(x, y + 1) else T_PAREDE_FACE
					if idx == T_PAREDE_FACE:
						_pintar(Vector2i(x, y), T_PAREDE_TOPO, _piso)  # sob o muro, no lugar do preto
				"D":
					idx = T_PORTA_FECHADA
					celulas_porta.append(Vector2i(x, y))
				"r":
					idx = T_PISO + posmod(hash(Vector2i(x, y)), 4)
					var cols_r: int = _brilho_runas.tile_set.get_source(2).texture.get_width() / tile
					var rn: int = T_RUNAS[posmod(hash(Vector2i(x * 7, y * 13)), T_RUNAS.size())]
					_brilho_runas.set_cell(Vector2i(x, y), 2, Vector2i(rn % cols_r, rn / cols_r))
				"q":
					idx = T_PISO_ESCURO
				"O":
					idx = T_PILAR
				"B":
					idx = T_BRASEIRO
					braseiros.append(_centro(x, y))
				"P":
					spawn_jogador = _centro(x, y)
				"E":
					spawns_inimigos.append(_centro(x, y))
				"X":
					posicao_portal = _centro(x, y)
				"G":
					posicao_chefe = _centro(x, y)
			if c == "m":
				if piso_grama:
					_mata.set_cell(Vector2i(x, y), 1, Vector2i(posmod(hash(Vector2i(x, y)), 4), 0))
				else:
					_pintar(Vector2i(x, y), T_PISO_ESCURO, _mata)
				continue
			if piso_grama and c != "#" and c != "D":
				_pintar_grama(Vector2i(x, y), posmod(hash(Vector2i(x, y)), 4), 1 if c == "p" else 0)
			elif c != "#" and c != "D":
				_pintar(Vector2i(x, y), T_PISO + posmod(hash(Vector2i(x, y)), 4), _piso)
			if c != "." and c != "p" and not (c in ["P", "E", "X", "G"]):
				_pintar(Vector2i(x, y), idx)
			elif c in ["P", "E", "X", "G"]:   # marcador sobre laje de pedra: o piso segue o dos vizinhos
				var viz := _piso_vizinho(x, y)
				if viz == "q":
					_pintar(Vector2i(x, y), T_PISO_ESCURO)
				elif viz in ["s", "r"]:
					_pintar(Vector2i(x, y), T_PISO + posmod(hash(Vector2i(x, y)), 4))
	for p in props:
		var d: Dictionary = _props_def.get(p["id"], {})
		if d.is_empty() or float(d["solido_l"]) <= 0.0:
			continue
		var cp := CollisionShape2D.new()
		var rp := RectangleShape2D.new()
		rp.size = Vector2(float(d["solido_l"]), float(d["solido_a"]))
		cp.shape = rp
		# a colisão fica no centro da base que toca o chão (nas árvores, o pé do tronco), o mesmo ponto do y-sort
		cp.position = p["pos"] + Vector2(0, tile * 0.5 - _apoio_prop(p["id"]))
		corpo.add_child(cp)
	if piso_grama and colunas * linhas > 2000:
		_tons_do_gramado()
	_sombra_da_mata()
	_desenhar_lajes()
	Terreno.montar(self, caminhos, riachos, piso_grama, tile)
	if aberta():
		_achar_vinheta()
	_mapear_livres()
	_porta_corpo = StaticBody2D.new()
	_porta_corpo.collision_layer = 1
	_porta_corpo.collision_mask = 0
	add_child(_porta_corpo)
	for c in celulas_porta:
		var cd := CollisionShape2D.new()
		var rd := RectangleShape2D.new()
		rd.size = Vector2(tile, tile)
		cd.shape = rd
		cd.position = _centro(c.x, c.y)
		_porta_corpo.add_child(cd)
	_porta_area = Area2D.new()
	_porta_area.collision_layer = 0
	_porta_area.collision_mask = 2
	_porta_area.monitoring = false
	add_child(_porta_area)
	for c in celulas_porta:
		var cs := CollisionShape2D.new()
		var r := RectangleShape2D.new()
		r.size = Vector2(tile, tile)
		cs.shape = r
		cs.position = _centro(c.x, c.y) + Vector2(0, tile * 0.5)
		_porta_area.add_child(cs)
	_porta_area.body_entered.connect(func(_c): porta_usada.emit())

## Fase aberta: manchas grandes e suaves de grama seca (clara) e de grama funda (escura) espalhadas pelo mapa,
## para o gramado não ser a mesma textura repetida de ponta a ponta.
func _tons_do_gramado() -> void:
	var g := Gradient.new()
	g.set_color(0, Color(1, 1, 1, 1))
	g.set_color(1, Color(1, 1, 1, 0))
	var tex := GradientTexture2D.new()
	tex.gradient = g
	tex.fill = GradientTexture2D.FILL_RADIAL
	tex.fill_from = Vector2(0.5, 0.5)
	tex.fill_to = Vector2(1.0, 0.5)
	tex.width = 128
	tex.height = 128
	var raiz := Node2D.new()
	add_child(raiz)
	move_child(raiz, _layer.get_index())
	var cores := [Color(0.78, 0.72, 0.36, 0.22), Color(0.55, 0.62, 0.3, 0.2), Color(0.12, 0.2, 0.08, 0.22), Color(0.42, 0.32, 0.18, 0.18)]
	for y in range(0, linhas, 5):
		for x in range(0, colunas, 5):
			var h := hash(Vector2i(x * 31, y * 17))
			var sp := Sprite2D.new()
			sp.texture = tex
			sp.position = Vector2((x + posmod(h, 50) / 10.0) * tile, (y + posmod(h / 50, 50) / 10.0) * tile)
			sp.scale = Vector2(3.0 + posmod(h / 7, 30) / 10.0, 2.2 + posmod(h / 11, 20) / 10.0)
			sp.rotation = posmod(h / 13, 314) / 100.0
			sp.modulate = cores[posmod(h / 3, cores.size())]
			raiz.add_child(sp)

## Mata fechada como uma massa escura de borda macia: manchas radiais sobrepostas em cada célula da mata
## (uma sim, outra não no miolo), sem o degrau dos tiles.
func _sombra_da_mata() -> void:
	var g := Gradient.new()
	g.set_color(0, Color(0.02, 0.03, 0.02, 0.62))
	g.set_color(1, Color(0.02, 0.03, 0.02, 0.0))
	var tex := GradientTexture2D.new()
	tex.gradient = g
	tex.fill = GradientTexture2D.FILL_RADIAL
	tex.fill_from = Vector2(0.5, 0.5)
	tex.fill_to = Vector2(1.0, 0.5)
	tex.width = 64
	tex.height = 64
	var raiz := Node2D.new()
	add_child(raiz)
	move_child(raiz, _layer.get_index())   # sobre o chão da mata, sob as lajes, caminhos e atores
	for y in linhas:
		for x in colunas:
			if _grade[y][x] != "m":
				continue
			var beira := false
			for d in [Vector2i(-1, 0), Vector2i(1, 0), Vector2i(0, -1), Vector2i(0, 1)]:
				var v: Vector2i = Vector2i(x, y) + d
				if v.x >= 0 and v.y >= 0 and v.x < colunas and v.y < linhas and _grade[v.y][v.x] != "m":
					beira = true
			if not beira and posmod(x + y, 2) == 1:
				continue
			var sp := Sprite2D.new()
			sp.texture = tex
			var h := hash(Vector2i(x, y))
			sp.position = _centro(x, y) + Vector2(posmod(h, 21) - 10, posmod(h / 21, 21) - 10)
			sp.scale = Vector2.ONE * (2.4 + posmod(h, 10) * 0.08)
			raiz.add_child(sp)

## Manchas de laje de pedra (ruínas e arena) com contorno orgânico: polígono ondulado, textura das lajes da cripta
## e uma orla escura de terra embaixo. Ficam sob as runas, os caminhos e os atores.
func _desenhar_lajes() -> void:
	if lajes.is_empty():
		return
	var raiz := Node2D.new()
	add_child(raiz)
	move_child(raiz, _brilho_runas.get_index())
	var tex_claro := _textura_lajes(T_PISO)
	var tex_escuro := _textura_lajes(T_PISO_ESCURO)
	var orlas := Node2D.new()
	raiz.add_child(orlas)
	for i in lajes.size():
		var m: Dictionary = lajes[i]
		var escuro: bool = m["tom"] == "escuro"
		# Sombra de terra e musgo esfumadas (sem contorno duro) sob a pedra.
		orlas.add_child(_laje_esfumada(m, 11 + i, null, Color(0.22, 0.3, 0.12, 0.3), 1.0, 56.0))
		orlas.add_child(_laje_esfumada(m, 11 + i, null, Color(0.13, 0.11, 0.08, 0.4), 1.0, 30.0))
		var cor_laje := Color(0.85, 0.82, 0.8) if escuro else Color(0.92, 0.92, 0.9)
		if not escuro and i > 0 and lajes[i - 1]["tom"] == "escuro" and m["raio"] < lajes[i - 1]["raio"]:
			cor_laje = Color(0.72, 0.68, 0.66, 0.8)   # estrado sobre a laje escura: contraste baixo, sem cara de tapete
		raiz.add_child(_laje_esfumada(m, 11 + i, tex_escuro if escuro else tex_claro, cor_laje, 0.95, 34.0))
	_desenhar_aneis(raiz)

## Laje de contorno irregular com a beira esfumada: o miolo é opaco e uma faixa externa perde a opacidade até zero,
## então a pedra some no gramado sem a divisa reta de antes.
func _laje_esfumada(m: Dictionary, semente: int, tex: Texture2D, cor: Color, fator_dentro: float, faixa: float) -> MeshInstance2D:
	var np := maxi(48, int(m["raio"] / 2.5))   # a mesma contagem de pontos nos dois contornos
	var dentro := _contorno(m["centro"], m["raio"] * fator_dentro, semente, 0.06, np)
	var fora := _contorno(m["centro"], m["raio"] * fator_dentro + faixa, semente, 0.06, np)
	var n := dentro.size()
	var pts := PackedVector2Array()
	pts.append_array(dentro)
	pts.append_array(fora)
	var cores := PackedColorArray()
	for k in n:
		cores.append(cor)
	for k in n:
		cores.append(Color(cor.r, cor.g, cor.b, 0.0))
	var idx := PackedInt32Array()
	var tri := Geometry2D.triangulate_polygon(dentro)
	for t in range(0, tri.size() - 2, 3):
		idx.append_array(PackedInt32Array([tri[t], tri[t + 1], tri[t + 2]]))
	for k in n:
		var k2 := (k + 1) % n
		idx.append_array(PackedInt32Array([k, k2, n + k2, k, n + k2, n + k]))
	var uvs := PackedVector2Array()
	for p in pts:
		uvs.append(p / Vector2(tex.get_size()) if tex != null else Vector2.ZERO)
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = pts
	arr[Mesh.ARRAY_COLOR] = cores
	arr[Mesh.ARRAY_TEX_UV] = uvs
	arr[Mesh.ARRAY_INDEX] = idx
	var malha := ArrayMesh.new()
	malha.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	var mi := MeshInstance2D.new()
	mi.mesh = malha
	if tex != null:
		mi.texture = tex
		mi.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
	return mi

## Anéis de runas: um sulco de pedra escuro com fio dourado dentro e glifos gravados com brilho a cada trecho.
## Com `sigilo` o anel vira só um círculo de glifos com halo, sem sulco (marca o centro da arena).
func _desenhar_aneis(raiz: Node2D) -> void:
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	var fonte: TileSetAtlasSource = _brilho_runas.tile_set.get_source(2)
	var atlas: Texture2D = fonte.texture
	var cols: int = atlas.get_width() / tile
	for a in aneis:
		var idx: int = a["laje"]
		if idx < 0 or idx >= lajes.size():
			continue
		var m: Dictionary = lajes[idx]
		var pts := _contorno(m["centro"], m["raio"] * float(a["fator"]), 11 + idx, 0.0)
		var sigilo: bool = a.get("sigilo", false)
		var n := pts.size()
		pts.append(pts[0])
		if sigilo:
			var halo := Sprite2D.new()
			halo.texture = _halo_dourado()
			halo.position = m["centro"]
			halo.scale = Vector2.ONE * (m["raio"] * float(a["fator"]) * 2.6 / 128.0)
			halo.material = mat
			raiz.add_child(halo)
		else:
			var sulco := Line2D.new()   # sulco escavado na pedra
			sulco.points = pts
			sulco.width = 9.0
			sulco.default_color = Color(0.06, 0.05, 0.05, 0.7)
			raiz.add_child(sulco)
			var brilho := Line2D.new()
			brilho.points = pts
			brilho.width = 7.0
			brilho.default_color = Color(1.0, 0.7, 0.22, 0.16)
			brilho.material = mat
			raiz.add_child(brilho)
			var fio := Line2D.new()
			fio.points = pts
			fio.width = 2.0
			fio.default_color = Color(1.0, 0.8, 0.35, 0.55)
			fio.material = mat
			raiz.add_child(fio)
		# Glifos de runa do atlas, aditivos, espaçados ao longo do anel.
		var comprimento := 0.0
		for k in n:
			comprimento += pts[k].distance_to(pts[k + 1])
		var passo := 52.0 if not sigilo else maxf(comprimento / 8.0, 40.0)
		var andou := passo * 0.5
		for k in n:
			var seg := pts[k].distance_to(pts[k + 1])
			while andou < seg:
				var c := pts[k].lerp(pts[k + 1], andou / maxf(seg, 0.001))
				var h := hash(Vector2i(int(c.x), int(c.y)))
				var rn: int = T_RUNAS[posmod(h, T_RUNAS.size())]
				var glifo := Sprite2D.new()
				var at := AtlasTexture.new()
				at.atlas = atlas
				at.region = Rect2((rn % cols) * tile, (rn / cols) * tile, tile, tile)
				glifo.texture = at
				glifo.position = c
				glifo.rotation = (pts[k + 1] - pts[k]).angle() + PI * 0.5 if not sigilo else (c - m["centro"]).angle() + PI * 0.5
				glifo.modulate = Color(1.3, 0.95, 0.45, 0.95)
				glifo.material = mat
				raiz.add_child(glifo)
				andou += passo
			andou -= seg

func _halo_dourado() -> Texture2D:
	var g := Gradient.new()
	g.set_color(0, Color(1.0, 0.75, 0.3, 0.32))
	g.set_color(1, Color(1.0, 0.6, 0.2, 0.0))
	var t := GradientTexture2D.new()
	t.gradient = g
	t.width = 128
	t.height = 128
	t.fill = GradientTexture2D.FILL_RADIAL
	t.fill_from = Vector2(0.5, 0.5)
	t.fill_to = Vector2(1.0, 0.5)
	return t

## Círculo ondulado (raio em px) para as manchas de laje; a mesma semente dá o mesmo contorno.
func _contorno(centro: Vector2, raio: float, semente: int, serrilha := 0.0, n_pts := 0) -> PackedVector2Array:
	var pts := PackedVector2Array()
	var n := n_pts if n_pts > 0 else maxi(48, int(raio / 2.5))
	var f1 := 2.0 + posmod(semente * 7, 3)
	var f2 := 5.0 + posmod(semente * 13, 4)
	for k in n:
		var a := k * TAU / n
		var onda := 0.12 * sin(a * f1 + semente) + 0.06 * sin(a * f2 + semente * 2.3) + 0.03 * sin(a * 11.0 + semente * 0.7)
		onda += serrilha * (float(posmod(hash(Vector2i(k, semente)), 100)) / 100.0 - 0.5)   # beira irregular, sem curva lisa
		pts.append(centro + Vector2(cos(a), sin(a)) * raio * (1.0 + onda))
	return pts

## Textura de 2 x 2 tiles do atlas da cripta a partir de `idx` (4 variantes lado a lado), para repetir sem emenda visível.
func _textura_lajes(idx: int) -> Texture2D:
	var atlas: Texture2D = _layer.tile_set.get_source(0).texture
	var img := atlas.get_image()
	if img.is_compressed():
		img.decompress()
	img.convert(Image.FORMAT_RGBA8)
	var cols: int = img.get_width() / tile
	var out := Image.create(tile * 2, tile * 2, false, Image.FORMAT_RGBA8)
	for k in 4:
		var t: int = idx + (k if idx == T_PISO else 0)
		out.blit_rect(img, Rect2i((t % cols) * tile, (t / cols) * tile, tile, tile), Vector2i((k % 2) * tile, (k / 2) * tile))
	return ImageTexture.create_from_image(out)

## Piso mais comum nas 4 vizinhas de uma célula de marcador (P, E, X, G).
func _piso_vizinho(x: int, y: int) -> String:
	var conta := {}
	for d in [Vector2i(-1, 0), Vector2i(1, 0), Vector2i(0, -1), Vector2i(0, 1)]:
		var v: Vector2i = Vector2i(x, y) + d
		if v.x >= 0 and v.y >= 0 and v.x < colunas and v.y < linhas:
			var k: String = _grade[v.y][v.x]
			conta[k] = int(conta.get(k, 0)) + 1
	var melhor := "."
	for k in [".", "s", "q", "r"]:
		if int(conta.get(k, 0)) > int(conta.get(melhor, 0)):
			melhor = k
	return melhor

## A vinheta do terreno é do tamanho da sala; na fase aberta ela escureceria tudo longe do centro do mapa.
## Aqui ela passa a seguir a câmera (run_2d chama seguir_vinheta), com o tamanho da tela.
var _vinheta: Sprite2D
func _achar_vinheta() -> void:
	for c in get_children():
		if c is Sprite2D and c.z_index == 20 and c.texture is GradientTexture2D:
			_vinheta = c

func seguir_vinheta(centro: Vector2, tam_vista: Vector2) -> void:
	if _vinheta == null:
		return
	_vinheta.position = centro
	_vinheta.scale = tam_vista * 1.5 / float(_vinheta.texture.get_width())

## Fase aberta: o mapa é maior que a tela (a câmera segue o jogador e as ondas nascem fora da vista).
func aberta() -> bool:
	return celulas_porta.is_empty()

## Marca as células onde um inimigo pode nascer: piso sem muro, pilar, braseiro, água (fora da travessia) nem prop sólido.
func _mapear_livres() -> void:
	var bloq := {}
	for r in riachos:
		var raio: int = ceili(float(r["larg"]) * 0.5 + 0.7)
		for p in Terreno.spline(r["pts"], tile * 0.5):
			var c := Vector2i(int(p.x / tile), int(p.y / tile))
			for dy in range(-raio, raio + 1):
				for dx in range(-raio, raio + 1):
					bloq[c + Vector2i(dx, dy)] = true
	for p in props:
		var d: Dictionary = _props_def.get(p["id"], {})
		if not d.is_empty() and float(d["solido_l"]) > 0.0:
			var c := Vector2i(int(p["pos"].x / tile), int(p["pos"].y / tile))
			for dx in range(-1, 2):
				bloq[c + Vector2i(dx, 0)] = true
	celulas_livres.clear()
	for y in range(1, linhas - 1):
		for x in range(1, colunas - 1):
			if _grade[y][x] in [".", "r", "q", "s", "p", "E", "P", "X", "G"] and not bloq.has(Vector2i(x, y)) \
					and not _eh_parede(x, y - 1) and not _eh_parede(x, y + 1) and not _eh_parede(x - 1, y) and not _eh_parede(x + 1, y):
				celulas_livres.append(Vector2i(x, y))

## Retângulo andável do mapa em px (dentro do muro da borda). O spawner usa para não pôr inimigo fora do mapa.
func bordas_jogaveis() -> Rect2:
	return Rect2(Vector2(tile, tile * 2), Vector2((colunas - 2) * tile, (linhas - 3) * tile))

## Leva um ponto qualquer (ex.: do anel de spawn além da borda do mapa) para a célula livre mais perto dele.
func empurrar_para_dentro(pos: Vector2) -> Vector2:
	var b := bordas_jogaveis()
	var alvo := Vector2(clampf(pos.x, b.position.x, b.end.x - 1.0), clampf(pos.y, b.position.y, b.end.y - 1.0))
	var c0 := Vector2i(int(alvo.x / tile), int(alvo.y / tile))
	if celulas_livres.is_empty():
		return alvo
	var melhor: Vector2i = celulas_livres[0]
	var d_melhor := INF
	for c in celulas_livres:
		var d := float((c - c0).length_squared())
		if d < d_melhor:
			d_melhor = d
			melhor = c
			if d == 0.0:
				break
	return _centro(melhor.x, melhor.y)

## Pontos de nascimento fora da área vista (`vista`, em px), no anel entre `margem_min` e `margem_max` px além dela.
## Sem célula no anel (canto do mapa), usa as livres mais perto dele. Sorteio pelo `rng` da corrida (determinístico).
func pontos_fora_da_vista(vista: Rect2, margem_min: float, margem_max: float, n: int, rng: RandomNumberGenerator) -> Array[Vector2]:
	var dentro := vista.grow(margem_min)
	var fora := vista.grow(margem_max)
	var anel: Array[Vector2i] = []
	for c in celulas_livres:
		var p := _centro(c.x, c.y)
		if fora.has_point(p) and not dentro.has_point(p):
			anel.append(c)
	if anel.is_empty():
		var ordem := celulas_livres.filter(func(c: Vector2i) -> bool: return not dentro.has_point(_centro(c.x, c.y)))
		var meio := vista.get_center()
		ordem.sort_custom(func(a: Vector2i, b: Vector2i) -> bool: return _centro(a.x, a.y).distance_squared_to(meio) < _centro(b.x, b.y).distance_squared_to(meio))
		for c in ordem.slice(0, maxi(n * 4, 16)):
			anel.append(c)
	if anel.is_empty():
		anel = celulas_livres
	var out: Array[Vector2] = []
	for i in n:
		var c: Vector2i = anel[rng.randi_range(0, anel.size() - 1)]
		out.append(_centro(c.x, c.y))
	return out

func _pintar(c: Vector2i, idx: int, camada: TileMapLayer = null) -> void:
	var l := camada if camada != null else _layer
	var cols: int = l.tile_set.get_source(0).texture.get_width() / tile
	l.set_cell(c, 0, Vector2i(idx % cols, idx / cols))

func _pintar_grama(c: Vector2i, variante: int, linha: int) -> void:
	_piso.set_cell(c, 1, Vector2i(variante, linha))

func _so_dourado(tex: Texture2D) -> Texture2D:
	var img := tex.get_image()
	img.convert(Image.FORMAT_RGBA8)
	for y in img.get_height():
		for x in img.get_width():
			var c := img.get_pixel(x, y)
			var dourado := clampf((c.r - c.b - 0.07) / 0.18, 0.0, 1.0)
			img.set_pixel(x, y, Color(minf(c.r * 1.25, 1.0), minf(c.g * 1.15, 1.0), c.b, dourado * c.a))
	return ImageTexture.create_from_image(img)

func _tileset() -> TileSet:
	var tex: Texture2D
	if ResourceLoader.exists(ATLAS):
		tex = load(ATLAS)
	elif FileAccess.file_exists(ATLAS):
		tex = ImageTexture.create_from_image(Image.load_from_file(ProjectSettings.globalize_path(ATLAS)))
	else:
		tex = Placeholders.tiles(tile, 8, 2)
	var ts := TileSet.new()
	ts.tile_size = Vector2i(tile, tile)
	var src := TileSetAtlasSource.new()
	src.texture = tex
	src.texture_region_size = Vector2i(tile, tile)
	for y in tex.get_height() / tile:
		for x in tex.get_width() / tile:
			src.create_tile(Vector2i(x, y))
	ts.add_source(src, 0)
	var sr := TileSetAtlasSource.new()  # só o dourado das runas, sem o fundo de pedra, para brilhar sobre o piso comum
	sr.texture = _so_dourado(tex)
	sr.texture_region_size = Vector2i(tile, tile)
	for y in tex.get_height() / tile:
		for x in tex.get_width() / tile:
			sr.create_tile(Vector2i(x, y))
	ts.add_source(sr, 2)
	var tg := _carregar_textura(ATLAS_GRAMA)
	if tg != null:
		var sg := TileSetAtlasSource.new()
		sg.texture = tg
		sg.texture_region_size = Vector2i(tile, tile)
		for y in tg.get_height() / tile:
			for x in tg.get_width() / tile:
				sg.create_tile(Vector2i(x, y))
		ts.add_source(sg, 1)
	return ts

func abrir_porta() -> void:
	for c in celulas_porta:
		_pintar(c, T_PORTA_ABERTA)
	_porta_corpo.queue_free()
	_porta_area.set_deferred("monitoring", true)

## Cria os sprites dos props dentro de `alvo` (Node2D com y_sort_enabled, o mesmo dos atores) e os
## decalques que os prendem ao chão (sombras, terra, raízes) num nó da própria sala, sob os atores.
func colocar_props(alvo: Node2D) -> void:
	var Ancoragem = preload("res://scripts2d/ancoragem_2d.gd")
	var chao := Node2D.new()
	chao.name = "ChaoProps"
	add_child(chao)
	var k := 0
	for p in props:
		var arte: Dictionary = _props_arte.get(p["id"], {})
		var d: Dictionary = _props_def.get(p["id"], {})
		if arte.is_empty() or d.is_empty():
			push_warning("Prop sem arte ou definição: " + p["id"])
			continue
		var tex: Texture2D = _carregar_textura(arte["arquivo"])
		if tex == null:
			continue
		var spr := Sprite2D.new()
		spr.texture = tex
		spr.centered = false
		spr.offset = -Vector2(float(arte["pivo_x"]), float(arte["pivo_y"]))
		spr.scale = Vector2.ONE * float(d["escala"])
		spr.flip_h = p["flip"]
		if p["id"] in ["tree_dry_orange", "bush_dry_red"]:
			spr.modulate = Color(0.72, 0.68, 0.68)  # laranja e vermelho mais calmos, para inimigos e projéteis saltarem
		elif String(p["id"]).begins_with("tree_"):
			spr.modulate = Color(0.8, 0.77, 0.76)  # copas de fundo menos saturadas
		if spr.flip_h:
			spr.offset.x = -(tex.get_width() - float(arte["pivo_x"]))
		# O nó entra no y-sort pelo ponto de apoio (centro da base que toca o chão; nas árvores, o pé do
		# tronco), não pela borda de baixo do sprite: assim quem passa ao lado fica na frente do prop.
		var pe: Vector2 = p["pos"] + Vector2(0, tile * 0.5)
		var ap: float = Ancoragem.apoio(p["id"], tex, d, arte)
		var tipo: String = Ancoragem.tipo(p["id"])
		var no := Node2D.new()
		no.position = pe - Vector2(0, ap)
		spr.position = Vector2(0, ap)
		var atras := Node2D.new()
		var frente := Node2D.new()
		atras.position = spr.position
		frente.position = spr.position
		no.add_child(atras)   # tufos atrás do sprite
		no.add_child(spr)
		no.add_child(frente)  # tufos que cobrem um pouco o pé
		Ancoragem.prender(chao, atras, frente, p["id"], tex, d, arte, spr.flip_h, pe, piso_grama, k)
		if tipo == "raso":
			# capim, folhas, ossos: ficam no chão, sob todos os atores, fora do y-sort (decisão do Jev, 1/11)
			add_child(no)
		else:
			alvo.add_child(no)
			if tipo == "folhagem":
				_ocultaveis.append({"no": no, "spr": spr, "meia": tex.get_width() * float(d["escala"]) * 0.5, "alt": tex.get_height() * float(d["escala"])})
		k += 1

var _ocultaveis: Array = []  # arbustos: {no, spr, meia, alt}; ficam semitransparentes com alguém atrás

## Arbusto na frente do personagem fica a 55% de alfa enquanto ele está atrás (decisão do Jev, 1/11), para o
## corpo não sumir atrás de uma moita de meio corpo. Árvores, pilares e tumbas altas não mudam: sumir atrás
## delas é natural. O personagem é o `player` da corrida ou, nas ferramentas de captura, quem estiver no
## grupo `arqueiro`.
func _process(delta: float) -> void:
	if _ocultaveis.is_empty():
		return
	var pl: Node2D = null
	var run := get_parent()
	if run != null:
		pl = run.get("player") as Node2D
	if pl == null:
		pl = get_tree().get_first_node_in_group("arqueiro") as Node2D
	if pl == null:
		return
	var pp := pl.global_position
	for o in _ocultaveis:
		var no: Node2D = o["no"]
		var dy := no.global_position.y - pp.y
		var atras: bool = dy > 0.0 and dy < o["alt"] * 0.9 and absf(pp.x - no.global_position.x) < o["meia"] + 10.0
		var spr: Sprite2D = o["spr"]
		var alvo_a := 0.55 if atras else 1.0
		if absf(spr.modulate.a - alvo_a) > 0.01:
			spr.modulate.a = move_toward(spr.modulate.a, alvo_a, delta * 5.0)

## Altura do ponto de apoio do prop (px acima do pé), via ancoragem_2d.gd; 0 se faltar arte ou definição.
func _apoio_prop(id: String) -> float:
	var arte: Dictionary = _props_arte.get(id, {})
	var d: Dictionary = _props_def.get(id, {})
	if arte.is_empty() or d.is_empty():
		return 0.0
	var tex: Texture2D = _carregar_textura(arte["arquivo"])
	if tex == null:
		return float(d["solido_a"]) * 0.5
	return preload("res://scripts2d/ancoragem_2d.gd").apoio(id, tex, d, arte)

func _carregar_textura(caminho: String) -> Texture2D:
	if ResourceLoader.exists(caminho):
		return load(caminho)
	if FileAccess.file_exists(caminho):
		return ImageTexture.create_from_image(Image.load_from_file(ProjectSettings.globalize_path(caminho)))
	return null
