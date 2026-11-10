extends RefCounted
## Testes das reações elementais (docs/design/38_reacoes_elementais.md), chamados por test_2d.gd.

const Reacoes = preload("res://scripts2d/reacoes_2d.gd")
const Gelo = preload("res://scripts2d/efeitos_arqueiro_gelo_2d.gd")

var t: SceneTree
var check: Callable

func _init(arvore: SceneTree, verifica: Callable) -> void:
	t = arvore
	check = verifica

func _inimigo(mundo: Node2D, p: Node2D, pos: Vector2) -> Node2D:
	var e = load("res://scripts2d/enemy_2d.gd").new()
	mundo.add_child(e)
	e.setup("hollow_sentinel", p, pos)
	e.hp = 100000.0
	e.hp_max = 100000.0
	e.stats["aggro"] = 0.0
	return e

func rodar() -> void:
	check.call(Reacoes.defs().size() == 7, "sete reações no CSV (%d)" % Reacoes.defs().size())
	var mundo := Node2D.new()
	t.root.add_child(mundo)
	var p = load("res://scripts2d/player_2d.gd").new()
	p.god_mode = true
	p.autocast = false
	mundo.add_child(p)
	await t.physics_frame
	var base := Vector2(900, 900)
	# vapor: queimadura em alvo com frio
	var a := _inimigo(mundo, p, base)
	var viz := _inimigo(mundo, p, base + Vector2(60, 0))
	a.set_meta("frio_acumulos", 2)
	a.aplicar_status("lentidao", 3.0, 0.3)
	var hp0: float = viz.hp
	a.aplicar_status("queimadura", 3.0, 2.0)
	check.call(viz.hp < hp0 and not a.tem_status("lentidao") and int(a.get_meta("frio_acumulos", 0)) == 0, "vapor: queimadura em alvo com frio fere em área e apaga o frio")
	check.call(a.tem_status("queimadura"), "vapor: a queimadura continua")
	# recarga: a segunda não dispara em cadeia
	var hp1: float = viz.hp
	a.set_meta("frio_acumulos", 2)
	a.aplicar_status("lentidao", 3.0, 0.3)
	a.aplicar_status("queimadura", 3.0, 2.0)
	check.call(is_equal_approx(viz.hp, hp1), "reação tem recarga por inimigo")
	# choque térmico: frio em alvo queimando
	var b := _inimigo(mundo, p, base + Vector2(0, 400))
	var vb := _inimigo(mundo, p, base + Vector2(60, 400))
	b.aplicar_status("queimadura", 3.0, 2.0)
	var hb: float = vb.hp
	b.set_meta("frio_acumulos", 1)
	b.aplicar_status("lentidao", 3.0, 0.2)
	check.call(vb.hp < hb and not b.tem_status("queimadura"), "choque térmico: frio em alvo queimando apaga a queimadura e fere em área")
	# gás inflamado
	var c := _inimigo(mundo, p, base + Vector2(0, 800))
	var vc := _inimigo(mundo, p, base + Vector2(60, 800))
	c.aplicar_status("veneno", 3.0, 5.0)
	var hc: float = vc.hp
	c.aplicar_status("queimadura", 3.0, 2.0)
	check.call(vc.hp < hc and not c.tem_status("veneno"), "gás inflamado: queimadura em alvo envenenado explode e consome o veneno")
	# quebra gélida
	var d := _inimigo(mundo, p, base + Vector2(0, 1200))
	var vd := _inimigo(mundo, p, base + Vector2(60, 1200))
	Gelo.congelar(d, 3.0)
	var hd: float = vd.hp
	d.aplicar_status("choque", 3.0, 0.15)
	check.call(vd.hp < hd and not Reacoes.sob(d, "congelado") and vd.tem_status("lentidao"), "quebra gélida: choque em alvo congelado estilhaça o gelo")
	# corrente tóxica
	var e := _inimigo(mundo, p, base + Vector2(0, 1600))
	var ve := _inimigo(mundo, p, base + Vector2(120, 1600))
	e.aplicar_status("veneno", 3.0, 5.0)
	e.aplicar_status("choque", 3.0, 0.15)
	check.call(ve.tem_status("veneno"), "corrente tóxica: choque em alvo envenenado passa o veneno ao vizinho")
	# sem a condição não reage
	var f := _inimigo(mundo, p, base + Vector2(0, 2000))
	var vf := _inimigo(mundo, p, base + Vector2(60, 2000))
	var hf: float = vf.hp
	f.aplicar_status("queimadura", 3.0, 2.0)
	f.aplicar_status("choque", 3.0, 0.15)
	check.call(is_equal_approx(vf.hp, hf), "sem combinação não há reação")
	# resistências por inimigo
	var osso = load("res://scripts2d/enemy_2d.gd").new()
	mundo.add_child(osso)
	osso.setup("skeleton_soldier", p, base + Vector2(0, 2400))
	osso.aplicar_status("veneno", 3.0, 5.0)
	check.call(not osso.tem_status("veneno"), "esqueleto é imune a veneno")
	osso.aplicar_status("choque", 3.0, 0.2)
	check.call(osso.tem_status("choque") and is_equal_approx(osso._status["choque"]["v"], 0.26), "esqueleto conduz mais o choque (x1.3)")
	var cao = load("res://scripts2d/enemy_2d.gd").new()
	mundo.add_child(cao)
	cao.setup("ash_hound", p, base + Vector2(0, 2600))
	cao.aplicar_status("queimadura", 4.0, 10.0)
	check.call(is_equal_approx(cao._status["queimadura"]["v"], 3.0) and cao._status["queimadura"]["t"] < 1.3, "cão de cinzas resiste ao fogo (x0.3)")
	# água: sala falsa no grupo sala_2d
	var agua := Node2D.new()
	agua.set_script(preload("res://scripts2d/tools/sala_falsa_agua_2d.gd"))
	agua.add_to_group("sala_2d")
	mundo.add_child(agua)
	var g := _inimigo(mundo, p, base + Vector2(0, 2800))
	var vg := _inimigo(mundo, p, base + Vector2(60, 2800))
	var hg: float = vg.hp
	g.aplicar_status("choque", 3.0, 0.15)
	check.call(vg.hp < hg and vg.tem_status("choque"), "condução na água: choque corre até o vizinho que também está na água")
	var h := _inimigo(mundo, p, base + Vector2(0, 3200))
	h.aplicar_status("queimadura", 3.0, 2.0)
	check.call(not h.tem_status("queimadura"), "apagar fogo: a água impede a queimadura")
	agua.remove_from_group("sala_2d")   # queue_free só vale no fim do quadro; sem isto a água falsa ainda responderia
	agua.queue_free()
	# dicas de resistência junto da barra de vida
	var dc: Array = Reacoes.dicas("skeleton_soldier")
	check.call(dc.size() == 2 and dc[0]["el"] == "raio" and dc[1]["m"] == 0.0, "dicas: esqueleto sofre mais raio e é imune a veneno")
	check.call(Reacoes.dicas("hollow_sentinel").is_empty() and cao._dicas.size() == 2, "dicas: sentinela sem dica; cão mostra fogo e gelo")
	# mapa: braseiros e pilares reagem (sala falsa com um braseiro em (900,4000) e um pilar em (900,4400))
	var mapa := Node2D.new()
	mapa.set_script(preload("res://scripts2d/tools/sala_falsa_mapa_2d.gd"))
	mapa.add_to_group("sala_2d")
	mundo.add_child(mapa)
	check.call(Reacoes.defs_mapa().size() == 4, "quatro reações do mapa no CSV")
	var m1 := _inimigo(mundo, p, Vector2(900, 4040))
	var m2 := _inimigo(mundo, p, Vector2(960, 4040))
	var hm: float = m2.hp
	m1.aplicar_status("queimadura", 3.0, 2.0)
	check.call(m2.hp < hm and m2.tem_status("queimadura"), "braseiro + fogo: labareda queima quem está em volta")
	var hm2: float = m2.hp
	var m3 := _inimigo(mundo, p, Vector2(930, 4040))
	m3.aplicar_status("queimadura", 3.0, 2.0)
	check.call(is_equal_approx(m2.hp, hm2), "braseiro tem recarga própria")
	mapa._estruturas[0]["ate"] = 0
	var m4 := _inimigo(mundo, p, Vector2(900, 3960))
	var m5 := _inimigo(mundo, p, Vector2(960, 3960))
	m4.aplicar_status("choque", 3.0, 0.15)
	check.call(m1.tem_status("choque") and m3.tem_status("choque") and not m5.tem_status("choque"), "braseiro + raio: descarga choca os 2 vizinhos mais próximos do braseiro")
	mapa._estruturas[0]["ate"] = 0
	var m6 := _inimigo(mundo, p, Vector2(900, 4060))
	m6.set_meta("frio_acumulos", 1)
	m6.aplicar_status("lentidao", 3.0, 0.2)
	check.call(int(mapa._estruturas[0]["apagado"]) > Time.get_ticks_msec(), "braseiro + gelo: apaga o braseiro")
	mapa._estruturas[0]["ate"] = 0
	var m7 := _inimigo(mundo, p, Vector2(930, 4080))
	var m8 := _inimigo(mundo, p, Vector2(990, 4080))
	var hm8: float = m8.hp
	m7.aplicar_status("queimadura", 3.0, 2.0)
	check.call(is_equal_approx(m8.hp, hm8), "braseiro apagado não reage")
	var q1 := _inimigo(mundo, p, Vector2(900, 4440))
	var q2 := _inimigo(mundo, p, Vector2(1000, 4440))
	var hq: float = q2.hp
	q1.aplicar_status("choque", 3.0, 0.15)
	check.call(q2.hp < hq and q2.tem_status("choque"), "pilar + raio: para-raios descarrega no vizinho")
	var far := _inimigo(mundo, p, Vector2(2500, 4440))
	var fv := _inimigo(mundo, p, Vector2(2560, 4440))
	var hf2: float = fv.hp
	far.aplicar_status("choque", 3.0, 0.15)
	check.call(is_equal_approx(fv.hp, hf2), "longe de braseiro e pilar nada reage")
	mapa.queue_free()
	mundo.queue_free()
	await t.physics_frame
