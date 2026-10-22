# Névoa, ambiente e tom por andar (guia docs/arte/24_direcao_visual_cripta.md, seção 4).
# Segue o `Alvo` da câmera de estudo (e, no jogo, o herói): quanto mais fundo, mais denso e escuro.
extends WorldEnvironment

const T := preload("res://scripts/terreno/terreno_cripta.gd")
const DENSIDADE := [0.006, 0.008, 0.011, 0.014]
const COR_NEVOA := [Color(0.09, 0.13, 0.24), Color(0.11, 0.12, 0.26), Color(0.10, 0.07, 0.20), Color(0.05, 0.03, 0.07)]
const COR_AMBIENTE := [Color(0.20, 0.25, 0.38), Color(0.22, 0.24, 0.40), Color(0.20, 0.17, 0.34), Color(0.12, 0.10, 0.16)]
const ENERGIA := [0.55, 0.50, 0.42, 0.32]
@export var alvo_path: NodePath = ^"../CameraEstudio"
var _atual := 0.0

func _process(delta: float) -> void:
	var cam := get_node_or_null(alvo_path)
	if cam == null or environment == null: return
	var a: Vector3 = cam.get("Alvo")
	var alvo := clampf(T.andar(a.x, -a.z), 0.0, 3.0)
	_atual = lerpf(_atual, alvo, 1.0 - exp(-2.0 * delta))
	aplicar(_atual)

func aplicar(andar: float) -> void:
	var i := clampi(int(floor(andar)), 0, 2)
	var f := andar - i
	environment.volumetric_fog_density = lerpf(DENSIDADE[i], DENSIDADE[i + 1], f)
	environment.fog_light_color = COR_NEVOA[i].lerp(COR_NEVOA[i + 1], f)
	environment.ambient_light_color = COR_AMBIENTE[i].lerp(COR_AMBIENTE[i + 1], f)
	environment.ambient_light_energy = lerpf(ENERGIA[i], ENERGIA[i + 1], f)
	environment.background_color = environment.fog_light_color * 0.16
