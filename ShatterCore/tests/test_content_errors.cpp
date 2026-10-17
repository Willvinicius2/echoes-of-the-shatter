// ContentDB — catálogo de erros (RNF-07), decisões de pendências (P3, P8) e conteúdo real.
#include "test_util.h"

#include <algorithm>

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

std::string Table(const std::string& name) { return tu::ReadFile(tu::RichDir() + "/" + name); }

void ExpectFail(const std::string& tag, const std::string& table, const std::string& text, const std::string& errTable,
                int line, const std::string& code) {
    ContentDB db;
    tu::LoadFixture(db, tu::RichDir(), table, text);
    if (db.Finalize()) {
        FAIL(tag + ": o conteudo invalido passou em Finalize");
        return;
    }
    if (!HasError(db, errTable, line, code))
        FAIL(tag + ": esperado " + errTable + ":" + std::to_string(line) + " " + code + "\nobtido:\n" + Dump(db));
}

}  // namespace

TEST(content_rnf07_error_catalog) {
    using tu::Replace;
    const std::string skills = Table("skills.csv"), loot = Table("loot_entries.csv"), maps = Table("maps.csv"),
                      affixes = Table("affixes.csv"), rules = Table("rules.csv");
    ExpectFail("id duplicado", "affixes.csv", affixes + "affix.life_flat,prefix,life,flat,,1,2,1,1,,,false\n", "affixes.csv", 10, "E_DUP_ID");
    ExpectFail("min > max", "affixes.csv", Replace(affixes, "life,flat,,10,20,1,10", "life,flat,,30,20,1,10"), "affixes.csv", 2, "E_RANGE");
    ExpectFail("peso 0", "affixes.csv", Replace(affixes, "1,10,body|head,life,false", "1,0,body|head,life,false"), "affixes.csv", 2, "E_RANGE");
    ExpectFail("efeito inexistente", "skills.csv", Replace(skills, "effect.guard_break", "effect.nope"), "skills.csv", 3, "E_FK");
    ExpectFail("idle sem amostra de paridade", "skills.csv",
               Replace(skills, "false,,,,,,,,1,,,,,,,\nskill.enemy.sentinel_strike", "true,1,,,,,,0,1,,,,,,,\nskill.enemy.sentinel_strike"), "skills.csv", 5, "E_RULE");
    ExpectFail("idle sem selo de calibracao", "skills.csv",
               Replace(skills, "false,,,,,,,,1,,,,,,,\nskill.enemy.sentinel_strike", "true,1,,,,,,20,1,,,,none,,,\nskill.enemy.sentinel_strike"), "skills.csv", 5, "E_RULE");
    ExpectFail("selo de calibracao desconhecido", "skills.csv",
               Replace(skills, "false,,,,,,,,1,,,,,,,\nskill.enemy.sentinel_strike", "true,1,,,,,,20,1,,,,guess,,,\nskill.enemy.sentinel_strike"), "skills.csv", 5, "E_ENUM");
    ExpectFail("unico idle sem amostra", "uniques.csv", Replace(Table("uniques.csv"), "damage:increased:0.2:melee,effect.block_spark,false,,,", "damage:increased:0.2:melee,effect.block_spark,true,,,"), "uniques.csv", 2, "E_RULE");
    ExpectFail("recarga abaixo do minimo", "skills.csv", Replace(skills, ",0,8,0.2,0,0.2,", ",0,0.05,0.2,0,0.2,"), "skills.csv", 4, "E_RANGE");
    ExpectFail("tipo invalido", "skills.csv", Replace(skills, "10,,,,1,1.1", "ten,,,,1,1.1"), "skills.csv", 2, "E_TYPE");
    ExpectFail("tags obrigatorias (P8)", "skills.csv", Replace(skills, "attack|melee|physical,melee,,10,,,,1,1.1", ",melee,,10,,,,1,1.1"), "skills.csv", 2, "E_REQUIRED");
    ExpectFail("aspas", "class_stats.csv", Replace(Table("class_stats.csv"), "class.warrior,life,600,40", "class.warrior,\"life\",200,20"), "class_stats.csv", 2, "E_QUOTE");
    ExpectFail("coluna faltando", "class_stats.csv", "classId,stat,base\nclass.warrior,life,200\n", "class_stats.csv", 1, "E_HEADER");
    ExpectFail("coluna extra", "class_stats.csv", "classId,stat,base,perLevel,x\nclass.warrior,life,600,40,1\n", "class_stats.csv", 1, "E_HEADER");
    ExpectFail("numero de colunas", "class_stats.csv", "classId,stat,base,perLevel\nclass.warrior,life,200\n", "class_stats.csv", 2, "E_COLUMNS");
    ExpectFail("classe sem recurso", "class_stats.csv", "classId,stat,base,perLevel\nclass.warrior,life,600,40\n", "classes.csv", 2, "E_RULE");
    ExpectFail("classe sem vida", "class_stats.csv", "classId,stat,base,perLevel\nclass.warrior,resource,100,0\n", "classes.csv", 2, "E_RULE");
    ExpectFail("classe desconhecida em class_stats", "class_stats.csv", Table("class_stats.csv") + "class.ghost,life,1,1\n", "class_stats.csv", 6, "E_FK");
    ExpectFail("startingSkill inexistente", "classes.csv", Replace(Table("classes.csv"), "skill.warrior.iron_cut", "skill.warrior.nope"), "classes.csv", 2, "E_FK");
    ExpectFail("unico sem manualOnly", "loot_entries.csv", Replace(loot, "unique.bell_warden_blade,,1,1,1,999,true", "unique.bell_warden_blade,,1,1,1,999,false"), "loot_entries.csv", 8, "E_RULE");
    ExpectFail("booleano invalido", "loot_entries.csv", Replace(loot, "1,1,1,999,true", "1,1,1,999,yes"), "loot_entries.csv", 8, "E_TYPE");
    ExpectFail("echo_fragment como stack", "loot_entries.csv", loot + "loot.crypt.area,stack,material.echo_fragment,1,1,1,1,999,false,,,\n", "loot_entries.csv", 14, "E_RULE");
    ExpectFail("ciclo de subtabelas", "loot_entries.csv", loot + "loot.crypt.common,table,loot.crypt.guardian,5,1,1,1,999,false,,,\n", "loot_tables.csv", -1, "E_RULE");
    ExpectFail("ataque com habilidade inexistente", "enemy_attacks.csv", Replace(Table("enemy_attacks.csv"), "skill.enemy.ember_spit", "skill.enemy.nope"), "enemy_attacks.csv", 3, "E_FK");
    ExpectFail("inimigo sem ataques", "enemy_attacks.csv", "enemyId,skillId,weight,telegraphed\nenemy.hollow_sentinel,skill.enemy.sentinel_strike,1,true\n", "enemies.csv", -1, "E_RULE");
    ExpectFail("chefe sem isBoss", "encounters.csv", Replace(Table("encounters.csv"), "enemy.crypt_guardian:1:1:0,1,10,true", "enemy.crypt_guardian:1:1:0,1,10,false"), "encounters.csv", 4, "E_RULE");
    ExpectFail("mapa com encontro inexistente", "maps.csv", Replace(maps, "enc.crypt.patrol_a|enc.crypt.patrol_b", "enc.crypt.patrol_a|enc.crypt.nope"), "maps.csv", 2, "E_FK");
    ExpectFail("arma sem dano", "item_bases.csv", Replace(Table("item_bases.csv"), "main_hand,1,,10,,,,1.0,melee,m", "main_hand,1,,,,,,1.0,melee,m"), "item_bases.csv", 2, "E_RULE");
    // A chave estranha fica na linha seguinte à última da fixture; não fixar o número, porque a fixture cresce.
    ExpectFail("regra desconhecida", "rules.csv", rules + "bogus_key,1\n", "rules.csv",
               static_cast<int>(std::count(rules.begin(), rules.end(), '\n')) + 1, "E_UNKNOWN_KEY");
    ExpectFail("regra faltando", "rules.csv", Replace(rules, "max_level,30\n", ""), "rules.csv", 0, "E_REQUIRED");
    ExpectFail("regra fora da faixa", "rules.csv", Replace(rules, "block_cap,0.5", "block_cap,-0.1"), "rules.csv", 4, "E_RANGE");
    ExpectFail("expoente de XP", "rules.csv", Replace(rules, "xp_exponent,1.5", "xp_exponent,1.3"), "rules.csv", -1, "E_RANGE");
    ExpectFail("content_version zero", "meta.csv", "key,value\ncontent_version,0\n", "meta.csv", 2, "E_RANGE");
    ExpectFail("prefixo errado", "effects.csv", Replace(Table("effects.csv"), "effect.slow,", "slow.effect,"), "effects.csv", 3, "E_ID_PREFIX");
    ExpectFail("DoT sem intervalo", "effects.csv", Replace(Table("effects.csv"), "effect.burn,4,1,", "effect.burn,4,0,"), "effects.csv", 2, "E_RULE");
    ExpectFail("habilidade de classe com prefixo trocado", "skills.csv", Replace(skills, "skill.warrior.cleave,class.warrior", "skill.mage.cleave,class.warrior"), "skills.csv", 3, "E_RULE");
    {
        ContentDB db;
        EXPECT_FALSE(db.LoadTableCsv("bogus.csv", "a,b\n"));
        EXPECT_FALSE(db.Finalize());
        EXPECT_TRUE(HasError(db, "bogus.csv", 0, "E_UNKNOWN_TABLE"));
    }
}

TEST(content_p3_p8_decisions_documented) {
    // P3: family.*, spec.*, currency.*, material.*, page.*, book.spec.* e map_stone.* nao tem tabela:
    // o core confere so formato e prefixo (o fixture rico ja usa familias e livros sem tabela e passa).
    ContentDB ok;
    EXPECT_TRUE(tu::LoadFixture(ok, tu::RichDir()));
    EXPECT_TRUE(ok.Finalize());
    // ...mas um prefixo errado continua sendo erro.
    ExpectFail("familia com prefixo errado", "enemies.csv", tu::Replace(Table("enemies.csv"), "family.soldier_echo", "soldier_echo.x"), "enemies.csv", 2, "E_ID_PREFIX");
    ExpectFail("stack com prefixo errado", "loot_entries.csv", tu::Replace(Table("loot_entries.csv"), "currency.gold,80", "gold.coin,80"), "loot_entries.csv", 4, "E_ID_PREFIX");
    // P8: tags de habilidade sao obrigatorias no CSV (como no esquema), mas SkillData::tags = 0 vale via Add().
    ContentDB db;
    db.SetContentVersion(1);
    SkillData s;
    s.id = "skill.common.untagged";
    db.Add(s);
    EXPECT_TRUE(db.Finalize());
}

TEST(content_programmatic_add_and_loot_depth_limit) {
    ContentDB db;
    db.SetContentVersion(1);
    ItemBaseData base;
    base.id = "item_base.rock";
    base.slot = ItemSlot::Head;
    db.Add(base);
    for (int i = 0; i < 9; ++i) {  // cadeia de 9 tabelas: profundidade 9 > 8
        LootTableData t;
        t.id = "loot.chain." + std::to_string(i);
        LootEntry e;
        if (i < 8) {
            e.kind = LootEntryKind::Table;
            e.refId = "loot.chain." + std::to_string(i + 1);
        } else {
            e.kind = LootEntryKind::ItemBase;
            e.refId = "item_base.rock";
        }
        t.entries.push_back(e);
        db.Add(t);
    }
    EXPECT_FALSE(db.Finalize());
    EXPECT_TRUE(HasError(db, "loot_tables.csv", -1, "E_RULE"));
    EXPECT_FALSE(db.Finalize());  // chamar de novo devolve o mesmo resultado
}

TEST(content_add_duplicate_and_bad_reference) {
    ContentDB db;
    db.SetContentVersion(1);
    SkillData s;
    s.id = "skill.common.poke";
    s.tags = Mask(Tag::Attack);
    s.onHitEffects = {"effect.missing"};
    db.Add(s);
    db.Add(s);  // duplicado
    EXPECT_FALSE(db.Finalize());
    EXPECT_TRUE(HasError(db, "skills", 0, "E_DUP_ID"));
    EXPECT_TRUE(HasError(db, "skills.csv", 0, "E_FK"));
}

TEST(content_real_data_passes_finalize) {
    ContentDB db;
    const bool loaded = db.LoadDirectory(SHATTER_CONTENT_DIR);
    const bool fin = db.Finalize();
    if (!loaded || !fin) FAIL("conteudo real invalido:\n" + Dump(db));
    EXPECT_TRUE(db.ContentVersion() >= 1u);
}

TEST(content_encounter_must_spawn_at_least_one_enemy) {
    // Um encontro com 0 inimigos duraria 0 s e travaria o simulador: Finalize recusa (programático ou CSV)
    // e o simulador encerra com ContentMismatch se ainda assim receber um.
    ContentDB db;
    db.SetContentVersion(1);
    EncounterTemplate e;
    e.id = "enc.test.empty";
    EncounterGroup g;
    g.enemyId = "enemy.ghost";
    g.countMin = 0;
    g.countMax = 0;
    e.groups.push_back(g);
    db.Add(e);
    EXPECT_FALSE(db.Finalize());
    EXPECT_TRUE(HasError(db, "encounters.csv", 0, "E_RANGE"));
    ExpectFail("grupo com zero inimigos", "encounters.csv",
               tu::Replace(Table("encounters.csv"), "enemy.hollow_sentinel:1:2:0.1", "enemy.hollow_sentinel:0:2:0.1"),
               "encounters.csv", 2, "E_RANGE");
}
