extends RefCounted
## Efeitos das habilidades ativas do mago (data2d/habilidades_mago.csv, coluna `efeito`).
## Contrato com o runtime de habilidades: executar(efeito, jogador, def, nivel, mira) -> bool,
## true = a habilidade foi usada (gasta custo e recarga), false = cancelada.
## `def` já vem escalonado por nível; `mira` é a direção da mira (vetor unitário).
## Todos os números vêm do CSV de habilidades e de data2d/mago.csv (stats do jogador); aqui só a lógica.

const Alvos = preload("res://scripts2d/alvos_2d.gd")
const Efeito = preload("res://scripts2d/efeito_2d.gd")
const Orbe = preload("res://scripts2d/orbe_2d.gd")
const Feel = preload("res://scripts2d/feel_2d.gd")

const COR_FOGO := Color(1.0, 0.48, 0.12)
const COR_GELO := Color(0.45, 0.85, 1.0)
const COR_RAIO := Color(1.0, 0.92, 0.3)
const COR_ARCANO := Color(0.7, 0.4, 1.0)

static func executar(efeito: String, jogador: Node2D, def: Dictionary, nivel: int, mira: Vector2) -> bool:
	if jogador == null or not jogador.is_inside_tree():
		return false
	var dir := mira.normalized() if mira.length() > 0.01 else Vector2.DOWN
	match efeito:
		"bola_fogo": return _projetil(jogador, def, dir, COR_FOGO, 12.0, _burn(jogador, def), true)
		"raio_gelo": return _projetil(jogador, def, dir, COR_GELO, 10.0, _slow(jogador), false)
		"estacas_gelo": return _estacas(jogador, def, dir)
		"sopro_chamas": return _sopro(jogador, def, dir)
		"muralha_fogo": return _muralha(jogador, def, dir)
		"meteoro": return _meteoro(jogador, def, dir)
		"nova_fogo": return _nova(jogador, def, COR_FOGO, _burn(jogador, def))
		"nova_gelo": return _nova(jogador, def, COR_GELO, _freeze(jogador))
		"nova_raio": return _nova(jogador, def, COR_RAIO, _stun(jogador, 2.0))
		"barreira_gelo": return _barreira(jogador, def)
		"nevasca": return _nevasca(jogador, def, dir)
		"corrente_raios": return _corrente(jogador, def, dir)
		"salto_arcano": return _salto(jogador, def, dir)
		"tempestade": return _tempestade(jogador, def, dir)
		"surto_mana": return _surto(jogador, def)
	push_warning("efeito de habilidade desconhecido: " + efeito)
	return false

# ---- números derivados -------------------------------------------------------------------

static func _dano(jogador: Node2D, def: Dictionary) -> float:
	return float(def["dano"]) * float(jogador.stats.get("spell_power", 1.0))

static func _burn(jogador: Node2D, def: Dictionary) -> Dictionary:
	var s: Dictionary = jogador.stats
	return {"tipo": "queimadura", "dur": s["burn_duration"],
		"valor": _dano(jogador, def) * s["burn_dps_ratio"] * (1.0 + s.get("burn_bonus", 0.0))}

static func _slow(jogador: Node2D) -> Dictionary:
	var s: Dictionary = jogador.stats
	return {"tipo": "lentidao", "dur": s["slow_duration"], "valor": s["slow_amount"] + s.get("slow_bonus", 0.0)}

static func _freeze(jogador: Node2D) -> Dictionary:
	return {"tipo": "atordoamento", "dur": jogador.stats["freeze_duration"], "valor": 0.0}

static func _stun(jogador: Node2D, mult: float = 1.0) -> Dictionary:
	return {"tipo": "atordoamento", "dur": jogador.stats["stun_duration"] * mult, "valor": 0.0}

static func _cena(jogador: Node2D) -> Node:
	return jogador.get_parent()

static func _alvo_chao(jogador: Node2D, dir: Vector2, alcance: float) -> Vector2:
	if jogador.has_method("ponto_mira"):
		return jogador.ponto_mira(alcance)
	return jogador.global_position + dir * alcance

static func _origem(jogador: Node2D, dir: Vector2) -> Vector2:
	return jogador.global_position + dir * float(jogador.stats.get("arrow_spawn_dist", 36.0))

# ---- projéteis ---------------------------------------------------------------------------

static func _projetil(jogador: Node2D, def: Dictionary, dir: Vector2, cor: Color, tam: float, status: Dictionary, explode: bool) -> bool:
	var o := Orbe.new()
	o.setup(_origem(jogador, dir), dir, float(def["valor"]), _dano(jogador, def), float(def["alcance"]))
	o.cor = cor
	o.tamanho = tam
	o.status = status
	o.raio_expl = float(def["raio"]) if explode else 0.0
	_cena(jogador).add_child(o)
	return true

static func _estacas(jogador: Node2D, def: Dictionary, dir: Vector2) -> bool:
	var n := maxi(1, int(round(float(def["qtd"]))))
	for i in n:
		var d := dir.rotated(deg_to_rad(float(def["angulo"])) * (float(i) / maxf(1.0, n - 1.0) - 0.5)) if n > 1 else dir
		var o := Orbe.new()
		o.setup(_origem(jogador, d), d, float(def["valor"]), _dano(jogador, def), float(def["alcance"]))
		o.cor = Color(0.85, 0.97, 1.0)
		o.tamanho = 9.0
		o.pierce = 99
		o.status = _freeze(jogador)
		_cena(jogador).add_child(o)
	return true

# ---- área --------------------------------------------------------------------------------

static func _sopro(jogador: Node2D, def: Dictionary, dir: Vector2) -> bool:
	var p := jogador.global_position
	Efeito.cone(_cena(jogador), p, dir, float(def["alcance"]), float(def["angulo"]), COR_FOGO)
	for n in Alvos.em_cone(jogador.get_tree(), p, dir, float(def["alcance"]), float(def["angulo"])):
		Alvos.golpear(n, _dano(jogador, def), p, _burn(jogador, def))
	Feel.shake(jogador, 2.5, 0.12)
	return true

static func _nova(jogador: Node2D, def: Dictionary, cor: Color, status: Dictionary) -> bool:
	var p := jogador.global_position
	Efeito.anel(_cena(jogador), p, float(def["raio"]), cor)
	for n in Alvos.em_circulo(jogador.get_tree(), p, float(def["raio"])):
		Alvos.golpear(n, _dano(jogador, def), p, status)
	Feel.shake(jogador, 4.0, 0.18)
	return true

static func _muralha(jogador: Node2D, def: Dictionary, dir: Vector2) -> bool:
	var centro := _alvo_chao(jogador, dir, float(def["alcance"]))
	var meio := (centro - jogador.global_position).normalized()
	if meio == Vector2.ZERO:
		meio = dir
	var lado := meio.orthogonal() * float(def["qtd"]) * 0.5
	var arv := jogador.get_tree()
	var dano := _dano(jogador, def)
	var st := _burn(jogador, def)
	var de := centro - lado
	var para := centro + lado
	var espessura := float(def["raio"])
	Efeito.linha(_cena(jogador), de, para, espessura, COR_FOGO, float(def["duracao"]), float(def["valor"]),
		func() -> void:
			for n in Alvos.em_segmento(arv, de, para, espessura):
				Alvos.golpear(n, dano, centro, st))
	return true

static func _meteoro(jogador: Node2D, def: Dictionary, dir: Vector2) -> bool:
	var ponto := _alvo_chao(jogador, dir, float(def["alcance"]))
	var arv := jogador.get_tree()
	var cena := _cena(jogador)
	var dano := _dano(jogador, def)
	var st := _burn(jogador, def)
	var raio := float(def["raio"])
	Efeito.marca(cena, ponto, raio, COR_FOGO, float(def["duracao"]),
		func() -> void:
			for n in Alvos.em_circulo(arv, ponto, raio):
				Alvos.golpear(n, dano, ponto, st)
			Efeito.anel(cena, ponto, raio * 1.2, COR_FOGO, 0.5)
			Feel.shake(jogador, 7.0, 0.3))
	return true

static func _nevasca(jogador: Node2D, def: Dictionary, dir: Vector2) -> bool:
	var ponto := _alvo_chao(jogador, dir, float(def["alcance"]))
	var arv := jogador.get_tree()
	var dano := _dano(jogador, def)
	var st := _slow(jogador)
	var raio := float(def["raio"])
	Efeito.disco(_cena(jogador), ponto, raio, COR_GELO, float(def["duracao"]), float(def["valor"]),
		func() -> void:
			for n in Alvos.em_circulo(arv, ponto, raio):
				Alvos.golpear(n, dano, Vector2.ZERO, st))
	return true

static func _tempestade(jogador: Node2D, def: Dictionary, dir: Vector2) -> bool:
	var ponto := _alvo_chao(jogador, dir, float(def["alcance"]))
	var arv := jogador.get_tree()
	var cena := _cena(jogador)
	var dano := _dano(jogador, def)
	var st := _stun(jogador)
	var raio := float(def["raio"])
	var r_raio: float = jogador.stats["thunder_strike_radius"]
	var vezes := maxi(1, int(round(float(def["qtd"]))))
	Efeito.disco(cena, ponto, raio, COR_RAIO, float(def["duracao"]), float(def["valor"]),
		func() -> void:
			for _i in vezes:
				var q := ponto + Vector2.RIGHT.rotated(randf() * TAU) * (raio * sqrt(randf()))
				Efeito.raio_zigue(cena, q + Vector2(0, -260), q, COR_RAIO, 0.25)
				Efeito.anel(cena, q, r_raio, COR_RAIO, 0.25)
				for n in Alvos.em_circulo(arv, q, r_raio):
					Alvos.golpear(n, dano, q, st))
	return true

# ---- alvo único e utilidade --------------------------------------------------------------

static func _corrente(jogador: Node2D, def: Dictionary, dir: Vector2) -> bool:
	var arv := jogador.get_tree()
	var p := jogador.global_position
	var visados: Array = []
	var atual: Node2D = Alvos.mais_proximo(arv, p, float(def["alcance"]))
	if atual == null:
		return false
	var de := p + Vector2(0, -34)
	var n_max := maxi(1, int(round(float(def["qtd"]))))
	var t: float = jogador.stats["chain_ray_time"]
	for _i in n_max:
		visados.append(atual)
		var alvo_pos := atual.global_position + Vector2(0, -30)
		Efeito.raio_zigue(_cena(jogador), de, alvo_pos, COR_RAIO, t)
		Alvos.golpear(atual, _dano(jogador, def), de, _stun(jogador, 0.5))
		de = alvo_pos
		atual = Alvos.mais_proximo(arv, atual.global_position, float(def["raio"]), visados)
		if atual == null:
			break
	return true

static func _salto(jogador: Node2D, def: Dictionary, dir: Vector2) -> bool:
	var p := jogador.global_position
	var alvo := _alvo_chao(jogador, dir, float(def["alcance"]))
	var v := alvo - p
	if v.length() > float(def["alcance"]):
		alvo = p + v.normalized() * float(def["alcance"])
	var q := PhysicsRayQueryParameters2D.create(p, alvo, 1)
	var hit := jogador.get_world_2d().direct_space_state.intersect_ray(q)
	if not hit.is_empty():
		alvo = hit["position"] - (alvo - p).normalized() * 18.0
	Efeito.anel(_cena(jogador), p, 50.0, COR_ARCANO, 0.3)
	jogador.global_position = alvo
	jogador.invencivel = maxf(jogador.invencivel, jogador.stats["blink_iframes"])
	Efeito.anel(_cena(jogador), alvo, float(def["raio"]), COR_ARCANO, 0.35)
	for n in Alvos.em_circulo(jogador.get_tree(), alvo, float(def["raio"])):
		Alvos.golpear(n, _dano(jogador, def), alvo, _stun(jogador))
	return true

static func _barreira(jogador: Node2D, def: Dictionary) -> bool:
	jogador.dar_escudo(float(def["valor"]), float(def["duracao"]))
	Efeito.anel(_cena(jogador), jogador.global_position, 60.0, COR_GELO, 0.4)
	return true

static func _surto(jogador: Node2D, def: Dictionary) -> bool:
	jogador.surto_t = float(def["duracao"])
	jogador.surto_mult = float(def["valor"])
	Efeito.anel(_cena(jogador), jogador.global_position, 80.0, COR_ARCANO, 0.5)
	return true
