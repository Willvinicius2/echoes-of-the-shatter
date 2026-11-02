extends RefCounted
## VFX em pixel art (folhas do patch-gg/pixelfx, MIT, geradas por tools/arte/fx_pixel/gerar_folhas.py; licença em
## art2d/fx/pixel/LICENSE-pixelfx.txt). Cada folha é uma grade de quadros já cortados pela caixa de conteúdo; aqui viram
## AnimatedSprite2D com filtro Nearest (nunca suavizar pixel art). Custo de runtime: um sprite animado por efeito.
## Âncoras: "base" = pé do efeito (meio da borda de baixo), "centro", "ponta" = meio da borda esquerda (efeito que sai de um ponto, apontando para a direita).

const DIR := "res://art2d/fx/pixel/"
const CATALOGO := {
	"thunderclap": {"n": 24, "w": 253, "h": 131, "cols": 4, "fps": 12.0},
	"storm_cloud": {"n": 36, "w": 154, "h": 170, "cols": 7, "fps": 12.0},
	"lightning_strike": {"n": 14, "w": 124, "h": 236, "cols": 6, "fps": 12.0},
	"ball_lightning": {"n": 48, "w": 116, "h": 89, "cols": 7, "fps": 12.0},
	"spore_burst": {"n": 39, "w": 99, "h": 105, "cols": 7, "fps": 12.0},
	"poison_cloud": {"n": 48, "w": 212, "h": 53, "cols": 4, "fps": 12.0},
	"acid_splash": {"n": 35, "w": 111, "h": 93, "cols": 6, "fps": 12.0},
	"ice_lance": {"n": 10, "w": 136, "h": 30, "cols": 2, "fps": 12.0},
	"ice_spikes": {"n": 37, "w": 257, "h": 88, "cols": 4, "fps": 12.0},
	"blizzard_vortex": {"n": 24, "w": 94, "h": 109, "cols": 6, "fps": 12.0},
	"fire_breath": {"n": 18, "w": 146, "h": 101, "cols": 4, "fps": 12.0},
	"fire_ring": {"n": 48, "w": 202, "h": 105, "cols": 5, "fps": 12.0},
	"barrel_explosion": {"n": 16, "w": 220, "h": 177, "cols": 4, "fps": 12.0},
}

static var _frames := {}

static func existe(id: String) -> bool:
	return CATALOGO.has(id) and ResourceLoader.exists(DIR + id + ".png")

static func tamanho(id: String) -> Vector2:
	var c: Dictionary = CATALOGO.get(id, {"w": 1, "h": 1})
	return Vector2(c["w"], c["h"])

static func frames(id: String, loop: bool) -> SpriteFrames:
	var chave := "%s|%d" % [id, int(loop)]
	if _frames.has(chave):
		return _frames[chave]
	var c: Dictionary = CATALOGO[id]
	var tex: Texture2D = load(DIR + id + ".png")
	var sf := SpriteFrames.new()
	sf.set_animation_loop("default", loop)
	sf.set_animation_speed("default", c["fps"])
	for i in int(c["n"]):
		var at := AtlasTexture.new()
		at.atlas = tex
		at.region = Rect2(float((i % int(c["cols"])) * int(c["w"])), float(floori(float(i) / float(c["cols"])) * int(c["h"])), float(c["w"]), float(c["h"]))
		sf.add_frame("default", at)
	_frames[chave] = sf
	return sf

## Cria o sprite (sem pôr na cena). `escala` multiplica o tamanho do quadro; `rot` gira em volta da âncora.
## Sem a folha (arte ausente) devolve um Node2D vazio, para o efeito seguir só com o desenho por código.
static func criar(id: String, escala := 1.0, loop := false, ancora := "base", rot := 0.0) -> Node2D:
	if not existe(id):
		return Node2D.new()
	var s := AnimatedSprite2D.new()
	s.sprite_frames = frames(id, loop)
	s.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	var t := tamanho(id)
	var ponto := Vector2(t.x * 0.5, t.y)
	if ancora == "centro":
		ponto = t * 0.5
	elif ancora == "ponta":
		ponto = Vector2(0.0, t.y * 0.5)
	s.offset = t * 0.5 - ponto
	s.scale = Vector2.ONE * escala
	s.rotation = rot
	s.play("default")
	return s

## Toca uma vez no mundo e some sozinho.
static func tocar(cena: Node, id: String, pos: Vector2, escala := 1.0, ancora := "base", rot := 0.0, z := 4) -> Node2D:
	var s := criar(id, escala, false, ancora, rot)
	if s is AnimatedSprite2D:
		s.animation_finished.connect(s.queue_free)
	else:
		s.queue_free()
		return s
	s.z_index = z
	cena.add_child(s)
	s.global_position = pos
	return s

## Textura de pixel art a partir de linhas de texto (cada caractere uma cor da paleta; "." = vazio).
static func textura_ascii(linhas: Array, paleta: Dictionary) -> ImageTexture:
	var h := linhas.size()
	var w := String(linhas[0]).length()
	var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	for y in h:
		for x in w:
			var ch := String(linhas[y])[x]
			if paleta.has(ch):
				img.set_pixel(x, y, paleta[ch])
	return ImageTexture.create_from_image(img)
