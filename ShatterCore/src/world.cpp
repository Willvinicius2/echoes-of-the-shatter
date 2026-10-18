// ShatterCore — jogo manual da Cripta (world.h).
#include "shatter/world.h"

#include <algorithm>

#include "shatter/combat.h"
#include "shatter/craft.h"

namespace shatter {

namespace {

std::uint64_t Fnv1a(std::uint64_t h, std::string_view text) {
    for (const char c : text) {
        h ^= static_cast<unsigned char>(c);
        h *= 0x100000001B3ull;
    }
    return h;
}

WorldAreaState* FindArea(SaveData& s, std::string_view mapId) {
    for (WorldAreaState& a : s.world)
        if (a.mapId == mapId) return &a;
    return nullptr;
}

int LevelCap(const ContentDB& db, std::string_view mapId) {
    int cap = db.Rules().maxLevel;
    if (const MapData* m = db.FindMap(mapId)) cap = std::min(cap, m->monsterLevel + db.Rules().xpLevelCapAboveArea);
    return cap;
}

}  // namespace

const WorldAreaState* FindWorldArea(const SaveData& s, std::string_view mapId) {
    for (const WorldAreaState& a : s.world)
        if (a.mapId == mapId) return &a;
    return nullptr;
}

bool IsWorldObjectOpen(const SaveData& s, std::string_view mapId, std::string_view objectId) {
    const WorldAreaState* a = FindWorldArea(s, mapId);
    if (a == nullptr) return false;
    return std::find(a->opened.begin(), a->opened.end(), objectId) != a->opened.end();
}

bool SetWorldObjectOpen(SaveData& s, const ContentId& mapId, const ContentId& objectId, bool open) {
    if (!IsValidContentId(mapId) || !IsValidContentId(objectId)) return false;
    WorldAreaState* a = FindArea(s, mapId);
    if (a == nullptr) {
        if (!open) return true;  // nada aberto numa área que nem existe
        if (s.world.size() >= kMaxWorldAreas) return false;
        WorldAreaState fresh;
        fresh.mapId = mapId;
        s.world.push_back(std::move(fresh));
        a = &s.world.back();
    }
    const auto it = std::find(a->opened.begin(), a->opened.end(), objectId);
    if (open) {
        if (it != a->opened.end()) return true;
        if (a->opened.size() >= kMaxWorldObjects) return false;
        a->opened.push_back(objectId);
    } else if (it != a->opened.end()) {
        a->opened.erase(it);
    }
    return true;
}

std::uint64_t VisitSeed(const SaveData& s, std::string_view mapId, std::uint32_t visit) {
    std::uint64_t h = Mix64(EffectiveCraftSeed(s) ^ 0x57304C4456495349ull);  // "W0LDVISI"
    h = Mix64(h ^ Fnv1a(0xCBF29CE484222325ull, mapId));
    return Mix64(h ^ (static_cast<std::uint64_t>(visit) * 0x9E3779B97F4A7C15ull));
}

bool BeginAreaVisit(const ContentDB& db, SaveData& s, const ContentId& mapId, std::uint64_t* visitSeed) {
    if (db.FindMap(mapId) == nullptr) return false;
    WorldAreaState* a = FindArea(s, mapId);
    if (a == nullptr) {
        if (s.world.size() >= kMaxWorldAreas) return false;
        WorldAreaState fresh;
        fresh.mapId = mapId;
        s.world.push_back(std::move(fresh));
        a = &s.world.back();
    }
    if (a->visits < 4000000000u) ++a->visits;
    if (visitSeed != nullptr) *visitSeed = VisitSeed(s, mapId, a->visits);
    return true;
}

std::string ChestLootTable(const ContentDB& db, std::string_view mapId, std::string_view chestId) {
    if (const ChestData* c = db.FindChest(chestId)) {
        if (c->mapId == mapId) return c->lootTable;
    }
    return AreaLootTable(db, mapId);
}

std::string AreaLootTable(const ContentDB& db, std::string_view mapId) {
    const MapData* m = db.FindMap(mapId);
    return m != nullptr ? m->areaLootTable : std::string();
}

bool RollEncounter(const ContentDB& db, std::string_view encounterId, std::uint64_t visitSeed, RolledEncounter& out) {
    const EncounterTemplate* enc = db.FindEncounter(encounterId);
    if (enc == nullptr) return false;
    out = RolledEncounter();
    out.encounterId = enc->id;
    out.isBoss = enc->isBoss;
    Pcg32 rng = Pcg32::ForStream(visitSeed, RngStream::Events, Fnv1a(0xCBF29CE484222325ull, encounterId));
    for (const EncounterGroup& g : enc->groups) {
        RolledGroup rg;
        rg.enemyId = g.enemyId;
        const EnemyData* enemy = db.FindEnemy(g.enemyId);
        const int count = rng.RangeInt(g.countMin, std::max(g.countMin, g.countMax));
        for (int i = 0; i < count; ++i) {
            RolledSlot slot;
            const bool becameElite = rng.Chance(g.eliteChance);          // consome sempre 1 número
            if (becameElite && enemy != nullptr && !enemy->isElite && !enemy->isBoss) {
                slot.elite = true;
                const EliteModifierData* mod = RollEliteModifier(db, rng);  // consome sempre 1 número
                if (mod != nullptr) slot.modifierId = mod->id;
            }
            rg.slots.push_back(std::move(slot));
        }
        out.groups.push_back(std::move(rg));
    }
    return true;
}

double KillXpBase(const ContentDB& db, std::string_view enemyId, int monsterLevel, bool eliteRolled, std::string_view modifierId) {
    const EnemyData* e = db.FindEnemy(enemyId);
    if (e == nullptr) return -1.0;
    const double base = e->xpBase + e->xpPerLevel * static_cast<double>(std::max(1, monsterLevel) - 1);
    double mult = 1.0;
    if (eliteRolled) {
        const EliteModifierData* mod = modifierId.empty() ? nullptr : db.FindEliteModifier(modifierId);
        mult = MakeEliteProfile(db, mod, true).xpMult;
    } else if (e->isElite) {
        const std::string_view id = modifierId.empty() ? std::string_view(e->modifierId) : modifierId;
        const EliteModifierData* mod = id.empty() ? nullptr : db.FindEliteModifier(id);
        mult = MakeEliteProfile(db, mod, false).xpMult;
    }
    return base * mult;
}

XpAward CharacterProgress(const ContentDB& db, const SaveData& s, std::size_t characterIndex, std::string_view mapId) {
    XpAward a;
    if (characterIndex >= s.characters.size()) return a;
    const CharacterState& c = s.characters[characterIndex];
    a.ok = true;
    a.levelBefore = a.levelAfter = c.level;
    a.levelCap = LevelCap(db, mapId);
    a.xpInLevel = c.xp;
    a.xpToNext = c.level >= a.levelCap ? 0.0 : db.XpToNextLevel(c.level);
    return a;
}

XpAward AwardKillXp(const ContentDB& db, SaveData& s, std::size_t characterIndex, std::string_view mapId,
                    std::string_view enemyId, int monsterLevel, bool eliteRolled, std::string_view modifierId, bool fervor) {
    XpAward a;
    if (characterIndex >= s.characters.size()) return a;
    const double base = KillXpBase(db, enemyId, monsterLevel, eliteRolled, modifierId);
    if (base < 0.0) return a;
    CharacterState& c = s.characters[characterIndex];
    const int cap = LevelCap(db, mapId);
    const double xp = base * (fervor ? db.Rules().fervorXpMult : 1.0);
    a.levelBefore = c.level;
    AwardXp(db, c, xp, cap);
    a.ok = true;
    a.awarded = c.level >= cap && a.levelBefore >= cap ? 0.0 : xp;  // já no teto: nada entra
    a.levelAfter = c.level;
    a.levelCap = cap;
    a.xpInLevel = c.xp;
    a.xpToNext = c.level >= cap ? 0.0 : db.XpToNextLevel(c.level);
    return a;
}

FervorInfo GetFervorInfo(const ContentDB& db) {
    const RulesConstants& r = db.Rules();
    FervorInfo f;
    f.xpMult = r.fervorXpMult;
    f.goldMatMult = r.fervorGoldMatMult;
    f.rareMult = r.fervorRareChanceMult;
    f.xpBonus = r.fervorXpMult - 1.0;
    f.goldMatBonus = r.fervorGoldMatMult - 1.0;
    f.rareBonus = r.fervorRareChanceMult - 1.0;
    return f;
}

}  // namespace shatter
