// Fronteira da API C do spawner de hordas (shatter_rogue_wave_*, API 1.11): argumentos nulos, fase desconhecida, fila
// entregue uma vez (BUFFER_TOO_SMALL não esvazia), mortes, estado, defs e determinismo pelo hash, ligado à DLL/so.
#include <string>
#include <vector>

#include "shatter/json.h"
#include "shatter/shatter_c.h"
#include "test_util.h"

using namespace shatter;

namespace {

struct Rogue {
    shatter_rogue* r = nullptr;
    shatter_status st = SHATTER_INTERNAL;
    Rogue() {
        const std::string d = SHATTER_ROGUE_DATA_DIR;
        shatter_error err{};
        st = shatter_rogue_load_directory(d.data(), d.size(), &r, &err);
    }
    ~Rogue() { shatter_rogue_destroy(r); }
    Rogue(const Rogue&) = delete;
    Rogue& operator=(const Rogue&) = delete;
};

template <class F>
std::string Out(F call) {
    std::size_t needed = 0;
    shatter_status st = call(nullptr, 0, &needed);
    if (st != SHATTER_BUFFER_TOO_SMALL) return std::string();
    std::vector<std::uint8_t> buf(needed);
    st = call(buf.data(), buf.size(), &needed);
    return st == SHATTER_OK ? std::string(reinterpret_cast<const char*>(buf.data()), needed) : std::string();
}

json::Value Parse(const std::string& s) {
    json::Value v;
    json::Parse(s, v);
    return v;
}

json::Value Take(shatter_rogue* r) {
    return Parse(Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_rogue_wave_take_json(r, o, c, n); }));
}
json::Value State(const shatter_rogue* r) {
    return Parse(Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_rogue_wave_json(r, o, c, n); }));
}
std::string Hash(const shatter_rogue* r) {
    return Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_rogue_wave_state_hash(r, o, c, n); });
}

// Joga a fase com um bot (cada inimigo morre 2 s depois de nascer) por `seconds`.
void Play(shatter_rogue* r, double seconds) {
    std::vector<std::pair<std::uint32_t, double>> due;
    double t = 0.0;
    while (t < seconds) {
        t += 0.25;
        for (std::size_t i = 0; i < due.size();) {
            if (due[i].second <= t) {
                std::uint8_t complete = 0;
                std::int32_t res = -1;
                shatter_rogue_wave_killed(r, due[i].first, &complete, &res);
                due.erase(due.begin() + static_cast<std::ptrdiff_t>(i));
            } else {
                ++i;
            }
        }
        std::uint32_t n = 0;
        shatter_rogue_wave_tick(r, 0.25, &n);
        const json::Value born = Take(r);
        for (const json::Value& s : born.Items())
            due.emplace_back(static_cast<std::uint32_t>(s["id"].AsInt(0)), t + 2.0);
    }
}

}  // namespace

TEST(c_api_rogue_wave_arguments) {
    Rogue g;
    ASSERT_EQ(g.st, SHATTER_OK);
    std::int32_t res = -1;
    std::uint32_t n = 0;
    std::uint8_t complete = 0;
    std::size_t needed = 0;
    EXPECT_EQ(shatter_rogue_wave_start(nullptr, "cripta", 6, 1, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_wave_start(g.r, nullptr, 0, 1, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_wave_start(g.r, "cripta", 6, 1, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_wave_stop(nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_wave_tick(nullptr, 1.0, &n), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_wave_tick(g.r, 1.0, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_wave_take_json(nullptr, nullptr, 0, &needed), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_wave_killed(g.r, 1, nullptr, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_wave_json(g.r, nullptr, 0, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_wave_state_restore(g.r, nullptr, 0, nullptr), SHATTER_INVALID_ARGUMENT);
    // Sem fase: kill dá NOT_RUNNING, tick não solta nada.
    EXPECT_EQ(shatter_rogue_wave_killed(g.r, 1, &complete, &res), SHATTER_OK);
    EXPECT_EQ(res, SHATTER_ROGUE_WAVE_NOT_RUNNING);
    EXPECT_EQ(shatter_rogue_wave_tick(g.r, 1.0, &n), SHATTER_OK);
    EXPECT_EQ(n, 0u);
    EXPECT_EQ(shatter_rogue_wave_start(g.r, "nada", 4, 1, &res), SHATTER_OK);
    EXPECT_EQ(res, SHATTER_ROGUE_WAVE_UNKNOWN);
    EXPECT_FALSE(State(g.r)["running"].AsBool(true));
}

TEST(c_api_rogue_wave_queue_and_kill) {
    Rogue g;
    std::int32_t res = -1;
    std::uint32_t n = 0;
    ASSERT_EQ(shatter_rogue_wave_start(g.r, "cripta", 6, 99, &res), SHATTER_OK);
    ASSERT_EQ(res, SHATTER_ROGUE_WAVE_OK);
    ASSERT_EQ(shatter_rogue_wave_tick(g.r, 0.1, &n), SHATTER_OK);
    EXPECT_TRUE(n > 0u);
    // Buffer pequeno não esvazia a fila.
    std::uint8_t tiny[4];
    std::size_t needed = 0;
    EXPECT_EQ(shatter_rogue_wave_take_json(g.r, tiny, sizeof tiny, &needed), SHATTER_BUFFER_TOO_SMALL);
    const json::Value spawns = Take(g.r);
    ASSERT_EQ(spawns.Size(), static_cast<std::size_t>(n));
    EXPECT_EQ(Take(g.r).Size(), std::size_t(0));  // entregue uma vez só
    const json::Value& s0 = spawns.At(0);
    EXPECT_EQ(s0["id"].AsInt(0), 1);
    EXPECT_EQ(s0["wave"].AsInt(0), 1);
    EXPECT_FALSE(s0["enemy"].AsString().empty());
    EXPECT_TRUE(s0["angle"].IsNumber());
    EXPECT_TRUE(s0["radius"].AsDouble(0.0) > 0.0);
    json::Value st = State(g.r);
    EXPECT_EQ(st["phase"].AsString(), std::string("cripta"));
    EXPECT_EQ(st["alive"].AsInt(-1), static_cast<std::int64_t>(n));
    EXPECT_EQ(st["waves_total"].AsInt(0), 8);
    EXPECT_EQ(st["cap"].AsInt(0), 18);  // teto da onda 1 (ondas.csv, calibrado no H4)
    EXPECT_NEAR(st["deadline"].AsDouble(0.0), 480.0, 1e-9);
    EXPECT_FALSE(st["swarm"].AsBool(true));
    EXPECT_EQ(st["can_wake"].AsInt(-1), SHATTER_ROGUE_WAVE_TOO_EARLY);
    EXPECT_EQ(shatter_rogue_wave_wake_boss(g.r, &res), SHATTER_OK);
    EXPECT_EQ(res, SHATTER_ROGUE_WAVE_TOO_EARLY);
    EXPECT_EQ(shatter_rogue_wave_wake_boss(g.r, nullptr), SHATTER_INVALID_ARGUMENT);
    std::uint8_t complete = 9;
    EXPECT_EQ(shatter_rogue_wave_killed(g.r, 1, &complete, &res), SHATTER_OK);
    EXPECT_EQ(res, SHATTER_ROGUE_WAVE_OK);
    EXPECT_EQ(complete, 0);
    EXPECT_EQ(shatter_rogue_wave_killed(g.r, 1, &complete, &res), SHATTER_OK);
    EXPECT_EQ(res, SHATTER_ROGUE_WAVE_NOT_ALIVE);
    EXPECT_EQ(State(g.r)["killed"].AsInt(0), 1);
    EXPECT_EQ(shatter_rogue_wave_stop(g.r), SHATTER_OK);
    EXPECT_EQ(State(g.r)["alive"].AsInt(-1), 0);
}

TEST(c_api_rogue_wave_defs) {
    Rogue g;
    const json::Value d =
        Parse(Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_rogue_wave_defs_json(g.r, o, c, n); }));
    ASSERT_EQ(d["phases"].Size(), std::size_t(1));
    const json::Value& ph = d["phases"].At(0);
    EXPECT_EQ(ph["id"].AsString(), std::string("cripta"));
    ASSERT_EQ(ph["waves"].Size(), std::size_t(8));
    EXPECT_EQ(ph["boss"].AsString(), std::string("crypt_guardian"));
    EXPECT_EQ(ph["swarm"]["wave"].AsInt(0), 9);
    EXPECT_TRUE(ph["ring_max"].AsDouble(0.0) >= ph["ring_min"].AsDouble(1.0));
    EXPECT_TRUE(ph["waves"].At(0)["enemies"].Size() > 0);
}

TEST(c_api_rogue_wave_determinism_and_restore) {
    Rogue a, b, c;
    std::int32_t res = -1;
    shatter_rogue_wave_start(a.r, "cripta", 6, 2024, &res);
    shatter_rogue_wave_start(b.r, "cripta", 6, 2024, &res);
    Play(a.r, 90.0);
    Play(b.r, 90.0);
    EXPECT_EQ(Hash(a.r), Hash(b.r));
    EXPECT_EQ(Hash(a.r).size(), std::size_t(64));
    // Restore em outro handle continua do mesmo ponto.
    const std::string mid =
        Out([&](std::uint8_t* o, std::size_t cap, std::size_t* n) { return shatter_rogue_wave_state_json(a.r, o, cap, n); });
    shatter_error err{};
    ASSERT_EQ(shatter_rogue_wave_state_restore(c.r, mid.data(), mid.size(), &err), SHATTER_OK);
    EXPECT_EQ(Hash(c.r), Hash(a.r));
    std::uint32_t n1 = 0, n2 = 0;
    shatter_rogue_wave_tick(a.r, 3.0, &n1);
    shatter_rogue_wave_tick(c.r, 3.0, &n2);
    EXPECT_EQ(n1, n2);
    EXPECT_EQ(Hash(c.r), Hash(a.r));
    const std::string before = Hash(c.r);
    EXPECT_EQ(shatter_rogue_wave_state_restore(c.r, "{}", 2, &err), SHATTER_PARSE_ERROR);
    EXPECT_EQ(Hash(c.r), before);
}
