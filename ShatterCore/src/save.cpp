// ShatterCore — save em JSON: SaveData <-> árvore JSON, envelope com SHA-256, gravação segura e coleta.
#include "shatter/save.h"

#include <algorithm>
#include <cmath>
#include <cstring>

#include "shatter/combat.h"
#include "shatter/sha256.h"

namespace shatter {

namespace {

using json::Value;

// ---------------------------------------------------------------------------
// Enums <-> texto
// ---------------------------------------------------------------------------
constexpr const char* kStopNames[] = {"none", "duration_reached", "retreat", "clock_rollback", "incompatible_build",
                                      "content_mismatch"};
constexpr const char* kObjectiveNames[] = {"xp", "gold", "materials"};
constexpr const char* kConditionNames[] = {"always",           "life_below",     "resource_above",
                                           "resource_below",   "enemies_at_least", "target_is_elite",
                                           "target_is_boss",   "effect_missing"};
constexpr const char* kActionNames[] = {"use_potion", "use_skill"};
constexpr const char* kStatusNames[] = {"none", "running", "collected"};

template <std::size_t N>
bool ParseName(const char* const (&names)[N], std::string_view text, std::size_t& out) {
    for (std::size_t i = 0; i < N; ++i) {
        if (text == names[i]) {
            out = i;
            return true;
        }
    }
    return false;
}

bool Fail(std::string* error, const std::string& msg) {
    if (error) *error = msg;
    return false;
}

template <std::size_t N>
const char* NameOf(const char* const (&names)[N], std::size_t i) {
    return i < N ? names[i] : names[0];
}

Value StrList(const std::vector<ContentId>& v) {
    Value a = Value::MakeArray();
    for (const ContentId& s : v) a.Push(Value(s));
    return a;
}

std::vector<ContentId> ReadStrList(const Value& v) {
    std::vector<ContentId> out;
    for (const Value& e : v.Items()) out.push_back(e.AsString());
    return out;
}

}  // namespace

// ---------------------------------------------------------------------------
// Enums <-> texto (públicos)
// ---------------------------------------------------------------------------
const char* ToString(ExpeditionObjective o) { return NameOf(kObjectiveNames, static_cast<std::size_t>(o)); }
const char* ToString(AiCondition c) { return NameOf(kConditionNames, static_cast<std::size_t>(c)); }
const char* ToString(AiAction a) { return NameOf(kActionNames, static_cast<std::size_t>(a)); }
const char* ToString(ExpeditionStatus s) { return NameOf(kStatusNames, static_cast<std::size_t>(s)); }
const char* ToString(StopReason r) { return NameOf(kStopNames, static_cast<std::size_t>(r)); }

bool ParseExpeditionObjective(std::string_view text, ExpeditionObjective& out) {
    std::size_t i = 0;
    if (!ParseName(kObjectiveNames, text, i)) return false;
    out = static_cast<ExpeditionObjective>(i);
    return true;
}
bool ParseAiCondition(std::string_view text, AiCondition& out) {
    std::size_t i = 0;
    if (!ParseName(kConditionNames, text, i)) return false;
    out = static_cast<AiCondition>(i);
    return true;
}
bool ParseAiAction(std::string_view text, AiAction& out) {
    std::size_t i = 0;
    if (!ParseName(kActionNames, text, i)) return false;
    out = static_cast<AiAction>(i);
    return true;
}
bool ParseStopReason(std::string_view text, StopReason& out) {
    std::size_t i = 0;
    if (!ParseName(kStopNames, text, i)) return false;
    out = static_cast<StopReason>(i);
    return true;
}

// ---------------------------------------------------------------------------
// SaveData -> JSON
// ---------------------------------------------------------------------------
Value ItemToJson(const ItemInstance& it) {
    Value o = Value::MakeObject();
    o.Set("uid", json::FromUInt64(it.uid));
    o.Set("base_id", Value(it.baseId));
    o.Set("rarity", Value(ToString(it.rarity)));
    o.Set("item_level", Value(it.itemLevel));
    o.Set("unique_id", Value(it.uniqueId));
    Value affixes = Value::MakeArray();
    for (const RolledAffix& a : it.affixes) {
        Value ao = Value::MakeObject();
        ao.Set("affix_id", Value(a.affixId));
        ao.Set("value", Value(a.value));
        if (a.polish > 0) ao.Set("polish", Value(static_cast<std::int64_t>(a.polish)));
        affixes.Push(std::move(ao));
    }
    o.Set("affixes", std::move(affixes));
    o.Set("has_inscription", Value(it.hasInscription));
    if (it.craftSteps > 0) o.Set("craft_steps", Value(static_cast<std::int64_t>(it.craftSteps)));
    if (it.craftReforges > 0) o.Set("craft_reforges", Value(static_cast<std::int64_t>(it.craftReforges)));
    return o;
}

Value CharacterToJson(const CharacterState& c) {
    Value o = Value::MakeObject();
    o.Set("name", Value(c.name));
    o.Set("class_id", Value(c.classId));
    o.Set("spec_id", Value(c.specId));
    o.Set("level", Value(c.level));
    o.Set("xp", Value(c.xp));
    o.Set("passives", StrList(c.passives));
    Value skills = Value::MakeArray();
    for (const LearnedSkill& s : c.skills) {
        Value so = Value::MakeObject();
        so.Set("skill_id", Value(s.skillId));
        so.Set("rank", Value(s.rank));
        so.Set("sigils", StrList(s.sigils));
        skills.Push(std::move(so));
    }
    o.Set("skills", std::move(skills));
    Value bar = Value::MakeArray();
    for (const ContentId& id : c.skillBar) bar.Push(Value(id));
    o.Set("skill_bar", std::move(bar));
    Value eq = Value::MakeObject();
    for (int s = 0; s < kItemSlotCount; ++s) {
        const auto& item = c.equipment[static_cast<std::size_t>(s)];
        eq.Set(ToString(static_cast<ItemSlot>(s)), item ? ItemToJson(*item) : Value());
    }
    o.Set("equipment", std::move(eq));
    if (!c.backpack.empty()) {   // Etapa 3: campo opcional (ausente = vazia); saves sem Mochila mantêm os mesmos bytes e hash
        Value bp = Value::MakeArray();
        for (const ItemInstance& it : c.backpack) bp.Push(ItemToJson(it));
        o.Set("backpack", std::move(bp));
    }
    o.Set("conquered_maps", StrList(c.conqueredMaps));
    o.Set("highest_tier_cleared", Value(c.highestTierCleared));
    Value slots = Value::MakeArray();
    for (const PotionSlotState& s : c.potionSlots) {
        Value so = Value::MakeObject();
        so.Set("potion_id", Value(s.potionId));
        so.Set("charges", Value(s.charges));
        so.Set("recharge_remaining", Value(s.rechargeRemaining));
        slots.Push(std::move(so));
    }
    o.Set("potion_slots", std::move(slots));
    Value bosses = Value::MakeArray();
    for (const BossProgressEntry& b : c.bossProgress) {
        Value bo = Value::MakeObject();
        bo.Set("enemy_id", Value(b.enemyId));
        bo.Set("kills", Value(b.kills));
        bo.Set("kills_since_unique", Value(b.killsSinceUnique));
        bosses.Push(std::move(bo));
    }
    o.Set("boss_progress", std::move(bosses));
    o.Set("play_time_seconds", Value(c.playTimeSeconds));
    return o;
}

Value ExpeditionRequestToJson(const ExpeditionRequest& r) {
    Value o = Value::MakeObject();
    Value snap = Value::MakeObject();
    snap.Set("character", CharacterToJson(r.snapshot.character));
    snap.Set("content_version", Value(r.snapshot.contentVersion));
    o.Set("snapshot", std::move(snap));
    o.Set("map_id", Value(r.mapId));
    o.Set("objective", Value(ToString(r.objective)));
    Value rules = Value::MakeArray();
    for (const AiRule& ar : r.rules) {
        Value ro = Value::MakeObject();
        ro.Set("condition", Value(ToString(ar.condition)));
        ro.Set("param", Value(ar.param));
        ro.Set("action", Value(ToString(ar.action)));
        ro.Set("ref_id", Value(ar.refId));
        rules.Push(std::move(ro));
    }
    o.Set("rules", std::move(rules));
    o.Set("seed", json::FromUInt64(r.seed));
    o.Set("start_utc", Value(static_cast<std::int64_t>(r.startUtc)));
    o.Set("duration_hours", Value(r.durationHours));
    o.Set("effective_seconds", Value(r.effectiveSeconds));
    o.Set("content_version", Value(r.contentVersion));
    // Campos opcionais da história: só gravados se != 0 (saves sem veredito mantêm os mesmos bytes e hash).
    if (r.storyStatBonusPct != 0) o.Set("story_stat_bonus_pct", Value(r.storyStatBonusPct));
    if (r.storyPotionEffectPct != 0) o.Set("story_potion_effect_pct", Value(r.storyPotionEffectPct));
    if (r.storyEliteBonusPct != 0) o.Set("story_elite_bonus_pct", Value(r.storyEliteBonusPct));
    return o;
}

// ---------------------------------------------------------------------------
// JSON -> SaveData
// ---------------------------------------------------------------------------
bool ItemFromJson(const Value& o, ItemInstance& it, std::string* err) {
    if (o.type() != json::Type::Object) return Fail(err, "item is not an object");
    it = ItemInstance();
    it.uid = o["uid"].AsUInt64(0);
    it.baseId = o["base_id"].AsString();
    if (!ParseRarity(o["rarity"].AsString(), it.rarity)) return Fail(err, "item: bad rarity");
    it.itemLevel = static_cast<int>(o["item_level"].AsInt(1));
    it.uniqueId = o["unique_id"].AsString();
    for (const Value& a : o["affixes"].Items()) {
        RolledAffix ra;
        ra.affixId = a["affix_id"].AsString();
        ra.value = a["value"].AsDouble(0.0);
        const std::int64_t polish = a["polish"].AsInt(0);
        if (polish < 0 || polish > kMaxSavedPolish) return Fail(err, "item: affix polish out of range");
        ra.polish = static_cast<std::uint8_t>(polish);
        it.affixes.push_back(std::move(ra));
    }
    it.hasInscription = o["has_inscription"].AsBool(false);
    const std::int64_t steps = o["craft_steps"].AsInt(0);
    const std::int64_t reforges = o["craft_reforges"].AsInt(0);
    if (steps < 0 || steps > 65535) return Fail(err, "item: craft_steps out of range");
    if (reforges < 0 || reforges > 65535) return Fail(err, "item: craft_reforges out of range");
    it.craftSteps = static_cast<std::uint16_t>(steps);
    it.craftReforges = static_cast<std::uint16_t>(reforges);
    return true;
}

bool CharacterFromJson(const Value& o, CharacterState& c, std::string* err) {
    if (o.type() != json::Type::Object) return Fail(err, "character is not an object");
    c = CharacterState();
    c.name = o["name"].AsString();
    c.classId = o["class_id"].AsString();
    c.specId = o["spec_id"].AsString();
    c.level = static_cast<int>(o["level"].AsInt(1));
    c.xp = o["xp"].AsDouble(0.0);
    c.passives = ReadStrList(o["passives"]);
    for (const Value& s : o["skills"].Items()) {
        LearnedSkill ls;
        ls.skillId = s["skill_id"].AsString();
        ls.rank = static_cast<int>(s["rank"].AsInt(1));
        ls.sigils = ReadStrList(s["sigils"]);
        c.skills.push_back(std::move(ls));
    }
    const auto& bar = o["skill_bar"].Items();
    if (bar.size() > c.skillBar.size()) return Fail(err, "character: skill_bar has too many entries");
    for (std::size_t i = 0; i < bar.size(); ++i) c.skillBar[i] = bar[i].AsString();
    const Value& eq = o["equipment"];
    for (int s = 0; s < kItemSlotCount; ++s) {
        const Value* slotV = eq.Find(ToString(static_cast<ItemSlot>(s)));
        if (slotV == nullptr || slotV->IsNull()) continue;
        ItemInstance it;
        if (!ItemFromJson(*slotV, it, err)) return false;
        c.equipment[static_cast<std::size_t>(s)] = std::move(it);
    }
    {
        const auto& bp = o["backpack"].Items();
        if (bp.size() > kMaxSavedItems) return Fail(err, "character: backpack has too many items");
        for (const Value& iv : bp) {
            ItemInstance it;
            if (!ItemFromJson(iv, it, err)) return false;
            c.backpack.push_back(std::move(it));
        }
    }
    c.conqueredMaps = ReadStrList(o["conquered_maps"]);
    c.highestTierCleared = static_cast<int>(o["highest_tier_cleared"].AsInt(0));
    // Save v2 vindo de disco pode estar adulterado (o SHA-256 não tem segredo): valida faixas na leitura (docs/17, M1 e B6).
    for (const Value& s : o["potion_slots"].Items()) {
        PotionSlotState ps;
        ps.potionId = s["potion_id"].AsString();
        const std::int64_t charges = s["charges"].AsInt(0);
        const double recharge = s["recharge_remaining"].AsDouble(0.0);
        if (charges < 0 || charges > kMaxSavedPotionCharges) return Fail(err, "character: potion_slots charges out of range");
        if (!(recharge >= 0.0) || recharge > kMaxSavedRechargeSeconds) return Fail(err, "character: potion_slots recharge_remaining out of range");
        for (const PotionSlotState& q : c.potionSlots)
            if (q.potionId == ps.potionId) return Fail(err, "character: potion_slots repeats '" + ps.potionId + "'");
        ps.charges = static_cast<int>(charges);
        ps.rechargeRemaining = recharge;
        c.potionSlots.push_back(std::move(ps));
    }
    for (const Value& b : o["boss_progress"].Items()) {
        BossProgressEntry be;
        be.enemyId = b["enemy_id"].AsString();
        const std::int64_t kills = b["kills"].AsInt(0);
        const std::int64_t since = b["kills_since_unique"].AsInt(0);
        if (be.enemyId.empty()) return Fail(err, "character: boss_progress without enemy_id");
        if (FindBossProgress(c.bossProgress, be.enemyId) != nullptr)
            return Fail(err, "character: boss_progress repeats '" + be.enemyId + "'");
        if (kills < 0 || kills > kMaxBossCounter) return Fail(err, "character: boss_progress kills out of range");
        if (since < 0 || since > kills) return Fail(err, "character: boss_progress kills_since_unique out of range");
        be.kills = static_cast<int>(kills);
        be.killsSinceUnique = static_cast<int>(since);
        c.bossProgress.push_back(std::move(be));
    }
    c.playTimeSeconds = o["play_time_seconds"].AsDouble(0.0);
    return true;
}

bool ExpeditionRequestFromJson(const Value& o, ExpeditionRequest& r, std::string* err) {
    if (o.type() != json::Type::Object) return Fail(err, "request is not an object");
    r = ExpeditionRequest();
    const Value& snap = o["snapshot"];
    if (!CharacterFromJson(snap["character"], r.snapshot.character, err)) return false;
    r.snapshot.contentVersion = static_cast<std::uint32_t>(snap["content_version"].AsInt(0));
    r.mapId = o["map_id"].AsString();
    if (!ParseExpeditionObjective(o["objective"].AsString(), r.objective)) return Fail(err, "request: bad objective");
    for (const Value& rv : o["rules"].Items()) {
        AiRule ar;
        if (!ParseAiCondition(rv["condition"].AsString(), ar.condition)) return Fail(err, "rule: bad condition");
        ar.param = rv["param"].AsDouble(0.0);
        if (!ParseAiAction(rv["action"].AsString(), ar.action)) return Fail(err, "rule: bad action");
        ar.refId = rv["ref_id"].AsString();
        r.rules.push_back(std::move(ar));
    }
    r.seed = o["seed"].AsUInt64(0);
    r.startUtc = o["start_utc"].AsInt(0);
    if (r.startUtc < 0 || r.startUtc > kMaxSaveUtc) return Fail(err, "request: start_utc out of range");
    r.durationHours = static_cast<int>(o["duration_hours"].AsInt(1));
    r.effectiveSeconds = o["effective_seconds"].AsDouble(0.0);
    r.contentVersion = static_cast<std::uint32_t>(o["content_version"].AsInt(0));
    auto pct = [&](const char* key) { return static_cast<int>(std::clamp<std::int64_t>(o[key].AsInt(0), 0, 100)); };
    r.storyStatBonusPct = pct("story_stat_bonus_pct");
    r.storyPotionEffectPct = pct("story_potion_effect_pct");
    r.storyEliteBonusPct = pct("story_elite_bonus_pct");
    return true;
}

namespace {

// Aplica XP ao personagem com o teto de nível da área (mesma regra de FinalizeExpedition).
void ApplyXp(const ContentDB& db, CharacterState& c, double gained, int capLevel) {
    if (c.level >= capLevel) return;
    c.xp += gained;
    while (c.level < capLevel) {
        const double need = db.XpToNextLevel(c.level);
        if (c.xp + 1e-9 < need) break;
        c.xp -= need;
        if (c.xp < 0.0) c.xp = 0.0;
        ++c.level;
    }
    if (c.level >= capLevel) c.xp = 0.0;
}

void AddCurrency(std::vector<StackEntry>& list, const ContentId& id, std::int64_t amount) {
    for (StackEntry& s : list) {
        if (s.id == id) {
            s.amount += amount;
            return;
        }
    }
    list.push_back({id, amount});
}

}  // namespace

int AwardXp(const ContentDB& db, CharacterState& c, double gained, int capLevel) {
    const int before = c.level;
    ApplyXp(db, c, gained, capLevel);
    return c.level - before;
}

// ---------------------------------------------------------------------------
Value SaveToJson(const SaveData& s) {
    Value o = Value::MakeObject();
    o.Set("save_version", Value(kCurrentSaveVersion));
    o.Set("content_version", Value(s.contentVersion));
    Value chars = Value::MakeArray();
    for (const CharacterState& c : s.characters) chars.Push(CharacterToJson(c));
    o.Set("characters", std::move(chars));
    Value stash = Value::MakeArray();
    for (const ItemInstance& it : s.stash) stash.Push(ItemToJson(it));
    o.Set("stash", std::move(stash));
    Value cur = Value::MakeArray();
    for (const StackEntry& e : s.currencies) {
        Value eo = Value::MakeObject();
        eo.Set("id", Value(e.id));
        eo.Set("amount", Value(e.amount));
        cur.Push(std::move(eo));
    }
    o.Set("currencies", std::move(cur));
    o.Set("marker_charges", Value(s.markerCharges));
    o.Set("last_rest_day", Value(s.lastRestDay));
    o.Set("last_seen_utc", Value(static_cast<std::int64_t>(s.lastSeenUtc)));
    o.Set("next_item_uid", json::FromUInt64(s.nextItemUid));
    o.Set("expedition_slots", Value(s.expeditionSlots));
    Value exps = Value::MakeArray();
    for (const SavedExpedition& e : s.expeditions) {
        Value eo = Value::MakeObject();
        eo.Set("status", Value(ToString(e.status)));
        eo.Set("character_index", Value(e.characterIndex));
        eo.Set("request", ExpeditionRequestToJson(e.request));
        eo.Set("collected_result_hash", json::FromUInt64(e.collectedResultHash));
        exps.Push(std::move(eo));
    }
    o.Set("expeditions", std::move(exps));
    o.Set("codex_seen_uniques", StrList(s.codexSeenUniques));
    o.Set("books_seen", StrList(s.booksSeen));
    if (s.craftSeed != 0) o.Set("craft_seed", json::FromUInt64(s.craftSeed));
    if (!s.world.empty()) {
        Value ws = Value::MakeArray();
        for (const WorldAreaState& a : s.world) {
            Value ao = Value::MakeObject();
            ao.Set("map_id", Value(a.mapId));
            ao.Set("visits", Value(static_cast<std::int64_t>(a.visits)));
            ao.Set("opened", StrList(a.opened));
            ws.Push(std::move(ao));
        }
        o.Set("world_state", std::move(ws));
    }
    if (!s.story.Empty()) {
        Value so = Value::MakeObject();
        so.Set("hunger", Value(s.story.hunger));
        Value vs = Value::MakeArray();
        for (const StoryVerdictRecord& v : s.story.verdicts) {
            Value vo = Value::MakeObject();
            vo.Set("region_id", Value(v.regionId));
            vo.Set("verdict_id", Value(v.verdictId));
            vs.Push(std::move(vo));
        }
        so.Set("verdicts", std::move(vs));
        so.Set("echoes", StrList(s.story.echoes));
        if (!s.story.quests.empty()) {   // campo opcional dentro de `story`: saves sem missões mantêm os mesmos bytes
            Value qs = Value::MakeArray();
            for (const StoryQuestRecord& q : s.story.quests) {
                Value qo = Value::MakeObject();
                qo.Set("quest_id", Value(q.questId));
                qo.Set("progress", Value(q.progress));
                qo.Set("done", Value(q.done));
                qs.Push(std::move(qo));
            }
            so.Set("quests", std::move(qs));
        }
        o.Set("story", std::move(so));
    }
    if (!s.vendorBuyback.empty()) {
        Value bb = Value::MakeArray();
        for (const BuybackEntry& e : s.vendorBuyback) {
            Value eo = Value::MakeObject();
            eo.Set("item", ItemToJson(e.item));
            eo.Set("paid", Value(e.paid));
            bb.Push(std::move(eo));
        }
        o.Set("vendor_buyback", std::move(bb));
    }
    return o;
}

bool SaveFromJson(const Value& data, SaveData& out, std::string* error) {
    if (data.type() != json::Type::Object) return Fail(error, "data is not an object");
    SaveData s;
    s.saveVersion = kCurrentSaveVersion;
    s.contentVersion = static_cast<std::uint32_t>(data["content_version"].AsInt(0));
    for (const Value& cv : data["characters"].Items()) {
        CharacterState c;
        if (!CharacterFromJson(cv, c, error)) return false;
        s.characters.push_back(std::move(c));
    }
    for (const Value& iv : data["stash"].Items()) {
        ItemInstance it;
        if (!ItemFromJson(iv, it, error)) return false;
        s.stash.push_back(std::move(it));
    }
    if (s.stash.size() > kMaxSavedItems) return Fail(error, "stash has too many items");
    for (const Value& e : data["currencies"].Items()) s.currencies.push_back({e["id"].AsString(), e["amount"].AsInt(0)});
    s.markerCharges = static_cast<int>(data["marker_charges"].AsInt(0));
    s.lastRestDay = data["last_rest_day"].AsInt(0);
    s.lastSeenUtc = data["last_seen_utc"].AsInt(0);
    s.nextItemUid = data["next_item_uid"].AsUInt64(1);
    s.expeditionSlots = static_cast<int>(data["expedition_slots"].AsInt(1));
    for (const Value& ev : data["expeditions"].Items()) {
        SavedExpedition se;
        std::size_t idx = 0;
        if (!ParseName(kStatusNames, ev["status"].AsString(), idx)) return Fail(error, "expedition: bad status");
        se.status = static_cast<ExpeditionStatus>(idx);
        const std::int64_t ci = ev["character_index"].AsInt(-1);
        if (ci < -1 || ci > 1000000) return Fail(error, "expedition: character_index out of range");
        se.characterIndex = static_cast<int>(ci);
        // Expedição em andamento ou coletada precisa apontar para um personagem do save (senão fica presa para sempre).
        if (se.status != ExpeditionStatus::None && (ci < 0 || static_cast<std::size_t>(ci) >= s.characters.size()))
            return Fail(error, "expedition: character_index does not exist");
        if (!ExpeditionRequestFromJson(ev["request"], se.request, error)) return false;
        se.collectedResultHash = ev["collected_result_hash"].AsUInt64(0);
        s.expeditions.push_back(std::move(se));
    }
    s.codexSeenUniques = ReadStrList(data["codex_seen_uniques"]);
    s.booksSeen = ReadStrList(data["books_seen"]);
    s.craftSeed = data["craft_seed"].AsUInt64(0);
    {
        const auto& ws = data["world_state"].Items();
        if (ws.size() > kMaxWorldAreas) return Fail(error, "world_state has too many areas");
        for (const Value& av : ws) {
            WorldAreaState a;
            a.mapId = av["map_id"].AsString();
            const std::int64_t visits = av["visits"].AsInt(0);
            if (a.mapId.empty() || !IsValidContentId(a.mapId)) return Fail(error, "world_state: bad map_id");
            if (visits < 0 || visits > 4000000000LL) return Fail(error, "world_state: visits out of range");
            a.visits = static_cast<std::uint32_t>(visits);
            a.opened = ReadStrList(av["opened"]);
            if (a.opened.size() > kMaxWorldObjects) return Fail(error, "world_state: too many opened objects");
            for (const WorldAreaState& other : s.world)
                if (other.mapId == a.mapId) return Fail(error, "world_state repeats '" + a.mapId + "'");
            for (const ContentId& id : a.opened)
                if (!IsValidContentId(id)) return Fail(error, "world_state: bad object id");
            s.world.push_back(std::move(a));
        }
    }
    {
        const Value& so = data["story"];
        const std::int64_t hunger = so["hunger"].AsInt(0);
        if (hunger < 0 || hunger > kMaxSavedHunger) return Fail(error, "story: hunger out of range");
        s.story.hunger = static_cast<int>(hunger);
        const auto& vs = so["verdicts"].Items();
        if (vs.size() > kMaxSavedVerdicts) return Fail(error, "story: too many verdicts");
        for (const Value& vv : vs) {
            StoryVerdictRecord r;
            r.regionId = vv["region_id"].AsString();
            r.verdictId = vv["verdict_id"].AsString();
            if (!IsValidContentId(r.regionId) || !IsValidContentId(r.verdictId)) return Fail(error, "story: bad verdict id");
            for (const StoryVerdictRecord& other : s.story.verdicts)
                if (other.regionId == r.regionId) return Fail(error, "story repeats verdict for '" + r.regionId + "'");
            s.story.verdicts.push_back(std::move(r));
        }
        s.story.echoes = ReadStrList(so["echoes"]);
        if (s.story.echoes.size() > kMaxSavedEchoes) return Fail(error, "story: too many echoes");
        for (std::size_t i = 0; i < s.story.echoes.size(); ++i) {
            if (!IsValidContentId(s.story.echoes[i])) return Fail(error, "story: bad echo id");
            for (std::size_t j = 0; j < i; ++j)
                if (s.story.echoes[j] == s.story.echoes[i]) return Fail(error, "story repeats echo '" + s.story.echoes[i] + "'");
        }
        const auto& qs = so["quests"].Items();
        if (qs.size() > kMaxSavedQuests) return Fail(error, "story: too many quests");
        for (const Value& qv : qs) {
            StoryQuestRecord q;
            q.questId = qv["quest_id"].AsString();
            const std::int64_t progress = qv["progress"].AsInt(0);
            if (!qv["progress"].IsNumber() || qv["done"].type() != json::Type::Bool) return Fail(error, "story: bad quest field type");
            if (!IsValidContentId(q.questId)) return Fail(error, "story: bad quest id");
            if (progress < 0 || progress > 1000000) return Fail(error, "story: quest progress out of range");
            q.progress = static_cast<int>(progress);
            q.done = qv["done"].AsBool(false);
            for (const StoryQuestRecord& other : s.story.quests)
                if (other.questId == q.questId) return Fail(error, "story repeats quest '" + q.questId + "'");
            s.story.quests.push_back(std::move(q));
        }
    }
    {
        const auto& bb = data["vendor_buyback"].Items();
        if (bb.size() > kMaxSavedBuyback) return Fail(error, "vendor_buyback has too many items");
        for (const Value& ev : bb) {
            BuybackEntry e;
            if (!ItemFromJson(ev["item"], e.item, error)) return false;
            e.paid = ev["paid"].AsInt(0);
            if (e.paid < 0) return Fail(error, "vendor_buyback paid out of range");
            s.vendorBuyback.push_back(std::move(e));
        }
    }
    out = std::move(s);
    return true;
}

std::string SerializeJson(const SaveData& s, bool pretty) {
    Value data = SaveToJson(s);
    Value env = Value::MakeObject();
    env.Set("format", Value(kSaveFormatTag));
    env.Set("save_version", Value(kCurrentSaveVersion));
    env.Set("sha256", Value(Sha256::HexDigest(json::Serialize(data, false))));
    env.Set("data", std::move(data));
    std::string text = json::Serialize(env, pretty);
    if (pretty) text += '\n';
    return text;
}

LoadStatus ParseJson(std::string_view fileText, SaveData& out, std::string* error) {
    Value env;
    json::ParseError perr;
    if (!json::Parse(fileText, env, &perr)) {
        if (error) *error = "json: " + perr.message + " (line " + std::to_string(perr.line) + ")";
        return LoadStatus::BadJson;
    }
    if (env.type() != json::Type::Object || env["format"].AsString() != kSaveFormatTag) {
        if (error) *error = "format tag mismatch";
        return LoadStatus::BadFormatTag;
    }
    const Value* verV = env.Find("save_version");
    if (verV == nullptr || !verV->IsNumber() || verV->AsInt(0) < 1) {
        if (error) *error = "missing or invalid save_version";
        return LoadStatus::BadData;
    }
    const int version = static_cast<int>(verV->AsInt(0));
    if (version > kCurrentSaveVersion) {
        if (error) *error = "save_version " + std::to_string(version) + " is newer than this game";
        return LoadStatus::TooNew;
    }
    const Value* dataV = env.Find("data");
    if (dataV == nullptr || dataV->type() != json::Type::Object) {
        if (error) *error = "missing data object";
        return LoadStatus::BadData;
    }
    if (env["sha256"].AsString() != Sha256::HexDigest(json::Serialize(*dataV, false))) {
        if (error) *error = "sha256 mismatch";
        return LoadStatus::ChecksumMismatch;
    }
    Value data = *dataV;
    if (!Migrate(data, version, kCurrentSaveVersion, error)) return LoadStatus::MigrationFailed;
    SaveData tmp;
    if (!SaveFromJson(data, tmp, error)) return LoadStatus::BadData;
    out = std::move(tmp);
    return LoadStatus::Ok;
}

bool SaveContentVersionSupported(const SaveData& s, const ContentDB& db) {
    return s.contentVersion <= db.ContentVersion();
}

// ---------------------------------------------------------------------------
// Gravação segura e leitura com backups
// ---------------------------------------------------------------------------
bool WriteSaveFile(IFileIO& io, const std::string& basePath, const SaveData& s, std::string* error) {
    const std::string main = SavePath(basePath);
    const std::string tmp = SaveTmpPath(basePath);
    const std::string text = SerializeJson(s, true);

    // 1) grava o .tmp e confere relendo (hash + parse).
    if (!io.WriteAll(tmp, text)) return Fail(error, "cannot write tmp file");
    std::string back;
    SaveData check;
    if (!io.ReadAll(tmp, back) || back != text || ParseJson(back, check) != LoadStatus::Ok) {
        io.Remove(tmp);
        return Fail(error, "tmp file verification failed");
    }

    // 2) rotaciona os backups (só se o principal atual for válido: um principal corrompido
    //    nunca empurra backups bons para fora).
    SaveData current;
    std::string mainText;
    const bool mainValid = io.Exists(main) && io.ReadAll(main, mainText) && ParseJson(mainText, current) == LoadStatus::Ok;
    if (mainValid) {
        for (int n = kSaveBackupCount; n >= 2; --n) {
            const std::string from = SaveBackupPath(basePath, n - 1);
            if (io.Exists(from) && !io.Copy(from, SaveBackupPath(basePath, n))) {
                io.Remove(tmp);
                return Fail(error, "backup rotation failed");
            }
        }
        if (!io.Copy(main, SaveBackupPath(basePath, 1))) {
            io.Remove(tmp);
            return Fail(error, "backup copy failed");
        }
    }

    // 3) troca atômica.
    if (!io.Rename(tmp, main)) {
        io.Remove(tmp);
        return Fail(error, "rename failed");
    }
    return true;
}

LoadReport ReadSaveFile(IFileIO& io, const std::string& basePath, SaveData& out) {
    LoadReport rep;
    rep.status = LoadStatus::Missing;
    bool anyExisting = false;
    for (int n = 0; n <= kSaveBackupCount; ++n) {
        const std::string path = n == 0 ? SavePath(basePath) : SaveBackupPath(basePath, n);
        std::string text;
        if (!io.Exists(path)) continue;
        if (!io.ReadAll(path, text)) {
            if (!anyExisting) { rep.status = LoadStatus::BadJson; rep.error = "cannot read " + path; }
            anyExisting = true;
            continue;
        }
        std::string err;
        SaveData tmp;
        const LoadStatus st = ParseJson(text, tmp, &err);
        if (st == LoadStatus::Ok) {
            out = std::move(tmp);
            rep.status = LoadStatus::Ok;
            rep.usedBackup = n;
            rep.error.clear();
            return rep;
        }
        if (!anyExisting) {  // guarda o motivo do principal (ou do primeiro arquivo existente)
            rep.status = st;
            rep.error = err;
        }
        anyExisting = true;
        // Save de versão futura: nunca cai para um backup antigo (perderia progresso sem aviso).
        if (st == LoadStatus::TooNew) return rep;
    }
    return rep;
}

// ---------------------------------------------------------------------------
// Progresso manual e início de expedição
// ---------------------------------------------------------------------------
bool RecordAreaRun(const ContentDB& db, SaveData& s, std::size_t characterIndex, const ContentId& mapId,
                   const AreaRunOutcome& run, AreaRunReward* reward) {
    if (reward) *reward = AreaRunReward();
    if (characterIndex >= s.characters.size()) return false;
    const MapData* map = db.FindMap(mapId);
    if (map == nullptr) return false;
    const RulesConstants& r = db.Rules();
    CharacterState& ch = s.characters[characterIndex];

    const bool hasBoss = !map->bossEncounter.empty();
    const bool conquest = run.reachedEnd && (!hasBoss || run.bossDefeated);
    const bool already = std::find(ch.conqueredMaps.begin(), ch.conqueredMaps.end(), mapId) != ch.conqueredMaps.end();

    int gain = 0;
    if (run.bossDefeated && hasBoss) gain = std::max(gain, r.chargesBoss);
    if (run.reachedEnd) gain = std::max(gain, r.chargesClearArea);
    const bool newConquest = conquest && !already;
    if (newConquest) {
        gain += r.chargesNewArea;
        ch.conqueredMaps.push_back(mapId);
        if (map->tier > ch.highestTierCleared) ch.highestTierCleared = map->tier;
    }
    const int before = s.markerCharges;
    const int after = std::min(r.chargesMax, std::max(0, before) + gain);
    s.markerCharges = std::max(before, after);  // o teto nunca tira cargas que já estavam lá
    if (reward) {
        reward->chargesGained = s.markerCharges - before;
        reward->newConquest = newConquest;
    }
    return true;
}

StartCheck StartExpedition(const ContentDB& db, SaveData& s, const ExpeditionStartParams& p,
                           std::vector<ContentId>* blockingIds) {
    if (blockingIds) blockingIds->clear();
    if (p.characterIndex >= s.characters.size()) return StartCheck::UnknownContent;
    const CharacterState& ch = s.characters[p.characterIndex];
    bool running = false;
    for (const SavedExpedition& e : s.expeditions) running = running || e.status == ExpeditionStatus::Running;
    const StartCheck check =
        CanStartExpedition(db, ch, p.mapId, p.durationHours, s.markerCharges, running, p.rules.size(), blockingIds);
    if (check != StartCheck::Ok) return check;

    // Vaga: a primeira None/Collected; senão acrescenta, até expeditionSlots.
    std::size_t slot = s.expeditions.size();
    for (std::size_t i = 0; i < s.expeditions.size(); ++i) {
        if (s.expeditions[i].status != ExpeditionStatus::Running) {
            slot = i;
            break;
        }
    }
    const std::size_t maxSlots = s.expeditionSlots < 1 ? 1 : static_cast<std::size_t>(s.expeditionSlots);
    if (slot == s.expeditions.size() && slot >= maxSlots) return StartCheck::AnotherExpeditionRunning;

    SavedExpedition e;
    e.status = ExpeditionStatus::Running;
    e.characterIndex = static_cast<int>(p.characterIndex);
    e.request.snapshot.character = ch;  // cópia congelada (RF-38)
    e.request.snapshot.character.backpack.clear();  // a Mochila não entra na simulação (e não infla o pedido salvo)
    e.request.snapshot.contentVersion = db.ContentVersion();
    e.request.mapId = p.mapId;
    e.request.objective = p.objective;
    e.request.rules = p.rules;
    e.request.seed = p.seed;
    e.request.startUtc = p.startUtc;
    e.request.durationHours = p.durationHours;
    e.request.effectiveSeconds = 0.0;  // calculado ao abrir o jogo (clock.h)
    e.request.contentVersion = db.ContentVersion();
    e.request.storyStatBonusPct = std::clamp(p.storyStatBonusPct, 0, 100);
    e.request.storyPotionEffectPct = std::clamp(p.storyPotionEffectPct, 0, 100);
    e.request.storyEliteBonusPct = std::clamp(p.storyEliteBonusPct, 0, 100);
    e.collectedResultHash = 0;
    if (slot == s.expeditions.size()) s.expeditions.push_back(std::move(e));
    else s.expeditions[slot] = std::move(e);
    s.markerCharges -= p.durationHours * db.Rules().chargesPerHour;
    if (s.markerCharges < 0) s.markerCharges = 0;
    return StartCheck::Ok;
}

// ---------------------------------------------------------------------------
// Coleta sem duplicar
// ---------------------------------------------------------------------------
void NormalizeSavePotions(const ContentDB& db, SaveData& s) {
    if (db.Potions().empty()) return;
    for (CharacterState& c : s.characters) c.potionSlots = MakePotionBelt(db, c.potionSlots).slots;
    for (SavedExpedition& e : s.expeditions) {
        CharacterState& c = e.request.snapshot.character;
        c.potionSlots = MakePotionBelt(db, c.potionSlots).slots;
    }
}

std::uint64_t DeriveExpeditionSeed(const SaveData& s, std::size_t characterIndex, UnixSeconds startUtc) {
    std::uint64_t h = Mix64(0x45434F53454544ull ^ s.nextItemUid);
    h = Mix64(h ^ static_cast<std::uint64_t>(startUtc));
    h = Mix64(h ^ static_cast<std::uint64_t>(s.lastSeenUtc));
    h = Mix64(h ^ (static_cast<std::uint64_t>(characterIndex) << 32) ^ static_cast<std::uint64_t>(s.expeditions.size()));
    if (characterIndex < s.characters.size()) {
        const CharacterState& c = s.characters[characterIndex];
        std::uint64_t bits = 0;
        const double t = c.playTimeSeconds + c.xp;
        std::memcpy(&bits, &t, sizeof(bits));
        h = Mix64(h ^ bits ^ static_cast<std::uint64_t>(c.level));
    }
    return h;
}

bool CollectExpedition(const ContentDB& db, SaveData& s, std::size_t expeditionIndex, const ExpeditionResult& r) {
    if (expeditionIndex >= s.expeditions.size()) return false;
    SavedExpedition& e = s.expeditions[expeditionIndex];
    if (e.status != ExpeditionStatus::Running) return false;  // já coletada (mesmo hash ou outro) ou inexistente
    if (r.resultHash == 0) return false;
    if (e.characterIndex < 0 || static_cast<std::size_t>(e.characterIndex) >= s.characters.size()) return false;

    CharacterState& ch = s.characters[static_cast<std::size_t>(e.characterIndex)];
    int capLevel = db.Rules().maxLevel;
    if (const MapData* m = db.FindMap(e.request.mapId))
        capLevel = std::min(capLevel, m->monsterLevel + db.Rules().xpLevelCapAboveArea);

    for (const ItemInstance& src : r.items) {
        ItemInstance it = src;
        it.uid = s.nextItemUid++;
        s.stash.push_back(std::move(it));
    }
    for (const StackEntry& st : r.stacks) AddCurrency(s.currencies, st.id, st.amount);
    ApplyXp(db, ch, r.xpGained, capLevel);

    e.status = ExpeditionStatus::Collected;
    e.collectedResultHash = r.resultHash;
    return true;
}

}  // namespace shatter
