class_name HitSpec
extends RefCounted
## Descrição de um golpe a ser resolvido pelo motor (DamageCalc).

var skill_id: String = ""
var tags: PackedStringArray = PackedStringArray()
var damage_type: int = 0
var coefficient: float = 1.0
var is_attack: bool = true
## false para dano periódico (não sofre evasão nem bloqueio).
var is_hit: bool = true
var can_crit: bool = true
var crit_chance_bonus: float = 0.0
var guard_break: float = 0.0
var from_front: bool = true

# Carga de apresentação: não afeta o cálculo de dano.
var knockback: float = 0.0
var hitstop_s: float = 0.0
var shake: float = 0.0
var heavy: bool = false
var impeto_gain: float = 0.0


static func from_skill(s: SkillData) -> HitSpec:
	var h: HitSpec = HitSpec.new()
	h.skill_id = s.id
	h.tags = s.tags.duplicate()
	var type_tag: String = Rules.damage_type_tag(s.damage_type)
	if not h.tags.has(type_tag):
		h.tags.append(type_tag)
	h.damage_type = s.damage_type
	h.coefficient = s.coefficient
	h.is_attack = s.is_attack
	h.guard_break = s.guard_break
	h.knockback = s.knockback
	h.hitstop_s = s.hitstop_ms / 1000.0
	h.shake = s.shake
	h.heavy = s.heavy
	h.impeto_gain = s.impeto_gain
	return h


static func from_enemy(d: EnemyData) -> HitSpec:
	var h: HitSpec = HitSpec.new()
	h.skill_id = d.id + ".attack"
	h.tags = PackedStringArray(["ataque", "corpo_a_corpo", "físico"])
	h.damage_type = 0
	h.coefficient = d.attack_coefficient
	h.is_attack = true
	h.knockback = d.attack_knockback
	h.hitstop_s = d.attack_hitstop_ms / 1000.0
	h.shake = d.attack_shake
	h.heavy = d.attack_heavy
	return h
