// Fronteira da API C do roguelike 2D (shatter_rogue_*, API 1.8): argumentos nulos, BUFFER_TOO_SMALL sem efeito, meta,
// stats, corrida, save automático e determinismo pelo hash. Ligado à DLL/so como o test_c_api.cpp.
#include <cstring>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

#include "shatter/shatter_c.h"
#include "test_util.h"

using namespace shatter;

namespace {

std::string RogueDir() { return SHATTER_ROGUE_DATA_DIR; }

struct Rogue {
    shatter_rogue* r = nullptr;
    shatter_status st = SHATTER_INTERNAL;
    Rogue() {
        const std::string d = RogueDir();
        shatter_error err{};
        st = shatter_rogue_load_directory(d.data(), d.size(), &r, &err);
    }
    ~Rogue() { shatter_rogue_destroy(r); }
    Rogue(const Rogue&) = delete;
    Rogue& operator=(const Rogue&) = delete;
};

template <class F>
std::string Out(F call, shatter_status* final = nullptr) {
    std::size_t needed = 0;
    shatter_status st = call(nullptr, 0, &needed);
    if (st == SHATTER_BUFFER_TOO_SMALL) {
        std::vector<std::uint8_t> buf(needed);
        st = call(buf.data(), buf.size(), &needed);
        if (final) *final = st;
        return st == SHATTER_OK ? std::string(reinterpret_cast<const char*>(buf.data()), needed) : std::string();
    }
    if (final) *final = st;
    return std::string();
}

std::string Hash(const shatter_rogue* r) {
    return Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_rogue_state_hash(r, o, c, n); });
}
std::string RunJson(const shatter_rogue* r) {
    return Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_rogue_run_json(r, o, c, n); });
}

std::int32_t Phase(const shatter_rogue* r) {
    std::int32_t p = -1;
    shatter_rogue_run_phase(r, &p);
    return p;
}

const char* kBase = "{\"hp_max\":100,\"arrow_damage\":10,\"speed\":200}";

// Inimigos da sala atual na ordem, tirados do run_json (node.enemies).
std::vector<std::string> RoomEnemies(const shatter_rogue* r) {
    json::Value v;
    json::Parse(RunJson(r), v);
    std::vector<std::string> out;
    for (const json::Value& e : v["node"]["enemies"].Items())
        for (std::int64_t i = 0; i < e["count"].AsInt(0); ++i) out.push_back(e["id"].AsString());
    return out;
}

void Kill(shatter_rogue* r, const std::string& id, std::uint8_t* cleared = nullptr) {
    std::uint8_t c = 0;
    std::int32_t res = -1;
    EXPECT_EQ(shatter_rogue_run_enemy_killed(r, id.data(), id.size(), &c, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_RUN_OK));
    if (cleared) *cleared = c;
}

}  // namespace

TEST(c_api_rogue_load_and_null_arguments) {
    shatter_rogue* r = nullptr;
    shatter_error err{};
    EXPECT_EQ(shatter_rogue_load_directory(nullptr, 3, &r, &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_load_directory("x", 1, nullptr, &err), SHATTER_INVALID_ARGUMENT);
    const std::string missing = RogueDir() + "/nao_existe";
    EXPECT_EQ(shatter_rogue_load_directory(missing.data(), missing.size(), &r, &err), SHATTER_IO_ERROR);
    EXPECT_TRUE(r == nullptr);
    shatter_rogue_destroy(nullptr);

    Rogue g;
    ASSERT_EQ(g.st, SHATTER_OK);
    std::int32_t res = 0;
    std::int64_t i64 = 0;
    std::int32_t i32 = 0;
    std::uint8_t u8 = 0;
    double dbl = 0.0;
    std::size_t needed = 0;
    // rogue nulo
    EXPECT_EQ(shatter_rogue_setting(nullptr, "seed", 4, &dbl), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_save_path_set(nullptr, "a", 1), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_load(nullptr, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_save(nullptr, &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_save_json(nullptr, nullptr, 0, &needed), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_load_json(nullptr, "{}", 2, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_buy(nullptr, "meta_dano", 9, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_can_buy(nullptr, "meta_dano", 9, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_craft(nullptr, "amuleto_osso", 12, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_can_craft(nullptr, "amuleto_osso", 12, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_equip(nullptr, "amuleto_osso", 12, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_prepare_run(nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_credit(nullptr, "{}", 2, &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_fragments(nullptr, &i64), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_material(nullptr, "osso_antigo", 11, &i64), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_level(nullptr, "meta_dano", 9, &i32), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_stock(nullptr, "tonico_vida", 11, &i32), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_owns(nullptr, "tonico_vida", 11, &u8), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_unlocked(nullptr, "pierce", 6, &u8), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_json(nullptr, nullptr, 0, &needed), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_drop_json(nullptr, "crypt_bat", 9, nullptr, 0, &needed), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_stats_apply(nullptr, kBase, std::strlen(kBase), 0, nullptr, 0, &needed, &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_start(nullptr, 1, kBase, std::strlen(kBase), &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_phase(nullptr, &i32), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_paths_json(nullptr, 0, nullptr, 0, &needed), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_enemy_killed(nullptr, "crypt_bat", 9, &u8, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_choose_card(nullptr, "power", 5, 1.0, &dbl, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_rest(nullptr, 1.0, &dbl, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_door(nullptr, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_choose_path(nullptr, 0, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_player_died(nullptr, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_finish(nullptr, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_json(nullptr, nullptr, 0, &needed), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_stats_json(nullptr, nullptr, 0, &needed), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_summary_json(nullptr, nullptr, 0, &needed), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_state_json(nullptr, nullptr, 0, &needed), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_state_restore(nullptr, "{}", 2, &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_state_hash(nullptr, nullptr, 0, &needed), SHATTER_INVALID_ARGUMENT);
    // ponteiros de saída e texto nulos
    shatter_rogue* r2 = g.r;
    EXPECT_EQ(shatter_rogue_setting(r2, "seed", 4, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_buy(r2, nullptr, 9, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_buy(r2, "meta_dano", 9, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_craft(r2, nullptr, 0, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_fragments(r2, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_load(r2, &res), SHATTER_INVALID_ARGUMENT);  // sem caminho ligado
    EXPECT_EQ(shatter_rogue_meta_save(r2, &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_meta_credit(r2, nullptr, 0, &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_stats_apply(r2, nullptr, 0, 0, nullptr, 0, &needed, &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_stats_apply(r2, kBase, std::strlen(kBase), 0, nullptr, 0, nullptr, &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_start(r2, 1, nullptr, 0, &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_enemy_killed(r2, "crypt_bat", 9, nullptr, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_choose_card(r2, "power", 5, 1.0, nullptr, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_rest(r2, 1.0, &dbl, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_door(r2, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_json(r2, nullptr, 0, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_state_restore(r2, nullptr, 0, &err), SHATTER_INVALID_ARGUMENT);
    // UTF-8 inválido
    const char bad[] = {static_cast<char>(0xC3), 0};
    EXPECT_EQ(shatter_rogue_meta_buy(r2, bad, 1, &res), SHATTER_INVALID_ARGUMENT);
}

TEST(c_api_rogue_settings_meta_buy_craft_equip_and_queries) {
    Rogue g;
    ASSERT_EQ(g.st, SHATTER_OK);
    shatter_rogue* r = g.r;
    double v = 0.0;
    EXPECT_EQ(shatter_rogue_setting(r, "rest_heal", 9, &v), SHATTER_OK);
    EXPECT_NEAR(v, 0.5, 0.0);
    EXPECT_EQ(shatter_rogue_setting(r, "nada", 4, &v), SHATTER_NOT_FOUND);

    shatter_error err{};
    const std::string gains = "{\"fragmentos\":72,\"materiais\":{\"osso_antigo\":3,\"pedra_cinza\":1}}";
    EXPECT_EQ(shatter_rogue_meta_credit(r, gains.data(), gains.size(), &err), SHATTER_OK);
    std::int64_t frag = 0;
    EXPECT_EQ(shatter_rogue_meta_fragments(r, &frag), SHATTER_OK);
    EXPECT_EQ(frag, std::int64_t(72));
    const std::string unknownMat = "{\"materiais\":{\"ouro\":1}}";
    EXPECT_EQ(shatter_rogue_meta_credit(r, unknownMat.data(), unknownMat.size(), &err), SHATTER_NOT_FOUND);
    const std::string negative = "{\"fragmentos\":-1}";
    EXPECT_EQ(shatter_rogue_meta_credit(r, negative.data(), negative.size(), &err), SHATTER_PARSE_ERROR);
    EXPECT_EQ(shatter_rogue_meta_credit(r, "[", 1, &err), SHATTER_PARSE_ERROR);
    shatter_rogue_meta_fragments(r, &frag);
    EXPECT_EQ(frag, std::int64_t(72));  // nada mudou

    std::int32_t res = -1;
    EXPECT_EQ(shatter_rogue_meta_can_buy(r, "meta_dano", 9, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_META_OK));
    EXPECT_EQ(shatter_rogue_meta_buy(r, "meta_dano", 9, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_META_OK));
    EXPECT_EQ(shatter_rogue_meta_buy(r, "meta_dano", 9, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_META_NO_FRAGMENTS));
    EXPECT_EQ(shatter_rogue_meta_buy(r, "nada", 4, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_META_UNKNOWN));
    std::int32_t lvl = 0;
    EXPECT_EQ(shatter_rogue_meta_level(r, "meta_dano", 9, &lvl), SHATTER_OK);
    EXPECT_EQ(lvl, 1);
    EXPECT_EQ(shatter_rogue_meta_level(r, "nada", 4, &lvl), SHATTER_NOT_FOUND);

    EXPECT_EQ(shatter_rogue_meta_craft(r, "amuleto_osso", 12, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_META_OK));
    std::int64_t osso = -1;
    EXPECT_EQ(shatter_rogue_meta_material(r, "osso_antigo", 11, &osso), SHATTER_OK);
    EXPECT_EQ(osso, std::int64_t(0));
    EXPECT_EQ(shatter_rogue_meta_material(r, "ouro", 4, &osso), SHATTER_NOT_FOUND);
    std::uint8_t owns = 0;
    EXPECT_EQ(shatter_rogue_meta_owns(r, "amuleto_osso", 12, &owns), SHATTER_OK);
    EXPECT_EQ(owns, 1);
    std::int32_t stock = -1;
    EXPECT_EQ(shatter_rogue_meta_stock(r, "amuleto_osso", 12, &stock), SHATTER_OK);
    EXPECT_EQ(stock, 1);
    EXPECT_EQ(shatter_rogue_meta_stock(r, "tonico_vida", 11, &stock), SHATTER_OK);
    EXPECT_EQ(stock, 0);
    EXPECT_EQ(shatter_rogue_meta_can_craft(r, "tonico_vida", 11, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_META_NO_FRAGMENTS));  // fragmentos conferidos antes dos materiais
    EXPECT_EQ(shatter_rogue_meta_equip(r, "amuleto_pedra", 13, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_META_NOT_OWNED));
    std::uint8_t unlocked = 1;
    EXPECT_EQ(shatter_rogue_skill_unlocked(r, "pierce", 6, &unlocked), SHATTER_OK);
    EXPECT_EQ(unlocked, 0);
    EXPECT_EQ(shatter_rogue_skill_unlocked(r, "power", 5, &unlocked), SHATTER_OK);
    EXPECT_EQ(unlocked, 1);
    EXPECT_EQ(shatter_rogue_skill_unlocked(r, "nada", 4, &unlocked), SHATTER_NOT_FOUND);

    shatter_status st = SHATTER_INTERNAL;
    const std::string meta = Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_rogue_meta_json(r, o, c, n); }, &st);
    EXPECT_EQ(st, SHATTER_OK);
    json::Value mv;
    ASSERT_TRUE(json::Parse(meta, mv));
    EXPECT_EQ(mv["equipped"].AsString(), std::string("amuleto_osso"));
    EXPECT_EQ(mv["upgrades"].Size(), std::size_t(6));
    EXPECT_EQ(mv["recipes"].Size(), std::size_t(9));
    EXPECT_EQ(mv["recipes"].At(0)["cost"].At(0)["qty"].AsInt(0), std::int64_t(3));
    const std::string drop = Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_rogue_drop_json(r, "crypt_guardian", 14, o, c, n);
    });
    EXPECT_EQ(drop, std::string("{\"enemy\":\"crypt_guardian\",\"fragments\":40,\"material\":\"nucleo_estilhaco\",\"material_qty\":1}"));

    // Stats: amuleto_osso (x1,05) e meta_dano (x1,1) sobre arrow_damage 10.
    const std::string stats = Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_rogue_stats_apply(r, kBase, std::strlen(kBase), 1, o, c, n, &err);
    });
    json::Value sv;
    ASSERT_TRUE(json::Parse(stats, sv));
    EXPECT_NEAR(sv["arrow_damage"].AsDouble(0.0), 10.0 * 1.05 * 1.1, 1e-12);
    EXPECT_NEAR(sv["hp_max"].AsDouble(0.0), 100.0, 0.0);
    EXPECT_EQ(sv.Members().front().first, std::string("hp_max"));  // ordem da entrada
    std::size_t needed = 0;
    const std::string notNum = "{\"hp_max\":\"cem\"}";
    EXPECT_EQ(shatter_rogue_stats_apply(r, notNum.data(), notNum.size(), 0, nullptr, 0, &needed, &err), SHATTER_PARSE_ERROR);
}

TEST(c_api_rogue_run_flow_cards_rest_victory_and_summary) {
    Rogue g;
    ASSERT_EQ(g.st, SHATTER_OK);
    shatter_rogue* r = g.r;
    shatter_error err{};
    std::int32_t res = -1;
    EXPECT_EQ(Phase(r), static_cast<std::int32_t>(SHATTER_ROGUE_PHASE_NONE));
    EXPECT_EQ(shatter_rogue_run_door(r, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_DOOR_NOT_READY));
    std::size_t needed = 0;
    EXPECT_EQ(shatter_rogue_run_paths_json(r, 4, nullptr, 0, &needed), SHATTER_NOT_FOUND);
    json::Value paths;
    ASSERT_TRUE(json::Parse(Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_rogue_run_paths_json(r, 1, o, c, n); }), paths));
    ASSERT_EQ(paths.Size(), std::size_t(2));
    EXPECT_EQ(paths.At(1)["kind"].AsString(), std::string("elite"));

    EXPECT_EQ(shatter_rogue_run_start(r, 42, kBase, std::strlen(kBase), &err), SHATTER_OK);
    EXPECT_EQ(Phase(r), static_cast<std::int32_t>(SHATTER_ROGUE_PHASE_FIGHT));
    // BUFFER_TOO_SMALL não muda nada.
    const std::string h0 = Hash(r);
    std::uint8_t tiny[4];
    EXPECT_EQ(shatter_rogue_run_json(r, tiny, sizeof(tiny), &needed), SHATTER_BUFFER_TOO_SMALL);
    EXPECT_TRUE(needed > sizeof(tiny));
    EXPECT_EQ(Hash(r), h0);

    // Etapa 1: limpa e escolhe uma carta.
    std::uint8_t cleared = 0;
    for (const std::string& e : RoomEnemies(r)) Kill(r, e, &cleared);
    EXPECT_EQ(cleared, 1);
    EXPECT_EQ(Phase(r), static_cast<std::int32_t>(SHATTER_ROGUE_PHASE_CHOICE));
    json::Value run;
    ASSERT_TRUE(json::Parse(RunJson(r), run));
    ASSERT_EQ(run["offer"].Size(), std::size_t(3));
    EXPECT_EQ(run["gains"]["fragments"].AsInt(0), std::int64_t(14));
    double hp = 0.0;
    EXPECT_EQ(shatter_rogue_run_choose_card(r, "pierce", 6, 50.0, &hp, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_RUN_NOT_OFFERED));
    const std::string card = run["offer"].At(0).AsString();
    EXPECT_EQ(shatter_rogue_run_choose_card(r, card.data(), card.size(), 50.0, &hp, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_RUN_OK));
    // Etapa 2: bifurcação, entra na elite.
    EXPECT_EQ(shatter_rogue_run_door(r, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_DOOR_ROUTE));
    ASSERT_TRUE(json::Parse(RunJson(r), run));
    EXPECT_EQ(run["route_options"].Size(), std::size_t(2));
    EXPECT_EQ(shatter_rogue_run_choose_path(r, 1, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_RUN_OK));
    for (const std::string& e : RoomEnemies(r)) Kill(r, e);
    ASSERT_TRUE(json::Parse(RunJson(r), run));
    EXPECT_EQ(run["offer"].Size(), std::size_t(4));
    const std::string card2 = run["offer"].At(0).AsString();
    shatter_rogue_run_choose_card(r, card2.data(), card2.size(), 50.0, &hp, &res);
    // Etapa 3: descanso.
    shatter_rogue_run_door(r, &res);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_DOOR_ROUTE));
    shatter_rogue_run_choose_path(r, 1, &res);
    EXPECT_EQ(Phase(r), static_cast<std::int32_t>(SHATTER_ROGUE_PHASE_CLEARED));
    json::Value rs;
    ASSERT_TRUE(json::Parse(Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_rogue_run_stats_json(r, o, c, n); }), rs));
    const double maxHp = rs["hp_max"].AsDouble(0.0);
    EXPECT_EQ(shatter_rogue_run_rest(r, 20.0, &hp, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_RUN_OK));
    EXPECT_NEAR(hp, 20.0 + maxHp * 0.5, 1e-12);
    // Etapa 4: chefe, sem cartas, porta = vitória.
    shatter_rogue_run_door(r, &res);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_DOOR_ENTERED));
    Kill(r, "crypt_guardian", &cleared);
    EXPECT_EQ(cleared, 1);
    EXPECT_EQ(Phase(r), static_cast<std::int32_t>(SHATTER_ROGUE_PHASE_CLEARED));
    shatter_rogue_run_door(r, &res);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_DOOR_VICTORY));
    json::Value sum;
    ASSERT_TRUE(json::Parse(Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_rogue_run_summary_json(r, o, c, n); }), sum));
    EXPECT_TRUE(sum["victory"].AsBool(false));
    EXPECT_EQ(sum["stage_reached"].AsInt(0), std::int64_t(4));
    EXPECT_EQ(sum["upgrades_total"].AsInt(0), std::int64_t(2));
    const std::int64_t total = sum["fragments"].AsInt(0);
    EXPECT_EQ(shatter_rogue_run_player_died(r, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_RUN_WRONG_PHASE));
    EXPECT_EQ(shatter_rogue_run_finish(r, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_RUN_OK));
    std::int64_t frag = 0;
    shatter_rogue_meta_fragments(r, &frag);
    EXPECT_EQ(frag, total);
    EXPECT_EQ(shatter_rogue_run_finish(r, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_RUN_WRONG_PHASE));
}

TEST(c_api_rogue_autosave_load_and_corrupt_file) {
    const std::string dir = tu::TmpDir("c_api_rogue_save");
    const std::string path = dir + "/save_2d.json";
    {
        Rogue g;
        ASSERT_EQ(g.st, SHATTER_OK);
        EXPECT_EQ(shatter_rogue_save_path_set(g.r, path.data(), path.size()), SHATTER_OK);
        std::int32_t res = -1;
        EXPECT_EQ(shatter_rogue_meta_load(g.r, &res), SHATTER_OK);
        EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_LOAD_MISSING));
        shatter_error err{};
        const std::string gains = "{\"fragmentos\":100}";
        EXPECT_EQ(shatter_rogue_meta_credit(g.r, gains.data(), gains.size(), &err), SHATTER_OK);  // grava sozinho
        EXPECT_EQ(shatter_rogue_meta_buy(g.r, "unlock_pierce", 13, &res), SHATTER_OK);
        EXPECT_TRUE(std::filesystem::exists(std::filesystem::u8path(path)));
        const std::string text = Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_rogue_meta_save_json(g.r, o, c, n); });
        EXPECT_EQ(tu::ReadFile(path), text);
        // Corrida abandonada: run_start credita e grava.
        EXPECT_EQ(shatter_rogue_run_start(g.r, 1, kBase, std::strlen(kBase), &err), SHATTER_OK);
        Kill(g.r, "hollow_sentinel");
        EXPECT_EQ(shatter_rogue_run_start(g.r, 2, kBase, std::strlen(kBase), &err), SHATTER_OK);
    }
    {
        Rogue g;
        shatter_rogue_save_path_set(g.r, path.data(), path.size());
        std::int32_t res = -1;
        EXPECT_EQ(shatter_rogue_meta_load(g.r, &res), SHATTER_OK);
        EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_LOAD_OK));
        std::int64_t frag = 0;
        shatter_rogue_meta_fragments(g.r, &frag);
        EXPECT_EQ(frag, std::int64_t(100 - 56 + 3));
        std::uint8_t u = 0;
        shatter_rogue_skill_unlocked(g.r, "pierce", 6, &u);
        EXPECT_EQ(u, 1);
        shatter_error err{};
        EXPECT_EQ(shatter_rogue_meta_save(g.r, &err), SHATTER_OK);
    }
    {
        // Save corrompido: estado zerado, sem crash.
        std::ofstream(std::filesystem::u8path(path), std::ios::binary | std::ios::trunc) << "{\"versao\":1,\"fragm";
        Rogue g;
        shatter_rogue_save_path_set(g.r, path.data(), path.size());
        std::int32_t res = -1;
        EXPECT_EQ(shatter_rogue_meta_load(g.r, &res), SHATTER_OK);
        EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_LOAD_BAD_JSON));
        std::int64_t frag = -1;
        shatter_rogue_meta_fragments(g.r, &frag);
        EXPECT_EQ(frag, std::int64_t(0));
        const std::string v2 = "{\"versao\":2,\"fragmentos\":5}";
        EXPECT_EQ(shatter_rogue_meta_load_json(g.r, v2.data(), v2.size(), &res), SHATTER_OK);
        EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_LOAD_BAD_VERSION));
    }
    {
        // Caminho que não dá para gravar: a ação vale na memória e a função avisa com IO_ERROR.
        Rogue g;
        const std::string blocked = dir + "/save_2d.json/dentro.json";  // um arquivo no lugar da pasta
        shatter_rogue_save_path_set(g.r, blocked.data(), blocked.size());
        shatter_error err{};
        const std::string gains = "{\"fragmentos\":1}";
        EXPECT_EQ(shatter_rogue_meta_credit(g.r, gains.data(), gains.size(), &err), SHATTER_IO_ERROR);
        std::int64_t frag = 0;
        shatter_rogue_meta_fragments(g.r, &frag);
        EXPECT_EQ(frag, std::int64_t(1));
    }
}

TEST(c_api_rogue_same_seed_same_hash_and_state_restore) {
    auto play = [](shatter_rogue* r, std::uint64_t seed) {
        shatter_error err{};
        std::int32_t res = -1;
        shatter_rogue_run_start(r, seed, kBase, std::strlen(kBase), &err);
        for (const std::string& e : RoomEnemies(r)) Kill(r, e);
        json::Value run;
        json::Parse(RunJson(r), run);
        const std::string card = run["offer"].At(1).AsString();
        double hp = 0.0;
        shatter_rogue_run_choose_card(r, card.data(), card.size(), 50.0, &hp, &res);
        shatter_rogue_run_door(r, &res);
    };
    Rogue a, b, c;
    play(a.r, 77);
    play(b.r, 77);
    play(c.r, 78);
    EXPECT_EQ(Hash(a.r), Hash(b.r));
    EXPECT_EQ(Hash(a.r).size(), std::size_t(64));
    // Restaura o estado de A em C: hashes iguais e as próximas ações dão o mesmo resultado.
    const std::string state = Out([&](std::uint8_t* o, std::size_t n, std::size_t* nd) { return shatter_rogue_state_json(a.r, o, n, nd); });
    shatter_error err{};
    EXPECT_EQ(shatter_rogue_state_restore(c.r, state.data(), state.size(), &err), SHATTER_OK);
    EXPECT_EQ(Hash(c.r), Hash(a.r));
    std::int32_t res = -1;
    shatter_rogue_run_choose_path(a.r, 1, &res);
    shatter_rogue_run_choose_path(c.r, 1, &res);
    for (const std::string& e : RoomEnemies(a.r)) Kill(a.r, e);
    for (const std::string& e : RoomEnemies(c.r)) Kill(c.r, e);
    EXPECT_EQ(Hash(c.r), Hash(a.r));
    const std::string before = Hash(c.r);
    EXPECT_EQ(shatter_rogue_state_restore(c.r, "{\"format\":9}", 12, &err), SHATTER_PARSE_ERROR);
    EXPECT_EQ(Hash(c.r), before);
}
