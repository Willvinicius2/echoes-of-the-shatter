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
	check.call(Reacoes.defs().size() == 5, "cinco reações no CSV (%d)" % Reacoes.defs().size())
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
	mundo.queue_free()
	await t.physics_frame
