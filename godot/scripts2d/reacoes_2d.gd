extends RefCounted
## Reações elementais: quando um elemento atinge um inimigo que já está sob outro, os dois se combinam numa reação
## com mecânica e visual próprios. Números em data2d/reacoes_elementais.csv (`dano` multiplicador do dano da flecha
## do jogador quando houver, senão base 10; `valor` = alvos extras ou fração). Chamado por enemy_2d.aplicar_status.
##   vapor            queimadura em alvo com frio   -> nuvem de vapor: dano em área, apaga o frio
##   choque_termico   frio em alvo queimando        -> rachadura: dano em área, apaga a queimadura
##   gas_inflamado    queimadura em alvo envenenado -> explosão de gás: dano proporcional ao veneno, consome o veneno
##   quebra_gelida    choque em alvo congelado      -> estilhaça o gelo: dano grande em área, descongela
##   corrente_toxica  choque em alvo envenenado     -> o veneno pula por arcos para os vizinhos
## Cada inimigo tem recarga de reação (meta `reacao_ate`) para uma reação não disparar a outra em cadeia infinita.

const Csv = preload("res://scripts2d/csv2d.gd")
const Alvos = preload("res://scripts2d/alvos_2d.gd")
const Efeito = preload("res://scripts2d/efeito_2d.gd")
const U = preload("res://scripts2d/efeitos_extra_util_2d.gd")
const Feel = preload("res://scripts2d/feel_2d.gd")
const BASE_DANO := 10.0

static var _defs := {}
static var _por_gatilho := {}

static func carregar() -> void:
	if not _defs.is_empty():
		return
	for r in Csv.rows("res://data2d/reacoes_elementais.csv"):
		var d := {"id": r["id"], "gatilho": r["gatilho"], "exige": r["exige"], "recarga": float(r["recarga"])}
		for k in ["dano", "raio", "valor"]:
			d[k] = float(r[k])
		var c: PackedStringArray = str(r["cor"]).split("/")
		d["cor"] = Color(float(c[0]), float(c[1]), float(c[2]))
		_defs[d["id"]] = d
		if not _por_gatilho.has(d["gatilho"]):
			_por_gatilho[d["gatilho"]] = []
		_por_gatilho[d["gatilho"]].append(d)

static func defs() -> Dictionary:
	carregar()
	return _defs

## O inimigo `e` está sob o estado `exige` (veneno, queimadura, frio, congelado)?
static func sob(e: Node, exige: String) -> bool:
	match exige:
		"frio":
			return int(e.get_meta("frio_acumulos", 0)) > 0 and e.has_method("tem_status") and e.tem_status("lentidao")
		"congelado":
			return e.has_meta("congelado_ate") and Time.get_ticks_msec() < int(e.get_meta("congelado_ate"))
		_:
			return e.has_method("tem_status") and e.tem_status(exige)

## Chamar ANTES de gravar o novo status. Devolve o id da reação disparada ("" = nenhuma).
## `gatilho`: queimadura, choque ou frio (lentidão vinda dos acúmulos de frio do Arqueiro).
static func tentar(alvo: Node2D, gatilho: String) -> String:
	carregar()
	if not _por_gatilho.has(gatilho) or not alvo.is_inside_tree():
		return ""
	var agora := Time.get_ticks_msec()
	if agora < int(alvo.get_meta("reacao_ate", 0)):
		return ""
	for d in _por_gatilho[gatilho]:
		if sob(alvo, d["exige"]):
			alvo.set_meta("reacao_ate", agora + int(d["recarga"] * 1000.0))
			_disparar(d, alvo)
			return d["id"]
	return ""

static func _dano_base(alvo: Node2D) -> float:
	var jog = alvo.get("alvo")
	if jog != null and is_instance_valid(jog) and jog.get("stats") != null and jog.stats.has("arrow_damage"):
		return float(jog.stats["arrow_damage"])
	return BASE_DANO

static func _disparar(d: Dictionary, alvo: Node2D) -> void:
	var pai := alvo.get_parent()
	var pos := alvo.global_position
	var dano: float = _dano_base(alvo) * float(d["dano"]) / 10.0
	var vizinhos: Array = U.no_raio(alvo, pos, d["raio"])
	match d["id"]:
		"vapor":
			alvo.set_meta("frio_acumulos", 0)
			alvo._status.erase("lentidao")
			alvo._recalcular_status()
			for n in vizinhos:
				n.take_damage(dano, pos)
			Marca.criar(pai, pos, "vapor", d)
		"choque_termico":
			_limpar_queimadura(alvo)
			for n in vizinhos:
				n.take_damage(dano, pos)
			Marca.criar(pai, pos, "rachadura", d)
		"gas_inflamado":
			var dps: float = alvo._status["veneno"]["v"] if alvo._status.has("veneno") else 3.0
			alvo._status.erase("veneno")
			alvo._recalcular_status()
			for n in vizinhos:
				n.take_damage(dano + dps * 4.0, pos)
			Marca.criar(pai, pos, "gas", d)
		"quebra_gelida":
			alvo.remove_meta("congelado_ate")
			alvo._status.erase("atordoamento")
			alvo.atordoado = 0.0
			alvo.set_meta("frio_acumulos", 0)
			for n in vizinhos:
				n.take_damage(dano, pos)
				if n != alvo and n.has_method("aplicar_status"):
					n.aplicar_status("lentidao", 1.5, 0.35)
			Marca.criar(pai, pos, "estilhaco", d)
		"corrente_toxica":
			var dps2: float = alvo._status["veneno"]["v"] if alvo._status.has("veneno") else 3.0
			var dur2: float = alvo._status["veneno"]["t"] if alvo._status.has("veneno") else 3.0
			vizinhos = vizinhos.filter(func(n): return n != alvo)
			vizinhos.sort_custom(func(a: Node2D, b: Node2D): return a.global_position.distance_squared_to(pos) < b.global_position.distance_squared_to(pos))
			var pts: Array = []
			for n in vizinhos.slice(0, int(d["valor"])):
				n.aplicar_status("veneno", maxf(dur2, 2.0), dps2)
				n.take_damage(dano, pos)
				pts.append(n.global_position)
			Marca.criar(pai, pos, "corrente", d, pts)
	Feel.numero(alvo, dano, d["cor"], false, true)

static func _limpar_queimadura(alvo: Node2D) -> void:
	alvo._status.erase("queimadura")
	if alvo.has_node("OverlayQueimadura"):
		alvo.get_node("OverlayQueimadura").queue_free()
	alvo._recalcular_status()

## Visual curto de cada reação (só `_draw`, sem sprite): cada uma tem silhueta própria.
class Marca extends Node2D:
	var forma := ""
	var cor := Color.WHITE
	var raio := 100.0
	var pts: Array = []
	var _t := 0.0
	const DUR := 0.55

	static func criar(pai: Node, pos: Vector2, forma_: String, d: Dictionary, pts_: Array = []) -> void:
		if pai == null:
			return
		var m := Marca.new()
		m.forma = forma_
		m.cor = d["cor"]
		m.raio = d["raio"]
		m.pts = pts_
		m.global_position = pos
		m.z_index = 5
		pai.add_child(m)

	func _process(delta: float) -> void:
		_t += delta
		if _t >= DUR:
			queue_free()
		queue_redraw()

	func _draw() -> void:
		var k := clampf(_t / DUR, 0.0, 1.0)
		var a := 1.0 - k
		var r := raio * (0.25 + 0.75 * sqrt(k))
		match forma:
			"vapor":   # nuvens brancas que sobem
				for i in 7:
					var ang := TAU * float(i) / 7.0
					var c := Vector2.from_angle(ang) * r * 0.55 + Vector2(0, -50.0 * k)
					draw_circle(c, 16.0 + 10.0 * k, Color(cor.r, cor.g, cor.b, 0.5 * a))
				U.elipse(self, Vector2.ZERO, r, Color(0.7, 0.85, 1.0, 0.25 * a))
			"rachadura":   # fendas vermelhas e azuis saindo do centro
				for i in 8:
					var ang := TAU * float(i) / 8.0 + 0.2
					var f := Vector2.from_angle(ang)
					var meio := f * r * 0.5 + f.orthogonal() * U.ruido(float(i), 2.0) * 10.0
					var cc := cor if i % 2 == 0 else Color(0.5, 0.8, 1.0)
					draw_polyline(PackedVector2Array([Vector2.ZERO, meio, f * r]), Color(cc.r, cc.g, cc.b, a), 3.0)
				draw_arc(Vector2.ZERO, r, 0, TAU, 32, Color(1, 0.9, 0.7, 0.6 * a), 2.0)
			"gas":   # bola de fogo verde e laranja
				draw_circle(Vector2.ZERO, r * 0.9, Color(0.4, 0.85, 0.2, 0.35 * a))
				draw_circle(Vector2.ZERO, r * 0.65, Color(1.0, 0.55, 0.1, 0.55 * a))
				draw_circle(Vector2.ZERO, r * 0.35, Color(1.0, 0.95, 0.6, 0.85 * a))
				draw_arc(Vector2.ZERO, r, 0, TAU, 36, Color(0.7, 1.0, 0.3, a), 3.0)
			"estilhaco":   # cristais voando para fora
				for i in 10:
					var ang := TAU * float(i) / 10.0 + 0.3
					U.cristal(self, Vector2.from_angle(ang) * r * 0.3, ang, 10.0 + 26.0 * (1.0 - k) , 4.0, a)
				draw_arc(Vector2.ZERO, r, 0, TAU, 36, Color(0.8, 0.97, 1.0, 0.8 * a), 2.0)
			"corrente":   # arcos verdes e amarelos até os vizinhos
				for i in pts.size():
					U.raio_zz(self, Vector2.ZERO, pts[i] - global_position, Color(0.75, 1.0, 0.3), 2.5, float(i) + _t * 20.0, a)
				draw_circle(Vector2.ZERO, 14.0 * a + 4.0, Color(0.75, 1.0, 0.3, 0.7 * a))
