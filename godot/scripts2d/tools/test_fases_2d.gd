extends RefCounted
## Testes da seleção de fase e do elite do portão (docs/design/34_fases_e_desbloqueio.md), chamados por test_2d.gd:
## tabela de fases, regra de destrancar, save das fases (save antigo abre), cartão da fase no título, corrida usando a
## sala e a fase do spawner escolhidas e o elite do portão (IA comum, escala, barra grande, entrada invulnerável, portal).
## Também confere que nenhuma fase usa inimigo sem arte pronta (regra: nada de caixa provisória no jogo).
## A corrida usa data2d/testes/fases_teste.csv, em que a Pedreira aponta para a sala de fase_1.txt (não depende de fase_2.txt).

const Csv = preload("res://scripts2d/csv2d.gd")
const ArteInimigos = preload("res://scripts2d/tools/arte_inimigos_2d.gd")
const Fase = preload("res://scripts2d/fase_2d.gd")
const MetaScript = preload("res://scripts2d/meta_2d.gd")
const MenusScript = preload("res://scripts2d/menus_2d.gd")
const EnemyScript = preload("res://scripts2d/enemy_2d.gd")
const RunScript = preload("res://scripts2d/run_2d.gd")
const RunScene = preload("res://scenes2d/Run2D.tscn")
const OpcoesScript = preload("res://scripts2d/opcoes_2d.gd")
const TABELA_TESTE := "res://data2d/testes/fases_teste.csv"
const SAVE := "user://teste_fases_meta_2d.json"
const OPCOES := "user://teste_fases_opcoes_2d.json"

var t: SceneTree
var check: Callable

func _init(arvore: SceneTree, verifica: Callable) -> void:
	t = arvore
	check = verifica

func _esperar(cond: Callable, max_s: float) -> void:
	var t0 := Time.get_ticks_msec()
	while not cond.call() and (Time.get_ticks_msec() - t0) < max_s * 1000.0:
		await t.physics_frame

func _escolher_tudo(run) -> void:
	var n := 0
	while run.ui.aberta and n < 50:
		run.ui.escolher(0)
		n += 1

func _limpar() -> void:
	DirAccess.remove_absolute(SAVE)
	DirAccess.remove_absolute(MetaScript.caminho_fases())
	DirAccess.remove_absolute(OPCOES)

func rodar() -> void:
	var caminho_antes: String = MetaScript.caminho
	var opcoes_antes: String = OpcoesScript.caminho
	var tabela_antes: String = Fase.tabela
	MetaScript.caminho = SAVE
	OpcoesScript.caminho = OPCOES
	_limpar()
	_testar_tabela()
	_testar_arte_das_fases()
	_testar_regra()
	_testar_save()
	await _testar_menu()
	await _testar_corrida_e_elite()
	Fase.tabela = tabela_antes
	Fase.todas_abertas = false
	Fase.vencidas = []
	Fase.definir("")
	_limpar()
	MetaScript.caminho = caminho_antes
	OpcoesScript.caminho = opcoes_antes

## fases_2d.csv: Cripta aberta de saída, Pedreira pede a Cripta; textos por chave; a fase do spawner existe no core.
func _testar_tabela() -> void:
	Fase.tabela = "res://data2d/fases_2d.csv"
	check.call(Fase.ids() == ["cripta", "pedreira"], "fases: tabela tem cripta e pedreira (%s)" % str(Fase.ids()))
	check.call(Fase.requer("cripta") == "" and Fase.requer("pedreira") == "cripta", "fases: a pedreira pede a cripta")
	check.call(Fase.sala("cripta") == "res://data2d/rooms/fase_1.txt" and Fase.sala("pedreira") == "res://data2d/rooms/fase_2.txt", "fases: salas da tabela")
	for id in Fase.ids():
		var d: Dictionary = Fase.dados(id)
		check.call(Csv.t(d["nome"]) != d["nome"] and Csv.t(d["descricao"]) != d["descricao"], "fases: %s tem nome e descrição por chave de loc" % id)
	for k in ["fase.trancada", "fase.em_breve", "fase.desbloqueada", "menu.fase", "hud.chefe_nome", "hud.gate_altar", "hud.gate_open"]:
		check.call(Csv.t(k) != k, "fases: loc %s" % k)
	var m = MetaScript.new()
	var defs: Array = m.nucleo.ondas_definicoes().get("phases", [])
	var por_id := {}
	for f in defs:
		por_id[str(f["id"])] = f
	for id in Fase.ids():
		check.call(por_id.has(Fase.onda_fase(id)), "fases: %s usa a fase do spawner '%s' do core" % [id, Fase.onda_fase(id)])
	if por_id.has("pedreira"):
		var p: Dictionary = por_id["pedreira"]
		check.call(str(p["boss"]) == "ossuary_captain" and Csv.enemy("ossuary_captain")["kind"] != "boss", "pedreira: o chefe é o Capitão do Ossuário, inimigo comum (elite do portão)")
		check.call(p["waves"].size() == 7, "pedreira: 7 ondas (%d)" % p["waves"].size())
		var sem_capitao := true
		var todas := ""
		for w in p["waves"]:
			var mix := JSON.stringify(w)
			sem_capitao = sem_capitao and not mix.contains("ossuary_captain")
			todas += mix
		check.call(sem_capitao, "pedreira: o capitão não aparece nas ondas comuns")
		# a assinatura da fase são as matilhas de ash_hound (folha animada por código, tools/sprites2d/cao_de_cinza) e o
		# stone_herald (modelo de pedra por código, tools/sprites2d/arauto_de_pedra) pesa nas duas últimas ondas. As ondas só usam
		# inimigos que têm arte (test_pedreira_2d.gd confere que nenhum sem folha entra) e variam entre os oito que existem
		check.call(todas.contains("ash_hound"), "pedreira: a matilha de ash_hound é a assinatura da fase")
		check.call(todas.contains("stone_herald"), "pedreira: o Arauto de Pedra pesa nas ondas finais")
		var tipos := 0
		for id in ["skeleton_soldier", "hollow_sentinel", "crypt_bat", "wandering_ghost", "ghost_archer", "chain_wraith", "ash_hound", "stone_herald"]:
			tipos += 1 if todas.contains(id) else 0
		check.call(tipos >= 7, "pedreira: as ondas variam entre os inimigos que têm arte (%d dos 8)" % tipos)
	if por_id.has("cripta"):
		check.call(str(por_id["cripta"]["boss"]) == "crypt_guardian", "cripta: o chefe continua o Guardião")
		var cripta := JSON.stringify(por_id["cripta"]["waves"])
		check.call(cripta.contains("stone_herald"), "cripta: o Arauto de Pedra voltou às ondas (a folha por código está pronta)")
	m = null

## Regra da direção de arte: nenhuma fase vai ao jogador com a caixa provisória. Toda fase da tabela só pode pôr na tela inimigos
## prontos (stats, as 5 animações com as 5 direções e folhas do tamanho do manifesto): ondas, chefe, enxame e encontros do mapa.
## Quando a folha de um inimigo pendente (ossuary_warden) chegar, ele volta às ondas da Cripta
## (docs/arte/35_pedreira_dos_ecos.md). O ash_hound e o stone_herald já voltaram.
func _testar_arte_das_fases() -> void:
	var fases := Csv.rows("res://data2d/fases_2d.csv")
	check.call(fases.size() >= 2, "arte das fases: a tabela tem %d fases" % fases.size())
	for f in fases:
		var ids := ArteInimigos.usados_na_fase(String(f["onda_fase"]), String(f["sala"]))
		check.call(ids.size() >= 5, "arte da fase %s: %d tipos de inimigo no total" % [f["id"], ids.size()])
		var sem_arte: Array[String] = []
		for id in ids:
			var m := ArteInimigos.motivo(id)
			if m != "":
				sem_arte.append("%s (%s)" % [id, m])
		check.call(sem_arte.is_empty(), "arte da fase %s: só inimigos prontos, sem caixa provisória %s" % [f["id"], str(sem_arte)])

## Regra: aberta sem requisito, ou com a fase exigida vencida, ou com o atalho de dev. Sala ausente = "em breve", sem erro.
func _testar_regra() -> void:
	Fase.tabela = TABELA_TESTE
	Fase.vencidas = []
	Fase.todas_abertas = false
	check.call(Fase.desbloqueada("cripta") and not Fase.desbloqueada("pedreira"), "fases: só a cripta abre num save novo")
	check.call(not Fase.desbloqueada("nao_existe"), "fases: id desconhecido fica trancado")
	Fase.vencidas = ["cripta"]
	check.call(Fase.desbloqueada("pedreira") and Fase.pode_jogar("pedreira"), "fases: vencer a cripta abre a pedreira")
	check.call(Fase.desbloqueada("sem_mapa") and not Fase.disponivel("sem_mapa") and not Fase.pode_jogar("sem_mapa"), "fases: fase sem mapa fica 'em breve'")
	Fase.vencidas = []
	Fase.todas_abertas = true
	check.call(Fase.desbloqueada("pedreira"), "fases: atalho de dev abre todas")
	Fase.todas_abertas = false
	Fase.definir("pedreira")
	check.call(Fase.jogavel() == "cripta", "fases: fase trancada cai na primeira jogável para a corrida")
	Fase.alternar(1)
	check.call(Fase.atual == "sem_mapa", "fases: alternar vai para a seguinte")
	Fase.alternar(1)
	check.call(Fase.atual == "cripta", "fases: alternar dá a volta")
	Fase.alternar(-1)
	check.call(Fase.atual == "sem_mapa", "fases: alternar volta")
	check.call(Fase.abertas_por("cripta") == ["pedreira"] and Fase.abertas_por("pedreira").is_empty(), "fases: vencer a cripta abre a pedreira; a pedreira não abre nada ainda")
	# Tabela real: a Pedreira só fica jogável quando data2d/rooms/fase_2.txt existir.
	Fase.tabela = "res://data2d/fases_2d.csv"
	Fase.vencidas = ["cripta"]
	check.call(Fase.pode_jogar("pedreira") == FileAccess.file_exists("res://data2d/rooms/fase_2.txt"), "fases: a pedreira real joga só com o mapa no disco")
	Fase.tabela = TABELA_TESTE
	Fase.vencidas = []

## Save das fases ao lado do save do meta: save antigo (sem o arquivo) abre sem fases vencidas; vencer e escolher gravam.
func _testar_save() -> void:
	Fase.tabela = TABELA_TESTE
	_limpar()
	var antigo := FileAccess.open(SAVE, FileAccess.WRITE)   # save do meta de antes das fases (sem o arquivo das fases)
	antigo.store_string("{}")
	antigo.close()
	var m = MetaScript.new()
	m.carregar()
	check.call(m.fases_vencidas.is_empty() and Fase.vencidas.is_empty() and Fase.atual == "cripta", "fases: save antigo abre sem fases vencidas e na cripta")
	check.call(m.vencer_fase("cripta") == ["pedreira"], "fases: a primeira vitória na cripta avisa que a pedreira abriu")
	check.call(m.vencer_fase("cripta").is_empty(), "fases: a segunda vitória não avisa de novo")
	m.escolher_fase("pedreira")
	var m2 = MetaScript.new()
	m2.carregar()
	check.call(m2.fases_vencidas == ["cripta"] and m2.fase_escolhida == "pedreira" and Fase.atual == "pedreira", "fases: vencidas e escolhida voltam do save")
	var ruim := FileAccess.open(MetaScript.caminho_fases(), FileAccess.WRITE)
	ruim.store_string("{nao e json")
	ruim.close()
	var m3 = MetaScript.new()
	m3.carregar()
	check.call(m3.fases_vencidas.is_empty() and Fase.atual == "cripta", "fases: arquivo de fases inválido abre como save novo")
	_limpar()

func _botao(m, chave: String) -> Button:
	for c in m._caixa.get_children():
		if c is Button and c.text == Csv.t(chave):
			return c
	return null

## Cartão da fase no título: nome, descrição, setas (mouse e ← →); trancada mostra cadeado e a dica e desativa Jogar.
func _testar_menu() -> void:
	Fase.tabela = TABELA_TESTE
	_limpar()
	var meta = MetaScript.new()
	meta.carregar()
	var m = MenusScript.new()
	m.meta = meta
	t.root.add_child(m)
	await t.process_frame
	m.mostrar_titulo()
	var cartao: Control = m._caixa.find_child("CartaoFase", true, false)
	check.call(cartao != null and m.tela == m.Tela.TITULO, "título: cartão da fase")
	check.call(cartao != null and (cartao.find_child("NomeFase", true, false) as Label).text == Csv.t("fase.cripta.nome"), "título: a cripta aparece escolhida num save novo")
	check.call(cartao != null and cartao.find_child("Cadeado", true, false) == null and cartao.find_child("DicaFase", true, false) == null, "título: cripta aberta sem cadeado nem dica")
	check.call(_botao(m, "menu.play") != null and not _botao(m, "menu.play").disabled, "título: Jogar ativo na cripta")
	(m._caixa.find_child("SetaProxima", true, false) as Button).pressed.emit()
	cartao = m._caixa.find_child("CartaoFase", true, false)
	var dica: Label = cartao.find_child("DicaFase", true, false)
	check.call(Fase.atual == "pedreira" and cartao.find_child("Cadeado", true, false) != null, "título: a seta mostra a pedreira trancada com cadeado")
	check.call(dica != null and dica.text == Csv.t("fase.trancada") % Csv.t("fase.cripta.nome"), "título: dica '%s'" % (dica.text if dica else ""))
	check.call(_botao(m, "menu.play").disabled, "título: Jogar desativado na fase trancada")
	check.call(meta.fase_escolhida == "pedreira", "título: a fase escolhida vai para o save")
	var ev := InputEventKey.new()
	ev.keycode = KEY_RIGHT
	ev.pressed = true
	m._input(ev)
	cartao = m._caixa.find_child("CartaoFase", true, false)
	dica = cartao.find_child("DicaFase", true, false)
	check.call(Fase.atual == "sem_mapa" and cartao.find_child("Cadeado", true, false) == null and dica != null and dica.text == Csv.t("fase.em_breve"), "título: → mostra a fase sem mapa como 'em breve'")
	check.call(_botao(m, "menu.play").disabled, "título: Jogar desativado na fase sem mapa")
	ev.keycode = KEY_LEFT
	m._input(ev)
	check.call(Fase.atual == "pedreira", "título: ← volta para a pedreira")
	meta.vencer_fase("cripta")
	m.mostrar_titulo()
	cartao = m._caixa.find_child("CartaoFase", true, false)
	check.call(cartao.find_child("Cadeado", true, false) == null and not _botao(m, "menu.play").disabled, "título: com a cripta vencida a pedreira abre e Jogar ativa")
	m.mostrar_fim(true, ["linha"], [Csv.t("fase.desbloqueada") % Csv.t("fase.pedreira.nome")])
	var avisos: Control = m._caixa.find_child("AvisosFim", true, false)
	check.call(m.tela == m.Tela.FIM and avisos != null and (avisos.get_child(0) as Label).text == "Pedreira dos Ecos desbloqueada!", "fim: aviso de fase desbloqueada")
	m.mostrar_fim(true, ["Tempo: 01:00", "Onda alcançada: 2 de 8", "Fragmentos ganhos: 3", "Materiais: Osso Antigo x13, Núcleo de Estilhaço x1, Essência Etérea x3"])
	var grade: GridContainer = m._caixa.find_child("Grade", true, false)
	check.call(grade != null and grade.columns == 2 and grade.get_child_count() == 2, "fim: resumo em duas colunas (linha ímpar e linha comprida fora da grade)")
	m.mostrar_fim(true, ["linha"])
	check.call(m._caixa.find_child("AvisosFim", true, false) == null, "fim: sem fase nova, sem aviso")
	m.queue_free()
	await t.process_frame
	_limpar()

## Corrida na Pedreira (sala de fase_1.txt pela tabela de teste) e o elite do portão do começo ao portal.
func _testar_corrida_e_elite() -> void:
	Fase.tabela = TABELA_TESTE
	_limpar()
	var meta = MetaScript.new()
	meta.carregar()
	meta.escolher_fase("pedreira")
	Fase.todas_abertas = true   # a cripta ainda não foi vencida: a vitória nela, no fim, precisa avisar
	var etapas_antes: bool = RunScript.modo_etapas
	RunScript.modo_etapas = false
	var run = RunScene.instantiate()
	run.com_menu = false
	t.root.add_child(run)
	await t.physics_frame
	var p = run.player
	p.god_mode = true
	p.autocast = false
	check.call(run.fase_id == "pedreira" and run.fase_horda == "pedreira" and run.horda, "corrida: usa a fase escolhida e a fase do spawner dela")
	check.call(str(run.nucleo.ondas_estado().get("phase", "")) == "pedreira", "corrida: o core roda as ondas da pedreira")
	check.call(run.room.aberta() and run.room.posicao_chefe != Vector2.ZERO, "corrida: sala da tabela (fase_1.txt na tabela de teste)")
	check.call(run.chefe_elite, "corrida: o chefe da pedreira é um elite do portão")
	await _esperar(func():
		run._tick_horda(2.0)
		run.matar_todos()
		_escolher_tudo(run)
		return int(run.nucleo.ondas_estado()["can_wake"]) == 0, 40.0)
	check.call(int(run.nucleo.ondas_estado()["can_wake"]) == 0, "elite: o portão pode ser despertado na onda %d" % run.onda)
	run.matar_todos()
	_escolher_tudo(run)
	await t.physics_frame
	p.global_position = run.room.posicao_chefe + Vector2(0, 120)
	await _esperar(func(): return run.nucleo.ondas_estado()["boss_spawned"], 3.0)
	_escolher_tudo(run)
	var e = null
	for n in t.get_nodes_in_group("hurtable"):
		if n.has_meta("chefe_portao"):
			e = n
	check.call(e != null, "elite: o capitão nasce quando o jogador chega ao portão")
	if e == null:
		run.queue_free()
		await t.process_frame
		RunScript.modo_etapas = etapas_antes
		return
	var cfg: Dictionary = run.config
	var base: Dictionary = Csv.enemy("ossuary_captain")
	check.call(e.get_script() == EnemyScript and e.stats["kind"] == "melee", "elite: IA comum (não o script do Guardião) e o kind real guardado")
	check.call(e.global_position.distance_to(run.room.posicao_chefe) < 1.0, "elite: nasce no lugar do chefe")
	check.call(e.has_meta("elite") and e.modulate == Color.WHITE and e.scale == Vector2.ONE, "elite: conta como elite, sem o tom dourado nem a escala dos elites de onda")
	var f := float(cfg["gate_elite_scale"])
	var forma: CircleShape2D = null
	for c in e.get_children():
		if c is CollisionShape2D:
			forma = c.shape
	check.call(is_equal_approx(e.escala_extra, f) and is_equal_approx(float(e.stats["radius"]), float(base["radius"]) * f) and forma != null and is_equal_approx(forma.radius, float(e.stats["radius"])), "elite: escala %.1f no sprite e no raio de colisão" % f)
	check.call(absf(e.sprite.scale.x - e._esc_base * f) < 0.01, "elite: sprite %.2f x" % (e.sprite.scale.x / e._esc_base))
	check.call(is_equal_approx(e.hp_max, run.nucleo.vida_chefe(float(base["hp"]), run.dps_medido)), "elite: vida adaptativa do core (%.0f)" % e.hp_max)
	check.call(run.hud.chefe == e and run.hud.chefe_nome == "enemy.ossuary_captain.name", "elite: barra grande da HUD com o nome dele")
	var y_barra := float(run.hud._lay["chefe_elite_y"])
	check.call(y_barra >= 40.0 and y_barra <= 60.0, "elite: a barra desce da faixa do topo (y %.0f) e deixa o nome com placa à vista" % y_barra)
	var halo: Sprite2D = e.get_node_or_null("LuzDoElite")
	check.call(halo != null and halo.show_behind_parent, "elite: a luz própria fica atrás do sprite (não pinta o osso de laranja)")
	check.call(run.room.find_child("ClaraoPortao", true, false) != null, "elite: clarão de luz no portão")
	check.call(e.invulneravel(), "elite: entra invulnerável")
	var hp0: float = e.hp
	var pos0: Vector2 = e.global_position
	e.take_damage(10.0, p.global_position)
	await t.physics_frame
	check.call(e.hp == hp0 and e.global_position.distance_to(pos0) < 1.0, "elite: na entrada não leva dano nem anda")
	await _esperar(func(): return not e.invulneravel(), float(cfg["gate_elite_intro"]) + 2.0)
	check.call(not e.invulneravel(), "elite: a entrada acaba")
	await _esperar(func(): return run.room.find_child("ClaraoPortao", true, false) == null, 2.0)
	check.call(run.room.find_child("ClaraoPortao", true, false) == null, "elite: o clarão some")
	e.take_damage(5.0, p.global_position)
	check.call(e.hp < hp0, "elite: depois da entrada leva dano")
	p.global_position = run.room.posicao_chefe + Vector2(0, 400)
	var d0: float = e.global_position.distance_to(p.global_position)
	for i in 30:
		await t.physics_frame
	check.call(e.global_position.distance_to(p.global_position) < d0 - 5.0, "elite: depois da entrada persegue o jogador")
	run.matar_todos()
	await t.physics_frame
	await _esperar(func(): return run.estado == run.Estado.LIMPA, 4.0)
	_escolher_tudo(run)
	check.call(run.hud.chefe == null, "elite: a barra some quando ele morre")
	check.call(run.estado == run.Estado.LIMPA and run.posicao_saida() != Vector2.ZERO, "elite: a morte dele abre o portal")
	check.call(run.hud.mensagem == Csv.t("hud.gate_open"), "elite: aviso do portal com o texto do portão")
	await t.physics_frame
	p.global_position = run.posicao_saida()
	await _esperar(func(): return run.estado == run.Estado.VENCEU, 4.0)
	check.call(run.estado == run.Estado.VENCEU and run.meta.fases_vencidas.has("pedreira"), "elite: o portal dá a vitória e a pedreira fica vencida")
	await _esperar(func(): return run.menus.tela == run.menus.Tela.FIM, 5.0)
	check.call(run.menus.tela == run.menus.Tela.FIM and run.menus._caixa.find_child("AvisosFim", true, false) == null, "fim: vencer a pedreira não abre fase nova")
	# Primeira vitória na cripta: o aviso sai na tela de fim, uma vez.
	run._fases_novas = run.meta.vencer_fase("cripta")
	run.estado = run.Estado.VENCEU
	run._mostrar_fim()
	var avisos: Control = run.menus._caixa.find_child("AvisosFim", true, false)
	check.call(avisos != null and (avisos.get_child(0) as Label).text == Csv.t("fase.desbloqueada") % Csv.t("fase.pedreira.nome"), "fim: a primeira vitória na cripta avisa a pedreira desbloqueada")
	check.call(run.meta.vencer_fase("cripta").is_empty(), "fim: o aviso não se repete")
	t.paused = false
	run.queue_free()
	await t.process_frame
	RunScript.modo_etapas = etapas_antes
