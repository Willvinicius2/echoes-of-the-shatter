// Fome e loot da Mancha na expedição idle (docs/tecnico/09, 15.4): golpes devorados limitados pela Fome e a tabela extra
// da Mancha rolada no encontro limpo. Usa o conteúdo real (Content/Data e Story/).
#include <memory>
#include <string>

#include "shatter/json.h"
#include "shatter/save.h"
#include "shatter/story.h"
#include "test_util.h"

using namespace shatter;

namespace {

const ContentDB& RealDb() {
    static const std::unique_ptr<ContentDB> db = [] {
        auto d = std::make_unique<ContentDB>();
        d->LoadDirectory(tu::ContentDir());
        d->Finalize();
        return d;
    }();
    return *db;
}

const StoryDB& RealStory() {
    static const std::unique_ptr<StoryDB> story = [] {
        auto s = std::make_unique<StoryDB>();
        s->LoadDirectory(tu::ContentDir() + "/Story");
        s->Finalize(&RealDb());
        return s;
    }();
    return *story;
}

const char* kSlam = "skill.devoured.guardian_slam";

// Guerreiro da Cripta nível 4 com 4 habilidades (espaços 5 e 6 livres para o golpe devorado), kit completo e 3 poções de Vida.
ExpeditionRequest Hero(std::uint64_t seed, int hours = 12) {
    const ContentDB& db = RealDb();
    ExpeditionRequest req;
    CharacterState& c = req.snapshot.character;
    c.name = "Teste";
    c.classId = "class.warrior";
    c.level = 4;
    c.potionSlots = {{"potion.life", 3, 0.0}, {"potion.ward", 2, 0.0}};
    c.skills = {{"skill.warrior.iron_cut", 1, {}}, {"skill.warrior.charge", 1, {}}, {"skill.warrior.stone_rift", 1, {}},
                {"skill.warrior.shield_bash", 1, {}}};
    c.skillBar = {"skill.warrior.iron_cut", "skill.warrior.charge", "skill.warrior.stone_rift", "skill.warrior.shield_bash", "", ""};
    const char* bases[] = {"item_base.iron_sword", "item_base.iron_helm", "item_base.leather_vest", "item_base.leather_gloves",
                           "item_base.worn_trousers", "item_base.worn_boots"};
    const ItemSlot slots[] = {ItemSlot::MainHand, ItemSlot::Head, ItemSlot::Body, ItemSlot::Hands, ItemSlot::Legs, ItemSlot::Feet};
    for (std::size_t i = 0; i < 6; ++i) {
        ItemInstance it;
        it.uid = i + 1;
        it.baseId = bases[i];
        c.equipment[static_cast<std::size_t>(slots[i])] = it;
    }
    c.conqueredMaps = {"map.act1.crypt"};
    req.snapshot.contentVersion = db.ContentVersion();
    req.contentVersion = db.ContentVersion();
    req.mapId = "map.act1.crypt";
    req.rules = {{AiCondition::LifeBelow, 0.35, AiAction::UsePotion, "potion.life"},
                 {AiCondition::EnemiesAtLeast, 3.0, AiAction::UseSkill, "skill.warrior.stone_rift"},
                 {AiCondition::Always, 0.0, AiAction::UseSkill, "skill.warrior.iron_cut"}};
    req.seed = seed;
    req.startUtc = 1'700'000'000;
    req.durationHours = hours;
    req.effectiveSeconds = hours * 3600.0;
    return req;
}

int DevouredUses(const ExpeditionResult& r) {
    int n = 0;
    for (const EncounterReceipt& rc : r.receipts) n += rc.devouredUses;
    return n;
}

std::int64_t LootUnits(const ExpeditionResult& r) {
    std::int64_t n = static_cast<std::int64_t>(r.items.size());
    for (const StackEntry& s : r.stacks) n += s.amount;
    return n;
}

ExpeditionProgress RunChunks(const ContentDB& db, const ExpeditionRequest& req, std::uint32_t chunk) {
    ExpeditionProgress p;
    int guard = 0;
    while (p.stop == StopReason::None && ++guard < 1000000) p = SimulateRange(db, req, p, p.nextEncounter, chunk);
    return p;
}

SaveData SaveWithKill() {
    SaveData s;
    CharacterState c;
    c.bossProgress.push_back({"enemy.crypt_guardian", 1, 0});
    s.characters.push_back(c);
    return s;
}

}  // namespace

TEST(story_idle_devoured_uses_follow_hunger) {
    const StoryDB& story = RealStory();
    ASSERT_TRUE(story.Errors().empty());
    SaveData none = SaveWithKill();
    EXPECT_TRUE(DevouredSkills(story, none).empty());

    SaveData devoured = SaveWithKill();
    ASSERT_TRUE(ApplyVerdict(story, devoured, "verdict.r1.devour") == VerdictResult::Ok);
    ASSERT_EQ(DevouredSkills(story, devoured).size(), static_cast<std::size_t>(1));
    EXPECT_EQ(DevouredSkills(story, devoured)[0], std::string(kSlam));
    // hunger_max 4 e custo 1 (story_rules.csv): Fome 1, 2, 3 e 4 liberam 3, 2, 1 e 0 usos.
    for (int hunger = 1; hunger <= 4; ++hunger) {
        devoured.story.hunger = hunger;
        EXPECT_EQ(IdleDevouredUses(story, devoured), 4 - hunger);
    }

    // Custo 0: sem limite.
    StoryDB free;
    const std::string dir = tu::ContentDir() + "/Story/";
    for (const char* t : {"regions.csv", "echoes.csv", "quests.csv", "verdicts.csv"}) free.LoadTableCsv(t, tu::ReadFile(dir + t));
    free.LoadTableCsv("story_rules.csv", tu::Replace(tu::ReadFile(dir + "story_rules.csv"), "devoured_hunger_cost,1", "devoured_hunger_cost,0"));
    ASSERT_TRUE(free.Finalize(&RealDb()));
    EXPECT_EQ(IdleDevouredUses(free, devoured), -1);
}

TEST(story_idle_apply_story_to_expedition_fills_every_field) {
    const StoryDB& story = RealStory();
    const std::string map = "map.act1.crypt";
    ExpeditionStartParams p;
    SaveData none = SaveWithKill();
    ApplyStoryToExpedition(story, none, map, p);
    EXPECT_EQ(p.storyStatBonusPct + p.storyPotionEffectPct + p.storyEliteBonusPct + p.storyDevouredUses, 0);
    EXPECT_TRUE(p.storyDevouredSkills.empty());
    EXPECT_TRUE(p.storyStainLootTable.empty());

    SaveData purified = SaveWithKill();
    ASSERT_TRUE(ApplyVerdict(story, purified, "verdict.r1.exorcise") == VerdictResult::Ok);
    ApplyStoryToExpedition(story, purified, map, p);
    EXPECT_EQ(p.storyPotionEffectPct, story.RelicPotionEffectPct());
    EXPECT_EQ(p.storyDevouredUses, 0);
    EXPECT_TRUE(p.storyDevouredSkills.empty());
    EXPECT_TRUE(p.storyStainLootTable.empty());

    SaveData stained = SaveWithKill();
    ASSERT_TRUE(ApplyVerdict(story, stained, "verdict.r1.devour") == VerdictResult::Ok);
    ApplyStoryToExpedition(story, stained, map, p);
    EXPECT_EQ(p.storyStatBonusPct, TotalStatBonusPct(story, stained));
    EXPECT_EQ(p.storyEliteBonusPct, story.StainEliteBonusPct());
    EXPECT_EQ(p.storyDevouredUses, 3);
    ASSERT_EQ(p.storyDevouredSkills.size(), static_cast<std::size_t>(1));
    EXPECT_EQ(p.storyStainLootTable, story.StainLootTable());
    ApplyStoryToExpedition(story, stained, "map.other", p);   // outro mapa: sem Mancha, mas a Fome vale para o save todo
    EXPECT_EQ(p.storyEliteBonusPct, 0);
    EXPECT_TRUE(p.storyStainLootTable.empty());
    EXPECT_EQ(p.storyDevouredUses, 3);

    stained.story.hunger = story.HungerMax();   // Fome cheia: o golpe nem vai para o idle
    ApplyStoryToExpedition(story, stained, map, p);
    EXPECT_EQ(p.storyDevouredUses, 0);
    EXPECT_TRUE(p.storyDevouredSkills.empty());
}

TEST(expedition_stain_loot_rolls_extra_table_without_touching_combat) {
    const ContentDB& db = RealDb();
    ASSERT_TRUE(db.Errors().empty());
    const ExpeditionRequest base = Hero(21);
    ExpeditionRequest stain = base;
    stain.storyStainLootTable = RealStory().StainLootTable();
    const ExpeditionResult a = SimulateExpedition(db, base);
    const ExpeditionResult b = SimulateExpedition(db, stain);
    ASSERT_TRUE(a.encountersCleared > 100);
    EXPECT_TRUE(a.stop == b.stop);
    // O loot usa só o fluxo Loot: combate, XP e tempo são os mesmos.
    EXPECT_EQ(a.kills, b.kills);
    EXPECT_NEAR(a.xpGained, b.xpGained, 1e-9);
    EXPECT_NEAR(a.effectiveSeconds, b.effectiveSeconds, 1e-9);
    EXPECT_TRUE(LootUnits(b) > LootUnits(a));
    EXPECT_TRUE(a.resultHash != b.resultHash);
    EXPECT_EQ(FinalizeExpedition(db, stain, RunChunks(db, stain, 5)).resultHash, b.resultHash);

    ExpeditionRequest unknown = base;
    unknown.storyStainLootTable = "loot.nao.existe";
    EXPECT_TRUE(SimulateExpedition(db, unknown).stop == StopReason::ContentMismatch);
}

TEST(expedition_devoured_strike_spends_the_hunger_budget) {
    const ContentDB& db = RealDb();
    const ExpeditionRequest base = Hero(33);
    const ExpeditionResult plain = SimulateExpedition(db, base);
    EXPECT_EQ(DevouredUses(plain), 0);

    // Fome cheia (0 usos): idêntico a não ter golpe.
    ExpeditionRequest full = base;
    full.storyDevouredSkills = {kSlam};
    full.storyDevouredUses = 0;
    EXPECT_EQ(SimulateExpedition(db, full).resultHash, plain.resultHash);

    // Fome 1: 3 usos na expedição inteira, gastos assim que o golpe fica pronto.
    ExpeditionRequest hungry = full;
    hungry.storyDevouredUses = 3;
    const ExpeditionResult h = SimulateExpedition(db, hungry);
    EXPECT_EQ(DevouredUses(h), 3);
    EXPECT_TRUE(h.resultHash != plain.resultHash);
    // A conta atravessa as partes da simulação (progresso salvo entre chamadas).
    for (std::uint32_t chunk : {1u, 4u}) {
        const ExpeditionProgress p = RunChunks(db, hungry, chunk);
        EXPECT_EQ(p.devouredUsesSpent, 3);
        EXPECT_EQ(FinalizeExpedition(db, hungry, p).resultHash, h.resultHash);
    }

    // Sem limite (custo 0): o golpe volta a cada recarga.
    ExpeditionRequest unlimited = full;
    unlimited.storyDevouredUses = -1;
    EXPECT_TRUE(DevouredUses(SimulateExpedition(db, unlimited)) > 3);

    // Regra da IA citando o golpe: só a regra o usa (aqui, contra elite).
    ExpeditionRequest ruled = hungry;
    ruled.rules.insert(ruled.rules.begin() + 1, AiRule{AiCondition::TargetIsElite, 0.0, AiAction::UseSkill, kSlam});
    const ExpeditionResult r = SimulateExpedition(db, ruled);
    EXPECT_TRUE(DevouredUses(r) <= 3);
    for (const EncounterReceipt& rc : r.receipts)
        if (rc.devouredUses > 0) EXPECT_TRUE(rc.elitesKilled > 0);

    // Barra cheia nos espaços 3 a 6: como no manual, o golpe fica de fora.
    ExpeditionRequest packed = hungry;
    packed.snapshot.character.skillBar[4] = "skill.warrior.charge";
    packed.snapshot.character.skillBar[5] = "skill.warrior.shield_bash";
    EXPECT_EQ(DevouredUses(SimulateExpedition(db, packed)), 0);

    // Golpe já na barra do snapshot: a Fome também o trava (0 usos = nunca; 2 usos = 2).
    ExpeditionRequest barred = base;
    barred.snapshot.character.skillBar[5] = kSlam;
    EXPECT_EQ(DevouredUses(SimulateExpedition(db, barred)), 0);
    barred.storyDevouredSkills = {kSlam};
    barred.storyDevouredUses = 2;
    EXPECT_EQ(DevouredUses(SimulateExpedition(db, barred)), 2);

    // Golpe que não existe mais no conteúdo.
    ExpeditionRequest unknown = hungry;
    unknown.storyDevouredSkills = {"skill.devoured.nao_existe"};
    EXPECT_TRUE(SimulateExpedition(db, unknown).stop == StopReason::ContentMismatch);
}

TEST(expedition_story_idle_fields_roundtrip_and_keep_old_bytes) {
    const ExpeditionRequest base = Hero(5, 1);
    const std::string plain = json::Serialize(ExpeditionRequestToJson(base), false);
    EXPECT_TRUE(plain.find("story_") == std::string::npos);

    ExpeditionRequest all = base;
    all.storyDevouredSkills = {kSlam};
    all.storyDevouredUses = 2;
    all.storyStainLootTable = "loot.crypt.stain";
    ExpeditionRequest back;
    ASSERT_TRUE(ExpeditionRequestFromJson(ExpeditionRequestToJson(all), back));
    ASSERT_EQ(back.storyDevouredSkills.size(), static_cast<std::size_t>(1));
    EXPECT_EQ(back.storyDevouredSkills[0], std::string(kSlam));
    EXPECT_EQ(back.storyDevouredUses, 2);
    EXPECT_EQ(back.storyStainLootTable, std::string("loot.crypt.stain"));

    // Sem usos a lista não é gravada (Fome cheia = mesmo pedido de antes).
    ExpeditionRequest spent = base;
    spent.storyDevouredSkills = {kSlam};
    EXPECT_EQ(json::Serialize(ExpeditionRequestToJson(spent), false), plain);

    // Tipos errados e lista longa demais são recusados.
    json::Value v = ExpeditionRequestToJson(all);
    v.Set("story_devoured_skills", json::Value("skill.devoured.guardian_slam"));
    EXPECT_FALSE(ExpeditionRequestFromJson(v, back));
    json::Value bad = json::Value::MakeArray();
    bad.Push(json::Value(static_cast<std::int64_t>(1)));
    v.Set("story_devoured_skills", bad);
    EXPECT_FALSE(ExpeditionRequestFromJson(v, back));
    json::Value many = json::Value::MakeArray();
    for (int i = 0; i <= kMaxStoryDevouredSkills; ++i) many.Push(json::Value(kSlam));
    v.Set("story_devoured_skills", many);
    EXPECT_FALSE(ExpeditionRequestFromJson(v, back));
    v.Set("story_devoured_skills", json::Value::MakeArray());
    v.Set("story_devoured_uses", json::Value(static_cast<std::int64_t>(-50)));
    ASSERT_TRUE(ExpeditionRequestFromJson(v, back));
    EXPECT_EQ(back.storyDevouredUses, -1);
}
