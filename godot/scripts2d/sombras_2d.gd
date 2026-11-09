extends Node2D
## Sombras de chão de todos os inimigos num único MultiMesh (uma draw call), em vez de um círculo desenhado
## por inimigo, que quebrava o lote de sprites (sombra, sprite, sombra, sprite...). Fica logo abaixo dos atores.
## Registro: o inimigo chama `Sombras.registrar(self)` ao nascer e `Sombras.remover(self)` ao sair da árvore.

const MAX_INICIAL := 512

static var _instancia: Node2D = null
static var _tex: Texture2D = null

var _mm: MultiMesh
var _reg := {}   # inimigo -> true
var _cap := 0

## Devolve true se a sombra do inimigo passa a ser desenhada aqui (precisa estar na árvore, dentro dos atores).
static func registrar(e: Node2D) -> bool:
	if not e.is_inside_tree() or e.get_parent() == null or e.get_parent().get_parent() == null:
		return false
	if _instancia == null or not is_instance_valid(_instancia) or not _instancia.is_inside_tree() \
			or _instancia.get_parent() != e.get_parent().get_parent():
		var atores := e.get_parent()
		var run := atores.get_parent()
		_instancia = (load("res://scripts2d/sombras_2d.gd") as GDScript).new()
		run.add_child(_instancia)
		run.move_child(_instancia, atores.get_index())   # logo antes dos atores: sob todos eles
	_instancia._reg[e] = true
	return true

static func remover(e: Node2D) -> void:
	if _instancia != null and is_instance_valid(_instancia):
		_instancia._reg.erase(e)

static func _textura() -> Texture2D:
	if _tex == null:
		var lado := 64
		var img := Image.create(lado, lado, false, Image.FORMAT_RGBA8)
		var c := (lado - 1) / 2.0
		for y in lado:
			for x in lado:
				var d := Vector2(x - c, y - c).length() / (lado / 2.0)
				img.set_pixel(x, y, Color(1, 1, 1, clampf((1.0 - d) * lado / 2.0, 0.0, 1.0)))   # borda suave de ~1 px
		_tex = ImageTexture.create_from_image(img)
	return _tex

func _ready() -> void:
	texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	var mmi := MultiMeshInstance2D.new()
	mmi.texture = _textura()
	_mm = MultiMesh.new()
	_mm.transform_format = MultiMesh.TRANSFORM_2D
	_mm.use_colors = true
	var q := QuadMesh.new()
	q.size = Vector2(2, 2)   # raio 1: a escala por inimigo dá o raio
	_mm.mesh = q
	_realocar(MAX_INICIAL)
	mmi.multimesh = _mm
	add_child(mmi)

func _realocar(n: int) -> void:
	_cap = n
	_mm.instance_count = 0
	_mm.use_colors = true
	_mm.instance_count = n
	_mm.visible_instance_count = 0

func _process(_delta: float) -> void:
	var n := _reg.size()
	if n > _cap:
		_realocar(maxi(n, _cap * 2))
	var i := 0
	for e in _reg:
		if not is_instance_valid(e):
			continue
		var r: float = e.shadow_radius
		_mm.set_instance_transform_2d(i, Transform2D(Vector2(r, 0.0), Vector2(0.0, r * 0.4), e.global_position))
		_mm.set_instance_color(i, Color(0, 0, 0, 0.4 * e._sombra_a))
		i += 1
	_mm.visible_instance_count = i
