// ShatterCore — Encantador (craft.h; docs/16 seção 11). Sem exceções, sem estado global; nenhum número de balanceamento.
#include "shatter/craft.h"

#include <algorithm>
#include <cmath>
#include <limits>

#include "shatter/inventory.h"
#include "shatter/loot.h"

namespace shatter {

namespace {

constexpr std::int64_t kCurrencyCeiling = std::numeric_limits<std::int64_t>::max() / 2;

std::uint64_t Fnv1a(std::uint64_t h, std::string_view text) {
    for (const char c : text) {
        h ^= static_cast<unsigned char>(c);
        h *= 0x100000001B3ull;
    }
    return h;
}

std::int64_t CeilCost(double v) {
    const double c = std::ceil(v - 1e-9);  // a margem evita 52.00000000000001 virar 53
    if (!(c > 0.0)) return 0;
    if (c >= static_cast<double>(kCurrencyCeiling)) return kCurrencyCeiling;
    return static_cast<std::int64_t>(c);
}

bool IsIntegral(double v) { return v == std::floor(v); }

struct Found {
    const ItemInstance* item = nullptr;
    ItemWhere where = ItemWhere::Backpack;
    int slot = -1;
    std::size_t index = 0;
};

Found Locate(const SaveData& s, std::size_t ci, std::uint64_t uid) {
    Found f;
    if (ci >= s.characters.size() || uid == 0) return f;
    const CharacterState& c = s.characters[ci];
    for (std::size_t i = 0; i < c.backpack.size(); ++i) {
        if (c.backpack[i].uid == uid) return Found{&c.backpack[i], ItemWhere::Backpack, -1, i};
    }
    for (std::size_t i = 0; i < s.stash.size(); ++i) {
        if (s.stash[i].uid == uid) return Found{&s.stash[i], ItemWhere::Stash, -1, i};
    }
    for (int sl = 0; sl < kItemSlotCount; ++sl) {
        const auto& e = c.equipment[static_cast<std::size_t>(sl)];
        if (e && e->uid == uid) return Found{&*e, ItemWhere::Equipped, sl, 0};
    }
    return f;
}

bool ContentOk(const ContentDB& db, const ItemInstance& it) {
    if (db.FindItemBase(it.baseId) == nullptr) return false;
    for (const RolledAffix& a : it.affixes)
        if (db.FindAffix(a.affixId) == nullptr) return false;
    return true;
}

int MaxAffixes(Rarity r) { return r == Rarity::Magic ? 2 : (r == Rarity::Rare ? 4 : 0); }

void PrefixesFirst(const ContentDB& db, std::vector<RolledAffix>& v) {
    std::stable_partition(v.begin(), v.end(), [&](const RolledAffix& r) {
        const AffixData* a = db.FindAffix(r.affixId);
        return a != nullptr && a->kind == AffixKind::Prefix;
    });
}

std::uint16_t Bump(std::uint16_t v) { return v == 65535 ? v : static_cast<std::uint16_t>(v + 1); }

// Custo final: base x (1 + fator x (itemLevel - 1)) x mult, arredondado para cima.
double LevelMul(const RulesConstants& r, int itemLevel) {
    return 1.0 + r.craftCostLevelFactor * static_cast<double>(std::max(1, itemLevel) - 1);
}

struct AddDraw {
    std::vector<const AffixData*> drawn;
    Pcg32 rng;
};

// Sorteia os candidatos (sem repetição) e deixa o gerador posicionado para o valor do escolhido.
AddDraw DrawOffer(const ContentDB& db, const SaveData& s, const ItemInstance& it, const ItemBaseData& base) {
    AddDraw d;
    d.rng = CraftRng(EffectiveCraftSeed(s), it.uid, it.craftSteps, CraftOp::Add);
    std::vector<const AffixData*> pool = EligibleAffixes(db, base, it.itemLevel, it.affixes, true);
    const int want = db.Rules().addAffixCandidates;
    while (static_cast<int>(d.drawn.size()) < want && !pool.empty()) {
        std::vector<double> w;
        w.reserve(pool.size());
        for (const AffixData* a : pool) w.push_back(a->weight);
        const int pick = PickWeighted(w, d.rng);
        if (pick < 0) break;
        d.drawn.push_back(pool[static_cast<std::size_t>(pick)]);
        pool.erase(pool.begin() + pick);
    }
    return d;
}

void Funds(const SaveData& s, CraftPlan& p) {
    if (CurrencyAmount(s, kGoldId) < p.gold) p.result = CraftResult::NoGold;
    else if (CurrencyAmount(s, kShardsId) < p.shards) p.result = CraftResult::NoShards;
}

// Planeja uma operação (só lê). offerOnly: Adicionar afixo sem escolher candidato (prévia da oferta).
CraftPlan PlanImpl(const ContentDB& db, const SaveData& s, std::size_t ci, std::uint64_t uid, CraftOp op, int arg,
                   bool offerOnly, AffixOffer* offer) {
    CraftPlan p;
    p.op = op;
    p.uid = uid;
    const Found f = Locate(s, ci, uid);
    if (f.item == nullptr) { p.result = CraftResult::NotFound; return p; }
    const ItemInstance& it = *f.item;
    p.where = f.where;
    p.slot = f.slot;
    p.index = f.index;
    if (it.rarity == Rarity::Unique || !it.uniqueId.empty()) { p.result = CraftResult::Unique; return p; }
    const ItemBaseData* base = db.FindItemBase(it.baseId);
    if (base == nullptr || !ContentOk(db, it)) { p.result = CraftResult::UnknownContent; return p; }
    const RulesConstants& R = db.Rules();
    p.after = it;
    p.result = CraftResult::Ok;
    const std::uint64_t seed = EffectiveCraftSeed(s);

    switch (op) {
        case CraftOp::Dismantle: {
            if (f.where == ItemWhere::Equipped) { p.result = CraftResult::EquippedDismantle; return p; }
            const int idx = static_cast<int>(it.rarity);
            if (idx < 0 || idx > 2) { p.result = CraftResult::WrongRarity; return p; }
            p.shardsGain = R.dismantleShards[idx];
            return p;
        }
        case CraftOp::Refine: {
            if (it.rarity != Rarity::Normal) { p.result = CraftResult::WrongRarity; return p; }
            const CraftCostData* row = db.FindCraftCost(CraftOp::Refine, Rarity::Normal, 0);
            if (row == nullptr) { p.result = CraftResult::UnknownContent; return p; }
            const double lvl = LevelMul(R, it.itemLevel);
            p.gold = CeilCost(static_cast<double>(row->goldCost) * lvl);
            p.shards = CeilCost(static_cast<double>(row->shardCost) * lvl);
            p.affixCountMin = 1;
            p.affixCountMax = 2;
            Pcg32 rng = CraftRng(seed, uid, it.craftSteps, CraftOp::Refine);
            const int count = rng.RangeInt(1, 2);
            std::vector<RolledAffix> rolled = RollAffixesFixed(db, *base, it.itemLevel, count, {}, rng);
            if (rolled.empty()) { p.result = CraftResult::NoCandidate; return p; }
            p.after.rarity = Rarity::Magic;
            p.after.affixes = std::move(rolled);
            p.after.craftSteps = Bump(it.craftSteps);
            Funds(s, p);
            return p;
        }
        case CraftOp::Reforge: {
            if (it.rarity != Rarity::Magic && it.rarity != Rarity::Rare) { p.result = CraftResult::WrongRarity; return p; }
            if (it.affixes.empty()) { p.result = CraftResult::NoCandidate; return p; }
            const bool lock = arg != -1;
            if (lock && (R.reforgeLockMax < 1 || arg < 0 || arg >= static_cast<int>(it.affixes.size()) || it.affixes.size() < 2)) {
                p.result = CraftResult::BadIndex;
                return p;
            }
            const CraftCostData* row = db.FindCraftCost(CraftOp::Reforge, it.rarity, 0);
            if (row == nullptr) { p.result = CraftResult::UnknownContent; return p; }
            p.reforgesBefore = it.craftReforges;
            const double mult = std::min(R.reforgeMultCap, 1.0 + R.reforgeStepMult * static_cast<double>(it.craftReforges));
            const double lvl = LevelMul(R, it.itemLevel);
            p.gold = CeilCost(static_cast<double>(row->goldCost) * lvl * mult);
            p.shardsNoLock = CeilCost(static_cast<double>(row->shardCost) * lvl * mult);
            p.shardsWithLock = CeilCost(static_cast<double>(row->shardCost) * lvl * mult * R.reforgeLockCostMult);
            p.shards = lock ? p.shardsWithLock : p.shardsNoLock;
            const int count = static_cast<int>(it.affixes.size());
            std::vector<RolledAffix> kept;
            if (lock) kept.push_back(it.affixes[static_cast<std::size_t>(arg)]);
            Pcg32 rng = CraftRng(seed, uid, it.craftSteps, CraftOp::Reforge);
            std::vector<RolledAffix> result;
            for (int attempt = 0; attempt < 16; ++attempt) {  // o sorteio guloso pode empacar num conjunto pequeno: tenta de novo
                std::vector<RolledAffix> r = RollAffixesFixed(db, *base, it.itemLevel, count, kept, rng);
                if (static_cast<int>(r.size()) == count) { result = std::move(r); break; }
            }
            if (result.empty()) {  // último recurso: mesmos afixos, valores novos (a quantidade nunca muda)
                for (int i = 0; i < count; ++i) {
                    if (lock && i == arg) { result.push_back(it.affixes[static_cast<std::size_t>(i)]); continue; }
                    RolledAffix ra;
                    ra.affixId = it.affixes[static_cast<std::size_t>(i)].affixId;
                    ra.value = RollAffixValue(*db.FindAffix(ra.affixId), rng);
                    result.push_back(std::move(ra));
                }
            }
            if (lock) {  // acha o travado de volta (a ordem pode ter mudado) para o destaque da UI
                for (std::size_t i = 0; i < result.size(); ++i)
                    if (result[i].affixId == kept[0].affixId) p.changedAffix = static_cast<int>(i);
            }
            p.after.affixes = std::move(result);
            p.after.craftSteps = Bump(it.craftSteps);
            p.after.craftReforges = Bump(it.craftReforges);
            Funds(s, p);
            return p;
        }
        case CraftOp::Add: {
            if (it.rarity != Rarity::Magic && it.rarity != Rarity::Rare) { p.result = CraftResult::WrongRarity; return p; }
            if (static_cast<int>(it.affixes.size()) >= MaxAffixes(it.rarity)) { p.result = CraftResult::AffixLimit; return p; }
            if (it.hasInscription) { p.result = CraftResult::AlreadyInscribed; return p; }
            const CraftCostData* row = db.FindCraftCost(CraftOp::Add, it.rarity, 0);
            if (row == nullptr) { p.result = CraftResult::UnknownContent; return p; }
            const double lvl = LevelMul(R, it.itemLevel);
            p.gold = CeilCost(static_cast<double>(row->goldCost) * lvl);
            p.shards = CeilCost(static_cast<double>(row->shardCost) * lvl);
            AddDraw d = DrawOffer(db, s, it, *base);
            if (offer != nullptr) {
                offer->gold = p.gold;
                offer->shards = p.shards;
                for (const AffixData* a : d.drawn) offer->candidates.push_back({a->id, a->minValue, a->maxValue});
            }
            if (d.drawn.empty()) { p.result = CraftResult::NoCandidate; return p; }
            if (offerOnly) return p;
            if (arg < 0 || arg >= static_cast<int>(d.drawn.size())) { p.result = CraftResult::BadIndex; return p; }
            const AffixData* chosen = d.drawn[static_cast<std::size_t>(arg)];
            RolledAffix ra;
            ra.affixId = chosen->id;
            ra.value = RollAffixValue(*chosen, d.rng);
            p.after.affixes.push_back(std::move(ra));
            PrefixesFirst(db, p.after.affixes);
            for (std::size_t i = 0; i < p.after.affixes.size(); ++i)
                if (p.after.affixes[i].affixId == chosen->id) p.changedAffix = static_cast<int>(i);
            p.after.hasInscription = true;
            p.after.craftSteps = Bump(it.craftSteps);
            Funds(s, p);
            return p;
        }
        case CraftOp::Polish: {
            if (it.rarity != Rarity::Magic && it.rarity != Rarity::Rare) { p.result = CraftResult::WrongRarity; return p; }
            if (arg < 0 || arg >= static_cast<int>(it.affixes.size())) { p.result = CraftResult::BadIndex; return p; }
            const RolledAffix& ra = it.affixes[static_cast<std::size_t>(arg)];
            const AffixData* a = db.FindAffix(ra.affixId);
            if (a == nullptr) { p.result = CraftResult::UnknownContent; return p; }
            p.changedAffix = arg;
            p.polishFrom = ra.value;
            p.polishTo = ra.value;
            if (static_cast<int>(ra.polish) >= R.polishMaxSteps) { p.result = CraftResult::PolishMax; return p; }
            double v = ra.value + R.polishStepFraction * (a->maxValue - a->minValue);
            if (IsIntegral(a->minValue) && IsIntegral(a->maxValue)) {
                v = std::floor(v + 0.5);
                if (v <= ra.value) v = ra.value + 1.0;  // um passo sempre anda pelo menos 1 em afixo inteiro
            }
            v = std::min(v, a->maxValue);
            if (!(v > ra.value)) { p.result = CraftResult::PolishMax; return p; }
            p.polishStep = static_cast<int>(ra.polish) + 1;
            p.polishTo = v;
            const CraftCostData* row = db.FindCraftCost(CraftOp::Polish, it.rarity, p.polishStep);
            if (row == nullptr) { p.result = CraftResult::UnknownContent; return p; }
            const double lvl = LevelMul(R, it.itemLevel);
            p.gold = CeilCost(static_cast<double>(row->goldCost) * lvl);
            p.shards = CeilCost(static_cast<double>(row->shardCost) * lvl);
            p.after.affixes[static_cast<std::size_t>(arg)].value = v;
            p.after.affixes[static_cast<std::size_t>(arg)].polish = static_cast<std::uint8_t>(p.polishStep);
            Funds(s, p);
            return p;
        }
    }
    p.result = CraftResult::UnknownContent;
    return p;
}

}  // namespace

std::uint64_t EffectiveCraftSeed(const SaveData& s) {
    if (s.craftSeed != 0) return s.craftSeed;
    std::uint64_t h = 0xCBF29CE484222325ull;
    if (!s.characters.empty()) {
        h = Fnv1a(h, s.characters[0].name);
        h = Fnv1a(h, std::string_view("\0", 1));
        h = Fnv1a(h, s.characters[0].classId);
    }
    h = Mix64(h ^ 0x43524146544C4F47ull);  // "CRAFTLOG"
    return h != 0 ? h : 0x9E3779B97F4A7C15ull;
}

void EnsureCraftSeed(SaveData& s) {
    if (s.craftSeed == 0) s.craftSeed = EffectiveCraftSeed(s);
}

Pcg32 CraftRng(std::uint64_t craftSeed, std::uint64_t itemUid, std::uint16_t craftSteps, CraftOp op) {
    const std::uint64_t perItem = Mix64(craftSeed ^ Mix64(itemUid ^ 0xC2AF7C0DE5EEDull));
    const std::uint64_t index = (static_cast<std::uint64_t>(craftSteps) << 8) | static_cast<std::uint64_t>(op);
    return Pcg32::ForStream(perItem, RngStream::Crafting, index);
}

std::int64_t CurrencyAmount(const SaveData& s, std::string_view id) {
    for (const StackEntry& e : s.currencies)
        if (e.id == id) return e.amount;
    return 0;
}

void CurrencyAdd(SaveData& s, const ContentId& id, std::int64_t delta) {
    for (StackEntry& e : s.currencies) {
        if (e.id != id) continue;
        std::int64_t v = e.amount;
        if (delta > 0) v = (v > kCurrencyCeiling - delta) ? kCurrencyCeiling : v + delta;
        else v = (v + delta < 0) ? 0 : v + delta;
        e.amount = v;
        return;
    }
    if (delta > 0) s.currencies.push_back(StackEntry{id, std::min(delta, kCurrencyCeiling)});
}

CraftPlan PlanCraft(const ContentDB& db, const SaveData& s, std::size_t characterIndex, std::uint64_t uid, CraftOp op, int arg) {
    return PlanImpl(db, s, characterIndex, uid, op, arg, false, nullptr);
}

void CommitCraft(SaveData& s, std::size_t characterIndex, const CraftPlan& plan) {
    if (plan.result != CraftResult::Ok || characterIndex >= s.characters.size()) return;
    // O plano é conferido contra o save de novo: plano velho (item mudou de lugar) não faz nada.
    const Found f = Locate(s, characterIndex, plan.uid);
    if (f.item == nullptr || f.where != plan.where || f.slot != plan.slot || f.index != plan.index) return;
    if (CurrencyAmount(s, kGoldId) < plan.gold || CurrencyAmount(s, kShardsId) < plan.shards) return;
    CharacterState& c = s.characters[characterIndex];
    if (plan.op == CraftOp::Refine || plan.op == CraftOp::Reforge || plan.op == CraftOp::Add) EnsureCraftSeed(s);
    if (plan.op == CraftOp::Dismantle) {
        std::vector<ItemInstance>& box = plan.where == ItemWhere::Stash ? s.stash : c.backpack;
        box.erase(box.begin() + static_cast<std::ptrdiff_t>(plan.index));
        CurrencyAdd(s, kShardsId, plan.shardsGain);
        return;
    }
    if (plan.where == ItemWhere::Backpack) c.backpack[plan.index] = plan.after;
    else if (plan.where == ItemWhere::Stash) s.stash[plan.index] = plan.after;
    else c.equipment[static_cast<std::size_t>(plan.slot)] = plan.after;
    CurrencyAdd(s, kGoldId, -plan.gold);
    CurrencyAdd(s, kShardsId, -plan.shards);
}

AffixOffer OfferAddAffix(const ContentDB& db, const SaveData& s, std::size_t characterIndex, std::uint64_t uid) {
    AffixOffer o;
    const CraftPlan p = PlanImpl(db, s, characterIndex, uid, CraftOp::Add, -1, true, &o);
    o.result = p.result;
    if (p.result != CraftResult::Ok) o.candidates.clear();
    return o;
}

namespace {
CraftResult Run(const ContentDB& db, SaveData& s, std::size_t ci, std::uint64_t uid, CraftOp op, int arg, CraftPlan* out) {
    CraftPlan p = PlanCraft(db, s, ci, uid, op, arg);
    CommitCraft(s, ci, p);
    const CraftResult r = p.result;
    if (out != nullptr) *out = std::move(p);
    return r;
}
}  // namespace

CraftResult CraftRefine(const ContentDB& db, SaveData& s, std::size_t ci, std::uint64_t uid, CraftPlan* out) {
    return Run(db, s, ci, uid, CraftOp::Refine, 0, out);
}
CraftResult CraftReforge(const ContentDB& db, SaveData& s, std::size_t ci, std::uint64_t uid, int lockedAffixIndex, CraftPlan* out) {
    return Run(db, s, ci, uid, CraftOp::Reforge, lockedAffixIndex, out);
}
CraftResult CraftAddAffix(const ContentDB& db, SaveData& s, std::size_t ci, std::uint64_t uid, int candidateIndex, CraftPlan* out) {
    return Run(db, s, ci, uid, CraftOp::Add, candidateIndex, out);
}
CraftResult CraftPolish(const ContentDB& db, SaveData& s, std::size_t ci, std::uint64_t uid, int affixIndex, CraftPlan* out) {
    return Run(db, s, ci, uid, CraftOp::Polish, affixIndex, out);
}
CraftResult CraftDismantle(const ContentDB& db, SaveData& s, std::size_t ci, std::uint64_t uid, CraftPlan* out) {
    return Run(db, s, ci, uid, CraftOp::Dismantle, 0, out);
}

bool HasRunningExpedition(const SaveData& s, std::size_t characterIndex) {
    for (const SavedExpedition& e : s.expeditions)
        if (e.status == ExpeditionStatus::Running && e.characterIndex >= 0 &&
            static_cast<std::size_t>(e.characterIndex) == characterIndex)
            return true;
    return false;
}

}  // namespace shatter
