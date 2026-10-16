class_name RngStreams
extends RefCounted
## Fluxos de RNG independentes. Cada fluxo tem seed = hash(seed, fluxo, índice):
## mesma seed => mesma sequência; consumir um fluxo não altera os outros.

const COMBAT: String = "combate"
const LOOT: String = "saque"
const EVENTS: String = "eventos"

var base_seed: int = 0
var _streams: Dictionary = {}


func _init(p_seed: int = 0) -> void:
	base_seed = p_seed


static func derive_seed(p_seed: int, flow: String, index: int = 0) -> int:
	return ("%d|%s|%d" % [p_seed, flow, index]).hash()


func stream(flow: String, index: int = 0) -> RandomNumberGenerator:
	var key: String = "%s#%d" % [flow, index]
	if not _streams.has(key):
		var r: RandomNumberGenerator = RandomNumberGenerator.new()
		r.seed = derive_seed(base_seed, flow, index)
		_streams[key] = r
	return _streams[key]
