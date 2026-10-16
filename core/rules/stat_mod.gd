class_name StatMod
extends RefCounted
## Modificador de atributo. Só vale quando TODAS as suas tags estão presentes
## nas tags da habilidade (sem tags = vale sempre).

enum Kind { FLAT, INCREASED, MORE }

var stat: String = ""
var kind: int = Kind.FLAT
## FLAT: soma direta. INCREASED/MORE: fração (0.2 = 20%).
var value: float = 0.0
var tags: PackedStringArray = PackedStringArray()
var source: String = ""


func matches(skill_tags: PackedStringArray) -> bool:
	for t in tags:
		if not skill_tags.has(t):
			return false
	return true
