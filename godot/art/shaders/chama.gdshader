shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never;
#include "res://art/shaders/ruido.gdshaderinc"
// Chama de braseiro: cartão billboard com máscara em gota deformada por ruído que sobe.
uniform vec3 core_color : source_color = vec3(1.0, 0.85, 0.45);
uniform vec3 edge_color : source_color = vec3(1.0, 0.25, 0.03);
uniform float intensity = 0.65;
uniform float speed = 1.4;
uniform float seed = 0.0;
void vertex() {
	// billboard no eixo Y: o cartão sempre encara a câmera
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(INV_VIEW_MATRIX[0], INV_VIEW_MATRIX[1], INV_VIEW_MATRIX[2], MODEL_MATRIX[3]);
}
void fragment() {
	vec2 uv = UV;
	float t = TIME * speed + seed;
	vec2 p = vec2(uv.x * 5.0, uv.y * 3.4 - t);                // frequência maior: línguas menores
	float n = fbm(p + vec2(0.0, 0.0)) ;
	float n2 = fbm(p * 1.9 + vec2(4.3, -t * 0.6));
	float h = 1.0 - uv.y;                                    // 0 na base, 1 na ponta
	float sway = (n - 0.5) * 0.55 * h;                       // oscilação lateral cresce com a altura
	float x = (uv.x - 0.5) * 2.0 + sway;
	float width = (0.8 - 0.76 * pow(h, 1.4)) * (1.0 + 0.35 * (n2 - 0.5));
	float body = smoothstep(width, width * 0.25, abs(x));
	float tip = smoothstep(1.0, 0.55, h + (n2 - 0.5) * 0.45);
	float f = body * tip * smoothstep(0.0, 0.3, h);        // base some devagar entre as brasas, sem corte serrilhado
	float hot = pow(f, 2.2) * (1.0 - h * 0.6);
	vec3 col = mix(edge_color, core_color, hot);
	ALBEDO = col * f * intensity;
	ALPHA = clamp(f, 0.0, 1.0);
}
