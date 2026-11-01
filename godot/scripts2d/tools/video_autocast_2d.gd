extends SceneTree
## Vídeo do autocast na fase aberta: cada classe luta as primeiras ondas com o básico e as 4 ativas disparando
## sozinhos e a ult saindo uma vez na "tecla". Precisa de janela (xvfb):
##   godot --rendering-driver opengl3 --path godot --write-movie saida.avi --fixed-fps 30 --resolution 1280x720 \
##         --script res://scripts2d/tools/video_autocast_2d.gd -- 20 arqueiro mago guerreiro
## Primeiro argumento: segundos de vídeo por classe (a 30 fps). Os demais: classes.
const RunScene = preload("res://scenes2d/Run2D.tscn")
const Classe = preload("res://scripts2d/classe_2d.gd")
const Csv = preload("res://scripts2d/csv2d.gd")

var run
var p

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var dur: float = float(args[0]) if args.size() > 0 else 20.0
	var classes: Array = args.slice(1) if args.size() > 1 else Classe.CLASSES
	for c in classes:
		await _classe(c, dur)
	quit()

func _classe(c: String, dur: float) -> void:
	Classe.atual = c
	run = RunScene.instantiate()
	run.com_menu = false
	root.add_child(run)
	await physics_frame
	p = run.player
	var h = p.habilidades
	h.ganhar_pontos(200)
	var slot := 0
	var ult := ""
	for id in h.ordem:
		if not h.eh_ativa(id):
			continue
		if h.eh_ult(id):
			ult = id
			continue
		if slot < 3 and h.mira_de(id) != "manual":
			_aprender(h, id)
			if h.nivel(id) > 0:
				h.equipar(slot, id)
				slot += 1
	if ult != "":
		_aprender(h, ult)
		h.equipar(3, ult)
	if "impeto" in p:
		p.impeto = 100.0
	var t := 0.0
	var dt := 1.0 / float(Engine.physics_ticks_per_second)   # o laço anda por passo de física, não por quadro do filme
	var ult_t := dur * 0.55
	while t < dur:
		if run.ui.aberta:
			run.ui.escolher(0)
		elif run.estado == run.Estado.ROTA:
			run.escolher_rota(run.opcoes_rota[0])
		_andar()
		if "impeto" in p:
			p.impeto = maxf(p.impeto, 60.0)
		if t >= ult_t:
			ult_t = INF
			p.usar_ult()
		await physics_frame
		t += dt
	run.queue_free()
	await physics_frame

func _aprender(h, id: String) -> void:
	var pai: String = h.defs[id]["pai"]
	if pai != "" and h.nivel(pai) == 0:
		_aprender(h, pai)
	if h.nivel(id) == 0:
		h.aprender(id)

## Anda devagar até o inimigo mais próximo e para a uma distância boa para a câmera; o resto é o autocast.
func _andar() -> void:
	var alvo: Node2D = null
	var md := INF
	for n in get_nodes_in_group("hurtable"):
		if is_instance_valid(n):
			var d: float = n.global_position.distance_to(p.global_position)
			if d < md:
				md = d
				alvo = n
	if alvo == null or run.estado != run.Estado.LUTA:
		p.auto_move = Vector2.ZERO
		return
	var para: Vector2 = alvo.global_position - p.global_position
	var perto: float = 120.0 if "impeto" in p else 300.0
	p.auto_move = para.normalized() if md > perto else Vector2.ZERO
