shader_type spatial;
#include "res://art/shaders/ruido.gdshaderinc"
// Piso da Cripta: lajotas escuras úmidas com poças, sujeira e quebra de repetição.
uniform sampler2D albedo_tex : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D normal_tex : hint_normal, repeat_enable, filter_linear_mipmap_anisotropic;
uniform float tile_m = 16.0;
uniform vec3 tint : source_color = vec3(0.80, 0.80, 0.85);
uniform float wet_amount : hint_range(0.0, 1.0) = 0.55;
uniform float grime_amount : hint_range(0.0, 1.0) = 0.55;
uniform float normal_strength : hint_range(0.0, 3.0) = 1.3;
varying vec3 wpos;
varying vec3 wnrm;
void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}
void fragment() {
	vec2 uv = wpos.xz / tile_m;
	vec3 side = vec3(1.0);
	// faces verticais (degraus, soco): projeta em x/y para não esticar
	if (abs(wnrm.y) < 0.6) uv = (abs(wnrm.x) > abs(wnrm.z) ? wpos.zy : wpos.xy) / tile_m;
	vec3 col = texture(albedo_tex, uv).rgb * tint;
	// manchas grandes de tom quebram o padrão repetido
	float big = fbm(wpos.xz * 0.09);
	col *= mix(0.78, 1.18, big);
	// sujeira fina e escurecimento nas juntas já vem da textura; acrescenta poeira irregular
	float dirt = fbm(wpos.xz * 1.7 + 3.0);
	col = mix(col, col * vec3(0.55, 0.52, 0.5), smoothstep(0.45, 0.8, dirt) * grime_amount);
	// poças: úmido onde o ruído grande passa de um limite
	float wet = smoothstep(0.50, 0.66, fbm(wpos.xz * 0.35 + 7.0)) * wet_amount;
	col *= mix(1.0, 0.55, wet);
	ALBEDO = col;
	ROUGHNESS = mix(0.55, 0.08, wet) - 0.1 * smoothstep(0.5, 0.9, dirt) * 0.0;
	SPECULAR = mix(0.35, 0.9, wet);
	vec3 n = texture(normal_tex, uv).xyz;
	NORMAL_MAP = mix(vec3(0.5, 0.5, 1.0), n, normal_strength / 3.0 * (1.0 - wet * 0.85) * 2.2);
	NORMAL_MAP_DEPTH = 1.0;
}
