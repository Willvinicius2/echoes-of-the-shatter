extends SceneTree
## Captura das magias do mago (precisa de janela): godot --path godot --script res://scripts2d/tools/captura_mago_2d.gd -- pasta grupo [quadros] [inimigos]
## Grupos: basico, eco_m_trovao, eco_m_peste, eco_m_gelo, eco_m_cinzas, fogo, fogo2, gelo, gelo2, raio, raio2, veneno.
## Monta um chão liso, o mago com as magias do grupo e inimigos parados à direita, deixa o autocast jogar e salva
## `pasta/<grupo>_<n>.png` nos quadros pedidos. Ferramenta de revisão visual, irmã da captura_skills_2d.gd do arqueiro.
const PlayerScript = preload("res://scripts2d/mago_2d.gd")
const EnemyScript = preload("res://scripts2d/enemy_2d.gd")

const ARVORES := {
	"basico": [],
	"eco_m_trovao": [], "eco_m_peste": [], "eco_m_gelo": [], "eco_m_cinzas": [],
	"fogo": ["skill.mage.fireball", "skill.mage.flame_breath", "skill.mage.fire_wall", "skill.mage.meteor", "arauto_cinzas"],
	"fogo2": ["skill.mage.inferno_nova"],
	"gelo": ["skill.mage.frost_bolt", "skill.mage.frost_nova", "skill.mage.blizzard", "skill.mage.glacial_spike", "herald_ice"],
	"gelo2": ["skill.mage.ice_barrier"],
	"raio": ["skill.mage.chain_lightning", "skill.mage.thunderstorm", "skill.mage.mana_surge", "herald_thunder"],
	"raio2": ["skill.mage.blink", "skill.mage.overload"],
	"veneno": ["skill.mage.plague_cloud", "skill.mage.spore_mark", "skill.mage.acid_pool", "herald_plague"],
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
	if el.begins_with("eco_"):
		p.afinidade = el
	if el.ends_with("2"):   # ult e magias manuais: a ferramenta aperta por elas
		p.set_meta("forcar_slots", true)
	for id in ARVORES[el]:
		_aprender(h, id)
	var i := 0
	for id in ARVORES[el]:
		if h.defs[id]["tipo"] == "ativa" and i < 4:
			h.equipar(i, id)
			i += 1
	for j in range(i, 4):   # o core equipa sozinho o que aprende (os pais também); só a skill pedida fica nos slots
		h.equipar(j, "")
	var qtd_inimigos: int = int(args[3]) if args.size() > 3 else 5
	if p.has_method("_atualizar_heralds"):
		p.call("_atualizar_heralds")
	var pos := [Vector2(240, -80), Vector2(300, 20), Vector2(380, -40), Vector2(440, 70), Vector2(520, 0)]
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	while pos.size() < qtd_inimigos:   # horda: espalhados num anel à direita, como na fase aberta
		pos.append(Vector2(rng.randf_range(200.0, 560.0), rng.randf_range(-160.0, 160.0)))
	for q in pos:
		var e = EnemyScript.new()
		mundo.add_child(e)
		e.setup("hollow_sentinel", p, q)
		e.hp = 99999.0
		e.hp_max = 99999.0
		e.set("_aggro", 0.0)   # parados: a captura mostra a magia, não a briga
		e.set("_speed", 0.0)
		e.stats["damage"] = 0.0
	var f := 0
	for n in quadros.size():
		while f < quadros[n]:
			f += 1
			if p.has_meta("forcar_slots") and f % 45 == 20:
				p.usar_habilidade((f / 45) % maxi(i, 1), {"dir": Vector2.RIGHT, "ponto": p.global_position + Vector2(260, 0)})
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
