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
	run.indice = 3 if chefe else 2
	if chefe:
		run._carregar_sala(3, {"id": "boss", "tipo": "combate", "room": "res://data2d/rooms/sala_boss.txt", "enemies": "crypt_guardian:1"})
	else:
		run._carregar_sala(2)
	run.player.god_mode = true
	run.hud._lay["faixa_modo"] = modo
	if classe == "guerreiro":
		var sk = run.upgrades
		for id in ["w_charge", "w_keen_edge", "w_heavy_slash", "w_iron_skin", "w_shield_bash"]:
			sk.escolher(id, run.player)
	elif "habilidades" in run.player and run.player.habilidades != null:   # arqueiro/mago: 3 ativas do runtime
		var h = run.player.habilidades
		h.ganhar_pontos(20)
		var n := 0
		for id in h.ordem:
			if n < 3 and h.eh_ativa(id) and h.aprender(id):
				n += 1
	for i in 40:
		await physics_frame
	var p = run.player
	p.hp = p.stats["hp_max"] * vida
	run.hud._hp_fantasma = minf(1.0, vida + 0.1)
	p.dodge_cd = p.stats["dodge_cooldown"] * 0.55
	if classe == "guerreiro":
		p._cds["w_charge"] = run.upgrades.recarga("w_charge") * 0.6
		p.impeto = 10.0
	elif "habilidades" in p and p.habilidades != null and p.habilidades.slots[0] != "":
		p.habilidades.recargas[p.habilidades.slots[0]] = float(p.habilidades.defs[p.habilidades.slots[0]]["cd"]) * 0.6
	run.hud.tempo = 83.0
	for i in 6:
		await physics_frame
	await RenderingServer.frame_post_draw
	root.get_viewport().get_texture().get_image().save_png(saida)
	quit()
