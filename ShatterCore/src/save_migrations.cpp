// ShatterCore — migrações do save (opera na árvore JSON de "data").
// Índice i da tabela = função de (i+1) -> (i+2). Hoje existe só a versão 1, logo não há passos.
// Ao publicar a v2, acrescentar UMA função v1->v2 aqui e guardar tests/data/saves/save_v1.json (já existe).
// O exemplo potion_slots do 06_dados.md é ilustrativo (pendência P10) e NÃO está registrado.
#include "shatter/save.h"

namespace shatter {

const std::vector<MigrationFn>& Migrations() {
    static const std::vector<MigrationFn> kMigrations;  // vazio: kCurrentSaveVersion == 1
    return kMigrations;
}

bool Migrate(json::Value& data, int from, int to, std::string* error) {
    if (from > to) {
        if (error) *error = "cannot migrate backwards";
        return false;
    }
    const std::vector<MigrationFn>& steps = Migrations();
    for (int v = from; v < to; ++v) {
        const std::size_t idx = static_cast<std::size_t>(v - 1);
        if (v < 1 || idx >= steps.size() || steps[idx] == nullptr) {
            if (error) *error = "missing migration step " + std::to_string(v) + " -> " + std::to_string(v + 1);
            return false;
        }
        if (!steps[idx](data, error)) return false;
    }
    return true;
}

}  // namespace shatter
