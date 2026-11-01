extends RefCounted
## Árvore de VENENO do Arqueiro (doc 32_veneno.md). Todos os números chegam em `def` (linha de
## data2d/habilidades_arqueiro.csv, já escalonada pelo nível); aqui não há balanceamento.
## Entrada: `executar(efeito, jogador, def, nivel, mira)` com efeito = tiro_veneno | bola_veneno | chuva_corrosiva.
## Gancho do Herald: `arauto_peste_morte(inimigo, def)`. A integradora liga os dois em efeitos_arqueiro_2d.gd.

const Feel = preload("res://scripts2d/feel_2d.gd")
const Vfx = preload("res://scripts2d/vfx_2d.gd")
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
