# Terreno da Cripta: chão contínuo e orgânico definido por campo de distância (SDF).
# Coordenadas "doc" (layout 14_layout_cripta): X leste, Z norte. Na cena Godot, z = -Z_doc.
# Nada aqui é balanceamento: só forma do cenário.
class_name TerrenoCripta
extends RefCounted

const PROFUNDIDADE_SUBSOLO := 3.2   # queda do nível alto para o subsolo (m)
const TOPO_ROCHA := 4.6             # altura média do topo da rocha ao redor
const K_UNIAO := 2.6                # suavização da união de salas e corredores (m)

# Primitivas por sala: ["b", cx, cz, meia_larg, meia_prof, raio_canto] ou ["e", cx, cz, rx, rz]
const SALAS := {
	"r00_atrio": [["b", 0.0, 12.0, 8.5, 12.0, 4.0], ["b", 0.0, 12.0, 12.0, 7.0, 4.0]],
	"r01_patrulha_a": [["e", 38.0, 14.0, 14.0, 12.5], ["e", 46.0, 22.0, 7.0, 6.0]],
	"r02_caes": [["b", 80.0, 14.0, 16.0, 14.0, 9.0], ["e", 72.0, 5.0, 7.0, 5.0]],
	"r03_arauto": [["e", 80.0, 54.0, 16.0, 14.0], ["b", 80.0, 54.0, 10.0, 14.0, 4.0]],
	"r04_patrulha_b": [["b", 35.0, 54.0, 11.0, 14.0, 5.0], ["b", 42.0, 48.0, 10.0, 8.0, 4.0]],
	"r05_linha_tiro": [["b", -4.0, 54.0, 16.0, 9.0, 4.0], ["e", -13.0, 47.0, 7.0, 7.0]],
	"r06_elite_escudada": [["e", -4.0, 94.0, 14.0, 14.0], ["b", -4.0, 94.0, 9.0, 14.0, 4.0]],
	"r07_elite_veloz": [["b", 37.0, 95.0, 15.0, 15.0, 8.0], ["e", 30.0, 86.0, 7.0, 6.0]],
	"r08_antecamara": [["b", 76.0, 95.0, 12.0, 12.0, 6.0], ["b", 76.0, 95.0, 8.0, 12.0, 3.0]],
	"r09_arena": [["e", 76.0, 139.0, 20.0, 20.0], ["e", 76.0, 139.0, 15.0, 19.5]],
	"s01_nicho": [["e", 82.0, -6.0, 6.5, 6.0]],
}
# Corredores: pontos (x, z) e meia-largura. Escadarias (c05, sa, c06) são retas.
const CORREDORES := {
	"c01": [[[12.0, 13.0], [18.0, 15.0], [24.0, 13.0]], 3.0],
	"c02": [[[52.0, 13.0], [58.0, 11.0], [64.0, 13.0]], 3.0],
	"c03": [[[80.0, 28.0], [82.0, 34.0], [80.0, 40.0]], 3.0],
	"c04": [[[64.0, 54.0], [58.0, 56.0], [52.0, 54.0]], 3.0],
	"c05": [[[24.0, 54.0], [12.0, 54.0]], 3.0],
	"c06": [[[-4.0, 68.0], [-4.0, 80.0]], 3.0],
	"c07": [[[10.0, 94.0], [16.0, 96.0], [22.0, 94.0]], 3.0],
	"c08": [[[52.0, 94.0], [58.0, 92.0], [64.0, 94.0]], 3.0],
	"c09": [[[76.0, 107.0], [75.0, 113.0], [76.0, 119.0]], 3.0],
	"sa": [[[0.0, 24.0], [0.0, 40.0]], 3.0],
	"s01": [[[82.0, -1.0], [82.0, 3.0]], 3.0],
}
# Escadarias: topo e fundo em doc, largura útil. O vão é o próprio corredor; o glb da escada encaixa nestas âncoras.
const ESCADAS := {
	"c05": {"topo": [22.0, 54.0], "fundo": [13.0, 54.0], "largura": 4.0},
	"sa": {"topo": [0.0, 26.0], "fundo": [0.0, 37.0], "largura": 4.0},
	"c06": {"topo": [-4.0, 78.0], "fundo": [-4.0, 69.0], "largura": 4.0},
}
# Ondulações largas: [x, z, raio, amplitude]
const MONTES := [
	[38.0, 14.0, 7.0, 0.35], [-6.0, 4.0, 5.0, -0.22], [80.0, 54.0, 9.0, 0.28], [72.0, 20.0, 6.0, -0.25],
	[37.0, 95.0, 8.0, 0.3], [76.0, 150.0, 6.0, 0.4], [76.0, 128.0, 8.0, -0.3], [-4.0, 94.0, 7.0, 0.25],
	[42.0, 48.0, 5.0, -0.2], [-12.0, 50.0, 6.0, -0.18],
]
# Praças planas (pisos e tapetes assentam aqui): [cx, cz, meia_x, meia_z]
const PRACAS := [
	[0.0, 12.0, 13.0, 9.0], [76.0, 137.0, 13.0, 9.0], [80.0, 54.0, 9.5, 5.0],
	[76.0, 95.0, 3.2, 4.4], [75.5, 113.0, 3.0, 4.6],
]

static var _ruido_a := _novo_ruido(7, 0.07)
static var _ruido_b := _novo_ruido(19, 0.38)
static var _ruido_c := _novo_ruido(31, 0.22)
static var _ruido_rocha := _novo_ruido(43, 0.11)

static func _novo_ruido(semente: int, freq: float) -> FastNoiseLite:
	var n := FastNoiseLite.new()
	n.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	n.seed = semente
	n.frequency = freq
	n.fractal_type = FastNoiseLite.FRACTAL_FBM
	n.fractal_octaves = 3
	return n

static func _smin(a: float, b: float, k: float) -> float:
	var h := maxf(k - absf(a - b), 0.0) / k
	return minf(a, b) - h * h * k * 0.25

static func _sd_caixa(px: float, pz: float, p: Array) -> float:
	var qx: float = absf(px - p[1]) - (p[3] - p[5])
	var qz: float = absf(pz - p[2]) - (p[4] - p[5])
	return Vector2(maxf(qx, 0.0), maxf(qz, 0.0)).length() + minf(maxf(qx, qz), 0.0) - p[5]

static func _sd_elipse(px: float, pz: float, p: Array) -> float:
	# aproximação boa o bastante para forma de sala (distância escalada pelo menor raio)
	var dx: float = (px - p[1]) / p[3]
	var dz: float = (pz - p[2]) / p[4]
	return (Vector2(dx, dz).length() - 1.0) * minf(p[3], p[4])

static func _sd_segmento(px: float, pz: float, a: Array, b: Array, r: float) -> float:
	var pa := Vector2(px - a[0], pz - a[1])
	var ba := Vector2(b[0] - a[0], b[1] - a[1])
	var h := clampf(pa.dot(ba) / ba.dot(ba), 0.0, 1.0)
	return (pa - ba * h).length() - r

static func sdf_sala(px: float, pz: float, nome: String) -> float:
	var d := 1e9
	for p in SALAS[nome]:
		var v := _sd_caixa(px, pz, p) if p[0] == "b" else _sd_elipse(px, pz, p)
		d = _smin(d, v, 3.0)
	return d

# distância assinada do vazio caminhável: negativo = chão, positivo = rocha
static func sdf(px: float, pz: float) -> float:
	var d := 1e9
	for nome in SALAS: d = _smin(d, sdf_sala(px, pz, nome), K_UNIAO)
	for nome in CORREDORES:
		var c: Array = CORREDORES[nome]
		var pts: Array = c[0]
		for i in pts.size() - 1: d = _smin(d, _sd_segmento(px, pz, pts[i], pts[i + 1], c[1]), K_UNIAO)
	# contorno irregular: não existe linha reta nem canto idêntico
	return d + _ruido_c.get_noise_2d(px, pz) * 1.6

static func _banda(px: float, pz: float, x0: float, z0: float, x1: float, z1: float, suave: float = 1.0) -> float:
	var dx: float = maxf(maxf(x0 - px, px - x1), 0.0)
	var dz: float = maxf(maxf(z0 - pz, pz - z1), 0.0)
	return 1.0 - smoothstep(0.0, suave, Vector2(dx, dz).length())

# 0 = nível alto, 1 = subsolo
static func subsolo(px: float, pz: float) -> float:
	var u := _banda(px, pz, -20.0, 40.0, 12.0, 68.0, 3.0)
	u = maxf(u, _banda(px, pz, 12.0, 49.0, 24.0, 59.0) * clampf((22.0 - px) / 9.0, 0.0, 1.0))
	u = maxf(u, _banda(px, pz, -5.0, 24.0, 5.0, 40.0) * clampf((pz - 26.0) / 11.0, 0.0, 1.0))
	u = maxf(u, _banda(px, pz, -9.0, 68.0, 1.0, 80.0) * clampf((78.0 - pz) / 9.0, 0.0, 1.0))
	return u

static func em_escada(px: float, pz: float) -> float:
	var w := 0.0
	w = maxf(w, _banda(px, pz, 12.0, 49.0, 24.0, 59.0, 1.5))
	w = maxf(w, _banda(px, pz, -5.0, 24.0, 5.0, 40.0, 1.5))
	w = maxf(w, _banda(px, pz, -9.0, 68.0, 1.0, 80.0, 1.5))
	# só vale dentro do trecho inclinado
	var t := 0.0
	if px > 12.0 and px < 24.0 and pz > 49.0 and pz < 59.0: t = 1.0
	if absf(px) < 5.0 and pz > 24.0 and pz < 40.0: t = 1.0
	if px > -9.0 and px < 1.0 and pz > 68.0 and pz < 80.0: t = 1.0
	return w * t

static func _praca(px: float, pz: float) -> float:
	var w := 0.0
	for p in PRACAS:
		w = maxf(w, _banda(px, pz, p[0] - p[2], p[1] - p[3], p[0] + p[2], p[1] + p[3], 3.0))
	return w

# altura do chão (sem rocha)
static func chao(px: float, pz: float) -> float:
	var ondas := 0.0
	for m in MONTES:
		ondas += m[3] * exp(-pow(Vector2(px - m[0], pz - m[1]).length() / m[2], 2.0))
	var pequeno := _ruido_a.get_noise_2d(px, pz) * 0.24 + _ruido_b.get_noise_2d(px, pz) * 0.06
	var base := ondas + pequeno
	var nivel := -PROFUNDIDADE_SUBSOLO * subsolo(px, pz)
	var e := em_escada(px, pz)
	var plano := _praca(px, pz)
	var h := nivel + base * (1.0 - clampf(maxf(e, plano), 0.0, 1.0))
	h = lerpf(h, nivel + altura_praca(px, pz), plano)
	return h - 0.12 * e   # sob a escadaria: o glb da escada assenta 12 cm acima

static func altura_praca(px: float, pz: float) -> float:
	var h := 0.0
	for p in PRACAS:
		if absf(px - p[0]) < p[2] + 4.0 and absf(pz - p[1]) < p[3] + 4.0:
			for m in MONTES: h += m[3] * exp(-pow(Vector2(p[0] - m[0], p[1] - m[1]).length() / m[2], 2.0))
			return h
	return 0.0

# altura final: chão dentro do vazio, parede de rocha fora
static func altura(px: float, pz: float) -> float:
	var s := sdf(px, pz)
	var f := chao(px, pz)
	var parede := TOPO_ROCHA + _ruido_rocha.get_noise_2d(px, pz) * 1.3 + minf(s, 8.0) * 0.08
	var t := smoothstep(-0.1, 3.0, s)
	# lábio gasto na base da parede: o chão sobe um pouco antes da rocha
	var lab := smoothstep(-1.2, 0.0, s) * 0.12
	return lerpf(f + lab, parede, t)

static func normal(px: float, pz: float) -> Vector3:
	var e := 0.3
	var dx: float = altura(px + e, pz) - altura(px - e, pz)
	var dz: float = altura(px, pz + e) - altura(px, pz - e)
	return Vector3(-dx, 2.0 * e, -dz).normalized()
