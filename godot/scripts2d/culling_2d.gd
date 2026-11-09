extends RefCounted
## Culling por blocos para a decoração estática da sala (decalques, tufos, manchas do terreno): são dezenas de
## milhares de nós 2D e o renderizador percorria todos a cada quadro, mesmo os fora da tela (~6 ms de CPU).
## `agrupar` põe os filhos pequenos de um contêiner em blocos por posição, e `atualizar` liga só os blocos que
## encostam na vista. Um bloco invisível é descartado inteiro, sem olhar os filhos. O visual não muda.

const CELULA := 512.0
const TAM_MAX := 1000.0     # filho maior que isto fica solto (sempre desenhado)
const MARGEM := 160.0       # folga para balanço de vento, tremor e a vista andar entre duas atualizações

## Retângulo do nó no espaço do contêiner (aproximado: usa o retângulo envolvente das transformações).
## Rect2() de tamanho zero e `ok = false` quando o nó não tem tamanho conhecido.
static func _rect(n: Node, ok: Array) -> Rect2:
	var r := Rect2()
	var tem := false
	if n is Polygon2D:
		var p: PackedVector2Array = n.polygon
		if p.size() > 0:
			var mn := p[0]
			var mx := p[0]
			for v in p:
				mn = mn.min(v)
				mx = mx.max(v)
			r = Rect2(mn + n.offset, mx - mn)
			tem = true
	elif n is Sprite2D:
		if n.texture != null:
			r = n.get_rect()   # considera região, quadros, centro e deslocamento
			tem = true
	elif n is Line2D:
		var p: PackedVector2Array = n.points
		if p.size() > 0:
			var mn := p[0]
			var mx := p[0]
			for v in p:
				mn = mn.min(v)
				mx = mx.max(v)
			var w: float = n.width
			r = Rect2(mn - Vector2(w, w), mx - mn + Vector2(w, w) * 2.0)
			tem = true
	elif n is MeshInstance2D:
		var m: Mesh = n.mesh
		if m != null:
			var a := m.get_aabb()
			r = Rect2(Vector2(a.position.x, a.position.y), Vector2(a.size.x, a.size.y))
			tem = true
	elif n is Node2D and n.get_class() == "Node2D":
		for c in n.get_children():
			if c is CanvasItem:
				var ok2 := [true]
				var cr := _rect(c, ok2)
				if not ok2[0]:
					ok[0] = false
					return Rect2()
				if cr.size != Vector2.ZERO or cr.position != Vector2.ZERO:
					r = cr if not tem else r.merge(cr)
					tem = true
	else:
		ok[0] = false   # partículas, corpos, luzes etc.: não sabemos o tamanho
		return Rect2()
	if not tem:
		return Rect2()
	if n is Node2D:
		r = (n as Node2D).transform * r
	return r

## Reparenta os filhos pequenos de `cont` em blocos. Devolve a lista de {no, rect} dos blocos criados.
static func agrupar(cont: Node2D) -> Array:
	var blocos := {}
	var lista: Array = []
	var mover: Array = []
	for c in cont.get_children():
		if not (c is Node2D) or c is CollisionObject2D or c.is_queued_for_deletion():
			continue
		if (c as Node2D).y_sort_enabled or (c as Node2D).z_index != 0 or c.top_level:
			continue
		var ok := [true]
		var r := _rect(c, ok)
		if not ok[0] or r.size == Vector2.ZERO or maxf(r.size.x, r.size.y) > TAM_MAX:
			continue
		mover.append([c, r])
	for par in mover:
		var c: Node2D = par[0]
		var r: Rect2 = par[1]
		var centro := r.get_center()
		var k := Vector2i(floori(centro.x / CELULA), floori(centro.y / CELULA))
		var b: Dictionary
		if blocos.has(k):
			b = blocos[k]
			b["rect"] = (b["rect"] as Rect2).merge(r)
		else:
			var no := Node2D.new()
			no.name = "Bloco_%d_%d" % [k.x, k.y]
			cont.add_child(no)
			cont.move_child(no, c.get_index())   # o bloco entra onde estava o primeiro filho dele
			b = {"no": no, "rect": r}
			blocos[k] = b
			lista.append(b)
		c.reparent(b["no"], false)   # false: mantém a posição local (o contêiner e o bloco ficam na origem)
	return lista

## Liga os blocos que encostam em `vista` (coordenadas do contêiner) e desliga o resto.
static func atualizar(blocos: Array, vista: Rect2) -> void:
	var v := vista.grow(MARGEM)
	for b in blocos:
		var no: Node2D = b["no"]
		var ve: bool = v.intersects(b["rect"])
		if no.visible != ve:
			no.visible = ve
