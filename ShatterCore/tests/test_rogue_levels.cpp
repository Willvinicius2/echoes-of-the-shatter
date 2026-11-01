// XP, nível, cartas de nível, baú de elite, curva de horda, vida do chefe adaptativa e modo horda (rogue.h, API 1.12;
// plano docs/design/31, pacote H4) com os CSV reais de godot/data2d.
#include <algorithm>
#include <string>
#include <vector>

#include "shatter/rogue_waves.h"
#include "test_util.h"

using namespace shatter;

namespace {

const RogueData& Data() {
    static RogueData d;
    static bool loaded = false;
    if (!loaded) {
        loaded = true;
        d.LoadDirectory(SHATTER_ROGUE_DATA_DIR);
        d.Finalize();
    }
    return d;
}

RogueStats Base() { return {{"hp_max", 100.0}, {"arrow_damage", 10.0}, {"speed", 200.0}, {"shoot_cooldown", 0.5}}; }

bool IsAttack(const RogueData& d, const ContentId& id) {
    return d.Upgrades()[static_cast<std::size_t>(d.FindUpgrade(id))].attack;
}

bool IsRare(const RogueData& d, const ContentId& id) {
    return d.Upgrades()[static_cast<std::size_t>(d.FindUpgrade(id))].rare;
}

// Pasta temporária com os CSV reais e uma troca de texto num deles.
RogueData Patched(const std::string& table, const std::string& from, const std::string& to, bool& ok) {
    RogueData d;
    ok = true;
    for (const char* name : {"meta.csv", "receitas.csv", "drops.csv", "rota.csv", "run.csv", "run_settings.csv",
                             "upgrades.csv", "ondas.csv", "ondas_fases.csv", "curva_horda.csv"}) {
        std::string text = tu::ReadFile(std::string(SHATTER_ROGUE_DATA_DIR) + "/" + name);
        if (table == name) {
            const std::size_t at = text.find(from);
            if (at == std::string::npos) ok = false;
            else text.replace(at, from.size(), to);
        }
        if (!d.LoadTableCsv(name, text)) ok = false;
    }
    if (!d.Finalize()) ok = false;
    return d;
}

}  // namespace

TEST(rogue_levels_data_loads) {
    const RogueData& d = Data();
    for (const ContentError& e : d.Errors()) FAIL(e.table + ":" + std::to_string(e.line) + " " + e.message);
    ASSERT_TRUE(d.Ok());
    EXPECT_TRUE(d.XpForLevel(1) > 0);
    EXPECT_TRUE(d.XpForLevel(2) >= d.XpForLevel(1));
    EXPECT_TRUE(d.LevelCards() >= 1);
    EXPECT_TRUE(d.ChestCards() >= 1);
    int attack = 0, rare = 0;
    for (const RogueUpgrade& u : d.Upgrades()) {
        attack += u.attack ? 1 : 0;
        rare += u.rare ? 1 : 0;
    }
    EXPECT_TRUE(attack >= 1);
    EXPECT_TRUE(rare >= 1);
    // Curva: toda onda da Cripta e o enxame têm linha.
    int first = 0, count = 0;
    ASSERT_TRUE(d.FindWavePhase("cripta", first, count));
    for (int w = 1; w <= count + 1; ++w) EXPECT_TRUE(d.FindCurve("cripta", w) != nullptr);
    EXPECT_TRUE(d.FindCurve("cripta", count + 2) == nullptr);
    const RogueDrop* bat = d.FindDrop("crypt_bat");
    ASSERT_TRUE(bat != nullptr);
    EXPECT_TRUE(bat->xp >= 1);
}

TEST(rogue_levels_bad_data_is_refused) {
    bool ok = true;
    Patched("upgrades.csv", "ataque", "magia", ok);
    EXPECT_FALSE(ok);
    Patched("upgrades.csv", "rara", "lendaria", ok);
    EXPECT_FALSE(ok);
    Patched("drops.csv", "crypt_bat,2,osso_antigo,1,1", "crypt_bat,2,osso_antigo,1,-3", ok);
    EXPECT_FALSE(ok);
    Patched("curva_horda.csv", "cripta,1,", "nada,1,", ok);
    EXPECT_FALSE(ok);
    Patched("curva_horda.csv", "cripta,9,", "cripta,10,", ok);
    EXPECT_FALSE(ok);
    Patched("curva_horda.csv", "cripta,2,1.1", "cripta,2,0", ok);
    EXPECT_FALSE(ok);
    Patched("curva_horda.csv", "cripta,3,", "cripta,2,", ok);
    EXPECT_FALSE(ok);
    Patched("run_settings.csv", "level_cards,3", "level_cards,2.5", ok);
    EXPECT_FALSE(ok);
    Patched("run_settings.csv", "boss_hp_max,2.5", "boss_hp_max,0.1", ok);
    EXPECT_FALSE(ok);
    // Sem as colunas novas (CSV da 1.11) continua valendo: tipo utilidade, comum, xp 0.
    RogueData old;
    const bool okOld = old.LoadTableCsv("upgrades.csv", "id,stat,modo,valor,nivel_max\npower,arrow_damage,mult,0.25,3\n") &&
                       old.LoadTableCsv("drops.csv", "inimigo,fragmentos,material,material_qtd\nbat,1,osso,1\n");
    EXPECT_TRUE(okOld);
    EXPECT_FALSE(old.Upgrades()[0].attack);
    EXPECT_EQ(old.Drops()[0].xp, std::int64_t(0));
}

TEST(rogue_levels_xp_levels_and_attack_card) {
    const RogueData& d = Data();
    RogueState s(d);
    EXPECT_ENUM_EQ(s.GainXp(5), RogueRunResult::WrongPhase);  // sem corrida
    s.StartRun(7, Base());
    const std::string before = s.StateHash();
    EXPECT_EQ(s.CharLevel(), 1);
    EXPECT_EQ(s.XpNext(), d.XpForLevel(1));
    int lv = -1;
    EXPECT_ENUM_EQ(s.GainXp(d.XpForLevel(1) - 1, &lv), RogueRunResult::Ok);
    EXPECT_EQ(lv, 0);
    EXPECT_TRUE(s.LevelOffer().empty());
    EXPECT_TRUE(s.StateHash() != before);  // XP entra no estado
    // Fecha dois níveis de uma vez: uma oferta aberta e uma na fila.
    EXPECT_ENUM_EQ(s.GainXp(1 + d.XpForLevel(2), &lv), RogueRunResult::Ok);
    EXPECT_EQ(lv, 2);
    EXPECT_EQ(s.CharLevel(), 3);
    EXPECT_EQ(s.RunXp(), std::int64_t(0));
    EXPECT_EQ(std::string(s.LevelOfferKind()), std::string("level"));
    EXPECT_EQ(s.LevelOffer().size(), static_cast<std::size_t>(d.LevelCards()));
    EXPECT_EQ(s.PendingLevels(), 1);
    EXPECT_TRUE(std::any_of(s.LevelOffer().begin(), s.LevelOffer().end(), [&](const ContentId& id) { return IsAttack(d, id); }));
    // Escolher sobe o upgrade e abre a próxima oferta; a vida sobe junto com hp_max.
    const ContentId pick = s.LevelOffer().front();
    double hp = 0.0;
    EXPECT_ENUM_EQ(s.ChooseLevelCard("nao_existe", 50.0, &hp), RogueRunResult::NotOffered);
    EXPECT_ENUM_EQ(s.ChooseLevelCard(pick, 50.0, &hp), RogueRunResult::Ok);
    EXPECT_EQ(s.RunLevel(pick), 1);
    EXPECT_EQ(s.PendingLevels(), 0);
    EXPECT_FALSE(s.LevelOffer().empty());
    EXPECT_ENUM_EQ(s.ChooseLevelCard(s.LevelOffer().front(), 50.0, &hp), RogueRunResult::Ok);
    EXPECT_TRUE(s.LevelOffer().empty());
    EXPECT_EQ(std::string(s.LevelOfferKind()), std::string(""));
    EXPECT_ENUM_EQ(s.ChooseLevelCard(pick, 50.0, &hp), RogueRunResult::WrongPhase);
}

TEST(rogue_levels_attack_guaranteed_over_many_seeds) {
    const RogueData& d = Data();
    for (std::uint64_t seed = 1; seed <= 200; ++seed) {
        RogueState s(d);
        s.StartRun(seed, Base());
        s.GainXp(d.XpForLevel(1));
        ASSERT_TRUE(!s.LevelOffer().empty());
        const bool hasAttack =
            std::any_of(s.LevelOffer().begin(), s.LevelOffer().end(), [&](const ContentId& id) { return IsAttack(d, id); });
        EXPECT_TRUE(hasAttack);
        // Sem repetir carta.
        std::vector<ContentId> o = s.LevelOffer();
        std::sort(o.begin(), o.end());
        EXPECT_TRUE(std::adjacent_find(o.begin(), o.end()) == o.end());
    }
}

TEST(rogue_levels_reroll_skip_ban_limits) {
    const RogueData& d = Data();
    RogueState s(d);
    s.StartRun(11, Base());
    EXPECT_ENUM_EQ(s.RerollLevel(), RogueRunResult::WrongPhase);  // sem oferta
    s.GainXp(d.XpForLevel(1) + d.XpForLevel(2) + d.XpForLevel(3));
    ASSERT_TRUE(!s.LevelOffer().empty());
    for (int i = 0; i < d.LevelRerolls(); ++i) EXPECT_ENUM_EQ(s.RerollLevel(), RogueRunResult::Ok);
    EXPECT_EQ(s.RerollsLeft(), 0);
    EXPECT_ENUM_EQ(s.RerollLevel(), RogueRunResult::WrongPhase);
    const ContentId ban = s.LevelOffer().front();
    EXPECT_ENUM_EQ(s.BanCard("nao_existe"), RogueRunResult::NotOffered);
    EXPECT_ENUM_EQ(s.BanCard(ban), RogueRunResult::Ok);
    EXPECT_TRUE(s.Banned(ban));
    EXPECT_FALSE(std::find(s.LevelOffer().begin(), s.LevelOffer().end(), ban) != s.LevelOffer().end());
    const std::vector<ContentId> avail = s.AvailableUpgrades();
    EXPECT_FALSE(std::find(avail.begin(), avail.end(), ban) != avail.end());
    EXPECT_EQ(s.BansLeft(), d.LevelBans() - 1);
    const int pending = s.PendingLevels();
    EXPECT_ENUM_EQ(s.SkipLevel(), RogueRunResult::Ok);
    EXPECT_EQ(s.PendingLevels(), pending - 1);
    EXPECT_EQ(s.SkipsLeft(), d.LevelSkips() - 1);
    if (d.LevelSkips() == 1) EXPECT_ENUM_EQ(s.SkipLevel(), RogueRunResult::WrongPhase);
    // Nova corrida devolve os saldos e tira o banimento.
    s.StartRun(12, Base());
    EXPECT_EQ(s.RerollsLeft(), d.LevelRerolls());
    EXPECT_FALSE(s.Banned(ban));
}

TEST(rogue_levels_chest_offers_rare_after_levels) {
    const RogueData& d = Data();
    RogueState s(d);
    s.StartRun(3, Base());
    std::int64_t xp = -1;
    bool chest = false;
    EXPECT_ENUM_EQ(s.KillXp("crypt_bat", 1.0, false, &xp, &chest), RogueRunResult::Ok);
    EXPECT_EQ(xp, d.FindDrop("crypt_bat")->xp);
    EXPECT_FALSE(chest);
    EXPECT_ENUM_EQ(s.KillXp("chain_wraith", 1.5, true, &xp, &chest), RogueRunResult::Ok);
    EXPECT_EQ(xp, (d.FindDrop("chain_wraith")->xp * 3 + 1) / 2);  // x 1,5 arredondado
    EXPECT_TRUE(chest);
    EXPECT_ENUM_EQ(s.KillXp("ninguem", 1.0, false, &xp, &chest), RogueRunResult::Unknown);
    // Baú com um nível pendente: o nível vem antes.
    s.GainXp(d.XpForLevel(1));
    EXPECT_ENUM_EQ(s.OpenChest(), RogueRunResult::Ok);
    EXPECT_EQ(std::string(s.LevelOfferKind()), std::string("level"));
    EXPECT_EQ(s.PendingChests(), 1);
    s.ChooseLevelCard(s.LevelOffer().front(), 50.0);
    EXPECT_EQ(std::string(s.LevelOfferKind()), std::string("chest"));
    ASSERT_TRUE(!s.LevelOffer().empty());
    for (const ContentId& id : s.LevelOffer()) EXPECT_TRUE(IsRare(d, id));
    EXPECT_TRUE(s.LevelOffer().size() <= static_cast<std::size_t>(d.ChestCards()));
}

TEST(rogue_levels_external_cards_level_without_offer) {
    const RogueData& d = Data();
    RogueState s(d);
    EXPECT_ENUM_EQ(s.SetExternalCards(true), RogueRunResult::Ok);
    s.StartRun(5, Base());
    int lv = 0;
    s.GainXp(d.XpForLevel(1) + d.XpForLevel(2), &lv);
    EXPECT_EQ(lv, 2);
    EXPECT_TRUE(s.LevelOffer().empty());
    EXPECT_EQ(s.PendingLevels(), 0);
    s.OpenChest();
    EXPECT_TRUE(s.LevelOffer().empty());
}

TEST(rogue_levels_state_roundtrip_and_hash) {
    const RogueData& d = Data();
    RogueState a(d), b(d);
    a.StartRun(21, Base());
    b.StartRun(21, Base());
    EXPECT_EQ(a.StateJson().find("progress"), std::string::npos);  // sem nível usado, JSON da 1.11
    a.GainXp(d.XpForLevel(1) + d.XpForLevel(2));
    a.OpenChest();
    a.RerollLevel();
    a.BanCard(a.LevelOffer().back());
    const std::string text = a.StateJson();
    EXPECT_TRUE(text.find("progress") != std::string::npos);
    std::string err;
    ASSERT_TRUE(b.RestoreState(text, &err));
    EXPECT_EQ(b.StateHash(), a.StateHash());
    EXPECT_TRUE(b.LevelOffer() == a.LevelOffer());
    // Mesmas ações nos dois = mesmas ofertas daqui para frente.
    a.ChooseLevelCard(a.LevelOffer().front(), 40.0);
    b.ChooseLevelCard(b.LevelOffer().front(), 40.0);
    EXPECT_EQ(b.StateHash(), a.StateHash());
    // Restore inválido não muda nada.
    const std::string h = b.StateHash();
    std::string bad = text;
    const std::size_t at = bad.find("\"kind\":");
    ASSERT_TRUE(at != std::string::npos);
    bad.replace(at, 8, "\"kind\":7");
    EXPECT_FALSE(b.RestoreState(bad, &err));
    EXPECT_EQ(b.StateHash(), h);
}

TEST(rogue_levels_horde_mode_and_win) {
    const RogueData& d = Data();
    RogueState s(d);
    EXPECT_ENUM_EQ(s.WinRun(), RogueRunResult::WrongPhase);
    EXPECT_ENUM_EQ(s.SetHorde(true), RogueRunResult::Ok);
    s.StartRun(9, Base());
    EXPECT_ENUM_EQ(s.SetHorde(false), RogueRunResult::WrongPhase);  // corrida viva
    const int alive = s.Alive();
    for (int i = 0; i < alive + 20; ++i) s.EnemyKilled("crypt_bat");
    EXPECT_ENUM_EQ(s.Phase(), RoguePhase::Fight);  // nunca limpa no modo horda
    EXPECT_TRUE(s.Offer().empty());
    const std::int64_t frag = s.GainFragments();
    EXPECT_EQ(frag, d.FindDrop("crypt_bat")->fragments * (alive + 20));
    EXPECT_ENUM_EQ(s.WinRun(), RogueRunResult::Ok);
    EXPECT_ENUM_EQ(s.Phase(), RoguePhase::Won);
    EXPECT_EQ(s.GainFragments(), frag + d.VictoryFragments());
    EXPECT_ENUM_EQ(s.WinRun(), RogueRunResult::WrongPhase);
    EXPECT_TRUE(s.StateJson().find("\"horde\":true") != std::string::npos);
    RogueState t(d);
    ASSERT_TRUE(t.RestoreState(s.StateJson()));
    EXPECT_TRUE(t.Horde());
}

TEST(rogue_levels_boss_hp_adaptive) {
    const RogueData& d = Data();
    double t = 0.0, lo = 0.0, hi = 0.0;
    ASSERT_TRUE(d.Setting("boss_fight_time", t));
    ASSERT_TRUE(d.Setting("boss_hp_min", lo));
    ASSERT_TRUE(d.Setting("boss_hp_max", hi));
    EXPECT_NEAR(d.BossHp(1000.0, 0.0), 1000.0, 1e-9);           // sem DPS: a base
    EXPECT_NEAR(d.BossHp(1000.0, -5.0), 1000.0, 1e-9);
    EXPECT_NEAR(d.BossHp(1000.0, 1.0e-3), 1000.0 * lo, 1e-9);   // DPS baixo: mínimo
    EXPECT_NEAR(d.BossHp(1000.0, 1.0e7), 1000.0 * hi, 1e-9);    // DPS alto: máximo
    const double mid = 1000.0 * (lo + hi) / 2.0 / t;            // DPS que cai no meio da faixa
    EXPECT_NEAR(d.BossHp(1000.0, mid), mid * t, 1e-6);
}

TEST(rogue_levels_curve_applies_to_spawns) {
    const RogueData& d = Data();
    RogueWaves w(d);
    ASSERT_TRUE(w.Start("cripta", 4) == RogueWaveResult::Ok);
    w.Tick(0.1);
    ASSERT_TRUE(!w.Pending().empty());
    const RogueCurveRow* c1 = d.FindCurve("cripta", 1);
    ASSERT_TRUE(c1 != nullptr);
    for (const RogueWaveSpawn& s : w.Pending()) {
        EXPECT_EQ(s.wave, 1);
        EXPECT_NEAR(s.speedMult, c1->speed, 1e-12);
        EXPECT_NEAR(s.xpMult, c1->xp, 1e-12);
        EXPECT_NEAR(s.hpMult, (s.elite ? d.Waves()[0].eliteHp : 1.0) * c1->hp, 1e-12);
    }
    // Estado com curva: ida e volta igual.
    RogueWaves w2(d);
    ASSERT_TRUE(w2.RestoreState(w.StateJson()));
    EXPECT_EQ(w2.StateHash(), w.StateHash());
}
