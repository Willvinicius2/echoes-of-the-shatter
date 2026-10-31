// ShatterCore — spawner de hordas do roguelike 2D (rogue_waves.h) e leitura de ondas.csv (RogueData::LoadWavesCsv).
#include "shatter/rogue_waves.h"

#include <algorithm>
#include <cmath>
#include <limits>

#include "csv.h"
#include "numtext.h"
#include "shatter/json.h"
#include "shatter/rng.h"
#include "shatter/sha256.h"

namespace shatter {

namespace {

using detail::CsvRow;
using detail::CsvTable;
using json::Value;

constexpr std::string_view kWavesTable = "ondas.csv";
// Limites de sanidade (não são balanceamento: só recusam dado absurdo).
constexpr double kMaxSeconds = 100000.0;
constexpr int kMaxBatch = 1000;
constexpr int kMaxCap = 1000;
constexpr int kMaxWeight = 1000000;
constexpr int kMaxCost = 1000000;
constexpr std::int64_t kMaxBudget = 1000000000;
constexpr int kMaxElites = 1000;
constexpr double kMaxMult = 1000.0;
constexpr double kMaxRadius = 100000.0;
constexpr double kTwoPi = 6.283185307179586;  // 2π (constante; nada de trigonometria no core)

bool IntCell(std::string_view cell, int lo, int hi, int& out) {
    std::int64_t v = 0;
    if (!detail::ParseInt64(cell, v) || v < lo || v > hi) return false;
    out = static_cast<int>(v);
    return true;
}

// Segundos > 0 e finitos -> microssegundos.
bool SecondsCell(std::string_view cell, double& s, std::int64_t& us) {
    if (!detail::ParseDouble(cell, s) || !(s > 0.0) || !(s <= kMaxSeconds)) return false;
    us = static_cast<std::int64_t>(std::llround(s * 1000000.0));
    return us > 0;
}

// Multiplicador do elite: vazio = 1.
bool MultCell(std::string_view cell, double& out) {
    if (cell.empty()) {
        out = 1.0;
        return true;
    }
    return detail::ParseDouble(cell, out) && out > 0.0 && out <= kMaxMult;
}

// "id:peso|id:peso:custo" (partes vazias ignoradas).
bool ParseMix(std::string_view spec, std::vector<RogueWaveMix>& out) {
    out.clear();
    for (std::string_view part : detail::SplitView(spec, '|')) {
        if (part.empty()) continue;
        const std::vector<std::string_view> f = detail::SplitView(part, ':');
        if (f.size() < 2 || f.size() > 3 || f[0].empty()) return false;
        RogueWaveMix m;
        m.enemy = ContentId(f[0]);
        if (!IntCell(f[1], 1, kMaxWeight, m.weight)) return false;
        if (f.size() == 3 && !IntCell(f[2], 1, kMaxCost, m.cost)) return false;
        for (const RogueWaveMix& o : out)
            if (o.enemy == m.enemy) return false;
        out.push_back(std::move(m));
    }
    return true;
}

Value SpawnValue(const RogueWaveSpawn& s) {
    Value o = Value::MakeObject();
    o.Set("id", Value(s.id));
    o.Set("enemy", Value(s.enemy));
    o.Set("elite", Value(s.elite));
    o.Set("boss", Value(s.boss));
    o.Set("wave", Value(s.wave));
    o.Set("angle", Value(s.angle));
    o.Set("radius", Value(s.radius));
    o.Set("hp_mult", Value(s.hpMult));
    o.Set("damage_mult", Value(s.damageMult));
    return o;
}

bool SpawnFromValue(const Value& v, RogueWaveSpawn& s) {
    if (v.type() != json::Type::Object) return false;
    const std::int64_t id = v["id"].AsInt(-1), wave = v["wave"].AsInt(-1);
    if (id < 1 || id > std::numeric_limits<std::uint32_t>::max() || wave < 1) return false;
    if (v["enemy"].type() != json::Type::String || v["enemy"].AsString().empty()) return false;
    if (!v["angle"].IsNumber() || !v["radius"].IsNumber() || !v["hp_mult"].IsNumber() || !v["damage_mult"].IsNumber())
        return false;
    s.id = static_cast<std::uint32_t>(id);
    s.enemy = v["enemy"].AsString();
    s.elite = v["elite"].AsBool(false);
    s.boss = v["boss"].AsBool(false);
    s.wave = static_cast<int>(wave);
    s.angle = v["angle"].AsDouble(0.0);
    s.radius = v["radius"].AsDouble(0.0);
    s.hpMult = v["hp_mult"].AsDouble(1.0);
    s.damageMult = v["damage_mult"].AsDouble(1.0);
    return s.angle >= 0.0 && s.angle < kTwoPi && s.radius >= 0.0;
}

}  // namespace

// ---------------------------------------------------------------------------------------------------------------
// ondas.csv
// ---------------------------------------------------------------------------------------------------------------
bool RogueData::LoadWavesCsv(std::string_view text) {
    const std::size_t before = errors_.size();
    const std::string name(kWavesTable);
    waves_.clear();
    CsvTable t;
    detail::CsvError ce;
    if (!detail::ParseCsv(text, t, ce)) {
        errors_.push_back({name, ce.line, ce.message});
        return false;
    }
    const std::vector<std::string_view> want = {"fase", "onda",     "duracao", "intervalo",  "lote",      "orcamento",
                                                "teto", "inimigos", "elites",  "elite_vida", "elite_dano"};
    bool headerOk = t.header.size() == want.size();
    for (std::size_t i = 0; headerOk && i < want.size(); ++i) headerOk = t.header[i] == want[i];
    if (!headerOk) {
        errors_.push_back({name, t.headerLine, "unexpected header"});
        return false;
    }
    for (const CsvRow& r : t.rows) {
        auto bad = [&](const std::string& msg) { errors_.push_back({name, r.line, msg}); };
        RogueWaveDef w;
        w.phase = std::string(r.cells[0]);
        if (w.phase.empty()) bad("fase is empty");
        const bool samePhase = !waves_.empty() && waves_.back().phase == w.phase;
        const int expected = samePhase ? waves_.back().wave + 1 : 1;
        if (!IntCell(r.cells[1], 1, kMaxCap, w.wave) || w.wave != expected) bad("onda must count 1, 2, 3... in each fase");
        if (!samePhase)
            for (const RogueWaveDef& o : waves_)
                if (o.phase == w.phase) {
                    bad("fase '" + w.phase + "' is split in two blocks");
                    break;
                }
        if (!SecondsCell(r.cells[2], w.duration, w.durationUs)) bad("duracao must be > 0 s");
        if (!SecondsCell(r.cells[3], w.interval, w.intervalUs)) bad("intervalo must be > 0 s");
        if (!IntCell(r.cells[4], 1, kMaxBatch, w.batch)) bad("lote out of range");
        std::int64_t b = 0;
        if (!detail::ParseInt64(r.cells[5], b) || b < 0 || b > kMaxBudget) bad("orcamento out of range");
        w.budget = b;
        if (!IntCell(r.cells[6], 1, kMaxCap, w.cap)) bad("teto out of range");
        w.mixText = std::string(r.cells[7]);
        if (!ParseMix(r.cells[7], w.mix)) bad("inimigos is not id:peso|id:peso:custo (ids sem repetir)");
        for (const RogueWaveMix& m : w.mix) w.minCost = w.minCost == 0 ? m.cost : std::min(w.minCost, m.cost);
        if (w.mix.empty()) bad("inimigos is empty");
        if (!IntCell(r.cells[8], 0, kMaxElites, w.elites)) bad("elites out of range");
        if (w.elites > 0 && w.mix.empty()) bad("elites without inimigos");
        if (!MultCell(r.cells[9], w.eliteHp)) bad("elite_vida must be > 0");
        if (!MultCell(r.cells[10], w.eliteDamage)) bad("elite_dano must be > 0");
        if (w.budget == 0) bad("orcamento must be > 0");
        waves_.push_back(std::move(w));
    }
    return errors_.size() == before;
}

bool RogueData::LoadWavePhasesCsv(std::string_view text) {
    const std::size_t before = errors_.size();
    const std::string name = "ondas_fases.csv";
    wavePhases_.clear();
    CsvTable t;
    detail::CsvError ce;
    if (!detail::ParseCsv(text, t, ce)) {
        errors_.push_back({name, ce.line, ce.message});
        return false;
    }
    const std::vector<std::string_view> want = {"fase",          "prazo",          "raio_min",         "raio_max",
                                                "chefe",         "despertar_onda", "enxame_inimigos",  "enxame_orcamento",
                                                "enxame_lote",   "enxame_intervalo", "enxame_teto"};
    bool headerOk = t.header.size() == want.size();
    for (std::size_t i = 0; headerOk && i < want.size(); ++i) headerOk = t.header[i] == want[i];
    if (!headerOk) {
        errors_.push_back({name, t.headerLine, "unexpected header"});
        return false;
    }
    for (const CsvRow& r : t.rows) {
        auto bad = [&](const std::string& msg) { errors_.push_back({name, r.line, msg}); };
        RogueWavePhaseDef p;
        p.id = std::string(r.cells[0]);
        if (p.id.empty()) bad("fase is empty");
        if (FindWavePhaseDef(p.id) != nullptr) bad("duplicate fase '" + p.id + "'");
        if (!SecondsCell(r.cells[1], p.deadline, p.deadlineUs)) bad("prazo must be > 0 s");
        if (!detail::ParseDouble(r.cells[2], p.ringMin) || !(p.ringMin > 0.0) || !(p.ringMin <= kMaxRadius))
            bad("raio_min must be > 0");
        if (!detail::ParseDouble(r.cells[3], p.ringMax) || !(p.ringMax >= p.ringMin) || !(p.ringMax <= kMaxRadius))
            bad("raio_max must be >= raio_min");
        p.boss = std::string(r.cells[4]);
        if (!IntCell(r.cells[5], 1, kMaxCap, p.wakeWave)) bad("despertar_onda out of range");
        RogueWaveDef& w = p.swarm;
        w.phase = p.id;
        w.mixText = std::string(r.cells[6]);
        if (!ParseMix(r.cells[6], w.mix) || w.mix.empty()) bad("enxame_inimigos is not id:peso|id:peso:custo");
        for (const RogueWaveMix& m : w.mix) w.minCost = w.minCost == 0 ? m.cost : std::min(w.minCost, m.cost);
        std::int64_t b = 0;
        if (!detail::ParseInt64(r.cells[7], b) || b < 1 || b > kMaxBudget) bad("enxame_orcamento out of range");
        w.budget = b;
        if (!IntCell(r.cells[8], 1, kMaxBatch, w.batch)) bad("enxame_lote out of range");
        if (!SecondsCell(r.cells[9], w.interval, w.intervalUs)) bad("enxame_intervalo must be > 0 s");
        if (!IntCell(r.cells[10], 1, kMaxCap, w.cap)) bad("enxame_teto out of range");
        w.duration = p.deadline;  // sem efeito: o enxame não passa de onda
        w.durationUs = p.deadlineUs;
        wavePhases_.push_back(std::move(p));
    }
    return errors_.size() == before;
}

void RogueData::CheckWaves() {
    const std::string waves = "ondas.csv", phases = "ondas_fases.csv";
    for (const std::string& id : WavePhases()) {
        const RogueWavePhaseDef* p = FindWavePhaseDef(id);
        if (p == nullptr) {
            errors_.push_back({phases, 0, "fase '" + id + "' of ondas.csv has no row"});
            continue;
        }
        int first = -1, count = 0;
        FindWavePhase(id, first, count);
        if (p->wakeWave > count) errors_.push_back({phases, 0, "despertar_onda beyond the ondas of '" + id + "'"});
    }
    for (RogueWavePhaseDef& p : wavePhases_) {
        int first = -1, count = 0;
        if (!FindWavePhase(p.id, first, count)) {
            errors_.push_back({waves, 0, "fase '" + p.id + "' of ondas_fases.csv has no ondas"});
            continue;
        }
        p.swarm.wave = count + 1;
    }
}

const RogueWavePhaseDef* RogueData::FindWavePhaseDef(std::string_view phase) const {
    for (const RogueWavePhaseDef& p : wavePhases_)
        if (p.id == phase) return &p;
    return nullptr;
}

std::vector<std::string> RogueData::WavePhases() const {
    std::vector<std::string> out;
    for (const RogueWaveDef& w : waves_)
        if (out.empty() || out.back() != w.phase) out.push_back(w.phase);
    return out;
}

bool RogueData::FindWavePhase(std::string_view phase, int& first, int& count) const {
    first = -1;
    count = 0;
    for (std::size_t i = 0; i < waves_.size(); ++i) {
        if (waves_[i].phase != phase) continue;
        if (first < 0) first = static_cast<int>(i);
        ++count;
    }
    return first >= 0;
}

// ---------------------------------------------------------------------------------------------------------------
// RogueWaves
// ---------------------------------------------------------------------------------------------------------------
const RogueWaveDef& RogueWaves::Def() const {
    return swarm_ ? pdef_->swarm : data_->Waves()[static_cast<std::size_t>(phase_ + wave_)];
}

const RogueWaveDef* RogueWaves::CurrentDef() const { return Running() ? &Def() : nullptr; }

std::string RogueWaves::PhaseId() const { return Running() ? pdef_->id : std::string(); }

int RogueWaves::Wave() const { return Running() ? wave_ + 1 : 0; }

bool RogueWaves::Exhausted() const {
    if (!Running()) return true;
    const RogueWaveDef& d = Def();
    return d.mix.empty() || budgetLeft_ < d.minCost;
}

bool RogueWaves::BossAlive() const {
    for (const RogueWaveSpawn& s : alive_)
        if (s.boss) return true;
    return false;
}

RogueWaveResult RogueWaves::Start(std::string_view phase, std::uint64_t seed) {
    int first = -1, count = 0;
    if (data_ == nullptr || !data_->FindWavePhase(phase, first, count)) return RogueWaveResult::Unknown;
    const RogueWavePhaseDef* p = data_->FindWavePhaseDef(phase);
    if (p == nullptr) return RogueWaveResult::Unknown;
    Stop();
    pdef_ = p;
    phase_ = first;
    count_ = count;
    seed_ = seed;
    EnterWave(0, 0);
    return RogueWaveResult::Ok;
}

void RogueWaves::Stop() {
    pdef_ = nullptr;
    phase_ = -1;
    count_ = 0;
    wave_ = 0;
    swarm_ = false;
    loops_ = 0;
    seed_ = 0;
    now_ = waveStart_ = nextSpawn_ = 0;
    waveEndPassed_ = false;
    budgetLeft_ = spent_ = 0;
    elitesSpawned_ = 0;
    spawned_ = killed_ = 0;
    bossSpawned_ = bossKilled_ = complete_ = false;
    alive_.clear();
    pending_.clear();
}

void RogueWaves::EnterWave(int wave, std::int64_t at) {
    wave_ = wave;
    waveStart_ = at;
    nextSpawn_ = at;  // o 1º lote nasce no início da onda
    waveEndPassed_ = false;
    const RogueWaveDef& d = Def();
    budgetLeft_ = d.budget;
    spent_ = 0;
    elitesSpawned_ = 0;
}

void RogueWaves::StartSwarm(std::int64_t at) {
    swarm_ = true;
    EnterWave(count_, at);
    waveEndPassed_ = true;  // o enxame não passa de onda
    if (!pdef_->boss.empty() && !bossSpawned_) SpawnBoss();
}

RogueWaveSpawn RogueWaves::MakeSpawn(bool boss) {
    const RogueWaveDef& d = Def();
    RogueWaveSpawn s;
    s.id = ++spawned_;
    s.boss = boss;
    s.wave = wave_ + 1;
    Pcg32 rng = Pcg32::ForStream(seed_, RngStream::RogueWave, s.id);
    if (boss) {
        s.enemy = pdef_->boss;
    } else {
        std::uint32_t total = 0;
        for (const RogueWaveMix& m : d.mix)
            if (m.cost <= budgetLeft_) total += static_cast<std::uint32_t>(m.weight);
        std::uint32_t r = rng.NextBelow(total);
        for (const RogueWaveMix& m : d.mix) {
            if (m.cost > budgetLeft_) continue;
            const std::uint32_t w = static_cast<std::uint32_t>(m.weight);
            if (r < w) {
                s.enemy = m.enemy;
                const std::int64_t spentAfter = spent_ + m.cost;
                // k-ésimo elite quando o gasto chega a k / (elites + 1) do orçamento.
                if (elitesSpawned_ < d.elites &&
                    spentAfter * (d.elites + 1) >= static_cast<std::int64_t>(elitesSpawned_ + 1) * d.budget) {
                    s.elite = true;
                    ++elitesSpawned_;
                }
                spent_ = spentAfter;
                budgetLeft_ -= m.cost;
                break;
            }
            r -= w;
        }
    }
    s.angle = rng.NextUnit() * kTwoPi;
    s.radius = pdef_->ringMin + (pdef_->ringMax - pdef_->ringMin) * rng.NextUnit();
    if (s.elite) {
        s.hpMult = d.eliteHp;
        s.damageMult = d.eliteDamage;
    }
    return s;
}

void RogueWaves::SpawnBoss() {
    const RogueWaveSpawn s = MakeSpawn(true);
    bossSpawned_ = true;
    alive_.push_back(s);
    pending_.push_back(s);
}

void RogueWaves::SpawnBatch() {
    const RogueWaveDef& d = Def();
    for (int k = 0; k < d.batch; ++k) {
        if (Exhausted()) return;
        int regular = 0;
        for (const RogueWaveSpawn& s : alive_) regular += s.boss ? 0 : 1;
        if (regular >= d.cap) return;
        const RogueWaveSpawn s = MakeSpawn(false);
        alive_.push_back(s);
        pending_.push_back(s);
    }
}

void RogueWaves::CheckComplete() {
    if (!Running() || complete_) return;
    if (!pdef_->boss.empty()) complete_ = bossKilled_;
    else complete_ = swarm_ && Exhausted() && alive_.empty();
}

int RogueWaves::Tick(double dt) {
    if (!Running() || complete_ || !(dt > 0.0) || !std::isfinite(dt)) return 0;
    const std::size_t before = pending_.size();
    const double clamped = std::min(dt, kRogueWaveMaxTick);
    const std::int64_t target = now_ + static_cast<std::int64_t>(std::llround(clamped * 1000000.0));
    constexpr std::int64_t kNever = std::numeric_limits<std::int64_t>::max();
    for (;;) {
        // Eventos em ordem de tempo; no mesmo instante: prazo, fim da onda, lote.
        const std::int64_t deadline = swarm_ ? kNever : pdef_->deadlineUs;
        const std::int64_t waveEnd = waveEndPassed_ ? kNever : waveStart_ + Def().durationUs;
        if (deadline <= target && deadline <= waveEnd && deadline <= nextSpawn_) {
            now_ = deadline;
            StartSwarm(now_);
            continue;
        }
        if (waveEnd <= target && waveEnd <= nextSpawn_) {
            now_ = waveEnd;
            waveEndPassed_ = true;
            if (Exhausted()) {
                loops_ += LastWave() ? 1 : 0;
                EnterWave(LastWave() ? wave_ : wave_ + 1, now_);
            }
            continue;
        }
        if (nextSpawn_ > target) break;
        now_ = nextSpawn_;
        SpawnBatch();
        nextSpawn_ += Def().intervalUs;
        if (!swarm_ && Exhausted() && (waveEndPassed_ || alive_.empty())) {
            // A última onda recomeça até o prazo.
            loops_ += LastWave() ? 1 : 0;
            EnterWave(LastWave() ? wave_ : wave_ + 1, now_);
            continue;
        }
        CheckComplete();
        if (complete_) break;
    }
    if (!complete_) now_ = target;
    return static_cast<int>(pending_.size() - before);
}

RogueWaveResult RogueWaves::Killed(std::uint32_t id, RogueWaveSpawn* out) {
    if (!Running()) return RogueWaveResult::NotRunning;
    for (std::size_t i = 0; i < alive_.size(); ++i) {
        if (alive_[i].id != id) continue;
        if (out != nullptr) *out = alive_[i];
        if (alive_[i].boss) bossKilled_ = true;
        alive_.erase(alive_.begin() + static_cast<std::ptrdiff_t>(i));
        ++killed_;
        CheckComplete();
        return RogueWaveResult::Ok;
    }
    return RogueWaveResult::NotAlive;
}

RogueWaveResult RogueWaves::CheckWake() const {
    if (!Running() || complete_) return RogueWaveResult::NotRunning;
    if (pdef_->boss.empty()) return RogueWaveResult::NoBoss;
    if (bossSpawned_) return RogueWaveResult::AlreadyAwake;
    if (!swarm_ && wave_ + 1 < pdef_->wakeWave) return RogueWaveResult::TooEarly;
    return RogueWaveResult::Ok;
}

RogueWaveResult RogueWaves::WakeBoss() {
    const RogueWaveResult r = CheckWake();
    if (r == RogueWaveResult::Ok) SpawnBoss();
    return r;
}

// ---------------------------------------------------------------------------------------------------------------
// Estado canônico
// ---------------------------------------------------------------------------------------------------------------
std::string RogueWaves::StateJson() const {
    Value o = Value::MakeObject();
    o.Set("format", Value(kRogueWaveStateFormat));
    o.Set("phase", Value(PhaseId()));
    if (Running()) {
        o.Set("seed", json::FromUInt64(seed_));
        o.Set("wave", Value(wave_ + 1));
        o.Set("swarm", Value(swarm_));
        o.Set("loops", Value(loops_));
        o.Set("now", Value(now_));
        o.Set("wave_start", Value(waveStart_));
        o.Set("next_spawn", Value(nextSpawn_));
        o.Set("wave_end_passed", Value(waveEndPassed_));
        o.Set("budget_left", Value(budgetLeft_));
        o.Set("spent", Value(spent_));
        o.Set("elites_spawned", Value(elitesSpawned_));
        o.Set("spawned", Value(spawned_));
        o.Set("killed", Value(killed_));
        o.Set("boss_spawned", Value(bossSpawned_));
        o.Set("boss_killed", Value(bossKilled_));
        o.Set("complete", Value(complete_));
        Value al = Value::MakeArray();
        for (const RogueWaveSpawn& s : alive_) al.Push(SpawnValue(s));
        o.Set("alive", std::move(al));
        Value pe = Value::MakeArray();
        for (const RogueWaveSpawn& s : pending_) pe.Push(SpawnValue(s));
        o.Set("pending", std::move(pe));
    }
    return json::Serialize(o, false);
}

bool RogueWaves::RestoreState(std::string_view text, std::string* error) {
    auto fail = [&](const char* msg) {
        if (error != nullptr) *error = msg;
        return false;
    };
    if (data_ == nullptr) return fail("no data");
    Value d;
    if (!json::Parse(text, d) || d.type() != json::Type::Object) return fail("state is not a json object");
    if (d["format"].AsInt(0) != kRogueWaveStateFormat) return fail("unknown state format");
    RogueWaves t(*data_);
    const std::string phase = d["phase"].AsString();
    if (phase.empty()) {
        *this = t;
        return true;
    }
    t.pdef_ = data_->FindWavePhaseDef(phase);
    if (t.pdef_ == nullptr || !data_->FindWavePhase(phase, t.phase_, t.count_)) return fail("unknown phase");
    t.swarm_ = d["swarm"].AsBool(false);
    const std::int64_t wave = d["wave"].AsInt(0), loops = d["loops"].AsInt(-1);
    if (t.swarm_ ? wave != t.count_ + 1 : (wave < 1 || wave > t.count_)) return fail("wave out of range");
    if (loops < 0 || loops > std::numeric_limits<int>::max()) return fail("bad loops");
    t.wave_ = static_cast<int>(wave - 1);
    t.loops_ = static_cast<int>(loops);
    if (d["seed"].type() != json::Type::String) return fail("bad seed");
    t.seed_ = d["seed"].AsUInt64(0);
    t.now_ = d["now"].AsInt(-1);
    t.waveStart_ = d["wave_start"].AsInt(-1);
    t.nextSpawn_ = d["next_spawn"].AsInt(-1);
    if (t.now_ < 0 || t.waveStart_ < 0 || t.waveStart_ > t.now_ || t.nextSpawn_ < t.waveStart_)
        return fail("bad clock");
    t.waveEndPassed_ = d["wave_end_passed"].AsBool(false);
    t.budgetLeft_ = d["budget_left"].AsInt(-1);
    t.spent_ = d["spent"].AsInt(-1);
    const RogueWaveDef& def = t.Def();
    if (t.budgetLeft_ < 0 || t.spent_ < 0 || t.budgetLeft_ + t.spent_ != def.budget) return fail("bad budget");
    const std::int64_t el = d["elites_spawned"].AsInt(-1);
    if (el < 0 || el > def.elites) return fail("bad elites");
    t.elitesSpawned_ = static_cast<int>(el);
    const std::int64_t sp = d["spawned"].AsInt(-1), ki = d["killed"].AsInt(-1);
    if (sp < 0 || ki < 0 || ki > sp || sp > std::numeric_limits<std::uint32_t>::max()) return fail("bad counters");
    t.spawned_ = static_cast<std::uint32_t>(sp);
    t.killed_ = static_cast<std::uint32_t>(ki);
    t.bossSpawned_ = d["boss_spawned"].AsBool(false);
    t.bossKilled_ = d["boss_killed"].AsBool(false);
    t.complete_ = d["complete"].AsBool(false);
    for (const char* key : {"alive", "pending"}) {
        std::vector<RogueWaveSpawn>& list = std::string_view(key) == "alive" ? t.alive_ : t.pending_;
        for (const Value& v : d[key].Items()) {
            RogueWaveSpawn s;
            if (!SpawnFromValue(v, s) || s.id > t.spawned_ || s.wave > t.count_ + 1) return fail("bad spawn");
            list.push_back(std::move(s));
        }
    }
    if (t.alive_.size() != static_cast<std::size_t>(t.spawned_ - t.killed_)) return fail("alive does not match counters");
    *this = t;
    return true;
}

std::string RogueWaves::StateHash() const { return Sha256::HexDigest(StateJson()); }

}  // namespace shatter
