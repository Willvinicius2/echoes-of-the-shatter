extends SceneTree
# Debug: close da mao esquerda. Uso: -- pasta estado(arco|shoot) 
var cam: Camera3D
var n: Node3D
func _init() -> void:
	var a := OS.get_cmdline_user_args()
	var pasta: String = a[0]
	var est: String = a[1] if a.size() > 1 else "arco"
	var raiz := Node3D.new(); root.add_child(raiz)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR; env.background_color = Color("5A5A60")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR; env.ambient_light_color = Color(0.7, 0.7, 0.75)
	var we := WorldEnvironment.new(); we.environment = env; raiz.add_child(we)
	var sol := DirectionalLight3D.new(); sol.rotation_degrees = Vector3(-50, 30, 0); raiz.add_child(sol)
	n = load("res://scenes/arqueiro/ArqueiroUnico.tscn").instantiate()
	n.rotation_degrees = Vector3(0, -90, 0); n.scale = Vector3.ONE * 1.6
	raiz.add_child(n)
	cam = Camera3D.new(); cam.fov = 30; raiz.add_child(cam)
	await create_timer(0.5).timeout
	if est == "shoot":
		n.call("tocar", "shoot"); n.call("mirar", 1.0, false); n.set("segurando", true)
	else:
		n.call("tocar", "arco"); n.set("segurando", true)
	await create_timer(2.0).timeout
	var sk := n.find_child("Skeleton3D", true, false) as Skeleton3D
	var h := sk.global_transform * sk.get_bone_global_pose(sk.find_bone("mixamorig_LeftHand")).origin
	for v in [["a", 0.0], ["b", 90.0], ["c", 180.0], ["d", 270.0]]:
		var yaw := deg_to_rad(v[1])
		cam.global_position = h + Vector3(sin(yaw) * 0.5, 0.15, cos(yaw) * 0.5)
		cam.look_at(h, Vector3.UP)
		await create_timer(0.1).timeout
		await RenderingServer.frame_post_draw
		get_root().get_viewport().get_texture().get_image().save_png("%s/mao_%s_%s.png" % [pasta, est, v[0]])
	quit()
