// Economia do protótipo (docs/16 seção 11): Vendedor, recompra, Frasco de Recarga e Encantador (craft.h, vendor.h).
// Números vêm de rules.csv, craft_costs.csv e vendor_stock.csv do fixture rico; nada de balanceamento é fixado aqui,
// exceto as cartas de teste construídas sobre o que o fixture declara.
#include <algorithm>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <memory>
#include <set>

#include "shatter/craft.h"
#include "shatter/vendor.h"
#include "test_util.h"

using namespace shatter;

#define ASSERT_ENUM_EQ_OK(expr) ASSERT_TRUE((expr) == CraftResult::Ok)
#define ASSERT_ENUM_EQ_OK2(expr) ASSERT_TRUE((expr) == CraftResult::Ok)

namespace {

using Overrides = std::vector<std::pair<std::string, std::string>>;

std::unique_ptr<ContentDB> RichWith(const Overrides& ov) {
    auto db = std::make_unique<ContentDB>();
    for (const char* t : tu::kTableNames) {
        const std::string path = tu::RichDir() + "/" + t;
        if (tu::IsOptionalTable(t) && !std::filesystem::exists(std::filesystem::u8path(path))) continue;
        std::string text = tu::ReadFile(path);
        for (const auto& o : ov)
            if (o.first == t) text = o.second;
        db->LoadTableCsv(t, text);
    }
    db->Finalize();
    return db;
}

std::string RulesWith(const std::string& key, const std::string& value) {
    std::string text = tu::ReadFile(tu::RichDir() + "/rules.csv");
    const std::size_t at = text.find("\n" + key + ",");
    if (at == std::string::npos) FAIL("regra ausente no fixture: " + key);
    const std::size_t eol = text.find_first_of("\r\n", at + 1);
    text.replace(at + 1, eol - at - 1, key + "," + value);
    return text;
}

ItemInstance Item(std::uint64_t uid, const char* base, Rarity r, int level = 1, std::vector<RolledAffix> affixes = {}) {
    ItemInstance it;
    it.uid = uid;
    it.baseId = base;
    it.rarity = r;
    it.itemLevel = level;
    it.affixes = std::move(affixes);
    return it;
}

RolledAffix Aff(const char* id, double value, std::uint8_t polish = 0) {
    RolledAffix a;
    a.affixId = id;
    a.value = value;
    a.polish = polish;
    return a;
}

void SetCur(SaveData& s, const char* id, std::int64_t amount) {
    for (StackEntry& e : s.currencies) {
        if (e.id == id) { e.amount = amount; return; }
    }
    s.currencies.push_back(StackEntry{id, amount});
}

SaveData NewSave(const ContentDB& db, std::int64_t gold = 100000, std::int64_t shards = 100000) {
    SaveData s;
    s.contentVersion = db.ContentVersion();
    s.characters.push_back(tu::MakeWarrior(db, 3));
    s.nextItemUid = 1000;
    SetCur(s, kGoldId, gold);
    SetCur(s, kShardsId, shards);
    return s;
}

const ItemInstance* FindBackpack(const SaveData& s, std::uint64_t uid) {
    for (const ItemInstance& it : s.characters[0].backpack)
        if (it.uid == uid) return &it;
    return nullptr;
}

std::string Bytes(const SaveData& s) { return SerializeJson(s, false); }

// As regras de "nunca pode acontecer" (docs/16 11.5) que dependem só do item depois de uma operação.
bool ItemIsValid(const ContentDB& db, const ItemInstance& it, std::string* why) {
    auto bad = [&](const std::string& m) { if (why) *why = m; return false; };
    const ItemBaseData* base = db.FindItemBase(it.baseId);
    if (base == nullptr) return bad("base");
    if (it.rarity == Rarity::Unique || !it.uniqueId.empty()) return bad("unico");
    const std::size_t maxAff = it.rarity == Rarity::Magic ? 2 : (it.rarity == Rarity::Rare ? 4 : 0);
    if (it.affixes.size() > maxAff) return bad("afixos demais");
    if (it.rarity == Rarity::Magic && it.affixes.empty()) return bad("magico sem afixo");
    int prefixes = 0, suffixes = 0;
    std::set<std::string> ids, groups;
    for (const RolledAffix& r : it.affixes) {
        const AffixData* a = db.FindAffix(r.affixId);
        if (a == nullptr) return bad("afixo desconhecido");
        if (!ids.insert(a->id).second) return bad("afixo repetido");
        if (!a->group.empty() && !groups.insert(a->group).second) return bad("grupo repetido");
        if (!a->allowedSlots.empty() &&
            std::find(a->allowedSlots.begin(), a->allowedSlots.end(), base->slot) == a->allowedSlots.end())
            return bad("slot");
        if (a->minItemLevel > it.itemLevel) return bad("nivel");
        if (r.value < a->minValue - 1e-9 || r.value > a->maxValue + 1e-9) return bad("valor fora da faixa");
        if (r.polish > db.Rules().polishMaxSteps) return bad("polish");
        if (a->kind == AffixKind::Prefix) ++prefixes; else ++suffixes;
    }
    if (prefixes > 2 || suffixes > 2) return bad("2 prefixos + 2 sufixos");
    // prefixos antes de sufixos
    bool seenSuffix = false;
    for (const RolledAffix& r : it.affixes) {
        const bool pre = db.FindAffix(r.affixId)->kind == AffixKind::Prefix;
        if (!pre) seenSuffix = true;
        else if (seenSuffix) return bad("ordem prefixo/sufixo");
    }
    return true;
}

}  // namespace

// ---------------------------------------------------------------------------------------------------------------------
// Dados
// ---------------------------------------------------------------------------------------------------------------------
TEST(economy_data_rules_tables_and_lookups_come_from_csv) {
    const ContentDB& db = tu::RichDb();
    ASSERT_TRUE(db.Errors().empty());
    const RulesConstants& r = db.Rules();
    EXPECT_EQ(r.vendorBuybackSlots, 10);
    EXPECT_NEAR(r.vendorBuybackPriceFactor, 1.25, 1e-12);
    EXPECT_EQ(r.refillFlaskCarryCap, 3);
    EXPECT_EQ(r.addAffixCandidates, 3);
    EXPECT_EQ(r.polishMaxSteps, 3);
    EXPECT_NEAR(r.polishStepFraction, 0.25, 1e-12);
    EXPECT_EQ(r.dismantleShards[0], 2);
    EXPECT_EQ(r.dismantleShards[2], 12);
    EXPECT_EQ(db.CraftCosts().size(), static_cast<std::size_t>(8));
    ASSERT_TRUE(db.FindCraftCost(CraftOp::Refine, Rarity::Normal, 0) != nullptr);
    EXPECT_TRUE(db.FindCraftCost(CraftOp::Refine, Rarity::Magic, 0) == nullptr);
    const CraftCostData* p2 = db.FindCraftCost(CraftOp::Polish, Rarity::Rare, 2);  // rarity = any
    ASSERT_TRUE(p2 != nullptr);
    EXPECT_EQ(p2->goldCost, 120);
    const VendorStockData* flask = db.FindVendorStock("vendor.refill_flask");
    ASSERT_TRUE(flask != nullptr);
    EXPECT_EQ(flask->refId, std::string("consumable.refill_flask"));
    EXPECT_EQ(flask->priceGold, 50);
    EXPECT_TRUE(db.FindVendorStockByRef("consumable.refill_flask") == flask);
}

TEST(economy_data_validation_errors_are_typed) {
    std::string costs = tu::ReadFile(tu::RichDir() + "/craft_costs.csv");
    // Operação sem nenhuma linha (polish passo 3).
    {
        std::string t = tu::Replace(costs, "craft.polish.3,polish,any,3,240,0\n", "");
        const auto db = RichWith({{"craft_costs.csv", t}});
        bool found = false;
        for (const ContentError& e : db->Errors()) found = found || e.message.find("E_RULE") == 0;
        EXPECT_TRUE(found);
    }
    {  // (op, rarity, step) repetido
        const auto db = RichWith({{"craft_costs.csv", costs + "craft.polish.9,polish,any,1,1,1\n"}});
        bool found = false;
        for (const ContentError& e : db->Errors()) found = found || e.message.find("E_DUP_ID") == 0;
        EXPECT_TRUE(found);
    }
    {  // op inválido, raridade inválida (Único nunca tem custo)
        const auto a = RichWith({{"craft_costs.csv", tu::Replace(costs, "refine,normal", "forge,normal")}});
        const auto b = RichWith({{"craft_costs.csv", tu::Replace(costs, "refine,normal", "refine,unique")}});
        EXPECT_FALSE(a->Errors().empty());
        EXPECT_FALSE(b->Errors().empty());
    }
    {  // o frasco no estoque tem que bater com a regra
        const auto db = RichWith({{"vendor_stock.csv", tu::Replace(tu::ReadFile(tu::RichDir() + "/vendor_stock.csv"), "stack,50,3", "stack,50,5")}});
        bool found = false;
        for (const ContentError& e : db->Errors()) found = found || e.message.find("E_RULE") == 0;
        EXPECT_TRUE(found);
    }
    {  // chave obrigatória ausente
        std::string text = tu::ReadFile(tu::RichDir() + "/rules.csv");
        const std::size_t at = text.find("\nreforge_mult_cap,");
        ASSERT_TRUE(at != std::string::npos);
        text.erase(at + 1, text.find_first_of("\r\n", at + 1) - at);
        const auto db = RichWith({{"rules.csv", text}});
        EXPECT_FALSE(db->Errors().empty());
    }
    {  // sem as tabelas opcionais, o conteúdo continua válido e o Encantador recusa por falta de preço
        auto db = std::make_unique<ContentDB>();
        for (const char* t : tu::kTableNames) {
            if (std::string(t) == "craft_costs.csv" || std::string(t) == "vendor_stock.csv") continue;
            const std::string path = tu::RichDir() + "/" + t;
            if (tu::IsOptionalTable(t) && !std::filesystem::exists(std::filesystem::u8path(path))) continue;
            db->LoadTableCsv(t, tu::ReadFile(path));
        }
        EXPECT_TRUE(db->Finalize());
        SaveData s = NewSave(*db);
        s.characters[0].backpack.push_back(Item(10, "item_base.iron_sword", Rarity::Normal));
        EXPECT_ENUM_EQ(CraftRefine(*db, s, 0, 10), CraftResult::UnknownContent);
    }
}

// ---------------------------------------------------------------------------------------------------------------------
// RNG e determinismo
// ---------------------------------------------------------------------------------------------------------------------
TEST(economy_rng_crafting_stream_is_pure_per_item_step_and_operation) {
    EXPECT_EQ(static_cast<int>(RngStream::Crafting), 4);
    Pcg32 a = CraftRng(77, 10, 0, CraftOp::Refine), b = CraftRng(77, 10, 0, CraftOp::Refine);
    for (int i = 0; i < 8; ++i) EXPECT_EQ(a.NextU32(), b.NextU32());
    auto first = [](std::uint64_t seed, std::uint64_t uid, std::uint16_t steps, CraftOp op) { return CraftRng(seed, uid, steps, op).NextU64(); };
    const std::uint64_t base = first(77, 10, 0, CraftOp::Refine);
    EXPECT_NE(base, first(78, 10, 0, CraftOp::Refine));    // outro craft_seed
    EXPECT_NE(base, first(77, 11, 0, CraftOp::Refine));    // outra peça
    EXPECT_NE(base, first(77, 10, 1, CraftOp::Refine));    // outro passo da peça
    EXPECT_NE(base, first(77, 10, 0, CraftOp::Reforge));   // outra operação
    // Fluxo separado de Loot e Combate com a mesma semente.
    EXPECT_NE(DeriveSeed(5, RngStream::Crafting, 1), DeriveSeed(5, RngStream::Loot, 1));
    EXPECT_NE(DeriveSeed(5, RngStream::Crafting, 1), DeriveSeed(5, RngStream::Combat, 1));
}

TEST(economy_craft_seed_effective_value_does_not_change_when_it_is_stored) {
    const ContentDB& db = tu::RichDb();
    SaveData s = NewSave(db);
    EXPECT_EQ(s.craftSeed, static_cast<std::uint64_t>(0));
    const std::uint64_t eff = EffectiveCraftSeed(s);
    EXPECT_TRUE(eff != 0);
    s.characters[0].backpack.push_back(Item(10, "item_base.iron_sword", Rarity::Normal));
    SaveData t = s;
    t.craftSeed = eff;  // o que EnsureCraftSeed grava
    EXPECT_ENUM_EQ(CraftRefine(db, s, 0, 10), CraftResult::Ok);
    EXPECT_ENUM_EQ(CraftRefine(db, t, 0, 10), CraftResult::Ok);
    EXPECT_EQ(s.craftSeed, eff);                                  // gravado na primeira operação
    EXPECT_EQ(FindBackpack(s, 10)->affixes.size(), FindBackpack(t, 10)->affixes.size());
    EXPECT_EQ(Bytes(s), Bytes(t));                                // mesmo resultado, byte a byte
    SaveData other = NewSave(db);
    other.characters[0].name = "Outra";
    EXPECT_NE(EffectiveCraftSeed(other), eff);
}

TEST(economy_same_save_same_operation_same_result_and_reload_does_not_change_the_roll) {
    const ContentDB& db = tu::RichDb();
    SaveData s = NewSave(db);
    s.characters[0].backpack.push_back(Item(10, "item_base.leather_vest", Rarity::Magic, 5, {Aff("affix.life_flat", 12)}));
    s.characters[0].backpack.push_back(Item(11, "item_base.iron_sword", Rarity::Normal, 5));
    for (CraftOp op : {CraftOp::Reforge, CraftOp::Add, CraftOp::Polish}) {
        SaveData a = s, b = s;
        const CraftPlan pa = PlanCraft(db, a, 0, 10, op, op == CraftOp::Add ? 0 : -1 + (op == CraftOp::Polish ? 1 : 0));
        const CraftPlan pb = PlanCraft(db, b, 0, 10, op, op == CraftOp::Add ? 0 : -1 + (op == CraftOp::Polish ? 1 : 0));
        EXPECT_ENUM_EQ(pa.result, CraftResult::Ok);
        CommitCraft(a, 0, pa);
        CommitCraft(b, 0, pb);
        EXPECT_EQ(Bytes(a), Bytes(b));
    }
    // "Salvar e recarregar" antes de confirmar: o sorteio é o mesmo.
    SaveData loaded;
    ASSERT_TRUE(ParseJson(SerializeJson(s, true), loaded) == LoadStatus::Ok);
    SaveData direct = s;
    EXPECT_ENUM_EQ(CraftReforge(db, direct, 0, 10, -1), CraftResult::Ok);
    EXPECT_ENUM_EQ(CraftReforge(db, loaded, 0, 10, -1), CraftResult::Ok);
    EXPECT_EQ(Bytes(direct), Bytes(loaded));
    // Operar em outra peça não muda o resultado desta.
    SaveData withOther = s;
    EXPECT_ENUM_EQ(CraftRefine(db, withOther, 0, 11), CraftResult::Ok);
    SaveData without = s;
    EXPECT_ENUM_EQ(CraftReforge(db, withOther, 0, 10, -1), CraftResult::Ok);
    EXPECT_ENUM_EQ(CraftReforge(db, without, 0, 10, -1), CraftResult::Ok);
    EXPECT_EQ(json::Serialize(ItemToJson(*FindBackpack(withOther, 10)), false),
              json::Serialize(ItemToJson(*FindBackpack(without, 10)), false));
}

// ---------------------------------------------------------------------------------------------------------------------
// Refinar
// ---------------------------------------------------------------------------------------------------------------------
TEST(economy_refine_normal_becomes_magic_with_one_or_two_valid_affixes_and_pays) {
    const ContentDB& db = tu::RichDb();
    const CraftCostData* row = db.FindCraftCost(CraftOp::Refine, Rarity::Normal, 0);
    ASSERT_TRUE(row != nullptr);
    int seen[3] = {0, 0, 0};
    for (std::uint64_t uid = 10; uid < 210; ++uid) {
        SaveData s = NewSave(db, 1000, 1000);
        const char* base = uid % 3 == 0 ? "item_base.iron_sword" : (uid % 3 == 1 ? "item_base.leather_vest" : "item_base.bone_helm");
        s.characters[0].backpack.push_back(Item(uid, base, Rarity::Normal, 1));
        CraftPlan plan;
        ASSERT_ENUM_EQ_OK(CraftRefine(db, s, 0, uid, &plan));
        const ItemInstance* it = FindBackpack(s, uid);
        ASSERT_TRUE(it != nullptr);
        EXPECT_ENUM_EQ(it->rarity, Rarity::Magic);
        EXPECT_TRUE(it->affixes.size() == 1 || it->affixes.size() == 2);
        ++seen[it->affixes.size()];
        std::string why;
        EXPECT_TRUE(ItemIsValid(db, *it, &why));
        EXPECT_EQ(it->uid, uid);
        EXPECT_EQ(it->baseId, std::string(base));
        EXPECT_EQ(it->itemLevel, 1);
        EXPECT_EQ(it->craftSteps, static_cast<std::uint16_t>(1));
        EXPECT_EQ(CurrencyAmount(s, kGoldId), 1000 - row->goldCost);       // nível 1: sem fator de nível
        EXPECT_EQ(CurrencyAmount(s, kShardsId), 1000 - row->shardCost);
        EXPECT_EQ(plan.gold, row->goldCost);
        EXPECT_EQ(s.craftSeed, EffectiveCraftSeed(s));
    }
    EXPECT_TRUE(seen[1] > 0 && seen[2] > 0);  // as duas quantidades saem
}

TEST(economy_refine_refuses_other_rarities_unique_and_missing_items_without_changing_the_save) {
    const ContentDB& db = tu::RichDb();
    SaveData s = NewSave(db);
    auto& bp = s.characters[0].backpack;
    bp.push_back(Item(10, "item_base.iron_sword", Rarity::Magic, 1, {Aff("affix.melee_dmg", 0.1)}));
    bp.push_back(Item(11, "item_base.iron_sword", Rarity::Rare, 1, {Aff("affix.melee_dmg", 0.1), Aff("affix.crit_chance", 0.03), Aff("affix.scorching", 0.1)}));
    ItemInstance uniq = Item(12, "item_base.iron_sword", Rarity::Unique, 1);
    uniq.uniqueId = "unique.bell_warden_helm";
    bp.push_back(uniq);
    bp.push_back(Item(13, "item_base.iron_sword", Rarity::Normal, 1));
    const std::string before = Bytes(s);
    EXPECT_ENUM_EQ(CraftRefine(db, s, 0, 10), CraftResult::WrongRarity);
    EXPECT_ENUM_EQ(CraftRefine(db, s, 0, 11), CraftResult::WrongRarity);
    EXPECT_ENUM_EQ(CraftRefine(db, s, 0, 12), CraftResult::Unique);
    EXPECT_ENUM_EQ(CraftRefine(db, s, 0, 999), CraftResult::NotFound);
    EXPECT_ENUM_EQ(CraftRefine(db, s, 5, 13), CraftResult::NotFound);  // personagem inexistente
    EXPECT_EQ(Bytes(s), before);
    // Sem Ouro ou sem Lascas: nada muda.
    SetCur(s, kGoldId, 0);
    const std::string poor = Bytes(s);
    EXPECT_ENUM_EQ(CraftRefine(db, s, 0, 13), CraftResult::NoGold);
    EXPECT_EQ(Bytes(s), poor);
    SetCur(s, kGoldId, 100000);
    SetCur(s, kShardsId, 0);
    const std::string noShards = Bytes(s);
    EXPECT_ENUM_EQ(CraftRefine(db, s, 0, 13), CraftResult::NoShards);
    EXPECT_EQ(Bytes(s), noShards);
    // Repetir depois de refinar não cobra de novo (agora é Mágico).
    SetCur(s, kShardsId, 100000);
    EXPECT_ENUM_EQ(CraftRefine(db, s, 0, 13), CraftResult::Ok);
    const std::string after = Bytes(s);
    EXPECT_ENUM_EQ(CraftRefine(db, s, 0, 13), CraftResult::WrongRarity);
    EXPECT_EQ(Bytes(s), after);
}

TEST(economy_cost_scales_with_item_level_rounding_up) {
    const ContentDB& db = tu::RichDb();
    const CraftCostData* row = db.FindCraftCost(CraftOp::Refine, Rarity::Normal, 0);
    SaveData s = NewSave(db);
    s.characters[0].backpack.push_back(Item(10, "item_base.iron_sword", Rarity::Normal, 14));
    const CraftPlan p = PlanCraft(db, s, 0, 10, CraftOp::Refine, 0);
    const double mul = 1.0 + db.Rules().craftCostLevelFactor * 13.0;
    EXPECT_EQ(p.gold, static_cast<std::int64_t>(std::ceil(static_cast<double>(row->goldCost) * mul - 1e-9)));
    EXPECT_EQ(p.shards, static_cast<std::int64_t>(std::ceil(static_cast<double>(row->shardCost) * mul - 1e-9)));
    EXPECT_TRUE(p.gold > row->goldCost);
}

// ---------------------------------------------------------------------------------------------------------------------
// Reforjar
// ---------------------------------------------------------------------------------------------------------------------
TEST(economy_reforge_keeps_count_rarity_and_inscription_and_resets_polish) {
    const ContentDB& db = tu::RichDb();
    for (int round = 0; round < 60; ++round) {
        SaveData s = NewSave(db);
        const std::uint64_t uid = 20 + static_cast<std::uint64_t>(round);
        ItemInstance it = Item(uid, "item_base.leather_vest", Rarity::Rare, 12,
                               {Aff("affix.life_flat", 15, 2), Aff("affix.armor_flat", 9, 1), Aff("affix.fire_res", 0.1, 3), Aff("affix.life_regen", 1.5)});
        it.hasInscription = true;
        s.characters[0].backpack.push_back(it);
        ASSERT_ENUM_EQ_OK(CraftReforge(db, s, 0, uid, -1));
        const ItemInstance* r = FindBackpack(s, uid);
        EXPECT_EQ(r->affixes.size(), static_cast<std::size_t>(4));
        EXPECT_ENUM_EQ(r->rarity, Rarity::Rare);
        EXPECT_TRUE(r->hasInscription);
        for (const RolledAffix& a : r->affixes) EXPECT_EQ(static_cast<int>(a.polish), 0);
        EXPECT_EQ(r->craftSteps, static_cast<std::uint16_t>(1));
        EXPECT_EQ(r->craftReforges, static_cast<std::uint16_t>(1));
        std::string why;
        EXPECT_TRUE(ItemIsValid(db, *r, &why));
    }
}

TEST(economy_reforge_lock_keeps_one_affix_with_value_and_polish_and_doubles_only_shards) {
    const ContentDB& db = tu::RichDb();
    const CraftCostData* row = db.FindCraftCost(CraftOp::Reforge, Rarity::Rare, 0);
    SaveData s = NewSave(db);
    s.characters[0].backpack.push_back(Item(30, "item_base.bone_helm", Rarity::Rare, 1,
        {Aff("affix.life_flat", 17, 2), Aff("affix.armor_flat", 9), Aff("affix.fire_res", 0.1), Aff("affix.life_regen", 1.5)}));
    const CraftPlan quote = PlanCraft(db, s, 0, 30, CraftOp::Reforge, 0);
    EXPECT_EQ(quote.gold, row->goldCost);
    EXPECT_EQ(quote.shardsNoLock, row->shardCost);
    EXPECT_EQ(quote.shardsWithLock, static_cast<std::int64_t>(std::ceil(static_cast<double>(row->shardCost) * db.Rules().reforgeLockCostMult - 1e-9)));
    EXPECT_EQ(quote.shards, quote.shardsWithLock);
    for (int i = 0; i < 20; ++i) {
        SaveData t = s;
        t.characters[0].backpack[0].uid = 30;
        ASSERT_ENUM_EQ_OK(CraftReforge(db, t, 0, 30, 0));
        const ItemInstance* r = FindBackpack(t, 30);
        bool kept = false;
        for (const RolledAffix& a : r->affixes)
            if (a.affixId == "affix.life_flat") { kept = true; EXPECT_NEAR(a.value, 17.0, 1e-12); EXPECT_EQ(static_cast<int>(a.polish), 2); }
        EXPECT_TRUE(kept);
        EXPECT_EQ(r->affixes.size(), static_cast<std::size_t>(4));
        // Mexer em outra peça não desloca nada: avança o passo e repete só para variar o estado.
        s.characters[0].backpack[0].craftSteps = static_cast<std::uint16_t>(i + 1);
    }
    // Índices inválidos e trava desligada.
    const std::string before = Bytes(s);
    EXPECT_ENUM_EQ(CraftReforge(db, s, 0, 30, 4), CraftResult::BadIndex);
    EXPECT_ENUM_EQ(CraftReforge(db, s, 0, 30, -2), CraftResult::BadIndex);
    EXPECT_EQ(Bytes(s), before);
    const auto off = RichWith({{"rules.csv", RulesWith("reforge_lock_max", "0")}});
    SaveData u = NewSave(*off);
    u.characters[0].backpack.push_back(Item(31, "item_base.bone_helm", Rarity::Magic, 1, {Aff("affix.life_flat", 17), Aff("affix.fire_res", 0.1)}));
    EXPECT_ENUM_EQ(CraftReforge(*off, u, 0, 31, 0), CraftResult::BadIndex);
    // Travar o único afixo de um Mágico não faz sentido.
    SaveData v = NewSave(db);
    v.characters[0].backpack.push_back(Item(32, "item_base.bone_helm", Rarity::Magic, 1, {Aff("affix.life_flat", 17)}));
    EXPECT_ENUM_EQ(CraftReforge(db, v, 0, 32, 0), CraftResult::BadIndex);
    EXPECT_ENUM_EQ(CraftReforge(db, v, 0, 32, -1), CraftResult::Ok);
}

TEST(economy_reforge_cost_rises_50_percent_per_reforge_up_to_the_cap) {
    const ContentDB& db = tu::RichDb();
    const CraftCostData* row = db.FindCraftCost(CraftOp::Reforge, Rarity::Magic, 0);
    SaveData s = NewSave(db, 10000000, 10000000);
    s.characters[0].backpack.push_back(Item(40, "item_base.leather_vest", Rarity::Magic, 1, {Aff("affix.life_flat", 12), Aff("affix.fire_res", 0.1)}));
    const double expected[] = {1.0, 1.5, 2.0, 2.5, 3.0, 3.0, 3.0};
    for (const double mult : expected) {
        const std::int64_t gold = CurrencyAmount(s, kGoldId);
        CraftPlan p;
        ASSERT_ENUM_EQ_OK(CraftReforge(db, s, 0, 40, -1, &p));
        EXPECT_EQ(p.gold, static_cast<std::int64_t>(std::ceil(static_cast<double>(row->goldCost) * mult - 1e-9)));
        EXPECT_EQ(gold - CurrencyAmount(s, kGoldId), p.gold);
    }
    EXPECT_EQ(FindBackpack(s, 40)->craftReforges, static_cast<std::uint16_t>(7));
}

TEST(economy_reforge_refuses_normal_and_unique_and_works_on_equipped_and_stash_items) {
    const ContentDB& db = tu::RichDb();
    SaveData s = NewSave(db);
    s.characters[0].backpack.push_back(Item(10, "item_base.iron_sword", Rarity::Normal));
    EXPECT_ENUM_EQ(CraftReforge(db, s, 0, 10, -1), CraftResult::WrongRarity);
    s.stash.push_back(Item(11, "item_base.iron_sword", Rarity::Magic, 1, {Aff("affix.melee_dmg", 0.1)}));
    ASSERT_ENUM_EQ_OK(CraftReforge(db, s, 0, 11, -1));
    EXPECT_EQ(s.stash[0].craftSteps, static_cast<std::uint16_t>(1));
    ItemInstance eq = Item(12, "item_base.bone_helm", Rarity::Magic, 1, {Aff("affix.armor_flat", 8)});
    s.characters[0].equipment[static_cast<std::size_t>(ItemSlot::Head)] = eq;
    ASSERT_ENUM_EQ_OK(CraftReforge(db, s, 0, 12, -1));
    EXPECT_EQ(s.characters[0].equipment[static_cast<std::size_t>(ItemSlot::Head)]->craftSteps, static_cast<std::uint16_t>(1));
    ItemInstance uniq = Item(13, "item_base.bone_helm", Rarity::Unique, 1);
    uniq.uniqueId = "unique.bell_warden_helm";
    s.characters[0].backpack.push_back(uniq);
    EXPECT_ENUM_EQ(CraftReforge(db, s, 0, 13, -1), CraftResult::Unique);
}

// ---------------------------------------------------------------------------------------------------------------------
// Adicionar afixo
// ---------------------------------------------------------------------------------------------------------------------
TEST(economy_add_affix_offers_the_same_valid_candidates_and_choosing_consumes_the_step) {
    const ContentDB& db = tu::RichDb();
    SaveData s = NewSave(db);
    s.characters[0].backpack.push_back(Item(50, "item_base.bone_helm", Rarity::Magic, 1, {Aff("affix.life_flat", 12)}));
    const AffixOffer o1 = OfferAddAffix(db, s, 0, 50);
    const std::string before = Bytes(s);
    const AffixOffer o2 = OfferAddAffix(db, s, 0, 50);
    EXPECT_EQ(Bytes(s), before);  // oferta não altera
    ASSERT_ENUM_EQ_OK2(o1.result);
    EXPECT_TRUE(!o1.candidates.empty() && o1.candidates.size() <= 3);
    ASSERT_EQ(o1.candidates.size(), o2.candidates.size());
    std::set<std::string> ids;
    for (std::size_t i = 0; i < o1.candidates.size(); ++i) {
        EXPECT_EQ(o1.candidates[i].affixId, o2.candidates[i].affixId);
        EXPECT_TRUE(ids.insert(o1.candidates[i].affixId).second);          // sem repetir
        EXPECT_TRUE(o1.candidates[i].affixId != "affix.life_flat");        // o que o item já tem fica de fora
        EXPECT_TRUE(o1.candidates[i].affixId != "affix.high_life");        // mesmo grupo (life) e nível alto
        EXPECT_TRUE(db.FindAffix(o1.candidates[i].affixId)->craftInscription);
    }
    // Fechar o jogo e reabrir: mesmos candidatos.
    SaveData loaded;
    ASSERT_TRUE(ParseJson(SerializeJson(s, true), loaded) == LoadStatus::Ok);
    const AffixOffer o3 = OfferAddAffix(db, loaded, 0, 50);
    ASSERT_EQ(o3.candidates.size(), o1.candidates.size());
    for (std::size_t i = 0; i < o1.candidates.size(); ++i) EXPECT_EQ(o3.candidates[i].affixId, o1.candidates[i].affixId);
    // Escolher o 2º.
    CraftPlan plan;
    ASSERT_ENUM_EQ_OK(CraftAddAffix(db, s, 0, 50, 1, &plan));
    const ItemInstance* it = FindBackpack(s, 50);
    EXPECT_EQ(it->affixes.size(), static_cast<std::size_t>(2));
    EXPECT_TRUE(it->hasInscription);
    EXPECT_EQ(it->craftSteps, static_cast<std::uint16_t>(1));
    EXPECT_EQ(it->affixes[static_cast<std::size_t>(plan.changedAffix)].affixId, o1.candidates[1].affixId);
    std::string why;
    EXPECT_TRUE(ItemIsValid(db, *it, &why));
    const AffixData* chosen = db.FindAffix(o1.candidates[1].affixId);
    EXPECT_TRUE(it->affixes[static_cast<std::size_t>(plan.changedAffix)].value >= chosen->minValue &&
                it->affixes[static_cast<std::size_t>(plan.changedAffix)].value <= chosen->maxValue);
    // 1 por item: nova tentativa recusa (e o Mágico já está no limite de 2).
    const std::string after = Bytes(s);
    EXPECT_ENUM_EQ(CraftAddAffix(db, s, 0, 50, 0), CraftResult::AffixLimit);
    EXPECT_EQ(Bytes(s), after);
}

TEST(economy_add_affix_rules_limits_inscription_candidates_and_indexes) {
    const ContentDB& db = tu::RichDb();
    SaveData s = NewSave(db);
    auto& bp = s.characters[0].backpack;
    bp.push_back(Item(60, "item_base.iron_sword", Rarity::Normal));
    EXPECT_ENUM_EQ(CraftAddAffix(db, s, 0, 60, 0), CraftResult::WrongRarity);
    bp.push_back(Item(61, "item_base.bone_helm", Rarity::Rare, 1,
                      {Aff("affix.life_flat", 12), Aff("affix.armor_flat", 8), Aff("affix.fire_res", 0.1), Aff("affix.life_regen", 1.2)}));
    EXPECT_ENUM_EQ(CraftAddAffix(db, s, 0, 61, 0), CraftResult::AffixLimit);
    ItemInstance inscribed = Item(62, "item_base.iron_sword", Rarity::Rare, 1, {Aff("affix.melee_dmg", 0.1), Aff("affix.crit_chance", 0.03)});
    inscribed.hasInscription = true;
    bp.push_back(inscribed);
    EXPECT_ENUM_EQ(CraftAddAffix(db, s, 0, 62, 0), CraftResult::AlreadyInscribed);
    // Raro de arma com 3 afixos recebe o 4º: sobra um candidato só (a pool de arma tem 4).
    bp.push_back(Item(63, "item_base.iron_sword", Rarity::Rare, 1, {Aff("affix.melee_dmg", 0.1), Aff("affix.crit_chance", 0.03), Aff("affix.scorching", 0.1)}));
    const AffixOffer o = OfferAddAffix(db, s, 0, 63);
    ASSERT_EQ(o.candidates.size(), static_cast<std::size_t>(1));
    EXPECT_EQ(o.candidates[0].affixId, std::string("affix.of_ruin"));
    EXPECT_ENUM_EQ(CraftAddAffix(db, s, 0, 63, 1), CraftResult::BadIndex);
    EXPECT_ENUM_EQ(CraftAddAffix(db, s, 0, 63, -1), CraftResult::BadIndex);
    ASSERT_ENUM_EQ_OK(CraftAddAffix(db, s, 0, 63, 0));
    EXPECT_EQ(FindBackpack(s, 63)->affixes.size(), static_cast<std::size_t>(4));
    // Sem candidato elegível (limite de 2 prefixos no item): Raro de arma com 2 prefixos + 1 sufixo oferece só sufixo;
    // uma base sem afixos craftáveis na posição fica sem oferta.
    bp.push_back(Item(64, "item_base.iron_boots", Rarity::Magic, 1, {Aff("affix.move_speed", 0.06)}));
    const AffixOffer boots = OfferAddAffix(db, s, 0, 64);
    EXPECT_ENUM_EQ(boots.result, CraftResult::NoCandidate);
    EXPECT_TRUE(boots.candidates.empty());
    const std::string before = Bytes(s);
    EXPECT_ENUM_EQ(CraftAddAffix(db, s, 0, 64, 0), CraftResult::NoCandidate);
    EXPECT_EQ(Bytes(s), before);
    // Só afixos com craftInscription = true entram na oferta.
    std::string affixes = tu::ReadFile(tu::RichDir() + "/affixes.csv");
    const auto restricted = RichWith({{"affixes.csv", tu::Replace(affixes, "affix.life_regen,suffix,life_regen,flat,,1,2,1,6,body|head,regen,true", "affix.life_regen,suffix,life_regen,flat,,1,2,1,6,body|head,regen,false")}});
    SaveData t = NewSave(*restricted);
    t.characters[0].backpack.push_back(Item(65, "item_base.bone_helm", Rarity::Magic, 1, {Aff("affix.life_flat", 12)}));
    const AffixOffer restrictedOffer = OfferAddAffix(*restricted, t, 0, 65);
    for (const AffixCandidate& c : restrictedOffer.candidates) EXPECT_TRUE(c.affixId != "affix.life_regen");
}

// ---------------------------------------------------------------------------------------------------------------------
// Lapidar
// ---------------------------------------------------------------------------------------------------------------------
TEST(economy_polish_raises_25_percent_of_the_range_max_3_steps_without_rng_or_steps) {
    const ContentDB& db = tu::RichDb();
    SaveData s = NewSave(db);
    s.characters[0].backpack.push_back(Item(70, "item_base.iron_sword", Rarity::Magic, 1, {Aff("affix.melee_dmg", 0.05)}));  // faixa 0,05 a 0,15
    const AffixData* a = db.FindAffix("affix.melee_dmg");
    double expected = 0.05;
    const std::int64_t goldCosts[] = {60, 120, 240};
    for (int step = 0; step < 3; ++step) {
        const std::int64_t gold = CurrencyAmount(s, kGoldId);
        const std::int64_t shards = CurrencyAmount(s, kShardsId);
        CraftPlan p;
        ASSERT_ENUM_EQ_OK(CraftPolish(db, s, 0, 70, 0, &p));
        expected = std::min(a->maxValue, expected + 0.25 * (a->maxValue - a->minValue));
        const ItemInstance* it = FindBackpack(s, 70);
        EXPECT_NEAR(it->affixes[0].value, expected, 1e-12);
        EXPECT_EQ(static_cast<int>(it->affixes[0].polish), step + 1);
        EXPECT_EQ(gold - CurrencyAmount(s, kGoldId), goldCosts[step]);
        EXPECT_EQ(shards, CurrencyAmount(s, kShardsId));
        EXPECT_EQ(it->craftSteps, static_cast<std::uint16_t>(0));  // Lapidar não consome o fluxo Crafting
        EXPECT_NEAR(p.polishFrom + 0.25 * (a->maxValue - a->minValue), p.polishTo, 1e-12);
    }
    const std::string before = Bytes(s);
    EXPECT_ENUM_EQ(CraftPolish(db, s, 0, 70, 0), CraftResult::PolishMax);   // 3 passos
    EXPECT_ENUM_EQ(CraftPolish(db, s, 0, 70, 1), CraftResult::BadIndex);
    EXPECT_ENUM_EQ(CraftPolish(db, s, 0, 70, -1), CraftResult::BadIndex);
    EXPECT_EQ(Bytes(s), before);
    EXPECT_EQ(s.craftSeed, static_cast<std::uint64_t>(0));  // nem fixou semente: não houve sorteio
}

TEST(economy_polish_never_leaves_the_range_integers_round_and_value_at_max_refuses) {
    const ContentDB& db = tu::RichDb();
    SaveData s = NewSave(db);
    // Afixo inteiro (10 a 20): passos de 25% da faixa = 2,5 -> arredonda.
    s.characters[0].backpack.push_back(Item(71, "item_base.leather_vest", Rarity::Rare, 1,
        {Aff("affix.life_flat", 19), Aff("affix.armor_flat", 5), Aff("affix.fire_res", 0.15), Aff("affix.life_regen", 1)}));
    ASSERT_ENUM_EQ_OK(CraftPolish(db, s, 0, 71, 0));
    EXPECT_NEAR(FindBackpack(s, 71)->affixes[0].value, 20.0, 1e-12);        // 19 + 2,5 limitado ao máximo
    EXPECT_ENUM_EQ(CraftPolish(db, s, 0, 71, 0), CraftResult::PolishMax);   // já no máximo da faixa (passo 1 de 3)
    ASSERT_ENUM_EQ_OK(CraftPolish(db, s, 0, 71, 1));
    const double armor = FindBackpack(s, 71)->affixes[1].value;
    EXPECT_NEAR(armor, std::floor(armor), 1e-12);                           // continua inteiro
    EXPECT_TRUE(armor > 5.0 && armor <= 15.0);
    ASSERT_ENUM_EQ_OK(CraftPolish(db, s, 0, 71, 3));                        // 1 -> 1 + 0,25 x 1 = 1,25 (faixa 1 a 2, inteiro): anda 1
    EXPECT_NEAR(FindBackpack(s, 71)->affixes[3].value, 2.0, 1e-12);
    // Comum não tem afixo.
    s.characters[0].backpack.push_back(Item(72, "item_base.iron_sword", Rarity::Normal));
    EXPECT_ENUM_EQ(CraftPolish(db, s, 0, 72, 0), CraftResult::WrongRarity);
}

// ---------------------------------------------------------------------------------------------------------------------
// Desmontar
// ---------------------------------------------------------------------------------------------------------------------
TEST(economy_dismantle_returns_shards_by_rarity_is_idempotent_and_refuses_equipped_and_unique) {
    const ContentDB& db = tu::RichDb();
    const RulesConstants& r = db.Rules();
    SaveData s = NewSave(db, 0, 0);
    auto& bp = s.characters[0].backpack;
    bp.push_back(Item(80, "item_base.iron_sword", Rarity::Normal));
    bp.push_back(Item(81, "item_base.iron_sword", Rarity::Magic, 1, {Aff("affix.melee_dmg", 0.1)}));
    s.stash.push_back(Item(82, "item_base.iron_sword", Rarity::Rare, 1, {Aff("affix.melee_dmg", 0.1), Aff("affix.crit_chance", 0.03), Aff("affix.scorching", 0.1)}));
    ASSERT_ENUM_EQ_OK(CraftDismantle(db, s, 0, 80));
    EXPECT_EQ(CurrencyAmount(s, kShardsId), r.dismantleShards[0]);
    ASSERT_ENUM_EQ_OK(CraftDismantle(db, s, 0, 81));
    ASSERT_ENUM_EQ_OK(CraftDismantle(db, s, 0, 82));
    EXPECT_EQ(CurrencyAmount(s, kShardsId), r.dismantleShards[0] + r.dismantleShards[1] + r.dismantleShards[2]);
    EXPECT_TRUE(bp.empty() && s.stash.empty());
    const std::string before = Bytes(s);
    EXPECT_ENUM_EQ(CraftDismantle(db, s, 0, 80), CraftResult::NotFound);    // repetir não paga de novo
    EXPECT_EQ(Bytes(s), before);
    s.characters[0].equipment[static_cast<std::size_t>(ItemSlot::MainHand)] = Item(83, "item_base.iron_sword", Rarity::Magic, 1, {Aff("affix.melee_dmg", 0.1)});
    EXPECT_ENUM_EQ(CraftDismantle(db, s, 0, 83), CraftResult::EquippedDismantle);
    ItemInstance uniq = Item(84, "item_base.bone_helm", Rarity::Unique, 1);
    uniq.uniqueId = "unique.bell_warden_helm";
    bp.push_back(uniq);
    EXPECT_ENUM_EQ(CraftDismantle(db, s, 0, 84), CraftResult::Unique);
    EXPECT_TRUE(FindBackpack(s, 84) != nullptr);
}

// ---------------------------------------------------------------------------------------------------------------------
// Atomicidade
// ---------------------------------------------------------------------------------------------------------------------
TEST(economy_plan_never_writes_and_an_interrupted_operation_leaves_the_save_identical) {
    const ContentDB& db = tu::RichDb();
    SaveData s = NewSave(db);
    s.characters[0].backpack.push_back(Item(90, "item_base.leather_vest", Rarity::Magic, 3, {Aff("affix.life_flat", 12)}));
    const std::string before = Bytes(s);
    for (CraftOp op : {CraftOp::Refine, CraftOp::Reforge, CraftOp::Add, CraftOp::Polish, CraftOp::Dismantle}) {
        const CraftPlan p = PlanCraft(db, s, 0, 90, op, op == CraftOp::Reforge ? -1 : 0);
        (void)p;  // "queda" antes do Commit: o plano é descartado
        EXPECT_EQ(Bytes(s), before);
    }
    (void)OfferAddAffix(db, s, 0, 90);
    EXPECT_EQ(Bytes(s), before);
    // Plano velho (o item mudou de lugar ou foi vendido) não faz nada ao ser confirmado.
    const CraftPlan stale = PlanCraft(db, s, 0, 90, CraftOp::Reforge, -1);
    ASSERT_ENUM_EQ_OK2(stale.result);
    SaveData moved = s;
    ASSERT_TRUE(MoveItem(db, moved, 0, 90, Container::Stash) == InvResult::Ok);
    const std::string movedBytes = Bytes(moved);
    CommitCraft(moved, 0, stale);
    EXPECT_EQ(Bytes(moved), movedBytes);
    // Confirmar duas vezes o mesmo plano cobra uma vez só quando o saldo acabou na segunda.
    SaveData poor = NewSave(db, 0, 0);
    SetCur(poor, kGoldId, stale.gold);
    SetCur(poor, kShardsId, stale.shards);
    poor.characters[0].backpack = s.characters[0].backpack;
    CommitCraft(poor, 0, stale);
    EXPECT_EQ(CurrencyAmount(poor, kGoldId), 0);
    const std::string once = Bytes(poor);
    CommitCraft(poor, 0, stale);   // saldo insuficiente: não aplica de novo
    EXPECT_EQ(Bytes(poor), once);
    // Plano que não é Ok nunca escreve.
    CraftPlan bad;
    bad.result = CraftResult::NoGold;
    bad.uid = 90;
    CommitCraft(poor, 0, bad);
    EXPECT_EQ(Bytes(poor), once);
}

TEST(economy_saldo_never_goes_negative_when_paying_exactly_what_is_left) {
    const ContentDB& db = tu::RichDb();
    const CraftCostData* row = db.FindCraftCost(CraftOp::Refine, Rarity::Normal, 0);
    SaveData s = NewSave(db, row->goldCost, row->shardCost);
    s.characters[0].backpack.push_back(Item(91, "item_base.iron_sword", Rarity::Normal));
    ASSERT_ENUM_EQ_OK(CraftRefine(db, s, 0, 91));
    EXPECT_EQ(CurrencyAmount(s, kGoldId), 0);
    EXPECT_EQ(CurrencyAmount(s, kShardsId), 0);
}

// ---------------------------------------------------------------------------------------------------------------------
// Vendedor, recompra e Frasco de Recarga
// ---------------------------------------------------------------------------------------------------------------------
TEST(economy_vendor_sells_at_core_value_moves_item_to_buyback_and_is_idempotent) {
    const ContentDB& db = tu::RichDb();
    SaveData s = NewSave(db, 0, 0);
    s.characters[0].backpack.push_back(Item(100, "item_base.iron_sword", Rarity::Rare, 5, {Aff("affix.melee_dmg", 0.1)}));
    s.stash.push_back(Item(101, "item_base.iron_sword", Rarity::Magic, 1));
    const std::int64_t value = SellValue(db, s.characters[0].backpack[0]);
    std::int64_t gold = 0;
    bool evicted = true;
    ASSERT_TRUE(VendorSell(db, s, 0, Container::Backpack, 100, &gold, &evicted) == VendorResult::Ok);
    EXPECT_EQ(gold, value);
    EXPECT_FALSE(evicted);
    EXPECT_EQ(CurrencyAmount(s, kGoldId), value);
    ASSERT_EQ(s.vendorBuyback.size(), static_cast<std::size_t>(1));
    EXPECT_EQ(s.vendorBuyback[0].item.uid, static_cast<std::uint64_t>(100));
    EXPECT_EQ(s.vendorBuyback[0].paid, value);
    const std::string before = Bytes(s);
    EXPECT_TRUE(VendorSell(db, s, 0, Container::Backpack, 100, &gold) == VendorResult::NotFound);   // repetir não paga
    EXPECT_EQ(gold, 0);
    EXPECT_EQ(Bytes(s), before);
    ASSERT_TRUE(VendorSell(db, s, 0, Container::Stash, 101) == VendorResult::Ok);                   // do Baú também
    EXPECT_EQ(s.vendorBuyback[0].item.uid, static_cast<std::uint64_t>(101));                        // o mais recente primeiro
    // Equipado não vende.
    s.characters[0].equipment[static_cast<std::size_t>(ItemSlot::Head)] = Item(102, "item_base.bone_helm", Rarity::Normal);
    EXPECT_TRUE(VendorSell(db, s, 0, Container::Backpack, 102) == VendorResult::NotFound);
    EXPECT_TRUE(s.characters[0].equipment[static_cast<std::size_t>(ItemSlot::Head)].has_value());
}

TEST(economy_vendor_buyback_keeps_the_last_10_and_the_11th_evicts_the_oldest) {
    const ContentDB& db = tu::RichDb();
    const int cap = db.Rules().vendorBuybackSlots;
    ASSERT_EQ(cap, 10);
    SaveData s = NewSave(db, 0, 0);
    for (int i = 0; i < cap + 3; ++i) s.characters[0].backpack.push_back(Item(200 + static_cast<std::uint64_t>(i), "item_base.iron_sword", i == 0 ? Rarity::Rare : Rarity::Normal, 1));
    for (int i = 0; i < cap; ++i) {
        const BuybackInfo info = GetBuybackInfo(db, s);
        EXPECT_FALSE(info.wouldEvict);
        bool evicted = true;
        ASSERT_TRUE(VendorSell(db, s, 0, Container::Backpack, 200 + static_cast<std::uint64_t>(i), nullptr, &evicted) == VendorResult::Ok);
        EXPECT_FALSE(evicted);
    }
    EXPECT_EQ(s.vendorBuyback.size(), static_cast<std::size_t>(10));
    const BuybackInfo full = GetBuybackInfo(db, s);
    EXPECT_TRUE(full.wouldEvict);
    EXPECT_ENUM_EQ(full.evictRarity, Rarity::Rare);   // o mais antigo (uid 200) é Raro: a UI avisa
    bool evicted = false;
    Rarity ev = Rarity::Normal;
    ASSERT_TRUE(VendorSell(db, s, 0, Container::Backpack, 210, nullptr, &evicted, &ev) == VendorResult::Ok);
    EXPECT_TRUE(evicted);
    EXPECT_ENUM_EQ(ev, Rarity::Rare);
    EXPECT_EQ(s.vendorBuyback.size(), static_cast<std::size_t>(10));
    EXPECT_EQ(s.vendorBuyback.front().item.uid, static_cast<std::uint64_t>(210));
    for (const BuybackEntry& e : s.vendorBuyback) EXPECT_TRUE(e.item.uid != 200);   // o expulso deixou de existir
    EXPECT_TRUE(FindBackpack(s, 200) == nullptr);
}

TEST(economy_vendor_buyback_costs_125_percent_rounded_up_and_persists_across_save) {
    const ContentDB& db = tu::RichDb();
    SaveData s = NewSave(db, 0, 0);
    s.characters[0].backpack.push_back(Item(300, "item_base.iron_sword", Rarity::Magic, 1, {Aff("affix.melee_dmg", 0.1)}));
    std::int64_t paid = 0;
    ASSERT_TRUE(VendorSell(db, s, 0, Container::Backpack, 300, &paid) == VendorResult::Ok);
    const std::int64_t price = BuybackPrice(db, paid);
    EXPECT_EQ(price, static_cast<std::int64_t>(std::ceil(static_cast<double>(paid) * 1.25 - 1e-9)));
    EXPECT_TRUE(price > paid);
    EXPECT_EQ(BuybackPrice(db, 12), 15);
    EXPECT_EQ(BuybackPrice(db, 35), 44);   // 43,75 sobe
    // A recompra "fecha e abre o jogo".
    SaveData loaded;
    ASSERT_TRUE(ParseJson(SerializeJson(s, true), loaded) == LoadStatus::Ok);
    ASSERT_EQ(loaded.vendorBuyback.size(), static_cast<std::size_t>(1));
    EXPECT_EQ(loaded.vendorBuyback[0].paid, paid);
    EXPECT_EQ(Bytes(loaded), Bytes(s));
    // Sem Ouro: recusa sem mudar nada.
    SetCur(s, kGoldId, price - 1);
    const std::string before = Bytes(s);
    EXPECT_TRUE(VendorBuyback(db, s, 0, 300) == VendorResult::NoGold);
    EXPECT_EQ(Bytes(s), before);
    SetCur(s, kGoldId, price);
    std::int64_t spent = 0;
    ASSERT_TRUE(VendorBuyback(db, s, 0, 300, &spent) == VendorResult::Ok);
    EXPECT_EQ(spent, price);
    EXPECT_EQ(CurrencyAmount(s, kGoldId), 0);
    ASSERT_TRUE(FindBackpack(s, 300) != nullptr);
    EXPECT_EQ(FindBackpack(s, 300)->uid, static_cast<std::uint64_t>(300));
    EXPECT_TRUE(s.vendorBuyback.empty());
    const std::string after = Bytes(s);
    EXPECT_TRUE(VendorBuyback(db, s, 0, 300) == VendorResult::NotFound);    // repetir não cobra de novo
    EXPECT_EQ(Bytes(s), after);
}

TEST(economy_vendor_buyback_refuses_when_backpack_is_full) {
    const auto small = RichWith({{"rules.csv", RulesWith("inventory_capacity", "2")}});
    ASSERT_TRUE(small->Errors().empty());
    SaveData s = NewSave(*small, 1000, 0);
    s.characters[0].backpack.push_back(Item(400, "item_base.iron_sword", Rarity::Normal));
    ASSERT_TRUE(VendorSell(*small, s, 0, Container::Backpack, 400) == VendorResult::Ok);
    s.characters[0].backpack.push_back(Item(401, "item_base.iron_sword", Rarity::Normal));
    s.characters[0].backpack.push_back(Item(402, "item_base.iron_sword", Rarity::Normal));
    const std::string before = Bytes(s);
    EXPECT_TRUE(VendorBuyback(*small, s, 0, 400) == VendorResult::Full);
    EXPECT_EQ(Bytes(s), before);
}

TEST(economy_vendor_sells_the_flask_up_to_the_carry_cap_and_checks_gold) {
    const ContentDB& db = tu::RichDb();
    SaveData s = NewSave(db, 120, 0);
    std::int64_t spent = 0;
    EXPECT_TRUE(VendorBuy(db, s, "vendor.nope", 1) == VendorResult::NotFound);
    EXPECT_TRUE(VendorBuy(db, s, "vendor.refill_flask", 0) == VendorResult::BadQuantity);
    EXPECT_TRUE(VendorBuy(db, s, "vendor.refill_flask", -3) == VendorResult::BadQuantity);
    ASSERT_TRUE(VendorBuy(db, s, "vendor.refill_flask", 1, &spent) == VendorResult::Ok);
    EXPECT_EQ(spent, 50);
    EXPECT_EQ(CurrencyAmount(s, kRefillFlaskId), 1);
    ASSERT_TRUE(VendorBuy(db, s, "vendor.refill_flask", 1) == VendorResult::Ok);
    const std::string before = Bytes(s);
    EXPECT_TRUE(VendorBuy(db, s, "vendor.refill_flask", 1) == VendorResult::NoGold);   // 20 Ouro
    EXPECT_EQ(Bytes(s), before);
    SetCur(s, kGoldId, 10000);
    EXPECT_TRUE(VendorBuy(db, s, "vendor.refill_flask", 2) == VendorResult::CarryCap);  // 2 + 2 > 3
    EXPECT_TRUE(VendorBuy(db, s, "vendor.refill_flask", 4) == VendorResult::CarryCap);
    ASSERT_TRUE(VendorBuy(db, s, "vendor.refill_flask", 1) == VendorResult::Ok);
    EXPECT_EQ(CurrencyAmount(s, kRefillFlaskId), 3);
    EXPECT_TRUE(VendorBuy(db, s, "vendor.refill_flask", 1) == VendorResult::CarryCap);
    EXPECT_EQ(CurrencyAmount(s, kGoldId), 10000 - 50);
}

namespace {
PotionBelt BeltWith(const ContentDB& db, int life, int ward) {
    PotionBelt b = MakeFullPotionBelt(db);
    b.slots[0].charges = life;
    b.slots[0].rechargeRemaining = life < 3 ? 40.0 : 0.0;
    b.slots[1].charges = ward;
    b.slots[1].rechargeRemaining = ward < 2 ? 60.0 : 0.0;
    return b;
}
}  // namespace

TEST(economy_flask_restores_one_charge_of_the_fewest_without_passing_the_max) {
    const ContentDB& db = tu::RichDb();
    SaveData s = NewSave(db);
    SetCur(s, kRefillFlaskId, 3);
    PotionBelt belt = BeltWith(db, 2, 0);           // a Resguardo tem menos
    FlaskOutcome o = UseRefillFlask(db, s, belt, FlaskContext::Run);
    ASSERT_TRUE(o.result == FlaskResult::Ok);
    EXPECT_EQ(o.potionIndex, 1);
    EXPECT_EQ(o.chargesAfter, 1);
    EXPECT_EQ(o.flasksLeft, 2);
    EXPECT_EQ(belt.slots[0].charges, 2);
    EXPECT_TRUE(belt.lockoutRemaining > 0.0);        // respeita a trava global do próximo uso
    EXPECT_TRUE(UseRefillFlask(db, s, belt, FlaskContext::Run).result == FlaskResult::LockedOut);
    EXPECT_EQ(CurrencyAmount(s, kRefillFlaskId), 2);  // recusa não gasta
    TickPotions(db, belt, 1.5);
    // Empate: a Vida (a primeira do CSV).
    belt = BeltWith(db, 1, 1);
    o = UseRefillFlask(db, s, belt, FlaskContext::Run);
    ASSERT_TRUE(o.result == FlaskResult::Ok);
    EXPECT_EQ(o.potionIndex, 0);
    EXPECT_EQ(belt.slots[0].charges, 2);
    EXPECT_EQ(belt.slots[1].charges, 1);
    // Chegar ao máximo zera a recarga pendente; nunca passa do máximo.
    belt = BeltWith(db, 2, 2);
    ASSERT_TRUE(UseRefillFlask(db, s, belt, FlaskContext::Run).result == FlaskResult::Ok);
    EXPECT_EQ(belt.slots[0].charges, 3);
    EXPECT_NEAR(belt.slots[0].rechargeRemaining, 0.0, 1e-12);
    // Tudo cheio: o frasco não é gasto.
    belt = MakeFullPotionBelt(db);
    SetCur(s, kRefillFlaskId, 1);
    const std::int64_t flasks = CurrencyAmount(s, kRefillFlaskId);
    EXPECT_TRUE(UseRefillFlask(db, s, belt, FlaskContext::Run).result == FlaskResult::PotionsFull);
    EXPECT_EQ(CurrencyAmount(s, kRefillFlaskId), flasks);
}

TEST(economy_flask_is_blocked_in_the_arena_and_idle_and_without_flasks) {
    const ContentDB& db = tu::RichDb();
    SaveData s = NewSave(db);
    PotionBelt belt = BeltWith(db, 0, 0);
    EXPECT_TRUE(UseRefillFlask(db, s, belt, FlaskContext::Run).result == FlaskResult::NoFlask);
    SetCur(s, kRefillFlaskId, 3);
    const std::string bytes = Bytes(s);
    EXPECT_TRUE(UseRefillFlask(db, s, belt, FlaskContext::Arena).result == FlaskResult::ArenaLocked);
    EXPECT_TRUE(UseRefillFlask(db, s, belt, FlaskContext::Idle).result == FlaskResult::IdleForbidden);
    EXPECT_EQ(Bytes(s), bytes);
    EXPECT_EQ(belt.slots[0].charges, 0);
    EXPECT_NEAR(belt.lockoutRemaining, 0.0, 1e-12);
}

// ---------------------------------------------------------------------------------------------------------------------
// Save
// ---------------------------------------------------------------------------------------------------------------------
TEST(economy_save_new_fields_are_optional_roundtrip_and_validated) {
    const ContentDB& db = tu::RichDb();
    SaveData plain = NewSave(db);
    const std::string plainJson = Bytes(plain);
    EXPECT_TRUE(plainJson.find("craft_seed") == std::string::npos);        // saves antigos: mesmos bytes
    EXPECT_TRUE(plainJson.find("vendor_buyback") == std::string::npos);
    EXPECT_TRUE(plainJson.find("craft_steps") == std::string::npos);
    EXPECT_TRUE(plainJson.find("polish") == std::string::npos);
    SaveData s = plain;
    s.craftSeed = 0xFFFFFFFFFFFFFFF1ull;
    ItemInstance it = Item(500, "item_base.iron_sword", Rarity::Rare, 4, {Aff("affix.melee_dmg", 0.12, 2), Aff("affix.crit_chance", 0.03)});
    it.craftSteps = 7;
    it.craftReforges = 3;
    s.characters[0].backpack.push_back(it);
    s.vendorBuyback.push_back(BuybackEntry{Item(501, "item_base.bone_helm", Rarity::Magic, 1, {Aff("affix.armor_flat", 9)}), 12});
    SaveData loaded;
    ASSERT_TRUE(ParseJson(SerializeJson(s, true), loaded) == LoadStatus::Ok);
    EXPECT_EQ(loaded.craftSeed, s.craftSeed);
    ASSERT_EQ(loaded.characters[0].backpack.size(), static_cast<std::size_t>(1));
    EXPECT_EQ(loaded.characters[0].backpack[0].craftSteps, static_cast<std::uint16_t>(7));
    EXPECT_EQ(loaded.characters[0].backpack[0].craftReforges, static_cast<std::uint16_t>(3));
    EXPECT_EQ(static_cast<int>(loaded.characters[0].backpack[0].affixes[0].polish), 2);
    EXPECT_EQ(loaded.vendorBuyback[0].paid, 12);
    EXPECT_EQ(Bytes(loaded), Bytes(s));
    // Valores adulterados são recusados na leitura.
    auto tamper = [&](const std::string& from, const std::string& to) {
        json::Value data = SaveToJson(s);
        std::string text = json::Serialize(data, false);
        const std::size_t at = text.find(from);
        if (at == std::string::npos) { FAIL("trecho nao encontrado: " + from); return false; }
        text.replace(at, from.size(), to);
        json::Value v;
        json::ParseError pe;
        if (!json::Parse(text, v, &pe)) { FAIL("json invalido"); return false; }
        SaveData out;
        return SaveFromJson(v, out, nullptr);
    };
    EXPECT_TRUE(tamper("\"paid\":12", "\"paid\":13"));
    EXPECT_FALSE(tamper("\"paid\":12", "\"paid\":-1"));
    EXPECT_FALSE(tamper("\"polish\":2", "\"polish\":11"));
    EXPECT_FALSE(tamper("\"craft_steps\":7", "\"craft_steps\":70000"));
}

TEST(economy_one_thousand_save_load_cycles_in_the_middle_do_not_change_the_result) {
    const ContentDB& db = tu::RichDb();
    SaveData straight = NewSave(db, 100000000, 100000000);
    straight.characters[0].backpack.push_back(Item(600, "item_base.leather_vest", Rarity::Normal, 9));
    SaveData cycled = straight;
    auto run = [&](SaveData& s, int i) {
        switch (i % 4) {
            case 0: if (CraftRefine(db, s, 0, 600) == CraftResult::WrongRarity) CraftReforge(db, s, 0, 600, -1); break;
            case 1: CraftReforge(db, s, 0, 600, i % 8 == 1 ? 0 : -1); break;
            case 2: CraftPolish(db, s, 0, 600, i % 2, nullptr); break;
            default: CraftAddAffix(db, s, 0, 600, i % 3); break;
        }
    };
    for (int i = 0; i < 1000; ++i) {
        run(straight, i);
        run(cycled, i);
        SaveData reloaded;
        ASSERT_TRUE(ParseJson(SerializeJson(cycled, false), reloaded) == LoadStatus::Ok);
        cycled = std::move(reloaded);
    }
    EXPECT_EQ(Bytes(cycled), Bytes(straight));
    std::string why;
    EXPECT_TRUE(ItemIsValid(db, *FindBackpack(straight, 600), &why));
}

// ---------------------------------------------------------------------------------------------------------------------
// "Nunca pode acontecer" (docs/16 11.5) como propriedade, em escala
// ---------------------------------------------------------------------------------------------------------------------
TEST(economy_property_random_operations_never_break_a_never_happens_rule) {
    const ContentDB& db = tu::RichDb();
    const long long total = 1000000LL;  // A3-35: 1 milhão de operações aleatórias
    Pcg32 rng(0xEC0Full, 7);
    const char* bases[] = {"item_base.iron_sword", "item_base.bone_helm", "item_base.leather_vest", "item_base.iron_boots", "item_base.worn_trousers"};
    SaveData s = NewSave(db, 0, 0);
    const std::uint64_t kBase = 10000;
    constexpr int kItems = 24;
    auto fresh = [&](int k) {
        const Rarity rar = static_cast<Rarity>(rng.NextBelow(3));          // Comum, Mágico ou Raro (como o loot gera)
        const int level = rng.RangeInt(1, 20);
        ItemInstance it = Item(kBase + static_cast<std::uint64_t>(k), bases[rng.NextBelow(5)], rar, level);
        if (rar != Rarity::Normal) {
            it.affixes = RollAffixes(db, *db.FindItemBase(it.baseId), rar, level, rng);
            if (it.affixes.empty()) it.rarity = Rarity::Normal;
        }
        return it;
    };
    for (int k = 0; k < kItems; ++k) s.characters[0].backpack.push_back(fresh(k));
    long long applied[5] = {0, 0, 0, 0, 0};
    std::string why;
    for (long long n = 0; n < total; ++n) {
        if (shatter_test::CurrentFailures() > 0) return;  // uma violação basta
        if (n % 97 == 0) {   // saldo oscila: às vezes rico, às vezes quase zerado
            SetCur(s, kGoldId, rng.NextBelow(4) == 0 ? static_cast<std::int64_t>(rng.NextBelow(150)) : 100000000);
            SetCur(s, kShardsId, rng.NextBelow(4) == 0 ? static_cast<std::int64_t>(rng.NextBelow(30)) : 100000000);
        }
        const int k = static_cast<int>(rng.NextBelow(kItems));
        const std::uint64_t uid = kBase + static_cast<std::uint64_t>(k);
        const ItemInstance* cur = FindBackpack(s, uid);
        if (cur == nullptr) { s.characters[0].backpack.push_back(fresh(k)); continue; }
        const ItemInstance before = *cur;
        const std::int64_t gold0 = CurrencyAmount(s, kGoldId), shards0 = CurrencyAmount(s, kShardsId);
        const CraftOp op = static_cast<CraftOp>(rng.NextBelow(5));
        const int arg = static_cast<int>(rng.NextBelow(6)) - 1;
        CraftPlan plan;
        CraftResult r = CraftResult::Ok;
        switch (op) {
            case CraftOp::Refine: r = CraftRefine(db, s, 0, uid, &plan); break;
            case CraftOp::Reforge: r = CraftReforge(db, s, 0, uid, arg, &plan); break;
            case CraftOp::Add: r = CraftAddAffix(db, s, 0, uid, arg, &plan); break;
            case CraftOp::Polish: r = CraftPolish(db, s, 0, uid, arg, &plan); break;
            case CraftOp::Dismantle: r = CraftDismantle(db, s, 0, uid, &plan); break;
        }
        const std::int64_t gold1 = CurrencyAmount(s, kGoldId), shards1 = CurrencyAmount(s, kShardsId);
        if (gold1 < 0 || shards1 < 0) FAIL("saldo negativo");
        const ItemInstance* after = FindBackpack(s, uid);
        if (r != CraftResult::Ok) {
            // Recusa não muda nada: nem item, nem saldo.
            if (gold1 != gold0 || shards1 != shards0) FAIL("recusa mexeu no saldo");
            if (after == nullptr || json::Serialize(ItemToJson(*after), false) != json::Serialize(ItemToJson(before), false))
                FAIL("recusa mexeu no item");
            continue;
        }
        ++applied[static_cast<int>(op)];
        if (op == CraftOp::Dismantle) {
            if (after != nullptr) FAIL("desmontado continua existindo");
            if (shards1 - shards0 != plan.shardsGain || gold1 != gold0) FAIL("desmontar cobrou errado");
            continue;
        }
        if (after == nullptr) FAIL("item sumiu sem Desmontar");
        // cobrou exatamente o que mostrou
        if (gold0 - gold1 != plan.gold || shards0 - shards1 != plan.shards) FAIL("cobrança diferente do custo");
        // identidade intocada
        if (after->uid != before.uid || after->baseId != before.baseId || after->itemLevel != before.itemLevel ||
            !after->uniqueId.empty())
            FAIL("identidade mudou");
        if (!ItemIsValid(db, *after, &why)) FAIL("item invalido depois de " + std::string(ToString(op)) + ": " + why);
        if (op == CraftOp::Refine) {
            if (before.rarity != Rarity::Normal || after->rarity != Rarity::Magic) FAIL("Refinar fora da regra");
        } else if (after->rarity != before.rarity) {
            FAIL("raridade mudou fora do Refinar");
        }
        if (op == CraftOp::Reforge && after->affixes.size() != before.affixes.size()) FAIL("Reforjar mudou a quantidade");
        if (op == CraftOp::Reforge && after->hasInscription != before.hasInscription) FAIL("Reforjar mudou a inscricao");
        if (op == CraftOp::Add && (!after->hasInscription || before.hasInscription || after->affixes.size() != before.affixes.size() + 1))
            FAIL("Adicionar fora da regra");
        if (op == CraftOp::Polish && (after->craftSteps != before.craftSteps || after->affixes.size() != before.affixes.size()))
            FAIL("Lapidar mexeu no fluxo ou na quantidade");
        if (n % 5000 == 0) {   // reabastece a vitrine de itens para manter variedade
            s.characters[0].backpack.erase(std::remove_if(s.characters[0].backpack.begin(), s.characters[0].backpack.end(),
                                                         [&](const ItemInstance& i) { return i.uid == uid; }),
                                           s.characters[0].backpack.end());
        }
    }
    // Todas as operações foram exercitadas de verdade, não só recusadas.
    for (int i = 0; i < 5; ++i) EXPECT_TRUE(applied[i] > 1000);
}
