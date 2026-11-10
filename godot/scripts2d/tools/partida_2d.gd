extends SceneTree
## Partida inteira pela cena principal (Main2D), como o jogador vê: título, prólogo, luta com subida de nível e cartas,
## chefe, portal e tela de fim. Um bot anda e escolhe as cartas; o ataque é o automático do jogo. Precisa de janela (xvfb):
##   godot --path godot --resolution 1280x720 --script res://scripts2d/tools/partida_2d.gd -- pasta [intervalo_s=5] [deus=0] [limite_s=900] [fase=cripta] [pular_ate_onda=0]
## Grava pasta/NNN_<momento>.png nos momentos-chave e a cada `intervalo_s` de luta. Com --write-movie vira o vídeo da partida.
## `pular_ate_onda` adianta o spawner do core até essa onda antes de jogar (conferir o chefe e o fim sem esperar a fase toda).
## `deus=1` deixa o jogador invulnerável (para ver a fase até o fim); o padrão é a partida de verdade.
const MainScene = preload("res://scenes2d/Main2D.tscn")
const Fase = preload("res://scripts2d/fase_2d.gd")

const ONDA_CHEFE := 6

var pasta := "partida"
var intervalo := 5.0
var deus := false
var limite := 900.0
var pular := 0
var run
var _n := 0
var _rng := RandomNumberGenerator.new()
var _preso_t := 0.0
var _ultima_pos := Vector2.ZERO
var _fuga_dir := Vector2.RIGHT
var _fuga_t := 0.0

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		pasta = args[0]
	if args.size() > 1:
		intervalo = float(args[1])
	if args.size() > 2:
		deus = int(args[2]) == 1
	if args.size() > 3:
		limite = float(args[3])
	if args.size() > 4 and args[4] != "cripta":
		Fase.todas_abertas = true
		Fase.atual = args[4]
	if args.size() > 5:
		pular = int(args[5])
	DirAccess.make_dir_recursive_absolute(pasta)
	_rng.seed = 7
	var main = MainScene.instantiate()
	root.add_child(main)
	await physics_frame
	run = main.run
	await _quadros(60)
	await _foto("titulo")
	run.menus._jogar_do_titulo()
	await _quadros(30)
	if run.menus.prologo != null and run.menus.prologo.ativo:
		var k := 0
		while run.menus.prologo.ativo and k < 40:
			await _quadros(70)
			if k < 3:
				await _foto("prologo")
			run.menus.prologo.avancar()
			run.menus.prologo.avancar()
			k += 1
	await _quadros(20)
	await _foto("inicio")
	await _jogar()
	await _quadros(150)
	await _foto("fim")
	await _quadros(60)
	quit()

func _quadros(n: int) -> void:
	for i in n:
		await process_frame

func _foto(nome: String) -> void:
	await RenderingServer.frame_post_draw
	root.get_viewport().get_texture().get_image().save_png("%s/%03d_%s.png" % [pasta, _n, nome])
	_n += 1

func _jogar() -> void:
	var p = run.player
	p.god_mode = deus
	while pular > 0 and int(run.nucleo.ondas_estado().get("wave", 0)) < pular:
		for s in run.nucleo.ondas_tick(0.5):
			run.nucleo.ondas_morto(int(s["id"]))
	if pular > 0:
		p.global_position = run.room.empurrar_para_dentro(run.room.posicao_chefe + Vector2(0, 220))
	var t := 0.0
	var prox := 2.0
	var chefe_visto := false
	var esquiva_t := 0.0
	var coleta_t := 0.0
	while t < limite:
		await physics_frame
		var dt := 1.0 / 60.0
		if run.ui.aberta:
			await _quadros(50)
			await _foto("carta_%s" % run.ui.modo)
			run.ui.escolher(_rng.randi_range(0, maxi(0, run.ui._ids.size() - 1)))
			await _quadros(8)
			continue
		if run.estado == run.Estado.VENCEU or run.estado == run.Estado.MORTO:
			await _foto("vitoria" if run.estado == run.Estado.VENCEU else "morte")
			print("[partida] %s t=%.0f tempo_jogo=%.0f" % ["VITORIA" if run.estado == run.Estado.VENCEU else "MORTE", t, run.tempo])
			return
		t += dt
		if t >= prox:
			prox = t + intervalo
			await _foto("luta_o%d" % run.onda)
			print("[partida] t=%.0f onda=%d vivos=%d hp=%.0f nivel=%s fps=%d" % [t, run.onda, run.vivos, p.hp, run.upgrades.nivel_estado().get("level", 0), Engine.get_frames_per_second()])
		if run.hud.chefe != null and is_instance_valid(run.hud.chefe) and not chefe_visto:
			chefe_visto = true
			await _quadros(40)
			await _foto("chefe")
			prox = t + 3.0
		esquiva_t = maxf(0.0, esquiva_t - dt)
		coleta_t += dt
		if coleta_t > 4.0:
			coleta_t = 0.0
			run.atrair_coletaveis()
		if Input.is_action_pressed("dodge"):
			Input.action_release("dodge")
		if _agir(p, esquiva_t <= 0.0):
			esquiva_t = 1.0
	print("[partida] LIMITE t=%.0f onda=%d" % [t, run.onda])

func _agir(p, pode_esquivar: bool) -> bool:
	if run.estado == run.Estado.LIMPA:
		var s: Vector2 = run.posicao_saida()
		p.auto_move = (s - p.global_position).normalized() if s != Vector2.ZERO else Vector2.ZERO
		_destravar(p)
		return false
	if run.estado != run.Estado.LUTA:
		p.auto_move = Vector2.ZERO
		return false
	var w: Dictionary = run.nucleo.ondas_estado()
	var ir_altar: bool = run.room.posicao_chefe != Vector2.ZERO and not bool(w.get("boss_spawned", false)) \
			and run.onda >= ONDA_CHEFE and int(w.get("can_wake", -1)) == 0
	var fuga := Vector2.ZERO
	var melhor := INF
	for n in get_nodes_in_group("hurtable"):
		if not is_instance_valid(n):
			continue
		var de: Vector2 = p.global_position - n.global_position
		var d := de.length()
		melhor = minf(melhor, d)
		if d < 380.0 and d > 0.01:
			fuga += de / (d * d) * 10000.0
	var destino: Vector2 = run.room.posicao_chefe + Vector2(0, 160) if ir_altar else run.room.tamanho_px() / 2.0
	var ao_destino: Vector2 = (destino - p.global_position).normalized()
	var mover: Vector2
	if fuga.length() > 0.05:
		var lado := Vector2(-fuga.y, fuga.x).normalized()
		mover = fuga.normalized() + lado * 0.5 + ao_destino * (1.4 if ir_altar else 0.5)
	else:
		mover = ao_destino * (1.0 if ir_altar else 0.3)
	_destravar(p)
	if _fuga_t > 0.0:
		mover = _fuga_dir
	p.auto_move = mover.normalized() if mover.length() > 0.01 else Vector2.ZERO
	if pode_esquivar and melhor < 70.0:
		Input.action_press("dodge")
	return Input.is_action_pressed("dodge")

## Encostado num muro ou na água: sai por um lado ao acaso por um instante.
func _destravar(p) -> void:
	_preso_t = _preso_t + 1.0 / 60.0 if p.global_position.distance_to(_ultima_pos) < 0.5 else 0.0
	_ultima_pos = p.global_position
	_fuga_t = maxf(0.0, _fuga_t - 1.0 / 60.0)
	if _preso_t > 0.6:
		_fuga_dir = Vector2.from_angle(_rng.randf() * TAU)
		_fuga_t = 0.7
		_preso_t = 0.0
