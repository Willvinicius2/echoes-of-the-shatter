#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/godot.hpp>

#include "shatter_rogue_node.h"

using namespace godot;

void inicializar_shatter(ModuleInitializationLevel nivel) {
    if (nivel != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }
    GDREGISTER_CLASS(ShatterRogue);
}

void finalizar_shatter(ModuleInitializationLevel) {}

extern "C" {
GDExtensionBool GDE_EXPORT shatter_gdextension_init(GDExtensionInterfaceGetProcAddress get_proc,
                                                    GDExtensionClassLibraryPtr lib,
                                                    GDExtensionInitialization* init) {
    GDExtensionBinding::InitObject obj(get_proc, lib, init);
    obj.register_initializer(inicializar_shatter);
    obj.register_terminator(finalizar_shatter);
    obj.set_minimum_library_initialization_level(MODULE_INITIALIZATION_LEVEL_SCENE);
    return obj.init();
}
}
