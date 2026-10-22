# Gera o terreno orgânico da Cripta, os props e a cena res://scenes/cripta/Cripta.tscn.
# godot --headless --path godot --script res://scripts/tools/build_terreno.gd
# Substitui o antigo build_cripta.gd (salas quadradas). Coordenadas "doc": X leste, Z norte; na cena z = -Z_doc.
extends SceneTree

const T := preload("res://scripts/terreno/terreno_cripta.gd")
const X0 := -24.0
const Z0 := -20.0
const NX := 256          # células em X (passo de 0.5 m)
const NZ := 372
const PASSO := 0.5
const BLOCO := 64        # células por bloco (32 m)
const MODELOS := "res://art/models/SM_Cripta_%s.glb"

var mat_piso: ShaderMaterial
var mat_terreno: ShaderMaterial
var mat_degrau: ShaderMaterial
var cenas := {}
var rng := RandomNumberGenerator.new()
var contagem := {}

func _init() -> void:
	rng.seed = 20261022
	_materiais()
	var raiz := Node3D.new(); raiz.name = "Cripta"
	_clima(raiz)
	var terreno := _terreno()
	raiz.add_child(terreno)
	var props := Node3D.new(); props.name = "Props"; raiz.add_child(props)
	_escadas(raiz)
	_zonas_proibidas()
	_pracas(props)
	for nome in T.SALAS: _decorar_sala(props, nome)
	_corredores(props)
	_pocas(props)
	_marcos(raiz)
	var cam := Camera3D.new(); cam.name = "CameraEstudio"; cam.fov = 38.0; cam.far = 500.0; cam.current = true
	cam.set_script(load("res://scripts/cripta/camera_estudio.gd"))
	cam.set("Alvo", Vector3(0, 0, -11))
	raiz.add_child(cam)
	_dono(raiz, raiz)
	var ps := PackedScene.new(); ps.pack(raiz)
	print("Cripta.tscn err=", ResourceSaver.save(ps, "res://scenes/cripta/Cripta.tscn"), " props=", contagem)
	quit()

func _dono(n: Node, dono: Node) -> void:
	for c in n.get_children():
		c.owner = dono
		if c.scene_file_path == "": _dono(c, dono)

func _tex(p: String) -> Texture2D: return load(p) as Texture2D

func _materiais() -> void:
	mat_piso = ShaderMaterial.new(); mat_piso.shader = load("res://art/shaders/cripta_piso.gdshader")
	mat_piso.set_shader_parameter("albedo_tex", _tex("res://art/textures/T_Cripta_Piso.png"))
	mat_piso.set_shader_parameter("normal_tex", _tex("res://art/textures/T_Cripta_Piso_n.png"))
	mat_terreno = ShaderMaterial.new(); mat_terreno.shader = load("res://art/shaders/cripta_terreno.gdshader")
	mat_terreno.set_shader_parameter("piso_tex", _tex("res://art/textures/T_Cripta_Piso.png"))
	mat_terreno.set_shader_parameter("piso_normal", _tex("res://art/textures/T_Cripta_Piso_n.png"))
	mat_terreno.set_shader_parameter("pedra_tex", _tex("res://art/textures/T_Cripta_Pedra.png"))
	mat_degrau = _pedra_mat(Color(0.62, 0.60, 0.58), 0.08, 0.3)

func _pedra_mat(cor: Color, musgo: float, escala: float) -> ShaderMaterial:
	var m := ShaderMaterial.new(); m.shader = load("res://art/shaders/cripta_pedra.gdshader")
	m.set_shader_parameter("albedo_tex", _tex("res://art/textures/T_Cripta_Pedra.png"))
	m.set_shader_parameter("tint", cor); m.set_shader_parameter("moss_amount", musgo)
	m.set_shader_parameter("tex_scale", escala); m.set_shader_parameter("world_space", 1.0)
	return m

func _clima(pai: Node3D) -> void:
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR; e.background_color = Color(0.015, 0.02, 0.04)
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR; e.ambient_light_color = Color(0.20, 0.25, 0.38); e.ambient_light_energy = 0.55
	e.tonemap_mode = Environment.TONE_MAPPER_FILMIC; e.tonemap_exposure = 1.15
	e.glow_enabled = true; e.glow_intensity = 0.3; e.glow_bloom = 0.05; e.glow_hdr_threshold = 1.3
	e.ssr_enabled = true; e.ssr_max_steps = 64; e.ssr_fade_in = 0.15; e.ssr_fade_out = 2.0; e.ssr_depth_tolerance = 0.3
	e.ssil_enabled = true; e.ssil_intensity = 0.8
	e.ssao_enabled = true; e.ssao_intensity = 2.0; e.ssao_radius = 1.5
	e.fog_enabled = true; e.fog_light_color = Color(0.09, 0.13, 0.24); e.fog_density = 0.003
	e.volumetric_fog_enabled = true; e.volumetric_fog_density = 0.006; e.volumetric_fog_albedo = Color(0.45, 0.55, 0.8)
	e.volumetric_fog_emission = Color(0.02, 0.03, 0.06); e.volumetric_fog_length = 60.0; e.volumetric_fog_anisotropy = 0.5
	e.adjustment_enabled = true; e.adjustment_saturation = 1.08; e.adjustment_contrast = 1.06
	var we := WorldEnvironment.new(); we.name = "Ambiente"; we.environment = e; we.set_script(load("res://scripts/cripta/clima_andar.gd")); pai.add_child(we)
	var lua := DirectionalLight3D.new(); lua.name = "LuarFrio"; lua.light_color = Color(0.55, 0.65, 1.0); lua.light_energy = 0.5
	lua.rotation_degrees = Vector3(-62, -35, 0); lua.shadow_enabled = true; lua.directional_shadow_max_distance = 90.0
	pai.add_child(lua)

# ------------------------------------------------------------------ terreno
func _terreno() -> Node3D:
	var nv := (NX + 1) * (NZ + 1)
	var alt := PackedFloat32Array(); alt.resize(nv)
	var sd := PackedFloat32Array(); sd.resize(nv)
	for j in NZ + 1:
		var z := Z0 + j * PASSO
		for i in NX + 1:
			var x := X0 + i * PASSO
			var k := j * (NX + 1) + i
			var s := T.sdf(x, z)
			sd[k] = s
			alt[k] = T.altura(x, z)
	var raiz := Node3D.new(); raiz.name = "Terreno"
	for bz in range(0, NZ, BLOCO):
		for bx in range(0, NX, BLOCO):
			var no := _bloco(bx, bz, mini(bx + BLOCO, NX), mini(bz + BLOCO, NZ), alt, sd)
			if no: raiz.add_child(no)
	var ps := PackedScene.new()
	_dono(raiz, raiz)
	ps.pack(raiz)
	DirAccess.make_dir_recursive_absolute("res://art/terreno")
	print("terreno.scn err=", ResourceSaver.save(ps, "res://art/terreno/terreno_cripta.scn"))
	raiz.queue_free()
	var inst := (load("res://art/terreno/terreno_cripta.scn") as PackedScene).instantiate()
	inst.name = "Terreno"
	return inst

func _bloco(i0: int, j0: int, i1: int, j1: int, alt: PackedFloat32Array, sd: PackedFloat32Array) -> Node3D:
	var w := NX + 1
	var nxl := i1 - i0 + 1
	var nzl := j1 - j0 + 1
	var vs := PackedVector3Array(); vs.resize(nxl * nzl)
	var ns := PackedVector3Array(); ns.resize(nxl * nzl)
	var cs_ := PackedColorArray(); cs_.resize(nxl * nzl)
	for j in nzl:
		for i in nxl:
			var gi := i0 + i
			var gj := j0 + j
			var k := gj * w + gi
			var x := X0 + gi * PASSO
			var z := Z0 + gj * PASSO
			vs[j * nxl + i] = Vector3(x, alt[k], -z)
			cs_[j * nxl + i] = Color(clampf(sd[k] / 2.5, 0.0, 1.0), 0, 0, 1)
			var hl := alt[gj * w + maxi(gi - 1, 0)]; var hr := alt[gj * w + mini(gi + 1, NX)]
			var hd := alt[maxi(gj - 1, 0) * w + gi]; var hu := alt[mini(gj + 1, NZ) * w + gi]
			# +Z doc = -Z Godot: o gradiente em z inverte de sinal
			ns[j * nxl + i] = Vector3(-(hr - hl), 2.0 * PASSO, (hu - hd)).normalized()
	var idx := PackedInt32Array()
	for j in nzl - 1:
		for i in nxl - 1:
			var a := j * nxl + i; var b := a + 1; var c := a + nxl; var d := c + 1
			# horário visto de cima (+Y) no Godot
			idx.append_array(PackedInt32Array([a, c, b, b, c, d]))
	var malha := ArrayMesh.new()
	var arr := []; arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = vs; arr[Mesh.ARRAY_NORMAL] = ns; arr[Mesh.ARRAY_COLOR] = cs_; arr[Mesh.ARRAY_INDEX] = idx
	malha.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	malha.surface_set_material(0, mat_terreno)
	var corpo := StaticBody3D.new(); corpo.name = "Bloco_%d_%d" % [i0 / BLOCO, j0 / BLOCO]
	var mi := MeshInstance3D.new(); mi.name = "Malha"; mi.mesh = malha
	var cs := CollisionShape3D.new(); cs.name = "Colisao"; cs.shape = malha.create_trimesh_shape()
	corpo.add_child(mi); corpo.add_child(cs)
	return corpo

# ------------------------------------------------------------------ utilitários de cena
func _p(x: float, z: float, dy: float = 0.0) -> Vector3: return Vector3(x, T.chao(x, z) + dy, -z)

func _glb(nome: String) -> PackedScene:
	if not cenas.has(nome): cenas[nome] = load(MODELOS % nome) as PackedScene
	return cenas[nome]

# escala uniforme de montagem (guia docs/arte/24_direcao_visual_cripta.md, seção 2) e raio da base para assentar no chão
const ESCALAS := {"Pilar": 0.70, "Braseiro": 0.75, "Estandarte": 0.90, "Estatua": 0.80, "ColunaCorrente": 0.90, "Entulho": 0.60, "Tapete": 0.65, "Velas": 1.0, "Piso": 1.0, "Tapete_Grande": 1.0}
const RAIOS := {"Pilar": 1.2, "Braseiro": 0.6, "Estandarte": 0.5, "Estatua": 0.7, "ColunaCorrente": 1.2, "Entulho": 0.8, "Velas": 0.3}

func _base_y(x: float, z: float, r: float) -> float:
	var y := T.chao(x, z)
	for d in [Vector2(r, 0), Vector2(-r, 0), Vector2(0, r), Vector2(0, -r)]: y = minf(y, T.chao(x + d.x, z + d.y))
	return y

func _inst(pai: Node3D, nome: String, modelo: String, x: float, z: float, yaw: float, dy: float = 0.0, y_abs: float = NAN) -> Node3D:
	var cena := _glb(modelo)
	if cena == null: return null
	var n := cena.instantiate() as Node3D; n.name = nome
	var esc: float = float(ESCALAS.get(modelo, 1.0))
	if esc != 1.0 and modelo != "Tapete": esc *= rng.randf_range(0.93, 1.07)   # variação de ±7%, menos tapete
	n.position = _p(x, z, dy)
	n.position.y = _base_y(x, z, float(RAIOS.get(modelo, 0.0))) + dy - 0.03 if RAIOS.has(modelo) else n.position.y
	if not is_nan(y_abs): n.position.y = y_abs
	n.scale = Vector3.ONE * esc
	n.rotation.y = yaw
	pai.add_child(n)
	_colisor(n, modelo)
	contagem[modelo] = int(contagem.get(modelo, 0)) + 1
	return n

# yaw para o -Z local (frente do módulo) apontar do ponto (x,z) ao alvo (ax,az), tudo em doc
func _yaw_para(x: float, z: float, ax: float, az: float) -> float:
	var d := Vector3(ax - x, 0.0, -(az - z))
	return Basis.looking_at(d.normalized(), Vector3.UP).get_euler().y

func _grupo(pai: Node3D, nome: String) -> Node3D:
	var g := pai.get_node_or_null(nome) as Node3D
	if g == null:
		g = Node3D.new(); g.name = nome; pai.add_child(g)
	return g

# ------------------------------------------------------------------ escadarias (placeholder)
func _escadas(raiz: Node3D) -> void:
	var gp := Node3D.new(); gp.name = "Escadarias"; raiz.add_child(gp)
	for k in T.ESCADAS:
		var e: Dictionary = T.ESCADAS[k]
		var t: Array = e["topo"]; var f: Array = e["fundo"]
		var topo := Vector3(t[0], T.chao(t[0], t[1]) + 0.12, -t[1])
		var fundo := Vector3(f[0], T.chao(f[0], f[1]) + 0.12, -f[1])
		var ancora := Marker3D.new(); ancora.name = "Ancora_Escadaria_" + k
		ancora.position = topo
		var dir := fundo - topo
		var comp := Vector2(dir.x, dir.z).length()
		var queda := topo.y - fundo.y
		ancora.rotation.y = Basis.looking_at(Vector3(dir.x, 0, dir.z).normalized(), Vector3.UP).get_euler().y
		ancora.set_meta("comprimento", comp); ancora.set_meta("queda", queda); ancora.set_meta("largura", e["largura"]); ancora.set_meta("andar_topo", e["andar"])
		gp.add_child(ancora)
		# colisão para o jogador: rampa lisa pela ponta dos degraus (sem afundar na terra, sem tropeçar em 22 degraus)
		var rampa := StaticBody3D.new(); rampa.name = "ColisaoRampa"; rampa.collision_layer = 1; rampa.collision_mask = 0
		var rs := CollisionShape3D.new(); rs.name = "Forma"
		var rb := BoxShape3D.new(); rb.size = Vector3(float(e["largura"]) + 0.6, 0.2, Vector2(comp, queda).length() + 0.8); rs.shape = rb
		rampa.add_child(rs)
		rampa.position = Vector3(0, -queda * 0.5 - 0.1, -comp * 0.5); rampa.rotation.x = -atan2(queda, comp)
		ancora.add_child(rampa)
		# glb aprovado da escadaria (pivô no nível do patamar, desce para -Z; 7,04 m de rampa, 3,96 m de queda); a colisão é a rampa acima
		var escada := _glb("Escadaria")
		if escada != null:
			var g := escada.instantiate() as Node3D; g.name = "Escadaria"
			g.position = Vector3(0, -0.12, 0); g.scale = Vector3(1.0, queda / 3.96, comp / 7.04)
			ancora.add_child(g)
			continue
		# sem o glb: placeholder de caixas (frente local = -Z desce)
		var ph := Node3D.new(); ph.name = "Placeholder"; ancora.add_child(ph)
		var n := 22
		var larg: float = e["largura"]
		for i in n:
			var topo_y := -queda * (i + 0.5) / n
			var base_y := -queda - 0.5
			var alt := topo_y - base_y
			_caixa(ph, "Degrau%d" % i, Vector3(0, base_y + alt * 0.5, -(i + 0.5) * comp / n), Vector3(larg, alt, comp / n + 0.02), mat_degrau)
		for lado in [-1.0, 1.0]:
			var off: float = lado * (larg * 0.5 + 0.08)
			var cx := off
			var comp3 := Vector3(0, -queda, -comp)
			var corr := MeshInstance3D.new(); corr.name = "Corrimao_%d" % int(lado)
			var bm := BoxMesh.new(); bm.size = Vector3(0.08, 0.08, comp3.length()); bm.material = mat_degrau
			corr.mesh = bm
			corr.transform = Transform3D(Basis.looking_at(comp3.normalized(), Vector3.UP), Vector3(cx, 0.9 + comp3.y * 0.5, comp3.z * 0.5))
			ph.add_child(corr)
			for m in 5:
				var tt := m / 4.0
				_caixa(ph, "Poste_%d_%d" % [int(lado), m], Vector3(cx, 0.45 - queda * tt, -comp * tt), Vector3(0.1, 0.9, 0.1), mat_degrau)

func _caixa(pai: Node3D, nome: String, centro: Vector3, tam: Vector3, mat: Material) -> MeshInstance3D:
	var mi := MeshInstance3D.new(); mi.name = nome; mi.position = centro
	var bm := BoxMesh.new(); bm.size = tam; bm.material = mat; mi.mesh = bm
	pai.add_child(mi)
	return mi

# ------------------------------------------------------------------ regras de composição (docs/arte/24, seção 5)
# Cada peça só entra se tiver motivo e espaço: nada em cima de tapete, na boca de corredor/escada ou dentro de outra peça.
var ocupados: Array = []      # Vector3(x, z, raio) em doc
var proibidos: Array = []     # Vector3(x, z, raio): bocas de corredor, escadas, ponto inicial
var tapetes: Array = []       # [cx, cz, meia_x, meia_z]

func _livre(x: float, z: float, r: float) -> bool:
	for o in ocupados:
		if Vector2(x - o.x, z - o.y).length() < r + o.z: return false
	for p in proibidos:
		if Vector2(x - p.x, z - p.y).length() < r + p.z: return false
	for t in tapetes:
		if absf(x - t[0]) < t[2] + r and absf(z - t[1]) < t[3] + r: return false
	return T.sdf(x, z) < -(r + 0.3)

func _reservar(x: float, z: float, r: float) -> void: ocupados.append(Vector3(x, z, r))

func _zonas_proibidas() -> void:
	for k in T.CORREDORES:
		var pts: Array = T.CORREDORES[k][0]
		for e in [pts[0], pts[pts.size() - 1]]: proibidos.append(Vector3(e[0], e[1], 5.0))
	for k in T.ESCADAS:
		var e: Dictionary = T.ESCADAS[k]
		proibidos.append(Vector3(e["topo"][0], e["topo"][1], 6.0))
		proibidos.append(Vector3(e["fundo"][0], e["fundo"][1], 6.0))
	proibidos.append(Vector3(0.0, 3.0, 4.0))      # ponto inicial
	proibidos.append(Vector3(76.0, 152.0, 3.0))   # posição do chefe

# colisão simples por AABB da malha: cilindro (pilar, braseiro, velas) ou caixa. Camada Mundo (1).
# estandartes só entram quando houver parede de arquitetura para pendurar (hoje ficam no chão da rocha e parecem lixo)
const COM_PAREDE := false
const COLISAO := {"Pilar": "cil", "Braseiro": "cil", "Velas": "cil", "ColunaCorrente": "caixa", "Estatua": "caixa", "Entulho": "caixa", "Estandarte": "caixa"}

func _aabb(n: Node, inv: Transform3D, acc: Array) -> void:
	if n is MeshInstance3D and (n as MeshInstance3D).mesh != null:
		var mi := n as MeshInstance3D
		var t := inv * mi.global_transform if mi.is_inside_tree() else inv * _local_xf(mi)
		var b := t * mi.mesh.get_aabb()
		acc[0] = b if acc[0] == null else (acc[0] as AABB).merge(b)
	for c in n.get_children(): _aabb(c, inv, acc)

func _local_xf(n: Node3D) -> Transform3D:
	var t := n.transform
	var p := n.get_parent()
	while p is Node3D:
		t = (p as Node3D).transform * t
		p = p.get_parent()
	return t

func _colisor(raiz: Node3D, modelo: String) -> void:
	if not COLISAO.has(modelo): return
	var acc := [null]
	_aabb(raiz, _local_xf(raiz).affine_inverse(), acc)
	if acc[0] == null: return
	var b: AABB = acc[0]
	var c := b.get_center()
	var cs := CollisionShape3D.new(); cs.name = "Forma"; cs.position = c
	if COLISAO[modelo] == "cil":
		var sh := CylinderShape3D.new(); sh.radius = minf(b.size.x, b.size.z) * 0.42; sh.height = b.size.y; cs.shape = sh
	else:
		var sh := BoxShape3D.new(); sh.size = Vector3(b.size.x * 0.85, b.size.y, b.size.z * 0.85); cs.shape = sh
	var corpo := StaticBody3D.new(); corpo.name = "Colisao"; corpo.collision_layer = 1; corpo.collision_mask = 0
	corpo.add_child(cs)
	raiz.add_child(corpo)

# ------------------------------------------------------------------ pisos e tapetes
func _pracas(props: Node3D) -> void:
	var gp := _grupo(props, "Pisos"); var gt := _grupo(props, "Tapetes")
	# pisos de 8x8: o topo (y=+0.097 no modelo) fica 5 cm acima do terreno, que é plano na praça
	var tiles := [[-8.0, 8.0, 0.0, 12.0], [-8.0, 16.0, 0.0, 12.0], [8.0, 8.0, 0.0, 12.0], [8.0, 16.0, 0.0, 12.0],
		[-8.0, 133.0, 76.0, 137.0], [-8.0, 141.0, 76.0, 137.0], [8.0, 133.0, 76.0, 137.0], [8.0, 141.0, 76.0, 137.0]]
	var i := 0
	for t in tiles:
		var cx: float = t[2] + t[0]
		var cz: float = t[1]
		_inst(gp, "Piso_%d" % i, "Piso", cx, cz, deg_to_rad(90.0 * (i % 4)), 0.0, T.chao(cx, cz) - 0.047); i += 1
	for p in [[76.0, 54.0], [84.0, 54.0]]:
		_inst(gp, "Piso_%d" % i, "Piso", p[0], p[1], deg_to_rad(90.0 * (i % 4)), 0.0, T.chao(p[0], p[1]) - 0.047); i += 1
	# tapete grande só em Átrio, Antecâmara e Arena; fica sobre praça plana, no mesmo nível do chão (+5 cm)
	for t in [["Atrio", 0.0, 12.0], ["Antecamara", 76.0, 95.0], ["Arena", 76.0, 137.0]]:
		_inst(gt, "TapeteGrande_" + t[0], "Tapete_Grande", t[1], t[2], 0.0, 0.0, T.chao(t[1], t[2]) + 0.075)
		tapetes.append([t[1], t[2], 4.0, 8.2]); _forro(gt, "Forro_" + t[0], t[1], t[2], 7.6, 16.0)
	# tapete de corredor (2,3 x 4,1 m) deitado no sentido do corredor, no centro de cada trecho reto
	for t in [["c01", 18.0, 15.0], ["c02", 58.0, 11.0], ["c04", 58.0, 56.0], ["c05", 18.0, 54.0], ["c07", 16.0, 96.0], ["c08", 58.0, 92.0]]:
		_inst(gt, "Tapete_" + t[0], "Tapete", t[1], t[2], PI * 0.5, 0.0, T.chao(t[1], t[2]) + 0.075)
		tapetes.append([t[1], t[2], 2.05, 1.15]); _forro(gt, "Forro_" + t[0], t[1], t[2], 3.9, 2.1)

# forro escuro sob o tapete: os furos de desgaste do tapete mostram tecido escuro e não o piso azul (parecia chão atravessando o tapete)
var _mat_forro: StandardMaterial3D
func _forro(pai: Node3D, nome: String, x: float, z: float, tx: float, tz: float) -> void:
	if _mat_forro == null:
		_mat_forro = StandardMaterial3D.new(); _mat_forro.albedo_color = Color(0.30, 0.05, 0.06); _mat_forro.roughness = 1.0
	var mi := MeshInstance3D.new(); mi.name = nome
	var pm := PlaneMesh.new(); pm.size = Vector2(tx, tz); pm.material = _mat_forro; mi.mesh = pm
	mi.position = Vector3(x, T.chao(x, z) + 0.06, -z)
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	pai.add_child(mi)

# ------------------------------------------------------------------ salas
func _centro_sala(nome: String) -> Vector2:
	var p: Array = T.SALAS[nome][0]
	return Vector2(p[1], p[2])

# ponto da parede (em doc) no ângulo dado, a "dentro" metros da borda; devolve null se a saída é corredor
func _ponto_parede(nome: String, ang: float, dentro: float) -> Variant:
	var c := _centro_sala(nome)
	var d := Vector2(cos(ang), sin(ang))
	var r := 1.0
	while r < 45.0 and T.sdf_sala(c.x + d.x * r, c.y + d.y * r, nome) < -dentro: r += 0.25
	r -= 0.25
	var q := c + d * r
	# se logo depois da borda o vazio continua, é uma abertura (corredor ou outra sala): não decora
	if T.sdf(q.x + d.x * (dentro + 1.2), q.y + d.y * (dentro + 1.2)) < 0.2: return null
	return q

# pontuação de canto: fração de rocha no círculo de 3 m em volta do ponto (parede reta ~50%, canto >60%)
func _pont_canto(x: float, z: float) -> float:
	var rocha := 0
	for k in 16:
		var a := k * TAU / 16.0
		if T.sdf(x + cos(a) * 3.0, z + sin(a) * 3.0) > 0.0: rocha += 1
	return rocha / 16.0

# entulho: pega os pontos mais "canto" da sala (por pontuação, então sempre existe), colado à parede
func _entulho_cantos(grupo: Node3D, nome: String, quantos: int) -> void:
	var cand: Array = []
	for k in 72:
		var q = _ponto_parede(nome, k * TAU / 72.0, 1.3)
		if q != null: cand.append([_pont_canto(q.x, q.y), q])
	cand.sort_custom(func(a, b): return a[0] > b[0])
	var n := 0
	for c in cand:
		if n >= quantos: break
		var q: Vector2 = c[1]
		if not _livre(q.x, q.y, 1.0): continue
		_inst(grupo, "Entulho_%d" % n, "Entulho", q.x, q.y, rng.randf() * TAU); _reservar(q.x, q.y, 1.0); n += 1

# estátua em nicho; as velas só existem aqui, em volta da base (motivo: oferenda)
func _estatua(grupo: Node3D, nome: String, q: Vector2, centro: Vector2) -> void:
	if not _livre(q.x, q.y, 1.1): return
	_inst(grupo, nome, "Estatua", q.x, q.y, _yaw_para(q.x, q.y, centro.x, centro.y)); _reservar(q.x, q.y, 1.1)
	var f := (centro - q).normalized(); var lado := Vector2(-f.y, f.x)
	for k in 3:
		var v := q + f * (1.6 + 0.15 * (k % 2)) + lado * (k - 1) * 0.95
		if _livre(v.x, v.y, 0.35):
			_inst(grupo, nome + "_Velas_%d" % k, "Velas", v.x, v.y, rng.randf() * TAU); _reservar(v.x, v.y, 0.35)

func _braseiro_se(grupo: Node3D, nome: String, x: float, z: float) -> void:
	if not _livre(x, z, 0.8): return
	_braseiro(grupo, nome, x, z); _reservar(x, z, 0.8)

func _pilar_se(grupo: Node3D, nome: String, x: float, z: float, ax: float, az: float, alinhado: bool = false) -> bool:
	if not _livre(x, z, 1.4): return false
	_inst(grupo, nome, "Pilar", x, z, 0.0 if alinhado else _yaw_para(x, z, ax, az)); _reservar(x, z, 1.4)
	return true

func _decorar_sala(props: Node3D, nome: String) -> void:
	var c := _centro_sala(nome)
	var grupo := _grupo(props, "Sala_" + nome.get_slice("_", 0))
	if nome.begins_with("s01"):
		# nicho: estátua no altar com as velas, braseiros nos quatro cantos do espaço
		var qe = _ponto_parede(nome, PI * 1.5, 2.6)
		if qe != null: _estatua(grupo, "Estatua", qe, c)
		for k in 4:
			var q = _ponto_parede(nome, k * TAU / 4.0 + 0.6, 2.4)
			if q != null: _braseiro_se(grupo, "Braseiro_%d" % k, q.x, q.y)
		return
	var soma := 0.0
	for k in 12:
		var d := Vector2(cos(k * TAU / 12.0), sin(k * TAU / 12.0))
		var r := 1.0
		while r < 45.0 and T.sdf_sala(c.x + d.x * r, c.y + d.y * r, nome) < -2.0: r += 0.5
		soma += r
	var raio := soma / 12.0
	# peças fixas por sala (o que a imagem conceito pede)
	match nome:
		"r00_atrio":
			for s in [-1.0, 1.0]:
				for dz in [-4.5, 4.5]: _braseiro_se(grupo, "BraseiroTapete_%d_%d" % [int(s), int(dz)], 5.9 * s, 12.0 + dz)
			_inst(grupo, "ColunaCorrente_Atrio", "ColunaCorrente", -8.8, 22.3, _yaw_para(-8.8, 22.3, 0.0, 10.0)); _reservar(-8.8, 22.3, 2.7)
			var q = _ponto_parede(nome, PI, 1.8)
			if q != null: _estatua(grupo, "Estatua_Atrio", q, c)
		"r08_antecamara":
			for s in [-1.0, 1.0]:
				for dz in [-5.5, 5.5]: _braseiro_se(grupo, "BraseiroTapete_%d_%d" % [int(s), int(dz)], 76.0 + 5.9 * s, 95.0 + dz)
			var q = _ponto_parede(nome, 0.0, 1.8)
			if q != null: _estatua(grupo, "Estatua_Antecamara", q, c)
		"r09_arena":
			_inst(grupo, "ColunaCorrente_Arena", "ColunaCorrente", 76.0, 156.0, _yaw_para(76.0, 156.0, 76.0, 139.0)); _reservar(76.0, 156.0, 2.8)
			for k in 8:   # anel de cobertura: pilares simétricos com chão aberto entre eles
				var a := k * PI / 4.0 + PI / 8.0
				_pilar_se(grupo, "PilarCobertura_%d" % k, 76.0 + cos(a) * 13.0, 139.0 + sin(a) * 13.0, 76.0, 139.0)
			for k in 6:   # braseiros de brasa no contorno
				var q = _ponto_parede(nome, k * TAU / 6.0 + 0.5, 3.0)
				if q != null: _braseiro_se(grupo, "BraseiroBorda_%d" % k, q.x, q.y)
		"r05_linha_tiro":
			for p in [[-10.0, 50.5], [-10.0, 57.5], [2.0, 50.5], [2.0, 57.5]]: _pilar_se(grupo, "PilarCobertura_%d" % int(p[1] + p[0]), p[0], p[1], c.x, c.y, true)
		"r06_elite_escudada":
			for p in [[-10.0, 91.0], [-10.0, 98.0]]: _pilar_se(grupo, "PilarCobertura_%d" % int(p[1]), p[0], p[1], c.x, c.y, true)
		"r07_elite_veloz":
			for p in [[37.0, 88.0], [37.0, 102.0]]: _pilar_se(grupo, "PilarCobertura_%d" % int(p[1]), p[0], p[1], c.x, c.y, true)
	# parede: pilares-pilastra emoldurando estandarte e braseiro, alternados e com espaço
	var n := clampi(int(round(TAU * raio / 9.5)), 6, 14)
	if n % 2 == 1: n += 1
	var fase := rng.randf() * TAU
	for k in n:
		var ang := fase + k * TAU / n + rng.randf_range(-0.07, 0.07)
		if k % 2 == 0:
			var q = _ponto_parede(nome, ang, 1.7)
			if q != null and nome != "r09_arena": _pilar_se(grupo, "Pilar_%d" % k, q.x, q.y, c.x, c.y)
		else:
			var qb = _ponto_parede(nome, ang, 3.0)
			if qb != null: _braseiro_se(grupo, "Braseiro_%d" % k, qb.x, qb.y)
			var qs = _ponto_parede(nome, ang + 0.12, 0.8)
			if COM_PAREDE and qs != null and _livre(qs.x, qs.y, 0.9):
				_inst(grupo, "Estandarte_%d" % k, "Estandarte", qs.x, qs.y, _yaw_para(qs.x, qs.y, c.x, c.y)); _reservar(qs.x, qs.y, 0.9)
	_entulho_cantos(grupo, nome, 2 if raio < 14.0 else 4)

func _corredores(props: Node3D) -> void:
	var g := _grupo(props, "Corredores")
	for k in T.CORREDORES:
		var pts: Array = T.CORREDORES[k][0]
		var meio: Array = pts[pts.size() / 2] if pts.size() > 2 else [(pts[0][0] + pts[1][0]) / 2.0, (pts[0][1] + pts[1][1]) / 2.0]
		var cl := OmniLight3D.new(); cl.name = "LuzCorredor_" + k; cl.position = _p(meio[0], meio[1], 2.6)
		cl.light_color = Color(1.0, 0.7, 0.4); cl.light_energy = 1.6; cl.omni_range = 7.0; cl.omni_attenuation = 1.4
		g.add_child(cl)
		if T.ESCADAS.has(k) or k == "s01": continue
		var a: Array = pts[0]; var b: Array = pts[pts.size() - 1]
		var dir := Vector2(b[0] - a[0], b[1] - a[1]).normalized()
		var perp := Vector2(-dir.y, dir.x)
		_braseiro_se(g, "Braseiro_" + k, meio[0] + perp.x * 2.2, meio[1] + perp.y * 2.2)

# poças aprovadas (decal v7, cenas Poca_A/B/C): em chão plano, fora de tapete, de peças e das bocas de corredor
func _pocas(props: Node3D) -> void:
	var g := _grupo(props, "Pocas")
	var onde := [["A", -3.0, 6.0], ["B", 5.0, 18.5], ["C", 12.0, 17.0], ["A", -4.0, 54.0], ["B", -12.0, 52.0], ["C", 33.0, 56.0], ["A", 40.0, 51.0],
		["B", -4.0, 89.0], ["C", 41.0, 98.0], ["A", 33.0, 91.0], ["B", 72.0, 56.0], ["C", 66.0, 131.0], ["A", 84.0, 146.0], ["B", 76.0, 122.0]]
	var i := 0
	for p in onde:
		var cena := load("res://scenes/cripta/Poca_%s.tscn" % p[0]) as PackedScene
		if cena != null and _livre(p[1], p[2], 1.3):
			var n := cena.instantiate() as Node3D; n.name = "Poca_%s_%d" % [p[0], i]
			n.position = Vector3(p[1], T.chao(p[1], p[2]) + 0.05, -p[2]); n.rotation.y = rng.randf() * TAU
			g.add_child(n); _reservar(p[1], p[2], 1.3); contagem["Poca"] = int(contagem.get("Poca", 0)) + 1
		i += 1

# marcos: nós vazios onde o glb da escadaria e as portas vão entrar
func _marcos(raiz: Node3D) -> void:
	var m := Node3D.new(); m.name = "Marcos"; raiz.add_child(m)
	var pontos := {"PontoInicial_Atrio": [0.0, 3.0], "Boss_Arena": [76.0, 152.0], "Subsolo_Centro": [-4.0, 54.0], "Profundeza_Centro": [37.0, 95.0]}
	for k in pontos:
		var mk := Marker3D.new(); mk.name = k; mk.position = _p(pontos[k][0], pontos[k][1]); m.add_child(mk)

# ------------------------------------------------------------------ braseiro (luz, chama e partículas)
var _tex_ponto: GradientTexture2D
var _faisca_malha: QuadMesh
var _faisca_proc: ParticleProcessMaterial
var _fumaca_malha: QuadMesh
var _fumaca_proc: ParticleProcessMaterial

func _braseiro(pai: Node3D, nome: String, x: float, z: float) -> void:
	var n := Node3D.new(); n.name = nome; n.position = _p(x, z)
	n.position.y = _base_y(x, z, 0.5) - 0.02
	n.rotation.y = rng.randf() * TAU
	var cena := _glb("Braseiro")
	if cena:
		var m := cena.instantiate() as Node3D; m.name = "Modelo"; m.scale = Vector3.ONE * 0.75; n.add_child(m); _colisor(m, "Braseiro")
	var luz := OmniLight3D.new(); luz.name = "Luz"; luz.position = Vector3(0, 1.45, 0)
	luz.light_color = Color(1.0, 0.68, 0.36); luz.light_energy = 1.2; luz.omni_range = 6.0; luz.omni_attenuation = 1.5
	luz.set_script(load("res://scripts/cripta/braseiro_luz.gd"))
	n.add_child(luz)
	var ch := Node3D.new(); ch.name = "Chama"; ch.position = Vector3(0, 0.88, 0); ch.scale = Vector3.ONE * 0.75
	var tam := [Vector2(1.5, 1.35), Vector2(1.05, 0.95), Vector2(1.05, 0.95), Vector2(0.6, 0.7), Vector2(0.55, 0.6), Vector2(0.6, 0.62)]
	var desl := [Vector3(0, 0, 0), Vector3(-0.2, 0, 0.03), Vector3(0.2, 0, 0.05), Vector3(0.1, 0, 0.1), Vector3(-0.12, 0, 0.12), Vector3(0.02, 0, -0.1)]
	for k in tam.size():
		var qm := QuadMesh.new(); qm.size = tam[k]; qm.center_offset = Vector3(0, tam[k].y * 0.5, 0)
		var sm := ShaderMaterial.new(); sm.shader = load("res://art/shaders/chama.gdshader")
		sm.set_shader_parameter("seed", float(hash(nome + str(x)) % 97) + k * 13.0); sm.set_shader_parameter("speed", 1.0 + 0.35 * k)
		qm.material = sm
		var mi := MeshInstance3D.new(); mi.name = "Cartao%d" % k; mi.mesh = qm; mi.position = desl[k]
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		ch.add_child(mi)
	n.add_child(ch)
	var lb := OmniLight3D.new(); lb.name = "LuzBacia"; lb.position = Vector3(0, 0.98, 0)
	lb.light_color = Color(1.0, 0.45, 0.12); lb.light_energy = 0.7; lb.omni_range = 2.2; lb.omni_attenuation = 1.3
	lb.set_script(load("res://scripts/cripta/braseiro_luz.gd"))
	n.add_child(lb)
	_particulas_braseiro(n)
	pai.add_child(n)
	contagem["Braseiro"] = int(contagem.get("Braseiro", 0)) + 1

func _particulas_braseiro(n: Node3D) -> void:
	if _tex_ponto == null:
		_tex_ponto = GradientTexture2D.new(); _tex_ponto.fill = GradientTexture2D.FILL_RADIAL
		_tex_ponto.fill_from = Vector2(0.5, 0.5); _tex_ponto.fill_to = Vector2(0.5, 0.0); _tex_ponto.width = 64; _tex_ponto.height = 64
		var gp := Gradient.new(); gp.set_color(0, Color(1, 1, 1, 1)); gp.set_color(1, Color(1, 1, 1, 0)); _tex_ponto.gradient = gp
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
	f.position = Vector3(0, 0.98, 0); f.process_material = _faisca_proc; f.draw_pass_1 = _faisca_malha
	f.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF; f.randomness = 1.0
	n.add_child(f)
	var u := GPUParticles3D.new(); u.name = "Fumaca"; u.amount = 8; u.lifetime = 3.6; u.local_coords = false
	u.position = Vector3(0, 1.6, 0); u.process_material = _fumaca_proc; u.draw_pass_1 = _fumaca_malha
	u.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF; u.randomness = 1.0
	n.add_child(u)
