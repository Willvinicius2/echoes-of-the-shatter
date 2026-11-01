extends Node2D
## Clima vivo da sala: vento com rajadas, árvores, arbustos e capim balançando, folhas caindo das copas
## e atravessando a sala, fogo, brasas e fumaça nos braseiros, sombras de nuvem, poeira no ar e ondas de
## vento no gramado. Só visual: não toca em colisão nem em regra. Números em data2d/clima.csv.
## Criado pelo ambiente_2d.gd de cada sala; acha a vegetação nos props já colocados (atores da corrida)
## e nos tufos do terreno, pelo nome do arquivo da textura.

const Csv = preload("res://scripts2d/csv2d.gd")
const Room = preload("res://scripts2d/room_2d.gd")

const BALANCO_SHADER := """
shader_type canvas_item;
uniform float vento = 0.0;
uniform float sentido = 1.0;
uniform float balanco_px = 8.0;
uniform float farfalhar_px = 1.5;
uniform float ritmo = 1.0;
varying float fase;
varying vec4 cor_v;
void vertex() {
	fase = MODEL_MATRIX[3].x * 0.013 + MODEL_MATRIX[3].y * 0.021;
	cor_v = COLOR;
}
void fragment() {
	float altura = 1.0 - UV.y;
	float curva = altura * altura;
	float vai_vem = 0.62 + 0.38 * sin(TIME * 1.35 * ritmo + fase);
	float dx = vento * vai_vem * balanco_px * curva;
	dx += sin(TIME * 3.3 * ritmo + UV.y * 19.0 + fase * 3.0) * farfalhar_px * smoothstep(0.3, 1.0, altura) * (0.35 + vento);
	vec2 uv = UV - vec2(dx * sentido * TEXTURE_PIXEL_SIZE.x, 0.0);
	vec4 c = texture(TEXTURE, uv);
	c.a *= step(0.0, uv.x) * step(uv.x, 1.0);
	COLOR = c * cor_v;
}
"""

## Fogo em pixel art desenhado quadro a quadro: ruído subindo, cortado em 4 cores, tempo em passos
## (fps baixo, como uma folha de sprites) e inclinação com o vento.
const FOGO_SHADER := """
shader_type canvas_item;
uniform vec2 res = vec2(18.0, 26.0);
uniform float fps = 12.0;
uniform float semente = 0.0;
uniform float vento = 0.0;
float h(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float ruido(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(h(i), h(i + vec2(1.0, 0.0)), f.x), mix(h(i + vec2(0.0, 1.0)), h(i + vec2(1.0, 1.0)), f.x), f.y);
}
void fragment() {
	vec2 p = (floor(UV * res) + 0.5) / res;
	float t = floor(TIME * fps) / fps + semente;
	float y = 1.0 - p.y;
	float x = p.x - 0.5 - vento * 0.16 * y * y - sin(t * 2.1 + y * 5.0) * 0.03 * y;
	float n = ruido(vec2(p.x * 5.0 + semente, p.y * 4.0 + t * 3.4)) * 0.6 + ruido(vec2(p.x * 11.0 - semente, p.y * 9.0 + t * 6.5)) * 0.4;
	float largura = 0.44 * (1.0 - y * 0.75);
	float corpo = 1.0 - smoothstep(largura * 0.35, largura, abs(x));
	float nucleo = 1.0 - smoothstep(0.0, largura * 0.55, abs(x));
	float calor = corpo * (1.0 - y * 1.3) + nucleo * 0.25 * (1.0 - y * 2.0) + (n - 0.5) * 1.05 * (0.35 + y);
	vec4 c = vec4(0.0);
	if (calor > 0.86) c = vec4(1.0, 0.94, 0.62, 1.0);
	else if (calor > 0.62) c = vec4(1.0, 0.76, 0.24, 1.0);
	else if (calor > 0.4) c = vec4(0.98, 0.47, 0.12, 1.0);
	else if (calor > 0.22) c = vec4(0.78, 0.2, 0.07, 0.95);
	COLOR = c;
}
"""

## Brasas do fundo da tigela: o brilho de cada pixel de carvão sobe e desce em passos.
const BRASA_SHADER := """
shader_type canvas_item;
render_mode blend_add;
uniform float fps = 10.0;
uniform float semente = 0.0;
float h(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
void fragment() {
	vec4 m = texture(TEXTURE, UV);
	float t = floor(TIME * fps + semente);
	vec2 cel = floor(UV * 16.0);
	float b = mix(h(cel + t * 0.37), h(cel + (t + 1.0) * 0.37), 0.5);
	COLOR = vec4(m.rgb * (0.35 + 0.9 * b), m.a);
}
"""

const ONDAS_SHADER := """
shader_type canvas_item;
render_mode blend_add;
uniform vec2 dir = vec2(1.0, 0.2);
uniform vec2 tamanho = vec2(1536.0, 832.0);
uniform float forca = 0.0;
uniform float alpha_max = 0.05;
void fragment() {
	vec2 p = UV * tamanho;
	vec2 d = normalize(dir);
	float s = dot(p, d);
	float t = dot(p, vec2(-d.y, d.x));
	float faixa = sin(s * 0.011 - TIME * 1.7 + sin(t * 0.009 + 1.3) * 1.8);
	faixa = smoothstep(0.55, 1.0, faixa);
	float quebra = 0.5 + 0.5 * sin(t * 0.021 + s * 0.003 + TIME * 0.25);
	COLOR = vec4(0.82, 0.86, 0.55, faixa * quebra * forca * alpha_max);
}
"""

const CORES_FOLHA := [Color(0.96, 0.56, 0.2), Color(0.86, 0.38, 0.14), Color(1.0, 0.72, 0.3), Color(0.7, 0.42, 0.2), Color(0.8, 0.26, 0.12)]
const CORES_FOLHA_TEAL := [Color(0.3, 0.7, 0.68), Color(0.22, 0.52, 0.5), Color(0.45, 0.78, 0.7)]

var cfg := {}
var sala: Node2D
var vento := 0.0           # força atual do vento, 0..1
var dir_vento := Vector2(1, 0)
var _t := 0.0
var _rng := RandomNumberGenerator.new()
var _mats := {}            # "categoria|flip" -> ShaderMaterial
var _arvores: Array = []   # {base, larg, alt, cores, acum}
var _folhas: Array = []
var _fogo: Array = []      # CPUParticles2D que seguem o vento (brasas e fumaça)
var _nuvens: Array = []
var _poeira: CPUParticles2D
var _ondas: ShaderMaterial
var _ar: Node2D            # folhas no ar (por cima de tudo)
var _chao: Node2D          # folhas caídas e sombras das folhas
var _tamanho := Vector2.ZERO
var _tex_cache := {}
var _escala_area := 1.0
var _mats_fogo: Array = []

func _ready() -> void:
	cfg = Csv.kv("res://data2d/clima.csv")
	dir_vento = Vector2(cfg["vento_dir_x"], cfg["vento_dir_y"]).normalized()
	_rng.seed = hash(get_instance_id())
	_montar.call_deferred()

func _montar() -> void:
	sala = _achar_sala()
	if sala == null or sala.is_queued_for_deletion():
		return  # sala trocada no mesmo quadro: os props já são da próxima
	_tamanho = sala.tamanho_px()
	_escala_area = clampf(_tamanho.x * _tamanho.y / (1536.0 * 832.0), 1.0, cfg["escala_area_max"])  # salas maiores (mapa ampliado) ganham mais nuvem, poeira e folhas
	_chao = Node2D.new()
	_chao.z_index = 2
	_chao.draw.connect(_desenhar_chao)
	add_child(_chao)
	_ar = Node2D.new()
	_ar.z_index = 12
	_ar.draw.connect(_desenhar_ar)
	add_child(_ar)
	_vegetacao()
	for b in sala.braseiros:
		_braseiro(b)
	_criar_poeira()
	if sala.piso_grama:
		_criar_nuvens(Color(0.02, 0.03, 0.06, cfg["nuvem_alpha"]), 2)
		_criar_ondas()
	else:  # cripta de pedra: névoa rasteira clara em vez de sombra de nuvem
		_criar_nuvens(Color(0.7, 0.74, 0.8, cfg["nevoa_alpha"]), 3)

func _achar_sala() -> Node2D:
	var n := get_parent()
	while n != null and not n.has_method("tamanho_px"):
		n = n.get_parent()
	return n as Node2D

# ---------------------------------------------------------------- vento

## Rajadas: soma de senos lentos, com pico mais curto que o vale.
func _forca_vento(t: float) -> float:
	var g := 0.5 + 0.5 * (sin(t * 0.43) * 0.55 + sin(t * 0.91 + 1.7) * 0.3 + sin(t * 2.3 + 4.1) * 0.15)
	g = clampf(g, 0.0, 1.0)
	return clampf(cfg["vento_base"] + cfg["vento_rajada"] * g * g, 0.0, 1.0)

func _process(delta: float) -> void:
	if sala == null:
		return
	_t += delta
	vento = _forca_vento(_t)
	for m in _mats.values():
		m.set_shader_parameter("vento", vento)
	for m in _mats_fogo:
		m.set_shader_parameter("vento", vento * signf(dir_vento.x))
	var w: Vector2 = dir_vento * vento * cfg["vento_vel_folha"]
	for p in _fogo:
		p["no"].gravity = p["base"] + w * p["fator"]
	if _poeira != null:
		_poeira.gravity = w * 0.12
	if _ondas != null:
		_ondas.set_shader_parameter("forca", vento)
	_mover_nuvens(delta)
	_soltar_folhas(delta, w)
	_mover_folhas(delta, w)
	_ar.queue_redraw()
	_chao.queue_redraw()

# ---------------------------------------------------------------- vegetação

func _categoria(id: String) -> String:
	if id == "tree_stump" or id == "tree_dry_pile":
		return ""
	if id.begins_with("tree_"):
		return "arvore"
	for pre in ["bush_", "shrub_", "sapling_", "ferns_"]:
		if id.begins_with(pre):
			return "arbusto"
	for pre in ["grass_", "reeds_", "thistles_", "flowers_"]:
		if id.begins_with(pre):
			return "capim"
	return ""

func _material(cat: String, flip: bool) -> ShaderMaterial:
	var chave := "%s|%s" % [cat, flip]
	if not _mats.has(chave):
		var sh := Shader.new()
		sh.code = BALANCO_SHADER
		var m := ShaderMaterial.new()
		m.shader = sh
		m.set_shader_parameter("sentido", (-1.0 if flip else 1.0) * signf(dir_vento.x if dir_vento.x != 0.0 else 1.0))
		m.set_shader_parameter("balanco_px", cfg["balanco_" + cat])
		m.set_shader_parameter("farfalhar_px", cfg["farfalhar_" + cat])
		m.set_shader_parameter("ritmo", {"arvore": 1.0, "arbusto": 1.3, "capim": 1.7}[cat])
		_mats[chave] = m
	return _mats[chave]

func _vegetacao() -> void:
	var sprites: Array = []
	var atores = sala.get_parent().get("atores") if sala.get_parent() != null else null
	if atores is Node2D:
		for no in atores.get_children():
			if no.is_queued_for_deletion():
				continue
			for c in no.get_children():
				if c is Sprite2D:
					sprites.append(c)
	for c in sala.get_children():
		if c is Sprite2D:
			sprites.append(c)
	for sp in sprites:
		if sp.texture == null or sp.material != null:
			continue
		var id: String = sp.texture.resource_path.get_file().get_basename()
		var cat := _categoria(id)
		if cat == "":
			continue
		sp.material = _material(cat, sp.flip_h)
		if cat == "arvore" and (id.begins_with("tree_dry_") or id == "tree_teal_leaves"):
			var tam: Vector2 = sp.texture.get_size() * sp.scale
			_arvores.append({"base": sp.global_position - global_position, "larg": tam.x, "alt": tam.y,
				"cores": CORES_FOLHA_TEAL if id == "tree_teal_leaves" else CORES_FOLHA, "acum": _rng.randf()})

# ---------------------------------------------------------------- folhas

func _nova_folha(p: Vector2, z: float, v: Vector2, cores: Array) -> void:
	if _folhas.size() >= int(cfg["folhas_max"] * _escala_area):
		return
	_folhas.append({"p": p, "z": z, "v": v, "ang": _rng.randf() * TAU, "giro": _rng.randf_range(-3.0, 3.0),
		"virar": _rng.randf() * TAU, "virar_v": _rng.randf_range(3.0, 7.0), "queda": _rng.randf_range(14.0, 26.0),
		"fase": _rng.randf() * TAU, "cor": cores[_rng.randi() % cores.size()].darkened(_rng.randf_range(0.0, 0.15)),
		"tam": _rng.randf_range(7.0, 11.0), "chao": false, "t_chao": 0.0})

func _soltar_folhas(delta: float, w: Vector2) -> void:
	var taxa: float = cfg["folhas_por_arvore"] * (0.5 + vento * 1.5)
	for a in _arvores:
		a["acum"] += taxa * delta
		while a["acum"] >= 1.0:
			a["acum"] -= 1.0
			var base: Vector2 = a["base"]
			var p := base + Vector2(_rng.randf_range(-0.32, 0.32) * a["larg"], _rng.randf_range(-14.0, 10.0))
			_nova_folha(p, _rng.randf_range(0.45, 0.85) * a["alt"], w * 0.3, a["cores"])
	if _rng.randf() < cfg["folhas_rajada"] * _escala_area * pow(vento, 3.0) * delta:
		var x := -30.0 if dir_vento.x >= 0.0 else _tamanho.x + 30.0
		var p := Vector2(x, _rng.randf_range(0.1, 1.0) * _tamanho.y)
		_nova_folha(p, _rng.randf_range(25.0, 110.0), w, CORES_FOLHA)

func _mover_folhas(delta: float, w: Vector2) -> void:
	var vivas: Array = []
	for f in _folhas:
		if f["chao"]:
			f["t_chao"] += delta
			if vento > 0.8:  # rajada forte arrasta um pouco as folhas caídas
				f["p"] += w * 0.18 * (vento - 0.8) * 5.0 * delta
				f["ang"] += f["giro"] * 0.3 * delta
		else:
			var ondula := Vector2(-dir_vento.y, dir_vento.x) * sin(_t * 2.4 + f["fase"]) * 22.0
			f["v"] = f["v"].lerp(w + ondula, clampf(delta * 1.6, 0.0, 1.0))
			f["p"] += f["v"] * delta
			f["z"] -= f["queda"] * (0.7 + 0.5 * sin(_t * 3.1 + f["fase"])) * delta
			f["ang"] += f["giro"] * delta
			f["virar"] += f["virar_v"] * delta
			if f["z"] <= 0.0:
				f["z"] = 0.0
				f["chao"] = true
		var dentro: bool = f["p"].x > -60.0 and f["p"].x < _tamanho.x + 60.0 and f["p"].y > -60.0 and f["p"].y < _tamanho.y + 60.0
		if dentro and f["t_chao"] < cfg["folha_tempo_chao"]:
			vivas.append(f)
	_folhas = vivas

func _poligono_folha(f: Dictionary) -> PackedVector2Array:
	var tam: float = f["tam"]
	var larg: float = tam * 0.42 * (0.25 + 0.75 * absf(cos(f["virar"]))) if not f["chao"] else tam * 0.42
	var pts := PackedVector2Array([Vector2(-tam, 0), Vector2(-tam * 0.4, -larg), Vector2(tam * 0.45, -larg * 0.8),
		Vector2(tam, 0), Vector2(tam * 0.45, larg * 0.8), Vector2(-tam * 0.4, larg)])
	var tr := Transform2D(f["ang"], f["p"] - Vector2(0, f["z"]))
	return tr * pts

func _desenhar_chao() -> void:
	for f in _folhas:
		var a := 1.0 - clampf((f["t_chao"] - (cfg["folha_tempo_chao"] - 1.5)) / 1.5, 0.0, 1.0)
		if f["chao"]:
			var c: Color = f["cor"].darkened(0.2)
			c.a = 0.92 * a
			var pts := _poligono_folha(f)
			_chao.draw_colored_polygon(pts, c)
			_chao.draw_line(pts[0], pts[3], c.darkened(0.4), 1.0)
		else:  # sombra da folha no chão, mais fraca quanto mais alta
			var s := clampf(1.0 - f["z"] / 120.0, 0.0, 1.0)
			_chao.draw_circle(f["p"], f["tam"] * 0.6, Color(0, 0, 0, 0.28 * s))

func _desenhar_ar() -> void:
	for f in _folhas:
		if f["chao"]:
			continue
		var c: Color = f["cor"]
		c = c.lightened(0.12 * absf(sin(f["virar"])))  # o lado virado para a luz brilha um pouco
		var a := clampf(f["z"] / 12.0, 0.0, 1.0)
		c.a = 0.95 * (0.4 + 0.6 * a)
		var pts := _poligono_folha(f)
		_ar.draw_colored_polygon(pts, c)
		# metade de baixo mais escura (volume) e nervura central
		_ar.draw_colored_polygon(PackedVector2Array([pts[0], pts[3], pts[4], pts[5]]), c.darkened(0.22))
		_ar.draw_line(pts[0], pts[3], c.darkened(0.45), 1.2)

# ---------------------------------------------------------------- fogo e fumaça

func _textura_suave(chave: String, lado: int, dura := false) -> GradientTexture2D:
	if not _tex_cache.has(chave):
		var g := Gradient.new()
		g.set_color(0, Color(1, 1, 1, 1))
		if dura:
			g.add_point(0.45, Color(1, 1, 1, 0.85))
		g.set_color(g.get_point_count() - 1, Color(1, 1, 1, 0))
		var t := GradientTexture2D.new()
		t.gradient = g
		t.width = lado
		t.height = lado
		t.fill = GradientTexture2D.FILL_RADIAL
		t.fill_from = Vector2(0.5, 0.5)
		t.fill_to = Vector2(1.0, 0.5)
		_tex_cache[chave] = t
	return _tex_cache[chave]

func _mat_shader(codigo: String, params: Dictionary) -> ShaderMaterial:
	if not _tex_cache.has(codigo):
		var sh := Shader.new()
		sh.code = codigo
		_tex_cache[codigo] = sh
	var m := ShaderMaterial.new()
	m.shader = _tex_cache[codigo]
	for k in params:
		m.set_shader_parameter(k, params[k])
	return m

## Tira a chama pintada do tile do braseiro: acima da borda da tigela fica transparente e o fogo
## dentro da tigela vira carvão escuro. Devolve [tigela, máscara do carvão] (a máscara brilha por shader).
static var _tigela_cache: Array = []

func _tigela_sem_chama() -> Array:
	if not _tigela_cache.is_empty():
		return _tigela_cache
	var camada = sala.get("_layer")
	if not (camada is TileMapLayer) or camada.tile_set == null:
		return []
	var tex: Texture2D = camada.tile_set.get_source(0).texture
	var img := tex.get_image()
	if img == null:
		return []
	img.decompress()
	img.convert(Image.FORMAT_RGBA8)
	var t: int = sala.tile
	var cols := img.get_width() / t
	var idx: int = Room.T_BRASEIRO
	var reg := img.get_region(Rect2i((idx % cols) * t, (idx / cols) * t, t, t))
	var masc := Image.create(t, t, false, Image.FORMAT_RGBA8)
	var borda := int(t * cfg["tigela_borda"])
	var fundo := int(t * cfg["tigela_fundo"])
	for y in t:
		for x in t:
			var c := reg.get_pixel(x, y)
			if c.a < 0.1:
				continue
			var fogo := c.r > 0.55 and c.r > c.b + 0.25 and (c.g > 0.3 or c.r > 0.75)
			if y < borda and (fogo or absf(x - t * 0.5) < t * 0.3):
				reg.set_pixel(x, y, Color(0, 0, 0, 0))
			elif y < fundo and fogo:
				var v := 0.10 + 0.06 * float(posmod(x * 7 + y * 13, 3))
				reg.set_pixel(x, y, Color(v * 1.4, v * 0.8, v * 0.6, c.a))
				masc.set_pixel(x, y, Color(1.0, 0.42 + 0.3 * c.g, 0.1, 1.0))
	_tigela_cache = [ImageTexture.create_from_image(reg), ImageTexture.create_from_image(masc)]
	return _tigela_cache

func _rampa(pontos: Array) -> Gradient:
	var g := Gradient.new()
	g.offsets = PackedFloat32Array(pontos.map(func(p): return p[0]))
	g.colors = PackedColorArray(pontos.map(func(p): return p[1]))
	return g

func _aditivo() -> CanvasItemMaterial:
	var m := CanvasItemMaterial.new()
	m.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	return m

func _curva(a: float, b: float) -> Curve:
	var c := Curve.new()
	c.add_point(Vector2(0, a))
	c.add_point(Vector2(1, b))
	return c

func _braseiro(b: Vector2) -> void:
	var boca := b + Vector2(0, -8)
	# tigela sem a chama pintada (a célula do tile some) + fogo animado + carvão piscando
	var cel := Vector2i(int(b.x) / int(sala.tile), int(b.y) / int(sala.tile))
	var canto := Vector2(cel) * float(sala.tile)
	var arte := _tigela_sem_chama()
	if not arte.is_empty():
		var camada = sala.get("_layer")
		if camada is TileMapLayer:
			camada.erase_cell(cel)
		var tig := Sprite2D.new()
		tig.texture = arte[0]
		tig.centered = false
		tig.position = canto
		add_child(tig)
		var carvao := Sprite2D.new()
		carvao.texture = arte[1]
		carvao.centered = false
		carvao.position = canto
		carvao.material = _mat_shader(BRASA_SHADER, {"semente": _rng.randf() * 50.0})
		carvao.z_index = 1
		add_child(carvao)
	var fogo := ColorRect.new()
	fogo.size = Vector2(cfg["fogo_largura"], cfg["fogo_altura"])
	fogo.position = canto + Vector2(sala.tile * 0.5 - fogo.size.x * 0.5, sala.tile * 0.42 - fogo.size.y)
	fogo.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var mf := _mat_shader(FOGO_SHADER, {"semente": _rng.randf() * 100.0, "fps": cfg["fogo_fps"], "res": fogo.size / cfg["fogo_pixel"]})
	fogo.material = mf
	fogo.z_index = 4
	add_child(fogo)
	_mats_fogo.append(mf)
	# brilho aditivo fraco por cima, para a chama clarear o que está atrás
	var miolo := CPUParticles2D.new()
	miolo.texture = _textura_suave("chama", 32, true)
	miolo.material = _aditivo()
	miolo.amount = 4
	miolo.lifetime = 0.5
	miolo.position = boca + Vector2(0, -8)
	miolo.emission_shape = CPUParticles2D.EMISSION_SHAPE_SPHERE
	miolo.emission_sphere_radius = 4.0
	miolo.direction = Vector2(0, -1)
	miolo.spread = 10.0
	miolo.gravity = Vector2(0, -20)
	miolo.initial_velocity_min = 8.0
	miolo.initial_velocity_max = 16.0
	miolo.scale_amount_min = 0.7
	miolo.scale_amount_max = 1.0
	miolo.color_ramp = _rampa([[0.0, Color(1, 0.7, 0.3, 0.0)], [0.3, Color(1, 0.6, 0.2, 0.22)], [1.0, Color(1, 0.4, 0.1, 0.0)]])
	miolo.z_index = 5
	add_child(miolo)
	_fogo.append({"no": miolo, "base": Vector2(0, -20), "fator": 0.08})
	# brasas subindo e indo com o vento
	var brasa := CPUParticles2D.new()
	brasa.texture = _textura_suave("brasa", 8, true)
	brasa.material = _aditivo()
	brasa.amount = int(cfg["fogo_brasas"])
	brasa.lifetime = 2.0
	brasa.randomness = 0.5
	brasa.position = boca + Vector2(0, -10)
	brasa.emission_shape = CPUParticles2D.EMISSION_SHAPE_SPHERE
	brasa.emission_sphere_radius = 8.0
	brasa.direction = Vector2(0, -1)
	brasa.spread = 30.0
	brasa.initial_velocity_min = 30.0
	brasa.initial_velocity_max = 60.0
	brasa.damping_min = 8.0
	brasa.damping_max = 16.0
	brasa.scale_amount_min = 0.5
	brasa.scale_amount_max = 0.85
	brasa.color_ramp = _rampa([[0.0, Color(1, 0.9, 0.5, 1)], [0.6, Color(1, 0.45, 0.1, 0.9)], [1.0, Color(0.6, 0.12, 0.05, 0)]])
	brasa.z_index = 12
	add_child(brasa)
	_fogo.append({"no": brasa, "base": Vector2(0, -12), "fator": 0.55})
	# fumaça escura subindo e entortando com o vento
	var fum := CPUParticles2D.new()
	fum.texture = _textura_suave("fumaca", 64)
	fum.amount = int(cfg["fumaca_qtd"])
	fum.lifetime = 3.4
	fum.randomness = 0.3
	fum.position = boca + Vector2(0, -26)
	fum.emission_shape = CPUParticles2D.EMISSION_SHAPE_SPHERE
	fum.emission_sphere_radius = 6.0
	fum.direction = Vector2(0, -1)
	fum.spread = 10.0
	fum.initial_velocity_min = 16.0
	fum.initial_velocity_max = 24.0
	fum.damping_min = 4.0
	fum.damping_max = 6.0
	fum.angle_min = 0.0
	fum.angle_max = 360.0
	fum.angular_velocity_min = -20.0
	fum.angular_velocity_max = 20.0
	fum.scale_amount_min = 0.5
	fum.scale_amount_max = 0.7
	fum.scale_amount_curve = _curva(0.6, 2.4)
	var a: float = cfg["fumaca_alpha"]
	fum.color_ramp = _rampa([[0.0, Color(0.62, 0.58, 0.55, 0.0)], [0.15, Color(0.58, 0.56, 0.55, a)], [0.6, Color(0.5, 0.5, 0.53, a * 0.6)], [1.0, Color(0.42, 0.43, 0.47, 0.0)]])
	fum.z_index = 13
	add_child(fum)
	_fogo.append({"no": fum, "base": Vector2(0, -3), "fator": 0.32})
	for p in [miolo, brasa, fum]:
		p.preprocess = p.lifetime

# ---------------------------------------------------------------- céu e ar

func _criar_poeira() -> void:
	_poeira = CPUParticles2D.new()
	_poeira.texture = _textura_suave("brasa", 8, true)
	_poeira.amount = int(cfg["poeira_qtd"] * _escala_area)
	_poeira.lifetime = 9.0
	_poeira.preprocess = 9.0
	_poeira.position = _tamanho * 0.5
	_poeira.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	_poeira.emission_rect_extents = _tamanho * 0.48
	_poeira.direction = Vector2(0, -1)
	_poeira.spread = 180.0
	_poeira.initial_velocity_min = 3.0
	_poeira.initial_velocity_max = 9.0
	_poeira.scale_amount_min = 0.2
	_poeira.scale_amount_max = 0.38
	_poeira.color_ramp = _rampa([[0.0, Color(1, 0.94, 0.78, 0)], [0.3, Color(1, 0.94, 0.78, 0.32)], [0.7, Color(1, 0.94, 0.78, 0.32)], [1.0, Color(1, 0.94, 0.78, 0)]])
	_poeira.z_index = 11
	add_child(_poeira)

## Sombra de nuvem (ou névoa rasteira, na cripta): três manchas sobrepostas, levadas pelo vento,
## que dão a volta na sala.
func _criar_nuvens(cor: Color, z: int) -> void:
	var tex := _textura_suave("nuvem", 128)
	for i in int(round(cfg["nuvens_qtd"] * _escala_area)):
		var n := Node2D.new()
		n.z_index = z
		for k in 3:
			var sp := Sprite2D.new()
			sp.texture = tex
			sp.modulate = cor
			var tam := Vector2(_rng.randf_range(380, 560), _rng.randf_range(220, 320))
			sp.scale = tam / 128.0
			sp.position = Vector2(_rng.randf_range(-180, 180), _rng.randf_range(-70, 70))
			n.add_child(sp)
		n.position = Vector2(_rng.randf() * (_tamanho.x + 1000.0) - 500.0, _rng.randf() * _tamanho.y)
		add_child(n)
		_nuvens.append(n)

func _mover_nuvens(delta: float) -> void:
	var v: Vector2 = dir_vento * cfg["nuvem_vel"] * (0.7 + vento * 0.6)
	for n in _nuvens:
		n.position += v * delta
		if n.position.x > _tamanho.x + 520.0:
			n.position = Vector2(-520.0, _rng.randf() * _tamanho.y)
		elif n.position.x < -520.0:
			n.position = Vector2(_tamanho.x + 520.0, _rng.randf() * _tamanho.y)
		if n.position.y > _tamanho.y + 300.0:
			n.position.y = -300.0
		elif n.position.y < -300.0:
			n.position.y = _tamanho.y + 300.0

## Ondas de vento passando pelo gramado: faixas claras e fracas que correm na direção do vento.
func _criar_ondas() -> void:
	var sh := Shader.new()
	sh.code = ONDAS_SHADER
	_ondas = ShaderMaterial.new()
	_ondas.shader = sh
	_ondas.set_shader_parameter("dir", dir_vento)
	_ondas.set_shader_parameter("tamanho", _tamanho)
	_ondas.set_shader_parameter("alpha_max", cfg["ondas_capim_alpha"])
	var r := ColorRect.new()
	r.size = _tamanho
	r.material = _ondas
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	r.z_index = 1
	add_child(r)
