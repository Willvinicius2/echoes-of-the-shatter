// ShatterCore — XP, nível e cartas de nível da corrida do roguelike 2D, curva de horda por onda, vida do chefe
// adaptativa e modo horda (rogue.h, API 1.12; plano docs/design/31, pacote H4; docs/tecnico/09 seção 19).
#include <algorithm>
#include <cmath>
#include <limits>

#include "csv.h"
#include "numtext.h"
#include "shatter/json.h"
#include "shatter/rng.h"
#include "shatter/rogue.h"

namespace shatter {

namespace {

using detail::CsvRow;
using detail::CsvTable;
using json::Value;

constexpr std::string_view kCurveTable = "curva_horda.csv";
// Limites de sanidade (não são balanceamento).
constexpr double kMaxCurveMult = 1000.0;
constexpr std::int64_t kMaxXp = 1000000000;
constexpr int kMaxCards = 1000;
constexpr int kMaxCharLevel = 100000;

bool PositiveMult(std::string_view cell, double& out) {
    return detail::ParseDouble(cell, out) && out > 0.0 && out <= kMaxCurveMult;
}

// Arredonda para o inteiro mais próximo (meio para longe do zero), só para valores >= 0.
std::int64_t RoundNonNegative(double v) {
    if (!(v > 0.0)) return 0;
    if (v >= static_cast<double>(kMaxXp)) return kMaxXp;
    return static_cast<std::int64_t>(std::floor(v + 0.5));
}

}  // namespace

// ---------------------------------------------------------------------------------------------------------------
// Dados
// ---------------------------------------------------------------------------------------------------------------
bool RogueData::LoadCurveCsv(std::string_view text) {
    const std::size_t before = errors_.size();
    const std::string name(kCurveTable);
    curve_.clear();
    CsvTable t;
    detail::CsvError ce;
    if (!detail::ParseCsv(text, t, ce)) {
        errors_.push_back({name, ce.line, ce.message});
        return false;
    }
    const std::vector<std::string_view> want = {"fase", "onda", "vida", "dano", "velocidade", "xp"};
    bool headerOk = t.header.size() == want.size();
    for (std::size_t i = 0; headerOk && i < want.size(); ++i) headerOk = t.header[i] == want[i];
    if (!headerOk) {
        errors_.push_back({name, t.headerLine, "unexpected header"});
        return false;
    }
    for (const CsvRow& r : t.rows) {
        auto bad = [&](const std::string& msg) { errors_.push_back({name, r.line, msg}); };
        RogueCurveRow c;
        c.phase = std::string(r.cells[0]);
        if (c.phase.empty()) bad("fase is empty");
        std::int64_t w = 0;
        if (!detail::ParseInt64(r.cells[1], w) || w < 1 || w > 100000) bad("onda out of range");
        c.wave = static_cast<int>(w);
        if (!PositiveMult(r.cells[2], c.hp)) bad("vida must be > 0");
        if (!PositiveMult(r.cells[3], c.damage)) bad("dano must be > 0");
        if (!PositiveMult(r.cells[4], c.speed)) bad("velocidade must be > 0");
        if (!PositiveMult(r.cells[5], c.xp)) bad("xp must be > 0");
        for (const RogueCurveRow& o : curve_)
            if (o.phase == c.phase && o.wave == c.wave) bad("duplicate fase and onda");
        curve_.push_back(std::move(c));
    }
    return errors_.size() == before;
}

// No Finalize: chaves opcionais de nível e do chefe; curva só de fases e ondas que existem (onda + 1 = enxame).
void RogueData::FinalizeLevels() {
    auto E = [&](const std::string& table, const std::string& msg) { errors_.push_back({table, 0, msg}); };
    auto optInt = [&](const char* key, std::int64_t hi, std::int64_t& out) {
        double v = 0.0;
        if (!Setting(key, v)) return;
        if (!(v >= 0.0 && v <= static_cast<double>(hi)) || v != static_cast<double>(static_cast<std::int64_t>(v))) {
            E("run_settings.csv", std::string("chave must be a non-negative integer: ") + key);
            return;
        }
        out = static_cast<std::int64_t>(v);
    };
    std::int64_t cards = 0, chest = 0, rerolls = 0, skips = 0, bans = 0, every = 0;
    optInt("skill_points_every_levels", kMaxCards, every);
    skillEveryLevels_ = static_cast<int>(every);
    optInt("xp_level_base", kMaxXp, xpLevelBase_);
    optInt("xp_level_step", kMaxXp, xpLevelStep_);
    optInt("level_cards", kMaxCards, cards);
    optInt("chest_cards", kMaxCards, chest);
    optInt("level_rerolls", kMaxCards, rerolls);
    optInt("level_skips", kMaxCards, skips);
    optInt("level_bans", kMaxCards, bans);
    levelCards_ = static_cast<int>(cards);
    chestCards_ = static_cast<int>(chest);
    levelRerolls_ = static_cast<int>(rerolls);
    levelSkips_ = static_cast<int>(skips);
    levelBans_ = static_cast<int>(bans);
    auto optPos = [&](const char* key, double& out) {
        double v = 0.0;
        if (!Setting(key, v)) return;
        if (!(v > 0.0 && v <= 1.0e9)) {
            E("run_settings.csv", std::string("chave must be > 0: ") + key);
            return;
        }
        out = v;
    };
    optPos("boss_fight_time", bossFightTime_);
    optPos("boss_hp_min", bossHpMin_);
    optPos("boss_hp_max", bossHpMax_);
    if (bossFightTime_ > 0.0 && (bossHpMin_ <= 0.0 || bossHpMax_ < bossHpMin_))
        E("run_settings.csv", "boss_fight_time needs boss_hp_min > 0 and boss_hp_max >= boss_hp_min");
    for (const RogueCurveRow& c : curve_) {
        int first = -1, count = 0;
        if (!FindWavePhase(c.phase, first, count)) {
            E(std::string(kCurveTable), "fase '" + c.phase + "' is not in ondas.csv");
            continue;
        }
        if (c.wave > count + 1) E(std::string(kCurveTable), "onda beyond the ondas (+ enxame) of '" + c.phase + "'");
    }
}

const RogueCurveRow* RogueData::FindCurve(std::string_view phase, int wave) const {
    for (const RogueCurveRow& c : curve_)
        if (c.phase == phase && c.wave == wave) return &c;
    return nullptr;
}

double RogueData::BossHp(double baseHp, double dps) const {
    if (!(baseHp > 0.0) || !(baseHp < 1.0e15)) return baseHp;
    if (!(bossFightTime_ > 0.0) || !(dps > 0.0) || !(dps < 1.0e12)) return baseHp;
    const double want = dps * bossFightTime_;
    return std::min(baseHp * bossHpMax_, std::max(baseHp * bossHpMin_, want));
}

std::int64_t RogueData::XpForLevel(int level) const {
    if (xpLevelBase_ <= 0) return 0;
    const std::int64_t steps = level > 1 ? static_cast<std::int64_t>(level - 1) : 0;
    const std::int64_t extra = xpLevelStep_ > 0 && steps > (kMaxXp / xpLevelStep_) ? kMaxXp : xpLevelStep_ * steps;
    return std::min<std::int64_t>(kMaxXp, xpLevelBase_ + extra);
}

// ---------------------------------------------------------------------------------------------------------------
// Modo horda
// ---------------------------------------------------------------------------------------------------------------
RogueRunResult RogueState::SetHorde(bool on) {
    if (phase_ != RoguePhase::None && phase_ != RoguePhase::Won && phase_ != RoguePhase::Dead)
        return RogueRunResult::WrongPhase;
    horde_ = on;
    return RogueRunResult::Ok;
}

RogueRunResult RogueState::WinRun(RogueKill* out) {
    if (out != nullptr) *out = RogueKill();
    if (data_ == nullptr || !horde_ || (phase_ != RoguePhase::Fight && phase_ != RoguePhase::Cleared))
        return RogueRunResult::WrongPhase;
    RogueKill k;
    phase_ = RoguePhase::Won;
    const std::int64_t v = data_->VictoryFragments();
    gainFragments_ = gainFragments_ > std::numeric_limits<std::int64_t>::max() - v ? std::numeric_limits<std::int64_t>::max()
                                                                                    : gainFragments_ + v;
    if (class_ >= 0) {
        k.skillPoints = data_->SkillPointsBoss();
        if (k.skillPoints > 0) AddSkillPoints(k.skillPoints);
    }
    levelOffer_.clear();
    offerKind_ = 0;
    pendingLevels_ = pendingChests_ = 0;
    if (out != nullptr) *out = k;
    return RogueRunResult::Ok;
}

// ---------------------------------------------------------------------------------------------------------------
// XP e nível
// ---------------------------------------------------------------------------------------------------------------
void RogueState::ResetLevels() {
    levelUsed_ = false;
    xp_ = 0;
    charLevel_ = 1;
    pendingLevels_ = pendingChests_ = 0;
    offerKind_ = 0;
    levelOffer_.clear();
    levelDraws_ = 0;
    rerolls_ = data_ != nullptr ? data_->LevelRerolls() : 0;
    skips_ = data_ != nullptr ? data_->LevelSkips() : 0;
    bans_ = data_ != nullptr ? data_->LevelBans() : 0;
    banned_.assign(data_ != nullptr ? data_->Upgrades().size() : 0, 0);
}

RogueRunResult RogueState::LevelPhaseOk() const {
    if (data_ == nullptr || phase_ == RoguePhase::None || phase_ == RoguePhase::Won || phase_ == RoguePhase::Dead)
        return RogueRunResult::WrongPhase;
    return RogueRunResult::Ok;
}

std::int64_t RogueState::XpNext() const { return data_ != nullptr ? data_->XpForLevel(charLevel_) : 0; }

const char* RogueState::LevelOfferKind() const { return offerKind_ == 1 ? "level" : (offerKind_ == 2 ? "chest" : ""); }

bool RogueState::Banned(std::string_view upgradeId) const {
    const int i = data_ != nullptr ? data_->FindUpgrade(upgradeId) : -1;
    return i >= 0 && static_cast<std::size_t>(i) < banned_.size() && banned_[static_cast<std::size_t>(i)] != 0;
}

RogueRunResult RogueState::KillXp(std::string_view enemyId, double xpMult, bool elite, std::int64_t* xp,
                                  bool* chest) const {
    if (xp != nullptr) *xp = 0;
    if (chest != nullptr) *chest = false;
    if (data_ == nullptr) return RogueRunResult::WrongPhase;
    const RogueDrop* d = data_->FindDrop(enemyId);
    if (d == nullptr) return RogueRunResult::Unknown;
    const double mult = xpMult > 0.0 && xpMult <= kMaxCurveMult ? xpMult : 1.0;
    if (xp != nullptr) *xp = RoundNonNegative(static_cast<double>(d->xp) * mult);
    if (chest != nullptr) *chest = elite && data_->ChestCards() > 0;
    return RogueRunResult::Ok;
}

// Oferta do tipo offerKind_ (1 nível, 2 baú): embaralha os disponíveis (sem banidos); o baú só leva raras (se houver).
// A oferta de nível garante uma carta de ataque: se o sorteio não trouxe nenhuma, a última dá lugar à primeira de
// ataque que sobrou no embaralhamento.
void RogueState::DrawLevelOffer() {
    levelOffer_.clear();
    std::vector<ContentId> pool = AvailableUpgrades();
    if (offerKind_ == 2) {
        std::vector<ContentId> rare;
        for (const ContentId& id : pool)
            if (data_->Upgrades()[static_cast<std::size_t>(data_->FindUpgrade(id))].rare) rare.push_back(id);
        if (!rare.empty()) pool = std::move(rare);
    }
    Pcg32 rng = Pcg32::ForStream(seed_, RngStream::RogueLevel, levelDraws_);
    ++levelDraws_;
    for (std::size_t i = pool.size(); i > 1; --i) {
        const std::size_t j = static_cast<std::size_t>(rng.RangeInt(0, static_cast<std::int32_t>(i - 1)));
        std::swap(pool[i - 1], pool[j]);
    }
    const std::size_t count = static_cast<std::size_t>(offerKind_ == 2 ? data_->ChestCards() : data_->LevelCards());
    auto isAttack = [&](const ContentId& id) {
        return data_->Upgrades()[static_cast<std::size_t>(data_->FindUpgrade(id))].attack;
    };
    if (pool.size() > count) {
        if (offerKind_ == 1 && count > 0 && std::none_of(pool.begin(), pool.begin() + static_cast<std::ptrdiff_t>(count), isAttack)) {
            const auto it = std::find_if(pool.begin() + static_cast<std::ptrdiff_t>(count), pool.end(), isAttack);
            if (it != pool.end()) std::swap(pool[count - 1], *it);
        }
        pool.resize(count);
    }
    levelOffer_ = std::move(pool);
}

// Abre a próxima oferta da fila (níveis antes de baús). Oferta que sairia vazia (tudo no máximo) é descartada.
void RogueState::NextLevelOffer() {
    while (levelOffer_.empty()) {
        if (externalCards_) {  // classe sem cartas: o nível sobe, mas não há oferta
            pendingLevels_ = pendingChests_ = 0;
        }
        if (pendingLevels_ > 0) {
            --pendingLevels_;
            offerKind_ = 1;
        } else if (pendingChests_ > 0) {
            --pendingChests_;
            offerKind_ = 2;
        } else {
            offerKind_ = 0;
            return;
        }
        DrawLevelOffer();
    }
}

RogueRunResult RogueState::GainXp(std::int64_t amount, int* levelsOut) {
    if (levelsOut != nullptr) *levelsOut = 0;
    const RogueRunResult ok = LevelPhaseOk();
    if (ok != RogueRunResult::Ok) return ok;
    if (amount <= 0) return RogueRunResult::Ok;
    levelUsed_ = true;
    xp_ = std::min<std::int64_t>(kMaxXp, xp_ + std::min<std::int64_t>(kMaxXp, amount));
    int gained = 0;
    for (std::int64_t need = XpNext(); need > 0 && xp_ >= need && charLevel_ < kMaxCharLevel; need = XpNext()) {
        xp_ -= need;
        ++charLevel_;
        ++gained;
        ++pendingLevels_;
        const int every = data_->SkillPointsEveryLevels();
        if (horde_ && class_ >= 0 && every > 0 && (charLevel_ - 1) % every == 0) AddSkillPoints(1);
    }
    if (XpNext() <= 0) xp_ = 0;
    NextLevelOffer();
    if (levelsOut != nullptr) *levelsOut = gained;
    return RogueRunResult::Ok;
}

RogueRunResult RogueState::OpenChest() {
    const RogueRunResult ok = LevelPhaseOk();
    if (ok != RogueRunResult::Ok) return ok;
    levelUsed_ = true;
    ++pendingChests_;
    NextLevelOffer();
    return RogueRunResult::Ok;
}

RogueRunResult RogueState::ChooseLevelCard(std::string_view upgradeId, double hp, double* hpOut) {
    if (hpOut != nullptr) *hpOut = hp;
    const RogueRunResult ok = LevelPhaseOk();
    if (ok != RogueRunResult::Ok) return ok;
    if (levelOffer_.empty()) return RogueRunResult::WrongPhase;
    if (std::find(levelOffer_.begin(), levelOffer_.end(), upgradeId) == levelOffer_.end()) return RogueRunResult::NotOffered;
    const int i = data_->FindUpgrade(upgradeId);
    if (i < 0) return RogueRunResult::Unknown;
    const std::size_t k = static_cast<std::size_t>(i);
    if (runLevels_[k] >= data_->Upgrades()[k].maxLevel) return RogueRunResult::NotOffered;
    BumpUpgrade(k, hp, hpOut);
    levelOffer_.clear();
    NextLevelOffer();
    return RogueRunResult::Ok;
}

RogueRunResult RogueState::RerollLevel() {
    const RogueRunResult ok = LevelPhaseOk();
    if (ok != RogueRunResult::Ok) return ok;
    if (levelOffer_.empty() || rerolls_ <= 0) return RogueRunResult::WrongPhase;
    --rerolls_;
    DrawLevelOffer();
    NextLevelOffer();
    return RogueRunResult::Ok;
}

RogueRunResult RogueState::SkipLevel() {
    const RogueRunResult ok = LevelPhaseOk();
    if (ok != RogueRunResult::Ok) return ok;
    if (levelOffer_.empty() || skips_ <= 0) return RogueRunResult::WrongPhase;
    --skips_;
    levelOffer_.clear();
    NextLevelOffer();
    return RogueRunResult::Ok;
}

RogueRunResult RogueState::BanCard(std::string_view upgradeId) {
    const RogueRunResult ok = LevelPhaseOk();
    if (ok != RogueRunResult::Ok) return ok;
    if (levelOffer_.empty() || bans_ <= 0) return RogueRunResult::WrongPhase;
    if (std::find(levelOffer_.begin(), levelOffer_.end(), upgradeId) == levelOffer_.end()) return RogueRunResult::NotOffered;
    const int i = data_->FindUpgrade(upgradeId);
    if (i < 0) return RogueRunResult::Unknown;
    --bans_;
    banned_[static_cast<std::size_t>(i)] = 1;
    DrawLevelOffer();
    NextLevelOffer();
    return RogueRunResult::Ok;
}

// ---------------------------------------------------------------------------------------------------------------
// Estado ("run.progress", só quando algo de nível aconteceu)
// ---------------------------------------------------------------------------------------------------------------
Value RogueState::LevelStateValue() const {
    Value o = Value::MakeObject();
    o.Set("xp", Value(xp_));
    o.Set("level", Value(charLevel_));
    o.Set("pending_levels", Value(pendingLevels_));
    o.Set("pending_chests", Value(pendingChests_));
    o.Set("kind", Value(offerKind_));
    Value off = Value::MakeArray();
    for (const ContentId& id : levelOffer_) off.Push(Value(id));
    o.Set("offer", std::move(off));
    o.Set("draws", json::FromUInt64(levelDraws_));
    o.Set("rerolls", Value(rerolls_));
    o.Set("skips", Value(skips_));
    o.Set("bans", Value(bans_));
    Value ban = Value::MakeArray();
    for (std::size_t i = 0; i < banned_.size(); ++i)
        if (banned_[i] != 0) ban.Push(Value(data_->Upgrades()[i].id));
    o.Set("banned", std::move(ban));
    return o;
}

bool RogueState::LevelStateFrom(const Value& v) {
    if (v.type() != json::Type::Object || data_ == nullptr) return false;
    auto intIn = [&](const char* key, std::int64_t lo, std::int64_t hi, std::int64_t& out) {
        const Value& x = v[key];
        if (x.type() != json::Type::Int) return false;
        out = x.AsInt(lo - 1);
        return out >= lo && out <= hi;
    };
    std::int64_t xp = 0, level = 0, pl = 0, pc = 0, kind = 0, rr = 0, sk = 0, bn = 0;
    if (!intIn("xp", 0, kMaxXp, xp) || !intIn("level", 1, kMaxCharLevel, level) ||
        !intIn("pending_levels", 0, kMaxCharLevel, pl) || !intIn("pending_chests", 0, kMaxCharLevel, pc) ||
        !intIn("kind", 0, 2, kind) || !intIn("rerolls", 0, kMaxCards, rr) || !intIn("skips", 0, kMaxCards, sk) ||
        !intIn("bans", 0, kMaxCards, bn))
        return false;
    if (v["draws"].type() != json::Type::String) return false;
    const std::uint64_t bad = std::numeric_limits<std::uint64_t>::max();
    const std::uint64_t draws = v["draws"].AsUInt64(bad);
    if (draws == bad) return false;
    std::vector<ContentId> offer;
    for (const Value& x : v["offer"].Items()) {
        if (x.type() != json::Type::String || data_->FindUpgrade(x.AsString()) < 0) return false;
        offer.push_back(x.AsString());
    }
    if ((kind == 0) != offer.empty()) return false;
    std::vector<std::uint8_t> banned(data_->Upgrades().size(), 0);
    for (const Value& x : v["banned"].Items()) {
        const int i = x.type() == json::Type::String ? data_->FindUpgrade(x.AsString()) : -1;
        if (i < 0) return false;
        banned[static_cast<std::size_t>(i)] = 1;
    }
    levelUsed_ = true;
    xp_ = xp;
    charLevel_ = static_cast<int>(level);
    pendingLevels_ = static_cast<int>(pl);
    pendingChests_ = static_cast<int>(pc);
    offerKind_ = static_cast<int>(kind);
    levelOffer_ = std::move(offer);
    levelDraws_ = draws;
    rerolls_ = static_cast<int>(rr);
    skips_ = static_cast<int>(sk);
    bans_ = static_cast<int>(bn);
    banned_ = std::move(banned);
    return true;
}

}  // namespace shatter
