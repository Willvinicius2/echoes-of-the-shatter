class_name EnemyData
extends Resource
## Dados de um inimigo (comum ou chefe).

@export var id: String = ""
@export var display_name: String = ""
@export var is_boss: bool = false

@export var max_life: float = 50.0
@export var damage: float = 10.0
@export var armour: float = 0.0
@export var evasion: float = 0.0
@export var block: float = 0.0
@export var block_reduction: float = 50.0
@export var res_fire: float = 0.0
@export var res_cold: float = 0.0
@export var res_lightning: float = 0.0

@export var move_speed: float = 70.0
@export var aggro_range: float = 220.0
@export var radius: float = 11.0
@export var patrol_radius: float = 40.0
@export var patrol_speed_mult: float = 0.35

@export var attack_range: float = 54.0
@export var attack_arc: float = 100.0
@export var attack_start_ratio: float = 0.8
@export var attack_coefficient: float = 1.0
@export var attack_windup: float = 0.55
@export var attack_active: float = 0.12
@export var attack_recover: float = 0.7
@export var attack_cooldown: float = 0.8
@export var attack_knockback: float = 120.0
@export var attack_hitstop_ms: float = 0.0
@export var attack_shake: float = 0.0
@export var attack_heavy: bool = false

@export var knockback_resist: float = 0.0
@export var kb_decay: float = 600.0
@export var death_time: float = 0.4

@export var guard_max: float = 40.0
@export var guard_stun: float = 1.6
@export var guard_decay: float = 12.0

@export var frontal_shield_reduction: float = 0.0
@export var shield_arc_degrees: float = 0.0

@export var phase2_threshold: float = 0.0
@export var phase2_speed_mult: float = 1.0
@export var phase_pause: float = 1.2
@export var summon_enemy_id: String = ""
@export var summon_count: int = 0

@export var body_color: Color = Color(0.6, 0.5, 0.4, 1.0)
@export var accent_color: Color = Color(0.8, 0.6, 0.25, 1.0)


func validate() -> PackedStringArray:
	var p: PackedStringArray = PackedStringArray()
	if not id.begins_with("enemy."):
		p.append("%s: id deve começar com 'enemy.'" % id)
	if max_life <= 0.0 or move_speed <= 0.0 or radius <= 0.0:
		p.append("%s: vida/velocidade/raio devem ser > 0" % id)
	if attack_range <= 0.0 or attack_arc <= 0.0 or attack_arc > 180.0:
		p.append("%s: alcance/arco de ataque inválidos" % id)
	if attack_windup <= 0.0:
		p.append("%s: telegraph deve ser > 0" % id)
	if knockback_resist < 0.0 or knockback_resist > 1.0:
		p.append("%s: knockback_resist fora de [0,1]" % id)
	if is_boss and (attack_windup < 0.7 or attack_windup > 1.2):
		p.append("%s: telegraph do chefe deve ficar entre 0,7 e 1,2 s" % id)
	if phase2_threshold < 0.0 or phase2_threshold >= 1.0:
		p.append("%s: phase2_threshold fora de [0,1)" % id)
	if summon_count > 0 and summon_enemy_id.is_empty():
		p.append("%s: summon_count sem summon_enemy_id" % id)
	return p
