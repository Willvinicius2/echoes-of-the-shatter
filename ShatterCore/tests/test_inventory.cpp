// Inventário, equipamento, comparação, venda, loot no chão e visualSetId (inventory.h; docs/16 seção 4).
// Capacidades, preços e posições liberadas vêm de rules.csv; nada disso é fixado aqui: os testes leem o banco.
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <memory>

#include "test_util.h"

using namespace shatter;

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

ItemInstance Item(std::uint64_t uid, const char* base, Rarity r = Rarity::Normal, int level = 1) {
    ItemInstance it;
    it.uid = uid;
    it.baseId = base;
    it.rarity = r;
    it.itemLevel = level;
    return it;
}

SaveData NewSave(const ContentDB& db) {
    SaveData s;
    s.contentVersion = db.ContentVersion();
    s.characters.push_back(tu::MakeWarrior(db, 3));
    s.nextItemUid = 1000;
    return s;
}

const ItemInstance* Equipped(const SaveData& s, ItemSlot slot) {
    const auto& e = s.characters[0].equipment[static_cast<std::size_t>(slot)];
    return e ? &*e : nullptr;
}

}  // namespace

TEST(inventory_capacity_comes_from_rules_and_full_changes_nothing) {
    const ContentDB& db = tu::RichDb();
    EXPECT_TRUE(db.Rules().inventoryCapacity > 0 && db.Rules().stashCapacity > 0);
    const auto small = RichWith({{"rules.csv", RulesWith("inventory_capacity", "3")}});
    ASSERT_TRUE(small->Errors().empty());
    SaveData s = NewSave(*small);
    for (std::uint64_t i = 1; i <= 3; ++i) EXPECT_ENUM_EQ(BackpackAdd(*small, s, 0, Item(i + 10, "item_base.bone_helm")), InvResult::Ok);
    const std::string before = SerializeJson(s, false);
    EXPECT_ENUM_EQ(BackpackAdd(*small, s, 0, Item(99, "item_base.bone_helm")), InvResult::Full);
    EXPECT_EQ(SerializeJson(s, false), before);
    const InventoryInfo info = GetInventoryInfo(*small, s, 0);
    EXPECT_EQ(info.backpackCapacity, 3);
    EXPECT_EQ(info.backpackUsed, 3);
    EXPECT_ENUM_EQ(BackpackAdd(*small, s, 7, Item(98, "item_base.bone_helm")), InvResult::NotFound);        // personagem inexistente
    EXPECT_ENUM_EQ(BackpackAdd(*small, s, 0, Item(97, "item_base.nope")), InvResult::UnknownContent);
    // Baú: capacidade própria.
    const auto tiny = RichWith({{"rules.csv", RulesWith("stash_capacity", "1")}});
    SaveData t = NewSave(*tiny);
    EXPECT_ENUM_EQ(StashAdd(*tiny, t, Item(1, "item_base.bone_helm")), InvResult::Ok);
    EXPECT_ENUM_EQ(StashAdd(*tiny, t, Item(2, "item_base.bone_helm")), InvResult::Full);
}

TEST(inventory_missing_new_rule_key_is_a_validation_error) {
    std::string text = tu::ReadFile(tu::RichDir() + "/rules.csv");
    const std::size_t at = text.find("\ninventory_capacity,");
    ASSERT_TRUE(at != std::string::npos);
    text.erase(at + 1, text.find_first_of("\r\n", at + 1) - at);
    const auto db = RichWith({{"rules.csv", text}});
    bool found = false;
    for (const ContentError& e : db->Errors()) found = found || e.message.find("inventory_capacity") != std::string::npos;
    EXPECT_TRUE(found);
}

TEST(inventory_equip_swaps_back_to_backpack_and_updates_stats_like_a_rebuild) {
    const ContentDB& db = tu::RichDb();
    SaveData s = NewSave(db);
    ItemInstance helmA = Item(11, "item_base.bone_helm");
    ItemInstance helmB = Item(12, "item_base.bone_helm", Rarity::Unique);
    helmB.uniqueId = "unique.idle_ready_helm";
    ASSERT_TRUE(BackpackAdd(db, s, 0, helmA) == InvResult::Ok);
    ASSERT_TRUE(BackpackAdd(db, s, 0, helmB) == InvResult::Ok);
    StatBlock stats;
    ASSERT_TRUE(BuildStatBlock(db, s.characters[0], stats));
    const double armor0 = stats.Get(StatId::Armor);

    EquipOutcome a = Equip(db, s, 0, 11, ItemSlot::Count, &stats);
    EXPECT_ENUM_EQ(a.result, InvResult::Ok);
    EXPECT_ENUM_EQ(a.slot, ItemSlot::Head);
    EXPECT_FALSE(a.displaced);
    EXPECT_EQ(Equipped(s, ItemSlot::Head)->uid, static_cast<std::uint64_t>(11));
    EXPECT_EQ(s.characters[0].backpack.size(), static_cast<std::size_t>(1));
    EXPECT_NEAR(stats.Get(StatId::Armor), armor0 + 5.0, 1e-9);

    // Troca: o antigo volta para a Mochila; o bloco incremental bate com a reconstrução.
    EquipOutcome b = Equip(db, s, 0, 12, ItemSlot::Head, &stats);
    EXPECT_ENUM_EQ(b.result, InvResult::Ok);
    EXPECT_TRUE(b.displaced && b.displacedUid == 11);
    EXPECT_EQ(Equipped(s, ItemSlot::Head)->uid, static_cast<std::uint64_t>(12));
    ASSERT_EQ(s.characters[0].backpack.size(), static_cast<std::size_t>(1));
    EXPECT_EQ(s.characters[0].backpack[0].uid, static_cast<std::uint64_t>(11));
    StatBlock rebuilt;
    ASSERT_TRUE(BuildStatBlock(db, s.characters[0], rebuilt));
    for (int i = 0; i < kStatCount; ++i)
        EXPECT_NEAR(stats.Get(static_cast<StatId>(i)), rebuilt.Get(static_cast<StatId>(i)), 1e-9);

    // Desequipar devolve à Mochila e tira os modificadores.
    EquipOutcome u = Unequip(db, s, 0, ItemSlot::Head, &stats);
    EXPECT_ENUM_EQ(u.result, InvResult::Ok);
    EXPECT_TRUE(Equipped(s, ItemSlot::Head) == nullptr);
    EXPECT_NEAR(stats.Get(StatId::Armor), armor0, 1e-9);
    EXPECT_ENUM_EQ(Unequip(db, s, 0, ItemSlot::Head, &stats).result, InvResult::SlotEmpty);
    EXPECT_ENUM_EQ(Equip(db, s, 0, 12345, ItemSlot::Count).result, InvResult::NotFound);
}

TEST(inventory_equip_validates_slot_locked_slots_come_from_rules_and_ring_fits_ring2) {
    const ContentDB& db = tu::RichDb();
    SaveData s = NewSave(db);
    ASSERT_TRUE(BackpackAdd(db, s, 0, Item(11, "item_base.bone_helm")) == InvResult::Ok);
    ASSERT_TRUE(BackpackAdd(db, s, 0, Item(13, "item_base.worn_trousers")) == InvResult::Ok);
    const std::string before = SerializeJson(s, false);
    EXPECT_ENUM_EQ(Equip(db, s, 0, 11, ItemSlot::Body).result, InvResult::SlotMismatch);
    EXPECT_ENUM_EQ(Equip(db, s, 0, 11, ItemSlot::Ring2).result, InvResult::SlotMismatch);
    EXPECT_EQ(SerializeJson(s, false), before);                           // recusa não muda nada
    EXPECT_ENUM_EQ(Equip(db, s, 0, 13, ItemSlot::Count).result, InvResult::Ok);   // legs liberada
    EXPECT_ENUM_EQ(Equipped(s, ItemSlot::Legs) != nullptr ? InvResult::Ok : InvResult::NotFound, InvResult::Ok);

    // Posição bloqueada por dado: o mesmo capacete, com equip_slot_head = false.
    const auto locked = RichWith({{"rules.csv", RulesWith("equip_slot_head", "false")}});
    SaveData t = NewSave(*locked);
    ASSERT_TRUE(BackpackAdd(*locked, t, 0, Item(11, "item_base.bone_helm")) == InvResult::Ok);
    EXPECT_ENUM_EQ(Equip(*locked, t, 0, 11, ItemSlot::Count).result, InvResult::SlotLocked);
    EXPECT_EQ(t.characters[0].backpack.size(), static_cast<std::size_t>(1));

    // Anéis: base `ring` serve em Ring e Ring2 (liberadas por dado); a padrão é a primeira livre.
    std::string bases = tu::ReadFile(tu::RichDir() + "/item_bases.csv");
    while (!bases.empty() && (bases.back() == '\n' || bases.back() == '\r')) bases.pop_back();
    bases += "\nitem_base.iron_band,ring,1,armor:flat:2,,,,,,,m,\n";
    std::string rules = RulesWith("equip_slot_ring", "true");
    const auto rings = RichWith({{"item_bases.csv", bases}, {"rules.csv", rules}});
    // equip_slot_ring2 ainda fechado: só o Ring serve.
    SaveData r = NewSave(*rings);
    ASSERT_TRUE(BackpackAdd(*rings, r, 0, Item(21, "item_base.iron_band")) == InvResult::Ok);
    ASSERT_TRUE(BackpackAdd(*rings, r, 0, Item(22, "item_base.iron_band")) == InvResult::Ok);
    EXPECT_ENUM_EQ(Equip(*rings, r, 0, 21, ItemSlot::Count).slot, ItemSlot::Ring);
    EXPECT_ENUM_EQ(Equip(*rings, r, 0, 22, ItemSlot::Ring2).result, InvResult::SlotLocked);
    std::string rules2;
    {
        std::string text = rules;
        const std::size_t at = text.find("\nequip_slot_ring2,");
        text.replace(at + 1, text.find_first_of("\r\n", at + 1) - at - 1, "equip_slot_ring2,true");
        rules2 = text;
    }
    const auto both = RichWith({{"item_bases.csv", bases}, {"rules.csv", rules2}});
    SaveData r2 = NewSave(*both);
    ASSERT_TRUE(BackpackAdd(*both, r2, 0, Item(21, "item_base.iron_band")) == InvResult::Ok);
    ASSERT_TRUE(BackpackAdd(*both, r2, 0, Item(22, "item_base.iron_band")) == InvResult::Ok);
    EXPECT_ENUM_EQ(Equip(*both, r2, 0, 21, ItemSlot::Count).slot, ItemSlot::Ring);
    EXPECT_ENUM_EQ(Equip(*both, r2, 0, 22, ItemSlot::Count).slot, ItemSlot::Ring2);   // a primeira livre
    EXPECT_TRUE(Equipped(r2, ItemSlot::Ring) != nullptr && Equipped(r2, ItemSlot::Ring2) != nullptr);
}

TEST(inventory_unequip_with_full_backpack_changes_nothing) {
    const auto db = RichWith({{"rules.csv", RulesWith("inventory_capacity", "1")}});
    SaveData s = NewSave(*db);
    s.characters[0].equipment[static_cast<std::size_t>(ItemSlot::Head)] = Item(5, "item_base.bone_helm");
    ASSERT_TRUE(BackpackAdd(*db, s, 0, Item(6, "item_base.leather_vest")) == InvResult::Ok);
    const std::string before = SerializeJson(s, false);
    EXPECT_ENUM_EQ(Unequip(*db, s, 0, ItemSlot::Head).result, InvResult::Full);
    EXPECT_EQ(SerializeJson(s, false), before);
    // Trocar com a Mochila cheia funciona: o novo sai e o antigo ocupa a vaga.
    ASSERT_TRUE(Equip(*db, s, 0, 6, ItemSlot::Body).result == InvResult::Ok);
    s.characters[0].backpack.clear();
    ASSERT_TRUE(BackpackAdd(*db, s, 0, Item(7, "item_base.bone_helm")) == InvResult::Ok);
    EXPECT_ENUM_EQ(Equip(*db, s, 0, 7, ItemSlot::Head).result, InvResult::Ok);
    EXPECT_EQ(s.characters[0].backpack.size(), static_cast<std::size_t>(1));
    EXPECT_EQ(s.characters[0].backpack[0].uid, static_cast<std::uint64_t>(5));
}

TEST(inventory_compare_gives_stat_deltas_and_weapon_dps_without_changing_anything) {
    const ContentDB& db = tu::RichDb();
    SaveData s = NewSave(db);
    s.characters[0].equipment[static_cast<std::size_t>(ItemSlot::Head)] = Item(5, "item_base.bone_helm");   // armadura 5
    ItemInstance better = Item(6, "item_base.bone_helm", Rarity::Unique);
    better.uniqueId = "unique.idle_ready_helm";                                                           // +20 armadura fixa
    const std::string before = SerializeJson(s, false);
    const ItemComparison c = CompareItem(db, s.characters[0], better, ItemSlot::Count);
    EXPECT_ENUM_EQ(c.result, InvResult::Ok);
    EXPECT_ENUM_EQ(c.slot, ItemSlot::Head);
    EXPECT_EQ(c.equippedUid, static_cast<std::uint64_t>(5));
    ASSERT_EQ(c.deltas.size(), static_cast<std::size_t>(1));
    EXPECT_ENUM_EQ(c.deltas[0].stat, StatId::Armor);
    EXPECT_NEAR(c.deltas[0].after - c.deltas[0].before, 20.0, 1e-9);
    EXPECT_FALSE(c.isWeapon);
    EXPECT_EQ(SerializeJson(s, false), before);
    // Igual ao equipado: neutro (sem deltas).
    EXPECT_TRUE(CompareItem(db, s.characters[0], Item(7, "item_base.bone_helm"), ItemSlot::Head).deltas.empty());
    // Posição vazia: equippedUid 0 e o item inteiro vira delta.
    const ItemComparison v = CompareItem(db, s.characters[0], Item(8, "item_base.leather_vest"), ItemSlot::Count);
    EXPECT_EQ(v.equippedUid, static_cast<std::uint64_t>(0));
    ASSERT_EQ(v.deltas.size(), static_cast<std::size_t>(1));
    EXPECT_ENUM_EQ(v.deltas[0].stat, StatId::Life);
    // Arma: DPS contra a equipada; arma com afixo de dano maior que a equipada.
    ItemInstance sword = Item(9, "item_base.iron_sword", Rarity::Unique);
    sword.uniqueId = "unique.bell_warden_blade";     // +20% de dano corpo a corpo
    const ItemComparison w = CompareItem(db, s.characters[0], sword, ItemSlot::Count);
    EXPECT_TRUE(w.isWeapon);
    EXPECT_TRUE(w.weaponDpsBefore > 0.0);
    EXPECT_TRUE(w.weaponDpsAfter > w.weaponDpsBefore);
    EXPECT_ENUM_EQ(CompareItem(db, s.characters[0], Item(1, "item_base.bone_helm"), ItemSlot::Body).result, InvResult::SlotMismatch);
    EXPECT_ENUM_EQ(CompareItem(db, s.characters[0], Item(1, "item_base.nope"), ItemSlot::Count).result, InvResult::UnknownContent);
}

TEST(inventory_sell_value_by_rarity_and_level_pays_gold_once) {
    const ContentDB& db = tu::RichDb();
    const RulesConstants& r = db.Rules();
    for (int rar = 0; rar < kRarityCount; ++rar) {
        const ItemInstance l1 = Item(1, "item_base.bone_helm", static_cast<Rarity>(rar), 1);
        EXPECT_EQ(SellValue(db, l1), static_cast<std::int64_t>(r.sellPrice[rar]));
        const ItemInstance l5 = Item(1, "item_base.bone_helm", static_cast<Rarity>(rar), 5);
        EXPECT_EQ(SellValue(db, l5), static_cast<std::int64_t>(std::floor(r.sellPrice[rar] * (1.0 + r.sellLevelFactor * 4.0) + 0.5)));
        EXPECT_TRUE(SellValue(db, l5) >= SellValue(db, l1));
    }
    EXPECT_EQ(SellValue(db, Item(1, "item_base.bone_helm", Rarity::Normal, -3)), SellValue(db, Item(1, "item_base.bone_helm", Rarity::Normal, 1)));

    SaveData s = NewSave(db);
    const ItemInstance rare = Item(30, "item_base.bone_helm", Rarity::Rare, 3);
    ASSERT_TRUE(BackpackAdd(db, s, 0, rare) == InvResult::Ok);
    ASSERT_TRUE(StashAdd(db, s, Item(31, "item_base.leather_vest")) == InvResult::Ok);
    s.currencies.push_back({"currency.gold", 7});
    std::int64_t gold = 0;
    EXPECT_ENUM_EQ(SellItem(db, s, 0, Container::Backpack, 30, &gold), InvResult::Ok);
    EXPECT_EQ(gold, SellValue(db, rare));
    EXPECT_EQ(s.currencies[0].amount, 7 + gold);
    EXPECT_TRUE(s.characters[0].backpack.empty());
    // Idempotente: o mesmo uid não paga de novo.
    EXPECT_ENUM_EQ(SellItem(db, s, 0, Container::Backpack, 30, &gold), InvResult::NotFound);
    EXPECT_EQ(s.currencies[0].amount, 7 + SellValue(db, rare));
    // Baú, sem moeda anterior de Ouro.
    SaveData t = NewSave(db);
    ASSERT_TRUE(StashAdd(db, t, Item(31, "item_base.leather_vest")) == InvResult::Ok);
    EXPECT_ENUM_EQ(SellItem(db, t, 0, Container::Stash, 31), InvResult::Ok);
    ASSERT_EQ(t.currencies.size(), static_cast<std::size_t>(1));
    EXPECT_EQ(t.currencies[0].id, std::string("currency.gold"));
    // Equipado não vende; descartar remove sem pagar.
    t.characters[0].equipment[static_cast<std::size_t>(ItemSlot::Head)] = Item(40, "item_base.bone_helm");
    EXPECT_ENUM_EQ(SellItem(db, t, 0, Container::Backpack, 40), InvResult::NotFound);
    ASSERT_TRUE(BackpackAdd(db, t, 0, Item(41, "item_base.bone_helm")) == InvResult::Ok);
    const std::int64_t goldNow = t.currencies[0].amount;
    EXPECT_ENUM_EQ(DiscardItem(t, 0, Container::Backpack, 41), InvResult::Ok);
    EXPECT_ENUM_EQ(DiscardItem(t, 0, Container::Backpack, 41), InvResult::NotFound);
    EXPECT_EQ(t.currencies[0].amount, goldNow);
}

TEST(inventory_sort_is_deterministic_by_slot_rarity_level) {
    const ContentDB& db = tu::RichDb();
    auto fill = [&](const std::vector<ItemInstance>& items) {
        SaveData s = NewSave(db);
        for (const ItemInstance& it : items) BackpackAdd(db, s, 0, it);
        SortBackpack(db, s, 0);
        std::vector<std::uint64_t> uids;
        for (const ItemInstance& it : s.characters[0].backpack) uids.push_back(it.uid);
        return uids;
    };
    std::vector<ItemInstance> items = {
        Item(1, "item_base.iron_boots"), Item(2, "item_base.bone_helm", Rarity::Normal, 1), Item(3, "item_base.bone_helm", Rarity::Rare, 1),
        Item(4, "item_base.iron_sword"), Item(5, "item_base.bone_helm", Rarity::Rare, 4), Item(6, "item_base.worn_trousers"),
        Item(7, "item_base.leather_vest", Rarity::Magic)};
    const std::vector<std::uint64_t> expect = {4, 5, 3, 2, 7, 1, 6};   // arma, elmo (Raro nv4, Raro nv1, Comum), peitoral, botas, calça
    // A ordem de ItemSlot é: main_hand, off_hand, head, body, hands, feet, ..., legs.
    EXPECT_TRUE(fill(items) == expect);
    std::reverse(items.begin(), items.end());
    EXPECT_TRUE(fill(items) == expect);                      // independe da ordem de entrada
    std::rotate(items.begin(), items.begin() + 3, items.end());
    EXPECT_TRUE(fill(items) == expect);
    SaveData s = NewSave(db);
    EXPECT_ENUM_EQ(SortBackpack(db, s, 9), InvResult::NotFound);
}

TEST(inventory_pickup_goes_to_backpack_unique_overflows_to_stash_others_stay_on_the_ground) {
    const auto db = RichWith({{"rules.csv", RulesWith("inventory_capacity", "1")}});
    SaveData s = NewSave(*db);
    EXPECT_ENUM_EQ(PickupItem(*db, s, 0, Item(1, "item_base.bone_helm")), PickupDest::Backpack);
    EXPECT_ENUM_EQ(PickupItem(*db, s, 0, Item(2, "item_base.bone_helm", Rarity::Rare)), PickupDest::Full);
    ItemInstance unique = Item(3, "item_base.bone_helm", Rarity::Unique);
    unique.uniqueId = "unique.idle_ready_helm";
    EXPECT_ENUM_EQ(PickupItem(*db, s, 0, unique), PickupDest::Stash);
    EXPECT_EQ(s.stash.size(), static_cast<std::size_t>(1));
    EXPECT_EQ(s.characters[0].backpack.size(), static_cast<std::size_t>(1));
    EXPECT_ENUM_EQ(MoveItem(*db, s, 0, 3, Container::Backpack), InvResult::Full);
    EXPECT_ENUM_EQ(MoveItem(*db, s, 0, 1, Container::Stash), InvResult::Ok);
    EXPECT_ENUM_EQ(MoveItem(*db, s, 0, 3, Container::Backpack), InvResult::Ok);
    EXPECT_ENUM_EQ(MoveItem(*db, s, 0, 77, Container::Backpack), InvResult::NotFound);
}

TEST(inventory_visual_set_id_prefers_unique_then_base_then_starter) {
    std::string uniques = tu::ReadFile(tu::RichDir() + "/uniques.csv");
    uniques = tu::Replace(uniques, "unique.idle_ready_helm,item_base.bone_helm,armor:flat:20,,true,20,manual_estimate,",
                          "unique.idle_ready_helm,item_base.bone_helm,armor:flat:20,,true,20,manual_estimate,vset.unq_idle_ready_helm");
    const auto db = RichWith({{"uniques.csv", uniques}});
    ASSERT_TRUE(db->Errors().empty());
    ItemInstance helm = Item(1, "item_base.bone_helm");
    EXPECT_EQ(ItemVisualSetId(*db, helm), std::string("vset.starter"));                     // base sem coluna: fallback
    helm.uniqueId = "unique.idle_ready_helm";
    EXPECT_EQ(ItemVisualSetId(*db, helm), std::string("vset.unq_idle_ready_helm"));          // o Único prevalece
    EXPECT_EQ(ItemVisualSetId(*db, Item(2, "item_base.worn_trousers")), std::string("vset.starter"));   // coluna da base
    // Base com conjunto próprio e Único sem coluna: vale a base.
    std::string bases = tu::Replace(tu::ReadFile(tu::RichDir() + "/item_bases.csv"), "item_base.worn_trousers,legs,1,armor:flat:4,,,,,,,f,vset.starter",
                                    "item_base.worn_trousers,legs,1,armor:flat:4,,,,,,,f,vset.iron_guard");
    const auto db2 = RichWith({{"item_bases.csv", bases}});
    EXPECT_EQ(ItemVisualSetId(*db2, Item(2, "item_base.worn_trousers")), std::string("vset.iron_guard"));
}

TEST(inventory_backpack_roundtrips_in_the_save_and_empty_backpack_keeps_the_old_bytes) {
    const ContentDB& db = tu::RichDb();
    SaveData s = NewSave(db);
    const std::string empty = SerializeJson(s, false);
    EXPECT_TRUE(empty.find("backpack") == std::string::npos);                 // vazia: nada novo no arquivo (hash antigo vale)
    ASSERT_TRUE(BackpackAdd(db, s, 0, Item(11, "item_base.bone_helm", Rarity::Rare, 3)) == InvResult::Ok);
    ASSERT_TRUE(BackpackAdd(db, s, 0, Item(12, "item_base.leather_vest")) == InvResult::Ok);
    const std::string text = SerializeJson(s, false);
    SaveData back;
    std::string err;
    ASSERT_TRUE(ParseJson(text, back, &err) == LoadStatus::Ok);
    ASSERT_EQ(back.characters[0].backpack.size(), static_cast<std::size_t>(2));
    EXPECT_EQ(back.characters[0].backpack[0].uid, static_cast<std::uint64_t>(11));
    EXPECT_ENUM_EQ(back.characters[0].backpack[0].rarity, Rarity::Rare);
    EXPECT_EQ(SerializeJson(back, false), text);
}
