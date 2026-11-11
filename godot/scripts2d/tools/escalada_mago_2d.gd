extends SceneTree
## Escalada de poder do Mago (precisa de janela): godot --path godot --resolution 1280x720 --script res://scripts2d/tools/escalada_mago_2d.gd -- pasta [segundos_por_nivel=7]
## Monta o Mago contra uma horda parada e roda três trechos seguidos, nos níveis 1, 8 e 16 da corrida, cada um com mais magias,
## níveis de magia e espíritos em volta. Salva pasta/nivel_<N>_<k>.png (3 quadros por trecho); com --write-movie vira o vídeo.
const PlayerScript = preload("res://scripts2d/mago_2d.gd")
const EnemyScript = preload("res://scripts2d/enemy_2d.gd")

const TRECHOS := [
	{"nivel": 1, "eco": "", "skills": [], "niveis": 1},
	{"nivel": 8, "eco": "eco_m_trovao", "skills": ["skill.mage.chain_lightning", "skill.mage.fireball"], "niveis": 1},
	{"nivel": 16, "eco": "eco_m_trovao", "skills": ["skill.mage.chain_lightning", "skill.mage.fireball", "skill.mage.plague_cloud", "skill.mage.frost_bolt", "skill.mage.thunderstorm", "skill.mage.meteor", "skill.mage.blizzard", "skill.mage.spore_mark"], "niveis": 3},
]

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var pasta: String = args[0] if args.size() > 0 else "escalada"
	var seg: float = float(args[1]) if args.size() > 1 else 7.0
	DirAccess.make_dir_recursive_absolute(pasta)
	var mundo := Node2D.new()
	root.add_child(mundo)
	var chao := ColorRect.new()
	chao.color = Color(0.30, 0.34, 0.22)
	chao.size = Vector2(4000, 4000)
	chao.position = Vector2(-2000, -2000)
	chao.z_index = -10
	mundo.add_child(chao)
	var cam := Camera2D.new()
	cam.position = Vector2(150, 0)
	cam.zoom = Vector2(1.3, 1.3)
	mundo.add_child(cam)
	cam.make_current()
	var p = PlayerScript.new()
	p.god_mode = true
	mundo.add_child(p)
	await physics_frame
	var h: RefCounted = p.habilidades
	h.ganhar_pontos(999)
	var rng := RandomNumberGenerator.new()
	rng.seed = 11
	var inimigos: Array = []
	for i in 16:
		var e = EnemyScript.new()
		mundo.add_child(e)
		e.setup("hollow_sentinel", p, Vector2(rng.randf_range(160.0, 520.0), rng.randf_range(-240.0, 240.0)))
		e.hp = 99999.0
		e.hp_max = 99999.0
		e.set("_aggro", 0.0)
		e.set("_speed", 0.0)
		e.set("_dano_zero", true)
		e.stats["damage"] = 0.0
		inimigos.append(e)
	var quadros_seg := int(seg * 60.0)
	for t in TRECHOS:
		p.nivel_corrida = t["nivel"]
		p.afinidade = t["eco"]
		for id in t["skills"]:
			_aprender(h, id, int(t["niveis"]))
		var i := 0
		for id in t["skills"]:
			if h.defs[id]["tipo"] == "ativa" and i < 4:
				h.equipar(i, id)
				i += 1
		for j in range(i, 4):
			h.equipar(j, "")
		for k in 3:
			for f in quadros_seg / 3:
				await physics_frame
			await RenderingServer.frame_post_draw
			root.get_viewport().get_texture().get_image().save_png("%s/nivel_%d_%d.png" % [pasta, t["nivel"], k + 1])
	quit()

func _aprender(h: RefCounted, id: String, alvo: int) -> void:
	var pai: String = h.defs[id]["pai"]
	if pai != "" and h.nivel(pai) == 0:
		_aprender(h, pai, 1)
	while h.nivel(id) < mini(alvo, int(h.defs[id]["nivel_max"])):
		if not h.aprender(id):
			break
