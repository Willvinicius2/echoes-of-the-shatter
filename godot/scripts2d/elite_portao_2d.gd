extends RefCounted
## Visuais do elite do portão (luz própria e clarão de entrada), tirados de run_2d.gd. Valores em `config` (CSV).

const Feel = preload("res://scripts2d/feel_2d.gd")

## Luz própria do elite do portão (revisão do Jev: ele precisa se destacar do fundo): um halo aditivo laranja-vermelho preso a
## ele, que pulsa devagar, como brasa. Fica ATRÁS do sprite (revisão do crítico: por cima, a luz pintava o osso de laranja e
## apagava os olhos ciano): ilumina o chão em volta e recorta o elite contra ele. Some junto com ele.
static func luz(e: Node2D, config: Dictionary) -> void:
	var lado := float(config.get("gate_elite_luz_tamanho", 0.0))
	if lado <= 0.0:
		return
	var alfa := float(config.get("gate_elite_luz_alfa", 0.4))
	var halo := Sprite2D.new()
	halo.name = "LuzDoElite"
	halo.texture = Feel.ponto()
	halo.material = Feel.aditivo()
	halo.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	halo.show_behind_parent = true
	halo.modulate = Color(1.0, 0.42, 0.14, alfa)
	halo.scale = Vector2.ONE * lado / float(halo.texture.get_width())
	halo.position = Vector2(0, -28)
	e.add_child(halo)
	var tw := halo.create_tween().set_loops()
	tw.tween_property(halo, "modulate:a", alfa * 0.7, 0.9).set_trans(Tween.TRANS_SINE)
	tw.tween_property(halo, "modulate:a", alfa, 0.9).set_trans(Tween.TRANS_SINE)

## Clarão aditivo no portão: um halo e uma coluna de luz que sobem e somem durante a entrada (`dur` s).
static func clarao(room: Node, config: Dictionary, pos: Vector2, dur: float) -> void:
	var lado := float(config.get("gate_elite_flash_size", 420.0))
	var luz := Node2D.new()
	luz.name = "ClaraoPortao"
	luz.position = pos
	luz.z_index = 15
	luz.modulate = Color(1, 1, 1, 0)
	for forma in [Vector2(1.0, 0.7), Vector2(0.28, 1.6)]:   # halo achatado no chão e coluna alta
		var sp := Sprite2D.new()
		sp.texture = Feel.ponto()
		sp.material = Feel.aditivo()
		sp.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
		sp.modulate = Color(1.5, 1.25, 0.8)   # aditivo acima de 1: o portão estoura de luz
		sp.scale = forma * lado / float(sp.texture.get_width())
		sp.position = Vector2(0, -lado * forma.y * 0.35) if forma.y > 1.0 else Vector2.ZERO
		luz.add_child(sp)
	room.add_child(luz)
	luz.scale = Vector2(0.4, 0.4)
	var tw := luz.create_tween()
	tw.set_parallel(true)
	tw.tween_property(luz, "modulate:a", 1.0, dur * 0.35)
	tw.tween_property(luz, "scale", Vector2.ONE, dur * 0.35).set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_QUAD)
	tw.chain().tween_property(luz, "modulate:a", 0.0, dur * 0.65)
	tw.chain().tween_callback(luz.queue_free)
