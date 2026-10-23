# godot --path godot --script res://scripts/tools/captura_arqueiro_dark.gd -- pasta_saida
# Capturas da cena de teste do arqueiro dark: 3/4 do jogo, 3/4 perto, frente, costas e lado.
# Precisa de renderizacao real (o --headless usa o driver "dummy" e sai preto): rode com a janela fora da tela
# (--position 30000,30000) ou use o wrapper tools/arqueiro_dark/captura.ps1. Sai sozinho, tambem no erro.
extends SceneTree
func _init() -> void:
	var a := OS.get_cmdline_user_args()
	var pasta: String = a[0] if a.size() > 0 else "D:/openclaude/_trabalho-claude/tmp/arq_dark"
	DirAccess.make_dir_recursive_absolute(pasta)
	var sv := SubViewport.new(); sv.size = Vector2i(1280, 960); sv.render_target_update_mode = SubViewport.UPDATE_ALWAYS; sv.msaa_3d = Viewport.MSAA_4X
	root.add_child(sv)
	var cena := load("res://scenes/teste/ArqueiroDarkTeste.tscn") as PackedScene
	if cena == null:
		push_error("cena de teste nao carregou"); quit(1); return
	var t := cena.instantiate()
	sv.add_child(t)
	for i in 30: await process_frame
	var nomes := ["3q_jogo", "3q_perto", "frente", "costas", "lado"]
	for v in nomes.size():
		t.DefinirVista(v)
		for i in 8: await process_frame
		var img := sv.get_texture().get_image()
		if img == null or img.is_empty():
			push_error("imagem vazia (driver dummy?)"); quit(1); return
		img.save_png("%s/godot_%s.png" % [pasta, nomes[v]])
	print("CAPTURA OK ", pasta)
	quit(0)
