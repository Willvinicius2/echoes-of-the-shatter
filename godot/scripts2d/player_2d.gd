extends "res://scripts2d/actor_2d.gd"
## Arqueiro 2D: corre e esquiva; o tiro básico e as habilidades disparam sozinhos no inimigo certo (autocast, mira
## em data2d/habilidades_mira.csv) e a ult sai na tecla de ult. Números em data2d/player.csv.

signal died
signal hp_changed(hp: float, hp_max: float)
signal mana_changed(mana: float, mana_max: float)

const Csv = preload("res://scripts2d/csv2d.gd")
const VenenoFx = preload("res://scripts2d/efeitos_arqueiro_veneno_2d.gd")
const GeloFx = preload("res://scripts2d/efeitos_arqueiro_gelo_2d.gd")
const FogoFx = preload("res://scripts2d/efeitos_arqueiro_fogo_2d.gd")
const RaioFx = preload("res://scripts2d/efeitos_arqueiro_raio_2d.gd")
const ArrowScript = preload("res://scripts2d/arrow_2d.gd")
const AfinidadeFx = preload("res://scripts2d/efeitos_arqueiro_afinidade_2d.gd")
const Vfx = preload("res://scripts2d/vfx_2d.gd")
const ANCORAS := "res://data2d/ancoras_2d.csv"   # boca do arco por linha da folha (doc 33 seção 2)
static var _ancoras := {}   # sprite_id -> {linha: Vector2 (px a partir dos pés)}
const Audio = preload("res://scripts2d/audio_2d.gd")
const HabilidadesScript = preload("res://scripts2d/habilidades_2d.gd")
const Alvos = preload("res://scripts2d/alvos_2d.gd")

enum Estado { LIVRE, ATIRANDO, ESQUIVA, MORTO }

var stats_csv := "res://data2d/player.csv"  # outras classes (mago) trocam no _init
var sprite_id := "arqueiro"
var stats := {}
var hp := 0.0
var mana := 0.0
var classe := "arqueiro"
var habilidades: RefCounted   # árvore e slots da classe (habilidades_2d.gd)
## Afinidade do ataque básico ("Eco", doc 36 seção 2): id de data2d/afinidades_arqueiro.csv ou vazio (básico neutro).
## Escolhida na primeira gema da corrida; zera a cada corrida (run_2d.gd).
var afinidade := ""
var estado := Estado.LIVRE
var invencivel := 0.0
var god_mode := false          # testes automáticos
var auto_aim := Vector2.ZERO   # testes: mira forçada
var auto_move := Vector2.ZERO  # testes: movimento forçado
var autocast := true           # básico e habilidades disparam sozinhos (falso: só tecla, como antes)
var _alvo_basico := {}         # alvo do tiro básico no autocast ({} = ninguém no alcance)
var alvo_ponto := Vector2.INF  # ponto no chão escolhido pelo autocast para a habilidade em uso (INF = nenhum)
var dodge_cd := 0.0
var _shoot_cd := 0.0
var _dodge_t := 0.0
var _dodge_dir := Vector2.DOWN
var _aim := Vector2.DOWN
var _disparou := false
var vel_buff := 1.0            # habilidade Adrenalina: velocidade de corrida
var cad_buff := 1.0            # habilidade Adrenalina: cadência de tiro
var buff_t := 0.0
var _salto_vel := 0.0          # >0: esquiva customizada (Salto Atrás) com esta velocidade
var _rng := RandomNumberGenerator.new()
## Habilidades que saem como projétil na direção da mira: entram no leque quando várias disparam juntas.
const EFEITOS_PROJETIL := ["tiro_forte", "rajada", "explosiva", "tiro_veneno", "gelo_flecha", "gelo_estilhaco", "tiro_ardente", "flecha_eletrica"]
var _leque_disparos: Array = []   # instantes (ms) dos últimos disparos de projétil
var _prox_autocast_ms := 0

func _ready() -> void:
	stats = Csv.kv(stats_csv)
	HabilidadesScript.registrar_tecla_ult()
	habilidades = HabilidadesScript.new()
	definir_classe(classe)
	habilidades.mudou.connect(_atualizar_heralds)
	collision_layer = 2
	collision_mask = 1 | 8
	add_to_group("arqueiro")
	setup_sprite(sprite_id)
	var cs := CollisionShape2D.new()
	var sh := CircleShape2D.new()
	sh.radius = stats["radius"]
	cs.shape = sh
	add_child(cs)
	reset()

## Troca a classe: stats de player.csv mais as sobrescritas de classes_2d.csv, e carrega a árvore dela.
func definir_classe(id: String) -> void:
	classe = id
	stats = Csv.kv(stats_csv)
	var cl: Dictionary = HabilidadesScript.classes().get(id, {})
	for k in cl:
		if stats.has(k) and str(cl[k]) != "":
			stats[k] = float(cl[k])
	habilidades.carregar_classe(id)
	aplicar_passivos_stats()
	mana = stats["mana_max"]

func gastar_mana(n: float) -> bool:
	if mana + 0.0001 < n:
		return false
	mana -= n
	mana_changed.emit(mana, stats["mana_max"])
	return true

func ganhar_mana(qtd: float) -> void:
	var antes := mana
	mana = minf(stats["mana_max"], mana + qtd)
	if absf(mana - antes) > 0.0001:
		mana_changed.emit(mana, stats["mana_max"])

## Regeneração de mana por segundo; classes com bônus temporários sobrescrevem.
func taxa_regen_mana() -> float:
	return stats["mana_regen"]

## Usa a habilidade do slot 0..3. Sem `alvo`, mira onde o jogador mira; com `alvo` ({dir, ponto} do autocast), nele.
func usar_habilidade(slot: int, alvo := {}) -> bool:
	if estado == Estado.MORTO or estado == Estado.ESQUIVA:
		return false
	var dir := _aim
	if not alvo.is_empty() and not Alvos.mira_mouse:
		dir = alvo["dir"]
		alvo_ponto = alvo["ponto"]
	var proj: bool = habilidades.slots[slot] != "" and EFEITOS_PROJETIL.has(habilidades.def_nivel(habilidades.slots[slot]).get("efeito", ""))
	var agora := Time.get_ticks_msec()
	if proj:
		dir = dir.rotated(_desvio_leque(agora))
	var facing_antes := facing
	facing = dir   # antes de disparar: a boca do arco e o sprite seguem a direção do tiro, não a do passo anterior
	var ok: bool = habilidades.usar(slot, self, dir)
	alvo_ponto = Vector2.INF
	if ok and proj:
		_leque_disparos.append(agora)
	if ok:
		if estado == Estado.LIVRE and has_method("animar_conjuracao"):   # mago: gesto de conjuração sem travar o movimento
			call("animar_conjuracao")
	else:
		facing = facing_antes
	return ok

## Leque do autocast: o 1º disparo sai reto na mira; os que saem junto (dentro de `leque_janela`) abrem para os lados,
## alternando +d, -d, +2d, -2d... Assim várias habilidades juntas formam um leque ordenado a partir do arqueiro,
## e uma habilidade sozinha continua reta no alvo.
func _desvio_leque(agora_ms: int) -> float:
	var janela_ms := int(stats.get("leque_janela", 0.0) * 1000.0)
	_leque_disparos = _leque_disparos.filter(func(t): return agora_ms - t <= janela_ms)
	var k := _leque_disparos.size()
	if k == 0:
		return 0.0
	var lado := 1.0 if k % 2 == 1 else -1.0
	return deg_to_rad(stats.get("leque_graus", 0.0)) * floorf((k + 1) * 0.5) * lado

## Heralds: gatilhos de morte (docs/design/32). Cada Herald aprendido age quando o inimigo morre com o status certo.
## `sobra` = dano que passou da vida do inimigo no golpe fatal (overkill).
func herald_morte(inimigo: Node2D, sobra := 0.0) -> void:
	if habilidades == null:
		return
	if habilidades.nivel("herald_plague") > 0 and inimigo.tem_status("veneno"):
		VenenoFx.arauto_peste_morte(inimigo, habilidades.def_nivel("herald_plague"))
		Vfx.aura_acender(self, "AuraPeste")
	if habilidades.nivel("herald_ice") > 0:
		GeloFx.arauto_vigiar(inimigo, self, habilidades.def_nivel("herald_ice"))   # explode no died.emit, se estiver congelado
		if GeloFx.esta_congelado(inimigo):
			Vfx.aura_acender(self, "AuraGelo")
	if habilidades.nivel("herald_thunder") > 0:
		RaioFx.ao_morrer(inimigo)
		if inimigo.tem_status("choque"):
			Vfx.aura_acender(self, "AuraArauto")
	if habilidades.nivel("arauto_cinzas") > 0:
		var d: Dictionary = habilidades.def_nivel("arauto_cinzas").duplicate()
		d["minimo"] = float(inimigo.hp_max) * float(d.get("qtd", 0.0)) / 100.0   # qtd = sobra mínima em % da vida máxima
		if FogoFx.ao_abate(self, inimigo.global_position, sobra, d):
			Vfx.aura_acender(self, "AuraCinzas")

## Auras e gatilhos dos Heralds seguem o que está aprendido (liga e desliga quando a árvore muda).
func _atualizar_heralds() -> void:
	if habilidades == null:
		return
	if habilidades.nivel("herald_plague") > 0:
		VenenoFx.aura_arauto(self)
	else:
		_tirar_no("AuraPeste")
	RaioFx.ativar_arauto(self, habilidades.def_nivel("herald_thunder") if habilidades.nivel("herald_thunder") > 0 else {})
	if habilidades.nivel("herald_ice") > 0:
		if not has_node("AuraGelo"):
			GeloFx.aura(self)
	else:
		_tirar_no("AuraGelo")
	if habilidades.nivel("arauto_cinzas") > 0:
		if not has_node("AuraCinzas"):
			FogoFx.aura(self).name = "AuraCinzas"
	else:
		_tirar_no("AuraCinzas")

func _tirar_no(nome: String) -> void:
	if has_node(nome):
		get_node(nome).queue_free()

## Ult: a ativa marcada como ult no slot sai só aqui (tecla de ult), mirando no inimigo do autocast quando há um.
func usar_ult() -> bool:
	var slot: int = habilidades.slot_ult()
	if slot < 0:
		return false
	var id: String = habilidades.slots[slot]
	return usar_habilidade(slot, habilidades.alvo_auto(id, get_tree(), global_position))

## Autocast: cada ativa equipada (menos a ult e as manuais) sai assim que a recarga acaba e há alvo. Uma por quadro.
func _autocast_habilidades() -> void:
	if Time.get_ticks_msec() < _prox_autocast_ms:
		return
	for i in HabilidadesScript.SLOTS:
		var id: String = habilidades.slots[i]
		if not habilidades.automatica(id) or habilidades.recargas.has(id):
			continue
		var alvo: Dictionary = habilidades.alvo_auto(id, get_tree(), global_position, stats["arrow_range"])
		if not alvo.is_empty() and usar_habilidade(i, alvo):
			_prox_autocast_ms = Time.get_ticks_msec() + int(stats.get("autocast_intervalo", 0.0) * 1000.0)
			return

## Ponto no chão para habilidades de área, limitado a `alcance`: o do autocast, senão o cursor (ou a mira).
func ponto_mira(alcance: float) -> Vector2:
	var alvo := global_position + _aim * alcance
	if alvo_ponto != Vector2.INF:
		alvo = alvo_ponto
	elif auto_aim == Vector2.ZERO and Input.get_vector("aim_left", "aim_right", "aim_up", "aim_down").length() <= 0.3:
		alvo = get_global_mouse_position()
	var v := alvo - global_position
	return global_position + v.limit_length(alcance)

func tem_alvo_auto() -> bool:
	return alvo_ponto != Vector2.INF

func reset() -> void:
	hp = stats["hp_max"]
	mana = stats["mana_max"]
	mana_changed.emit(mana, stats["mana_max"])
	habilidades.limpar_recargas()
	estado = Estado.LIVRE
	invencivel = 0.0
	dodge_cd = 0.0
	_shoot_cd = 0.0
	buff_t = 0.0
	vel_buff = 1.0
	cad_buff = 1.0
	_salto_vel = 0.0
	velocity = Vector2.ZERO
	modulate = Color.WHITE
	play("idle", true)
	hp_changed.emit(hp, stats["hp_max"])

func _physics_process(delta: float) -> void:
	if estado == Estado.MORTO:
		velocity = Vector2.ZERO
		return
	_shoot_cd = maxf(0.0, _shoot_cd - delta * cad_buff)
	if buff_t > 0.0:
		buff_t -= delta
		if buff_t <= 0.0:
			vel_buff = 1.0
			cad_buff = 1.0
	dodge_cd = maxf(0.0, dodge_cd - delta)
	invencivel = maxf(0.0, invencivel - delta)
	habilidades.tick(delta)
	if estado != Estado.MORTO:
		ganhar_mana(taxa_regen_mana() * delta)
	var entrada := auto_move if auto_move != Vector2.ZERO else Input.get_vector("move_left", "move_right", "move_up", "move_down")
	_aim = _ler_mira(entrada)

	match estado:
		Estado.ESQUIVA:
			_dodge_t -= delta
			velocity = _dodge_dir * (_salto_vel if _salto_vel > 0.0 else stats["dodge_speed"])
			if _dodge_t <= 0.0:
				estado = Estado.LIVRE
				_salto_vel = 0.0
		_:
			var vmax: float = stats["speed"] * vel_buff * (stats["attack_move_mult"] if estado == Estado.ATIRANDO else 1.0)
			var alvo := entrada * vmax
			var taxa: float = stats["accel"] if entrada != Vector2.ZERO else stats["friction"]
			velocity = velocity.move_toward(alvo, taxa * delta)
			for i in HabilidadesScript.SLOTS:
				if Input.is_action_just_pressed("skill_%d" % (i + 1)):
					usar_habilidade(i, habilidades.alvo_auto(habilidades.slots[i], get_tree(), global_position, stats["arrow_range"]) if autocast else {})
			if InputMap.has_action("ult") and Input.is_action_just_pressed("ult"):
				usar_ult()
			if autocast and estado != Estado.ESQUIVA:
				_autocast_habilidades()
			if Input.is_action_just_pressed("dodge") and dodge_cd <= 0.0:
				_comecar_esquiva(entrada if entrada != Vector2.ZERO else _aim)
			elif _quer_atirar() and _shoot_cd <= 0.0:
				_comecar_tiro()
	move_and_slide()
	_animar(entrada)

## Fração 0..1 da recarga do tiro (0 = pronto), para a barra de habilidades.
func recarga_tiro() -> float:
	return clampf(_shoot_cd / stats["shoot_cooldown"], 0.0, 1.0)

func esta_morto() -> bool:
	return estado == Estado.MORTO

func _quer_atirar() -> bool:
	return Input.is_action_pressed("shoot") or auto_aim != Vector2.ZERO or not _alvo_basico.is_empty()

## Mira: a forçada dos testes; no autocast, o inimigo do básico (ou a direção do movimento); senão analógico e cursor.
func _ler_mira(entrada := Vector2.ZERO) -> Vector2:
	_alvo_basico = {}
	if auto_aim != Vector2.ZERO:
		return auto_aim.normalized()
	if autocast:
		_alvo_basico = habilidades.alvo_auto("basico", get_tree(), global_position, stats["arrow_range"])
		if not Alvos.mira_mouse:
			if not _alvo_basico.is_empty():
				return _alvo_basico["dir"]
			if entrada != Vector2.ZERO:
				return entrada.normalized()
			return _aim
	var stick := Input.get_vector("aim_left", "aim_right", "aim_up", "aim_down")
	if stick.length() > 0.3:
		return stick.normalized()
	var d := get_global_mouse_position() - global_position
	return d.normalized() if d.length() > 4.0 else _aim

func _comecar_esquiva(dir: Vector2) -> void:
	estado = Estado.ESQUIVA
	_dodge_dir = dir.normalized()
	_dodge_t = stats["dodge_time"]
	dodge_cd = stats["dodge_cooldown"]
	invencivel = maxf(invencivel, stats["dodge_time"])
	facing = _dodge_dir
	play("dodge", true)
	Audio.tocar("dodge")

func _comecar_tiro() -> void:
	estado = Estado.ATIRANDO
	_shoot_cd = stats["shoot_cooldown"]
	_disparou = false
	facing = _aim
	play("attack", true)

func _animar(entrada: Vector2) -> void:
	match estado:
		Estado.ATIRANDO, Estado.ESQUIVA:
			if estado == Estado.ATIRANDO:
				facing = _aim
		_:
			if entrada != Vector2.ZERO:
				facing = _aim if _aim != Vector2.ZERO else entrada
				play("run")
			else:
				facing = _aim
				play("idle")

func _on_frame_changed() -> void:
	if estado != Estado.ATIRANDO or anim_base() != "attack" or _disparou:
		return
	var ev: int = evento("attack")
	if sprite.frame >= ev:
		_disparou = true
		_soltar_flecha()

func mira_atual() -> Vector2:
	return _aim

## Pontos de ancoragem da folha (data2d/ancoras_2d.csv): linha da animação de ataque -> boca do arco em px dos pés.
static func _ancoras_de(id: String) -> Dictionary:
	if not _ancoras.has(id):
		var d := {}
		for r in Csv.rows(ANCORAS):
			if r["id"] == id and r["anim"] == "attack":
				d[int(r["linha"])] = Vector2(float(r["x"]), float(r["y"]))
		_ancoras[id] = d
	return _ancoras[id]

## Boca do arco para a direção `dir` (doc 33 seção 2): {chao: ponto no chão (mundo) sob a mão do arco, altura: px
## acima do chão, origem: onde a colisão da flecha nasce (linha da mira, como antes), desloc: da origem até a mão}. Sai da linha da folha que o sprite mostra nessa direção, espelhada quando a linha é espelhada.
## Sprite sem ancoragem (outra classe) cai no antigo `arrow_spawn_dist` à frente dos pés, na altura de voo.
func boca_do_arco(dir: Vector2) -> Dictionary:
	var anc := _ancoras_de(sprite_id)
	var d: Array = SpriteLoader.dir_for(dir if dir != Vector2.ZERO else facing, SpriteLoader.info(sprite_id)["dirs"])
	var origem: Vector2 = global_position + dir * float(stats["arrow_spawn_dist"])
	if anc.is_empty() or not anc.has(d[0]):
		return {"chao": origem, "altura": stats["arrow_altura"], "origem": origem, "desloc": Vector2.ZERO}
	var p: Vector2 = anc[d[0]]
	if d[1]:
		p.x = -p.x
	var chao: Vector2 = global_position + Vector2(p.x, 0.0)
	return {"chao": chao, "altura": -p.y, "origem": origem, "desloc": chao - origem}

## Cria e lança uma flecha com os stats do jogador (crítico, veneno, perfuração). Usada pelo tiro e pelas habilidades.
## A flecha nasce na boca do arco, com flash de boca e recuo do sprite, e desce até a altura de voo (doc 33 seção 2).
## `def` é a linha da habilidade já resolvida pela árvore de passivos: `vel` multiplica a velocidade, `perfura` soma
## corpos atravessados e `proj_extra` lança cópias em leque (abertura `multishot_spread`) do mesmo tiro.
## Acima de `max_projeteis` (passivas_limites.csv) flechas vivas, o tiro não nasce (devolve a mais antiga).
func lancar_flecha(dir: Vector2, dano_mult := 1.0, pierce_extra := 0, vel_mult := 1.0, def := {}) -> Node:
	var vivas: Array = get_tree().get_nodes_in_group("flecha_jogador")
	if vivas.size() >= _max_projeteis():
		return vivas[0]
	var extra := int(def.get("proj_extra", 0))
	if extra > 0:
		var sem := def.duplicate()
		sem["proj_extra"] = 0
		var abertura := deg_to_rad(stats.get("multishot_spread", 12.0))
		for i in extra:
			var lado := 1.0 if i % 2 == 0 else -1.0
			lancar_flecha(dir.rotated(abertura * lado * float(i / 2 + 1)), dano_mult, pierce_extra, vel_mult, sem)
	var f := ArrowScript.new()
	var dano: float = stats["arrow_damage"] * dano_mult
	if stats["crit_chance"] > 0.0 and _rng.randf() < stats["crit_chance"]:
		dano *= stats["crit_mult"]
	var boca := boca_do_arco(dir)
	f.setup("player", boca["origem"], dir, stats["arrow_speed"] * vel_mult * float(def.get("vel", 1.0)), dano, stats["arrow_range"],
		boca["altura"], stats["arrow_altura"], stats["arrow_altura_dist"], boca["desloc"])
	f.pierce = int(stats["arrow_pierce"]) + pierce_extra + int(def.get("perfura", 0))  # gancho de upgrades e passivos
	f.add_to_group("flecha_jogador")
	if stats["poison_dps"] > 0.0:
		f.veneno_dps = stats["poison_dps"]
		f.veneno_t = stats["poison_time"]
	get_parent().add_child(f)
	if afinidade != "" and def.is_empty():   # só o tiro básico (as habilidades sempre passam o def delas)
		AfinidadeFx.aplicar(self, f, AfinidadeFx.def_de(self, afinidade))
	var c := Feel.cfg()
	Vfx.flash_boca(get_parent(), boca["chao"] + Vector2(0.0, -boca["altura"]), dir, f)
	recuar_sprite(dir, c["shot_recoil_px"], c["shot_recoil_time"])
	return f

## Várias cópias do mesmo disparo saem do mesmo arco uma a uma, com `projetil_atraso` entre elas (doc 33 seção 5).
## `dirs` são as direções já abertas em leque. Devolve a primeira flecha (as outras saem depois).
func lancar_flechas(dirs: Array, dano_mult := 1.0, pierce_extra := 0, vel_mult := 1.0, def := {}) -> Node:
	var primeira: Node = null
	var atraso: float = stats.get("projetil_atraso", 0.0)
	var eu: WeakRef = weakref(self)   # o temporizador não segura o jogador: se ele sumir antes, a cópia não sai
	for i in dirs.size():
		var d: Vector2 = dirs[i]
		if i == 0 or atraso <= 0.0:
			var f := lancar_flecha(d, dano_mult, pierce_extra, vel_mult, def)
			if primeira == null:
				primeira = f
		else:
			get_tree().create_timer(atraso * i).timeout.connect(func():
				var j: Node = eu.get_ref()
				if j != null and j.is_inside_tree() and not j.esta_morto():
					j.lancar_flecha(d, dano_mult, pierce_extra, vel_mult, def))
	return primeira

func _max_projeteis() -> int:
	if habilidades != null and habilidades.passivos != null:
		return int(habilidades.passivos.limite("max_projeteis", 120.0))
	return 120

## Stats finais: o core já somou meta, upgrades e passivas da árvore; aqui entram os nós `global` dos passivos.
func aplicar_passivos_stats() -> void:
	if habilidades != null:
		stats = habilidades.aplicar_passivos_globais(stats)

## Salto das habilidades: avança `dist` px na direção `dir` em `dur` s, invulnerável. Não gasta a recarga da esquiva.
func saltar(dir: Vector2, dist: float, dur: float) -> void:
	if estado == Estado.MORTO:
		return
	estado = Estado.ESQUIVA
	_dodge_dir = dir.normalized()
	_dodge_t = dur
	_salto_vel = dist / maxf(dur, 0.01)
	invencivel = maxf(invencivel, dur)
	play("dodge", true)
	Audio.tocar("dodge")

func dar_buff(dur: float, vel: float, cad: float) -> void:
	buff_t = dur
	vel_buff = vel
	cad_buff = cad

func _soltar_flecha() -> void:
	var n := int(stats["arrow_count"])  # gancho de upgrades: multishot abre as flechas em leque
	var dirs := []
	for i in n:
		dirs.append(_aim.rotated(deg_to_rad(stats["multishot_spread"]) * (i - (n - 1) * 0.5)))
	lancar_flechas(dirs)
	Audio.tocar("shoot")
	var c := Feel.cfg()
	velocity -= _aim * c["player_recoil"]
	Feel.shake(self, c["shake_shot_amp"], c["shake_shot_time"])

func _on_anim_finished() -> void:
	if estado == Estado.ATIRANDO:
		estado = Estado.LIVRE
	elif estado == Estado.MORTO:
		return

func take_damage(amount: float, _origem := Vector2.ZERO) -> void:
	if estado == Estado.MORTO or invencivel > 0.0 or god_mode:
		return
	hp = maxf(0.0, hp - amount)
	invencivel = stats["hit_iframes"]
	flash()
	Audio.tocar("player_hurt")
	var c := Feel.cfg()
	Feel.hit_stop(c["hit_stop_player_ms"])
	Feel.shake(self, c["shake_player_amp"], c["shake_player_time"])
	Feel.numero(self, amount, Color(1.0, 0.35, 0.3), true)
	hp_changed.emit(hp, stats["hp_max"])
	if hp <= 0.0:
		estado = Estado.MORTO
		play("death", true)
		died.emit()
