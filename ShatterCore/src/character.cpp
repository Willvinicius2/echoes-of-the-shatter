// ShatterCore — montagem do StatBlock do personagem e checagem de compatibilidade com o idle.
#include "shatter/character.h"

#include <algorithm>

#include "shatter/loot.h"

namespace shatter {

namespace {

bool Fail(std::string* error, const std::string& msg) {
    if (error) *error = msg;
    return false;
}

bool SlotCompatible(ItemSlot equipped, ItemSlot base) {
    if (equipped == base) return true;
    const bool ringA = equipped == ItemSlot::Ring || equipped == ItemSlot::Ring2;
    const bool ringB = base == ItemSlot::Ring || base == ItemSlot::Ring2;
    return ringA && ringB;
}

}  // namespace

// Ordem fixa de inserção dos mods (determinismo): classe -> itens por ItemSlot crescente
// (implícito, afixos na ordem) -> únicos (mods fixos) -> passivas na ordem do vetor.
// Passivas e Sigilos ainda não têm tabela de dados (pendência P3): não são consultados e não somam mods.
bool BuildStatBlock(const ContentDB& db, const CharacterState& c, StatBlock& out, std::string* error) {
    const ClassData* cls = db.FindClass(c.classId);
    if (cls == nullptr) return Fail(error, "unknown class '" + c.classId + "'");

    // Validação de IDs antes de montar (out só é tocado se tudo existir).
    for (const LearnedSkill& ls : c.skills) {
        if (db.FindSkill(ls.skillId) == nullptr) return Fail(error, "unknown skill '" + ls.skillId + "'");
    }
    for (const ContentId& id : c.skillBar) {
        if (id.empty()) continue;
        if (db.FindSkill(id) == nullptr) return Fail(error, "unknown skill on bar '" + id + "'");
    }
    for (int s = 0; s < kItemSlotCount; ++s) {
        const auto& item = c.equipment[static_cast<std::size_t>(s)];
        if (!item) continue;
        const ItemBaseData* base = db.FindItemBase(item->baseId);
        if (base == nullptr) return Fail(error, "unknown item base '" + item->baseId + "'");
        if (!SlotCompatible(static_cast<ItemSlot>(s), base->slot))
            return Fail(error, "item base '" + item->baseId + "' does not fit slot " + ToString(static_cast<ItemSlot>(s)));
        for (const RolledAffix& a : item->affixes) {
            if (db.FindAffix(a.affixId) == nullptr) return Fail(error, "unknown affix '" + a.affixId + "'");
        }
        if (!item->uniqueId.empty() && db.FindUnique(item->uniqueId) == nullptr)
            return Fail(error, "unknown unique '" + item->uniqueId + "'");
    }

    StatBlock sb;
    const int lvl = c.level < 1 ? 1 : c.level;
    for (const StatGrowth& g : cls->stats) {
        sb.SetBase(g.stat, g.base + g.perLevel * static_cast<double>(lvl - 1));
    }
    for (int s = 0; s < kItemSlotCount; ++s) {
        const auto& item = c.equipment[static_cast<std::size_t>(s)];
        if (item) sb.AddModifiers(ItemModifiers(db, *item));
    }
    for (int s = 0; s < kItemSlotCount; ++s) {
        const auto& item = c.equipment[static_cast<std::size_t>(s)];
        if (!item || item->uniqueId.empty()) continue;
        const UniqueData* u = db.FindUnique(item->uniqueId);
        for (const Modifier& m : u->fixedMods) {
            Modifier mod = m;
            mod.source = "item:" + std::to_string(item->uid);
            sb.AddModifier(mod);
        }
    }
    out = std::move(sb);
    return true;
}

void BuildEnemyStatBlock(const EnemyData& enemy, int level, StatBlock& out) {
    StatBlock sb;
    const int lvl = level < 1 ? 1 : level;
    for (const StatGrowth& g : enemy.stats) sb.SetBase(g.stat, g.base + g.perLevel * static_cast<double>(lvl - 1));
    out = std::move(sb);
}

bool IsIdleCompatible(const ContentDB& db, const CharacterState& c, std::vector<ContentId>* blockingIds) {
    std::vector<ContentId> blocking;
    auto add = [&](const ContentId& id) {
        if (std::find(blocking.begin(), blocking.end(), id) == blocking.end()) blocking.push_back(id);
    };
    for (const ContentId& id : c.skillBar) {
        if (id.empty()) continue;
        const SkillData* s = db.FindSkill(id);
        if (s == nullptr || !s->idle.supported) add(id);
    }
    for (int s = 0; s < kItemSlotCount; ++s) {
        const auto& item = c.equipment[static_cast<std::size_t>(s)];
        if (!item || item->uniqueId.empty()) continue;
        const UniqueData* u = db.FindUnique(item->uniqueId);
        if (u == nullptr || !u->idleSupported) add(item->uniqueId);
    }
    if (blockingIds) *blockingIds = blocking;
    return blocking.empty();
}

}  // namespace shatter
