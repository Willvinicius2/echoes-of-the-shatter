extends SceneTree
## Mede o tempo de montar a fase aberta (headless):
##   godot --headless --path godot --script res://scripts2d/tools/tempo_fase_2d.gd
const RoomScript = preload("res://scripts2d/room_2d.gd")

func _initialize() -> void:
	var t0 := Time.get_ticks_msec()
	var sala = RoomScript.new()
	root.add_child(sala)
	sala.carregar("res://data2d/rooms/fase_1.txt")
	var t1 := Time.get_ticks_msec()
	var alvo := Node2D.new()
	root.add_child(alvo)
	sala.colocar_props(alvo)
	print("carregar: %d ms, props: %d ms, nós: %d" % [t1 - t0, Time.get_ticks_msec() - t1, sala.get_child_count() + alvo.get_child_count()])
	quit()
