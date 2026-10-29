extends Area2D
## Projétil 2D. `team` = "player" acerta inimigos; "enemy" acerta o jogador. Paredes sempre param.

const Placeholders = preload("res://scripts2d/placeholders.gd")

var team := "player"
var velocity := Vector2.ZERO
var damage := 0.0
var max_dist := 1000.0
var _viajado := 0.0

func setup(equipe: String, origem: Vector2, dir: Vector2, vel: float, dano: float, alcance: float) -> void:
	team = equipe
	global_position = origem
	velocity = dir.normalized() * vel
	damage = dano
	max_dist = alcance
	rotation = dir.angle()

func _ready() -> void:
	collision_layer = 0
	collision_mask = 1 | (4 if team == "player" else 2)
	var cs := CollisionShape2D.new()
	var sh := CircleShape2D.new()
	sh.radius = 6.0
	cs.shape = sh
	add_child(cs)
	var sp := Sprite2D.new()
	var caminho := "res://art2d/fx/arrow.png"
	if ResourceLoader.exists(caminho):
		sp.texture = load(caminho)
	else:
		sp.texture = Placeholders.seta(Vector2i(64, 16))
		if team == "enemy":
			sp.modulate = Color(0.6, 1.0, 0.9)
	sp.position = Vector2(0, -30)  # só o desenho sobe até o peito; a colisão fica no chão
	add_child(sp)
	body_entered.connect(_on_body)

func _physics_process(delta: float) -> void:
	var passo := velocity * delta
	global_position += passo
	_viajado += passo.length()
	if _viajado >= max_dist:
		queue_free()

func _on_body(corpo: Node) -> void:
	if corpo.has_method("take_damage"):
		corpo.take_damage(damage, global_position)
	queue_free()
