extends RefCounted
## Game feel: hit stop, tremor de câmera, número de dano e faísca de impacto. Números em data2d/feel.csv.

const Feel = preload("res://scripts2d/feel_2d.gd")
const Csv = preload("res://scripts2d/csv2d.gd")
const DamageNumber = preload("res://scripts2d/damage_number_2d.gd")
const ImpactFx = preload("res://scripts2d/impact_fx_2d.gd")

const FX_SHADER := """
shader_type canvas_item;
uniform float flash : hint_range(0.0, 1.0) = 0.0;
uniform float dissolve : hint_range(0.0, 1.0) = 0.0;
uniform vec4 edge_color : source_color = vec4(0.55, 0.9, 1.0, 1.0);
uniform vec4 glow_color : source_color = vec4(1.0, 0.3, 0.2, 1.0);
uniform float glow : hint_range(0.0, 1.0) = 0.0;
float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
void fragment() {
	float n = hash(floor(UV * vec2(textureSize(TEXTURE, 0)) / 3.0));
	float keep = step(dissolve, n);
	float rim = (1.0 - step(dissolve + 0.12, n)) * step(0.001, dissolve);
	COLOR.rgb = mix(COLOR.rgb, edge_color.rgb, rim);
	COLOR.a *= keep;
	COLOR.rgb = mix(COLOR.rgb, vec3(1.0), flash);
	COLOR.rgb += glow_color.rgb * glow * COLOR.a;
}
"""

static var _cfg := {}
static var _shader: Shader
static var _ponto: Texture2D
static var _aditivo: CanvasItemMaterial
static var _stop_ate := 0   # ticks (ms) em que o hit stop atual termina
static var _stop_livre_ate := 0   # ticks (ms) antes dos quais um novo hit stop não começa (intervalo entre congelamentos)
static var _impactos: Array = []   # faíscas, rajadas de partículas e números vivos: o teto evita tempestade de nós com auras e venenos
static var _rajadas: Array = []
static var _numeros: Array = []

## Conta os nós vivos da lista (descarta os já liberados) e diz se ainda cabe mais um abaixo de `teto`.
static func _cabe(lista: Array, teto: int) -> bool:
	if lista.size() < teto:
		return true
	var i := lista.size() - 1
	while i >= 0:
		if not is_instance_valid(lista[i]):
			lista.remove_at(i)
		i -= 1
	return lista.size() < teto

static func cfg() -> Dictionary:
	if _cfg.is_empty():
		_cfg = Csv.kv("res://data2d/feel.csv")
	return _cfg

## Congela o jogo por `ms` milissegundos reais. Pedidos sobrepostos valem pelo maior tempo restante.
## Um nó vigia o relógio real a cada quadro e devolve a escala de tempo (não depende de timers).
static func hit_stop(ms: float) -> void:
	if ms <= 0.0:
		return
	var tree := Engine.get_main_loop() as SceneTree
	if tree == null or tree.root == null:
		return
	var agora := Time.get_ticks_msec()
	# Sem intervalo, auras e venenos (dano em vários inimigos por segundo) deixavam o jogo em 5% de velocidade quase
	# o tempo todo, o que parece FPS baixo. Depois de um congelamento há uma folga (hit_stop_cooldown_ms) sem outro.
	if agora < _stop_livre_ate:
		return
	var fim := agora + int(ms)
	if fim <= _stop_ate:
		return
	_stop_ate = fim
	_stop_livre_ate = fim + int(cfg().get("hit_stop_cooldown_ms", 400))
	Engine.time_scale = cfg()["hit_stop_scale"]
	var guarda := tree.root.get_node_or_null("FeelHitStop")
	if guarda == null:
		guarda = HitStopGuard.new()
		guarda.name = "FeelHitStop"
		guarda.process_mode = Node.PROCESS_MODE_ALWAYS
		tree.root.add_child(guarda)

static func hit_stop_acabou() -> bool:
	return Time.get_ticks_msec() >= _stop_ate

class HitStopGuard extends Node:
	func _process(_d: float) -> void:
		if Feel.hit_stop_acabou():
			Engine.time_scale = 1.0
			queue_free()

## Tremor da câmera ativa do nó `ref`: amplitude em px, decai até zero em `tempo` s.
static func shake(ref: Node, amp: float, tempo: float) -> void:
	if amp <= 0.0 or tempo <= 0.0 or not ref.is_inside_tree():
		return
	var cam := ref.get_viewport().get_camera_2d()
	if cam == null:
		return
	if cam.has_meta("feel_tween"):
		var velho: Tween = cam.get_meta("feel_tween")
		if velho != null and velho.is_valid():
			velho.kill()
	cam.offset = Vector2.ZERO
	var tw := cam.create_tween()
	cam.set_meta("feel_tween", tw)
	tw.tween_method(func(t: float) -> void:
		cam.offset = Vector2.from_angle(randf() * TAU) * amp * (1.0 - t), 0.0, 1.0, tempo)
	tw.tween_callback(func() -> void: cam.offset = Vector2.ZERO)

## Número flutuante sobre `alvo`. `cor` distingue dano no inimigo, morte e dano no jogador.
static func numero(alvo: Node2D, valor: float, cor: Color, grande := false, forte := false) -> void:
	var pai := alvo.get_parent()
	if pai == null:
		return
	# Golpes no mesmo alvo dentro de `dmg_number_group_ms` somam num número só (doc 36 seção 6.1: menos amontoado)
	var agora := Time.get_ticks_msec()
	var ant = alvo.get_meta("dmg_num", null)
	if ant != null and is_instance_valid(ant) and agora - int(alvo.get_meta("dmg_num_t", 0)) <= int(cfg().get("dmg_number_group_ms", 200)):
		var soma: float = float(alvo.get_meta("dmg_num_v", 0.0)) + valor
		alvo.set_meta("dmg_num_v", soma)
		ant.texto = str(int(round(soma)))
		ant.forte = ant.forte or grande or forte
		if grande or forte:
			ant.cor = cor
		return
	if not (grande or forte) and not _cabe(_numeros, int(cfg().get("fx_max_numeros", 30))):
		return   # tempestade de golpes pequenos: os números fatais e fortes continuam aparecendo
	var n := DamageNumber.new()
	_numeros.append(n)
	n.texto = str(int(round(valor)))
	alvo.set_meta("dmg_num", n)
	alvo.set_meta("dmg_num_v", valor)
	alvo.set_meta("dmg_num_t", agora)
	n.cor = cor
	n.tamanho = cfg()["dmg_number_size_kill" if grande else ("dmg_number_size_strong" if forte else "dmg_number_size")]
	var esc: float = alvo.escala_sprite() if alvo.has_method("escala_sprite") else 1.0   # alvo grande: número mais alto e maior
	n.tamanho *= clampf(esc, 1.0, 1.4)
	n.forte = grande or forte
	n.deriva = randf_range(-1.0, 1.0) * cfg()["dmg_number_drift"]
	n.tempo = cfg()["dmg_number_time"]
	n.subida = cfg()["dmg_number_rise"]
	pai.add_child(n)
	n.global_position = alvo.global_position + Vector2(randf_range(-1.0, 1.0) * cfg()["number_offset_x"], (-90.0 * maxf(esc, 0.7) - 8.0) + randf_range(-10.0, 6.0))

## Faísca de impacto em `pos` (mundo), filha de `pai`.
static func impacto(pai: Node, pos: Vector2, cor: Color, dir := Vector2.ZERO, escala := 1.0) -> void:
	if pai == null or not _cabe(_impactos, int(cfg().get("fx_max_impactos", 30))):
		return
	var fx := ImpactFx.new()
	_impactos.append(fx)
	fx.cor = cor
	fx.tempo = cfg()["impact_time"] * (1.0 if escala <= 1.0 else 2.5)
	fx.escala = escala
	pai.add_child(fx)
	fx.global_position = pos
	if escala <= 1.0:
		var c := cfg()
		particulas(pai, pos, cor, int(c["spark_count"]), c["spark_speed"], c["spark_time"], dir)

## Material de ator: flash branco, dissolução e brilho colorido (uma instância por ator).
static func material_ator() -> ShaderMaterial:
	if _shader == null:
		_shader = Shader.new()
		_shader.code = FX_SHADER
	var m := ShaderMaterial.new()
	m.shader = _shader
	return m

## Bolinha macia (branco → transparente), base de brilhos e partículas.
static func ponto() -> Texture2D:
	if _ponto == null:
		var g := Gradient.new()
		g.colors = PackedColorArray([Color(1, 1, 1, 1), Color(1, 1, 1, 0)])
		var t := GradientTexture2D.new()
		t.gradient = g
		t.fill = GradientTexture2D.FILL_RADIAL
		t.fill_from = Vector2(0.5, 0.5)
		t.fill_to = Vector2(1.0, 0.5)
		t.width = 32
		t.height = 32
		_ponto = t
	return _ponto

static func aditivo() -> CanvasItemMaterial:
	if _aditivo == null:
		_aditivo = CanvasItemMaterial.new()
		_aditivo.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	return _aditivo

## Rajada única de partículas em `pos` (mundo). `dir` zero espalha em todas as direções.
static func particulas(pai: Node, pos: Vector2, cor: Color, qtd: int, vel: float, vida: float, dir := Vector2.ZERO, tam := 0.2) -> void:
	if pai == null or qtd <= 0 or not _cabe(_rajadas, int(cfg().get("fx_max_rajadas", 24))):
		return
	var p := CPUParticles2D.new()
	_rajadas.append(p)
	p.one_shot = true
	p.explosiveness = 1.0
	p.amount = qtd
	p.lifetime = vida
	p.texture = ponto()
	p.material = aditivo()
	p.gravity = Vector2.ZERO
	p.direction = dir if dir != Vector2.ZERO else Vector2.RIGHT
	p.spread = 180.0 if dir == Vector2.ZERO else 55.0
	p.initial_velocity_min = vel * 0.4
	p.initial_velocity_max = vel
	p.damping_min = vel * 1.2
	p.damping_max = vel * 2.0
	p.scale_amount_min = tam * 0.6
	p.scale_amount_max = tam
	var rampa := Gradient.new()
	rampa.colors = PackedColorArray([cor, Color(cor.r, cor.g, cor.b, 0.0)])
	p.color_ramp = rampa
	p.z_index = 150
	pai.add_child(p)
	p.global_position = pos
	p.emitting = true
	p.finished.connect(p.queue_free)

## Poeira e almas na morte de um inimigo.
static func morte(pai: Node, pos: Vector2, cor: Color) -> void:
	var c := cfg()
	particulas(pai, pos, cor, int(c["death_particles"]), 110.0, c["death_particle_time"], Vector2.ZERO, 0.16)
	particulas(pai, pos, Color(1, 1, 1, 0.8), int(c["death_particles"]) / 3, 50.0, c["death_particle_time"] * 0.8, Vector2.UP, 0.1)

## Zoom que começa em `fator` vezes o atual e volta ao normal em `tempo` s.
static func zoom_punch(ref: Node, fator: float, tempo: float) -> void:
	if fator == 1.0 or tempo <= 0.0 or not ref.is_inside_tree():
		return
	var cam := ref.get_viewport().get_camera_2d()
	if cam == null:
		return
	var base: Vector2 = cam.get_meta("feel_zoom_base", cam.zoom)
	if cam.has_meta("feel_zoom_tween"):
		var velho: Tween = cam.get_meta("feel_zoom_tween")
		if velho != null and velho.is_valid():
			velho.kill()
	cam.set_meta("feel_zoom_base", base)
	cam.zoom = base * fator
	var tw := cam.create_tween().set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_QUAD)
	cam.set_meta("feel_zoom_tween", tw)
	tw.tween_property(cam, "zoom", base, tempo)
	tw.tween_callback(func() -> void: cam.remove_meta("feel_zoom_base"))
