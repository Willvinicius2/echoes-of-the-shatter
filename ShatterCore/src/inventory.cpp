// ShatterCore — inventário, equipamento, comparação e venda (inventory.h).
#include "shatter/inventory.h"

#include <algorithm>
#include <cmath>

#include "shatter/loot.h"

namespace shatter {

namespace {

bool SlotCompatible(ItemSlot target, ItemSlot base) {
    if (target == base) return true;
    const bool ringT = target == ItemSlot::Ring || target == ItemSlot::Ring2;
    const bool ringB = base == ItemSlot::Ring || base == ItemSlot::Ring2;
    return ringT && ringB;
}

CharacterState* Hero(SaveData& s, std::size_t i) { return i < s.characters.size() ? &s.characters[i] : nullptr; }
const CharacterState* Hero(const SaveData& s, std::size_t i) { return i < s.characters.size() ? &s.characters[i] : nullptr; }

std::vector<ItemInstance>* Box(SaveData& s, CharacterState* c, Container where) {
    if (where == Container::Stash) return &s.stash;
    return c != nullptr ? &c->backpack : nullptr;
}

std::size_t IndexOf(const std::vector<ItemInstance>& v, std::uint64_t uid) {
    for (std::size_t i = 0; i < v.size(); ++i)
        if (v[i].uid == uid) return i;
    return v.size();
}

bool ContentOk(const ContentDB& db, const ItemInstance& it) {
    if (db.FindItemBase(it.baseId) == nullptr) return false;
    for (const RolledAffix& a : it.affixes)
        if (db.FindAffix(a.affixId) == nullptr) return false;
    return it.uniqueId.empty() || db.FindUnique(it.uniqueId) != nullptr;
}

// Mesmos modificadores do BuildStatBlock (source = "item:<uid>").
void AddItemMods(const ContentDB& db, StatBlock& sb, const ItemInstance& it) {
    sb.AddModifiers(ItemModifiers(db, it));
    if (it.uniqueId.empty()) return;
    if (const UniqueData* u = db.FindUnique(it.uniqueId)) {
        for (const Modifier& m : u->fixedMods) {
            Modifier mod = m;
            mod.source = "item:" + std::to_string(it.uid);
            sb.AddModifier(mod);
        }
    }
}

int RarityRank(Rarity r) { return static_cast<int>(r); }

double WeaponDps(const ContentDB& db, const CharacterState& c) {
    const auto& w = c.equipment[static_cast<std::size_t>(ItemSlot::MainHand)];
    if (!w) return 0.0;
    const ItemBaseData* base = db.FindItemBase(w->baseId);
    if (base == nullptr) return 0.0;
    StatBlock sb;
    if (!BuildStatBlock(db, c, sb)) return 0.0;
    double raw = 0.0;
    for (double d : base->weaponDamage) raw += d;
    const double perHit = sb.ApplyTagged(StatId::Damage, base->weaponTags, raw);
    const double time = base->attackTime > 0.0 ? base->attackTime : 1.0;
    return perHit * sb.Get(StatId::AttackSpeed) / time;
}

}  // namespace

InventoryInfo GetInventoryInfo(const ContentDB& db, const SaveData& s, std::size_t characterIndex) {
    InventoryInfo info;
    info.backpackCapacity = db.Rules().inventoryCapacity;
    info.stashCapacity = db.Rules().stashCapacity;
    if (const CharacterState* c = Hero(s, characterIndex)) info.backpackUsed = static_cast<int>(c->backpack.size());
    info.stashUsed = static_cast<int>(s.stash.size());
    return info;
}

const ItemInstance* FindInContainer(const SaveData& s, std::size_t characterIndex, Container where, std::uint64_t uid) {
    const std::vector<ItemInstance>* v = nullptr;
    if (where == Container::Stash) v = &s.stash;
    else if (const CharacterState* c = Hero(s, characterIndex)) v = &c->backpack;
    if (v == nullptr) return nullptr;
    const std::size_t i = IndexOf(*v, uid);
    return i < v->size() ? &(*v)[i] : nullptr;
}

InvResult BackpackAdd(const ContentDB& db, SaveData& s, std::size_t characterIndex, ItemInstance item) {
    CharacterState* c = Hero(s, characterIndex);
    if (c == nullptr) return InvResult::NotFound;
    if (!ContentOk(db, item)) return InvResult::UnknownContent;
    if (static_cast<int>(c->backpack.size()) >= db.Rules().inventoryCapacity) return InvResult::Full;
    c->backpack.push_back(std::move(item));
    return InvResult::Ok;
}

InvResult StashAdd(const ContentDB& db, SaveData& s, ItemInstance item) {
    if (!ContentOk(db, item)) return InvResult::UnknownContent;
    if (static_cast<int>(s.stash.size()) >= db.Rules().stashCapacity) return InvResult::Full;
    s.stash.push_back(std::move(item));
    return InvResult::Ok;
}

InvResult SortBackpack(const ContentDB& db, SaveData& s, std::size_t characterIndex) {
    CharacterState* c = Hero(s, characterIndex);
    if (c == nullptr) return InvResult::NotFound;
    auto slotOf = [&](const ItemInstance& it) {
        const ItemBaseData* b = db.FindItemBase(it.baseId);
        return b != nullptr ? static_cast<int>(b->slot) : 1000;
    };
    std::stable_sort(c->backpack.begin(), c->backpack.end(), [&](const ItemInstance& a, const ItemInstance& b) {
        const int sa = slotOf(a), sb = slotOf(b);
        if (sa != sb) return sa < sb;
        if (a.rarity != b.rarity) return RarityRank(a.rarity) > RarityRank(b.rarity);
        if (a.itemLevel != b.itemLevel) return a.itemLevel > b.itemLevel;
        if (a.baseId != b.baseId) return a.baseId < b.baseId;
        return a.uid < b.uid;
    });
    return InvResult::Ok;
}

InvResult MoveItem(const ContentDB& db, SaveData& s, std::size_t characterIndex, std::uint64_t uid, Container to) {
    CharacterState* c = Hero(s, characterIndex);
    if (c == nullptr) return InvResult::NotFound;
    const Container from = to == Container::Stash ? Container::Backpack : Container::Stash;
    std::vector<ItemInstance>* src = Box(s, c, from);
    std::vector<ItemInstance>* dst = Box(s, c, to);
    const std::size_t i = IndexOf(*src, uid);
    if (i >= src->size()) return InvResult::NotFound;
    const int cap = to == Container::Stash ? db.Rules().stashCapacity : db.Rules().inventoryCapacity;
    if (static_cast<int>(dst->size()) >= cap) return InvResult::Full;
    dst->push_back(std::move((*src)[i]));
    src->erase(src->begin() + static_cast<std::ptrdiff_t>(i));
    return InvResult::Ok;
}

ItemSlot DefaultSlotFor(const ContentDB& db, const CharacterState& c, const ItemInstance& item) {
    const ItemBaseData* b = db.FindItemBase(item.baseId);
    if (b == nullptr) return ItemSlot::Count;
    if (b->slot == ItemSlot::Ring || b->slot == ItemSlot::Ring2) {
        if (!c.equipment[static_cast<std::size_t>(ItemSlot::Ring)]) return ItemSlot::Ring;
        if (!c.equipment[static_cast<std::size_t>(ItemSlot::Ring2)]) return ItemSlot::Ring2;
        return ItemSlot::Ring;
    }
    return b->slot;
}

EquipOutcome Equip(const ContentDB& db, SaveData& s, std::size_t characterIndex, std::uint64_t uid, ItemSlot slot,
                   StatBlock* stats) {
    EquipOutcome out;
    CharacterState* c = Hero(s, characterIndex);
    if (c == nullptr) { out.result = InvResult::NotFound; return out; }
    const std::size_t i = IndexOf(c->backpack, uid);
    if (i >= c->backpack.size()) { out.result = InvResult::NotFound; return out; }
    const ItemInstance& cand = c->backpack[i];
    const ItemBaseData* base = db.FindItemBase(cand.baseId);
    if (!ContentOk(db, cand)) { out.result = InvResult::UnknownContent; return out; }
    if (slot == ItemSlot::Count) slot = DefaultSlotFor(db, *c, cand);
    if (static_cast<int>(slot) < 0 || static_cast<int>(slot) >= kItemSlotCount) { out.result = InvResult::SlotMismatch; return out; }
    out.slot = slot;
    if (!SlotCompatible(slot, base->slot)) { out.result = InvResult::SlotMismatch; return out; }
    if (!db.Rules().equipSlotEnabled[static_cast<std::size_t>(slot)]) { out.result = InvResult::SlotLocked; return out; }

    ItemInstance incoming = std::move(c->backpack[i]);
    c->backpack.erase(c->backpack.begin() + static_cast<std::ptrdiff_t>(i));
    std::optional<ItemInstance>& place = c->equipment[static_cast<std::size_t>(slot)];
    if (place) {
        out.displaced = true;
        out.displacedUid = place->uid;
        if (stats != nullptr) stats->RemoveModifiersFrom("item:" + std::to_string(place->uid));
        c->backpack.push_back(std::move(*place));  // sempre cabe: o novo item acabou de sair da Mochila
    }
    if (stats != nullptr) AddItemMods(db, *stats, incoming);
    place = std::move(incoming);
    return out;
}

EquipOutcome Unequip(const ContentDB& db, SaveData& s, std::size_t characterIndex, ItemSlot slot, StatBlock* stats) {
    EquipOutcome out;
    CharacterState* c = Hero(s, characterIndex);
    if (c == nullptr) { out.result = InvResult::NotFound; return out; }
    if (static_cast<int>(slot) < 0 || static_cast<int>(slot) >= kItemSlotCount) { out.result = InvResult::SlotMismatch; return out; }
    out.slot = slot;
    std::optional<ItemInstance>& place = c->equipment[static_cast<std::size_t>(slot)];
    if (!place) { out.result = InvResult::SlotEmpty; return out; }
    if (static_cast<int>(c->backpack.size()) >= db.Rules().inventoryCapacity) { out.result = InvResult::Full; return out; }
    out.displaced = true;
    out.displacedUid = place->uid;
    if (stats != nullptr) stats->RemoveModifiersFrom("item:" + std::to_string(place->uid));
    c->backpack.push_back(std::move(*place));
    place.reset();
    return out;
}

ItemComparison CompareItem(const ContentDB& db, const CharacterState& c, const ItemInstance& item, ItemSlot slot) {
    ItemComparison cmp;
    const ItemBaseData* base = db.FindItemBase(item.baseId);
    if (base == nullptr || !ContentOk(db, item)) { cmp.result = InvResult::UnknownContent; return cmp; }
    if (slot == ItemSlot::Count) slot = DefaultSlotFor(db, c, item);
    if (static_cast<int>(slot) < 0 || static_cast<int>(slot) >= kItemSlotCount || !SlotCompatible(slot, base->slot)) {
        cmp.result = InvResult::SlotMismatch;
        return cmp;
    }
    cmp.slot = slot;
    if (!db.Rules().equipSlotEnabled[static_cast<std::size_t>(slot)]) { cmp.result = InvResult::SlotLocked; return cmp; }
    const auto& cur = c.equipment[static_cast<std::size_t>(slot)];
    cmp.equippedUid = cur ? cur->uid : 0;

    CharacterState with = c;
    with.equipment[static_cast<std::size_t>(slot)] = item;
    StatBlock before, after;
    if (!BuildStatBlock(db, c, before) || !BuildStatBlock(db, with, after)) { cmp.result = InvResult::UnknownContent; return cmp; }
    for (int i = 0; i < kStatCount; ++i) {
        const StatId id = static_cast<StatId>(i);
        const double a = before.Get(id), b = after.Get(id);
        if (std::fabs(a - b) > 1e-9) cmp.deltas.push_back({id, a, b});
    }
    cmp.isWeapon = base->slot == ItemSlot::MainHand;
    if (cmp.isWeapon) {
        cmp.weaponDpsBefore = WeaponDps(db, c);
        cmp.weaponDpsAfter = WeaponDps(db, with);
    }
    return cmp;
}

std::int64_t SellValue(const ContentDB& db, const ItemInstance& item) {
    const RulesConstants& r = db.Rules();
    const int idx = std::clamp(static_cast<int>(item.rarity), 0, kRarityCount - 1);
    const double lvl = static_cast<double>(std::max(1, item.itemLevel) - 1);
    const double v = std::floor(static_cast<double>(r.sellPrice[idx]) * (1.0 + r.sellLevelFactor * lvl) + 0.5);
    return v < 0.0 ? 0 : static_cast<std::int64_t>(v);
}

InvResult SellItem(const ContentDB& db, SaveData& s, std::size_t characterIndex, Container from, std::uint64_t uid,
                   std::int64_t* goldGained) {
    CharacterState* c = Hero(s, characterIndex);
    if (c == nullptr) return InvResult::NotFound;
    std::vector<ItemInstance>* box = Box(s, c, from);
    const std::size_t i = IndexOf(*box, uid);
    if (i >= box->size()) return InvResult::NotFound;
    const std::int64_t value = SellValue(db, (*box)[i]);
    box->erase(box->begin() + static_cast<std::ptrdiff_t>(i));
    bool found = false;
    for (StackEntry& e : s.currencies) {
        if (e.id == kGoldId) {
            e.amount += value;
            found = true;
            break;
        }
    }
    if (!found) s.currencies.push_back(StackEntry{kGoldId, value});
    if (goldGained != nullptr) *goldGained = value;
    return InvResult::Ok;
}

InvResult DiscardItem(SaveData& s, std::size_t characterIndex, Container from, std::uint64_t uid) {
    CharacterState* c = Hero(s, characterIndex);
    if (c == nullptr) return InvResult::NotFound;
    std::vector<ItemInstance>* box = Box(s, c, from);
    const std::size_t i = IndexOf(*box, uid);
    if (i >= box->size()) return InvResult::NotFound;
    box->erase(box->begin() + static_cast<std::ptrdiff_t>(i));
    return InvResult::Ok;
}

PickupDest PickupItem(const ContentDB& db, SaveData& s, std::size_t characterIndex, ItemInstance item) {
    CharacterState* c = Hero(s, characterIndex);
    if (c == nullptr) return PickupDest::Full;
    if (static_cast<int>(c->backpack.size()) < db.Rules().inventoryCapacity) {
        c->backpack.push_back(std::move(item));
        return PickupDest::Backpack;
    }
    if (item.rarity == Rarity::Unique && static_cast<int>(s.stash.size()) < db.Rules().stashCapacity) {
        s.stash.push_back(std::move(item));
        return PickupDest::Stash;
    }
    return PickupDest::Full;
}

std::string ItemVisualSetId(const ContentDB& db, const ItemInstance& item) {
    if (!item.uniqueId.empty()) {
        if (const UniqueData* u = db.FindUnique(item.uniqueId))
            if (!u->visualSetId.empty()) return u->visualSetId;
    }
    if (const ItemBaseData* b = db.FindItemBase(item.baseId))
        if (!b->visualSetId.empty()) return b->visualSetId;
    return kFallbackVisualSet;
}

}  // namespace shatter
