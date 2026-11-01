// Fronteira da API C de XP, nível, baú, curva, vida do chefe e modo horda (shatter_rogue_level_*, _horde_*, API 1.12),
// ligado à DLL/so com os CSV reais de godot/data2d.
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

json::Value Level(const shatter_rogue* r) {
    json::Value v;
    json::Parse(Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_rogue_level_json(r, o, c, n); }), v);
    return v;
}

}  // namespace

TEST(c_api_rogue_levels_null_args) {
    std::int32_t res = 0, lv = 0;
    std::int64_t xp = 0;
    std::uint8_t chest = 0;
    double hp = 0.0;
    EXPECT_EQ(shatter_rogue_horde_set(nullptr, 1, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_horde_win(nullptr, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_level_kill_xp(nullptr, "a", 1, 1.0, 0, &xp, &chest, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_level_gain_xp(nullptr, 1, &lv, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_level_open_chest(nullptr, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_level_choose(nullptr, "a", 1, 1.0, &hp, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_level_reroll(nullptr, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_level_skip(nullptr, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_level_ban(nullptr, "a", 1, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_boss_hp(nullptr, 1.0, 1.0, &hp), SHATTER_INVALID_ARGUMENT);
    Rogue g;
    ASSERT_TRUE(g.st == SHATTER_OK);
    EXPECT_EQ(shatter_rogue_level_kill_xp(g.r, nullptr, 0, 1.0, 0, &xp, &chest, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_level_gain_xp(g.r, 1, nullptr, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_boss_hp(g.r, 1.0, 1.0, nullptr), SHATTER_INVALID_ARGUMENT);
}

TEST(c_api_rogue_levels_flow) {
    Rogue g;
    ASSERT_TRUE(g.st == SHATTER_OK);
    std::int32_t res = -1, lv = 0;
    EXPECT_EQ(shatter_rogue_horde_set(g.r, 1, &res), SHATTER_OK);
    EXPECT_EQ(res, 0);
    const std::string base = "{\"hp_max\":100,\"arrow_damage\":10}";
    shatter_error err{};
    ASSERT_TRUE(shatter_rogue_run_start(g.r, 5, base.data(), base.size(), &err) == SHATTER_OK);
    json::Value l = Level(g.r);
    EXPECT_EQ(l["level"].AsInt(), std::int64_t(1));
    EXPECT_TRUE(l["horde"].AsBool(false));
    const std::int64_t need = l["xp_next"].AsInt();
    ASSERT_TRUE(need > 0);
    EXPECT_EQ(shatter_rogue_level_gain_xp(g.r, need, &lv, &res), SHATTER_OK);
    EXPECT_EQ(lv, 1);
    l = Level(g.r);
    EXPECT_EQ(l["kind"].AsString(), std::string("level"));
    ASSERT_TRUE(l["offer"].Size() > 0);
    const std::string pick = l["offer"].Items()[0].AsString();
    double hp = 0.0;
    EXPECT_EQ(shatter_rogue_level_choose(g.r, pick.data(), pick.size(), 50.0, &hp, &res), SHATTER_OK);
    EXPECT_EQ(res, 0);
    EXPECT_EQ(Level(g.r)["kind"].AsString(), std::string(""));
    std::int64_t xp = 0;
    std::uint8_t chest = 0;
    EXPECT_EQ(shatter_rogue_level_kill_xp(g.r, "chain_wraith", 12, 2.0, 1, &xp, &chest, &res), SHATTER_OK);
    EXPECT_TRUE(xp > 0);
    EXPECT_EQ(chest, 1);
    EXPECT_EQ(shatter_rogue_level_open_chest(g.r, &res), SHATTER_OK);
    EXPECT_EQ(Level(g.r)["kind"].AsString(), std::string("chest"));
    EXPECT_EQ(shatter_rogue_level_skip(g.r, &res), SHATTER_OK);
    EXPECT_EQ(res, 0);
    json::Value c;
    json::Parse(Out([&](std::uint8_t* o, std::size_t cap, std::size_t* n) { return shatter_rogue_curve_json(g.r, "cripta", 6, 1, o, cap, n); }), c);
    EXPECT_TRUE(c["hp"].AsDouble(0.0) > 0.0);
    double bhp = 0.0;
    EXPECT_EQ(shatter_rogue_boss_hp(g.r, 1000.0, 0.0, &bhp), SHATTER_OK);
    EXPECT_NEAR(bhp, 1000.0, 1e-9);
    EXPECT_EQ(shatter_rogue_horde_win(g.r, &res), SHATTER_OK);
    EXPECT_EQ(res, 0);
}
