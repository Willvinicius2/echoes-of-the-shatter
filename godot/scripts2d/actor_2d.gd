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
## true: o sprite só tem material próprio enquanto o flash ou a dissolução estão ativos (sai de um pool).
## Sem material próprio todos os inimigos do mesmo tipo desenham juntos, num lote só; com 500 em tela, um
## material por inimigo quebrava o lote e multiplicava as draw calls. O chefe e o jogador mantêm o fixo.
var _mat_sob_demanda := false
static var _pool_mat: Array[ShaderMaterial] = []
var _desloc_ant := Vector2.ZERO
var _morrendo := false
var _flash_ligado := false
var _dir_k := -1
var _esc_base := 1.0   # escala de mundo do sprite (sprites_escala.csv)
var escala_extra := 1.0   # multiplica a escala do sprite (elite do portão); a colisão é ajustada por quem muda isto
var _sombra_a := 1.0
var _recuo := Vector2.ZERO   # recuo do sprite ao disparar (doc 33 seção 2): só o desenho, a colisão não muda
var _recuo_t := 0.0
var _recuo_total := 0.0

func setup_sprite(id: String) -> void:
	char_id = id
	sprite = AnimatedSprite2D.new()
	sprite.sprite_frames = SpriteLoader.frames_for(id)
	sprite.offset = SpriteLoader.info(id)["offset"]
	_esc_base = float(SpriteLoader.info(id)["escala"])
	sprite.scale = Vector2(_esc_base, _esc_base)
	if not _mat_sob_demanda:
		_mat = Feel.material_ator()
		sprite.material = _mat
	add_child(sprite)
	sprite.frame_changed.connect(_on_frame_changed)
	sprite.animation_finished.connect(_on_anim_finished)

## Troca a folha do sprite por outra do manifesto (elite: `<id>_elite`, re-renderizada maior na grade nativa, sem esticar
## pixel). Devolve false e não muda nada se a folha não existe.
func usar_arte(id: String) -> bool:
	if sprite == null or not bool(SpriteLoader.info(id)["tem_arquivo"]):
		return false
	char_id = id
	sprite.sprite_frames = SpriteLoader.frames_for(id)
	sprite.offset = SpriteLoader.info(id)["offset"]
	_esc_base = float(SpriteLoader.info(id)["escala"])
	sprite.scale = Vector2(_esc_base, _esc_base) * escala_extra
	return true

func has_anim(base: String) -> bool:
	return sprite.sprite_frames.has_animation("%s_0" % base)

## Toca a animação `base` na direção de `facing`. Mantém o quadro ao só trocar de direção.
func play(base: String, restart := false) -> void:
	var k := posmod(int(round(facing.angle() / (PI / 4.0))), 8)
	if _dir_k >= 0 and k != _dir_k and not restart:
		# histerese: perto da fronteira entre dois setores mantém o antigo (até 12 graus além), sem piscar
		var centro := float(_dir_k) * PI / 4.0
		if absf(angle_difference(centro, facing.angle())) < PI / 8.0 + deg_to_rad(12.0):
			k = _dir_k
	if not restart and k == _dir_k and base == _anim_base and sprite.is_playing():
		return   # caminho rápido: mesma animação e direção, nada a trocar
	if not has_anim(base):
		return
	if _mat_sob_demanda:
		set_process(true)   # troca de animação: o _process confere o redesenho e volta a dormir
	_dir_k = k
	var d := SpriteLoader.dir_for(Vector2.from_angle(float(k) * PI / 4.0), SpriteLoader.info(char_id)["dirs"])
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
	return float(SpriteLoader.info(char_id)["lado"]) * float(SpriteLoader.info(char_id)["escala"]) / 128.0

## Altura do topo do desenho acima do pé, em px de mundo (negativa): barra de vida e números de dano. Sprite em pixel art
## (escala do CSV != 1) usa o pivô da arte vezes a escala atual; os HD antigos seguem a fórmula de sempre.
func topo_visual() -> float:
	var inf := SpriteLoader.info(char_id)
	if inf["tem_arquivo"] and _esc_base != 1.0:
		return -(float(inf["lado"]) * 0.5 - float(inf["offset"].y)) * sprite.scale.x * 0.88
	return -90.0 * escala_sprite() * escala_extra

func anim_base() -> String:
	return _anim_base

func flash() -> void:
	_flash = Feel.cfg()["flash_time"]
	set_process(true)

## Pega um material do pool (ou cria) com os parâmetros zerados e liga no sprite.
func _pegar_mat() -> void:
	if _mat != null:
		return
	if _pool_mat.is_empty():
		_mat = Feel.material_ator()
	else:
		_mat = _pool_mat.pop_back()
	_mat.set_shader_parameter("flash", 0.0)
	_mat.set_shader_parameter("dissolve", 0.0)
	sprite.material = _mat

## Devolve o material ao pool e deixa o sprite com o material padrão (entra no lote).
func _soltar_mat() -> void:
	if _mat == null or not _mat_sob_demanda or _morrendo:
		return
	_mat.set_shader_parameter("flash", 0.0)
	sprite.material = null
	_pool_mat.append(_mat)
	_mat = null

## Treme só o sprite (a colisão não muda), decaindo até zero em `tempo` s.
func tremer_sprite(px: float, tempo: float) -> void:
	_shake_px = px
	set_process(true)
	_shake_t = tempo
	_shake_total = tempo

## Recua o sprite `px` contra `dir` e volta em `tempo` s (coice do arco). Soma-se ao tremor.
func recuar_sprite(dir: Vector2, px: float, tempo: float) -> void:
	if px <= 0.0 or tempo <= 0.0:
		return
	_recuo = -dir.normalized() * px
	set_process(true)
	_recuo_t = tempo
	_recuo_total = tempo

## Dissolve o sprite em pixels e some com a sombra; depois remove o ator.
func dissolver(tempo: float) -> void:
	if _morrendo:
		return
	_morrendo = true
	set_process(true)
	_pegar_mat()
	var tw := create_tween()
	tw.tween_method(func(v: float) -> void:
		_mat.set_shader_parameter("dissolve", v)
		_sombra_a = 1.0 - v, 0.0, 1.0, tempo)
	tw.tween_callback(queue_free)


func _process(delta: float) -> void:
	if _mat != null or _mat_sob_demanda:
		if _flash > 0.0:
			_flash -= delta
		var ligado := _flash > 0.0
		if ligado != _flash_ligado:   # só fala com o shader quando o flash liga ou desliga
			_flash_ligado = ligado
			if ligado:
				_pegar_mat()
				_mat.set_shader_parameter("flash", float(Feel.cfg().get("flash_amount", 0.5)))
			elif _mat != null:
				_mat.set_shader_parameter("flash", 0.0)
				_soltar_mat()
	if sprite != null:
		var desloc := Vector2.ZERO
		if _shake_t > 0.0:
			_shake_t -= delta
			desloc = Vector2.from_angle(randf() * TAU) * _shake_px * clampf(_shake_t / _shake_total, 0.0, 1.0)
		if _recuo_t > 0.0:
			_recuo_t -= delta
			desloc += _recuo * clampf(_recuo_t / _recuo_total, 0.0, 1.0)
		if desloc != _desloc_ant or not _mat_sob_demanda:   # mexer na posição do filho todo quadro invalida o transform à toa
			_desloc_ant = desloc
			sprite.position = desloc
		if char_id == "arqueiro" and _anim_base == "run":
			# quique do passo (a folha quase não move o corpo): sobe 1 px da folha em cada apoio de pé
			sprite.position.y = desloc.y - (sprite.scale.y if sprite.frame % 3 == 1 else 0.0)
		_respirar(delta)
	if _precisa_redesenhar():
		queue_redraw()
	elif _mat_sob_demanda and _flash <= 0.0 and _shake_t <= 0.0 and _recuo_t <= 0.0 and not _morrendo 			and _anim_base != "idle" and _flash_ligado == false:
		set_process(false)   # nada animado por código: acorda de novo por evento (golpe, troca de animação)

## O desenho só muda em casos pontuais (aviso, barra de vida, sombra sumindo): redesenhar todo quadro
## custa caro com centenas de atores. Quem tem desenho animado sobrescreve.
func _precisa_redesenhar() -> bool:
	return true

## Respiração do idle por código (os quadros da folha mal mudam): o corpo estica de 2 a 3 px a partir dos pés.
func _respirar(delta: float) -> void:
	if _esc_base != 1.0:
		# pixel art na grade: 1 px do sprite = 1 px da grade, então a escala é 1 / zoom da câmera (esticar pisca;
		# a respiração vem dos quadros da folha)
		var vp := get_viewport()
		var cam := vp.get_camera_2d() if vp is SubViewport else null   # só o mundo de pixel art (SubViewport) escala por 1/zoom
		var e := (_esc_base if cam == null else 1.0 / maxf(cam.zoom.x, 0.05)) * escala_extra   # fora do SubViewport (testes, modo normal), fica na escala do CSV
		if absf(sprite.scale.x - e) > 0.001:
			sprite.scale = Vector2(e, e)
		return
	var base := _esc_base * escala_extra
	if _anim_base == "idle":
		_fase_respiro += delta * 2.4
		var r := sin(_fase_respiro)
		var k := 1.0 / escala_sprite()  # sprite maior (chefe) respira a mesma quantidade de px, não a mesma fração
		sprite.scale = Vector2(1.0 - 0.012 * k * r, 1.0 + 0.026 * k * r) * base
	elif sprite.scale != Vector2(base, base):
		sprite.scale = Vector2(base, base)

var _sombra_externa := false   # true: a sombra é desenhada pelo sombras_2d.gd (MultiMesh)

func _draw() -> void:
	if _sombra_externa:
		return
	draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.4))
	draw_circle(Vector2.ZERO, shadow_radius, Color(0, 0, 0, 0.4 * _sombra_a))

func _on_frame_changed() -> void:
	pass

func _on_anim_finished() -> void:
	pass
