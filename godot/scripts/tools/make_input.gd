# Grava as ações de entrada do arqueiro em project.godot.  godot --headless --path godot --script res://scripts/tools/make_input.gd
extends SceneTree

func tecla(code: int) -> InputEventKey:
	var e := InputEventKey.new(); e.physical_keycode = code; return e
func botao(i: int) -> InputEventJoypadButton:
	var e := InputEventJoypadButton.new(); e.button_index = i; return e
func eixo(a: int, v: float) -> InputEventJoypadMotion:
	var e := InputEventJoypadMotion.new(); e.axis = a; e.axis_value = v; return e
func mouse(b: int) -> InputEventMouseButton:
	var e := InputEventMouseButton.new(); e.button_index = b; return e

func acao(nome: String, eventos: Array, dz: float = 0.2) -> void:
	ProjectSettings.set_setting("input/" + nome, {"deadzone": dz, "events": eventos})

func _init() -> void:
	acao("move_left", [tecla(KEY_A), tecla(KEY_LEFT), eixo(JOY_AXIS_LEFT_X, -1.0)])
	acao("move_right", [tecla(KEY_D), tecla(KEY_RIGHT), eixo(JOY_AXIS_LEFT_X, 1.0)])
	acao("move_up", [tecla(KEY_W), tecla(KEY_UP), eixo(JOY_AXIS_LEFT_Y, -1.0)])
	acao("move_down", [tecla(KEY_S), tecla(KEY_DOWN), eixo(JOY_AXIS_LEFT_Y, 1.0)])
	acao("aim_left", [eixo(JOY_AXIS_RIGHT_X, -1.0)])
	acao("aim_right", [eixo(JOY_AXIS_RIGHT_X, 1.0)])
	acao("aim_up", [eixo(JOY_AXIS_RIGHT_Y, -1.0)])
	acao("aim_down", [eixo(JOY_AXIS_RIGHT_Y, 1.0)])
	acao("dodge", [tecla(KEY_SPACE), botao(JOY_BUTTON_B)], 0.5)
	acao("shoot", [mouse(MOUSE_BUTTON_LEFT), eixo(JOY_AXIS_TRIGGER_RIGHT, 1.0), botao(JOY_BUTTON_RIGHT_SHOULDER)], 0.5)
	acao("toggle_camera", [tecla(KEY_C)], 0.5)
	acao("debug_dano", [tecla(KEY_H)], 0.5)
	acao("renascer", [tecla(KEY_R)], 0.5)
	ProjectSettings.set_setting("application/run/main_scene", "res://scenes/cripta/CriptaJogavel.tscn")
	print(ProjectSettings.save())
	quit()
