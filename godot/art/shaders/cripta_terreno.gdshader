shader_type spatial;
#include "res://art/shaders/ruido.gdshaderinc"
// Terreno contínuo da Cripta: lajotas no chão e pedra triplanar na rocha, misturadas pela cor de vértice (r = distância à borda do chão)
// e pela inclinação, sem emenda entre os dois. Une o que cripta_piso e cripta_pedra faziam em peças separadas.
uniform sampler2D piso_tex : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D piso_normal : hint_normal, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D pedra_tex : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform float tile_m = 16.0;
uniform vec3 piso_tint : source_color = vec3(0.80, 0.80, 0.85);
uniform vec3 pedra_tint : source_color = vec3(0.34, 0.33, 0.37);
uniform float pedra_escala = 0.18;
uniform float wet_amount : hint_range(0.0, 1.0) = 0.55;
uniform float grime_amount : hint_range(0.0, 1.0) = 0.55;
uniform float moss_amount : hint_range(0.0, 1.0) = 0.35;
uniform float normal_strength : hint_range(0.0, 3.0) = 1.3;
varying vec3 wpos;
varying vec3 wnrm;
varying float borda;
void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	borda = COLOR.r;
}
vec3 tri(sampler2D t, vec3 p, vec3 n) {
	vec3 w = pow(abs(n), vec3(4.0)); w /= (w.x + w.y + w.z);
	return texture(t, p.zy).rgb * w.x + texture(t, p.xz).rgb * w.y + texture(t, p.xy).rgb * w.z;
}
void fragment() {
	float rocha = max(smoothstep(0.12, 0.55, borda), smoothstep(0.35, 0.7, 1.0 - wnrm.y));
	// chão: lajotas úmidas com poças e sujeira
	vec2 uv = wpos.xz / tile_m;
	vec3 cp = texture(piso_tex, uv).rgb * piso_tint;
	cp *= mix(0.78, 1.18, fbm(wpos.xz * 0.09));
	float dirt = fbm(wpos.xz * 1.7 + 3.0);
	cp = mix(cp, cp * vec3(0.55, 0.52, 0.5), smoothstep(0.45, 0.8, dirt) * grime_amount);
	float wet = smoothstep(0.50, 0.66, fbm(wpos.xz * 0.35 + 7.0)) * wet_amount;
	cp *= mix(1.0, 0.55, wet);
	// rocha: triplanar, manchas, veios e musgo
	vec3 p = wpos * pedra_escala;
	vec3 cr = tri(pedra_tex, p, wnrm) * pedra_tint;
	vec2 q = wpos.xz + wpos.y * 1.3;
	float patches = fbm(q * 0.8);
	cr *= mix(0.65, 1.2, patches);
	float crack = smoothstep(0.47, 0.5, abs(fbm(q * 3.1 + wpos.y) - 0.5) * 2.0);
	cr *= mix(0.55, 1.0, crack);
	float up = smoothstep(0.55, 0.95, wnrm.y);
	float mossmask = up * smoothstep(0.45, 0.7, fbm(q * 1.3 + 5.0)) * moss_amount;
	cr = mix(cr, vec3(0.17, 0.19, 0.07) * (0.6 + 0.6 * patches), mossmask);
	// sujeira acumulada no pé da parede: o chão escurece perto da rocha
	cp = mix(cp, cp * vec3(0.5, 0.47, 0.45), (1.0 - smoothstep(0.0, 0.18, borda)) * 0.0 + smoothstep(0.0, 0.12, borda) * 0.45);
	ALBEDO = mix(cp, cr, rocha);
	ROUGHNESS = mix(mix(0.55, 0.08, wet), 0.82, rocha);
	SPECULAR = mix(mix(0.35, 0.9, wet), 0.4, rocha);
	vec3 n = texture(piso_normal, uv).xyz;
	vec3 nc = mix(vec3(0.5, 0.5, 1.0), n, normal_strength / 3.0 * (1.0 - wet * 0.85) * 2.2);
	float h = fbm(q * 4.0);
	vec3 nr = vec3(0.5 + (h - 0.5) * 0.28, 0.5 + (fbm(q * 4.0 + 9.0) - 0.5) * 0.28, 1.0);
	NORMAL_MAP = mix(nc, nr, rocha);
	NORMAL_MAP_DEPTH = 1.0;
}
