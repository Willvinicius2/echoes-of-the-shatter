class_name EffectData
extends Resource
## Efeito com duração, tick e regra de acúmulo.

enum StackRule { REFRESH, STACK, STRONGEST }

@export var id: String = ""
@export var display_name: String = ""
@export var duration: float = 3.0
@export var stack_rule: StackRule = StackRule.REFRESH
@export var max_stacks: int = 1
## Força do efeito (multiplica o tick; valor do modificador de atributo).
@export var magnitude: float = 1.0
@export var tick_interval: float = 0.0
@export var tick_damage: float = 0.0
@export var damage_type: int = 0
## Modificador de atributo opcional (stat vazio = nenhum).
@export var stat: String = ""
@export var mod_kind: int = 1
@export var tags: PackedStringArray = PackedStringArray()


func validate() -> PackedStringArray:
	var p: PackedStringArray = PackedStringArray()
	if not id.begins_with("effect."):
		p.append("%s: id deve começar com 'effect.'" % id)
	if duration <= 0.0:
		p.append("%s: duração deve ser > 0" % id)
	if max_stacks < 1:
		p.append("%s: max_stacks deve ser >= 1" % id)
	if tick_interval > 0.0 and tick_interval >= duration:
		p.append("%s: tick_interval deve ser < duração" % id)
	return p
