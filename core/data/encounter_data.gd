class_name EncounterData
extends Resource
## Estrutura de um encontro (ondas + chefe).

@export var id: String = ""
## Quantidade de inimigos por onda.
@export var waves: PackedInt32Array = PackedInt32Array()
@export var wave_enemy_id: String = ""
@export var boss_id: String = ""
@export var wave_start_delay: float = 1.0
@export var between_waves_delay: float = 1.5
## Fração da vida restaurada ao limpar uma onda.
@export var heal_on_wave_clear: float = 0.4
@export var respawn_delay: float = 1.5


func validate() -> PackedStringArray:
	var p: PackedStringArray = PackedStringArray()
	if not id.begins_with("encounter."):
		p.append("%s: id deve começar com 'encounter.'" % id)
	if waves.is_empty():
		p.append("%s: sem ondas" % id)
	for n in waves:
		if n <= 0:
			p.append("%s: onda com tamanho <= 0" % id)
	if heal_on_wave_clear < 0.0 or heal_on_wave_clear > 1.0:
		p.append("%s: heal_on_wave_clear fora de [0,1]" % id)
	return p
