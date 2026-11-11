extends RefCounted
## Sprites de pixel art por código e utilidades das habilidades físicas do Arqueiro (efeitos_arqueiro_fisico_2d.gd e
## efeitos_arqueiro_sombra_2d.gd). As classes internas dos efeitos chamam estas funções por `F.`.

const Px = preload("res://scripts2d/fx_pixel_2d.gd")
const ESC := 2.5                       # 1 px da arte = 2,5 px do mundo (sprites_escala.csv)
const PALETA := {"k": Color(0.1, 0.08, 0.1), "W": Color(0.95, 0.93, 0.85), "M": Color(0.5, 0.33, 0.18), "m": Color(0.7, 0.5, 0.28),
	"S": Color(0.62, 0.68, 0.78), "s": Color(0.92, 0.96, 1.0), "H": Color(0.3, 0.33, 0.42), "Y": Color(1.0, 0.8, 0.3),
	"P": Color(1.0, 0.92, 0.7), "p": Color(0.85, 0.65, 0.3), "R": Color(0.75, 0.25, 0.15), "B": Color(0.2, 0.18, 0.22)}
const ARTE := {
	"virote": [
		"...........................H..",
		".kk.....................HHHH..",
		"kWWk..kkkkkkkkkkkkkkkkkkHSSSH.",
		".kWWkkMmmmmmmmmmmmmmmmmMSSsSSH",
		"kWWk..kkkkkkkkkkkkkkkkkkHSSSH.",
		".kk.....................HHHH..",
		"...........................H.."],
	"lamina": [
		"....kkkk...",
		"..kkSSSSk..",
		".kSSssSSk..",
		".kSsk.kk...",
		"kSSk.......",
		"kSsk.......",
		"kSSk.......",
		".kSsk.kk...",
		".kSSssSSk..",
		"..kkSSSSk..",
		"....kkkk..."],
	"cravada": [
		".....WW",
		"....WWk",
		"....Mk.",
		"...mk..",
		"...M...",
		"..mk...",
		"..M....",
		".Mk....",
		".k....."],
	"flecha": [
		".k.......k..",
		"kWkkkkkkkSk.",
		".WmmmmmmmSsk",
		"kWkkkkkkkSk.",
		".k.......k.."],
	"pote": [
		".k......kkk.",
		"kWkkkkkkRRRk",
		".WmmmmmkRYRk",
		"kWkkkkkkRRRk",
		".k......kkk."],
	"falcao_a": [
		"....kk..........",
		"...kPPk.........",
		"...kPpPk........",
		"....kPpPk..kk...",
		"..kkkPPPPkkPPk..",
		".kPpPPPPPPPPkYk.",
		"..kkPPPPPPPkkk..",
		"....kkPPPk......",
		"......kkk......."],
	"falcao_b": [
		"................",
		"...........kk...",
		"..kkkkkkkkkPPk..",
		".kPpPPPPPPPPkYk.",
		"..kkPPPPPPPkkk..",
		"...kPpPPk.......",
		"...kPpPk........",
		"...kPPk.........",
		"....kk.........."],
}
static var _tex := {}

static func tex(nome: String) -> Texture2D:
	if not _tex.has(nome):
		_tex[nome] = Px.textura_ascii(ARTE[nome], PALETA)
	return _tex[nome]

## Sprite de pixel art (filtro Nearest, escala do mundo) centrado.
static func sprite(nome: String, escala := 1.0) -> Sprite2D:
	var s := Sprite2D.new()
	s.texture = tex(nome)
	s.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	s.scale = Vector2.ONE * ESC * escala
	return s

## Empurrão no inimigo (respeita a resistência dele). Chefes sem empurrão ficam parados.
static func empurrar(e: Node, v: Vector2) -> void:
	if is_instance_valid(e) and "_kb" in e:
		e._kb = v * (1.0 - float(e.stats.get("kb_resist", 0.0)))

## Dano de uma skill de precisão: rola o crítico do arqueiro (as de área não rolam).
static func dano_critico(jogador: Node2D, mult: float) -> float:
	var d: float = jogador.stats["arrow_damage"] * mult
	if float(jogador.stats.get("crit_chance", 0.0)) > 0.0 and randf() < float(jogador.stats["crit_chance"]):
		d *= float(jogador.stats.get("crit_mult", 1.0))
	return d

