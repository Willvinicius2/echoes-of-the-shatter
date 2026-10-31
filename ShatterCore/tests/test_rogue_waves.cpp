// Spawner de hordas do roguelike 2D (rogue_waves.h, API 1.11): leitura de ondas.csv, orçamento, teto de vivos, elites,
// chefe na última onda, passagem de onda, determinismo (1 ou N ticks, restore) com o ondas.csv real de godot/data2d.
#include <algorithm>
#include <map>
#include <string>
#include <vector>

#include "test_util.h"

using namespace shatter;

namespace {

const RogueData& RealData() {
    static RogueData d;
    static bool loaded = false;
    if (!loaded) {
        loaded = true;
        d.LoadDirectory(SHATTER_ROGUE_DATA_DIR);
        d.Finalize();
    }
    return d;
}

const char* kHeader = "fase,onda,duracao,intervalo,lote,orcamento,teto,inimigos,elites,elite_vida,elite_dano,chefe\n";

// Só o ondas.csv (o spawner não lê as outras tabelas).
bool LoadWaves(RogueData& d, const std::string& rows) { return d.LoadTableCsv("ondas.csv", std::string(kHeader) + rows); }

std::vector<RogueWaveSpawn> Take(RogueWaves& w) {
    std::vector<RogueWaveSpawn> out = w.Pending();
    w.ClearPending();
    return out;
}

// Bot simples: cada inimigo morre `life` segundos depois de nascer (o chefe, `bossLife`). Mede o pico de vivos comuns.
struct Bot {
    double life = 3.0;
    double bossLife = 70.0;  // o bastante para a última onda gastar o orçamento antes de o chefe cair
    double t = 0.0;
    int peakRegular = 0;
    int elites = 0;
    int bosses = 0;
    int bossWave = 0;
    std::map<std::uint32_t, double> due;  // id -> instante da morte

    void Step(RogueWaves& w, double dt) {
        t += dt;
        for (auto it = due.begin(); it != due.end();) {
            if (it->second <= t) {
                w.Killed(it->first);
                it = due.erase(it);
            } else {
                ++it;
            }
        }
        w.Tick(dt);
        for (const RogueWaveSpawn& s : Take(w)) {
            due[s.id] = t + (s.boss ? bossLife : life);
            elites += s.elite ? 1 : 0;
            if (s.boss) {
                ++bosses;
                bossWave = s.wave;
            }
        }
        int regular = 0;
        for (const RogueWaveSpawn& s : w.AliveList()) regular += s.boss ? 0 : 1;
        peakRegular = std::max(peakRegular, regular);
    }
};

}  // namespace

TEST(rogue_waves_real_csv_loads) {
    const RogueData& d = RealData();
    for (const ContentError& e : d.Errors()) FAIL(e.table + ":" + std::to_string(e.line) + " " + e.message);
    ASSERT_TRUE(d.Ok());
    int first = -1, count = 0;
    ASSERT_TRUE(d.FindWavePhase("cripta", first, count));
    EXPECT_EQ(first, 0);
    EXPECT_EQ(count, 8);
    const RogueWaveDef& last = d.Waves()[static_cast<std::size_t>(first + count - 1)];
    EXPECT_EQ(last.boss, std::string("crypt_guardian"));
    EXPECT_EQ(last.cap, 40);
    for (const RogueWaveDef& w : d.Waves()) {
        EXPECT_TRUE(w.cap <= 40);  // teto ~40 vivos do plano 31
        EXPECT_TRUE(w.minCost >= 1);
    }
    EXPECT_FALSE(d.FindWavePhase("nao_existe", first, count));
}

TEST(rogue_waves_csv_errors) {
    struct Case {
        const char* rows;
        const char* why;
    };
    const Case cases[] = {
        {"f,2,10,1,1,5,5,a:1,0,,,\n", "onda must start at 1"},
        {"f,1,10,1,1,5,5,a:1,0,,,\nf,3,10,1,1,5,5,a:1,0,,,\n", "onda must count"},
        {"f,1,10,1,1,5,5,a:1,0,,,b\nf,2,10,1,1,5,5,a:1,0,,,\n", "chefe not on last onda"},
        {"f,1,10,1,1,5,5,a:1,0,,,\ng,1,10,1,1,5,5,a:1,0,,,\nf,2,10,1,1,5,5,a:1,0,,,\n", "fase split"},
        {"f,1,0,1,1,5,5,a:1,0,,,\n", "duracao 0"},
        {"f,1,10,0,1,5,5,a:1,0,,,\n", "intervalo 0"},
        {"f,1,10,1,0,5,5,a:1,0,,,\n", "lote 0"},
        {"f,1,10,1,1,5,0,a:1,0,,,\n", "teto 0"},
        {"f,1,10,1,1,5,5,a:0,0,,,\n", "peso 0"},
        {"f,1,10,1,1,5,5,a:1|a:2,0,,,\n", "id repetido"},
        {"f,1,10,1,1,5,5,a:1:0,0,,,\n", "custo 0"},
        {"f,1,10,1,1,5,5,,0,,,\n", "orcamento sem inimigos"},
        {"f,1,10,1,1,0,5,,0,,,\n", "onda vazia"},
        {"f,1,10,1,1,5,5,a:1,0,0,,\n", "elite_vida 0"},
        {",1,10,1,1,5,5,a:1,0,,,\n", "fase vazia"},
    };
    for (const Case& c : cases) {
        RogueData d;
        if (LoadWaves(d, c.rows)) FAIL(std::string("accepted: ") + c.why);
    }
    RogueData bad;
    EXPECT_FALSE(bad.LoadTableCsv("ondas.csv", "fase,onda\nf,1\n"));
    RogueData ok;
    EXPECT_TRUE(LoadWaves(ok, "f,1,10,1,1,5,5,a:1|b:2:3,1,2,1.5,\nf,2,10,1,1,0,5,,0,,,boss\n"));
    ASSERT_EQ(ok.Waves().size(), std::size_t(2));
    EXPECT_EQ(ok.Waves()[0].mix[1].cost, 3);
    EXPECT_EQ(ok.Waves()[0].minCost, 1);
    EXPECT_EQ(ok.Waves()[0].durationUs, std::int64_t(10000000));
    EXPECT_NEAR(ok.Waves()[1].eliteHp, 1.0, 1e-12);
}

TEST(rogue_waves_basic_results) {
    RogueWaves none;
    EXPECT_ENUM_EQ(none.Start("cripta", 1), RogueWaveResult::Unknown);
    RogueWaves w(RealData());
    EXPECT_ENUM_EQ(w.Killed(1), RogueWaveResult::NotRunning);
    EXPECT_ENUM_EQ(w.Start("nao_existe", 1), RogueWaveResult::Unknown);
    EXPECT_FALSE(w.Running());
    EXPECT_EQ(w.Tick(1.0), 0);
    ASSERT_TRUE(w.Start("cripta", 7) == RogueWaveResult::Ok);
    EXPECT_EQ(w.Wave(), 1);
    EXPECT_EQ(w.WavesTotal(), 8);
    EXPECT_EQ(w.Tick(0.0), 0);
    EXPECT_EQ(w.Tick(-1.0), 0);
    // 1º lote no instante 0: `lote` da onda 1.
    EXPECT_EQ(w.Tick(0.001), RealData().Waves()[0].batch);
    EXPECT_ENUM_EQ(w.Killed(9999), RogueWaveResult::NotAlive);
    const std::uint32_t id = w.AliveList().front().id;
    EXPECT_ENUM_EQ(w.Killed(id), RogueWaveResult::Ok);
    EXPECT_ENUM_EQ(w.Killed(id), RogueWaveResult::NotAlive);
    EXPECT_EQ(w.KilledTotal(), 1u);
    w.Stop();
    EXPECT_FALSE(w.Running());
    EXPECT_EQ(w.Alive(), 0);
    EXPECT_TRUE(w.Pending().empty());
}

TEST(rogue_waves_cap_holds_without_kills) {
    RogueWaves w(RealData());
    w.Start("cripta", 3);
    const RogueWaveDef& d1 = RealData().Waves()[0];
    for (int i = 0; i < 400; ++i) w.Tick(0.5);  // 200 s sem matar ninguém
    EXPECT_EQ(w.Alive(), d1.cap);               // parou no teto
    EXPECT_EQ(w.Wave(), 1);                      // e não passa de onda com orçamento sobrando
    EXPECT_FALSE(w.Exhausted());
    EXPECT_EQ(w.BudgetLeft() + d1.cap, d1.budget);  // onda 1 só tem custo 1
}

TEST(rogue_waves_full_phase_with_bot) {
    RogueWaves w(RealData());
    ASSERT_TRUE(w.Start("cripta", 1234) == RogueWaveResult::Ok);
    Bot bot;
    int guard = 0;
    while (!w.Complete() && guard++ < 20000) bot.Step(w, 0.25);
    ASSERT_TRUE(w.Complete());
    int expectedElites = 0;
    for (const RogueWaveDef& d : RealData().Waves()) expectedElites += d.elites;
    EXPECT_EQ(bot.elites, expectedElites);
    EXPECT_EQ(bot.bosses, 1);
    EXPECT_EQ(bot.bossWave, 8);
    EXPECT_TRUE(bot.peakRegular <= 40);
    EXPECT_TRUE(bot.peakRegular >= 8);  // é horda de verdade
    // ~8 min (plano 31): soma das durações + o tempo de matar o chefe.
    const double minutes = static_cast<double>(w.TimeUs()) / 60000000.0;
    EXPECT_TRUE(minutes > 6.0);
    EXPECT_TRUE(minutes < 10.0);
    // Depois de completa, nada mais nasce.
    EXPECT_EQ(w.Tick(5.0), 0);
}

TEST(rogue_waves_advance_early_when_cleared) {
    RogueData d;
    ASSERT_TRUE(LoadWaves(d, "t,1,100,1,10,4,10,a:1,0,,,\nt,2,100,1,10,4,10,b:1,0,,,\n"));
    RogueWaves w(d);
    w.Start("t", 5);
    EXPECT_EQ(w.Tick(0.1), 4);  // orçamento todo no 1º lote
    EXPECT_TRUE(w.Exhausted());
    for (const RogueWaveSpawn& s : Take(w)) w.Killed(s.id);
    EXPECT_EQ(w.Wave(), 1);
    w.Tick(1.0);  // no próximo lote vê que a onda acabou e ninguém está vivo
    EXPECT_EQ(w.Wave(), 2);
    const std::vector<RogueWaveSpawn> s2 = Take(w);
    ASSERT_EQ(s2.size(), std::size_t(4));
    EXPECT_EQ(s2[0].enemy, std::string("b"));
    EXPECT_EQ(s2[0].wave, 2);
    for (const RogueWaveSpawn& s : s2) w.Killed(s.id);
    EXPECT_TRUE(w.Complete());  // última onda sem chefe: orçamento gasto e ninguém vivo
}

TEST(rogue_waves_advance_on_duration_with_survivors) {
    RogueData d;
    ASSERT_TRUE(LoadWaves(d, "t,1,10,1,10,4,10,a:1,0,,,\nt,2,10,1,10,4,10,b:1,0,,,boss\n"));
    RogueWaves w(d);
    w.Start("t", 5);
    w.Tick(9.9);
    EXPECT_EQ(w.Wave(), 1);
    EXPECT_EQ(w.Alive(), 4);
    w.Tick(0.2);  // passou dos 10 s: onda 2 começa com os 4 da onda 1 ainda vivos
    EXPECT_EQ(w.Wave(), 2);
    EXPECT_TRUE(w.BossSpawned());
    EXPECT_TRUE(w.BossAlive());
    EXPECT_EQ(w.Alive(), 4 + 1 + 4);
    std::uint32_t bossId = 0;
    for (const RogueWaveSpawn& s : w.AliveList())
        if (s.boss) bossId = s.id;
    ASSERT_TRUE(bossId != 0u);
    EXPECT_FALSE(w.Complete());
    w.Killed(bossId);
    EXPECT_TRUE(w.Complete());  // o chefe morto fecha a fase mesmo com gente viva
}

TEST(rogue_waves_elites_and_costs) {
    RogueData d;
    ASSERT_TRUE(LoadWaves(d, "t,1,100,1,100,30,100,a:1|big:1:5,3,4,1.5,\n"));
    RogueWaves w(d);
    w.Start("t", 9);
    w.Tick(0.5);
    const std::vector<RogueWaveSpawn> s = Take(w);
    std::int64_t spent = 0;
    int elites = 0;
    for (const RogueWaveSpawn& x : s) {
        spent += x.enemy == "big" ? 5 : 1;
        if (x.elite) {
            ++elites;
            EXPECT_NEAR(x.hpMult, 4.0, 1e-12);
            EXPECT_NEAR(x.damageMult, 1.5, 1e-12);
        } else {
            EXPECT_NEAR(x.hpMult, 1.0, 1e-12);
        }
        EXPECT_TRUE(x.edge >= 0 && x.edge <= 3);
        EXPECT_TRUE(x.pos >= 0.0 && x.pos < 1.0);
    }
    EXPECT_EQ(spent, std::int64_t(30));  // orçamento exato: o custo 1 sempre fecha a conta
    EXPECT_EQ(elites, 3);
    EXPECT_TRUE(w.Exhausted());
}

TEST(rogue_waves_deterministic_split_and_seed) {
    auto run = [](const std::vector<double>& dts, std::uint64_t seed) {
        RogueWaves w(RealData());
        w.Start("cripta", seed);
        for (double dt : dts) w.Tick(dt);
        return w.StateHash();
    };
    const std::string one = run({30.0}, 42);
    EXPECT_EQ(one, run(std::vector<double>(60, 0.5), 42));
    EXPECT_EQ(one, run({10.0, 0.25, 9.75, 10.0}, 42));
    EXPECT_NE(one, run({30.0}, 43));
}

TEST(rogue_waves_restore_continues) {
    RogueWaves a(RealData());
    a.Start("cripta", 77);
    Bot ba;
    for (int i = 0; i < 400; ++i) ba.Step(a, 0.25);
    const std::string mid = a.StateJson();
    RogueWaves b(RealData());
    std::string err;
    ASSERT_TRUE(b.RestoreState(mid, &err));
    EXPECT_EQ(b.StateHash(), a.StateHash());
    Bot bb = ba;
    for (int i = 0; i < 400; ++i) {
        ba.Step(a, 0.25);
        bb.Step(b, 0.25);
    }
    EXPECT_EQ(a.StateHash(), b.StateHash());
    // Restore inválido não muda nada.
    const std::string before = b.StateHash();
    EXPECT_FALSE(b.RestoreState("{\"format\":1,\"phase\":\"cripta\",\"wave\":99}", &err));
    EXPECT_FALSE(b.RestoreState("nao e json", &err));
    EXPECT_EQ(b.StateHash(), before);
    // Estado vazio volta a "sem fase".
    RogueWaves idle(RealData());
    ASSERT_TRUE(b.RestoreState(idle.StateJson(), &err));
    EXPECT_FALSE(b.Running());
}
