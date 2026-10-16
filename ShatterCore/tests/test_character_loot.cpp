// Personagem (BuildStatBlock, IsIdleCompatible) e loot (RF-25, RF-26, RF-27, RF-32 parcial, RF-34 parcial).
#include <cmath>
#include <map>

#include "test_util.h"

using namespace shatter;

TEST(character_build_statblock_values_and_order) {
    const ContentDB& db = tu::RichDb();
    CharacterState c = tu::MakeWarrior(db, 3);
    ItemInstance helm;
    helm.uid = 2;
    helm.baseId = "item_base.bone_helm";
    helm.rarity = Rarity::Magic;
    helm.affixes = {{"affix.life_flat", 15.0}};
    c.equipment[static_cast<std::size_t>(ItemSlot::Head)] = helm;
    ItemInstance blade;
    blade.uid = 3;
    blade.baseId = "item_base.iron_sword";
    blade.rarity = Rarity::Unique;
    blade.uniqueId = "unique.bell_warden_blade";
    c.equipment[static_cast<std::size_t>(ItemSlot::MainHand)] = blade;
    c.passives = {"passive.n12"};  // sem tabela (P3): aceito e sem efeito

    StatBlock sb;
    std::string err;
    ASSERT_TRUE(BuildStatBlock(db, c, sb, &err));
    EXPECT_NEAR(sb.GetBase(StatId::Life), 680.0, 1e-9);   // 600 + 40 * (3 - 1)
    EXPECT_NEAR(sb.Get(StatId::Life), 695.0, 1e-9);       // + afixo do elmo
    EXPECT_NEAR(sb.Get(StatId::Armor), 60.0 + 5.0, 1e-9); // 50 + 5*2 da classe, + implícito 5 do elmo
    EXPECT_NEAR(sb.GetBase(StatId::DamageTaken), 1.0, 1e-12);
    // Ordem de inserção: classe (bases, sem mods) -> item por slot (main_hand antes de head) -> únicos.
    const auto& mods = sb.Modifiers();
    ASSERT_TRUE(mods.size() == 3);
    EXPECT_EQ(mods[0].source, std::string("item:2"));     // implícito do elmo (armadura)
    EXPECT_EQ(mods[1].source, std::string("item:2"));     // afixo do elmo
    EXPECT_EQ(mods[2].source, std::string("item:3"));     // mod fixo do Único, depois de todos os itens
    EXPECT_EQ(mods[2].requiredTags, Mask(Tag::Melee));
    // Mesmo personagem, mesmo resultado.
    StatBlock sb2;
    ASSERT_TRUE(BuildStatBlock(db, c, sb2));
    EXPECT_NEAR(sb2.Get(StatId::Life), sb.Get(StatId::Life), 0.0);
}

TEST(character_build_statblock_reports_missing_ids) {
    const ContentDB& db = tu::RichDb();
    StatBlock sb;
    std::string err;
    CharacterState c = tu::MakeWarrior(db);
    c.classId = "class.ghost";
    EXPECT_FALSE(BuildStatBlock(db, c, sb, &err));
    EXPECT_TRUE(err.find("class.ghost") != std::string::npos);
    c = tu::MakeWarrior(db);
    c.skills[0].skillId = "skill.warrior.ghost";
    EXPECT_FALSE(BuildStatBlock(db, c, sb, &err));
    c = tu::MakeWarrior(db);
    c.skillBar[3] = "skill.warrior.ghost";
    EXPECT_FALSE(BuildStatBlock(db, c, sb, &err));
    c = tu::MakeWarrior(db);
    c.equipment[static_cast<std::size_t>(ItemSlot::MainHand)]->baseId = "item_base.ghost";
    EXPECT_FALSE(BuildStatBlock(db, c, sb, &err));
    c = tu::MakeWarrior(db);
    c.equipment[static_cast<std::size_t>(ItemSlot::MainHand)]->affixes = {{"affix.ghost", 1.0}};
    EXPECT_FALSE(BuildStatBlock(db, c, sb, &err));
    c = tu::MakeWarrior(db);  // espada no slot da cabeça
    c.equipment[static_cast<std::size_t>(ItemSlot::Head)] = c.equipment[static_cast<std::size_t>(ItemSlot::MainHand)];
    EXPECT_FALSE(BuildStatBlock(db, c, sb, &err));
    EXPECT_TRUE(err.find("slot") != std::string::npos);
    c = tu::MakeWarrior(db);
    c.equipment[static_cast<std::size_t>(ItemSlot::MainHand)]->uniqueId = "unique.ghost";
    EXPECT_FALSE(BuildStatBlock(db, c, sb, &err));
}

TEST(character_idle_compatibility) {
    const ContentDB& db = tu::RichDb();
    std::vector<ContentId> blocking;
    CharacterState c = tu::MakeWarrior(db);
    EXPECT_TRUE(IsIdleCompatible(db, c, &blocking));
    EXPECT_TRUE(blocking.empty());
    c.skillBar[3] = "skill.warrior.unsupported_roar";
    EXPECT_FALSE(IsIdleCompatible(db, c, &blocking));
    ASSERT_TRUE(blocking.size() == 1);
    EXPECT_EQ(blocking[0], std::string("skill.warrior.unsupported_roar"));
    // Único sem perfil testado bloqueia; com idleSupported libera.
    c = tu::MakeWarrior(db);
    ItemInstance blade;
    blade.uid = 5;
    blade.baseId = "item_base.iron_sword";
    blade.rarity = Rarity::Unique;
    blade.uniqueId = "unique.bell_warden_blade";
    c.equipment[static_cast<std::size_t>(ItemSlot::MainHand)] = blade;
    EXPECT_FALSE(IsIdleCompatible(db, c, &blocking));
    EXPECT_EQ(blocking[0], std::string("unique.bell_warden_blade"));
    c = tu::MakeWarrior(db);
    ItemInstance helm;
    helm.uid = 6;
    helm.baseId = "item_base.bone_helm";
    helm.rarity = Rarity::Unique;
    helm.uniqueId = "unique.idle_ready_helm";
    c.equipment[static_cast<std::size_t>(ItemSlot::Head)] = helm;
    EXPECT_TRUE(IsIdleCompatible(db, c, nullptr));
}

// ---------------------------------------------------------------------------
namespace {

// 3 desvios-padrão de uma contagem binomial.
double Sigma3(double n, double p) { return 3.0 * std::sqrt(n * p * (1.0 - p)); }

ContentDB MakeGoldDb(std::int64_t minAmount, std::int64_t maxAmount, int minArea = 1, int maxArea = 999) {
    ContentDB db;
    db.SetContentVersion(1);
    LootTableData t;
    t.id = "loot.test.gold";
    LootEntry e;
    e.kind = LootEntryKind::Stack;
    e.refId = "currency.gold";
    e.minAmount = minAmount;
    e.maxAmount = maxAmount;
    e.minAreaLevel = minArea;
    e.maxAreaLevel = maxArea;
    t.entries.push_back(e);
    db.Add(t);
    return db;
}

}  // namespace

TEST(loot_rf25_pick_weighted_matches_weights) {
    const std::vector<double> w = {1.0, 2.0, 3.0, 4.0, 0.0};
    Pcg32 rng(31337);
    std::array<int, 5> counts{};
    const int n = 100000;
    for (int i = 0; i < n; ++i) {
        const int k = PickWeighted(w, rng);
        ASSERT_TRUE(k >= 0 && k < 5);
        ++counts[static_cast<std::size_t>(k)];
    }
    for (int i = 0; i < 4; ++i) {
        const double p = w[static_cast<std::size_t>(i)] / 10.0;
        EXPECT_NEAR(counts[static_cast<std::size_t>(i)], p * n, Sigma3(n, p));
    }
    EXPECT_EQ(counts[4], 0);  // peso 0 nunca sai
    Pcg32 a(1), b(1);
    EXPECT_EQ(PickWeighted({0.0, -1.0}, a), -1);
    b.NextU32();
    EXPECT_EQ(a.State(), b.State());  // consome exatamente 1 número mesmo sem soma
    EXPECT_EQ(PickWeighted({}, a), -1);
}

TEST(loot_rf25_table_frequencies_match_weights) {
    const ContentDB& db = tu::RichDb();
    const LootTableData* t = db.FindLootTable("loot.crypt.common");
    ASSERT_TRUE(t != nullptr);
    LootContext ctx;
    ctx.mode = LootMode::Manual;
    ctx.areaLevel = 4;
    Pcg32 rng(2025);
    const int n = 100000;
    std::map<std::string, int> counts;
    for (int i = 0; i < n; ++i) {
        const LootDrop d = RollLootTable(db, *t, ctx, rng);
        for (const ItemInstance& it : d.items) ++counts[it.baseId];
        for (const StackEntry& s : d.stacks) ++counts[s.id];
        if (d.items.empty() && d.stacks.empty()) ++counts["nothing"];
    }
    const double total = 6 + 6 + 80 + 20;
    EXPECT_NEAR(counts["item_base.bone_helm"], n * 6 / total, Sigma3(n, 6 / total));
    EXPECT_NEAR(counts["item_base.leather_vest"], n * 6 / total, Sigma3(n, 6 / total));
    EXPECT_NEAR(counts["currency.gold"], n * 80 / total, Sigma3(n, 80 / total));
    EXPECT_NEAR(counts["nothing"], n * 20 / total, Sigma3(n, 20 / total));
}

TEST(loot_rf26_affix_rules_over_many_items) {
    const ContentDB& db = tu::RichDb();
    const ItemBaseData* vest = db.FindItemBase("item_base.leather_vest");
    const ItemBaseData* sword = db.FindItemBase("item_base.iron_sword");
    ASSERT_TRUE(vest != nullptr && sword != nullptr);
    Pcg32 rng(777);
    const int n = 50000;
    for (int i = 0; i < n; ++i) {
        const Rarity r = (i % 2) ? Rarity::Rare : Rarity::Magic;
        const int ilvl = (i % 3 == 0) ? 12 : 4;
        const ItemBaseData& base = (i % 5 == 0) ? *sword : *vest;
        const std::vector<RolledAffix> a = RollAffixes(db, base, r, ilvl, rng);
        const std::size_t maxCount = r == Rarity::Magic ? 2 : 4;
        if (a.size() > maxCount) { FAIL("afixos demais"); return; }
        if (r == Rarity::Magic && a.empty()) { FAIL("magico sem afixo"); return; }
        std::map<std::string, int> seen, groups;
        int prefixes = 0, suffixes = 0;
        bool sawSuffix = false;
        for (const RolledAffix& ra : a) {
            const AffixData* ad = db.FindAffix(ra.affixId);
            if (ad == nullptr) { FAIL("afixo inexistente"); return; }
            if (++seen[ra.affixId] > 1) { FAIL("afixo repetido"); return; }
            if (!ad->group.empty() && ++groups[ad->group] > 1) { FAIL("grupo repetido"); return; }
            if (ra.value < ad->minValue || ra.value > ad->maxValue) { FAIL("valor fora da faixa"); return; }
            if (ad->minItemLevel > ilvl) { FAIL("afixo de nivel alto em item baixo"); return; }
            if (!ad->allowedSlots.empty() &&
                std::find(ad->allowedSlots.begin(), ad->allowedSlots.end(), base.slot) == ad->allowedSlots.end()) {
                FAIL("afixo em slot nao permitido");
                return;
            }
            if (ad->kind == AffixKind::Prefix) {
                ++prefixes;
                if (sawSuffix) { FAIL("prefixo depois de sufixo"); return; }
            } else {
                ++suffixes;
                sawSuffix = true;
            }
            if (ad->minValue == std::floor(ad->minValue) && ad->maxValue == std::floor(ad->maxValue) &&
                ra.value != std::floor(ra.value)) {
                FAIL("faixa inteira devia sortear inteiro");
                return;
            }
        }
        if (prefixes > 2 || suffixes > 2) { FAIL("mais de 2 prefixos ou 2 sufixos"); return; }
    }
    // Normal e Único não têm afixos rolados.
    EXPECT_TRUE(RollAffixes(db, *vest, Rarity::Normal, 5, rng).empty());
    EXPECT_TRUE(RollAffixes(db, *vest, Rarity::Unique, 5, rng).empty());
    // Afixo de nível 10 só em item de nível >= 10.
    bool sawHigh = false;
    for (int i = 0; i < 2000; ++i) {
        for (const RolledAffix& ra : RollAffixes(db, *vest, Rarity::Rare, 4, rng))
            if (ra.affixId == "affix.high_life") { FAIL("high_life em item nivel 4"); return; }
        for (const RolledAffix& ra : RollAffixes(db, *vest, Rarity::Rare, 12, rng))
            if (ra.affixId == "affix.high_life") sawHigh = true;
    }
    EXPECT_TRUE(sawHigh);
}

TEST(loot_rf27_no_uniques_outside_boss_tables) {
    const ContentDB& db = tu::RichDb();
    const LootTableData* t = db.FindLootTable("loot.crypt.common");
    ASSERT_TRUE(t != nullptr);
#ifdef NDEBUG
    const int n = 1000000;
#else
    const int n = 200000;
#endif
    LootContext ctx;
    ctx.mode = LootMode::Manual;
    ctx.areaLevel = 4;
    Pcg32 rng(4242);
    int uniques = 0;
    for (int i = 0; i < n; ++i) {
        const LootDrop d = RollLootTable(db, *t, ctx, rng);
        for (const ItemInstance& it : d.items)
            if (it.rarity == Rarity::Unique || !it.uniqueId.empty()) ++uniques;
    }
    EXPECT_EQ(uniques, 0);
}

TEST(loot_idle_never_drops_top_tier) {
    const ContentDB& db = tu::RichDb();
    const LootTableData* boss = db.FindLootTable("loot.crypt.guardian");
    ASSERT_TRUE(boss != nullptr);
    LootContext idle;
    idle.mode = LootMode::Idle;
    idle.areaLevel = 4;
    Pcg32 rng(11);
    int items = 0;
    for (int i = 0; i < 50000; ++i) {
        const LootDrop d = RollLootTable(db, *boss, idle, rng);
        for (const ItemInstance& it : d.items) {
            ++items;
            if (it.rarity == Rarity::Unique || !it.uniqueId.empty()) { FAIL("unico no idle"); return; }
        }
        for (const StackEntry& s : d.stacks) {
            if (s.id.rfind("book.", 0) == 0 || s.id.rfind("map_stone.", 0) == 0 || s.id == "material.echo_fragment") {
                FAIL("item de topo no idle: " + s.id);
                return;
            }
        }
    }
    EXPECT_TRUE(items > 0);
    // No manual, a mesma tabela entrega Únicos, livros, pedras e fragmentos.
    LootContext manual = idle;
    manual.mode = LootMode::Manual;
    int uniques = 0, books = 0, stones = 0, echoes = 0;
    for (int i = 0; i < 50000; ++i) {
        const LootDrop d = RollLootTable(db, *boss, manual, rng);
        for (const ItemInstance& it : d.items) uniques += (it.rarity == Rarity::Unique && it.uniqueId == "unique.bell_warden_blade") ? 1 : 0;
        for (const StackEntry& s : d.stacks) {
            books += s.id == "book.spec.warrior_bastion" ? 1 : 0;
            stones += s.id == "map_stone.ossuary_t1" ? 1 : 0;
            echoes += s.id == "material.echo_fragment" ? 1 : 0;
        }
    }
    EXPECT_TRUE(uniques > 0 && books > 0 && stones > 0 && echoes > 0);
}

TEST(loot_rare_cap_and_rare_rate_idle_is_half_of_manual) {
    const ContentDB& db = tu::RichDb();
    const LootTableData* t = db.FindLootTable("loot.crypt.common");
    ASSERT_TRUE(t != nullptr);
    // Teto: 3 Raros já obtidos e teto 4 => no máximo 1 nova rolagem Rara por chamada com 100 sorteios.
    LootContext ctx;
    ctx.mode = LootMode::Idle;
    ctx.areaLevel = 4;
    ctx.maxRares = 4;
    ctx.raresAlreadyDropped = 3;
    Pcg32 rng(5);
    LootDrop total;
    for (int i = 0; i < 5000; ++i) {
        LootContext c2 = ctx;
        c2.raresAlreadyDropped = 3 + total.raresDropped;
        LootDrop d = RollLootTable(db, *t, c2, rng);
        total.raresDropped += d.raresDropped;
        for (const ItemInstance& it : d.items) total.items.push_back(it);
    }
    EXPECT_EQ(total.raresDropped, 1);
    int rares = 0, magic = 0;
    for (const ItemInstance& it : total.items) {
        rares += it.rarity == Rarity::Rare ? 1 : 0;
        magic += it.rarity == Rarity::Magic ? 1 : 0;
    }
    EXPECT_EQ(rares, 1);
    EXPECT_TRUE(magic > 50);  // o excedente virou Mágico
    ctx.maxRares = 0;
    ctx.raresAlreadyDropped = 0;
    for (int i = 0; i < 3000; ++i) EXPECT_EQ(RollLootTable(db, *t, ctx, rng).raresDropped, 0);

    // Taxa de Raro por item: idle = base; manual = peso x2 => razão ~0,5.
    auto rareRate = [&](LootMode mode) {
        LootContext c;
        c.mode = mode;
        c.areaLevel = 4;
        Pcg32 r(808);
        int items = 0, rare = 0;
        for (int i = 0; i < 400000; ++i) {
            const LootDrop d = RollLootTable(db, *t, c, r);
            for (const ItemInstance& it : d.items) {
                ++items;
                rare += it.rarity == Rarity::Rare ? 1 : 0;
            }
        }
        return static_cast<double>(rare) / static_cast<double>(items);
    };
    const double idle = rareRate(LootMode::Idle), manual = rareRate(LootMode::Manual);
    EXPECT_NEAR(idle / manual, 0.5, 0.05);
}

TEST(loot_fervor_multiplies_gold_by_1_25_exactly) {
    ContentDB db = MakeGoldDb(8, 8);
    const LootTableData* t = db.FindLootTable("loot.test.gold");
    ASSERT_TRUE(t != nullptr);
    Pcg32 rng(1);
    LootContext idle;
    idle.mode = LootMode::Idle;
    LootContext manual;
    manual.mode = LootMode::Manual;
    EXPECT_EQ(RollLootTable(db, *t, idle, rng).stacks[0].amount, static_cast<std::int64_t>(8));
    EXPECT_EQ(RollLootTable(db, *t, manual, rng).stacks[0].amount, static_cast<std::int64_t>(10));  // 8 x 1,25
    idle.quantityMult = 1.5;  // Pedra de Rota
    EXPECT_EQ(RollLootTable(db, *t, idle, rng).stacks[0].amount, static_cast<std::int64_t>(12));
    idle.quantityMult = 0.01;  // mínimo 1
    EXPECT_EQ(RollLootTable(db, *t, idle, rng).stacks[0].amount, static_cast<std::int64_t>(1));
}

TEST(loot_area_level_filter_uid_and_modifiers) {
    ContentDB db = MakeGoldDb(1, 1, 10, 20);
    const LootTableData* t = db.FindLootTable("loot.test.gold");
    LootContext ctx;
    ctx.areaLevel = 5;
    Pcg32 rng(3);
    for (int i = 0; i < 100; ++i) {
        const LootDrop d = RollLootTable(db, *t, ctx, rng);
        if (!d.stacks.empty() || !d.items.empty()) { FAIL("entrada fora do nivel de area"); return; }
    }
    ctx.areaLevel = 10;
    EXPECT_EQ(RollLootTable(db, *t, ctx, rng).stacks.size(), static_cast<std::size_t>(1));
    ctx.areaLevel = 21;
    EXPECT_TRUE(RollLootTable(db, *t, ctx, rng).stacks.empty());

    // UIDs sequenciais vindos do contador do chamador.
    const ContentDB& rich = tu::RichDb();
    std::uint64_t uid = 100;
    LootContext c2;
    c2.areaLevel = 4;
    c2.nextItemUid = &uid;
    const LootTableData* common = rich.FindLootTable("loot.crypt.common");
    int made = 0;
    for (int i = 0; i < 200; ++i) {
        const LootDrop d = RollLootTable(rich, *common, c2, rng);
        for (const ItemInstance& it : d.items) {
            if (it.uid != 100 + static_cast<std::uint64_t>(made)) { FAIL("uid fora de sequencia"); return; }
            ++made;
        }
    }
    EXPECT_TRUE(made > 0);
    EXPECT_EQ(uid, 100 + static_cast<std::uint64_t>(made));

    ItemInstance item;
    item.uid = 9;
    item.baseId = "item_base.bone_helm";
    item.affixes = {{"affix.life_flat", 12.0}, {"affix.fire_res", 0.1}};
    const std::vector<Modifier> mods = ItemModifiers(rich, item);
    ASSERT_TRUE(mods.size() == 3);
    EXPECT_ENUM_EQ(mods[0].stat, StatId::Armor);  // implícito primeiro
    EXPECT_ENUM_EQ(mods[1].stat, StatId::Life);
    EXPECT_NEAR(mods[1].value, 12.0, 1e-12);
    EXPECT_EQ(mods[2].source, std::string("item:9"));
}
