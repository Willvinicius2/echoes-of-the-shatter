# Cria os materiais de pedra suja (shader cripta_pedra) usados pelos módulos glb (remap em art/models/*.glb.import).
# godot --headless --path godot --script res://scripts/tools/make_materiais.gd
extends SceneTree

func _init() -> void:
	DirAccess.make_dir_recursive_absolute("res://art/materials")
	_pedra("M_Pedra", Color(0.50, 0.50, 0.54), 0.3, 0.4)
	_pedra("M_PedraEscura", Color(0.22, 0.22, 0.26), 0.25, 0.4)
	_pedra("M_Estatua", Color(0.32, 0.31, 0.31), 0.25, 0.9)
	quit()

func _pedra(nome: String, cor: Color, musgo: float, escala: float) -> void:
	var m := ShaderMaterial.new()
	m.shader = load("res://art/shaders/cripta_pedra.gdshader") as Shader
	m.set_shader_parameter("albedo_tex", load("res://art/textures/T_Cripta_Pedra.png"))
	m.set_shader_parameter("tint", cor)
	m.set_shader_parameter("moss_amount", musgo)
	m.set_shader_parameter("tex_scale", escala)
	ResourceSaver.save(m, "res://art/materials/%s.tres" % nome)
