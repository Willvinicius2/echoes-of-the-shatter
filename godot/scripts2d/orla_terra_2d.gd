extends RefCounted
## Orla de terra da massa de rocha da Pedreira (`m` no mapa): o chão aberto não termina num corte reto contra a rocha.
## Um retângulo sobre o mapa inteiro, com um shader que lê uma textura de 1 px por célula (massa ou não) e pinta, em px
## inteiros de mundo e sem gradiente: do lado aberto um pé escuro de 2 a 4 px e terra em manchas que rareiam até 6 a 22 px da
## emenda (a largura muda devagar ao longo dela, a borda sai em blocos de 3 px, com salpicos mais claros e mais escuros);
## do lado da massa o pé morde a rocha em 0 a 3 px, em trechos, e uma sombra de contato em dither de Bayer 4x4 completa a
## emenda. O chão da massa é o próprio tile do piso, escurecido em marrom por `Room2D` (não o preto da sombra da mata).

const SHADER := """
shader_type canvas_item;
uniform sampler2D mascara : filter_nearest;
uniform ivec2 grade_tam;
uniform float tile = 64.0;
uniform vec4 cor_pe : source_color = vec4(0.1, 0.07, 0.045, 1.0);
uniform vec4 cor_sombra_terra : source_color = vec4(0.15, 0.105, 0.07, 1.0);
uniform vec4 cor_terra : source_color = vec4(0.22, 0.16, 0.105, 1.0);
uniform vec4 cor_terra_clara : source_color = vec4(0.31, 0.235, 0.165, 1.0);
uniform vec4 cor_sombra : source_color = vec4(0.03, 0.02, 0.015, 1.0);
varying vec2 wpos;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 0.0, 1.0)).xy;
}

float h21(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float ruido(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(h21(i), h21(i + vec2(1.0, 0.0)), f.x), mix(h21(i + vec2(0.0, 1.0)), h21(i + vec2(1.0, 1.0)), f.x), f.y);
}

float massa(ivec2 c) {
	if (c.x < 0 || c.y < 0 || c.x >= grade_tam.x || c.y >= grade_tam.y) {
		return 1.0;
	}
	return texelFetch(mascara, c, 0).r;
}

float dist_rect(vec2 p, ivec2 c) {
	vec2 c0 = vec2(c) * tile;
	vec2 d = max(max(c0 - p, vec2(0.0)), p - (c0 + vec2(tile)));
	return length(d);
}

void fragment() {
	vec2 p = floor(wpos) + 0.5;
	ivec2 cel = ivec2(floor(p / tile));
	float aqui = massa(cel);
	float d = 1.0e9;
	for (int j = -1; j <= 1; j++) {
		for (int i = -1; i <= 1; i++) {
			ivec2 c = cel + ivec2(i, j);
			if (massa(c) != aqui) {
				d = min(d, dist_rect(p, c));
			}
		}
	}
	int bx = int(mod(floor(wpos.x), 4.0));
	int by = int(mod(floor(wpos.y), 4.0));
	float lim = (float((bx * 5 + by * 7 + bx * by) % 16) + 0.5) / 16.0;
	COLOR = vec4(0.0);
	if (d < 30.0) {
		if (aqui > 0.5) {
			// lado da massa: o pé morde a rocha em 0 a 3 px, em trechos (o corte do tile não fica uma reta), e a sombra de contato vem em dither
			float mordida = 1.7 + 4.0 * (ruido(p / 6.0) - 0.5) + 1.5 * (h21(floor(p / 2.0)) - 0.5);
			float prof = 7.0 + 3.0 * ruido(p / 9.0);
			float forca = clamp(1.0 - d / prof, 0.0, 1.0);
			if (d < mordida) {
				COLOR = cor_pe;
			} else if (forca > lim) {
				COLOR = vec4(cor_sombra.rgb, 0.6);
			}
		} else {
			// lado aberto: pé escuro de 2 a 4 px e terra em manchas que rareiam com a distância (largura de 6 a 22 px, que muda
			// devagar ao longo da emenda), a borda em blocos de 3 px e salpicos mais claros: sem uma faixa reta
			float pe = 2.5 + 2.0 * ruido(p / 7.0);
			float largura = 6.0 + 16.0 * ruido(p / 41.0 + 11.0);
			float n = ruido(p / 13.0) * 0.7 + h21(floor(p / 3.0)) * 0.3;
			float forca = clamp(1.0 - d / largura, 0.0, 1.0) * 1.25;
			float grao = h21(floor(p / 2.0) + 17.0);
			vec4 terra = cor_terra;
			if (d < largura * 0.38) {
				terra = cor_sombra_terra;
			} else if (grao > 0.88) {
				terra = cor_terra_clara;
			} else if (grao < 0.07) {
				terra = cor_sombra_terra;
			}
			if (d < pe) {
				COLOR = cor_pe;
			} else if (n < forca) {
				COLOR = terra;
			}
		}
	}
}
"""

## Cria a orla na `sala` e a põe logo abaixo de `acima` (a camada dos objetos): sobre o chão e a massa, sob as lajes, os
## caminhos e os atores. `grade` são as linhas do mapa; `m` é a massa.
static func montar(sala: Node2D, grade: Array, colunas: int, linhas: int, tile: int, acima: Node) -> ColorRect:
	var img := Image.create(colunas, linhas, false, Image.FORMAT_R8)
	for y in linhas:
		for x in colunas:
			img.set_pixel(x, y, Color(1, 0, 0) if grade[y][x] == "m" else Color(0, 0, 0))
	var mat := ShaderMaterial.new()
	mat.shader = Shader.new()
	mat.shader.code = SHADER
	mat.set_shader_parameter("mascara", ImageTexture.create_from_image(img))
	mat.set_shader_parameter("grade_tam", Vector2i(colunas, linhas))
	mat.set_shader_parameter("tile", float(tile))
	var r := ColorRect.new()
	r.name = "OrlaTerra"
	r.size = Vector2(colunas * tile, linhas * tile)
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	r.material = mat
	sala.add_child(r)
	sala.move_child(r, acima.get_index())
	return r
