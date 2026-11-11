extends Node2D
## Espíritos elementais do Mago: conforme o nível da corrida sobe, mais orbes giram em volta dele (um por elemento que ele
## aprendeu, em rodízio) e disparam sozinhos no inimigo mais perto, com ricochete entre os alvos. Cada conjuração do Mago
## também faz todos soltarem uma rajada na hora. É o que faz a tela encher de magia à medida que ele cresce.
## Quantidade, cadência, alcance e ricochetes vêm de data2d/mago.csv (chaves espirito_*); aqui só regra e aparência.

const Afinidades = preload("res://scripts2d/afinidades_2d.gd")
const Alvos = preload("res://scripts2d/alvos_2d.gd")
const Orbe = preload("res://scripts2d/orbe_2d.gd")
const FxMago = preload("res://scripts2d/fx_mago_2d.gd")
const GeloFx = preload("res://scripts2d/efeitos_arqueiro_gelo_2d.gd")
const RaioFx = preload("res://scripts2d/efeitos_arqueiro_raio_2d.gd")
const FORMAS := {"": "orbe", "fogo": "chama", "gelo": "lasca", "raio": "faisca", "veneno": "bolha"}
const GRADE := 2.5

var mago: Node2D
var _sprites: Array = []     # um Sprite2D por espírito
var _elementos: Array = []   # elemento de cada espírito
var _espera: Array = []      # recarga de cada espírito (s)
var _fase := 0.0
var _n_alvo := -1

func _ready() -> void:
	z_index = 3
	mago = get_parent()

func _cfg(chave: String) -> float:
	return float(mago.stats.get(chave, 0.0))

## Quantos espíritos o nível `nv` da corrida dá.
func quantidade(nv: int) -> int:
	var passo := maxf(_cfg("espirito_nivel_passo"), 1.0)
	return mini(int(_cfg("espirito_max")), int(float(nv) / passo))

## Elementos que o Mago aprendeu (o Eco conta), na ordem da árvore; sem nenhum, o arcano.
func _elementos_aprendidos() -> Array:
	var out: Array = []
	var h = mago.habilidades
	if h != null:
		for id in h.defs:
			var ramo: String = h.defs[id]["ramo"]
			if h.nivel(id) > 0 and not out.has(ramo):
				out.append(ramo)
	if str(mago.afinidade) != "":
		var el: String = Afinidades.elemento(str(mago.afinidade))
		if el != "" and not out.has(el):
			out.append(el)
	return out if not out.is_empty() else [""]

func _refazer(n: int) -> void:
	for s in _sprites:
		s.queue_free()
	_sprites.clear()
	_elementos.clear()
	_espera.clear()
	var els := _elementos_aprendidos()
	for i in n:
		var el: String = els[i % els.size()]
		var sp := Sprite2D.new()
		sp.texture = FxMago.textura_projetil("orbe", el)
		sp.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		sp.scale = Vector2.ONE * GRADE * 1.3
		add_child(sp)
		_sprites.append(sp)
		_elementos.append(el)
		_espera.append(randf() * _cd())
	_n_alvo = n

func _cd() -> float:
	var nv := float(mago.nivel_corrida)
	return maxf(_cfg("espirito_cd_min"), _cfg("espirito_cd") - _cfg("espirito_cd_por_nivel") * nv)

func ricochetes() -> int:
	return int(_cfg("espirito_ricochete_base")) + int(float(mago.nivel_corrida) / maxf(_cfg("espirito_nivel_ricochete"), 1.0))

func _physics_process(delta: float) -> void:
	var n := quantidade(int(mago.nivel_corrida))
	var h = mago.habilidades
	var chave: int = n * 1000 + (_elementos_aprendidos().size() * 7 + (hash(h.slots) if h != null else 0)) % 997
	if n != _n_alvo or chave != int(get_meta("chave", -1)):
		set_meta("chave", chave)
		_refazer(n)
	var vel := 1.4 + 0.12 * float(n)
	_fase += delta * vel
	for i in _sprites.size():
		var a := _fase + TAU * float(i) / float(maxi(_sprites.size(), 1))
		var anel := i % 2   # dois anéis: o de fora é mais largo e gira ao contrário
		var r := _cfg("espirito_orbita") * (1.0 + 0.45 * float(anel))
		var ang := a if anel == 0 else -a * 0.8 + 1.0
		var p := Vector2(cos(ang) * r, sin(ang) * r * 0.5 - 34.0 + 5.0 * sin(_fase * 3.0 + float(i)))
		_sprites[i].position = (p / GRADE).round() * GRADE
		_sprites[i].z_index = 1 if sin(ang) > 0.0 else -1
		_espera[i] -= delta
		if _espera[i] <= 0.0:
			_espera[i] = _cd() * randf_range(0.8, 1.2)
			_disparar(i)

## Rajada: todos os espíritos prontos (metade da recarga já passou) atiram agora, quando o Mago conjura.
func rajada() -> void:
	for i in _sprites.size():
		if _espera[i] <= _cd() * 0.6:
			_espera[i] = _cd() * randf_range(0.9, 1.3)
			_disparar(i)

func _disparar(i: int) -> void:
	var origem: Vector2 = _sprites[i].global_position
	var alvo: Node2D = Alvos.mais_proximo(get_tree(), mago.global_position, _cfg("espirito_alcance"), [])
	if alvo == null:
		return
	var dano: float = mago.dano_basico() * _cfg("espirito_dano")
	var el: String = _elementos[i]
	var cena: Node = mago.get_parent()
	if el == "raio":
		_corrente(cena, origem, alvo, dano)
		return
	var dir: Vector2 = (alvo.global_position - origem).normalized()
	var o := Orbe.new()
	o.setup(origem, dir, _cfg("espirito_vel"), dano, _cfg("espirito_alcance") * 1.5)
	o.elemento = el
	o.forma = FORMAS.get(el, "orbe")
	o.tamanho = 8.0
	o.pierce = ricochetes()
	var visados: Array = []
	var rico: WeakRef = weakref(o)
	var ex := _cfg("espirito_efeito_dur")
	var dps := dano * _cfg("espirito_efeito_ratio")
	o.ao_acertar = func(corpo: Node) -> void:
		visados.append(corpo)
		if is_instance_valid(corpo):
			match el:
				"veneno":
					if corpo.has_method("aplicar_status"):
						corpo.aplicar_status("veneno", ex, dps)
				"gelo":
					GeloFx.acumular_frio(corpo, 1, {"duracao": ex, "valor": float(mago.stats["chill_per_stack"])})
				"fogo":
					if corpo.has_method("aplicar_status"):
						corpo.aplicar_status("queimadura", ex, dps)
		var b = rico.get_ref()
		if b == null:
			return
		var prox: Node2D = Alvos.mais_proximo(b.get_tree(), b.global_position, _cfg("espirito_alcance") * 0.7, visados)
		if prox != null:
			b.velocity = (prox.global_position - b.global_position).normalized() * b.velocity.length()
			b._viajado = 0.0
	cena.add_child(o)

## Raio do espírito: arco que salta de inimigo em inimigo (ricochetes + 1 alvos), com choque.
func _corrente(cena: Node, de: Vector2, alvo: Node2D, dano: float) -> void:
	var visados: Array = []
	var forca := 1.0
	for k in ricochetes() + 1:
		visados.append(alvo)
		var para: Vector2 = alvo.global_position + Vector2(0, -30)
		RaioFx.arco_entre(cena, de, para, forca)
		FxMago.impacto(cena, para, "raio", 0.7)
		var pos: Vector2 = alvo.global_position
		alvo.take_damage(dano * forca, de)
		if is_instance_valid(alvo) and alvo.has_method("aplicar_status"):
			RaioFx.aplicar_choque(alvo, _cfg("espirito_efeito_dur"), 0.15)
		de = para
		forca = 0.8
		alvo = Alvos.mais_proximo(get_tree(), pos, _cfg("espirito_alcance") * 0.5, visados)
		if alvo == null:
			break
