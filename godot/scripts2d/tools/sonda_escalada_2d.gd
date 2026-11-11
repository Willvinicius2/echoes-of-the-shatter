extends SceneTree
## Diagnóstico da escalada de poder do Guerreiro (sem janela): joga a corrida com o bot esperto, invulnerável, e a cada
## 10 s de jogo imprime nível de XP, ativas equipadas (com nível e recarga) e quantos nós de efeito nasceram por segundo.
##   godot --headless --path godot --script res://scripts2d/tools/sonda_escalada_2d.gd -- [classe=guerreiro] [limite_s=420]
const Classe = preload("res://scripts2d/classe_2d.gd")
const RunScene = preload("res://scenes2d/Run2D.tscn")
const CARTAS_BOAS := ["multishot", "pierce", "wide_reach", "extra_shot", "swift_shots", "piercing_skills", "lingering", "haste", "power"]
var nascidos := 0
var run

func _contar(n: Node) -> void:
	if n is AnimatedSprite2D or n is Sprite2D or n is Line2D:
		nascidos += 1

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	Classe.atual = args[0] if args.size() > 0 else "guerreiro"
	var limite := float(args[1]) if args.size() > 1 else 420.0
	run = RunScene.instantiate()
	run.com_menu = false
	root.add_child(run)
	await physics_frame
	var p = run.player
	p.god_mode = true
	node_added.connect(_contar)
	var t := 0.0
	var prox := 10.0
	var e := 0.0
	var ult_nivel := 0
	while t < limite:
		await physics_frame
		t += 1.0 / 60.0
		if run.ui.aberta:
			run.ui.escolher(_carta())
		var mais_perto: Node2D = null
		for n in get_nodes_in_group("hurtable"):
			if mais_perto == null or n.global_position.distance_to(p.global_position) < mais_perto.global_position.distance_to(p.global_position):
				mais_perto = n
		p.auto_move = (mais_perto.global_position - p.global_position).normalized() if mais_perto != null and mais_perto.global_position.distance_to(p.global_position) > 60.0 else Vector2.ZERO
		if t >= prox:
			prox += 10.0
			var h = p.habilidades
			var s := []
			for id in h.slots:
				if id != "":
					s.append("%s L%d cd%.1f" % [id, h.nivel(id), float(h.def_nivel(id).get("cd", 0.0))])
			print("t=%3.0f nivel=%2d ativas=%d efeitos/s=%.1f vivos=%d | %s" % [t, run._nivel_atual(), s.size(), nascidos / 10.0, run.vivos, ", ".join(s)])
			nascidos = 0
	quit()

func _carta() -> int:
	var ids: Array = run.ui._ids
	var hab = run.player.habilidades
	if run.ui.modo == "gem" or run.ui.modo == "afinidade":
		for i in ids.size():
			if hab.defs.has(ids[i]) and hab.eh_ativa(ids[i]) and hab.nivel(ids[i]) == 0:
				return i
		for i in ids.size():
			if hab.defs.has(ids[i]) and hab.eh_ativa(ids[i]):
				return i
		return 0
	for b in CARTAS_BOAS:
		var k: int = ids.find(b)
		if k >= 0:
			return k
	return 0
