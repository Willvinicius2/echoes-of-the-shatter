class_name DataDB
extends RefCounted
## Carrega e indexa todos os .tres de res://data/ por ID estável.

const DIRS: PackedStringArray = [
	"res://data/heroes",
	"res://data/skills",
	"res://data/enemies",
	"res://data/effects",
	"res://data/encounters",
]

static var _index: Dictionary = {}
static var _loaded: bool = false
static var duplicate_ids: PackedStringArray = PackedStringArray()
static var load_errors: PackedStringArray = PackedStringArray()


static func reload() -> void:
	_index.clear()
	duplicate_ids = PackedStringArray()
	load_errors = PackedStringArray()
	for dir in DIRS:
		for f in DirAccess.get_files_at(dir):
			var name: String = f.trim_suffix(".remap")
			if not name.ends_with(".tres"):
				continue
			var path: String = dir + "/" + name
			var res: Resource = load(path)
			if res == null:
				load_errors.append(path)
				continue
			var rid: String = str(res.get("id"))
			if _index.has(rid):
				duplicate_ids.append(rid)
			_index[rid] = res
	_loaded = true


static func all_resources() -> Array[Resource]:
	_ensure()
	var out: Array[Resource] = []
	for k in _index.keys():
		out.append(_index[k])
	return out


static func get_res(id: String) -> Resource:
	_ensure()
	return _index.get(id, null)


static func get_hero(id: String) -> ClassData:
	return get_res(id) as ClassData


static func get_skill(id: String) -> SkillData:
	return get_res(id) as SkillData


static func get_enemy(id: String) -> EnemyData:
	return get_res(id) as EnemyData


static func get_effect(id: String) -> EffectData:
	return get_res(id) as EffectData


static func get_encounter(id: String) -> EncounterData:
	return get_res(id) as EncounterData


static func _ensure() -> void:
	if not _loaded:
		reload()
