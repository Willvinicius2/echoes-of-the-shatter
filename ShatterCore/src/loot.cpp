// ShatterCore — rolagem de loot (só o fluxo de RNG Loot) e conversão de itens em modificadores.
#include "shatter/loot.h"

#include <algorithm>
#include <cmath>

namespace shatter {

namespace {

constexpr int kMaxTableDepth = 8;

bool IsIntegral(double v) { return v == std::floor(v); }

void AddStack(std::vector<StackEntry>& stacks, const ContentId& id, std::int64_t amount) {
    for (StackEntry& s : stacks) {
        if (s.id == id) {
            s.amount += amount;
            return;
        }
    }
    stacks.push_back({id, amount});
}

struct RollState {
    const ContentDB& db;
    const LootContext& ctx;
    Pcg32& rng;
    LootDrop& out;
    bool idle() const { return ctx.mode == LootMode::Idle; }
};

bool IsTopTier(LootEntryKind k) {
    return k == LootEntryKind::Unique || k == LootEntryKind::SpecBook || k == LootEntryKind::MapStone ||
           k == LootEntryKind::EchoFragment;
}

void RollTable(RollState& st, const LootTableData& table, int depth);

// Efetiva UMA entrada (a escolhida no sorteio ponderado ou uma entrada fixa que caiu).
void EmitEntry(RollState& st, const LootTableData& table, const LootEntry& e, int depth) {
    const RulesConstants& rules = st.db.Rules();
    {
        switch (e.kind) {
            case LootEntryKind::Nothing:
                break;
            case LootEntryKind::Stack: {
                const std::int64_t lo = e.minAmount, hi = e.maxAmount < e.minAmount ? e.minAmount : e.maxAmount;
                const std::int32_t base = st.rng.RangeInt(static_cast<std::int32_t>(std::min<std::int64_t>(lo, 2147483647)),
                                                          static_cast<std::int32_t>(std::min<std::int64_t>(hi, 2147483647)));
                double amount = static_cast<double>(base) * st.ctx.quantityMult;
                if (st.ctx.mode == LootMode::Manual) amount *= rules.fervorGoldMatMult;
                std::int64_t n = static_cast<std::int64_t>(std::floor(amount));
                if (n < 1) n = 1;
                AddStack(st.out.stacks, e.refId, n);
                break;
            }
            case LootEntryKind::SpecBook:
            case LootEntryKind::MapStone:
            case LootEntryKind::EchoFragment: {
                const std::int32_t n = st.rng.RangeInt(static_cast<std::int32_t>(std::min<std::int64_t>(e.minAmount, 2147483647)),
                                                       static_cast<std::int32_t>(std::min<std::int64_t>(e.maxAmount, 2147483647)));
                AddStack(st.out.stacks, e.refId, n < 1 ? 1 : n);
                break;
            }
            case LootEntryKind::ItemBase: {
                const ItemBaseData* base = st.db.FindItemBase(e.refId);
                if (base == nullptr) break;
                std::vector<double> rw = {table.rarityWeights[0], table.rarityWeights[1], table.rarityWeights[2]};
                if (st.ctx.mode == LootMode::Manual) rw[2] *= rules.fervorRareChanceMult;
                const int ri = PickWeighted(rw, st.rng);
                Rarity rarity = ri == 2 ? Rarity::Rare : (ri == 1 ? Rarity::Magic : Rarity::Normal);
                if (rarity == Rarity::Rare && st.idle() && st.ctx.maxRares >= 0 &&
                    st.ctx.raresAlreadyDropped + st.out.raresDropped >= st.ctx.maxRares) {
                    rarity = Rarity::Magic;  // teto de Raros: o excedente vira Mágico, sem nova rolagem
                }
                ItemInstance item;
                item.uid = st.ctx.nextItemUid ? (*st.ctx.nextItemUid)++ : 0;
                item.baseId = base->id;
                item.rarity = rarity;
                item.itemLevel = st.ctx.areaLevel < 1 ? 1 : st.ctx.areaLevel;
                item.affixes = RollAffixes(st.db, *base, rarity, item.itemLevel, st.rng);
                if (rarity == Rarity::Rare) ++st.out.raresDropped;
                st.out.items.push_back(std::move(item));
                break;
            }
            case LootEntryKind::Unique: {
                if (st.idle()) break;  // nunca no idle
                const UniqueData* u = st.db.FindUnique(e.refId);
                if (u == nullptr) break;
                ItemInstance item;
                item.uid = st.ctx.nextItemUid ? (*st.ctx.nextItemUid)++ : 0;
                item.baseId = u->baseId;
                item.rarity = Rarity::Unique;
                item.uniqueId = u->id;
                item.itemLevel = st.ctx.areaLevel < 1 ? 1 : st.ctx.areaLevel;
                st.out.items.push_back(std::move(item));
                break;
            }
            case LootEntryKind::Table: {
                const LootTableData* sub = st.db.FindLootTable(e.refId);
                if (sub != nullptr) RollTable(st, *sub, depth + 1);
                break;
            }
        }
    }
}

void RollTable(RollState& st, const LootTableData& table, int depth) {
    if (depth > kMaxTableDepth) return;

    // Entradas FIXAS (docs/13, item 9): só no Manual, só na tabela de topo, fora do sorteio ponderado.
    // Cada entrada fixa consome exatamente 1 número do fluxo Loot, tenha caído ou não (posição do fluxo estável).
    if (depth == 1 && !st.idle()) {
        if (st.ctx.bossProgress != nullptr) {  // contador fora da faixa (só por código; o save recusa): vale 0
            if (st.ctx.bossProgress->kills < 0) st.ctx.bossProgress->kills = 0;
            if (st.ctx.bossProgress->killsSinceUnique < 0) st.ctx.bossProgress->killsSinceUnique = 0;
        }
        bool uniqueDropped = false;
        bool anyFixed = false;
        for (const LootEntry& e : table.entries) {
            if (!e.IsFixed()) continue;
            if (st.ctx.areaLevel < e.minAreaLevel || st.ctx.areaLevel > e.maxAreaLevel) continue;
            anyFixed = true;
            bool drop = st.rng.Chance(e.fixedChance);
            if (st.ctx.bossProgress != nullptr) {
                if (e.guaranteeFirstKill && st.ctx.bossProgress->kills <= 0) drop = true;
                // `killsSinceUnique + 1 >= pity` sem somar (INT_MAX estouraria); contador negativo vale 0.
                if (e.pityKills > 0 && st.ctx.bossProgress->killsSinceUnique >= e.pityKills - 1) drop = true;
            }
            if (!drop) continue;
            uniqueDropped = true;
            EmitEntry(st, table, e, depth);
        }
        if (st.ctx.bossProgress != nullptr) {
            // Contadores saturam em kMaxBossCounter (sem estouro de int com sinal).
            BossProgressEntry& bp = *st.ctx.bossProgress;
            if (bp.kills < kMaxBossCounter) ++bp.kills;
            else bp.kills = kMaxBossCounter;
            if (anyFixed && uniqueDropped) bp.killsSinceUnique = 0;
            else if (bp.killsSinceUnique < kMaxBossCounter) ++bp.killsSinceUnique;
            else bp.killsSinceUnique = kMaxBossCounter;
        }
    }

    for (int roll = 0; roll < table.rolls; ++roll) {
        if (!st.rng.Chance(table.dropChance)) continue;

        // Entradas válidas para o nível de área e o modo (ordem da tabela).
        std::vector<const LootEntry*> valid;
        std::vector<double> weights;
        for (const LootEntry& e : table.entries) {
            if (e.IsFixed()) continue;
            if (st.ctx.areaLevel < e.minAreaLevel || st.ctx.areaLevel > e.maxAreaLevel) continue;
            if (st.idle() && (e.manualOnly || IsTopTier(e.kind))) continue;  // dupla checagem do idle
            valid.push_back(&e);
            weights.push_back(e.weight);
        }
        const int pick = PickWeighted(weights, st.rng);
        if (pick < 0) continue;
        EmitEntry(st, table, *valid[static_cast<std::size_t>(pick)], depth);
    }
}

}  // namespace

int PickWeighted(const std::vector<double>& weights, Pcg32& rng) {
    double sum = 0.0;
    for (double w : weights) {
        if (w > 0.0) sum += w;
    }
    const double u = rng.NextUnit();  // sempre consome 1 número
    if (!(sum > 0.0)) return -1;
    const double target = u * sum;
    double acc = 0.0;
    int lastPositive = -1;
    for (std::size_t i = 0; i < weights.size(); ++i) {
        if (!(weights[i] > 0.0)) continue;
        lastPositive = static_cast<int>(i);
        acc += weights[i];
        if (target < acc) return static_cast<int>(i);
    }
    return lastPositive;  // arredondamento: cai no último com peso
}

std::vector<const AffixData*> EligibleAffixes(const ContentDB& db, const ItemBaseData& base, int itemLevel,
                                              const std::vector<RolledAffix>& current, bool onlyCraftInscription) {
    int prefixes = 0, suffixes = 0;
    std::vector<const AffixData*> chosen;
    for (const RolledAffix& r : current) {
        const AffixData* a = db.FindAffix(r.affixId);
        if (a == nullptr) continue;
        chosen.push_back(a);
        if (a->kind == AffixKind::Prefix) ++prefixes; else ++suffixes;
    }
    std::vector<const AffixData*> out;
    for (const AffixData& a : db.Affixes()) {  // ordem do CSV
        if (a.minItemLevel > itemLevel) continue;
        if (onlyCraftInscription && !a.craftInscription) continue;
        if (!a.allowedSlots.empty() &&
            std::find(a.allowedSlots.begin(), a.allowedSlots.end(), base.slot) == a.allowedSlots.end())
            continue;
        if (a.kind == AffixKind::Prefix && prefixes >= 2) continue;
        if (a.kind == AffixKind::Suffix && suffixes >= 2) continue;
        bool conflict = false;
        for (const AffixData* c : chosen) {
            if (c == &a || (!a.group.empty() && c->group == a.group)) conflict = true;
        }
        if (conflict) continue;
        out.push_back(&a);
    }
    return out;
}

double RollAffixValue(const AffixData& a, Pcg32& rng) {
    if (IsIntegral(a.minValue) && IsIntegral(a.maxValue))
        return static_cast<double>(rng.RangeInt(static_cast<std::int32_t>(a.minValue), static_cast<std::int32_t>(a.maxValue)));
    return rng.RangeReal(a.minValue, a.maxValue);
}

namespace {

// Completa `result` (afixos já fixos, em ordem) até `count` afixos, sorteando um por vez. Para quando não há mais candidato.
void DrawAffixes(const ContentDB& db, const ItemBaseData& base, int itemLevel, int count, std::vector<RolledAffix>& result,
                 Pcg32& rng) {
    while (static_cast<int>(result.size()) < count) {
        const std::vector<const AffixData*> cands = EligibleAffixes(db, base, itemLevel, result, false);
        std::vector<double> weights;
        weights.reserve(cands.size());
        for (const AffixData* a : cands) weights.push_back(a->weight);
        const int pick = PickWeighted(weights, rng);
        if (pick < 0) break;
        const AffixData* a = cands[static_cast<std::size_t>(pick)];
        RolledAffix ra;
        ra.affixId = a->id;
        ra.value = RollAffixValue(*a, rng);
        result.push_back(std::move(ra));
    }
}

// Prefixos antes de sufixos, mantendo a ordem de rolagem dentro de cada grupo.
void PrefixesFirst(const ContentDB& db, std::vector<RolledAffix>& result) {
    std::stable_partition(result.begin(), result.end(), [&](const RolledAffix& r) {
        const AffixData* a = db.FindAffix(r.affixId);
        return a != nullptr && a->kind == AffixKind::Prefix;
    });
}

}  // namespace

std::vector<RolledAffix> RollAffixes(const ContentDB& db, const ItemBaseData& base, Rarity rarity, int itemLevel,
                                     Pcg32& lootRng) {
    std::vector<RolledAffix> result;
    int count = 0;
    if (rarity == Rarity::Magic) count = lootRng.RangeInt(1, 2);
    else if (rarity == Rarity::Rare) count = lootRng.RangeInt(3, 4);
    if (count == 0) return result;
    DrawAffixes(db, base, itemLevel, count, result, lootRng);
    PrefixesFirst(db, result);
    return result;
}

std::vector<RolledAffix> RollAffixesFixed(const ContentDB& db, const ItemBaseData& base, int itemLevel, int count,
                                          const std::vector<RolledAffix>& kept, Pcg32& rng) {
    std::vector<RolledAffix> result = kept;
    DrawAffixes(db, base, itemLevel, count, result, rng);
    PrefixesFirst(db, result);
    return result;
}

LootDrop RollLootTable(const ContentDB& db, const LootTableData& table, const LootContext& ctx, Pcg32& lootRng) {
    LootDrop out;
    RollState st{db, ctx, lootRng, out};
    RollTable(st, table, 1);
    return out;
}

std::vector<Modifier> ItemModifiers(const ContentDB& db, const ItemInstance& item) {
    std::vector<Modifier> mods;
    const std::string src = "item:" + std::to_string(item.uid);
    if (const ItemBaseData* base = db.FindItemBase(item.baseId)) {
        for (const Modifier& m : base->implicitMods) {
            Modifier mod = m;
            mod.source = src;
            mods.push_back(std::move(mod));
        }
    }
    for (const RolledAffix& ra : item.affixes) {
        const AffixData* a = db.FindAffix(ra.affixId);
        if (a == nullptr) continue;
        Modifier mod;
        mod.stat = a->stat;
        mod.kind = a->modKind;
        mod.value = ra.value;
        mod.requiredTags = a->requiredTags;
        mod.source = src;
        mods.push_back(std::move(mod));
    }
    return mods;
}

}  // namespace shatter
