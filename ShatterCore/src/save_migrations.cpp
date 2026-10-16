// ShatterCore — migrações do save (opera na árvore JSON de "data").
// Índice i da tabela = função de (i+1) -> (i+2).
//   v1 -> v2: potions (int) vira potion_slots [{potion_id, charges, recharge_remaining}] (tudo no slot da "Vida");
//             boss_progress = []; equipment.legs = null (calça, C-10); potion_heal_fraction sai do pedido de expedição.
//             Nada é apagado: as cargas antigas entram inteiras no 1º slot (o jogo corta no máximo ao normalizar).
#include "shatter/save.h"

namespace shatter {

namespace {

using json::Value;

Value MigrateCharacter1To2(const Value& ch) {
    Value out = Value::MakeObject();
    for (const Value::Member& m : ch.Members()) {
        if (m.first == "potions") {
            Value slots = Value::MakeArray();
            Value s = Value::MakeObject();
            s.Set("potion_id", Value("potion.life"));
            s.Set("charges", Value(m.second.AsInt(0)));
            s.Set("recharge_remaining", Value(0.0));
            slots.Push(std::move(s));
            out.Set("potion_slots", std::move(slots));
            out.Set("boss_progress", Value::MakeArray());
        } else if (m.first == "equipment") {
            Value eq = Value::MakeObject();
            for (const Value::Member& e : m.second.Members()) eq.Set(e.first, e.second);
            if (!eq.Has("legs")) eq.Set("legs", Value());
            out.Set("equipment", std::move(eq));
        } else {
            out.Set(m.first, m.second);
        }
    }
    return out;
}

bool Migrate1To2(Value& data, std::string* error) {
    if (data.type() != json::Type::Object) {
        if (error) *error = "save data is not an object";
        return false;
    }
    Value out = Value::MakeObject();
    for (const Value::Member& m : data.Members()) {
        if (m.first == "characters") {
            Value chars = Value::MakeArray();
            for (const Value& c : m.second.Items()) chars.Push(MigrateCharacter1To2(c));
            out.Set("characters", std::move(chars));
        } else if (m.first == "expeditions") {
            Value exps = Value::MakeArray();
            for (const Value& e : m.second.Items()) {
                Value eo = Value::MakeObject();
                for (const Value::Member& em : e.Members()) {
                    if (em.first != "request") {
                        eo.Set(em.first, em.second);
                        continue;
                    }
                    Value req = Value::MakeObject();
                    for (const Value::Member& rm : em.second.Members()) {
                        if (rm.first == "potion_heal_fraction") continue;
                        if (rm.first == "snapshot") {
                            Value snap = Value::MakeObject();
                            for (const Value::Member& sm : rm.second.Members()) {
                                if (sm.first == "character") snap.Set("character", MigrateCharacter1To2(sm.second));
                                else snap.Set(sm.first, sm.second);
                            }
                            req.Set("snapshot", std::move(snap));
                        } else {
                            req.Set(rm.first, rm.second);
                        }
                    }
                    eo.Set("request", std::move(req));
                }
                exps.Push(std::move(eo));
            }
            out.Set("expeditions", std::move(exps));
        } else {
            out.Set(m.first, m.second);
        }
    }
    data = std::move(out);
    return true;
}

}  // namespace

const std::vector<MigrationFn>& Migrations() {
    static const std::vector<MigrationFn> kMigrations = {&Migrate1To2};
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
