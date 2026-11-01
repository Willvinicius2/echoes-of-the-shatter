extends RefCounted
## Utilidades compartilhadas dos efeitos da árvore de fogo (arquivo novo, ver efeitos_arqueiro_fogo_2d.gd).

const FX_DIR := "res://art2d/fx/fogo/"
const COR_FOGO := Color(1.0, 0.55, 0.15)
const COR_BRASA := Color(1.0, 0.35, 0.1)
const TEMPO_QUEDA := 0.55   # só ritmo visual do meteoro; o dano cai quando a bola toca o chão

## Folhas de quadros em linha (quadros, tamanho do quadro em px, quadros por segundo, repete?).
const FOLHAS := {
	"flecha_proj": {"n": 6, "tam": 96, "fps": 14.0, "loop": true},
	"flecha_impacto": {"n": 8, "tam": 128, "fps": 18.0, "loop": false},
	"queimadura": {"n": 6, "tam": 96, "fps": 10.0, "loop": true},
	"meteoro_queda": {"n": 6, "tam": 128, "fps": 12.0, "loop": true},
	"meteoro_impacto": {"n": 8, "tam": 256, "fps": 16.0, "loop": false},
	"brasas_chao": {"n": 6, "tam": 256, "fps": 8.0, "loop": true},
	"muralha_chama": {"n": 8, "tam": 128, "fps": 12.0, "loop": true},
	"arauto_aura": {"n": 6, "tam": 128, "fps": 8.0, "loop": true},
	"arauto_explosao": {"n": 8, "tam": 256, "fps": 16.0, "loop": false},
}

static var _cache := {}

static func textura(nome: String) -> Texture2D:
	if not _cache.has(nome):
		var p: String = FX_DIR + nome + ".png"
		_cache[nome] = load(p) if ResourceLoader.exists(p) else null
	return _cache[nome]

static func no_raio(arvore: Node, centro: Vector2, r: float) -> Array:
	var out := []
	for n in arvore.get_tree().get_nodes_in_group("hurtable"):
		if n is Node2D and n.global_position.distance_to(centro) <= r:
			out.append(n)
	return out

static func queimar(n: Node, dur: float, dps: float) -> void:
	if n.has_method("aplicar_status"):
		n.aplicar_status("queimadura", dur, dps)
