extends RefCounted
## Regras visuais comuns aos efeitos das habilidades (docs/arte/33_direcao_vfx_habilidades.md):
## saída do tiro no arco por direção, flash de boca e recuo, aura no chão atrás do ator, sombra de aviso de
## queda e orçamento de efeitos animados. As quatro árvores do Arqueiro e as outras classes usam daqui,
## em vez de cada uma inventar posição, camada e alfa.

const Csv = preload("res://scripts2d/csv2d.gd")
const SpriteLoader = preload("res://scripts2d/sprite_loader.gd")
const Feel = preload("res://scripts2d/feel_2d.gd")

const SAIDAS := "res://data2d/saidas_2d.csv"
const ALTURA_PEITO := Vector2(0, -30)   # altura padrão do desenho do projétil (arrow_2d.gd)
const GRUPO_ANIMADOS := "fx_animados"

static var _saidas := {}   # id -> {linha: Vector2}

## Ponto de saída do projétil (px a partir do pé do ator), já espelhado e na escala do sprite.
## Vem de `saidas_2d.csv` pela linha da folha na direção `facing`; sem linha, cai no antigo "pé + 36 px na mira".
static func saida_local(ator: Node2D) -> Vector2:
	var id: String = str(ator.get("char_id"))
	var facing: Vector2 = ator.get("facing") if ator.get("facing") != null else Vector2.DOWN
	if facing == Vector2.ZERO:
		facing = Vector2.DOWN
	var tabela: Dictionary = _tabela(id)
	if tabela.is_empty():
		return ALTURA_PEITO + facing.normalized() * 36.0
	var d: Array = SpriteLoader.dir_for(facing, SpriteLoader.info(id)["dirs"])
	var p: Vector2 = tabela.get(int(d[0]), ALTURA_PEITO)
	if d[1]:
		p.x = -p.x
	var esc: float = ator.escala_sprite() if ator.has_method("escala_sprite") else 1.0
	return p * esc

static func saida_global(ator: Node2D) -> Vector2:
	return ator.global_position + saida_local(ator)

## Faz o projétil `f` (arrow_2d.gd, com o nó `vis`) nascer desenhado na boca do arco e convergir à altura
## padrão em `fx_saida_tempo` s. A colisão continua na trilha do chão: só o desenho sai do arco.
static func lancar_do_arco(ator: Node2D, f: Node) -> void:
	if f == null or f.get("vis") == null:
		return
	var vis: Node2D = f.vis
	var alvo := ALTURA_PEITO
	vis.position = alvo + (saida_global(ator) - (f.global_position + alvo))
	var t: float = float(Feel.cfg().get("fx_saida_tempo", 0.12))
	var tw := vis.create_tween()
	tw.tween_property(vis, "position", alvo, t).set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_QUAD)

## Flash de 2 quadros na boca do arco e recuo do sprite de 3 px contra a mira.
static func flash_boca(ator: Node2D, dir: Vector2, cor: Color) -> void:
	var c := Feel.cfg()
	var p := Sprite2D.new()
	p.texture = Feel.ponto()
	p.material = Feel.aditivo()
	p.position = saida_local(ator)
	p.z_index = 4
	var esc: float = float(c.get("fx_flash_boca_escala", 0.7))
	p.scale = Vector2(esc * 1.4, esc)
	p.rotation = dir.angle()
	p.modulate = Color(cor.r, cor.g, cor.b, 0.9)
	ator.add_child(p)
	var tw := p.create_tween()
	tw.tween_property(p, "scale", Vector2.ZERO, float(c.get("fx_flash_boca_tempo", 0.07)))
	tw.tween_callback(p.queue_free)
	var sprite: Node2D = ator.get("sprite")
	if sprite != null:
		var rec: float = float(c.get("fx_recuo_px", 3.0))
		sprite.position = -dir.normalized() * rec
		var tr := sprite.create_tween()
		tr.tween_property(sprite, "position", Vector2.ZERO, float(c.get("fx_recuo_tempo", 0.08)))

## Aura de Herald: elipse no chão, aos pés, desenhada atrás do ator (camada C1), alfa limitado.
## `no` é o sprite/animação da árvore; esta função só o coloca na camada e na posição certas.
static func aura_chao(ator: Node2D, no: Node2D) -> Node2D:
	var c := Feel.cfg()
	no.position = Vector2(0, float(c.get("fx_aura_altura", -4.0)))
	no.scale = Vector2(1.0, float(c.get("fx_aura_achatamento", 0.5)))
	no.show_behind_parent = true
	no.z_index = 0
	no.modulate.a = minf(no.modulate.a, float(c.get("fx_aura_alfa_max", 0.45)))
	no.add_to_group("fx_aura")
	if no.get_parent() == null:
		ator.add_child(no)
	return no

## Acende a aura por um instante (gatilho do Herald disparou) e volta ao alfa de antes.
static func pulsar_aura(no: Node2D) -> void:
	if no == null or not is_instance_valid(no):
		return
	var a := no.modulate.a
	var tw := no.create_tween()
	tw.tween_property(no, "modulate:a", minf(a + 0.3, 0.8), 0.05)
	tw.tween_property(no, "modulate:a", a, 0.25)

## Sombra de aviso no chão (camada C0): círculo escuro com anel da cor do elemento que cresce até o `raio`
## em `tempo` s, para o jogador ler onde a queda ou a zona vai acontecer. Some sozinha logo depois.
static func sombra_aviso(pai: Node, pos: Vector2, raio: float, cor: Color, tempo: float) -> Node2D:
	var s := Aviso.new()
	s.raio = raio
	s.cor = cor
	s.alfa = float(Feel.cfg().get("fx_aviso_alfa", 0.35))
	s.z_index = -1
	s.global_position = pos
	s.scale = Vector2.ONE * 0.35
	pai.add_child(s)
	var tw := s.create_tween()
	tw.tween_property(s, "scale", Vector2.ONE, maxf(tempo, 0.05)).set_ease(Tween.EASE_OUT)
	tw.tween_interval(0.2)
	tw.tween_property(s, "modulate:a", 0.0, 0.15)
	tw.tween_callback(s.queue_free)
	return s

class Aviso extends Node2D:
	var raio := 40.0
	var cor := Color.WHITE
	var alfa := 0.35
	func _draw() -> void:
		draw_circle(Vector2.ZERO, raio, Color(0, 0, 0, alfa))
		draw_arc(Vector2.ZERO, raio, 0.0, TAU, 40, Color(cor.r, cor.g, cor.b, 0.8), 2.0)
		draw_arc(Vector2.ZERO, raio * 0.15, 0.0, TAU, 12, Color(cor.r, cor.g, cor.b, 0.6), 1.5)

## Orçamento de efeitos animados em tela (doc 33, seção 4). Quem cria um efeito animado o registra;
## quando passa de `fx_max_animados`, os novos devem nascer na versão curta (só 1º e último quadro).
static func registrar_animado(no: Node) -> void:
	no.add_to_group(GRUPO_ANIMADOS)

static func lotado(tree: SceneTree) -> bool:
	if tree == null:
		return false
	return tree.get_nodes_in_group(GRUPO_ANIMADOS).size() >= int(Feel.cfg().get("fx_max_animados", 24))

static func _tabela(id: String) -> Dictionary:
	if _saidas.is_empty():
		for r in Csv.rows(SAIDAS):
			var k: String = r["id"]
			if not _saidas.has(k):
				_saidas[k] = {}
			_saidas[k][int(r["linha"])] = Vector2(float(r["x"]), float(r["y"]))
	return _saidas.get(id, {})
