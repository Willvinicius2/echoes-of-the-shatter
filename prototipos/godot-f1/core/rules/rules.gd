class_name Rules
extends RefCounted
## Constantes das REGRAS do jogo (tetos e mínimos definidos pelo design).
## Não são números de balanceamento: valores de balanceamento ficam em res://data/.

const CAP_EVASION: float = 70.0
const CAP_BLOCK: float = 50.0
const CAP_RESISTANCE: float = 75.0
const ARMOUR_FACTOR: float = 5.0
const MIN_COOLDOWN: float = 0.1
const MIN_TRIGGER_ICD: float = 0.25
const DEFAULT_CRIT_MULTIPLIER: float = 150.0

## Índice = SkillData.DamageType.
const DAMAGE_TYPE_TAGS: PackedStringArray = ["físico", "fogo", "frio", "raio"]
const RESIST_STATS: PackedStringArray = ["", "res_fire", "res_cold", "res_lightning"]


static func clamp_cooldown(value: float) -> float:
	return maxf(value, MIN_COOLDOWN)


static func damage_type_tag(damage_type: int) -> String:
	return DAMAGE_TYPE_TAGS[clampi(damage_type, 0, DAMAGE_TYPE_TAGS.size() - 1)]


static func resist_stat(damage_type: int) -> String:
	return RESIST_STATS[clampi(damage_type, 0, RESIST_STATS.size() - 1)]
