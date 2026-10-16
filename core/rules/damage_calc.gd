class_name DamageCalc
extends RefCounted
## Cálculo de golpe. Ordem:
## dano base × coeficiente -> modificadores -> crítico -> evasão (só ataques, teto 70%)
## -> bloqueio (teto 50%) -> escudo frontal -> armadura (só físico) -> resistência
## elemental (teto 75%) -> barreira -> vida.
## Função pura em relação ao defensor: apenas Combatant.take() altera estado.


static func resolve(attacker: Combatant, defender: Combatant, spec: HitSpec, rng: RandomNumberGenerator) -> HitResult:
	var r: HitResult = HitResult.new()
	r.damage_type = spec.damage_type
	if defender.invulnerable:
		r.invulnerable = true
		return r

	# 1) base × coeficiente, 2) modificadores (planos entram depois do coeficiente)
	r.base_damage = attacker.stats.get_base("damage") * spec.coefficient
	var dmg: float = attacker.stats.get_value_from("damage", r.base_damage, spec.tags)
	r.after_mods = dmg

	# 3) crítico (RNG de combate; sempre consome 1 número quando pode critar)
	if spec.can_crit:
		r.crit_chance = clampf(attacker.stats.get_value("crit_chance", spec.tags) + spec.crit_chance_bonus, 0.0, 100.0)
		r.crit_roll = rng.randf() * 100.0
		if r.crit_roll < r.crit_chance:
			r.crit = true
			var mult: float = attacker.stats.get_value("crit_multiplier", spec.tags)
			if mult <= 0.0:
				mult = Rules.DEFAULT_CRIT_MULTIPLIER
			dmg *= mult / 100.0
	r.after_crit = dmg

	_defend(r, defender, dmg, spec.damage_type, spec.is_attack, spec.is_hit, spec.from_front, spec.guard_break, rng)
	return r


## Dano periódico (tick de efeito): sem crítico, evasão ou bloqueio.
static func resolve_dot(defender: Combatant, amount: float, damage_type: int) -> HitResult:
	var r: HitResult = HitResult.new()
	r.damage_type = damage_type
	if defender.invulnerable:
		r.invulnerable = true
		return r
	r.base_damage = maxf(0.0, amount)
	r.after_mods = r.base_damage
	r.after_crit = r.base_damage
	_defend(r, defender, r.base_damage, damage_type, false, false, true, 0.0, null)
	return r


static func _defend(r: HitResult, defender: Combatant, dmg_in: float, damage_type: int, is_attack: bool, is_hit: bool, from_front: bool, guard_break: float, rng: RandomNumberGenerator) -> void:
	var dmg: float = dmg_in

	# 4) evasão: só ataques, teto 70%
	if is_attack:
		var ev: float = minf(defender.stats.get_value("evasion"), Rules.CAP_EVASION)
		if ev > 0.0 and rng != null and rng.randf() * 100.0 < ev:
			r.evaded = true
			r.after_block = 0.0
			r.after_shield = 0.0
			r.after_armour = 0.0
			r.after_resist = 0.0
			return

	# 5) bloqueio: teto 50%
	if is_hit:
		var bl: float = minf(defender.stats.get_value("block"), Rules.CAP_BLOCK)
		if bl > 0.0 and rng != null and rng.randf() * 100.0 < bl:
			r.blocked = true
			var red: float = clampf(defender.stats.get_value("block_reduction"), 0.0, 100.0)
			dmg *= 1.0 - red / 100.0
	r.after_block = dmg

	# 6) escudo frontal (anulado com guarda quebrada ou golpe por trás)
	if is_hit and defender.frontal_shield_reduction > 0.0 and from_front and not defender.guard.is_broken():
		r.shield_reduced = true
		dmg *= 1.0 - clampf(defender.frontal_shield_reduction, 0.0, 100.0) / 100.0
	r.after_shield = dmg

	# 7) armadura: só físico; reduz menos golpes grandes
	if damage_type == 0:
		var armour: float = defender.stats.get_value("armour")
		if armour > 0.0 and dmg > 0.0:
			dmg *= 1.0 - armour / (armour + Rules.ARMOUR_FACTOR * dmg)
	r.after_armour = dmg

	# 8) resistência elemental: teto 75%
	var rs: String = Rules.resist_stat(damage_type)
	if rs != "":
		var res: float = minf(defender.stats.get_value(rs), Rules.CAP_RESISTANCE)
		dmg *= 1.0 - res / 100.0
	r.after_resist = dmg

	# 9) barreira e vida
	r.final_damage = maxf(0.0, dmg)
	r.barrier_absorbed = minf(defender.barrier, r.final_damage)
	r.life_damage = r.final_damage - r.barrier_absorbed
	r.guard_added = maxf(0.0, guard_break)
