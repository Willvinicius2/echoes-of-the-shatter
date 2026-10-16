// Utilidades compartilhadas pelos testes do ShatterCore (só testes; nada daqui entra no motor).
#pragma once

#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

#include "shatter/shatter.h"
#include "test_framework.h"

namespace tu {

inline std::string DataDir() { return SHATTER_TEST_DATA_DIR; }

inline std::string ReadFile(const std::string& path) {
    std::ifstream in(std::filesystem::u8path(path), std::ios::binary);
    return std::string(std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>());
}

// Pasta temporária DENTRO do repositório (<repo>/build/test_tmp/<nome>): tudo fica no mesmo disco do projeto.
inline std::string TmpDir(const std::string& name) {
    namespace fs = std::filesystem;
    const fs::path p = fs::path(DataDir()) / ".." / ".." / ".." / "build" / "test_tmp" / name;
    std::error_code ec;
    fs::remove_all(p, ec);
    fs::create_directories(p, ec);
    return p.lexically_normal().generic_string();
}

inline const char* const kTableNames[] = {
    "rules.csv",   "meta.csv",         "classes.csv", "class_stats.csv", "skills.csv",
    "effects.csv", "enemies.csv",      "enemy_attacks.csv", "affixes.csv", "item_bases.csv",
    "uniques.csv", "loot_tables.csv",  "loot_entries.csv",  "encounters.csv", "maps.csv"};

// Carrega as 15 tabelas de uma pasta de fixtures, permitindo trocar o texto de UMA tabela.
inline bool LoadFixture(shatter::ContentDB& db, const std::string& dir, const std::string& overrideTable = "",
                        const std::string& overrideText = "") {
    bool ok = true;
    for (const char* t : kTableNames) {
        const std::string text = (overrideTable == t) ? overrideText : ReadFile(dir + "/" + t);
        ok = db.LoadTableCsv(t, text) && ok;
    }
    return ok;
}

// Troca a primeira ocorrência de `from` por `to` (para derivar CSV inválidos do fixture rico).
inline std::string Replace(std::string text, const std::string& from, const std::string& to) {
    const std::size_t pos = text.find(from);
    if (pos != std::string::npos) text.replace(pos, from.size(), to);
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
    c.potions = potions;
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

}  // namespace tu
