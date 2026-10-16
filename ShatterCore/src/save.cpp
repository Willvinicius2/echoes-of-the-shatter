// ShatterCore — save em JSON: SaveData <-> árvore JSON, envelope com SHA-256, gravação segura e coleta.
#include "shatter/save.h"

#include <algorithm>
#include <cmath>

#include "shatter/sha256.h"

namespace shatter {

namespace {

using json::Value;

// ---------------------------------------------------------------------------
// Enums <-> texto
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// SaveData -> JSON
// ---------------------------------------------------------------------------
Value StrList(const std::vector<ContentId>& v) {
    Value a = Value::MakeArray();
    for (const ContentId& s : v) a.Push(Value(s));
    return a;
}

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
        affixes.Push(std::move(ao));
    }
    o.Set("affixes", std::move(affixes));
    o.Set("has_inscription", Value(it.hasInscription));
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
    o.Set("conquered_maps", StrList(c.conqueredMaps));
    o.Set("highest_tier_cleared", Value(c.highestTierCleared));
    o.Set("potions", Value(c.potions));
    o.Set("play_time_seconds", Value(c.playTimeSeconds));
    return o;
}

Value RequestToJson(const ExpeditionRequest& r) {
    Value o = Value::MakeObject();
    Value snap = Value::MakeObject();
    snap.Set("character", CharacterToJson(r.snapshot.character));
    snap.Set("content_version", Value(r.snapshot.contentVersion));
    o.Set("snapshot", std::move(snap));
    o.Set("map_id", Value(r.mapId));
    o.Set("objective", Value(kObjectiveNames[static_cast<std::size_t>(r.objective)]));
    Value rules = Value::MakeArray();
    for (const AiRule& ar : r.rules) {
        Value ro = Value::MakeObject();
        ro.Set("condition", Value(kConditionNames[static_cast<std::size_t>(ar.condition)]));
        ro.Set("param", Value(ar.param));
        ro.Set("action", Value(kActionNames[static_cast<std::size_t>(ar.action)]));
        ro.Set("ref_id", Value(ar.refId));
        rules.Push(std::move(ro));
    }
    o.Set("rules", std::move(rules));
    o.Set("potion_heal_fraction", Value(r.potionHealFraction));
    o.Set("seed", json::FromUInt64(r.seed));
    o.Set("start_utc", Value(static_cast<std::int64_t>(r.startUtc)));
    o.Set("duration_hours", Value(r.durationHours));
    o.Set("effective_seconds", Value(r.effectiveSeconds));
    o.Set("content_version", Value(r.contentVersion));
    return o;
}

// ---------------------------------------------------------------------------
// JSON -> SaveData
// ---------------------------------------------------------------------------
std::vector<ContentId> ReadStrList(const Value& v) {
    std::vector<ContentId> out;
    for (const Value& e : v.Items()) out.push_back(e.AsString());
    return out;
}

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
        it.affixes.push_back(std::move(ra));
    }
    it.hasInscription = o["has_inscription"].AsBool(false);
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
    c.conqueredMaps = ReadStrList(o["conquered_maps"]);
    c.highestTierCleared = static_cast<int>(o["highest_tier_cleared"].AsInt(0));
    c.potions = o["potions"].AsInt(0);
    c.playTimeSeconds = o["play_time_seconds"].AsDouble(0.0);
    return true;
}

bool RequestFromJson(const Value& o, ExpeditionRequest& r, std::string* err) {
    if (o.type() != json::Type::Object) return Fail(err, "request is not an object");
    r = ExpeditionRequest();
    const Value& snap = o["snapshot"];
    if (!CharacterFromJson(snap["character"], r.snapshot.character, err)) return false;
    r.snapshot.contentVersion = static_cast<std::uint32_t>(snap["content_version"].AsInt(0));
    r.mapId = o["map_id"].AsString();
    std::size_t idx = 0;
    if (!ParseName(kObjectiveNames, o["objective"].AsString(), idx)) return Fail(err, "request: bad objective");
    r.objective = static_cast<ExpeditionObjective>(idx);
    for (const Value& rv : o["rules"].Items()) {
        AiRule ar;
        if (!ParseName(kConditionNames, rv["condition"].AsString(), idx)) return Fail(err, "rule: bad condition");
        ar.condition = static_cast<AiCondition>(idx);
        ar.param = rv["param"].AsDouble(0.0);
        if (!ParseName(kActionNames, rv["action"].AsString(), idx)) return Fail(err, "rule: bad action");
        ar.action = static_cast<AiAction>(idx);
        ar.refId = rv["ref_id"].AsString();
        r.rules.push_back(std::move(ar));
    }
    r.potionHealFraction = o["potion_heal_fraction"].AsDouble(0.35);
    r.seed = o["seed"].AsUInt64(0);
    r.startUtc = o["start_utc"].AsInt(0);
    r.durationHours = static_cast<int>(o["duration_hours"].AsInt(1));
    r.effectiveSeconds = o["effective_seconds"].AsDouble(0.0);
    r.contentVersion = static_cast<std::uint32_t>(o["content_version"].AsInt(0));
    return true;
}

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
        eo.Set("status", Value(kStatusNames[static_cast<std::size_t>(e.status)]));
        eo.Set("character_index", Value(e.characterIndex));
        eo.Set("request", RequestToJson(e.request));
        eo.Set("collected_result_hash", json::FromUInt64(e.collectedResultHash));
        exps.Push(std::move(eo));
    }
    o.Set("expeditions", std::move(exps));
    o.Set("codex_seen_uniques", StrList(s.codexSeenUniques));
    o.Set("books_seen", StrList(s.booksSeen));
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
        se.characterIndex = static_cast<int>(ev["character_index"].AsInt(-1));
        if (!RequestFromJson(ev["request"], se.request, error)) return false;
        se.collectedResultHash = ev["collected_result_hash"].AsUInt64(0);
        s.expeditions.push_back(std::move(se));
    }
    s.codexSeenUniques = ReadStrList(data["codex_seen_uniques"]);
    s.booksSeen = ReadStrList(data["books_seen"]);
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
// Coleta sem duplicar
// ---------------------------------------------------------------------------
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
