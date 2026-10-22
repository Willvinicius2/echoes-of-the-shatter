shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, specular_schlick_ggx;
#include "res://art/shaders/ruido.gdshaderinc"
// Água rasa da Cripta (poça). Lê UV2 da malha: x = profundidade (0 borda, 1 centro), y = opacidade.
// Reflexo: SSR/ambiente do WorldEnvironment (ative ssr_enabled na Cripta); o brilho de Fresnel cobre o caso sem SSR.
uniform vec3 shallow_color : source_color = vec3(0.045, 0.095, 0.115);
uniform vec3 deep_color : source_color = vec3(0.008, 0.026, 0.04);
uniform vec3 sheen_color : source_color = vec3(0.55, 0.7, 0.9);
uniform float opacity : hint_range(0.0, 1.0) = 0.78;
uniform float ripple_scale = 7.0;
uniform float ripple_speed = 0.06;
uniform float ripple_strength : hint_range(0.0, 1.0) = 0.22;
uniform float drip_period = 3.4;
uniform float drip_strength : hint_range(0.0, 1.0) = 0.5;
uniform float edge_glint : hint_range(0.0, 2.0) = 0.7;
varying vec2 lpos;
varying vec3 wpos;
float height(vec2 p) {
	float t = TIME * ripple_speed;
	return fbm(p * ripple_scale + vec2(t, t * 0.7)) * 0.6 + fbm(p * ripple_scale * 2.3 - vec2(t * 1.3, -t)) * 0.4;
}
void vertex() {
	lpos = VERTEX.xz;                 // espaço do objeto (Y do Godot = cima)
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}
void fragment() {
	float depth = UV2.x;
	vec2 p = wpos.xz;
	// ondulação por diferenças finitas do campo de altura
	float e = 0.02;
	float h0 = height(p);
	vec2 g = vec2(height(p + vec2(e, 0.0)) - h0, height(p + vec2(0.0, e)) - h0) / e;
	// pingo: anéis que nascem no centro e se abrem
	float r = length(lpos);
	float ph = fract(TIME / drip_period);
	float front = ph * 0.55;
	float ring = sin((r - front) * 70.0) * exp(-pow((r - front) * 9.0, 2.0)) * (1.0 - ph);
	vec2 dirv = r > 0.001 ? lpos / r : vec2(0.0);
	g += dirv * ring * drip_strength * 3.0;
	vec3 n = vec3(-g * ripple_strength * 0.35 * smoothstep(0.0, 0.2, depth), 1.0);
	NORMAL_MAP = vec3(n.xy * 0.5 + 0.5, 1.0);
	NORMAL_MAP_DEPTH = 1.0;
	// cor: raso mostra a pedra, fundo escurece
	float d = smoothstep(0.0, 0.7, depth);
	ALBEDO = mix(shallow_color, deep_color, d);
	ALPHA = clamp(mix(0.38, opacity, smoothstep(0.0, 0.25, depth)) * UV2.y, 0.0, 1.0);
	ROUGHNESS = 0.02;
	SPECULAR = 1.0;
	METALLIC = 0.0;
	// Fresnel simples + fio de luz no menisco (borda nítida da poça)
	float fres = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
	float rim = (1.0 - smoothstep(0.0, 0.07, depth)) * smoothstep(0.0, 0.015, depth + 0.02);
	EMISSION = sheen_color * (fres * 0.18 + rim * 0.12 * edge_glint) + sheen_color * 0.015 * ring * ring;
}
