extends RefCounted
## Recolor por shader (doc 33, "elemento convertido"; doc 36 seção 6): reaproveita uma folha pintada de outro elemento
## girando o matiz e puxando para a paleta aprovada, sem redesenhar. Um material por pedido (os uniformes são da instância).
## Só aparência: nada de balanceamento.

const CODIGO := """
shader_type canvas_item;
render_mode blend_add;
uniform float matiz = 0.0;             // giro de matiz, em voltas (0,5 = cor oposta)
uniform vec3 tinta : source_color = vec3(1.0, 1.0, 1.0);
uniform float forca = 0.0;             // 0 = só o giro; 1 = tudo na cor da tinta (mantendo o brilho)
uniform float brilho = 1.0;
vec3 rgb2hsv(vec3 c) {
	vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
	vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
	vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
	float d = q.x - min(q.w, q.y);
	float e = 1.0e-10;
	return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}
vec3 hsv2rgb(vec3 c) {
	vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
	vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
	return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}
void fragment() {
	vec4 c = COLOR;
	vec3 h = rgb2hsv(c.rgb);
	h.x = fract(h.x + matiz);
	vec3 r = hsv2rgb(h);
	r = mix(r, tinta * h.z, forca * h.y);   // partes brancas (sem saturação) continuam brancas: miolo claro
	COLOR = vec4(r * brilho, c.a);
}
"""

static var _shader: Shader

## Material aditivo que gira o matiz da folha em `matiz` voltas e mistura `forca` da `tinta` (paleta do elemento).
static func material(matiz: float, tinta: Color, forca := 0.6, brilho := 1.0) -> ShaderMaterial:
	if _shader == null:
		_shader = Shader.new()
		_shader.code = CODIGO
	var m := ShaderMaterial.new()
	m.shader = _shader
	m.set_shader_parameter("matiz", matiz)
	m.set_shader_parameter("tinta", Vector3(tinta.r, tinta.g, tinta.b))
	m.set_shader_parameter("forca", forca)
	m.set_shader_parameter("brilho", brilho)
	return m

## Atalhos das paletas aprovadas (corpo de cada elemento, doc 33 seção 6) a partir das folhas que existem.
static func tornado_para_veneno() -> ShaderMaterial:   # tornado_tempestade.png (azul) -> verde-ácido
	return material(-0.36, Color("5CD12B"), 0.55, 1.05)

static func meteoro_para_gelo() -> ShaderMaterial:     # meteoro_queda.png (laranja) -> azul-gelo
	return material(0.47, Color("7FD3F2"), 0.7, 1.1)
