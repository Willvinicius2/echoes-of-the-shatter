// Utilidades compartilhadas pelos testes do ShatterCore (só testes; nada daqui entra no motor).
#pragma once

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <map>
#include <string>
#include <utility>
#include <vector>

#include "shatter/shatter.h"
#include "test_framework.h"

namespace tu {

inline std::string DataDir() { return SHATTER_TEST_DATA_DIR; }
inline std::string ContentDir() { return SHATTER_CONTENT_DIR; }

// Variável de ambiente ("" se ausente). _dupenv_s no MSVC (getenv gera aviso C4996 com /W4 /WX).
inline std::string GetEnv(const char* name) {
#ifdef _MSC_VER
    char* v = nullptr;
    std::size_t len = 0;
    std::string out;
    if (_dupenv_s(&v, &len, name) == 0 && v != nullptr) out = v;
    std::free(v);
    return out;
#else
    const char* v = std::getenv(name);
    return v ? std::string(v) : std::string();
#endif
}

// SHATTER_NIGHTLY=1: escala cheia dos critérios estatísticos (ex.: 10 mil expedições de 12 h).
inline bool Nightly() { return !GetEnv("SHATTER_NIGHTLY").empty(); }

inline std::string ReadFile(const std::string& path) {
    std::ifstream in(std::filesystem::u8path(path), std::ios::binary);
    return std::string(std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>());
}

// Pasta temporária na pasta de build (<build>/test_tmp/<nome>): tudo fica no mesmo disco do projeto e
// builds diferentes (Release, Debug, sanitizers) não disputam os mesmos arquivos.
inline std::string TmpDir(const std::string& name) {
    namespace fs = std::filesystem;
#ifdef SHATTER_TEST_TMP_DIR
    const fs::path p = fs::u8path(SHATTER_TEST_TMP_DIR) / name;
#else
    const fs::path p = fs::path(DataDir()) / ".." / ".." / ".." / "build" / "test_tmp" / name;
#endif
    std::error_code ec;
    fs::remove_all(p, ec);
    fs::create_directories(p, ec);
    return p.lexically_normal().generic_string();
}

inline const char* const kTableNames[] = {
    "rules.csv",   "meta.csv",         "classes.csv", "class_stats.csv", "skills.csv",
    "effects.csv", "enemies.csv",      "enemy_attacks.csv", "affixes.csv", "item_bases.csv",
    "uniques.csv", "loot_tables.csv",  "loot_entries.csv",  "encounters.csv", "maps.csv",
    // Opcionais (docs/13): a pasta de fixtures pode não ter o arquivo.
    "potions.csv", "elite_modifiers.csv", "boss_phases.csv", "boss_patterns.csv", "enemy_ai.csv"};

inline bool IsOptionalTable(const std::string& t) {
    return t == "potions.csv" || t == "elite_modifiers.csv" || t == "boss_phases.csv" || t == "boss_patterns.csv" ||
           t == "enemy_ai.csv";
}

// Carrega as 15 tabelas de uma pasta de fixtures, permitindo trocar o texto de UMA tabela.
inline bool LoadFixture(shatter::ContentDB& db, const std::string& dir, const std::string& overrideTable = "",
                        const std::string& overrideText = "") {
    bool ok = true;
    for (const char* t : kTableNames) {
        if (IsOptionalTable(t) && overrideTable != t && !std::filesystem::exists(std::filesystem::u8path(dir + "/" + t))) continue;
        const std::string text = (overrideTable == t) ? overrideText : ReadFile(dir + "/" + t);
        ok = db.LoadTableCsv(t, text) && ok;
    }
    return ok;
}

// Troca a primeira ocorrência de `from` por `to` (para derivar CSV inválidos do fixture rico).
// Trecho inexistente é falha do teste: uma troca silenciosamente ignorada deixaria o cenário errado.
inline std::string Replace(std::string text, const std::string& from, const std::string& to) {
    const std::size_t pos = text.find(from);
    if (pos == std::string::npos) {
        FAIL("tu::Replace: trecho nao encontrado: " + from);
        return text;
    }
    text.replace(pos, from.size(), to);
    return text;
}

inline std::string RichDir() { return DataDir() + "/rich"; }

// Conteúdo rico (guerreiro, mapa da Cripta, loot com Únicos...). Carregado uma vez; imutável.
inline const shatter::ContentDB& RichDb() {
    static const shatter::ContentDB* db = [] {
        auto* d = new shatter::ContentDB();
        LoadFixture(*d, RichDir());
        d->Finalize();
        return d;
    }();
    return *db;
}

inline shatter::CharacterState MakeWarrior(const shatter::ContentDB& db, int level = 1, std::int64_t potions = 3) {
    (void)db;
    using namespace shatter;
    CharacterState c;
    c.name = "Teste";
    c.classId = "class.warrior";
    c.level = level;
    // Save v2: espaços de poção (Vida com `potions` cargas, Resguardo cheio). Sem recarga pendente.
    c.potionSlots = {{"potion.life", static_cast<int>(potions), 0.0}, {"potion.ward", 2, 0.0}};
    c.skills = {{"skill.warrior.iron_cut", 1, {}}, {"skill.warrior.cleave", 1, {}}, {"skill.warrior.stone_stance", 1, {}}};
    c.skillBar[0] = "skill.warrior.iron_cut";
    c.skillBar[1] = "skill.warrior.cleave";
    c.skillBar[2] = "skill.warrior.stone_stance";
    ItemInstance sword;
    sword.uid = 1;
    sword.baseId = "item_base.iron_sword";
    c.equipment[static_cast<std::size_t>(ItemSlot::MainHand)] = sword;
    c.conqueredMaps = {"map.act1.crypt"};
    return c;
}

inline std::vector<shatter::AiRule> DefaultRules() {
    using namespace shatter;
    AiRule potion;
    potion.condition = AiCondition::LifeBelow;
    potion.param = 0.35;
    potion.action = AiAction::UsePotion;
    AiRule cleave;
    cleave.condition = AiCondition::EnemiesAtLeast;
    cleave.param = 2;
    cleave.action = AiAction::UseSkill;
    cleave.refId = "skill.warrior.cleave";
    AiRule basic;
    basic.condition = AiCondition::Always;
    basic.action = AiAction::UseSkill;
    basic.refId = "skill.warrior.iron_cut";
    return {potion, cleave, basic};
}

inline shatter::ExpeditionRequest MakeRequest(const shatter::ContentDB& db, int hours = 1, std::uint64_t seed = 12345,
                                              int level = 1, std::int64_t potions = 3) {
    using namespace shatter;
    ExpeditionRequest r;
    r.snapshot.character = MakeWarrior(db, level, potions);
    r.snapshot.contentVersion = db.ContentVersion();
    r.mapId = "map.act1.crypt";
    r.rules = DefaultRules();
    r.seed = seed;
    r.startUtc = 1700000000;
    r.durationHours = hours;
    r.effectiveSeconds = static_cast<double>(hours) * 3600.0;
    r.contentVersion = db.ContentVersion();
    return r;
}

// Textos de Content/Data/Loc/*.csv (RFC 4180, UTF-8): chave → (pt_BR, en). Só para os testes de RF-45/RF-61;
// o jogo lê estes arquivos no C# (LocalizationService), nunca pelo core.
struct LocEntry {
    std::string ptBR;
    std::string en;
    std::string file;
    std::string context;
    std::string gender;
};

inline std::vector<std::vector<std::string>> ParseCsvRfc4180(const std::string& text) {
    std::vector<std::vector<std::string>> rows;
    std::vector<std::string> row;
    std::string cell;
    bool quoted = false, any = false;
    std::size_t i = 0;
    if (text.size() >= 3 && text.compare(0, 3, "\xEF\xBB\xBF") == 0) i = 3;
    for (; i < text.size(); ++i) {
        const char c = text[i];
        if (quoted) {
            if (c == '"') {
                if (i + 1 < text.size() && text[i + 1] == '"') { cell += '"'; ++i; }
                else quoted = false;
            } else {
                cell += c;
            }
            continue;
        }
        if (c == '"') { quoted = true; any = true; }
        else if (c == ',') { row.push_back(cell); cell.clear(); any = true; }
        else if (c == '\r') {}
        else if (c == '\n') {
            if (any || !cell.empty()) { row.push_back(cell); rows.push_back(row); }
            row.clear(); cell.clear(); any = false;
        } else { cell += c; any = true; }
    }
    if (any || !cell.empty()) { row.push_back(cell); rows.push_back(row); }
    return rows;
}

inline std::map<std::string, LocEntry> ReadLoc(const std::string& locDir) {
    namespace fs = std::filesystem;
    std::map<std::string, LocEntry> out;
    std::error_code ec;
    for (fs::directory_iterator it(fs::u8path(locDir), ec), end; !ec && it != end; it.increment(ec)) {
        if (it->path().extension() != ".csv") continue;
        const auto rows = ParseCsvRfc4180(ReadFile(it->path().u8string()));
        if (rows.empty()) continue;
        int kKey = -1, kPt = -1, kEn = -1, kCtx = -1, kGender = -1;
        for (std::size_t c = 0; c < rows[0].size(); ++c) {
            if (rows[0][c] == "key") kKey = static_cast<int>(c);
            if (rows[0][c] == "pt_BR") kPt = static_cast<int>(c);
            if (rows[0][c] == "en") kEn = static_cast<int>(c);
            if (rows[0][c] == "context") kCtx = static_cast<int>(c);
            if (rows[0][c] == "gender") kGender = static_cast<int>(c);
        }
        if (kKey < 0 || kPt < 0 || kEn < 0) continue;
        for (std::size_t r = 1; r < rows.size(); ++r) {
            const auto& row = rows[r];
            auto cell = [&](int k) {
                return k >= 0 && static_cast<std::size_t>(k) < row.size() ? row[static_cast<std::size_t>(k)] : std::string();
            };
            out[cell(kKey)] = LocEntry{cell(kPt), cell(kEn), it->path().filename().u8string(), cell(kCtx), cell(kGender)};
        }
    }
    return out;
}

}  // namespace tu
