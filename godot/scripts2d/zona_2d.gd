extends Node2D
## Zona no chão criada por habilidades: chuva (dano em pulsos), fumaça (lentidão) e armadilha (dispara uma vez).
## Parâmetros vêm da linha da habilidade em data2d/habilidades_*.csv, já escalonada pelo nível.

const Feel = preload("res://scripts2d/feel_2d.gd")
const Vfx = preload("res://scripts2d/vfx_2d.gd")

var tipo := "chuva"
var raio := 100.0
var duracao := 2.0
var dano := 0.0
var pulsos := 1          # chuva: quantos pulsos de dano
var valor := 0.0         # fumaça: fração de velocidade perdida
var cor := Color(0.8, 0.7, 0.3)
var _t := 0.0
var _proximo := 0
var _gatilho := 18.0     # armadilha: vida máxima se ninguém pisar

func setup(t: String, pos: Vector2, r: float, dur: float, dmg: float, c: Color) -> void:
	tipo = t
	global_position = pos
	raio = r
	duracao = dur
	dano = dmg
	cor = c
	z_index = -1

func _ready() -> void:
	Vfx.anel_entrada(get_parent(), global_position, raio, cor)   # a zona nasce com anel de entrada (doc 33 seção 2)

func _alvos(r: float) -> Array:
	var out := []
	for n in get_tree().get_nodes_in_group("hurtable"):
		if n is Node2D and n.global_position.distance_to(global_position) <= r:
			out.append(n)
	return out

func _physics_process(delta: float) -> void:
	_t += delta
	queue_redraw()
	match tipo:
		"chuva":
			while _proximo < pulsos and _t >= duracao * _proximo / float(pulsos):
				_proximo += 1
				for n in _alvos(raio):
					n.take_damage(dano, global_position)
				Feel.impacto(get_parent(), global_position + Vector2(randf_range(-raio, raio), randf_range(-raio, raio)) * 0.5, cor)
			if _t >= duracao:
				queue_free()
		"fumaca":
			for n in _alvos(raio):
				if n.has_method("aplicar_status"):
					n.aplicar_status("lentidao", 0.3, valor)
			if _t >= duracao:
				queue_free()
		"armadilha":
			var pisou := _alvos(raio * 0.45)
			if not pisou.is_empty():
				for n in _alvos(raio):
					n.take_damage(dano, global_position)
					if n.has_method("aplicar_status"):
						n.aplicar_status("atordoamento", duracao, 0.0)
				Feel.impacto(get_parent(), global_position, cor, Vector2.ZERO, raio / 40.0)
				queue_free()
			elif _t >= _gatilho:
				queue_free()

func _draw() -> void:
	var a := 0.18 + 0.08 * sin(_t * 8.0)
	var apaga := Vfx.fade_zona(_t, duracao) if tipo != "armadilha" else 1.0   # some em fade, nunca de uma vez
	draw_circle(Vector2.ZERO, raio, Color(cor.r, cor.g, cor.b, a * apaga))
	draw_arc(Vector2.ZERO, raio, 0.0, TAU, 40, Color(cor.r, cor.g, cor.b, 0.7 * apaga), 2.0)
