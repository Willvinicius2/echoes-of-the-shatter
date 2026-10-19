// História (story.h): tabelas Story/, Ecos, veredito irreversível e o campo opcional `story` do save.
#include <string>

#include "shatter/story.h"
#include "test_util.h"

using namespace shatter;

namespace {

const char* kRegions =
    "id,order,mapId,generalId,exorcizeVerdict,devourVerdict\n"
    "region.r1.crypt,1,map.act1.crypt,enemy.crypt_guardian,verdict.r1.exorcise,verdict.r1.devour\n";
const char* kEchoes =
    "id,regionId,kind,revealsSkill,minToReveal\n"
    "echo.r1.a,region.r1.crypt,weapon,skill.enemy.guardian_hammer,2\n"
    "echo.r1.b,region.r1.crypt,memory,skill.enemy.guardian_hammer,2\n"
    "echo.r1.c,region.r1.crypt,memory,skill.enemy.guardian_shield_bash,1\n";
const char* kQuests =
    "id,regionId,giver,objectiveType,objectiveTarget,objectiveCount,requires,reward\n"
    "quest.r1.one,region.r1.crypt,npc.ilsa,talk,npc.ilsa,1,,unlock.x\n"
    "quest.r1.two,region.r1.crypt,npc.tico,collect_echo,region.r1.crypt,3,quest.r1.one,reveal.y\n";
const char* kVerdicts =
    "id,regionId,choice,hungerDelta,statBonusPct,grantsRelic,grantsSignature,regionState,hubState,lastWordsKey\n"
    "verdict.r1.exorcise,region.r1.crypt,exorcise,0,0,relic.r1.rest,,purified,hub.a,dlg.x\n"
    "verdict.r1.devour,region.r1.crypt,devour,1,10,,skill.devoured.slam,stain,hub.b,\n";
const char* kRules = "key,value\nhunger_max,4\n";

StoryDB Make(const std::string& verdicts = kVerdicts, const std::string& rules = kRules, bool* ok = nullptr) {
    StoryDB db;
    bool all = db.LoadTableCsv("regions.csv", kRegions);
    all = db.LoadTableCsv("echoes.csv", kEchoes) && all;
    all = db.LoadTableCsv("quests.csv", kQuests) && all;
    all = db.LoadTableCsv("verdicts.csv", verdicts) && all;
    all = db.LoadTableCsv("story_rules.csv", rules) && all;
    all = db.Finalize() && all;
    if (ok != nullptr) *ok = all;
    return db;
}

SaveData SaveWithKill(bool killed) {
    SaveData s;
    CharacterState c;
    if (killed) c.bossProgress.push_back({"enemy.crypt_guardian", 1, 0});
    s.characters.push_back(c);
    return s;
}

}  // namespace

TEST(story_tables_load_and_validate) {
    bool ok = false;
    const StoryDB db = Make(kVerdicts, kRules, &ok);
    EXPECT_TRUE(ok);
    EXPECT_EQ(db.HungerMax(), 4);
    EXPECT_EQ(db.Regions().size(), static_cast<std::size_t>(1));
    EXPECT_TRUE(db.FindVerdict("verdict.r1.devour") != nullptr);
}

TEST(story_repo_tables_are_valid) {
    StoryDB db;
    const std::string dir = tu::DataDir() + "/../../../EchoesOfTheShatter/Content/Data/Story";
    EXPECT_TRUE(db.LoadDirectory(dir));
    EXPECT_TRUE(db.Finalize());
    for (const ContentError& e : db.Errors()) FAIL(e.table + ": " + e.message);
}

TEST(story_rejects_bad_rules_and_references) {
    bool ok = true;
    Make(kVerdicts, "key,value\n", &ok);                       // sem hunger_max
    EXPECT_FALSE(ok);
    Make("id,regionId,choice,hungerDelta,statBonusPct,grantsRelic,grantsSignature,regionState,hubState,lastWordsKey\n"
         "verdict.r1.exorcise,region.r1.crypt,exorcise,1,0,,,purified,hub.a,\n"   // Exorcizar com Fome
         "verdict.r1.devour,region.r1.crypt,devour,1,10,,,stain,hub.b,\n",
         kRules, &ok);
    EXPECT_FALSE(ok);
    Make("id,regionId,choice,hungerDelta,statBonusPct,grantsRelic,grantsSignature,regionState,hubState,lastWordsKey\n"
         "verdict.r1.exorcise,region.r1.crypt,exorcise,0,0,,,purified,hub.a,\n"
         "verdict.r1.devour,region.r1.crypt,devour,9,10,,,stain,hub.b,\n",          // Fome acima do máximo
         kRules, &ok);
    EXPECT_FALSE(ok);
}

TEST(story_rejects_swapped_unlisted_and_repeated_rules) {
    bool ok = true;
    StoryDB a;   // exorcizeVerdict apontando para o veredito de Devorar
    a.LoadTableCsv("regions.csv", "id,order,mapId,generalId,exorcizeVerdict,devourVerdict\n"
                                  "region.r1.crypt,1,map.act1.crypt,enemy.crypt_guardian,verdict.r1.devour,verdict.r1.devour\n");
    a.LoadTableCsv("echoes.csv", kEchoes);
    a.LoadTableCsv("quests.csv", kQuests);
    a.LoadTableCsv("verdicts.csv", kVerdicts);
    a.LoadTableCsv("story_rules.csv", kRules);
    EXPECT_FALSE(a.Finalize());
    const std::string extra = std::string(kVerdicts) + "verdict.r1.x,region.r1.crypt,devour,1,0,,,stain,hub.b,\n";
    Make(extra, kRules, &ok);                                   // veredito que nenhuma região lista
    EXPECT_FALSE(ok);
    Make(kVerdicts, "key,value\nhunger_max,4\nhunger_max,5\n", &ok);
    EXPECT_FALSE(ok);
    SaveData s = SaveWithKill(true);
    EXPECT_TRUE(ApplyVerdict(StoryDB(), s, "verdict.r1.devour") == VerdictResult::UnknownVerdict);   // banco vazio
}

TEST(story_echoes_record_once_and_reveal_skill) {
    const StoryDB db = Make();
    SaveData s;
    EXPECT_FALSE(RecordEcho(db, s, "echo.r1.nope"));
    EXPECT_TRUE(RecordEcho(db, s, "echo.r1.a"));
    EXPECT_FALSE(RecordEcho(db, s, "echo.r1.a"));
    EXPECT_EQ(EchoesFound(db, s, "region.r1.crypt"), 1);
    EXPECT_FALSE(IsSkillRevealed(db, s, "region.r1.crypt", "skill.enemy.guardian_hammer"));   // precisa de 2
    EXPECT_TRUE(RecordEcho(db, s, "echo.r1.b"));
    EXPECT_TRUE(IsSkillRevealed(db, s, "region.r1.crypt", "skill.enemy.guardian_hammer"));
    EXPECT_FALSE(IsSkillRevealed(db, s, "region.r1.crypt", "skill.enemy.guardian_shield_bash"));
}

TEST(story_verdict_requires_general_defeated_and_is_irreversible) {
    const StoryDB db = Make();
    SaveData fresh = SaveWithKill(false);
    EXPECT_TRUE(ApplyVerdict(db, fresh, "verdict.r1.devour") == VerdictResult::GeneralNotDefeated);
    EXPECT_TRUE(fresh.story.Empty());
    EXPECT_TRUE(ApplyVerdict(db, fresh, "verdict.r1.nope") == VerdictResult::UnknownVerdict);

    SaveData s = SaveWithKill(true);
    EXPECT_TRUE(ApplyVerdict(db, s, "verdict.r1.devour") == VerdictResult::Ok);
    EXPECT_EQ(s.story.hunger, 1);
    EXPECT_EQ(TotalStatBonusPct(db, s), 10);
    EXPECT_TRUE(DecidedVerdict(db, s, "region.r1.crypt") != nullptr);
    EXPECT_TRUE(ApplyVerdict(db, s, "verdict.r1.exorcise") == VerdictResult::AlreadyDecided);   // não desfaz
    EXPECT_EQ(s.story.hunger, 1);

    SaveData e = SaveWithKill(true);
    EXPECT_TRUE(ApplyVerdict(db, e, "verdict.r1.exorcise") == VerdictResult::Ok);
    EXPECT_EQ(e.story.hunger, 0);
    EXPECT_EQ(TotalStatBonusPct(db, e), 0);
}

TEST(story_save_roundtrip_and_old_saves_keep_bytes) {
    const StoryDB db = Make();
    SaveData old = SaveWithKill(true);
    const std::string before = SerializeJson(old, false);
    EXPECT_TRUE(before.find("\"story\"") == std::string::npos);   // sem história: mesmos bytes e hash de antes

    SaveData s = SaveWithKill(true);
    RecordEcho(db, s, "echo.r1.c");
    ApplyVerdict(db, s, "verdict.r1.devour");
    const std::string text = SerializeJson(s, true);
    SaveData back;
    EXPECT_TRUE(ParseJson(text, back) == LoadStatus::Ok);
    EXPECT_EQ(back.story.hunger, 1);
    EXPECT_EQ(back.story.verdicts.size(), static_cast<std::size_t>(1));
    EXPECT_EQ(back.story.echoes.size(), static_cast<std::size_t>(1));
    EXPECT_EQ(SerializeJson(back, false), SerializeJson(s, false));
}

TEST(story_save_rejects_bad_story_data) {
    SaveData s = SaveWithKill(true);
    s.story.hunger = 1;
    s.story.verdicts.push_back({"region.r1.crypt", "verdict.r1.devour"});
    s.story.verdicts.push_back({"region.r1.crypt", "verdict.r1.exorcise"});   // região repetida
    SaveData back;
    EXPECT_TRUE(ParseJson(SerializeJson(s, true), back) == LoadStatus::BadData);
    SaveData h = SaveWithKill(true);
    h.story.hunger = 101;
    EXPECT_TRUE(ParseJson(SerializeJson(h, true), back) == LoadStatus::BadData);
}

TEST(story_directory_errors_are_marked_as_io) {
    StoryDB db;
    EXPECT_FALSE(db.LoadDirectory("/nao/existe/story"));
    ASSERT_TRUE(!db.Errors().empty());
    EXPECT_TRUE(db.Errors().front().message.rfind("E_IO", 0) == 0);
}

TEST(story_repo_content_has_devoured_signature_skill) {
    const std::string root = tu::DataDir() + "/../../../EchoesOfTheShatter/Content/Data";
    ContentDB content;
    ASSERT_TRUE(content.LoadDirectory(root));
    ASSERT_TRUE(content.Finalize());
    StoryDB story;
    ASSERT_TRUE(story.LoadDirectory(root + "/Story"));
    EXPECT_TRUE(story.Finalize(&content));
    for (const ContentError& e : story.Errors()) FAIL(e.table + ": " + e.message);
    for (const StoryVerdict& v : story.Verdicts())
        if (!v.grantsSignature.empty()) EXPECT_TRUE(content.FindSkill(v.grantsSignature) != nullptr);
    EXPECT_TRUE(story.RelicPotionEffectPct() > 0);
    EXPECT_TRUE(story.StainEliteBonusPct() > 0);
}

TEST(story_relic_potion_effect_and_stain_elite_bonus) {
    const StoryDB db = Make(kVerdicts, "key,value\nhunger_max,4\nrelic_potion_effect_pct,25\nstain_elite_bonus_pct,15\n");
    SaveData none = SaveWithKill(true);
    EXPECT_EQ(TotalPotionEffectPct(db, none), 0);
    EXPECT_EQ(StainEliteBonusPctForMap(db, none, "map.act1.crypt"), 0);

    SaveData purified = SaveWithKill(true);
    ASSERT_TRUE(ApplyVerdict(db, purified, "verdict.r1.exorcise") == VerdictResult::Ok);
    EXPECT_EQ(TotalPotionEffectPct(db, purified), 25);
    EXPECT_EQ(StainEliteBonusPctForMap(db, purified, "map.act1.crypt"), 0);

    SaveData stained = SaveWithKill(true);
    ASSERT_TRUE(ApplyVerdict(db, stained, "verdict.r1.devour") == VerdictResult::Ok);
    EXPECT_EQ(TotalPotionEffectPct(db, stained), 0);
    EXPECT_EQ(StainEliteBonusPctForMap(db, stained, "map.act1.crypt"), 15);
    EXPECT_EQ(StainEliteBonusPctForMap(db, stained, "map.other"), 0);
}
