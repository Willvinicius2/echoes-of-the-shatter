extends RefCounted
## Comandos de playtest para o console do LimboConsole (tecla ` ). Só existem em build de debug:
## o run_2d.gd só cria isto com OS.is_debug_build(). Nada daqui calcula regra do jogo.
##   god                  liga/desliga invencibilidade
##   curar                enche a vida
##   matar                mata todos os inimigos vivos
##   horda <id> <n>       nasce n inimigos do id (enemies.csv) em volta do jogador
##   sala <n>             vai para a sala n (começa em 0)
##   status               mostra posição e vida

const Csv = preload("res://scripts2d/csv2d.gd")
const EnemyScript = preload("res://scripts2d/enemy_2d.gd")

var run: Node

func _init(p_run: Node) -> void:
	run = p_run

func registrar() -> bool:
	var con: Node = run.get_node_or_null("/root/LimboConsole")
	if con == null:
		return false
	con.overwrite_command(god, "god", "liga/desliga invencibilidade")
	con.overwrite_command(curar, "curar", "enche a vida do jogador")
	con.overwrite_command(matar, "matar", "mata todos os inimigos vivos")
	con.overwrite_command(horda, "horda", "horda <id> <n>: nasce n inimigos em volta do jogador")
	con.overwrite_command(sala, "sala", "sala <n>: vai para a sala n (0 = primeira)")
	con.overwrite_command(status, "status", "posição e vida do jogador")
	con.add_argument_autocomplete_source("horda", 0, ids_inimigos)
	return true

static func ids_inimigos() -> Array:
	return Csv.rows("res://data2d/enemies.csv").map(func(r): return r["id"])

func _info(txt: String) -> void:
	var con: Node = run.get_node_or_null("/root/LimboConsole")
	if con != null:
		con.info(txt)

func god() -> void:
	run.player.god_mode = not run.player.god_mode
	_info("god mode: %s" % run.player.god_mode)

func curar() -> void:
	run.player.hp = run.player.stats["hp_max"]
	run.player.hp_changed.emit(run.player.hp, run.player.stats["hp_max"])

func matar() -> void:
	run.matar_todos()

func horda(id: String, n: int) -> void:
	_info("%d x %s" % [spawnar_horda(run, id, n), id])

func sala(n: int) -> void:
	run._carregar_sala(clampi(n, 0, run.salas.size() - 1))

func status() -> void:
	_info("pos %s  hp %.0f/%.0f  inimigos %d" % [run.player.global_position, run.player.hp, run.player.stats["hp_max"], run.get_tree().get_nodes_in_group("hurtable").size()])

## Nasce `n` inimigos do tipo `id` num anel em volta do jogador. Não liga o sinal `died` ao
## run (a contagem de sala do core não conhece esses extras). Devolve quantos nasceram.
static func spawnar_horda(p_run: Node, id: String, n: int, raio_min := 300.0, raio_max := 700.0) -> int:
	if not Csv.enemy(id).has("hp"):
		return 0
	var rng := RandomNumberGenerator.new()
	rng.seed = 12345
	for i in n:
		var e: Node2D = EnemyScript.new()
		p_run.atores.add_child(e)
		var ang := rng.randf() * TAU
		var pos: Vector2 = p_run.player.global_position + Vector2.RIGHT.rotated(ang) * rng.randf_range(raio_min, raio_max)
		e.setup(id, p_run.player, pos)
	return n
