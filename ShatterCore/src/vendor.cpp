// ShatterCore — Vendedor e Frasco de Recarga (vendor.h).
#include "shatter/vendor.h"

#include <algorithm>
#include <cmath>

namespace shatter {

namespace {

std::size_t Capacity(const ContentDB& db) { return static_cast<std::size_t>(std::max(1, db.Rules().vendorBuybackSlots)); }

}  // namespace

BuybackInfo GetBuybackInfo(const ContentDB& db, const SaveData& s) {
    BuybackInfo b;
    b.count = static_cast<int>(s.vendorBuyback.size());
    b.capacity = static_cast<int>(Capacity(db));
    if (s.vendorBuyback.size() >= Capacity(db)) {
        b.wouldEvict = true;
        b.evictRarity = s.vendorBuyback.back().item.rarity;
    }
    return b;
}

VendorResult VendorSell(const ContentDB& db, SaveData& s, std::size_t ci, Container from, std::uint64_t uid,
                        std::int64_t* goldGained, bool* evicted, Rarity* evictedRarity) {
    if (goldGained != nullptr) *goldGained = 0;
    if (evicted != nullptr) *evicted = false;
    const ItemInstance* found = FindInContainer(s, ci, from, uid);
    if (found == nullptr) return VendorResult::NotFound;
    ItemInstance item = *found;
    std::int64_t paid = 0;
    if (SellItem(db, s, ci, from, uid, &paid) != InvResult::Ok) return VendorResult::NotFound;
    s.vendorBuyback.insert(s.vendorBuyback.begin(), BuybackEntry{std::move(item), paid});
    while (s.vendorBuyback.size() > Capacity(db)) {
        if (evicted != nullptr) *evicted = true;
        if (evictedRarity != nullptr) *evictedRarity = s.vendorBuyback.back().item.rarity;
        s.vendorBuyback.pop_back();
    }
    if (goldGained != nullptr) *goldGained = paid;
    return VendorResult::Ok;
}

std::int64_t BuybackPrice(const ContentDB& db, std::int64_t paid) {
    const double v = std::ceil(static_cast<double>(paid) * db.Rules().vendorBuybackPriceFactor - 1e-9);
    return v > 0.0 ? static_cast<std::int64_t>(v) : 0;
}

VendorResult VendorBuyback(const ContentDB& db, SaveData& s, std::size_t ci, std::uint64_t uid, std::int64_t* goldSpent) {
    if (goldSpent != nullptr) *goldSpent = 0;
    std::size_t at = s.vendorBuyback.size();
    for (std::size_t i = 0; i < s.vendorBuyback.size(); ++i) {
        if (s.vendorBuyback[i].item.uid == uid) { at = i; break; }
    }
    if (ci >= s.characters.size() || at >= s.vendorBuyback.size()) return VendorResult::NotFound;
    const std::int64_t price = BuybackPrice(db, s.vendorBuyback[at].paid);
    if (static_cast<int>(s.characters[ci].backpack.size()) >= db.Rules().inventoryCapacity) return VendorResult::Full;
    if (CurrencyAmount(s, kGoldId) < price) return VendorResult::NoGold;
    const InvResult r = BackpackAdd(db, s, ci, s.vendorBuyback[at].item);
    if (r != InvResult::Ok) return r == InvResult::Full ? VendorResult::Full : VendorResult::UnknownContent;
    CurrencyAdd(s, kGoldId, -price);
    s.vendorBuyback.erase(s.vendorBuyback.begin() + static_cast<std::ptrdiff_t>(at));
    if (goldSpent != nullptr) *goldSpent = price;
    return VendorResult::Ok;
}

VendorResult VendorBuy(const ContentDB& db, SaveData& s, std::string_view stockId, std::int64_t qty, std::int64_t* goldSpent) {
    if (goldSpent != nullptr) *goldSpent = 0;
    const VendorStockData* row = db.FindVendorStock(stockId);
    if (row == nullptr) return VendorResult::NotFound;
    if (qty < 1) return VendorResult::BadQuantity;
    const std::int64_t cap = static_cast<std::int64_t>(row->carryCap);
    const std::int64_t owned = CurrencyAmount(s, row->refId);
    if (qty > cap || owned + qty > cap) return VendorResult::CarryCap;
    const std::int64_t cost = row->priceGold * qty;  // qty <= carryCap (<= 1e6) e preço <= 1e12: cabe em int64
    if (CurrencyAmount(s, kGoldId) < cost) return VendorResult::NoGold;
    CurrencyAdd(s, kGoldId, -cost);
    CurrencyAdd(s, row->refId, qty);
    if (goldSpent != nullptr) *goldSpent = cost;
    return VendorResult::Ok;
}

FlaskOutcome UseRefillFlask(const ContentDB& db, SaveData& s, PotionBelt& belt, FlaskContext context) {
    FlaskOutcome o;
    o.flasksLeft = static_cast<int>(CurrencyAmount(s, kRefillFlaskId));
    if (context == FlaskContext::Arena) { o.result = FlaskResult::ArenaLocked; return o; }
    if (context == FlaskContext::Idle) { o.result = FlaskResult::IdleForbidden; return o; }
    if (o.flasksLeft <= 0) { o.result = FlaskResult::NoFlask; return o; }
    int best = -1;
    const PotionData* bestData = nullptr;
    for (std::size_t i = 0; i < belt.slots.size(); ++i) {
        const PotionData* p = db.FindPotion(belt.slots[i].potionId);
        if (p == nullptr || belt.slots[i].charges >= p->maxCharges) continue;
        if (best < 0 || belt.slots[i].charges < belt.slots[static_cast<std::size_t>(best)].charges) {  // empate: a primeira
            best = static_cast<int>(i);
            bestData = p;
        }
    }
    if (bestData == nullptr) {
        o.result = belt.slots.empty() ? FlaskResult::UnknownContent : FlaskResult::PotionsFull;
        return o;
    }
    if (belt.lockoutRemaining > 1e-9) { o.result = FlaskResult::LockedOut; return o; }
    PotionSlotState& slot = belt.slots[static_cast<std::size_t>(best)];
    slot.charges = std::min(bestData->maxCharges, slot.charges + std::max(1, db.Rules().refillFlaskCharges));
    if (slot.charges >= bestData->maxCharges) slot.rechargeRemaining = 0.0;
    belt.lockoutRemaining = bestData->globalLockout > 0.0 ? bestData->globalLockout : db.Rules().potionLockout;
    CurrencyAdd(s, kRefillFlaskId, -1);
    o.result = FlaskResult::Ok;
    o.potionIndex = best;
    o.chargesAfter = slot.charges;
    o.flasksLeft = static_cast<int>(CurrencyAmount(s, kRefillFlaskId));
    return o;
}

}  // namespace shatter
