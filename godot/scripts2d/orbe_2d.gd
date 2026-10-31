extends Area2D
## Projétil mágico do mago: orbe arcano, bola de fogo, raio de gelo, estaca glacial.
## Acerta inimigos (camada 4) e para em parede. `raio_expl` > 0 explode em área; `pierce` atravessa.

const Alvos = preload("res://scripts2d/alvos_2d.gd")
const Efeito = preload("res://scripts2d/efeito_2d.gd")
const Feel = preload("res://scripts2d/feel_2d.gd")

var velocity := Vector2.ZERO
var dano := 0.0
var max_dist := 900.0
var raio_expl := 0.0
var pierce := 0
var cor := Color(0.7, 0.5, 1.0)
var tamanho := 9.0
var status := {}      # {tipo, dur, valor} aplicado a quem toma o golpe
var _viajado := 0.0
var _acertados := []

func setup(origem: Vector2, dir: Vector2, vel: float, dano_: float, alcance: float) -> void:
	global_position = origem
	velocity = dir.normalized() * vel
	dano = dano_
	max_dist = alcance
	rotation = dir.angle()

func _ready() -> void:
	collision_layer = 0
	collision_mask = 1 | 4
	var cs := CollisionShape2D.new()
	var sh := CircleShape2D.new()
	sh.radius = tamanho
	cs.shape = sh
	add_child(cs)
	body_entered.connect(_on_body)

func _physics_process(delta: float) -> void:
	var passo := velocity * delta
	global_position += passo
	_viajado += passo.length()
	queue_redraw()
	if _viajado >= max_dist:
		_fim()

func _draw() -> void:
	# o desenho sobe até o peito; a colisão fica no chão (igual à flecha)
	var c := Vector2(0, -30).rotated(-rotation)
	draw_circle(c, tamanho * 1.9, Color(cor, 0.18))
	draw_circle(c, tamanho * 1.3, Color(cor, 0.4))
	draw_circle(c, tamanho * 0.8, cor.lightened(0.35))
	draw_circle(c, tamanho * 0.4, Color(1, 1, 1, 0.9))

func _on_body(corpo: Node) -> void:
	if corpo.has_method("take_damage"):
		if _acertados.has(corpo):
			return
		_acertados.append(corpo)
		if raio_expl > 0.0:
			_explodir()
			return
		Alvos.golpear(corpo, dano, global_position - velocity.normalized() * 8.0, status)
		if pierce > 0:
			pierce -= 1
			return
		_fim()
	else:
		_fim()

func _explodir() -> void:
	for n in Alvos.em_circulo(get_tree(), global_position, raio_expl):
		Alvos.golpear(n, dano, global_position, status)
	Efeito.anel(get_parent(), global_position, raio_expl, cor)
	Feel.shake(self, 3.0, 0.12)
	queue_free()

func _fim() -> void:
	if raio_expl > 0.0 and is_inside_tree():
		_explodir()
	else:
		queue_free()
