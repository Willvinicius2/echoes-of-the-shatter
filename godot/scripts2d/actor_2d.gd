extends CharacterBody2D
## Base de jogador e inimigos: sprite animado por direção, sombra, flash de dano.

const SpriteLoader = preload("res://scripts2d/sprite_loader.gd")
const Feel = preload("res://scripts2d/feel_2d.gd")

var char_id := ""
var facing := Vector2.DOWN
var sprite: AnimatedSprite2D
var shadow_radius := 18.0
var _anim_base := ""
var _flash := 0.0
var _fase_respiro := randf() * TAU  # fase própria: atores juntos não respiram em uníssono
var _shake_t := 0.0
var _shake_total := 0.0
var _shake_px := 0.0
var _mat: ShaderMaterial     # flash branco, dissolução e brilho do sprite
var _morrendo := false
var _flash_ligado := false
var _dir_k := -1
var _sombra_a := 1.0
var _recuo := Vector2.ZERO   # recuo do sprite ao disparar (doc 33 seção 2): só o desenho, a colisão não muda
var _recuo_t := 0.0
var _recuo_total := 0.0

func setup_sprite(id: String) -> void:
	char_id = id
	sprite = AnimatedSprite2D.new()
	sprite.sprite_frames = SpriteLoader.frames_for(id)
	sprite.offset = SpriteLoader.info(id)["offset"]
	_mat = Feel.material_ator()
	sprite.material = _mat
	add_child(sprite)
	sprite.frame_changed.connect(_on_frame_changed)
	sprite.animation_finished.connect(_on_anim_finished)

func has_anim(base: String) -> bool:
	return sprite.sprite_frames.has_animation("%s_0" % base)

## Toca a animação `base` na direção de `facing`. Mantém o quadro ao só trocar de direção.
func play(base: String, restart := false) -> void:
	var k := posmod(int(round(facing.angle() / (PI / 4.0))), 8)
	if not restart and k == _dir_k and base == _anim_base and sprite.is_playing():
		return   # caminho rápido: mesma animação e direção, nada a trocar
	if not has_anim(base):
		return
	_dir_k = k
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
	_flash = Feel.cfg()["flash_time"]

## Treme só o sprite (a colisão não muda), decaindo até zero em `tempo` s.
func tremer_sprite(px: float, tempo: float) -> void:
	_shake_px = px
	_shake_t = tempo
	_shake_total = tempo

## Recua o sprite `px` contra `dir` e volta em `tempo` s (coice do arco). Soma-se ao tremor.
func recuar_sprite(dir: Vector2, px: float, tempo: float) -> void:
	if px <= 0.0 or tempo <= 0.0:
		return
	_recuo = -dir.normalized() * px
	_recuo_t = tempo
	_recuo_total = tempo

## Dissolve o sprite em pixels e some com a sombra; depois remove o ator.
func dissolver(tempo: float) -> void:
	if _morrendo:
		return
	_morrendo = true
	var tw := create_tween()
	tw.tween_method(func(v: float) -> void:
		_mat.set_shader_parameter("dissolve", v)
		_sombra_a = 1.0 - v, 0.0, 1.0, tempo)
	tw.tween_callback(queue_free)


func _process(delta: float) -> void:
	if _mat != null:
		if _flash > 0.0:
			_flash -= delta
		var ligado := _flash > 0.0
		if ligado != _flash_ligado:   # só fala com o shader quando o flash liga ou desliga
			_flash_ligado = ligado
			_mat.set_shader_parameter("flash", 0.7 if ligado else 0.0)
	if sprite != null:
		var desloc := Vector2.ZERO
		if _shake_t > 0.0:
			_shake_t -= delta
			desloc = Vector2.from_angle(randf() * TAU) * _shake_px * clampf(_shake_t / _shake_total, 0.0, 1.0)
		if _recuo_t > 0.0:
			_recuo_t -= delta
			desloc += _recuo * clampf(_recuo_t / _recuo_total, 0.0, 1.0)
		sprite.position = desloc
		_respirar(delta)
	if _precisa_redesenhar():
		queue_redraw()

## O desenho só muda em casos pontuais (aviso, barra de vida, sombra sumindo): redesenhar todo quadro
## custa caro com centenas de atores. Quem tem desenho animado sobrescreve.
func _precisa_redesenhar() -> bool:
	return true

## Respiração do idle por código (os quadros da folha mal mudam): o corpo estica de 2 a 3 px a partir dos pés.
func _respirar(delta: float) -> void:
	if _anim_base == "idle":
		_fase_respiro += delta * 2.4
		var r := sin(_fase_respiro)
		var k := 1.0 / escala_sprite()  # sprite maior (chefe) respira a mesma quantidade de px, não a mesma fração
		sprite.scale = Vector2(1.0 - 0.012 * k * r, 1.0 + 0.026 * k * r)
	elif sprite.scale != Vector2.ONE:
		sprite.scale = Vector2.ONE

func _draw() -> void:
	draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.4))
	draw_circle(Vector2.ZERO, shadow_radius, Color(0, 0, 0, 0.4 * _sombra_a))

func _on_frame_changed() -> void:
	pass

func _on_anim_finished() -> void:
	pass
