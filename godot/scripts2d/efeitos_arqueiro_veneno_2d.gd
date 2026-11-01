extends RefCounted
## Árvore de VENENO do Arqueiro (doc 32_veneno.md). Todos os números chegam em `def` (linha de
## data2d/habilidades_arqueiro.csv, já escalonada pelo nível); aqui não há balanceamento.
## Entrada: `executar(efeito, jogador, def, nivel, mira)` com efeito = tiro_veneno | bola_veneno | chuva_corrosiva.
## Gancho do Herald: `arauto_peste_morte(inimigo, def)`. A integradora liga os dois em efeitos_arqueiro_2d.gd.

const Feel = preload("res://scripts2d/feel_2d.gd")
const Vfx = preload("res://scripts2d/vfx_2d.gd")
const Recolor = preload("res://scripts2d/recolor_2d.gd")
const Placeholders = preload("res://scripts2d/placeholders.gd")
const VERDE := Color(0.45, 0.9, 0.25)
const PASTA := "res://art2d/fx/veneno/"
## Folhas em linha: nome -> [largura do quadro, altura, quadros, fps, loop]. Só formato de arte, sem balanceamento.
const FOLHAS := {
	"fx_veneno_flecha": [64, 64, 6, 14.0, true],
	"fx_veneno_impacto": [96, 96, 8, 16.0, false],
	"fx_veneno_bola": [64, 64, 6, 12.0, true],
	"fx_veneno_poca": [192, 192, 8, 8.0, true],
	"fx_veneno_nuvem": [192, 192, 8, 12.0, false],
	"fx_veneno_chuva": [192, 192, 8, 10.0, true],
	"fx_veneno_status": [96, 96, 6, 10.0, true],
	"fx_veneno_arauto_aura": [128, 128, 6, 8.0, true],
	"fx_veneno_arauto_gatilho": [128, 128, 8, 14.0, false],
}

static func executar(efeito: String, jogador: Node2D, def: Dictionary, nivel: int, mira: Vector2) -> bool:
	if jogador == null or not jogador.is_inside_tree() or jogador.esta_morto():
		return false
	var dir: Vector2 = mira.normalized() if mira != Vector2.ZERO else jogador.mira_atual()
	var dano: float = def.get("dano", 1.0)
	match efeito:
		"tiro_veneno":
			var f = jogador.lancar_flecha(dir, dano, int(def.get("qtd", 0)), 1.0, def)
			f.veneno_dps = def.get("valor", 4.0)       # dps do veneno vem do CSV
			f.veneno_t = def.get("duracao", 3.0)
			f.cor_fx = VERDE
			_anexar_anim(f.vis, "fx_veneno_flecha", Vector2.ZERO)
		"bola_veneno":
			_bola(jogador, dir, def, jogador.stats["arrow_damage"] * dano)
		"chuva_corrosiva":
			var alvo: Vector2 = _ponto(jogador, dir, def.get("alcance", 450.0))
			var z := ZonaVeneno.new()
			z.configurar("chuva", def, jogador.stats["arrow_damage"] * dano, _anim_sprite, _anim_unica)
			z.global_position = alvo
			jogador.get_parent().add_child(z)
		"tornado_toxico":
			_ciclone(jogador, dir, def, jogador.stats["arrow_damage"] * dano)
		_:
			push_error("Efeito de veneno desconhecido: " + efeito)
			return false
	return true

## Herald (passiva de gatilho): chamar quando um inimigo envenenado morre. def: raio, duracao, valor (dps), dano.
static func arauto_peste_morte(inimigo: Node2D, def: Dictionary) -> void:
	if inimigo == null or not inimigo.is_inside_tree() or not inimigo.tem_status("veneno"):
		return
	var raio: float = def.get("raio", 140.0)
	var pai := inimigo.get_parent()
	_anim_unica(pai, "fx_veneno_arauto_gatilho", inimigo.global_position + Vector2(0, -40), raio / 64.0)
	for n in inimigo.get_tree().get_nodes_in_group("hurtable"):
		if n != inimigo and n is Node2D and n.has_method("aplicar_status") \
				and n.global_position.distance_to(inimigo.global_position) <= raio:
			n.aplicar_status("veneno", def.get("duracao", 3.0), def.get("valor", 4.0))

## Overlay curto do status veneno no inimigo (bolhas verdes subindo). Chamar quando aplica o status.
static func overlay_status(inimigo: Node2D, dur: float) -> void:
	if inimigo.has_node("OverlayVeneno"):
		return
	var s := _anim_sprite("fx_veneno_status")
	if s == null:
		return
	s.name = "OverlayVeneno"
	s.position = Vector2(0, -50)
	inimigo.add_child(s)
	inimigo.get_tree().create_timer(dur).timeout.connect(func():
		if is_instance_valid(s):
			s.queue_free())

## Aura leve do Herald no arqueiro (liga/desliga conforme a gema equipada).
## Aura do Arauto da Peste na camada C1 (elipse no chão, atrás do arqueiro; regra única em vfx_2d.gd). Nó "AuraPeste".
static func aura_arauto(jogador: Node2D) -> void:
	if jogador.has_node("AuraPeste"):
		return
	var s := _anim_sprite("fx_veneno_arauto_aura")
	if s == null:
		return
	Vfx.aura_c1(jogador, s, float(FOLHAS["fx_veneno_arauto_aura"][0]), "AuraPeste")

# --- Bola de Veneno: sai do arco, sobe em arco com sombra no chão e aviso no ponto de queda, vira poça e estoura ---
const VOO_BOLA := 0.55     # só ritmo visual
const ALTURA_BOLA := 320.0

static func _bola(jogador: Node2D, dir: Vector2, def: Dictionary, dano: float) -> void:
	var destino: Vector2 = _ponto(jogador, dir, def.get("alcance", 450.0))
	var pai := jogador.get_parent()
	var bola: Node2D = _anim_sprite("fx_veneno_bola")
	if bola == null:
		bola = Node2D.new()
	var boca: Dictionary = jogador.boca_do_arco(dir) if jogador.has_method("boca_do_arco") \
			else {"chao": jogador.global_position, "altura": 50.0}
	Vfx.flash_boca(pai, boca["chao"] + Vector2(0, -boca["altura"]), dir)
	Vfx.arco(pai, boca["chao"], boca["altura"], destino, ALTURA_BOLA, VOO_BOLA, bola, VERDE, def.get("raio", 110.0),
		func(ponto: Vector2):
			if not is_instance_valid(pai) or not pai.is_inside_tree():
				return
			var z := ZonaVeneno.new()
			z.configurar("poca", def, dano, _anim_sprite, _anim_unica)
			z.global_position = ponto
			pai.add_child(z))

## Veste a flecha básica com a folha do veneno (Eco da Peste); o rastro vetorial vem de vfx_identidade_2d.gd.
static func vestir_flecha(f: Node) -> void:
	if f != null and "vis" in f:
		_anexar_anim(f.vis, "fx_veneno_flecha", Vector2.ZERO)

# --- Ciclone Pestilento (doc 36, família tornado): a flecha sobe em arco e cai; no chão nasce um funil baixo e largo
# que anda atrás do grupo mais denso, EMPURRA os inimigos para fora (o de tempestade puxa), envenena quem toca e
# deixa poças no caminho. Um nó desenha as poças (C0); o filho desenha o funil e as bolhas (C4).
const VOO_CICLONE := 0.55
const ALTURA_CICLONE := 360.0

static func _ciclone(jogador: Node2D, dir: Vector2, def: Dictionary, dano: float) -> void:
	var destino: Vector2 = _ponto(jogador, dir, def.get("alcance", 600.0))
	var pai := jogador.get_parent()
	var corpo := Node2D.new()
	var seta := Sprite2D.new()
	seta.texture = load("res://art2d/fx/arrow.png") if ResourceLoader.exists("res://art2d/fx/arrow.png") else Placeholders.seta(Vector2i(64, 16))
	corpo.add_child(seta)
	_anexar_anim(corpo, "fx_veneno_flecha", Vector2.ZERO)
	var boca: Dictionary = jogador.boca_do_arco(dir) if jogador.has_method("boca_do_arco") \
			else {"chao": jogador.global_position, "altura": 50.0}
	Vfx.flash_boca(pai, boca["chao"] + Vector2(0, -boca["altura"]), dir)
	Vfx.arco(pai, boca["chao"], boca["altura"], destino, ALTURA_CICLONE, VOO_CICLONE, corpo, VERDE, def.get("raio", 130.0),
		func(ponto: Vector2):
			if not is_instance_valid(pai) or not pai.is_inside_tree():
				return
			var c := Ciclone.new()
			c.configurar(def, dano)
			c.global_position = ponto
			pai.add_child(c), true)

static func _ponto(jogador: Node2D, dir: Vector2, alcance: float) -> Vector2:
	if jogador.has_method("tem_alvo_auto") and jogador.tem_alvo_auto():
		return jogador.ponto_mira(alcance)
	return jogador.global_position + dir * (0.7 * alcance)

# --- sprites ---
static func _frames(nome: String) -> SpriteFrames:
	var info: Array = FOLHAS[nome]
	var caminho: String = PASTA + nome + ".png"
	if not ResourceLoader.exists(caminho):
		return null   # arte ainda não chegou: o efeito roda só com partículas
	var tex: Texture2D = load(caminho)
	var sf := SpriteFrames.new()
	sf.add_animation("a")
	sf.set_animation_speed("a", info[3])
	sf.set_animation_loop("a", info[4])
	for i in int(info[2]):
		var at := AtlasTexture.new()
		at.atlas = tex
		at.region = Rect2(i * info[0], 0, info[0], info[1])
		sf.add_frame("a", at)
	return sf

static func _anim_sprite(nome: String) -> AnimatedSprite2D:
	var sf := _frames(nome)
	if sf == null:
		return null
	var s := AnimatedSprite2D.new()
	s.sprite_frames = sf
	s.material = Feel.aditivo()
	s.play("a")
	return s

static func _anexar_anim(no: Node2D, nome: String, pos: Vector2) -> void:
	var s := _anim_sprite(nome)
	if s != null:
		s.position = pos
		no.add_child(s)

static func _anim_unica(pai: Node, nome: String, pos: Vector2, escala := 1.0) -> void:
	var s := _anim_sprite(nome)
	if s == null:
		Feel.impacto(pai, pos, VERDE, Vector2.ZERO, escala)
		return
	s.global_position = pos
	s.scale = Vector2(escala, escala)
	pai.add_child(s)
	s.animation_finished.connect(s.queue_free)

## Zona de veneno. "poca": fere e lentifica em pulsos, no fim estoura em nuvem. "chuva": pulsos que
## aplicam corrosão (inimigo sofre mais dano, via status "marca"). Parâmetros: raio, duracao, qtd (pulsos),
## valor (lentidão/corrosão), alcance já usado fora; dano chega pronto.
class ZonaVeneno extends Node2D:
	var tipo := "poca"
	var raio := 100.0
	var duracao := 3.0
	var dano := 0.0
	var pulsos := 4
	var valor := 0.3
	var dps_veneno := 0.0
	var _t := 0.0
	var _prox := 0
	var _fabrica: Callable   # nome -> AnimatedSprite2D (vem do script de fora; inner class não vê os estáticos dele)
	var _unica: Callable    # (pai, nome, pos, escala)

	func configurar(t: String, def: Dictionary, d: float, fabrica: Callable, unica: Callable) -> void:
		_fabrica = fabrica
		_unica = unica
		tipo = t
		raio = def.get("raio", 110.0)
		duracao = def.get("duracao", 3.0)
		pulsos = maxi(1, int(def.get("qtd", 4)))
		valor = def.get("valor", 0.3)
		dps_veneno = def.get("escala", 0.0)
		dano = d
		z_index = -1

	func _ready() -> void:
		var nome := "fx_veneno_poca" if tipo == "poca" else "fx_veneno_chuva"
		var s = _fabrica.call(nome)
		if s != null:
			s.scale = Vector2.ONE * (raio * 2.0 / 192.0)
			add_child(s)
		Vfx.anel_entrada(get_parent(), global_position, raio, VERDE)   # anel de entrada (doc 33 seção 2)

	func _alvos() -> Array:
		var out := []
		for n in get_tree().get_nodes_in_group("hurtable"):
			if n is Node2D and n.global_position.distance_to(global_position) <= raio:
				out.append(n)
		return out

	func _physics_process(delta: float) -> void:
		_t += delta
		while _prox < pulsos and _t >= duracao * _prox / float(pulsos):
			_prox += 1
			for n in _alvos():
				n.take_damage(dano, global_position)
				if n.has_method("aplicar_status"):
					if tipo == "poca":
						n.aplicar_status("lentidao", duracao / float(pulsos) + 0.2, valor)
					else:
						n.aplicar_status("marca", duracao / float(pulsos) + 0.5, valor)   # corrosão = recebe mais dano
					if dps_veneno > 0.0:
						n.aplicar_status("veneno", 2.0, dps_veneno)
		modulate.a = Vfx.fade_zona(_t, duracao)   # some em fade, nunca de uma vez
		if _t >= duracao:
			if tipo == "poca":   # estouro final em nuvem
				_unica.call(get_parent(), "fx_veneno_nuvem", global_position, raio / 96.0)
				for n in _alvos():
					n.take_damage(dano * 1.5, global_position)
			queue_free()

## Ciclone Pestilento. Números do CSV: raio, duracao, dano (por pulso de 0,5 s), qtd (dps do veneno), valor (px/s que anda).
class Ciclone extends Node2D:
	const PAL := [Color("E6FF8A"), Color("5CD12B"), Color("123D1A")]
	const PULSO := 0.5
	const EMPURRA := 120.0     # px/s para fora (aparência de "sopro"; o dano é do CSV)
	var raio := 130.0
	var duracao := 5.0
	var dano := 0.0
	var dps := 3.0
	var anda := 70.0
	var _t := 0.0
	var _acc := 0.0
	var _busca := 0.0
	var _alvo := Vector2.INF
	var _pocas: Array = []     # [pos (global), nasceu em s]
	var _prox_poca := 0.0
	var _funil: Node2D

	func configurar(def: Dictionary, d: float) -> void:
		raio = def.get("raio", 130.0)
		duracao = def.get("duracao", 5.0)
		dano = d
		dps = def.get("qtd", 3.0)
		anda = def.get("valor", 70.0)
		z_index = -1

	func _ready() -> void:
		Vfx.registrar_animado(self)
		Vfx.registrar_decalque(self)
		_funil = CicloneFunil.new()
		_funil.dona = self
		_funil.z_index = 5   # -1 + 5 = 4 (C4)
		add_child(_funil)
		Vfx.anel_entrada(get_parent(), global_position, raio, PAL[1])

	func _physics_process(delta: float) -> void:
		_t += delta
		_acc += delta
		_busca -= delta
		if _busca <= 0.0:
			_busca = 0.5
			_alvo = _onde_ir()
		if _alvo != Vector2.INF and _alvo.distance_to(global_position) > 12.0:
			global_position += (_alvo - global_position).normalized() * anda * delta
		var tree := get_tree()
		for n in tree.get_nodes_in_group("hurtable"):
			if n is Node2D:
				var v: Vector2 = n.global_position - global_position
				if v.length() <= raio and v.length() > 1.0:
					n.global_position += v.normalized() * EMPURRA * delta   # sopra para fora
		if _acc >= PULSO:
			_acc = 0.0
			for n in tree.get_nodes_in_group("hurtable"):
				if n is Node2D and n.has_method("take_damage"):
					var dentro: bool = n.global_position.distance_to(global_position) <= raio
					if not dentro:
						for pc in _pocas:
							if n.global_position.distance_to(pc[0]) <= 26.0:
								dentro = true
								break
					if dentro:
						n.take_damage(dano, global_position)
						if is_instance_valid(n) and n.has_method("aplicar_status"):
							n.aplicar_status("veneno", 2.0, dps)
							n.aplicar_status("lentidao", 0.6, 0.3)
		_prox_poca -= delta
		if _prox_poca <= 0.0:
			_prox_poca = 0.35
			if _pocas.size() < 5 and Vfx.decalque_cabe(tree):   # poucas e espalhadas: não viram um borrão com 20 inimigos
				_pocas.append([global_position + Vector2(randf_range(-raio, raio) * 0.7, randf_range(-raio, raio) * 0.4), _t])
		_pocas = _pocas.filter(func(pc): return _t - pc[1] < 1.6)
		queue_redraw()
		_funil.queue_redraw()
		if _t >= duracao:
			queue_free()

	## Centro do grupo mais denso num raio de busca; sem grupo, o inimigo mais perto; sem ninguém, fica.
	func _onde_ir() -> Vector2:
		var melhor: Node2D = null
		var melhor_n := 0
		var melhor_d := INF
		var vivos := get_tree().get_nodes_in_group("hurtable")
		for a in vivos:
			if not (a is Node2D) or a.global_position.distance_to(global_position) > raio * 5.0:
				continue
			var k := 0
			for b in vivos:
				if b is Node2D and a.global_position.distance_to(b.global_position) <= raio:
					k += 1
			var d: float = a.global_position.distance_to(global_position)
			if k > melhor_n or (k == melhor_n and d < melhor_d):
				melhor = a
				melhor_n = k
				melhor_d = d
		return melhor.global_position if melhor != null else Vector2.INF

	## Poças no chão (C0): elipses com borda escura e miolo claro, somem em 1,6 s.
	func _draw() -> void:
		var apaga: float = Vfx.fade_zona(_t, duracao)
		for pc in _pocas:
			var idade: float = _t - pc[1]
			var k := clampf(1.0 - idade / 1.6, 0.0, 1.0)
			var r := 8.0 + 10.0 * minf(idade * 4.0, 1.0)
			var p: Vector2 = to_local(pc[0])
			draw_set_transform(p, 0.0, Vector2(1.0, 0.5))
			draw_circle(Vector2.ZERO, r + 2.0, Color(PAL[2], 0.5 * k * apaga))
			draw_circle(Vector2.ZERO, r, Color(PAL[1].darkened(0.25), 0.4 * k * apaga))
			draw_circle(Vector2(-r * 0.3, -r * 0.3), r * 0.3, Color(PAL[0], 0.35 * k * apaga))
		draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.5))
		draw_arc(Vector2.ZERO, raio, 0.0, TAU, 48, Color(PAL[1], 0.25 * apaga), 2.0)   # área real do CSV

## Funil do Ciclone (filho, C4): folha do tornado com matiz girado para o verde-ácido, ACHATADA (baixo e largo, silhueta
## diferente do de tempestade), base de lama escura e bolhas que orbitam e estouram. Arte provisória até a folha própria.
class CicloneFunil extends Node2D:
	var dona: Node2D
	var _tex: Texture2D
	func _ready() -> void:
		var c := "res://art2d/fx/raio/tornado_tempestade.png"
		_tex = load(c) if ResourceLoader.exists(c) else null
		material = Recolor.tornado_para_veneno()
	func _draw() -> void:
		if dona == null:
			return
		var pal: Array = dona.PAL
		var t: float = dona._t
		var raio: float = dona.raio
		var apaga: float = Vfx.fade_zona(t, dona.duracao)
		# base de lama: anel escuro girando (o funil arrasta o chão)
		draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.5))
		for i in 10:
			var a := t * 4.0 + TAU * i / 10.0
			var p := Vector2.from_angle(a) * raio * 0.55
			draw_circle(p, 7.0 + 3.0 * sin(t * 6.0 + i), Color(pal[1], 0.35 * apaga))
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
		if _tex != null:
			var w := float(_tex.get_width()) / 8.0
			var h := float(_tex.get_height())
			var ex := raio * 2.2 / w      # mais largo...
			var ey := ex * 0.62           # ...e mais baixo que o de tempestade
			var qi := int(t * 12.0) % 8
			draw_texture_rect_region(_tex, Rect2(Vector2(-w * 0.5 * ex, -h * ey + 14.0), Vector2(w * ex, h * ey)), Rect2(qi * w, 0, w, h))
		else:
			for i in 5:
				var k := float(i) / 4.0
				draw_arc(Vector2(0, -10.0 - 50.0 * k), raio * (0.3 + 0.7 * k), 0.0, TAU, 32, Color(pal[1], 0.5 * apaga), 3.0)
		# bolhas: sobem em espiral e estouram em cima (miolo claro + contorno)
		for i in 7:
			var f := fmod(t * 0.9 + float(i) / 7.0, 1.0)
			var ang := t * 5.0 + TAU * i / 7.0
			var r := raio * (0.7 - 0.45 * f)
			var p := Vector2(cos(ang) * r, -f * raio * 1.1 + sin(ang) * r * 0.3)
			var tam := 3.0 + 3.0 * (1.0 - f)
			draw_circle(p, tam + 1.2, Color(pal[2], 0.6 * apaga))
			draw_circle(p, tam, Color(pal[1], 0.9 * apaga))
			draw_circle(p + Vector2(-tam * 0.35, -tam * 0.35), tam * 0.4, Color(pal[0], apaga))
