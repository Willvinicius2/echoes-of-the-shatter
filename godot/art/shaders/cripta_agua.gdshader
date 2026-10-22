shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, specular_schlick_ggx;
#include "res://art/shaders/ruido.gdshaderinc"
// Água rasa da Cripta (poça). Lê UV2 da malha: x = profundidade (0 borda, 1 centro), y = opacidade.
// Reflexo: SSR/ambiente do WorldEnvironment (ative ssr_enabled na Cripta); o brilho de Fresnel cobre o caso sem SSR.
uniform sampler2D screen_tex : hint_screen_texture, repeat_disable, filter_linear_mipmap;
uniform vec3 shallow_color : source_color = vec3(0.07, 0.09, 0.13);   // azul-ardósia, um pouco mais escuro e frio que o piso
uniform vec3 deep_color : source_color = vec3(0.02, 0.03, 0.06);
uniform vec3 sky_top : source_color = vec3(0.16, 0.2, 0.32);
uniform vec3 sky_horizon : source_color = vec3(0.42, 0.5, 0.64);
uniform vec3 torch_color : source_color = vec3(1.0, 0.55, 0.22);
uniform vec3 torch_dir = vec3(0.6, 0.45, -0.4);   // direção (mundo) de onde vem a luz das tochas
uniform float distortion = 0.035;
uniform float reflection : hint_range(0.0, 2.0) = 1.0;
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
	// transparência: o piso aparece por baixo, levemente deslocado pela ondulação
	vec2 off = g * distortion * smoothstep(0.0, 0.25, depth);
	vec3 floor_col = textureLod(screen_tex, SCREEN_UV + off, 0.0).rgb;
	float d = smoothstep(0.0, 0.7, depth);
	vec3 tint = mix(shallow_color, deep_color, d);
	ALBEDO = mix(floor_col * tint * 4.0, tint, 0.35 + 0.35 * d);
	ALPHA = clamp(mix(0.45, 1.0, smoothstep(0.0, 0.2, depth)) * UV2.y, 0.0, 1.0);
	ROUGHNESS = 0.02;
	SPECULAR = 1.0;
	METALLIC = 0.0;
	// Fresnel simples + fio de luz no menisco (borda nítida da poça)
	float fres = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
	float rim = (1.0 - smoothstep(0.0, 0.07, depth)) * smoothstep(0.0, 0.015, depth + 0.02);
	// reflexo: céu em degradê + brilho especular da luz das tochas (refletidos pelo normal ondulado)
	vec3 vn = normalize(vec3(n.x, n.z, n.y));
	vec3 vv = normalize((INV_VIEW_MATRIX * vec4(-VIEW, 0.0)).xyz);
	vec3 rv = reflect(vv, vn);
	vec3 sky = mix(sky_horizon, sky_top, clamp(rv.y, 0.0, 1.0));
	float torch = pow(clamp(dot(rv, normalize(torch_dir)), 0.0, 1.0), 64.0);
	EMISSION = reflection * (sky * (0.05 + fres * 0.7) + torch_color * torch * 1.4) + sheen_color * (rim * 0.12 * edge_glint) + sheen_color * 0.015 * ring * ring;
}
