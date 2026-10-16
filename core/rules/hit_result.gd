class_name HitResult
extends RefCounted
## Resultado detalhado de um golpe. Todos os valores numéricos são >= 0.

var damage_type: int = 0
var invulnerable: bool = false
var evaded: bool = false
var blocked: bool = false
var crit: bool = false
var shield_reduced: bool = false
var guard_broken: bool = false
var killed: bool = false

var crit_chance: float = 0.0
var crit_roll: float = 0.0

# Etapas do cálculo, na ordem em que acontecem.
var base_damage: float = 0.0      # dano base × coeficiente
var after_mods: float = 0.0       # após modificadores
var after_crit: float = 0.0       # após crítico
var after_block: float = 0.0      # após bloqueio
var after_shield: float = 0.0     # após escudo frontal
var after_armour: float = 0.0     # após armadura (só físico)
var after_resist: float = 0.0     # após resistência elemental

var final_damage: float = 0.0     # dano total aplicado (barreira + vida)
var barrier_absorbed: float = 0.0
var life_damage: float = 0.0
var guard_added: float = 0.0
