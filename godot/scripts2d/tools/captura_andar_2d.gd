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
	var modo: String = args[2] if args.size() > 2 else "andar"
	var n := 0
	var t := 0
	if modo == "acao":
		# atirar e esquivar: corre para a direita mirando para a esquerda (tiro para trás), solta a mira e segue correndo
		# (volta a olhar o movimento), depois esquiva em três direções
		var tps := int(Engine.physics_ticks_per_second)
		var roteiro := [
			{"move": Vector2.RIGHT, "aim": Vector2.LEFT, "t": 2.0},
			{"move": Vector2.RIGHT, "aim": Vector2.ZERO, "t": 1.0},
			{"move": Vector2.DOWN, "aim": Vector2.UP, "t": 2.0},
			{"move": Vector2.ZERO, "aim": Vector2.ZERO, "t": 0.5},
		]
		for r in roteiro:
			p.auto_move = r["move"]
			p.auto_aim = r["aim"]
			for k in int(float(r["t"]) * tps):
				await physics_frame
				cam.position = p.global_position
				t += 1
				if t % 4 == 0:
					await RenderingServer.frame_post_draw
					n += 1
					root.get_viewport().get_texture().get_image().save_png("%s/andar_%d.png" % [pasta, n])
		p.auto_aim = Vector2.ZERO
		for d in [Vector2.RIGHT, Vector2(-1, -1), Vector2.DOWN]:
			p.auto_move = Vector2.ZERO
			p._aim = d
			p.call("_comecar_esquiva", d)
			for k in int(0.9 * tps):
				await physics_frame
				cam.position = p.global_position
				t += 1
				if t % 4 == 0:
					await RenderingServer.frame_post_draw
					n += 1
					root.get_viewport().get_texture().get_image().save_png("%s/andar_%d.png" % [pasta, n])
		quit()
		return
	var passos := int(seg * float(Engine.physics_ticks_per_second))
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
