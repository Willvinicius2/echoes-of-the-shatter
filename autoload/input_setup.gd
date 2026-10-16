extends Node
## Registra as ações do InputMap se ainda não existirem (todo input do jogo usa ações nomeadas).


func _enter_tree() -> void:
	register_actions()


func register_actions() -> void:
	_key("move_up", KEY_W)
	_key("move_down", KEY_S)
	_key("move_left", KEY_A)
	_key("move_right", KEY_D)
	_mouse("attack_basic", MOUSE_BUTTON_LEFT)
	_mouse("skill_1", MOUSE_BUTTON_RIGHT)
	_key("skill_2", KEY_Q)
	_key("skill_3", KEY_E)
	_key("skill_4", KEY_R)
	_key("skill_5", KEY_F)
	_key("dodge", KEY_SPACE)
	_key("potion_1", KEY_1)
	_key("potion_2", KEY_2)


func _key(action: String, keycode: Key) -> void:
	if InputMap.has_action(action):
		return
	InputMap.add_action(action)
	var ev: InputEventKey = InputEventKey.new()
	ev.physical_keycode = keycode
	InputMap.action_add_event(action, ev)


func _mouse(action: String, button: MouseButton) -> void:
	if InputMap.has_action(action):
		return
	InputMap.add_action(action)
	var ev: InputEventMouseButton = InputEventMouseButton.new()
	ev.button_index = button
	InputMap.action_add_event(action, ev)
