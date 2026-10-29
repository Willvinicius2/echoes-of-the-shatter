extends RefCounted
## Monta SpriteFrames a partir de res://data2d/sprites_manifest.csv.
## Usa a folha real se o PNG existir; senão gera um placeholder no mesmo formato.

const Csv = preload("res://scripts2d/csv2d.gd")
const Placeholders = preload("res://scripts2d/placeholders.gd")
const MANIFESTO := "res://data2d/sprites_manifest.csv"

# Para 5 linhas (S, SE, E, NE, N; o resto é espelho): setor de 45 graus -> [linha, espelhar]
const TABELA_5 := {0: [2, false], 1: [1, false], 2: [0, false], 3: [1, true], 4: [2, true], 5: [3, true], 6: [4, false], 7: [3, false]}
# Para 8 linhas (S, SE, E, NE, N, NW, W, SW)
const TABELA_8 := {0: [2, false], 1: [1, false], 2: [0, false], 3: [7, false], 4: [6, false], 5: [5, false], 6: [4, false], 7: [3, false]}

static var _frames := {}
static var _info := {}

## Linha da folha e espelhamento para um vetor de direção (0 graus = leste, y para baixo).
static func dir_for(facing: Vector2, dirs: int) -> Array:
	var k := posmod(int(round(facing.angle() / (PI / 4.0))), 8)
	return TABELA_8[k] if dirs == 8 else TABELA_5[k]

static func frames_for(id: String) -> SpriteFrames:
	if not _frames.has(id):
		_build(id)
	return _frames[id]

## {offset: Vector2, dirs: int, lado: int, evento: {anim: quadro}, tem_arquivo: bool}
static func info(id: String) -> Dictionary:
	if not _frames.has(id):
		_build(id)
	return _info[id]

static func _build(id: String) -> void:
	var sf := SpriteFrames.new()
	sf.remove_animation("default")
	var inf := {"offset": Vector2.ZERO, "dirs": 5, "lado": 128, "evento": {}, "tem_arquivo": false}
	for r in Csv.rows(MANIFESTO):
		if r["id"] != id:
			continue
		var lado := int(r["quadro"])
		var n := int(r["quadros"])
		var dirs := int(r["direcoes"])
		var pivo := Vector2i(int(r["pivo_x"]), int(r["pivo_y"]))
		var tex := _textura(r["arquivo"], r["anim"], id, lado, n, dirs, pivo, inf)
		inf["offset"] = Vector2(lado / 2.0 - pivo.x, lado / 2.0 - pivo.y)
		inf["dirs"] = dirs
		inf["lado"] = lado
		inf["evento"][r["anim"]] = int(r["evento_quadro"])
		for d in dirs:
			var nome := "%s_%d" % [r["anim"], d]
			sf.add_animation(nome)
			sf.set_animation_speed(nome, float(r["fps"]))
			sf.set_animation_loop(nome, r["loop"] == "true")
			for q in n:
				var at := AtlasTexture.new()
				at.atlas = tex
				at.region = Rect2(q * lado, d * lado, lado, lado)
				sf.add_frame(nome, at)
	_frames[id] = sf
	_info[id] = inf

static func _textura(caminho: String, anim: String, id: String, lado: int, n: int, dirs: int, pivo: Vector2i, inf: Dictionary) -> Texture2D:
	if ResourceLoader.exists(caminho):
		inf["tem_arquivo"] = true
		return load(caminho)
	if FileAccess.file_exists(caminho):
		var img := Image.load_from_file(ProjectSettings.globalize_path(caminho))
		if img != null:
			inf["tem_arquivo"] = true
			return ImageTexture.create_from_image(img)
	return Placeholders.sheet(id, anim, lado, n, dirs, pivo)
