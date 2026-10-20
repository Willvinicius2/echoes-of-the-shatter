# Cria os materiais de pedra triplanar usados pelos módulos glb (remap em art/models/*.glb.import).
# godot --headless --path godot --script res://scripts/tools/make_materiais.gd
extends SceneTree

func _init() -> void:
	DirAccess.make_dir_recursive_absolute("res://art/materials")
	_pedra("M_Pedra", Color(0.46, 0.46, 0.5))
	_pedra("M_PedraEscura", Color(0.2, 0.2, 0.24))
	quit()

func _pedra(nome: String, cor: Color) -> void:
	var m := StandardMaterial3D.new()
	m.albedo_texture = load("res://art/textures/T_Cripta_Pedra.png") as Texture2D
	m.albedo_color = cor; m.roughness = 0.8
	m.uv1_triplanar = true; m.uv1_world_triplanar = false; m.uv1_scale = Vector3.ONE / 2.5
	ResourceSaver.save(m, "res://art/materials/%s.tres" % nome)
