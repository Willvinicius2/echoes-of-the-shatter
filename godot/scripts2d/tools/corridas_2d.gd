extends SceneTree
## Corridas automáticas (bot) do cliente 2D, sem god mode, para achar travas e picos de dificuldade:
##   godot --headless --fixed-fps 600 --path godot --script res://scripts2d/tools/corridas_2d.gd -- [corridas=10] [saida_dir=.] [seed=1] [--classe=mago]
## No modo horda (pacote H4 do plano 31) cada "sala" do relatório é uma onda do spawner; o bot pega as gemas, escolhe
## cartas ao acaso, acorda o Guardião no altar a partir da onda BOT_ONDA_CHEFE e mede mortes por onda, tempo de fase,
## DPS medido, vida que o core deu ao chefe e o nível final.
## Use --fixed-fps 600: sem ele o headless anda em tempo real (uma corrida leva ~100 s) e com ele ~10x mais rápido.
## Escreve metricas_corridas.json e metricas_corridas.md em saida_dir.
## Sai com código 1 se alguma corrida travar (sem avançar de sala por tempo demais) ou der erro.

const Csv = preload("res://scripts2d/csv2d.gd")
const RunScene = preload("res://scenes2d/Run2D.tscn")

const LIMITE_SALA := 240.0     # s simulados numa sala sem sair dela = travou (modo horda: LIMITE_ONDA)
const LIMITE_ONDA := 420.0     # modo horda: uma onda pode durar ate este tempo com o teto cheio
const LIMITE_CORRIDA := 1500.0 # s simulados numa corrida inteira = travou
const BOT_ONDA_CHEFE := 6      # modo horda: a partir desta onda o bot vai ao altar acordar o Guardião
const BOT_COLETA := 3.0        # s entre as coletas de gemas (o bot não anda até elas; um jogador anda)

var n_corridas := 10
var saida := "."
var semente := 1
var rng := RandomNumberGenerator.new()
var run
var resultados: Array = []
var _na_porta := false

func _initialize() -> void:
	var args := Array(OS.get_cmdline_user_args()).filter(func(a): return not str(a).begins_with("--"))
	if args.size() > 0:
		n_corridas = int(args[0])
	if args.size() > 1:
		saida = args[1]
	if args.size() > 2:
		semente = int(args[2])
	rng.seed = semente
	await _executar()

func _executar() -> void:
	run = RunScene.instantiate()
	run.com_menu = false
	root.add_child(run)
	await physics_frame
	for i in n_corridas:
		resultados.append(await _corrida(i))
		if i < n_corridas - 1:
			await _proxima()
	var travadas := 0
	for r in resultados:
		if r["resultado"] == "travou":
			travadas += 1
	_gravar()
	print("corridas=%d vitorias=%d mortes=%d travadas=%d" % [n_corridas, _contar("vitoria"), _contar("morte"), travadas])
	quit(1 if travadas > 0 else 0)

func _contar(res: String) -> int:
	var n := 0
	for r in resultados:
		if r["resultado"] == res:
			n += 1
	return n

## Volta ao início depois de morrer ou vencer (mesmo caminho do botão "jogar de novo").
func _proxima() -> void:
	await _esperar(func(): return run.menus.tela == run.menus.Tela.FIM, 8.0)
	run.menus.jogar.emit()
	await physics_frame

func _esperar(cond: Callable, limite: float) -> void:
	var t := 0.0
	while not cond.call() and t < limite:
		await physics_frame
		t += 1.0 / 60.0

func _corrida(n: int) -> Dictionary:
	var p = run.player
	p.god_mode = false
	var salas_tempo := {}   # sala (1..N) -> segundos simulados
	var r := {"corrida": n + 1, "resultado": "travou", "sala_final": 1, "morreu_na_sala": 0, "tempo": 0.0, "cartas": 0, "vida_final": 0.0, "salas": salas_tempo,
		"classe": preload("res://scripts2d/classe_2d.gd").atual, "horda": run.horda, "nivel": 1, "mortes": 0, "dps_chefe": 0.0, "vida_chefe": 0.0, "pico_vivos": 0}
	var coleta_t := 0.0
	var sala := 0
	var t_sala := 0.0
	var t_corrida := 0.0
	var esquiva_t := 0.0
	while true:
		await physics_frame
		var dt := 1.0 / 60.0
		t_corrida += dt
		t_sala += dt
		var agora: int = maxi(0, run.onda - 1) if run.horda else run.indice
		if agora != sala:
			sala = agora
			t_sala = 0.0
		r["pico_vivos"] = maxi(int(r["pico_vivos"]), run.vivos)
		if run.horda and run.estado == run.Estado.LUTA:
			r["mortes"] = maxi(int(r["mortes"]), int(run.nucleo.ondas_estado().get("killed", 0)))
		if run.horda:
			coleta_t += dt
			if coleta_t >= BOT_COLETA:
				coleta_t = 0.0
				run.atrair_coletaveis()
		salas_tempo[sala + 1] = float(salas_tempo.get(sala + 1, 0.0)) + dt
		r["sala_final"] = sala + 1
		if int(t_corrida * 60.0) % 600 == 0:
			var perto := INF
			for e in get_nodes_in_group("hurtable"):
				if is_instance_valid(e):
					perto = minf(perto, e.global_position.distance_to(p.global_position))
			print("[bot] wall=%d corrida %d t=%.0f sala=%d estado=%d vivos=%d hp=%.0f mortes=%d nivel=%s pausa=%s ui=%s/%s jog=%s pos=%s perto=%.0f slots=%s" % [
				Time.get_ticks_msec() / 1000, n + 1, t_corrida, sala + 1, run.estado, run.vivos, p.hp, r["mortes"],
				run.upgrades.nivel_estado().get("level", 0) if run.upgrades.has_method("nivel_estado") else 0,
				paused, run.ui.aberta, run.ui.modo, p.estado, p.global_position.round(), perto,
				p.habilidades.slots if "habilidades" in p and p.habilidades != null else []])
		r["vida_final"] = p.hp
		if run.estado == run.Estado.VENCEU:
			r["resultado"] = "vitoria"
			break
		if run.estado == run.Estado.MORTO:
			r["resultado"] = "morte"
			r["morreu_na_sala"] = sala + 1
			break
		if t_sala > (LIMITE_ONDA if run.horda else LIMITE_SALA) or t_corrida > LIMITE_CORRIDA:
			push_error("corrida %d travada na sala %d (estado %d)" % [n + 1, sala + 1, run.estado])
			break
		esquiva_t = maxf(0.0, esquiva_t - dt)
		if Input.is_action_pressed("dodge"):
			Input.action_release("dodge")
		if _agir(p, esquiva_t <= 0.0):
			esquiva_t = 1.0
		if run.ui.aberta:
			run.ui.escolher(rng.randi_range(0, maxi(0, run.ui._ids.size() - 1)))
			r["cartas"] += 1
		elif run.estado == run.Estado.ROTA:
			run.escolher_rota(run.opcoes_rota[rng.randi_range(0, run.opcoes_rota.size() - 1)])
	r["tempo"] = run.tempo
	if run.horda:
		var w: Dictionary = run.nucleo.ondas_estado()
		r["mortes"] = maxi(int(r["mortes"]), int(w.get("killed", 0)))
		r["nivel"] = int(run.upgrades.nivel_estado().get("level", 1)) if run.upgrades.has_method("nivel_estado") else 1
		r["dps_chefe"] = run.dps_medido
		r["vida_chefe"] = run.vida_chefe
	p.auto_aim = Vector2.ZERO
	p.auto_move = Vector2.ZERO
	return r

## Bot simples: mira no inimigo mais próximo, mantém distância, esquiva de perto; sala limpa -> vai à porta.
var _preso_t := 0.0
var _ultima_pos := Vector2.ZERO

func _agir(p, pode_esquivar: bool) -> bool:
	if run.estado == run.Estado.LIMPA:
		if run._timer <= 0.0 and run.posicao_saida() != Vector2.ZERO:
			p.auto_aim = Vector2.ZERO
			if not _na_porta:   # teleporta uma vez para a saída (porta antiga ou portal da fase aberta), como no teste da corrida
				p.global_position = run.posicao_saida()
				_na_porta = true
			p.auto_move = Vector2.UP
		return false
	_na_porta = false
	if run.estado != run.Estado.LUTA:
		p.auto_aim = Vector2.ZERO
		p.auto_move = Vector2.ZERO
		return false
	var alvo = null
	var melhor := INF
	for n in get_nodes_in_group("hurtable"):
		if not is_instance_valid(n):
			continue
		var d: float = n.global_position.distance_to(p.global_position)
		if d < melhor:
			melhor = d
			alvo = n
	# Modo horda: a partir de BOT_ONDA_CHEFE vai ao altar (o Guardião acorda quando ele chega perto).
	if run.horda and run.room.posicao_chefe != Vector2.ZERO and not run.nucleo.ondas_estado()["boss_spawned"] \
			and run.onda >= BOT_ONDA_CHEFE and int(run.nucleo.ondas_estado()["can_wake"]) == 0:
		p.global_position = run.room.empurrar_para_dentro(run.room.posicao_chefe + Vector2(0, 200))
	if alvo == null:
		p.auto_aim = Vector2.ZERO
		p.auto_move = Vector2.ZERO
		return false
	if run.horda:
		return _agir_horda(p, pode_esquivar, alvo, melhor)
	var para: Vector2 = alvo.global_position - p.global_position
	# Fase aberta: alvo longe (chefe na arena) e o bot preso no riacho ou num muro: pula para perto dele.
	if melhor > 900.0 and run.room.aberta():
		_preso_t = _preso_t + 1.0 / 60.0 if p.global_position.distance_to(_ultima_pos) < 1.0 else 0.0
		_ultima_pos = p.global_position
		if _preso_t > 2.0:
			p.global_position = run.room.empurrar_para_dentro(alvo.global_position - para.normalized() * 500.0)
			_preso_t = 0.0
	p.auto_aim = para
	var lado := Vector2(-para.y, para.x).normalized()
	if melhor < 170.0:
		p.auto_move = (-para.normalized() + lado * 0.6).normalized()
		if pode_esquivar and melhor < 100.0:
			Input.action_press("dodge")
	elif melhor > 340.0:
		p.auto_move = para.normalized()
	else:
		p.auto_move = lado
	return Input.is_action_pressed("dodge")

## Modo horda: como um jogador de horda, o bot deixa o autocast mirar e só anda. Foge do peso dos inimigos perto
## (1/d²), circula em volta deles, puxa para o centro do mapa para não encurralar e esquiva quando alguém encosta.
var _fuga_dir := Vector2.RIGHT
var _fuga_t := 0.0
func _agir_horda(p, pode_esquivar: bool, alvo, melhor: float) -> bool:
	p.auto_aim = Vector2.ZERO
	var fuga := Vector2.ZERO
	for n in get_nodes_in_group("hurtable"):
		if not is_instance_valid(n):
			continue
		var de: Vector2 = p.global_position - n.global_position
		var d := de.length()
		if d < 450.0 and d > 0.01:
			fuga += de / (d * d) * 10000.0
	var centro: Vector2 = run.room.tamanho_px() / 2.0
	var ao_centro: Vector2 = (centro - p.global_position) / maxf(1.0, centro.length())
	var mover: Vector2
	if fuga.length() > 0.05:
		var lado := Vector2(-fuga.y, fuga.x).normalized()
		mover = fuga.normalized() + lado * 0.5 + ao_centro * 0.8
	else:
		mover = (alvo.global_position - p.global_position).normalized() * (1.0 if melhor > 360.0 else 0.0) + ao_centro * 0.3
	_preso_t = _preso_t + 1.0 / 60.0 if p.global_position.distance_to(_ultima_pos) < 0.5 else 0.0
	_ultima_pos = p.global_position
	_fuga_t = maxf(0.0, _fuga_t - 1.0 / 60.0)
	if _preso_t > 0.6:   # encostado num muro ou no riacho: sai por um lado ao acaso por um instante
		_fuga_dir = Vector2.from_angle(rng.randf() * TAU)
		_fuga_t = 0.6
		_preso_t = 0.0
	if _fuga_t > 0.0:
		mover = _fuga_dir
	p.auto_move = mover.normalized() if mover.length() > 0.01 else Vector2.ZERO
	if pode_esquivar and melhor < 70.0:
		Input.action_press("dodge")
	return Input.is_action_pressed("dodge")

func _gravar() -> void:
	DirAccess.make_dir_recursive_absolute(saida)
	var f := FileAccess.open(saida.path_join("metricas_corridas.json"), FileAccess.WRITE)
	f.store_string(JSON.stringify({"corridas": resultados, "semente": semente}, "\t"))
	f.close()
	var n := resultados.size()
	var por_sala := {}   # sala -> {mortes, tempo_total, passagens}
	var tempos := []
	for r in resultados:
		tempos.append(float(r["tempo"]))
		for s in r["salas"]:
			var d: Dictionary = por_sala.get(s, {"mortes": 0, "tempo": 0.0, "n": 0})
			d["tempo"] += r["salas"][s]
			d["n"] += 1
			if int(r["morreu_na_sala"]) == int(s):
				d["mortes"] += 1
			por_sala[s] = d
	var md := "# Métricas de corridas automáticas\n\n"
	md += "Corridas: %d | vitórias: %d | mortes: %d | travadas: %d | semente: %d\n\n" % [n, _contar("vitoria"), _contar("morte"), _contar("travou"), semente]
	md += "| Sala | Entradas | Mortes | Tempo médio (s) |\n|---|---|---|---|\n"
	var chaves := por_sala.keys()
	chaves.sort()
	for s in chaves:
		var d: Dictionary = por_sala[s]
		md += "| %d | %d | %d | %.1f |\n" % [s, d["n"], d["mortes"], d["tempo"] / maxf(1.0, d["n"])]
	var soma := 0.0
	for t in tempos:
		soma += t
	md += "\nTempo médio de corrida: %.1f s\n\n" % (soma / maxf(1.0, n))
	md += "| # | Classe | Resultado | Sala/onda final | Tempo (s) | Cartas | Vida final | Nível | Mortes | Pico vivos | DPS no chefe | Vida do chefe |\n|---|---|---|---|---|---|---|---|---|---|---|---|\n"
	for r in resultados:
		md += "| %d | %s | %s | %d | %.1f | %d | %.0f | %d | %d | %d | %.1f | %.0f |\n" % [r["corrida"], r["classe"], r["resultado"], r["sala_final"], r["tempo"], r["cartas"], r["vida_final"],
			r["nivel"], r["mortes"], r["pico_vivos"], r["dps_chefe"], r["vida_chefe"]]
	var g := FileAccess.open(saida.path_join("metricas_corridas.md"), FileAccess.WRITE)
	g.store_string(md)
	g.close()
	print(md)
