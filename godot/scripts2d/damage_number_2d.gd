extends Node2D
## Número de dano que sobe e some, em fonte pixel: Jersey 15, 20 e 25 (SIL OFL, ver art2d/fonts/LEIA-ME.md). Cada arquivo só é
## usado no tamanho nativo (1 px da fonte = 1 px da grade do mundo, sem anti-serrilhado nem hinting), o contorno é de 1 px em 8
## direções e o estouro do golpe forte ou fatal abre no tamanho nativo seguinte (não amplia o desenho).

const FONTES := ["res://art2d/fonts/Jersey15-Regular.ttf", "res://art2d/fonts/Jersey20-Regular.ttf", "res://art2d/fonts/Jersey25-Regular.ttf"]
const TAMANHOS := [15, 20, 25]            # tamanho nativo de cada fonte (altura dos dígitos: 8, 12 e 16 px)
const CORTES := [16.0, 24.0]              # `tamanho` pedido (px de mundo, já com a escala do alvo): abaixo de 16 a fonte 15; até 24 a 20; acima a 25
const ESTOURO := 0.07                     # s em que o golpe forte ou fatal fica no tamanho nativo seguinte
const VIZINHOS: Array[Vector2] = [Vector2(-1, -1), Vector2(0, -1), Vector2(1, -1), Vector2(-1, 0), Vector2(1, 0), Vector2(-1, 1), Vector2(0, 1), Vector2(1, 1)]

static var _fontes: Array[Font] = []

var texto := ""
var cor := Color.WHITE
var tamanho := 20.0
var tempo := 0.65
var subida := 42.0
var forte := false      # golpe forte ou fatal: abre maior e fica um pouco mais
var deriva := 0.0       # deslocamento lateral ao longo da subida
var _t := 0.0

func _ready() -> void:
	z_index = 200

func _process(delta: float) -> void:
	_t += delta
	if _t >= tempo:
		queue_free()
		return
	queue_redraw()

## Fonte do degrau 0 a 2; sem o arquivo (teste sem importar) cai na fonte padrão da engine.
static func _fonte(degrau: int) -> Font:
	if _fontes.is_empty():
		for caminho in FONTES:
			var f = load(caminho)
			_fontes.append(f if f is Font else ThemeDB.fallback_font)
	return _fontes[degrau]

## Degrau (0 a 2) da fonte para um `tamanho` pedido.
static func degrau_de(tam: float) -> int:
	return 0 if tam < CORTES[0] else (1 if tam < CORTES[1] else 2)

func _draw() -> void:
	var p := clampf(_t / tempo, 0.0, 1.0)
	var sobe := -subida * (1.0 - pow(1.0 - p, 2.0))
	var degrau := degrau_de(tamanho)
	if forte and _t < ESTOURO:
		degrau = mini(degrau + 1, TAMANHOS.size() - 1)   # estoura no começo
	var fonte := _fonte(degrau)
	var tam: int = TAMANHOS[degrau]
	var larg := fonte.get_string_size(texto, HORIZONTAL_ALIGNMENT_LEFT, -1, tam).x
	var c := cor
	c.a = 1.0 - maxf(0.0, (p - 0.55) / 0.45)
	var sombra := Color(0, 0, 0, c.a)
	var pos := Vector2(roundf(-larg / 2.0 + deriva * p), roundf(sobe))   # sempre em px inteiros da grade
	for d in VIZINHOS:
		fonte.draw_string(get_canvas_item(), pos + d, texto, HORIZONTAL_ALIGNMENT_LEFT, -1, tam, sombra)
	fonte.draw_string(get_canvas_item(), pos, texto, HORIZONTAL_ALIGNMENT_LEFT, -1, tam, c)
