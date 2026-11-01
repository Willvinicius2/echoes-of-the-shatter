extends Node2D
## Gema de XP ou baú de elite caído no chão (pacote H4 do plano 31). O valor de XP vem do core
## (`nivel_xp_da_morte`); aqui só voa para o jogador quando ele chega perto (ímã) e avisa a coleta.
## Distâncias e velocidade em data2d/run_settings.csv (gem_magnet_radius, gem_pickup_radius, gem_speed).
## Desenho provisório em código: a arte final dos itens é do pacote H6.

signal coletada(gema)

var tipo := "xp"          # "xp" ou "bau"
var valor := 0            # XP da gema (0 no baú)
var alvo: Node2D
var ima := 140.0
var pegar := 24.0
var velocidade := 520.0
var atraida := false      # true: voa para o jogador de qualquer distância (onda vencida, fim da fase)
var _t := 0.0

func setup(t: String, v: int, pos: Vector2, jogador: Node2D, cfg: Dictionary) -> void:
	tipo = t
	valor = v
	global_position = pos + Vector2(randf_range(-10.0, 10.0), randf_range(-10.0, 10.0))
	alvo = jogador
	ima = float(cfg.get("gem_magnet_radius", ima)) * (1.6 if tipo != "xp" else 1.0)
	pegar = float(cfg.get("gem_pickup_radius", pegar))
	velocidade = float(cfg.get("gem_speed", velocidade))
	z_index = 0
	add_to_group("coletaveis")

func _physics_process(delta: float) -> void:
	_t += delta
	queue_redraw()
	if alvo == null or not is_instance_valid(alvo):
		return
	var para := alvo.global_position - global_position
	var d := para.length()
	if d <= pegar:
		coletada.emit(self)
		queue_free()
		return
	if atraida or d <= ima:
		atraida = true   # pegou no ímã: não para mais
		global_position += para / maxf(d, 0.001) * minf(d, (velocidade + _t * 60.0) * delta)

func _draw() -> void:
	var sobe := sin(_t * 4.0) * 2.0
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	draw_circle(Vector2(0, 4), 7.0 if tipo == "xp" else 14.0, Color(0, 0, 0, 0.3))
	if tipo == "bau":
		var r := Rect2(-13, -18 + sobe, 26, 18)
		draw_rect(r, Color(0.36, 0.22, 0.12))
		draw_rect(Rect2(-13, -18 + sobe, 26, 6), Color(0.5, 0.32, 0.16))
		draw_rect(r, Color(0.95, 0.75, 0.3), false, 2.0)
		draw_rect(Rect2(-3, -13 + sobe, 6, 6), Color(1.0, 0.85, 0.35))
		draw_circle(Vector2(0, -10 + sobe), 18.0, Color(1.0, 0.8, 0.3, 0.12 + 0.06 * sin(_t * 6.0)))
		return
	if tipo == "habilidade":
		var c2 := Color(1.0, 0.6, 0.15)
		var q := PackedVector2Array([Vector2(0, -12 + sobe), Vector2(8, -4 + sobe), Vector2(5, 6 + sobe), Vector2(-5, 6 + sobe), Vector2(-8, -4 + sobe)])
		draw_circle(Vector2(0, -2 + sobe), 16.0, Color(c2, 0.18))
		draw_colored_polygon(q, c2)
		draw_polyline(q + PackedVector2Array([q[0]]), c2.lightened(0.6), 1.5)
		return
	var grande := valor >= 3
	var s := 7.0 if grande else 5.0
	var c := Color(0.95, 0.55, 1.0) if grande else Color(0.35, 0.95, 0.85)
	var pts := PackedVector2Array([Vector2(0, -s * 1.5 + sobe - 6), Vector2(s, sobe - 6), Vector2(0, s * 1.5 + sobe - 6), Vector2(-s, sobe - 6)])
	draw_circle(Vector2(0, sobe - 6), s * 1.9, Color(c, 0.15))
	draw_colored_polygon(pts, c)
	draw_polyline(pts + PackedVector2Array([pts[0]]), c.lightened(0.5), 1.5)
