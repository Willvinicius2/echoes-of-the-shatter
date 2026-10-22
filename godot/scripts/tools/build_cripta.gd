# Gera res://scenes/cripta/Cripta.tscn a partir do layout (docs 14_layout_cripta). Coordenadas do doc: X leste, Z norte; no Godot z = -Z_doc.
# godot --headless --path godot --script res://scripts/tools/build_cripta.gd
extends SceneTree

# [x0, z0, x1, z1] em metros (layout do doc)
const SALAS := {
	"r00_atrio": [-12.0, 0.0, 12.0, 24.0], "r01_patrulha_a": [24.0, 0.0, 52.0, 28.0], "r02_caes": [64.0, 0.0, 96.0, 28.0],
	"r03_arauto": [64.0, 40.0, 96.0, 68.0], "r04_patrulha_b": [24.0, 40.0, 52.0, 68.0], "r05_linha_tiro": [-20.0, 40.0, 12.0, 68.0],
	"r06_elite_escudada": [-18.0, 80.0, 10.0, 108.0], "r07_elite_veloz": [22.0, 80.0, 52.0, 110.0], "r08_antecamara": [64.0, 83.0, 88.0, 107.0],
	"r09_arena": [56.0, 119.0, 96.0, 159.0], "s01_nicho": [76.0, -12.0, 88.0, 0.0],
}
const CORREDORES := {
	"c01": [12.0, 10.0, 24.0, 16.0], "c02": [52.0, 10.0, 64.0, 16.0], "c03": [77.0, 28.0, 83.0, 40.0], "c04": [52.0, 51.0, 64.0, 57.0],
	"c05": [12.0, 51.0, 24.0, 57.0], "c06": [-7.0, 68.0, -1.0, 80.0], "c07": [10.0, 91.0, 22.0, 97.0], "c08": [52.0, 91.0, 64.0, 97.0],
	"c09": [73.0, 107.0, 79.0, 119.0], "sa": [-3.0, 24.0, 3.0, 40.0],
}
const ALTURA_PAREDE := 4.5
const ESPESSURA := 1.2

var raiz: Node3D
var mat_piso: ShaderMaterial
var mat_parede: ShaderMaterial
var mat_degrau: ShaderMaterial
var mat_fogo: StandardMaterial3D
var fogo_proc: ParticleProcessMaterial
var fogo_malha: QuadMesh
var braseiro_cena: PackedScene

func _init() -> void:
	raiz = Node3D.new(); raiz.name = "Cripta"
	_materiais()
	var env := Node3D.new(); env.name = "Clima"; raiz.add_child(env)
	_clima(env)
	var pisos := Node3D.new(); pisos.name = "Pisos"; raiz.add_child(pisos)
	var paredes := Node3D.new(); paredes.name = "Paredes"; raiz.add_child(paredes)
	var props := Node3D.new(); props.name = "Props"; raiz.add_child(props)
	var todos := {}
	for k in SALAS: todos[k] = SALAS[k]
	for k in CORREDORES: todos[k] = CORREDORES[k]
	for k in todos:
		_piso(pisos, k, todos[k])
		_paredes(paredes, k, todos[k], todos)
	braseiro_cena = _carregar_cena("res://art/models/SM_Cripta_Braseiro.glb")
	for k in SALAS: _decorar_sala(props, k, SALAS[k])
	for k in CORREDORES:
		var cr: Array = CORREDORES[k]
		var cl := OmniLight3D.new(); cl.name = "LuzCorredor_" + k; cl.position = _p((cr[0] + cr[2]) / 2.0, (cr[1] + cr[3]) / 2.0, 2.6)
		cl.light_color = Color(1.0, 0.6, 0.3); cl.light_energy = 5.0; cl.omni_range = 10.0
		props.add_child(cl)
	_tapetes(props)
	var niveis := Node3D.new(); niveis.name = "Desniveis"; raiz.add_child(niveis)
	for k in SALAS:
		if not k.begins_with("s01"): _escadaria_norte(niveis, "Escadaria_" + k, SALAS[k])
	_tablado(niveis, "Tablado_Arena", 76.0, 146.0, 12.0, 6.0, 0.9, 1)
	_tablado(niveis, "Tablado_Atrio", 0.0, 21.0, 12.0, 5.0, 0.6, 1)
	_tablado(niveis, "Tablado_Antecamara", 76.0, 101.0, 10.0, 4.0, 0.45, 1)
	var cam := Camera3D.new(); cam.name = "CameraEstudio"; cam.fov = 38.0; cam.far = 400.0; cam.current = true
	cam.set_script(load("res://scripts/cripta/CameraEstudio.cs"))
	cam.set("Alvo", Vector3(0, 0, -11))
	raiz.add_child(cam)
	_dono(raiz, raiz)
	var ps := PackedScene.new(); ps.pack(raiz)
	var err := ResourceSaver.save(ps, "res://scenes/cripta/Cripta.tscn")
	print("salvo Cripta.tscn err=", err)
	quit()

func _dono(n: Node, dono: Node) -> void:
	for c in n.get_children():
		c.owner = dono
		if c.scene_file_path == "": _dono(c, dono)

func _carregar_cena(p: String) -> PackedScene:
	if ResourceLoader.exists(p): return load(p) as PackedScene
	return null

func _tex(p: String) -> Texture2D: return load(p) as Texture2D

func _materiais() -> void:
	mat_piso = ShaderMaterial.new(); mat_piso.shader = load("res://art/shaders/cripta_piso.gdshader")
	mat_piso.set_shader_parameter("albedo_tex", _tex("res://art/textures/T_Cripta_Piso.png"))
	mat_piso.set_shader_parameter("normal_tex", _tex("res://art/textures/T_Cripta_Piso_n.png"))
	mat_parede = _pedra_mat(Color(0.36, 0.35, 0.37), 0.28, 0.18, 1)
	mat_degrau = _pedra_mat(Color(0.62, 0.60, 0.58), 0.08, 0.3, 1)
	var g := GradientTexture2D.new(); g.fill = GradientTexture2D.FILL_RADIAL; g.fill_from = Vector2(0.5, 0.5); g.fill_to = Vector2(0.5, 0.0)
	var gr := Gradient.new(); gr.set_color(0, Color(1, 1, 1, 1)); gr.set_color(1, Color(1, 1, 1, 0)); g.gradient = gr; g.width = 64; g.height = 64
	mat_fogo = StandardMaterial3D.new()
	mat_fogo.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED; mat_fogo.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mat_fogo.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA; mat_fogo.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	mat_fogo.vertex_color_use_as_albedo = true; mat_fogo.billboard_keep_scale = true; mat_fogo.albedo_texture = load("res://art/textures/T_Cripta_Chama.png")
	fogo_malha = QuadMesh.new(); fogo_malha.size = Vector2(1.0, 1.7); fogo_malha.material = mat_fogo
	fogo_proc = ParticleProcessMaterial.new()
	fogo_proc.direction = Vector3(0, 1, 0); fogo_proc.spread = 8.0
	fogo_proc.initial_velocity_min = 0.2; fogo_proc.initial_velocity_max = 0.6
	fogo_proc.gravity = Vector3(0, 0.9, 0)
	fogo_proc.scale_min = 0.6; fogo_proc.scale_max = 1.2
	fogo_proc.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE; fogo_proc.emission_sphere_radius = 0.22
	var rampa := Gradient.new()
	rampa.set_color(0, Color(1.0, 0.85, 0.35, 0.9)); rampa.set_color(1, Color(0.9, 0.12, 0.02, 0.0))
	rampa.add_point(0.45, Color(1.0, 0.45, 0.08, 0.6))
	var rt := GradientTexture1D.new(); rt.gradient = rampa
	fogo_proc.color_ramp = rt
	var curva := Curve.new(); curva.add_point(Vector2(0, 0.7)); curva.add_point(Vector2(0.3, 1.0)); curva.add_point(Vector2(1, 0.1))
	var ct := CurveTexture.new(); ct.curve = curva
	fogo_proc.scale_curve = ct

func _clima(pai: Node3D) -> void:
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR; e.background_color = Color(0.015, 0.02, 0.04)
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR; e.ambient_light_color = Color(0.20, 0.25, 0.38); e.ambient_light_energy = 0.5
	e.tonemap_mode = Environment.TONE_MAPPER_FILMIC; e.tonemap_exposure = 1.15
	e.glow_enabled = true; e.glow_intensity = 1.0; e.glow_bloom = 0.12; e.glow_hdr_threshold = 0.9
	e.ssr_enabled = true; e.ssr_max_steps = 64; e.ssr_fade_in = 0.15; e.ssr_fade_out = 2.0; e.ssr_depth_tolerance = 0.3
	e.ssil_enabled = true; e.ssil_intensity = 0.8
	e.ssao_enabled = true; e.ssao_intensity = 2.0; e.ssao_radius = 1.5
	e.fog_enabled = true; e.fog_light_color = Color(0.09, 0.13, 0.24); e.fog_density = 0.003
	e.volumetric_fog_enabled = true; e.volumetric_fog_density = 0.006; e.volumetric_fog_albedo = Color(0.45, 0.55, 0.8)
	e.volumetric_fog_emission = Color(0.02, 0.03, 0.06); e.volumetric_fog_length = 60.0; e.volumetric_fog_anisotropy = 0.5
	e.adjustment_enabled = true; e.adjustment_saturation = 1.08; e.adjustment_contrast = 1.06
	var we := WorldEnvironment.new(); we.name = "Ambiente"; we.environment = e; pai.add_child(we)
	var lua := DirectionalLight3D.new(); lua.name = "LuarFrio"; lua.light_color = Color(0.55, 0.65, 1.0); lua.light_energy = 0.28
	lua.rotation_degrees = Vector3(-62, -35, 0); lua.shadow_enabled = true; lua.directional_shadow_max_distance = 90.0
	pai.add_child(lua)

func _p(x: float, z: float, y: float = 0.0) -> Vector3: return Vector3(x, y, -z)

func _caixa(pai: Node3D, nome: String, centro: Vector3, tam: Vector3, mat: Material) -> void:
	var sb := StaticBody3D.new(); sb.name = nome; sb.position = centro
	var mi := MeshInstance3D.new(); mi.name = "Malha"
	var bm := BoxMesh.new(); bm.size = tam; bm.material = mat; mi.mesh = bm
	var cs := CollisionShape3D.new(); cs.name = "Colisao"
	var bs := BoxShape3D.new(); bs.size = tam; cs.shape = bs
	sb.add_child(mi); sb.add_child(cs); pai.add_child(sb)

func _piso(pai: Node3D, nome: String, r: Array) -> void:
	var w: float = r[2] - r[0]; var d: float = r[3] - r[1]
	_caixa(pai, "Piso_" + nome, _p((r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0, -0.2), Vector3(w, 0.4, d), mat_piso)

# intervalos ocupados por aberturas numa aresta; eixo 0 = aresta vertical (x fixo, varia z), 1 = horizontal (z fixo, varia x)
func _aberturas(nome: String, r: Array, eixo: int, pos: float, todos: Dictionary) -> Array:
	var res: Array = []
	var lo: float = r[1] if eixo == 0 else r[0]
	var hi: float = r[3] if eixo == 0 else r[2]
	for k in todos:
		if k == nome: continue
		var o: Array = todos[k]
		var toca := false
		var a: float
		var b: float
		if eixo == 0:
			toca = absf(o[0] - pos) < 0.01 or absf(o[2] - pos) < 0.01
			a = maxf(lo, o[1]); b = minf(hi, o[3])
		else:
			toca = absf(o[1] - pos) < 0.01 or absf(o[3] - pos) < 0.01
			a = maxf(lo, o[0]); b = minf(hi, o[2])
		if toca and b - a > 0.5: res.append([a, b])
	res.sort_custom(func(p, q): return p[0] < q[0])
	return res

func _paredes(pai: Node3D, nome: String, r: Array, todos: Dictionary) -> void:
	for lado in 4:
		var eixo := 0 if lado < 2 else 1
		var pos: float = r[[0, 2, 1, 3][lado]]
		var lo: float = r[1] if eixo == 0 else r[0]
		var hi: float = r[3] if eixo == 0 else r[2]
		var ab := _aberturas(nome, r, eixo, pos, todos)
		var cursor := lo
		var segs: Array = []
		for a in ab:
			if a[0] > cursor + 0.01: segs.append([cursor, a[0]])
			cursor = maxf(cursor, a[1])
		if hi > cursor + 0.01: segs.append([cursor, hi])
		var dir := -1.0 if (lado == 0 or lado == 2) else 1.0
		var i := 0
		for s in segs:
			var comp: float = s[1] - s[0]
			var meio: float = (s[0] + s[1]) / 2.0
			var off: float = pos + dir * ESPESSURA / 2.0
			var c: Vector3
			var tam: Vector3
			if eixo == 0:
				c = _p(off, meio, ALTURA_PAREDE / 2.0); tam = Vector3(ESPESSURA, ALTURA_PAREDE, comp)
			else:
				comp += ESPESSURA * 2.0
				c = _p(meio, off, ALTURA_PAREDE / 2.0); tam = Vector3(comp, ALTURA_PAREDE, ESPESSURA)
			_caixa(pai, "Parede_%s_%d_%d" % [nome, lado, i], c, tam, mat_parede)
			i += 1

func _decorar_sala(pai: Node3D, nome: String, r: Array) -> void:
	var w: float = r[2] - r[0]
	var d: float = r[3] - r[1]
	var cx: float = (r[0] + r[2]) / 2.0
	var cz: float = (r[1] + r[3]) / 2.0
	var lado := minf(w, d) * 0.55
	var dec := Decal.new(); dec.name = "Runas_" + nome; dec.size = Vector3(lado, 2.0, lado); dec.position = _p(cx, cz, 0.0)
	dec.texture_albedo = _tex("res://art/textures/T_Cripta_Runas.png"); dec.modulate = Color(0.8, 0.75, 0.65, 0.85)
	pai.add_child(dec)
	var rng := RandomNumberGenerator.new(); rng.seed = hash(nome)
	var nicho := nome.begins_with("s01")
	var cantos := [[r[0], r[1], 1.0, 1.0], [r[2], r[1], -1.0, 1.0], [r[0], r[3], 1.0, -1.0], [r[2], r[3], -1.0, -1.0]]
	var i := 0
	for c in cantos:
		var sx: float = c[2]
		var sz: float = c[3]
		if nicho:
			_braseiro(pai, "Braseiro_%s_%d" % [nome, i], c[0] + sx * 2.2, c[1] + sz * 2.2)
			if i == 2: _modulo(pai, "Estatua_%s" % nome, "SM_Cripta_Estatua", c[0] + sx * 1.6, c[1] + sz * 1.6, cx, cz)
			i += 1
			continue
		_modulo(pai, "Pilar_%s_%d" % [nome, i], "SM_Cripta_Pilar", c[0] + sx * 2.0, c[1] + sz * 2.0, cx, cz)
		_braseiro(pai, "Braseiro_%s_%d" % [nome, i], c[0] + sx * 4.6, c[1] + sz * 4.6)
		_modulo(pai, "Velas_%s_%d" % [nome, i], "SM_Cripta_Velas", c[0] + sx * 3.3, c[1] + sz * 1.0, cx, cz, rng.randf() * 360.0)
		_modulo(pai, "Velas_%s_%db" % [nome, i], "SM_Cripta_Velas", c[0] + sx * 1.0, c[1] + sz * 3.4, cx, cz, rng.randf() * 360.0)
		_modulo(pai, "Estandarte_%s_%d" % [nome, i], "SM_Cripta_Estandarte", c[0] + sx * 6.2, c[1] + sz * 1.0, cx, cz)
		_modulo(pai, "Entulho_%s_%d" % [nome, i], "SM_Cripta_Entulho", c[0] + sx * (5.5 + rng.randf() * 2.0), c[1] + sz * (3.0 + rng.randf() * 3.0), cx, cz, rng.randf() * 360.0)
		i += 1
	if not nicho and (w >= 28.0 or d >= 28.0):
		var k := 0
		for t in [0.3, 0.7]:
			_braseiro(pai, "BraseiroLado_%s_%d" % [nome, k], r[0] + w * t, r[1] + 3.2); k += 1
			_braseiro(pai, "BraseiroLado_%s_%d" % [nome, k], r[0] + w * t, r[3] - 3.2); k += 1
		if w >= 36.0 or d >= 36.0:
			_braseiro(pai, "BraseiroLado_%s_%d" % [nome, k], r[0] + 3.2, cz); k += 1
			_braseiro(pai, "BraseiroLado_%s_%d" % [nome, k], r[2] - 3.2, cz)
	if nome == "r00_atrio": _modulo(pai, "Corrente_Atrio", "SM_Cripta_ColunaCorrente", cx, 6.0, cx, cz + 50.0)
	if nome == "r09_arena": _modulo(pai, "Corrente_Arena", "SM_Cripta_ColunaCorrente", cx, 123.0, cx, cz + 50.0)

func _modulo(pai: Node3D, nome: String, modulo: String, x: float, z: float, alvo_x: float, alvo_z: float, yaw_extra: float = 0.0) -> void:
	var cena := _carregar_cena("res://art/models/%s.glb" % modulo)
	if cena == null: return
	var n := cena.instantiate() as Node3D; n.name = nome; n.position = _p(x, z)
	var dir := Vector3(alvo_x - x, 0.0, -(alvo_z - z))
	if dir.length() > 0.01: n.basis = Basis.looking_at(dir.normalized(), Vector3.UP)
	if yaw_extra != 0.0: n.rotate_y(deg_to_rad(yaw_extra))
	pai.add_child(n)

func _braseiro(pai: Node3D, nome: String, x: float, z: float) -> void:
	var n := Node3D.new(); n.name = nome; n.position = _p(x, z)
	if braseiro_cena:
		var m := braseiro_cena.instantiate(); m.name = "Modelo"; n.add_child(m)
	var luz := OmniLight3D.new(); luz.name = "Luz"; luz.position = Vector3(0, 1.9, 0)
	luz.light_color = Color(1.0, 0.62, 0.25); luz.light_energy = 8.0; luz.omni_range = 15.0; luz.omni_attenuation = 1.6
	luz.set_script(load("res://scripts/cripta/BraseiroLuz.cs"))
	n.add_child(luz)
	var ch := Node3D.new(); ch.name = "Chama"; ch.position = Vector3(0, 1.32, 0)
	var tam := [Vector2(1.15, 1.75), Vector2(0.8, 1.25), Vector2(0.55, 0.95)]
	for k in 3:
		var qm := QuadMesh.new(); qm.size = tam[k]; qm.center_offset = Vector3(0, tam[k].y * 0.5, 0)
		var sm := ShaderMaterial.new(); sm.shader = load("res://art/shaders/chama.gdshader")
		sm.set_shader_parameter("seed", float(hash(nome) % 97) + k * 13.0); sm.set_shader_parameter("speed", 1.2 + 0.5 * k)
		qm.material = sm
		var mi := MeshInstance3D.new(); mi.name = "Cartao%d" % k; mi.mesh = qm; mi.position = Vector3(0.0, 0.0, 0.02 * k)
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		ch.add_child(mi)
	n.add_child(ch)
	_particulas_braseiro(n)
	pai.add_child(n)

var _tex_ponto: GradientTexture2D
var _faisca_malha: QuadMesh
var _faisca_proc: ParticleProcessMaterial
var _fumaca_malha: QuadMesh
var _fumaca_proc: ParticleProcessMaterial

# Faíscas e brasas subindo, mais fumaça leve: partículas compartilhadas por todos os braseiros (recursos criados uma vez).
func _particulas_braseiro(n: Node3D) -> void:
	if _tex_ponto == null:
		_tex_ponto = GradientTexture2D.new(); _tex_ponto.fill = GradientTexture2D.FILL_RADIAL
		_tex_ponto.fill_from = Vector2(0.5, 0.5); _tex_ponto.fill_to = Vector2(0.5, 0.0); _tex_ponto.width = 64; _tex_ponto.height = 64
		var gp := Gradient.new(); gp.set_color(0, Color(1, 1, 1, 1)); gp.set_color(1, Color(1, 1, 1, 0)); _tex_ponto.gradient = gp
		# faíscas: pontos amarelos que esfriam para laranja e somem
		var mf := StandardMaterial3D.new()
		mf.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED; mf.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
		mf.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA; mf.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
		mf.vertex_color_use_as_albedo = true; mf.albedo_texture = _tex_ponto
		_faisca_malha = QuadMesh.new(); _faisca_malha.size = Vector2(1, 1); _faisca_malha.material = mf
		_faisca_proc = ParticleProcessMaterial.new()
		_faisca_proc.direction = Vector3(0, 1, 0); _faisca_proc.spread = 30.0
		_faisca_proc.initial_velocity_min = 0.7; _faisca_proc.initial_velocity_max = 1.8
		_faisca_proc.gravity = Vector3(0, 0.35, 0); _faisca_proc.scale_min = 0.025; _faisca_proc.scale_max = 0.06
		_faisca_proc.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE; _faisca_proc.emission_sphere_radius = 0.32
		_faisca_proc.turbulence_enabled = true; _faisca_proc.turbulence_noise_strength = 0.6; _faisca_proc.turbulence_noise_scale = 2.0
		var rf := Gradient.new(); rf.set_color(0, Color(1.0, 0.9, 0.45, 1.0)); rf.set_color(1, Color(1.0, 0.25, 0.03, 0.0)); rf.add_point(0.4, Color(1.0, 0.55, 0.12, 0.9))
		var rft := GradientTexture1D.new(); rft.gradient = rf; _faisca_proc.color_ramp = rft
		# fumaça: nuvens escuras e suaves que sobem devagar e crescem
		var mu := StandardMaterial3D.new()
		mu.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED; mu.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		mu.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES; mu.vertex_color_use_as_albedo = true; mu.albedo_texture = _tex_ponto
		_fumaca_malha = QuadMesh.new(); _fumaca_malha.size = Vector2(1, 1); _fumaca_malha.material = mu
		_fumaca_proc = ParticleProcessMaterial.new()
		_fumaca_proc.direction = Vector3(0, 1, 0); _fumaca_proc.spread = 12.0
		_fumaca_proc.initial_velocity_min = 0.25; _fumaca_proc.initial_velocity_max = 0.5
		_fumaca_proc.gravity = Vector3(0, 0.15, 0); _fumaca_proc.scale_min = 0.5; _fumaca_proc.scale_max = 0.9
		_fumaca_proc.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE; _fumaca_proc.emission_sphere_radius = 0.25
		_fumaca_proc.turbulence_enabled = true; _fumaca_proc.turbulence_noise_strength = 0.3
		var ru := Gradient.new(); ru.set_color(0, Color(0.10, 0.09, 0.09, 0.0)); ru.set_color(1, Color(0.06, 0.06, 0.07, 0.0)); ru.add_point(0.3, Color(0.10, 0.09, 0.09, 0.16))
		var rut := GradientTexture1D.new(); rut.gradient = ru; _fumaca_proc.color_ramp = rut
		var cu := Curve.new(); cu.add_point(Vector2(0, 0.4)); cu.add_point(Vector2(1, 1.6))
		var cut := CurveTexture.new(); cut.curve = cu; _fumaca_proc.scale_curve = cut
	var f := GPUParticles3D.new(); f.name = "Faiscas"; f.amount = 20; f.lifetime = 1.8; f.local_coords = false
	f.position = Vector3(0, 1.4, 0); f.process_material = _faisca_proc; f.draw_pass_1 = _faisca_malha
	f.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF; f.randomness = 1.0
	n.add_child(f)
	var u := GPUParticles3D.new(); u.name = "Fumaca"; u.amount = 8; u.lifetime = 3.6; u.local_coords = false
	u.position = Vector3(0, 2.1, 0); u.process_material = _fumaca_proc; u.draw_pass_1 = _fumaca_malha
	u.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF; u.randomness = 1.0
	n.add_child(u)

func _tapete(pai: Node3D, nome: String, x: float, z: float, larg: float, comp: float) -> void:
	var m := MeshInstance3D.new(); m.name = nome
	var pm := PlaneMesh.new(); pm.size = Vector2(larg, comp)
	var mt := StandardMaterial3D.new()
	mt.albedo_texture = _tex("res://art/textures/T_Cripta_Tapete.png"); mt.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
	mt.roughness = 0.9; mt.albedo_color = Color(1.9, 1.5, 1.5)
	pm.material = mt; m.mesh = pm; m.position = _p(x, z, 0.02)
	pai.add_child(m)

func _tapetes(pai: Node3D) -> void:
	_tapete(pai, "Tapete_Atrio", 0.0, 12.0, 4.0, 23.0)
	_tapete(pai, "Tapete_C09", 76.0, 113.0, 3.0, 12.0)
	_tapete(pai, "Tapete_Arena", 76.0, 139.0, 5.0, 38.0)

# tablado elevado com 3 degraus voltados para -Z do doc (sul); (x,z) = centro do topo
func _tablado(pai: Node3D, nome: String, x: float, z: float, larg: float, prof: float, altura: float, _d: int) -> void:
	_caixa(pai, nome, _p(x, z, altura / 2.0), Vector3(larg, altura, prof), mat_degrau)
	_degraus(pai, nome, x, z - prof / 2.0, larg, altura, 3, -1.0)

# degraus descendo para o sul (-1) a partir da aresta z_borda; cada degrau tem 0.5 m de profundidade
func _degraus(pai: Node3D, nome: String, x: float, z_borda: float, larg: float, altura: float, n: int, dir: float) -> void:
	for i in n:
		var hh: float = altura * float(n - i) / float(n + 1)
		_caixa(pai, "%s_Degrau%d" % [nome, i], _p(x, z_borda + dir * (0.25 + 0.5 * i), hh / 2.0), Vector3(larg, hh, 0.5), mat_degrau)

# plataforma elevada junto à parede norte, em duas metades, com dois degraus voltados ao centro da sala
func _escadaria_norte(pai: Node3D, nome: String, r: Array) -> void:
	var cx: float = (r[0] + r[2]) / 2.0
	for lado in [-1.0, 1.0]:
		var xa: float = (r[0] + 6.0) if lado < 0 else (cx + 5.0)
		var xb: float = (cx - 5.0) if lado < 0 else (r[2] - 6.0)
		var larg := xb - xa
		var prof := 2.6
		var zc: float = r[3] - prof / 2.0
		_caixa(pai, "%s_%d" % [nome, int(lado)], _p((xa + xb) / 2.0, zc, 0.35), Vector3(larg, 0.7, prof), mat_degrau)
		_degraus(pai, "%s_%d" % [nome, int(lado)], (xa + xb) / 2.0, r[3] - prof, larg, 0.7, 2, -1.0)

func _pedra_mat(cor: Color, musgo: float, escala: float, mundo: int) -> ShaderMaterial:
	var m := ShaderMaterial.new(); m.shader = load("res://art/shaders/cripta_pedra.gdshader")
	m.set_shader_parameter("albedo_tex", _tex("res://art/textures/T_Cripta_Pedra.png"))
	m.set_shader_parameter("tint", cor); m.set_shader_parameter("moss_amount", musgo)
	m.set_shader_parameter("tex_scale", escala); m.set_shader_parameter("world_space", float(mundo))
	return m
