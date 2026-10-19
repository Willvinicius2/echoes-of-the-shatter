// ShatterCore — história da campanha (story.h).
#include "shatter/story.h"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <map>

#include "csv.h"
#include "numtext.h"

namespace shatter {

namespace {

namespace fs = std::filesystem;
using detail::CsvRow;
using detail::CsvTable;


bool Header(const CsvTable& t, const std::vector<std::string>& want, std::string_view table, std::vector<ContentError>& errs) {
    bool ok = t.header.size() == want.size();
    for (std::size_t i = 0; ok && i < want.size(); ++i) ok = t.header[i] == want[i];
    if (!ok) errs.push_back({std::string(table), t.headerLine, "unexpected header"});
    return ok;
}

bool Int(std::string_view cell, int lo, int hi, int& out) {
    std::int64_t v = 0;
    if (!detail::ParseInt64(cell, v) || v < lo || v > hi) return false;
    out = static_cast<int>(v);
    return true;
}

template <class T>
const T* FindById(const std::vector<T>& list, std::string_view id) {
    for (const T& e : list)
        if (e.id == id) return &e;
    return nullptr;
}

const StoryVerdictRecord* FindRecord(const SaveData& s, std::string_view regionId) {
    for (const StoryVerdictRecord& r : s.story.verdicts)
        if (r.regionId == regionId) return &r;
    return nullptr;
}

StoryQuestRecord* FindQuestRecord(SaveData& s, std::string_view id) {
    for (StoryQuestRecord& r : s.story.quests)
        if (r.questId == id) return &r;
    return nullptr;
}
const StoryQuestRecord* FindQuestRecord(const SaveData& s, std::string_view id) {
    for (const StoryQuestRecord& r : s.story.quests)
        if (r.questId == id) return &r;
    return nullptr;
}
// nullptr se o save já guarda kMaxSavedQuests missões.
StoryQuestRecord* GetOrAddQuestRecord(SaveData& s, std::string_view id) {
    if (StoryQuestRecord* r = FindQuestRecord(s, id)) return r;
    if (s.story.quests.size() >= kMaxSavedQuests) return nullptr;
    s.story.quests.push_back({ContentId(id), 0, false});
    return &s.story.quests.back();
}
bool QuestUnlocked(const SaveData& s, const StoryQuest& q) {
    if (q.requires_.empty()) return true;
    const StoryQuestRecord* r = FindQuestRecord(s, q.requires_);
    return r != nullptr && r->done;
}
bool QuestDone(const SaveData& s, const StoryQuest& q) {
    const StoryQuestRecord* r = FindQuestRecord(s, q.id);
    return r != nullptr && r->done;
}
void MarkProgress(StoryQuestRecord& r, const StoryQuest& q, int progress, int& newlyDone) {
    r.progress = std::max(r.progress, std::min(progress, q.objectiveCount));
    if (!r.done && r.progress >= q.objectiveCount) {
        r.done = true;
        ++newlyDone;
    }
}
// Avança as missões de objetivo derivado (Ecos, veredito) até nada mudar: concluir uma pode liberar outra já cumprida.
int SyncQuests(const StoryDB& story, SaveData& s) {
    int newlyDone = 0;
    for (bool changed = true; changed;) {
        changed = false;
        for (const StoryQuest& q : story.Quests()) {
            if (QuestDone(s, q) || !QuestUnlocked(s, q)) continue;
            int derived = 0;
            if (q.objectiveType == "collect_echo") derived = EchoesFound(story, s, q.objectiveTarget);
            else if (q.objectiveType == "verdict") derived = DecidedVerdict(story, s, q.objectiveTarget) != nullptr ? 1 : 0;
            else continue;
            if (derived <= 0) continue;
            StoryQuestRecord* r = GetOrAddQuestRecord(s, q.id);
            if (r == nullptr) continue;
            const int before = newlyDone;
            MarkProgress(*r, q, derived, newlyDone);
            changed = changed || newlyDone != before;
        }
    }
    return newlyDone;
}

}  // namespace

bool StoryDB::LoadTableCsv(std::string_view table, std::string_view text) {
    const std::size_t before = errors_.size();
    const std::string name(table);
    CsvTable t;
    detail::CsvError ce;
    if (!detail::ParseCsv(text, t, ce)) {
        errors_.push_back({name, ce.line, ce.message});
        return false;
    }
    auto bad = [&](const CsvRow& r, const char* msg) { errors_.push_back({name, r.line, msg}); };
    auto S = [](const CsvRow& r, std::size_t i) { return std::string(r.cells[i]); };
    if (table == "regions.csv") {
        if (!Header(t, {"id", "order", "mapId", "generalId", "exorcizeVerdict", "devourVerdict"}, table, errors_)) return false;
        for (const CsvRow& r : t.rows) {
            StoryRegion x;
            x.id = S(r, 0);
            if (!Int(r.cells[1], 1, 1000, x.order)) bad(r, "order out of range");
            x.mapId = S(r, 2);
            x.generalId = S(r, 3);
            x.exorcizeVerdict = S(r, 4);
            x.devourVerdict = S(r, 5);
            regions_.push_back(std::move(x));
        }
    } else if (table == "echoes.csv") {
        if (!Header(t, {"id", "regionId", "kind", "revealsSkill", "minToReveal"}, table, errors_)) return false;
        for (const CsvRow& r : t.rows) {
            StoryEcho x;
            x.id = S(r, 0);
            x.regionId = S(r, 1);
            x.kind = S(r, 2);
            if (x.kind != "weapon" && x.kind != "memory") bad(r, "kind must be weapon or memory");
            x.revealsSkill = S(r, 3);
            if (!Int(r.cells[4], 1, 100, x.minToReveal)) bad(r, "minToReveal out of range");
            echoes_.push_back(std::move(x));
        }
    } else if (table == "quests.csv") {
        if (!Header(t, {"id", "regionId", "giver", "objectiveType", "objectiveTarget", "objectiveCount", "requires", "reward"},
                    table, errors_))
            return false;
        for (const CsvRow& r : t.rows) {
            StoryQuest x;
            x.id = S(r, 0);
            x.regionId = S(r, 1);
            x.giver = S(r, 2);
            x.objectiveType = S(r, 3);
            if (x.objectiveType != "talk" && x.objectiveType != "collect_echo" && x.objectiveType != "reach_map_boss" &&
                x.objectiveType != "verdict")
                bad(r, "unknown objectiveType");
            x.objectiveTarget = S(r, 4);
            if (!Int(r.cells[5], 1, 1000, x.objectiveCount)) bad(r, "objectiveCount out of range");
            x.requires_ = S(r, 6);
            x.reward = S(r, 7);
            quests_.push_back(std::move(x));
        }
    } else if (table == "verdicts.csv") {
        if (!Header(t, {"id", "regionId", "choice", "hungerDelta", "statBonusPct", "grantsRelic", "grantsSignature", "regionState",
                        "hubState", "lastWordsKey"},
                    table, errors_))
            return false;
        for (const CsvRow& r : t.rows) {
            StoryVerdict x;
            x.id = S(r, 0);
            x.regionId = S(r, 1);
            if (r.cells[2] == "exorcise") x.choice = VerdictChoice::Exorcise;
            else if (r.cells[2] == "devour") x.choice = VerdictChoice::Devour;
            else bad(r, "choice must be exorcise or devour");
            if (!Int(r.cells[3], 0, 100, x.hungerDelta)) bad(r, "hungerDelta out of range");
            if (!Int(r.cells[4], 0, 1000, x.statBonusPct)) bad(r, "statBonusPct out of range");
            x.grantsRelic = S(r, 5);
            x.grantsSignature = S(r, 6);
            x.regionState = S(r, 7);
            if (x.regionState != "purified" && x.regionState != "stain") bad(r, "regionState must be purified or stain");
            x.hubState = S(r, 8);
            x.lastWordsKey = S(r, 9);
            verdicts_.push_back(std::move(x));
        }
    } else if (table == "story_rules.csv") {
        if (!Header(t, {"key", "value"}, table, errors_)) return false;
        for (const CsvRow& r : t.rows) {
            if (r.cells[0] == "hunger_max") {
                if (hasHungerMax_) bad(r, "hunger_max repeated");
                if (!Int(r.cells[1], 1, kMaxSavedHunger, hungerMax_)) bad(r, "hunger_max out of range");
                hasHungerMax_ = true;
            } else if (r.cells[0] == "relic_potion_effect_pct") {
                if (!Int(r.cells[1], 0, 100, relicPotionEffectPct_)) bad(r, "relic_potion_effect_pct out of range");
            } else if (r.cells[0] == "stain_elite_bonus_pct") {
                if (!Int(r.cells[1], 0, 100, stainEliteBonusPct_)) bad(r, "stain_elite_bonus_pct out of range");
            } else if (r.cells[0] == "devoured_hunger_cost") {
                if (!Int(r.cells[1], 0, kMaxSavedHunger, devouredHungerCost_)) bad(r, "devoured_hunger_cost out of range");
            } else if (r.cells[0] == "stain_loot_table") {
                stainLootTable_ = r.cells[1];
                if (!stainLootTable_.empty() && !IsValidContentId(stainLootTable_)) bad(r, "stain_loot_table is not a valid id");
            } else {
                bad(r, "unknown key");
            }
        }
    } else {
        errors_.push_back({name, 0, "unknown story table"});
    }
    return errors_.size() == before;
}

bool StoryDB::LoadDirectory(const std::string& path) {
    std::error_code ec;
    const fs::path dir = fs::u8path(path);
    if (!fs::is_directory(dir, ec)) {
        errors_.push_back({"Story", 0, "E_IO story directory missing"});
        return false;
    }
    bool ok = true;
    for (const char* name : {"regions.csv", "echoes.csv", "quests.csv", "verdicts.csv", "story_rules.csv"}) {
        std::ifstream in(dir / name, std::ios::binary);
        if (!in) {
            errors_.push_back({name, 0, "E_IO table file missing"});
            ok = false;
            continue;
        }
        const std::string text((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
        ok = LoadTableCsv(name, text) && ok;
    }
    return ok;
}

bool StoryDB::Finalize(const ContentDB* content) {
    const std::size_t before = errors_.size();
    auto E = [&](const char* table, const std::string& msg) { errors_.push_back({table, 0, msg}); };
    if (!hasHungerMax_) E("story_rules.csv", "hunger_max missing");
    if (hasHungerMax_ && devouredHungerCost_ > hungerMax_) E("story_rules.csv", "devoured_hunger_cost above hunger_max");
    if (content != nullptr && !stainLootTable_.empty() && content->FindLootTable(stainLootTable_) == nullptr)
        E("story_rules.csv", "stain_loot_table not found: '" + stainLootTable_ + "'");
    auto uniqueIds = [&](const char* table, const auto& list, const char* prefix) {
        for (std::size_t i = 0; i < list.size(); ++i) {
            const std::string& id = list[i].id;
            if (!IsValidContentId(id) || id.rfind(prefix, 0) != 0) E(table, "bad id '" + id + "'");
            for (std::size_t j = 0; j < i; ++j)
                if (list[j].id == id) E(table, "duplicate id '" + id + "'");
        }
    };
    uniqueIds("regions.csv", regions_, "region.");
    uniqueIds("echoes.csv", echoes_, "echo.");
    uniqueIds("quests.csv", quests_, "quest.");
    uniqueIds("verdicts.csv", verdicts_, "verdict.");
    for (const StoryRegion& r : regions_) {
        for (const ContentId* v : {&r.exorcizeVerdict, &r.devourVerdict}) {
            const StoryVerdict* sv = FindById(verdicts_, *v);
            if (sv == nullptr) E("regions.csv", "verdict '" + *v + "' not in verdicts.csv");
            else if (sv->regionId != r.id) E("regions.csv", "verdict '" + *v + "' belongs to another region");
        }
        const StoryVerdict* ex = FindById(verdicts_, r.exorcizeVerdict);
        const StoryVerdict* dv = FindById(verdicts_, r.devourVerdict);
        if (ex != nullptr && ex->choice != VerdictChoice::Exorcise) E("regions.csv", "exorcizeVerdict is not an exorcise verdict");
        if (dv != nullptr && dv->choice != VerdictChoice::Devour) E("regions.csv", "devourVerdict is not a devour verdict");
        if (content != nullptr) {
            if (content->FindMap(r.mapId) == nullptr) E("regions.csv", "mapId '" + r.mapId + "' not in maps.csv");
            if (content->FindEnemy(r.generalId) == nullptr) E("regions.csv", "generalId '" + r.generalId + "' not in enemies.csv");
        }
    }
    for (const StoryEcho& e : echoes_) {
        if (FindById(regions_, e.regionId) == nullptr) E("echoes.csv", "regionId '" + e.regionId + "' not in regions.csv");
        if (content != nullptr && content->FindSkill(e.revealsSkill) == nullptr)
            E("echoes.csv", "revealsSkill '" + e.revealsSkill + "' not in skills.csv");
    }
    for (const StoryQuest& q : quests_) {
        if (FindById(regions_, q.regionId) == nullptr) E("quests.csv", "regionId '" + q.regionId + "' not in regions.csv");
        if (!q.requires_.empty() && FindById(quests_, q.requires_) == nullptr)
            E("quests.csv", "requires '" + q.requires_ + "' not in quests.csv");
        if (q.objectiveType == "collect_echo" &&
            q.objectiveCount > static_cast<int>(std::count_if(echoes_.begin(), echoes_.end(),
                                                              [&](const StoryEcho& e) { return e.regionId == q.regionId; })))
            E("quests.csv", "objectiveCount above the region's echoes for '" + q.id + "'");
    }
    // Um save guarda no máximo kMaxSavedQuests missões: com mais que isso, os eventos das últimas seriam ignorados sem aviso.
    if (quests_.size() > kMaxSavedQuests) E("quests.csv", "more quests than the save can hold (" + std::to_string(kMaxSavedQuests) + ")");
    // `requires` em ciclo (ou apontando para si) deixaria as missoes trancadas para sempre.
    for (const StoryQuest& q : quests_) {
        const StoryQuest* cur = &q;
        for (std::size_t step = 0; step <= quests_.size() && cur != nullptr && !cur->requires_.empty(); ++step) {
            cur = FindById(quests_, cur->requires_);
            if (cur == &q) {
                E("quests.csv", "requires cycle through '" + q.id + "'");
                break;
            }
        }
    }
    for (const StoryVerdict& v : verdicts_) {
        const StoryRegion* owner = FindById(regions_, v.regionId);
        if (owner != nullptr && owner->exorcizeVerdict != v.id && owner->devourVerdict != v.id)
            E("verdicts.csv", "verdict '" + v.id + "' is not listed by its region");
        if (FindById(regions_, v.regionId) == nullptr) E("verdicts.csv", "regionId '" + v.regionId + "' not in regions.csv");
        if (hasHungerMax_ && v.hungerDelta > hungerMax_) E("verdicts.csv", "hungerDelta above hunger_max for '" + v.id + "'");
        if (v.choice == VerdictChoice::Exorcise && (v.hungerDelta != 0 || v.statBonusPct != 0 || !v.grantsSignature.empty()))
            E("verdicts.csv", "exorcise gives no hunger, bonus or signature: '" + v.id + "'");
        if (v.choice == VerdictChoice::Devour && (v.hungerDelta < 1 || !v.grantsRelic.empty()))
            E("verdicts.csv", "devour needs hunger >= 1 and gives no relic: '" + v.id + "'");
    }
    return errors_.size() == before;
}

const StoryRegion* StoryDB::FindRegion(std::string_view id) const { return FindById(regions_, id); }
const StoryEcho* StoryDB::FindEcho(std::string_view id) const { return FindById(echoes_, id); }
const StoryQuest* StoryDB::FindQuest(std::string_view id) const { return FindById(quests_, id); }
const StoryVerdict* StoryDB::FindVerdict(std::string_view id) const { return FindById(verdicts_, id); }

bool RecordEcho(const StoryDB& story, SaveData& s, std::string_view echoId) {
    if (story.FindEcho(echoId) == nullptr) return false;
    if (std::find(s.story.echoes.begin(), s.story.echoes.end(), echoId) != s.story.echoes.end()) return false;
    if (s.story.echoes.size() >= kMaxSavedEchoes) return false;
    s.story.echoes.emplace_back(echoId);
    SyncQuests(story, s);
    return true;
}

int EchoesFound(const StoryDB& story, const SaveData& s, std::string_view regionId) {
    int n = 0;
    for (const ContentId& id : s.story.echoes) {
        const StoryEcho* e = story.FindEcho(id);
        if (e != nullptr && e->regionId == regionId) ++n;
    }
    return n;
}

bool IsSkillRevealed(const StoryDB& story, const SaveData& s, std::string_view regionId, std::string_view skillId) {
    int found = 0, need = 0;
    for (const ContentId& id : s.story.echoes) {
        const StoryEcho* e = story.FindEcho(id);
        if (e != nullptr && e->regionId == regionId && e->revealsSkill == skillId) ++found;
    }
    for (const StoryEcho& e : story.Echoes())
        if (e.regionId == regionId && e.revealsSkill == skillId) need = std::max(need, e.minToReveal);
    return need > 0 && found >= need;
}

VerdictResult ApplyVerdict(const StoryDB& story, SaveData& s, std::string_view verdictId) {
    const StoryVerdict* v = story.FindVerdict(verdictId);
    const StoryRegion* region = v != nullptr ? story.FindRegion(v->regionId) : nullptr;
    if (v == nullptr || region == nullptr || story.HungerMax() < 1) return VerdictResult::UnknownVerdict;   // banco não finalizado
    if (FindRecord(s, v->regionId) != nullptr) return VerdictResult::AlreadyDecided;
    bool defeated = false;
    for (const CharacterState& c : s.characters) {
        const BossProgressEntry* b = FindBossProgress(c.bossProgress, region->generalId);
        defeated = defeated || (b != nullptr && b->kills >= 1);
    }
    if (!defeated) return VerdictResult::GeneralNotDefeated;
    if (s.story.verdicts.size() >= kMaxSavedVerdicts) return VerdictResult::SaveFull;
    s.story.verdicts.push_back({v->regionId, v->id});
    s.story.hunger = std::min(story.HungerMax(), s.story.hunger + v->hungerDelta);
    SyncQuests(story, s);
    return VerdictResult::Ok;
}

const StoryVerdict* DecidedVerdict(const StoryDB& story, const SaveData& s, std::string_view regionId) {
    const StoryVerdictRecord* r = FindRecord(s, regionId);
    return r != nullptr ? story.FindVerdict(r->verdictId) : nullptr;
}

QuestStatus GetQuestStatus(const StoryDB& story, const SaveData& s, std::string_view questId) {
    const StoryQuest* q = story.FindQuest(questId);
    if (q == nullptr) return QuestStatus::Locked;
    if (QuestDone(s, *q)) return QuestStatus::Done;
    return QuestUnlocked(s, *q) ? QuestStatus::Active : QuestStatus::Locked;
}

int QuestProgress(const StoryDB& story, const SaveData& s, std::string_view questId) {
    const StoryQuest* q = story.FindQuest(questId);
    const StoryQuestRecord* r = q != nullptr ? FindQuestRecord(s, questId) : nullptr;
    return r != nullptr ? std::min(r->progress, q->objectiveCount) : 0;
}

int ReportQuestEvent(const StoryDB& story, SaveData& s, std::string_view type, std::string_view target, int amount) {
    if (amount < 1 || (type != "talk" && type != "reach_map_boss")) return 0;
    int newlyDone = 0;
    for (const StoryQuest& q : story.Quests()) {
        if (q.objectiveType != type || q.objectiveTarget != target || QuestDone(s, q) || !QuestUnlocked(s, q)) continue;
        StoryQuestRecord* r = GetOrAddQuestRecord(s, q.id);
        if (r == nullptr) continue;
        const int capped = static_cast<int>(std::min<std::int64_t>(q.objectiveCount, static_cast<std::int64_t>(r->progress) + amount));
        MarkProgress(*r, q, capped, newlyDone);
    }
    return newlyDone + SyncQuests(story, s);
}

int TotalStatBonusPct(const StoryDB& story, const SaveData& s) {
    int total = 0;
    for (const StoryVerdictRecord& r : s.story.verdicts) {
        const StoryVerdict* v = story.FindVerdict(r.verdictId);
        if (v != nullptr) total += v->statBonusPct;
    }
    return std::min(total, 100);   // mesmo teto que a expedição e shatter_story_state_json aplicam
}

int TotalPotionEffectPct(const StoryDB& story, const SaveData& s) {
    int total = 0;
    for (const StoryVerdictRecord& r : s.story.verdicts) {
        const StoryVerdict* v = story.FindVerdict(r.verdictId);
        if (v != nullptr && !v->grantsRelic.empty()) total += story.RelicPotionEffectPct();
    }
    return std::min(total, 100);
}

namespace {
bool MapHasStain(const StoryDB& story, const SaveData& s, std::string_view mapId) {
    for (const StoryRegion& region : story.Regions()) {
        if (region.mapId != mapId) continue;
        const StoryVerdict* v = DecidedVerdict(story, s, region.id);
        if (v != nullptr && v->regionState == "stain") return true;
    }
    return false;
}
}  // namespace

int StainEliteBonusPctForMap(const StoryDB& story, const SaveData& s, std::string_view mapId) {
    return MapHasStain(story, s, mapId) ? story.StainEliteBonusPct() : 0;
}

std::string StainLootTableForMap(const StoryDB& story, const SaveData& s, std::string_view mapId) {
    return MapHasStain(story, s, mapId) ? story.StainLootTable() : std::string();
}

std::vector<ContentId> DevouredSkills(const StoryDB& story, const SaveData& s) {
    std::vector<ContentId> out;
    for (const StoryVerdictRecord& r : s.story.verdicts) {
        const StoryVerdict* v = story.FindVerdict(r.verdictId);
        if (v == nullptr || v->grantsSignature.rfind("skill.devoured.", 0) != 0) continue;
        if (std::find(out.begin(), out.end(), v->grantsSignature) == out.end()) out.push_back(v->grantsSignature);
    }
    return out;
}

int IdleDevouredUses(const StoryDB& story, const SaveData& s) {
    const int cost = story.DevouredHungerCost();
    const int max = story.HungerMax();
    if (cost <= 0 || max <= 0) return -1;
    const int left = max - s.story.hunger;
    return left > 0 ? left / cost : 0;
}

void ApplyStoryToExpedition(const StoryDB& story, const SaveData& s, std::string_view mapId, ExpeditionStartParams& p) {
    p.storyStatBonusPct = TotalStatBonusPct(story, s);
    p.storyPotionEffectPct = TotalPotionEffectPct(story, s);
    p.storyEliteBonusPct = std::clamp(StainEliteBonusPctForMap(story, s, mapId), 0, 100);
    p.storyDevouredSkills = DevouredSkills(story, s);
    p.storyDevouredUses = p.storyDevouredSkills.empty() ? 0 : std::min(IdleDevouredUses(story, s), kMaxStoryDevouredUses);
    if (p.storyDevouredUses == 0) p.storyDevouredSkills.clear();
    p.storyStainLootTable = StainLootTableForMap(story, s, mapId);
}

}  // namespace shatter
