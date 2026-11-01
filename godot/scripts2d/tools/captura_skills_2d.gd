extends SceneTree
## Captura de habilidades (precisa de janela): godot --path godot --script res://scripts2d/tools/captura_skills_2d.gd -- pasta elemento [quadros]
## Elementos: raio, veneno, gelo, fogo, base. Monta um chão liso, o arqueiro com as habilidades da árvore e 5 inimigos parados à direita,
## deixa o autocast jogar e salva `pasta/<elemento>_<n>.png` nos quadros pedidos (juntar com ffmpeg). Ferramenta de revisão visual (doc 33).
const PlayerScript = preload("res://scripts2d/player_2d.gd")
const EnemyScript = preload("res://scripts2d/enemy_2d.gd")

const ARVORES := {
	"base": ["power_shot"],
	"raio": ["shock_arrow", "chain_lightning", "storm_tornado", "herald_thunder"],
	"veneno": ["poison_arrow", "venom_orb", "corrosive_rain", "herald_plague"],
	"gelo": ["frost_arrow", "glacial_shard", "ice_prison", "herald_ice"],
	"fogo": ["flecha_ardente", "flecha_meteoro", "muralha_brasas", "arauto_cinzas"],
}

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var pasta: String = args[0] if args.size() > 0 else "skills"
	var el: String = args[1] if args.size() > 1 else "raio"
	var quadros := PackedInt32Array([40, 70, 100, 130, 160, 200, 240])
	if args.size() > 2:
		quadros = PackedInt32Array()
		for s in args[2].split(","):
			quadros.append(int(s))
	DirAccess.make_dir_recursive_absolute(pasta)
	var mundo := Node2D.new()
	root.add_child(mundo)
	var chao := ColorRect.new()
	chao.color = Color(0.30, 0.34, 0.22)
	chao.size = Vector2(3000, 3000)
	chao.position = Vector2(-1500, -1500)
	chao.z_index = -10
	mundo.add_child(chao)
	var cam := Camera2D.new()
	cam.position = Vector2(180, 0)
	cam.zoom = Vector2(1.6, 1.6)
	mundo.add_child(cam)
	cam.make_current()
	var p = PlayerScript.new()
	p.god_mode = true
	mundo.add_child(p)
	await physics_frame
	var h: RefCounted = p.habilidades
	h.ganhar_pontos(300)
	for id in ARVORES[el]:
		_aprender(h, id)
	var i := 0
	for id in ARVORES[el]:
		if h.defs[id]["tipo"] == "ativa" and i < 4:
			h.equipar(i, id)
			i += 1
	p.has_method("_atualizar_heralds") and p.call("_atualizar_heralds")
	var pos := [Vector2(240, -80), Vector2(300, 20), Vector2(380, -40), Vector2(440, 70), Vector2(520, 0)]
	for q in pos:
		var e = EnemyScript.new()
		mundo.add_child(e)
		e.setup("hollow_sentinel", p, q)
		e.hp = 99999.0
		e.hp_max = 99999.0
		e.stats["aggro"] = 0.0
		e.stats["damage"] = 0.0
	var f := 0
	for n in quadros.size():
		while f < quadros[n]:
			f += 1
			await physics_frame
		await RenderingServer.frame_post_draw
		root.get_viewport().get_texture().get_image().save_png("%s/%s_%d.png" % [pasta, el, n + 1])
	quit()

func _aprender(h: RefCounted, id: String) -> void:
	var pai: String = h.defs[id]["pai"]
	if pai != "" and h.nivel(pai) == 0:
		_aprender(h, pai)
	if h.nivel(id) == 0:
		h.aprender(id)
