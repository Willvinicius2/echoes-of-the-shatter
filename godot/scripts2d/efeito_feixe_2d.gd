extends RefCounted
## Feixe contínuo que VARRE um arco à frente do herói (forma genérica, reutilizável por Arqueiro, Guerreiro e Mago).
## Pixel art de 3 tons com borda dura (sem alfa suave): casca escura, miolo da cor do elemento e fio de luz no centro.
## Uso: Feixe.lancar(jogador, dir, {cor: [escuro, meio, luz], comp, larg, arco, dur, tick, dano, ao_acertar: Callable(inimigo)}).

const U = preload("res://scripts2d/efeitos_extra_util_2d.gd")
const Vfx = preload("res://scripts2d/vfx_2d.gd")
const Alvos = preload("res://scripts2d/alvos_2d.gd")

const ALT := 26.0   # altura da boca do arco, em px de mundo

static func lancar(jogador: Node2D, dir: Vector2, op: Dictionary) -> Node2D:
	var f := Feixe.new()
	f.dir = dir.normalized() if dir != Vector2.ZERO else Vector2.RIGHT
	f.op = op
	f.jogador = jogador
	jogador.add_child(f)
	return f

class Feixe extends Node2D:
	var dir := Vector2.RIGHT
	var op: Dictionary = {}
	var jogador: Node2D
	var _t := 0.0
	var _tick_t := 0.0
	var _dur := 1.4
	var _arco := 1.2
	var _comp := 360.0
	var _larg := 22.0
	var _cor: Array = [Color(0.1, 0.25, 0.5), Color(0.45, 0.8, 1.0), Color(0.95, 1.0, 1.0)]
	var _fim := Vector2.ZERO

	func _ready() -> void:
		z_index = 4
		Vfx.registrar_animado(self)
		_dur = maxf(op.get("dur", 1.4), 0.2)
		_arco = op.get("arco", 1.2)
		_comp = op.get("comp", 360.0)
		_larg = op.get("larg", 22.0)
		_cor = op.get("cor", _cor)
		position = Vector2(0, -ALT)

	func _ang() -> float:
		var u := clampf(_t / _dur, 0.0, 1.0)
		var e := u * u * (3.0 - 2.0 * u)   # acelera e freia, a varredura "pesa"
		return dir.angle() + (e - 0.5) * _arco

	func _physics_process(delta: float) -> void:
		_t += delta
		if _t >= _dur or not is_instance_valid(jogador):
			queue_free()
			return
		_tick_t -= delta
		if _tick_t > 0.0:
			return
		_tick_t = op.get("tick", 0.12)
		var a := _ang()
		var ini := global_position
		var fim := ini + Vector2.from_angle(a) * _comp
		var dano: float = op.get("dano", 1.0)
		for e in Alvos.em_segmento(get_tree(), ini, fim, _larg):
			e.take_damage(dano, ini)
			if is_instance_valid(e) and op.has("ao_acertar"):
				op["ao_acertar"].call(e)

	func _process(_delta: float) -> void:
		queue_redraw()

	func _draw() -> void:
		var a := _ang()
		var d := Vector2.from_angle(a)
		var o := d.orthogonal()
		var vida := 1.0 - clampf((_t - (_dur - 0.15)) / 0.15, 0.0, 1.0)   # fecha o feixe no fim
		var cresce := clampf(_t / 0.12, 0.0, 1.0)
		var comp := _comp * cresce
		_fim = d * comp
		# 1) rastro da varredura: três leques de chão que ficam para trás (resíduo), do mais velho ao mais novo
		for k in 3:
			var ak := a - float(k + 1) * 0.09 * signf(_arco) * (1.0 if _t < _dur else 0.0)
			var dk := Vector2.from_angle(ak)
			draw_line(Vector2.ZERO, dk * comp * (0.9 - 0.12 * k), Color(_cor[0], 0.35 - 0.1 * k), _larg * 0.5, false)
		# 2) corpo em degraus (borda dura): casca, miolo, fio de luz; larga na ponta, fina na boca
		for faixa in 3:
			var esc: float = [1.0, 0.62, 0.22][faixa]
			var larg: float = _larg * esc * vida
			var pts := PackedVector2Array([
				o * larg * 0.18, d * comp + o * larg * 0.5, d * comp - o * larg * 0.5, -o * larg * 0.18])
			draw_colored_polygon(pts, _cor[faixa])
		# 3) dentes de energia na casca, estalam a cada fração de segundo (animação de 3 tempos: preparo, corpo, resíduo)
		var passo := floori(_t * 18.0)
		for i in 7:
			var u := (float(i) + 0.5) / 7.0
			var lado := 1.0 if (i + passo) % 2 == 0 else -1.0
			var p := d * comp * u + o * lado * _larg * 0.5 * u * vida
			draw_rect(Rect2(p - Vector2(2, 2), Vector2(4, 4)), _cor[2])
		# 4) ponta no chão: faíscas em quadrados duros
		for i in 5:
			var ang := float(i) * 1.26 + float(passo)
			var q := _fim + Vector2.from_angle(ang) * (8.0 + 7.0 * U.ruido(float(i), float(passo)))
			draw_rect(Rect2(q - Vector2(2, 2), Vector2(4, 4)), _cor[1])
		draw_rect(Rect2(_fim - Vector2(5, 5), Vector2(10, 10)), _cor[2])
