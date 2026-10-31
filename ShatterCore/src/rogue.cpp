// ShatterCore — roguelike 2D da Cripta (rogue.h). Paridade com godot/scripts2d/{meta_2d,upgrades_2d,run_2d}.gd.
#include "shatter/rogue.h"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <limits>
#include <system_error>

#include "csv.h"
#include "numtext.h"
#include "shatter/json.h"
#include "shatter/rng.h"
#include "shatter/sha256.h"

namespace shatter {

namespace {

namespace fs = std::filesystem;
using detail::CsvRow;
using detail::CsvTable;
using json::Value;

// Tipos de sala que mudam regra (ids de dados de rota.csv; o padrão de run.csv é "combate").
constexpr std::string_view kKindCombat = "combate";
constexpr std::string_view kKindElite = "elite";
constexpr std::string_view kKindRest = "descanso";
// Stat da vida máxima: o ganho de hp_max sobe a vida atual e o descanso cura uma fração dele (contrato com o cliente).
constexpr std::string_view kHpMaxStat = "hp_max";
// Limites de sanidade das tabelas (não são balanceamento: só recusam dado absurdo).
constexpr std::int64_t kMaxCount = 1000000000;
constexpr int kMaxLevel = 1000;
constexpr int kMaxEnemiesPerKind = 1000;

// Classes do cliente 2D (opcional) e colunas de texto da árvore de habilidades (doc 29); as demais são números.
constexpr std::string_view kClassesTable = "classes_2d.csv";
constexpr const char* kSkillTextColumns[] = {"id", "ramo", "tipo", "pai", "efeito", "stat", "modo", "icone"};

bool IsSkillTextColumn(std::string_view col) {
    for (const char* c : kSkillTextColumns)
        if (col == c) return true;
    return false;
}

int ColumnIndex(const detail::CsvTable& t, std::string_view col) {
    for (std::size_t i = 0; i < t.header.size(); ++i)
        if (t.header[i] == col) return static_cast<int>(i);
    return -1;
}

// "res://data2d/habilidades_mago.csv" -> "habilidades_mago.csv" (o core lê da pasta que recebeu).
std::string_view BaseName(std::string_view path) {
    const std::size_t cut = path.find_last_of("/\\");
    return cut == std::string_view::npos ? path : path.substr(cut + 1);
}

constexpr const char* kTables[] = {"meta.csv", "receitas.csv", "drops.csv", "rota.csv", "run.csv", "run_settings.csv",
                                   "upgrades.csv"};

bool Header(const CsvTable& t, const std::vector<std::string_view>& want, std::string_view table,
            std::vector<ContentError>& errs) {
    bool ok = t.header.size() == want.size();
    for (std::size_t i = 0; ok && i < want.size(); ++i) ok = t.header[i] == want[i];
    if (!ok) errs.push_back({std::string(table), t.headerLine, "unexpected header"});
    return ok;
}

bool Int64In(std::string_view cell, std::int64_t lo, std::int64_t hi, std::int64_t& out) {
    std::int64_t v = 0;
    if (!detail::ParseInt64(cell, v) || v < lo || v > hi) return false;
    out = v;
    return true;
}

bool IntIn(std::string_view cell, int lo, int hi, int& out) {
    std::int64_t v = 0;
    if (!Int64In(cell, lo, hi, v)) return false;
    out = static_cast<int>(v);
    return true;
}

bool Mode(std::string_view cell, RogueMode& out) {
    if (cell == "add") out = RogueMode::Add;
    else if (cell == "mult") out = RogueMode::Mult;
    else return false;
    return true;
}

// "id:n|id:n" (partes vazias ignoradas, como split("|", false) do GDScript).
bool ParseEnemies(std::string_view spec, std::vector<RogueEnemyCount>& out, int& total) {
    out.clear();
    total = 0;
    for (std::string_view part : detail::SplitView(spec, '|')) {
        if (part.empty()) continue;
        const std::vector<std::string_view> kv = detail::SplitView(part, ':');
        if (kv.size() != 2 || kv[0].empty()) return false;
        int n = 0;
        if (!IntIn(kv[1], 1, kMaxEnemiesPerKind, n)) return false;
        out.push_back({ContentId(kv[0]), n});
        total += n;
    }
    return true;
}

template <class T>
int IndexById(const std::vector<T>& list, std::string_view id) {
    for (std::size_t i = 0; i < list.size(); ++i)
        if (list[i].id == id) return static_cast<int>(i);
    return -1;
}

std::int64_t SatAdd(std::int64_t a, std::int64_t b) {
    if (b > 0 && a > std::numeric_limits<std::int64_t>::max() - b) return std::numeric_limits<std::int64_t>::max();
    if (b < 0 && a < std::numeric_limits<std::int64_t>::min() - b) return std::numeric_limits<std::int64_t>::min();
    return a + b;
}

// int() do GDScript sobre um valor de JSON (o JSON do Godot lê todo número como float): trunca em direção a zero.
std::int64_t LooseInt(const Value& v) {
    switch (v.type()) {
        case json::Type::Int: return v.AsInt(0);
        case json::Type::Double: {
            const double d = v.AsDouble(0.0);
            if (!(d == d)) return 0;
            if (d >= 9.2e18) return std::numeric_limits<std::int64_t>::max();
            if (d <= -9.2e18) return std::numeric_limits<std::int64_t>::min();
            return static_cast<std::int64_t>(d);
        }
        case json::Type::Bool: return v.AsBool(false) ? 1 : 0;
        case json::Type::String: {
            std::int64_t out = 0;
            return detail::ParseInt64(v.AsString(), out) ? out : 0;
        }
        default: return 0;
    }
}

int ClampLevel(std::int64_t v, int hi) { return static_cast<int>(std::clamp<std::int64_t>(v, 0, hi)); }

void ApplyBonus(RogueStats& s, const std::string& stat, RogueMode mode, double value) {
    for (auto& p : s) {
        if (p.first != stat) continue;
        if (mode == RogueMode::Mult) p.second = p.second * (1.0 + value);
        else p.second = p.second + value;
        return;
    }
}

bool FindStat(const RogueStats& s, std::string_view stat, double& out) {
    for (const auto& p : s) {
        if (p.first == stat) {
            out = p.second;
            return true;
        }
    }
    return false;
}

RoguePhase PhaseFromName(std::string_view n, bool& ok) {
    ok = true;
    for (int i = 0; i <= static_cast<int>(RoguePhase::Dead); ++i) {
        const RoguePhase p = static_cast<RoguePhase>(i);
        if (n == RoguePhaseName(p)) return p;
    }
    ok = false;
    return RoguePhase::None;
}

}  // namespace

const char* RogueModeName(RogueMode m) { return m == RogueMode::Mult ? "mult" : "add"; }

const char* RoguePhaseName(RoguePhase p) {
    switch (p) {
        case RoguePhase::None: return "none";
        case RoguePhase::Fight: return "fight";
        case RoguePhase::Cleared: return "cleared";
        case RoguePhase::Choice: return "choice";
        case RoguePhase::Route: return "route";
        case RoguePhase::Won: return "won";
        case RoguePhase::Dead: return "dead";
    }
    return "none";
}

// ---------------------------------------------------------------------------------------------------------------
// RogueData
// ---------------------------------------------------------------------------------------------------------------
bool RogueData::LoadTableCsv(std::string_view table, std::string_view text) {
    const std::size_t before = errors_.size();
    const std::string name(table);
    CsvTable t;
    detail::CsvError ce;
    if (!detail::ParseCsv(text, t, ce)) {
        errors_.push_back({name, ce.line, ce.message});
        return false;
    }
    auto bad = [&](const CsvRow& r, const std::string& msg) { errors_.push_back({name, r.line, msg}); };
    auto S = [](const CsvRow& r, std::size_t i) { return std::string(r.cells[i]); };

    if (table == "meta.csv") {
        if (!Header(t, {"id", "tipo", "alvo", "stat", "modo", "valor", "custo", "nivel_max"}, table, errors_)) return false;
        for (const CsvRow& r : t.rows) {
            RogueMetaDef d;
            d.id = S(r, 0);
            if (d.id.empty()) bad(r, "id is empty");
            if (r.cells[1] == "habilidade") d.ability = true;
            else if (r.cells[1] != "stat") bad(r, "tipo must be stat or habilidade");
            d.target = S(r, 2);
            d.stat = S(r, 3);
            if (d.ability) {
                if (d.target.empty()) bad(r, "habilidade needs alvo");
            } else {
                if (d.stat.empty()) bad(r, "stat needs a stat");
                if (!Mode(r.cells[4], d.mode)) bad(r, "modo must be add or mult");
                if (!detail::ParseDouble(r.cells[5], d.value)) bad(r, "valor is not a number");
            }
            if (d.ability && !r.cells[5].empty() && !detail::ParseDouble(r.cells[5], d.value)) bad(r, "valor is not a number");
            if (!Int64In(r.cells[6], 0, kMaxCount, d.cost)) bad(r, "custo out of range");
            if (!IntIn(r.cells[7], 1, kMaxLevel, d.maxLevel)) bad(r, "nivel_max out of range");
            if (IndexById(meta_, d.id) >= 0) bad(r, "duplicate id '" + d.id + "'");
            meta_.push_back(std::move(d));
        }
    } else if (table == "receitas.csv") {
        if (!Header(t, {"id", "tipo", "stat", "modo", "valor", "mat1", "qtd1", "mat2", "qtd2", "fragmentos", "estoque_max"},
                    table, errors_))
            return false;
        for (const CsvRow& r : t.rows) {
            RogueRecipe x;
            x.id = S(r, 0);
            if (x.id.empty()) bad(r, "id is empty");
            if (r.cells[1] == "amuleto") x.amulet = true;
            else if (r.cells[1] != "consumivel") bad(r, "tipo must be amuleto or consumivel");
            x.stat = S(r, 2);
            if (x.stat.empty()) bad(r, "stat is empty");
            if (!Mode(r.cells[3], x.mode)) bad(r, "modo must be add or mult");
            if (!detail::ParseDouble(r.cells[4], x.value)) bad(r, "valor is not a number");
            for (std::size_t k = 5; k <= 7; k += 2) {
                if (r.cells[k].empty()) continue;
                std::int64_t q = 0;
                if (!Int64In(r.cells[k + 1], 1, kMaxCount, q)) bad(r, "material quantity out of range");
                x.materials.emplace_back(S(r, k), q);
            }
            if (x.materials.size() == 2 && x.materials[0].first == x.materials[1].first) bad(r, "mat1 equals mat2");
            if (!Int64In(r.cells[9], 0, kMaxCount, x.fragments)) bad(r, "fragmentos out of range");
            if (!IntIn(r.cells[10], 1, kMaxLevel, x.maxStock)) bad(r, "estoque_max out of range");
            if (IndexById(recipes_, x.id) >= 0) bad(r, "duplicate id '" + x.id + "'");
            recipes_.push_back(std::move(x));
        }
    } else if (table == "drops.csv") {
        if (!Header(t, {"inimigo", "fragmentos", "material", "material_qtd"}, table, errors_)) return false;
        for (const CsvRow& r : t.rows) {
            RogueDrop d;
            d.enemy = S(r, 0);
            if (d.enemy.empty()) bad(r, "inimigo is empty");
            if (!Int64In(r.cells[1], 0, kMaxCount, d.fragments)) bad(r, "fragmentos out of range");
            d.material = S(r, 2);
            if (!Int64In(r.cells[3], 0, kMaxCount, d.materialQty)) bad(r, "material_qtd out of range");
            if (!d.material.empty() && d.materialQty < 1) bad(r, "material without quantity");
            if (d.material.empty() && d.materialQty != 0) bad(r, "material_qtd without material");
            for (const RogueDrop& o : drops_)
                if (o.enemy == d.enemy) bad(r, "duplicate inimigo '" + d.enemy + "'");
            drops_.push_back(std::move(d));
        }
    } else if (table == "rota.csv") {
        if (!Header(t, {"etapa", "id", "tipo", "room", "enemies"}, table, errors_)) return false;
        for (const CsvRow& r : t.rows) {
            RouteRow rr;
            if (!IntIn(r.cells[0], 1, kMaxLevel, rr.stage)) bad(r, "etapa out of range");
            rr.node.id = S(r, 1);
            if (rr.node.id.empty() || rr.node.id == kKindCombat) bad(r, "id is empty or reserved");
            rr.node.kind = S(r, 2);
            if (rr.node.kind != kKindCombat && rr.node.kind != kKindElite && rr.node.kind != kKindRest)
                bad(r, "tipo must be combate, elite or descanso");
            rr.node.room = S(r, 3);
            if (rr.node.room.empty()) bad(r, "room is empty");
            rr.node.enemies = S(r, 4);
            if (!ParseEnemies(r.cells[4], rr.node.enemyList, rr.node.enemyTotal)) bad(r, "enemies is not id:n|id:n");
            if (rr.node.kind != kKindRest && rr.node.enemyTotal == 0) bad(r, "combat room without enemies");
            for (const RouteRow& o : routes_)
                if (o.stage == rr.stage && o.node.id == rr.node.id) bad(r, "duplicate id in etapa");
            routes_.push_back(std::move(rr));
        }
    } else if (table == "run.csv") {
        if (!Header(t, {"sala", "room", "enemies"}, table, errors_)) return false;
        for (const CsvRow& r : t.rows) {
            RogueNode n;
            int sala = 0;
            if (!IntIn(r.cells[0], 1, kMaxLevel, sala) || sala != static_cast<int>(stages_.size()) + 1)
                bad(r, "sala must count 1, 2, 3...");
            n.id = std::string(kKindCombat);
            n.kind = std::string(kKindCombat);
            n.room = S(r, 1);
            if (n.room.empty()) bad(r, "room is empty");
            n.enemies = S(r, 2);
            if (!ParseEnemies(r.cells[2], n.enemyList, n.enemyTotal)) bad(r, "enemies is not id:n|id:n");
            if (n.enemyTotal == 0) bad(r, "combat room without enemies");
            stages_.push_back(std::move(n));
        }
    } else if (table == "run_settings.csv") {
        if (!Header(t, {"chave", "valor", "unidade", "nota"}, table, errors_)) return false;
        for (const CsvRow& r : t.rows) {
            const std::string key = S(r, 0);
            double v = 0.0;
            if (key.empty()) bad(r, "chave is empty");
            if (!detail::ParseDouble(r.cells[1], v)) bad(r, "valor is not a number");
            double dummy = 0.0;
            if (Setting(key, dummy)) bad(r, "duplicate chave '" + key + "'");
            settings_.emplace_back(key, v);
        }
    } else if (table == "upgrades.csv") {
        if (!Header(t, {"id", "stat", "modo", "valor", "nivel_max"}, table, errors_)) return false;
        for (const CsvRow& r : t.rows) {
            RogueUpgrade u;
            u.id = S(r, 0);
            if (u.id.empty()) bad(r, "id is empty");
            u.stat = S(r, 1);
            if (u.stat.empty()) bad(r, "stat is empty");
            if (!Mode(r.cells[2], u.mode)) bad(r, "modo must be add or mult");
            if (!detail::ParseDouble(r.cells[3], u.value)) bad(r, "valor is not a number");
            if (!IntIn(r.cells[4], 1, kMaxLevel, u.maxLevel)) bad(r, "nivel_max out of range");
            if (IndexById(upgrades_, u.id) >= 0) bad(r, "duplicate id '" + u.id + "'");
            upgrades_.push_back(std::move(u));
        }
    } else if (table == kClassesTable) {
        // Só id e habilidades importam ao core; as demais colunas (nome, sprite, efeitos, stats) são do cliente.
        const int colId = ColumnIndex(t, "id"), colSkills = ColumnIndex(t, "habilidades");
        if (colId < 0 || colSkills < 0) {
            errors_.push_back({name, t.headerLine, "classes_2d.csv needs id and habilidades columns"});
            return false;
        }
        for (const CsvRow& r : t.rows) {
            RogueClass c;
            c.id = S(r, static_cast<std::size_t>(colId));
            if (c.id.empty()) bad(r, "id is empty");
            c.skillFile = std::string(BaseName(r.cells[static_cast<std::size_t>(colSkills)]));
            if (c.skillFile == "." || c.skillFile == "..") bad(r, "habilidades is not a file name");
            if (IndexById(classes_, c.id) >= 0) bad(r, "duplicate id '" + c.id + "'");
            classes_.push_back(std::move(c));
        }
    } else {
        errors_.push_back({name, 0, "unknown rogue table"});
        return false;
    }
    return errors_.size() == before;
}

bool RogueData::LoadSkillTableCsv(std::string_view classId, std::string_view text) {
    const std::size_t before = errors_.size();
    const int ci = IndexById(classes_, classId);
    const std::string name = ci >= 0 && !classes_[static_cast<std::size_t>(ci)].skillFile.empty()
                                 ? classes_[static_cast<std::size_t>(ci)].skillFile
                                 : "habilidades_" + std::string(classId) + ".csv";
    if (ci < 0) {
        errors_.push_back({name, 0, "class not in classes_2d.csv"});
        return false;
    }
    RogueClass& cls = classes_[static_cast<std::size_t>(ci)];
    cls.skills.clear();
    CsvTable t;
    detail::CsvError ce;
    if (!detail::ParseCsv(text, t, ce)) {
        errors_.push_back({name, ce.line, ce.message});
        return false;
    }
    for (const char* req : {"id", "tipo", "pai", "pontos", "nivel_max"}) {
        if (ColumnIndex(t, req) < 0) {
            errors_.push_back({name, t.headerLine, std::string("missing column ") + req});
            return false;
        }
    }
    for (std::size_t c = 0; c < t.header.size(); ++c)
        for (std::size_t o = 0; o < c; ++o)
            if (t.header[o] == t.header[c]) {
                errors_.push_back({name, t.headerLine, "duplicate column " + std::string(t.header[c])});
                return false;
            }
    for (const CsvRow& r : t.rows) {
        auto bad = [&](const std::string& msg) { errors_.push_back({name, r.line, msg}); };
        RogueSkillDef d;
        std::string tipo, modo;
        for (std::size_t c = 0; c < t.header.size(); ++c) {
            const std::string col(t.header[c]);
            const std::string_view cell = r.cells[c];
            if (IsSkillTextColumn(col)) {
                d.texts.emplace_back(col, std::string(cell));
                if (col == "id") d.id = std::string(cell);
                else if (col == "tipo") tipo = std::string(cell);
                else if (col == "pai") d.parent = std::string(cell);
                else if (col == "stat") d.stat = std::string(cell);
                else if (col == "modo") modo = std::string(cell);
                continue;
            }
            double v = 0.0;
            if (!cell.empty() && !detail::ParseDouble(cell, v)) {
                bad("column " + col + " is not a number");
                continue;
            }
            if (col == "pontos" || col == "nivel_max") {
                // maxi(1, int(...)) do GDScript: aqui o valor tem de ser inteiro de verdade; 0 conta como 1.
                if (!(v >= 0.0 && v <= kMaxLevel) || v != static_cast<double>(static_cast<int>(v))) {
                    bad(col + " out of range");
                    continue;
                }
                const int n = std::max(1, static_cast<int>(v));
                if (col == "pontos") d.points = n;
                else d.maxLevel = n;
                v = n;
            } else if (col == "cd" || col == "custo") {
                if (!(v >= 0.0)) bad(col + " must be >= 0");
                if (col == "cd") d.cooldown = v;
                else d.cost = v;
            } else if (col == "escala") {
                d.scale = v;
            } else if (col == "valor") {
                d.value = v;
            }
            d.numbers.emplace_back(col, v);
        }
        if (d.id.empty()) bad("id is empty");
        if (tipo == "ativa") d.active = true;
        else if (tipo != "passiva") bad("tipo must be ativa or passiva");
        if (!d.active && !d.stat.empty() && !Mode(modo, d.mode)) bad("modo must be add or mult");
        if (d.parent == d.id && !d.id.empty()) bad("pai is the skill itself");
        if (IndexById(cls.skills, d.id) >= 0) bad("duplicate id '" + d.id + "'");
        cls.skills.push_back(std::move(d));
    }
    return errors_.size() == before;
}

bool RogueData::LoadDirectory(const std::string& dir) {
    std::error_code ec;
    const fs::path d = fs::u8path(dir);
    if (!fs::is_directory(d, ec)) {
        errors_.push_back({"data2d", 0, "E_IO rogue data directory missing"});
        return false;
    }
    bool ok = true;
    for (const char* name : kTables) {
        std::ifstream in(d / name, std::ios::binary);
        if (!in) {
            errors_.push_back({name, 0, "E_IO table file missing"});
            ok = false;
            continue;
        }
        const std::string text((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
        ok = LoadTableCsv(name, text) && ok;
    }
    // Classes e árvores: opcionais. Sem classes_2d.csv não há classes; árvore ausente = classe sem árvore
    // (como o carregar_classe do habilidades_2d.gd).
    std::ifstream classesIn(d / std::string(kClassesTable), std::ios::binary);
    if (classesIn) {
        const std::string text((std::istreambuf_iterator<char>(classesIn)), std::istreambuf_iterator<char>());
        if (LoadTableCsv(kClassesTable, text)) {
            for (std::size_t i = 0; i < classes_.size(); ++i) {
                const RogueClass& c = classes_[i];
                if (c.skillFile.empty()) continue;
                std::ifstream skillIn(d / fs::u8path(c.skillFile), std::ios::binary);
                if (!skillIn) continue;
                const std::string st((std::istreambuf_iterator<char>(skillIn)), std::istreambuf_iterator<char>());
                ok = LoadSkillTableCsv(classes_[i].id, st) && ok;
            }
        } else {
            ok = false;
        }
    }
    return ok;
}

bool RogueData::Finalize() {
    const std::size_t before = errors_.size();
    auto E = [&](const char* table, const std::string& msg) { errors_.push_back({table, 0, msg}); };
    for (const RogueMetaDef& d : meta_)
        if (d.ability && FindUpgrade(d.target) < 0) E("meta.csv", "habilidade alvo is not an upgrade: '" + d.target + "'");
    if (stages_.empty()) E("run.csv", "no rooms");
    for (const RouteRow& r : routes_)
        if (r.stage > static_cast<int>(stages_.size())) E("rota.csv", "etapa beyond run.csv: '" + r.node.id + "'");

    // Materiais conhecidos: drops e depois receitas, na ordem.
    materials_.clear();
    auto addMat = [&](const ContentId& m) {
        if (!m.empty() && std::find(materials_.begin(), materials_.end(), m) == materials_.end()) materials_.push_back(m);
    };
    for (const RogueDrop& d : drops_) addMat(d.material);
    for (const RogueRecipe& r : recipes_)
        for (const auto& m : r.materials) addMat(m.first);

    // Chaves de regra obrigatórias. As inteiras passam por int() no GDScript: aqui têm de ser inteiras de verdade.
    auto intKey = [&](const char* key, std::int64_t hi, std::int64_t& out) {
        double v = 0.0;
        if (!Setting(key, v)) {
            E("run_settings.csv", std::string("missing chave ") + key);
            return;
        }
        if (!(v >= 0.0 && v <= static_cast<double>(hi)) || v != static_cast<double>(static_cast<std::int64_t>(v))) {
            E("run_settings.csv", std::string("chave must be a non-negative integer: ") + key);
            return;
        }
        out = static_cast<std::int64_t>(v);
    };
    std::int64_t seed = 0, cards = 0, extra = 0;
    intKey("seed", 9007199254740992, seed);
    intKey("upgrade_cards", kMaxLevel, cards);
    intKey("elite_extra_cards", kMaxLevel, extra);
    intKey("room_clear_fragments", kMaxCount, roomClearFragments_);
    intKey("elite_fragments", kMaxCount, eliteFragments_);
    intKey("victory_fragments", kMaxCount, victoryFragments_);
    baseSeed_ = static_cast<std::uint64_t>(seed);
    upgradeCards_ = static_cast<int>(cards);
    eliteExtraCards_ = static_cast<int>(extra);
    double heal = 0.0;
    if (!Setting("rest_heal", heal)) E("run_settings.csv", "missing chave rest_heal");
    else if (!(heal >= 0.0 && heal <= 1.0)) E("run_settings.csv", "rest_heal must be in 0..1");
    else restHeal_ = heal;

    // Pontos de habilidade: opcionais (sem a chave, a sala não dá pontos).
    auto optIntKey = [&](const char* key, std::int64_t& out) {
        double v = 0.0;
        if (!Setting(key, v)) return;
        if (!(v >= 0.0 && v <= static_cast<double>(kMaxCount)) || v != static_cast<double>(static_cast<std::int64_t>(v))) {
            E("run_settings.csv", std::string("chave must be a non-negative integer: ") + key);
            return;
        }
        out = static_cast<std::int64_t>(v);
    };
    optIntKey("skill_points_room", skillPointsRoom_);
    optIntKey("skill_points_boss", skillPointsBoss_);

    // Árvores: pai existe na mesma classe e não há ciclo (um nó num ciclo nunca abriria).
    for (RogueClass& c : classes_) {
        const std::string table = c.skillFile.empty() ? c.id : c.skillFile;
        for (RogueSkillDef& d : c.skills) {
            d.parentIndex = -1;
            if (d.parent.empty()) continue;
            d.parentIndex = IndexById(c.skills, d.parent);
            if (d.parentIndex < 0) errors_.push_back({table, 0, "pai is not a skill of the class: '" + d.parent + "'"});
        }
        for (std::size_t i = 0; i < c.skills.size(); ++i) {
            int p = c.skills[i].parentIndex;
            for (std::size_t steps = 0; p >= 0 && steps <= c.skills.size(); ++steps)
                p = c.skills[static_cast<std::size_t>(p)].parentIndex;
            if (p >= 0) errors_.push_back({table, 0, "pai forms a cycle: '" + c.skills[i].id + "'"});
        }
    }

    finalized_ = true;
    return errors_.size() == before && errors_.empty();
}

int RogueData::FindMetaDef(std::string_view id) const { return IndexById(meta_, id); }
int RogueData::FindClass(std::string_view id) const { return IndexById(classes_, id); }
int RogueData::FindSkill(int classIndex, std::string_view skillId) const {
    if (classIndex < 0 || classIndex >= static_cast<int>(classes_.size())) return -1;
    return IndexById(classes_[static_cast<std::size_t>(classIndex)].skills, skillId);
}
int RogueData::FindRecipe(std::string_view id) const { return IndexById(recipes_, id); }
int RogueData::FindUpgrade(std::string_view id) const { return IndexById(upgrades_, id); }
int RogueData::FindMaterial(std::string_view id) const {
    for (std::size_t i = 0; i < materials_.size(); ++i)
        if (materials_[i] == id) return static_cast<int>(i);
    return -1;
}
const RogueDrop* RogueData::FindDrop(std::string_view enemy) const {
    for (const RogueDrop& d : drops_)
        if (d.enemy == enemy) return &d;
    return nullptr;
}

bool RogueData::Setting(std::string_view key, double& out) const {
    for (const auto& kv : settings_) {
        if (kv.first == key) {
            out = kv.second;
            return true;
        }
    }
    return false;
}

std::vector<RogueNode> RogueData::Paths(int stage) const {
    std::vector<RogueNode> out;
    if (stage < 0 || stage >= static_cast<int>(stages_.size())) return out;
    out.push_back(stages_[static_cast<std::size_t>(stage)]);
    for (const RouteRow& r : routes_)
        if (r.stage == stage + 1) out.push_back(r.node);
    return out;
}

// ---------------------------------------------------------------------------------------------------------------
// RogueState: meta
// ---------------------------------------------------------------------------------------------------------------
RogueState::RogueState(const RogueData& data) : data_(&data) {
    ResetMeta();
    runLevels_.assign(data.Upgrades().size(), 0);
}

void RogueState::ResetMeta() {
    fragments_ = 0;
    if (data_ == nullptr) return;
    materials_.assign(data_->Materials().size(), 0);
    levels_.assign(data_->MetaDefs().size(), 0);
    owned_.assign(data_->Recipes().size(), 0);
    stock_.assign(data_->Recipes().size(), 0);
    active_.assign(data_->Recipes().size(), 0);
    equipped_ = -1;
    ResetSkillState();
}

std::int64_t RogueState::Material(std::string_view id) const {
    const int i = data_ != nullptr ? data_->FindMaterial(id) : -1;
    return i < 0 ? 0 : materials_[static_cast<std::size_t>(i)];
}

int RogueState::Level(std::string_view metaId) const {
    const int i = data_ != nullptr ? data_->FindMetaDef(metaId) : -1;
    return i < 0 ? 0 : levels_[static_cast<std::size_t>(i)];
}

bool RogueState::Unlocked(std::string_view upgradeId) const {
    if (data_ == nullptr) return true;
    const auto& defs = data_->MetaDefs();
    for (std::size_t i = 0; i < defs.size(); ++i)
        if (defs[i].ability && defs[i].target == upgradeId) return levels_[i] > 0;
    return true;
}

RogueMetaResult RogueState::CheckBuy(std::string_view metaId) const {
    const int i = data_ != nullptr ? data_->FindMetaDef(metaId) : -1;
    if (i < 0) return RogueMetaResult::Unknown;
    const RogueMetaDef& d = data_->MetaDefs()[static_cast<std::size_t>(i)];
    if (levels_[static_cast<std::size_t>(i)] >= d.maxLevel) return RogueMetaResult::Maxed;
    if (fragments_ < d.cost) return RogueMetaResult::NoFragments;
    return RogueMetaResult::Ok;
}

RogueMetaResult RogueState::Buy(std::string_view metaId) {
    const RogueMetaResult r = CheckBuy(metaId);
    if (r != RogueMetaResult::Ok) return r;
    const std::size_t i = static_cast<std::size_t>(data_->FindMetaDef(metaId));
    fragments_ -= data_->MetaDefs()[i].cost;
    ++levels_[i];
    return r;
}

bool RogueState::Owns(std::string_view recipeId) const {
    const int i = data_ != nullptr ? data_->FindRecipe(recipeId) : -1;
    if (i < 0) return false;
    const std::size_t k = static_cast<std::size_t>(i);
    return data_->Recipes()[k].amulet ? owned_[k] != 0 : stock_[k] > 0;
}

int RogueState::Stock(std::string_view recipeId) const {
    const int i = data_ != nullptr ? data_->FindRecipe(recipeId) : -1;
    return i < 0 ? 0 : stock_[static_cast<std::size_t>(i)];
}

bool RogueState::Active(std::string_view recipeId) const {
    const int i = data_ != nullptr ? data_->FindRecipe(recipeId) : -1;
    return i >= 0 && active_[static_cast<std::size_t>(i)] != 0;
}

const ContentId& RogueState::Equipped() const {
    static const ContentId kNone;
    if (data_ == nullptr || equipped_ < 0) return kNone;
    return data_->Recipes()[static_cast<std::size_t>(equipped_)].id;
}

RogueMetaResult RogueState::CheckCraft(std::string_view recipeId) const {
    const int i = data_ != nullptr ? data_->FindRecipe(recipeId) : -1;
    if (i < 0) return RogueMetaResult::Unknown;
    const std::size_t k = static_cast<std::size_t>(i);
    const RogueRecipe& r = data_->Recipes()[k];
    if (r.amulet && owned_[k] != 0) return RogueMetaResult::AlreadyOwned;
    if (!r.amulet && stock_[k] >= r.maxStock) return RogueMetaResult::StockFull;
    if (fragments_ < r.fragments) return RogueMetaResult::NoFragments;
    for (const auto& m : r.materials)
        if (Material(m.first) < m.second) return RogueMetaResult::NoMaterials;
    return RogueMetaResult::Ok;
}

RogueMetaResult RogueState::Craft(std::string_view recipeId) {
    const RogueMetaResult res = CheckCraft(recipeId);
    if (res != RogueMetaResult::Ok) return res;
    const std::size_t k = static_cast<std::size_t>(data_->FindRecipe(recipeId));
    const RogueRecipe& r = data_->Recipes()[k];
    fragments_ -= r.fragments;
    for (const auto& m : r.materials) materials_[static_cast<std::size_t>(data_->FindMaterial(m.first))] -= m.second;
    if (r.amulet) {
        owned_[k] = 1;
        if (equipped_ < 0) equipped_ = static_cast<int>(k);
    } else {
        ++stock_[k];
    }
    return res;
}

RogueMetaResult RogueState::Equip(std::string_view recipeId) {
    const int i = data_ != nullptr ? data_->FindRecipe(recipeId) : -1;
    if (i < 0 || !data_->Recipes()[static_cast<std::size_t>(i)].amulet || owned_[static_cast<std::size_t>(i)] == 0)
        return RogueMetaResult::NotOwned;
    equipped_ = equipped_ == i ? -1 : i;
    return RogueMetaResult::Ok;
}

void RogueState::PrepareRun() {
    if (data_ == nullptr) return;
    const auto& recipes = data_->Recipes();
    for (std::size_t k = 0; k < recipes.size(); ++k) {
        active_[k] = 0;
        if (!recipes[k].amulet && stock_[k] > 0) {
            --stock_[k];
            active_[k] = 1;
        }
    }
}

bool RogueState::Credit(std::int64_t fragments, const std::vector<std::pair<ContentId, std::int64_t>>& materials) {
    if (data_ == nullptr || fragments < 0) return false;
    for (const auto& m : materials)
        if (m.second < 0 || data_->FindMaterial(m.first) < 0) return false;
    fragments_ = SatAdd(fragments_, fragments);
    for (const auto& m : materials) {
        std::int64_t& slot = materials_[static_cast<std::size_t>(data_->FindMaterial(m.first))];
        slot = SatAdd(slot, m.second);
    }
    return true;
}

RogueStats RogueState::ApplyMeta(const RogueStats& base) const {
    RogueStats s = base;
    if (data_ == nullptr) return s;
    const auto& recipes = data_->Recipes();
    if (equipped_ >= 0) {
        const RogueRecipe& r = recipes[static_cast<std::size_t>(equipped_)];
        ApplyBonus(s, r.stat, r.mode, r.value);
    }
    for (std::size_t k = 0; k < recipes.size(); ++k)
        if (active_[k] != 0) ApplyBonus(s, recipes[k].stat, recipes[k].mode, recipes[k].value);
    const auto& defs = data_->MetaDefs();
    for (std::size_t i = 0; i < defs.size(); ++i) {
        if (defs[i].ability) continue;
        for (int n = 0; n < levels_[i]; ++n) ApplyBonus(s, defs[i].stat, defs[i].mode, defs[i].value);
    }
    return s;
}

RogueStats RogueState::ApplyRunUpgrades(const RogueStats& stats) const {
    RogueStats s = stats;
    if (data_ == nullptr) return s;
    const auto& ups = data_->Upgrades();
    for (std::size_t i = 0; i < ups.size(); ++i)
        for (int n = 0; n < runLevels_[i]; ++n) ApplyBonus(s, ups[i].stat, ups[i].mode, ups[i].value);
    return s;
}

namespace {

// "habilidades": {classe: {"niveis", "slots", "pontos"}} só das classes com algo guardado, e "classe" (a atual).
// Sem classes_2d.csv nenhuma das duas chaves aparece: o save fica byte a byte o da API 1.8.
void SkillsToValue(Value& o, const RogueData& data, const std::vector<RogueSkillMeta>& metas, int cls) {
    if (data.Classes().empty()) return;
    Value hab = Value::MakeObject();
    for (std::size_t c = 0; c < metas.size(); ++c) {
        const RogueSkillMeta& m = metas[c];
        const auto& skills = data.Classes()[c].skills;
        bool any = m.points != 0;
        Value lv = Value::MakeObject();
        for (std::size_t i = 0; i < m.levels.size(); ++i) {
            if (m.levels[i] <= 0) continue;
            lv.Set(skills[i].id, Value(m.levels[i]));
            any = true;
        }
        Value sl = Value::MakeArray();
        for (int k : m.slots) {
            sl.Push(Value(k >= 0 ? skills[static_cast<std::size_t>(k)].id : std::string()));
            any = any || k >= 0;
        }
        if (!any) continue;
        Value e = Value::MakeObject();
        e.Set("niveis", std::move(lv));
        e.Set("slots", std::move(sl));
        e.Set("pontos", Value(m.points));
        hab.Set(data.Classes()[c].id, std::move(e));
    }
    o.Set("habilidades", std::move(hab));
    o.Set("classe", Value(cls >= 0 ? data.Classes()[static_cast<std::size_t>(cls)].id : std::string()));
}

Value MetaToValue(const RogueData& data, std::int64_t fragments, const std::vector<std::int64_t>& materials,
                  const std::vector<int>& levels, const std::vector<std::uint8_t>& owned, const std::vector<int>& stock,
                  int equipped) {
    Value o = Value::MakeObject();
    o.Set("versao", Value(kRogueSaveVersion));
    o.Set("fragmentos", Value(fragments));
    Value mats = Value::MakeObject();
    for (std::size_t i = 0; i < materials.size(); ++i)
        if (materials[i] > 0) mats.Set(data.Materials()[i], Value(materials[i]));
    o.Set("materiais", std::move(mats));
    Value lv = Value::MakeObject();
    for (std::size_t i = 0; i < levels.size(); ++i)
        if (levels[i] > 0) lv.Set(data.MetaDefs()[i].id, Value(levels[i]));
    o.Set("niveis", std::move(lv));
    Value am = Value::MakeArray();
    for (std::size_t k = 0; k < owned.size(); ++k)
        if (owned[k] != 0) am.Push(Value(data.Recipes()[k].id));
    o.Set("amuletos", std::move(am));
    o.Set("equipado", Value(equipped >= 0 ? data.Recipes()[static_cast<std::size_t>(equipped)].id : std::string()));
    Value st = Value::MakeObject();
    for (std::size_t k = 0; k < stock.size(); ++k)
        if (stock[k] > 0) st.Set(data.Recipes()[k].id, Value(stock[k]));
    o.Set("estoque", std::move(st));
    return o;
}

}  // namespace

std::string RogueState::MetaToJson() const {
    if (data_ == nullptr) return std::string();
    Value o = MetaToValue(*data_, fragments_, materials_, levels_, owned_, stock_, equipped_);
    SkillsToValue(o, *data_, skillMeta_, class_);
    return json::Serialize(o, false);
}

RogueLoadResult RogueState::MetaFromJson(std::string_view text) {
    ResetMeta();
    if (data_ == nullptr) return RogueLoadResult::BadJson;
    Value d;
    if (!json::Parse(text, d) || d.type() != json::Type::Object) return RogueLoadResult::BadJson;
    if (LooseInt(d["versao"]) != kRogueSaveVersion) return RogueLoadResult::BadVersion;
    fragments_ = std::max<std::int64_t>(0, LooseInt(d["fragmentos"]));
    for (const auto& m : d["materiais"].Members()) {
        const int i = data_->FindMaterial(m.first);  // material que o jogo não conhece mais: descartado
        if (i >= 0) materials_[static_cast<std::size_t>(i)] = std::max<std::int64_t>(0, LooseInt(m.second));
    }
    for (const auto& m : d["niveis"].Members()) {
        const int i = data_->FindMetaDef(m.first);
        if (i >= 0)
            levels_[static_cast<std::size_t>(i)] =
                ClampLevel(LooseInt(m.second), data_->MetaDefs()[static_cast<std::size_t>(i)].maxLevel);
    }
    for (const Value& v : d["amuletos"].Items()) {
        const int i = v.type() == json::Type::String ? data_->FindRecipe(v.AsString()) : -1;
        if (i >= 0 && data_->Recipes()[static_cast<std::size_t>(i)].amulet) owned_[static_cast<std::size_t>(i)] = 1;
    }
    const Value& eq = d["equipado"];
    if (eq.type() == json::Type::String) {
        const int i = data_->FindRecipe(eq.AsString());
        if (i >= 0 && owned_[static_cast<std::size_t>(i)] != 0) equipped_ = i;
    }
    for (const auto& m : d["estoque"].Members()) {
        const int i = data_->FindRecipe(m.first);
        if (i >= 0 && !data_->Recipes()[static_cast<std::size_t>(i)].amulet)
            stock_[static_cast<std::size_t>(i)] =
                ClampLevel(LooseInt(m.second), data_->Recipes()[static_cast<std::size_t>(i)].maxStock);
    }
    // Habilidades (de_dicionario do habilidades_2d.gd): classe e habilidade desconhecidas descartadas, nível limitado
    // a 0..máximo, slot só com ativa aprendida, pontos >= 0. Classe salva desconhecida: fica a padrão.
    const auto& classes = data_->Classes();
    for (const auto& m : d["habilidades"].Members()) {
        const int c = data_->FindClass(m.first);
        if (c < 0) continue;
        const auto& skills = classes[static_cast<std::size_t>(c)].skills;
        RogueSkillMeta& sm = skillMeta_[static_cast<std::size_t>(c)];
        for (const auto& n : m.second["niveis"].Members()) {
            const int i = data_->FindSkill(c, n.first);
            if (i >= 0)
                sm.levels[static_cast<std::size_t>(i)] =
                    ClampLevel(LooseInt(n.second), skills[static_cast<std::size_t>(i)].maxLevel);
        }
        const auto& sv = m.second["slots"].Items();
        for (std::size_t k = 0; k < sv.size() && k < static_cast<std::size_t>(kRogueSkillSlots); ++k) {
            const int i = sv[k].type() == json::Type::String ? data_->FindSkill(c, sv[k].AsString()) : -1;
            if (i >= 0 && skills[static_cast<std::size_t>(i)].active && sm.levels[static_cast<std::size_t>(i)] >= 1 &&
                std::find(sm.slots.begin(), sm.slots.end(), i) == sm.slots.end())
                sm.slots[k] = i;
        }
        sm.points = std::max<std::int64_t>(0, LooseInt(m.second["pontos"]));
    }
    const Value& cls = d["classe"];
    if (cls.type() == json::Type::String) {
        const int c = data_->FindClass(cls.AsString());
        if (c >= 0) class_ = c;
    }
    ClearCooldowns();
    return RogueLoadResult::Ok;
}

// ---------------------------------------------------------------------------------------------------------------
// RogueState: corrida
// ---------------------------------------------------------------------------------------------------------------
int RogueState::StagesTotal() const { return data_ != nullptr ? static_cast<int>(data_->Stages().size()) : 0; }

const RogueNode* RogueState::CurrentNode() const { return phase_ == RoguePhase::None ? nullptr : &node_; }

int RogueState::RunLevel(std::string_view upgradeId) const {
    const int i = data_ != nullptr ? data_->FindUpgrade(upgradeId) : -1;
    return i < 0 ? 0 : runLevels_[static_cast<std::size_t>(i)];
}

std::vector<ContentId> RogueState::AvailableUpgrades() const {
    std::vector<ContentId> out;
    if (data_ == nullptr) return out;
    const auto& ups = data_->Upgrades();
    for (std::size_t i = 0; i < ups.size(); ++i)
        if (runLevels_[i] < ups[i].maxLevel && Unlocked(ups[i].id)) out.push_back(ups[i].id);
    return out;
}

RogueStats RogueState::RunStats() const { return ApplySkillPassives(ApplyRunUpgrades(base_)); }

void RogueState::CreditGains() {
    if (gainFragments_ != 0 || !gainMaterials_.empty()) Credit(gainFragments_, gainMaterials_);
    gainFragments_ = 0;
    gainMaterials_.clear();
}

void RogueState::AddGainMaterial(const ContentId& id, std::int64_t qty) {
    for (auto& m : gainMaterials_) {
        if (m.first == id) {
            m.second = SatAdd(m.second, qty);
            return;
        }
    }
    gainMaterials_.emplace_back(id, qty);
}

bool RogueState::StartRun(std::uint64_t seed, const RogueStats& baseStats) {
    if (data_ == nullptr || data_->Stages().empty()) return false;
    const bool credited = gainFragments_ != 0 || !gainMaterials_.empty();
    CreditGains();
    seed_ = seed;
    draws_ = 0;
    runLevels_.assign(data_->Upgrades().size(), 0);
    base_ = ApplyMeta(baseStats);
    ClearCooldowns();
    EnterNode(0, 0);
    return credited;
}

void RogueState::EnterNode(int stage, int pathIndex) {
    const std::vector<RogueNode> paths = data_->Paths(stage);
    stage_ = stage;
    path_ = pathIndex;
    node_ = paths[static_cast<std::size_t>(pathIndex)];
    offer_.clear();
    restPending_ = false;
    if (node_.kind == kKindRest) {
        // _descansar: sem inimigos; a porta abre sem cartas e a cura vale uma vez (Rest).
        alive_ = 0;
        restPending_ = true;
        phase_ = RoguePhase::Cleared;
    } else {
        alive_ = node_.enemyTotal;
        phase_ = RoguePhase::Fight;
    }
}

void RogueState::DrawCards(int count) {
    offer_.clear();
    std::vector<ContentId> pool = AvailableUpgrades();
    Pcg32 rng = Pcg32::ForStream(seed_, RngStream::Rogue, draws_);
    ++draws_;
    // Fisher-Yates de trás para frente, como upgrades_2d.gd sortear() (a sequência é a do Pcg32, não a do Godot).
    for (std::size_t i = pool.size(); i > 1; --i) {
        const std::size_t j = static_cast<std::size_t>(rng.RangeInt(0, static_cast<std::int32_t>(i - 1)));
        std::swap(pool[i - 1], pool[j]);
    }
    if (count < 0) count = 0;
    if (pool.size() > static_cast<std::size_t>(count)) pool.resize(static_cast<std::size_t>(count));
    offer_ = std::move(pool);
}

RogueRunResult RogueState::EnemyKilled(std::string_view enemyId, RogueKill* out) {
    if (out != nullptr) *out = RogueKill();
    if (data_ == nullptr || phase_ == RoguePhase::None) return RogueRunResult::WrongPhase;
    RogueKill k;
    if (const RogueDrop* d = data_->FindDrop(enemyId)) {
        k.hasDrop = true;
        k.fragments = d->fragments;
        k.material = d->material;
        k.materialQty = d->materialQty;
        gainFragments_ = SatAdd(gainFragments_, d->fragments);
        if (!d->material.empty()) AddGainMaterial(d->material, d->materialQty);
    }
    if (alive_ > 0) --alive_;
    if (alive_ == 0 && phase_ == RoguePhase::Fight) {
        k.roomCleared = true;
        phase_ = RoguePhase::Cleared;
        const bool elite = node_.kind == kKindElite;
        k.clearFragments = data_->RoomClearFragments() + (elite ? data_->EliteFragments() : 0);
        gainFragments_ = SatAdd(gainFragments_, k.clearFragments);
        // Pontos de habilidade: permanentes na hora (ganhar_pontos do habilidades_2d.gd), da classe atual.
        if (class_ >= 0) {
            const bool boss = stage_ + 1 >= StagesTotal();
            k.skillPoints = SatAdd(data_->SkillPointsRoom(), boss ? data_->SkillPointsBoss() : 0);
            if (k.skillPoints > 0) AddSkillPoints(k.skillPoints);
        }
        // Cartas: não na última sala nem no descanso nem no modo cartas externas; a elite oferece elite_extra_cards a mais.
        if (!externalCards_ && stage_ + 1 < StagesTotal() && node_.kind != kKindRest) {
            DrawCards(data_->UpgradeCards() + (elite ? data_->EliteExtraCards() : 0));
            if (!offer_.empty()) phase_ = RoguePhase::Choice;
        }
    }
    if (out != nullptr) *out = k;
    return RogueRunResult::Ok;
}

RogueRunResult RogueState::SetExternalCards(bool on) {
    if (phase_ != RoguePhase::None && phase_ != RoguePhase::Won && phase_ != RoguePhase::Dead)
        return RogueRunResult::WrongPhase;
    externalCards_ = on;
    return RogueRunResult::Ok;
}

RogueRunResult RogueState::ChooseCard(std::string_view upgradeId, double hp, double* hpOut) {
    if (hpOut != nullptr) *hpOut = hp;
    if (data_ == nullptr || phase_ != RoguePhase::Choice) return RogueRunResult::WrongPhase;
    if (std::find(offer_.begin(), offer_.end(), upgradeId) == offer_.end()) return RogueRunResult::NotOffered;
    const int i = data_->FindUpgrade(upgradeId);
    if (i < 0) return RogueRunResult::Unknown;
    const std::size_t k = static_cast<std::size_t>(i);
    if (runLevels_[k] >= data_->Upgrades()[k].maxLevel) return RogueRunResult::NotOffered;
    double before = 0.0, after = 0.0;
    const bool hasHp = FindStat(RunStats(), kHpMaxStat, before);
    ++runLevels_[k];
    if (hasHp) FindStat(RunStats(), kHpMaxStat, after);
    const double gain = hasHp ? after - before : 0.0;
    if (hpOut != nullptr) *hpOut = gain > 0.0 ? hp + gain : hp;
    offer_.clear();
    phase_ = RoguePhase::Cleared;
    return RogueRunResult::Ok;
}

RogueRunResult RogueState::Rest(double hp, double* hpOut) {
    if (hpOut != nullptr) *hpOut = hp;
    if (data_ == nullptr || phase_ == RoguePhase::None || !restPending_ || node_.kind != kKindRest)
        return RogueRunResult::WrongPhase;
    double maxHp = 0.0;
    if (!FindStat(RunStats(), kHpMaxStat, maxHp)) return RogueRunResult::NoHpStat;
    restPending_ = false;
    if (hpOut != nullptr) *hpOut = std::min(maxHp, hp + maxHp * data_->RestHeal());
    return RogueRunResult::Ok;
}

RogueDoor RogueState::UseDoor() {
    if (data_ == nullptr || phase_ != RoguePhase::Cleared) return RogueDoor::NotReady;
    if (stage_ + 1 >= StagesTotal()) {
        phase_ = RoguePhase::Won;
        gainFragments_ = SatAdd(gainFragments_, data_->VictoryFragments());
        return RogueDoor::Victory;
    }
    const int next = stage_ + 1;
    if (data_->Paths(next).size() == 1) {
        EnterNode(next, 0);
        return RogueDoor::Entered;
    }
    stage_ = next;  // indice += 1 antes da escolha (a sala atual continua a mesma até ChoosePath)
    phase_ = RoguePhase::Route;
    return RogueDoor::Route;
}

RogueRunResult RogueState::ChoosePath(int pathIndex) {
    if (data_ == nullptr || phase_ != RoguePhase::Route) return RogueRunResult::WrongPhase;
    if (pathIndex < 0 || pathIndex >= static_cast<int>(data_->Paths(stage_).size())) return RogueRunResult::Unknown;
    EnterNode(stage_, pathIndex);
    return RogueRunResult::Ok;
}

RogueRunResult RogueState::PlayerDied() {
    if (phase_ == RoguePhase::None || phase_ == RoguePhase::Won || phase_ == RoguePhase::Dead)
        return RogueRunResult::WrongPhase;
    phase_ = RoguePhase::Dead;
    offer_.clear();
    return RogueRunResult::Ok;
}

RogueSummary RogueState::Summary() const {
    RogueSummary s;
    s.victory = phase_ == RoguePhase::Won;
    s.stageReached = stage_ + 1;
    s.stagesTotal = StagesTotal();
    for (int n : runLevels_) s.upgradesTotal += n;
    s.fragments = gainFragments_;
    s.materials = gainMaterials_;
    return s;
}

bool RogueState::FinishRun() {
    if (phase_ == RoguePhase::None) return false;
    CreditGains();
    phase_ = RoguePhase::None;
    offer_.clear();
    alive_ = 0;
    restPending_ = false;
    return true;
}

// ---------------------------------------------------------------------------------------------------------------
// Estado completo
// ---------------------------------------------------------------------------------------------------------------
std::string RogueState::StateJson() const {
    if (data_ == nullptr) return std::string();
    Value o = Value::MakeObject();
    o.Set("format", Value(kRogueStateFormat));
    Value meta = MetaToValue(*data_, fragments_, materials_, levels_, owned_, stock_, equipped_);
    SkillsToValue(meta, *data_, skillMeta_, class_);
    o.Set("meta", std::move(meta));
    Value act = Value::MakeArray();
    for (std::size_t k = 0; k < active_.size(); ++k)
        if (active_[k] != 0) act.Push(Value(data_->Recipes()[k].id));
    o.Set("active", std::move(act));
    // Só aparece ligado: o estado sem o modo continua byte a byte o da API 1.8 (mesmo hash).
    if (externalCards_) o.Set("external_cards", Value(true));
    Value run = Value::MakeObject();
    run.Set("phase", Value(RoguePhaseName(phase_)));
    run.Set("seed", json::FromUInt64(seed_));
    run.Set("draws", json::FromUInt64(draws_));
    run.Set("stage", Value(stage_));
    run.Set("path", Value(path_));
    run.Set("alive", Value(alive_));
    run.Set("rest_pending", Value(restPending_));
    Value lv = Value::MakeObject();
    for (std::size_t i = 0; i < runLevels_.size(); ++i)
        if (runLevels_[i] > 0) lv.Set(data_->Upgrades()[i].id, Value(runLevels_[i]));
    run.Set("levels", std::move(lv));
    Value off = Value::MakeArray();
    for (const ContentId& id : offer_) off.Push(Value(id));
    run.Set("offer", std::move(off));
    Value base = Value::MakeObject();
    for (const auto& p : base_) base.Set(p.first, Value(p.second));
    run.Set("base", std::move(base));
    Value gains = Value::MakeObject();
    gains.Set("fragments", Value(gainFragments_));
    Value gm = Value::MakeObject();
    for (const auto& m : gainMaterials_) gm.Set(m.first, Value(m.second));
    gains.Set("materials", std::move(gm));
    run.Set("gains", std::move(gains));
    // Recargas das habilidades: só as que estão correndo (sem nenhuma, o JSON fica o da 1.9).
    if (class_ >= 0) {
        Value cd = Value::MakeObject();
        const auto& skills = data_->Classes()[static_cast<std::size_t>(class_)].skills;
        for (std::size_t i = 0; i < cooldowns_.size(); ++i)
            if (cooldowns_[i] > 0.0) cd.Set(skills[i].id, Value(cooldowns_[i]));
        if (cd.Size() > 0) run.Set("cooldowns", std::move(cd));
    }
    o.Set("run", std::move(run));
    return json::Serialize(o, false);
}

bool RogueState::RestoreState(std::string_view text, std::string* error) {
    auto fail = [&](const char* msg) {
        if (error != nullptr) *error = msg;
        return false;
    };
    if (data_ == nullptr) return fail("no data");
    Value d;
    if (!json::Parse(text, d) || d.type() != json::Type::Object) return fail("state is not a json object");
    if (d["format"].AsInt(0) != kRogueStateFormat) return fail("unknown state format");
    RogueState t(*data_);
    if (t.MetaFromJson(json::Serialize(d["meta"], false)) != RogueLoadResult::Ok) return fail("bad meta");
    for (const Value& v : d["active"].Items()) {
        const int k = v.type() == json::Type::String ? data_->FindRecipe(v.AsString()) : -1;
        if (k < 0 || data_->Recipes()[static_cast<std::size_t>(k)].amulet) return fail("bad active consumable");
        t.active_[static_cast<std::size_t>(k)] = 1;
    }
    const Value& ext = d["external_cards"];
    if (ext.type() != json::Type::Null && ext.type() != json::Type::Bool) return fail("bad external_cards");
    t.externalCards_ = ext.AsBool(false);
    const Value& run = d["run"];
    if (run.type() != json::Type::Object) return fail("run is not an object");
    bool okPhase = false;
    t.phase_ = PhaseFromName(run["phase"].AsString(), okPhase);
    if (!okPhase) return fail("bad phase");
    const std::uint64_t badU = std::numeric_limits<std::uint64_t>::max();
    t.seed_ = run["seed"].AsUInt64(badU);
    t.draws_ = run["draws"].AsUInt64(badU);
    if (run["seed"].type() != json::Type::String || t.draws_ == badU) return fail("bad seed or draws");
    const std::int64_t stage = run["stage"].AsInt(-1), path = run["path"].AsInt(-1), alive = run["alive"].AsInt(-1);
    if (stage < 0 || stage >= t.StagesTotal()) return fail("bad stage");
    t.stage_ = static_cast<int>(stage);
    const int nodeStage = t.phase_ == RoguePhase::Route ? t.stage_ - 1 : t.stage_;
    const std::vector<RogueNode> paths = data_->Paths(nodeStage);
    if (path < 0 || path >= static_cast<std::int64_t>(paths.size())) return fail("bad path");
    t.path_ = static_cast<int>(path);
    t.node_ = paths[static_cast<std::size_t>(path)];
    if (alive < 0 || alive > t.node_.enemyTotal) return fail("bad alive");
    t.alive_ = static_cast<int>(alive);
    if (run["rest_pending"].type() != json::Type::Bool) return fail("bad rest_pending");
    t.restPending_ = run["rest_pending"].AsBool(false);
    for (const auto& m : run["levels"].Members()) {
        const int i = data_->FindUpgrade(m.first);
        const std::int64_t n = m.second.AsInt(-1);
        if (i < 0 || n < 0 || n > data_->Upgrades()[static_cast<std::size_t>(i)].maxLevel) return fail("bad level");
        t.runLevels_[static_cast<std::size_t>(i)] = static_cast<int>(n);
    }
    for (const Value& v : run["offer"].Items()) {
        if (v.type() != json::Type::String || data_->FindUpgrade(v.AsString()) < 0) return fail("bad offer");
        t.offer_.push_back(v.AsString());
    }
    // No modo cartas externas nunca há escolha nem oferta pendente.
    if (t.externalCards_ && (t.phase_ == RoguePhase::Choice || !t.offer_.empty())) return fail("offer with external cards");
    if (run["base"].type() != json::Type::Object) return fail("bad base");
    for (const auto& m : run["base"].Members()) {
        if (!m.second.IsNumber()) return fail("bad base stat");
        t.base_.emplace_back(m.first, m.second.AsDouble(0.0));
    }
    const Value& gains = run["gains"];
    t.gainFragments_ = gains["fragments"].AsInt(-1);
    if (t.gainFragments_ < 0) return fail("bad gains");
    for (const auto& m : gains["materials"].Members()) {
        const std::int64_t q = m.second.AsInt(-1);
        if (q < 0 || data_->FindMaterial(m.first) < 0) return fail("bad gain material");
        t.gainMaterials_.emplace_back(m.first, q);
    }
    // A classe do estado vem do meta; o MetaFromJson tolerante troca dado ruim pelo padrão, mas aqui é erro.
    const Value& metaClass = d["meta"]["classe"];
    if (metaClass.type() != json::Type::Null &&
        (metaClass.type() != json::Type::String || data_->FindClass(metaClass.AsString()) != t.class_))
        return fail("bad classe");
    for (const auto& m : run["cooldowns"].Members()) {
        const int i = data_->FindSkill(t.class_, m.first);
        const double left = m.second.AsDouble(-1.0);
        if (i < 0 || !m.second.IsNumber() || !(left > 0.0) || left > 1e12) return fail("bad cooldown");
        t.cooldowns_[static_cast<std::size_t>(i)] = left;
    }
    *this = std::move(t);
    return true;
}

std::string RogueState::StateHash() const { return Sha256::HexDigest(StateJson()); }

// ---------------------------------------------------------------------------------------------------------------
// Arquivo do save do meta
// ---------------------------------------------------------------------------------------------------------------
bool WriteRogueMetaFile(IFileIO& io, const std::string& path, const RogueState& s, std::string* error) {
    auto fail = [&](const char* msg) {
        if (error != nullptr) *error = msg;
        return false;
    };
    if (path.empty()) return fail("empty path");
    const std::string text = s.MetaToJson();
    const std::string tmp = path + ".tmp";
    if (!io.WriteAll(tmp, text)) return fail("cannot write tmp file");
    std::string back;
    if (!io.ReadAll(tmp, back) || back != text) {
        io.Remove(tmp);
        return fail("tmp file verification failed");
    }
    // Troca atômica; se o sistema não substituir o principal, remove e tenta de novo (como o meta_2d.gd).
    if (!io.Rename(tmp, path) && !(io.Remove(path) && io.Rename(tmp, path))) {
        io.Remove(tmp);
        return fail("rename failed");
    }
    return true;
}

RogueLoadResult ReadRogueMetaFile(IFileIO& io, const std::string& path, RogueState& s) {
    s.ResetMeta();
    if (path.empty() || !io.Exists(path)) return RogueLoadResult::Missing;
    std::string text;
    if (!io.ReadAll(path, text)) return RogueLoadResult::BadJson;
    return s.MetaFromJson(text);
}

}  // namespace shatter
