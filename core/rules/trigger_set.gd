class_name TriggerSet
extends RefCounted
## Gatilhos automáticos com recarga interna (mínimo 0,25 s).

var _triggers: Array[Dictionary] = []


func add(id: String, event: String, callback: Callable, icd: float = 0.25) -> void:
	_triggers.append({
		"id": id,
		"event": event,
		"callback": callback,
		"icd": maxf(icd, Rules.MIN_TRIGGER_ICD),
		"remaining": 0.0,
	})


func remove(id: String) -> void:
	for i in range(_triggers.size() - 1, -1, -1):
		if _triggers[i]["id"] == id:
			_triggers.remove_at(i)


## Dispara os gatilhos do evento que estiverem fora de recarga. Retorna quantos dispararam.
func fire(event: String, ctx: Dictionary = {}) -> int:
	var count: int = 0
	for t in _triggers:
		if t["event"] != event or float(t["remaining"]) > 0.0:
			continue
		t["remaining"] = t["icd"]
		var cb: Callable = t["callback"]
		if cb.is_valid():
			cb.call(ctx)
		count += 1
	return count


func update(delta: float) -> void:
	for t in _triggers:
		t["remaining"] = maxf(0.0, float(t["remaining"]) - delta)
