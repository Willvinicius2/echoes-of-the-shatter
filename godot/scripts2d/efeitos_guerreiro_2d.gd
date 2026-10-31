extends RefCounted
## Efeitos das habilidades ativas do Guerreiro (contrato do sistema de habilidades).
## `executar` começa a habilidade; as com tempo de preparo, investida e salto rodam como estado do jogador
## (warrior_2d.gd) e chamam `aplicar` no momento do efeito. Números vêm de data2d/habilidades_guerreiro.csv.

const Feel = preload("res://scripts2d/feel_2d.gd")

const COR_LAMINA := Color(0.95, 0.92, 0.8)
const COR_FOGO := Color(1.0, 0.55, 0.2)
const COR_ESCUDO := Color(0.35, 0.65, 0.95)
const COR_FURIA := Color(0.9, 0.25, 0.2)
const COR_PEDRA := Color(0.75, 0.6, 0.4)

## true = consumiu recarga e custo; false = cancelou.
static func executar(efeito: String, jogador: Node2D, def: Dictionary, nivel: int, mira: Vector2) -> bool:
	if jogador.estado != jogador.Estado.LIVRE:
		return false
	match efeito:
		"investida":
			jogador.comecar_investida(def, mira, nivel)
		"salto_sismico":
			jogador.comecar_salto(def, mira, nivel)
		"golpe_pesado", "redemoinho", "fenda_pedra", "escudada", "grito_guerra", "furia":
			jogador.comecar_conjuracao(efeito, def, mira, nivel)
		_:
			return false
	return true

## Aplica o efeito no instante certo (fim do preparo, ou ao pousar no salto).
static func aplicar(efeito: String, j: Node2D, d: Dictionary, nivel: int, mira: Vector2) -> void:
	match efeito:
		"golpe_pesado":
			for a in j.alvos_cone(j.global_position, mira, d["raio"], d["angulo"]):
				j.acertar(a, d["dano"])
			j.fx_arco(mira.angle(), d["raio"], deg_to_rad(d["angulo"]), 0.25, COR_FOGO)
			Feel.shake(j, 4.0, 0.15)
		"redemoinho":
			for a in j.alvos_cone(j.global_position, mira, d["raio"], 360.0):
				j.acertar(a, d["dano"])
			j.fx_arco(0.0, d["raio"], TAU, 0.3, COR_LAMINA)
			Feel.shake(j, 3.0, 0.12)
		"fenda_pedra":
			for a in j.alvos_retangulo(j.global_position, mira, d["alcance"], d["raio"]):
				j.acertar(a, d["dano"])
			j.fx_faixa(mira.angle(), d["alcance"], d["raio"], 0.4, COR_PEDRA)
			Feel.shake(j, 5.0, 0.2)
		"escudada":
			for a in j.alvos_cone(j.global_position, mira, d["raio"], d["angulo"]):
				j.acertar(a, d["dano"], d["duracao"])
			j.velocity += mira * 220.0
			j.fx_arco(mira.angle(), d["raio"], deg_to_rad(d["angulo"]), 0.2, COR_ESCUDO)
			Feel.shake(j, 3.0, 0.1)
		"grito_guerra":
			j.buff_grito(d["duracao"], d["valor"])
			for a in j.alvos_cone(j.global_position, mira, d["raio"], 360.0):
				j.aplicar_status(a, "atordoamento", 0.5)
				a.take_damage(1.0, j.global_position)  # só empurra: o dano é simbólico
			j.fx_arco(0.0, d["raio"], TAU, 0.45, COR_FURIA)
		"furia":
			j.buff_furia(d["duracao"], d["valor"])
			j.fx_arco(0.0, 110.0, TAU, 0.5, COR_FURIA)
			Feel.shake(j, 6.0, 0.25)
		"investida":
			j.fx_arco(mira.angle(), 50.0, 1.4, 0.15, COR_FOGO)
		"salto_sismico":
			for a in j.alvos_cone(j.global_position, mira, d["raio"], 360.0):
				j.acertar(a, d["dano"], maxf(d["valor"], 1.0))
			j.fx_arco(0.0, d["raio"], TAU, 0.4, COR_PEDRA)
			Feel.shake(j, 7.0, 0.25)
