shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_back, specular_schlick_ggx;
// Anel de pedra molhada em volta da poça: escurece o piso e o deixa lustroso. UV2.x = opacidade (degradê da malha).
uniform vec3 wet_color : source_color = vec3(0.012, 0.016, 0.026);
uniform float strength : hint_range(0.0, 1.0) = 0.9;
void fragment() {
	ALBEDO = wet_color;
	ALPHA = clamp(UV2.x * strength, 0.0, 1.0);
	ROUGHNESS = 0.1;
	SPECULAR = 0.8;
}
