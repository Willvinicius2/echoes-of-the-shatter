extends Node
## Cena principal: roda o mundo (Run2D) num SubViewport de baixa resolução e sobe com escala inteira e filtro
## nearest, para o visual de pixel art. A HUD, os menus e a barra do chefe ficam na janela, nítidos.
## O container estica o SubViewport pela janela: tamanho do mundo = janela / stretch_shrink, com
## stretch_shrink inteiro (janela 1440 de altura e pixel_altura 360 = 4x). O mouse chega ao mundo já convertido.
## pixel_altura em run_settings.csv (0 desliga e o mundo roda direto na janela).
const RunScene = preload("res://scenes2d/Run2D.tscn")
const Csv = preload("res://scripts2d/csv2d.gd")

var run
var _cont: SubViewportContainer
var _altura := 0

func _ready() -> void:
	_altura = int(Csv.kv("res://data2d/run_settings.csv").get("pixel_altura", 0.0))
	run = RunScene.instantiate()
	if _altura <= 0:
		add_child(run)
		return
	var fundo := CanvasLayer.new()
	fundo.layer = -10
	add_child(fundo)
	_cont = SubViewportContainer.new()
	_cont.set_anchors_preset(Control.PRESET_FULL_RECT)
	_cont.stretch = true
	_cont.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	fundo.add_child(_cont)
	var sv := SubViewport.new()
	sv.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
	sv.handle_input_locally = true
	sv.disable_3d = true                      # mundo 100% 2D: sem o caminho 3D do Forward+ no SubViewport
	sv.snap_2d_transforms_to_pixel = true     # posições na grade de pixels (sem tremida de sub-pixel)
	sv.snap_2d_vertices_to_pixel = true
	sv.msaa_2d = Viewport.MSAA_DISABLED
	sv.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	_cont.add_child(sv)
	run.ui_raiz = self   # a interface sai do SubViewport e fica na janela
	sv.add_child(run)
	sv.size_changed.connect(_ao_mudar_tamanho)
	get_window().size_changed.connect(_ajustar_escala)
	_ajustar_escala()

func _ajustar_escala() -> void:
	var alt := get_viewport().get_visible_rect().size.y
	_cont.stretch_shrink = maxi(1, roundi(alt / float(_altura)))

func _ao_mudar_tamanho() -> void:
	if is_instance_valid(run) and run.get("room") != null:
		run._ajustar_camera.call_deferred(false)
