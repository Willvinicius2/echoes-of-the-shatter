class_name ClassData
extends Resource
## Dados de uma classe jogável (F1: Guerreiro).

@export var id: String = ""
@export var display_name: String = ""
## Ordem: ataque básico, skill_1, skill_2, skill_3.
@export var skill_ids: PackedStringArray = PackedStringArray()

@export var max_life: float = 200.0
@export var damage: float = 10.0
@export var armour: float = 0.0
@export var evasion: float = 0.0
@export var block: float = 0.0
@export var block_reduction: float = 50.0
@export var crit_chance: float = 5.0
@export var crit_multiplier: float = 150.0
@export var res_fire: float = 0.0
@export var res_cold: float = 0.0
@export var res_lightning: float = 0.0

@export var move_speed: float = 150.0
@export var action_move_mult: float = 0.35
@export var kb_decay: float = 900.0
@export var radius: float = 9.0

@export var max_impeto: float = 100.0
@export var impeto_decay_delay: float = 3.0
@export var impeto_decay_rate: float = 8.0
@export var impeto_on_block: float = 12.0
## Aumento de dano (fração) por ponto de Ímpeto.
@export var impeto_damage_per_point: float = 0.004

@export var dodge_duration: float = 0.35
@export var dodge_invuln: float = 0.2
@export var dodge_charges: int = 3
@export var dodge_recharge: float = 1.5
@export var dodge_distance: float = 110.0


func validate() -> PackedStringArray:
	var p: PackedStringArray = PackedStringArray()
	if not id.begins_with("class."):
		p.append("%s: id deve começar com 'class.'" % id)
	if skill_ids.size() != 4:
		p.append("%s: precisa de 4 skills" % id)
	if max_life <= 0.0 or max_impeto <= 0.0 or move_speed <= 0.0:
		p.append("%s: vida/ímpeto/velocidade devem ser > 0" % id)
	if dodge_invuln >= dodge_duration:
		p.append("%s: invulnerabilidade da esquiva deve ser < duração" % id)
	if dodge_charges < 1 or dodge_recharge < Rules.MIN_COOLDOWN:
		p.append("%s: cargas/recarga de esquiva inválidas" % id)
	return p
