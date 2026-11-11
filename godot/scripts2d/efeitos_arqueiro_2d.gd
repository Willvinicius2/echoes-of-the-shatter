extends RefCounted
## Efeitos das habilidades ativas do Arqueiro (data2d/habilidades_arqueiro.csv). O `def` chega escalonado pelo nível;
## `mira` é a direção da mira. Devolve true se gastou a habilidade (entra em recarga) e false se cancelou.

const Veneno = preload("res://scripts2d/efeitos_arqueiro_veneno_2d.gd")
const Gelo = preload("res://scripts2d/efeitos_arqueiro_gelo_2d.gd")
const Fogo = preload("res://scripts2d/efeitos_arqueiro_fogo_2d.gd")
const Raio = preload("res://scripts2d/efeitos_arqueiro_raio_2d.gd")
const ExtraRaio = preload("res://scripts2d/efeitos_extra_raio_2d.gd")
const ExtraVeneno = preload("res://scripts2d/efeitos_extra_veneno_2d.gd")
const ExtraGelo = preload("res://scripts2d/efeitos_extra_gelo_2d.gd")
const ExtraFogo = preload("res://scripts2d/efeitos_extra_fogo_2d.gd")
const Fisico = preload("res://scripts2d/efeitos_arqueiro_fisico_2d.gd")
const Sombra = preload("res://scripts2d/efeitos_arqueiro_sombra_2d.gd")

static func executar(efeito: String, jogador: Node2D, def: Dictionary, nivel: int, mira: Vector2) -> bool:
	if jogador == null or not jogador.is_inside_tree() or jogador.esta_morto():
		return false
	match efeito:
		"tiro_forte", "tiro_certeiro", "rajada", "leque", "chuva", "armadilha", "explosiva", "marca":
			return Fisico.executar(efeito, jogador, def, mira)
		"salto", "fumaca", "furia":
			return Sombra.executar(efeito, jogador, def, mira)
		"tiro_veneno", "bola_veneno", "chuva_corrosiva", "tornado_toxico":
			return Veneno.executar(efeito, jogador, def, nivel, mira)
		"gelo_flecha", "gelo_estilhaco", "gelo_prisao", "cometa_gelo", "nova_gelo":
			return Gelo.executar(efeito, jogador, def, nivel, mira)
		"tiro_ardente", "meteoro", "muralha", "serpente_fogo":
			return Fogo.executar(efeito, jogador, def, nivel, mira)
		"flecha_eletrica", "raio_encadeado", "tornado", "haste_eletrica":
			return Raio.executar(efeito, jogador, def, nivel, mira)
		"trovoada", "tempestade_raios", "orbes_tempestade":
			return ExtraRaio.executar(efeito, jogador, def, mira)
		"contagio", "minas_toxicas", "geiser_acido":
			return ExtraVeneno.executar(efeito, jogador, def, mira)
		"lanca_gelo", "espinhos_gelo", "nevasca":
			return ExtraGelo.executar(efeito, jogador, def, mira)
		"sopro_chamas", "anel_fogo", "bomba_rastilho":
			return ExtraFogo.executar(efeito, jogador, def, mira)
		_:
			push_error("Efeito de arqueiro desconhecido: " + efeito)
			return false
	return true
