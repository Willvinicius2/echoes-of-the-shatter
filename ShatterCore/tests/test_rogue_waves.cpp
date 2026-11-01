// Spawner de hordas do roguelike 2D (rogue_waves.h, API 1.11): leitura de ondas.csv, orçamento, teto de vivos, elites,
// chefe na última onda, passagem de onda, determinismo (1 ou N ticks, restore) com o ondas.csv real de godot/data2d.
#include <algorithm>
#include <filesystem>
#include <fstream>
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

const char* kHeader = "fase,onda,duracao,intervalo,lote,orcamento,teto,inimigos,elites,elite_vida,elite_dano\n";
const char* kPhaseHeader =
    "fase,prazo,raio_min,raio_max,chefe,despertar_onda,enxame_inimigos,enxame_orcamento,enxame_lote,enxame_intervalo,"
    "enxame_teto\n";

// Só ondas.csv e ondas_fases.csv (o spawner não lê as outras tabelas). Fase padrão "t": prazo 1000 s, sem chefe.
bool LoadWaves(RogueData& d, const std::string& rows,
               const std::string& phases = "t,1000,100,200,,1,s:1,10,10,1,10\n") {
    const bool a = d.LoadTableCsv("ondas.csv", std::string(kHeader) + rows);
    const bool b = d.LoadTableCsv("ondas_fases.csv", std::string(kPhaseHeader) + phases);
    return a && b;
}

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
    bool radiusOut = false;
    int elites = 0;
    int bosses = 0;
    int bossWave = 0;
    bool wake = true;                     // acorda o chefe assim que puder
    std::map<std::uint32_t, double> due;  // id -> instante da morte

    void Step(RogueWaves& w, double dt) {
        t += dt;
        if (wake && w.CheckWake() == RogueWaveResult::Ok) w.WakeBoss();
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
            if (s.radius < w.PhaseDef()->ringMin || s.radius > w.PhaseDef()->ringMax) radiusOut = true;
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
    const RogueWavePhaseDef* p = d.FindWavePhaseDef("cripta");
    ASSERT_TRUE(p != nullptr);
    EXPECT_EQ(p->boss, std::string("crypt_guardian"));
    EXPECT_NEAR(p->deadline, 480.0, 1e-9);  // ~8 min (plano 31)
    EXPECT_TRUE(p->ringMin > 0.0 && p->ringMax >= p->ringMin);
    EXPECT_TRUE(p->wakeWave >= 1 && p->wakeWave <= count);
    EXPECT_EQ(p->swarm.wave, count + 1);
    EXPECT_TRUE(p->swarm.cap <= 40);
    for (const RogueWaveDef& w : d.Waves()) {
        EXPECT_TRUE(w.cap <= 40);  // teto ~40 vivos do plano 31
        EXPECT_TRUE(w.minCost >= 1);
    }
    EXPECT_FALSE(d.FindWavePhase("nao_existe", first, count));
    EXPECT_TRUE(d.FindWavePhaseDef("nao_existe") == nullptr);
}

TEST(rogue_waves_csv_errors) {
    struct Case {
        const char* rows;
        const char* why;
    };
    const Case cases[] = {
        {"t,2,10,1,1,5,5,a:1,0,,\n", "onda must start at 1"},
        {"t,1,10,1,1,5,5,a:1,0,,\nt,3,10,1,1,5,5,a:1,0,,\n", "onda must count"},
        {"t,1,10,1,1,5,5,a:1,0,,\ng,1,10,1,1,5,5,a:1,0,,\nt,2,10,1,1,5,5,a:1,0,,\n", "fase split"},
        {"t,1,0,1,1,5,5,a:1,0,,\n", "duracao 0"},
        {"t,1,10,0,1,5,5,a:1,0,,\n", "intervalo 0"},
        {"t,1,10,1,0,5,5,a:1,0,,\n", "lote 0"},
        {"t,1,10,1,1,5,0,a:1,0,,\n", "teto 0"},
        {"t,1,10,1,1,5,5,a:0,0,,\n", "peso 0"},
        {"t,1,10,1,1,5,5,a:1|a:2,0,,\n", "id repetido"},
        {"t,1,10,1,1,5,5,a:1:0,0,,\n", "custo 0"},
        {"t,1,10,1,1,5,5,,0,,\n", "sem inimigos"},
        {"t,1,10,1,1,0,5,a:1,0,,\n", "orcamento 0"},
        {"t,1,10,1,1,5,5,a:1,0,0,\n", "elite_vida 0"},
        {",1,10,1,1,5,5,a:1,0,,\n", "fase vazia"},
    };
    for (const Case& c : cases) {
        RogueData d;
        if (LoadWaves(d, c.rows)) FAIL(std::string("accepted: ") + c.why);
    }
    const Case phaseCases[] = {
        {"t,0,100,200,,1,s:1,10,10,1,10\n", "prazo 0"},
        {"t,100,0,200,,1,s:1,10,10,1,10\n", "raio_min 0"},
        {"t,100,300,200,,1,s:1,10,10,1,10\n", "raio_max < raio_min"},
        {"t,100,100,200,,0,s:1,10,10,1,10\n", "despertar_onda 0"},
        {"t,100,100,200,,1,,10,10,1,10\n", "enxame sem inimigos"},
        {"t,100,100,200,,1,s:1,0,10,1,10\n", "enxame sem orcamento"},
        {"t,100,100,200,,1,s:1,10,10,0,10\n", "enxame_intervalo 0"},
        {"t,100,100,200,,1,s:1,10,10,1,10\nt,100,100,200,,1,s:1,10,10,1,10\n", "fase repetida"},
    };
    for (const Case& c : phaseCases) {
        RogueData d;
        if (LoadWaves(d, "t,1,10,1,1,5,5,a:1,0,,\n", c.rows)) FAIL(std::string("accepted: ") + c.why);
    }
    RogueData bad;
    EXPECT_FALSE(bad.LoadTableCsv("ondas.csv", "fase,onda\nf,1\n"));
    RogueData ok;
    EXPECT_TRUE(LoadWaves(ok, "t,1,10,1,1,5,5,a:1|b:2:3,1,2,1.5\nt,2,10,1,1,4,5,a:1,0,,\n"));
    ASSERT_EQ(ok.Waves().size(), std::size_t(2));
    EXPECT_EQ(ok.Waves()[0].mix[1].cost, 3);
    EXPECT_EQ(ok.Waves()[0].minCost, 1);
    EXPECT_EQ(ok.Waves()[0].durationUs, std::int64_t(10000000));
    EXPECT_NEAR(ok.Waves()[1].eliteHp, 1.0, 1e-12);
}

TEST(rogue_waves_finalize_cross_checks) {
    namespace fs = std::filesystem;
    const fs::path dir = fs::temp_directory_path() / "shatter_rogue_waves_cross";
    fs::remove_all(dir);
    fs::create_directories(dir);
    for (const auto& e : fs::directory_iterator(SHATTER_ROGUE_DATA_DIR))
        if (e.path().extension() == ".csv") fs::copy_file(e.path(), dir / e.path().filename());
    {
        std::ofstream f(dir / "ondas_fases.csv", std::ios::binary | std::ios::trunc);
        f << kPhaseHeader << "outra,100,100,200,,9,s:1,10,10,1,10\n";
    }
    RogueData d;
    d.LoadDirectory(dir.string());
    d.Finalize();
    EXPECT_FALSE(d.Ok());
    int missing = 0;
    for (const ContentError& e : d.Errors())
        missing += e.message.find("has no") != std::string::npos ? 1 : 0;
    EXPECT_EQ(missing, 2);  // cripta sem linha de fase e "outra" sem ondas
    fs::remove_all(dir);
}

TEST(rogue_waves_basic_results) {
    RogueWaves none;
    EXPECT_ENUM_EQ(none.Start("cripta", 1), RogueWaveResult::Unknown);
    RogueWaves w(RealData());
    EXPECT_ENUM_EQ(w.Killed(1), RogueWaveResult::NotRunning);
    EXPECT_ENUM_EQ(w.WakeBoss(), RogueWaveResult::NotRunning);
    EXPECT_ENUM_EQ(w.Start("nao_existe", 1), RogueWaveResult::Unknown);
    EXPECT_FALSE(w.Running());
    EXPECT_EQ(w.Tick(1.0), 0);
    ASSERT_TRUE(w.Start("cripta", 7) == RogueWaveResult::Ok);
    EXPECT_EQ(w.Wave(), 1);
    EXPECT_EQ(w.WavesTotal(), 8);
    EXPECT_ENUM_EQ(w.WakeBoss(), RogueWaveResult::TooEarly);  // despertar_onda 4
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

    RogueData d;
    ASSERT_TRUE(LoadWaves(d, "t,1,10,1,1,5,5,a:1,0,,\n"));
    RogueWaves nb(d);
    nb.Start("t", 1);
    EXPECT_ENUM_EQ(nb.WakeBoss(), RogueWaveResult::NoBoss);
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

TEST(rogue_waves_full_phase_waking_the_boss) {
    RogueWaves w(RealData());
    ASSERT_TRUE(w.Start("cripta", 1234) == RogueWaveResult::Ok);
    Bot bot;
    int guard = 0;
    while (!w.Complete() && guard++ < 20000) bot.Step(w, 0.25);
    ASSERT_TRUE(w.Complete());
    EXPECT_FALSE(w.Swarm());  // acordou e matou o chefe antes do prazo
    EXPECT_EQ(bot.bosses, 1);
    EXPECT_EQ(bot.bossWave, RealData().FindWavePhaseDef("cripta")->wakeWave);
    EXPECT_TRUE(bot.peakRegular <= 40);
    EXPECT_TRUE(bot.peakRegular >= 8);  // é horda de verdade
    EXPECT_FALSE(bot.radiusOut);
    EXPECT_TRUE(bot.elites >= 1);
    EXPECT_EQ(w.Tick(5.0), 0);  // completa: nada mais nasce
}

TEST(rogue_waves_deadline_brings_swarm_and_boss) {
    RogueWaves w(RealData());
    w.Start("cripta", 99);
    Bot bot;
    bot.wake = false;
    const RogueWavePhaseDef* p = RealData().FindWavePhaseDef("cripta");
    while (static_cast<double>(w.TimeUs()) < p->deadline * 1000000.0 - 300000.0) bot.Step(w, 0.25);
    EXPECT_FALSE(w.Swarm());
    EXPECT_FALSE(w.BossSpawned());
    bot.bossLife = 1e9;  // o chefe vai seguir vivo: o enxame gasta o orçamento e para
    int elitesBefore = 0;
    for (const RogueWaveDef& d : RealData().Waves()) elitesBefore += d.elites;
    EXPECT_TRUE(bot.elites >= elitesBefore);  // as 8 ondas passaram inteiras
    for (int i = 0; i < 4; ++i) bot.Step(w, 0.25);
    EXPECT_TRUE(w.Swarm());
    EXPECT_EQ(w.Wave(), 9);
    EXPECT_TRUE(w.BossSpawned());
    EXPECT_EQ(bot.bossWave, 9);
    EXPECT_ENUM_EQ(w.WakeBoss(), RogueWaveResult::AlreadyAwake);
    for (int i = 0; i < 800; ++i) bot.Step(w, 0.25);
    EXPECT_TRUE(w.Exhausted());
    EXPECT_FALSE(w.Complete());
    EXPECT_TRUE(bot.peakRegular <= 40);
    for (const RogueWaveSpawn& s : w.AliveList())
        if (s.boss) w.Killed(s.id);
    EXPECT_TRUE(w.Complete());
}

TEST(rogue_waves_last_wave_loops_until_deadline) {
    RogueData d;
    ASSERT_TRUE(LoadWaves(d, "t,1,5,1,10,3,10,a:1,0,,\n", "t,30,100,200,,1,s:1,2,10,1,10\n"));
    RogueWaves w(d);
    w.Start("t", 4);
    // Ninguém morre: a onda recomeça a cada 5 s (3, 6, 9 vivos) até o teto (10) segurar o orçamento da 4ª volta.
    for (int i = 0; i < 25; ++i) w.Tick(1.0);
    EXPECT_EQ(w.Loops(), 3);
    EXPECT_EQ(w.Wave(), 1);
    EXPECT_EQ(w.Alive(), 10);  // teto
    w.Tick(10.0);              // prazo (30 s): enxame
    EXPECT_TRUE(w.Swarm());
    EXPECT_EQ(w.Wave(), 2);
    for (const RogueWaveSpawn& s : std::vector<RogueWaveSpawn>(w.AliveList())) w.Killed(s.id);
    w.Tick(1.0);
    EXPECT_TRUE(w.Exhausted());
    for (const RogueWaveSpawn& s : std::vector<RogueWaveSpawn>(w.AliveList())) w.Killed(s.id);
    EXPECT_TRUE(w.Complete());  // sem chefe: enxame gasto e ninguém vivo
}

TEST(rogue_waves_advance_early_when_cleared) {
    RogueData d;
    ASSERT_TRUE(LoadWaves(d, "t,1,100,1,10,4,10,a:1,0,,\nt,2,100,1,10,4,10,b:1,0,,\n"));
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
}

TEST(rogue_waves_advance_on_duration_and_wake) {
    RogueData d;
    ASSERT_TRUE(LoadWaves(d, "t,1,10,1,10,4,10,a:1,0,,\nt,2,10,1,10,4,10,b:1,0,,\n",
                          "t,1000,100,200,boss,2,s:1,10,10,1,10\n"));
    RogueWaves w(d);
    w.Start("t", 5);
    w.Tick(9.9);
    EXPECT_EQ(w.Wave(), 1);
    EXPECT_EQ(w.Alive(), 4);
    EXPECT_ENUM_EQ(w.CheckWake(), RogueWaveResult::TooEarly);
    w.Tick(0.2);  // passou dos 10 s: onda 2 começa com os 4 da onda 1 ainda vivos
    EXPECT_EQ(w.Wave(), 2);
    EXPECT_EQ(w.Alive(), 8);
    EXPECT_FALSE(w.BossSpawned());
    ASSERT_TRUE(w.WakeBoss() == RogueWaveResult::Ok);
    EXPECT_TRUE(w.BossAlive());
    std::uint32_t bossId = 0;
    for (const RogueWaveSpawn& s : w.AliveList())
        if (s.boss) bossId = s.id;
    ASSERT_TRUE(bossId != 0u);
    EXPECT_FALSE(w.Complete());
    w.Killed(bossId);
    EXPECT_TRUE(w.Complete());  // o chefe morto fecha a fase mesmo com gente viva
    EXPECT_ENUM_EQ(w.WakeBoss(), RogueWaveResult::NotRunning);
}

TEST(rogue_waves_elites_costs_and_ring) {
    RogueData d;
    ASSERT_TRUE(LoadWaves(d, "t,1,100,1,100,30,100,a:1|big:1:5,3,4,1.5\n", "t,1000,700,900,,1,s:1,10,10,1,10\n"));
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
        EXPECT_TRUE(x.angle >= 0.0 && x.angle < 6.2831853072);
        EXPECT_TRUE(x.radius >= 700.0 && x.radius <= 900.0);
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
    // Passando pelo prazo (enxame): 10 x 50 s = 1000 x 0,5 s.
    EXPECT_EQ(run(std::vector<double>(10, 50.0), 42), run(std::vector<double>(1000, 0.5), 42));
}

TEST(rogue_waves_restore_continues) {
    for (int part = 0; part < 2; ++part) {
        RogueWaves a(RealData());
        a.Start("cripta", 77);
        Bot ba;
        ba.wake = part == 0;
        for (int i = 0; i < (part == 0 ? 400 : 1960); ++i) ba.Step(a, 0.25);  // part 1: perto do prazo
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
        if (part == 1) EXPECT_TRUE(b.Swarm());
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
}
