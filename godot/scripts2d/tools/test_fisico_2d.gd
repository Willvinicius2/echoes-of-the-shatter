extends RefCounted
## Testes das habilidades físicas do Arqueiro com identidade própria (doc 39): cada uma tem de mostrar a sua mecânica,
## não só "feriu alguém". Chamado pelo test_2d.gd.
const Efeitos = preload("res://scripts2d/efeitos_arqueiro_2d.gd")
const Csv = preload("res://scripts2d/csv2d.gd")

var arv: SceneTree
var check: Callable
var mundo: Node2D
var p: Node2D

func _init(a: SceneTree, c: Callable) -> void:
	arv = a
	check = c

func _passos(n: int) -> void:
	for i in n:
		await arv.physics_frame

func _palco() -> void:
	if mundo != null:
		mundo.queue_free()
		await arv.physics_frame
	mundo = Node2D.new()
	arv.root.add_child(mundo)
	p = load("res://scripts2d/player_2d.gd").new()
	p.god_mode = true
	p.autocast = false
	p.auto_aim = Vector2.RIGHT
	mundo.add_child(p)
	await arv.physics_frame

func _inimigo(pos: Vector2, hp := 100000.0) -> Node2D:
	var e = load("res://scripts2d/enemy_2d.gd").new()
	mundo.add_child(e)
	e.setup("hollow_sentinel", p, p.global_position + pos)
	e.hp_max = hp
	e.hp = hp
	e._speed = 0.0
	return e

func _def(id: String) -> Dictionary:
	for r in Csv.rows("res://data2d/habilidades_arqueiro.csv"):
		if r["id"] == id:
			var d: Dictionary = r.duplicate()
			for c in ["dano", "qtd", "angulo", "raio", "duracao", "alcance", "valor"]:
				d[c] = float(r[c]) if str(r[c]) != "" else 0.0
			return d
	return {}

func _usar(id: String) -> bool:
	var d := _def(id)
	return Efeitos.executar(d["efeito"], p, d, 1, Vector2.RIGHT)

func rodar() -> void:
	# Virote de Cerco: atravessa, arrasta para longe do arqueiro e atordoa ao cravar
	await _palco()
	var a := _inimigo(Vector2(150, 0))
	var b := _inimigo(Vector2(230, 0))
	var xa: float = a.global_position.x
	check.call(_usar("power_shot"), "virote: executa")
	await _passos(40)
	check.call(a.hp < a.hp_max and b.hp < b.hp_max, "virote: atravessa os dois da fila")
	check.call(a.global_position.x > xa + 20.0, "virote: arrasta o atingido na direção do voo")
	# Tiro Certeiro: espera a mira e acerta o de maior vida com dano maior
	await _palco()
	var fraco := _inimigo(Vector2(200, 0), 50000.0)
	var forte := _inimigo(Vector2(200, 160), 100000.0)
	_usar("sniper_shot")
	await _passos(4)
	check.call(is_equal_approx(forte.hp, forte.hp_max), "tiro certeiro: mira antes de atirar")
	await _passos(50)
	check.call((forte.hp_max - forte.hp) > 10.0 * (fraco.hp_max - fraco.hp), "tiro certeiro: vai no inimigo de maior vida, não no mais perto (o básico do arqueiro fere o outro com pouco)")
	# Revoada: cada flecha busca um inimigo diferente, mesmo fora da linha da mira
	await _palco()
	var alvos := [_inimigo(Vector2(220, -200)), _inimigo(Vector2(260, 0)), _inimigo(Vector2(220, 200))]
	_usar("rapid_volley")
	await _passos(90)
	check.call(alvos.all(func(e): return e.hp < e.hp_max), "revoada: as flechas se repartem entre os três inimigos")
	# Leque de Lâminas: fere na ida e de novo na volta
	await _palco()
	var e1 := _inimigo(Vector2(180, 0))
	_usar("fan_of_arrows")
	await _passos(20)
	var depois_ida: float = e1.hp
	await _passos(100)
	check.call(depois_ida < e1.hp_max and e1.hp < depois_ida, "lâminas: ferem na ida e na volta")
	check.call(mundo.get_children().filter(func(c): return c.get("_volta") != null).is_empty(), "lâminas: voltam ao arqueiro e somem")
	# Chuva de Flechas: prende (lentidão) quem é atingido
	await _palco()
	var e2 := _inimigo(Vector2(280, 0))
	_usar("arrow_rain")
	await _passos(60)
	check.call(e2.hp < e2.hp_max and e2.tem_status("lentidao"), "chuva: fere e deixa lento")
	# Armadilha de Mandíbulas: puxa para o centro quem está no raio
	await _palco()
	var e3 := _inimigo(Vector2(280, 0))
	var e4 := _inimigo(Vector2(350, 0))
	_usar("spike_trap")
	await _passos(45)
	check.call(e3.atordoado > 0.0 and e4.atordoado > 0.0 and e4.hp < e4.hp_max, "armadilha: fecha, fere e atordoa todos no raio")
	# Flecha de Estilhaços: o miolo e as bombas do anel ferem em lugares diferentes
	await _palco()
	var centro := _inimigo(Vector2(420, 0))
	var borda := _inimigo(Vector2(420, 85))
	_usar("explosive_arrow")
	await _passos(100)
	check.call(centro.hp < centro.hp_max and borda.hp < borda.hp_max, "estilhaços: miolo e bombas do anel ferem")
	# Marca do Caçador: marca e, se o marcado morre, passa ao vizinho
	await _palco()
	var m1 := _inimigo(Vector2(250, 0), 500.0)
	var m2 := _inimigo(Vector2(330, 60))
	check.call(_usar("hunters_mark"), "marca: executa com alvo na mira")
	await _passos(40)
	check.call(m1.tem_status("marca") and not m2.tem_status("marca"), "marca: o falcão marca só o alvo mirado")
	m1.take_damage(1.0e6, p.global_position)
	await _passos(60)
	check.call(m2.tem_status("marca"), "marca: salta para o vizinho quando o marcado morre")
	# Salto das Sombras: o duplo estoura em quem encosta
	await _palco()
	var e5 := _inimigo(Vector2(30, 0))
	_usar("backstep_shot")
	await _passos(40)
	check.call(e5.hp < e5.hp_max, "salto das sombras: o duplo estoura em quem encosta")
	# Bomba de Fumaça: lentidão nos inimigos e proteção para o arqueiro dentro dela
	await _palco()
	var e6 := _inimigo(Vector2(245, 0))
	_usar("smoke_bomb")
	await _passos(40)
	p.global_position = e6.global_position + Vector2(0, 40)
	p.invencivel = 0.0
	await _passos(3)
	check.call(e6.tem_status("lentidao") and p.invencivel > 0.0, "fumaça: inimigos lentos e arqueiro protegido dentro dela")
	# Adrenalina: a onda de choque afasta quem está colado
	await _palco()
	var e7 := _inimigo(Vector2(60, 0))
	var x7: float = e7.global_position.x
	_usar("adrenaline")
	await _passos(20)
	check.call(p.cad_buff > 1.0 and e7.global_position.x > x7 + 10.0, "adrenalina: acelera e empurra quem está em volta")
	mundo.queue_free()
	await arv.physics_frame
