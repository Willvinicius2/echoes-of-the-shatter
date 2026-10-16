// ShatterCore — StatBlock, nomes de atributos e de tipos de modificador.
#include "shatter/stats.h"

#include <algorithm>

namespace shatter {

namespace {

constexpr const char* kStatNames[kStatCount] = {
    "life",           "life_regen",        "resource",        "resource_regen",   "armor",
    "evasion_chance", "block_chance",      "resist_fire",     "resist_cold",      "resist_lightning",
    "damage",         "attack_speed",      "cast_speed",      "crit_chance",      "crit_multiplier",
    "move_speed",     "cooldown_recovery", "area_of_effect",  "projectile_count", "damage_taken",
    "potion_effect",
};

// Atributos multiplicativos: a base neutra é 1 (a classe ou o inimigo pode sobrescrever com SetBase).
constexpr bool HasNeutralBaseOne(StatId id) {
    return id == StatId::AttackSpeed || id == StatId::CastSpeed || id == StatId::MoveSpeed ||
           id == StatId::CooldownRecovery || id == StatId::AreaOfEffect || id == StatId::DamageTaken ||
           id == StatId::PotionEffect;
}

constexpr bool ValidStat(StatId id) { return static_cast<int>(id) >= 0 && static_cast<int>(id) < kStatCount; }

}  // namespace

bool ParseStatId(std::string_view text, StatId& out) {
    for (int i = 0; i < kStatCount; ++i) {
        if (text == kStatNames[i]) {
            out = static_cast<StatId>(i);
            return true;
        }
    }
    return false;
}

const char* ToString(StatId id) { return ValidStat(id) ? kStatNames[static_cast<int>(id)] : "life"; }

bool ParseModKind(std::string_view text, ModKind& out) {
    if (text == "flat") { out = ModKind::Flat; return true; }
    if (text == "increased") { out = ModKind::Increased; return true; }
    if (text == "more") { out = ModKind::More; return true; }
    return false;
}

StatBlock::StatBlock() {
    base_.fill(0.0);
    for (int i = 0; i < kStatCount; ++i) {
        if (HasNeutralBaseOne(static_cast<StatId>(i))) base_[static_cast<std::size_t>(i)] = 1.0;
    }
}

void StatBlock::Invalidate() {
    dirty_ = true;
    ++revision_;
}

void StatBlock::SetBase(StatId stat, double value) {
    if (!ValidStat(stat)) return;
    base_[static_cast<std::size_t>(stat)] = value;
    Invalidate();
}

double StatBlock::GetBase(StatId stat) const {
    return ValidStat(stat) ? base_[static_cast<std::size_t>(stat)] : 0.0;
}

void StatBlock::AddModifier(const Modifier& mod) {
    if (!ValidStat(mod.stat)) return;
    mods_.push_back(mod);
    Invalidate();
}

void StatBlock::AddModifiers(const std::vector<Modifier>& mods) {
    bool any = false;
    for (const Modifier& m : mods) {
        if (!ValidStat(m.stat)) continue;
        mods_.push_back(m);
        any = true;
    }
    if (any) Invalidate();
}

std::size_t StatBlock::RemoveModifiersFrom(std::string_view sourceId) {
    const std::size_t before = mods_.size();
    mods_.erase(std::remove_if(mods_.begin(), mods_.end(),
                               [&](const Modifier& m) { return std::string_view(m.source) == sourceId; }),
                mods_.end());
    const std::size_t removed = before - mods_.size();
    if (removed > 0) Invalidate();
    return removed;
}

void StatBlock::ClearModifiers() {
    if (mods_.empty()) return;
    mods_.clear();
    Invalidate();
}

StatBlock::Breakdown StatBlock::Explain(StatId stat, TagMask contextTags) const {
    Breakdown b;
    if (!ValidStat(stat)) return b;
    b.base = base_[static_cast<std::size_t>(stat)];
    // Soma na ordem de inserção (determinismo de ponto flutuante).
    for (const Modifier& m : mods_) {
        if (m.stat != stat || !HasAllTags(contextTags, m.requiredTags)) continue;
        switch (m.kind) {
            case ModKind::Flat: b.sumFlat += m.value; break;
            case ModKind::Increased: b.sumIncreased += m.value; break;
            case ModKind::More: b.productMore *= (1.0 + m.value); break;
        }
    }
    b.final = ComputeStatValue(b.base, b.sumFlat, b.sumIncreased, b.productMore);
    return b;
}

double StatBlock::GetTagged(StatId stat, TagMask contextTags) const {
    if (!ValidStat(stat)) return 0.0;
    if (dirty_) {
        cache_.clear();
        dirty_ = false;
    }
    const std::uint64_t key = (static_cast<std::uint64_t>(stat) << 32) | contextTags;
    const auto it = cache_.find(key);
    if (it != cache_.end()) return it->second;
    const double v = Explain(stat, contextTags).final;
    cache_.emplace(key, v);
    return v;
}

double StatBlock::Get(StatId stat) const { return GetTagged(stat, 0); }

double StatBlock::ApplyTagged(StatId stat, TagMask contextTags, double baseOverride) const {
    if (!ValidStat(stat)) return 0.0;
    const Breakdown b = Explain(stat, contextTags);
    return ComputeStatValue(baseOverride, b.sumFlat, b.sumIncreased, b.productMore);
}

}  // namespace shatter
