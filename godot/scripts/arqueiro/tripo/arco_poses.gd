extends RefCounted
# Gera por codigo (IK analitico de 2 ossos, amostrado a 30 fps) as animacoes do arco:
#   arco_segurando (loop), sacar_arco (0.6 s), shoot (1.2 s), guardar_arco (0.6 s).
# O resto do corpo vem do idle; so bracos, maos, dedos e o osso CordaNock (ponto da corda) sao sobrescritos.
# Espaco: o de repouso do esqueleto (+X frente, +Y cima, -Z esquerda do personagem, +Z direita).

const FPS := 30.0
const PFX := "Armature/Skeleton3D:mixamorig_"
# eixos do arco no espaco de repouso (medidos no Blender, build6.py "BOWAX", convertidos Y-up)
const ARCO_LONGO := Vector3(-0.154, 0.646, -0.748)
const ARCO_VENTRE := Vector3(0.301, -0.690, -0.658)   # lado oposto a corda (aponta para o alvo)
const FRENTE := Vector3(1, 0, 0)
const CIMA := Vector3(0, 1, 0)
const FINGERS := ["Index", "Middle", "Ring", "Pinky", "Thumb"]

# parametros ajustaveis (espaco do esqueleto, relativos aos ombros / cabeca)
var L_HOLD := Vector3(0.14, -0.10, 0.045)     # pulso esquerdo relativo ao ombro esquerdo (arco em guarda)
var L_AIM := Vector3(0.215, 0.025, 0.06)      # pulso esquerdo no tiro (estendido, levemente erguido)
var L_COSTAS := Vector3(-0.11, 0.03, -0.09)   # mao esquerda atras do ombro (sacar/guardar)
var R_QUIVER := Vector3(-0.075, 0.115, 0.04)  # nocas da mao direita relativas ao ombro direito (aljava)
var ANCHOR := Vector3(0.105, 0.845, 0.04)     # posicao absoluta da mao direita no queixo
const POLE_L := Vector3(0.0, -1.0, -0.4)
const POLE_R := Vector3(-0.5, -0.1, 1.0)

var sk: Skeleton3D
var idle: Animation
var curl_L: Dictionary = {}   # osso -> Quaternion (rotacao local do punho fechado, da pose antiga)
var bi: Dictionary = {}
var order: Array = []
var rest_g: Dictionary = {}
var rest_o: Dictionary = {}
var tr_idx: Dictionary = {}
var nock_rest_hand: Transform3D   # nock em repouso no referencial da mao esquerda
var grip_r: Vector3               # ponto de pegada da mao direita (no referencial dela)
var last_twist := 0.0

func _bone(n: String) -> int:
	return sk.find_bone("mixamorig_" + n)

func _ease(x: float) -> float:
	x = clampf(x, 0.0, 1.0)
	return x * x * (3.0 - 2.0 * x)

func _seg(t: float, a: float, b: float) -> float:
	return _ease((t - a) / (b - a))

func _init_dados(p_sk: Skeleton3D, p_idle: Animation, p_old: Animation) -> void:
	sk = p_sk
	idle = p_idle
	for i in sk.get_bone_count():
		bi[sk.get_bone_name(i).trim_prefix("mixamorig_")] = i
		rest_g[i] = sk.get_bone_global_rest(i)
		rest_o[i] = sk.get_bone_rest(i).origin
		tr_idx[i] = idle.find_track(NodePath("Armature/Skeleton3D:" + sk.get_bone_name(i)), Animation.TYPE_ROTATION_3D)
	var q: Array = []
	for r in sk.get_parentless_bones():
		q.append(r)
	var k := 0
	while k < q.size():
		for c in sk.get_bone_children(q[k]):
			q.append(c)
		k += 1
	order = q
	for f in FINGERS:
		for j in [1, 2, 3]:
			var n := "LeftHand%s%d" % [f, j]
			var t := p_old.find_track(NodePath(PFX + n), Animation.TYPE_ROTATION_3D)
			if t >= 0:
				curl_L[n] = p_old.track_get_key_value(t, 0)
	var lh: int = bi["LeftHand"]
	nock_rest_hand = rest_g[lh].affine_inverse() * rest_g[bi["CordaNock"]]
	grip_r = Vector3(0, (rest_g[bi["RightHand"]].affine_inverse() * rest_g[bi["RightHandIndex2"]].origin).y, 0)

func _base(t: float) -> Array:
	var rot: Array = []
	rot.resize(sk.get_bone_count())
	for i in sk.get_bone_count():
		var ti: int = tr_idx[i]
		rot[i] = idle.rotation_track_interpolate(ti, t) if ti >= 0 else sk.get_bone_rest(i).basis.get_rotation_quaternion()
	return rot

func _fk(rot: Array, hips: Vector3) -> Dictionary:
	var g := {}
	for i in order:
		var par := sk.get_bone_parent(i)
		var o: Vector3 = rest_o[i]
		if i == bi["Hips"]:
			o = hips
		var loc := Transform3D(Basis(rot[i]), o)
		g[i] = loc if par < 0 else g[par] * loc
	return g

# IK de 2 ossos; escreve rot[Arm], rot[ForeArm], rot[Hand]. Retorna o pulso real.
func _ik(rot: Array, g: Dictionary, lado: String, wrist: Vector3, pole: Vector3, gh: Basis) -> Dictionary:
	var A: int = bi[lado + "Arm"]
	var F: int = bi[lado + "ForeArm"]
	var H: int = bi[lado + "Hand"]
	var S: Vector3 = g[A].origin
	var la: float = (rest_g[F].origin - rest_g[A].origin).length()
	var lb: float = (rest_g[H].origin - rest_g[F].origin).length()
	var d := wrist - S
	var dist := clampf(d.length(), 0.03, (la + lb) * 0.995)
	var u := d.normalized()
	var along := (la * la - lb * lb + dist * dist) / (2.0 * dist)
	var h := sqrt(maxf(la * la - along * along, 0.0))
	var pv := (pole - u * pole.dot(u)).normalized()
	var E := S + u * along + pv * h
	var Tw := S + u * dist
	var GA: Basis = Basis(Quaternion(rest_g[A].basis.y.normalized(), (E - S).normalized())) * rest_g[A].basis
	var par: int = sk.get_bone_parent(A)
	rot[A] = (g[par].basis.inverse() * GA).orthonormalized().get_rotation_quaternion()
	var GF: Basis = Basis(Quaternion(rest_g[F].basis.y.normalized(), (Tw - E).normalized())) * rest_g[F].basis
	rot[F] = (GA.inverse() * GF).orthonormalized().get_rotation_quaternion()
	var q: Quaternion = (GF.inverse() * gh).orthonormalized().get_rotation_quaternion()
	rot[H] = q
	last_twist = rad_to_deg(2.0 * atan2(q.y, q.w))
	return {"wrist": Tw, "GH": gh}

# orienta a mao esquerda para o arco ter o eixo longo em `longo` e o ventre em `ventre`
func _mao_arco(longo: Vector3, ventre: Vector3) -> Basis:
	var hb: Basis = rest_g[bi["LeftHand"]].basis.inverse()
	var ah := (hb * ARCO_LONGO).normalized()
	var bh := hb * ARCO_VENTRE
	bh = (bh - ah * ah.dot(bh)).normalized()
	var Mh := Basis(ah, bh, ah.cross(bh))
	var l := longo.normalized()
	var bw := (ventre - l * l.dot(ventre)).normalized()
	var Mw := Basis(l, bw, l.cross(bw))
	return (Mw * Mh.inverse()).orthonormalized()

func _curl_esq(rot: Array, s: float) -> void:
	for n in curl_L:
		var b: int = bi[n]
		var rq: Quaternion = sk.get_bone_rest(b).basis.get_rotation_quaternion()
		rot[b] = rq.slerp(curl_L[n], s)

# punho direito aberto/fechado em volta da flecha: gira em torno do eixo "atravessado" da mao
func _curl_dir(rot: Array, s: float) -> void:
	if s <= 0.0:
		return
	for f in ["Index", "Middle", "Ring", "Pinky"]:
		for j in [1, 2, 3]:
			var n := "RightHand%s%d" % [f, j]
			var b: int = bi[n]
			var rq: Quaternion = sk.get_bone_rest(b).basis.get_rotation_quaternion()
			var lq: Quaternion = curl_L.get("LeftHand%s%d" % [f, j], rq)
			# delta do lado esquerdo, espelhado no referencial local (conj. no eixo Z do mundo ~ eixo local X/Z)
			var d := rq.inverse() * lq
			var dm := Quaternion(d.x, -d.y, -d.z, d.w)
			rot[b] = rq.slerp(rq * dm, s * 0.8)

# amostra uma pose. L = dict do braco esquerdo; fr = Callable(t, ctx) -> dict da mao direita
func _amostra(L: Dictionary, fr: Callable, t: float, saida: Dictionary) -> void:
	var rot := _base(t)
	var hips := Vector3(0.0254, 0.4863, -0.002)
	var th := idle.find_track(NodePath(PFX + "Hips"), Animation.TYPE_POSITION_3D)
	if th >= 0:
		hips = idle.position_track_interpolate(th, t)
	var g := _fk(rot, hips)
	var base := rot.duplicate()
	var SL: Vector3 = g[bi["LeftArm"]].origin
	var SR: Vector3 = g[bi["RightArm"]].origin
	var bonesL := [bi["LeftArm"], bi["LeftForeArm"], bi["LeftHand"]]
	var bonesR := [bi["RightArm"], bi["RightForeArm"], bi["RightHand"]]
	var gh := _mao_arco(L["long"], L["belly"])
	var rl := rot.duplicate()
	var infoL := _ik(rl, g, "Left", SL + (L["off"] as Vector3), POLE_L, gh)
	var wL: float = L["w"]
	for b in bonesL:
		rot[b] = (base[b] as Quaternion).slerp(rl[b], wL)
	_curl_esq(rot, L["curl"] * wL)
	var GHL := Transform3D(infoL["GH"], infoL["wrist"])
	var nock_rest_w: Vector3 = (GHL * nock_rest_hand).origin
	var ctx := {"SL": SL, "SR": SR, "nock_rest_w": nock_rest_w, "belly": (L["belly"] as Vector3).normalized()}
	var R: Dictionary = fr.call(t, ctx)
	var wR: float = R["w"]
	var nockpos: Vector3 = rest_o[bi["CordaNock"]]
	if wR > 0.0:
		var dirw: Vector3 = (R["dir"] as Vector3).normalized()
		var GRH: Basis = Basis(Quaternion(rest_g[bi["RightHand"]].basis.y.normalized(), dirw)) * rest_g[bi["RightHand"]].basis
		var wr: Vector3 = (R["grip"] as Vector3) - GRH * grip_r
		var rr := rot.duplicate()
		_ik(rr, g, "Right", wr, R.get("pole", POLE_R), GRH)
		for b in bonesR:
			rot[b] = (base[b] as Quaternion).slerp(rr[b], wR)
		_curl_dir(rot, R["curl"] * wR)
		if R.get("pull", 0.0) > 0.0:
			var loc := GHL.affine_inverse() * (R["grip"] as Vector3)
			nockpos = nockpos.lerp(loc, R["pull"])
	saida["rot"] = rot
	saida["nock_pos"] = nockpos

func _construir(base_anim: Animation, dur: float, fl: Callable, fr: Callable, nome: String) -> Animation:
	var a := base_anim.duplicate() as Animation
	a.length = dur
	a.loop_mode = Animation.LOOP_NONE
	var n := int(round(dur * FPS))
	var ossos: Array = []
	for lado in ["Left", "Right"]:
		for b in ["Arm", "ForeArm", "Hand"]:
			ossos.append(lado + b)
		for f in FINGERS:
			for j in [1, 2, 3]:
				ossos.append("%sHand%s%d" % [lado, f, j])
	var tracks := {}
	for o in ossos:
		var pth := NodePath(PFX + o)
		var ti := a.find_track(pth, Animation.TYPE_ROTATION_3D)
		if ti < 0:
			ti = a.add_track(Animation.TYPE_ROTATION_3D)
			a.track_set_path(ti, pth)
		while a.track_get_key_count(ti) > 0:
			a.track_remove_key(ti, 0)
		tracks[o] = ti
	var pth_n := NodePath(PFX + "CordaNock")
	var tn := a.find_track(pth_n, Animation.TYPE_POSITION_3D)
	if tn < 0:
		tn = a.add_track(Animation.TYPE_POSITION_3D)
		a.track_set_path(tn, pth_n)
	while a.track_get_key_count(tn) > 0:
		a.track_remove_key(tn, 0)
	var tw := 0.0
	for k in n + 1:
		var t := minf(k / FPS, dur)
		var out := {}
		_amostra(fl.call(t), fr, t, out)
		tw = maxf(tw, absf(last_twist))
		for o in ossos:
			a.rotation_track_insert_key(tracks[o], t, (out["rot"][bi[o]] as Quaternion))
		a.position_track_insert_key(tn, t, out["nock_pos"])
	print("ARCO anim ", nome, " ", n + 1, " quadros; torcao do punho (ultimo braco) max ", snappedf(tw, 0.1))
	return a

# ----- especificacoes por tempo -----
func _hold_L(_t: float) -> Dictionary:
	return {"off": L_HOLD, "long": CIMA, "belly": FRENTE, "w": 1.0, "curl": 1.0}

func _hold_R(_t: float, _c: Dictionary) -> Dictionary:
	return {"w": 0.0}

func draw_dir() -> Vector3:
	var s0: Vector3 = rest_g[bi["LeftArm"]].origin
	var d := (s0 + L_AIM) - ANCHOR
	return Vector3(d.x, d.y * 0.4, d.z).normalized()

# tempos do shoot (usados tambem pelo script principal)
const T_GRAB := 0.20
const T_NOCK := 0.48
const T_FULL := 0.78
const T_REL := 0.90
const T_END := 1.2

func _shoot_L(t: float) -> Dictionary:
	var kl := _seg(t, 0.22, 0.62) * (1.0 - _seg(t, 1.0, 1.2))
	var belly := FRENTE.lerp(draw_dir(), kl).normalized()
	return {"off": L_HOLD.lerp(L_AIM, kl), "long": CIMA, "belly": belly, "w": 1.0, "curl": 1.0}

func _shoot_R(t: float, c: Dictionary) -> Dictionary:
	var w := _seg(t, 0.0, 0.1) * (1.0 - _seg(t, 1.08, 1.2))
	var SR: Vector3 = c["SR"]
	var relax := SR + Vector3(0.02, -0.19, 0.05)
	var quiver := SR + R_QUIVER
	var nock: Vector3 = c["nock_rest_w"]
	var dd := draw_dir()
	var out := {"w": w, "pull": 0.0}
	var grip: Vector3
	var dir: Vector3
	var curl := 0.0
	if t < T_GRAB:
		grip = relax.lerp(quiver, _seg(t, 0.0, T_GRAB))
		dir = Vector3(0.2, 1.0, 0.2)
	elif t < T_NOCK:
		var u := _seg(t, T_GRAB, T_NOCK)
		grip = quiver.lerp(nock, u) + Vector3(0.0, 0.05 * sin(PI * u), 0.0)
		dir = Vector3(0.2, 1.0, 0.2).lerp(c["belly"], u)
		curl = _seg(t, T_GRAB, T_GRAB + 0.05)
	elif t < T_REL:
		var u2 := _seg(t, T_NOCK, T_FULL)
		grip = nock.lerp(ANCHOR, u2)
		dir = c["belly"]
		curl = 1.0
		out["pull"] = 1.0
	else:
		var u3 := _seg(t, T_REL, T_REL + 0.10)
		var rec := ANCHOR + Vector3(-0.035, 0.0, 0.025) * u3
		var u4 := _seg(t, T_REL + 0.10, 1.2)
		grip = rec.lerp(relax, u4)
		dir = (c["belly"] as Vector3).lerp(Vector3(0.2, -1.0, 0.2), u4)
		curl = 1.0 - _seg(t, T_REL, T_REL + 0.07)
		# a corda estala de volta em 0.05 s
		out["pull"] = 1.0 - _seg(t, T_REL, T_REL + 0.05)
	out["grip"] = grip
	out["dir"] = dir
	out["curl"] = curl
	return out

const LONG_COSTAS := Vector3(0.0, 0.6, -0.8)
const BELLY_COSTAS := Vector3(-1.0, 0.0, 0.0)
const T_SWAP_SACAR := 0.26

func _sacar_L(t: float) -> Dictionary:
	var up := _seg(t, 0.0, T_SWAP_SACAR)
	var fw := _seg(t, T_SWAP_SACAR, 0.6)
	var off: Vector3
	var lg := LONG_COSTAS
	var bl := BELLY_COSTAS
	if t < T_SWAP_SACAR:
		off = Vector3(0.10, -0.20, -0.04).lerp(L_COSTAS, up)
	else:
		off = L_COSTAS.lerp(L_HOLD, fw)
		lg = LONG_COSTAS.lerp(CIMA, fw).normalized()
		bl = BELLY_COSTAS.lerp(FRENTE, fw).normalized()
	return {"off": off, "long": lg, "belly": bl, "w": _seg(t, 0.0, 0.12), "curl": _seg(t, 0.12, T_SWAP_SACAR)}

func _guardar_L(t: float) -> Dictionary:
	return _sacar_L(0.6 - t)

func instalar(p: AnimationPlayer, p_sk: Skeleton3D) -> void:
	var lib := p.get_animation_library("")
	var idle_a := p.get_animation("idle")
	var old := p.get_animation("arco_segurando")
	_init_dados(p_sk, idle_a, old)
	var hold := _construir(idle_a, 3.0, _hold_L, _hold_R, "arco_segurando")
	var shoot := _construir(idle_a, T_END, _shoot_L, _shoot_R, "shoot")
	var sacar := _construir(idle_a, 0.6, _sacar_L, _hold_R, "sacar_arco")
	var guardar := _construir(idle_a, 0.6, _guardar_L, _hold_R, "guardar_arco")
	for par in [["arco_segurando", hold], ["shoot", shoot], ["sacar_arco", sacar], ["guardar_arco", guardar]]:
		if lib.has_animation(par[0]):
			lib.remove_animation(par[0])
		lib.add_animation(par[0], par[1])
