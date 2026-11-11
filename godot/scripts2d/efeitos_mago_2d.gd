extends RefCounted
## Efeitos das habilidades ativas do mago (data2d/habilidades_mago.csv, coluna `efeito`).
## Contrato com o runtime de habilidades: executar(efeito, jogador, def, nivel, mira) -> bool,
## true = a habilidade foi usada (gasta custo e recarga), false = cancelada.
## `def` já vem escalonado por nível e pelos passivos; `mira` é a direção da mira (vetor unitário).
## Cada magia tem mecânica própria (ver a nota de cada função) e usa os status do jogo, para as reações elementais
## e os Arautos valerem também para o mago: queimadura, frio em acúmulos (congela no 4º), choque e veneno.
## Todos os números vêm do CSV de habilidades e de data2d/mago.csv (stats do jogador); aqui só a lógica.

const Alvos = preload("res://scripts2d/alvos_2d.gd")
const Orbe = preload("res://scripts2d/orbe_2d.gd")
const Feel = preload("res://scripts2d/feel_2d.gd")
const Vfx = preload("res://scripts2d/vfx_2d.gd")
const Px = preload("res://scripts2d/fx_pixel_2d.gd")
const FxMago = preload("res://scripts2d/fx_mago_2d.gd")
const U = preload("res://scripts2d/efeitos_extra_util_2d.gd")
const FogoU = preload("res://scripts2d/fogo_util_2d.gd")
const FogoFx = preload("res://scripts2d/efeitos_arqueiro_fogo_2d.gd")
const ExtraFogo = preload("res://scripts2d/efeitos_extra_fogo_2d.gd")
const GeloFx = preload("res://scripts2d/efeitos_arqueiro_gelo_2d.gd")
const ExtraGelo = preload("res://scripts2d/efeitos_extra_gelo_2d.gd")
const RaioFx = preload("res://scripts2d/efeitos_arqueiro_raio_2d.gd")
const ExtraRaio = preload("res://scripts2d/efeitos_extra_raio_2d.gd")
const Veneno = preload("res://scripts2d/efeitos_mago_veneno_2d.gd")

const COR_FOGO := Color(1.0, 0.48, 0.12)
const COR_GELO := Color(0.45, 0.85, 1.0)
const COR_RAIO := Color(0.5, 0.7, 1.0)
const COR_ARCANO := Color(0.7, 0.4, 1.0)
const ALTURA := Vector2(0, -30)

static func executar(efeito: String, jogador: Node2D, def: Dictionary, nivel: int, mira: Vector2) -> bool:
	if jogador == null or not jogador.is_inside_tree():
		return false
	var dir := mira.normalized() if mira.length() > 0.01 else Vector2.DOWN
	match efeito:
		"bola_fogo": return _bola_fogo(jogador, def, dir)
		"sopro_chamas": return _sopro(jogador, def, dir)
		"muralha_fogo": return _muralha(jogador, def, dir)
		"meteoro": return _meteoro(jogador, def, dir)
		"nova_fogo": return _nova_fogo(jogador, def)
		"raio_gelo": return _lanca_gelo(jogador, def, dir)
		"nova_gelo": return _nova_gelo(jogador, def)
		"barreira_gelo": return _barreira(jogador, def)
		"nevasca": return _nevasca(jogador, def, dir)
		"estacas_gelo": return _estacas(jogador, def, dir)
		"corrente_raios": return _corrente(jogador, def, dir)
		"salto_arcano": return _salto(jogador, def, dir)
		"tempestade": return _tempestade(jogador, def, dir)
		"surto_mana": return _surto(jogador, def)
		"nova_raio": return _sobrecarga(jogador, def, dir)
		"nuvem_peste", "esporos", "poco_acido": return Veneno.executar(efeito, jogador, def, dir)
	push_warning("efeito de habilidade desconhecido: " + efeito)
	return false

# ---- números derivados -------------------------------------------------------------------

## Dano da magia: o do CSV vezes o poder do mago (spell_power e o que as cartas subiram do dano básico).
static func _dano(jogador: Node2D, def: Dictionary) -> float:
	var poder: float = jogador.poder() if jogador.has_method("poder") else float(jogador.stats.get("spell_power", 1.0))
	return float(def.get("dano", 0.0)) * poder

static func _burn(jogador: Node2D, def: Dictionary) -> Dictionary:
	var s: Dictionary = jogador.stats
	return {"tipo": "queimadura", "dur": s["burn_duration"],
		"valor": _dano(jogador, def) * s["burn_dps_ratio"] * (1.0 + s.get("burn_bonus", 0.0))}

## Linha de frio para Gelo.acumular_frio: lentidão por acúmulo (com a passiva Frio Cortante) e duração.
static func _frio(jogador: Node2D, def: Dictionary) -> Dictionary:
	var s: Dictionary = jogador.stats
	var dur := float(def.get("duracao", 0.0))
	return {"duracao": dur if dur > 0.0 else float(s["slow_duration"]),
		"valor": float(s["chill_per_stack"]) + float(s.get("slow_bonus", 0.0))}

static func _cena(jogador: Node2D) -> Node:
	return jogador.get_parent()

static func _alvo_chao(jogador: Node2D, dir: Vector2, alcance: float) -> Vector2:
	if jogador.has_method("ponto_mira"):
		return jogador.ponto_mira(alcance)
	return jogador.global_position + dir * alcance

static func _origem(jogador: Node2D, dir: Vector2) -> Vector2:
	return jogador.global_position + dir * float(jogador.stats.get("arrow_spawn_dist", 36.0))

## Direções de um projétil com as cópias extras dos passivos (`proj_extra`) abertas em leque.
static func _leque(jogador: Node2D, def: Dictionary, dir: Vector2) -> Array:
	var dirs := [dir]
	var abertura := deg_to_rad(float(jogador.stats.get("multishot_spread", 10.0)))
	for i in int(def.get("proj_extra", 0)):
		var lado := 1.0 if i % 2 == 0 else -1.0
		dirs.append(dir.rotated(abertura * lado * float(int(i / 2.0) + 1)))
	return dirs

static func _novo_orbe(jogador: Node2D, def: Dictionary, dir: Vector2, elemento: String, forma: String, tam: float) -> Node:
	var o := Orbe.new()
	o.setup(_origem(jogador, dir), dir, float(def.get("valor", 600.0)) * float(def.get("vel", 1.0)), _dano(jogador, def), float(def.get("alcance", 900.0)))
	o.elemento = elemento
	o.forma = forma
	o.tamanho = tam
	o.pierce = int(def.get("perfura", 0))
	return o

# ---- fogo --------------------------------------------------------------------------------

## Bola de Fogo: cometa que explode em área no primeiro toque e queima todos na explosão.
static func _bola_fogo(jogador: Node2D, def: Dictionary, dir: Vector2) -> bool:
	for d in _leque(jogador, def, dir):
		var o := _novo_orbe(jogador, def, d, "fogo", "chama", 16.0)
		o.pierce = 0
		o.status = _burn(jogador, def)
		o.raio_expl = float(def.get("raio", 90.0))
		_cena(jogador).add_child(o)
	return true

## Sopro de Chamas: cone de fogo preso ao cajado que acompanha a mira por `duracao` s e fere em pulsos.
static func _sopro(jogador: Node2D, def: Dictionary, dir: Vector2) -> bool:
	var s := ExtraFogo.Sopro.new()
	s.jogador = jogador
	s.dir = dir
	s.meio_ang = deg_to_rad(float(def.get("angulo", 70.0))) * 0.5
	s.comp = float(def.get("alcance", 240.0))
	s.dur = maxf(float(def.get("duracao", 1.2)), 0.3)
	s.dano = _dano(jogador, def)
	s.queima_s = float(jogador.stats["burn_duration"])
	s.dps = float(def.get("valor", 4.0)) * (1.0 + float(jogador.stats.get("burn_bonus", 0.0)))
	_cena(jogador).add_child(s)
	s.global_position = jogador.global_position
	Feel.shake(jogador, 2.5, 0.12)
	return true

## Muralha de Fogo: parede de chamas ATRAVESSADA na frente do alvo (perpendicular à mira), que fecha a passagem
## por `duracao` s; quem cruza queima. `qtd` = comprimento em px, `raio` = espessura.
static func _muralha(jogador: Node2D, def: Dictionary, dir: Vector2) -> bool:
	var centro := _alvo_chao(jogador, dir, float(def.get("alcance", 260.0)))
	var meio := (centro - jogador.global_position).normalized()
	if meio == Vector2.ZERO:
		meio = dir
	var comp := float(def.get("qtd", 260.0))
	var lado := meio.orthogonal()
	var ini := centro - lado * comp * 0.5
	var m := FogoFx._Muralha.new()
	var espessura := float(def.get("raio", 30.0))
	m.preparar(ini, lado, comp, espessura, _dano(jogador, def), float(def.get("duracao", 5.0)),
		maxi(3, int(comp / maxf(espessura * 1.3, 1.0))), float(def.get("valor", 4.0)) * (1.0 + float(jogador.stats.get("burn_bonus", 0.0))))
	_cena(jogador).add_child(m)
	m.global_position = ini
	FxMago.anel(_cena(jogador), centro, "fogo", comp * 0.5, 0.25)
	return true

## Meteoro: sombra de aviso no maior grupo, a rocha cai do céu, explode e deixa o chão em brasa por `duracao` s.
static func _meteoro(jogador: Node2D, def: Dictionary, dir: Vector2) -> bool:
	var ponto := _alvo_chao(jogador, dir, float(def.get("alcance", 700.0)))
	var m := FogoFx._Meteoro.new()
	m.preparar(ponto, float(def.get("raio", 150.0)), _dano(jogador, def), float(def.get("duracao", 3.0)),
		float(def.get("valor", 6.0)) * (1.0 + float(jogador.stats.get("burn_bonus", 0.0))))
	_cena(jogador).add_child(m)
	m.global_position = ponto
	var eu: WeakRef = weakref(jogador)
	jogador.get_tree().create_timer(FogoU.TEMPO_QUEDA).timeout.connect(func() -> void:
		if eu.get_ref() != null:
			Feel.shake(eu.get_ref(), 7.0, 0.3))
	return true

## Nova Infernal: onda de fogo que abre do mago até `raio`, fere, queima e empurra o ritmo da luta para longe dele.
static func _nova_fogo(jogador: Node2D, def: Dictionary) -> bool:
	var n := NovaFogo.new()
	n.raio = float(def.get("raio", 230.0))
	n.dano = _dano(jogador, def)
	n.status = _burn(jogador, def)
	_cena(jogador).add_child(n)
	n.global_position = jogador.global_position
	Feel.shake(jogador, 5.0, 0.22)
	return true

## Onda de fogo que cresce: cada inimigo é atingido uma vez, quando a frente da onda passa por ele.
class NovaFogo extends Node2D:
	const VIDA := 0.45   # só ritmo visual da onda
	var raio := 230.0
	var dano := 0.0
	var status := {}
	var _t := 0.0
	var _feitos := {}
	func _ready() -> void:
		z_index = 2
		Vfx.registrar_animado(self)

	func _physics_process(delta: float) -> void:
		_t += delta
		var k := clampf(_t / VIDA, 0.0, 1.0)
		var frente := raio * (1.0 - pow(1.0 - k, 2.0))
		for e in U.no_raio(self, global_position, frente):
			if not _feitos.has(e.get_instance_id()):
				_feitos[e.get_instance_id()] = true
				Alvos.golpear(e, dano, global_position, status)
		queue_redraw()
		if _t >= VIDA + 0.25:
			queue_free()

	func _draw() -> void:   # chão queimado por baixo e uma parede de labaredas na frente da onda (elipse da visão 3/4)
		var k := clampf(_t / VIDA, 0.0, 1.0)
		var frente := raio * (1.0 - pow(1.0 - k, 2.0))
		var some := clampf((VIDA + 0.25 - _t) / 0.25, 0.0, 1.0)
		U.elipse_arco(self, Vector2.ZERO, frente, Color(1.0, 0.8, 0.35, 0.9 * some), 3.0)
		var n := 30
		var ordem := []
		for i in n:
			var a := TAU * float(i) / float(n)
			ordem.append(Vector2(cos(a) * frente, sin(a) * frente * 0.5))
		ordem.sort_custom(func(p: Vector2, q: Vector2) -> bool: return p.y < q.y)   # as de trás primeiro
		for i in n:
			var h := (30.0 + 16.0 * sin(_t * 22.0 + float(i) * 2.1)) * (0.6 + 0.4 * some)
			U.chama(self, ordem[i], h, 9.0, float(i) + _t * 9.0, some)

# ---- gelo --------------------------------------------------------------------------------

## Lança de Gelo: lasca grande e rápida que atravessa a fila e soma `qtd` acúmulos de frio em cada um.
static func _lanca_gelo(jogador: Node2D, def: Dictionary, dir: Vector2) -> bool:
	var frio := _frio(jogador, def)
	var acumulos := maxi(1, int(round(float(def.get("qtd", 2)))))
	for d in _leque(jogador, def, dir):
		var o := _novo_orbe(jogador, def, d, "gelo", "lasca", 16.0)
		o.pierce += int(jogador.stats.get("frost_bolt_pierce", 2))
		o.ao_acertar = func(corpo: Node) -> void:
			GeloFx.acumular_frio(corpo, acumulos, frio)
		_cena(jogador).add_child(o)
	return true

## Nova Glacial: explosão de gelo em volta do mago que CONGELA na hora quem estiver no raio.
static func _nova_gelo(jogador: Node2D, def: Dictionary) -> bool:
	var p := jogador.global_position
	var raio := float(def.get("raio", 200.0))
	FxMago.explosao(_cena(jogador), p, "gelo", raio)
	var dur: float = jogador.stats["freeze_duration"]
	for n in Alvos.em_circulo(jogador.get_tree(), p, raio):
		Alvos.golpear(n, _dano(jogador, def), p)
		if is_instance_valid(n):
			GeloFx.congelar(n, dur)
	Feel.shake(jogador, 4.0, 0.18)
	return true

## Barreira de Gelo: escudo que absorve `valor` de dano por `duracao` s; quando quebra ou acaba, estilhaça.
static func _barreira(jogador: Node2D, def: Dictionary) -> bool:
	var d := def.duplicate()
	d["dano_final"] = _dano(jogador, def)
	jogador.dar_escudo(float(def.get("valor", 40.0)), float(def.get("duracao", 6.0)), d)
	FxMago.anel(_cena(jogador), jogador.global_position, "gelo", 60.0)
	return true

## Estilhaços da Barreira (chamado pelo mago quando o escudo acaba): dano e `qtd` acúmulos de frio em `raio`.
static func estilhacar_barreira(jogador: Node2D, def: Dictionary) -> void:
	var p := jogador.global_position
	var raio := float(def.get("raio", 120.0))
	FxMago.explosao(_cena(jogador), p, "gelo", raio)
	var frio := _frio(jogador, def)
	frio["duracao"] = float(jogador.stats["slow_duration"])
	for n in Alvos.em_circulo(jogador.get_tree(), p, raio):
		Alvos.golpear(n, float(def.get("dano_final", 0.0)), p)
		if is_instance_valid(n):
			GeloFx.acumular_frio(n, maxi(1, int(round(float(def.get("qtd", 2))))), frio)

## Nevasca: tempestade de neve PARADA no ponto mirado (não segue o mago): fere em pulsos e soma frio em quem fica nela.
static func _nevasca(jogador: Node2D, def: Dictionary, dir: Vector2) -> bool:
	var nv := ExtraGelo.Nevasca.new()
	nv.raio = float(def.get("raio", 200.0))
	nv.dur = maxf(float(def.get("duracao", 6.0)), 1.0)
	nv.dano = _dano(jogador, def)
	nv.def = _frio(jogador, def)
	_cena(jogador).add_child(nv)
	nv.global_position = _alvo_chao(jogador, dir, float(def.get("alcance", 650.0)))
	Vfx.anel_entrada(_cena(jogador), nv.global_position, nv.raio, COR_GELO)
	return true

## Estacas Glaciais: `qtd` fileiras de estacas brotam do chão em leque a partir do mago, uma onda que anda para a frente.
static func _estacas(jogador: Node2D, def: Dictionary, dir: Vector2) -> bool:
	var n := maxi(1, int(round(float(def.get("qtd", 3)))))
	var abertura := deg_to_rad(float(def.get("angulo", 50.0)))
	var frio := _frio(jogador, def)
	for i in n:
		var d := dir.rotated(abertura * (float(i) / maxf(1.0, n - 1.0) - 0.5)) if n > 1 else dir
		var e := ExtraGelo.Espinhos.new()
		e.dir = d
		e.n = 6
		e.comp = float(def.get("alcance", 520.0))
		e.raio = float(def.get("raio", 46.0))
		e.dano = _dano(jogador, def)
		e.def = frio
		_cena(jogador).add_child(e)
		e.global_position = jogador.global_position
	Feel.shake(jogador, 4.0, 0.2)
	return true

# ---- raio --------------------------------------------------------------------------------

## Corrente de Raios: o raio sai do cajado, acerta o inimigo mais perto e salta `qtd` vezes, perdendo `valor` por salto.
static func _corrente(jogador: Node2D, def: Dictionary, _dir: Vector2) -> bool:
	var arv := jogador.get_tree()
	var p := jogador.global_position
	var visados: Array = []
	var atual: Node2D = Alvos.mais_proximo(arv, p, float(def.get("alcance", 520.0)))
	if atual == null:
		return false
	var de: Vector2 = jogador.ponta_do_cajado((atual.global_position - p).normalized()) if jogador.has_method("ponta_do_cajado") else p + ALTURA
	var n_max := maxi(1, int(round(float(def.get("qtd", 4)))))
	var dano := _dano(jogador, def)
	var queda := clampf(float(def.get("valor", 0.2)), 0.0, 0.9)
	for i in n_max:
		visados.append(atual)
		var pos := atual.global_position
		var alvo_pos := pos + ALTURA
		RaioFx.arco_entre(_cena(jogador), de, alvo_pos, 1.0 - 0.12 * float(i))
		FxMago.impacto(_cena(jogador), alvo_pos, "raio", 1.0)
		atual.take_damage(dano, de)
		if is_instance_valid(atual) and atual.has_method("aplicar_status"):
			RaioFx.aplicar_choque(atual, float(def.get("duracao", 3.0)), 0.15)
		dano *= 1.0 - queda
		de = alvo_pos
		atual = Alvos.mais_proximo(arv, pos, float(def.get("raio", 180.0)), visados)
		if atual == null:
			break
	Feel.shake(jogador, 2.0, 0.08)
	return true

## Salto Arcano: o mago some num raio e reaparece para longe do perigo; um raio cai onde ele estava e outro onde chega,
## ferindo e dando choque nos dois pontos.
static func _salto(jogador: Node2D, def: Dictionary, dir: Vector2) -> bool:
	var p := jogador.global_position
	var alcance := float(def.get("alcance", 320.0))
	var alvo := p + (_alvo_chao(jogador, dir, alcance) - p).limit_length(alcance)
	var q := PhysicsRayQueryParameters2D.create(p, alvo, 1)
	var hit := jogador.get_world_2d().direct_space_state.intersect_ray(q)
	if not hit.is_empty():
		alvo = hit["position"] - (alvo - p).normalized() * 18.0
	jogador.global_position = alvo
	jogador.invencivel = maxf(jogador.invencivel, jogador.stats["blink_iframes"])
	var raio := float(def.get("raio", 120.0))
	for ponto in [p, alvo]:
		var col := ExtraRaio.Coluna.new()
		_cena(jogador).add_child(col)
		col.global_position = ponto
		FxMago.anel(_cena(jogador), ponto, "raio", raio, 0.3)
		for n in Alvos.em_circulo(jogador.get_tree(), ponto, raio):
			n.take_damage(_dano(jogador, def), ponto)
			if is_instance_valid(n) and n.has_method("aplicar_status"):
				RaioFx.aplicar_choque(n, float(def.get("duracao", 3.0)), 0.15)
				n.aplicar_status("atordoamento", jogador.stats["stun_duration"])
	Feel.shake(jogador, 3.0, 0.12)
	return true

## Tempestade: nuvem escura sobre o maior grupo que derruba `qtd` raios com aviso, um de cada vez, por `duracao` s.
static func _tempestade(jogador: Node2D, def: Dictionary, dir: Vector2) -> bool:
	var t := ExtraRaio.Tempestade.new()
	t.raio = float(def.get("raio", 230.0))
	t.golpes = maxi(1, int(round(float(def.get("qtd", 6)))))
	t.dur = maxf(float(def.get("duracao", 4.0)), 0.5)
	t.dano = _dano(jogador, def)
	t.val = float(def.get("valor", 0.15))
	_cena(jogador).add_child(t)
	t.global_position = _alvo_chao(jogador, dir, float(def.get("alcance", 600.0)))
	return true

## Surto de Mana: por `duracao` s a mana regenera `valor` vezes mais rápido (faíscas arcanas sobem em volta do mago).
static func _surto(jogador: Node2D, def: Dictionary) -> bool:
	jogador.surto_t = float(def.get("duracao", 6.0))
	jogador.surto_mult = float(def.get("valor", 3.0))
	FxMago.anel(_cena(jogador), jogador.global_position, "", 80.0, 0.5)
	return true

## Sobrecarga (ult): estrela de `qtd` raios que sai do mago em todas as direções; choque e atordoamento em quem pega.
static func _sobrecarga(jogador: Node2D, def: Dictionary, dir: Vector2) -> bool:
	var e := ExtraRaio.Estrela.new()
	e.raio = float(def.get("raio", 260.0))
	e.qtd = maxi(3, int(round(float(def.get("qtd", 8)))))
	e.dano = _dano(jogador, def)
	e.dur_choque = float(def.get("duracao", 3.0))
	e.val = float(def.get("valor", 0.15))
	e.rot = dir.angle()
	_cena(jogador).add_child(e)
	e.global_position = jogador.global_position
	for n in Alvos.em_circulo(jogador.get_tree(), jogador.global_position, e.raio * 0.5):
		if n.has_method("aplicar_status"):
			n.aplicar_status("atordoamento", float(jogador.stats["stun_duration"]) * 2.0)
	Feel.shake(jogador, 6.0, 0.25)
	return true
