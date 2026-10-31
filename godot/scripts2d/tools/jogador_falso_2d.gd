extends Node2D
## Jogador mínimo para testar habilidades_2d.gd sem cena.

var mana := 0.0
var stats := {"skill_cd_mult": 1.0}

func gastar_mana(n: float) -> void:
	mana = maxf(0.0, mana - n)
