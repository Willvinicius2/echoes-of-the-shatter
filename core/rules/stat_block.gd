class_name StatBlock
extends RefCounted
## Atributo = (base + planos) × (1 + soma dos aumentados) × produto dos "mais".
## Resultado em cache, invalidado quando base ou modificadores mudam.

var recompute_count: int = 0
var _base: Dictionary = {}
var _mods: Array[StatMod] = []
var _cache: Dictionary = {}


func set_base(stat: String, value: float) -> void:
	_base[stat] = value
	_cache.clear()


func get_base(stat: String) -> float:
	return float(_base.get(stat, 0.0))


func add_mod(m: StatMod) -> StatMod:
	_mods.append(m)
	_cache.clear()
	return m


func add(stat: String, kind: int, value: float, tags: PackedStringArray = PackedStringArray(), source: String = "") -> StatMod:
	var m: StatMod = StatMod.new()
	m.stat = stat
	m.kind = kind
	m.value = value
	m.tags = tags
	m.source = source
	return add_mod(m)


func remove_source(source: String) -> int:
	var removed: int = 0
	for i in range(_mods.size() - 1, -1, -1):
		if _mods[i].source == source:
			_mods.remove_at(i)
			removed += 1
	if removed > 0:
		_cache.clear()
	return removed


## Valor final (nunca negativo) do atributo para as tags dadas.
func get_value(stat: String, tags: PackedStringArray = PackedStringArray()) -> float:
	var key: String = stat + "|" + _tag_key(tags)
	if _cache.has(key):
		return float(_cache[key])
	recompute_count += 1
	var v: float = _compute(stat, get_base(stat), tags)
	_cache[key] = v
	return v


## Igual a get_value, mas com uma base explícita (sem cache).
## Usado para aplicar os modificadores sobre "dano base × coeficiente".
func get_value_from(stat: String, base: float, tags: PackedStringArray = PackedStringArray()) -> float:
	return _compute(stat, base, tags)


func _compute(stat: String, base: float, tags: PackedStringArray) -> float:
	var flat: float = 0.0
	var inc: float = 0.0
	var more: float = 1.0
	for m in _mods:
		if m.stat != stat or not m.matches(tags):
			continue
		match m.kind:
			StatMod.Kind.FLAT:
				flat += m.value
			StatMod.Kind.INCREASED:
				inc += m.value
			StatMod.Kind.MORE:
				more *= maxf(0.0, 1.0 + m.value)
	var result: float = (base + flat) * maxf(0.0, 1.0 + inc) * more
	return maxf(0.0, result)


static func _tag_key(tags: PackedStringArray) -> String:
	var arr: Array = Array(tags)
	arr.sort()
	return ",".join(PackedStringArray(arr))
