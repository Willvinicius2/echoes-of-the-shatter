extends RefCounted
## Ataque básico do mago e os quatro Ecos dele (data2d/afinidades_mago.csv). O Eco muda o que o básico FAZ:
##   sem Eco      = orbe arcano que voa reto e devolve mana ao acertar;
##   eco_m_trovao = Centelha: não há projétil, o raio cai na hora no alvo e salta para os vizinhos (choque);
##   eco_m_peste  = Bolha: orbe lento que atravessa a fila inteira envenenando e estoura numa nuvem no fim;
##   eco_m_gelo   = Lascas: leque de lascas curtas que somam frio (no 4º acúmulo congela);
##   eco_m_cinzas = Brasa: cometa de fogo que explode ao tocar e queima em volta.
## Números na tabela; aqui só regra e aparência. Uso: `disparar(jogador, dir)` a cada golpe básico.

const Afinidades = preload("res://scripts2d/afinidades_2d.gd")
const Alvos = preload("res://scripts2d/alvos_2d.gd")
const Orbe = preload("res://scripts2d/orbe_2d.gd")
const FxMago = preload("res://scripts2d/fx_mago_2d.gd")
const GeloFx = preload("res://scripts2d/efeitos_arqueiro_gelo_2d.gd")
const RaioFx = preload("res://scripts2d/efeitos_arqueiro_raio_2d.gd")
const Feel = preload("res://scripts2d/feel_2d.gd")
const CLASSE := "mago"
const ALTURA := Vector2(0, -30)

## Def do Eco `id` passado pela árvore de passivos (tags `basico`, `projetil` e a do elemento), como o do arqueiro.
static func def_de(jogador: Node2D, id: String) -> Dictionary:
	var d: Dictionary = Afinidades.defs(CLASSE).get(id, {}).duplicate()
	if d.is_empty():
		return d
	var h = jogador.habilidades if "habilidades" in jogador else null
	if h != null and h.passivos != null:
		d = h.passivos.resolver(id, d, ["basico", "projetil", str(d["elemento"])])
	return d

## Um golpe básico na direção `dir`. Devolve o projétil criado (null na Centelha, que não tem projétil).
static func disparar(jogador: Node2D, dir: Vector2) -> Node:
	var s: Dictionary = jogador.stats
	var d := def_de(jogador, str(jogador.afinidade)) if str(jogador.afinidade) != "" else {}
	var dano: float = jogador.dano_basico() * float(d.get("dano", 1.0))
	if d.is_empty():
		var o := _orbe(jogador, dir, dano, 1.0, "", "orbe")
		o.pierce = int(s["arrow_pierce"])
		return o
	match str(d["elemento"]):
		"raio":
			_centelha(jogador, dir, dano, d)
			return null
		"veneno":
			var b := _orbe(jogador, dir, dano, float(d["vel"]), "veneno", "bolha")
			b.pierce = int(d["perfura"]) + int(s["arrow_pierce"])
			b.tamanho = float(s["bolt_radius"]) * 1.4
			var dps: float = float(d["valor"]) * jogador.poder()
			b.ao_acertar = func(corpo: Node) -> void:
				if is_instance_valid(corpo) and corpo.has_method("aplicar_status"):
					corpo.aplicar_status("veneno", float(d["duracao"]), dps)
			var raio: float = float(d["raio"])
			var arv: SceneTree = jogador.get_tree()
			var cena: Node = jogador.get_parent()
			b.ao_fim = func(pos: Vector2) -> void:
				FxMago.explosao(cena, pos, "veneno", raio)
				for n in Alvos.em_circulo(arv, pos, raio):
					if n.has_method("aplicar_status"):
						n.aplicar_status("veneno", float(d["duracao"]), dps)
			return b
		"gelo":
			var n := maxi(1, int(d["qtd"]))
			var passo := deg_to_rad(float(d["raio"]))
			var primeira: Node = null
			for i in n:
				var l := _orbe(jogador, dir.rotated(passo * (float(i) - float(n - 1) * 0.5)), dano, float(d["vel"]), "gelo", "lasca")
				l.pierce = int(d["perfura"]) + int(s["arrow_pierce"])
				l.ao_acertar = func(corpo: Node) -> void:
					GeloFx.acumular_frio(corpo, 1, d)
				if primeira == null:
					primeira = l
			return primeira
		"fogo":
			var c := _orbe(jogador, dir, dano, float(d["vel"]), "fogo", "chama")
			c.raio_expl = float(d["raio"])
			c.status = {"tipo": "queimadura", "dur": float(d["duracao"]), "valor": float(d["valor"]) * jogador.poder()}
			return c
	return _orbe(jogador, dir, dano, 1.0, "", "orbe")

static func _orbe(jogador: Node2D, dir: Vector2, dano: float, vel_mult: float, elemento: String, forma: String) -> Node:
	var s: Dictionary = jogador.stats
	var o := Orbe.new()
	o.setup(jogador.global_position + dir * float(s["arrow_spawn_dist"]), dir, float(s["arrow_speed"]) * vel_mult, dano, float(s["arrow_range"]))
	o.elemento = elemento
	o.forma = forma
	o.tamanho = float(s["bolt_radius"])
	o.dono = weakref(jogador)
	o.mana_acerto = float(s.get("mana_on_hit", 0.0))
	jogador.get_parent().add_child(o)
	return o

## Centelha: raio instantâneo no inimigo da mira (o do autocast, senão o primeiro na linha), que salta para os vizinhos.
static func _centelha(jogador: Node2D, dir: Vector2, dano: float, d: Dictionary) -> void:
	var arv: SceneTree = jogador.get_tree()
	var cena: Node = jogador.get_parent()
	var de: Vector2 = jogador.ponta_do_cajado(dir)
	var alcance: float = float(jogador.stats["arrow_range"]) * 0.7
	var alvo: Node2D = null
	var melhor := INF
	for n in Alvos.em_segmento(arv, jogador.global_position, jogador.global_position + dir * alcance, 26.0):
		var dist: float = n.global_position.distance_to(jogador.global_position)
		if dist < melhor and Alvos.ve(arv, jogador.global_position, n.global_position):
			melhor = dist
			alvo = n
	if alvo == null:   # ninguém na linha: a centelha se perde no ar, curta
		RaioFx.arco_entre(cena, de, de + dir * 160.0, 0.5)
		return
	var visados: Array = []
	var saltos := maxi(0, int(d["qtd"])) + int(jogador.stats["arrow_pierce"])
	var forca := 1.0
	for i in saltos + 1:
		visados.append(alvo)
		var para: Vector2 = alvo.global_position + ALTURA
		RaioFx.arco_entre(cena, de, para, forca)
		FxMago.impacto(cena, para, "raio", 0.9)
		var pos: Vector2 = alvo.global_position
		alvo.take_damage(dano * forca, de)
		if is_instance_valid(alvo) and alvo.has_method("aplicar_status"):
			RaioFx.aplicar_choque(alvo, float(d["duracao"]), 0.15)
		jogador.ganhar_mana(float(jogador.stats.get("mana_on_hit", 0.0)))
		de = para
		forca = float(d["valor"])
		alvo = Alvos.mais_proximo(arv, pos, float(d["raio"]), visados)
		if alvo == null:
			break
	Feel.shake(jogador, 1.5, 0.06)
