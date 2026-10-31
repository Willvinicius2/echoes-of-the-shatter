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

TEST(c_api_rogue_external_cards_mode_no_offer_no_draw_and_state) {
    Rogue g, ref;
    ASSERT_EQ(g.st, SHATTER_OK);
    ASSERT_EQ(ref.st, SHATTER_OK);
    shatter_rogue* r = g.r;
    shatter_error err{};
    std::int32_t res = -1;
    std::uint8_t on = 9;
    EXPECT_TRUE(shatter_api_minor() >= 9u);
    EXPECT_EQ(shatter_rogue_run_external_cards_set(nullptr, 1, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_external_cards_set(r, 1, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_external_cards_get(nullptr, &on), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_external_cards_get(r, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_run_external_cards_get(r, &on), SHATTER_OK);
    EXPECT_EQ(on, 0);
    const std::string hOff = Hash(r);
    EXPECT_EQ(shatter_rogue_run_external_cards_set(r, 1, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_RUN_OK));
    EXPECT_EQ(shatter_rogue_run_external_cards_get(r, &on), SHATTER_OK);
    EXPECT_EQ(on, 1);
    EXPECT_NE(Hash(r), hOff);  // o modo entra no hash

    EXPECT_EQ(shatter_rogue_run_start(r, 42, kBase, std::strlen(kBase), &err), SHATTER_OK);
    EXPECT_EQ(shatter_rogue_run_start(ref.r, 42, kBase, std::strlen(kBase), &err), SHATTER_OK);
    EXPECT_EQ(shatter_rogue_run_external_cards_set(r, 0, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_RUN_WRONG_PHASE));  // corrida viva: não muda
    // Sala limpa: CLEARED sem oferta; escolher carta é WRONG_PHASE.
    std::uint8_t cleared = 0;
    for (const std::string& e : RoomEnemies(r)) Kill(r, e, &cleared);
    for (const std::string& e : RoomEnemies(ref.r)) Kill(ref.r, e);
    EXPECT_EQ(cleared, 1);
    EXPECT_EQ(Phase(r), static_cast<std::int32_t>(SHATTER_ROGUE_PHASE_CLEARED));
    EXPECT_EQ(Phase(ref.r), static_cast<std::int32_t>(SHATTER_ROGUE_PHASE_CHOICE));
    json::Value run, runRef;
    ASSERT_TRUE(json::Parse(RunJson(r), run));
    ASSERT_TRUE(json::Parse(RunJson(ref.r), runRef));
    EXPECT_EQ(run["offer"].Size(), std::size_t(0));
    EXPECT_TRUE(run["external_cards"].AsBool(false));
    EXPECT_FALSE(runRef["external_cards"].AsBool(true));
    EXPECT_EQ(run["gains"]["fragments"].AsInt(0), runRef["gains"]["fragments"].AsInt(-1));
    const std::string card = runRef["offer"].At(0).AsString();
    double hp = 0.0;
    EXPECT_EQ(shatter_rogue_run_choose_card(r, card.data(), card.size(), 50.0, &hp, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_RUN_WRONG_PHASE));
    EXPECT_NEAR(hp, 50.0, 1e-12);
    // Nenhum sorteio consumido: o estado guarda draws 0 (na referência, 1).
    json::Value st;
    ASSERT_TRUE(json::Parse(Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_rogue_state_json(r, o, c, n); }), st));
    EXPECT_EQ(st["run"]["draws"].AsUInt64(99), std::uint64_t(0));
    EXPECT_TRUE(st["external_cards"].AsBool(false));
    // Stats da corrida = base + meta (stats_apply sem corrida).
    const std::string base = kBase;
    EXPECT_EQ(Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_rogue_run_stats_json(r, o, c, n); }),
              Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
                  return shatter_rogue_stats_apply(r, base.data(), base.size(), 0, o, c, n, &err);
              }));
    // Porta segue o fluxo normal (bifurcação).
    EXPECT_EQ(shatter_rogue_run_door(r, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_DOOR_ROUTE));

    // Estado ida e volta em outro objeto: modo e hash voltam juntos.
    const std::string state = Out([&](std::uint8_t* o, std::size_t n, std::size_t* nd) { return shatter_rogue_state_json(r, o, n, nd); });
    Rogue c;
    ASSERT_EQ(c.st, SHATTER_OK);
    EXPECT_EQ(shatter_rogue_state_restore(c.r, state.data(), state.size(), &err), SHATTER_OK);
    EXPECT_EQ(Hash(c.r), Hash(r));
    EXPECT_EQ(shatter_rogue_run_external_cards_get(c.r, &on), SHATTER_OK);
    EXPECT_EQ(on, 1);
    shatter_rogue_run_choose_path(r, 1, &res);
    shatter_rogue_run_choose_path(c.r, 1, &res);
    for (const std::string& e : RoomEnemies(r)) Kill(r, e);
    for (const std::string& e : RoomEnemies(c.r)) Kill(c.r, e);
    EXPECT_EQ(Phase(c.r), static_cast<std::int32_t>(SHATTER_ROGUE_PHASE_CLEARED));  // elite também sem cartas
    EXPECT_EQ(Hash(c.r), Hash(r));
    // Morte libera a troca; finish não zera o modo.
    EXPECT_EQ(shatter_rogue_run_player_died(r, &res), SHATTER_OK);
    EXPECT_EQ(shatter_rogue_run_external_cards_set(r, 1, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_RUN_OK));
    EXPECT_EQ(shatter_rogue_run_finish(r, &res), SHATTER_OK);
    EXPECT_EQ(shatter_rogue_run_external_cards_get(r, &on), SHATTER_OK);
    EXPECT_EQ(on, 1);
}

// --- API 1.10: habilidades por classe ---------------------------------------------------------------------------
namespace {

void WriteText(const std::string& path, const std::string& text) {
    std::ofstream out(std::filesystem::u8path(path), std::ios::binary);
    out << text;
}

// Cópia de godot/data2d com classes_2d.csv (a fixture do PR 127 e a árvore real do Guerreiro) e os pontos do run_settings.
std::string SkillDir() {
    static std::string dir;
    if (!dir.empty()) return dir;
    dir = tu::TmpDir("c_api_rogue_skills_data");
    for (const char* t : {"meta.csv", "receitas.csv", "drops.csv", "rota.csv", "run.csv", "upgrades.csv",
                          "habilidades_guerreiro.csv"})
        WriteText(dir + "/" + t, tu::ReadFile(RogueDir() + "/" + t));
    std::string settings = tu::ReadFile(RogueDir() + "/run_settings.csv");
    if (settings.find("skill_points_room") == std::string::npos) {
        if (!settings.empty() && settings.back() != '\n') settings += "\n";
        settings += "skill_points_room,1,pontos,teste\nskill_points_boss,3,pontos,teste\n";
    }
    WriteText(dir + "/run_settings.csv", settings);
    WriteText(dir + "/habilidades_teste.csv",
              "id,ramo,tipo,tier,pai,pontos,nivel_max,efeito,cd,custo,dano,qtd,angulo,raio,duracao,alcance,valor,escala,stat,modo,icone\n"
              "t_golpe,fogo,ativa,1,,1,3,golpe,2,10,20,1,0,0,0,300,0,0.5,,,tiro\n"
              "t_nova,fogo,ativa,2,t_golpe,2,2,nova,5,30,40,0,0,120,0,0,0,0.5,,,tiro\n"
              "t_vigor,vida,passiva,1,,1,3,,0,0,0,0,0,0,0,0,0.2,0,hp_max,mult,\n"
              "t_passo,vida,passiva,2,t_vigor,1,2,,0,0,0,0,0,0,0,0,10,0,speed,add,\n");
    WriteText(dir + "/classes_2d.csv",
              "id,nome,sprite,habilidades,efeitos\n"
              "teste,class.teste,arqueiro,res://data2d/habilidades_teste.csv,\n"
              "guerreiro,class.guerreiro,guerreiro,res://data2d/habilidades_guerreiro.csv,\n");
    return dir;
}

struct SkillRogue {
    shatter_rogue* r = nullptr;
    shatter_status st = SHATTER_INTERNAL;
    SkillRogue() {
        const std::string d = SkillDir();
        shatter_error err{};
        st = shatter_rogue_load_directory(d.data(), d.size(), &r, &err);
    }
    ~SkillRogue() { shatter_rogue_destroy(r); }
    SkillRogue(const SkillRogue&) = delete;
    SkillRogue& operator=(const SkillRogue&) = delete;
};

json::Value SkillsJson(const shatter_rogue* r) {
    json::Value v;
    json::Parse(Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_rogue_skills_json(r, o, c, n); }), v);
    return v;
}

std::int32_t Learn(shatter_rogue* r, const char* id) {
    std::int32_t res = -1;
    EXPECT_EQ(shatter_rogue_skill_learn(r, id, std::strlen(id), &res), SHATTER_OK);
    return res;
}

}  // namespace

TEST(c_api_rogue_skills_null_arguments_and_no_classes) {
    SkillRogue g;
    ASSERT_EQ(g.st, SHATTER_OK);
    shatter_rogue* r = g.r;
    std::int32_t res = -1;
    double dbl = 0.0;
    std::size_t needed = 0;
    EXPECT_EQ(shatter_rogue_class_set(nullptr, "teste", 5, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_class_set(r, nullptr, 5, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_class_set(r, "teste", 5, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_class_set(r, "\xff", 1, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skills_json(nullptr, nullptr, 0, &needed), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skills_json(r, nullptr, 0, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_def_json(nullptr, "t_golpe", 7, 1, nullptr, 0, &needed), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_def_json(r, nullptr, 7, 1, nullptr, 0, &needed), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_def_json(r, "t_golpe", 7, 1, nullptr, 0, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_can_learn(nullptr, "t_golpe", 7, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_can_learn(r, "t_golpe", 7, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_learn(nullptr, "t_golpe", 7, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_learn(r, nullptr, 7, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_equip(nullptr, 0, "t_golpe", 7, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_equip(r, 0, nullptr, 7, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_equip(r, 0, "t_golpe", 7, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_respec(nullptr, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_respec(r, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_points_add(nullptr, 1, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_points_add(r, 1, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_tick(nullptr, 1.0), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_can_use(nullptr, 0, 1.0, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_can_use(r, 0, 1.0, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_commit_use(nullptr, 0, 1.0, &dbl, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_commit_use(r, 0, 1.0, nullptr, &res), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_commit_use(r, 0, 1.0, &dbl, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_cooldown(nullptr, 0, &dbl), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rogue_skill_cooldown(r, 0, nullptr), SHATTER_INVALID_ARGUMENT);

    // Dados de hoje (sem classes_2d.csv): sem classe, NO_CLASS e o save sem as chaves novas.
    Rogue plain;
    ASSERT_EQ(plain.st, SHATTER_OK);
    const json::Value v = SkillsJson(plain.r);
    if (v["classes"].Size() == 0) {
        EXPECT_EQ(v["class"].AsString(), std::string());
        EXPECT_EQ(Learn(plain.r, "t_golpe"), static_cast<std::int32_t>(SHATTER_ROGUE_SKILL_NO_CLASS));
        EXPECT_EQ(shatter_rogue_skill_can_use(plain.r, 0, 99.0, &res), SHATTER_OK);
        EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_SKILL_NO_CLASS));
        const std::string save = Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
            return shatter_rogue_meta_save_json(plain.r, o, c, n);
        });
        EXPECT_TRUE(save.find("habilidades") == std::string::npos && save.find("classe") == std::string::npos);
    }
}

TEST(c_api_rogue_skills_tree_slots_use_and_save) {
    SkillRogue g;
    ASSERT_EQ(g.st, SHATTER_OK);
    shatter_rogue* r = g.r;
    const std::string dir = tu::TmpDir("c_api_rogue_skills_save");
    const std::string path = dir + "/save_2d.json";
    std::filesystem::remove(std::filesystem::u8path(path));
    ASSERT_EQ(shatter_rogue_save_path_set(r, path.data(), path.size()), SHATTER_OK);
    std::int32_t res = -1;

    json::Value v = SkillsJson(r);
    EXPECT_EQ(v["class"].AsString(), std::string("teste"));
    EXPECT_EQ(v["classes"].Size(), std::size_t(2));
    EXPECT_EQ(v["slots"].Size(), std::size_t(4));
    EXPECT_EQ(v["skills"].Size(), std::size_t(4));
    EXPECT_EQ(Learn(r, "t_golpe"), static_cast<std::int32_t>(SHATTER_ROGUE_SKILL_NO_POINTS));
    EXPECT_FALSE(std::filesystem::exists(std::filesystem::u8path(path)));  // ação recusada não grava
    ASSERT_EQ(shatter_rogue_skill_points_add(r, 5, &res), SHATTER_OK);
    EXPECT_TRUE(std::filesystem::exists(std::filesystem::u8path(path)));
    EXPECT_EQ(shatter_rogue_skill_can_learn(r, "t_nova", 6, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_SKILL_LOCKED));
    EXPECT_EQ(Learn(r, "t_golpe"), static_cast<std::int32_t>(SHATTER_ROGUE_SKILL_OK));
    EXPECT_EQ(Learn(r, "t_golpe"), static_cast<std::int32_t>(SHATTER_ROGUE_SKILL_OK));
    EXPECT_EQ(Learn(r, "t_vigor"), static_cast<std::int32_t>(SHATTER_ROGUE_SKILL_OK));
    v = SkillsJson(r);
    EXPECT_EQ(v["points"].AsInt(-1), std::int64_t(2));
    EXPECT_EQ(v["slots"].At(0).AsString(), std::string("t_golpe"));
    EXPECT_EQ(v["skills"].At(0)["level"].AsInt(-1), std::int64_t(2));
    EXPECT_EQ(v["skills"].At(1)["can_learn"].AsInt(-1), std::int64_t(SHATTER_ROGUE_SKILL_OK));
    EXPECT_TRUE(tu::ReadFile(path).find("\"t_golpe\":2") != std::string::npos);

    // Definição escalonada (nível 2: 1 + 0.5 = 1.5x), BUFFER_TOO_SMALL e desconhecida.
    std::size_t needed = 0;
    std::uint8_t tiny[4] = {0, 0, 0, 0};
    EXPECT_EQ(shatter_rogue_skill_def_json(r, "t_golpe", 7, -1, tiny, sizeof tiny, &needed), SHATTER_BUFFER_TOO_SMALL);
    EXPECT_TRUE(needed > sizeof tiny);
    EXPECT_EQ(shatter_rogue_skill_def_json(r, "nada", 4, 1, nullptr, 0, &needed), SHATTER_NOT_FOUND);
    json::Value def;
    json::Parse(Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
                    return shatter_rogue_skill_def_json(r, "t_golpe", 7, -1, o, c, n);
                }),
                def);
    EXPECT_NEAR(def["dano"].AsDouble(0.0), 30.0, 1e-12);
    EXPECT_EQ(def["efeito"].AsString(), std::string("golpe"));
    EXPECT_EQ(def["nivel"].AsInt(-1), std::int64_t(2));

    // Passivas nos stats (include_run, sem corrida) e na corrida.
    shatter_error err{};
    json::Value st;
    json::Parse(Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
                    return shatter_rogue_stats_apply(r, kBase, std::strlen(kBase), 1, o, c, n, &err);
                }),
                st);
    EXPECT_NEAR(st["hp_max"].AsDouble(0.0), 120.0, 1e-9);
    ASSERT_EQ(shatter_rogue_run_start(r, 5, kBase, std::strlen(kBase), &err), SHATTER_OK);
    json::Parse(Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_rogue_run_stats_json(r, o, c, n); }), st);
    EXPECT_NEAR(st["hp_max"].AsDouble(0.0), 120.0, 1e-9);
    EXPECT_EQ(shatter_rogue_class_set(r, "guerreiro", 9, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_SKILL_WRONG_PHASE));

    // Uso: mana, recarga e fração da HUD.
    double cost = -1.0, frac = -1.0;
    EXPECT_EQ(shatter_rogue_skill_can_use(r, 0, 9.0, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_SKILL_NO_MANA));
    EXPECT_EQ(shatter_rogue_skill_commit_use(r, 0, 50.0, &cost, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_SKILL_OK));
    EXPECT_NEAR(cost, 10.0, 1e-12);
    EXPECT_EQ(shatter_rogue_skill_cooldown(r, 0, &frac), SHATTER_OK);
    EXPECT_NEAR(frac, 1.0, 1e-12);
    EXPECT_EQ(shatter_rogue_skill_tick(r, 0.5), SHATTER_OK);
    shatter_rogue_skill_cooldown(r, 0, &frac);
    EXPECT_NEAR(frac, 0.75, 1e-12);
    EXPECT_EQ(shatter_rogue_skill_can_use(r, 0, 50.0, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_SKILL_COOLDOWN));
    EXPECT_EQ(shatter_rogue_skill_can_use(r, 7, 50.0, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_SKILL_BAD_SLOT));

    // Estado com recarga: ida e volta com o mesmo hash.
    const std::string state = Out([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_rogue_state_json(r, o, c, n); });
    SkillRogue other;
    ASSERT_EQ(shatter_rogue_state_restore(other.r, state.data(), state.size(), &err), SHATTER_OK);
    EXPECT_EQ(Hash(other.r), Hash(r));

    // Sala limpa dá pontos e grava; equipar e redistribuir também gravam.
    for (const std::string& e : RoomEnemies(r)) Kill(r, e);
    EXPECT_EQ(SkillsJson(r)["points"].AsInt(-1), std::int64_t(3));
    EXPECT_TRUE(tu::ReadFile(path).find("\"pontos\":3") != std::string::npos);
    EXPECT_EQ(shatter_rogue_skill_equip(r, 2, "t_golpe", 7, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_SKILL_OK));
    EXPECT_EQ(shatter_rogue_skill_equip(r, 9, "t_golpe", 7, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_SKILL_BAD_SLOT));
    EXPECT_TRUE(tu::ReadFile(path).find("\"slots\":[\"\",\"\",\"t_golpe\",\"\"]") != std::string::npos);
    EXPECT_EQ(shatter_rogue_skill_respec(r, &res), SHATTER_OK);
    EXPECT_EQ(SkillsJson(r)["points"].AsInt(-1), std::int64_t(6));
    EXPECT_TRUE(tu::ReadFile(path).find("\"pontos\":6") != std::string::npos);

    // Recarrega o save num núcleo novo.
    SkillRogue back;
    ASSERT_EQ(shatter_rogue_save_path_set(back.r, path.data(), path.size()), SHATTER_OK);
    ASSERT_EQ(shatter_rogue_meta_load(back.r, &res), SHATTER_OK);
    EXPECT_EQ(res, static_cast<std::int32_t>(SHATTER_ROGUE_LOAD_OK));
    EXPECT_EQ(SkillsJson(back.r)["points"].AsInt(-1), std::int64_t(6));
}
