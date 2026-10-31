extends "res://scripts2d/actor_2d.gd"
## Inimigo 2D. Comportamento por `kind` em data2d/enemies.csv: melee, ranged, boss.

signal died(enemy)

const Csv = preload("res://scripts2d/csv2d.gd")
const ArrowScript = preload("res://scripts2d/arrow_2d.gd")
const Audio = preload("res://scripts2d/audio_2d.gd")

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
var raio_despertar := 0.0       # > 0: começa adormecido; acorda (com o grupo) quando o jogador chega a essa distância ou fere alguém

func setup(id: String, jogador: Node2D, pos: Vector2) -> void:
	stats = Csv.enemy(id)
	alvo = jogador
	global_position = pos
	hp = stats["hp"]
	hp_max = hp
	_burst_cd = stats["burst_interval"]
	_cd = stats["attack_cooldown"] * 0.5
	collision_layer = 4
	collision_mask = 1 | 4 | 8
	add_to_group("hurtable")
	shadow_radius = stats["radius"] * 1.2
	setup_sprite(id)
	var cs := CollisionShape2D.new()
	var sh := CircleShape2D.new()
	sh.radius = stats["radius"]
	cs.shape = sh
	add_child(cs)
	play("idle", true)

func _physics_process(delta: float) -> void:
	if estado == Estado.MORTO or alvo == null:
		return
	_tick_status(delta)
	if atordoado > 0.0:
		velocity = Vector2.ZERO
		move_and_slide()
		return
	_cd = maxf(0.0, _cd - delta)
	var para := alvo.global_position - global_position
	var dist := para.length()
	if raio_despertar > 0.0:
		if dist > raio_despertar:
			velocity = _kb
			move_and_slide()
			return
		despertar_grupo()
	var dir := para.normalized() if dist > 0.01 else Vector2.DOWN
	_kb = _kb.move_toward(Vector2.ZERO, Feel.cfg()["knockback_decay"] * delta)
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
	if dist <= stats["aggro"]:
		if stats["kind"] == "ranged":
			if dist < stats["keep_distance"] * 0.8:
				mover = -dir
			elif dist > stats["attack_range"] * 0.9:
				mover = dir
			if dist <= stats["attack_range"] and _cd <= 0.0 and not alvo_morto():
				_atacar()
		else:
			if dist > stats["attack_range"] * 0.8:
				mover = dir
			if dist <= stats["attack_range"] and _cd <= 0.0 and not alvo_morto():
				_atacar()
		if stats["burst_interval"] > 0.0:
			_burst_cd -= delta
			if _burst_cd <= 0.0:
				_burst_cd = stats["burst_interval"]
				_rajada()
	velocity = mover * stats["speed"] * vel_mult + _kb
	move_and_slide()
	if estado == Estado.PERSEGUE:
		play("run" if mover != Vector2.ZERO else "idle")

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
	_recalcular_status()

func tem_status(tipo: String) -> bool:
	return _status.has(tipo)

func _recalcular_status() -> void:
	dano_mult = 1.0 + (_status["marca"]["v"] if _status.has("marca") else 0.0)
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
		velocity = Vector2.ZERO
		remove_from_group("hurtable")
		set_deferred("collision_layer", 0)
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
