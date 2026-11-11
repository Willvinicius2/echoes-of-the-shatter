extends Area2D
## Projétil mágico do mago em pixel art: orbe arcano, brasa, lasca de gelo, bolha de peste e faísca.
## Acerta inimigos (camada 4) e para em parede. `raio_expl` > 0 explode em área; `pierce` atravessa.
## O desenho é um sprite pequeno gerado por código (uma vez por forma e elemento), ampliado pela grade do mundo
## (1 px da arte = GRADE px), com rastro de quadradinhos e sombra no chão. A colisão fica no chão, como a da flecha.

const Alvos = preload("res://scripts2d/alvos_2d.gd")
const Feel = preload("res://scripts2d/feel_2d.gd")
const FxMago = preload("res://scripts2d/fx_mago_2d.gd")

const GRADE := 2.5          # px de mundo por px de arte (a mesma do sprite do mago)
const ALTURA := 30.0        # o desenho voa na altura do peito
const RASTRO_MAX := 6

var velocity := Vector2.ZERO
var dano := 0.0
var max_dist := 900.0
var raio_expl := 0.0
var pierce := 0
var cor := Color(0.7, 0.5, 1.0)   # legado: tinge o orbe arcano quando `elemento` fica vazio
var tamanho := 9.0
var status := {}             # {tipo, dur, valor} aplicado a quem toma o golpe
var elemento := ""           # "" (arcano), fogo, gelo, raio ou veneno: paleta, rastro e impacto
var forma := "orbe"          # orbe, chama, lasca, bolha ou faisca
var ao_acertar := Callable() # (corpo: Node) depois do dano de cada acerto
var ao_fim := Callable()     # (pos: Vector2) quando o projétil acaba (acerto final, parede ou alcance)
var dono: WeakRef            # quem lançou (para devolver mana)
var mana_acerto := 0.0       # mana devolvida ao dono por inimigo atingido (ataque básico)
var _viajado := 0.0
var _acertados := []
var _vis: Sprite2D
var _rastro: Array = []      # posições (mundo) dos últimos passos
var _t := 0.0
var _acabou := false

func setup(origem: Vector2, dir: Vector2, vel: float, dano_: float, alcance: float) -> void:
	global_position = origem
	velocity = dir.normalized() * vel
	dano = dano_
	max_dist = alcance

func _ready() -> void:
	collision_layer = 0
	collision_mask = 1 | 4
	add_to_group("orbe_jogador")
	var cs := CollisionShape2D.new()
	var sh := CircleShape2D.new()
	sh.radius = tamanho
	cs.shape = sh
	add_child(cs)
	_vis = Sprite2D.new()
	_vis.texture = FxMago.textura_projetil(forma, elemento)
	_vis.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_vis.position = Vector2(0, -ALTURA)
	_vis.rotation = velocity.angle() if forma != "orbe" and forma != "bolha" else 0.0
	_vis.scale = Vector2.ONE * GRADE * maxf(1.0, roundf(tamanho / 8.0))
	_vis.z_index = 3
	if elemento == "":
		_vis.modulate = Color.WHITE.lerp(cor, 0.0 if cor.is_equal_approx(Color(0.7, 0.5, 1.0)) else 0.6)
	add_child(_vis)
	body_entered.connect(_on_body)

func _physics_process(delta: float) -> void:
	_t += delta
	var passo := velocity * delta
	global_position += passo
	_viajado += passo.length()
	if _rastro.is_empty() or _rastro.back().distance_to(global_position) > GRADE * 3.0:
		_rastro.append(global_position)
		if _rastro.size() > RASTRO_MAX:
			_rastro.pop_front()
	if forma == "bolha":   # a bolha balança
		var k := 1.0 + 0.12 * sin(_t * 14.0)
		_vis.scale = Vector2(k, 2.0 - k) * GRADE * maxf(1.0, roundf(tamanho / 8.0))
	queue_redraw()
	if _viajado >= max_dist:
		_fim()

func _draw() -> void:
	draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.5))
	draw_circle(Vector2.ZERO, tamanho * 0.9, Color(0, 0, 0, 0.28))   # sombra no chão
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	var pal: Array = FxMago.paleta(elemento)
	var n := _rastro.size()
	for i in n:   # rastro: quadradinhos na grade, do mais velho (pequeno e apagado) ao mais novo
		var k := float(i + 1) / float(n + 1)
		var lado := GRADE * (1.0 if k < 0.5 else 2.0)
		var p: Vector2 = ((_rastro[i] - global_position + Vector2(0, -ALTURA)) / GRADE).round() * GRADE
		var c: Color = pal[2] if k < 0.7 else pal[3]
		draw_rect(Rect2(p - Vector2(lado, lado) * 0.5, Vector2(lado, lado)), Color(c, 0.25 + 0.5 * k))

func _on_body(corpo: Node) -> void:
	if _acabou:
		return
	if corpo.has_method("take_damage"):
		if _acertados.has(corpo):
			return
		_acertados.append(corpo)
		if raio_expl > 0.0:
			_explodir()
			return
		Alvos.golpear(corpo, dano, global_position - velocity.normalized() * 8.0, status)
		_devolver_mana()
		if ao_acertar.is_valid():
			ao_acertar.call(corpo)
		if pierce > 0:
			pierce -= 1
			FxMago.impacto(get_parent(), global_position + Vector2(0, -ALTURA), elemento, 0.6)
			return
		_fim()
	else:
		_fim()

func _devolver_mana() -> void:
	if mana_acerto > 0.0 and dono != null and dono.get_ref() != null:
		dono.get_ref().ganhar_mana(mana_acerto)

func _explodir() -> void:
	if _acabou:
		return
	_acabou = true
	for n in Alvos.em_circulo(get_tree(), global_position, raio_expl):
		Alvos.golpear(n, dano, global_position, status)
		_devolver_mana()
		if ao_acertar.is_valid() and is_instance_valid(n):
			ao_acertar.call(n)
	FxMago.explosao(get_parent(), global_position, elemento, raio_expl)
	Feel.shake(self, 3.0, 0.12)
	if ao_fim.is_valid():
		ao_fim.call(global_position)
	queue_free()

func _fim() -> void:
	if _acabou:
		return
	if raio_expl > 0.0 and is_inside_tree():
		_explodir()
		return
	_acabou = true
	if is_inside_tree():
		FxMago.impacto(get_parent(), global_position + Vector2(0, -ALTURA), elemento, 1.0)
		if ao_fim.is_valid():
			ao_fim.call(global_position)
	queue_free()
