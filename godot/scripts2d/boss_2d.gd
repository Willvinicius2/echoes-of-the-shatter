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
var _glow_t := 0.0       # brilho no corpo restante após a troca de fase
var _glow_total := 1.0
var _entrada_avisada := false

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
	sprite.modulate.a = 0.7
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
	_tick_status(delta)
	var para := alvo.global_position - global_position
	var dist := para.length()
	var dir := para.normalized() if dist > 0.01 else Vector2.DOWN
	_kb = _kb.move_toward(Vector2.ZERO, Feel.cfg()["knockback_decay"] * delta)
	_t -= delta
	var mover := Vector2.ZERO
	match ciclo:
		Ciclo.ENTRADA:
			facing = Vector2.DOWN
			if not _entrada_avisada:
				_entrada_avisada = true
				var c := Feel.cfg()
				Feel.shake(self, c["boss_entry_shake_amp"], _t_total * 0.85)
				Feel.zoom_punch(self, c["boss_entry_zoom"], _t_total)
			sprite.modulate.a = 0.7 + 0.3 * clampf(1.0 - _t / maxf(_t_total * 0.7, 0.01), 0.0, 1.0)
			if _t <= 0.0:
				sprite.modulate.a = 1.0
				Feel.shake(self, 5.0, 0.3)
				Feel.impacto(get_parent(), global_position, Color(1.0, 0.3, 0.25), Vector2.ZERO, 6.0)
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
	velocity = mover * stats["speed"] * vel_mult + _kb
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
		dissolver(Feel.cfg()["death_dissolve_time"] * 1.6)
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
			Feel.impacto(get_parent(), global_position, Color(1.0, 0.35, 0.2), Vector2.ZERO, float(passo["alcance"]) * 1.3 / 20.0)
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
	var c := Feel.cfg()
	_glow_total = c["boss_phase_glow_time"]
	_glow_t = _glow_total
	_mat.set_shader_parameter("glow_color", Color(0.9, 0.25, 0.55) if f == 2 else Color(1.0, 0.2, 0.15))
	Feel.impacto(get_parent(), global_position, Color(1.0, 0.3, 0.4), Vector2.ZERO, c["boss_phase_wave"] / 20.0)
	Feel.particulas(get_parent(), global_position + Vector2(0, -50), Color(1.0, 0.35, 0.4), 28, 220.0, 0.6, Vector2.ZERO, 0.2)
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
	if _glow_t > 0.0:
		_glow_t -= delta
		var k := clampf(_glow_t / _glow_total, 0.0, 1.0)
		_mat.set_shader_parameter("glow", k * (0.55 + 0.3 * sin(_glow_t * 24.0)))
	elif _mat != null and ciclo == Ciclo.ENTRADA:
		_mat.set_shader_parameter("glow", 0.35 * (1.0 - clampf(_t / maxf(_t_total, 0.01), 0.0, 1.0)))
	elif _mat != null:
		_mat.set_shader_parameter("glow", 0.0)
	super._process(delta)
	if _ctl != null:
		_ctl.queue_redraw()

func _desenhar_barra() -> void:
	if estado == Estado.MORTO or ciclo == Ciclo.FIM:
		return
	var vp := _ctl.size
	var alfa := 1.0 if ciclo != Ciclo.ENTRADA else clampf(1.0 - _t / maxf(_t_total, 0.01), 0.0, 1.0)
	_ctl.modulate.a = alfa
	# moldura pintada em tamanho fixo no topo; a caveira fica centrada sobre a porta (cx) e a barra roxa e o nome
	# serifado ficam dentro do canal da moldura (docs/arte/29_arte_ui_gpt_image.md)
	var cx: float = vp.x * 0.5 + Csv.kv("res://data2d/hud_layout.csv")["chefe_deslocamento_x"]
	var canal := Arte.canal_chefe(cx, 4.0)
	var cor := Color(0.6, 0.2, 0.7) if fase == 1 else (Color(0.8, 0.25, 0.55) if fase == 2 else Color(0.9, 0.2, 0.2))
	_ctl.draw_rect(canal, Color(0.02, 0.015, 0.03))
	var frac := clampf(hp / hp_max, 0.0, 1.0)
	_ctl.draw_polygon(PackedVector2Array([canal.position, canal.position + Vector2(canal.size.x * frac, 0), canal.position + Vector2(canal.size.x * frac, canal.size.y), canal.position + Vector2(0, canal.size.y)]), PackedColorArray([cor.lightened(0.2), cor.lightened(0.2), cor.darkened(0.5), cor.darkened(0.5)]))
	_ctl.draw_rect(Rect2(canal.position + Vector2(0, 1), Vector2(canal.size.x * frac, 3)), Color(1, 1, 1, 0.2))
	for f in fases:
		if f > 1:
			var x: float = canal.position.x + canal.size.x * fases[f]["pct"] / 100.0
			_ctl.draw_rect(Rect2(x - 1.5, canal.position.y, 3, canal.size.y), Tema.cor("destaque"))
	Arte.moldura_chefe(_ctl, cx, 4.0)
	var base_y := canal.position.y + canal.size.y - 4.0
	Arte.texto(_ctl, Vector2(canal.position.x + 14.0, base_y), Csv.t("hud.boss"), 16, Tema.cor("texto"), HORIZONTAL_ALIGNMENT_LEFT, -1.0, true)
	var total := total_fases()
	var texto_fase: String = Csv.t("hud.boss_phase") % [fase, total]
	var larg_txt := ThemeDB.fallback_font.get_string_size(texto_fase, HORIZONTAL_ALIGNMENT_LEFT, -1, 14).x
	Arte.texto(_ctl, Vector2(canal.position.x, base_y), texto_fase, 14, Tema.cor("texto"), HORIZONTAL_ALIGNMENT_RIGHT, canal.size.x - 12.0)
	for i in total:   # losangos de fase à esquerda do texto: cheio = fase atual ou passada
		Arte.runa(_ctl, Vector2(canal.end.x - 12.0 - larg_txt - 20.0 - (total - 1 - i) * 20.0, canal.position.y + canal.size.y * 0.5), i, i < fase)

## Marca vermelha no chão por padrão: área (golpe), faixa (investida), cunha (leque) ou anel (anel).
func _draw() -> void:
	super._draw()
	if ciclo == Ciclo.ENTRADA and _t_total > 0.0:
		_desenhar_marca_entrada()
		return
	if ciclo != Ciclo.AVISO or _wind_total <= 0.0 or passo.is_empty():
		return
	var p := clampf(1.0 - _t / _wind_total, 0.0, 1.0)
	var a: float = Feel.cfg()["boss_mark_alpha"]
	var pulso := 0.5 + 0.5 * sin(p * 26.0)
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	match passo["padrao"]:
		"golpe":
			var r: float = passo["alcance"] * 1.3
			draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.6))
			draw_circle(Vector2.ZERO, r, Color(0.9, 0.08, 0.05, a * 0.3))
			draw_circle(Vector2.ZERO, r * p, Color(1, 0.12, 0.08, a * (0.55 + 0.35 * p)))
			draw_arc(Vector2.ZERO, r, 0.0, TAU, 48, Color(1, 0.45, 0.3, minf(1.0, a + 0.3 + 0.2 * pulso * p)), 3.0 + 2.0 * p)
		"investida":
			var comp: float = float(passo["vel_proj"]) * float(passo["duracao"])
			var larg: float = stats["radius"] + 22.0
			var d := _dir_para_alvo()
			var n := d.orthogonal() * larg
			var fim := d * comp
			draw_colored_polygon(PackedVector2Array([n, fim + n, fim - n, -n]), Color(0.9, 0.08, 0.05, a * 0.3))
			var fr := fim * p
			draw_colored_polygon(PackedVector2Array([n, fr + n, fr - n, -n]), Color(1, 0.12, 0.08, a * 0.6))
			draw_line(n, fim + n, Color(1, 0.45, 0.3, a + 0.25), 2.0)
			draw_line(-n, fim - n, Color(1, 0.45, 0.3, a + 0.25), 2.0)
		"leque":
			var base := (alvo.global_position - global_position).angle()
			var abre := deg_to_rad(passo["abertura"])
			var cunha := PackedVector2Array([Vector2.ZERO])
			for i in 13:
				cunha.append(Vector2.from_angle(base - abre / 2.0 + abre * i / 12.0) * 360.0)
			draw_colored_polygon(cunha, Color(0.9, 0.08, 0.05, a * 0.2 * (0.4 + 0.6 * p)))
			for sd in [-0.5, 0.5]:
				draw_line(Vector2.ZERO, Vector2.from_angle(base + abre * sd) * 360.0, Color(1, 0.4, 0.3, a * (0.4 + 0.6 * p) + 0.15), 2.0)
		"anel":
			draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.6))
			draw_circle(Vector2.ZERO, 120.0 * p + 20.0, Color(0.7, 0.2, 0.9, a * 0.25))
			draw_arc(Vector2.ZERO, 120.0 * p + 20.0, 0.0, TAU, 40, Color(0.8, 0.3, 1.0, a + 0.3), 3.0)

## Marca no chão enquanto o chefe se materializa: anel vermelho que cresce e pulsa.
func _desenhar_marca_entrada() -> void:
	var p := clampf(1.0 - _t / _t_total, 0.0, 1.0)
	var r: float = Feel.cfg()["boss_entry_mark"]
	var a: float = Feel.cfg()["boss_mark_alpha"]
	draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.6))
	draw_circle(Vector2.ZERO, r * p, Color(1.0, 0.05, 0.03, minf(1.0, a * 0.75)))
	draw_arc(Vector2.ZERO, r * p, 0.0, TAU, 64, Color(1, 0.55, 0.35, 1.0), 4.0)
	draw_arc(Vector2.ZERO, r * 0.6 * p, 0.0, TAU, 48, Color(1, 0.3, 0.2, 0.9), 3.0)

func _dir_para_alvo() -> Vector2:
	return (alvo.global_position - global_position).normalized()
