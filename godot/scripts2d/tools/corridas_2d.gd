extends SceneTree
## Corridas automáticas (bot) do cliente 2D, sem god mode, para achar travas e picos de dificuldade:
##   godot --headless --fixed-fps 600 --path godot --script res://scripts2d/tools/corridas_2d.gd -- [corridas=10] [saida_dir=.] [seed=1] [--classe=mago]
##   opções: --cartas=acaso (escolha de carta ao acaso, como antes), --fase=pedreira (joga outra fase)
## No modo horda (pacote H4 do plano 31) cada "sala" do relatório é uma onda do spawner; o bot pega as gemas, escolhe
## cartas com critério (ver _escolher_carta), acorda o Guardião no altar a partir da onda BOT_ONDA_CHEFE e mede mortes por onda, tempo de fase,
## DPS medido, vida que o core deu ao chefe e o nível final.
## Use --fixed-fps 600: sem ele o headless anda em tempo real (uma corrida leva ~100 s) e com ele ~10x mais rápido.
## Escreve metricas_corridas.json e metricas_corridas.md em saida_dir.
## Sai com código 1 se alguma corrida travar (sem avançar de sala por tempo demais) ou der erro.

const Csv = preload("res://scripts2d/csv2d.gd")
const RunScene = preload("res://scenes2d/Run2D.tscn")

const LIMITE_SALA := 240.0     # s simulados numa sala sem sair dela = travou (modo horda: LIMITE_ONDA)
const LIMITE_ONDA := 420.0     # modo horda: uma onda pode durar ate este tempo com o teto cheio
const BOT_SEM_ABATE := 45.0    # modo horda: sem nenhum abate por este tempo, o bot sai do canto onde encalhou (centro do mapa)
const LIMITE_CORRIDA := 1500.0 # s simulados numa corrida inteira = travou
const BOT_ONDA_CHEFE := 6      # modo horda: a partir desta onda o bot vai ao altar acordar o Guardião
const BOT_CHEFE_PERTO := 15.0  # modo horda: a cada tanto, com o chefe vivo e longe, o bot vai para perto dele
const BOT_COLETA := 3.0        # s entre as coletas de gemas (o bot não anda até elas; um jogador anda)

var n_corridas := 10
var saida := "."
var semente := 1
var rng := RandomNumberGenerator.new()
var run
var resultados: Array = []
var _na_porta := false
var cartas_acaso := false   # --cartas=acaso: volta à escolha ao acaso (comparar com o critério)
var _cartas_def := {}       # id -> {tipo, raridade, stat} de upgrades.csv

func _initialize() -> void:
	var args := Array(OS.get_cmdline_user_args()).filter(func(a): return not str(a).begins_with("--"))
	for a in OS.get_cmdline_user_args():
		if str(a) == "--cartas=acaso":
			cartas_acaso = true
		elif str(a).begins_with("--fase="):
			var Fase = preload("res://scripts2d/fase_2d.gd")
			Fase.todas_abertas = true
			Fase.atual = str(a).trim_prefix("--fase=")
	for l in Csv.rows("res://data2d/upgrades.csv"):
		_cartas_def[l["id"]] = l
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
		"classe": preload("res://scripts2d/classe_2d.gd").atual, "horda": run.horda, "nivel": 1, "mortes": 0, "dps_chefe": 0.0, "vida_chefe": 0.0, "pico_vivos": 0,
		"afinidade": "", "habilidades": [], "nivel_onda": {}, "vida_min_onda": {}, "tempo_chefe": 0.0, "dano_onda": {}, "dano_fonte": {}, "fase": preload("res://scripts2d/fase_2d.gd").atual}
	var nivel_onda: Dictionary = r["nivel_onda"]       # onda -> nível do Cristal ao fim dela (curva de nível)
	var vida_min_onda: Dictionary = r["vida_min_onda"] # onda -> menor vida do jogador nela (aperto)
	var dano_onda: Dictionary = r["dano_onda"]         # onda -> dano que o jogador levou nela
	var dano_fonte: Dictionary = r["dano_fonte"]       # quem bateu (inimigo encostado, senão "tiro") -> dano
	var vida_antes: float = p.hp
	var coleta_t := 0.0
	var ultimo_abate := 0
	var sem_abate := 0.0
	var sala := 0
	var t_sala := 0.0
	var t_corrida := 0.0
	var esquiva_t := 0.0
	var boss_t := 0.0
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
		if run.horda and run.estado == run.Estado.LUTA:
			# Encalhado num canto sem linha de tiro: um jogador andaria; o bot é levado ao centro do mapa.
			sem_abate = 0.0 if int(r["mortes"]) != ultimo_abate else sem_abate + dt
			ultimo_abate = int(r["mortes"])
			if sem_abate > BOT_SEM_ABATE:
				sem_abate = 0.0
				var centro: Vector2 = run.room.tamanho_px() / 2.0
				p.global_position = run.room.empurrar_para_dentro(centro + Vector2(rng.randf_range(-600.0, 600.0), rng.randf_range(-600.0, 600.0)))
		if run.horda and run.estado == run.Estado.LUTA and run.hud.chefe != null and is_instance_valid(run.hud.chefe) and run.hud.chefe.hp > 0.0:
			# Chefe vivo e o bot longe dele ou sem acertá-lo: um jogador chegaria perto; o bot é levado a ~320 px a cada 15 s
			# (o autocast só mira o que está no alcance; sem isto a corrida podia passar de 7 min sem terminar o chefe).
			boss_t += dt
			if boss_t >= BOT_CHEFE_PERTO:
				boss_t = 0.0
				if p.global_position.distance_to(run.hud.chefe.global_position) > 420.0:
					p.global_position = run.room.empurrar_para_dentro(run.hud.chefe.global_position + Vector2.from_angle(rng.randf() * TAU) * 320.0)
		if run.horda:
			coleta_t += dt
			if coleta_t >= BOT_COLETA:
				coleta_t = 0.0
				run.atrair_coletaveis()
		salas_tempo[sala + 1] = float(salas_tempo.get(sala + 1, 0.0)) + dt
		if p.hp < vida_antes:
			var perda: float = vida_antes - p.hp
			dano_onda[sala + 1] = float(dano_onda.get(sala + 1, 0.0)) + perda
			var fonte := "tiro"
			var d_fonte := INF
			for e in get_nodes_in_group("hurtable"):
				if is_instance_valid(e):
					var de: float = e.global_position.distance_to(p.global_position)
					if de < d_fonte and de <= float(e.stats.get("attack_range", 0.0)) + 40.0 and str(e.stats.get("kind", "")) != "ranged":
						d_fonte = de
						fonte = str(e.stats.get("id", "?"))
			dano_fonte[fonte] = float(dano_fonte.get(fonte, 0.0)) + perda
		vida_antes = p.hp
		if run.horda and run.upgrades.has_method("nivel_estado"):
			nivel_onda[sala + 1] = int(run.upgrades.nivel_estado().get("level", 1))
			vida_min_onda[sala + 1] = minf(float(vida_min_onda.get(sala + 1, p.hp)), p.hp)
			if bool(run.nucleo.ondas_estado().get("boss_spawned", false)) and run.estado == run.Estado.LUTA:
				r["tempo_chefe"] += dt
		r["sala_final"] = sala + 1
		if int(t_corrida * 60.0) % 600 == 0:
			var perto := INF
			var com_visao := 0
			var na_tela := 0
			var amostra := ""
			for e in get_nodes_in_group("hurtable"):
				if is_instance_valid(e):
					var dist: float = e.global_position.distance_to(p.global_position)
					if dist < perto:
						perto = dist
						amostra = "%s est=%s pos=%s" % [e.stats.get("id", "?"), e.estado, e.global_position.round()]
					if preload("res://scripts2d/alvos_2d.gd").ve(self, p.global_position, e.global_position):
						com_visao += 1
					if run.vista().has_point(e.global_position):
						na_tela += 1
			print("[bot] wall=%d corrida %d t=%.0f sala=%d estado=%d vivos=%d hp=%.0f mortes=%d nivel=%s pausa=%s ui=%s/%s jog=%s pos=%s perto=%.0f los=%d tela=%d mais_perto=[%s] slots=%s" % [
				Time.get_ticks_msec() / 1000, n + 1, t_corrida, sala + 1, run.estado, run.vivos, p.hp, r["mortes"],
				run.upgrades.nivel_estado().get("level", 0) if run.upgrades.has_method("nivel_estado") else 0,
				paused, run.ui.aberta, run.ui.modo, p.estado, p.global_position.round(), perto, com_visao, na_tela, amostra,
				p.habilidades.slots if "habilidades" in p and p.habilidades != null else []])
		r["vida_final"] = p.hp
		if run.estado == run.Estado.VENCEU:
			r["resultado"] = "vitoria"
			break
		if run.estado == run.Estado.MORTO:
			r["resultado"] = "morte"
			r["morreu_na_sala"] = sala + 1
			break
		if run.horda and t_sala > LIMITE_ONDA and bool(run.nucleo.ondas_estado().get("boss_spawned", false)) \
				and run.hud.chefe != null and is_instance_valid(run.hud.chefe) and run.hud.chefe.hp > 0.0:
			# Luta de chefe que passou do limite com o bot vivo e o chefe ainda de pé: dificuldade (lenta demais), não trava do
			# jogo. Conta como "lenta" no relatório e não derruba o CI; trava de verdade (sem chefe vivo) continua falhando.
			r["resultado"] = "lenta"
			r["morreu_na_sala"] = sala + 1
			print("[bot] corrida %d: luta do chefe passou de %.0f s (lenta)" % [n + 1, LIMITE_ONDA])
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
			run.ui.escolher(_escolher_carta(p, n))
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
	if "afinidade" in p:
		r["afinidade"] = p.afinidade
	if "habilidades" in p and p.habilidades != null:
		for id in p.habilidades.slots:
			if id != "":
				r["habilidades"].append("%s:%d" % [id, p.habilidades.nivel(id)])
	p.auto_aim = Vector2.ZERO
	p.auto_move = Vector2.ZERO
	return r

## Escolha de carta com critério, como um jogador que monta a corrida em volta de um elemento:
## - afinidade (Eco do básico): uma por corrida, em rodízio, para medir os quatro elementos;
## - gema de habilidade: prefere habilidade ativa do elemento da afinidade, depois subir uma que já tem;
## - carta de nível ou baú: ataque antes de tudo, vida quando está apanhando, e saber elemental só do elemento que usa.
## Empate decide no sorteio (a semente continua valendo).
func _escolher_carta(p, n: int) -> int:
	var ids: Array = run.ui._ids
	if ids.is_empty():
		return 0
	if cartas_acaso:
		return rng.randi_range(0, ids.size() - 1)
	if run.ui.modo == "afinidade":
		return (semente + n) % ids.size()
	var h = p.habilidades if "habilidades" in p else null
	var el := ""
	if "afinidade" in p and p.afinidade != "":
		el = preload("res://scripts2d/efeitos_arqueiro_afinidade_2d.gd").elemento(p.afinidade)
	var elementos := {}   # elementos das habilidades que o bot já tem
	var ativas := 0
	if h != null:
		for id in h.slots:
			if id != "":
				ativas += 1
				elementos[str(h.defs[id].get("ramo", ""))] = true
	var melhor := -INF
	var escolha := 0
	for i in ids.size():
		var id := str(ids[i])
		var nota := rng.randf() * 0.5
		if run.ui.modo == "gem" and h != null:
			var d: Dictionary = h.defs.get(id, {})
			var ativa: bool = str(d.get("tipo", "")) == "ativa"
			if str(d.get("ramo", "")) == el:
				nota += 3.0
			if h.nivel(id) > 0:
				nota += 2.0
			elif ativa and h.slots.has(""):
				nota += 2.5
			elif ativa:
				nota -= 2.0   # ativa nova sem slot livre não entra na barra
		else:
			var c: Dictionary = _cartas_def.get(id, {})
			var stat := str(c.get("stat", ""))
			match str(c.get("tipo", "")):
				"ataque":
					nota += 3.0
				"defesa":
					nota += 4.0 if p.hp < 0.6 * float(p.stats.get("hp_max", 100.0)) else 1.5
				_:
					nota += 1.0
			if str(c.get("raridade", "")) == "rara":
				nota += 0.75
			if stat.begins_with("run_dmg_"):
				var e := stat.trim_prefix("run_dmg_")
				if e == "herald" or not elementos.has(e):
					nota -= 3.0   # saber de um elemento que ele não usa
			elif stat.begins_with("run_") and ativas == 0:
				nota -= 3.0       # reforço de habilidade sem ter habilidade
			if stat == "hp_max" and str(c.get("tipo", "")) == "defesa" and int(run.onda) >= 4:
				nota += 0.5
		if nota > melhor:
			melhor = nota
			escolha = i
	return escolha

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
## (1/d²), circula em volta deles, puxa para o centro do mapa para não encurralar, esquiva quando alguém encosta e
## sai de lado da linha dos tiros inimigos que vêm na direção dele (um jogador vê a linha de mira e o projétil).
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
	var desvio := _desvio_tiros(p)
	if desvio != Vector2.ZERO:
		mover = mover.normalized() * 0.4 + desvio
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

## Direção para sair de lado do tiro inimigo mais urgente (o que passaria a menos de BOT_TIRO_FOLGA px em até
## BOT_TIRO_TEMPO s); Vector2.ZERO quando nenhum vem. O bot não é perfeito: só reage ao tiro já no ar.
const BOT_TIRO_FOLGA := 55.0
const BOT_TIRO_TEMPO := 0.7
func _desvio_tiros(p) -> Vector2:
	var urgente := INF
	var lado := Vector2.ZERO
	for f in p.get_parent().get_children():
		if not (f is Area2D) or not ("team" in f) or f.team != "enemy":
			continue
		var v: Vector2 = f.velocity
		var vel := v.length()
		if vel < 1.0:
			continue
		var dir := v / vel
		var ate: Vector2 = p.global_position - f.global_position
		var frente := ate.dot(dir)
		if frente < 0.0 or frente / vel > BOT_TIRO_TEMPO:
			continue
		var fora := ate - dir * frente   # do eixo do tiro até o jogador
		if fora.length() < BOT_TIRO_FOLGA and frente / vel < urgente:
			urgente = frente / vel
			lado = fora.normalized() if fora.length() > 1.0 else Vector2(-dir.y, dir.x)
	return lado

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
	md += "Corridas: %d | vitórias: %d | mortes: %d | lentas (chefe de pé após o limite): %d | travadas: %d | semente: %d\n\n" % [n, _contar("vitoria"), _contar("morte"), _contar("lenta"), _contar("travou"), semente]
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
	md += "| # | Classe | Resultado | Sala/onda final | Tempo (s) | Cartas | Vida final | Nível | Mortes | Pico vivos | DPS no chefe | Vida do chefe | Luta do chefe (s) | Eco | Habilidades |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
	for r in resultados:
		md += "| %d | %s | %s | %d | %.1f | %d | %.0f | %d | %d | %d | %.1f | %.0f | %.0f | %s | %s |\n" % [r["corrida"], r["classe"], r["resultado"], r["sala_final"], r["tempo"], r["cartas"], r["vida_final"],
			r["nivel"], r["mortes"], r["pico_vivos"], r["dps_chefe"], r["vida_chefe"], r["tempo_chefe"], r["afinidade"], " ".join(r["habilidades"])]
	md += "\nNível do Cristal ao fim de cada onda e menor vida nela (cartas: %s):\n\n| # | Curva (onda:nível/vida mínima) |\n|---|---|\n" % ("acaso" if cartas_acaso else "critério")
	for r in resultados:
		var partes := []
		var ks: Array = r["nivel_onda"].keys()
		ks.sort()
		for k in ks:
			partes.append("%d:%d/%.0f" % [k, r["nivel_onda"][k], r["vida_min_onda"].get(k, 0.0)])
		md += "| %d | %s |\n" % [r["corrida"], " ".join(partes)]
	# Dano levado: média por onda (entre as corridas que chegaram nela) e por quem bateu (soma de todas).
	var dano_ondas := {}
	var fontes := {}
	for r in resultados:
		for k in r["salas"]:
			var d: Dictionary = dano_ondas.get(k, {"dano": 0.0, "n": 0, "tempo": 0.0})
			d["dano"] += float(r["dano_onda"].get(k, 0.0))
			d["tempo"] += float(r["salas"][k])
			d["n"] += 1
			dano_ondas[k] = d
		for q in r["dano_fonte"]:
			fontes[q] = float(fontes.get(q, 0.0)) + float(r["dano_fonte"][q])
	md += "\n| Onda | Dano levado (média) | Dano por minuto |\n|---|---|---|\n"
	var ko := dano_ondas.keys()
	ko.sort()
	for k in ko:
		var d: Dictionary = dano_ondas[k]
		md += "| %d | %.0f | %.1f |\n" % [k, d["dano"] / maxf(1.0, d["n"]), 60.0 * d["dano"] / maxf(1.0, d["tempo"])]
	var kf := fontes.keys()
	kf.sort_custom(func(a, b): return fontes[a] > fontes[b])
	md += "\nDano levado por fonte (todas as corridas): "
	for q in kf:
		md += "%s %.0f, " % [q, fontes[q]]
	md += "\n"
	var g := FileAccess.open(saida.path_join("metricas_corridas.md"), FileAccess.WRITE)
	g.store_string(md)
	g.close()
	print(md)
