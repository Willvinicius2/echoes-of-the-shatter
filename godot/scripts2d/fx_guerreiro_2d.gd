extends RefCounted
## Efeitos em pixel art das habilidades do Guerreiro: folhas desenhadas por código (tools/arte/fx_guerreiro/gerar.py)
## em art2d/fx/guerreiro/, com o catálogo (quadros, tamanho, fps, âncora) em catalogo.json. Cada efeito vira um
## AnimatedSprite2D com filtro Nearest; a âncora do catálogo fica na posição pedida e o giro é em volta dela.
## `ESCALA` é a do mundo (1 px da arte = 1 px da grade, como os atores).

const DIR := "res://art2d/fx/guerreiro/"
const ESCALA := 2.5

static var _cat := {}
static var _frames := {}

static func catalogo() -> Dictionary:
	if _cat.is_empty() and FileAccess.file_exists(DIR + "catalogo.json"):
		var j = JSON.parse_string(FileAccess.get_file_as_string(DIR + "catalogo.json"))
		if typeof(j) == TYPE_DICTIONARY:
			_cat = j
	return _cat

static func existe(id: String) -> bool:
	return catalogo().has(id) and ResourceLoader.exists(DIR + id + ".png")

## Medida de referência do desenho em px da arte (raio do corte, comprimento da fenda...), para o chamador escalar
## o efeito pelo alcance real da habilidade.
static func ref(id: String) -> float:
	return float(catalogo().get(id, {}).get("ref", 1.0))

static func frames(id: String) -> SpriteFrames:
	if _frames.has(id):
		return _frames[id]
	var c: Dictionary = catalogo()[id]
	var tex: Texture2D = load(DIR + id + ".png")
	var sf := SpriteFrames.new()
	sf.set_animation_loop("default", bool(c.get("loop", false)))
	sf.set_animation_speed("default", float(c["fps"]))
	for i in int(c["n"]):
		var at := AtlasTexture.new()
		at.atlas = tex
		at.region = Rect2(float(i * int(c["w"])), 0.0, float(c["w"]), float(c["h"]))
		sf.add_frame("default", at)
	_frames[id] = sf
	return sf

## Cria o sprite (sem pôr na cena). `tam` = tamanho no mundo da medida de referência (0 = escala do mundo).
## Sem a folha devolve um Node2D vazio, para a regra da habilidade seguir sem o desenho.
static func criar(id: String, tam := 0.0, rot := 0.0, cor := Color.WHITE) -> Node2D:
	if not existe(id):
		return Node2D.new()
	var c: Dictionary = catalogo()[id]
	var s := AnimatedSprite2D.new()
	s.sprite_frames = frames(id)
	s.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	s.centered = false
	s.offset = -Vector2(float(c["ax"]), float(c["ay"]))
	var e: float = tam / maxf(ref(id), 1.0) if tam > 0.0 else ESCALA
	s.scale = Vector2(e, e)
	s.rotation = rot
	s.modulate = cor
	s.play("default")
	return s

## Toca no mundo; o que não repete some sozinho ao fim (o que repete fica com quem chamou).
static func tocar(cena: Node, id: String, pos: Vector2, tam := 0.0, rot := 0.0, cor := Color.WHITE, z := 4) -> Node2D:
	var s := criar(id, tam, rot, cor)
	s.z_index = z
	cena.add_child(s)
	s.global_position = pos
	if s is AnimatedSprite2D:
		if not s.sprite_frames.get_animation_loop("default"):
			s.animation_finished.connect(s.queue_free)
	else:
		s.queue_free()
	return s
