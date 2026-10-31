extends RefCounted
## Classe jogável escolhida (arqueiro ou guerreiro). Vale para a próxima corrida; o título alterna.
## Também aceita `-- --classe=guerreiro` na linha de comando (testes e bot).

const CLASSES := ["arqueiro", "guerreiro"]

static var atual := "arqueiro"

static func ler_argumentos() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--classe="):
			var c := a.trim_prefix("--classe=")
			if CLASSES.has(c):
				atual = c

static func alternar() -> void:
	atual = CLASSES[(CLASSES.find(atual) + 1) % CLASSES.size()]
