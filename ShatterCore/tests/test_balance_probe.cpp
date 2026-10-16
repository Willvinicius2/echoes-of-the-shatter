// Sonda de balanceamento do idle (docs/13, R2.1.5): 20 sementes de 12 h com o Guerreiro nível 4 no CONTEÚDO REAL.
// Só roda com SHATTER_BALANCE_PROBE=1 (imprime a tabela); sem a variável o teste só confere que o conteúdo carrega.
// Variantes: multiplicador de dano recebido (idleDamageTakenMult) e fichas de ataque (attackTokens) ligadas ou não.
#include <algorithm>
#include <cstdio>
#include <memory>
#include <sstream>

#include "test_util.h"

using namespace shatter;

namespace {

std::vector<std::string> SplitLines(const std::string& text) {
    std::vector<std::string> out;
    std::istringstream in(text);
    std::string line;
    while (std::getline(in, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (!line.empty()) out.push_back(line);
    }
    return out;
}

std::vector<std::string> SplitCells(const std::string& line) {
    std::vector<std::string> cells;
    std::string cur;
    for (char c : line) {
        if (c == ',') { cells.push_back(cur); cur.clear(); }
        else cur += c;
    }
    cells.push_back(cur);
    return cells;
}

// Troca a coluna `column` das linhas cujo 1º campo está em `ids` (ou de todas, se `ids` vazio).
std::string SetColumn(const std::string& table, const std::string& column, const std::string& value,
                      const std::vector<std::string>& ids) {
    const std::vector<std::string> lines = SplitLines(table);
    const std::vector<std::string> header = SplitCells(lines[0]);
    std::size_t col = header.size();
    for (std::size_t i = 0; i < header.size(); ++i)
        if (header[i] == column) col = i;
    if (col == header.size()) return table;  // coluna ainda não existe: nada a trocar
    std::string out = lines[0] + "\n";
    for (std::size_t i = 1; i < lines.size(); ++i) {
        std::vector<std::string> cells = SplitCells(lines[i]);
        if (ids.empty() || std::find(ids.begin(), ids.end(), cells[0]) != ids.end()) cells[col] = value;
        for (std::size_t k = 0; k < cells.size(); ++k) out += (k ? "," : "") + cells[k];
        out += "\n";
    }
    return out;
}

struct Variant {
    const char* name;
    std::string damageMult;   // idleDamageTakenMult das 4 habilidades do Guerreiro
    bool tokens;              // attackTokens do enemy_ai.csv ligadas
};

std::unique_ptr<ContentDB> LoadVariant(const Variant& v) {
    auto db = std::make_unique<ContentDB>();
    const std::string dir = tu::ContentDir();
    for (const char* t : tu::kTableNames) {
        const std::string path = dir + "/" + t;
        if (tu::IsOptionalTable(t) && !std::filesystem::exists(std::filesystem::u8path(path))) continue;
        std::string text = tu::ReadFile(path);
        if (std::string(t) == "skills.csv")
            text = SetColumn(text, "idleDamageTakenMult", v.damageMult,
                             {"skill.warrior.iron_cut", "skill.warrior.charge", "skill.warrior.stone_rift", "skill.warrior.shield_bash"});
        if (std::string(t) == "enemy_ai.csv" && !v.tokens) text = SetColumn(text, "attackTokens", "", {});
        db->LoadTableCsv(t, text);
    }
    db->Finalize();
    return db;
}

ExpeditionRequest HeroRequest(const ContentDB& db, bool fullKit, std::uint64_t seed) {
    ExpeditionRequest req;
    CharacterState& c = req.snapshot.character;
    c.name = "Sonda";
    c.classId = "class.warrior";
    c.level = 4;
    c.skills = {{"skill.warrior.iron_cut", 1, {}}, {"skill.warrior.charge", 1, {}}, {"skill.warrior.stone_rift", 1, {}},
                {"skill.warrior.shield_bash", 1, {}}};
    c.skillBar = {"skill.warrior.iron_cut", "skill.warrior.charge", "skill.warrior.stone_rift", "skill.warrior.shield_bash", "", ""};
    auto put = [&](ItemSlot slot, const char* base, std::uint64_t uid) {
        ItemInstance it;
        it.uid = uid;
        it.baseId = base;
        c.equipment[static_cast<std::size_t>(slot)] = it;
    };
    put(ItemSlot::MainHand, "item_base.iron_sword", 1);
    if (fullKit) {
        put(ItemSlot::Head, "item_base.iron_helm", 2);
        put(ItemSlot::Body, "item_base.leather_vest", 3);
        put(ItemSlot::Hands, "item_base.leather_gloves", 4);
        put(ItemSlot::Legs, "item_base.worn_trousers", 5);
        put(ItemSlot::Feet, "item_base.worn_boots", 6);
    }
    c.conqueredMaps = {"map.act1.crypt"};
    req.snapshot.contentVersion = db.ContentVersion();
    req.contentVersion = db.ContentVersion();
    req.mapId = "map.act1.crypt";
    // Regras de IA típicas da tela da Ilsa: curar abaixo de 35%, área com 3+, Escudada em elite, ataque básico.
    req.rules = {{AiCondition::LifeBelow, 0.35, AiAction::UsePotion, "potion.life"},
                 {AiCondition::EnemiesAtLeast, 3.0, AiAction::UseSkill, "skill.warrior.stone_rift"},
                 {AiCondition::TargetIsElite, 0.0, AiAction::UseSkill, "skill.warrior.shield_bash"},
                 {AiCondition::Always, 0.0, AiAction::UseSkill, "skill.warrior.iron_cut"}};
    req.seed = seed;
    req.startUtc = 1'700'000'000;
    req.durationHours = 12;
    req.effectiveSeconds = 12.0 * 3600.0;
    return req;
}

}  // namespace

TEST(balance_probe_idle_retreat_time_and_rates_when_requested) {
    ContentDB real;
    real.LoadDirectory(tu::ContentDir());
    ASSERT_TRUE(real.Finalize());
    if (tu::GetEnv("SHATTER_BALANCE_PROBE").empty()) return;
    const Variant variants[] = {
        {"antes: m=1,00 sem fichas", "1", false},
        {"fichas ligadas, m=1,00", "1", true},
        {"fichas ligadas, m=0,85", "0.85", true},
        {"fichas ligadas, m=0,92", "0.92", true},
        {"fichas ligadas, m=0,80", "0.8", true},
        {"fichas ligadas, m=0,75", "0.75", true},
        {"fichas ligadas, m=0,70", "0.7", true},
    };
    const int seeds = 20;
    std::printf("\nvariante | cenario | recuaram/20 | recuo em ate 1 h | tempo ate recuar min/mediana/max (min) | xpRaw/h | kills/h\n");
    for (const Variant& v : variants) {
        const std::unique_ptr<ContentDB> db = LoadVariant(v);
        if (!db->Errors().empty()) { FAIL(std::string("variante invalida: ") + v.name + ": " + db->Errors()[0].message); continue; }
        for (int kit = 0; kit < 2; ++kit) {
            std::vector<double> times;
            int retreats = 0, within1h = 0;
            double xp = 0.0, kills = 0.0, secs = 0.0;
            for (int s = 1; s <= seeds; ++s) {
                const ExpeditionRequest req = HeroRequest(*db, kit == 1, static_cast<std::uint64_t>(s));
                const ExpeditionProgress p = SimulateRange(*db, req, ExpeditionProgress(), 0, 0xFFFFFFFFu);
                const ExpeditionResult r = FinalizeExpedition(*db, req, p);
                if (r.stop == StopReason::Retreat) {
                    ++retreats;
                    if (r.effectiveSeconds <= 3600.0) ++within1h;
                }
                times.push_back(r.effectiveSeconds / 60.0);
                for (const EncounterReceipt& rc : r.receipts) { xp += rc.xpRaw; kills += rc.kills; }
                secs += r.effectiveSeconds;
            }
            std::sort(times.begin(), times.end());
            const double hours = secs / 3600.0;
            std::printf("%-26s | %-13s | %2d | %2d | %7.1f / %7.1f / %7.1f | %9.0f | %7.0f\n", v.name, kit ? "kit completo" : "so espada",
                        retreats, within1h, times.front(), (times[9] + times[10]) / 2.0, times.back(), hours > 0 ? xp / hours : 0.0,
                        hours > 0 ? kills / hours : 0.0);
        }
    }
}
