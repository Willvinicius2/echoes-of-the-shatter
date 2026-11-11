extends "res://scripts2d/enemy_2d.gd"
## Tecelã de Cascalho (chefe da Ponte do Sino): o corpo a corpo do inimigo comum mais três golpes próprios, em ciclo, cada um com
## aviso no chão antes de sair (docs/arte/37_ponte_do_sino.md):
##   teia      mancha de teia sob o jogador (posição travada no início do aviso) que desacelera quem fica dentro; a esquiva sai dela
##   badalada  onda de choque em anel, do sino para fora; só a esquiva (invulnerável) a atravessa sem dano
##   filhotes  chama uma ninhada de Filhotes de Cascalho em volta dela (espera se já há muitos vivos)
## Abaixo de `tecela_fase2_hp_pct` da vida ela entra na fase 2: avisos mais curtos, pausas menores e ninhadas maiores.
## Tempos, raios e dano: data2d/tecela_golpes_2d.csv e as chaves `tecela_*` de run_settings.csv.

const Efeitos = preload("res://scripts2d/tecela_efeitos_2d.gd")

## Quem liga o chefe ao resto da partida (run_2d.gd): pontos livres no mapa e o nascimento dos filhotes.
var pontos_livres := Callable()   # (centro, raio, n) -> Array de Vector2
var convocar := Callable()        # (id do inimigo, pontos) -> Array de inimigos nascidos

var _golpes: Array = []
var _cfg := {}
var _idx := 0
var _golpe := {}          # golpe em andamento (vazio = nenhum)
var _t := 0.0             # aviso restante; depois, recuperação restante
var _aviso := 1.0
var _solto := false       # aviso acabou: a animação de ataque toca e o efeito sai no quadro de contato
var _efeito_feito := false
var _pausa := 0.0
var _fase2 := false
var _alvo_pos := Vector2.ZERO
var _pontos: Array = []
var _filhotes: Array = []

func setup(id: String, jogador: Node2D, pos: Vector2) -> void:
	super.setup(id, jogador, pos)
	_cfg = Csv.kv("res://data2d/run_settings.csv")
	_golpes = Csv.rows("res://data2d/tecela_golpes_2d.csv")
	_golpes.sort_custom(func(a, b) -> bool: return int(a["ordem"]) < int(b["ordem"]))
	_pausa = float(_cfg.get("tecela_primeira_pausa", 1.6))
	died.connect(_ao_morrer)

func _precisa_redesenhar() -> bool:
	return not _golpe.is_empty() or super._precisa_redesenhar()

func _num(chave: String) -> float:
	return float(_golpe.get(chave, 0.0))

func _physics_process(delta: float) -> void:
	if estado == Estado.MORTO or alvo == null:
		return
	if entrada_t > 0.0:
		super._physics_process(delta)
		return
	_checar_fase()
	if not _golpe.is_empty():
		_tick_golpe(delta)
		return
	if estado == Estado.PERSEGUE and atordoado <= 0.0:
		_pausa -= delta
		if _pausa <= 0.0 and not alvo_morto() and alvo.global_position.distance_to(global_position) <= float(_cfg.get("tecela_alcance_especial", 820.0)):
			_iniciar_proximo()
	super._physics_process(delta)

func _checar_fase() -> void:
	if _fase2 or hp > hp_max * float(_cfg.get("tecela_fase2_hp_pct", 50.0)) / 100.0:
		return
	_fase2 = true
	_pausa = minf(_pausa, 0.8)
	flash()
	Feel.shake(self, 6.0, 0.45)
	tremer_sprite(3.0, 0.6)

func _iniciar_proximo() -> void:
	if _golpes.is_empty():
		return
	for _i in _golpes.size():
		var g: Dictionary = _golpes[_idx]
		_idx = (_idx + 1) % _golpes.size()
		if g["golpe"] == "filhotes" and _vivos_filhotes() >= int(_cfg.get("tecela_filhotes_max", 7.0)):
			continue
		_iniciar(g)
		return
	_pausa = 1.0   # nada a fazer agora (só ninhada na lista e já há filhotes demais)

func _iniciar(g: Dictionary) -> void:
	_golpe = {}
	for k in g:
		_golpe[k] = g[k] if (k == "golpe" or k == "inimigo") else float(g[k])
	_aviso = _num("aviso") * (float(_cfg.get("tecela_fase2_aviso_mult", 1.0)) if _fase2 else 1.0)
	_t = _aviso
	_solto = false
	_efeito_feito = false
	_pontos.clear()
	match _golpe["golpe"]:
		"teia":
			_alvo_pos = alvo.global_position
		"filhotes":
			var n := _qtd_filhotes()
			if pontos_livres.is_valid():
				for p in pontos_livres.call(global_position, _num("raio"), n):
					_pontos.append(p)
			if _pontos.is_empty():
				for i in n:
					_pontos.append(global_position + Vector2.from_angle(TAU * i / n + 0.5) * _num("raio"))
	for i in _pontos.size():   # a ninhada nasce deslocada do jogador (pelo menos ~1 tile): o filhote não esconde o herói
		var d: Vector2 = _pontos[i] - alvo.global_position
		if d.length() < 80.0:
			_pontos[i] = alvo.global_position + (d.normalized() if d.length() > 0.01 else Vector2.RIGHT) * 80.0
	velocity = Vector2.ZERO
	play("idle", true)
	tremer_sprite(2.0, _aviso)
	set_process(true)

func _qtd_filhotes() -> int:
	return int(_num("qtd")) + (int(_cfg.get("tecela_fase2_qtd_extra", 0.0)) if _fase2 else 0)

func _vivos_filhotes() -> int:
	_filhotes = _filhotes.filter(func(f) -> bool: return is_instance_valid(f) and f.estado != Estado.MORTO)
	return _filhotes.size()

func _tick_golpe(delta: float) -> void:
	if not _status.is_empty():
		_tick_status(delta)
		if estado == Estado.MORTO:
			return
	if atordoado > 0.0:   # atordoada (gelo, choque): o golpe se perde
		_golpe = {}
		_pausa = _num("pausa") * 0.5
		return
	var para := alvo.global_position - global_position
	if para.length() > 0.01 and not _solto:
		facing = para.normalized()
	if _kb != Vector2.ZERO:
		_kb = _kb.move_toward(Vector2.ZERO, _kb_decay * delta)
	velocity = _kb
	if _kb != Vector2.ZERO:
		move_and_slide()
	_t -= delta
	if _t > 0.0:
		return
	if not _solto:
		_solto = true
		_t = float(_cfg.get("tecela_recuperacao", 0.75))
		play("attack", true)
		return
	if not _efeito_feito:   # a animação não chegou ao quadro de contato (interrompida): sai agora
		_efeito()
	_pausa = _num("pausa") * (float(_cfg.get("tecela_fase2_pausa_mult", 1.0)) if _fase2 else 1.0)
	_golpe = {}

func _on_frame_changed() -> void:
	super._on_frame_changed()
	if _golpe.is_empty() or not _solto or _efeito_feito or anim_base() != "attack":
		return
	if sprite.frame >= evento("attack"):
		_efeito()

func _efeito() -> void:
	_efeito_feito = true
	var pai := get_parent()
	match _golpe["golpe"]:
		"teia":
			var teia := Efeitos.Teia.new()
			teia.alvo = alvo
			teia.raio = _num("raio")
			teia.duracao = _num("duracao")
			teia.lentidao = _num("lentidao")
			pai.add_child(teia)
			teia.global_position = _alvo_pos
			Feel.particulas(pai, _alvo_pos, Efeitos.COR_TEIA, 14, 120.0, 0.45)
		"badalada":
			var onda := Efeitos.Onda.new()
			onda.alvo = alvo
			onda.raio_max = _num("raio")
			onda.vel = _num("vel")
			onda.dano = float(stats["damage"]) * _num("dano_mult")
			pai.add_child(onda)
			onda.global_position = global_position
			Feel.shake(self, _num("tremor"), 0.4)
			Feel.particulas(pai, global_position + Vector2(0, -60), Efeitos.COR_SINO, 18, 200.0, 0.5)
		"filhotes":
			if convocar.is_valid():
				for f in convocar.call(str(_golpe.get("inimigo", "")), _pontos):
					_filhotes.append(f)
			for p in _pontos:
				Feel.particulas(pai, p, Color(0.7, 0.72, 0.8), 10, 90.0, 0.5)
			Feel.shake(self, _num("tremor"), 0.25)

func _ao_morrer(_e) -> void:
	_golpe = {}
	if float(_cfg.get("tecela_fim_filhotes", 0.0)) < 1.0:
		return
	for f in _filhotes:
		if is_instance_valid(f) and f.estado != Estado.MORTO:
			f.take_damage(1.0e9)   # a teia se desfaz: a ninhada cai junto

# ---------- avisos no chão ----------

func _draw() -> void:
	super._draw()
	if _golpe.is_empty() or estado == Estado.MORTO:
		return
	var p := 1.0 if _solto else clampf(1.0 - _t / maxf(_aviso, 0.01), 0.0, 1.0)
	match _golpe["golpe"]:
		"teia":
			_aviso_teia(p)
		"badalada":
			_aviso_badalada(p)
		"filhotes":
			_aviso_filhotes(p)

func _aviso_teia(p: float) -> void:
	var c := to_local(_alvo_pos)
	var r := _num("raio")
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	draw_line(Vector2(0, -60), c, Color(0.9, 0.97, 1.0, 0.25 + 0.5 * p), 1.0)   # o fio que ela lança até o ponto
	draw_set_transform(c, 0.0, Vector2(1.0, Efeitos.ACHATA))
	draw_circle(Vector2.ZERO, r, Color(Efeitos.COR_TEIA.r, Efeitos.COR_TEIA.g, Efeitos.COR_TEIA.b, 0.2 + 0.18 * p))
	draw_circle(Vector2.ZERO, r * p, Color(Efeitos.COR_TEIA.r, Efeitos.COR_TEIA.g, Efeitos.COR_TEIA.b, 0.4))
	draw_arc(Vector2.ZERO, r, 0.0, TAU, 48, Color(1.0, 1.0, 1.0, 0.8 + 0.2 * p), 2.0)   # borda branca
	for i in 6:
		draw_line(Vector2.ZERO, Vector2.from_angle(TAU * i / 6.0 + 0.2) * r * p, Color(0.9, 0.97, 1.0, 0.6), 1.0)

func _aviso_badalada(p: float) -> void:
	var r := _num("raio")
	draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, Efeitos.ACHATA))
	draw_arc(Vector2.ZERO, r, 0.0, TAU, 72, Color(1.0, 0.72, 0.3, 0.45 + 0.5 * p), 4.0)   # até onde a onda vai
	draw_arc(Vector2.ZERO, r - 8.0, 0.0, TAU, 72, Color(1.0, 0.72, 0.3, 0.18 + 0.2 * p), 10.0)
	for k in 3:   # anéis que se fecham sobre o sino: o som sendo puxado antes da batida
		var f := fposmod(p * 2.0 + k / 3.0, 1.0)
		draw_arc(Vector2.ZERO, r * 0.45 * (1.0 - f) + 30.0, 0.0, TAU, 40, Color(1.0, 0.78, 0.4, 0.75 * f * (0.4 + 0.6 * p)), 3.0)
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	draw_circle(Vector2(0, -62), 16.0 + 16.0 * p, Color(1.0, 0.72, 0.3, 0.12 + 0.28 * p))   # brilho âmbar no sino que ela carrega

func _aviso_filhotes(p: float) -> void:
	for pt in _pontos:
		var c := to_local(pt)
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
		draw_line(Vector2(0, -50), c, Color(1.0, 0.72, 0.3, 0.2 + 0.35 * p), 1.0)
		draw_set_transform(c, 0.0, Vector2(1.0, Efeitos.ACHATA))   # círculo de convocação: 4 anéis que se fecham no ponto, na cor do aviso da badalada
		draw_circle(Vector2.ZERO, 34.0, Color(0.05, 0.04, 0.05, 0.35 + 0.2 * p))
		for k in 4:
			var f := fposmod(p * 2.0 + k / 4.0, 1.0)
			draw_arc(Vector2.ZERO, 12.0 + 26.0 * (1.0 - f), 0.0, TAU, 28, Color(1.0, 0.72, 0.3, 0.35 + 0.65 * f), 2.0)
		draw_arc(Vector2.ZERO, 38.0, 0.0, TAU, 28, Color(1.0, 0.78, 0.4, 0.5 + 0.5 * p), 3.0)
