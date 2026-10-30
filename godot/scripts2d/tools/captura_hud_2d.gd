extends SceneTree
## Captura só da HUD (sem menu), com vida parcial, recarga e upgrades, para revisão de arte:
##   godot --path godot --script res://scripts2d/tools/captura_hud_2d.gd -- saida.png [sala] [vida_pct] [chefe]
const RunScene = preload("res://scenes2d/Run2D.tscn")

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var saida: String = args[0] if args.size() > 0 else "captura_hud.png"
	var sala: int = int(args[1]) if args.size() > 1 else 0
	var vida: float = float(args[2]) / 100.0 if args.size() > 2 else 0.6
	var run = RunScene.instantiate()
	run.com_menu = false
	root.add_child(run)
	await physics_frame
	if sala > 0:
		run.indice = sala
		run._carregar_sala(sala)
	run.player.god_mode = true
	for id in ["power", "haste", "swift"]:
		run.upgrades.niveis[id] = 2
		if not run.upgrades.ordem.has(id):
			run.upgrades.ordem.append(id)
	for i in 40:
		await physics_frame
	run.player.hp = run.player.stats["hp_max"] * vida
	run.hud._hp_fantasma = minf(1.0, vida + 0.1)
	run.player.dodge_cd = run.player.stats["dodge_cooldown"] * 0.55
	run.hud.tempo = 83.0
	for i in 10:
		await physics_frame
	await RenderingServer.frame_post_draw
	root.get_viewport().get_texture().get_image().save_png(saida)
	quit()
