extends RefCounted
## Efeitos das habilidades ativas do Arqueiro (data2d/habilidades_arqueiro.csv). O `def` chega escalonado pelo nível;
## `mira` é a direção da mira. Devolve true se gastou a habilidade (entra em recarga) e false se cancelou.

const ZonaScript = preload("res://scripts2d/zona_2d.gd")
const Veneno = preload("res://scripts2d/efeitos_arqueiro_veneno_2d.gd")
const Gelo = preload("res://scripts2d/efeitos_arqueiro_gelo_2d.gd")
const Fogo = preload("res://scripts2d/efeitos_arqueiro_fogo_2d.gd")
const Raio = preload("res://scripts2d/efeitos_arqueiro_raio_2d.gd")

static func executar(efeito: String, jogador: Node2D, def: Dictionary, nivel: int, mira: Vector2) -> bool:
	if jogador == null or not jogador.is_inside_tree() or jogador.esta_morto():
		return false
	var dir: Vector2 = mira.normalized() if mira != Vector2.ZERO else jogador.mira_atual()
	var dano: float = def.get("dano", 1.0)
	match efeito:
		"tiro_forte":
			var f = jogador.lancar_flecha(dir, dano, int(def.get("qtd", 0)), def.get("valor", 1.0))
			f.cor_fx = Color(1.0, 0.7, 0.3)
		"rajada":
			var n := int(def.get("qtd", 3))
			var passo: float = def.get("duracao", 0.1)
			for i in n:
				if i == 0:
					jogador.lancar_flecha(dir, dano)
				else:
					jogador.get_tree().create_timer(passo * i).timeout.connect(func():
						if is_instance_valid(jogador) and not jogador.esta_morto():
							jogador.lancar_flecha(jogador.mira_atual(), dano))
		"leque":
			var n := int(def.get("qtd", 3))
			var abertura: float = deg_to_rad(def.get("angulo", 40.0))
			for i in n:
				var a := 0.0 if n == 1 else -abertura * 0.5 + abertura * i / float(n - 1)
				jogador.lancar_flecha(dir.rotated(a), dano)
		"chuva":
			_zona("chuva", jogador, dir, def, jogador.stats["arrow_damage"] * dano, Color(0.9, 0.75, 0.35), int(def.get("qtd", 5)))
		"armadilha":
			_zona("armadilha", jogador, dir, def, jogador.stats["arrow_damage"] * dano, Color(0.85, 0.5, 0.25), 1)
		"fumaca":
			_zona("fumaca", jogador, dir, def, 0.0, Color(0.55, 0.6, 0.7), 1)
		"explosiva":
			var f = jogador.lancar_flecha(dir, 0.6)
			f.explode_raio = def.get("raio", 120.0)
			f.explode_dano = jogador.stats["arrow_damage"] * dano
			f.cor_fx = Color(1.0, 0.5, 0.2)
		"marca":
			var alvo := _alvo_na_mira(jogador, dir, def.get("alcance", 600.0))
			if alvo == null:
				return false   # sem alvo perto da mira: não gasta a recarga
			alvo.aplicar_status("marca", def.get("duracao", 6.0), def.get("valor", 0.3))
		"salto":
			jogador.saltar(-dir, def.get("alcance", 280.0), def.get("duracao", 0.2))
			jogador.get_tree().create_timer(def.get("duracao", 0.2)).timeout.connect(func():
				if is_instance_valid(jogador) and not jogador.esta_morto():
					jogador.lancar_flecha(dir, dano))
		"furia":
			var v: float = def.get("valor", 0.35)
			jogador.dar_buff(def.get("duracao", 5.0), 1.0 + v * 0.5, 1.0 / (1.0 - minf(v, 0.8)))
		"tiro_veneno", "bola_veneno", "chuva_corrosiva":
			return Veneno.executar(efeito, jogador, def, nivel, mira)
		"gelo_flecha", "gelo_estilhaco", "gelo_prisao":
			return Gelo.executar(efeito, jogador, def, nivel, mira)
		"tiro_ardente", "meteoro", "muralha":
			return Fogo.executar(efeito, jogador, def, nivel, mira)
		"flecha_eletrica", "raio_encadeado", "tornado":
			return Raio.executar(efeito, jogador, def, nivel, mira)
		_:
			push_error("Efeito de arqueiro desconhecido: " + efeito)
			return false
	return true

## Ponto no chão mirado: o alvo do autocast (limitado ao alcance); senão até onde o mouse aponta; sem mouse, 70% do alcance.
static func _ponto(jogador: Node2D, dir: Vector2, alcance: float) -> Vector2:
	if jogador.has_method("tem_alvo_auto") and jogador.tem_alvo_auto():
		return jogador.ponto_mira(alcance)
	var d: float = 0.7 * alcance
	if jogador.auto_aim == Vector2.ZERO:
		var m: Vector2 = jogador.get_global_mouse_position() - jogador.global_position
		if m.length() > 8.0 and m.normalized().dot(dir) > 0.9:
			d = minf(m.length(), alcance)
	return jogador.global_position + dir * d

static func _zona(tipo: String, jogador: Node2D, dir: Vector2, def: Dictionary, dano: float, cor: Color, pulsos: int) -> void:
	var z := ZonaScript.new()
	z.setup(tipo, _ponto(jogador, dir, def.get("alcance", 400.0)), def.get("raio", 120.0), def.get("duracao", 2.0), dano, cor)
	z.pulsos = pulsos
	z.valor = def.get("valor", 0.0)
	jogador.get_parent().add_child(z)

## Inimigo mais alinhado com a mira (até 20 graus) dentro do alcance.
static func _alvo_na_mira(jogador: Node2D, dir: Vector2, alcance: float) -> Node2D:
	var melhor: Node2D = null
	var melhor_a := deg_to_rad(20.0)
	for n in jogador.get_tree().get_nodes_in_group("hurtable"):
		if n is Node2D and n.has_method("aplicar_status"):
			var v: Vector2 = n.global_position - jogador.global_position
			if v.length() <= alcance and absf(dir.angle_to(v)) <= melhor_a:
				melhor_a = absf(dir.angle_to(v))
				melhor = n
	return melhor
