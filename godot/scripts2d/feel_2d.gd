extends RefCounted
## Game feel: hit stop, tremor de câmera, número de dano e faísca de impacto. Números em data2d/feel.csv.

const Feel = preload("res://scripts2d/feel_2d.gd")
const Csv = preload("res://scripts2d/csv2d.gd")
const DamageNumber = preload("res://scripts2d/damage_number_2d.gd")
const ImpactFx = preload("res://scripts2d/impact_fx_2d.gd")

static var _cfg := {}
static var _stop_ate := 0   # ticks (ms) em que o hit stop atual termina

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
	var fim := Time.get_ticks_msec() + int(ms)
	if fim <= _stop_ate:
		return
	_stop_ate = fim
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
static func numero(alvo: Node2D, valor: float, cor: Color, grande := false) -> void:
	var pai := alvo.get_parent()
	if pai == null:
		return
	var n := DamageNumber.new()
	n.texto = str(int(round(valor)))
	n.cor = cor
	n.tamanho = cfg()["dmg_number_size_kill" if grande else "dmg_number_size"]
	n.tempo = cfg()["dmg_number_time"]
	n.subida = cfg()["dmg_number_rise"]
	pai.add_child(n)
	n.global_position = alvo.global_position + Vector2(randf_range(-10.0, 10.0), -60.0)

## Faísca de impacto em `pos` (mundo), filha de `pai`.
static func impacto(pai: Node, pos: Vector2, cor: Color) -> void:
	if pai == null:
		return
	var fx := ImpactFx.new()
	fx.cor = cor
	fx.tempo = cfg()["impact_time"]
	pai.add_child(fx)
	fx.global_position = pos
