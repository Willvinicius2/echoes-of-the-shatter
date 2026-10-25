extends Node3D
# Arqueiro animado: AnimationTree com AnimationNodeStateMachine.
#   Locomocao = BlendSpace1D (idle 0.0, walk 0.5, run 1.0) -> velocidade normalizada 0..1
#   one-shots: slash, shoot, dash (anim "dive"), hurt, jump, turn, fall, arco (anim "arco_segurando")
# Polimento (25/10): recorte dos one-shots por timeline custom (sem rebuild do GLB),
#   raiz travada em X/Z e altura do quadril limitada, interpolacao cubica, arco escondido fora
#   dos estados de arco, crossfade 0.12 s ida / 0.2 s volta.

const ArcoPoses := preload("res://scripts/arqueiro/tripo/arco_poses.gd")
const RetargetUal := preload("res://scripts/arqueiro/tripo/retarget_ual.gd")
const UAL_GLB := "res://art/models/personagens/ual/ual_standard.glb"
const ROLL_DUR := 0.42  # s: o Roll do Quaternius (CC0) retargetado e comprimido para casar com a esquiva
const LOOPS := ["idle", "walk", "run", "arco_segurando"]
var ONE_SHOTS := {
	"slash": "slash", "shoot": "shoot", "dash": "roll", "hurt": "hurt_pe",
	"jump": "jump", "turn": "turn", "fall": "fall", "arco": "arco_segurando",
	"sacar_arco": "sacar_arco", "guardar_arco": "guardar_arco",
}
# recorte [inicio_s, duracao_s] dentro da animacao original (mocap longo)
const RECORTE := {
	"slash": [1.2, 0.8],
	"shoot": [0.0, 1.2],
	"dash": [0.0, 0.42],
	"hurt": [0.0, 0.45],
	"jump": [0.0, 0.8],
	"turn": [0.0, 0.8],
	"fall": [0.0, 0.8],
	"arco": [0.0, 3.0],
	"sacar_arco": [0.0, 0.6],
	"guardar_arco": [0.0, 0.6],
}
# o que vem depois de cada estado ao terminar (padrao: Locomocao)
const FIM := {"sacar_arco": "arco", "shoot": "arco"}
const ARCO_TIMEOUT := 2.5     # segundos parado em "arco" antes de guardar sozinho
const T_SWAP_SACAR := 0.26    # a mao esquerda passa pelo ombro: ArcoCostas some, Arco aparece
const T_SWAP_GUARDAR := 0.34  # e o inverso ao guardar
const FLECHA_COMP := 0.38
const FLECHA_VEL := 9.0
const FLECHA_VOO := 0.3
const IDLE_LOOP := 3.0
# casa a fase dos pes do run com a do walk (pe esquerdo a frente no mesmo ponto do ciclo normalizado)
const RUN_FASE := 0.396
# atenuacao da rotacao do tronco/cabeca no slash (1 = original, 0 = pose de repouso)
const SLASH_ATEN := {"Head": 0.25, "Neck": 0.3, "Spine2": 0.45, "Spine1": 0.45, "Spine": 0.5, "Hips": 0.7}
# reacao de hurt em pe: graus para tras por osso (eixo X do modelo) e queda do quadril
const HURT_GRAUS := {"Spine": 3.0, "Spine1": 3.0, "Spine2": 3.5, "Head": 3.5}
const HURT_QUEDA := 0.03
const HURT_T := [0.0, 0.1, 0.2, 0.32, 0.45]
const HURT_W := [0.0, 1.0, 0.55, 0.2, 0.0]
const REST_Y := 0.48  # altura do Hips em idle (o hurt do mocap e todo sentado no chao: y=0.09)
const XFADE_IN := 0.12
const XFADE_OUT := 0.2
# quanto falta do one-shot (s) para iniciar a saida (padrao XFADE_OUT + 0.02); o rolamento termina junto da esquiva
const SAIDA_ANT := {"dash": 0.08}
const ESTADOS_ARCO := ["shoot", "arco", "sacar_arco", "guardar_arco"]

@export var velocidade: float = 0.0   # 0 idle, 0.5 walk, 1 run (alvo)
@export var suavizacao: float = 10.0  # 1/s, aproximacao da velocidade ao alvo

@export var segurando: bool = false   # o controlador esta carregando/atirando: nao guardar o arco sozinho
@export var flecha_visual_voo: bool = true  # false no jogo: o Arrow.tscn faz o voo
const PASSO_WALK := 0.51
const PASSO_RUN := 1.59
@export var vel_real: float = -1.0     # m/s do mundo; >= 0 liga o casamento passo x velocidade
@export var escala_corpo: float = 1.0  # escala 3D aplicada ao corpo (muda o passo em m/s)
var _vel_atual := 0.0
var _playback: AnimationNodeStateMachinePlayback
var _espada_mao: Node
var _espada_quadril: Node
var _arco: Node
var _arco_costas: Node
var _len_atual := 0.0
var _corda: Node
var _flecha_mao: Node3D
var _flecha_corda: Node3D
var _flecha_voo: Node3D
var _voo_t := -1.0
var _disparou := false
var _fila: Array = []
var _t_arco := 0.0

# esquiva: rolamento da Universal Animation Library (Quaternius, CC0) retargetado para o esqueleto do arqueiro
func _criar_roll(p: AnimationPlayer) -> void:
	var sk0 := $Modelo.find_child("Skeleton3D", true, false) as Skeleton3D
	if sk0 == null or not ResourceLoader.exists(UAL_GLB):
		ONE_SHOTS["dash"] = "dive"
		return
	var ual: Node = (load(UAL_GLB) as PackedScene).instantiate()
	var a := RetargetUal.gerar(sk0, ual, "Roll", ROLL_DUR)
	ual.free()
	if a == null:
		ONE_SHOTS["dash"] = "dive"
		return
	p.get_animation_library("").add_animation("roll", a)

func player() -> AnimationPlayer:
	return $Modelo.find_child("AnimationPlayer", true, false) as AnimationPlayer

func _ready() -> void:
	var p := player()
	if p == null:
		return
	_criar_roll(p)
	for n in p.get_animation_list():
		var a := p.get_animation(n)
		a.loop_mode = Animation.LOOP_LINEAR if n in LOOPS else Animation.LOOP_NONE
		if n == "run":
			_fase(a, RUN_FASE)
		if n == "slash":
			_atenuar(a, SLASH_ATEN)
		_travar_raiz(a)
		_cubico(a)
	_criar_hurt_pe(p)
	var sk := $Modelo.find_child("Skeleton3D", true, false) as Skeleton3D
	if sk and sk.find_bone("mixamorig_CordaNock") >= 0:
		ArcoPoses.new().instalar(p, sk)
		for n in ["arco_segurando", "shoot", "sacar_arco", "guardar_arco"]:
			var a2 := p.get_animation(n)
			a2.loop_mode = Animation.LOOP_LINEAR if n == "arco_segurando" else Animation.LOOP_NONE
			_cubico(a2)
		_montar_flechas(sk)
	_corda = $Modelo.find_child("Corda", true, false)
	_espada_mao = $Modelo.find_child("EspadaMao", true, false)
	_espada_quadril = $Modelo.find_child("Espada", true, false)
	_arco = $Modelo.find_child("Arco", true, false)
	_arco_costas = $Modelo.find_child("ArcoCostas", true, false)
	_atualizar_props("Locomocao")

	var loco := AnimationNodeBlendSpace1D.new()
	for par in [["idle", 0.0], ["walk", 0.5], ["run", 1.0]]:
		var an := AnimationNodeAnimation.new()
		an.animation = par[0]
		if par[0] == "idle":
			an.use_custom_timeline = true
			an.timeline_length = IDLE_LOOP
			an.start_offset = 0.0
			an.stretch_time_scale = false
			an.loop_mode = Animation.LOOP_LINEAR
		loco.add_blend_point(an, par[1])
	loco.min_space = 0.0
	loco.max_space = 1.0
	loco.blend_mode = AnimationNodeBlendSpace1D.BLEND_MODE_INTERPOLATED
	loco.sync = true

	var sm := AnimationNodeStateMachine.new()
	# locomocao = blend space -> TimeScale (casa o passo com a velocidade real, sem patinar)
	var bt := AnimationNodeBlendTree.new()
	var ts := AnimationNodeTimeScale.new()
	bt.add_node("Loco", loco, Vector2(-300, 0))
	bt.add_node("Escala", ts, Vector2(0, 0))
	bt.connect_node("Escala", 0, "Loco")
	bt.connect_node("output", 0, "Escala")
	sm.add_node("Locomocao", bt, Vector2(0, 0))
	var y := -120.0
	for estado in ONE_SHOTS:
		var an2 := AnimationNodeAnimation.new()
		an2.animation = ONE_SHOTS[estado]
		if estado in RECORTE:
			an2.use_custom_timeline = true
			an2.start_offset = RECORTE[estado][0]
			an2.timeline_length = RECORTE[estado][1]
			an2.stretch_time_scale = false
			an2.loop_mode = Animation.LOOP_LINEAR if estado == "arco" else Animation.LOOP_NONE
		if estado == "shoot":
			# tiro controlado pela carga: TimeScale permite segurar a corda cheia e acelerar o solte
			var bts := AnimationNodeBlendTree.new()
			var ts_s := AnimationNodeTimeScale.new()
			bts.add_node("Anim", an2, Vector2(-300, 0))
			bts.add_node("Escala", ts_s, Vector2(0, 0))
			bts.connect_node("Escala", 0, "Anim")
			bts.connect_node("output", 0, "Escala")
			sm.add_node(estado, bts, Vector2(300, y))
		else:
			sm.add_node(estado, an2, Vector2(300, y))
		y += 80.0
		var ida := AnimationNodeStateMachineTransition.new()
		ida.xfade_time = XFADE_IN
		ida.switch_mode = AnimationNodeStateMachineTransition.SWITCH_MODE_IMMEDIATE
		sm.add_transition("Locomocao", estado, ida)
		var volta := AnimationNodeStateMachineTransition.new()
		volta.xfade_time = XFADE_OUT
		volta.switch_mode = AnimationNodeStateMachineTransition.SWITCH_MODE_AT_END
		sm.add_transition(estado, "Locomocao", volta)
	for par in [["sacar_arco", "arco"], ["shoot", "arco"], ["arco", "shoot"], ["arco", "guardar_arco"]]:
		var trn := AnimationNodeStateMachineTransition.new()
		trn.xfade_time = XFADE_IN
		trn.switch_mode = AnimationNodeStateMachineTransition.SWITCH_MODE_IMMEDIATE
		sm.add_transition(par[0], par[1], trn)
	sm.set_graph_offset(Vector2(-100, -150))
	sm.add_transition("Start", "Locomocao", AnimationNodeStateMachineTransition.new())

	var arv: AnimationTree = $Arvore
	arv.tree_root = _camada_pernas(sm, loco.duplicate(true), p)
	arv.anim_player = arv.get_path_to(p)
	arv.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_IDLE
	arv.active = true
	_playback = arv.get("parameters/Sm/playback")
	_playback.start("Locomocao")

var _mist := 0.0
var _pos_shoot := 0.0     # posicao do clipe shoot (s), acumulada aqui com a escala de tempo aplicada
var _solto := false
var _carga := 0.0
var _escala_shoot := 1.0

# Chamado todo quadro pelo controlador: carga 0..1 e se o botao ja foi solto.
# Segura a corda cheia (T_FULL) enquanto carrega; ao soltar corre ate T_REL (solte) e segue ate T_END.
func mirar(carga: float, solto: bool) -> void:
	_carga = carga
	_solto = solto

func shoot_solta() -> bool:
	return estado_atual() == "shoot" and _pos_shoot >= ArcoPoses.T_REL

func shoot_terminou() -> bool:
	return estado_atual() != "shoot" or _pos_shoot >= ArcoPoses.T_END - XFADE_OUT

# Camada de pernas: a maquina de estados (tronco, bracos, arco) fica em "Sm"; as pernas vem da locomocao
# (idle/walk/run casados com a velocidade real) quando o personagem se move nos estados de arco.
func _camada_pernas(sm: AnimationNodeStateMachine, loco2: AnimationNodeBlendSpace1D, p: AnimationPlayer) -> AnimationNodeBlendTree:
	var raiz := AnimationNodeBlendTree.new()
	var ts2 := AnimationNodeTimeScale.new()
	var mist := AnimationNodeBlend2.new()
	mist.filter_enabled = true
	if p.has_animation("walk"):
		var a := p.get_animation("walk")
		for i in a.get_track_count():
			var caminho := String(a.track_get_path(i))
			var osso := caminho.get_slice(":", 1) if ":" in caminho else ""
			if osso.contains("Leg") or osso.contains("Foot") or osso.contains("Toe"):
				mist.set_filter_path(a.track_get_path(i), true)
	raiz.add_node("Sm", sm, Vector2(-400, 0))
	raiz.add_node("LocoPernas", loco2, Vector2(-400, 200))
	raiz.add_node("EscalaPernas", ts2, Vector2(-200, 200))
	raiz.add_node("Mistura", mist, Vector2(0, 0))
	raiz.connect_node("EscalaPernas", 0, "LocoPernas")
	raiz.connect_node("Mistura", 0, "Sm")
	raiz.connect_node("Mistura", 1, "EscalaPernas")
	raiz.connect_node("output", 0, "Mistura")
	return raiz

func duracao(estado: String) -> float:
	return RECORTE[estado][1] if estado in RECORTE else 0.0

func tocar(estado: String) -> void:
	if estado == "shoot":
		_pos_shoot = 0.0
		_solto = false
		_fila.clear()
		if not (estado_atual() in ESTADOS_ARCO):
			_playback.travel("shoot")
			return
		if estado_atual() == "shoot":
			return
	# one-shot: "slash", "dash", "hurt", "jump", "turn", "fall"
	# arco: "sacar_arco" (0.6 s) -> "arco" (guarda, loop) ; "shoot" (1.2 s) a partir de "arco" (se nao estiver, saca antes);
	#       "guardar_arco" (0.6 s) volta o arco para as costas (tambem automatico apos ARCO_TIMEOUT s parado)
	if _playback == null:
		return
	var est := estado_atual()
	match estado:
		"shoot":
			if est == "guardar_arco":
				return
			if est == "sacar_arco":
				_fila = ["shoot"]
				return
			if not (est in ESTADOS_ARCO):
				_fila = ["shoot"]
				_playback.travel("sacar_arco")
				return
		"arco", "sacar_arco":
			if est in ESTADOS_ARCO:
				return
			_fila.clear()
			_playback.travel("sacar_arco")
			return
		"guardar_arco":
			if not (est in ESTADOS_ARCO) or est == "guardar_arco":
				return
			_fila.clear()
	_playback.travel(estado)

func em_arco() -> bool:
	return estado_atual() in ESTADOS_ARCO

func estado_atual() -> String:
	return String(_playback.get_current_node()) if _playback else ""

func _atualizar_props(est: String) -> void:
	var espada := est == "slash"
	if _espada_mao:
		_espada_mao.visible = espada
	if _espada_quadril:
		_espada_quadril.visible = not espada
	var pos := 0.0
	if _playback and est != "":
		pos = _playback.get_current_play_position()
	var na_mao := est in ESTADOS_ARCO
	if est == "sacar_arco":
		na_mao = pos >= T_SWAP_SACAR
	elif est == "guardar_arco":
		na_mao = pos < T_SWAP_GUARDAR
	if _arco:
		_arco.visible = na_mao
	if _corda:
		_corda.visible = na_mao
	if _arco_costas:
		_arco_costas.visible = false  # fora do tiro nenhum arco aparece nas costas
	var em_tiro := est == "shoot"
	if _flecha_mao:
		_flecha_mao.visible = em_tiro and pos >= ArcoPoses.T_GRAB and pos < ArcoPoses.T_NOCK
	if _flecha_corda:
		_flecha_corda.visible = em_tiro and pos >= ArcoPoses.T_NOCK and pos < ArcoPoses.T_REL
	if em_tiro and pos >= ArcoPoses.T_REL and not _disparou:
		_disparou = true
		_disparar()
	if not em_tiro:
		_disparou = false

func _material(c: Color, metal: float = 0.0, rug: float = 0.7) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.metallic = metal
	m.roughness = rug
	return m

# flecha: haste + ponta + penas; origem na ponta de tras (encaixe), eixo +Y para a ponta; comprimento FLECHA_COMP (0.38)
func _criar_flecha(nome: String) -> Node3D:
	var raiz := Node3D.new()
	raiz.name = nome
	var haste := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = 0.0035
	cm.bottom_radius = 0.0035
	cm.height = FLECHA_COMP - 0.05
	cm.radial_segments = 8
	haste.mesh = cm
	haste.material_override = _material(Color(0.62, 0.45, 0.25))
	haste.position = Vector3(0, cm.height * 0.5, 0)
	raiz.add_child(haste)
	var ponta := MeshInstance3D.new()
	var pm := CylinderMesh.new()
	pm.top_radius = 0.0
	pm.bottom_radius = 0.0085
	pm.height = 0.05
	pm.radial_segments = 8
	ponta.mesh = pm
	ponta.material_override = _material(Color(0.72, 0.74, 0.8), 0.8, 0.35)
	ponta.position = Vector3(0, FLECHA_COMP - 0.025, 0)
	raiz.add_child(ponta)
	for i in 3:
		var pena := MeshInstance3D.new()
		var bm := BoxMesh.new()
		bm.size = Vector3(0.0012, 0.05, 0.014)
		pena.mesh = bm
		pena.material_override = _material(Color(0.78, 0.16, 0.12))
		var piv := Node3D.new()
		piv.rotation = Vector3(0, deg_to_rad(120.0 * i), 0)
		pena.position = Vector3(0, 0.035, 0.009)
		piv.add_child(pena)
		raiz.add_child(piv)
	raiz.visible = false
	return raiz

func _montar_flechas(sk: Skeleton3D) -> void:
	var mao := BoneAttachment3D.new()
	mao.bone_name = "mixamorig_RightHand"
	mao.name = "AncoraMaoDireita"
	sk.add_child(mao)
	_flecha_mao = _criar_flecha("FlechaMao")
	var rest_rh := sk.get_bone_global_rest(sk.find_bone("mixamorig_RightHand"))
	var gr := Vector3(0, (rest_rh.affine_inverse() * sk.get_bone_global_rest(sk.find_bone("mixamorig_RightHandIndex2")).origin).y, 0)
	_flecha_mao.position = gr
	mao.add_child(_flecha_mao)
	var nock := BoneAttachment3D.new()
	nock.bone_name = "mixamorig_CordaNock"
	nock.name = "AncoraCorda"
	sk.add_child(nock)
	_flecha_corda = _criar_flecha("FlechaCorda")
	_flecha_corda.basis = Basis(Quaternion(Vector3.UP, ArcoPoses.ARCO_VENTRE.normalized()))
	nock.add_child(_flecha_corda)
	_flecha_voo = _criar_flecha("FlechaVoo")
	add_child(_flecha_voo)

func _disparar() -> void:
	if not flecha_visual_voo:
		return  # no jogo a flecha real vem do ArqueiroController
	if _flecha_corda == null or _flecha_voo == null:
		return
	_flecha_voo.global_transform = _flecha_corda.global_transform
	_flecha_voo.visible = true
	_voo_t = 0.0

func _process(delta: float) -> void:
	if _playback == null:
		return
	var ts_alvo := 1.0
	if vel_real >= 0.0:
		# vel_real em m/s do mundo; passo medido dos clipes (escala 1): walk 0.51 m/s, run 1.59 m/s
		var vw := PASSO_WALK * escala_corpo
		var vr := PASSO_RUN * escala_corpo
		var alvo := 0.0
		if vel_real < 0.15:
			alvo = 0.0
		elif vel_real < vw:
			alvo = 0.5 * vel_real / vw
		elif vel_real < vr:
			alvo = 0.5 + 0.5 * (vel_real - vw) / (vr - vw)
		else:
			alvo = 1.0
			ts_alvo = clampf(vel_real / vr, 1.0, 2.2)
		_vel_atual = lerpf(_vel_atual, alvo, 1.0 - exp(-suavizacao * delta))
	else:
		_vel_atual = lerpf(_vel_atual, velocidade, 1.0 - exp(-suavizacao * delta))
	$Arvore.set("parameters/Sm/Locomocao/Loco/blend_position", _vel_atual)
	$Arvore.set("parameters/Sm/Locomocao/Escala/scale", ts_alvo)
	$Arvore.set("parameters/LocoPernas/blend_position", _vel_atual)
	$Arvore.set("parameters/EscalaPernas/scale", ts_alvo)
	var est := estado_atual()
	if est == "shoot":
		var alvo_pos := ArcoPoses.T_FULL * _carga
		var esc := 1.0
		if _solto:
			esc = 3.0 if _pos_shoot < ArcoPoses.T_REL - 0.03 else 1.0
		else:
			esc = clampf((alvo_pos - _pos_shoot) / 0.05, 0.0, 2.5)
			if _pos_shoot >= ArcoPoses.T_FULL:
				esc = 0.0
		_escala_shoot = esc
		$Arvore.set("parameters/Sm/shoot/Escala/scale", esc)
		_pos_shoot += delta * esc
	# nos estados de arco (sacar, mirar, atirar) as pernas seguem a locomocao: anda com o arco na mao, sem patinar
	var alvo_mist := clampf(_vel_atual * 8.0, 0.0, 1.0) if est in ESTADOS_ARCO else 0.0
	_mist = lerpf(_mist, alvo_mist, 1.0 - exp(-14.0 * delta))
	$Arvore.set("parameters/Mistura/blend_amount", _mist)
	_atualizar_props(est)
	# voo da flecha: translacao em linha reta por FLECHA_VOO s
	if _voo_t >= 0.0:
		_voo_t += delta
		_flecha_voo.global_position += _flecha_voo.global_transform.basis.y.normalized() * FLECHA_VEL * delta
		if _voo_t >= FLECHA_VOO:
			_voo_t = -1.0
			_flecha_voo.visible = false
	if est == "arco":
		_t_arco = 0.0 if segurando else _t_arco + delta
		if not _fila.is_empty():
			_playback.travel(_fila.pop_front())
		elif _t_arco > ARCO_TIMEOUT:
			_playback.travel("guardar_arco")
	else:
		_t_arco = 0.0
	# ao fim do one-shot vai para o proximo estado (o AT_END automatico nao disparou nesta versao; fazemos explicitamente)
	if est == "shoot":
		if _solto and _pos_shoot >= ArcoPoses.T_END - XFADE_OUT:
			_playback.travel("Locomocao")
	elif est != "Locomocao" and est != "arco" and est != "":
		var restante := _playback.get_current_length() - _playback.get_current_play_position()
		if restante <= SAIDA_ANT.get(est, XFADE_OUT + 0.02):
			var prox: String = FIM.get(est, "Locomocao")
			if est == "sacar_arco" and not _fila.is_empty():
				prox = _fila.pop_front()
			_playback.travel(prox)

# Remove a translacao X/Z do Hips (movimento no lugar) e limita a altura do quadril
func _travar_raiz(a: Animation) -> void:
	for i in a.get_track_count():
		if a.track_get_type(i) != Animation.TYPE_POSITION_3D:
			continue
		var path := String(a.track_get_path(i))
		if not path.ends_with("Hips"):
			continue
		var n := a.track_get_key_count(i)
		if n == 0:
			continue
		if a.track_is_compressed(i):
			push_warning("faixa Hips comprimida em " + a.resource_name + "; raiz nao travada")
			continue
		var p0: Vector3 = a.track_get_key_value(i, 0)
		var ymin := p0.y
		for k in n:
			var v: Vector3 = a.track_get_key_value(i, k)
			ymin = minf(ymin, v.y)
			v.x = p0.x
			v.z = p0.z
			v.y = clampf(v.y, REST_Y - 0.13, REST_Y + 0.25)
			a.track_set_key_value(i, k, v)
		if ymin < REST_Y - 0.2:
			print("RAIZ ", a.resource_name, ": quadril ia a y=", ymin, "; travado em ", REST_Y - 0.13)

func _cubico(a: Animation) -> void:
	for i in a.get_track_count():
		var t := a.track_get_type(i)
		if t == Animation.TYPE_POSITION_3D or t == Animation.TYPE_ROTATION_3D or t == Animation.TYPE_SCALE_3D:
			a.track_set_interpolation_type(i, Animation.INTERPOLATION_CUBIC)

func _osso(nome_track: String) -> String:
	return nome_track.get_slice(":", 1)

# desloca a fase de uma animacao ciclica: novo(t) = antigo(t + off), reamostrado a 30 fps
func _fase(a: Animation, off: float) -> void:
	var n := int(round(a.length * 30.0))
	for i in a.get_track_count():
		var t := a.track_get_type(i)
		if (t != Animation.TYPE_POSITION_3D and t != Animation.TYPE_ROTATION_3D) or a.track_is_compressed(i):
			continue
		var vals := []
		for k in n + 1:
			var tk := fposmod(minf(k / 30.0, a.length) + off, a.length)
			vals.append(a.position_track_interpolate(i, tk) if t == Animation.TYPE_POSITION_3D else a.rotation_track_interpolate(i, tk))
		while a.track_get_key_count(i) > 0:
			a.track_remove_key(i, 0)
		for k in n + 1:
			a.track_insert_key(i, minf(k / 30.0, a.length), vals[k])

# aproxima a rotacao dos ossos listados da pose de repouso (fator < 1 reduz o movimento)
func _atenuar(a: Animation, fatores: Dictionary) -> void:
	var sk := $Modelo.find_child("Skeleton3D", true, false) as Skeleton3D
	if sk == null:
		return
	for i in a.get_track_count():
		if a.track_get_type(i) != Animation.TYPE_ROTATION_3D or a.track_is_compressed(i):
			continue
		var nome := _osso(String(a.track_get_path(i)))
		var f := -1.0
		for k in fatores:
			if nome.ends_with(k):
				f = fatores[k]
		var b := sk.find_bone(nome)
		if f < 0.0 or b < 0:
			continue
		var rest := sk.get_bone_rest(b).basis.get_rotation_quaternion()
		for k in a.track_get_key_count(i):
			var q: Quaternion = a.track_get_key_value(i, k)
			a.track_set_key_value(i, k, rest.slerp(q, f))

# hurt em pe: copia do idle com tronco/cabeca indo para tras e quadril caindo, ease-out
func _criar_hurt_pe(p: AnimationPlayer) -> void:
	var sk := $Modelo.find_child("Skeleton3D", true, false) as Skeleton3D
	var idle := p.get_animation("idle")
	if sk == null or idle == null:
		return
	var h := idle.duplicate() as Animation
	h.length = HURT_T[HURT_T.size() - 1]
	h.loop_mode = Animation.LOOP_NONE
	var eixo_modelo := ($Modelo as Node3D).global_transform.basis * Vector3.BACK  # o modelo olha para +X; lateral = Z; +Z inclina o tronco para tras
	for i in h.get_track_count():
		var t := h.track_get_type(i)
		if h.track_is_compressed(i):
			continue
		var nome := _osso(String(h.track_get_path(i)))
		if t == Animation.TYPE_ROTATION_3D:
			var graus := 0.0
			for k in HURT_GRAUS:
				if nome.ends_with(k):
					graus = HURT_GRAUS[k]
			var b := sk.find_bone(nome)
			if graus == 0.0 or b < 0:
				continue
			var eixo_sk := sk.global_transform.basis.inverse() * eixo_modelo
			var eixo := (sk.get_bone_global_rest(b).basis.inverse() * eixo_sk).normalized()
			var vals := []
			for k in HURT_T.size():
				var q: Quaternion = idle.rotation_track_interpolate(i, HURT_T[k])
				vals.append(q * Quaternion(eixo, deg_to_rad(graus) * HURT_W[k]))
			while h.track_get_key_count(i) > 0:
				h.track_remove_key(i, 0)
			for k in HURT_T.size():
				h.track_insert_key(i, HURT_T[k], vals[k])
		elif t == Animation.TYPE_POSITION_3D and nome.ends_with("Hips"):
			var vals2 := []
			for k in HURT_T.size():
				var v: Vector3 = idle.position_track_interpolate(i, HURT_T[k])
				vals2.append(v + Vector3(0, -HURT_QUEDA * HURT_W[k], 0))
			while h.track_get_key_count(i) > 0:
				h.track_remove_key(i, 0)
			for k in HURT_T.size():
				h.track_insert_key(i, HURT_T[k], vals2[k])
	_cubico(h)
	p.get_animation_library("").add_animation("hurt_pe", h)
