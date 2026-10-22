shader_type spatial;
render_mode blend_mix, unshaded, depth_draw_never, cull_disabled, shadows_disabled;
#include "res://art/shaders/ruido.gdshaderinc"
// Gotas da poça da Cripta: quad deitado (plano XZ do objeto, em metros) sobre a poça.
// Anéis pequenos nascem em pontos aleatórios (hash por célula e por ciclo de tempo), crescem e somem.
// Alfa só nos anéis finos e suaves. Sem texturas.
uniform vec3 ring_color : source_color = vec3(0.62, 0.74, 0.9);
uniform float intensidade : hint_range(0.0, 1.0) = 0.35;
uniform float densidade : hint_range(0.0, 1.0) = 0.22;   // fração das células com gota ativa
uniform float velocidade : hint_range(0.05, 3.0) = 0.6;  // ciclos por segundo
uniform float tamanho : hint_range(0.02, 0.3) = 0.1;     // raio máximo do anel externo, em metros
uniform float espessura : hint_range(0.002, 0.03) = 0.006;
uniform float celula = 0.4;                               // lado da célula em metros (>= 2 * tamanho)
varying vec2 lpos;
float h11(float x) { return fract(sin(x * 127.1) * 43758.5453); }
vec2 h22(vec2 p) {
	return vec2(h21(p + 3.1), h21(p * 1.7 + 8.9));
}
void vertex() {
	lpos = VERTEX.xz;
}
void fragment() {
	vec2 g = lpos / celula;
	vec2 ci = floor(g);
	float acc = 0.0;
	for (int j = -1; j <= 1; j++) {
		for (int i = -1; i <= 1; i++) {
			vec2 c = ci + vec2(float(i), float(j));
			float off = h21(c + 17.3);                     // desloca o relógio de cada célula
			float t = TIME * velocidade * (0.7 + 0.6 * h21(c + 5.7)) + off * 7.0;
			float cyc = floor(t);
			float ph = fract(t);
			vec2 key = c + vec2(cyc * 13.37, cyc * 7.77);
			if (h21(key + 41.0) > densidade) continue;      // só uma fração das gotas acontece
			vec2 pos = (c + 0.2 + 0.6 * h22(key)) * celula; // ponto da gota dentro da célula
			float r = length(lpos - pos);
			float rad = tamanho * (0.25 + 0.75 * h21(key + 9.0)) * (1.0 - pow(1.0 - ph, 2.2));
			float life = smoothstep(0.0, 0.08, ph) * pow(1.0 - ph, 1.6);
			// 3 anéis finos, cada um mais fraco e atrás do anterior
			float w = espessura * (1.0 + ph);
			float a = 0.0;
			for (int k = 0; k < 3; k++) {
				float rk = rad - float(k) * tamanho * 0.22;
				if (rk > 0.0) {
					float d = (r - rk) / w;
					a += exp(-d * d) * (1.0 - 0.38 * float(k));
				}
			}
			acc += a * life;
		}
	}
	// leve irregularidade ao longo do anel para não parecer desenho
	acc *= 0.75 + 0.5 * vnoise(lpos * 55.0);
	ALBEDO = ring_color;
	ALPHA = clamp(acc * intensidade, 0.0, 1.0);
}
