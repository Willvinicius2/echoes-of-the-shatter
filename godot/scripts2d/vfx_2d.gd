extends RefCounted
## Ajudas visuais compartilhadas pelas árvores de habilidades (docs/arte/33_direcao_vfx_habilidades.md):
## aura de Herald na camada C1 (atrás do ator), flash de boca do arco, projétil em arco com sombra no chão e
## sombra de aviso no ponto de queda, anel de entrada de zona. Só regras visuais; os números ficam em data2d/feel.csv.

const Feel = preload("res://scripts2d/feel_2d.gd")
const Efeito = preload("res://scripts2d/efeito_2d.gd")

# ---------- camada C1: auras ----------

## Aura de Herald na camada C1 (seção 1 do doc 33): elipse no chão, aos pés, desenhada atrás do ator, achatada e com
## alfa limitado, igual para as quatro árvores (nunca sobre o corpo: no 3/4 uma aura no tronco lê como bolha).
## `no` é o desenho da árvore (sprite animado, quadros...) que ocupa `tam_natural` px na escala 1. Substitui a aura de
## mesmo `nome` se já houver. Devolve o nó, já filho do jogador.
static func aura_c1(jogador: Node2D, no: Node2D, tam_natural: float, nome: String) -> Node2D:
	var velho := jogador.get_node_or_null(nome)
	if velho != null:
		velho.name = nome + "_velha"   # libera o nome no mesmo quadro
		velho.queue_free()
	var c := Feel.cfg()
	no.name = nome
	no.position = Vector2(0, -c["aura_altura"])
	var k: float = c["aura_diametro"] / maxf(tam_natural, 1.0)
	no.scale = Vector2(k, k * c["aura_achatamento"])
	no.show_behind_parent = true
	no.z_index = 0
	no.modulate.a = minf(no.modulate.a, c["aura_alfa"])
	no.set_meta("aura_alfa", no.modulate.a)
	jogador.add_child(no)
	return no

## A aura acende por `aura_acende_tempo` s quando o gatilho do Herald dispara (tabela da seção 5 do doc 33).
static func aura_acender(jogador: Node2D, nome: String) -> void:
	var a := jogador.get_node_or_null(nome) as CanvasItem
	if a == null:
		return
	var base: float = a.get_meta("aura_alfa", a.modulate.a)
	var t: float = Feel.cfg()["aura_acende_tempo"]
	var tw := a.create_tween()
	tw.tween_property(a, "modulate:a", minf(1.0, base * 2.0), t * 0.3)
	tw.tween_property(a, "modulate:a", base, t * 0.7)

# ---------- origem do tiro ----------

## Flash de boca (seção 2): brilho curto no ponto do arco, girado na direção do tiro. A cor vem do projétil `fonte`
## um quadro depois (quando a árvore já pintou a flecha); sem fonte fica branco.
static func flash_boca(cena: Node, pos: Vector2, dir: Vector2, fonte: Node = null) -> void:
	if cena == null:
		return
	var f := FlashBoca.new()
	f.fonte = fonte
	f.rotation = dir.angle()
	cena.add_child(f)
	f.global_position = pos

class FlashBoca extends Sprite2D:
	var fonte: Node
	var _t := 0.0
	func _ready() -> void:
		texture = Feel.ponto()
		material = Feel.aditivo()
		z_index = 4
		var k: float = Feel.cfg()["muzzle_flash_scale"]
		scale = Vector2(k * 1.6, k)
		modulate = Color(1, 1, 1, 0.9)
		_pintar.call_deferred()
	func _pintar() -> void:
		if is_instance_valid(fonte) and fonte.has_method("cor_atual"):
			var c: Color = fonte.cor_atual()
			modulate = Color(c.r, c.g, c.b, modulate.a)
	func _process(delta: float) -> void:
		_t += delta
		var dur: float = Feel.cfg()["muzzle_flash_time"]
		if _t >= dur:
			queue_free()
			return
		modulate.a = 0.9 * (1.0 - _t / dur)
		scale *= 1.0 + 4.0 * delta   # abre um pouco enquanto some

# ---------- chão: sombra de aviso e projétil em arco ----------

## Sombra de aviso no ponto de queda (seção 2): círculo escuro com borda na cor do elemento que cresce de 35% a 100% do
## raio em `tempo` s (camada C0). Some sozinha pouco depois do tempo, ou antes com `concluir()`.
static func sombra_aviso(cena: Node, ponto: Vector2, raio: float, cor: Color, tempo: float) -> Node2D:
	var s := SombraAviso.new()
	s.raio = raio
	s.cor = cor
	s.tempo = maxf(tempo, 0.05)
	cena.add_child(s)
	s.global_position = ponto
	return s

class SombraAviso extends Node2D:
	var raio := 40.0
	var cor := Color.WHITE
	var tempo := 0.4
	var _t := 0.0
	var _saindo := false
	func _ready() -> void:
		z_index = -1
	func concluir() -> void:
		if _saindo:
			return
		_saindo = true
		var tw := create_tween()
		tw.tween_property(self, "modulate:a", 0.0, 0.12)
		tw.tween_callback(queue_free)
	func _process(delta: float) -> void:
		_t += delta
		if not _saindo and _t >= tempo + 0.25:
			concluir()
		queue_redraw()
	func _draw() -> void:
		var f := clampf(_t / tempo, 0.0, 1.0)
		var r := raio * (0.35 + 0.65 * f)
		var a: float = Feel.cfg()["arc_shadow_alpha"]
		draw_circle(Vector2.ZERO, r, Color(0, 0, 0, a * (0.5 + 0.5 * f)))
		draw_arc(Vector2.ZERO, r, 0.0, TAU, 40, Color(cor.r, cor.g, cor.b, 0.5 + 0.5 * f), 2.0)
		draw_arc(Vector2.ZERO, raio, 0.0, TAU, 40, Color(cor.r, cor.g, cor.b, 0.35), 1.0)   # contorno da área final

## Projétil em arco (bola de veneno, flecha que sobe e cai): o nó anda no chão de `origem` a `destino` em `voo` s e o
## `corpo` sobe em parábola até `altura_voo` px (sai rápido, pico de um quadro, cai acelerando), partindo de
## `altura_ini` (altura do arco). A sombra do corpo fica no chão e a sombra de aviso cresce em `destino` desde o
## disparo. Ao cair chama `ao_cair(destino)` e some. Com `gira`, o corpo aponta para onde está indo (flecha).
static func arco(cena: Node, origem: Vector2, altura_ini: float, destino: Vector2, altura_voo: float, voo: float,
		corpo: Node2D, cor: Color, raio_aviso: float, ao_cair: Callable, gira := false) -> Node2D:
	var p := ProjetilArco.new()
	p.origem = origem
	p.destino = destino
	p.altura_ini = altura_ini
	p.altura_voo = altura_voo
	p.voo = maxf(voo, 0.05)
	p.corpo = corpo
	p.cor = cor
	p.ao_cair = ao_cair
	p.gira = gira
	cena.add_child(p)
	p.global_position = origem
	if raio_aviso > 0.0:
		p.aviso = sombra_aviso(cena, destino, raio_aviso, cor, p.voo)
	return p

class ProjetilArco extends Node2D:
	var origem := Vector2.ZERO
	var destino := Vector2.ZERO
	var altura_ini := 0.0
	var altura_voo := 200.0
	var voo := 0.5
	var corpo: Node2D
	var cor := Color.WHITE
	var ao_cair := Callable()
	var gira := false
	var aviso: Node2D
	var _t := 0.0
	var _altura := 0.0
	func _ready() -> void:
		z_index = -1   # este nó desenha a sombra no chão (C0); o corpo vai para o "céu" (C5)
		if corpo != null:
			corpo.z_index = 6   # relativo ao pai: -1 + 6 = 5
			add_child(corpo)
		_altura = altura_ini
		_posicionar(0.0)
	func altura() -> float:
		return _altura
	func _posicionar(f: float) -> void:
		global_position = origem.lerp(destino, f)
		_altura = altura_ini * (1.0 - f) + altura_voo * 4.0 * f * (1.0 - f)
		if corpo != null:
			corpo.position = Vector2(0, -_altura)
	func _physics_process(delta: float) -> void:
		var antes := global_position + Vector2(0, -_altura)
		_t += delta
		var f := clampf(_t / voo, 0.0, 1.0)
		_posicionar(f)
		if gira and corpo != null:
			var v := (global_position + Vector2(0, -_altura)) - antes
			if v.length_squared() > 0.01:
				corpo.rotation = v.angle()
		queue_redraw()
		if f >= 1.0:
			if is_instance_valid(aviso) and aviso.has_method("concluir"):
				aviso.concluir()
			if ao_cair.is_valid():
				ao_cair.call(destino)
			queue_free()
	func _draw() -> void:   # sombra do corpo no chão: encolhe e clareia conforme sobe
		var k := clampf(1.0 - _altura / maxf(altura_voo + altura_ini, 1.0), 0.25, 1.0)
		draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.45))
		draw_circle(Vector2.ZERO, 11.0 * k, Color(0, 0, 0, 0.35 * k))

# ---------- orçamento de efeitos (seção 4) ----------

const GRUPO_ANIMADOS := "fx_animados"

## Quem cria um efeito animado o registra; passado `fx_max_animados`, os novos nascem na versão curta (1º e último quadro).
static func registrar_animado(no: Node) -> void:
	no.add_to_group(GRUPO_ANIMADOS)

static func lotado(tree: SceneTree) -> bool:
	if tree == null:
		return false
	return tree.get_nodes_in_group(GRUPO_ANIMADOS).size() >= int(Feel.cfg().get("fx_max_animados", 24))

## Decalques de chão (poças, brasas, rachaduras; doc 36 seção 7): teto global `fx_max_decalques`. Quem deixa marca no
## chão registra o nó aqui; quando lotou, marcas novas não nascem e as existentes somem em fade.
const GRUPO_DECAIS := "fx_decalques"

static func registrar_decalque(no: Node) -> void:
	no.add_to_group(GRUPO_DECAIS)

static func decalque_cabe(tree: SceneTree) -> bool:
	if tree == null:
		return true
	return tree.get_nodes_in_group(GRUPO_DECAIS).size() < int(Feel.cfg().get("fx_max_decalques", 12))

## Overlays de status sobre inimigos (frio, veneno, queimadura; doc 36 seção 6.1): teto global `fx_max_status`.
## Quando lotou, o status nasce na versão pequena (ícone sobre a cabeça) em vez do anel/nuvem em volta do corpo.
const GRUPO_STATUS := "fx_status_overlays"

static func registrar_status(no: Node) -> void:
	no.add_to_group(GRUPO_STATUS)

static func status_cabe(tree: SceneTree) -> bool:
	if tree == null:
		return true
	return tree.get_nodes_in_group(GRUPO_STATUS).size() < int(Feel.cfg().get("fx_max_status", 6))

# ---------- zonas ----------

## Anel de entrada de uma zona (seção 2: nascem com anel de 0,15 s), na cor do elemento.
static func anel_entrada(cena: Node, pos: Vector2, raio: float, cor: Color) -> void:
	if cena == null:
		return
	Efeito.anel(cena, pos, raio, cor, Feel.cfg()["zone_ring_time"])

## Fator 0..1 para apagar uma zona nos últimos `zone_fade_time` s (nunca some de uma vez).
static func fade_zona(t: float, duracao: float) -> float:
	var f: float = Feel.cfg()["zone_fade_time"]
	return clampf((duracao - t) / maxf(f, 0.01), 0.0, 1.0)
