# Câmera de estudo do mapa: WASD move no chão, Q/E gira, roda do mouse dá zoom. Equivalente em GDScript do CameraEstudio.cs.
extends Camera3D

const T := preload("res://scripts/terreno/terreno_cripta.gd")

@export var Distancia := 26.0
@export var Yaw := 45.0
@export var Pitch := -52.0
@export var Velocidade := 14.0
@export var Alvo := Vector3.ZERO
@export var seguir_chao := true   # a altura do alvo acompanha o terreno (andares)

func _ready() -> void:
	aplicar()

func _process(delta: float) -> void:
	var d := Vector2.ZERO
	if Input.is_key_pressed(KEY_W): d.y -= 1
	if Input.is_key_pressed(KEY_S): d.y += 1
	if Input.is_key_pressed(KEY_A): d.x -= 1
	if Input.is_key_pressed(KEY_D): d.x += 1
	if Input.is_key_pressed(KEY_Q): Yaw -= 60.0 * delta
	if Input.is_key_pressed(KEY_E): Yaw += 60.0 * delta
	var b := Basis.from_euler(Vector3(0, deg_to_rad(Yaw), 0))
	Alvo += b * Vector3(d.x, 0, d.y) * Velocidade * delta * (Distancia / 26.0)
	if seguir_chao: Alvo.y = lerpf(Alvo.y, T.chao(Alvo.x, -Alvo.z), 1.0 - exp(-6.0 * delta))
	aplicar()

func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed:
		if e.button_index == MOUSE_BUTTON_WHEEL_UP: Distancia = maxf(6.0, Distancia * 0.92)
		if e.button_index == MOUSE_BUTTON_WHEEL_DOWN: Distancia = minf(160.0, Distancia * 1.08)

func aplicar() -> void:
	var rot := Basis.from_euler(Vector3(deg_to_rad(Pitch), deg_to_rad(Yaw), 0))
	basis = rot
	position = Alvo + rot.z * Distancia
