// Sonda de balanceamento da história (Ato I, Cripta): Exorcizar x Devorar no idle, no duelo com o Guardião e no loot da Mancha.
// Só imprime com SHATTER_BALANCE_PROBE=1; sem a variável só confere que o conteúdo carrega. Não afirma números de design.
#include <algorithm>
#include <cstdio>
#include <memory>
#include <sstream>

#include "test_util.h"

using namespace shatter;

namespace {

std::vector<std::string> Lines(const std::string& text) {
    std::vector<std::string> out;
    std::istringstream in(text);
    std::string line;
    while (std::getline(in, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (!line.empty()) out.push_back(line);
    }
    return out;
}

std::vector<std::string> Cells(const std::string& line) {
    std::vector<std::string> c;
    std::string cur;
    for (char ch : line) {
        if (ch == ',') { c.push_back(cur); cur.clear(); }
        else cur += ch;
    }
    c.push_back(cur);
    return c;
}

std::string SetColumn(const std::string& table, const std::string& column, const std::string& value) {
    const std::vector<std::string> lines = Lines(table);
    const std::vector<std::string> header = Cells(lines[0]);
    std::size_t col = header.size();
    for (std::size_t i = 0; i < header.size(); ++i)
        if (header[i] == column) col = i;
    if (col == header.size()) return table;
    std::string out = lines[0] + "\n";
    for (std::size_t i = 1; i < lines.size(); ++i) {
        std::vector<std::string> cells = Cells(lines[i]);
        cells[col] = value;
        for (std::size_t k = 0; k < cells.size(); ++k) out += (k ? "," : "") + cells[k];
        out += "\n";
    }
    return out;
}

std::unique_ptr<ContentDB> Load(bool guardianOnly) {
    auto db = std::make_unique<ContentDB>();
    const std::string dir = tu::ContentDir();
    for (const char* t : tu::kTableNames) {
        const std::string path = dir + "/" + t;
        if (tu::IsOptionalTable(t) && !std::filesystem::exists(std::filesystem::u8path(path))) continue;
        std::string text = tu::ReadFile(path);
        if (guardianOnly && std::string(t) == "maps.csv") text = SetColumn(text, "encounters", "enc.crypt.guardian_duel");
        // Clone do Guardião sem a marca de chefe (o idle não luta contra chefe): mesma vida, armadura e ataques, sem fases nem padrões.
        if (guardianOnly && std::string(t) == "encounters.csv") text += "enc.crypt.guardian_duel,enemy.guardian_duel:1:1:0,1,0,false\n";
        if (guardianOnly && std::string(t) == "enemies.csv")
            text += "enemy.guardian_duel,family.soldier_echo,life:700:50|armor:30:2,150,30,loot.crypt.guardian,false,false,180,1400,true,,,,,,,,\n";
        if (guardianOnly && std::string(t) == "enemy_attacks.csv")
            text += "enemy.guardian_duel,skill.enemy.guardian_hammer,3,true\nenemy.guardian_duel,skill.enemy.guardian_shield_bash,2,true\n"
                    "enemy.guardian_duel,skill.enemy.guardian_shield_charge,2,true\n";
        db->LoadTableCsv(t, text);
    }
    db->Finalize();
    return db;
}

ExpeditionRequest Hero(const ContentDB& db, int level, std::uint64_t seed, bool slam, bool fullKit = true) {
    ExpeditionRequest req;
    CharacterState& c = req.snapshot.character;
    c.name = "Sonda";
    c.classId = "class.warrior";
    c.level = level;
    c.skills = {{"skill.warrior.iron_cut", 1, {}}, {"skill.warrior.charge", 1, {}}, {"skill.warrior.stone_rift", 1, {}},
                {"skill.warrior.shield_bash", 1, {}}};
    c.skillBar = {"skill.warrior.iron_cut", "skill.warrior.charge", "skill.warrior.stone_rift", "skill.warrior.shield_bash", "", ""};
    if (slam) {
        c.skills.push_back({"skill.devoured.guardian_slam", 1, {}});
        c.skillBar[4] = "skill.devoured.guardian_slam";
    }
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
    req.rules = {{AiCondition::LifeBelow, 0.35, AiAction::UsePotion, "potion.life"}};
    if (slam) req.rules.push_back({AiCondition::TargetIsBoss, 0.0, AiAction::UseSkill, "skill.devoured.guardian_slam"});
    req.rules.push_back({AiCondition::EnemiesAtLeast, 3.0, AiAction::UseSkill, "skill.warrior.stone_rift"});
    req.rules.push_back({AiCondition::TargetIsElite, 0.0, AiAction::UseSkill, "skill.warrior.shield_bash"});
    req.rules.push_back({AiCondition::Always, 0.0, AiAction::UseSkill, "skill.warrior.iron_cut"});
    req.seed = seed;
    req.startUtc = 1'700'000'000;
    req.durationHours = 12;
    req.effectiveSeconds = 12.0 * 3600.0;
    return req;
}

struct Scenario {
    const char* name;
    int statPct, potionPct, elitePct;
    bool slam;
};

}  // namespace

TEST(balance_story_idle_duel_and_stain_loot_when_requested) {
    const std::unique_ptr<ContentDB> db = Load(false);
    ASSERT_TRUE(db->Errors().empty());
    if (tu::GetEnv("SHATTER_BALANCE_PROBE").empty()) return;
    const std::unique_ptr<ContentDB> duelDb = Load(true);
    if (!duelDb->Errors().empty()) { FAIL(duelDb->Errors()[0].message); return; }

    const Scenario scenarios[] = {
        {"sem veredito", 0, 0, 0, false},
        {"Exorcizar (reliquia +25%)", 0, 25, 0, false},
        {"Exorcizar (reliquia +35%)", 0, 35, 0, false},
        {"Exorcizar (reliquia +40%) [vigente]", 0, 40, 0, false},
        {"Devorar 8% mancha 10 [vigente]", 8, 0, 10, false},
        {"Devorar 10% mancha 15 [antigo]", 10, 0, 15, false},
        {"Devorar 15% mancha 25", 15, 0, 25, false},
    };
    const int seeds = 30;
    std::printf("\n== Idle 12 h na Cripta (Guerreiro, kit completo) ==\ncenario | nivel | recuos/%d | recuo mediana (min) | xp/h | kills/h | elites/h | pocoes/h | itens/h | raros/exp\n", seeds);
    for (int level : {4, 6}) {
        for (const Scenario& sc : scenarios) {
            std::vector<double> times;
            int retreats = 0;
            double xp = 0, kills = 0, elites = 0, pots = 0, items = 0, rares = 0, secs = 0;
            for (int s = 1; s <= seeds; ++s) {
                ExpeditionRequest req = Hero(*db, level, static_cast<std::uint64_t>(s), false);
                req.storyStatBonusPct = sc.statPct;
                req.storyPotionEffectPct = sc.potionPct;
                req.storyEliteBonusPct = sc.elitePct;
                const ExpeditionProgress p = SimulateRange(*db, req, ExpeditionProgress(), 0, 0xFFFFFFFFu);
                const ExpeditionResult r = FinalizeExpedition(*db, req, p);
                if (r.stop == StopReason::Retreat) ++retreats;
                times.push_back(r.effectiveSeconds / 60.0);
                for (const EncounterReceipt& rc : r.receipts) { xp += rc.xpRaw; kills += rc.kills; elites += rc.elitesKilled; pots += rc.potionsUsed; }
                items += static_cast<double>(r.items.size());
                rares += r.raresDropped;
                secs += r.effectiveSeconds;
            }
            std::sort(times.begin(), times.end());
            const double h = secs > 0 ? secs / 3600.0 : 1.0;
            std::printf("%-27s | %d | %2d | %7.1f | %7.0f | %6.0f | %5.1f | %5.1f | %5.1f | %4.2f\n", sc.name, level, retreats,
                        (times[seeds / 2 - 1] + times[seeds / 2]) / 2.0, xp / h, kills / h, elites / h, pots / h, items / h, rares / seeds);
        }
    }

    {
        std::printf("\n== Idle 12 h, heroi fraco (so espada) e isolamento dos efeitos ==\ncenario | nivel | recuos/%d | recuo mediana (min) | xp/h | elites/h | pocoes/h\n", seeds);
        const Scenario iso[] = {
            {"sem veredito", 0, 0, 0, false},
            {"Exorcizar +25%", 0, 25, 0, false},
            {"Exorcizar +40%", 0, 40, 0, false},
            {"Devorar so atributos 10%", 10, 0, 0, false},
            {"Devorar so mancha 15", 0, 0, 15, false},
            {"Devorar so mancha 8", 0, 0, 8, false},
            {"Devorar 6% mancha 8", 6, 0, 8, false},
            {"Devorar 8% mancha 10 [vigente]", 8, 0, 10, false},
            {"Devorar 10% mancha 15 [antigo]", 10, 0, 15, false},
        };
        for (int level : {3, 4}) {
            for (const Scenario& sc : iso) {
                std::vector<double> times;
                int retreats = 0;
                double xp = 0, elites = 0, pots = 0, secs = 0;
                for (int s = 1; s <= seeds; ++s) {
                    ExpeditionRequest req = Hero(*db, level, static_cast<std::uint64_t>(s), false, false);
                    req.storyStatBonusPct = sc.statPct;
                    req.storyPotionEffectPct = sc.potionPct;
                    req.storyEliteBonusPct = sc.elitePct;
                    const ExpeditionProgress p = SimulateRange(*db, req, ExpeditionProgress(), 0, 0xFFFFFFFFu);
                    const ExpeditionResult r = FinalizeExpedition(*db, req, p);
                    if (r.stop == StopReason::Retreat) ++retreats;
                    times.push_back(r.effectiveSeconds / 60.0);
                    for (const EncounterReceipt& rc : r.receipts) { xp += rc.xpRaw; elites += rc.elitesKilled; pots += rc.potionsUsed; }
                    secs += r.effectiveSeconds;
                }
                std::sort(times.begin(), times.end());
                const double h = secs > 0 ? secs / 3600.0 : 1.0;
                std::printf("%-27s | %d | %2d | %7.1f | %7.0f | %5.1f | %5.1f\n", sc.name, level, retreats,
                            (times[seeds / 2 - 1] + times[seeds / 2]) / 2.0, xp / h, elites / h, pots / h);
            }
        }
    }

    std::printf("\n== Duelo com o Guardiao (1o encontro, heroi cheio, idle sem padroes de chefe) ==\ncenario | nivel | vitorias/%d | duracao mediana (s) | vida ao fim (media) | pocoes (media)\n", seeds);
    const Scenario duel[] = {
        {"sem veredito", 0, 0, 0, false},
        {"Exorcizar +40%", 0, 40, 0, false},
        {"Devorar 8%", 8, 0, 0, false},
    };
    for (int level : {3, 4, 5, 6}) {
        for (const Scenario& sc : duel) {
            int wins = 0;
            std::vector<double> dur;
            double life = 0, pots = 0;
            for (int s = 1; s <= seeds; ++s) {
                ExpeditionRequest req = Hero(*duelDb, level, static_cast<std::uint64_t>(s), sc.slam);
                req.storyStatBonusPct = sc.statPct;
                req.storyPotionEffectPct = sc.potionPct;
                req.durationHours = 1;
                req.effectiveSeconds = 3600.0;
                const ExpeditionProgress p = SimulateRange(*duelDb, req, ExpeditionProgress(), 0, 1);
                if (p.receipts.empty()) continue;
                const EncounterReceipt& rc = p.receipts[0];
                if (rc.outcome == EncounterOutcome::Cleared) ++wins;
                dur.push_back(rc.duration);
                life += rc.lifeFractionAtEnd;
                pots += rc.potionsUsed;
            }
            std::sort(dur.begin(), dur.end());
            const double n = dur.empty() ? 1.0 : static_cast<double>(dur.size());
            std::printf("%-26s | %d | %2d | %6.1f | %4.2f | %3.1f\n", sc.name, level, wins, dur.empty() ? 0.0 : dur[dur.size() / 2], life / n, pots / n);
        }
    }

    std::printf("\n== Loot por encontro limpo (10000 rolagens, areaLevel 3, modo Manual) ==\ntabela | itens/rolagem | raros/rolagem | pilhas/rolagem\n");
    for (const char* id : {"loot.crypt.area", "loot.crypt.common", "loot.crypt.elite", "loot.crypt.stain", "loot.crypt.guardian"}) {
        const LootTableData* t = db->FindLootTable(id);
        ASSERT_TRUE(t != nullptr);
        double items = 0, rares = 0, stacks = 0;
        const int n = 10000;
        for (int i = 0; i < n; ++i) {
            Pcg32 rng = Pcg32::ForStream(77, RngStream::Loot, static_cast<std::uint64_t>(i));
            LootContext ctx;
            ctx.mode = LootMode::Manual;
            ctx.areaLevel = 3;
            const LootDrop d = RollLootTable(*db, *t, ctx, rng);
            items += static_cast<double>(d.items.size());
            rares += d.raresDropped;
            stacks += static_cast<double>(d.stacks.size());
        }
        std::printf("%-20s | %.3f | %.3f | %.3f\n", id, items / n, rares / n, stacks / n);
    }
}
