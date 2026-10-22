# Terreno da Cripta: chão contínuo e orgânico definido por campo de distância (SDF).
# Coordenadas "doc" (layout 14_layout_cripta): X leste, Z norte. Na cena Godot, z = -Z_doc.
# Nada aqui é balanceamento: só forma do cenário.
class_name TerrenoCripta
extends RefCounted

const QUEDA_ANDAR := 4.0            # desnível entre andares (m), guia docs/arte/24
const PE_DIREITO_SALA := 5.4        # altura da parede da sala acima do piso (m)
const PE_DIREITO_CORREDOR := 4.5
const RELEVO := 0.15               # fração do relevo original mantida no chão jogável
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
	"c03": [[[80.0, 28.0], [80.0, 40.0]], 3.0],
	"c04": [[[64.0, 54.0], [58.0, 56.0], [52.0, 54.0]], 3.0],
	"c05": [[[24.0, 54.0], [12.0, 54.0]], 3.0],
	"c06": [[[-4.0, 68.0], [-4.0, 80.0]], 3.0],
	"c07": [[[10.0, 94.0], [16.0, 96.0], [22.0, 94.0]], 3.0],
	"c08": [[[52.0, 94.0], [58.0, 92.0], [64.0, 94.0]], 3.0],
	"c09": [[[76.0, 107.0], [76.0, 119.0]], 3.0],
	"sa": [[[0.0, 24.0], [0.0, 40.0]], 3.0],
	"s01": [[[82.0, -1.0], [82.0, 3.0]], 3.0],
}
# Escadarias (desnível de 4 m = 22 degraus de 0,18 m, ~7 m de comprimento, largura útil 4 m): topo e fundo em doc.
# O vão é o próprio corredor; o glb da escada encaixa nestas âncoras. andar = andar de cima.
const ESCADAS := {
	"c03": {"topo": [80.0, 30.5], "fundo": [80.0, 37.5], "largura": 4.0, "andar": 0},
	"sa": {"topo": [0.0, 29.5], "fundo": [0.0, 36.5], "largura": 4.0, "andar": 0},
	"c06": {"topo": [-4.0, 70.5], "fundo": [-4.0, 77.5], "largura": 4.0, "andar": 1},
	"c09": {"topo": [76.0, 109.5], "fundo": [76.0, 116.5], "largura": 4.0, "andar": 2},
}
# Andares: retângulos [x0, z0, x1, z1] por andar (A0 superfície, A1 subsolo, A2 profundeza, A3 arena)
const ANDARES := {1: [-24.0, 40.0, 100.0, 68.0], 2: [-24.0, 80.0, 100.0, 112.0], 3: [52.0, 119.0, 100.0, 162.0]}
# Ondulações largas: [x, z, raio, amplitude]
const MONTES := [
	[38.0, 14.0, 7.0, 0.35], [-6.0, 4.0, 5.0, -0.22], [80.0, 54.0, 9.0, 0.28], [72.0, 20.0, 6.0, -0.25],
	[37.0, 95.0, 8.0, 0.3], [76.0, 150.0, 6.0, 0.4], [76.0, 128.0, 8.0, -0.3], [-4.0, 94.0, 7.0, 0.25],
	[42.0, 48.0, 5.0, -0.2], [-12.0, 50.0, 6.0, -0.18],
]
# Praças planas (pisos e tapetes assentam aqui): [cx, cz, meia_x, meia_z]
const PRACAS := [
	[0.0, 12.0, 13.0, 9.0], [76.0, 137.0, 13.0, 9.0], [80.0, 54.0, 9.5, 5.0], [76.0, 95.0, 5.0, 9.0],
	[18.0, 15.0, 2.6, 1.7], [58.0, 11.0, 2.6, 1.7], [58.0, 56.0, 2.6, 1.7], [18.0, 54.0, 2.6, 1.7],
	[16.0, 96.0, 2.6, 1.7], [58.0, 92.0, 2.6, 1.7],
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

# distância assinada do vazio caminhável: negativo = chão, positivo = rocha. Devolve (d, d_salas, d_corredores)
static func sdf3(px: float, pz: float) -> Vector3:
	var ds := 1e9
	for nome in SALAS: ds = _smin(ds, sdf_sala(px, pz, nome), K_UNIAO)
	var dc := 1e9
	for nome in CORREDORES:
		var c: Array = CORREDORES[nome]
		var pts: Array = c[0]
		for i in pts.size() - 1: dc = _smin(dc, _sd_segmento(px, pz, pts[i], pts[i + 1], c[1]), K_UNIAO)
	# contorno irregular: não existe linha reta nem canto idêntico
	var r := _ruido_c.get_noise_2d(px, pz) * 1.6
	return Vector3(_smin(ds, dc, K_UNIAO) + r, ds + r, dc + r)

static func sdf(px: float, pz: float) -> float:
	return sdf3(px, pz).x

static func _banda(px: float, pz: float, x0: float, z0: float, x1: float, z1: float, suave: float = 1.0) -> float:
	var dx := maxf(maxf(x0 - px, px - x1), 0.0)
	var dz := maxf(maxf(z0 - pz, pz - z1), 0.0)
	return 1.0 - smoothstep(0.0, suave, Vector2(dx, dz).length())

# andar contínuo: 0 = superfície, 1 = subsolo, 2 = profundeza, 3 = arena (fração dentro das escadarias)
static func andar(px: float, pz: float, suave: float = 3.0) -> float:
	var a := 0.0
	for k in ANDARES:
		var r: Array = ANDARES[k]
		a = maxf(a, float(k) * _banda(px, pz, r[0], r[1], r[2], r[3], suave))
	for k in ESCADAS:
		var e: Dictionary = ESCADAS[k]
		var t: Array = e["topo"]; var f: Array = e["fundo"]
		var l := float(e["andar"])
		var rampa := clampf(Vector2(px - t[0], pz - t[1]).dot(Vector2(f[0] - t[0], f[1] - t[1]).normalized()) / Vector2(f[0] - t[0], f[1] - t[1]).length(), 0.0, 1.0)
		var m := _banda(px, pz, minf(t[0], f[0]) - 4.5, minf(t[1], f[1]) - 3.0, maxf(t[0], f[0]) + 4.5, maxf(t[1], f[1]) + 3.0, 1.0)
		a = maxf(a, (l + rampa) * m)
	return a

# 1 dentro do trecho inclinado de uma escadaria
static func em_escada(px: float, pz: float) -> float:
	var w := 0.0
	for k in ESCADAS:
		var e: Dictionary = ESCADAS[k]
		var t: Array = e["topo"]; var f: Array = e["fundo"]
		w = maxf(w, _banda(px, pz, minf(t[0], f[0]) - 3.0, minf(t[1], f[1]), maxf(t[0], f[0]) + 3.0, maxf(t[1], f[1]), 1.5))
	return w

static func _praca(px: float, pz: float) -> float:
	var w := 0.0
	for p in PRACAS:
		w = maxf(w, _banda(px, pz, p[0] - p[2], p[1] - p[3], p[0] + p[2], p[1] + p[3], 3.0))
	return w

static func nivel(px: float, pz: float) -> float:
	return -QUEDA_ANDAR * andar(px, pz)

static func _ondas(px: float, pz: float) -> float:
	var h := 0.0
	for m in MONTES: h += m[3] * exp(-pow(Vector2(px - m[0], pz - m[1]).length() / m[2], 2.0))
	return h

# altura do chão (sem rocha)
static func chao(px: float, pz: float) -> float:
	# chão jogável quase plano: relevo forte distorce a projeção planar da textura do piso (só ~4 cm de ondulação)
	var pequeno := (_ruido_a.get_noise_2d(px, pz) * 0.24 + _ruido_b.get_noise_2d(px, pz) * 0.06) * RELEVO
	var base := _ondas(px, pz) * RELEVO + pequeno
	var lvl := nivel(px, pz)
	var e := em_escada(px, pz)
	var plano := _praca(px, pz)
	var h := lvl + base * (1.0 - clampf(maxf(e, plano), 0.0, 1.0))
	h = lerpf(h, lvl, plano)
	return h - 0.1 * e   # sob a escadaria: o glb da escada assenta 10 cm acima

# altura final: chão dentro do vazio, parede de rocha fora (pé-direito 5,4 m em sala, 4,5 m em corredor, relativo ao andar)
static func altura(px: float, pz: float) -> float:
	var d := sdf3(px, pz)
	var s := d.x
	var f := chao(px, pz)
	var sala := clampf((d.z - d.y) / 4.0 + 0.5, 0.0, 1.0)
	var pe := lerpf(PE_DIREITO_CORREDOR, PE_DIREITO_SALA, sala)
	# longe do chão a rocha desce em rampa suave entre andares (sem degraus retos no topo da pedra)
	var nv := lerpf(nivel(px, pz), -QUEDA_ANDAR * andar(px, pz, 16.0), smoothstep(2.0, 8.0, s))
	var parede := nv + pe + _ruido_rocha.get_noise_2d(px, pz) * 0.9 + minf(s, 8.0) * 0.06
	var t := smoothstep(-0.1, 3.0, s)
	var lab := smoothstep(-1.2, 0.0, s) * 0.12   # lábio gasto na base da parede
	return lerpf(f + lab, parede, t)

static func normal(px: float, pz: float) -> Vector3:
	var e := 0.3
	var dx := altura(px + e, pz) - altura(px - e, pz)
	var dz := altura(px, pz + e) - altura(px, pz - e)
	return Vector3(-dx, 2.0 * e, -dz).normalized()
