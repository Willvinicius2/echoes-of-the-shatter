extends RefCounted
## Reações elementais: quando um elemento atinge um inimigo que já está sob outro, os dois se combinam numa reação
## com mecânica e visual próprios. Números em data2d/reacoes_elementais.csv (`dano` multiplicador do dano da flecha
## do jogador quando houver, senão base 10; `valor` = alvos extras ou fração). Chamado por enemy_2d.aplicar_status.
##   vapor            queimadura em alvo com frio   -> nuvem de vapor: dano em área, apaga o frio
##   choque_termico   frio em alvo queimando        -> rachadura: dano em área, apaga a queimadura
##   gas_inflamado    queimadura em alvo envenenado -> explosão de gás: dano proporcional ao veneno, consome o veneno
##   quebra_gelida    choque em alvo congelado      -> estilhaça o gelo: dano grande em área, descongela
##   corrente_toxica  choque em alvo envenenado     -> o veneno pula por arcos para os vizinhos
##   conducao_agua    choque em alvo na margem d'água -> a corrente corre pela água e choca vizinhos que também estão nela
##   apagar_fogo      queimadura em alvo na água     -> a água apaga a chama (o status não pega), só sobe vapor
## Resistências por inimigo (data2d/resistencias_elementais.csv): multiplicador do valor e da duração do status do elemento;
## 0 = imune. Ver `mult()`.
## Cada inimigo tem recarga de reação (meta `reacao_ate`) para uma reação não disparar a outra em cadeia infinita.

const Csv = preload("res://scripts2d/csv2d.gd")
const Alvos = preload("res://scripts2d/alvos_2d.gd")
const Efeito = preload("res://scripts2d/efeito_2d.gd")
const U = preload("res://scripts2d/efeitos_extra_util_2d.gd")
const Feel = preload("res://scripts2d/feel_2d.gd")
const BASE_DANO := 10.0

const DIST_AGUA := 70.0   # px da margem do riacho que contam como "na água"
const ELEMENTO := {"veneno": "veneno", "queimadura": "fogo", "choque": "raio", "lentidao": "gelo"}
static var _defs := {}
static var _resist := {}
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

## Multiplicador de resistência do inimigo `id` ao elemento do status `tipo` (1 = neutro, 0 = imune).
static func mult(id: String, tipo: String) -> float:
	if _resist.is_empty():
		for r in Csv.rows("res://data2d/resistencias_elementais.csv"):
			_resist[r["id"]] = r
	var el: String = ELEMENTO.get(tipo, "")
	if el == "" or not _resist.has(id):
		return 1.0
	return float(_resist[id][el])

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
		"agua":
			for sala in e.get_tree().get_nodes_in_group("sala_2d"):
				if sala.has_method("perto_agua") and sala.perto_agua(e.global_position, DIST_AGUA):
					return true
			return false
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
		"conducao_agua":
			var alcance: Array = []
			for n in vizinhos:
				if n != alvo and _perto_agua(n):
					alcance.append(n)
			alcance.sort_custom(func(a: Node2D, b: Node2D): return a.global_position.distance_squared_to(pos) < b.global_position.distance_squared_to(pos))
			var pts_a: Array = []
			alvo.take_damage(dano, pos)
			for n in alcance.slice(0, int(d["valor"])):
				n.aplicar_status("choque", 2.0, 0.15)
				n.take_damage(dano, pos)
				pts_a.append(n.global_position)
			Marca.criar(pai, pos, "conducao", d, pts_a)
		"apagar_fogo":
			Marca.criar(pai, pos, "vapor", d)
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
	if dano >= 1.0:
		Feel.numero(alvo, dano, d["cor"], false, true)

static func _perto_agua(n: Node2D) -> bool:
	return sob(n, "agua")

static func _limpar_queimadura(alvo: Node2D) -> void:
	alvo._status.erase("queimadura")
	if alvo.has_node("OverlayQueimadura"):
		alvo.get_node("OverlayQueimadura").queue_free()
	alvo._recalcular_status()

## Elementos que o inimigo `id` resiste (mult <= 0.6), é imune (0) ou sofre mais (>= 1.3): [{el, m}], na ordem do CSV.
## Alimenta os ícones junto da barra de vida (dica de quem não fica a perder tempo com o elemento errado).
static func dicas(id: String) -> Array:
	mult(id, "veneno")   # garante o CSV carregado
	var out: Array = []
	if not _resist.has(id):
		return out
	for el in ["fogo", "gelo", "raio", "veneno"]:
		var m := float(_resist[id][el])
		if m <= 0.6 or m >= 1.3:
			out.append({"el": el, "m": m})
	return out

const COR_EL := {"fogo": Color(1.0, 0.55, 0.15), "gelo": Color(0.55, 0.9, 1.0), "raio": Color(1.0, 0.95, 0.35), "veneno": Color(0.55, 0.95, 0.3)}
const DICA_LADO := 16   # ícone de resistência em px de tela: 1 px de arte = 1 px de tela, contorno preto de 1 px
const DICA_ESC := 1.5   # ícone desenhado a 1,5x em jogo (o mundo é mostrado a menos de 1 px por px): ~16 px legíveis em 1280x720
const DICA_PASSO := 26  # distância entre ícones vizinhos junto da barra de vida
## Silhuetas 12x12 (a = corpo, b = realce); o contorno preto de 1 px e a insígnia são gerados em `_icone`.
const FORMAS := {
	"fogo": ["......a.....", ".....aa.....", "....aaa..a..", "...aaaaa.aa.", "...aabaaaaa.", "..aaabbaaaaa", "..aabbbbaaaa", "..aabbbbbaaa", "..aaabbbbaaa", "...aaabbaaa.", "....aaaaaa..", ".....aaaa..."],
	"gelo": ["......aa....", "......ab....", ".....aabb...", "..a..abbb.a.", "..aa.abbb.aa", "...aaabbbaa.", "aaaabbbbbbaa", "...aaabbbaa.", "..aa.abbb.aa", "..a..abbb.a.", ".....aabb...", "......ab...."],
	"raio": ["......aaaa..", ".....aabba..", "....aabba...", "...aabba....", "..aabbbbaa..", "..aaaabbaa..", ".....abba...", "....aabba...", "...aabba....", "...abba.....", "..aaba......", "..aa........"],
	"veneno": ["......aa....", "......aa....", ".....aaaa...", ".....abaa...", "....aabaaa..", "....abaaaa..", "...aabaaaaa.", "...aaaaaaaa.", "...aaaaaaaa.", "....aaaaaa..", ".....aaaa...", "............"],
}
const INSIGNIA_SOBE := ["..r..", ".rrr.", "rrrrr", "..r..", "..r.."]   # sofre mais
const INSIGNIA_DESCE := ["..c..", "..c..", "ccccc", ".ccc.", "..c.."]   # resiste
const INSIGNIA_IMUNE := ["r...r", ".r.r.", "..r..", ".r.r.", "r...r"]   # imune
static var _icones := {}

static func _cores_el(el: String) -> Array:
	var c: Color = COR_EL[el]
	return [c, c.lerp(Color(1, 1, 1), 0.65)]

## Textura 16x16 do ícone (elemento + insígnia). `m` decide a insígnia: <= 0 imune, <= 0.6 resiste, senão sofre mais.
static func _icone(el: String, m: float) -> ImageTexture:
	var tipo := "imune" if m <= 0.0 else ("resiste" if m <= 0.6 else "sobe")
	var chave := el + "|" + tipo
	if _icones.has(chave):
		return _icones[chave]
	var n := DICA_LADO
	var img := Image.create(n, n, false, Image.FORMAT_RGBA8)
	var cores := _cores_el(el)
	var corpo := Image.create(n, n, false, Image.FORMAT_RGBA8)   # camada de cor, para depois cercar de preto
	for y in 12:
		for x in 12:
			var ch := String(FORMAS[el][y])[x]
			if ch == "a":
				corpo.set_pixel(x + 1, y + 2, cores[0])
			elif ch == "b":
				corpo.set_pixel(x + 1, y + 2, cores[1])
	var ins: Array = INSIGNIA_SOBE if tipo == "sobe" else (INSIGNIA_DESCE if tipo == "resiste" else INSIGNIA_IMUNE)
	var cor_ins := Color(1.0, 0.25, 0.22) if tipo != "resiste" else Color(0.72, 0.76, 0.86)
	var ins_img := Image.create(n, n, false, Image.FORMAT_RGBA8)
	for y in 5:
		for x in 5:
			if String(ins[y])[x] != ".":
				ins_img.set_pixel(10 + x, 10 + y, cor_ins)
	for camada in [corpo, ins_img]:
		for y in n:
			for x in n:
				if camada.get_pixel(x, y).a > 0.5:
					for d in [Vector2i(-1, 0), Vector2i(1, 0), Vector2i(0, -1), Vector2i(0, 1), Vector2i(-1, -1), Vector2i(1, 1), Vector2i(-1, 1), Vector2i(1, -1)]:
						var q: Vector2i = Vector2i(x, y) + d
						if q.x >= 0 and q.y >= 0 and q.x < n and q.y < n and img.get_pixel(q.x, q.y).a < 0.5:
							img.set_pixel(q.x, q.y, Color(0.02, 0.02, 0.03))
		for y in n:
			for x in n:
				var c: Color = camada.get_pixel(x, y)
				if c.a > 0.5:
					img.set_pixel(x, y, c)
	var tex := ImageTexture.create_from_image(img)
	_icones[chave] = tex
	return tex

## Ícone de 16 px com contorno preto de 1 px: o elemento (cor + realce) e, no canto, uma seta vermelha para cima
## (sofre mais), cinza para baixo (resiste) ou um X vermelho (imune). `c` = centro do ícone.
static func desenhar_dica(ci: CanvasItem, c: Vector2, d: Dictionary) -> void:
	ci.draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	var lado := float(DICA_LADO) * DICA_ESC
	ci.draw_texture_rect(_icone(d["el"], d["m"]), Rect2((c - Vector2(lado, lado) * 0.5).round(), Vector2(lado, lado)), false)

# ---------------- Mapa: braseiros e pilares ----------------
## Braseiros (`B`) e pilares (`O`) do mapa reagem ao fogo, ao raio e ao gelo quando o inimigo atingido está perto deles
## (data2d/reacoes_mapa.csv). A sala (grupo sala_2d) responde `estruturas_perto(pos, dist)` com dicionários vivos
## {tipo, pos, ate}; `ate` é a recarga da estrutura (ms), que também evita a cadeia entre vizinhos.
##   braseiro + fogo  -> labareda: a chama sobe e queima quem está em volta
##   braseiro + raio  -> descarga: a brasa solta arcos e choca até 2 inimigos
##   braseiro + gelo  -> apaga: o braseiro apaga por alguns segundos (sem labareda nem descarga) e sobe fumaça
##   pilar + raio     -> para-raios: o pilar atrai o raio e descarrega em até 2 inimigos
static var _mapa := {}

static func carregar_mapa() -> void:
	if not _mapa.is_empty():
		return
	for r in Csv.rows("res://data2d/reacoes_mapa.csv"):
		var d := {"id": r["id"], "estrutura": r["estrutura"], "gatilho": r["gatilho"], "recarga": float(r["recarga"])}
		for k in ["dano", "raio", "valor", "alcance"]:
			d[k] = float(r[k])
		var c: PackedStringArray = str(r["cor"]).split("/")
		d["cor"] = Color(float(c[0]), float(c[1]), float(c[2]))
		_mapa[r["estrutura"] + "/" + r["gatilho"]] = d

static func defs_mapa() -> Dictionary:
	carregar_mapa()
	return _mapa

## Chamar de aplicar_status junto de `tentar`. Devolve o id da reação do mapa disparada ("" = nenhuma).
static func tentar_mapa(alvo: Node2D, gatilho: String) -> String:
	carregar_mapa()
	if not alvo.is_inside_tree():
		return ""
	var agora := Time.get_ticks_msec()
	for sala in alvo.get_tree().get_nodes_in_group("sala_2d"):
		if not sala.has_method("estruturas_perto"):
			continue
		for est in sala.estruturas_perto(alvo.global_position, 140.0):
			var d: Dictionary = _mapa.get(str(est["tipo"]) + "/" + gatilho, {})
			if d.is_empty() or agora < int(est["ate"]) or est["pos"].distance_to(alvo.global_position) > d["alcance"]:
				continue
			if est["tipo"] == "braseiro" and agora < int(est.get("apagado", 0)):
				continue   # braseiro apagado não faz nada até reacender
			est["ate"] = agora + int(d["recarga"] * 1000.0)
			_disparar_mapa(d, est, alvo)
			return d["id"]
	return ""

static func _disparar_mapa(d: Dictionary, est: Dictionary, alvo: Node2D) -> void:
	var pai := alvo.get_parent()
	var pos: Vector2 = est["pos"]
	var dano: float = _dano_base(alvo) * float(d["dano"]) / 10.0
	var vizinhos: Array = U.no_raio(alvo, pos, d["raio"])
	match d["id"]:
		"braseiro_labareda":
			for n in vizinhos:
				n.take_damage(dano, pos)
				if n != alvo and n.has_method("aplicar_status"):
					n.aplicar_status("queimadura", 3.0, d["valor"])
			Marca.criar(pai, pos, "labareda", d)
		"braseiro_descarga", "pilar_pararaios":
			vizinhos = vizinhos.filter(func(n): return n != alvo)
			vizinhos.sort_custom(func(a: Node2D, b: Node2D): return a.global_position.distance_squared_to(pos) < b.global_position.distance_squared_to(pos))
			var pts: Array = [alvo.global_position]
			alvo.take_damage(dano, pos)
			for n in vizinhos.slice(0, int(d["valor"])):
				n.aplicar_status("choque", 2.0, 0.15)
				n.take_damage(dano, pos)
				pts.append(n.global_position)
			est["carga"] = Time.get_ticks_msec() + 1300   # a estrutura fica azul-branca um instante (room_2d._atualizar_estruturas)
			Marca.criar(pai, pos, "descarga" if d["id"] == "braseiro_descarga" else "pararaios", d, pts)
		"braseiro_apaga":
			est["apagado"] = Time.get_ticks_msec() + int(d["valor"] * 1000.0)
			Marca.criar(pai, pos, "fumaca", d)
	if dano >= 1.0 and d["id"] != "braseiro_apaga":
		Feel.numero(alvo, dano, d["cor"], false, true)

## Visual curto de cada reação, no padrão pixel do jogo: grão de 1 px, sem suavização, 2 a 4 cores por efeito, coordenadas
## sempre inteiras e nada de círculo vetorial liso (discos e anéis são montados em linhas de 1 px). Onde já existe folha
## de pixel art (fx_pixel_2d.gd) ela entra por baixo: gás e labareda.
class Marca extends Node2D:
	const Px = preload("res://scripts2d/fx_pixel_2d.gd")
	const PRETO := Color(0.03, 0.03, 0.06)
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
		m.global_position = pos.round()
		m.z_index = 5
		pai.add_child(m)
		match forma_:
			"gas":   # a folha de explosão (laranja) vira amarelo-esverdeado pela cor do gás
				var fx := Px.tocar(pai, "barrel_explosion", pos.round(), clampf(d["raio"] / 130.0, 0.6, 1.1), "centro", 0.0, 4)
				fx.modulate = Color(0.75, 1.0, 0.4)
			"labareda":
				Px.tocar(pai, "fire_ring", pos.round(), clampf(d["raio"] / 110.0, 0.8, 1.4), "centro", 0.0, 4)

	func _process(delta: float) -> void:
		_t += delta
		if _t >= DUR:
			queue_free()
		queue_redraw()

	## Vale desenhar neste quadro? No fim o efeito pisca (sem alfa: pixel art some em degrau, não em fade).
	func _visivel(k: float) -> bool:
		return k < 0.7 or int(_t * 40.0) % 2 == 0

	## Disco de pixels (linhas de 1 px, sem borda suave): contorno escuro, corpo `c1` e miolo `c2`. `r` em px.
	func _disco(c: Vector2, r: float, c1: Color, c2: Color, contorno := true) -> void:
		var ri := int(r)
		if ri < 2:
			return
		for ly in range(-ri, ri + 1):
			var hw := int(sqrt(float(ri * ri - ly * ly)))
			var rect := Rect2(c.x - hw, c.y + ly, hw * 2 + 1, 1)
			if contorno and (absi(ly) >= ri - 1 or hw < 2):
				draw_rect(rect, PRETO)
				continue
			draw_rect(rect, c1)
			if contorno:
				draw_rect(Rect2(rect.position.x, rect.position.y, 1, 1), PRETO)
				draw_rect(Rect2(rect.end.x - 1, rect.position.y, 1, 1), PRETO)
			var hi := int(sqrt(maxf(float(ri * ri) * 0.36 - float(ly * ly), 0.0)))
			if hi > 1:
				draw_rect(Rect2(c.x - hi, c.y + ly, hi * 2, 1), c2)

	## Anel de 1 px de cor, achatado (visão 3/4), feito de pontos inteiros.
	func _anel(c: Vector2, r: float, cor_: Color) -> void:
		var n := int(r * TAU * 0.7)
		for i in n:
			var a := TAU * float(i) / float(maxi(n, 1))
			if int(i) % 3 == 2:
				continue   # tracejado: lê como poeira, não como linha de UI
			draw_rect(Rect2(floorf(c.x + cos(a) * r), floorf(c.y + sin(a) * r * 0.5), 1, 1), cor_)

	## Raio em zigue-zague, 3 cores sólidas: contorno escuro (3 px), corpo (2 px) e miolo branco (1 px).
	func _raio(a: Vector2, b: Vector2, c_corpo: Color, c_borda: Color, sem: float) -> void:
		var dir := b - a
		if dir.length() < 3.0:
			return
		var n := dir.orthogonal().normalized()
		var pt := PackedVector2Array([a.round()])
		var passos := maxi(int(dir.length() / 14.0), 3)
		for i in range(1, passos):
			var q := float(i) / float(passos)
			pt.append((a + dir * q + n * U.ruido(sem, float(i)) * minf(dir.length() * 0.09, 14.0)).round())
		pt.append(b.round())
		draw_polyline(pt, c_borda, 3.0)
		draw_polyline(pt, c_corpo, 2.0)
		draw_polyline(pt, Color(1, 1, 1), 1.0)

	## Estrela de 5x5 px (cruz com miolo), para o ponto de onde o raio sai.
	func _faisca(c: Vector2, c1: Color, c2: Color) -> void:
		var o := c.round()
		draw_rect(Rect2(o.x - 3, o.y, 7, 1), c1)
		draw_rect(Rect2(o.x, o.y - 3, 1, 7), c1)
		draw_rect(Rect2(o.x - 1, o.y - 1, 3, 3), c2)

	## Estilhaço de gelo (losango alongado) apontando para `ang`: 3 tons chapados e contorno escuro, vértices inteiros.
	func _cristal(pos: Vector2, ang: float, comp: float, larg: float) -> void:
		if comp < 4.0:
			return
		var f := Vector2.from_angle(ang)
		var o := f.orthogonal()
		var topo := (pos + f * comp).round()
		var base_e := (pos + o * larg).round()
		var base_d := (pos - o * larg).round()
		var meio := (pos + f * comp * 0.3).round()
		draw_colored_polygon(PackedVector2Array([base_e - f * 1.0, (pos + f * comp * 0.3 + o * (larg + 1.0)).round(), topo + f, (pos + f * comp * 0.3 - o * (larg + 1.0)).round(), base_d - f * 1.0]), PRETO)
		draw_colored_polygon(PackedVector2Array([base_e, meio + o.round(), topo, meio - o.round(), base_d]), Color(0.3, 0.6, 0.95))
		draw_colored_polygon(PackedVector2Array([pos.round(), (pos + f * comp * 0.3 + o * larg).round(), topo]), Color(0.78, 0.96, 1.0))

	func _draw() -> void:
		var k := clampf(_t / DUR, 0.0, 1.0)
		if not _visivel(k):
			return
		var r := raio * (0.25 + 0.75 * sqrt(k))
		match forma:
			"vapor", "fumaca":   # nuvens de pixel que sobem; clareiam ao chegar no topo
				var vap := forma == "vapor"
				var tons := [Color(0.93, 0.96, 1.0), Color(0.72, 0.8, 0.92), Color(0.5, 0.58, 0.72)] if vap else [Color(0.62, 0.62, 0.68), Color(0.46, 0.46, 0.53), Color(0.3, 0.3, 0.37)]
				var n := 7 if vap else 4
				for i in n:
					var ang := TAU * float(i) / float(n) + 0.4
					var c := Vector2(cos(ang) * r * 0.5 if vap else sin(float(i) * 2.1 + _t * 3.0) * 7.0, (sin(ang) * r * 0.25 if vap else -14.0) - (46.0 if vap else 56.0) * k - float(i) * (0.0 if vap else 5.0))
					_disco(c.round(), (11.0 if vap else 13.0) + 8.0 * k, tons[1 if k < 0.6 else 2], tons[0 if k < 0.6 else 1], true)
			"rachadura":   # fendas vermelhas e azuis de 1 px com contorno escuro, mais brasas
				for i in 8:
					var ang := TAU * float(i) / 8.0 + 0.2
					var f := Vector2.from_angle(ang)
					var meio := f * r * 0.5 + f.orthogonal() * U.ruido(float(i), 2.0) * 10.0
					var cc := cor if i % 2 == 0 else Color(0.5, 0.85, 1.0)
					var linha := PackedVector2Array([Vector2.ZERO, meio.round(), (f * r).round()])
					draw_polyline(linha, PRETO, 3.0)
					draw_polyline(linha, cc, 2.0)
					draw_polyline(linha, Color(1.0, 0.95, 0.85), 1.0)
				_anel(Vector2.ZERO, r, Color(1.0, 0.85, 0.55))
			"gas":   # a folha de explosão cuida do clarão; aqui, bolhas de gás verde e fagulhas por cima
				for i in 9:
					var ang2 := TAU * float(i) / 9.0 + 0.5
					var rr := r * (0.35 + 0.5 * fposmod(float(i) * 0.37, 1.0))
					_disco((Vector2(cos(ang2), sin(ang2) * 0.6) * rr).round(), 5.0 + 4.0 * (1.0 - k), Color(0.42, 0.78, 0.2), Color(0.8, 1.0, 0.45))
				_faisca(Vector2.ZERO, Color(1.0, 0.8, 0.3), Color(1.0, 1.0, 0.8))
			"estilhaco":   # cristais voando para fora, mais pontos de gelo
				for i in 10:
					var ang3 := TAU * float(i) / 10.0 + 0.3
					_cristal(Vector2.from_angle(ang3) * r * 0.3, ang3, 8.0 + 22.0 * (1.0 - k), 3.0)
				for i in 14:
					var ang4 := TAU * float(i) / 14.0
					var q := (Vector2.from_angle(ang4) * r * (0.55 + 0.4 * fposmod(float(i) * 0.61, 1.0))).round()
					draw_rect(Rect2(q.x, q.y * 0.6, 2, 2), Color(0.85, 0.97, 1.0))
			"conducao":   # arcos azuis que correm pela água e marolas tracejadas
				_anel(Vector2.ZERO, r * 0.55, Color(0.7, 0.92, 1.0))
				_anel(Vector2.ZERO, r * 0.3, Color(0.4, 0.75, 1.0))
				for i in pts.size():
					_raio(Vector2.ZERO, pts[i] - global_position, Color(0.45, 0.8, 1.0), Color(0.05, 0.15, 0.4), float(i) + floorf(_t * 20.0))
				_faisca(Vector2.ZERO, Color(0.5, 0.85, 1.0), Color(1, 1, 1))
			"labareda":   # a folha do anel de fogo cuida da forma; brasas de 2 px sobem por cima
				for i in 12:
					var ox := (float(i) - 5.5) * 8.0
					var sobe := fposmod(float(i) * 0.43 + k * 1.4, 1.0)
					draw_rect(Rect2(floorf(ox + U.ruido(float(i), 1.0) * 5.0), floorf(-6.0 - sobe * 70.0), 2, 2), Color(1.0, 0.8, 0.3) if i % 2 == 0 else Color(1.0, 0.45, 0.12))
			"descarga", "pararaios":   # arcos que saem da estrutura até cada alvo; o pilar usa azul-gelo
				var forte := Color(1.0, 0.9, 0.4) if forma == "descarga" else Color(0.6, 0.85, 1.0)
				var borda := Color(0.45, 0.2, 0.02) if forma == "descarga" else Color(0.05, 0.15, 0.45)
				var topo_y := -52.0 if forma == "pararaios" else -20.0   # o raio sai do alto do pilar
				for i in pts.size():
					_raio(Vector2(0, topo_y), pts[i] - global_position, forte, borda, float(i) + floorf(_t * 20.0))
				_faisca(Vector2(0, topo_y), forte, Color(1, 1, 1))
			"corrente":   # arcos verdes e amarelos até os vizinhos
				for i in pts.size():
					_raio(Vector2.ZERO, pts[i] - global_position, Color(0.75, 1.0, 0.3), Color(0.1, 0.3, 0.05), float(i) + floorf(_t * 20.0))
				_faisca(Vector2.ZERO, Color(0.75, 1.0, 0.3), Color(1, 1, 0.9))
