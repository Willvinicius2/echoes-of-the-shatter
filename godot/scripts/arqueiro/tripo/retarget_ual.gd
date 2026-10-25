extends RefCounted
# Retarget em codigo de um clipe da Universal Animation Library (Quaternius, CC0) para o esqueleto
# Mixamo do arqueiro. Metodo mundial: G_alvo = C * G_fonte * R_fonte^-1 * C^-1 * R_alvo
# (so a rotacao relativa ao repouso passa; C vira o rosto da fonte (+Z) para o do alvo (+X)).
# Quadril: o deslocamento em relacao ao repouso e escalado pela altura do quadril.

const FPS := 30.0
const PFX := "Armature/Skeleton3D:mixamorig_"

const MAPA := {
	"hips": "Hips", "spine.001": "Spine", "spine.002": "Spine1", "spine.003": "Spine2",
	"neck": "Neck", "head": "Head",
	"shoulder.L": "LeftShoulder", "upper_arm.L": "LeftArm", "forearm.L": "LeftForeArm", "hand.L": "LeftHand",
	"shoulder.R": "RightShoulder", "upper_arm.R": "RightArm", "forearm.R": "RightForeArm", "hand.R": "RightHand",
	"thigh.L": "LeftUpLeg", "shin.L": "LeftLeg", "foot.L": "LeftFoot", "toe.L": "LeftToeBase",
	"thigh.R": "RightUpLeg", "shin.R": "RightLeg", "foot.R": "RightFoot", "toe.R": "RightToeBase",
}
const DEDOS := {"f_index": "Index", "f_middle": "Middle", "f_ring": "Ring", "f_pinky": "Pinky", "thumb": "Thumb"}

static func _nome_fonte_para_alvo() -> Dictionary:
	var m: Dictionary = {}
	for k in MAPA:
		m["DEF-" + k] = MAPA[k]
	for lado in ["L", "R"]:
		var ld := "Left" if lado == "L" else "Right"
		for f in DEDOS:
			for j in [1, 2, 3]:
				m["DEF-%s.%02d.%s" % [f, j, lado]] = "%sHand%s%d" % [ld, DEDOS[f], j]
	return m

# ordem pai -> filho
static func _ordem(sk: Skeleton3D) -> Array:
	var q: Array = []
	for r in sk.get_parentless_bones():
		q.append(r)
	var k := 0
	while k < q.size():
		for c in sk.get_bone_children(q[k]):
			q.append(c)
		k += 1
	return q

# yaw_graus: rotacao em Y que leva a frente da fonte para a do alvo
static func gerar(sk_t: Skeleton3D, ual: Node, anim_nome: String, dur_alvo: float, yaw_graus: float = 90.0) -> Animation:
	var sk_s := ual.find_child("Skeleton3D", true, false) as Skeleton3D
	var ap := ual.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if sk_s == null or ap == null or not ap.has_animation(anim_nome):
		return null
	var src := ap.get_animation(anim_nome)
	var nomes := _nome_fonte_para_alvo()
	var C := Basis(Vector3.UP, deg_to_rad(yaw_graus))
	var Ci := C.inverse()
	# trilhas da fonte por osso
	var rot_tr: Dictionary = {}
	var pos_tr: Dictionary = {}
	for i in src.get_track_count():
		var cam := String(src.track_get_path(i))
		var osso := cam.get_slice(":", 1) if ":" in cam else ""
		if src.track_get_type(i) == Animation.TYPE_ROTATION_3D:
			rot_tr[osso] = i
		elif src.track_get_type(i) == Animation.TYPE_POSITION_3D:
			pos_tr[osso] = i
	var ord_s := _ordem(sk_s)
	var ord_t := _ordem(sk_t)
	var Rs: Dictionary = {}
	for i in sk_s.get_bone_count():
		Rs[i] = sk_s.get_bone_global_rest(i).basis
	var Rt: Dictionary = {}
	for i in sk_t.get_bone_count():
		Rt[i] = sk_t.get_bone_global_rest(i).basis
	# osso alvo -> osso fonte
	var fonte_de: Dictionary = {}
	for i in sk_s.get_bone_count():
		var nm := sk_s.get_bone_name(i)
		if nm in nomes:
			var bt := sk_t.find_bone("mixamorig_" + nomes[nm])
			if bt >= 0:
				fonte_de[bt] = i
	var hips_s := sk_s.find_bone("DEF-hips")
	var hips_t := sk_t.find_bone("mixamorig_Hips")
	var h_s := maxf(sk_s.get_bone_global_rest(hips_s).origin.y, 0.01)
	var h_t := maxf(sk_t.get_bone_global_rest(hips_t).origin.y, 0.01)
	var esc := h_t / h_s
	var k_t := dur_alvo / maxf(src.length, 0.01)
	var out := Animation.new()
	out.length = dur_alvo
	var tr_alvo: Dictionary = {}
	for bt in fonte_de:
		var idx := out.add_track(Animation.TYPE_ROTATION_3D)
		out.track_set_path(idx, NodePath(PFX + sk_t.get_bone_name(bt).trim_prefix("mixamorig_")))
		tr_alvo[bt] = idx
	var idx_pos := out.add_track(Animation.TYPE_POSITION_3D)
	out.track_set_path(idx_pos, NodePath(PFX + "Hips"))
	var n := int(ceil(src.length * FPS)) + 1
	for f in n:
		var ts := minf(f / FPS, src.length)
		# FK de rotacoes globais da fonte
		var Gs: Dictionary = {}
		for i in ord_s:
			var nm := sk_s.get_bone_name(i)
			var q: Quaternion = sk_s.get_bone_rest(i).basis.get_rotation_quaternion()
			if nm in rot_tr:
				q = src.rotation_track_interpolate(rot_tr[nm], ts)
			var par := sk_s.get_bone_parent(i)
			Gs[i] = Basis(q) if par < 0 else (Gs[par] as Basis) * Basis(q)
		# FK do alvo
		var Gt: Dictionary = {}
		var tk := ts * k_t
		for i in ord_t:
			var par := sk_t.get_bone_parent(i)
			var Gpar: Basis = Basis() if par < 0 else Gt[par]
			var local: Quaternion
			if i in fonte_de:
				var j: int = fonte_de[i]
				var G: Basis = C * (Gs[j] as Basis) * (Rs[j] as Basis).inverse() * Ci * (Rt[i] as Basis)
				G = G.orthonormalized()
				local = (Gpar.inverse() * G).orthonormalized().get_rotation_quaternion()
				out.rotation_track_insert_key(tr_alvo[i], tk, local)
			else:
				local = sk_t.get_bone_rest(i).basis.get_rotation_quaternion()
			Gt[i] = Gpar * Basis(local)
		var pr := sk_s.get_bone_global_rest(hips_s).origin
		var ps := pr
		var nh := "DEF-hips"
		if nh in pos_tr:
			ps = src.position_track_interpolate(pos_tr[nh], ts)
		var d := C * (ps - pr) * esc
		out.position_track_insert_key(idx_pos, tk, sk_t.get_bone_rest(hips_t).origin + d)
	return out
