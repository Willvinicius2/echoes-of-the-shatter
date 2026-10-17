// Revisão do core da Etapa 2 (docs/17_revisao_core_etapa2.md): reproduções de achados na API C 1.1.
//
// Ligação: o CMake põe tests/*.cpp em shattercore_tests, que liga só a biblioteca estática (sem a API C; só
// test_c_api.cpp vai para o executável ligado à DLL). Para não mexer no CMakeLists.txt, este arquivo compila a própria
// implementação da API C nesta unidade. SHATTER_C_STATIC evita o dllimport no MSVC. ATENÇÃO: só UM arquivo de
// shattercore_tests pode fazer este #include (senão as funções shatter_* ficam definidas duas vezes no link): junte
// aqui todo teste novo da API C.
//
// Cada teste afirma o comportamento CORRETO e falha no master atual. Ficam DESLIGADOS por padrão (saem cedo e passam)
// e só rodam com SHATTER_REVISAO_BUGS=1, no mesmo padrão de SHATTER_BALANCE_PROBE:
//   SHATTER_REVISAO_BUGS=1 shattercore_tests revisao_
// O nome de cada teste traz o ID do achado no docs/17. Quando o achado for corrigido, apague a guarda do teste.
// Os testes com "UB" no nome dependem de comportamento indefinido (o UBSan acusa e, no Clang, aborta; o ASan aborta
// no B8, que derruba até o Release): rodam só com SHATTER_REVISAO_UB=1, um de cada vez (shattercore_tests <nome>).
#define SHATTER_C_STATIC
#include "../src/c_api/shatter_c.cpp"

#include <cstring>
#include <limits>
#include <sstream>
#include <string>

#include "test_util.h"

namespace revisao_api_c {

using namespace shatter;

bool BugsOn() { return !tu::GetEnv("SHATTER_REVISAO_BUGS").empty(); }
// Variável própria para os testes de UB: SHATTER_REVISAO_BUGS=1 roda os demais até o fim sem abortar.
bool UbOn() { return !tu::GetEnv("SHATTER_REVISAO_UB").empty(); }

struct Db {
    shatter_db* db = nullptr;
    Db() {
        const std::string dir = tu::RichDir();
        shatter_error err{};
        shatter_db_load_directory(dir.data(), dir.size(), &db, &err);
    }
    ~Db() { shatter_db_destroy(db); }
    Db(const Db&) = delete;
    Db& operator=(const Db&) = delete;
};

struct Save {
    shatter_save* save = nullptr;
    Save() = default;
    ~Save() { shatter_save_destroy(save); }
    Save(const Save&) = delete;
    Save& operator=(const Save&) = delete;
};

constexpr std::int64_t kLastSeen = 1'700'000'000;

// Save com o Guerreiro do fixture rico (Cripta dominada), 12 cargas e last_seen = kLastSeen.
SaveData BaseSave() {
    SaveData s;
    s.contentVersion = tu::RichDb().ContentVersion();
    s.characters.push_back(tu::MakeWarrior(tu::RichDb(), 3));
    s.markerCharges = 12;
    s.lastSeenUtc = kLastSeen;
    return s;
}

bool LoadSave(const SaveData& s, Save& out) {
    const std::string text = SerializeJson(s, false);
    std::int32_t load = -1;
    shatter_error err{};
    return shatter_save_from_json(text.data(), text.size(), &out.save, &load, &err) == SHATTER_OK;
}

std::string StartParams(int hours) {
    std::ostringstream os;
    os << R"({"character_index":0,"map_id":"map.act1.crypt","objective":"xp","rules":[)"
       << R"({"condition":"always","param":0,"action":"use_skill","ref_id":"skill.warrior.iron_cut"}],)"
       << R"("duration_hours":)" << hours << "}";
    return os.str();
}

shatter_rules Rules(const shatter_db* db) {
    shatter_rules r{};
    shatter_db_rules(db, &r);
    return r;
}

// Espelho C# de shatter_rules_ext com dodge_duration e dodge_iframes trocados (mesmo tamanho; ordem errada).
struct RulesExtTrocado {
    double dodge_recharge, dodge_iframes, dodge_duration, dodge_distance, dodge_cost_resource, dodge_buffer;
    double dodge_perfect_resource, dodge_cancel_recovery_fraction;
    double guard_break_stagger_seconds, guard_break_stagger_damage_taken;
    double guard_break_immunity_boss, guard_break_immunity_other, boss_shield_down_seconds;
    double elite_life_mult, elite_damage_mult, elite_xp_mult;
    double potion_lockout, out_of_combat_seconds;
    std::int32_t dodge_max_charges;
    std::int32_t reserved;
};

}  // namespace revisao_api_c

using namespace revisao_api_c;

// ---------------------------------------------------------------------------------------------
// A2 — o início "confiável" usa o agora do chamador e ignora o rollback (shatter_c.cpp:2873-2875). O relógio do PC
// voltou 7 dias, sem hora da Steam: shatter_clock_resolve_now devolve rollback_detected = 1 e o início grava start_utc
// 7 dias no passado. Com o relógio corrigido, 60 s depois, a coleta confiável entrega a expedição de 4 h inteira
// (contorna o RF-48). Esperado: o início recusa (ou usa max(now, last_seen)) e a coleta 60 s depois diz NOT_FINISHED.
// ---------------------------------------------------------------------------------------------
TEST(revisao_A2_inicio_confiavel_aceita_relogio_atrasado_e_coleta_na_hora) {
    if (!BugsOn()) return;  // DESLIGADO: A2
    Db db;
    ASSERT_TRUE(db.db != nullptr);
    Save save;
    ASSERT_TRUE(LoadSave(BaseSave(), save));
    const shatter_rules rules = Rules(db.db);

    shatter_clock_input atrasado{};
    atrasado.local_now_utc = kLastSeen - 7 * 86400;
    atrasado.last_seen_utc = kLastSeen;
    shatter_trusted_now now{};
    ASSERT_EQ(shatter_clock_resolve_now(&atrasado, &rules, &now), SHATTER_OK);
    EXPECT_EQ(now.rollback_detected, 1);

    const std::string params = StartParams(4);
    std::int32_t check = -1;
    shatter_error err{};
    const shatter_status st =
        shatter_save_start_expedition_trusted(db.db, save.save, params.data(), params.size(), &now, &check, &err);
    if (st != SHATTER_OK || check != SHATTER_START_OK) return;  // recusou o início: comportamento correto

    shatter_clock_input agora{};
    agora.local_now_utc = kLastSeen + 60;  // relógio corrigido, 1 minuto depois do último ponto visto
    std::int32_t collect = -1;
    std::size_t needed = 0;
    EXPECT_EQ(shatter_save_collect_expedition_trusted(db.db, save.save, 0, &agora, 0, &collect, nullptr, 0, &needed, &err),
              SHATTER_OK);
    EXPECT_EQ(collect, SHATTER_COLLECT_NOT_FINISHED);  // hoje: BUFFER_TOO_SMALL com a expedição pronta (needed > 0)
    EXPECT_EQ(needed, static_cast<std::size_t>(0));
}

// ---------------------------------------------------------------------------------------------
// M1 — boss_progress duplicado no save: a leitura pega a ÚLTIMA entrada do chefe (shatter_c.cpp:2790-2795 e
// 2818-2820) e a gravação vai para a PRIMEIRA (FindOrAddBossProgress, progress.h:27-35). O contador lido nunca muda:
// com [{0,0},{10,3}] kills fica em 10 e a garantia (pity 5) nunca dispara; com [{5,..},{0,..}] a 1ª vitória é
// garantida em TODA vitória.
// ---------------------------------------------------------------------------------------------
TEST(revisao_M1_boss_progress_duplicado_congela_o_contador) {
    if (!BugsOn()) return;  // DESLIGADO: M1
    CharacterState c = tu::MakeWarrior(tu::RichDb(), 3);
    c.bossProgress = {{"enemy.crypt_guardian", 0, 0}, {"enemy.crypt_guardian", 10, 3}};
    SaveData s;
    s.characters.push_back(c);
    Save save;
    ASSERT_TRUE(LoadSave(s, save));
    Db db;
    ASSERT_TRUE(db.db != nullptr);
    const std::string id = "enemy.crypt_guardian";
    shatter_rng rng{};
    ASSERT_EQ(shatter_rng_for_stream(12345, SHATTER_RNG_LOOT, 0, &rng), SHATTER_OK);
    std::vector<std::uint8_t> buf(1 << 16);
    for (int i = 0; i < 6; ++i) {
        std::size_t needed = 0;
        ASSERT_EQ(shatter_save_roll_boss_loot(db.db, save.save, 0, id.data(), id.size(), 3, &rng, buf.data(), buf.size(),
                                              &needed, nullptr),
                  SHATTER_OK);
    }
    shatter_boss_progress p{};
    ASSERT_EQ(shatter_save_boss_progress_get(save.save, 0, id.data(), id.size(), &p), SHATTER_OK);
    EXPECT_EQ(p.kills, 16);  // 10 + 6 vitórias; hoje fica em 10 (lê a última entrada, grava na primeira)
}

// ---------------------------------------------------------------------------------------------
// M2 — expedição guardada no save sem validação.
// (a) start_utc extremo: ComputeExpeditionWindow faz ref − startUtc em int64 (clock.h:66) → estouro com sinal (UB).
//     Em Release (GCC 13) o tempo decorrido dá a volta para negativo e a coleta responde NOT_FINISHED para sempre.
// (b) character_index inexistente (save.cpp:381): CollectExpedition devolve false e a API responde COLLECT_ALREADY
//     (shatter_c.cpp:2920-2921), mas a expedição fica Running para sempre e bloqueia novos inícios.
// ---------------------------------------------------------------------------------------------
TEST(revisao_M2_start_utc_extremo_no_save_estoura_a_janela_UB) {
    if (!UbOn()) return;  // DESLIGADO: M2 (UB: o UBSan acusa clock.h:66)
    Db db;
    ASSERT_TRUE(db.db != nullptr);
    SaveData s = BaseSave();
    SavedExpedition e;
    e.status = ExpeditionStatus::Running;
    e.characterIndex = 0;
    e.request = tu::MakeRequest(tu::RichDb(), 1, 777, 3);
    e.request.startUtc = std::numeric_limits<std::int64_t>::min() + 1;
    s.expeditions.push_back(e);
    Save save;
    if (!LoadSave(s, save)) return;  // recusou na leitura: comportamento correto
    shatter_clock_input clock{};
    clock.local_now_utc = kLastSeen + 60;
    std::int32_t collect = -1;
    std::size_t needed = 0;
    shatter_error err{};
    EXPECT_EQ(shatter_save_collect_expedition_trusted(db.db, save.save, 0, &clock, 0, &collect, nullptr, 0, &needed, &err),
              SHATTER_BUFFER_TOO_SMALL);  // terminada: pede buffer para o resultado
    EXPECT_TRUE(collect != SHATTER_COLLECT_NOT_FINISHED);
}

TEST(revisao_M2_coleta_diz_already_com_expedicao_ainda_running) {
    if (!BugsOn()) return;  // DESLIGADO: M2
    Db db;
    ASSERT_TRUE(db.db != nullptr);
    SaveData s = BaseSave();
    SavedExpedition e;
    e.status = ExpeditionStatus::Running;
    e.characterIndex = 5;  // não existe
    e.request = tu::MakeRequest(tu::RichDb(), 1, 777, 3);
    e.request.startUtc = kLastSeen - 2 * 3600;
    s.expeditions.push_back(e);
    Save save;
    if (!LoadSave(s, save)) return;  // recusou na leitura: comportamento correto
    shatter_clock_input clock{};
    clock.local_now_utc = kLastSeen + 60;
    std::int32_t collect = -1;
    std::size_t needed = 0;
    shatter_error err{};
    std::vector<std::uint8_t> buf(1 << 20);
    const shatter_status st = shatter_save_collect_expedition_trusted(db.db, save.save, 0, &clock, 0, &collect, buf.data(),
                                                                      buf.size(), &needed, &err);
    shatter_save_summary sum{};
    ASSERT_EQ(shatter_save_summary_get(save.save, &sum), SHATTER_OK);
    if (st == SHATTER_OK && collect == SHATTER_COLLECT_ALREADY) {
        EXPECT_EQ(sum.running_expedition, -1);  // hoje: 0 (continua Running) — "já coletada" é falso
    }
}

// ---------------------------------------------------------------------------------------------
// M6 — o layout 1.1 confere poucos campos (shatter_c.cpp:256-278), como o M-08 do docs/11. Um espelho C# de
// shatter_rules_ext com dodge_duration e dodge_iframes trocados tem o mesmo tamanho e os mesmos offsets dos 3 campos
// conferidos: shatter_layout_check_ext aceita e o jogo usa a duração da esquiva como janela de invulnerabilidade.
// ---------------------------------------------------------------------------------------------
TEST(revisao_M6_layout_ext_aceita_campos_trocados) {
    if (!BugsOn()) return;  // DESLIGADO: M6
    std::uint32_t values[SHATTER_LAYOUT_EXT_COUNT];
    std::size_t needed = 0;
    ASSERT_EQ(shatter_layout_info_ext(values, SHATTER_LAYOUT_EXT_COUNT, &needed), SHATTER_OK);
    // O que o C# monta para shatter_rules_ext (as 4 primeiras entradas da lista), a partir do espelho errado.
    values[0] = static_cast<std::uint32_t>(sizeof(RulesExtTrocado));
    values[1] = static_cast<std::uint32_t>(offsetof(RulesExtTrocado, guard_break_stagger_seconds));
    values[2] = static_cast<std::uint32_t>(offsetof(RulesExtTrocado, potion_lockout));
    values[3] = static_cast<std::uint32_t>(offsetof(RulesExtTrocado, dodge_max_charges));
    shatter_error err{};
    EXPECT_EQ(shatter_layout_check_ext(values, SHATTER_LAYOUT_EXT_COUNT, &err), SHATTER_VERSION_MISMATCH);  // hoje: OK
}

// ---------------------------------------------------------------------------------------------
// B7 — shatter_elite_apply não é idempotente (combat.cpp:476, shatter_c.cpp:2640-2648): aplicar de novo no mesmo bloco
// (reinício no checkpoint com bloco reaproveitado, docs/13 R2.4) multiplica a vida outra vez.
// ---------------------------------------------------------------------------------------------
TEST(revisao_B7_elite_apply_duas_vezes_multiplica_de_novo) {
    if (!BugsOn()) return;  // DESLIGADO: B7
    Db db;
    ASSERT_TRUE(db.db != nullptr);
    const std::string enemy = "enemy.hollow_sentinel";
    shatter_statblock* sb = nullptr;
    ASSERT_EQ(shatter_statblock_for_enemy(db.db, enemy.data(), enemy.size(), 3, &sb), SHATTER_OK);
    double baseLife = 0.0;
    ASSERT_EQ(shatter_statblock_get(sb, SHATTER_STAT_LIFE, 0, &baseLife), SHATTER_OK);
    shatter_elite_info info{};
    ASSERT_EQ(shatter_elite_profile(db.db, nullptr, 0, 1, &info), SHATTER_OK);  // elite sorteado sem modificador
    double barrier = 0.0;
    ASSERT_EQ(shatter_elite_apply(db.db, &info, sb, &barrier), SHATTER_OK);
    double once = 0.0;
    shatter_statblock_get(sb, SHATTER_STAT_LIFE, 0, &once);
    ASSERT_EQ(shatter_elite_apply(db.db, &info, sb, &barrier), SHATTER_OK);
    double twice = 0.0;
    shatter_statblock_get(sb, SHATTER_STAT_LIFE, 0, &twice);
    EXPECT_NEAR(once, baseLife * info.life_mult, 1e-9);
    EXPECT_NEAR(twice, once, 1e-9);  // hoje: baseLife × life_mult²
    shatter_statblock_destroy(sb);
}

// ---------------------------------------------------------------------------------------------
// B8 — shatter_boss depende do shatter_db sem dono (shatter_c.cpp:41-46, combat.h:316-319): o vínculo está só no
// comentário do header. Destruir o banco antes do chefe deixa db_, boss_, phases_ e patterns_ pendurados. Sob ASan:
// heap-use-after-free em BossFight::PickAndStart; em Release, falha de segmentação ou lixo.
// ---------------------------------------------------------------------------------------------
TEST(revisao_B8_boss_depois_do_db_destruido_usa_memoria_liberada_UB) {
    if (!UbOn()) return;  // DESLIGADO: B8 (UB: sob ASan aborta com heap-use-after-free)
    shatter_db* db = nullptr;
    {
        const std::string dir = tu::RichDir();
        shatter_error err{};
        ASSERT_EQ(shatter_db_load_directory(dir.data(), dir.size(), &db, &err), SHATTER_OK);
    }
    const std::string boss = "enemy.crypt_guardian";
    shatter_boss* b = nullptr;
    ASSERT_EQ(shatter_boss_create(db, boss.data(), boss.size(), 5, 7, &b), SHATTER_OK);
    shatter_statblock* sb = nullptr;
    ASSERT_EQ(shatter_statblock_for_enemy(db, boss.data(), boss.size(), 5, &sb), SHATTER_OK);
    ASSERT_EQ(shatter_boss_start(b), SHATTER_OK);
    shatter_db_destroy(db);  // ordem errada: o chefe ainda vive
    shatter_boss_context ctx{};
    ctx.player.x = 100.0;
    std::size_t n = 0;
    for (int i = 0; i < 200; ++i) shatter_boss_step(b, 0.1, &ctx, sb, &n);  // usa db_ e phases_ liberados
    shatter_boss_destroy(b);
    shatter_statblock_destroy(sb);
}
