extends "res://scripts2d/player_2d.gd"
## Mago 2D: o ataque básico é o orbe arcano (ou o Eco escolhido na corrida: Centelha, Bolha, Lascas ou Brasa,
## em efeitos_mago_afinidade_2d.gd) e as habilidades vêm do runtime de habilidades (data2d/habilidades_mago.csv +
## efeitos_mago_2d.gd). Mana, Barreira de Gelo e Surto de Mana ficam aqui. Números em data2d/mago.csv.

const Efeitos = preload("res://scripts2d/efeitos_mago_2d.gd")
const Basico = preload("res://scripts2d/efeitos_mago_afinidade_2d.gd")
const FxMago = preload("res://scripts2d/fx_mago_2d.gd")
const Orbe = preload("res://scripts2d/orbe_2d.gd")
const Espiritos = preload("res://scripts2d/espiritos_mago_2d.gd")
const ExtraU = preload("res://scripts2d/efeitos_extra_util_2d.gd")

const CRISTAIS := 7
var escudo := 0.0        # dano que a Barreira de Gelo ainda absorve
var escudo_t := 0.0
var _frente: Node2D
var escudo_def := {}     # linha da Barreira que criou o escudo (estilhaços ao quebrar)
var surto_t := 0.0       # Surto de Mana: tempo restante
var surto_mult := 0.0    # regeneração extra (x) enquanto dura
var _cast_t := 0.0
var _dano_base := 1.0    # arrow_damage de mago.csv: as cartas de dano escalam as magias na mesma proporção
var _t_fx := 0.0
var nivel_corrida := 1   # nível da corrida (a corrida atualiza): quantos espíritos giram em volta e quanto ricocheteiam
var espiritos: Node2D

func _init() -> void:
	stats_csv = "res://data2d/mago.csv"
	sprite_id = "mago"
	classe = "mago"

func _ready() -> void:
	_dano_base = maxf(float(Csv.kv(stats_csv)["arrow_damage"]), 0.001)
	super._ready()
	add_to_group("mago")
	espiritos = Espiritos.new()
	add_child(espiritos)

func reset() -> void:
	super.reset()
	mana = stats["mana_max"]
	escudo = 0.0
	escudo_t = 0.0
	surto_t = 0.0
	_cast_t = 0.0
	mana_changed.emit(mana, stats["mana_max"])

func _physics_process(delta: float) -> void:
	surto_t = maxf(0.0, surto_t - delta)
	_cast_t = maxf(0.0, _cast_t - delta)
	_t_fx += delta
	if escudo_t > 0.0:
		escudo_t -= delta
		if escudo_t <= 0.0:
			_quebrar_escudo()
	if escudo > 0.0 or surto_t > 0.0:
		queue_redraw()
	super._physics_process(delta)

# ---- poder das magias --------------------------------------------------------------------

## Multiplicador de dano das magias: `spell_power` vezes o quanto as cartas e o meta já subiram o dano do básico.
func poder() -> float:
	return float(stats.get("spell_power", 1.0)) * float(stats["arrow_damage"]) / _dano_base

## Dano de um golpe básico (com crítico).
func dano_basico() -> float:
	var d: float = stats["arrow_damage"]
	if float(stats.get("crit_chance", 0.0)) > 0.0 and _rng.randf() < float(stats["crit_chance"]):
		d *= float(stats.get("crit_mult", 2.0))
	return d

## Ponta do cajado (mundo, já na altura do desenho) para a direção `dir`: de onde saem raios e clarões.
func ponta_do_cajado(dir: Vector2) -> Vector2:
	return global_position + dir * float(stats["arrow_spawn_dist"]) + Vector2(0, -44)

# ---- mana e escudo (usados pelo runtime de habilidades e pelos efeitos) -------------------

func mana_frac() -> float:
	return clampf(mana / stats["mana_max"], 0.0, 1.0)

## Surto de Mana multiplica a regeneração enquanto dura.
func taxa_regen_mana() -> float:
	return stats["mana_regen"] * (1.0 + surto_mult if surto_t > 0.0 else 1.0)

func dar_escudo(valor: float, dur: float, def := {}) -> void:
	escudo = maxf(escudo, valor)
	escudo_t = maxf(escudo_t, dur)
	escudo_def = def
	queue_redraw()

## A Barreira acabou (quebrada ou no tempo): estilhaça em volta, ferindo e gelando quem está perto.
func _quebrar_escudo() -> void:
	escudo = 0.0
	escudo_t = 0.0
	queue_redraw()
	if not escudo_def.is_empty() and is_inside_tree():
		Efeitos.estilhacar_barreira(self, escudo_def)
	escudo_def = {}

## Direção atual da mira (vetor unitário), para o runtime passar a `executar`.
func direcao_mira() -> Vector2:
	return _aim

## Toca a animação de conjuração sem travar o movimento.
func animar_conjuracao() -> void:
	facing = _aim
	_cast_t = float(stats.get("cast_time", 0.3))
	play("attack", true)

## Atalho para testes e para o runtime: executa um efeito do CSV de habilidades.
func lancar_efeito(efeito: String, def: Dictionary, nivel := 1) -> bool:
	var ok := Efeitos.executar(efeito, self, def, nivel, _aim)
	if ok:
		animar_conjuracao()
		espiritos.rajada()
	return ok

## Ícone do ataque na HUD: o Eco escolhido ou o orbe arcano.
func slots_hud() -> Array:
	return [{"icone": afinidade if afinidade != "" else "skill.mage.basic", "recarga": recarga_tiro()}]

# ---- ataque básico, dano e desenho -------------------------------------------------------

func _soltar_flecha() -> void:
	var n := int(stats["arrow_count"])
	for i in n:
		Basico.disparar(self, _aim.rotated(deg_to_rad(stats["multishot_spread"]) * (i - (n - 1) * 0.5)))
	FxMago.impacto(get_parent(), ponta_do_cajado(_aim), Basico.Afinidades.elemento(afinidade), 0.5)   # clarão na ponta do cajado
	Audio.tocar("shoot")
	var c := Feel.cfg()
	velocity -= _aim * c["player_recoil"]
	Feel.shake(self, c["shake_shot_amp"], c["shake_shot_time"])

func _animar(entrada: Vector2) -> void:
	if _cast_t > 0.0 and estado == Estado.LIVRE:
		facing = _aim
		return
	super._animar(entrada)

func take_damage(amount: float, origem := Vector2.ZERO) -> void:
	if estado == Estado.MORTO or invencivel > 0.0 or god_mode:
		return
	if escudo > 0.0:
		var absorve := minf(escudo, amount)
		_estilhacos(origem)
		escudo -= absorve
		amount -= absorve
		if escudo <= 0.0:
			_quebrar_escudo()
		queue_redraw()
		if amount <= 0.0:
			invencivel = stats["hit_iframes"] * 0.5
			return
	super.take_damage(amount, origem)

func _draw() -> void:
	super._draw()
	if escudo > 0.0:   # Barreira de Gelo: anel de geada no chão e os cristais de trás (os da frente ficam na _Frente)
		ExtraU.elipse_arco(self, Vector2.ZERO, 40.0, Color(0.7, 0.92, 1.0, 0.7), 2.5)
		_cristais(self, false)
	if _frente == null:
		_frente = _Frente.new()
		_frente.z_index = 1
		add_child(_frente)
	_frente.queue_redraw()
	if surto_t > 0.0:   # Surto de Mana: faíscas arcanas sobem do chão
		var pal: Array = FxMago.paleta("")
		for i in 6:
			var u := fmod(_t_fx * 0.9 + float(i) / 6.0, 1.0)
			var a := TAU * float(i) / 6.0 + _t_fx
			var p := ((Vector2(cos(a) * 26.0, sin(a) * 13.0 - 70.0 * u)) / 2.5).round() * 2.5
			draw_rect(Rect2(p, Vector2(5, 5) if u < 0.5 else Vector2(2.5, 2.5)), Color(pal[3] if i % 2 == 0 else pal[2], 1.0 - u))

## Três cristais giram em volta do mago; `na_frente` escolhe a metade da órbita que passa diante do corpo.
func _cristais(ci: CanvasItem, na_frente: bool) -> void:
	for i in CRISTAIS:
		var a := _t_fx * 1.0 + TAU * float(i) / float(CRISTAIS)
		if (sin(a) > 0.0) != na_frente:
			continue
		var p := Vector2(cos(a) * 40.0, sin(a) * 20.0 - 44.0)
		ExtraU.cristal(ci, p, -PI / 2.0, 52.0, 12.0, 0.95 if na_frente else 0.7)

## Camada desenhada por cima do sprite do mago (cristais da Barreira que passam pela frente).
class _Frente extends Node2D:
	func _draw() -> void:
		var m = get_parent()
		if m.escudo > 0.0:
			m._cristais(self, true)

## Ao bloquear um golpe, a Barreira solta 3 a 4 estilhaços de gelo (lascas em pixel) para os lados.
func _estilhacos(origem: Vector2) -> void:
	if not is_inside_tree():
		return
	var base := (origem - global_position).angle() if origem != Vector2.ZERO else randf() * TAU
	var dano_e := float(escudo_def.get("dano_final", 0.0)) * 0.3
	for i in 4:
		var l := Orbe.new()
		l.setup(global_position, Vector2.from_angle(base + (float(i) - 1.5) * 0.7), 420.0, dano_e, 150.0)
		l.elemento = "gelo"
		l.forma = "lasca"
		l.tamanho = 7.0
		get_parent().add_child(l)
