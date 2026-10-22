shader_type spatial;
#include "res://art/shaders/ruido.gdshaderinc"
// Pedra suja e irregular da Cripta: triplanar, manchas, umidade no pé, musgo nas faces de cima e desgaste.
uniform sampler2D albedo_tex : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform vec3 tint : source_color = vec3(0.46, 0.46, 0.50);
uniform float tex_scale = 0.4;
uniform float moss_amount : hint_range(0.0, 1.0) = 0.6;
uniform float grime_height = 1.6;
uniform float world_space : hint_range(0.0, 1.0) = 0.0;
uniform float bump : hint_range(0.0, 2.0) = 0.8;
varying vec3 lpos;
varying vec3 wpos;
varying vec3 wnrm;
varying vec3 lnrm;
void vertex() {
	lpos = VERTEX;
	lnrm = NORMAL;
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}
vec3 tri(sampler2D t, vec3 p, vec3 n) {
	vec3 w = pow(abs(n), vec3(4.0)); w /= (w.x + w.y + w.z);
	return texture(t, p.zy).rgb * w.x + texture(t, p.xz).rgb * w.y + texture(t, p.xy).rgb * w.z;
}
void fragment() {
	vec3 p = (world_space > 0.5 ? wpos : lpos) * tex_scale;
	vec3 n = world_space > 0.5 ? wnrm : normalize(lnrm);
	vec3 col = tri(albedo_tex, p, n) * tint;
	vec2 q = wpos.xz + wpos.y * 1.3;
	float patches = fbm(q * 0.8);
	col *= mix(0.65, 1.2, patches);                         // manchas irregulares
	float crack = smoothstep(0.47, 0.5, abs(fbm(q * 3.1 + wpos.y) - 0.5) * 2.0 + 0.0);
	col *= mix(0.55, 1.0, crack);                           // veios escuros finos
	// sujeira acumulada perto do chão e nas arestas
	float low = 1.0 - smoothstep(0.0, grime_height, wpos.y);
	col = mix(col, col * vec3(0.45, 0.42, 0.40), low * (0.4 + 0.5 * fbm(q * 2.0)));
	// musgo nas faces voltadas para cima e perto do chão
	float up = smoothstep(0.55, 0.95, wnrm.y);
	float mossmask = clamp(up * 0.9 + low * 0.6, 0.0, 1.0) * smoothstep(0.45, 0.7, fbm(q * 1.3 + 5.0)) * moss_amount;
	col = mix(col, vec3(0.17, 0.19, 0.07) * (0.6 + 0.6 * patches), mossmask);
	ALBEDO = col;
	ROUGHNESS = mix(0.82, 0.45, low * 0.6);
	float h = fbm(q * 4.0) ;
	NORMAL_MAP = vec3(0.5 + (h - 0.5) * 0.35 * bump, 0.5 + (fbm(q * 4.0 + 9.0) - 0.5) * 0.35 * bump, 1.0);
	NORMAL_MAP_DEPTH = 1.0;
}
