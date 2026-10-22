shader_type spatial;
// Cera das velas: textura baked (cor, normal, MR do glb) + translucidez falsa por rim quente e luz que atravessa as partes finas.
// Uso: ShaderMaterial com albedo_tex, normal_tex e mr_tex (G = rugosidade) tirados do glb das velas.
uniform sampler2D albedo_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D normal_tex : hint_normal, filter_linear_mipmap, repeat_disable;
uniform sampler2D mr_tex : hint_default_white, filter_linear_mipmap, repeat_disable;
uniform vec3 cor_transmissao : source_color = vec3(1.0, 0.62, 0.25);
uniform float forca_transmissao : hint_range(0.0, 3.0) = 1.1;
uniform float forca_rim : hint_range(0.0, 3.0) = 0.8;

void fragment() {
	vec3 alb = texture(albedo_tex, UV).rgb;
	ALBEDO = alb;
	NORMAL_MAP = texture(normal_tex, UV).rgb;
	ROUGHNESS = texture(mr_tex, UV).g;
	METALLIC = 0.0;
	SPECULAR = 0.5;
	float rim = pow(1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0), 2.5);
	EMISSION = cor_transmissao * rim * forca_rim * 0.35 * alb;
}

void light() {
	// luz que atravessa a cera: a face voltada contra a luz recebe um brilho quente (aproximação de SSS)
	float atras = clamp(dot(-NORMAL, LIGHT), 0.0, 1.0);
	DIFFUSE_LIGHT += atras * ATTENUATION * LIGHT_COLOR / PI * cor_transmissao * forca_transmissao * 0.5;
}
