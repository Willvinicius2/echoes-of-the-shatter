class_name SkillData
extends Resource
## Dados de uma habilidade. Nenhum número de balanceamento mora em script.

enum Shape { ARC, CIRCLE, CONE, DASH }
## Tipos de dano (índices usados por Rules.DAMAGE_TYPE_TAGS).
enum DamageType { PHYSICAL, FIRE, COLD, LIGHTNING }

@export var id: String = ""
@export var display_name: String = ""
@export var short_name: String = ""
@export var tags: PackedStringArray = PackedStringArray()
@export var damage_type: DamageType = DamageType.PHYSICAL
@export var is_attack: bool = true
@export var coefficient: float = 1.0
@export var shape: Shape = Shape.ARC
@export var range_px: float = 60.0
@export var arc_degrees: float = 90.0
@export var radius_px: float = 0.0
@export var dash_distance: float = 0.0
@export var dash_min: float = 0.0
@export var dash_time: float = 0.0
@export var windup: float = 0.1
@export var recovery: float = 0.3
@export var cooldown: float = 0.0
@export var impeto_cost: float = 0.0
@export var impeto_gain: float = 0.0
@export var guard_break: float = 0.0
@export var knockback: float = 0.0
@export var hitstop_ms: float = 0.0
@export var shake: float = 0.0
@export var heavy: bool = false
@export var color: Color = Color(0.78, 0.59, 0.24, 1.0)


## Duração total da ação (preparação + avanço + recuperação), em segundos.
func total_time() -> float:
	var d: float = dash_time if shape == Shape.DASH else 0.0
	return windup + d + recovery


## Retorna a lista de problemas encontrados (vazia = válido).
func validate() -> PackedStringArray:
	var p: PackedStringArray = PackedStringArray()
	if not id.begins_with("skill."):
		p.append("%s: id deve começar com 'skill.'" % id)
	if display_name.is_empty():
		p.append("%s: display_name vazio" % id)
	if coefficient <= 0.0:
		p.append("%s: coeficiente deve ser > 0" % id)
	if windup < 0.0 or recovery < 0.0 or cooldown < 0.0:
		p.append("%s: tempos negativos" % id)
	if not (hitstop_ms == 0.0 or (hitstop_ms >= 40.0 and hitstop_ms <= 80.0)):
		p.append("%s: hitstop_ms deve ser 0 ou entre 40 e 80" % id)
	if shape == Shape.ARC or shape == Shape.CONE:
		if range_px <= 0.0:
			p.append("%s: range_px deve ser > 0" % id)
		if arc_degrees <= 0.0 or arc_degrees > 180.0:
			p.append("%s: arc_degrees deve estar em (0, 180]" % id)
	else:
		if radius_px <= 0.0:
			p.append("%s: radius_px deve ser > 0" % id)
	if shape == Shape.DASH:
		if dash_time <= 0.0:
			p.append("%s: dash_time deve ser > 0" % id)
		if dash_min >= dash_distance:
			p.append("%s: dash_min deve ser < dash_distance" % id)
	return p
