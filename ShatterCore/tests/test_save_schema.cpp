// RF-51: o save gerado pelo core passa no esquema do Data Engineer (schemas/save_v1.schema.json) e contém
// todos os campos listados. Aqui roda um validador mínimo (o subconjunto de JSON Schema que o esquema usa);
// o ctest "save_rf51_python_validator" roda também o tools/dados/validate_data.py sobre um save gravado pelo core.
#include <regex>

#include "test_util.h"

using namespace shatter;

namespace {

using json::Type;
using json::Value;

class SchemaChecker {
public:
    explicit SchemaChecker(const Value& root) : root_(root) {}

    void Check(const Value& schema, const Value& v, const std::string& path) {
        if (const Value* ref = schema.Find("$ref")) {
            const std::string& r = ref->AsString();
            const std::string prefix = "#/$defs/";
            if (r.rfind(prefix, 0) != 0) { Err(path, "ref nao suportado " + r); return; }
            const Value* def = root_["$defs"].Find(r.substr(prefix.size()));
            if (def == nullptr) { Err(path, "ref inexistente " + r); return; }
            Check(*def, v, path);
            return;
        }
        if (const Value* one = schema.Find("oneOf")) {
            int ok = 0;
            for (const Value& alt : one->Items()) {
                SchemaChecker sub(root_);
                sub.Check(alt, v, path);
                ok += sub.errors_.empty() ? 1 : 0;
            }
            if (ok != 1) Err(path, "oneOf com " + std::to_string(ok) + " alternativas validas");
            return;
        }
        if (const Value* t = schema.Find("type")) {
            if (!TypeOk(t->AsString(), v)) { Err(path, "tipo esperado " + t->AsString()); return; }
        }
        if (const Value* c = schema.Find("const")) {
            if (json::Serialize(*c, false) != json::Serialize(v, false)) Err(path, "const diferente");
        }
        if (const Value* e = schema.Find("enum")) {
            bool found = false;
            for (const Value& opt : e->Items()) found = found || json::Serialize(opt, false) == json::Serialize(v, false);
            if (!found) Err(path, "fora do enum: " + json::Serialize(v, false));
        }
        if (const Value* p = schema.Find("pattern")) {
            if (!std::regex_search(v.AsString(), std::regex(p->AsString()))) Err(path, "pattern: " + v.AsString());
        }
        if (const Value* m = schema.Find("minLength")) {
            if (static_cast<std::int64_t>(v.AsString().size()) < m->AsInt()) Err(path, "minLength");
        }
        if (const Value* m = schema.Find("minimum")) {
            if (v.AsDouble() < m->AsDouble()) Err(path, "minimum");
        }
        if (const Value* m = schema.Find("maximum")) {
            if (v.AsDouble() > m->AsDouble()) Err(path, "maximum");
        }
        if (const Value* m = schema.Find("exclusiveMinimum")) {
            if (v.AsDouble() <= m->AsDouble()) Err(path, "exclusiveMinimum");
        }
        if (v.type() == Type::Array) {
            if (const Value* m = schema.Find("minItems"))
                if (static_cast<std::int64_t>(v.Size()) < m->AsInt()) Err(path, "minItems");
            if (const Value* m = schema.Find("maxItems"))
                if (static_cast<std::int64_t>(v.Size()) > m->AsInt()) Err(path, "maxItems");
            if (const Value* items = schema.Find("items"))
                for (std::size_t i = 0; i < v.Size(); ++i) Check(*items, v.At(i), path + "[" + std::to_string(i) + "]");
        }
        if (v.type() == Type::Object) {
            for (const Value& req : schema["required"].Items())
                if (!v.Has(req.AsString())) Err(path, "campo obrigatorio ausente: " + req.AsString());
            const Value& props = schema["properties"];
            const Value* addl = schema.Find("additionalProperties");
            const bool closed = addl != nullptr && addl->type() == Type::Bool && !addl->AsBool();
            for (const auto& m : v.Members()) {
                const Value* ps = props.Find(m.first);
                if (ps != nullptr) Check(*ps, m.second, path + "." + m.first);
                else if (closed) Err(path, "campo extra: " + m.first);
            }
        }
    }

    const std::vector<std::string>& Errors() const { return errors_; }

private:
    static bool TypeOk(const std::string& t, const Value& v) {
        if (t == "object") return v.type() == Type::Object;
        if (t == "array") return v.type() == Type::Array;
        if (t == "string") return v.type() == Type::String;
        if (t == "boolean") return v.type() == Type::Bool;
        if (t == "null") return v.IsNull();
        if (t == "number") return v.IsNumber();
        if (t == "integer") return v.type() == Type::Int;
        return false;
    }
    void Err(const std::string& path, const std::string& msg) { errors_.push_back(path + ": " + msg); }

    const Value& root_;
    std::vector<std::string> errors_;
};

// Save completo com o conteúdo do fixture rico: personagem equipado, baú, moedas, expedição em andamento.
SaveData FullSave() {
    const ContentDB& db = tu::RichDb();
    SaveData s;
    s.contentVersion = db.ContentVersion();
    CharacterState c = tu::MakeWarrior(db, 3);
    c.xp = 42.5;
    c.playTimeSeconds = 1234.5;
    ItemInstance helm;
    helm.uid = 2;
    helm.baseId = "item_base.bone_helm";
    helm.rarity = Rarity::Magic;
    helm.itemLevel = 4;
    helm.affixes = {{"affix.life_flat", 12.0}};
    c.equipment[static_cast<std::size_t>(ItemSlot::Head)] = helm;
    s.characters.push_back(c);
    ItemInstance vest;
    vest.uid = 3;
    vest.baseId = "item_base.leather_vest";
    s.stash.push_back(vest);
    s.currencies = {{"currency.gold", 250}};
    s.markerCharges = 12;
    s.lastRestDay = 19675;
    s.lastSeenUtc = 1'700'000'000;
    s.nextItemUid = 4;
    ExpeditionStartParams p;
    p.mapId = "map.act1.crypt";
    p.rules = tu::DefaultRules();
    p.durationHours = 4;
    p.seed = 18446744073709551557ull;
    p.startUtc = 1'700'000'000;
    if (StartExpedition(db, s, p) != StartCheck::Ok) FAIL("StartExpedition recusou o save de exemplo");
    return s;
}

json::Value Schema() {
    json::Value schema;
    const std::string path = tu::ContentDir() + "/schemas/save_v2.schema.json";
    if (!json::Parse(tu::ReadFile(path), schema)) FAIL("esquema ilegivel: " + path);
    return schema;
}

}  // namespace

TEST(save_rf51_generated_save_matches_schema_and_has_every_field) {
    const json::Value schema = Schema();
    ASSERT_TRUE(schema.type() == Type::Object);
    json::Value file;
    ASSERT_TRUE(json::Parse(SerializeJson(FullSave(), true), file));
    SchemaChecker ok(schema);
    ok.Check(schema, file, "$");
    for (const std::string& e : ok.Errors()) FAIL(e);
    // Coleta também gera um save válido (status collected com hash diferente de "0").
    SaveData s = FullSave();
    ExpeditionRequest req = s.expeditions[0].request;
    req.effectiveSeconds = 600.0;
    ASSERT_TRUE(CollectExpedition(tu::RichDb(), s, 0, SimulateExpedition(tu::RichDb(), req)));
    ASSERT_TRUE(json::Parse(SerializeJson(s, true), file));
    SchemaChecker collected(schema);
    collected.Check(schema, file, "$");
    for (const std::string& e : collected.Errors()) FAIL(e);
    // O verificador acusa campo faltando e campo extra (prova de que não aceita tudo).
    json::Value data = SaveToJson(FullSave());
    json::Value broken = json::Value::MakeObject();
    for (const auto& m : data.Members())
        if (m.first != "marker_charges") broken.Set(m.first, m.second);
    broken.Set("surprise", json::Value(1));
    json::Value env = file;
    env.Set("data", broken);
    SchemaChecker bad(schema);
    bad.Check(schema, env, "$");
    EXPECT_EQ(bad.Errors().size(), static_cast<std::size_t>(2));
}

// Grava um save real do core para o validador Python (ctest save_rf51_python_validator).
// Sem SHATTER_SAVE_SAMPLE_OUT, só confere que a gravação funciona numa pasta temporária.
TEST(save_rf51_sample_for_python_validator) {
    std::string base = tu::GetEnv("SHATTER_SAVE_SAMPLE_OUT");
    if (base.empty()) base = tu::TmpDir("rf51") + "/slot_1";
    const std::unique_ptr<IFileIO> io = MakeStdFileIO();
    std::string err;
    ASSERT_TRUE(WriteSaveFile(*io, base, FullSave(), &err));
    SaveData back;
    EXPECT_ENUM_EQ(ReadSaveFile(*io, base, back).status, LoadStatus::Ok);
}
