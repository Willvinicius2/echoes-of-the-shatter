extends CanvasLayer
## Filtro de pixel art do mundo: reduz a imagem do jogo (sem a HUD) para uma grade interna baixa
## (pixel_base_x por pixel_base_y, ex. 640x360) com amostragem "nearest" e, se quiser, paleta reduzida.
## Fica acima do mundo e abaixo da HUD. Números em run_settings.csv (pixel_*).

const SHADER_CODIGO := """
shader_type canvas_item;
uniform sampler2D tela : hint_screen_texture, filter_nearest, repeat_disable;
uniform vec2 grade = vec2(640.0, 360.0);
uniform float niveis = 0.0;
void fragment() {
	vec2 sz = vec2(textureSize(tela, 0));
	vec2 celula = sz / grade;
	vec2 centro = (floor(FRAGCOORD.xy / celula) + 0.5) * celula;
	vec4 c = texture(tela, centro / sz);
	if (niveis > 1.0) {
		c.rgb = floor(c.rgb * (niveis - 1.0) + 0.5) / (niveis - 1.0);
	}
	COLOR = vec4(c.rgb, 1.0);
}
"""

var _mat: ShaderMaterial

static func ligado(cfg: Dictionary) -> bool:
	return float(cfg.get("pixel_base_x", 0.0)) > 0.0

func iniciar(cfg: Dictionary) -> void:
	layer = 1
	var sh := Shader.new()
	sh.code = SHADER_CODIGO
	_mat = ShaderMaterial.new()
	_mat.shader = sh
	_mat.set_shader_parameter("grade", Vector2(float(cfg["pixel_base_x"]), float(cfg["pixel_base_y"])))
	_mat.set_shader_parameter("niveis", float(cfg.get("pixel_niveis_cor", 0.0)))
	var r := ColorRect.new()
	r.set_anchors_preset(Control.PRESET_FULL_RECT)
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	r.material = _mat
	add_child(r)
