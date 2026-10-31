extends "res://scripts2d/player_2d.gd"
## Mago 2D: ataque básico é o orbe arcano; as habilidades vêm do runtime de habilidades
## (data2d/habilidades_mago.csv + efeitos_mago_2d.gd). Mana, escudo de gelo e surto de mana ficam aqui.
## Números em data2d/mago.csv.

signal mana_changed(mana: float, mana_max: float)

const OrbeScript = preload("res://scripts2d/orbe_2d.gd")
const Efeitos = preload("res://scripts2d/efeitos_mago_2d.gd")

const COR_ORBE := Color(0.72, 0.45, 1.0)

var mana := 0.0
var escudo := 0.0        # dano que a Barreira de Gelo ainda absorve
var escudo_t := 0.0
var surto_t := 0.0       # Surto de Mana: tempo restante
var surto_mult := 0.0    # regeneração extra (x) enquanto dura
var _cast_t := 0.0

func _init() -> void:
	stats_csv = "res://data2d/mago.csv"
	sprite_id = "mago"

func _ready() -> void:
	super._ready()
	add_to_group("mago")

func reset() -> void:
	super.reset()
	mana = stats["mana_max"]
	escudo = 0.0
	escudo_t = 0.0
	surto_t = 0.0
	_cast_t = 0.0
	mana_changed.emit(mana, stats["mana_max"])

func _physics_process(delta: float) -> void:
	if estado != Estado.MORTO:
		var regen: float = stats["mana_regen"] * (1.0 + surto_mult if surto_t > 0.0 else 1.0)
		ganhar_mana(regen * delta)
	surto_t = maxf(0.0, surto_t - delta)
	_cast_t = maxf(0.0, _cast_t - delta)
	if escudo_t > 0.0:
		escudo_t -= delta
		if escudo_t <= 0.0:
			escudo = 0.0
		queue_redraw()
	super._physics_process(delta)

# ---- mana e escudo (usados pelo runtime de habilidades e pelos efeitos) -------------------

func mana_frac() -> float:
	return clampf(mana / stats["mana_max"], 0.0, 1.0)

func gastar_mana(custo: float) -> bool:
	if mana + 0.0001 < custo:
		return false
	mana -= custo
	mana_changed.emit(mana, stats["mana_max"])
	return true

func ganhar_mana(qtd: float) -> void:
	var antes := mana
	mana = minf(stats["mana_max"], mana + qtd)
	if absf(mana - antes) > 0.0001:
		mana_changed.emit(mana, stats["mana_max"])

func dar_escudo(valor: float, dur: float) -> void:
	escudo = maxf(escudo, valor)
	escudo_t = maxf(escudo_t, dur)
	queue_redraw()

## Direção atual da mira (vetor unitário), para o runtime passar a `executar`.
func direcao_mira() -> Vector2:
	return _aim

## Ponto no chão mirado pelo cursor (ou analógico), limitado a `alcance` a partir do mago.
func ponto_mira(alcance: float) -> Vector2:
	var alvo := global_position + _aim * alcance
	if auto_aim == Vector2.ZERO and Input.get_vector("aim_left", "aim_right", "aim_up", "aim_down").length() <= 0.3:
		alvo = get_global_mouse_position()
	var v := alvo - global_position
	return global_position + v.limit_length(alcance)

## Toca a animação de conjuração sem travar o movimento.
func animar_conjuracao() -> void:
	facing = _aim
	_cast_t = 0.3
	play("attack", true)

## Atalho para testes e para o runtime: executa um efeito do CSV de habilidades.
func lancar_efeito(efeito: String, def: Dictionary, nivel := 1) -> bool:
	var ok := Efeitos.executar(efeito, self, def, nivel, _aim)
	if ok:
		animar_conjuracao()
	return ok

# ---- ataque básico, dano e desenho -------------------------------------------------------

func _soltar_flecha() -> void:
	var n := int(stats["arrow_count"])
	for i in n:
		var dir := _aim.rotated(deg_to_rad(stats["multishot_spread"]) * (i - (n - 1) * 0.5))
		var o := OrbeScript.new()
		o.setup(global_position + dir * stats["arrow_spawn_dist"], dir, stats["arrow_speed"],
			stats["arrow_damage"], stats["arrow_range"])
		o.cor = COR_ORBE
		o.tamanho = stats["bolt_radius"]
		o.pierce = int(stats["arrow_pierce"])
		get_parent().add_child(o)
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
		escudo -= absorve
		amount -= absorve
		queue_redraw()
		if amount <= 0.0:
			invencivel = stats["hit_iframes"] * 0.5
			return
	super.take_damage(amount, origem)

func _draw() -> void:
	super._draw()
	if escudo > 0.0:
		draw_set_transform(Vector2(0, -40), 0.0, Vector2(1.0, 1.0))
		draw_circle(Vector2.ZERO, 44.0, Color(0.45, 0.85, 1.0, 0.16))
		draw_arc(Vector2.ZERO, 44.0, 0.0, TAU, 40, Color(0.7, 0.95, 1.0, 0.8), 3.0)
