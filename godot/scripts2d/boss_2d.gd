extends "res://scripts2d/enemy_2d.gd"
## Guardião da Cripta: chefe em fases. Padrões, limiares de vida e tempos em data2d/boss_patterns_2d.csv.
## Padrões: golpe (área), leque (tiros mirados), anel (tiros em círculo), investida (avanço em linha reta).

enum Ciclo { ENTRADA, PAUSA, AVISO, ACAO, FASE, FIM }

const Tema = preload("res://scripts2d/tema_2d.gd")
const Arte = preload("res://scripts2d/hud_arte_2d.gd")

signal fase_mudou(fase: int)

var ciclo := Ciclo.ENTRADA
var fases := {}          # fase -> {pct, vel, passos: Array}
var fase := 1
var entrada_dur := 2.0
var passo := {}          # linha do CSV em andamento
var _idx := -1
var _t := 0.0            # tempo restante do estado atual
var _t_total := 0.0
var _espera := 0.0       # tempo já gasto esperando chegar perto para o golpe
var _disparou := false
var _dir_invest := Vector2.DOWN
var _invest_acertou := false
var _anel_alt := false
var _barra: CanvasLayer
var _ctl: Control

static func carregar_padroes() -> Dictionary:
	var out := {}
	var entrada := 2.2
	var ultima_trans := {}
	for r in Csv.rows("res://data2d/boss_patterns_2d.csv"):
		var f := int(r["fase"])
		var p := {}
		for k in r:
			p[k] = r[k] if k == "padrao" else float(r[k])
		if r["padrao"] == "entrada":
			entrada = p["duracao"]
			continue
		if not out.has(f):
			out[f] = {"pct": p["hp_pct"], "vel": p["vel_mult"], "trans": 0.0, "passos": []}
		if r["padrao"] == "transicao":
			out[f]["trans"] = p["duracao"]
			continue
		out[f]["passos"].append(p)
	out["entrada"] = entrada
	return out

func setup(id: String, jogador: Node2D, pos: Vector2) -> void:
	super.setup(id, jogador, pos)
	stats["hp_bar"] = 0.0     # a barra do chefe é a da tela, não a da cabeça
	var d := carregar_padroes()
	entrada_dur = d["entrada"]
	d.erase("entrada")
	fases = d
	_iniciar_ciclo(Ciclo.ENTRADA, entrada_dur)
	sprite.modulate.a = 0.0
	_criar_barra()

func total_fases() -> int:
	return fases.size()

func invulneravel() -> bool:
	return ciclo == Ciclo.ENTRADA or ciclo == Ciclo.FASE

func _iniciar_ciclo(c: Ciclo, dur: float) -> void:
	ciclo = c
	_t = dur
	_t_total = dur

func _physics_process(delta: float) -> void:
	if estado == Estado.MORTO or alvo == null:
		return
	var para := alvo.global_position - global_position
	var dist := para.length()
	var dir := para.normalized() if dist > 0.01 else Vector2.DOWN
	_kb = _kb.move_toward(Vector2.ZERO, Feel.cfg()["knockback_decay"] * delta)
	_t -= delta
	var mover := Vector2.ZERO
	match ciclo:
		Ciclo.ENTRADA:
			facing = Vector2.DOWN
			sprite.modulate.a = clampf(1.0 - _t / maxf(_t_total * 0.7, 0.01), 0.0, 1.0)
			if _t <= 0.0:
				sprite.modulate.a = 1.0
				Feel.shake(self, 5.0, 0.3)
				_proxima_pausa(0.6)
		Ciclo.FASE:
			facing = dir
			if _t <= 0.0:
				_proxima_pausa(fases[fase]["passos"][0].get("pausa", 1.0) * 0.5)
		Ciclo.PAUSA:
			facing = dir
			if dist > stats["attack_range"] * 0.8:
				mover = dir * fases[fase]["vel"]
			if _t <= 0.0 and not alvo_morto():
				_escolher_passo(dist)
		Ciclo.AVISO:
			if passo["padrao"] != "investida" or _t > 0.0:
				facing = dir
			if _t <= 0.0:
				_executar(dir)
		Ciclo.ACAO:
			if passo["padrao"] == "investida":
				mover = _dir_invest * passo["vel_proj"] / stats["speed"]
				if not _invest_acertou and dist <= stats["radius"] + 22.0:
					_invest_acertou = true
					alvo.take_damage(stats["damage"] * passo["dano_mult"], global_position)
				if _t <= 0.0:
					_terminar_passo()
			elif _t <= -1.5:   # sem animação de ataque: não trava o chefe
				_disparar()
				_terminar_passo()
	velocity = mover * stats["speed"] + _kb
	move_and_slide()
	if ciclo == Ciclo.PAUSA or (ciclo == Ciclo.ACAO and passo.get("padrao", "") == "investida"):
		play("run" if mover != Vector2.ZERO else "idle")
	elif ciclo == Ciclo.AVISO or ciclo == Ciclo.ENTRADA or ciclo == Ciclo.FASE:
		play("idle")

func _proxima_pausa(seg: float) -> void:
	_iniciar_ciclo(Ciclo.PAUSA, seg)
	_espera = 0.0

func _escolher_passo(dist: float) -> void:
	var passos: Array = fases[fase]["passos"]
	var prox: Dictionary = passos[(_idx + 1) % passos.size()]
	# o golpe só sai com o jogador ao alcance; espera um pouco e segue com o próximo padrão se não chegar
	if prox["padrao"] == "golpe" and dist > prox["alcance"] * 1.1 and _espera < 2.5:
		_espera += 0.1
		_t = 0.1
		return
	_idx = (_idx + 1) % passos.size()
	passo = prox
	_iniciar_ciclo(Ciclo.AVISO, passo["aviso"])
	_wind_total = passo["aviso"]
	_wind = _wind_total

func _executar(dir: Vector2) -> void:
	_disparou = false
	_iniciar_ciclo(Ciclo.ACAO, passo["duracao"])
	if passo["padrao"] == "investida":
		_dir_invest = dir
		_invest_acertou = false
		facing = dir
		return
	_t = 0.0
	if has_anim("attack"):
		play("attack", true)
	else:
		_t = 0.0   # o relógio de segurança em ACAO dispara o padrão

func _on_frame_changed() -> void:
	if ciclo != Ciclo.ACAO or anim_base() != "attack" or _disparou:
		return
	if sprite.frame < evento("attack"):
		return
	_disparar()

func _on_anim_finished() -> void:
	if estado == Estado.MORTO:
		queue_free()
	elif ciclo == Ciclo.ACAO and passo.get("padrao", "") != "investida":
		_disparar()
		_terminar_passo()

func _terminar_passo() -> void:
	_proxima_pausa(passo["pausa"])

func _disparar() -> void:
	if _disparou:
		return
	_disparou = true
	var dano: float = stats["damage"] * passo["dano_mult"]
	var vel: float = passo["vel_proj"]
	var n := int(passo["qtd"])
	match passo["padrao"]:
		"golpe":
			if alvo.global_position.distance_to(global_position) <= passo["alcance"] * 1.3:
				alvo.take_damage(dano, global_position)
			Feel.shake(self, 3.0, 0.15)
		"leque":
			var base := (alvo.global_position - global_position).angle()
			var abre := deg_to_rad(passo["abertura"])
			for i in n:
				var a := base + (abre * (float(i) / maxf(n - 1, 1) - 0.5) if n > 1 else 0.0)
				_proj_chefe(Vector2.from_angle(a), dano, vel)
		"anel":
			var off := PI / n if _anel_alt else 0.0
			_anel_alt = not _anel_alt
			for i in n:
				_proj_chefe(Vector2.from_angle(TAU * i / n + off), dano, vel)

func _proj_chefe(dir: Vector2, dano: float, vel: float) -> void:
	var f := ArrowScript.new()
	f.setup("enemy", global_position + dir * 30.0, dir, vel, dano, 1400.0)
	f.add_to_group("proj_chefe")
	get_parent().add_child(f)

func take_damage(amount: float, origem := Vector2.ZERO) -> void:
	# 1e8 ou mais é o atalho de depuração (matar_todos), que ignora a invulnerabilidade
	if estado == Estado.MORTO or (invulneravel() and amount < 1.0e8):
		return
	super.take_damage(amount, origem)
	if estado == Estado.MORTO:
		_ao_morrer()
		return
	var prox := fase + 1
	if fases.has(prox) and hp / hp_max * 100.0 <= fases[prox]["pct"]:
		_entrar_fase(prox)

func _entrar_fase(f: int) -> void:
	fase = f
	_idx = -1
	_disparou = true
	_iniciar_ciclo(Ciclo.FASE, maxf(fases[f]["trans"], 0.01))
	Feel.shake(self, 8.0, 0.4)
	Feel.hit_stop(120.0)
	flash()
	fase_mudou.emit(f)

func _ao_morrer() -> void:
	ciclo = Ciclo.FIM
	for n in get_tree().get_nodes_in_group("proj_chefe"):
		n.queue_free()
	Feel.hit_stop(220.0)
	Feel.shake(self, 10.0, 0.6)
	if _barra != null:
		_barra.visible = false

# --- barra de vida do chefe -------------------------------------------------

func _criar_barra() -> void:
	_barra = CanvasLayer.new()
	_barra.layer = 2
	_ctl = Control.new()
	_ctl.set_anchors_preset(Control.PRESET_FULL_RECT)
	_ctl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_ctl.draw.connect(_desenhar_barra)
	_barra.add_child(_ctl)
	add_child(_barra)

func _process(delta: float) -> void:
	super._process(delta)
	if _ctl != null:
		_ctl.queue_redraw()

func _desenhar_barra() -> void:
	if estado == Estado.MORTO or ciclo == Ciclo.FIM:
		return
	var vp := _ctl.size
	var alfa := 1.0 if ciclo != Ciclo.ENTRADA else clampf(1.0 - _t / maxf(_t_total, 0.01), 0.0, 1.0)
	_ctl.modulate.a = alfa
	var pos := Vector2(vp.x / 2 - 300, 62)
	var tam := Vector2(600, 18)
	var cor := Color(0.6, 0.2, 0.7) if fase == 1 else (Color(0.8, 0.25, 0.55) if fase == 2 else Color(0.9, 0.2, 0.2))
	Arte.barra(_ctl, Rect2(pos, tam), hp / hp_max, cor.darkened(0.6), cor.lightened(0.15))
	for f in fases:
		if f > 1:
			var x: float = pos.x + tam.x * fases[f]["pct"] / 100.0
			_ctl.draw_rect(Rect2(x - 1.5, pos.y - 3, 3, tam.y + 6), Tema.cor("destaque"))
	Arte.texto(_ctl, pos + Vector2(0, -10), Csv.t("hud.boss"), 18, Tema.cor("destaque"), HORIZONTAL_ALIGNMENT_LEFT)
	Arte.texto(_ctl, pos + Vector2(0, -10), Csv.t("hud.boss_phase") % [fase, total_fases()], 14, Tema.cor("texto_suave"), HORIZONTAL_ALIGNMENT_RIGHT, tam.x)

## Aviso por padrão: área (golpe), linha de mira (leque/investida) ou anel que se expande (anel).
func _draw() -> void:
	super._draw()
	if ciclo != Ciclo.AVISO or _wind_total <= 0.0 or passo.is_empty():
		return
	var p := clampf(1.0 - _t / _wind_total, 0.0, 1.0)
	var a: float = Feel.cfg()["telegraph_alpha"]
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	match passo["padrao"]:
		"golpe":
			var r: float = passo["alcance"] * 1.3
			draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.6))
			draw_circle(Vector2.ZERO, r, Color(1, 0.15, 0.1, a * 0.35))
			draw_circle(Vector2.ZERO, r * p, Color(1, 0.15, 0.1, a))
			draw_arc(Vector2.ZERO, r, 0.0, TAU, 32, Color(1, 0.3, 0.2, a + 0.3), 2.0)
		"investida":
			var fim: Vector2 = _dir_para_alvo() * float(passo["vel_proj"]) * float(passo["duracao"])
			draw_line(Vector2(0, -20), Vector2(0, -20) + fim, Color(1, 0.2, 0.2, a * p), 4.0 + 6.0 * p)
		"leque":
			var base := (alvo.global_position - global_position).angle()
			var abre := deg_to_rad(passo["abertura"])
			for s in [-0.5, 0.5]:
				draw_line(Vector2(0, -30), Vector2(0, -30) + Vector2.from_angle(base + abre * s) * 360.0, Color(1, 0.2, 0.2, a * p), 2.0)
		"anel":
			draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.6))
			draw_arc(Vector2.ZERO, 120.0 * p + 20.0, 0.0, TAU, 40, Color(0.8, 0.3, 1.0, a + 0.3), 3.0)

func _dir_para_alvo() -> Vector2:
	return (alvo.global_position - global_position).normalized()
