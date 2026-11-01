extends SceneTree
## Capturas da HUD para escolher variantes (faixa_modo de hud_layout.csv) e ver os slots das ativas:
##   godot --path godot --script res://scripts2d/tools/captura_hud_variantes_2d.gd -- saida.png [faixa_modo] [classe] [vida_pct] [chefe]
## classe = arqueiro (slots de ativa vazios) ou guerreiro (2 ativas aprendidas, uma em recarga, outra sem ímpeto).
const RunScene = preload("res://scenes2d/Run2D.tscn")
const Classe = preload("res://scripts2d/classe_2d.gd")

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var saida: String = args[0] if args.size() > 0 else "captura_hud_variante.png"
	var modo: float = float(args[1]) if args.size() > 1 else 0.0
	var classe: String = args[2] if args.size() > 2 else "arqueiro"
	var vida: float = float(args[3]) / 100.0 if args.size() > 3 else 0.6
	Classe.atual = classe
	var run = RunScene.instantiate()
	run.com_menu = false
	root.add_child(run)
	await physics_frame
	var chefe := args.size() > 4 and args[4] == "chefe"
	run.player.god_mode = true
	run.hud._lay["faixa_modo"] = modo
	var h = run.player.habilidades
	if h != null:   # as 3 primeiras ativas da classe, nos slots Q, E e F
		h.ganhar_pontos(30)
		var n := 0
		for id in h.ordem:
			if n < 3 and h.eh_ativa(id) and h.pode_aprender(id) and h.aprender(id):
				n += 1
	for i in 40:
		await physics_frame
	if chefe:
		var b: Node2D = load("res://scripts2d/boss_2d.gd").new()
		run.atores.add_child(b)
		b.setup("crypt_guardian", run.player, run.player.global_position + Vector2(0, -260))
		b.died.connect(run._on_inimigo_morto)
		for i in 240:
			await physics_frame
	var p = run.player
	p.hp = p.stats["hp_max"] * vida
	p.god_mode = true
	run.hud._hp_fantasma = minf(1.0, vida + 0.1)
	p.dodge_cd = p.stats["dodge_cooldown"] * 0.55
	if "impeto" in p:
		p.impeto = 10.0
	if p.habilidades != null and p.habilidades.slots[0] != "":
		if "mana" in p:
			p.mana = p.stats["mana_max"] * 0.7
		p.habilidades.usar(0, p, Vector2.RIGHT)   # põe a primeira ativa em recarga de verdade (o core guarda o tempo)
	run.hud.tempo = 83.0
	run.hud.xp_demo = {"level": 4, "xp": 37, "xp_next": 60}
	for i in 6:
		await physics_frame
	await RenderingServer.frame_post_draw
	root.get_viewport().get_texture().get_image().save_png(saida)
	quit()
