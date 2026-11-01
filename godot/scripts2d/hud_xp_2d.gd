extends CanvasLayer
## Barra de experiência e nível do personagem (modo horda). Fica numa camada própria, fina, no topo da tela, para
## caber em qualquer versão da HUD de baixo. Os números (nível, XP, XP do próximo nível) vêm do core pela ponte
## `upgrades.nivel_estado()`; medidas e cores em data2d/hud_xp.csv; texto por chave de localização.

const Csv = preload("res://scripts2d/csv2d.gd")
const Tema = preload("res://scripts2d/tema_2d.gd")

var upgrades: RefCounted     # ponte do core (nivel_estado)
var jogador: Node            # recebe nivel_jogador, xp e xp_proximo (a HUD principal lê daqui)
var ativo := false           # só o modo horda tem nível
var _ctl: Control
var _lay := {}
var _nivel := 1
var _xp := 0.0
var _xp_prox := 1.0
var _fracao := 0.0           # fração exibida (sobe suave)
var _brilho := 0.0           # pulso de 1 s ao subir de nível
var _t := 0.0

func _ready() -> void:
	layer = 8
	_lay = Csv.kv("res://data2d/hud_xp.csv")
	_ctl = Control.new()
	_ctl.set_anchors_preset(Control.PRESET_FULL_RECT)
	_ctl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_ctl.draw.connect(_desenhar)
	add_child(_ctl)

func _process(d: float) -> void:
	_ctl.visible = ativo
	if not ativo or upgrades == null or not upgrades.has_method("nivel_estado"):
		return
	_t += d
	var e: Dictionary = upgrades.nivel_estado()
	var nv := int(e.get("level", 1))
	if nv > _nivel:
		_brilho = 1.0
	_nivel = nv
	_xp = float(e.get("xp", 0))
	_xp_prox = maxf(1.0, float(e.get("xp_next", 1)))
	var alvo := clampf(_xp / _xp_prox, 0.0, 1.0)
	_fracao = alvo if alvo < _fracao else lerpf(_fracao, alvo, minf(1.0, d * float(_lay.get("suavizar", 8.0))))
	_brilho = maxf(0.0, _brilho - d)
	if jogador != null and is_instance_valid(jogador) and "xp_proximo" in jogador:
		jogador.nivel_jogador = _nivel
		jogador.xp = _xp
		jogador.xp_proximo = _xp_prox
	_ctl.queue_redraw()

func _desenhar() -> void:
	if int(_lay.get("barra_propria", 1)) != 1:
		return   # a HUD principal desenha a barra; este componente só mantém jogador.xp e companhia
	var vp := _ctl.size
	var alt: float = _lay.get("altura", 8.0)
	var m: float = _lay.get("margem", 0.0)
	var r := Rect2(m, 0.0, vp.x - m * 2.0, alt)
	_ctl.draw_rect(r, Color(0.02, 0.02, 0.04, 0.8))
	var cheio := Rect2(r.position, Vector2(r.size.x * _fracao, r.size.y))
	var cor: Color = Tema.cor("destaque").lerp(Color(1, 1, 1), _brilho * 0.6)
	_ctl.draw_rect(cheio, cor)
	_ctl.draw_rect(Rect2(cheio.position, Vector2(cheio.size.x, 2.0)), cor.lightened(0.35))
	_ctl.draw_rect(r, Tema.cor("metal_medio"), false, 1.0)
	# Selo do nível, encostado no canto de cima à esquerda.
	var fonte := ThemeDB.fallback_font
	var tam := int(_lay.get("fonte", 18))
	var txt: String = Csv.t("hud.level") % _nivel
	var larg := fonte.get_string_size(txt, HORIZONTAL_ALIGNMENT_LEFT, -1, tam).x + 22.0
	var selo := Rect2(8.0, alt + 4.0, larg, tam + 10.0)
	_ctl.draw_rect(selo, Color(0.04, 0.04, 0.07, 0.85))
	_ctl.draw_rect(selo, Tema.cor("destaque").lerp(Color(1, 1, 1), _brilho), false, 2.0)
	_ctl.draw_string(fonte, selo.position + Vector2(11.0, tam + 1.0), txt, HORIZONTAL_ALIGNMENT_LEFT, -1, tam, Tema.cor("texto"))
	var xp_txt: String = Csv.t("hud.xp") % [int(_xp), int(_xp_prox)]
	_ctl.draw_string(fonte, selo.position + Vector2(larg + 8.0, tam), xp_txt, HORIZONTAL_ALIGNMENT_LEFT, -1, int(_lay.get("fonte_xp", 14)), Tema.cor("texto_suave"))
