// ContentDB — RNF-07: CSV válidos passam em Finalize; ID duplicado, referência inexistente,
// mín > máx, peso 0 etc. falham com tabela, linha e código certos. LF e CRLF.
#include "test_util.h"

using namespace shatter;

namespace {

bool HasError(const ContentDB& db, const std::string& table, int line, const std::string& code) {
    for (const ContentError& e : db.Errors()) {
        if (e.table == table && (line < 0 || e.line == line) && e.message.rfind(code, 0) == 0) return true;
    }
    return false;
}

std::string Dump(const ContentDB& db) {
    std::string s;
    for (const ContentError& e : db.Errors()) s += e.table + ":" + std::to_string(e.line) + " " + e.message + "\n";
    return s;
}

std::string ToCrlf(const std::string& in) {
    std::string out;
    for (char c : in) {
        if (c == '\n') out += '\r';
        out += c;
    }
    return out;
}

std::string Table(const std::string& name) { return tu::ReadFile(tu::RichDir() + "/" + name); }

}  // namespace

TEST(content_valid_fixture_dir_passes) {
    ContentDB db;
    EXPECT_TRUE(db.LoadDirectory(tu::DataDir()));
    EXPECT_TRUE(db.Finalize());
    EXPECT_TRUE(db.Errors().empty());
    EXPECT_EQ(db.ContentVersion(), static_cast<std::uint32_t>(1));
    EXPECT_TRUE(db.FindSkill("skill.warrior.iron_cut") != nullptr);
    EXPECT_TRUE(db.FindSkill("skill.nope") == nullptr);
    const ClassData* c = db.FindClass("class.warrior");
    ASSERT_TRUE(c != nullptr);
    EXPECT_EQ(c->stats.size(), static_cast<std::size_t>(2));
    EXPECT_NEAR(c->resourceOnHit, 10.0, 1e-12);
    const EnemyData* e = db.FindEnemy("enemy.hollow_sentinel");
    ASSERT_TRUE(e != nullptr);
    EXPECT_EQ(e->attacks.size(), static_cast<std::size_t>(1));
    EXPECT_TRUE(e->attacks[0].telegraphed);
    EXPECT_NEAR(db.Rules().evasionCap, 0.7, 1e-12);
}

TEST(content_rich_fixture_passes_and_exposes_everything) {
    ContentDB db;
    EXPECT_TRUE(db.LoadDirectory(tu::RichDir()));
    EXPECT_TRUE(db.Finalize());
    if (!db.Errors().empty()) FAIL(Dump(db));
    const SkillData* cleave = db.FindSkill("skill.warrior.cleave");
    ASSERT_TRUE(cleave != nullptr);
    EXPECT_TRUE(cleave->idle.supported);
    EXPECT_NEAR(cleave->idle.fractionOfGroupHit, 0.5, 1e-12);
    EXPECT_EQ(cleave->idle.paritySampleSize, static_cast<std::uint32_t>(100));
    EXPECT_EQ(cleave->onHitEffects.size(), static_cast<std::size_t>(1));
    EXPECT_NEAR(cleave->coefficientByRank[2], 1.2, 1e-12);
    EXPECT_EQ(db.Affixes().size(), static_cast<std::size_t>(10));  // ordem do CSV
    EXPECT_EQ(db.Affixes()[0].id, std::string("affix.life_flat"));
    EXPECT_EQ(db.Maps().size(), static_cast<std::size_t>(3));
    const MapData* crypt = db.FindMap("map.act1.crypt");
    ASSERT_TRUE(crypt != nullptr);
    EXPECT_EQ(crypt->encounters.size(), static_cast<std::size_t>(3));
    const LootTableData* t = db.FindLootTable("loot.crypt.guardian");
    ASSERT_TRUE(t != nullptr);
    EXPECT_EQ(t->entries.size(), static_cast<std::size_t>(6));
    EXPECT_TRUE(t->entries[0].manualOnly);
    EXPECT_TRUE(db.EffectLookup().count("effect.burn") == 1);
    const EffectData* burn = db.FindEffect("effect.burn");
    ASSERT_TRUE(burn != nullptr);
    EXPECT_NEAR(burn->damagePerTick[1], 1.0, 1e-12);
    EXPECT_EQ(burn->tags, Mask(Tag::Fire));
    const ItemBaseData* vest = db.FindItemBase("item_base.leather_vest");
    ASSERT_TRUE(vest != nullptr);
    EXPECT_NEAR(vest->implicitMods[0].value, 10.0, 1e-12);
    const UniqueData* u = db.FindUnique("unique.bell_warden_blade");
    ASSERT_TRUE(u != nullptr);
    EXPECT_EQ(u->fixedMods[0].requiredTags, Mask(Tag::Melee));
}

TEST(content_crlf_and_lf_give_the_same_database) {
    ContentDB lf, crlf;
    EXPECT_TRUE(tu::LoadFixture(lf, tu::RichDir()));
    EXPECT_TRUE(lf.Finalize());
    bool ok = true;
    for (const char* t : tu::kTableNames) ok = crlf.LoadTableCsv(t, ToCrlf(Table(t))) && ok;
    EXPECT_TRUE(ok);
    EXPECT_TRUE(crlf.Finalize());
    EXPECT_TRUE(crlf.Errors().empty());
    EXPECT_EQ(crlf.Affixes().size(), lf.Affixes().size());
    EXPECT_EQ(crlf.FindEnemy("enemy.crypt_guardian")->stats.size(), lf.FindEnemy("enemy.crypt_guardian")->stats.size());
    // BOM, linhas em branco e arquivo sem quebra final também são aceitos.
    ContentDB b;
    std::string meta = "\xEF\xBB\xBF" "key,value\r\n\r\ncontent_version,3";
    EXPECT_TRUE(b.LoadTableCsv("meta.csv", meta));
    EXPECT_TRUE(b.Errors().empty());
}

TEST(content_load_order_does_not_matter) {
    ContentDB db;
    const int n = static_cast<int>(sizeof(tu::kTableNames) / sizeof(tu::kTableNames[0]));
    for (int i = n - 1; i >= 0; --i) db.LoadTableCsv(tu::kTableNames[i], Table(tu::kTableNames[i]));
    EXPECT_TRUE(db.Finalize());
    if (!db.Errors().empty()) FAIL(Dump(db));
    EXPECT_EQ(db.FindClass("class.warrior")->stats.size(), static_cast<std::size_t>(4));
    EXPECT_EQ(db.FindLootTable("loot.crypt.common")->entries.size(), static_cast<std::size_t>(4));
}

TEST(content_invalid_fixtures_fail_with_expected_error) {
    const char* names[] = {"dup_skill_id", "encounter_unknown_enemy", "rule_out_of_range"};
    for (const char* n : names) {
        const std::string dir = tu::DataDir() + "/invalid/" + n;
        json::Value exp;
        ASSERT_TRUE(json::Parse(tu::ReadFile(dir + "/expected_error.json"), exp));
        ContentDB db;
        tu::LoadFixture(db, dir);
        EXPECT_FALSE(db.Finalize());
        const bool found = HasError(db, exp["table"].AsString(), static_cast<int>(exp["line"].AsInt()), exp["code"].AsString());
        if (!found) FAIL(std::string(n) + ": erro esperado nao encontrado. Erros:\n" + Dump(db));
    }
}

