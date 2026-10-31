extends RefCounted
## Efeitos de mentira para o teste de habilidades_2d.gd: guarda a última chamada.

static var ultimo := {}

static func executar(efeito: String, _jogador: Node2D, def: Dictionary, nivel: int, mira: Vector2) -> bool:
	ultimo = {"efeito": efeito, "dano": def["dano"], "nivel": nivel, "mira": mira}
	return efeito != "recusa"
