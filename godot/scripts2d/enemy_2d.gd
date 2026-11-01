extends "res://scripts2d/actor_2d.gd"
## Inimigo 2D. Comportamento por `kind` em data2d/enemies.csv: melee, ranged, boss.

signal died(enemy)

const Csv = preload("res://scripts2d/csv2d.gd")
const ArrowScript = preload("res://scripts2d/arrow_2d.gd")
const Audio = preload("res://scripts2d/audio_2d.gd")
const Veneno = preload("res://scripts2d/efeitos_arqueiro_veneno_2d.gd")
const Fogo = preload("res://scripts2d/efeitos_arqueiro_fogo_2d.gd")

enum Estado { PERSEGUE, TELEGRAFA, ATACANDO, MORTO }

var stats := {}
var hp := 0.0
var hp_max := 0.0
var alvo: Node2D
var estado := Estado.PERSEGUE
var _cd := 0.0
var _burst_cd := 0.0
var _acertou := false
var _wind := 0.0                # tempo restante do aviso antes do golpe
var _wind_total := 0.0
var _kb := Vector2.ZERO         # empurrão por golpe recebido
var dano_mult := 1.0            # status marca: dano recebido multiplicado
var vel_mult := 1.0             # status lentidão: velocidade multiplicada
var atordoado := 0.0            # status atordoamento: segundos parado
var _status := {}               # id -> {t: segundos restantes, v: valor}
## Inimigos vivos na cena: com horda grande, quem só persegue atualiza a cada 2 ou 3 quadros (com o `delta`
## acumulado), cada um numa fase própria, para o custo de física não crescer linear com a horda.
static var vivos_n := 0
const HORDA_PASSO2 := 400
const HORDA_PASSO3 := 900
const CELULA := 40.0
static var _grade := {}
static var _grade_quadro := -1
var _acum := 0.0
var _contado := false
var _kind := ""
var _speed := 0.0
var _aggro := 0.0
var _range := 0.0
var _keep := 0.0
var _burst := 0.0
var _kb_decay := 0.0
var raio_despertar := 0.0       # > 0: começa adormecido; acorda (com o grupo) quando o jogador chega a essa distância ou fere alguém

func setup(id: String, jogador: Node2D, pos: Vector2) -> void:
	stats = Csv.enemy(id)
	alvo = jogador
	global_position = pos
	hp = stats["hp"]
	hp_max = hp
	vivos_n += 1
	_contado = true
	_kind = stats["kind"]
	_speed = stats["speed"]
	_aggro = stats["aggro"]
	_range = stats["attack_range"]
	_keep = stats["keep_distance"]
	_burst = stats["burst_interval"]
	_kb_decay = Feel.cfg()["knockback_decay"]
	_burst_cd = stats["burst_interval"]
	_cd = stats["attack_cooldown"] * 0.5
	motion_mode = CharacterBody2D.MOTION_MODE_FLOATING   # visão de cima: sem chão nem gravidade
	max_slides = 2
	collision_layer = 4
	collision_mask = 1 | 8
	add_to_group("hurtable")
	shadow_radius = stats["radius"] * 1.2
	setup_sprite(id)
	var cs := CollisionShape2D.new()
	var sh := CircleShape2D.new()
	sh.radius = stats["radius"]
	cs.shape = sh
	add_child(cs)
	play("idle", true)

## Separação leve (no lugar da colisão física entre inimigos, que custava O(n²)): empurra para longe de quem está
## na mesma célula da grade, reconstruída uma vez por quadro de física. No máximo 4 vizinhos por inimigo.
func _separacao() -> Vector2:
	var q := Engine.get_physics_frames()
	if _grade_quadro != q:
		_grade_quadro = q
		_grade.clear()
	var c := Vector2i((global_position / CELULA).floor())
	var cel: Array = _grade.get(c, [])
	var push := Vector2.ZERO
	var viz := 0
	for outro in cel:
		var d: Vector2 = global_position - outro
		var l2 := d.length_squared()
		if l2 < CELULA * CELULA and l2 > 0.01:
			push += d / l2 * CELULA
			viz += 1
			if viz >= 4:
				break
	if cel.size() < 8:
		cel.append(global_position)
		_grade[c] = cel
	return push

func _descontar() -> void:
	if _contado:
		_contado = false
		vivos_n -= 1

func _exit_tree() -> void:
	_descontar()

func _precisa_redesenhar() -> bool:
	return estado != Estado.PERSEGUE or _morrendo or hp < hp_max

func _physics_process(delta: float) -> void:
	if estado == Estado.MORTO or alvo == null:
		return
	if estado == Estado.PERSEGUE and vivos_n > HORDA_PASSO2:
		var passo := 2 if vivos_n <= HORDA_PASSO3 else 3
		_acum += delta
		if (Engine.get_physics_frames() + get_instance_id()) % passo != 0:
			return
		delta = _acum
		_acum = 0.0
	if not _status.is_empty():
		_tick_status(delta)
	if atordoado > 0.0:
		velocity = Vector2.ZERO
		move_and_slide()
		return
	if _cd > 0.0:
		_cd = maxf(0.0, _cd - delta)
	var para := alvo.global_position - global_position
	var dist := para.length()
	if raio_despertar > 0.0:
		if dist > raio_despertar:
			_mover_parado()
			return
		despertar_grupo()
	var dir := para / dist if dist > 0.01 else Vector2.DOWN
	if _kb != Vector2.ZERO:
		_kb = _kb.move_toward(Vector2.ZERO, _kb_decay * delta)
	if estado == Estado.TELEGRAFA:
		facing = dir
		_wind -= delta
		if _wind <= 0.0:
			_golpear()
		velocity = _kb
		move_and_slide()
		return
	if estado == Estado.ATACANDO:
		velocity = _kb
		move_and_slide()
		return
	facing = dir
	var mover := Vector2.ZERO
	if dist <= _aggro:
		if _kind == "ranged":
			if dist < _keep * 0.8:
				mover = -dir
			elif dist > _range * 0.9:
				mover = dir
		elif dist > _range * 0.8:
			mover = dir
		if dist <= _range and _cd <= 0.0 and not alvo_morto():
			_atacar()
		if _burst > 0.0:
			_burst_cd -= delta
			if _burst_cd <= 0.0:
				_burst_cd = _burst
				_rajada()
	if mover != Vector2.ZERO:
		mover = (mover + _separacao() * 0.8).limit_length(1.0)
	velocity = mover * _speed * vel_mult + _kb
	if velocity != Vector2.ZERO:   # parado e sem empurrão: nada a resolver na física
		move_and_slide()
	if estado == Estado.PERSEGUE:
		play("run" if mover != Vector2.ZERO else "idle")

## Sem mover por vontade própria: só o empurrão de golpes (adormecido, atordoado).
func _mover_parado() -> void:
	velocity = _kb
	if _kb != Vector2.ZERO:
		move_and_slide()

## Adormecidos acordam juntos: o primeiro que vê o jogador (ou leva dano) chama o resto da sala.
func adormecer(raio: float) -> void:
	raio_despertar = raio
	add_to_group("inimigos_adormecidos")

func despertar_grupo() -> void:
	if is_inside_tree():
		get_tree().call_group("inimigos_adormecidos", "despertar")

func despertar() -> void:
	raio_despertar = 0.0
	remove_from_group("inimigos_adormecidos")

func alvo_morto() -> bool:
	return alvo.has_method("esta_morto") and alvo.esta_morto()

## Começa o aviso (telégrafo); o golpe só sai quando `windup` acaba, dando tempo de esquivar.
func _atacar() -> void:
	_cd = stats["attack_cooldown"]
	_wind_total = stats.get("windup", 0.0)
	_wind = _wind_total
	if _wind <= 0.0:
		_golpear()
		return
	estado = Estado.TELEGRAFA
	play("idle")

func _golpear() -> void:
	estado = Estado.ATACANDO
	_acertou = false
	play("attack", true)

func _on_frame_changed() -> void:
	if estado != Estado.ATACANDO or anim_base() != "attack" or _acertou:
		return
	if sprite.frame < evento("attack"):
		return
	_acertou = true
	if stats["kind"] == "ranged":
		_projetil((alvo.global_position - global_position).normalized(), stats["damage"])
	elif alvo.global_position.distance_to(global_position) <= stats["attack_range"] * 1.3:
		alvo.take_damage(stats["damage"], global_position)

func _on_anim_finished() -> void:
	if estado == Estado.ATACANDO:
		estado = Estado.PERSEGUE
	elif estado == Estado.MORTO:
		dissolver(Feel.cfg()["death_dissolve_time"])

func _rajada() -> void:
	var n := int(stats["burst_count"])
	for i in n:
		_projetil(Vector2.RIGHT.rotated(TAU * i / n), stats["damage"])

func _projetil(dir: Vector2, dano: float) -> void:
	var f := ArrowScript.new()
	f.setup("enemy", global_position + dir * 30.0, dir, stats["projectile_speed"], dano, 1400.0)
	get_parent().add_child(f)

## Status das habilidades: veneno e queimadura (v = dano/s), marca (v = dano extra), lentidao (v = fração de velocidade
## perdida), atordoamento. Reaplicar renova a duração e fica com o maior valor.
func aplicar_status(tipo: String, dur: float, valor := 0.0) -> void:
	if estado == Estado.MORTO:
		return
	var atual: Dictionary = _status.get(tipo, {"t": 0.0, "v": 0.0})
	_status[tipo] = {"t": maxf(atual["t"], dur), "v": maxf(atual["v"], valor)}
	if tipo == "veneno":
		Veneno.overlay_status(self, dur)
	elif tipo == "queimadura" and not has_node("OverlayQueimadura"):
		Fogo.overlay_queimadura(self).name = "OverlayQueimadura"
	_recalcular_status()

func tem_status(tipo: String) -> bool:
	return _status.has(tipo)

func _recalcular_status() -> void:
	dano_mult = 1.0 + (_status["marca"]["v"] if _status.has("marca") else 0.0) + (_status["choque"]["v"] if _status.has("choque") else 0.0)
	vel_mult = 1.0 - (_status["lentidao"]["v"] if _status.has("lentidao") else 0.0)
	atordoado = _status["atordoamento"]["t"] if _status.has("atordoamento") else 0.0

func _tick_status(delta: float) -> void:
	if _status.is_empty():
		return
	var mudou := false
	for tipo in _status.keys():
		var st: Dictionary = _status[tipo]
		if tipo == "veneno" or tipo == "queimadura":
			st["acc"] = st.get("acc", 0.0) + delta
			if st["acc"] >= 0.5:   # dano em pulsos de meio segundo, para não piscar todo quadro
				take_damage(st["v"] * st["acc"])
				st["acc"] = 0.0
		st["t"] -= delta
		if st["t"] <= 0.0:
			_status.erase(tipo)
			mudou = true
			if tipo == "queimadura" and has_node("OverlayQueimadura"):
				get_node("OverlayQueimadura").queue_free()
		elif tipo == "atordoamento":
			atordoado = st["t"]
		if estado == Estado.MORTO:
			return
	if mudou:
		_recalcular_status()

func take_damage(amount: float, _origem := Vector2.ZERO) -> void:
	if estado == Estado.MORTO:
		return
	amount *= dano_mult
	if raio_despertar > 0.0:
		despertar_grupo()
	var mostrado := minf(amount, hp)
	hp -= amount
	flash()
	var morreu := hp <= 0.0
	_feedback_golpe(mostrado, _origem, morreu)
	if morreu:
		estado = Estado.MORTO
		_descontar()
		velocity = Vector2.ZERO
		remove_from_group("hurtable")
		set_deferred("collision_layer", 0)
		if alvo != null and alvo.has_method("herald_morte"):
			alvo.herald_morte(self, -hp)   # gatilhos de morte dos Heralds; -hp = dano que passou da vida (overkill)
		died.emit(self)
		Feel.morte(get_parent(), global_position + Vector2(0, -30), Color(0.8, 0.95, 1.0))
		if has_anim("death"):
			play("death", true)
		else:
			dissolver(Feel.cfg()["death_dissolve_time"])

func _feedback_golpe(amount: float, origem: Vector2, morreu: bool) -> void:
	Audio.tocar("kill_enemy" if morreu else "hit_enemy")
	var c := Feel.cfg()
	var forte: bool = not morreu and amount >= hp_max * c["strong_hit_pct"]
	var stop: float = c["hit_stop_kill_ms"] if morreu else (c["hit_stop_strong_ms"] if forte else c["hit_stop_hit_ms"])
	if origem != Vector2.ZERO or morreu:   # veneno e queimadura (sem origem) não congelam nem tremem a tela a cada pulso
		Feel.hit_stop(stop)
		Feel.shake(self, c["shake_kill_amp" if morreu else "shake_hit_amp"], c["shake_kill_time" if morreu else "shake_hit_time"])
		tremer_sprite(c["sprite_shake_px"], c["sprite_shake_time"])
	Feel.numero(self, amount, Color(1.0, 0.85, 0.2) if (morreu or forte) else (Color(1.0, 0.65, 0.15) if amount >= hp_max * c["weak_hit_pct"] else Color.WHITE), morreu, forte)
	if origem != Vector2.ZERO:
		var dir := (global_position - origem).normalized()
		_kb = dir * c["enemy_knockback"] * (1.0 - stats.get("kb_resist", 0.0))

func _draw() -> void:
	super._draw()
	if estado == Estado.TELEGRAFA and _wind_total > 0.0:
		_desenhar_aviso()
	if stats.get("hp_bar", 0.0) > 0.0 and estado != Estado.MORTO and hp < hp_max:
		var larg := 40.0
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
		var topo := -90.0 * (escala_sprite())
		draw_rect(Rect2(-larg / 2.0, topo, larg, 5.0), Color(0, 0, 0, 0.7))
		draw_rect(Rect2(-larg / 2.0, topo, larg * hp / hp_max, 5.0), Color(0.8, 0.15, 0.15))

## Aviso de ataque: área vermelha que enche até o golpe (melee) ou linha de mira (ranged/chefe).
func _desenhar_aviso() -> void:
	var p := clampf(1.0 - _wind / _wind_total, 0.0, 1.0)
	var a: float = Feel.cfg()["telegraph_alpha"]
	if stats["kind"] == "ranged":
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
		var fim := (alvo.global_position - global_position).normalized() * minf(stats["attack_range"], 600.0)
		draw_line(Vector2(0, -30), Vector2(0, -30) + fim, Color(1, 0.2, 0.2, a * p), 2.0 + 3.0 * p)
		return
	var r: float = stats["attack_range"] * 1.3
	draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.6))
	draw_circle(Vector2.ZERO, r, Color(1, 0.15, 0.1, a * 0.35))
	draw_circle(Vector2.ZERO, r * p, Color(1, 0.15, 0.1, a))
	draw_arc(Vector2.ZERO, r, 0.0, TAU, 32, Color(1, 0.3, 0.2, a + 0.3), 2.0)
