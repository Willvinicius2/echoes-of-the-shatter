extends SceneTree
## Vídeo da escalada de poder do Arqueiro no jogo real (cena principal, horda de verdade, autocast ligado):
## três trechos legendados com 4 habilidades de elementos diferentes: nível 1, nível 8 e nível 15. Precisa de janela (xvfb):
##   godot --rendering-driver opengl3 --path godot --write-movie saida.avi --fixed-fps 30 --resolution 1280x720 \
##         --script res://scripts2d/tools/video_poder_2d.gd -- 20
## Argumento: segundos por trecho. Com `foto pasta` no lugar, grava PNGs (um a cada 15 quadros).
const MainScene = preload("res://scenes2d/Main2D.tscn")
const SKILLS := ["icicle_lance", "toxic_mines", "storm_tornado", "flecha_meteoro"]
var run
var p
var legenda: Label

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var foto: bool = args.size() > 0 and args[0] == "foto"
	var pasta: String = args[1] if foto and args.size() > 1 else ""
	var dur: float = float(args[0]) if args.size() > 0 and not foto else 20.0
	var main = MainScene.instantiate()
	root.add_child(main)
	await physics_frame
	run = main.run
	run.menus.fechar()
	run.estado = run.Estado.LUTA
	paused = false
	p = run.player
	p.god_mode = true
	var ui := CanvasLayer.new()
	ui.layer = 50
	root.add_child(ui)
	legenda = Label.new()
	legenda.position = Vector2(40, 24)
	legenda.add_theme_font_size_override("font_size", 34)
	legenda.add_theme_color_override("font_color", Color(1, 0.95, 0.8))
	legenda.add_theme_color_override("font_outline_color", Color(0, 0, 0))
	legenda.add_theme_constant_override("outline_size", 8)
	ui.add_child(legenda)
	if foto:
		DirAccess.make_dir_recursive_absolute(pasta)
	var h: RefCounted = p.habilidades
	var niveis := [[1, 1], [8, 2], [15, 3]]   # [nível do jogador, nível das habilidades]
	for t in niveis.size():
		var nv: int = niveis[t][0]
		p.set_meta("nivel_forcado", nv)
		for id in SKILLS:
			_aprender(h, id, niveis[t][1])
		for s in h.SLOTS:
			h.equipar(s, "")
		for s in (1 if nv == 1 else (3 if nv == 8 else 4)):
			h.equipar(s, SKILLS[s])
		legenda.text = "Poder de nível %d (simulado)" % nv
		for i in int(dur * float(Engine.physics_ticks_per_second)):
			if run.ui.aberta:
				run.ui.escolher(0)
			await physics_frame
			if foto and i % 15 == 0 and i > 0:
				await RenderingServer.frame_post_draw
				root.get_viewport().get_texture().get_image().save_png("%s/n%02d_%03d.png" % [pasta, nv, i / 15])
	quit()

func _aprender(h: RefCounted, id: String, alvo: int) -> void:
	var pai: String = h.defs[id]["pai"]
	if pai != "" and h.nivel(pai) == 0:
		_aprender(h, pai, 1)
	while h.nivel(id) < alvo:
		h.ganhar_pontos(int(h.defs[id].get("pontos", 1)))
		if not h.aprender(id):
			break
