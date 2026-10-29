extends RefCounted
## Leitura de CSV e localização do cliente 2D. Nenhum número de balanceamento mora no código.

static var _loc := {}

## Linhas do CSV como Array de Dictionary (cabeçalho -> valor).
static func rows(path: String) -> Array:
	var out := []
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("CSV ausente: " + path)
		return out
	var header := PackedStringArray()
	while not f.eof_reached():
		var cells := f.get_csv_line()
		if cells.size() == 0 or (cells.size() == 1 and cells[0].strip_edges() == ""):
			continue
		if header.is_empty():
			header = cells
			header[0] = header[0].trim_prefix("﻿")
			continue
		var d := {}
		for i in header.size():
			d[header[i]] = cells[i] if i < cells.size() else ""
		out.append(d)
	return out

## CSV chave,valor -> Dictionary chave -> float.
static func kv(path: String) -> Dictionary:
	var d := {}
	for r in rows(path):
		d[r["chave"]] = float(r["valor"])
	return d

## Linha de enemies.csv pelo id, com números convertidos.
static func enemy(id: String) -> Dictionary:
	for r in rows("res://data2d/enemies.csv"):
		if r["id"] == id:
			var d := {"id": id, "kind": r["kind"]}
			for k in r:
				if k != "id" and k != "kind":
					d[k] = float(r[k])
			return d
	push_error("Inimigo ausente em enemies.csv: " + id)
	return {}

## Texto visível por chave de localização.
static func t(key: String) -> String:
	if _loc.is_empty():
		for r in rows("res://data2d/loc_2d.csv"):
			_loc[r["chave"]] = r["pt"]
	return _loc.get(key, key)
