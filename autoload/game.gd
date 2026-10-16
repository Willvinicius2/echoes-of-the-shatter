extends Node
## Estado global da partida: seed da run, fluxos de RNG e opções de apresentação.

var seed_value: int = 20261015
var rng: RngStreams = RngStreams.new(20261015)
## Flag para desligar o tremor de tela.
var shake_enabled: bool = true


func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--seed="):
			new_run(int(arg.substr(7)))


func new_run(p_seed: int) -> void:
	seed_value = p_seed
	rng = RngStreams.new(p_seed)
