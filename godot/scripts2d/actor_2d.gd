extends CharacterBody2D
## Base de jogador e inimigos: sprite animado por direção, sombra, flash de dano.

const SpriteLoader = preload("res://scripts2d/sprite_loader.gd")

var char_id := ""
var facing := Vector2.DOWN
var sprite: AnimatedSprite2D
var shadow_radius := 18.0
var _anim_base := ""
var _flash := 0.0

func setup_sprite(id: String) -> void:
	char_id = id
	sprite = AnimatedSprite2D.new()
	sprite.sprite_frames = SpriteLoader.frames_for(id)
	sprite.offset = SpriteLoader.info(id)["offset"]
	add_child(sprite)
	sprite.frame_changed.connect(_on_frame_changed)
	sprite.animation_finished.connect(_on_anim_finished)

func has_anim(base: String) -> bool:
	return sprite.sprite_frames.has_animation("%s_0" % base)

## Toca a animação `base` na direção de `facing`. Mantém o quadro ao só trocar de direção.
func play(base: String, restart := false) -> void:
	if not has_anim(base):
		return
	var d := SpriteLoader.dir_for(facing, SpriteLoader.info(char_id)["dirs"])
	sprite.flip_h = d[1]
	var nome := "%s_%d" % [base, d[0]]
	if base == _anim_base and not restart:
		if sprite.animation != nome:
			var q := sprite.frame
			var p := sprite.frame_progress
			sprite.play(nome)
			sprite.set_frame_and_progress(q, p)
		elif not sprite.is_playing() and sprite.sprite_frames.get_animation_loop(nome):
			sprite.play(nome)
		return
	_anim_base = base
	sprite.play(nome)

## Quadro da animação em que o golpe/tiro acontece (coluna evento_quadro do manifesto).
func evento(base: String) -> int:
	return SpriteLoader.info(char_id)["evento"].get(base, 0)

func escala_sprite() -> float:
	return float(SpriteLoader.info(char_id)["lado"]) / 128.0

func anim_base() -> String:
	return _anim_base

func flash() -> void:
	_flash = 0.12

func _process(delta: float) -> void:
	if _flash > 0.0:
		_flash -= delta
		modulate = Color(2.0, 2.0, 2.0) if _flash > 0.0 else Color.WHITE
	queue_redraw()

func _draw() -> void:
	draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.4))
	draw_circle(Vector2.ZERO, shadow_radius, Color(0, 0, 0, 0.4))

func _on_frame_changed() -> void:
	pass

func _on_anim_finished() -> void:
	pass
