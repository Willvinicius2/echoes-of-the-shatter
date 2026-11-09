extends SceneTree
## Captura da corrida do arqueiro em 8 direções (precisa de janela): godot --path godot --script res://scripts2d/tools/captura_andar_2d.gd -- pasta [segundos_por_direcao=2]
## Chão com grade de pontos para ver o deslize dos pés; o arqueiro anda sozinho (auto_move) e a câmera o segue.
## Salva `pasta/andar_<n>.png` a cada 4 passos físicos (junte com ffmpeg a 15 fps).
const PlayerScript = preload("res://scripts2d/player_2d.gd")

const DIRS := [Vector2.DOWN, Vector2(1, 1), Vector2.RIGHT, Vector2(1, -1), Vector2.UP, Vector2(-1, -1), Vector2.LEFT, Vector2(-1, 1)]

class Grade extends Node2D:
	func _draw() -> void:
		for x in range(-60, 61):
			for y in range(-60, 61):
				draw_circle(Vector2(x, y) * 48.0, 2.0, Color(0.15, 0.18, 0.1))

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var pasta: String = args[0] if args.size() > 0 else "andar"
	var seg: float = float(args[1]) if args.size() > 1 else 2.0
	DirAccess.make_dir_recursive_absolute(pasta)
	var mundo := Node2D.new()
	root.add_child(mundo)
	var chao := ColorRect.new()
	chao.color = Color(0.30, 0.34, 0.22)
	chao.size = Vector2(6000, 6000)
	chao.position = Vector2(-3000, -3000)
	chao.z_index = -10
	mundo.add_child(chao)
	mundo.add_child(Grade.new())
	var cam := Camera2D.new()
	cam.zoom = Vector2(2.2, 2.2)
	mundo.add_child(cam)
	cam.make_current()
	var p = PlayerScript.new()
	p.god_mode = true
	mundo.add_child(p)
	await physics_frame
	var passos := int(seg * float(Engine.physics_ticks_per_second))
	var n := 0
	var t := 0
	for d in DIRS:
		p.auto_move = d.normalized()
		for k in passos:
			await physics_frame
			cam.position = p.global_position
			t += 1
			if t % 4 == 0:
				await RenderingServer.frame_post_draw
				n += 1
				root.get_viewport().get_texture().get_image().save_png("%s/andar_%d.png" % [pasta, n])
	quit()
