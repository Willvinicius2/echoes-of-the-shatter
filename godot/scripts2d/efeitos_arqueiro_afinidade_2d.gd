extends RefCounted
## Afinidade do ataque básico ("Ecos", doc 36 seção 2): o jogador escolhe UM elemento na corrida e a flecha básica muda
## de comportamento e de visual, não só de cor. Números em data2d/afinidades_arqueiro.csv; aqui só regra e aparência.
## Uso: `aplicar(jogador, flecha, def)` logo depois de `lancar_flecha` do tiro básico (player_2d.gd).

const Csv = preload("res://scripts2d/csv2d.gd")
const Feel = preload("res://scripts2d/feel_2d.gd")
const VfxIdent = preload("res://scripts2d/vfx_identidade_2d.gd")
const Raio = preload("res://scripts2d/efeitos_arqueiro_raio_2d.gd")
const Gelo = preload("res://scripts2d/efeitos_arqueiro_gelo_2d.gd")
const Fogo = preload("res://scripts2d/efeitos_arqueiro_fogo_2d.gd")
const Veneno = preload("res://scripts2d/efeitos_arqueiro_veneno_2d.gd")

const CSV := "res://data2d/afinidades_arqueiro.csv"
const CAMPOS_NUM := ["dano", "vel", "perfura", "qtd", "raio", "duracao", "valor"]
const CORES := {"raio": Color("5FA8FF"), "veneno": Color("5CD12B"), "gelo": Color("7FD3F2"), "fogo": Color("FF7A1F")}

static var _defs := {}

## Linhas do CSV por id (números já convertidos).
static func defs() -> Dictionary:
	if _defs.is_empty() and FileAccess.file_exists(CSV):
		for r in Csv.rows(CSV):
			var d: Dictionary = r.duplicate()
			for c in CAMPOS_NUM:
				d[c] = float(r.get(c, "")) if str(r.get(c, "")) != "" else 0.0
			_defs[d["id"]] = d
	return _defs

static func ids() -> Array:
	return defs().keys()

static func elemento(id: String) -> String:
	return str(defs().get(id, {}).get("elemento", ""))

## Def da afinidade já passado pela árvore de passivos (nós de tag `basico`, `projetil` e do elemento valem para ela).
static func def_de(jogador: Node2D, id: String) -> Dictionary:
	var d: Dictionary = defs().get(id, {}).duplicate()
	if d.is_empty():
		return d
	var h = jogador.get("habilidades")
	if h != null and h.passivos != null:
		d = h.passivos.resolver("basico", d, ["basico", "projetil", d["elemento"]])
	return d

## Veste a flecha básica com a afinidade: velocidade, dano, perfuração, rastro, impacto e o efeito ao acertar.
static func aplicar(jogador: Node2D, f: Node, def: Dictionary) -> void:
	if f == null or def.is_empty() or not is_instance_valid(f):
		return
	var el: String = def["elemento"]
	f.velocity *= maxf(def.get("vel", 1.0), 0.1)
	f.damage *= def.get("dano", 1.0)
	f.pierce += int(def.get("perfura", 0))
	f.cor_fx = CORES.get(el, Color.WHITE)
	VfxIdent.anexar(f, el)
	match el:
		"raio":
			var dur: float = def.get("duracao", 2.0)
			var raio: float = def.get("raio", 160.0)
			var fracao: float = def.get("valor", 0.5)
			var saltos := int(def.get("qtd", 1))
			f.body_entered.connect(func(corpo: Node):
				if not _vivo(corpo):
					return
				Raio.aplicar_choque(corpo, dur, 0.15)
				_saltar(jogador, corpo, f.damage * fracao, raio, saltos, dur))
		"veneno":
			f.veneno_dps = maxf(f.veneno_dps, def.get("valor", 3.0))
			f.veneno_t = maxf(f.veneno_t, def.get("duracao", 3.0))
			Veneno.vestir_flecha(f)
		"gelo":
			var qtd := int(def.get("qtd", 1))
			Gelo.vestir_flecha(f)
			f.body_entered.connect(func(corpo: Node):
				if _vivo(corpo):
					Gelo.acumular_frio(corpo, qtd, def))
		"fogo":
			Fogo.vestir_flecha(f, def.get("duracao", 2.5), def.get("valor", 3.0), def.get("raio", 40.0))

static func _vivo(corpo: Node) -> bool:
	return is_instance_valid(corpo) and corpo.has_method("aplicar_status") and corpo.has_method("take_damage") \
		and not (corpo.has_method("esta_morto") and corpo.esta_morto())

## Eco do Trovão: do alvo acertado, um arco pula para o vizinho mais próximo (até `saltos` vezes), com dano `dano`.
static func _saltar(jogador: Node2D, de: Node2D, dano: float, raio: float, saltos: int, dur: float) -> void:
	var visitados: Array = [de]
	var atual: Node2D = de
	var cena: Node = de.get_parent()
	for _i in saltos:
		var prox: Node2D = Raio.mais_proximo_de(jogador, atual.global_position, raio, visitados)
		if prox == null:
			break
		visitados.append(prox)
		Raio.arco_entre(cena, atual.global_position + Vector2(0, -24), prox.global_position + Vector2(0, -24))
		prox.take_damage(dano, atual.global_position)
		if is_instance_valid(prox):
			Raio.aplicar_choque(prox, dur, 0.15)
			VfxIdent.impacto(cena, prox.global_position + Vector2(0, -24), "raio", Vector2.ZERO, 0.7)
		atual = prox
