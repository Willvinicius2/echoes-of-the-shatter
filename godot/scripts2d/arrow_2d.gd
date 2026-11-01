extends Area2D
## Projétil 2D. `team` = "player" acerta inimigos; "enemy" acerta o jogador. Paredes sempre param.
## A colisão anda no chão (global_position); o desenho (`vis`) fica `altura` px acima, girado na direção do voo.
## A flecha nasce na altura da boca do arco e desce até `altura_voo` nos primeiros `altura_dist` px (doc 33 seção 2).

const Placeholders = preload("res://scripts2d/placeholders.gd")
const Feel = preload("res://scripts2d/feel_2d.gd")

var team := "player"
var velocity := Vector2.ZERO
var damage := 0.0
var max_dist := 1000.0
var pierce := 0  # inimigos que ainda pode atravessar (upgrade)
var veneno_dps := 0.0       # habilidade Pontas Venenosas
var veneno_t := 0.0
var explode_raio := 0.0     # habilidade Flecha Explosiva: explode ao acertar
var explode_dano := 0.0
## Cor do elemento (árvore): pinta brilho, rastro, flash de boca e explosão. Mudar depois de criada repinta na hora.
var cor_fx := Color(0.8, 0.8, 0.8):
	set(v):
		cor_fx = v
		_cor = v
		_repintar()
var altura := 30.0          # altura atual do desenho sobre o chão
var altura_voo := 30.0      # altura de cruzeiro (peito dos inimigos)
var altura_dist := 0.0      # distância para descer da altura inicial até a de cruzeiro (0 = já nasce na de cruzeiro)
var _altura_ini := 30.0
var _desloc_ini := Vector2.ZERO   # desvio do desenho em relação à colisão ao nascer (boca do arco ao lado do corpo)
var _viajado := 0.0
var _trilha: Line2D
var _brilho: Sprite2D
var _cor := Color(0.45, 1.0, 0.5)
## Nó do desenho: fica na altura da flecha e gira com a direção. Efeitos elementais se penduram aqui (posição local zero).
## Antes o corpo todo girava e o desvio para cima girava junto: o desenho saía ao lado da trilha e do acerto.
var vis := Node2D.new()

## A colisão sai de `origem` na linha da mira; só o desenho nasce em `desloc` (px de lado, a partir da colisão) e na
## altura `alt_ini` (a boca do arco) e converge para a colisão e para `alt_voo` em `alt_dist` px: a flecha sai da mão
## e acerta onde o jogador mirou.
func setup(equipe: String, origem: Vector2, dir: Vector2, vel: float, dano: float, alcance: float,
		alt_ini := 30.0, alt_voo := 30.0, alt_dist := 0.0, desloc := Vector2.ZERO) -> void:
	team = equipe
	global_position = origem
	velocity = dir.normalized() * vel
	damage = dano
	max_dist = alcance
	vis.rotation = dir.angle()
	_altura_ini = alt_ini
	altura = alt_ini
	altura_voo = alt_voo
	altura_dist = alt_dist
	_desloc_ini = desloc

func cor_atual() -> Color:
	return _cor

func ponta() -> Vector2:
	return vis.global_position

func _ready() -> void:
	collision_layer = 0
	collision_mask = 1 | (4 if team == "player" else 2)
	var cs := CollisionShape2D.new()
	var sh := CircleShape2D.new()
	sh.radius = 6.0
	cs.shape = sh
	add_child(cs)
	var c := Feel.cfg()
	if team == "enemy":
		_cor = Color(1.0, 0.35, 0.5)
	var sp := Sprite2D.new()
	var caminho := "res://art2d/fx/arrow.png"
	if ResourceLoader.exists(caminho):
		sp.texture = load(caminho)
	else:
		sp.texture = Placeholders.seta(Vector2i(64, 16))
		sp.modulate = Color(0.55, 0.38, 0.22) if team == "player" else Color(0.6, 1.0, 0.9)  # haste de madeira escura
	vis.position = _desloc_ini + Vector2(0, -altura)  # só o desenho sobe e sai da mão; a colisão fica no chão
	sp.scale = Vector2(c["arrow_scale"], 1.0)  # só alonga: haste continua fina
	_brilho = Sprite2D.new()
	_brilho.texture = Feel.ponto()
	_brilho.material = Feel.aditivo()
	_brilho.scale = Vector2(c["arrow_glow_scale"] * 1.6, c["arrow_glow_scale"])
	_brilho.modulate = Color(_cor.r, _cor.g, _cor.b, c["arrow_glow_alpha"])
	vis.add_child(_brilho)
	vis.add_child(sp)
	add_child(vis)
	_criar_trilha(c)
	body_entered.connect(_on_body)

func _criar_trilha(c: Dictionary) -> void:
	_trilha = Line2D.new()
	_trilha.top_level = true
	_trilha.global_position = Vector2.ZERO
	_trilha.width = c["arrow_trail_width"]
	_trilha.material = Feel.aditivo()
	_trilha.begin_cap_mode = Line2D.LINE_CAP_ROUND
	_trilha.gradient = _gradiente()
	var w := Curve.new()
	w.add_point(Vector2(0, 0.0))
	w.add_point(Vector2(1, 1.0))
	_trilha.width_curve = w
	add_child(_trilha)

func _gradiente() -> Gradient:
	var g := Gradient.new()
	g.colors = PackedColorArray([Color(_cor.r, _cor.g, _cor.b, 0.0), Color(_cor.r, _cor.g, _cor.b, 0.85)])
	return g

## Brilho e rastro acompanham a cor do elemento (doc 33 seção 4: a cor identifica o elemento).
func _repintar() -> void:
	if _brilho != null:
		_brilho.modulate = Color(_cor.r, _cor.g, _cor.b, _brilho.modulate.a)
	if _trilha != null:
		_trilha.gradient = _gradiente()

func _physics_process(delta: float) -> void:
	var passo := velocity * delta
	global_position += passo
	_viajado += passo.length()
	if altura_dist > 0.0 and _viajado < altura_dist + 1.0:
		var f := clampf(_viajado / altura_dist, 0.0, 1.0)
		altura = lerpf(_altura_ini, altura_voo, f)
		vis.position = _desloc_ini.lerp(Vector2.ZERO, f) + Vector2(0, -altura)
	if _trilha != null:
		_trilha.add_point(ponta())
		if _trilha.get_point_count() > int(Feel.cfg()["arrow_trail_points"]):
			_trilha.remove_point(0)
	if _viajado >= max_dist:
		_fim()

func _on_body(corpo: Node) -> void:
	var p := ponta()
	if corpo.has_method("take_damage"):
		Feel.impacto(get_parent(), p, _cor, velocity.normalized() * -1.0)
		corpo.take_damage(damage, global_position - velocity.normalized() * 8.0)
		if veneno_dps > 0.0 and corpo.has_method("aplicar_status"):
			corpo.aplicar_status("veneno", veneno_t, veneno_dps)
		if pierce > 0:
			pierce -= 1
			return
	elif is_inside_tree():
		Feel.impacto(get_parent(), p, Color(0.8, 0.8, 0.8), velocity.normalized() * -1.0)
	if explode_raio > 0.0 and is_inside_tree():
		_explodir()
	_fim()

func _explodir() -> void:
	Feel.impacto(get_parent(), ponta(), cor_fx, Vector2.ZERO, explode_raio / 40.0)
	for n in get_tree().get_nodes_in_group("hurtable"):
		if n is Node2D and n.global_position.distance_to(global_position) <= explode_raio:
			n.take_damage(explode_dano, global_position)

## Solta o rastro para sumir sozinho e remove a flecha.
func _fim() -> void:
	if _trilha != null and is_inside_tree():
		var t := _trilha
		_trilha = null
		t.reparent(get_parent())
		var tw := t.create_tween()
		tw.tween_property(t, "modulate:a", 0.0, Feel.cfg()["arrow_trail_fade"])
		tw.tween_callback(t.queue_free)
	queue_free()
