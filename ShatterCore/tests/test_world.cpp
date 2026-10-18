// Core da Cripta (world.h): estado do mundo no save, semente da visita, encontros sorteados, baús, XP por morte, Fervor e o
// tempo da arma (docs/19 N0). Números vêm do banco; o fixture rico traz os dados dos testes.
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <memory>
#include <set>

#include "shatter/world.h"
#include "test_util.h"

using namespace shatter;

namespace {

SaveData NewSave(const ContentDB& db, int level = 1) {
    SaveData s;
    s.contentVersion = db.ContentVersion();
    s.characters.push_back(tu::MakeWarrior(db, level));
    s.nextItemUid = 1000;
    return s;
}

std::unique_ptr<ContentDB> RichWith(const std::string& table, const std::string& text) {
    auto db = std::make_unique<ContentDB>();
    for (const char* t : tu::kTableNames) {
        const std::string path = tu::RichDir() + "/" + t;
        std::string body;
        if (table == t) body = text;
        else if (std::filesystem::exists(std::filesystem::u8path(path))) body = tu::ReadFile(path);
        else if (tu::IsOptionalTable(t)) continue;
        else body = tu::ReadFile(path);
        db->LoadTableCsv(t, body);
    }
    db->Finalize();
    return db;
}

std::string Bytes(const SaveData& s) { return SerializeJson(s, false); }

constexpr const char* kMap = "map.act1.crypt";

}  // namespace

// ---------------------------------------------------------------------------------------------------------------------
// Estado do mundo
// ---------------------------------------------------------------------------------------------------------------------
TEST(world_state_set_get_is_idempotent_per_area_and_does_not_leak_between_areas) {
    const ContentDB& db = tu::RichDb();
    SaveData s = NewSave(db);
    EXPECT_FALSE(IsWorldObjectOpen(s, kMap, "chest.crypt.01"));
    EXPECT_TRUE(SetWorldObjectOpen(s, kMap, "chest.crypt.01", true));
    EXPECT_TRUE(SetWorldObjectOpen(s, kMap, "chest.crypt.01", true));              // idempotente
    EXPECT_TRUE(SetWorldObjectOpen(s, kMap, "secret.crypt.cracked_wall", true));
    EXPECT_TRUE(SetWorldObjectOpen(s, kMap, "shortcut.crypt.a", true));
    ASSERT_TRUE(FindWorldArea(s, kMap) != nullptr);
    EXPECT_EQ(FindWorldArea(s, kMap)->opened.size(), static_cast<std::size_t>(3));
    EXPECT_TRUE(IsWorldObjectOpen(s, kMap, "chest.crypt.01"));
    EXPECT_FALSE(IsWorldObjectOpen(s, kMap, "chest.crypt.02"));
    EXPECT_FALSE(IsWorldObjectOpen(s, "map.endgame.ossuary", "chest.crypt.01"));   // outra área
    EXPECT_TRUE(SetWorldObjectOpen(s, kMap, "chest.crypt.01", false));
    EXPECT_FALSE(IsWorldObjectOpen(s, kMap, "chest.crypt.01"));
    EXPECT_TRUE(SetWorldObjectOpen(s, "map.nowhere.x", "chest.x.01", false));      // fechar o que nunca abriu: nada
    EXPECT_TRUE(FindWorldArea(s, "map.nowhere.x") == nullptr);
    // IDs inválidos e limites: recusa sem mudar nada.
    const std::string before = Bytes(s);
    EXPECT_FALSE(SetWorldObjectOpen(s, kMap, "Chest Bad", true));
    EXPECT_FALSE(SetWorldObjectOpen(s, "", "chest.crypt.01", true));
    EXPECT_EQ(Bytes(s), before);
    for (std::size_t i = 0; FindWorldArea(s, kMap)->opened.size() < kMaxWorldObjects; ++i)
        SetWorldObjectOpen(s, kMap, "obj.test.n" + std::to_string(i), true);
    const std::string full = Bytes(s);
    EXPECT_FALSE(SetWorldObjectOpen(s, kMap, "obj.test.extra", true));
    EXPECT_EQ(Bytes(s), full);
    SaveData many = NewSave(db);
    for (std::size_t i = 0; i < kMaxWorldAreas; ++i) EXPECT_TRUE(SetWorldObjectOpen(many, "map.t.a" + std::to_string(i), "obj.t.x", true));
    EXPECT_FALSE(SetWorldObjectOpen(many, "map.t.over", "obj.t.x", true));
}

TEST(world_state_survives_the_save_file_and_old_saves_load_with_nothing_opened) {
    const ContentDB& db = tu::RichDb();
    SaveData plain = NewSave(db);
    const std::string plainJson = Bytes(plain);
    EXPECT_TRUE(plainJson.find("world_state") == std::string::npos);   // save sem estado de mundo: mesmos bytes e hash de antes
    SaveData s = plain;
    SetWorldObjectOpen(s, kMap, "chest.crypt.02", true);
    SetWorldObjectOpen(s, kMap, "shortcut.crypt.a", true);
    std::uint64_t seed = 0;
    ASSERT_TRUE(BeginAreaVisit(db, s, kMap, &seed));
    SaveData loaded;
    ASSERT_TRUE(ParseJson(SerializeJson(s, true), loaded) == LoadStatus::Ok);
    EXPECT_EQ(Bytes(loaded), Bytes(s));
    EXPECT_TRUE(IsWorldObjectOpen(loaded, kMap, "chest.crypt.02"));
    EXPECT_TRUE(IsWorldObjectOpen(loaded, kMap, "shortcut.crypt.a"));
    EXPECT_EQ(FindWorldArea(loaded, kMap)->visits, static_cast<std::uint32_t>(1));
    // Save v2 antigo (sem o campo) abre normalmente e grava o mesmo conteúdo.
    SaveData old;
    ASSERT_TRUE(ParseJson(SerializeJson(plain, true), old) == LoadStatus::Ok);
    EXPECT_TRUE(old.world.empty());
    EXPECT_FALSE(IsWorldObjectOpen(old, kMap, "chest.crypt.02"));
    EXPECT_EQ(Bytes(old), plainJson);
    // Adulterado: visitas negativas, repetição de área e ID inválido são recusados.
    auto tamper = [&](const std::string& from, const std::string& to) {
        std::string text = json::Serialize(SaveToJson(s), false);
        const std::size_t at = text.find(from);
        if (at == std::string::npos) { FAIL("trecho nao encontrado: " + from); return false; }
        text.replace(at, from.size(), to);
        json::Value v;
        if (!json::Parse(text, v)) { FAIL("json invalido"); return false; }
        SaveData out;
        return SaveFromJson(v, out, nullptr);
    };
    EXPECT_FALSE(tamper("\"visits\":1", "\"visits\":-1"));
    EXPECT_FALSE(tamper("\"chest.crypt.02\"", "\"Chest Bad\""));
    EXPECT_FALSE(tamper("\"map_id\":\"map.act1.crypt\"", "\"map_id\":\"\""));
}

// ---------------------------------------------------------------------------------------------------------------------
// Visita e encontros
// ---------------------------------------------------------------------------------------------------------------------
TEST(world_visit_seed_comes_from_the_core_and_the_encounter_is_deterministic_per_seed) {
    const ContentDB& db = tu::RichDb();
    SaveData s = NewSave(db);
    std::uint64_t a = 0, b = 0, c = 0;
    EXPECT_FALSE(BeginAreaVisit(db, s, "map.nowhere.x", &a));
    ASSERT_TRUE(BeginAreaVisit(db, s, kMap, &a));
    SaveData copy = s;
    ASSERT_TRUE(BeginAreaVisit(db, s, kMap, &b));
    ASSERT_TRUE(BeginAreaVisit(db, copy, kMap, &c));
    EXPECT_NE(a, b);                         // outra visita, outra semente
    EXPECT_EQ(b, c);                         // mesmo estado, mesma semente
    EXPECT_EQ(b, VisitSeed(s, kMap, 2));
    EXPECT_NE(VisitSeed(s, kMap, 2), VisitSeed(s, "map.endgame.ossuary", 2));
    EXPECT_EQ(FindWorldArea(s, kMap)->visits, static_cast<std::uint32_t>(2));
    // Mesma semente e encontro: mesma formação, quantas vezes pedir (também depois de um checkpoint).
    for (std::uint64_t seed = 1; seed <= 200; ++seed) {
        RolledEncounter x, y;
        ASSERT_TRUE(RollEncounter(db, "enc.crypt.patrol_b", seed, x));
        ASSERT_TRUE(RollEncounter(db, "enc.crypt.patrol_b", seed, y));
        ASSERT_EQ(x.groups.size(), y.groups.size());
        for (std::size_t g = 0; g < x.groups.size(); ++g) {
            ASSERT_EQ(x.groups[g].slots.size(), y.groups[g].slots.size());
            for (std::size_t i = 0; i < x.groups[g].slots.size(); ++i) {
                EXPECT_EQ(x.groups[g].slots[i].elite, y.groups[g].slots[i].elite);
                EXPECT_EQ(x.groups[g].slots[i].modifierId, y.groups[g].slots[i].modifierId);
            }
        }
    }
    RolledEncounter none;
    EXPECT_FALSE(RollEncounter(db, "enc.crypt.nope", 1, none));
}

TEST(world_encounter_counts_stay_in_range_elite_follows_chance_and_boss_never_becomes_elite) {
    const ContentDB& db = tu::RichDb();
    int sentinels[3] = {0, 0, 0}, spitters[3] = {0, 0, 0};
    long long slotsA = 0, elitesA = 0, slotsSpit = 0, elitesSpit = 0;
    std::set<std::string> mods;
    for (std::uint64_t seed = 1; seed <= 20000; ++seed) {
        RolledEncounter e;
        ASSERT_TRUE(RollEncounter(db, "enc.crypt.patrol_a", seed, e));
        ASSERT_EQ(e.groups.size(), static_cast<std::size_t>(1));
        const std::size_t n = e.groups[0].slots.size();
        ASSERT_TRUE(n >= 1 && n <= 2);                         // enemy.hollow_sentinel:1:2
        ++sentinels[n];
        for (const RolledSlot& sl : e.groups[0].slots) {
            ++slotsA;
            if (sl.elite) { ++elitesA; mods.insert(sl.modifierId); }
        }
        ASSERT_TRUE(RollEncounter(db, "enc.crypt.patrol_b", seed, e));
        ASSERT_EQ(e.groups.size(), static_cast<std::size_t>(2));
        EXPECT_EQ(e.groups[0].slots.size(), static_cast<std::size_t>(1));
        const std::size_t m = e.groups[1].slots.size();
        ASSERT_TRUE(m >= 1 && m <= 2);                         // enemy.ash_spitter:1:2:0.2
        ++spitters[m];
        for (const RolledSlot& sl : e.groups[1].slots) {
            ++slotsSpit;
            if (sl.elite) ++elitesSpit;
        }
        ASSERT_TRUE(RollEncounter(db, "enc.crypt.guardian", seed, e));
        EXPECT_TRUE(e.isBoss);
        EXPECT_FALSE(e.groups[0].slots[0].elite);
        ASSERT_TRUE(RollEncounter(db, "enc.crypt.elite_shield", seed, e));   // elite fixo: nunca "sorteado"
        EXPECT_FALSE(e.groups[0].slots[0].elite);
    }
    EXPECT_TRUE(sentinels[1] > 8000 && sentinels[2] > 8000);   // uniforme entre min e max
    EXPECT_TRUE(spitters[1] > 8000 && spitters[2] > 8000);
    EXPECT_NEAR(static_cast<double>(elitesA) / static_cast<double>(slotsA), 0.1, 0.01);     // chanceElite 0,1
    EXPECT_NEAR(static_cast<double>(elitesSpit) / static_cast<double>(slotsSpit), 0.2, 0.012);   // chanceElite 0,2
    for (const std::string& id : mods) EXPECT_TRUE(id.empty() || db.FindEliteModifier(id) != nullptr);
    EXPECT_TRUE(mods.size() >= 2);                             // os modificadores com peso aparecem
}

TEST(world_encounter_roll_does_not_touch_the_loot_or_craft_streams) {
    const ContentDB& db = tu::RichDb();
    Pcg32 loot = Pcg32::ForStream(77, RngStream::Loot, 0);
    const std::uint64_t next = Pcg32::ForStream(77, RngStream::Loot, 0).NextU64();
    RolledEncounter e;
    for (std::uint64_t seed = 1; seed <= 100; ++seed) ASSERT_TRUE(RollEncounter(db, "enc.crypt.patrol_b", seed, e));
    EXPECT_EQ(loot.NextU64(), next);                           // RollEncounter não recebe nem consome o Loot
}

// ---------------------------------------------------------------------------------------------------------------------
// Baús e loot de encontro
// ---------------------------------------------------------------------------------------------------------------------
TEST(world_chest_table_comes_from_chests_csv_with_the_area_table_as_fallback) {
    const ContentDB& db = tu::RichDb();
    EXPECT_EQ(ChestLootTable(db, kMap, "chest.crypt.04"), std::string("loot.crypt.common"));    // chests.csv do fixture
    EXPECT_EQ(ChestLootTable(db, kMap, "chest.crypt.01"), std::string("loot.crypt.area"));
    EXPECT_EQ(ChestLootTable(db, kMap, "chest.crypt.99"), std::string("loot.crypt.area"));      // sem linha: areaLootTable
    EXPECT_EQ(ChestLootTable(db, "map.endgame.ossuary", "chest.crypt.04"), std::string("loot.crypt.area"));  // baú de outro mapa
    EXPECT_EQ(ChestLootTable(db, "map.nowhere.x", "chest.crypt.01"), std::string());
    EXPECT_EQ(AreaLootTable(db, kMap), std::string("loot.crypt.area"));
    EXPECT_EQ(AreaLootTable(db, "map.nowhere.x"), std::string());
    // Sem chests.csv, todo baú cai na tabela da área.
    auto none = std::make_unique<ContentDB>();
    for (const char* t : tu::kTableNames) {
        if (std::string(t) == "chests.csv") continue;
        const std::string path = tu::RichDir() + "/" + t;
        if (tu::IsOptionalTable(t) && !std::filesystem::exists(std::filesystem::u8path(path))) continue;
        none->LoadTableCsv(t, tu::ReadFile(path));
    }
    EXPECT_TRUE(none->Finalize());
    EXPECT_EQ(ChestLootTable(*none, kMap, "chest.crypt.04"), std::string("loot.crypt.area"));
}

TEST(world_chests_csv_validation_errors) {
    const std::string good = tu::ReadFile(tu::RichDir() + "/chests.csv");
    auto bad = [&](const std::string& text, const char* code) {
        const auto db = RichWith("chests.csv", text);
        bool found = false;
        for (const ContentError& e : db->Errors()) found = found || e.message.find(code) == 0;
        EXPECT_TRUE(found);
    };
    bad(good + "chest.crypt.06,map.nowhere.x,loot.crypt.area\n", "E_FK");
    bad(good + "chest.crypt.06,map.act1.crypt,loot.nowhere.x\n", "E_FK");
    bad(good + "chest.crypt.01,map.act1.crypt,loot.crypt.area\n", "E_DUP_ID");
    bad(good + "box.crypt.06,map.act1.crypt,loot.crypt.area\n", "E_ID_PREFIX");
    EXPECT_TRUE(RichWith("chests.csv", good)->Errors().empty());
}

// ---------------------------------------------------------------------------------------------------------------------
// XP por morte e Fervor
// ---------------------------------------------------------------------------------------------------------------------
TEST(world_kill_xp_comes_from_enemies_csv_with_elite_and_boss_values) {
    const ContentDB& db = tu::RichDb();
    EXPECT_NEAR(KillXpBase(db, "enemy.hollow_sentinel", 4, false, ""), 10.0 + 2.0 * 3.0, 1e-12);
    EXPECT_NEAR(KillXpBase(db, "enemy.hollow_sentinel", 1, false, ""), 10.0, 1e-12);
    // Elite sorteado: elite_xp_mult (3,0) x o modificador (xpMult neutro).
    EXPECT_NEAR(KillXpBase(db, "enemy.hollow_sentinel", 4, true, "modifier.elite.swift"), 16.0 * db.Rules().eliteXpMult, 1e-9);
    EXPECT_NEAR(KillXpBase(db, "enemy.hollow_sentinel", 4, true, ""), 16.0 * db.Rules().eliteXpMult, 1e-9);
    // Elite fixo e chefe: o valor do próprio inimigo.
    EXPECT_NEAR(KillXpBase(db, "enemy.shielded_sentinel", 4, false, ""), 30.0 + 4.0 * 3.0, 1e-12);
    EXPECT_NEAR(KillXpBase(db, "enemy.crypt_guardian", 4, false, ""), 100.0 + 10.0 * 3.0, 1e-12);
    EXPECT_TRUE(KillXpBase(db, "enemy.nope", 4, false, "") < 0.0);
    EXPECT_TRUE(KillXpBase(db, "enemy.crypt_guardian", 4, false, "") > KillXpBase(db, "enemy.hollow_sentinel", 4, false, ""));
}

TEST(world_award_kill_xp_applies_fervor_levels_up_in_the_save_and_stops_at_the_area_cap) {
    const ContentDB& db = tu::RichDb();
    const double fervor = db.Rules().fervorXpMult;
    SaveData s = NewSave(db, 1);
    XpAward a = AwardKillXp(db, s, 0, kMap, "enemy.hollow_sentinel", 4, false, "", true);
    ASSERT_TRUE(a.ok);
    EXPECT_NEAR(a.awarded, 16.0 * fervor, 1e-9);
    EXPECT_EQ(s.characters[0].level, 1);
    EXPECT_NEAR(s.characters[0].xp, 16.0 * fervor, 1e-9);
    EXPECT_EQ(a.levelCap, 6);                                  // monsterLevel 4 + xp_cap_levels_above_area 2
    // Sem Fervor entra o valor cru.
    SaveData raw = NewSave(db, 1);
    EXPECT_NEAR(AwardKillXp(db, raw, 0, kMap, "enemy.hollow_sentinel", 4, false, "", false).awarded, 16.0, 1e-9);
    // Sobe de nível no save.
    const double need1 = db.XpToNextLevel(1);
    int kills = 0;
    while (s.characters[0].level == 1 && kills < 1000) {
        AwardKillXp(db, s, 0, kMap, "enemy.hollow_sentinel", 4, false, "", true);
        ++kills;
    }
    EXPECT_EQ(s.characters[0].level, 2);
    EXPECT_TRUE(static_cast<double>(kills + 1) * 16.0 * fervor >= need1);
    EXPECT_TRUE(s.characters[0].xp < db.XpToNextLevel(2));
    // O getter devolve o nível e o XP do save (o herói usa este).
    const XpAward p = CharacterProgress(db, s, 0, kMap);
    EXPECT_EQ(p.levelAfter, 2);
    EXPECT_NEAR(p.xpInLevel, s.characters[0].xp, 1e-12);
    EXPECT_NEAR(p.xpToNext, db.XpToNextLevel(2), 1e-9);
    EXPECT_EQ(CharacterProgress(db, s, 0, "").levelCap, db.Rules().maxLevel);
    // Teto da área: nunca passa do nível 6 e, no teto, o XP não entra.
    for (int i = 0; i < 100000 && s.characters[0].level < 6; ++i) AwardKillXp(db, s, 0, kMap, "enemy.crypt_guardian", 4, false, "", true);
    EXPECT_EQ(s.characters[0].level, 6);
    const std::string atCap = Bytes(s);
    const XpAward capped = AwardKillXp(db, s, 0, kMap, "enemy.crypt_guardian", 4, false, "", true);
    EXPECT_NEAR(capped.awarded, 0.0, 1e-12);
    EXPECT_NEAR(capped.xpToNext, 0.0, 1e-12);
    EXPECT_EQ(Bytes(s), atCap);
    // Recusas: inimigo e personagem desconhecidos não mudam nada.
    EXPECT_FALSE(AwardKillXp(db, s, 0, kMap, "enemy.nope", 4, false, "", true).ok);
    EXPECT_FALSE(AwardKillXp(db, s, 3, kMap, "enemy.hollow_sentinel", 4, false, "", true).ok);
    EXPECT_EQ(Bytes(s), atCap);
    EXPECT_EQ(AwardXp(db, s.characters[0], 1.0e9, 30), 24);   // a coleta e o jogo manual usam a mesma regra
}

TEST(world_fervor_info_mirrors_rules_for_the_hud) {
    const ContentDB& db = tu::RichDb();
    const FervorInfo f = GetFervorInfo(db);
    EXPECT_NEAR(f.xpMult, 3.0, 1e-12);
    EXPECT_NEAR(f.xpBonus, 2.0, 1e-12);          // XP +200%
    EXPECT_NEAR(f.goldMatBonus, 0.25, 1e-12);
    EXPECT_NEAR(f.rareBonus, 1.0, 1e-12);
}

// ---------------------------------------------------------------------------------------------------------------------
// N0: o attackTime da arma muda o tempo dos golpes que escalam com arma
// ---------------------------------------------------------------------------------------------------------------------
namespace {
const ContentDB* RealDb() {
    static const ContentDB* db = [] {
        auto* d = new ContentDB();
        d->LoadDirectory(tu::ContentDir());
        d->Finalize();
        return d;
    }();
    return db;
}
double Combo(const ContentDB& db, const StatBlock& stats, const ItemBaseData* weapon) {
    const BasicKitData* kit = db.FindBasicKit("class.warrior");
    double total = 0.0;
    if (kit == nullptr) return total;
    const double ref = ClassRefAttackTime(db, "class.warrior");
    for (const ContentId& id : kit->lightChain) {
        const SkillData* s = db.FindSkill(id);
        const ActionTimingInfo t = ComputeActionTiming(db, *s, stats, nullptr, WeaponTimeFactor(*s, weapon, ref));
        total += t.windup + t.impact + t.recovery;
    }
    return total;
}
}  // namespace

TEST(weapon_time_factor_slows_scaling_skills_with_heavier_weapons_and_leaves_the_rest_alone) {
    SkillData scaling, flat;
    scaling.scalesWithWeapon = true;
    flat.scalesWithWeapon = false;
    ItemBaseData sword, maul;
    sword.attackTime = 0.9;
    maul.attackTime = 1.4;
    EXPECT_NEAR(WeaponTimeFactor(scaling, &sword, 0.9), 1.0, 1e-12);           // a arma inicial não muda nada
    EXPECT_NEAR(WeaponTimeFactor(scaling, &maul, 0.9), 1.4 / 0.9, 1e-12);       // o Martelo fica mais lento
    EXPECT_NEAR(WeaponTimeFactor(flat, &maul, 0.9), 1.0, 1e-12);                // habilidade que não escala com arma
    EXPECT_NEAR(WeaponTimeFactor(scaling, nullptr, 0.9), 1.0, 1e-12);           // desarmado
    EXPECT_NEAR(WeaponTimeFactor(scaling, &maul, 0.0), 1.0, 1e-12);             // classe sem refAttackTime
    const ContentDB& db = tu::RichDb();
    StatBlock stats;
    SkillData s;
    s.windup = 0.2; s.impact = 0.1; s.recovery = 0.4; s.cooldown = 4.0;
    const ActionTimingInfo base = ComputeActionTiming(db, s, stats);
    const ActionTimingInfo slow = ComputeActionTiming(db, s, stats, nullptr, 2.0);
    EXPECT_NEAR(slow.windup, base.windup * 2.0, 1e-12);
    EXPECT_NEAR(slow.impact, base.impact * 2.0, 1e-12);
    EXPECT_NEAR(slow.recovery, base.recovery * 2.0, 1e-12);
    EXPECT_NEAR(slow.cooldown, base.cooldown, 1e-12);                           // a recarga não muda
}

TEST(weapon_time_real_content_maul_is_slower_than_sword_and_dps_stays_in_the_doc_range) {
    const ContentDB& db = *RealDb();
    ASSERT_TRUE(db.Errors().empty());
    const ItemBaseData* sword = db.FindItemBase("item_base.iron_sword");
    const ItemBaseData* maul = db.FindItemBase("item_base.stone_maul");
    ASSERT_TRUE(sword != nullptr && maul != nullptr);
    const BasicKitData* kit = db.FindBasicKit("class.warrior");
    ASSERT_TRUE(kit != nullptr);
    EXPECT_NEAR(kit->refAttackTime, sword->attackTime, 1e-12);                  // referência = arma inicial da classe
    StatBlock stats;   // atributos neutros (velocidade de ataque 1): isola o efeito da arma
    const double swordCombo = Combo(db, stats, sword);
    const double maulCombo = Combo(db, stats, maul);
    EXPECT_TRUE(swordCombo > 0.0);
    EXPECT_TRUE(maulCombo > swordCombo);
    EXPECT_NEAR(maulCombo / swordCombo, maul->attackTime / sword->attackTime, 1e-9);   // 36% menos velocidade
    // DPS do tooltip (dano x velocidade de ataque / attackTime) dentro da faixa do docs/19 1.3.1: Espada 10,0 e Martelo 11,4.
    auto dps = [&](const ItemBaseData* w) {
        double raw = 0.0;
        for (double v : w->weaponDamage) raw += v;
        return raw * stats.Get(StatId::AttackSpeed) / w->attackTime;
    };
    EXPECT_TRUE(dps(sword) > 9.5 && dps(sword) < 10.5);
    EXPECT_TRUE(dps(maul) > 10.9 && dps(maul) < 11.9);
    EXPECT_TRUE(dps(maul) > dps(sword));
}

TEST(weapon_time_ref_attack_time_column_is_validated) {
    const std::string kits = tu::ReadFile(tu::ContentDir() + "/basic_kits.csv");
    EXPECT_TRUE(kits.find("refAttackTime") != std::string::npos);
    // A coluna é opcional: o fixture rico (sem basic_kits) e kits sem a coluna continuam válidos (fator 1).
    EXPECT_NEAR(ClassRefAttackTime(tu::RichDb(), "class.warrior"), 0.0, 1e-12);
    EXPECT_NEAR(ClassRefAttackTime(*RealDb(), "class.nope"), 0.0, 1e-12);
}
