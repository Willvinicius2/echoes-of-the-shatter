extends RefCounted
## Theme de pedra escura das telas (menus, cartas, HUD). Cores em data2d/tema.csv.

const Csv = preload("res://scripts2d/csv2d.gd")

static var _cores := {}
static var _tema: Theme

static func cor(chave: String) -> Color:
	if _cores.is_empty():
		for r in Csv.rows("res://data2d/tema.csv"):
			_cores[r["chave"]] = Color.html(r["valor"])
	return _cores.get(chave, Color.MAGENTA)

## Moldura de pedra: fundo, borda e cantos arredondados.
static func caixa(fundo: Color, borda: Color, largura := 2, raio := 5, margem := 10) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = fundo
	sb.border_color = borda
	sb.set_border_width_all(largura)
	sb.set_corner_radius_all(raio)
	sb.set_content_margin_all(margem)
	return sb

static func tema() -> Theme:
	if _tema != null:
		return _tema
	var t := Theme.new()
	t.set_stylebox("normal", "Button", caixa(cor("pedra_clara"), cor("borda"), 2, 5, 12))
	t.set_stylebox("hover", "Button", caixa(cor("pedra_hover"), cor("borda_foco"), 2, 5, 12))
	t.set_stylebox("pressed", "Button", caixa(cor("pedra_pressionada"), cor("borda_foco"), 2, 5, 12))
	t.set_stylebox("focus", "Button", caixa(Color(0, 0, 0, 0), cor("borda_foco"), 3, 5, 12))
	t.set_stylebox("disabled", "Button", caixa(cor("pedra"), cor("borda"), 2, 5, 12))
	t.set_color("font_color", "Button", cor("texto"))
	t.set_color("font_hover_color", "Button", cor("destaque"))
	t.set_color("font_pressed_color", "Button", cor("destaque"))
	t.set_color("font_focus_color", "Button", cor("texto"))
	t.set_color("font_disabled_color", "Button", cor("texto_suave"))
	t.set_constant("h_separation", "Button", 8)
	t.set_stylebox("panel", "PanelContainer", caixa(cor("pedra"), cor("borda"), 3, 6, 36))
	t.set_color("font_color", "Label", cor("texto"))
	return t
