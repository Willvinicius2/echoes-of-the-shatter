extends CanvasLayer
## HUD de ARPG sombrio: globos de vida e recurso, barra de habilidades de pedra e ferro, plaqueta da sala, barra do chefe
## e mensagem central. Peças em hud_arte_2d.gd; medidas em data2d/hud_layout.csv; textos por chave de localização.

const Csv = preload("res://scripts2d/csv2d.gd")
const Tema = preload("res://scripts2d/tema_2d.gd")
const Icones = preload("res://scripts2d/icones_2d.gd")
const Arte = preload("res://scripts2d/hud_arte_2d.gd")

var jogador: Node2D
var sala := 1
var total_salas := 1
var mensagem := ""
var chefe: Node2D
var upgrades: RefCounted
var tempo := 0.0
var _ctl: Control
var _lay := {}
var _rel := 0.0         # relógio da animação (líquido, pulso)
var _hp_fantasma := 1.0 # fração antiga de vida, desce devagar depois de um golpe

func _ready() -> void:
	_lay = Csv.kv("res://data2d/hud_layout.csv")
	_ctl = Control.new()
	_ctl.set_anchors_preset(Control.PRESET_FULL_RECT)
	_ctl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_ctl.draw.connect(_desenhar)
	add_child(_ctl)

func _process(d: float) -> void:
	_rel += d
	if jogador != null and "hp" in jogador:
		var f: float = clampf(jogador.hp / jogador.stats.get("hp_max", 1.0), 0.0, 1.0)
		_hp_fantasma = f if f >= _hp_fantasma else maxf(f, _hp_fantasma - d * 0.35)
	_ctl.queue_redraw()

func _desenhar() -> void:
	var vp := _ctl.size
	_fundo_inferior(vp)
	if jogador != null and "hp" in jogador:
		_desenhar_base(vp)
		_desenhar_habilidades(vp)
		_desenhar_globos(vp)
	_desenhar_upgrades()
	Arte.plaqueta(_ctl, Rect2(vp.x - 8 - _lay["plaqueta_largura"], 8, _lay["plaqueta_largura"], 58), Csv.t("hud.room") % [sala, total_salas], Csv.t("hud.time") % _tempo_texto())
	if _rel < 8.0 and estado_ajuda_visivel():
		var al := clampf((8.0 - _rel) / 2.0, 0.0, 1.0)
		var cor := Color(Tema.cor("texto").r, Tema.cor("texto").g, Tema.cor("texto").b, al)
		var partes := Csv.t("hud.help").split(" | ")
		var meio := int(ceil(partes.size() / 2.0))
		var esq := " | ".join(partes.slice(0, meio))
		var dir := " | ".join(partes.slice(meio))
		Arte.texto(_ctl, Vector2(165, vp.y - 34), esq, 14, cor, HORIZONTAL_ALIGNMENT_RIGHT, 410.0)
		Arte.texto(_ctl, Vector2(1000, vp.y - 34), dir, 14, cor, HORIZONTAL_ALIGNMENT_LEFT, 410.0)
	if chefe != null and is_instance_valid(chefe) and chefe.hp > 0.0:
		var w: float = _lay["chefe_largura"]
		var r := Rect2(vp.x * 0.5 - w * 0.5, 62, w, 18)
		Arte.barra(_ctl, r, chefe.hp / chefe.hp_max, Tema.cor("chefe_escura"), Tema.cor("chefe_clara"))
		Arte.texto(_ctl, Vector2(r.position.x, r.position.y - 12), Csv.t("hud.boss"), 18, Tema.cor("destaque"), HORIZONTAL_ALIGNMENT_CENTER, w)
	if mensagem != "":
		Arte.texto(_ctl, Vector2(0, vp.y * 0.3), mensagem, 32, Tema.cor("texto"), HORIZONTAL_ALIGNMENT_CENTER, vp.x)

## A lista completa de controles só aparece nos primeiros segundos (os slots já têm as plaquinhas de tecla).
func estado_ajuda_visivel() -> bool:
	return mensagem == ""

func _tempo_texto() -> String:
	var total := int(tempo)
	return "%02d:%02d" % [total / 60, total % 60]

## Sombra suave no rodapé para os globos e a barra ficarem legíveis sobre qualquer sala.
func _fundo_inferior(vp: Vector2) -> void:
	var h := 190.0
	_ctl.draw_polygon(PackedVector2Array([Vector2(0, vp.y - h), Vector2(vp.x, vp.y - h), Vector2(vp.x, vp.y), Vector2(0, vp.y)]), PackedColorArray([Color(0, 0, 0, 0), Color(0, 0, 0, 0), Color(0, 0, 0, 0.45), Color(0, 0, 0, 0.45)]))

func _centro_globo(vp: Vector2, direita: bool) -> Vector2:
	var r: float = _lay["globo_raio"]
	var m: float = _lay["globo_margem"]
	return Vector2(vp.x - m - r if direita else m + r, vp.y - m - r)

## Faixa de ferro e pedra que liga os dois globos por baixo da barra de habilidades, com friso dourado e gema central.
func _desenhar_base(vp: Vector2) -> void:
	var e := _centro_globo(vp, false)
	var d := _centro_globo(vp, true)
	var alt: float = _lay["base_altura"]
	var r := Rect2(e.x + 50.0, vp.y - alt, d.x - e.x - 100.0, alt)
	_ctl.draw_rect(r.grow(3), Color(0, 0, 0, 0.6))
	_ctl.draw_rect(r, Tema.cor("metal_escuro"))
	var miolo := r.grow(-4)
	Arte.alvenaria(_ctl, miolo)
	# moldura de ferro: borda, friso dourado em cima e rebites nos cantos
	_ctl.draw_rect(r, Tema.cor("metal_medio"), false, 2.0)
	_ctl.draw_rect(Rect2(r.position.x, r.position.y, r.size.x, 4), Tema.cor("metal_medio"))
	_ctl.draw_rect(Rect2(r.position.x, r.position.y + 4, r.size.x, 1.5), Tema.cor("destaque").darkened(0.2))
	for k in 20:
		Arte.rebite(_ctl, Vector2(r.position.x + 14 + k * (r.size.x - 28) / 19.0, r.position.y + 2), 1.8)
	Arte.losango(_ctl, Vector2(vp.x * 0.5, r.position.y + 4), 8.0, Tema.cor("destaque"))

## Vida (esquerda) e recurso (direita, reservado e vazio). Vida baixa pulsa no aro.
func _desenhar_globos(vp: Vector2) -> void:
	var raio: float = _lay["globo_raio"]
	var hmax: float = jogador.stats.get("hp_max", 1.0)
	var frac: float = clampf(jogador.hp / hmax, 0.0, 1.0)
	var pulso := (0.4 + 0.6 * (0.5 + 0.5 * sin(_rel * 5.0))) if frac < 0.3 and frac > 0.0 else 0.0
	var ev := _centro_globo(vp, false)
	Arte.globo(_ctl, ev, raio, frac, _hp_fantasma, Tema.cor("vida_escura"), Tema.cor("vida_clara"), _rel, pulso)
	Arte.texto(_ctl, ev + Vector2(-raio, 4), "%d/%d" % [ceili(jogador.hp), int(hmax)], 18, Tema.cor("texto"), HORIZONTAL_ALIGNMENT_CENTER, raio * 2.0)
	Arte.texto(_ctl, Vector2(ev.x + raio + 10, ev.y + 30), Csv.t("hud.hp"), 14, Tema.cor("texto_suave"))
	var ed := _centro_globo(vp, true)
	Arte.globo(_ctl, ed, raio, 0.0, 0.0, Tema.cor("mana_escura"), Tema.cor("mana_clara"), _rel, 0.0, true)
	# corrente nítida em X sobre o vidro vazio e cadeado pequeno no centro
	var rr := raio * 0.66
	Arte.corrente(_ctl, ed + Vector2(-rr, -rr), ed + Vector2(rr, rr), 7)
	Arte.corrente(_ctl, ed + Vector2(rr, -rr), ed + Vector2(-rr, rr), 7)
	Arte.cadeado(_ctl, ed + Vector2(0, -8), 20.0)
	Arte.texto(_ctl, Vector2(ed.x - raio - 150, ed.y + 30), Csv.t("hud.mana"), 14, Tema.cor("texto_suave"), HORIZONTAL_ALIGNMENT_RIGHT, 140.0)

func _desenhar_upgrades() -> void:
	if upgrades == null or upgrades.niveis.is_empty():
		return
	var x: float = _lay["margem"] - 8
	var y: float = _lay["lista_y"]
	var lado := 38.0
	var mouse := _ctl.get_local_mouse_position()
	var dica := ""
	var dica_pos := Vector2.ZERO
	for id in upgrades.ordem:
		var nv: int = upgrades.nivel(id)
		if nv <= 0:
			continue
		var r := Rect2(x, y, lado, lado)
		Arte.placa(_ctl, r, Tema.cor("pedra").darkened(0.15), 2.0, false)
		_ctl.draw_texture_rect(Icones.textura(id), r.grow(-6), false)
		var sel := r.has_point(mouse)
		if sel:
			_ctl.draw_rect(r, Tema.cor("destaque"), false, 2.0)
			dica = "%s x%d" % [Csv.t("upgrade.%s.name" % id), nv]
			dica_pos = Vector2(r.position.x, r.end.y + 6)
		if nv > 1:
			var tag := Rect2(r.end.x - 20, r.end.y - 14, 22, 16)
			Arte.placa(_ctl, tag, Tema.cor("metal_escuro"), 1.0, false)
			Arte.texto(_ctl, Vector2(tag.position.x, tag.position.y + 12), "x%d" % nv, 12, Tema.cor("destaque").lightened(0.25), HORIZONTAL_ALIGNMENT_CENTER, tag.size.x)
		x += lado + 8.0
	if dica != "":
		var fonte := ThemeDB.fallback_font
		var larg := fonte.get_string_size(dica, HORIZONTAL_ALIGNMENT_LEFT, -1, 15).x + 20.0
		var rd := Rect2(dica_pos, Vector2(larg, 26))
		Arte.placa(_ctl, rd, Tema.cor("pedra"), 2.0, false)
		Arte.texto(_ctl, rd.position + Vector2(0, 19), dica, 15, Tema.cor("texto"), HORIZONTAL_ALIGNMENT_CENTER, larg)

## Barra de habilidades: slots 0 e 1 = tiro e esquiva (lêem a recarga do jogador); o resto fica bloqueado.
## A barra fina de estamina (recarga da esquiva) fica logo acima dos slots.
func _desenhar_habilidades(vp: Vector2) -> void:
	var lado: float = _lay["slot_tamanho"]
	var esp: float = _lay["slot_espaco"]
	var total := int(_lay["slot_total"])
	var largura := total * lado + (total - 1) * esp
	var x0 := (vp.x - largura) * 0.5
	var y0: float = vp.y - _lay["slot_base"] - lado
	var cdmax: float = jogador.stats.get("dodge_cooldown", 1.0)
	var rec_esq := clampf(jogador.dodge_cd / cdmax, 0.0, 1.0)
	var bw: float = _lay["estamina_barra_largura"]
	Arte.barra(_ctl, Rect2((vp.x - bw) * 0.5, y0 - 24.0, bw, 7.0), 1.0 - rec_esq, Tema.cor("estamina").darkened(0.5), Tema.cor("estamina_clara"), 0)
	var fr := Rect2((vp.x - bw) * 0.5, y0 - 24.0, bw, 7.0).grow(4)
	for q in [fr.position, Vector2(fr.end.x, fr.position.y), Vector2(fr.position.x, fr.end.y), fr.end]:
		Arte.rebite(_ctl, q, 2.4)
	var slots := [
		{"icone": "tiro", "tecla": "hud.key.shoot", "recarga": jogador.recarga_tiro() if jogador.has_method("recarga_tiro") else 0.0, "cor": Tema.cor("destaque")},
		{"icone": "esquiva", "tecla": "hud.key.dodge", "recarga": rec_esq, "cor": Tema.cor("estamina")},
	]
	for i in total:
		var r := Rect2(x0 + i * (lado + esp), y0, lado, lado)
		if i < slots.size():
			var sl: Dictionary = slots[i]
			Arte.slot(_ctl, r, Icones.textura(sl["icone"]), sl["recarga"], Csv.t(sl["tecla"]), true, sl["cor"])
		else:
			Arte.slot(_ctl, r, Icones.textura("bloqueado"), 0.0, "", false, Color.WHITE)
