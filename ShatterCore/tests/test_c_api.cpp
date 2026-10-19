// Fronteira da API C (docs/tecnico/04_arquitetura.md, seções 9.2 e 9.7): versão e layout, argumento nulo,
// BUFFER_TOO_SMALL sem efeito colateral, ida e volta de cada grupo de funções e o MESMO resultado do C++
// (golpe, expedição, golden). Este executável é ligado à DLL/so shattercore.
#include <cmath>
#include <cstring>
#include <filesystem>
#include <functional>
#include <sstream>

#include "shatter/shatter_c.h"
#include "test_util.h"

using namespace shatter;

namespace {

// Chamada com buffer do chamador no padrão de duas chamadas: a 1ª com cap 0 tem de devolver
// BUFFER_TOO_SMALL (ou OK se a saída for vazia) e informar `needed`; a 2ª usa exatamente `needed`.
using BufferCall = std::function<shatter_status(std::uint8_t*, std::size_t, std::size_t*)>;

std::string TwoCalls(const BufferCall& call, shatter_status* final = nullptr) {
    std::size_t needed = 0;
    shatter_status st = call(nullptr, 0, &needed);
    if (st == SHATTER_OK && needed == 0) {
        if (final) *final = st;
        return std::string();
    }
    if (st != SHATTER_BUFFER_TOO_SMALL) {
        if (final) *final = st;
        return std::string();
    }
    std::vector<std::uint8_t> buf(needed);
    std::size_t needed2 = 0;
    st = call(buf.data(), buf.size(), &needed2);
    if (final) *final = st;
    if (st != SHATTER_OK || needed2 != needed) return std::string();
    return std::string(reinterpret_cast<const char*>(buf.data()), buf.size());
}

struct DbHandle {
    shatter_db* db = nullptr;
    explicit DbHandle(const std::string& dir) {
        shatter_error err{};
        shatter_db_load_directory(dir.data(), dir.size(), &db, &err);
    }
    ~DbHandle() { shatter_db_destroy(db); }
    DbHandle(const DbHandle&) = delete;
    DbHandle& operator=(const DbHandle&) = delete;
};

struct SaveHandle {
    shatter_save* save = nullptr;
    SaveHandle() = default;
    ~SaveHandle() { shatter_save_destroy(save); }
    SaveHandle(SaveHandle&& o) noexcept : save(o.save) { o.save = nullptr; }
    SaveHandle(const SaveHandle&) = delete;
    SaveHandle& operator=(const SaveHandle&) = delete;
    SaveHandle& operator=(SaveHandle&&) = delete;
};

json::Value Parse(const std::string& text) {
    json::Value v;
    if (!json::Parse(text, v)) FAIL("JSON invalido vindo da API C: " + text.substr(0, 200));
    return v;
}

std::string S(const json::Value& v) { return json::Serialize(v, false); }

// Save do core com o Guerreiro do fixture rico (Cripta dominada) e 12 cargas.
SaveHandle MakeSave(const shatter_db* db) {
    SaveData s;
    s.contentVersion = tu::RichDb().ContentVersion();
    CharacterState c = tu::MakeWarrior(tu::RichDb(), 3);
    c.conqueredMaps.clear();
    s.characters.push_back(c);
    s.markerCharges = 0;
    s.lastSeenUtc = 1'700'000'000;
    const std::string text = SerializeJson(s, false);
    SaveHandle h;
    std::int32_t load = -1;
    shatter_error err{};
    if (shatter_save_from_json(text.data(), text.size(), &h.save, &load, &err) != SHATTER_OK) FAIL(err.message);
    shatter_area_run_reward rw{};
    const std::string map = "map.act1.crypt";
    if (shatter_save_record_area_run(db, h.save, 0, map.data(), map.size(), 1, 1, &rw) != SHATTER_OK || !rw.new_conquest)
        FAIL("record_area_run");
    for (int i = 0; i < 4; ++i) shatter_save_record_area_run(db, h.save, 0, map.data(), map.size(), 1, 0, &rw);
    return h;
}

std::string StartParams(int hours, std::uint64_t seed) {
    std::ostringstream os;
    os << R"({"character_index":0,"map_id":"map.act1.crypt","objective":"xp","rules":[)"
       << R"({"condition":"life_below","param":0.35,"action":"use_potion","ref_id":""},)"
       << R"({"condition":"enemies_at_least","param":2,"action":"use_skill","ref_id":"skill.warrior.cleave"},)"
       << R"({"condition":"always","param":0,"action":"use_skill","ref_id":"skill.warrior.iron_cut"}],)"
       << R"("duration_hours":)" << hours;
    if (seed != 0) os << R"(,"seed":")" << seed << R"(","start_utc":1700000000)";  // seed 0 = parâmetros confiáveis (sem seed nem início)
    os << "}";
    return os.str();
}

shatter_trusted_now TrustedStart() {
    shatter_trusted_now t{};
    t.now = 1'700'000'000;
    return t;
}

}  // namespace

TEST(c_api_version_layout_and_status_names) {
    EXPECT_EQ(shatter_api_version(), SHATTER_C_API_VERSION);
    std::uint32_t major = 99, minor = 99;
    shatter_core_version(&major, &minor);
    EXPECT_EQ(major, kCoreVersionMajor);
    EXPECT_EQ(minor, kCoreVersionMinor);
    shatter_core_version(nullptr, nullptr);  // não quebra
    EXPECT_EQ(std::string(shatter_status_name(SHATTER_BUFFER_TOO_SMALL)), std::string("buffer_too_small"));
    EXPECT_EQ(std::string(shatter_status_name(12345)), std::string("unknown"));
    // Layout: o que o C# vai montar com Marshal.SizeOf/OffsetOf.
    std::size_t needed = 0;
    EXPECT_EQ(shatter_layout_info(nullptr, 0, &needed), SHATTER_BUFFER_TOO_SMALL);
    EXPECT_EQ(needed, static_cast<std::size_t>(SHATTER_LAYOUT_COUNT));
    std::vector<std::uint32_t> layout(needed);
    ASSERT_EQ(shatter_layout_info(layout.data(), layout.size(), &needed), SHATTER_OK);
    const std::uint32_t expectedStart[] = {static_cast<std::uint32_t>(sizeof(shatter_error)), 0, 4, 8, 16, 0, 8, 288};
    for (std::size_t i = 0; i < sizeof(expectedStart) / sizeof(expectedStart[0]); ++i) EXPECT_EQ(layout[i], expectedStart[i]);
    shatter_error err{};
    EXPECT_EQ(shatter_layout_check(layout.data(), layout.size(), &err), SHATTER_OK);
    EXPECT_EQ(err.code, SHATTER_OK);
    layout[20] += 8;  // C# com um campo fora do lugar
    EXPECT_EQ(shatter_layout_check(layout.data(), layout.size(), &err), SHATTER_VERSION_MISMATCH);
    EXPECT_EQ(err.line, 21);
    EXPECT_TRUE(std::strlen(err.message) > 0);
    EXPECT_EQ(shatter_layout_check(layout.data(), layout.size() - 1, &err), SHATTER_VERSION_MISMATCH);
    EXPECT_EQ(shatter_layout_check(nullptr, 3, &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_layout_info(layout.data(), layout.size(), nullptr), SHATTER_INVALID_ARGUMENT);
}

TEST(c_api_null_handles_and_arguments_are_errors_not_crashes) {
    shatter_error err{};
    std::size_t needed = 0;
    std::uint8_t buf[16];
    double d = 0;
    std::uint64_t u = 0;
    shatter_rules rules{};
    shatter_rng rng{};
    shatter_hit_input hin{};
    shatter_hit_result hout{};
    EXPECT_EQ(shatter_db_load_directory(nullptr, 3, nullptr, &err), SHATTER_INVALID_ARGUMENT);
    shatter_db* db = reinterpret_cast<shatter_db*>(&buf);  // nunca deve ser lido quando outro argumento é nulo
    EXPECT_EQ(shatter_db_load_directory(nullptr, 3, &db, &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_TRUE(db == nullptr);
    EXPECT_EQ(shatter_db_content_version(nullptr, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_db_rules(nullptr, &rules), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_db_lookup_json(nullptr, "skill.a", 7, buf, sizeof(buf), &needed), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_db_errors_json(nullptr, buf, sizeof(buf), &needed), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_db_load_table(nullptr, "meta.csv", 8, "", 0, &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_db_finalize(nullptr, &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_statblock_get(nullptr, 0, 0, &d), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_statblock_revision(nullptr, &u), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_resolve_hit(nullptr, nullptr, &hin, &rules, &rng, &hout), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_effects_tick(nullptr, nullptr, 0.1, nullptr, &needed), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_save_to_json(nullptr, 0, buf, sizeof(buf), &needed), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_save_summary_get(nullptr, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_save_write(nullptr, "x", 1, &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_expedition_simulate(nullptr, "{}", 2, 0, buf, sizeof(buf), &needed, &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_rng_for_stream(1, 9, 0, &rng), SHATTER_INVALID_ARGUMENT);  // fluxo inexistente
    EXPECT_EQ(shatter_rng_next_u32(nullptr, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_clock_resolve_now(nullptr, &rules, nullptr), SHATTER_INVALID_ARGUMENT);
    // err é opcional; destroy(NULL) não faz nada.
    EXPECT_EQ(shatter_db_finalize(nullptr, nullptr), SHATTER_INVALID_ARGUMENT);
    shatter_db_destroy(nullptr);
    shatter_save_destroy(nullptr);
    shatter_statblock_destroy(nullptr);
    shatter_effects_destroy(nullptr);
    // Texto com comprimento: ponteiro nulo só com len 0; UTF-8 inválido é recusado.
    shatter_statblock* sb = nullptr;
    ASSERT_EQ(shatter_statblock_create(&sb), SHATTER_OK);
    EXPECT_EQ(shatter_statblock_remove_modifiers_from(sb, nullptr, 4, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_statblock_remove_modifiers_from(sb, nullptr, 0, nullptr), SHATTER_OK);
    EXPECT_EQ(shatter_statblock_remove_modifiers_from(sb, "\xC3\x28", 2, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_statblock_set_base(sb, SHATTER_STAT_COUNT, 1.0), SHATTER_INVALID_ARGUMENT);
    shatter_statblock_destroy(sb);
}

TEST(c_api_content_database_load_lookup_and_errors) {
    DbHandle rich(tu::RichDir());
    ASSERT_TRUE(rich.db != nullptr);
    std::uint32_t cv = 0;
    ASSERT_EQ(shatter_db_content_version(rich.db, &cv), SHATTER_OK);
    EXPECT_EQ(cv, tu::RichDb().ContentVersion());
    shatter_rules rules{};
    ASSERT_EQ(shatter_db_rules(rich.db, &rules), SHATTER_OK);
    EXPECT_NEAR(rules.evasion_cap, tu::RichDb().Rules().evasionCap, 0.0);
    EXPECT_NEAR(rules.vigor_h5_8, tu::RichDb().Rules().vigorByBand[1], 0.0);
    EXPECT_EQ(rules.charges_max, tu::RichDb().Rules().chargesMax);
    EXPECT_EQ(rules.max_level, tu::RichDb().Rules().maxLevel);
    double xp = 0;
    ASSERT_EQ(shatter_db_xp_to_next_level(rich.db, 5, &xp), SHATTER_OK);
    EXPECT_NEAR(xp, 580.0, 1e-9);
    EXPECT_EQ(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_db_errors_json(rich.db, o, c, n); }),
              std::string("[]"));
    // Consulta de exibição: tempos e dano da habilidade (o C# não lê o CSV).
    const std::string id = "skill.warrior.cleave";
    std::size_t needed = 0;
    EXPECT_EQ(shatter_db_lookup_json(rich.db, id.data(), id.size(), nullptr, 0, &needed), SHATTER_BUFFER_TOO_SMALL);
    EXPECT_TRUE(needed > 50);
    const json::Value skill = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_db_lookup_json(rich.db, id.data(), id.size(), o, c, n);
    }));
    EXPECT_EQ(skill["type"].AsString(), std::string("skill"));
    EXPECT_NEAR(skill["windup"].AsDouble(), 0.3, 1e-12);
    EXPECT_NEAR(skill["coefficient_by_rank"].At(2).AsDouble(), 1.2, 1e-12);
    EXPECT_EQ(skill["tags_mask"].AsInt(), static_cast<std::int64_t>(Tag::Attack | Tag::Melee | Tag::Area | Tag::Physical));
    EXPECT_EQ(skill["on_hit_effects"].At(0).AsString(), std::string("effect.guard_break"));
    EXPECT_TRUE(skill["idle"]["supported"].AsBool());
    for (const char* other : {"class.warrior", "effect.burn", "enemy.crypt_guardian", "affix.life_flat", "item_base.iron_sword",
                              "unique.bell_warden_blade", "loot.crypt.guardian", "enc.crypt.patrol_a", "map.act1.crypt"}) {
        const json::Value v = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
            return shatter_db_lookup_json(rich.db, other, std::strlen(other), o, c, n);
        }));
        EXPECT_EQ(v["id"].AsString(), std::string(other));
    }
    std::uint8_t buf[8];
    EXPECT_EQ(shatter_db_lookup_json(rich.db, "skill.nope", 10, buf, sizeof(buf), &needed), SHATTER_NOT_FOUND);
    EXPECT_EQ(shatter_db_lookup_json(rich.db, "currency.gold", 13, buf, sizeof(buf), &needed), SHATTER_NOT_FOUND);
    const json::Value maps = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_db_ids_json(rich.db, "maps", 4, o, c, n);
    }));
    ASSERT_EQ(maps.Size(), static_cast<std::size_t>(3));
    EXPECT_EQ(maps.At(0).AsString(), std::string("map.act1.crypt"));
    EXPECT_EQ(shatter_db_ids_json(rich.db, "skills", 6, buf, sizeof(buf), &needed), SHATTER_NOT_FOUND);

    // CSV inválido: CONTENT_INVALID, mas o handle volta para a lista de erros; consultas são recusadas.
    shatter_error err{};
    shatter_db* bad = nullptr;
    const std::string dup = tu::DataDir() + "/invalid/dup_skill_id";
    EXPECT_EQ(shatter_db_load_directory(dup.data(), dup.size(), &bad, &err), SHATTER_CONTENT_INVALID);
    ASSERT_TRUE(bad != nullptr);
    EXPECT_TRUE(std::string(err.message).find("E_DUP_ID") != std::string::npos);
    EXPECT_EQ(err.line, 4);
    const json::Value errs = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_db_errors_json(bad, o, c, n); }));
    ASSERT_TRUE(errs.Size() >= 1);
    EXPECT_EQ(errs.At(0)["table"].AsString(), std::string("skills.csv"));
    EXPECT_EQ(shatter_db_rules(bad, &rules), SHATTER_CONTENT_INVALID);
    shatter_db_destroy(bad);
    // Pasta inexistente: IO_ERROR.
    shatter_db* none = nullptr;
    const std::string missing = tu::DataDir() + "/nao_existe";
    EXPECT_EQ(shatter_db_load_directory(missing.data(), missing.size(), &none, &err), SHATTER_IO_ERROR);
    shatter_db_destroy(none);
    // Caminho com UTF-8 inválido.
    EXPECT_EQ(shatter_db_load_directory("\xFF\xFE", 2, &none, &err), SHATTER_INVALID_ARGUMENT);
    // Tabela a tabela + finalize; tabela depois do finalize é recusada.
    shatter_db* manual = nullptr;
    ASSERT_EQ(shatter_db_create(&manual), SHATTER_OK);
    for (const char* t : tu::kTableNames) {
        const std::string text = tu::ReadFile(tu::RichDir() + "/" + t);
        EXPECT_EQ(shatter_db_load_table(manual, t, std::strlen(t), text.data(), text.size(), &err), SHATTER_OK);
    }
    EXPECT_EQ(shatter_db_content_version(manual, &cv), SHATTER_CONTENT_INVALID);  // ainda não finalizado
    EXPECT_EQ(shatter_db_finalize(manual, &err), SHATTER_OK);
    EXPECT_EQ(shatter_db_load_table(manual, "meta.csv", 8, "key,value\n", 10, &err), SHATTER_CONTENT_INVALID);
    EXPECT_EQ(shatter_db_load_table(manual, "bogus.csv", 9, "a\n", 2, &err), SHATTER_CONTENT_INVALID);
    shatter_db_destroy(manual);
    shatter_db* broken = nullptr;
    ASSERT_EQ(shatter_db_create(&broken), SHATTER_OK);
    EXPECT_EQ(shatter_db_load_table(broken, "meta.csv", 8, "key,value\ncontent_version,0\n", 28, &err), SHATTER_CONTENT_INVALID);
    EXPECT_EQ(err.line, 2);
    shatter_db_destroy(broken);
}

TEST(c_api_statblock_formula_and_hit_match_the_cpp_core) {
    DbHandle db(tu::RichDir());
    // RF-01 pela fronteira: 130 × 1,5 × 1,1 × 1,2 = 257,4.
    shatter_statblock* sb = nullptr;
    ASSERT_EQ(shatter_statblock_create(&sb), SHATTER_OK);
    ASSERT_EQ(shatter_statblock_set_base(sb, SHATTER_STAT_LIFE, 100), SHATTER_OK);
    const shatter_modifier mods[] = {{10, 0, SHATTER_STAT_LIFE, SHATTER_MOD_FLAT, 0}, {20, 0, SHATTER_STAT_LIFE, SHATTER_MOD_FLAT, 0},
                                     {0.2, 0, SHATTER_STAT_LIFE, SHATTER_MOD_INCREASED, 0}, {0.3, 0, SHATTER_STAT_LIFE, SHATTER_MOD_INCREASED, 0},
                                     {0.1, 0, SHATTER_STAT_LIFE, SHATTER_MOD_MORE, 0}, {0.2, 0, SHATTER_STAT_LIFE, SHATTER_MOD_MORE, 0}};
    std::uint64_t rev0 = 0, rev1 = 0;
    ASSERT_EQ(shatter_statblock_revision(sb, &rev0), SHATTER_OK);
    for (const shatter_modifier& m : mods) EXPECT_EQ(shatter_statblock_add_modifier(sb, &m, "item:7", 6), SHATTER_OK);
    ASSERT_EQ(shatter_statblock_revision(sb, &rev1), SHATTER_OK);
    EXPECT_EQ(rev1, rev0 + 6);
    double v = 0;
    ASSERT_EQ(shatter_statblock_get(sb, SHATTER_STAT_LIFE, 0, &v), SHATTER_OK);
    EXPECT_NEAR(v, 257.4, 1e-6);
    std::uint32_t removed = 0;
    ASSERT_EQ(shatter_statblock_remove_modifiers_from(sb, "item:7", 6, &removed), SHATTER_OK);
    EXPECT_EQ(removed, 6u);
    ASSERT_EQ(shatter_statblock_get(sb, SHATTER_STAT_LIFE, 0, &v), SHATTER_OK);
    EXPECT_NEAR(v, 100.0, 0.0);
    shatter_modifier bad = mods[0];
    bad.kind = 7;
    EXPECT_EQ(shatter_statblock_add_modifier(sb, &bad, "x", 1), SHATTER_INVALID_ARGUMENT);
    shatter_statblock_destroy(sb);

    // Golpe: personagem (JSON do save) contra Sentinela no nível 4 = o mesmo ResolveHit do C++, mesmo RNG.
    const ContentDB& cdb = tu::RichDb();
    const CharacterState hero = tu::MakeWarrior(cdb, 3);
    const std::string heroJson = S(CharacterToJson(hero));
    shatter_error err{};
    shatter_statblock* atk = nullptr;
    shatter_statblock* def = nullptr;
    ASSERT_EQ(shatter_statblock_from_character_json(db.db, heroJson.data(), heroJson.size(), &atk, &err), SHATTER_OK);
    ASSERT_EQ(shatter_statblock_for_enemy(db.db, "enemy.hollow_sentinel", 21, 4, &def), SHATTER_OK);
    shatter_statblock* nobody = def;  // a saída é zerada antes de qualquer erro
    EXPECT_EQ(shatter_statblock_for_enemy(db.db, "enemy.nobody", 12, 4, &nobody), SHATTER_NOT_FOUND);
    EXPECT_TRUE(nobody == nullptr);
    StatBlock catk, cdef;
    ASSERT_TRUE(BuildStatBlock(cdb, hero, catk));
    BuildEnemyStatBlock(*cdb.FindEnemy("enemy.hollow_sentinel"), 4, cdef);
    double cLife = 0;
    ASSERT_EQ(shatter_statblock_get(def, SHATTER_STAT_LIFE, 0, &cLife), SHATTER_OK);
    EXPECT_NEAR(cLife, cdef.Get(StatId::Life), 0.0);
    shatter_rules rules{};
    ASSERT_EQ(shatter_db_rules(db.db, &rules), SHATTER_OK);
    shatter_rng rng{};
    ASSERT_EQ(shatter_rng_for_stream(424242, SHATTER_RNG_COMBAT, 0, &rng), SHATTER_OK);
    Pcg32 cr = Pcg32::ForStream(424242, RngStream::Combat, 0);
    EXPECT_EQ(rng.state, cr.State());
    for (int i = 0; i < 2000; ++i) {
        shatter_hit_input in{};
        in.base_damage[SHATTER_DAMAGE_PHYSICAL] = 5.0 + i % 40;
        in.base_damage[SHATTER_DAMAGE_FIRE] = (i % 3 == 0) ? 7.0 : 0.0;
        in.coefficient = 1.1;
        in.defender_life = 200.0;
        in.defender_barrier = (i % 5 == 0) ? 10.0 : 0.0;
        in.skill_tags = SHATTER_TAG_ATTACK | SHATTER_TAG_MELEE | SHATTER_TAG_PHYSICAL;
        in.is_damage_over_time = (i % 7 == 0) ? 1 : 0;
        in.can_be_blocked = 1;
        shatter_hit_result out{};
        ASSERT_EQ(shatter_resolve_hit(atk, def, &in, &rules, &rng, &out), SHATTER_OK);
        HitInput ci;
        ci.attacker = &catk;
        ci.defender = &cdef;
        ci.skillTags = in.skill_tags;
        ci.baseDamage = {in.base_damage[0], in.base_damage[1], 0.0, 0.0};
        ci.coefficient = in.coefficient;
        ci.isDamageOverTime = in.is_damage_over_time != 0;
        ci.defenderLife = in.defender_life;
        ci.defenderBarrier = in.defender_barrier;
        const HitResult hr = ResolveHit(ci, cdb.Rules(), cr);
        if (out.total_damage != hr.totalDamage || out.critical != (hr.critical ? 1 : 0) ||
            out.outcome != static_cast<std::uint8_t>(hr.outcome) || out.defender_life_after != hr.defenderLifeAfter ||
            out.absorbed_by_barrier != hr.absorbedByBarrier || rng.state != cr.State()) {
            FAIL("golpe divergiu do C++ no indice " + std::to_string(i));
            break;
        }
    }
    double cd = 0;
    ASSERT_EQ(shatter_effective_cooldown(5.0, 100.0, &rules, &cd), SHATTER_OK);
    EXPECT_NEAR(cd, rules.cooldown_min, 0.0);
    std::uint32_t r32 = 0;
    ASSERT_EQ(shatter_rng_next_u32(&rng, &r32), SHATTER_OK);
    EXPECT_EQ(r32, cr.NextU32());
    shatter_statblock_destroy(atk);
    shatter_statblock_destroy(def);
}

TEST(c_api_effects_tick_events_and_buffer) {
    DbHandle db(tu::RichDir());
    shatter_statblock* target = nullptr;
    shatter_effects* fx = nullptr;
    ASSERT_EQ(shatter_statblock_for_enemy(db.db, "enemy.hollow_sentinel", 21, 1, &target), SHATTER_OK);
    ASSERT_EQ(shatter_effects_create(&fx), SHATTER_OK);
    std::uint8_t applied = 0;
    ASSERT_EQ(shatter_effects_apply(fx, db.db, "effect.burn", 11, "player", 6, 2.0, SHATTER_TRIGGER_NONE, target, &applied), SHATTER_OK);
    EXPECT_EQ(applied, 1);
    EXPECT_EQ(shatter_effects_apply(fx, db.db, "effect.none", 11, "player", 6, 1.0, SHATTER_TRIGGER_NONE, target, &applied), SHATTER_NOT_FOUND);
    EXPECT_EQ(shatter_effects_apply(fx, db.db, "effect.burn", 11, "player", 6, 1.0, 99, target, &applied), SHATTER_INVALID_ARGUMENT);
    std::int32_t stacks = 0;
    ASSERT_EQ(shatter_effects_stack_count(fx, "effect.burn", 11, &stacks), SHATTER_OK);
    EXPECT_EQ(stacks, 1);
    const json::Value active = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_effects_active_json(fx, o, c, n); }));
    ASSERT_EQ(active.Size(), static_cast<std::size_t>(1));
    EXPECT_NEAR(active.At(0)["magnitude"].AsDouble(), 2.0, 0.0);
    // O mesmo efeito no C++: eventos idênticos tick a tick.
    const ContentDB& cdb = tu::RichDb();
    StatBlock csb;
    BuildEnemyStatBlock(*cdb.FindEnemy("enemy.hollow_sentinel"), 1, csb);
    EffectContainer cfx;
    cfx.Apply(*cdb.FindEffect("effect.burn"), "player", 2.0, TriggerKind::None, csb, cdb.Rules());
    int damageTicks = 0;
    bool expired = false;
    for (int step = 0; step < 60; ++step) {
        std::size_t count = 0;
        ASSERT_EQ(shatter_effects_tick(fx, db.db, 0.1, target, &count), SHATTER_OK);
        std::vector<EffectEvent> cev;
        cfx.Tick(0.1, cdb.EffectLookup(), csb, cev);
        ASSERT_EQ(count, cev.size());
        if (count == 0) continue;
        std::size_t needed = 0;
        EXPECT_EQ(shatter_effects_events(fx, nullptr, 0, &needed), SHATTER_BUFFER_TOO_SMALL);
        EXPECT_EQ(needed, count);
        std::vector<shatter_effect_event> ev(count);
        ASSERT_EQ(shatter_effects_events(fx, ev.data(), ev.size(), &needed), SHATTER_OK);
        // Ler de novo devolve os mesmos eventos (o tick não é refeito).
        std::vector<shatter_effect_event> again(count);
        ASSERT_EQ(shatter_effects_events(fx, again.data(), again.size(), &needed), SHATTER_OK);
        for (std::size_t k = 0; k < count; ++k) {
            EXPECT_EQ(std::string(ev[k].effect_id), cev[k].effectId);
            EXPECT_EQ(ev[k].effect_id_len, static_cast<std::uint32_t>(cev[k].effectId.size()));
            EXPECT_NEAR(ev[k].damage[SHATTER_DAMAGE_FIRE], cev[k].damage[1], 0.0);
            EXPECT_EQ(std::memcmp(&ev[k], &again[k], sizeof(shatter_effect_event)), 0);
            damageTicks += ev[k].kind == SHATTER_EFFECT_EVENT_DAMAGE_TICK ? 1 : 0;
            expired = expired || ev[k].kind == SHATTER_EFFECT_EVENT_EXPIRED;
        }
    }
    EXPECT_TRUE(damageTicks > 0);
    EXPECT_TRUE(expired);
    ASSERT_EQ(shatter_effects_stack_count(fx, "effect.burn", 11, &stacks), SHATTER_OK);
    EXPECT_EQ(stacks, 0);
    // Lentidão: mods no StatBlock enquanto ativo; clear remove.
    ASSERT_EQ(shatter_effects_apply(fx, db.db, "effect.slow", 11, "", 0, 1.0, SHATTER_TRIGGER_NONE, target, &applied), SHATTER_OK);
    double before = 0, after = 0;
    ASSERT_EQ(shatter_statblock_get(target, SHATTER_STAT_MOVE_SPEED, 0, &before), SHATTER_OK);
    ASSERT_EQ(shatter_effects_clear(fx, target), SHATTER_OK);
    ASSERT_EQ(shatter_statblock_get(target, SHATTER_STAT_MOVE_SPEED, 0, &after), SHATTER_OK);
    EXPECT_TRUE(after > before);
    shatter_effects_destroy(fx);
    shatter_statblock_destroy(target);
}

TEST(c_api_clock_matches_cpp) {
    DbHandle db(tu::RichDir());
    shatter_rules rules{};
    ASSERT_EQ(shatter_db_rules(db.db, &rules), SHATTER_OK);
    const UnixSeconds t = 1'700'000'000;
    for (UnixSeconds delta : {-6 * 60, -4 * 60, 0, 3600, 30 * 3600}) {
        shatter_clock_input in{};
        in.local_now_utc = t + delta;
        in.last_seen_utc = t;
        shatter_trusted_now now{};
        ASSERT_EQ(shatter_clock_resolve_now(&in, &rules, &now), SHATTER_OK);
        ClockInput ci;
        ci.localNowUtc = t + delta;
        ci.lastSeenUtc = t;
        const TrustedNow cn = ResolveNow(ci, tu::RichDb().Rules());
        EXPECT_EQ(now.now, cn.now);
        EXPECT_EQ(now.rollback_detected != 0, cn.rollbackDetected);
        shatter_offline_window w{};
        ASSERT_EQ(shatter_clock_expedition_window(t - 3600, 4, &now, t, &rules, &w), SHATTER_OK);
        const OfflineWindow cw = ComputeExpeditionWindow(t - 3600, 4, cn, t, tu::RichDb().Rules());
        EXPECT_NEAR(w.effective_seconds, cw.effectiveSeconds, 0.0);
        EXPECT_EQ(w.ended_by_rollback != 0, cw.endedByRollback);
        EXPECT_EQ(w.finished != 0, cw.finished);
    }
}

TEST(c_api_loot_roll_buffer_too_small_changes_nothing) {
    DbHandle db(tu::RichDir());
    SaveHandle save = MakeSave(db.db);
    shatter_save_summary sum{};
    ASSERT_EQ(shatter_save_summary_get(save.save, &sum), SHATTER_OK);
    const std::uint64_t uidBefore = sum.next_item_uid;
    shatter_loot_context ctx{};
    ctx.quantity_mult = 1.0;
    ctx.mode = SHATTER_LOOT_MANUAL;
    ctx.area_level = 4;
    ctx.max_rares = -1;
    shatter_rng rng{};
    ASSERT_EQ(shatter_rng_for_stream(7, SHATTER_RNG_LOOT, 0, &rng), SHATTER_OK);
    const shatter_rng start = rng;
    const std::string table = "loot.crypt.guardian";
    std::size_t needed = 0;
    shatter_error err{};
    // Buffer pequeno: nem o RNG nem o contador de uid andam.
    EXPECT_EQ(shatter_loot_roll(db.db, save.save, table.data(), table.size(), &ctx, &rng, nullptr, 0, &needed, &err),
              SHATTER_BUFFER_TOO_SMALL);
    EXPECT_EQ(rng.state, start.state);
    ASSERT_EQ(shatter_save_summary_get(save.save, &sum), SHATTER_OK);
    EXPECT_EQ(sum.next_item_uid, uidBefore);
    std::vector<std::uint8_t> buf(needed);
    ASSERT_EQ(shatter_loot_roll(db.db, save.save, table.data(), table.size(), &ctx, &rng, buf.data(), buf.size(), &needed, &err),
              SHATTER_OK);
    EXPECT_NE(rng.state, start.state);
    const std::string lootText(reinterpret_cast<const char*>(buf.data()), buf.size());
    const json::Value loot = Parse(lootText);
    // O mesmo sorteio no C++ (mesmo RNG, mesmo contador).
    std::uint64_t uid = uidBefore;
    LootContext lc;
    lc.areaLevel = 4;
    lc.nextItemUid = &uid;
    Pcg32 cr = Pcg32::FromRaw(start.state, start.inc);
    const LootDrop cd = RollLootTable(tu::RichDb(), *tu::RichDb().FindLootTable(table), lc, cr);
    EXPECT_EQ(loot["items"].Size(), cd.items.size());
    EXPECT_EQ(rng.state, cr.State());
    ASSERT_EQ(shatter_save_summary_get(save.save, &sum), SHATTER_OK);
    EXPECT_EQ(sum.next_item_uid, uid);
    // Pegar o loot: entra no baú com os uids reservados.
    ASSERT_EQ(shatter_save_add_loot(save.save, lootText.data(), lootText.size(), &err), SHATTER_OK);
    const json::Value file = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_save_to_json(save.save, 0, o, c, n); }));
    EXPECT_EQ(file["data"]["stash"].Size(), cd.items.size());
    EXPECT_EQ(shatter_save_add_loot(save.save, "{\"items\":[{\"rarity\":\"mythic\"}]}", 32, &err), SHATTER_PARSE_ERROR);
    EXPECT_EQ(shatter_loot_roll(db.db, save.save, "loot.none", 9, &ctx, &rng, buf.data(), buf.size(), &needed, &err), SHATTER_NOT_FOUND);
}

TEST(c_api_save_roundtrip_files_backups_and_version_checks) {
    DbHandle db(tu::RichDir());
    shatter_error err{};
    // save_v2.json (publicado): abre pela fronteira e volta com o mesmo hash. O save_v1.json também abre (migra para v2).
    const std::string v2 = tu::ReadFile(tu::DataDir() + "/saves/save_v2.json");
    SaveHandle s;
    std::int32_t load = -1;
    ASSERT_EQ(shatter_save_from_json(v2.data(), v2.size(), &s.save, &load, &err), SHATTER_OK);
    EXPECT_EQ(load, 0);
    const json::Value back = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_save_to_json(s.save, 1, o, c, n); }));
    EXPECT_EQ(back["sha256"].AsString(), Parse(v2)["sha256"].AsString());
    {
        const std::string v1 = tu::ReadFile(tu::DataDir() + "/saves/save_v1.json");
        SaveHandle migrated;
        ASSERT_EQ(shatter_save_from_json(v1.data(), v1.size(), &migrated.save, &load, &err), SHATTER_OK);
        shatter_save_summary msum{};
        ASSERT_EQ(shatter_save_summary_get(migrated.save, &msum), SHATTER_OK);
        EXPECT_EQ(msum.save_version, 2);
    }
    shatter_save_summary sum{};
    ASSERT_EQ(shatter_save_summary_get(s.save, &sum), SHATTER_OK);
    EXPECT_EQ(sum.character_count, 1);
    EXPECT_EQ(sum.marker_charges, 3);
    EXPECT_EQ(sum.running_expedition, 0);
    const json::Value ch = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_save_character_json(s.save, 0, o, c, n); }));
    EXPECT_EQ(ch["class_id"].AsString(), std::string("class.warrior"));
    std::uint8_t tiny[4];
    std::size_t needed = 0;
    EXPECT_EQ(shatter_save_character_json(s.save, 5, tiny, sizeof(tiny), &needed), SHATTER_INVALID_ARGUMENT);
    // Checksum adulterado: PARSE_ERROR com o status do core.
    const std::string altered = tu::ReadFile(tu::DataDir() + "/saves/invalid/checksum_altered.json");
    shatter_save* bad = nullptr;
    EXPECT_EQ(shatter_save_from_json(altered.data(), altered.size(), &bad, &load, &err), SHATTER_PARSE_ERROR);
    EXPECT_EQ(load, static_cast<std::int32_t>(LoadStatus::ChecksumMismatch));
    EXPECT_TRUE(bad == nullptr);

    // Disco: 5 gravações = principal + 3 backups; principal corrompido carrega o bak1 e avisa.
    const std::string dir = tu::TmpDir("c_api_save");
    const std::string base = dir + "/slot_1";
    const std::int64_t seen0 = sum.last_seen_utc;  // o last_seen nunca anda para trás: parte do valor do arquivo
    const std::int64_t restDay0 = sum.last_rest_day;
    for (int i = 0; i < 5; ++i) {
        shatter_trusted_now now{};
        now.now = seen0 + i;
        ASSERT_EQ(shatter_save_touch_last_seen(s.save, &now), SHATTER_OK);
        ASSERT_EQ(shatter_save_write(s.save, base.data(), base.size(), &err), SHATTER_OK);
    }
    SaveHandle r1;
    shatter_load_report rep{};
    ASSERT_EQ(shatter_save_read(db.db, base.data(), base.size(), &r1.save, &rep, &err), SHATTER_OK);
    EXPECT_EQ(rep.used_backup, 0);
    ASSERT_EQ(shatter_save_summary_get(r1.save, &sum), SHATTER_OK);
    EXPECT_EQ(sum.last_seen_utc, seen0 + 4);
    std::string mainText = tu::ReadFile(base + ".json");
    mainText[mainText.size() / 2] = static_cast<char>(mainText[mainText.size() / 2] == '1' ? '2' : '1');
    std::unique_ptr<IFileIO> io = MakeStdFileIO();
    ASSERT_TRUE(io->WriteAll(base + ".json", mainText));
    SaveHandle r2;
    ASSERT_EQ(shatter_save_read(db.db, base.data(), base.size(), &r2.save, &rep, &err), SHATTER_OK);
    EXPECT_EQ(rep.used_backup, 1);
    ASSERT_EQ(shatter_save_summary_get(r2.save, &sum), SHATTER_OK);
    EXPECT_EQ(sum.last_seen_utc, seen0 + 3);
    // Nada no disco: NOT_FOUND.
    const std::string nowhere = dir + "/slot_9";
    shatter_save* none = nullptr;
    EXPECT_EQ(shatter_save_read(nullptr, nowhere.data(), nowhere.size(), &none, &rep, &err), SHATTER_NOT_FOUND);
    EXPECT_EQ(rep.status, static_cast<std::int32_t>(LoadStatus::Missing));
    // RNF-10: content_version maior que o do jogo é recusado sem tocar no arquivo.
    SaveData future;
    future.contentVersion = tu::RichDb().ContentVersion() + 1;
    future.characters.push_back(tu::MakeWarrior(tu::RichDb()));
    const std::string fbase = dir + "/slot_future";
    ASSERT_TRUE(WriteSaveFile(*io, fbase, future));
    const std::string fbefore = tu::ReadFile(fbase + ".json");
    EXPECT_EQ(shatter_save_read(db.db, fbase.data(), fbase.size(), &none, &rep, &err), SHATTER_VERSION_MISMATCH);
    EXPECT_TRUE(none == nullptr);
    EXPECT_EQ(tu::ReadFile(fbase + ".json"), fbefore);
    // Sem db, o mesmo arquivo abre (a checagem de conteúdo é opcional).
    SaveHandle r3;
    EXPECT_EQ(shatter_save_read(nullptr, fbase.data(), fbase.size(), &r3.save, &rep, &err), SHATTER_OK);
    // save_version futuro também é VERSION_MISMATCH.
    std::string newer = SerializeJson(future, true);
    newer = tu::Replace(newer, "\"save_version\": 2,", "\"save_version\": 3,");
    EXPECT_EQ(shatter_save_from_json(newer.data(), newer.size(), &none, &load, &err), SHATTER_VERSION_MISMATCH);
    EXPECT_EQ(load, static_cast<std::int32_t>(LoadStatus::TooNew));
    // Descanso diário: +4 num dia UTC novo, sem acumular.
    std::int32_t charges = -1;
    shatter_trusted_now later{};
    later.now = (restDay0 + 3) * 86400 + 100;  // 3 dias UTC depois do último descanso
    ASSERT_EQ(shatter_save_apply_daily_rest(db.db, r1.save, &later, &charges), SHATTER_OK);
    EXPECT_EQ(charges, 3 + 4);
    ASSERT_EQ(shatter_save_apply_daily_rest(db.db, r1.save, &later, &charges), SHATTER_OK);
    EXPECT_EQ(charges, 7);
}

TEST(c_api_expedition_end_to_end_matches_cpp_and_collects_once) {
    DbHandle db(tu::RichDir());
    const ContentDB& cdb = tu::RichDb();
    SaveHandle save = MakeSave(db.db);
    shatter_save_summary sum{};
    ASSERT_EQ(shatter_save_summary_get(save.save, &sum), SHATTER_OK);
    EXPECT_EQ(sum.marker_charges, 5 + 4);  // domínio (+5) e 4 corridas sem o chefe (+1 cada)
    shatter_error err{};
    std::int32_t check = -1;
    // Conferir: 12 h com 9 cargas é recusada; o save não muda.
    const std::string twelve = StartParams(12, 1);
    std::string blocking = TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_expedition_check(db.db, save.save, twelve.data(), twelve.size(), &check, o, c, n, &err);
    });
    EXPECT_EQ(check, SHATTER_START_NOT_ENOUGH_CHARGES);
    EXPECT_EQ(blocking, std::string("[]"));
    // Build com habilidade sem perfil idle: bloqueio com o ID.
    {
        SaveData copy;
        const std::string text = TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_save_to_json(save.save, 0, o, c, n); });
        ASSERT_TRUE(ParseJson(text, copy) == LoadStatus::Ok);
        copy.characters[0].skillBar[3] = "skill.warrior.unsupported_roar";
        const std::string roarText = SerializeJson(copy, false);
        SaveHandle roar;
        std::int32_t load = 0;
        ASSERT_EQ(shatter_save_from_json(roarText.data(), roarText.size(), &roar.save, &load, &err), SHATTER_OK);
        const std::string p = StartParams(1, 1);
        blocking = TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
            return shatter_expedition_check(db.db, roar.save, p.data(), p.size(), &check, o, c, n, &err);
        });
        EXPECT_EQ(check, SHATTER_START_IDLE_INCOMPATIBLE);
        EXPECT_EQ(blocking, std::string("[\"skill.warrior.unsupported_roar\"]"));
    }
    // Inicia 4 h.
    const std::string params = StartParams(4, 0);
    const shatter_trusted_now startNow = TrustedStart();
    // A API antiga (start_utc e seed do chamador) foi retirada; seed e start_utc no JSON são recusados.
    EXPECT_EQ(shatter_save_start_expedition(db.db, save.save, params.data(), params.size(), &check, &err), SHATTER_INVALID_ARGUMENT);
    const std::string forged = StartParams(4, 20261016);
    EXPECT_EQ(shatter_save_start_expedition_trusted(db.db, save.save, forged.data(), forged.size(), &startNow, &check, &err), SHATTER_INVALID_ARGUMENT);
    ASSERT_EQ(shatter_save_summary_get(save.save, &sum), SHATTER_OK);
    EXPECT_EQ(sum.expedition_count, 0);  // nada foi iniciado
    ASSERT_EQ(shatter_save_start_expedition_trusted(db.db, save.save, params.data(), params.size(), &startNow, &check, &err), SHATTER_OK);
    ASSERT_EQ(check, SHATTER_START_OK);
    ASSERT_EQ(shatter_save_summary_get(save.save, &sum), SHATTER_OK);
    EXPECT_EQ(sum.marker_charges, 9 - 4);
    EXPECT_EQ(sum.running_expedition, 0);
    ASSERT_EQ(shatter_save_start_expedition_trusted(db.db, save.save, params.data(), params.size(), &startNow, &check, &err), SHATTER_OK);
    EXPECT_EQ(check, SHATTER_START_ANOTHER_RUNNING);  // RF-37
    EXPECT_EQ(shatter_save_start_expedition_trusted(db.db, save.save, "{nope", 5, &startNow, &check, &err), SHATTER_PARSE_ERROR);
    EXPECT_EQ(err.line, 1);

    // Abrir o jogo 10 h depois: janela de 4 h; pedido pronto em JSON.
    shatter_clock_input clock{};
    clock.local_now_utc = 1'700'000'000 + 10 * 3600;
    shatter_offline_window window{};
    const std::string request = TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_save_expedition_request(db.db, save.save, 0, &clock, &window, o, c, n, &err);
    });
    ASSERT_TRUE(!request.empty());
    EXPECT_NEAR(window.effective_seconds, 4 * 3600.0, 0.0);
    EXPECT_EQ(window.finished, 1);
    EXPECT_EQ(window.ended_by_rollback, 0);
    // Simular pela fronteira = simular no C++ (mesmo resultHash).
    ExpeditionRequest creq;
    ASSERT_TRUE(ExpeditionRequestFromJson(Parse(request), creq));
    const ExpeditionResult cres = SimulateExpedition(cdb, creq);
    shatter_status st = SHATTER_INTERNAL;
    const std::string resultText = TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_expedition_simulate(db.db, request.data(), request.size(), SHATTER_RESULT_RECEIPTS, o, c, n, &err);
    }, &st);
    ASSERT_EQ(st, SHATTER_OK);
    const json::Value result = Parse(resultText);
    EXPECT_EQ(result["result_hash"].AsUInt64(), cres.resultHash);
    EXPECT_EQ(result["stop"].AsString(), std::string("duration_reached"));
    EXPECT_EQ(result["receipts"].Size(), cres.receipts.size());
    EXPECT_EQ(result["receipt_count"].AsInt(), static_cast<std::int64_t>(cres.receipts.size()));
    EXPECT_NEAR(result["xp_gained"].AsDouble(), cres.xpGained, 0.0);
    EXPECT_EQ(result["tip_keys"].At(0).AsString(), cres.tipKeys[0]);
    // Sem recibos o JSON é menor, com o mesmo hash.
    const json::Value lean = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_expedition_simulate(db.db, request.data(), request.size(), 0, o, c, n, &err);
    }));
    EXPECT_FALSE(lean.Has("receipts"));
    EXPECT_EQ(lean["result_hash"].AsString(), result["result_hash"].AsString());
    // Em fatias (cancelável entre elas) + finalize = o mesmo resultHash (RNF-02 pela fronteira).
    std::string progress;
    std::uint32_t next = 0;
    int slices = 0;
    for (;;) {
        const std::string prev = progress;
        progress = TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
            return shatter_expedition_simulate_range(db.db, request.data(), request.size(), prev.empty() ? nullptr : prev.data(),
                                                     prev.size(), next, 37, o, c, n, &err);
        });
        ASSERT_TRUE(!progress.empty());
        ++slices;
        const json::Value p = Parse(progress);
        next = static_cast<std::uint32_t>(p["next_encounter"].AsInt());
        if (p["stop"].AsString() != "none") break;
        if (slices > 10000) { FAIL("fatias sem fim"); break; }
    }
    EXPECT_TRUE(slices > 10);
    const json::Value finalized = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_expedition_finalize(db.db, request.data(), request.size(), progress.data(), progress.size(), 0, o, c, n, &err);
    }));
    EXPECT_EQ(finalized["result_hash"].AsString(), result["result_hash"].AsString());
    // Previsão (RF-40) igual à do C++.
    shatter_forecast fc{};
    ASSERT_EQ(shatter_expedition_forecast(db.db, request.data(), request.size(), 99, 20, &fc, &err), SHATTER_OK);
    const ExpeditionForecast cf = ForecastExpedition(cdb, creq, 99, 20);
    EXPECT_NEAR(fc.xp_p50, cf.xpP50, 0.0);
    EXPECT_NEAR(fc.gold_p90, cf.goldP90, 0.0);
    EXPECT_EQ(shatter_expedition_forecast(db.db, request.data(), request.size(), 99, 0, &fc, &err), SHATTER_INVALID_ARGUMENT);

    // Coleta (RF-55): entra uma vez; a segunda não muda nada.
    ASSERT_EQ(shatter_save_summary_get(save.save, &sum), SHATTER_OK);
    const std::uint64_t uidBefore = sum.next_item_uid;
    std::int32_t collectStatus = -1;
    std::size_t collectNeeded = 0;
    // Antes da hora: a janela não acabou, nada muda (o relógio confiável decide, não o chamador).
    shatter_clock_input early{};
    early.local_now_utc = 1'700'000'000 + 3600;
    ASSERT_EQ(shatter_save_collect_expedition_trusted(db.db, save.save, 0, &early, 0, &collectStatus, nullptr, 0, &collectNeeded, &err), SHATTER_OK);
    EXPECT_EQ(collectStatus, SHATTER_COLLECT_NOT_FINISHED);
    EXPECT_EQ(collectNeeded, static_cast<std::size_t>(0));
    ASSERT_EQ(shatter_save_summary_get(save.save, &sum), SHATTER_OK);
    EXPECT_EQ(sum.running_expedition, 0);
    // A API antiga (resultado do chamador) foi retirada.
    std::uint8_t legacy = 9;
    EXPECT_EQ(shatter_save_collect_expedition(db.db, save.save, 0, resultText.data(), resultText.size(), &legacy, &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(legacy, 0);
    // Buffer pequeno: nada muda.
    EXPECT_EQ(shatter_save_collect_expedition_trusted(db.db, save.save, 0, &clock, 0, &collectStatus, nullptr, 0, &collectNeeded, &err), SHATTER_BUFFER_TOO_SMALL);
    EXPECT_TRUE(collectNeeded > 0);
    ASSERT_EQ(shatter_save_summary_get(save.save, &sum), SHATTER_OK);
    EXPECT_EQ(sum.running_expedition, 0);
    shatter_status collectSt = SHATTER_INTERNAL;
    const std::string collectedText = TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_save_collect_expedition_trusted(db.db, save.save, 0, &clock, SHATTER_RESULT_RECEIPTS, &collectStatus, o, c, n, &err);
    }, &collectSt);
    ASSERT_EQ(collectSt, SHATTER_OK);
    EXPECT_EQ(collectStatus, SHATTER_COLLECT_COLLECTED);
    // O que entrou é o que o core recalculou do pedido salvo (mesmo hash da simulação do C++).
    EXPECT_EQ(Parse(collectedText)["result_hash"].AsString(), result["result_hash"].AsString());
    const std::string afterFirst = TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_save_to_json(save.save, 0, o, c, n); });
    ASSERT_EQ(shatter_save_collect_expedition_trusted(db.db, save.save, 0, &clock, 0, &collectStatus, nullptr, 0, &collectNeeded, &err), SHATTER_OK);
    EXPECT_EQ(collectStatus, SHATTER_COLLECT_ALREADY);
    EXPECT_EQ(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_save_to_json(save.save, 0, o, c, n); }), afterFirst);
    const json::Value saved = Parse(afterFirst);
    EXPECT_EQ(saved["data"]["expeditions"].At(0)["status"].AsString(), std::string("collected"));
    EXPECT_EQ(saved["data"]["expeditions"].At(0)["collected_result_hash"].AsString(), result["result_hash"].AsString());
    EXPECT_EQ(saved["data"]["stash"].Size(), cres.items.size());
    ASSERT_EQ(shatter_save_summary_get(save.save, &sum), SHATTER_OK);
    EXPECT_EQ(sum.next_item_uid, uidBefore + cres.items.size());
    EXPECT_EQ(sum.running_expedition, -1);
    // Pedido de expedição já coletada é recusado; resultado sem hash também.
    std::size_t needed = 0;
    EXPECT_EQ(shatter_save_expedition_request(db.db, save.save, 0, &clock, &window, nullptr, 0, &needed, &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_save_collect_expedition_trusted(db.db, save.save, 9, &clock, 0, &collectStatus, nullptr, 0, &collectNeeded, &err), SHATTER_INVALID_ARGUMENT);
}

TEST(c_api_rf48_clock_rollback_reaches_the_report) {
    DbHandle db(tu::RichDir());
    SaveHandle save = MakeSave(db.db);
    shatter_error err{};
    std::int32_t check = -1;
    const std::string params = StartParams(4, 0);
    const shatter_trusted_now startNow = TrustedStart();
    ASSERT_EQ(shatter_save_start_expedition_trusted(db.db, save.save, params.data(), params.size(), &startNow, &check, &err), SHATTER_OK);
    ASSERT_EQ(check, SHATTER_START_OK);
    // last_seen = T = início + 2 h; o relógio do PC agora diz T − 6 min.
    shatter_trusted_now seen{};
    seen.now = 1'700'000'000 + 2 * 3600;
    ASSERT_EQ(shatter_save_touch_last_seen(save.save, &seen), SHATTER_OK);
    shatter_clock_input clock{};
    clock.local_now_utc = seen.now - 6 * 60;
    clock.last_seen_utc = 0;  // ignorado: o last_seen vem do save
    shatter_offline_window window{};
    const std::string request = TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_save_expedition_request(db.db, save.save, 0, &clock, &window, o, c, n, &err);
    });
    EXPECT_EQ(window.ended_by_rollback, 1);
    EXPECT_NEAR(window.effective_seconds, 2 * 3600.0, 0.0);
    EXPECT_TRUE(Parse(request)["ended_by_rollback"].AsBool());
    const json::Value result = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_expedition_simulate(db.db, request.data(), request.size(), 0, o, c, n, &err);
    }));
    EXPECT_EQ(result["stop"].AsString(), std::string("clock_rollback"));
    // T − 4 min: segue normal.
    clock.local_now_utc = seen.now - 4 * 60;
    const std::string normal = TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_save_expedition_request(db.db, save.save, 0, &clock, &window, o, c, n, &err);
    });
    EXPECT_EQ(window.ended_by_rollback, 0);
    EXPECT_FALSE(Parse(normal)["ended_by_rollback"].AsBool());
}

TEST(c_api_golden_expeditions_same_hash_through_the_dll) {
    // O mesmo arquivo golden do CMake (e do teste Rules.GoldenExpedition do Unity): a DLL dá o mesmo resultHash.
    DbHandle db(tu::RichDir());
    struct Case { const char* name; int hours; std::uint64_t seed; int level; std::int64_t potions; };
    const Case cases[] = {{"crypt_1h_seed1", 1, 1, 1, 3}, {"crypt_4h_seed2", 4, 2, 1, 3}, {"crypt_12h_seed3", 12, 3, 1, 3},
                          {"crypt_2h_level6_capped", 2, 4, 6, 3}, {"crypt_1h_no_potions", 1, 5, 1, 0}};
    const std::string golden = tu::ReadFile(tu::DataDir() + "/golden/expeditions.txt");
    ASSERT_TRUE(!golden.empty());
    shatter_error err{};
    for (const Case& c : cases) {
        const std::string req = S(ExpeditionRequestToJson(tu::MakeRequest(tu::RichDb(), c.hours, c.seed, c.level, c.potions)));
        const json::Value r = Parse(TwoCalls([&](std::uint8_t* o, std::size_t cap, std::size_t* n) {
            return shatter_expedition_simulate(db.db, req.data(), req.size(), 0, o, cap, n, &err);
        }));
        const std::string expect = std::string(c.name) + " hash=" + r["result_hash"].AsString() + " ";
        if (golden.find(expect) == std::string::npos) FAIL(std::string("golden divergiu pela DLL: ") + c.name);
    }
}

// =============================================================================================
// API C 1.1 (shatter_c.h): poções, esquiva, stun, elite, chefe, Único, vitals e tempos, confiança do resultado
// =============================================================================================
namespace {

struct StatHandle {
    shatter_statblock* sb = nullptr;
    ~StatHandle() { shatter_statblock_destroy(sb); }
    StatHandle() = default;
    StatHandle(const StatHandle&) = delete;
    StatHandle& operator=(const StatHandle&) = delete;
};

struct FxHandle {
    shatter_effects* fx = nullptr;
    FxHandle() { shatter_effects_create(&fx); }
    ~FxHandle() { shatter_effects_destroy(fx); }
    FxHandle(const FxHandle&) = delete;
    FxHandle& operator=(const FxHandle&) = delete;
};

struct ActorHandle {
    shatter_actor* a = nullptr;
    ~ActorHandle() { shatter_actor_destroy(a); }
    ActorHandle() = default;
    ActorHandle(const ActorHandle&) = delete;
    ActorHandle& operator=(const ActorHandle&) = delete;
};

struct PotionsHandle {
    shatter_potions* p = nullptr;
    ~PotionsHandle() { shatter_potions_destroy(p); }
    PotionsHandle() = default;
    PotionsHandle(const PotionsHandle&) = delete;
    PotionsHandle& operator=(const PotionsHandle&) = delete;
};

struct BossHandle {
    shatter_boss* b = nullptr;
    ~BossHandle() { shatter_boss_destroy(b); }
    BossHandle() = default;
    BossHandle(const BossHandle&) = delete;
    BossHandle& operator=(const BossHandle&) = delete;
};

}  // namespace

TEST(c_api_11_minor_version_ext_layout_and_rules_ext) {
    EXPECT_EQ(shatter_api_version(), 1u);              // a v1 não mudou de forma incompatível
    EXPECT_EQ(shatter_api_minor(), SHATTER_C_API_MINOR);
    std::size_t needed = 0;
    EXPECT_EQ(shatter_layout_info_ext(nullptr, 0, &needed), SHATTER_BUFFER_TOO_SMALL);
    EXPECT_EQ(needed, static_cast<std::size_t>(SHATTER_LAYOUT_EXT_COUNT));
    std::vector<std::uint32_t> layout(needed);
    ASSERT_EQ(shatter_layout_info_ext(layout.data(), layout.size(), &needed), SHATTER_OK);
    EXPECT_EQ(layout[0], static_cast<std::uint32_t>(sizeof(shatter_rules_ext)));
    shatter_error err{};
    EXPECT_EQ(shatter_layout_check_ext(layout.data(), layout.size(), &err), SHATTER_OK);
    layout[5] += 4;
    EXPECT_EQ(shatter_layout_check_ext(layout.data(), layout.size(), &err), SHATTER_VERSION_MISMATCH);
    EXPECT_EQ(err.line, 6);
    EXPECT_EQ(shatter_layout_check_ext(layout.data(), layout.size() - 1, &err), SHATTER_VERSION_MISMATCH);
    EXPECT_EQ(shatter_layout_info_ext(layout.data(), layout.size(), nullptr), SHATTER_INVALID_ARGUMENT);
    // O layout da v1 continua com a mesma contagem (o C# da v1 segue valendo).
    EXPECT_EQ(SHATTER_LAYOUT_COUNT, 82u);

    DbHandle db(tu::RichDir());
    const RulesConstants& r = tu::RichDb().Rules();
    shatter_rules_ext x{};
    ASSERT_EQ(shatter_db_rules_ext(db.db, &x), SHATTER_OK);
    EXPECT_EQ(x.dodge_max_charges, r.dodgeMaxCharges);
    EXPECT_NEAR(x.dodge_recharge, r.dodgeRecharge, 0.0);
    EXPECT_NEAR(x.dodge_duration, 0.35, 0.0);
    EXPECT_NEAR(x.dodge_iframes, 0.2, 0.0);
    EXPECT_NEAR(x.dodge_buffer, 0.1, 0.0);
    EXPECT_NEAR(x.guard_break_stagger_seconds, 1.5, 0.0);
    EXPECT_NEAR(x.guard_break_immunity_boss, 8.0, 0.0);
    EXPECT_NEAR(x.boss_shield_down_seconds, 5.0, 0.0);
    EXPECT_NEAR(x.elite_xp_mult, 3.0, 0.0);
    EXPECT_NEAR(x.potion_lockout, 1.0, 0.0);
    EXPECT_NEAR(x.out_of_combat_seconds, r.outOfCombatSeconds, 0.0);
    EXPECT_EQ(shatter_db_rules_ext(db.db, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_db_rules_ext(nullptr, &x), SHATTER_INVALID_ARGUMENT);
}

TEST(c_api_11_vitals_timing_move_pick_attack_and_hit_with_db_rules) {
    DbHandle db(tu::RichDir());
    const ContentDB& cdb = tu::RichDb();
    SaveHandle save = MakeSave(db.db);
    StatHandle hero;
    shatter_error err{};
    ASSERT_EQ(shatter_statblock_from_save(db.db, save.save, 0, &hero.sb, &err), SHATTER_OK);
    StatBlock csb;
    ASSERT_TRUE(BuildStatBlock(cdb, tu::MakeWarrior(cdb, 3), csb));
    const std::string cls = "class.warrior";
    shatter_vitals v{};
    ASSERT_EQ(shatter_vitals_create(db.db, hero.sb, cls.data(), cls.size(), &v), SHATTER_OK);
    Vitals cv = CreateVitals(csb, cdb.FindClass(cls));
    EXPECT_NEAR(v.life, cv.life, 0.0);
    EXPECT_NEAR(v.resource, cv.resource, 0.0);
    v.life -= 20.0;
    cv.life -= 20.0;
    ASSERT_EQ(shatter_vitals_tick(db.db, &v, hero.sb, cls.data(), cls.size(), 0.5, 0), SHATTER_OK);
    TickVitals(cv, csb, cdb.FindClass(cls), 0.5, false);
    EXPECT_NEAR(v.life, cv.life, 0.0);
    EXPECT_NEAR(v.resource, cv.resource, 0.0);
    ASSERT_EQ(shatter_vitals_gain_resource(&v, hero.sb, 40.0), SHATTER_OK);
    GainResource(cv, csb, 40.0);
    EXPECT_NEAR(v.resource, cv.resource, 0.0);
    std::uint8_t ok = 9;
    ASSERT_EQ(shatter_vitals_spend_resource(&v, 1e9, &ok), SHATTER_OK);
    EXPECT_EQ(ok, 0);
    EXPECT_NEAR(v.resource, cv.resource, 0.0);
    ASSERT_EQ(shatter_vitals_spend_resource(&v, 10.0, &ok), SHATTER_OK);
    EXPECT_EQ(ok, 1);
    EXPECT_NEAR(v.resource, cv.resource - 10.0, 1e-12);
    EXPECT_EQ(shatter_vitals_create(db.db, hero.sb, "class.nope", 10, &v), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_vitals_create(db.db, nullptr, cls.data(), cls.size(), &v), SHATTER_INVALID_ARGUMENT);

    // Tempos de ação = ComputeActionTiming; elite Veloz: o telegraph não encurta.
    shatter_action_timing t{};
    const std::string cleave = "skill.warrior.cleave";
    ASSERT_EQ(shatter_skill_timing(db.db, cleave.data(), cleave.size(), hero.sb, nullptr, 0, &t), SHATTER_OK);
    const ActionTimingInfo ct = ComputeActionTiming(cdb, *cdb.FindSkill(cleave), csb);
    EXPECT_NEAR(t.windup, ct.windup, 0.0);
    EXPECT_NEAR(t.recovery, ct.recovery, 0.0);
    EXPECT_NEAR(t.cooldown, 3.0, 0.0);
    EXPECT_NEAR(t.cost, 20.0, 0.0);
    EXPECT_EQ(shatter_skill_timing(db.db, "skill.nope", 10, hero.sb, nullptr, 0, &t), SHATTER_NOT_FOUND);
    double speed = 0.0;
    ASSERT_EQ(shatter_move_speed(hero.sb, 450.0, &speed), SHATTER_OK);
    EXPECT_NEAR(speed, MoveSpeedUu(csb, 450.0), 0.0);
    std::uint8_t can = 0;
    ASSERT_EQ(shatter_can_act(hero.sb, nullptr, &can), SHATTER_OK);
    EXPECT_EQ(can, 1);
    ASSERT_EQ(shatter_can_move(hero.sb, nullptr, &can), SHATTER_OK);
    EXPECT_EQ(can, 1);

    // Próximo ataque do inimigo: mesma escolha e mesma posição do fluxo que o C++.
    const std::string boss = "enemy.crypt_guardian";
    shatter_rng rng{};
    ASSERT_EQ(shatter_rng_for_stream(7, SHATTER_RNG_EVENTS, 0, &rng), SHATTER_OK);
    Pcg32 cr = Pcg32::ForStream(7, RngStream::Events, 0);
    for (int i = 0; i < 50; ++i) {
        std::int32_t pick = -2;
        ASSERT_EQ(shatter_pick_attack(db.db, boss.data(), boss.size(), &rng, &pick), SHATTER_OK);
        EXPECT_EQ(pick, PickEnemyAttack(*cdb.FindEnemy(boss), cr));
    }
    EXPECT_EQ(rng.state, cr.State());

    // Golpe lendo as constantes do banco: igual ao golpe com a struct do banco.
    shatter_rules rules{};
    ASSERT_EQ(shatter_db_rules(db.db, &rules), SHATTER_OK);
    StatHandle enemy;
    const std::string sent = "enemy.hollow_sentinel";
    ASSERT_EQ(shatter_statblock_for_enemy(db.db, sent.data(), sent.size(), 3, &enemy.sb), SHATTER_OK);
    shatter_hit_input in{};
    in.base_damage[0] = 20.0;
    in.coefficient = 1.0;
    in.defender_life = 100.0;
    in.can_be_blocked = 1;
    shatter_rng r1{}, r2{};
    shatter_rng_for_stream(5, SHATTER_RNG_COMBAT, 0, &r1);
    r2 = r1;
    shatter_hit_result h1{}, h2{};
    ASSERT_EQ(shatter_resolve_hit(hero.sb, enemy.sb, &in, &rules, &r1, &h1), SHATTER_OK);
    ASSERT_EQ(shatter_resolve_hit_db(db.db, hero.sb, enemy.sb, &in, &r2, &h2), SHATTER_OK);
    EXPECT_NEAR(h1.total_damage, h2.total_damage, 0.0);
    EXPECT_EQ(r1.state, r2.state);
    double cd = 0.0;
    ASSERT_EQ(shatter_effective_cooldown_db(db.db, 3.0, 1.0, &cd), SHATTER_OK);
    EXPECT_NEAR(cd, 3.0, 0.0);
    EXPECT_EQ(shatter_resolve_hit_db(nullptr, hero.sb, enemy.sb, &in, &r2, &h2), SHATTER_INVALID_ARGUMENT);
}

TEST(c_api_11_potions_belt_use_tick_elite_refill_and_save_roundtrip) {
    DbHandle db(tu::RichDir());
    SaveHandle save = MakeSave(db.db);
    StatHandle hero;
    shatter_error err{};
    ASSERT_EQ(shatter_statblock_from_save(db.db, save.save, 0, &hero.sb, &err), SHATTER_OK);
    shatter_vitals v{};
    const std::string cls = "class.warrior";
    ASSERT_EQ(shatter_vitals_create(db.db, hero.sb, cls.data(), cls.size(), &v), SHATTER_OK);
    double maxLife = 0.0;
    ASSERT_EQ(shatter_statblock_get(hero.sb, SHATTER_STAT_LIFE, 0, &maxLife), SHATTER_OK);
    v.life = maxLife * 0.2;

    PotionsHandle belt;
    ASSERT_EQ(shatter_potions_from_save(db.db, save.save, 0, &belt.p), SHATTER_OK);
    const std::string life = "potion.life", ward = "potion.ward";
    shatter_potion_outcome o{};
    ASSERT_EQ(shatter_potions_use(db.db, belt.p, life.data(), life.size(), hero.sb, &v, &o), SHATTER_OK);
    EXPECT_EQ(o.status, SHATTER_POTION_OK);
    EXPECT_NEAR(o.heal_amount, maxLife * 0.4, 1e-9);
    EXPECT_NEAR(v.life, maxLife * 0.6, 1e-9);
    EXPECT_NEAR(o.lockout, 1.0, 0.0);
    // Trava global: outra poção, mesmo de outro tipo, é recusada sem gastar carga.
    ASSERT_EQ(shatter_potions_use(db.db, belt.p, ward.data(), ward.size(), hero.sb, &v, &o), SHATTER_OK);
    EXPECT_EQ(o.status, SHATTER_POTION_LOCKED_OUT);
    EXPECT_NEAR(v.barrier, 0.0, 0.0);
    ASSERT_EQ(shatter_potions_tick(db.db, belt.p, 1.0), SHATTER_OK);
    ASSERT_EQ(shatter_potions_use(db.db, belt.p, ward.data(), ward.size(), hero.sb, &v, &o), SHATTER_OK);
    EXPECT_EQ(o.status, SHATTER_POTION_OK);
    EXPECT_NEAR(v.barrier, maxLife * 0.3, 1e-9);
    EXPECT_NEAR(v.barrier_seconds_left, 6.0, 0.0);
    EXPECT_NEAR(o.barrier_amount, maxLife * 0.3, 1e-9);
    ASSERT_EQ(shatter_potions_use(db.db, belt.p, "potion.nope", 11, hero.sb, &v, &o), SHATTER_OK);
    EXPECT_EQ(o.status, SHATTER_POTION_UNKNOWN);
    // Estado do cinto em JSON.
    const json::Value info = Parse(TwoCalls([&](std::uint8_t* b, std::size_t c, std::size_t* n) { return shatter_potions_info_json(db.db, belt.p, b, c, n); }));
    EXPECT_EQ(info["slots"].Size(), static_cast<std::size_t>(2));
    EXPECT_EQ(info["slots"].At(0)["potion_id"].AsString(), life);
    EXPECT_EQ(info["slots"].At(0)["charges"].AsInt(), static_cast<std::int64_t>(2));
    EXPECT_EQ(info["slots"].At(0)["max_charges"].AsInt(), static_cast<std::int64_t>(3));
    EXPECT_EQ(info["slots"].At(1)["charges"].AsInt(), static_cast<std::int64_t>(1));
    EXPECT_TRUE(info["lockout_remaining"].AsDouble() > 0.9);
    // Elite morto: +1 carga na poção com menos cargas (Resguardo 1 < Vida 2).
    std::uint8_t added = 0;
    ASSERT_EQ(shatter_potions_on_elite_killed(db.db, belt.p, &added), SHATTER_OK);
    EXPECT_EQ(added, 1);
    // Grava no save e volta: as cargas e a recarga atravessam o save.
    ASSERT_EQ(shatter_potions_to_save(belt.p, save.save, 0), SHATTER_OK);
    const json::Value file = Parse(TwoCalls([&](std::uint8_t* b, std::size_t c, std::size_t* n) { return shatter_save_to_json(save.save, 0, b, c, n); }));
    const json::Value& slots = file["data"]["characters"].At(0)["potion_slots"];
    ASSERT_TRUE(slots.Size() == 2);
    EXPECT_EQ(slots.At(0)["charges"].AsInt(), static_cast<std::int64_t>(2));
    EXPECT_EQ(slots.At(1)["charges"].AsInt(), static_cast<std::int64_t>(2));
    EXPECT_TRUE(slots.At(0)["recharge_remaining"].AsDouble() > 0.0);
    PotionsHandle again;
    ASSERT_EQ(shatter_potions_from_save(db.db, save.save, 0, &again.p), SHATTER_OK);
    const json::Value info2 = Parse(TwoCalls([&](std::uint8_t* b, std::size_t c, std::size_t* n) { return shatter_potions_info_json(db.db, again.p, b, c, n); }));
    EXPECT_EQ(info2["slots"].At(0)["charges"].AsInt(), static_cast<std::int64_t>(2));
    EXPECT_NEAR(info2["lockout_remaining"].AsDouble(), 0.0, 0.0);              // a trava não é salva
    ASSERT_EQ(shatter_potions_refill(db.db, again.p), SHATTER_OK);
    const json::Value full = Parse(TwoCalls([&](std::uint8_t* b, std::size_t c, std::size_t* n) { return shatter_potions_info_json(db.db, again.p, b, c, n); }));
    EXPECT_EQ(full["slots"].At(0)["charges"].AsInt(), static_cast<std::int64_t>(3));
    // Poção pura (sem cinto) e argumentos inválidos.
    shatter_vitals pv = v;
    pv.life = 1.0;
    shatter_potion_outcome po{};
    ASSERT_EQ(shatter_potion_resolve(db.db, life.data(), life.size(), hero.sb, &pv, &po), SHATTER_OK);
    EXPECT_NEAR(pv.life, 1.0 + maxLife * 0.4, 1e-9);
    EXPECT_EQ(shatter_potion_resolve(db.db, "potion.nope", 11, hero.sb, &pv, &po), SHATTER_NOT_FOUND);
    EXPECT_EQ(shatter_potions_use(db.db, nullptr, life.data(), life.size(), hero.sb, &v, &o), SHATTER_INVALID_ARGUMENT);
    shatter_potions* invalid = nullptr;  // variável própria: a API zera *out antes de recusar (contrato); `again` não pode perder o dono (LeakSanitizer)
    EXPECT_EQ(shatter_potions_from_save(db.db, save.save, 9, &invalid), SHATTER_INVALID_ARGUMENT);
    EXPECT_TRUE(invalid == nullptr);
    shatter_potions_destroy(nullptr);
}

TEST(c_api_11_dodge_state_charges_iframes_and_perfect_reward) {
    DbHandle db(tu::RichDir());
    shatter_dodge_state d{};
    ASSERT_EQ(shatter_dodge_init(db.db, &d), SHATTER_OK);
    EXPECT_EQ(d.charges, 3);
    std::int32_t status = -1;
    ASSERT_EQ(shatter_dodge_start(db.db, &d, 0.0, &status), SHATTER_OK);
    EXPECT_EQ(status, SHATTER_DODGE_OK);
    EXPECT_EQ(d.charges, 2);
    std::uint8_t inv = 0;
    ASSERT_EQ(shatter_dodge_invulnerable(db.db, &d, &inv), SHATTER_OK);
    EXPECT_EQ(inv, 1);
    double reward = 0.0;
    ASSERT_EQ(shatter_dodge_perfect_reward(db.db, &d, &reward), SHATTER_OK);
    EXPECT_NEAR(reward, 10.0, 0.0);
    ASSERT_EQ(shatter_dodge_start(db.db, &d, 0.0, &status), SHATTER_OK);
    EXPECT_EQ(status, SHATTER_DODGE_ACTIVE);
    ASSERT_EQ(shatter_dodge_tick(db.db, &d, 0.3), SHATTER_OK);
    ASSERT_EQ(shatter_dodge_invulnerable(db.db, &d, &inv), SHATTER_OK);
    EXPECT_EQ(inv, 0);
    ASSERT_EQ(shatter_dodge_perfect_reward(db.db, &d, &reward), SHATTER_OK);
    EXPECT_NEAR(reward, 0.0, 0.0);
    ASSERT_EQ(shatter_dodge_tick(db.db, &d, 0.1), SHATTER_OK);
    EXPECT_EQ(d.active, 0);
    for (int i = 0; i < 2; ++i) {
        ASSERT_EQ(shatter_dodge_start(db.db, &d, 0.0, &status), SHATTER_OK);
        ASSERT_EQ(shatter_dodge_tick(db.db, &d, 0.4), SHATTER_OK);
    }
    ASSERT_EQ(shatter_dodge_start(db.db, &d, 0.0, &status), SHATTER_OK);
    EXPECT_EQ(status, SHATTER_DODGE_NO_CHARGES);
    EXPECT_EQ(shatter_dodge_start(db.db, nullptr, 0.0, &status), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_dodge_tick(db.db, &d, std::nan("")), SHATTER_INVALID_ARGUMENT);
}

TEST(c_api_11_actor_stun_guard_break_stagger_and_immunities) {
    DbHandle db(tu::RichDir());
    const std::string common = "enemy.hollow_sentinel", eliteFixed = "enemy.shielded_sentinel";
    const std::string stun = "effect.stun", gb = "effect.guard_break", src = "player";
    // Comum: stun real que interrompe e zera a velocidade de ataque.
    {
        StatHandle sb;
        ASSERT_EQ(shatter_statblock_for_enemy(db.db, common.data(), common.size(), 3, &sb.sb), SHATTER_OK);
        FxHandle fx;
        ActorHandle actor;
        ASSERT_EQ(shatter_actor_create(db.db, common.data(), common.size(), 0, &actor.a), SHATTER_OK);
        shatter_actor_apply ap{};
        ASSERT_EQ(shatter_actor_apply_effect(actor.a, db.db, stun.data(), stun.size(), src.data(), src.size(), 1.0, fx.fx, sb.sb, &ap), SHATTER_OK);
        EXPECT_EQ(ap.stunned, 1);
        EXPECT_EQ(ap.interrupted, 1);
        EXPECT_NEAR(ap.stun_seconds, 0.8, 0.0);
        std::uint8_t can = 1;
        ASSERT_EQ(shatter_can_act(sb.sb, actor.a, &can), SHATTER_OK);
        EXPECT_EQ(can, 0);
        shatter_actor_info info{};
        ASSERT_EQ(shatter_actor_info_get(actor.a, &info), SHATTER_OK);
        EXPECT_NEAR(info.stun_remaining, 0.8, 0.0);
        std::uint8_t ended = 9;
        std::size_t evs = 0;
        ASSERT_EQ(shatter_effects_tick(fx.fx, db.db, 0.9, sb.sb, &evs), SHATTER_OK);
        ASSERT_EQ(shatter_actor_tick(actor.a, 0.9, sb.sb, &ended), SHATTER_OK);
        ASSERT_EQ(shatter_can_act(sb.sb, actor.a, &can), SHATTER_OK);
        EXPECT_EQ(can, 1);
    }
    // Elite sorteado (flag) e fixo: imunes ao stun; sofrem Guarda Quebrada com stagger no 3º acúmulo.
    for (int mode = 0; mode < 2; ++mode) {
        const std::string& id = mode == 0 ? eliteFixed : common;
        StatHandle sb;
        ASSERT_EQ(shatter_statblock_for_enemy(db.db, id.data(), id.size(), 3, &sb.sb), SHATTER_OK);
        FxHandle fx;
        ActorHandle actor;
        ASSERT_EQ(shatter_actor_create(db.db, id.data(), id.size(), mode == 1 ? 1 : 0, &actor.a), SHATTER_OK);
        shatter_actor_apply ap{};
        ASSERT_EQ(shatter_actor_apply_effect(actor.a, db.db, stun.data(), stun.size(), src.data(), src.size(), 1.0, fx.fx, sb.sb, &ap), SHATTER_OK);
        EXPECT_EQ(ap.stun_blocked, 1);
        EXPECT_EQ(ap.applied, 0);
        for (int i = 1; i <= 3; ++i) {
            ASSERT_EQ(shatter_actor_apply_effect(actor.a, db.db, gb.data(), gb.size(), src.data(), src.size(), 1.0, fx.fx, sb.sb, &ap), SHATTER_OK);
            EXPECT_EQ(ap.staggered, i == 3 ? 1 : 0);
            EXPECT_EQ(ap.guard_break_stacks, i == 3 ? 0 : i);
        }
        EXPECT_EQ(ap.remove_barrier, 1);
        EXPECT_EQ(ap.interrupted, 1);
        EXPECT_NEAR(ap.stagger_seconds, 1.5, 0.0);
        shatter_actor_info info{};
        ASSERT_EQ(shatter_actor_info_get(actor.a, &info), SHATTER_OK);
        EXPECT_EQ(info.can_act, 0);
        EXPECT_EQ(info.stun_immune, 1);
        EXPECT_NEAR(info.immunity_remaining, 4.0, 0.0);
        std::uint8_t ended = 0;
        ASSERT_EQ(shatter_actor_tick(actor.a, 1.6, sb.sb, &ended), SHATTER_OK);
        EXPECT_EQ(ended, 1);
        double taken = 0.0;
        ASSERT_EQ(shatter_statblock_get(sb.sb, SHATTER_STAT_DAMAGE_TAKEN, 0, &taken), SHATTER_OK);
        EXPECT_NEAR(taken, 1.0, 1e-9);
    }
    shatter_actor* none = nullptr;
    EXPECT_EQ(shatter_actor_create(db.db, "enemy.nope", 10, 0, &none), SHATTER_NOT_FOUND);
    EXPECT_TRUE(none == nullptr);
}

TEST(c_api_11_elite_roll_profile_and_apply) {
    DbHandle db(tu::RichDir());
    const ContentDB& cdb = tu::RichDb();
    shatter_rng rng{};
    ASSERT_EQ(shatter_rng_for_stream(11, SHATTER_RNG_EVENTS, 3, &rng), SHATTER_OK);
    Pcg32 cr = Pcg32::ForStream(11, RngStream::Events, 3);
    for (int i = 0; i < 30; ++i) {
        shatter_elite_info e{};
        ASSERT_EQ(shatter_elite_roll(db.db, &rng, &e), SHATTER_OK);
        const EliteModifierData* m = RollEliteModifier(cdb, cr);
        ASSERT_TRUE(m != nullptr);
        EXPECT_EQ(std::string(e.modifier_id), m->id);
        EXPECT_EQ(e.rolled, 1);
        EXPECT_NEAR(e.life_mult, 2.0, 0.0);
        EXPECT_NEAR(e.xp_mult, 3.0, 0.0);
    }
    EXPECT_EQ(rng.state, cr.State());
    shatter_elite_info fixed{};
    const std::string shield = "modifier.elite.shield";
    ASSERT_EQ(shatter_elite_profile(db.db, shield.data(), shield.size(), 0, &fixed), SHATTER_OK);
    EXPECT_NEAR(fixed.life_mult, 1.0, 0.0);
    EXPECT_NEAR(fixed.barrier_fraction_of_life, 0.4, 0.0);
    StatHandle sb;
    const std::string sent = "enemy.hollow_sentinel";
    ASSERT_EQ(shatter_statblock_for_enemy(db.db, sent.data(), sent.size(), 3, &sb.sb), SHATTER_OK);
    double before = 0.0, after = 0.0, barrier = 0.0;
    shatter_statblock_get(sb.sb, SHATTER_STAT_LIFE, 0, &before);
    shatter_elite_info rolled{};
    ASSERT_EQ(shatter_elite_profile(db.db, shield.data(), shield.size(), 1, &rolled), SHATTER_OK);
    ASSERT_EQ(shatter_elite_apply(db.db, &rolled, sb.sb, &barrier), SHATTER_OK);
    shatter_statblock_get(sb.sb, SHATTER_STAT_LIFE, 0, &after);
    EXPECT_NEAR(after, before * 2.0, 1e-9);
    EXPECT_NEAR(barrier, after * 0.4, 1e-9);
    // Modificador acelerado: o telegraph não encurta pela API também (o bloco do elite já tem os mods de shatter_elite_apply).
    StatHandle swiftSb;
    ASSERT_EQ(shatter_statblock_for_enemy(db.db, sent.data(), sent.size(), 3, &swiftSb.sb), SHATTER_OK);
    shatter_action_timing plain{}, swift{};
    const std::string strike = "skill.enemy.sentinel_strike", mod = "modifier.elite.swift";
    ASSERT_EQ(shatter_skill_timing(db.db, strike.data(), strike.size(), swiftSb.sb, nullptr, 0, &plain), SHATTER_OK);
    shatter_elite_info swiftInfo{};
    ASSERT_EQ(shatter_elite_profile(db.db, mod.data(), mod.size(), 0, &swiftInfo), SHATTER_OK);
    double swiftBarrier = -1.0;
    ASSERT_EQ(shatter_elite_apply(db.db, &swiftInfo, swiftSb.sb, &swiftBarrier), SHATTER_OK);
    EXPECT_NEAR(swiftBarrier, 0.0, 0.0);
    ASSERT_EQ(shatter_skill_timing(db.db, strike.data(), strike.size(), swiftSb.sb, mod.data(), mod.size(), &swift), SHATTER_OK);
    EXPECT_NEAR(swift.windup, plain.windup, 1e-12);
    EXPECT_NEAR(swift.impact, plain.impact / 1.25, 1e-12);
    EXPECT_NEAR(swift.recovery, plain.recovery * 0.8 / 1.25, 1e-12);
    EXPECT_EQ(shatter_elite_profile(db.db, "modifier.elite.nope", 19, 0, &fixed), SHATTER_NOT_FOUND);
    EXPECT_EQ(shatter_elite_roll(db.db, nullptr, &fixed), SHATTER_INVALID_ARGUMENT);
}

TEST(c_api_11_boss_fight_events_shield_damage_phase_and_effects) {
    DbHandle db(tu::RichDir());
    const std::string id = "enemy.crypt_guardian";
    BossHandle boss;
    ASSERT_EQ(shatter_boss_create(db.db, id.data(), id.size(), 4, 2026, &boss.b), SHATTER_OK);
    StatHandle sb;
    ASSERT_EQ(shatter_statblock_for_enemy(db.db, id.data(), id.size(), 4, &sb.sb), SHATTER_OK);
    FxHandle fx;
    shatter_boss_info info{};
    ASSERT_EQ(shatter_boss_info_get(boss.b, &info), SHATTER_OK);
    EXPECT_EQ(info.state, SHATTER_BOSS_IDLE);
    EXPECT_EQ(info.phase, 1);
    EXPECT_NEAR(info.max_life, 600.0 + 60.0 * 3.0, 1e-9);
    ASSERT_EQ(shatter_boss_start(boss.b), SHATTER_OK);
    shatter_boss_context ctx{};
    ctx.player = {0.0, 1000.0};
    std::size_t count = 0;
    std::vector<shatter_boss_event> all;
    auto step = [&](int n) {
        for (int i = 0; i < n; ++i) {
            ASSERT_EQ(shatter_boss_step(boss.b, 1.0 / 60.0, &ctx, sb.sb, &count), SHATTER_OK);
            if (count > 0) {
                std::vector<shatter_boss_event> ev(count);
                std::size_t needed = 0;
                ASSERT_EQ(shatter_boss_events(boss.b, ev.data(), ev.size(), &needed), SHATTER_OK);
                for (const auto& e : ev) all.push_back(e);
            }
        }
    };
    step(1);
    // Escudo: de frente 0 de dano; por trás entra.
    shatter_boss_damage dmg{};
    ASSERT_EQ(shatter_boss_apply_damage(boss.b, 30.0, {0.0, 0.0}, {10.0, 400.0}, &dmg), SHATTER_OK);
    EXPECT_EQ(dmg.shield_blocked, 1);
    std::uint8_t covers = 0;
    ASSERT_EQ(shatter_boss_shield_covers(boss.b, {0.0, 0.0}, {0.0, -400.0}, &covers), SHATTER_OK);
    EXPECT_EQ(covers, 0);
    ASSERT_EQ(shatter_boss_apply_damage(boss.b, 30.0, {0.0, 0.0}, {0.0, -400.0}, &dmg), SHATTER_OK);
    EXPECT_EQ(dmg.shield_blocked, 0);
    EXPECT_NEAR(dmg.applied, 30.0, 0.0);
    // Padrões saem como eventos com os ids do CSV.
    step(60 * 4);
    bool sawStart = false;
    for (const auto& e : all)
        if (e.kind == SHATTER_BOSS_EVT_PATTERN_START) {
            sawStart = true;
            EXPECT_TRUE(std::string(e.pattern_id).rfind("pattern.guardian.", 0) == 0);
            EXPECT_TRUE(std::string(e.skill_id).rfind("skill.enemy.guardian_", 0) == 0);
            EXPECT_TRUE(e.seconds > 0.0);
        }
    EXPECT_TRUE(sawStart);
    // Guarda Quebrada: 3 acúmulos derrubam o escudo e atordoam.
    const std::string gb = "effect.guard_break", src = "player";
    shatter_actor_apply ap{};
    for (int i = 0; i < 3; ++i)
        ASSERT_EQ(shatter_boss_apply_effect(boss.b, db.db, gb.data(), gb.size(), src.data(), src.size(), 1.0, fx.fx, sb.sb, &ap), SHATTER_OK);
    EXPECT_EQ(ap.staggered, 1);
    ASSERT_EQ(shatter_boss_info_get(boss.b, &info), SHATTER_OK);
    EXPECT_EQ(info.state, SHATTER_BOSS_STAGGER);
    EXPECT_EQ(info.shield_up, 0);
    EXPECT_NEAR(info.shield_down_remaining, 5.0, 1e-9);
    std::size_t needed = 0;
    ASSERT_EQ(shatter_boss_events(boss.b, nullptr, 0, &needed), SHATTER_BUFFER_TOO_SMALL);
    EXPECT_TRUE(needed >= 2);
    // Chefe imune ao stun.
    const std::string stun = "effect.stun";
    ASSERT_EQ(shatter_boss_apply_effect(boss.b, db.db, stun.data(), stun.size(), src.data(), src.size(), 1.0, fx.fx, sb.sb, &ap), SHATTER_OK);
    EXPECT_EQ(ap.stun_blocked, 1);
    // Fase 2: dano excedente cortado em 50%, rugido invulnerável e 2 invocadas.
    step(60 * 2);
    all.clear();
    ASSERT_EQ(shatter_boss_apply_damage(boss.b, 5000.0, {0.0, 0.0}, {0.0, -400.0}, &dmg), SHATTER_OK);
    EXPECT_EQ(dmg.clamped_by_phase, 1);
    ASSERT_EQ(shatter_boss_info_get(boss.b, &info), SHATTER_OK);
    EXPECT_NEAR(info.life, info.max_life * 0.5, 1e-9);
    step(60 * 8);
    int spawns = 0;
    for (const auto& e : all)
        if (e.kind == SHATTER_BOSS_EVT_SUMMON_SPAWN) {
            ++spawns;
            EXPECT_EQ(e.count, 2);
            EXPECT_EQ(std::string(e.enemy_id), std::string("enemy.hollow_sentinel"));
        }
    EXPECT_EQ(spawns, 1);
    ASSERT_EQ(shatter_boss_info_get(boss.b, &info), SHATTER_OK);
    EXPECT_EQ(info.phase, 2);
    ASSERT_EQ(shatter_boss_reset(boss.b, sb.sb), SHATTER_OK);
    ASSERT_EQ(shatter_boss_info_get(boss.b, &info), SHATTER_OK);
    EXPECT_EQ(info.phase, 1);
    EXPECT_NEAR(info.life, info.max_life, 0.0);
    // Argumentos inválidos e chefe sem fases.
    EXPECT_EQ(shatter_boss_step(nullptr, 0.1, &ctx, sb.sb, &count), SHATTER_INVALID_ARGUMENT);
    ctx.boss.x = std::nan("");
    EXPECT_EQ(shatter_boss_step(boss.b, 0.1, &ctx, sb.sb, &count), SHATTER_INVALID_ARGUMENT);
    shatter_boss* none = nullptr;
    const std::string common = "enemy.hollow_sentinel";
    EXPECT_EQ(shatter_boss_create(db.db, common.data(), common.size(), 3, 1, &none), SHATTER_CONTENT_INVALID);
    EXPECT_TRUE(none == nullptr);
    EXPECT_EQ(shatter_boss_create(db.db, "enemy.nope", 10, 3, 1, &none), SHATTER_NOT_FOUND);
    shatter_boss_destroy(nullptr);
}

TEST(c_api_11_boss_loot_progress_persists_and_buffer_too_small_changes_nothing) {
    DbHandle db(tu::RichDir());
    SaveHandle save = MakeSave(db.db);
    const std::string boss = "enemy.crypt_guardian";
    shatter_boss_progress p{};
    ASSERT_EQ(shatter_save_boss_progress_get(save.save, 0, boss.data(), boss.size(), &p), SHATTER_OK);
    EXPECT_EQ(p.kills, 0);
    shatter_rng rng{};
    ASSERT_EQ(shatter_rng_for_stream(31, SHATTER_RNG_LOOT, 0, &rng), SHATTER_OK);
    const shatter_rng rngBefore = rng;
    shatter_save_summary sum{};
    ASSERT_EQ(shatter_save_summary_get(save.save, &sum), SHATTER_OK);
    const std::uint64_t uidBefore = sum.next_item_uid;
    shatter_error err{};
    std::size_t needed = 0;
    // Buffer pequeno: nada muda (nem rng, nem contador, nem uid).
    EXPECT_EQ(shatter_save_roll_boss_loot(db.db, save.save, 0, boss.data(), boss.size(), 3, &rng, nullptr, 0, &needed, &err), SHATTER_BUFFER_TOO_SMALL);
    EXPECT_TRUE(needed > 0);
    EXPECT_EQ(rng.state, rngBefore.state);
    ASSERT_EQ(shatter_save_boss_progress_get(save.save, 0, boss.data(), boss.size(), &p), SHATTER_OK);
    EXPECT_EQ(p.kills, 0);
    ASSERT_EQ(shatter_save_summary_get(save.save, &sum), SHATTER_OK);
    EXPECT_EQ(sum.next_item_uid, uidBefore);
    // 1ª vitória: o Único cai (garantido), o contador avança e os uids saem do save.
    shatter_status st = SHATTER_INTERNAL;
    const std::string text = TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_save_roll_boss_loot(db.db, save.save, 0, boss.data(), boss.size(), 3, &rng, o, c, n, &err);
    }, &st);
    ASSERT_EQ(st, SHATTER_OK);
    const json::Value loot = Parse(text);
    bool unique = false;
    for (const json::Value& it : loot["items"].Items()) unique = unique || it["unique_id"].AsString() == "unique.bell_warden_blade";
    EXPECT_TRUE(unique);
    EXPECT_TRUE(rng.state != rngBefore.state);
    ASSERT_EQ(shatter_save_boss_progress_get(save.save, 0, boss.data(), boss.size(), &p), SHATTER_OK);
    EXPECT_EQ(p.kills, 1);
    EXPECT_EQ(p.kills_since_unique, 0);
    // O contador está no save (persistir ANTES de entregar o item: o save já o grava), e a entrega soma o item uma vez.
    const json::Value file = Parse(TwoCalls([&](std::uint8_t* b, std::size_t c, std::size_t* n) { return shatter_save_to_json(save.save, 0, b, c, n); }));
    EXPECT_EQ(file["data"]["characters"].At(0)["boss_progress"].At(0)["kills"].AsInt(), static_cast<std::int64_t>(1));
    EXPECT_EQ(file["data"]["stash"].Size(), static_cast<std::size_t>(0));
    ASSERT_EQ(shatter_save_add_loot(save.save, text.data(), text.size(), &err), SHATTER_OK);
    const json::Value after = Parse(TwoCalls([&](std::uint8_t* b, std::size_t c, std::size_t* n) { return shatter_save_to_json(save.save, 0, b, c, n); }));
    EXPECT_EQ(after["data"]["stash"].Size(), loot["items"].Size());
    EXPECT_EQ(shatter_save_roll_boss_loot(db.db, save.save, 5, boss.data(), boss.size(), 3, &rng, nullptr, 0, &needed, &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_save_roll_boss_loot(db.db, save.save, 0, "enemy.nope", 10, 3, &rng, nullptr, 0, &needed, &err), SHATTER_NOT_FOUND);
}

TEST(c_api_11_forecast_shows_calibration_and_lookup_exposes_the_new_tables) {
    DbHandle db(tu::RichDir());
    ExpeditionRequest req = tu::MakeRequest(tu::RichDb(), 1, 9);
    std::string text = S(ExpeditionRequestToJson(req));
    shatter_error err{};
    shatter_forecast_ex f{};
    ASSERT_EQ(shatter_expedition_forecast_ex(db.db, text.data(), text.size(), 1, 5, &f, &err), SHATTER_OK);
    EXPECT_EQ(f.calibration, SHATTER_CALIBRATION_BOT_PARITY);
    shatter_forecast plain{};
    ASSERT_EQ(shatter_expedition_forecast(db.db, text.data(), text.size(), 1, 5, &plain, &err), SHATTER_OK);
    EXPECT_NEAR(f.base.xp_p50, plain.xp_p50, 0.0);
    req.snapshot.character.skills.push_back({"skill.warrior.shield_bash", 1, {}});
    req.snapshot.character.skillBar[3] = "skill.warrior.shield_bash";
    text = S(ExpeditionRequestToJson(req));
    ASSERT_EQ(shatter_expedition_forecast_ex(db.db, text.data(), text.size(), 1, 5, &f, &err), SHATTER_OK);
    EXPECT_EQ(f.calibration, SHATTER_CALIBRATION_MANUAL_ESTIMATE);
    // E o relatório (resultado) leva o selo em texto.
    const json::Value res = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_expedition_simulate(db.db, text.data(), text.size(), 0, o, c, n, &err);
    }));
    EXPECT_EQ(res["calibration"].AsString(), std::string("manual_estimate"));
    // Lookup: poção, modificador, chefe com fases e padrões, skill com cone, Único com selo.
    auto look = [&](const std::string& id) {
        return Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_db_lookup_json(db.db, id.data(), id.size(), o, c, n); }));
    };
    EXPECT_NEAR(look("potion.ward")["fraction_of_max_life"].AsDouble(), 0.3, 0.0);
    EXPECT_EQ(look("potion.ward")["kind"].AsString(), std::string("barrier"));
    EXPECT_NEAR(look("modifier.elite.swift")["attack_speed_mult"].AsDouble(), 1.25, 0.0);
    const json::Value g = look("enemy.crypt_guardian");
    EXPECT_NEAR(g["shield_arc_degrees"].AsDouble(), 120.0, 0.0);
    EXPECT_EQ(g["phases"].Size(), static_cast<std::size_t>(2));
    EXPECT_EQ(g["patterns"].Size(), static_cast<std::size_t>(5));
    EXPECT_NEAR(look("skill.enemy.guardian_hammer")["cone_angle"].AsDouble(), 100.0, 0.0);
    EXPECT_EQ(look("skill.warrior.shield_bash")["idle"]["calibration"].AsString(), std::string("manual_estimate"));
    EXPECT_EQ(look("item_base.worn_trousers")["visual_set_id"].AsString(), std::string("vset.starter"));
    EXPECT_EQ(look("item_base.worn_trousers")["slot"].AsString(), std::string("legs"));
    EXPECT_TRUE(look("effect.stun")["interrupts_action"].AsBool());
    EXPECT_TRUE(look("enemy.ash_spitter").Has("ai"));
    bool fixedFound = false;
    const json::Value guardianLoot = look("loot.crypt.guardian");
    for (const json::Value& e : guardianLoot["entries"].Items()) fixedFound = fixedFound || e["pity_kills"].AsInt() == 5;
    EXPECT_TRUE(fixedFound);
}

TEST(c_api_11_trusted_start_derives_seed_from_the_core_state) {
    DbHandle db(tu::RichDir());
    shatter_error err{};
    const std::string params = StartParams(2, 0);
    auto startAndSeed = [&](std::int64_t now, std::uint64_t extraUid) {
        SaveHandle s = MakeSave(db.db);
        shatter_save_summary sm{};
        shatter_save_summary_get(s.save, &sm);
        (void)extraUid;
        shatter_trusted_now t{};
        t.now = now;
        std::int32_t check = -1;
        shatter_save_start_expedition_trusted(db.db, s.save, params.data(), params.size(), &t, &check, &err);
        if (check != SHATTER_START_OK) FAIL("inicio recusado");
        const json::Value file = Parse(TwoCalls([&](std::uint8_t* b, std::size_t c, std::size_t* n) { return shatter_save_to_json(s.save, 0, b, c, n); }));
        const json::Value& e = file["data"]["expeditions"].At(0)["request"];
        EXPECT_EQ(e["start_utc"].AsInt(), now);                        // o início é o relógio confiável
        return e["seed"].AsString();
    };
    const std::string a = startAndSeed(1'700'000'000, 0), b = startAndSeed(1'700'000'000, 0), c = startAndSeed(1'700'000'777, 0);
    EXPECT_EQ(a, b);                  // determinístico pelo estado do save e pelo início
    EXPECT_NE(a, c);                  // mudou o início, mudou a seed
    EXPECT_NE(a, std::string("0"));
    // Nulos.
    SaveHandle s = MakeSave(db.db);
    std::int32_t check = 0;
    EXPECT_EQ(shatter_save_start_expedition_trusted(db.db, s.save, params.data(), params.size(), nullptr, &check, &err), SHATTER_INVALID_ARGUMENT);
}

// =============================================================================================
// Rodada 2 (docs/13, R2): dano desarmado, chaves novas, stagger de parede, colunas novas no lookup
// =============================================================================================
TEST(c_api_r2_rules_ext2_layout_unarmed_base_damage_and_lookup_columns) {
    DbHandle db(tu::RichDir());
    shatter_rules_ext2 x{};
    ASSERT_EQ(shatter_db_rules_ext2(db.db, &x), SHATTER_OK);
    EXPECT_NEAR(x.unarmed_weapon_damage_physical, tu::RichDb().Rules().unarmedWeaponDamagePhysical, 0.0);
    EXPECT_TRUE(x.unarmed_weapon_damage_physical > 0.0 && x.require_on_screen_margin >= 0.0);
    EXPECT_EQ(shatter_db_rules_ext2(db.db, nullptr), SHATTER_INVALID_ARGUMENT);
    std::size_t needed = 0;
    EXPECT_EQ(shatter_layout_info_ext2(nullptr, 0, &needed), SHATTER_BUFFER_TOO_SMALL);
    EXPECT_EQ(needed, static_cast<std::size_t>(SHATTER_LAYOUT_EXT2_COUNT));
    std::vector<std::uint32_t> layout(needed);
    ASSERT_EQ(shatter_layout_info_ext2(layout.data(), layout.size(), &needed), SHATTER_OK);
    EXPECT_EQ(layout[0], 16u);
    shatter_error err{};
    EXPECT_EQ(shatter_layout_check_ext2(layout.data(), layout.size(), &err), SHATTER_OK);
    layout[2] += 8;
    EXPECT_EQ(shatter_layout_check_ext2(layout.data(), layout.size(), &err), SHATTER_VERSION_MISMATCH);
    EXPECT_EQ(SHATTER_LAYOUT_EXT_COUNT, 114u);         // layout ext completo (todos os campos; docs/17 M6)

    // Dano base: com espada o da arma; SEM arma (id vazio) o desarmado, só físico; golpe que não escala usa o dele.
    double dmg[4] = {-1, -1, -1, -1};
    const std::string cut = "skill.warrior.shield_bash", sword = "item_base.iron_sword", strike = "skill.enemy.sentinel_strike";
    ASSERT_EQ(shatter_skill_base_damage(db.db, cut.data(), cut.size(), sword.data(), sword.size(), dmg), SHATTER_OK);
    EXPECT_NEAR(dmg[0], tu::RichDb().FindItemBase(sword)->weaponDamage[0], 0.0);
    ASSERT_EQ(shatter_skill_base_damage(db.db, cut.data(), cut.size(), nullptr, 0, dmg), SHATTER_OK);
    EXPECT_NEAR(dmg[0], x.unarmed_weapon_damage_physical, 0.0);
    EXPECT_NEAR(dmg[1] + dmg[2] + dmg[3], 0.0, 0.0);
    ASSERT_EQ(shatter_skill_base_damage(db.db, strike.data(), strike.size(), nullptr, 0, dmg), SHATTER_OK);
    EXPECT_NEAR(dmg[0], tu::RichDb().FindSkill(strike)->baseDamage[0], 0.0);
    EXPECT_EQ(shatter_skill_base_damage(db.db, "skill.nope", 10, nullptr, 0, dmg), SHATTER_NOT_FOUND);
    EXPECT_EQ(shatter_skill_base_damage(db.db, cut.data(), cut.size(), "item_base.nope", 14, dmg), SHATTER_NOT_FOUND);
    EXPECT_EQ(shatter_skill_base_damage(db.db, cut.data(), cut.size(), nullptr, 0, nullptr), SHATTER_INVALID_ARGUMENT);

    auto look = [&](const std::string& id) {
        return Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_db_lookup_json(db.db, id.data(), id.size(), o, c, n); }));
    };
    EXPECT_NEAR(look("skill.enemy.guardian_shield_charge")["wall_stagger_seconds"].AsDouble(), 2.0, 0.0);
    EXPECT_NEAR(look("enemy.hollow_sentinel")["patrol_speed_mult"].AsDouble(), 0.5, 0.0);
    EXPECT_TRUE(look("enemy.ash_spitter")["ai"]["require_on_screen"].AsBool());
    EXPECT_NEAR(look("enemy.crypt_guardian")["phases"].At(1)["summon_at_fraction"].AsDouble(), 0.5, 0.0);
}

TEST(c_api_r2_boss_wall_hit_staggers_and_swift_timing_ignores_missing_mods) {
    DbHandle db(tu::RichDir());
    const std::string id = "enemy.crypt_guardian";
    StatHandle sb;
    ASSERT_EQ(shatter_statblock_for_enemy(db.db, id.data(), id.size(), 4, &sb.sb), SHATTER_OK);
    std::uint8_t applied = 9;
    bool done = false;
    for (std::uint64_t seed = 1; seed <= 40 && !done; ++seed) {
        BossHandle boss;
        ASSERT_EQ(shatter_boss_create(db.db, id.data(), id.size(), 4, seed, &boss.b), SHATTER_OK);
        ASSERT_EQ(shatter_boss_wall_hit(boss.b, sb.sb, &applied), SHATTER_OK);
        EXPECT_EQ(applied, 0);                          // parado: nada acontece
        ASSERT_EQ(shatter_boss_start(boss.b), SHATTER_OK);
        shatter_boss_context ctx{};
        ctx.player = {0.0, 900.0};
        std::size_t count = 0;
        shatter_boss_damage dmg{};
        shatter_boss_info info{};
        ASSERT_EQ(shatter_boss_step(boss.b, 1.0 / 60.0, &ctx, sb.sb, &count), SHATTER_OK);
        ASSERT_EQ(shatter_boss_info_get(boss.b, &info), SHATTER_OK);
        ASSERT_EQ(shatter_boss_apply_damage(boss.b, info.max_life, {0.0, 0.0}, {0.0, -400.0}, &dmg), SHATTER_OK);
        for (int i = 0; i < 60 * 3; ++i) ASSERT_EQ(shatter_boss_step(boss.b, 1.0 / 60.0, &ctx, sb.sb, &count), SHATTER_OK);
        for (int i = 0; i < 60 * 100 && !done; ++i) {
            ASSERT_EQ(shatter_boss_step(boss.b, 1.0 / 60.0, &ctx, sb.sb, &count), SHATTER_OK);
            std::vector<shatter_boss_event> ev(count);
            std::size_t needed = 0;
            if (count > 0) ASSERT_EQ(shatter_boss_events(boss.b, ev.data(), ev.size(), &needed), SHATTER_OK);
            bool charge = false;
            for (const auto& e : ev)
                if (e.kind == SHATTER_BOSS_EVT_PATTERN_IMPACT && std::string(e.pattern_id) == "pattern.guardian.shield_charge") charge = true;
            if (!charge) continue;
            ASSERT_EQ(shatter_boss_wall_hit(boss.b, sb.sb, &applied), SHATTER_OK);
            EXPECT_EQ(applied, 1);
            ASSERT_EQ(shatter_boss_info_get(boss.b, &info), SHATTER_OK);
            EXPECT_EQ(info.state, SHATTER_BOSS_STAGGER);
            EXPECT_EQ(info.shield_up, 0);
            EXPECT_NEAR(info.stagger_remaining, 2.0, 1e-9);
            ASSERT_EQ(shatter_boss_wall_hit(boss.b, sb.sb, &applied), SHATTER_OK);
            EXPECT_EQ(applied, 0);
            done = true;
        }
    }
    EXPECT_TRUE(done);
    EXPECT_EQ(shatter_boss_wall_hit(nullptr, sb.sb, &applied), SHATTER_INVALID_ARGUMENT);

    // Cão Veloz: o telegraph fica em 0,3 s mesmo se o chamador não aplicou os mods do modificador no bloco.
    DbHandle real(tu::ContentDir());
    const std::string hound = "enemy.swift_ash_hound", bite = "skill.enemy.ash_bite", mod = "modifier.elite.swift";
    StatHandle houndSb;
    ASSERT_EQ(shatter_statblock_for_enemy(real.db, hound.data(), hound.size(), 3, &houndSb.sb), SHATTER_OK);
    shatter_action_timing t{};
    shatter_action_timing plainT{};
    ASSERT_EQ(shatter_skill_timing(real.db, bite.data(), bite.size(), houndSb.sb, nullptr, 0, &plainT), SHATTER_OK);
    ASSERT_EQ(shatter_skill_timing(real.db, bite.data(), bite.size(), houndSb.sb, mod.data(), mod.size(), &t), SHATTER_OK);
    EXPECT_NEAR(t.windup, plainT.windup, 1e-12);          // o modificador não muda o telegraph (valor vem do CSV)
    shatter_elite_info info{};
    double barrier = 0.0;
    ASSERT_EQ(shatter_elite_profile(real.db, mod.data(), mod.size(), 0, &info), SHATTER_OK);
    ASSERT_EQ(shatter_elite_apply(real.db, &info, houndSb.sb, &barrier), SHATTER_OK);
    shatter_action_timing t2{};
    ASSERT_EQ(shatter_skill_timing(real.db, bite.data(), bite.size(), houndSb.sb, mod.data(), mod.size(), &t2), SHATTER_OK);
    EXPECT_NEAR(t2.windup, plainT.windup, 1e-12);
    EXPECT_NEAR(t2.impact, t.impact, 1e-12);
    EXPECT_NEAR(t2.recovery, t.recovery, 1e-12);
}

// =============================================================================================
// API 1.3: fuga do inimigo decidida pelo core (shatter_actor_flee_step / _reset)
// =============================================================================================
TEST(c_api_13_enemy_flee_is_decided_by_the_core_from_enemy_ai_csv) {
    DbHandle db(tu::ContentDir());
    const std::string id = "enemy.ash_hound";
    const json::Value look = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_db_lookup_json(db.db, id.data(), id.size(), o, c, n);
    }));
    const json::Value& ai = look["ai"];
    const double frac = ai["flee_life_fraction"].AsDouble(), secs = ai["flee_seconds"].AsDouble();
    const bool once = ai["flee_once_per_life"].AsBool();
    ASSERT_TRUE(frac > 0.0 && secs > 0.0);

    shatter_actor* a = nullptr;
    ASSERT_EQ(shatter_actor_create(db.db, id.data(), id.size(), 0, &a), SHATTER_OK);
    shatter_flee_result r{};
    const double maxLife = 1000.0;
    ASSERT_EQ(shatter_actor_flee_step(a, 0.1, maxLife, maxLife, 1, 0, &r), SHATTER_OK);
    EXPECT_TRUE(r.can_flee == 1 && r.fleeing == 0 && r.started == 0);
    ASSERT_EQ(shatter_actor_flee_step(a, 0.1, frac * maxLife, maxLife, 1, 0, &r), SHATTER_OK);   // no limite: não foge
    EXPECT_EQ(r.fleeing, 0);
    ASSERT_EQ(shatter_actor_flee_step(a, 0.1, frac * maxLife - 1.0, maxLife, 1, 0, &r), SHATTER_OK);
    EXPECT_TRUE(r.fleeing == 1 && r.started == 1 && r.ended == 0);
    EXPECT_NEAR(r.remaining, secs, 1e-9);
    ASSERT_EQ(shatter_actor_flee_step(a, secs / 2.0, frac * maxLife - 1.0, maxLife, 1, 0, &r), SHATTER_OK);
    EXPECT_TRUE(r.fleeing == 1 && r.started == 0);
    EXPECT_NEAR(r.remaining, secs / 2.0, 1e-9);
    ASSERT_EQ(shatter_actor_flee_step(a, secs, frac * maxLife - 1.0, maxLife, 1, 0, &r), SHATTER_OK);
    EXPECT_TRUE(r.fleeing == 0 && r.ended == 1);
    ASSERT_EQ(shatter_actor_flee_step(a, 0.1, 1.0, maxLife, 1, 0, &r), SHATTER_OK);
    EXPECT_EQ(r.started, once ? 0 : 1);                                  // uma vez por vida (CSV)
    ASSERT_EQ(shatter_actor_flee_reset(a), SHATTER_OK);
    ASSERT_EQ(shatter_actor_flee_step(a, 0.1, 1.0, maxLife, 1, 0, &r), SHATTER_OK);
    EXPECT_EQ(r.started, 1);                                             // revive libera
    ASSERT_EQ(shatter_actor_flee_step(a, 0.1, 1.0, maxLife, 0, 0, &r), SHATTER_OK);   // alvo sumiu
    EXPECT_TRUE(r.ended == 1 && r.fleeing == 0);
    shatter_actor_destroy(a);

    // Inimigo sem fuga no CSV e ator do herói: nunca foge, can_flee = 0.
    for (const std::string& eid : {std::string("enemy.ghost_archer"), std::string()}) {
        shatter_actor* b = nullptr;
        ASSERT_EQ(shatter_actor_create(db.db, eid.data(), eid.size(), 0, &b), SHATTER_OK);
        ASSERT_EQ(shatter_actor_flee_step(b, 0.1, 1.0, 1000.0, 1, 0, &r), SHATTER_OK);
        EXPECT_TRUE(r.can_flee == 0 && r.fleeing == 0);
        shatter_actor_destroy(b);
    }

    // Erros de argumento e layout.
    EXPECT_EQ(shatter_actor_flee_step(nullptr, 0.1, 1.0, 1.0, 1, 0, &r), SHATTER_INVALID_ARGUMENT);
    shatter_actor* c = nullptr;
    ASSERT_EQ(shatter_actor_create(db.db, id.data(), id.size(), 0, &c), SHATTER_OK);
    EXPECT_EQ(shatter_actor_flee_step(c, -1.0, 1.0, 1.0, 1, 0, &r), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_actor_flee_step(c, 0.1, 1.0, 1.0, 1, 0, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_actor_flee_reset(nullptr), SHATTER_INVALID_ARGUMENT);
    shatter_actor_destroy(c);
    std::size_t needed = 0;
    EXPECT_EQ(shatter_layout_info_ext3(nullptr, 0, &needed), SHATTER_BUFFER_TOO_SMALL);
    EXPECT_EQ(needed, static_cast<std::size_t>(SHATTER_LAYOUT_EXT3_COUNT));
    std::vector<std::uint32_t> layout(needed);
    ASSERT_EQ(shatter_layout_info_ext3(layout.data(), layout.size(), &needed), SHATTER_OK);
    shatter_error err{};
    EXPECT_EQ(shatter_layout_check_ext3(layout.data(), layout.size(), &err), SHATTER_OK);
    layout[2] += 1;
    EXPECT_EQ(shatter_layout_check_ext3(layout.data(), layout.size(), &err), SHATTER_VERSION_MISMATCH);
}

// =============================================================================================
// API 1.4: inventário, equipamento, venda e loot no chão
// =============================================================================================
namespace {

std::string LootJsonOf(const std::vector<ItemInstance>& items) {
    json::Value o = json::Value::MakeObject();
    json::Value a = json::Value::MakeArray();
    for (const ItemInstance& it : items) a.Push(ItemToJson(it));
    o.Set("items", std::move(a));
    o.Set("stacks", json::Value::MakeArray());
    return json::Serialize(o, false);
}

ItemInstance InvItem(std::uint64_t uid, const char* base, Rarity r = Rarity::Normal, int lvl = 1) {
    ItemInstance it;
    it.uid = uid;
    it.baseId = base;
    it.rarity = r;
    it.itemLevel = lvl;
    return it;
}

json::Value Ground(const shatter_save* s) {
    return Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_save_ground_list(s, o, c, n); }));
}

json::Value Box(const shatter_save* s, int container) {
    return Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_inventory_list_json(s, 0, container, o, c, n); }));
}

json::Value SaveFile(const shatter_save* s) {
    return Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_save_to_json(s, 0, o, c, n); }));
}

std::int64_t Gold(const json::Value& file) {
    std::int64_t g = 0;
    for (const json::Value& cur : file["data"]["currencies"].Items())
        if (cur["id"].AsString() == "currency.gold") g = cur["amount"].AsInt();
    return g;
}

}  // namespace

TEST(c_api_14_drop_loot_goes_to_the_ground_with_uids_banks_stacks_and_is_deterministic) {
    DbHandle db(tu::RichDir());
    const std::string table = "loot.crypt.guardian";
    shatter_loot_context ctx{};
    ctx.quantity_mult = 1.0;
    ctx.mode = SHATTER_LOOT_MANUAL;
    ctx.area_level = 4;
    ctx.max_rares = -1;
    auto run = [&](std::uint64_t seed, std::string* groundText, std::string* lootText, std::int64_t* gold) {
        SaveHandle save = MakeSave(db.db);
        shatter_rng rng{};
        shatter_rng_for_stream(seed, SHATTER_RNG_LOOT, 0, &rng);
        std::size_t needed = 0;
        shatter_error err{};
        // Buffer pequeno: nada muda (nem rng, nem uid, nem chão).
        const shatter_rng start = rng;
        EXPECT_EQ(shatter_save_drop_loot(db.db, save.save, table.data(), table.size(), &ctx, &rng, nullptr, 0, &needed, &err),
                  SHATTER_BUFFER_TOO_SMALL);
        EXPECT_EQ(rng.state, start.state);
        EXPECT_EQ(Ground(save.save)["items"].Size(), static_cast<std::size_t>(0));
        std::vector<std::uint8_t> buf(needed);
        ASSERT_EQ(shatter_save_drop_loot(db.db, save.save, table.data(), table.size(), &ctx, &rng, buf.data(), buf.size(), &needed, &err),
                  SHATTER_OK);
        *lootText = std::string(buf.begin(), buf.end());
        const json::Value loot = Parse(*lootText);
        const json::Value ground = Ground(save.save);
        EXPECT_EQ(ground["items"].Size(), loot["items"].Size());   // itens no chão, na ordem da queda
        for (std::size_t i = 0; i < ground["items"].Size(); ++i) EXPECT_TRUE(ground["items"].At(i)["uid"].AsString() != "0");
        EXPECT_EQ(Box(save.save, SHATTER_CONTAINER_BACKPACK).Size(), static_cast<std::size_t>(0));   // nada vai à Mochila sozinho
        std::int64_t g = 0;
        for (const json::Value& st : loot["stacks"].Items())
            if (st["id"].AsString() == "currency.gold") g = st["amount"].AsInt();
        *gold = g;
        EXPECT_EQ(Gold(SaveFile(save.save)), g);                  // Ouro entra direto no save (ímã)
        *groundText = S(ground);
    };
    std::string g1, g2, l1, l2;
    std::int64_t gold1 = 0, gold2 = 0;
    run(11, &g1, &l1, &gold1);
    run(11, &g2, &l2, &gold2);
    EXPECT_EQ(g1, g2);
    EXPECT_EQ(l1, l2);
    EXPECT_EQ(gold1, gold2);
    std::string g3, l3;
    std::int64_t gold3 = 0;
    bool differs = false;
    for (std::uint64_t seed = 12; seed < 40 && !differs; ++seed) {
        run(seed, &g3, &l3, &gold3);
        differs = l3 != l1;
    }
    EXPECT_TRUE(differs);                                         // outra seed, outro drop
    SaveHandle save = MakeSave(db.db);
    shatter_rng rng{};
    shatter_rng_for_stream(11, SHATTER_RNG_LOOT, 0, &rng);
    std::size_t needed = 0;
    shatter_error err{};
    std::vector<std::uint8_t> buf(8192);
    EXPECT_EQ(shatter_save_drop_loot(db.db, save.save, "loot.none", 9, &ctx, &rng, buf.data(), buf.size(), &needed, &err), SHATTER_NOT_FOUND);
}

TEST(c_api_14_pickup_respects_capacity_unique_overflows_to_stash_and_ground_is_not_saved) {
    DbHandle db(tu::RichDir());
    SaveHandle save = MakeSave(db.db);
    shatter_inventory_info info{};
    ASSERT_EQ(shatter_inventory_info_get(db.db, save.save, 0, &info), SHATTER_OK);
    ASSERT_TRUE(info.backpack_capacity > 0 && info.stash_capacity > 0);
    EXPECT_EQ(info.backpack_used, 0);
    std::vector<ItemInstance> drops;
    const int total = info.backpack_capacity + 2;
    for (int i = 0; i < total; ++i) drops.push_back(InvItem(100 + static_cast<std::uint64_t>(i), "item_base.bone_helm"));
    ItemInstance unique = InvItem(900, "item_base.bone_helm", Rarity::Unique);
    unique.uniqueId = "unique.idle_ready_helm";
    drops.push_back(unique);
    const std::string loot = LootJsonOf(drops);
    shatter_error err{};
    ASSERT_EQ(shatter_save_ground_add_loot(save.save, loot.data(), loot.size(), &err), SHATTER_OK);
    EXPECT_EQ(Ground(save.save)["items"].Size(), drops.size());
    std::int32_t dest = -1;
    for (int i = 0; i < info.backpack_capacity; ++i) {
        ASSERT_EQ(shatter_save_pickup(db.db, save.save, 0, 100 + static_cast<std::uint64_t>(i), &dest), SHATTER_OK);
        EXPECT_EQ(dest, SHATTER_PICKUP_BACKPACK);
    }
    ASSERT_EQ(shatter_inventory_info_get(db.db, save.save, 0, &info), SHATTER_OK);
    EXPECT_EQ(info.backpack_used, info.backpack_capacity);
    // Cheia: item comum fica no chão; o Único vai para o Baú.
    const std::uint64_t extra = 100 + static_cast<std::uint64_t>(info.backpack_capacity);
    ASSERT_EQ(shatter_save_pickup(db.db, save.save, 0, extra, &dest), SHATTER_OK);
    EXPECT_EQ(dest, SHATTER_PICKUP_FULL);
    EXPECT_EQ(Ground(save.save)["items"].Size(), static_cast<std::size_t>(3));
    ASSERT_EQ(shatter_save_pickup(db.db, save.save, 0, 900, &dest), SHATTER_OK);
    EXPECT_EQ(dest, SHATTER_PICKUP_STASH);
    ASSERT_EQ(shatter_save_pickup(db.db, save.save, 0, 424242, &dest), SHATTER_OK);
    EXPECT_EQ(dest, SHATTER_PICKUP_NOT_FOUND);
    ASSERT_EQ(shatter_inventory_info_get(db.db, save.save, 0, &info), SHATTER_OK);
    EXPECT_EQ(info.stash_used, 1);
    // Libera espaço (descarta um) e pega o que ficou.
    std::int32_t res = -1;
    ASSERT_EQ(shatter_inventory_discard(save.save, 0, SHATTER_CONTAINER_BACKPACK, 100, &res), SHATTER_OK);
    EXPECT_EQ(res, SHATTER_INV_OK);
    ASSERT_EQ(shatter_save_pickup(db.db, save.save, 0, extra, &dest), SHATTER_OK);
    EXPECT_EQ(dest, SHATTER_PICKUP_BACKPACK);
    // O chão não é salvo; Mochila e Baú sim.
    const json::Value file = SaveFile(save.save);
    EXPECT_EQ(file["data"]["characters"].At(0)["backpack"].Size(), static_cast<std::size_t>(info.backpack_capacity));
    EXPECT_EQ(file["data"]["stash"].Size(), static_cast<std::size_t>(1));
    const std::string text = TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_save_to_json(save.save, 0, o, c, n); });
    SaveHandle reloaded;
    std::int32_t load = -1;
    ASSERT_EQ(shatter_save_from_json(text.data(), text.size(), &reloaded.save, &load, &err), SHATTER_OK);
    EXPECT_EQ(Box(reloaded.save, SHATTER_CONTAINER_BACKPACK).Size(), static_cast<std::size_t>(info.backpack_capacity));
    EXPECT_EQ(Ground(reloaded.save)["items"].Size(), static_cast<std::size_t>(0));
    ASSERT_EQ(shatter_save_ground_clear(save.save), SHATTER_OK);
    EXPECT_EQ(Ground(save.save)["items"].Size(), static_cast<std::size_t>(0));
    EXPECT_EQ(shatter_save_pickup(db.db, nullptr, 0, 1, &dest), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_save_pickup(db.db, save.save, 5, 1, &dest), SHATTER_INVALID_ARGUMENT);
}

TEST(c_api_14_equip_compare_sell_sort_move_and_visual_set_through_the_api) {
    DbHandle db(tu::RichDir());
    SaveHandle save = MakeSave(db.db);
    const std::string loot = LootJsonOf({InvItem(11, "item_base.bone_helm"), InvItem(12, "item_base.bone_helm", Rarity::Rare, 3),
                                         InvItem(13, "item_base.worn_trousers"), InvItem(14, "item_base.iron_boots", Rarity::Magic)});
    shatter_error err{};
    ASSERT_EQ(shatter_save_ground_add_loot(save.save, loot.data(), loot.size(), &err), SHATTER_OK);
    std::int32_t dest = -1, res = -1;
    for (std::uint64_t uid : {14ull, 11ull, 13ull, 12ull}) ASSERT_EQ(shatter_save_pickup(db.db, save.save, 0, uid, &dest), SHATTER_OK);
    // Ordenar: posição, depois raridade: cabeça (Raro 12, Comum 11), pés (14), pernas (13).
    ASSERT_EQ(shatter_inventory_sort(db.db, save.save, 0), SHATTER_OK);
    const json::Value sorted = Box(save.save, SHATTER_CONTAINER_BACKPACK);
    ASSERT_EQ(sorted.Size(), static_cast<std::size_t>(4));
    EXPECT_EQ(sorted.At(0)["uid"].AsString(), std::string("12"));
    EXPECT_EQ(sorted.At(1)["uid"].AsString(), std::string("11"));
    EXPECT_EQ(sorted.At(2)["uid"].AsString(), std::string("14"));
    EXPECT_EQ(sorted.At(3)["uid"].AsString(), std::string("13"));

    // Comparação (tooltip): capacete contra a posição vazia.
    const json::Value cmp = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_inventory_compare(db.db, save.save, 0, 11, -1, o, c, n);
    }));
    EXPECT_EQ(cmp["result"].AsInt(), static_cast<std::int64_t>(SHATTER_INV_OK));
    EXPECT_EQ(cmp["slot"].AsString(), std::string("head"));
    ASSERT_EQ(cmp["deltas"].Size(), static_cast<std::size_t>(1));
    EXPECT_EQ(cmp["deltas"].At(0)["stat"].AsString(), std::string("armor"));
    const json::Value missing = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_inventory_compare(db.db, save.save, 0, 777, -1, o, c, n);
    }));
    EXPECT_EQ(missing["result"].AsInt(), static_cast<std::int64_t>(SHATTER_INV_NOT_FOUND));

    // Equipar atualiza o StatBlock do herói sem refazer o resto.
    StatHandle sb;
    ASSERT_EQ(shatter_statblock_from_save(db.db, save.save, 0, &sb.sb, &err), SHATTER_OK);
    const std::uint32_t kArmor = static_cast<std::uint32_t>(StatId::Armor);
    double armor0 = 0.0;
    ASSERT_EQ(shatter_statblock_get(sb.sb, kArmor, 0, &armor0), SHATTER_OK);
    shatter_equip_result eq{};
    ASSERT_EQ(shatter_inventory_equip(db.db, save.save, 0, 11, -1, sb.sb, &eq), SHATTER_OK);
    EXPECT_EQ(eq.result, SHATTER_INV_OK);
    EXPECT_EQ(eq.slot, static_cast<std::int32_t>(ItemSlot::Head));
    double armor1 = 0.0;
    ASSERT_EQ(shatter_statblock_get(sb.sb, kArmor, 0, &armor1), SHATTER_OK);
    EXPECT_NEAR(armor1, armor0 + 5.0, 1e-9);
    ASSERT_EQ(shatter_inventory_equip(db.db, save.save, 0, 12, static_cast<std::int32_t>(ItemSlot::Head), sb.sb, &eq), SHATTER_OK);   // troca
    EXPECT_TRUE(eq.displaced == 1 && eq.displaced_uid == 11);
    StatHandle rebuilt;
    ASSERT_EQ(shatter_statblock_from_save(db.db, save.save, 0, &rebuilt.sb, &err), SHATTER_OK);
    double a2 = 0.0, a3 = 0.0;
    shatter_statblock_get(sb.sb, kArmor, 0, &a2);
    shatter_statblock_get(rebuilt.sb, kArmor, 0, &a3);
    EXPECT_NEAR(a2, a3, 1e-9);
    // Recusas: posição errada, posição vazia, item inexistente, posição fora da faixa.
    ASSERT_EQ(shatter_inventory_equip(db.db, save.save, 0, 13, static_cast<std::int32_t>(ItemSlot::Body), sb.sb, &eq), SHATTER_OK);
    EXPECT_EQ(eq.result, SHATTER_INV_SLOT_MISMATCH);
    ASSERT_EQ(shatter_inventory_equip(db.db, save.save, 0, 999, -1, nullptr, &eq), SHATTER_OK);
    EXPECT_EQ(eq.result, SHATTER_INV_NOT_FOUND);
    ASSERT_EQ(shatter_inventory_unequip(db.db, save.save, 0, static_cast<std::int32_t>(ItemSlot::Body), nullptr, &eq), SHATTER_OK);
    EXPECT_EQ(eq.result, SHATTER_INV_SLOT_EMPTY);
    EXPECT_EQ(shatter_inventory_equip(db.db, save.save, 0, 13, 99, nullptr, &eq), SHATTER_INVALID_ARGUMENT);
    std::uint8_t on = 9;
    ASSERT_EQ(shatter_inventory_slot_enabled(db.db, static_cast<std::int32_t>(ItemSlot::Head), &on), SHATTER_OK);
    EXPECT_EQ(on, 1);
    ASSERT_EQ(shatter_inventory_slot_enabled(db.db, static_cast<std::int32_t>(ItemSlot::Amulet), &on), SHATTER_OK);
    EXPECT_EQ(on, 0);

    // Valor de venda (sem vendedor), Baú, venda idempotente e descarte.
    std::int64_t value = -1, gold = -1;
    ASSERT_EQ(shatter_inventory_sell_value(db.db, save.save, 0, 14, &value), SHATTER_OK);
    EXPECT_TRUE(value > 0);
    EXPECT_EQ(shatter_inventory_sell_value(db.db, save.save, 0, 4040, &value), SHATTER_NOT_FOUND);
    ASSERT_EQ(shatter_inventory_move(db.db, save.save, 0, 14, SHATTER_CONTAINER_STASH, &res), SHATTER_OK);
    EXPECT_EQ(res, SHATTER_INV_OK);
    EXPECT_EQ(Box(save.save, SHATTER_CONTAINER_STASH).Size(), static_cast<std::size_t>(1));
    ASSERT_EQ(shatter_inventory_sell(db.db, save.save, 0, SHATTER_CONTAINER_STASH, 14, &gold, &res), SHATTER_OK);
    EXPECT_TRUE(res == SHATTER_INV_OK && gold == value);
    ASSERT_EQ(shatter_inventory_sell(db.db, save.save, 0, SHATTER_CONTAINER_STASH, 14, &gold, &res), SHATTER_OK);
    EXPECT_TRUE(res == SHATTER_INV_NOT_FOUND && gold == 0);
    EXPECT_EQ(Gold(SaveFile(save.save)), value);                  // pagou uma vez só
    EXPECT_EQ(shatter_inventory_sell(db.db, save.save, 0, 5, 1, &gold, &res), SHATTER_INVALID_ARGUMENT);

    // visualSetId: Único, base, fallback.
    auto vset = [&](const std::string& base, const std::string& uni) {
        std::size_t n = 0;
        const shatter_status st = shatter_item_visual_set_id(db.db, base.data(), base.size(), uni.data(), uni.size(), nullptr, 0, &n);
        if (st != SHATTER_BUFFER_TOO_SMALL) return std::string("<") + shatter_status_name(st) + ">";
        std::string out(n, 'x');
        shatter_item_visual_set_id(db.db, base.data(), base.size(), uni.data(), uni.size(), reinterpret_cast<std::uint8_t*>(&out[0]), n, &n);
        return out;
    };
    EXPECT_EQ(vset("item_base.worn_trousers", ""), std::string("vset.starter"));
    EXPECT_EQ(vset("item_base.bone_helm", ""), std::string("vset.starter"));
    EXPECT_EQ(vset("item_base.nope", ""), std::string("<not_found>"));
    EXPECT_EQ(vset("item_base.bone_helm", "unique.nope"), std::string("<not_found>"));

    // Layout.
    std::size_t needed = 0;
    EXPECT_EQ(shatter_layout_info_ext4(nullptr, 0, &needed), SHATTER_BUFFER_TOO_SMALL);
    EXPECT_EQ(needed, static_cast<std::size_t>(SHATTER_LAYOUT_EXT4_COUNT));
    std::vector<std::uint32_t> layout(needed);
    ASSERT_EQ(shatter_layout_info_ext4(layout.data(), layout.size(), &needed), SHATTER_OK);
    EXPECT_EQ(layout[0], static_cast<std::uint32_t>(sizeof(shatter_inventory_info)));
    EXPECT_EQ(shatter_layout_check_ext4(layout.data(), layout.size(), &err), SHATTER_OK);
    layout[3] += 4;
    EXPECT_EQ(shatter_layout_check_ext4(layout.data(), layout.size(), &err), SHATTER_VERSION_MISMATCH);
    EXPECT_TRUE(shatter_api_minor() >= 4u);
}

// ---------------------------------------------------------------------------------------------------------------------
// API C 1.5 (docs/18, docs/09 seção 12): kits, chaves do combo, defesa com arco, regen em movimento, recurso por golpe
// ---------------------------------------------------------------------------------------------------------------------
namespace {

const ContentDB& RealContent() {
    static ContentDB* real = [] {
        auto* d = new ContentDB();
        d->LoadDirectory(tu::ContentDir());
        d->Finalize();
        return d;
    }();
    return *real;
}

// Dano de um golpe com ou sem a flag de arco; a mesma semente de combate em todas as chamadas.
double HitDamage(const shatter_db* db, const shatter_statblock* attacker, const shatter_statblock* defender, bool fromArc) {
    shatter_hit_input in{};
    in.base_damage[SHATTER_DAMAGE_PHYSICAL] = 100.0;
    in.coefficient = 1.0;
    in.defender_life = 1000.0;
    in.can_be_blocked = 1;
    in.skill_tags = SHATTER_TAG_ATTACK | SHATTER_TAG_MELEE | SHATTER_TAG_PHYSICAL;
    in.from_guard_arc = fromArc ? 1 : 0;
    shatter_rng rng{};
    shatter_rng_for_stream(99, SHATTER_RNG_COMBAT, 0, &rng);
    shatter_hit_result out{};
    if (shatter_resolve_hit_db(db, attacker, defender, &in, &rng, &out) != SHATTER_OK) FAIL("resolve_hit_db");
    return out.total_damage;
}

}  // namespace

TEST(c_api_15_minor_5_layout_combat_rules_and_basic_kits) {
    EXPECT_EQ(SHATTER_C_API_MINOR, 7u);  // 1.5 ganhou a 1.6 e a 1.7: só adições
    EXPECT_EQ(shatter_api_minor(), 7u);
    EXPECT_EQ(shatter_api_version(), 1u);
    EXPECT_EQ(static_cast<int>(SHATTER_TAG_GUARD), static_cast<int>(Mask(Tag::Guard)));

    // Layout: [from_guard_arc, combat_rules, basic_kit...]; a v1 e as outras extensões não mudaram.
    EXPECT_EQ(SHATTER_LAYOUT_COUNT, 82u);
    std::size_t needed = 0;
    EXPECT_EQ(shatter_layout_info_ext5(nullptr, 0, &needed), SHATTER_BUFFER_TOO_SMALL);
    EXPECT_EQ(needed, static_cast<std::size_t>(SHATTER_LAYOUT_EXT5_COUNT));
    std::vector<std::uint32_t> layout(needed);
    ASSERT_EQ(shatter_layout_info_ext5(layout.data(), layout.size(), &needed), SHATTER_OK);
    EXPECT_EQ(layout[0], static_cast<std::uint32_t>(offsetof(shatter_hit_input, from_guard_arc)));
    EXPECT_EQ(layout[1], static_cast<std::uint32_t>(sizeof(shatter_combat_rules)));
    EXPECT_EQ(layout[9], static_cast<std::uint32_t>(sizeof(shatter_basic_kit)));
    shatter_error err{};
    EXPECT_EQ(shatter_layout_check_ext5(layout.data(), layout.size(), &err), SHATTER_OK);
    layout[12] += 4;
    EXPECT_EQ(shatter_layout_check_ext5(layout.data(), layout.size(), &err), SHATTER_VERSION_MISMATCH);
    EXPECT_EQ(err.line, 13);
    layout[12] -= 4;
    EXPECT_EQ(shatter_layout_check_ext5(layout.data(), layout.size() - 1, &err), SHATTER_VERSION_MISMATCH);
    EXPECT_EQ(shatter_layout_info_ext5(layout.data(), layout.size(), nullptr), SHATTER_INVALID_ARGUMENT);

    DbHandle db(tu::ContentDir());
    ASSERT_TRUE(db.db != nullptr);
    const ContentDB& cdb = RealContent();
    ASSERT_TRUE(cdb.Errors().empty());

    // Chaves novas de rules.csv.
    shatter_combat_rules cr{};
    ASSERT_EQ(shatter_db_combat_rules(db.db, &cr), SHATTER_OK);
    const RulesConstants& r = cdb.Rules();
    EXPECT_NEAR(cr.combo_window, r.comboWindow, 0.0);
    EXPECT_NEAR(cr.combo_window_after_dodge, r.comboWindowAfterDodge, 0.0);
    EXPECT_NEAR(cr.attack_buffer, r.attackBuffer, 0.0);
    EXPECT_NEAR(cr.heavy_hold_threshold, r.heavyHoldThreshold, 0.0);
    EXPECT_NEAR(cr.light_windup_credit_max, r.lightWindupCreditMax, 0.0);
    EXPECT_NEAR(cr.guard_lower_time, r.guardLowerTime, 0.0);
    EXPECT_NEAR(cr.dash_shot_range, r.dashShotRange, 0.0);
    EXPECT_TRUE(cr.combo_window > 0.0 && cr.dash_shot_range > 0.0);
    EXPECT_EQ(shatter_db_combat_rules(db.db, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_db_combat_rules(nullptr, &cr), SHATTER_INVALID_ARGUMENT);

    // Kit de cada classe = BasicKitData.
    for (const char* cid : {"class.warrior", "class.archer", "class.mage"}) {
        shatter_basic_kit kit{};
        ASSERT_EQ(shatter_basic_kit_get(db.db, cid, std::strlen(cid), &kit), SHATTER_OK);
        const BasicKitData* k = cdb.FindBasicKit(cid);
        ASSERT_TRUE(k != nullptr);
        ASSERT_EQ(static_cast<std::size_t>(kit.light_chain_count), k->lightChain.size());
        for (std::size_t i = 0; i < k->lightChain.size(); ++i) EXPECT_EQ(std::string(kit.light_chain[i]), k->lightChain[i]);
        EXPECT_EQ(std::string(kit.heavy_skill), k->heavySkill);
        EXPECT_EQ(std::string(kit.charge_effect), k->chargeEffect);
        EXPECT_EQ(std::string(kit.guard_effect), k->guardEffect);
        EXPECT_NEAR(kit.heavy_charge_time, k->heavyChargeTime, 0.0);
        EXPECT_NEAR(kit.heavy_max_mult, k->heavyMaxMult, 0.0);
        EXPECT_NEAR(kit.guard_arc, k->guardArc, 0.0);
        EXPECT_NEAR(kit.guard_max_hold, k->guardMaxHold, 0.0);
        EXPECT_NEAR(kit.guard_cooldown, k->guardCooldown, 0.0);
        EXPECT_NEAR(kit.guard_perfect_window, k->guardPerfectWindow, 0.0);
        EXPECT_NEAR(kit.guard_perfect_cooldown, k->guardPerfectCooldown, 0.0);
        EXPECT_NEAR(kit.guard_perfect_resource, k->guardPerfectResource, 0.0);
        EXPECT_NEAR(kit.guard_drain_per_damage, k->guardDrainPerDamage, 0.0);
        ASSERT_EQ(static_cast<std::size_t>(kit.guard_perfect_effect_count), k->guardPerfectEffects.size());
        for (std::size_t i = 0; i < k->guardPerfectEffects.size(); ++i)
            EXPECT_EQ(std::string(kit.guard_perfect_effects[i]), k->guardPerfectEffects[i]);
        // O que sobra do vetor fica zerado (o C# pode ler só os `count` primeiros, sem lixo depois).
        for (int i = kit.light_chain_count; i < 3; ++i) EXPECT_EQ(kit.light_chain[i][0], '\0');
    }
    shatter_basic_kit k2{};
    EXPECT_EQ(shatter_basic_kit_get(db.db, "class.nope", 10, &k2), SHATTER_NOT_FOUND);
    EXPECT_EQ(shatter_basic_kit_get(db.db, "", 0, &k2), SHATTER_NOT_FOUND);
    EXPECT_EQ(shatter_basic_kit_get(db.db, nullptr, 0, &k2), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_basic_kit_get(db.db, "class.mage", 10, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_basic_kit_get(nullptr, "class.mage", 10, &k2), SHATTER_INVALID_ARGUMENT);
    // Banco sem a tabela (fixture rico): NOT_FOUND, sem erro de carga (tabela opcional).
    DbHandle rich(tu::RichDir());
    EXPECT_EQ(shatter_basic_kit_get(rich.db, "class.warrior", 13, &k2), SHATTER_NOT_FOUND);
}

TEST(c_api_15_guard_flag_reduces_damage_only_from_inside_the_arc_and_lookup_exposes_pierce_and_behavior) {
    DbHandle db(tu::ContentDir());
    ASSERT_TRUE(db.db != nullptr);
    StatHandle atk, def;
    ASSERT_EQ(shatter_statblock_create(&atk.sb), SHATTER_OK);
    ASSERT_EQ(shatter_statblock_create(&def.sb), SHATTER_OK);
    ASSERT_EQ(shatter_statblock_set_base(def.sb, SHATTER_STAT_LIFE, 1000.0), SHATTER_OK);

    // Sem efeito de defesa: a flag não muda nada.
    EXPECT_NEAR(HitDamage(db.db, atk.sb, def.sb, false), 100.0, 1e-9);
    EXPECT_NEAR(HitDamage(db.db, atk.sb, def.sb, true), 100.0, 1e-9);

    // Com a defesa do Guerreiro: de fora do arco, dano cheio; de dentro, o efeito vale.
    FxHandle fx;
    const std::string id = "effect.guarding.warrior";
    std::uint8_t applied = 0;
    ASSERT_EQ(shatter_effects_apply(fx.fx, db.db, id.data(), id.size(), "self", 4, 1.0, SHATTER_TRIGGER_NONE, def.sb, &applied), SHATTER_OK);
    EXPECT_EQ(applied, 1);
    const json::Value fxv = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_db_lookup_json(db.db, id.data(), id.size(), o, c, n);
    }));
    EXPECT_EQ(fxv["tags"].At(0).AsString(), std::string("guard"));
    double more = 0.0;
    for (std::size_t i = 0; i < fxv["modifiers"].Size(); ++i) {
        const json::Value& m = fxv["modifiers"].At(i);
        if (m["stat"].AsString() == "damage_taken" || m["stat"].AsInt(-1) == SHATTER_STAT_DAMAGE_TAKEN) more = m["value"].AsDouble();
    }
    ASSERT_TRUE(more < 0.0);
    const double outside = HitDamage(db.db, atk.sb, def.sb, false);
    const double inside = HitDamage(db.db, atk.sb, def.sb, true);
    EXPECT_NEAR(outside, 100.0, 1e-9);
    EXPECT_NEAR(inside, 100.0 * (1.0 + more), 1e-9);
    // Os atributos lidos pelo C# também: sem o contexto de arco o dano recebido não muda; com a tag, muda.
    double dt = 0.0;
    ASSERT_EQ(shatter_statblock_get(def.sb, SHATTER_STAT_DAMAGE_TAKEN, 0, &dt), SHATTER_OK);
    EXPECT_NEAR(dt, 1.0, 0.0);
    ASSERT_EQ(shatter_statblock_get(def.sb, SHATTER_STAT_DAMAGE_TAKEN, SHATTER_TAG_GUARD, &dt), SHATTER_OK);
    EXPECT_NEAR(dt, 1.0 + more, 1e-12);
    // Chamadores antigos (reserved zerado) recebem "fora do arco": o struct não mudou de tamanho.
    EXPECT_EQ(sizeof(shatter_hit_input), static_cast<std::size_t>(64));

    // Habilidades: pierce e comportamento no lookup.
    auto skill = [&](const char* sid) {
        return Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
            return shatter_db_lookup_json(db.db, sid, std::strlen(sid), o, c, n);
        }));
    };
    const json::Value ray = skill("skill.mage.arcane_ray");
    EXPECT_EQ(ray["pierce"].AsInt(-1), 99);
    EXPECT_FALSE(ray["behavior"]["explodes"].AsBool(true));
    EXPECT_TRUE(skill("skill.mage.fireball")["behavior"]["explodes"].AsBool());
    EXPECT_TRUE(skill("skill.archer.fan_shot")["behavior"]["fan"].AsBool());
    EXPECT_TRUE(skill("skill.mage.frost_nova")["behavior"]["self_centered"].AsBool());
    EXPECT_TRUE(skill("skill.archer.arrow_rain")["behavior"]["ground_targeted"].AsBool());
    EXPECT_TRUE(skill("skill.archer.back_leap")["behavior"]["dash_back_shot"].AsBool());
    EXPECT_FALSE(skill("skill.warrior.charge")["behavior"]["dash_back_shot"].AsBool(true));
    EXPECT_EQ(skill("skill.warrior.iron_cut")["pierce"].AsInt(-1), 0);
    EXPECT_NEAR(skill("skill.archer.fan_shot")["cone_angle"].AsDouble(), 28.0, 0.0);
}

TEST(c_api_15_vitals_regen_while_moving_and_resource_on_hit_and_block) {
    DbHandle db(tu::ContentDir());
    ASSERT_TRUE(db.db != nullptr);
    const ContentDB& cdb = RealContent();
    // Arqueiro: Foco máximo 100, regeneração 8/s; andando, a fração do classes.csv disso.
    StatHandle archer;
    ASSERT_EQ(shatter_statblock_create(&archer.sb), SHATTER_OK);
    ASSERT_EQ(shatter_statblock_set_base(archer.sb, SHATTER_STAT_LIFE, 90.0), SHATTER_OK);
    ASSERT_EQ(shatter_statblock_set_base(archer.sb, SHATTER_STAT_RESOURCE, 100.0), SHATTER_OK);
    ASSERT_EQ(shatter_statblock_set_base(archer.sb, SHATTER_STAT_RESOURCE_REGEN, 8.0), SHATTER_OK);
    const std::string cls = "class.archer";
    const double mult = cdb.FindClass(cls)->regenMultWhileMoving;
    ASSERT_TRUE(mult > 0.0 && mult < 1.0);
    shatter_vitals still{}, moving{}, legacy{};
    still.life = moving.life = legacy.life = 50.0;
    ASSERT_EQ(shatter_vitals_tick_ex(db.db, &still, archer.sb, cls.data(), cls.size(), 1.0, 1, 0), SHATTER_OK);
    ASSERT_EQ(shatter_vitals_tick_ex(db.db, &moving, archer.sb, cls.data(), cls.size(), 1.0, 1, 1), SHATTER_OK);
    ASSERT_EQ(shatter_vitals_tick(db.db, &legacy, archer.sb, cls.data(), cls.size(), 1.0, 1), SHATTER_OK);
    EXPECT_NEAR(still.resource, 8.0, 1e-12);
    EXPECT_NEAR(moving.resource, 8.0 * mult, 1e-12);
    EXPECT_NEAR(legacy.resource, still.resource, 0.0);
    EXPECT_NEAR(moving.life, still.life, 0.0);
    EXPECT_EQ(shatter_vitals_tick_ex(db.db, nullptr, archer.sb, cls.data(), cls.size(), 1.0, 1, 1), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_vitals_tick_ex(db.db, &moving, archer.sb, "class.nope", 10, 1.0, 1, 1), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_vitals_tick_ex(nullptr, &moving, archer.sb, cls.data(), cls.size(), 1.0, 1, 1), SHATTER_INVALID_ARGUMENT);
    // Sem classe: andar não muda a regeneração.
    shatter_vitals a{}, b{};
    ASSERT_EQ(shatter_vitals_tick_ex(db.db, &a, archer.sb, nullptr, 0, 1.0, 1, 0), SHATTER_OK);
    ASSERT_EQ(shatter_vitals_tick_ex(db.db, &b, archer.sb, nullptr, 0, 1.0, 1, 1), SHATTER_OK);
    EXPECT_NEAR(a.resource, b.resource, 0.0);

    // Guerreiro: recurso por golpe e por bloqueio, os mesmos valores do classes.csv, limitados ao máximo.
    StatHandle warrior;
    ASSERT_EQ(shatter_statblock_create(&warrior.sb), SHATTER_OK);
    ASSERT_EQ(shatter_statblock_set_base(warrior.sb, SHATTER_STAT_RESOURCE, 100.0), SHATTER_OK);
    const std::string wcls = "class.warrior";
    const ClassData* wc = cdb.FindClass(wcls);
    shatter_vitals v{};
    ASSERT_EQ(shatter_vitals_gain_on_hit(db.db, &v, warrior.sb, wcls.data(), wcls.size()), SHATTER_OK);
    EXPECT_NEAR(v.resource, wc->resourceOnHit, 0.0);
    ASSERT_EQ(shatter_vitals_gain_on_block(db.db, &v, warrior.sb, wcls.data(), wcls.size()), SHATTER_OK);
    EXPECT_NEAR(v.resource, wc->resourceOnHit + wc->resourceOnBlock, 1e-12);
    for (int i = 0; i < 50; ++i) shatter_vitals_gain_on_hit(db.db, &v, warrior.sb, wcls.data(), wcls.size());
    EXPECT_NEAR(v.resource, 100.0, 0.0);
    // Foco/Mana não ganham por golpe; sem classe, nada; classe desconhecida é erro de argumento.
    shatter_vitals f{};
    f.resource = 7.0;
    ASSERT_EQ(shatter_vitals_gain_on_hit(db.db, &f, archer.sb, cls.data(), cls.size()), SHATTER_OK);
    EXPECT_NEAR(f.resource, 7.0, 0.0);
    ASSERT_EQ(shatter_vitals_gain_on_block(db.db, &f, archer.sb, nullptr, 0), SHATTER_OK);
    EXPECT_NEAR(f.resource, 7.0, 0.0);
    EXPECT_EQ(shatter_vitals_gain_on_hit(db.db, &f, archer.sb, "class.nope", 10), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_vitals_gain_on_block(db.db, nullptr, archer.sb, cls.data(), cls.size()), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_vitals_gain_on_hit(nullptr, &f, archer.sb, cls.data(), cls.size()), SHATTER_INVALID_ARGUMENT);
}

TEST(c_api_15_charged_hit_multiplies_with_the_kit_max_mult_and_rejects_bad_charge) {
    DbHandle db(tu::ContentDir());
    ASSERT_TRUE(db.db != nullptr);
    const BasicKitData* kit = RealContent().FindBasicKit("class.warrior");
    ASSERT_TRUE(kit != nullptr && kit->heavyMaxMult > 1.0);
    StatHandle atk, def;
    ASSERT_EQ(shatter_statblock_create(&atk.sb), SHATTER_OK);
    ASSERT_EQ(shatter_statblock_create(&def.sb), SHATTER_OK);
    shatter_hit_input in{};
    in.base_damage[SHATTER_DAMAGE_PHYSICAL] = 100.0;
    in.coefficient = 1.0;
    in.defender_life = 100000.0;
    in.can_be_blocked = 1;
    in.skill_tags = SHATTER_TAG_ATTACK | SHATTER_TAG_MELEE | SHATTER_TAG_PHYSICAL;
    EXPECT_EQ(sizeof(shatter_hit_input), static_cast<std::size_t>(64));
    const std::string cls = "class.warrior";
    auto run = [&](double fraction, shatter_rng* rng, shatter_hit_result* out, shatter_error* err) {
        return shatter_resolve_hit_charged(db.db, atk.sb, def.sb, &in, cls.data(), cls.size(), fraction, rng, out, err);
    };
    shatter_rng r0{};
    shatter_rng_for_stream(3, SHATTER_RNG_COMBAT, 0, &r0);
    shatter_rng ra = r0, rb = r0, rc = r0, rplain = r0;
    shatter_hit_result plain{}, lo{}, hi{}, mid{};
    shatter_error err{};
    ASSERT_EQ(shatter_resolve_hit_db(db.db, atk.sb, def.sb, &in, &rplain, &plain), SHATTER_OK);
    ASSERT_EQ(run(0.0, &ra, &lo, &err), SHATTER_OK);
    ASSERT_EQ(run(1.0, &rb, &hi, &err), SHATTER_OK);
    ASSERT_EQ(run(0.5, &rc, &mid, &err), SHATTER_OK);
    EXPECT_NEAR(lo.total_damage, plain.total_damage, 1e-9);                       // carga mínima = golpe comum
    EXPECT_NEAR(hi.total_damage, plain.total_damage * kit->heavyMaxMult, 1e-9);   // carga máxima = heavy_max_mult
    EXPECT_NEAR(mid.total_damage, plain.total_damage * (1.0 + (kit->heavyMaxMult - 1.0) * 0.5), 1e-9);
    EXPECT_EQ(ra.state, rplain.state);  // 3 números de rng, como o golpe comum

    // Erros: nada muda (rng não avança), mensagem em err.
    for (double bad : {-0.01, 1.01, 5.0, std::nan("")}) {
        shatter_rng rr = r0;
        shatter_hit_result out{};
        out.total_damage = -5.0;
        EXPECT_EQ(run(bad, &rr, &out, &err), SHATTER_INVALID_ARGUMENT);
        EXPECT_EQ(rr.state, r0.state);
        EXPECT_NEAR(out.total_damage, -5.0, 0.0);
        EXPECT_TRUE(std::string(err.message).find("charge_fraction") != std::string::npos);
    }
    shatter_rng rr = r0;
    EXPECT_EQ(shatter_resolve_hit_charged(db.db, atk.sb, def.sb, &in, "class.nope", 10, 0.5, &rr, &hi, &err), SHATTER_NOT_FOUND);
    EXPECT_EQ(shatter_resolve_hit_charged(db.db, atk.sb, def.sb, &in, nullptr, 0, 0.5, &rr, &hi, &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_resolve_hit_charged(nullptr, atk.sb, def.sb, &in, cls.data(), cls.size(), 0.5, &rr, &hi, &err), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_resolve_hit_charged(db.db, atk.sb, def.sb, nullptr, cls.data(), cls.size(), 0.5, &rr, &hi, &err), SHATTER_INVALID_ARGUMENT);
}

TEST(c_api_15_lookup_exposes_knockback_and_explosion_radius_separate_from_radius) {
    DbHandle db(tu::ContentDir());
    ASSERT_TRUE(db.db != nullptr);
    const ContentDB& cdb = RealContent();
    auto skill = [&](const char* sid) {
        return Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
            return shatter_db_lookup_json(db.db, sid, std::strlen(sid), o, c, n);
        }));
    };
    const json::Value fire = skill("skill.mage.fireball");
    const SkillData& s = *cdb.FindSkill("skill.mage.fireball");
    EXPECT_NEAR(fire["explosion_radius"].AsDouble(), s.explosionRadius, 0.0);
    EXPECT_NEAR(fire["radius"].AsDouble(), s.radius, 0.0);
    EXPECT_TRUE(fire["explosion_radius"].AsDouble() > fire["radius"].AsDouble());
    EXPECT_NEAR(fire["knockback"].AsDouble(), s.knockback, 0.0);
    EXPECT_TRUE(fire["behavior"]["explodes"].AsBool());
    const json::Value finisher = skill("skill.warrior.combo_3");
    EXPECT_NEAR(finisher["knockback"].AsDouble(), cdb.FindSkill("skill.warrior.combo_3")->knockback, 0.0);
    EXPECT_TRUE(finisher["knockback"].AsDouble() > 0.0);
    EXPECT_NEAR(skill("skill.warrior.iron_cut")["knockback"].AsDouble(), 0.0, 0.0);
    EXPECT_NEAR(skill("skill.mage.arcane_dart")["explosion_radius"].AsDouble(), 0.0, 0.0);
}

// --- API 1.6: economia do protótipo (Vendedor, Frasco de Recarga, Encantador) -------------------------------------
namespace {

SaveHandle EconomySave(const SaveData& data) {
    const std::string text = SerializeJson(data, false);
    SaveHandle h;
    std::int32_t load = -1;
    shatter_error err{};
    if (shatter_save_from_json(text.data(), text.size(), &h.save, &load, &err) != SHATTER_OK) FAIL(err.message);
    return h;
}

std::int64_t Cur(const shatter_save* s, const char* id) {
    std::int64_t v = -1;
    if (shatter_currency_get(s, id, std::strlen(id), &v) != SHATTER_OK) FAIL("currency_get");
    return v;
}

RolledAffix RA(const char* id, double value) {
    RolledAffix a;
    a.affixId = id;
    a.value = value;
    return a;
}

ItemInstance EconItem(std::uint64_t uid, const char* base, Rarity r, int lvl, std::vector<RolledAffix> aff = {}) {
    ItemInstance it;
    it.uid = uid;
    it.baseId = base;
    it.rarity = r;
    it.itemLevel = lvl;
    it.affixes = std::move(aff);
    return it;
}

std::string SaveBytes(const shatter_save* s) {
    return TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_save_to_json(s, 0, o, c, n); });
}

}  // namespace

TEST(c_api_16_minor_6_layout_ext6_and_constants) {
    EXPECT_TRUE(SHATTER_C_API_MINOR >= 6u);
    EXPECT_TRUE(shatter_api_minor() >= 6u);
    std::size_t needed = 0;
    EXPECT_EQ(shatter_layout_info_ext6(nullptr, 0, &needed), SHATTER_BUFFER_TOO_SMALL);
    EXPECT_EQ(needed, static_cast<std::size_t>(SHATTER_LAYOUT_EXT6_COUNT));
    std::vector<std::uint32_t> layout(needed);
    ASSERT_EQ(shatter_layout_info_ext6(layout.data(), layout.size(), &needed), SHATTER_OK);
    const std::uint32_t expected[] = {32, 0, 4, 8, 16, 24, 24, 0, 4, 8, 16, 16, 0, 4, 8, 12};
    for (std::size_t i = 0; i < sizeof(expected) / sizeof(expected[0]); ++i) EXPECT_EQ(layout[i], expected[i]);
    shatter_error err{};
    EXPECT_EQ(shatter_layout_check_ext6(layout.data(), layout.size(), &err), SHATTER_OK);
    layout[3] += 8;
    EXPECT_EQ(shatter_layout_check_ext6(layout.data(), layout.size(), &err), SHATTER_VERSION_MISMATCH);
    EXPECT_EQ(shatter_layout_check_ext6(layout.data(), layout.size() - 1, &err), SHATTER_VERSION_MISMATCH);
    EXPECT_EQ(static_cast<int>(SHATTER_CRAFT_BAD_INDEX), static_cast<int>(CraftResult::BadIndex));
    EXPECT_EQ(static_cast<int>(SHATTER_CRAFT_OP_DISMANTLE), static_cast<int>(CraftOp::Dismantle));
}

TEST(c_api_16_craft_quote_refine_offer_apply_polish_and_dismantle) {
    DbHandle db(tu::RichDir());
    SaveData data;
    data.contentVersion = tu::RichDb().ContentVersion();
    data.characters.push_back(tu::MakeWarrior(tu::RichDb(), 3));
    data.nextItemUid = 1000;
    data.currencies = {{kGoldId, 5000}, {kShardsId, 500}};
    auto& bp = data.characters[0].backpack;
    bp.push_back(EconItem(10, "item_base.iron_sword", Rarity::Normal, 1));
    bp.push_back(EconItem(11, "item_base.bone_helm", Rarity::Magic, 1, {RA("affix.life_flat", 12.0)}));
    bp.push_back(EconItem(12, "item_base.leather_vest", Rarity::Rare, 2,
                          {RA("affix.life_flat", 12.0), RA("affix.armor_flat", 8.0), RA("affix.fire_res", 0.1)}));
    SaveHandle save = EconomySave(data);
    // Prévia não altera e traz o custo da tabela.
    const std::string before = SaveBytes(save.save);
    const json::Value q = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_craft_quote_json(db.db, save.save, 0, 10, SHATTER_CRAFT_OP_REFINE, 0, o, c, n);
    }));
    EXPECT_EQ(q["result"].AsInt(), static_cast<std::int64_t>(SHATTER_CRAFT_OK));
    EXPECT_EQ(q["gold"].AsInt(), 40);
    EXPECT_EQ(q["shards"].AsInt(), 10);
    EXPECT_EQ(q["affix_count_min"].AsInt(), 1);
    EXPECT_EQ(q["affix_count_max"].AsInt(), 2);
    EXPECT_EQ(q["have_gold"].AsInt(), 5000);
    EXPECT_FALSE(q["expedition_running"].AsBool(true));
    EXPECT_EQ(SaveBytes(save.save), before);
    const json::Value qLock = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_craft_quote_json(db.db, save.save, 0, 12, SHATTER_CRAFT_OP_REFORGE, 0, o, c, n);
    }));
    EXPECT_EQ(qLock["shards_no_lock"].AsInt() * 2, qLock["shards_with_lock"].AsInt());
    EXPECT_EQ(qLock["shards"].AsInt(), qLock["shards_with_lock"].AsInt());
    // Buffer pequeno não muda nada.
    std::size_t needed = 0;
    EXPECT_EQ(shatter_craft_quote_json(db.db, save.save, 0, 10, SHATTER_CRAFT_OP_REFINE, 0, nullptr, 0, &needed), SHATTER_BUFFER_TOO_SMALL);
    EXPECT_EQ(SaveBytes(save.save), before);
    // Refinar.
    shatter_craft_result r{};
    ASSERT_EQ(shatter_craft_refine(db.db, save.save, 0, 10, &r), SHATTER_OK);
    EXPECT_EQ(r.result, SHATTER_CRAFT_OK);
    EXPECT_EQ(r.gold_spent, 40);
    EXPECT_EQ(r.shards_spent, 10);
    EXPECT_EQ(Cur(save.save, "currency.gold"), 4960);
    EXPECT_EQ(Cur(save.save, "material.shards"), 490);
    ASSERT_EQ(shatter_craft_refine(db.db, save.save, 0, 10, &r), SHATTER_OK);
    EXPECT_EQ(r.result, SHATTER_CRAFT_WRONG_RARITY);
    EXPECT_EQ(r.gold_spent, 0);
    EXPECT_EQ(Cur(save.save, "currency.gold"), 4960);
    // Adicionar afixo: a oferta repete; aplicar custa; o índice precisa existir.
    auto offer = [&]() {
        return Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
            return shatter_craft_add_affix_offer(db.db, save.save, 0, 11, o, c, n);
        }));
    };
    const json::Value o1 = offer(), o2 = offer();
    EXPECT_EQ(S(o1), S(o2));
    ASSERT_TRUE(o1["candidates"].Size() >= 1 && o1["candidates"].Size() <= 3);
    ASSERT_EQ(shatter_craft_add_affix_apply(db.db, save.save, 0, 11, 9, &r), SHATTER_OK);
    EXPECT_EQ(r.result, SHATTER_CRAFT_BAD_INDEX);
    ASSERT_EQ(shatter_craft_add_affix_apply(db.db, save.save, 0, 11, 0, &r), SHATTER_OK);
    EXPECT_EQ(r.result, SHATTER_CRAFT_OK);
    EXPECT_TRUE(r.changed_affix >= 0 && r.changed_affix < 2);
    EXPECT_EQ(Cur(save.save, "currency.gold"), 4960 - 90);
    ASSERT_EQ(shatter_craft_add_affix_apply(db.db, save.save, 0, 11, 0, &r), SHATTER_OK);
    EXPECT_EQ(r.result, SHATTER_CRAFT_AFFIX_LIMIT);
    // Lapidar e Reforjar com trava.
    ASSERT_EQ(shatter_craft_polish(db.db, save.save, 0, 12, 0, &r), SHATTER_OK);
    EXPECT_EQ(r.result, SHATTER_CRAFT_OK);
    EXPECT_EQ(r.changed_affix, 0);
    EXPECT_EQ(r.gold_spent, 66);   // 60 no nível 2: +10%
    ASSERT_EQ(shatter_craft_reforge(db.db, save.save, 0, 12, 7, &r), SHATTER_OK);
    EXPECT_EQ(r.result, SHATTER_CRAFT_BAD_INDEX);
    ASSERT_EQ(shatter_craft_reforge(db.db, save.save, 0, 12, 0, &r), SHATTER_OK);
    EXPECT_EQ(r.result, SHATTER_CRAFT_OK);
    // Desmontar: 11 é Mágico (5 Lascas); repetir não paga de novo.
    const std::int64_t shards = Cur(save.save, "material.shards");
    ASSERT_EQ(shatter_craft_dismantle(db.db, save.save, 0, 11, &r), SHATTER_OK);
    EXPECT_EQ(r.result, SHATTER_CRAFT_OK);
    EXPECT_EQ(r.shards_gained, 5);
    EXPECT_EQ(Cur(save.save, "material.shards"), shards + 5);
    ASSERT_EQ(shatter_craft_dismantle(db.db, save.save, 0, 11, &r), SHATTER_OK);
    EXPECT_EQ(r.result, SHATTER_CRAFT_NOT_FOUND);
    // Argumentos inválidos.
    EXPECT_EQ(shatter_craft_refine(db.db, save.save, 7, 10, &r), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_craft_refine(db.db, nullptr, 0, 10, &r), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_craft_refine(db.db, save.save, 0, 10, nullptr), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_craft_quote_json(db.db, save.save, 0, 10, 9, 0, nullptr, 0, &needed), SHATTER_INVALID_ARGUMENT);
    std::int64_t unused = 0;
    EXPECT_EQ(shatter_currency_get(nullptr, "currency.gold", 13, &unused), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(Cur(save.save, "currency.nada"), 0);
}

TEST(c_api_16_vendor_sell_buyback_stock_buy_and_flask) {
    DbHandle db(tu::RichDir());
    SaveData data;
    data.contentVersion = tu::RichDb().ContentVersion();
    data.characters.push_back(tu::MakeWarrior(tu::RichDb(), 3));
    data.characters[0].potionSlots = {{"potion.life", 1, 40.0}, {"potion.ward", 2, 0.0}};
    data.nextItemUid = 1000;
    data.currencies = {{kGoldId, 300}};
    for (std::uint64_t i = 0; i < 11; ++i)
        data.characters[0].backpack.push_back(EconItem(100 + i, "item_base.iron_sword", i == 0 ? Rarity::Rare : Rarity::Normal, 1));
    SaveHandle save = EconomySave(data);
    shatter_vendor_result v{};
    for (std::uint64_t i = 0; i < 10; ++i) {
        ASSERT_EQ(shatter_vendor_sell(db.db, save.save, 0, SHATTER_CONTAINER_BACKPACK, 100 + i, &v), SHATTER_OK);
        EXPECT_EQ(v.result, SHATTER_VENDOR_OK);
        EXPECT_EQ(v.evicted, 0);
    }
    auto buyback = [&]() {
        return Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_vendor_buyback_json(db.db, save.save, o, c, n); }));
    };
    json::Value b = buyback();
    EXPECT_EQ(b["capacity"].AsInt(), 10);
    EXPECT_EQ(b["count"].AsInt(), 10);
    EXPECT_TRUE(b["would_evict"].AsBool(false));
    EXPECT_EQ(b["evict_rarity"].AsInt(), static_cast<std::int64_t>(Rarity::Rare));   // o mais antigo (uid 100) é Raro
    EXPECT_EQ(b["items"].At(0)["item"]["uid"].AsString(), std::string("109"));       // mais recente primeiro
    ASSERT_EQ(shatter_vendor_sell(db.db, save.save, 0, SHATTER_CONTAINER_BACKPACK, 110, &v), SHATTER_OK);
    EXPECT_EQ(v.evicted, 1);
    EXPECT_EQ(v.evicted_rarity, static_cast<std::int32_t>(Rarity::Rare));
    ASSERT_EQ(shatter_vendor_sell(db.db, save.save, 0, SHATTER_CONTAINER_BACKPACK, 110, &v), SHATTER_OK);
    EXPECT_EQ(v.result, SHATTER_VENDOR_NOT_FOUND);
    // Recompra por uid: 4 Ouro do Comum -> 5 Ouro; repetir não cobra.
    const std::int64_t gold = Cur(save.save, "currency.gold");
    ASSERT_EQ(shatter_vendor_buyback(db.db, save.save, 0, 105, &v), SHATTER_OK);
    EXPECT_EQ(v.result, SHATTER_VENDOR_OK);
    EXPECT_EQ(v.gold, 5);
    EXPECT_EQ(Cur(save.save, "currency.gold"), gold - 5);
    ASSERT_EQ(shatter_vendor_buyback(db.db, save.save, 0, 105, &v), SHATTER_OK);
    EXPECT_EQ(v.result, SHATTER_VENDOR_NOT_FOUND);
    EXPECT_EQ(Cur(save.save, "currency.gold"), gold - 5);
    // A recompra sobrevive ao arquivo.
    const std::string text = SaveBytes(save.save);
    SaveHandle again;
    std::int32_t load = -1;
    shatter_error err{};
    ASSERT_EQ(shatter_save_from_json(text.data(), text.size(), &again.save, &load, &err), SHATTER_OK);
    EXPECT_EQ(SaveBytes(again.save), text);
    // Estoque e compra.
    const json::Value stock = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_vendor_stock_json(db.db, save.save, o, c, n); }));
    ASSERT_EQ(stock.Size(), static_cast<std::size_t>(1));
    EXPECT_EQ(stock.At(0)["id"].AsString(), std::string("vendor.refill_flask"));
    EXPECT_EQ(stock.At(0)["price_gold"].AsInt(), 50);
    EXPECT_EQ(stock.At(0)["owned"].AsInt(), 0);
    const char* id = "vendor.refill_flask";
    ASSERT_EQ(shatter_vendor_buy(db.db, save.save, id, std::strlen(id), 2, &v), SHATTER_OK);
    EXPECT_EQ(v.result, SHATTER_VENDOR_OK);
    EXPECT_EQ(v.gold, 100);
    ASSERT_EQ(shatter_vendor_buy(db.db, save.save, id, std::strlen(id), 2, &v), SHATTER_OK);
    EXPECT_EQ(v.result, SHATTER_VENDOR_CARRY_CAP);
    ASSERT_EQ(shatter_vendor_buy(db.db, save.save, id, std::strlen(id), 0, &v), SHATTER_OK);
    EXPECT_EQ(v.result, SHATTER_VENDOR_BAD_QUANTITY);
    EXPECT_EQ(shatter_vendor_buy(db.db, save.save, nullptr, 0, 1, &v), SHATTER_INVALID_ARGUMENT);
    // Frasco: a Vida tem 1 carga; o cinto é o vivo do personagem.
    shatter_potions* belt = nullptr;
    ASSERT_EQ(shatter_potions_from_save(db.db, save.save, 0, &belt), SHATTER_OK);
    shatter_flask_result f{};
    ASSERT_EQ(shatter_flask_use(db.db, save.save, belt, SHATTER_FLASK_CTX_ARENA, &f), SHATTER_OK);
    EXPECT_EQ(f.result, SHATTER_FLASK_ARENA_LOCKED);
    ASSERT_EQ(shatter_flask_use(db.db, save.save, belt, SHATTER_FLASK_CTX_IDLE, &f), SHATTER_OK);
    EXPECT_EQ(f.result, SHATTER_FLASK_IDLE_FORBIDDEN);
    EXPECT_EQ(Cur(save.save, "consumable.refill_flask"), 2);
    ASSERT_EQ(shatter_flask_use(db.db, save.save, belt, SHATTER_FLASK_CTX_RUN, &f), SHATTER_OK);
    EXPECT_EQ(f.result, SHATTER_FLASK_OK);
    EXPECT_EQ(f.potion_index, 0);
    EXPECT_EQ(f.charges_after, 2);
    EXPECT_EQ(f.flasks_left, 1);
    ASSERT_EQ(shatter_flask_use(db.db, save.save, belt, SHATTER_FLASK_CTX_RUN, &f), SHATTER_OK);
    EXPECT_EQ(f.result, SHATTER_FLASK_LOCKED_OUT);     // trava global de 1 s
    ASSERT_EQ(shatter_potions_tick(db.db, belt, 1.5), SHATTER_OK);
    ASSERT_EQ(shatter_flask_use(db.db, save.save, belt, SHATTER_FLASK_CTX_RUN, &f), SHATTER_OK);
    EXPECT_EQ(f.result, SHATTER_FLASK_OK);
    EXPECT_EQ(f.charges_after, 3);
    EXPECT_EQ(Cur(save.save, "consumable.refill_flask"), 0);
    EXPECT_EQ(shatter_flask_use(db.db, save.save, belt, 9, &f), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_flask_use(db.db, save.save, nullptr, SHATTER_FLASK_CTX_RUN, &f), SHATTER_INVALID_ARGUMENT);
    shatter_potions_destroy(belt);
}

// --- API 1.7: core da Cripta (mundo, baús, encontros, XP, Fervor, tempo da arma) -----------------------------------
TEST(c_api_17_layout_ext7_xp_info_and_fervor_info) {
    std::size_t needed = 0;
    EXPECT_EQ(shatter_layout_info_ext7(nullptr, 0, &needed), SHATTER_BUFFER_TOO_SMALL);
    EXPECT_EQ(needed, static_cast<std::size_t>(SHATTER_LAYOUT_EXT7_COUNT));
    std::vector<std::uint32_t> layout(needed);
    ASSERT_EQ(shatter_layout_info_ext7(layout.data(), layout.size(), &needed), SHATTER_OK);
    const std::uint32_t expected[] = {40, 0, 8, 16, 24, 28, 32, 36, 48, 0, 8, 16, 24, 32, 40};
    for (std::size_t i = 0; i < sizeof(expected) / sizeof(expected[0]); ++i) EXPECT_EQ(layout[i], expected[i]);
    shatter_error err{};
    EXPECT_EQ(shatter_layout_check_ext7(layout.data(), layout.size(), &err), SHATTER_OK);
    layout[2] += 8;
    EXPECT_EQ(shatter_layout_check_ext7(layout.data(), layout.size(), &err), SHATTER_VERSION_MISMATCH);
    DbHandle db(tu::RichDir());
    shatter_fervor_info f{};
    ASSERT_EQ(shatter_fervor_get(db.db, &f), SHATTER_OK);
    EXPECT_NEAR(f.xp_mult, 3.0, 1e-12);
    EXPECT_NEAR(f.xp_bonus, 2.0, 1e-12);          // XP +200%
    EXPECT_NEAR(f.gold_mat_bonus, 0.25, 1e-12);
    EXPECT_NEAR(f.rare_bonus, 1.0, 1e-12);
    EXPECT_EQ(shatter_fervor_get(db.db, nullptr), SHATTER_INVALID_ARGUMENT);
}

TEST(c_api_17_world_state_visit_seed_map_info_and_encounter_roll) {
    DbHandle db(tu::RichDir());
    SaveHandle save = MakeSave(db.db);
    const std::string map = "map.act1.crypt";
    const char* chest = "chest.crypt.01";
    std::uint8_t opened = 7;
    ASSERT_EQ(shatter_world_object_get(save.save, map.data(), map.size(), chest, std::strlen(chest), &opened), SHATTER_OK);
    EXPECT_EQ(opened, 0);
    ASSERT_EQ(shatter_world_object_set(save.save, map.data(), map.size(), chest, std::strlen(chest), 1), SHATTER_OK);
    ASSERT_EQ(shatter_world_object_get(save.save, map.data(), map.size(), chest, std::strlen(chest), &opened), SHATTER_OK);
    EXPECT_EQ(opened, 1);
    EXPECT_EQ(shatter_world_object_set(save.save, map.data(), map.size(), "Bad Id", 6, 1), SHATTER_INVALID_ARGUMENT);
    const json::Value ws = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_world_state_json(save.save, map.data(), map.size(), o, c, n);
    }));
    EXPECT_EQ(ws["visits"].AsInt(), 0);
    ASSERT_EQ(ws["opened"].Size(), static_cast<std::size_t>(1));
    EXPECT_EQ(ws["opened"].At(0).AsString(), std::string(chest));
    // O estado vai no arquivo e volta igual.
    const std::string text = SaveBytes(save.save);
    SaveHandle again;
    std::int32_t load = -1;
    shatter_error err{};
    ASSERT_EQ(shatter_save_from_json(text.data(), text.size(), &again.save, &load, &err), SHATTER_OK);
    ASSERT_EQ(shatter_world_object_get(again.save, map.data(), map.size(), chest, std::strlen(chest), &opened), SHATTER_OK);
    EXPECT_EQ(opened, 1);
    EXPECT_EQ(SaveBytes(again.save), text);
    // Visita: a semente nasce no core.
    std::uint64_t s1 = 0, s2 = 0;
    ASSERT_EQ(shatter_world_begin_visit(db.db, save.save, map.data(), map.size(), &s1), SHATTER_OK);
    ASSERT_EQ(shatter_world_begin_visit(db.db, save.save, map.data(), map.size(), &s2), SHATTER_OK);
    EXPECT_NE(s1, s2);
    EXPECT_EQ(shatter_world_begin_visit(db.db, save.save, "map.none.x", 10, &s1), SHATTER_NOT_FOUND);
    EXPECT_EQ(shatter_world_begin_visit(db.db, save.save, nullptr, 0, &s1), SHATTER_INVALID_ARGUMENT);
    // Mapa.
    const json::Value mi = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_map_info_json(db.db, map.data(), map.size(), o, c, n);
    }));
    EXPECT_EQ(mi["monster_level"].AsInt(), 4);
    EXPECT_EQ(mi["area_loot_table"].AsString(), std::string("loot.crypt.area"));
    EXPECT_EQ(mi["boss_encounter"].AsString(), std::string("enc.crypt.guardian"));
    EXPECT_EQ(mi["encounters"].Size(), static_cast<std::size_t>(3));
    EXPECT_EQ(mi["chests"].Size(), static_cast<std::size_t>(5));
    // Encontro: mesma semente = mesmo JSON, formação dentro de [min,max].
    const std::string enc = "enc.crypt.patrol_b";
    auto roll = [&](std::uint64_t seed) {
        return TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
            return shatter_encounter_roll_json(db.db, enc.data(), enc.size(), seed, o, c, n);
        });
    };
    EXPECT_EQ(roll(s2), roll(s2));
    const json::Value r = Parse(roll(s2));
    ASSERT_EQ(r["groups"].Size(), static_cast<std::size_t>(2));
    EXPECT_EQ(r["groups"].At(0)["enemy_id"].AsString(), std::string("enemy.hollow_sentinel"));
    EXPECT_EQ(r["groups"].At(0)["count"].AsInt(), 1);
    const std::int64_t spitters = r["groups"].At(1)["count"].AsInt();
    EXPECT_TRUE(spitters >= 1 && spitters <= 2);
    EXPECT_EQ(r["groups"].At(1)["slots"].Size(), static_cast<std::size_t>(spitters));
    bool differs = false;
    for (std::uint64_t seed = 1; seed < 64 && !differs; ++seed) differs = roll(seed) != roll(s2);
    EXPECT_TRUE(differs);
    std::size_t needed = 0;
    EXPECT_EQ(shatter_encounter_roll_json(db.db, "enc.none.x", 10, 1, nullptr, 0, &needed), SHATTER_NOT_FOUND);
}

TEST(c_api_17_chest_opens_once_clear_loot_and_buffer_too_small_changes_nothing) {
    DbHandle db(tu::RichDir());
    SaveHandle save = MakeSave(db.db);
    const std::string map = "map.act1.crypt";
    const std::string chest = "chest.crypt.04";
    shatter_loot_context ctx{};
    ctx.quantity_mult = 1.0;
    ctx.mode = SHATTER_LOOT_MANUAL;
    ctx.area_level = 4;
    ctx.max_rares = -1;
    shatter_rng rng{};
    shatter_rng_for_stream(5, SHATTER_RNG_LOOT, 0, &rng);
    const shatter_rng start = rng;
    std::size_t needed = 0;
    std::int32_t result = -1;
    shatter_error err{};
    // Buffer pequeno: nem o baú abre, nem o rng anda.
    EXPECT_EQ(shatter_chest_open(db.db, save.save, map.data(), map.size(), chest.data(), chest.size(), &ctx, &rng, nullptr, 0, &needed,
                                 &result, &err), SHATTER_BUFFER_TOO_SMALL);
    EXPECT_EQ(rng.state, start.state);
    std::uint8_t opened = 9;
    shatter_world_object_get(save.save, map.data(), map.size(), chest.data(), chest.size(), &opened);
    EXPECT_EQ(opened, 0);
    std::vector<std::uint8_t> buf(needed);
    ASSERT_EQ(shatter_chest_open(db.db, save.save, map.data(), map.size(), chest.data(), chest.size(), &ctx, &rng, buf.data(), buf.size(),
                                 &needed, &result, &err), SHATTER_OK);
    EXPECT_EQ(result, SHATTER_CHEST_OPENED);
    const json::Value loot = Parse(std::string(buf.begin(), buf.end()));
    EXPECT_EQ(Ground(save.save)["items"].Size(), loot["items"].Size());    // o loot cai no chão
    shatter_world_object_get(save.save, map.data(), map.size(), chest.data(), chest.size(), &opened);
    EXPECT_EQ(opened, 1);
    // Segunda abertura: nada rola, o rng não anda e o save não muda.
    const std::string before = SaveBytes(save.save);
    const shatter_rng after = rng;
    std::vector<std::uint8_t> big(8192);
    ASSERT_EQ(shatter_chest_open(db.db, save.save, map.data(), map.size(), chest.data(), chest.size(), &ctx, &rng, big.data(), big.size(),
                                 &needed, &result, &err), SHATTER_OK);
    EXPECT_EQ(result, SHATTER_CHEST_ALREADY_OPEN);
    EXPECT_EQ(needed, static_cast<std::size_t>(0));
    EXPECT_EQ(rng.state, after.state);
    EXPECT_EQ(SaveBytes(save.save), before);
    // Baú sem linha em chests.csv usa a tabela da área; mapa desconhecido e id inválido recusam.
    ASSERT_EQ(shatter_chest_open(db.db, save.save, map.data(), map.size(), "chest.crypt.99", 14, &ctx, &rng, big.data(), big.size(), &needed,
                                 &result, &err), SHATTER_OK);
    EXPECT_EQ(result, SHATTER_CHEST_OPENED);
    EXPECT_EQ(shatter_chest_open(db.db, save.save, "map.none.x", 10, "chest.crypt.98", 14, &ctx, &rng, big.data(), big.size(), &needed, &result,
                                 &err), SHATTER_NOT_FOUND);
    EXPECT_EQ(shatter_chest_open(db.db, save.save, map.data(), map.size(), "Bad Id", 6, &ctx, &rng, big.data(), big.size(), &needed, &result,
                                 &err), SHATTER_INVALID_ARGUMENT);
    // Loot ao limpar um encontro: areaLootTable do mapa, determinístico pelo rng.
    auto clear = [&](std::uint64_t seed) {
        SaveHandle s = MakeSave(db.db);
        shatter_rng r{};
        shatter_rng_for_stream(seed, SHATTER_RNG_LOOT, 0, &r);
        std::size_t n = 0;
        shatter_error e{};
        EXPECT_EQ(shatter_encounter_clear_loot(db.db, s.save, map.data(), map.size(), &ctx, &r, nullptr, 0, &n, &e), SHATTER_BUFFER_TOO_SMALL);
        std::vector<std::uint8_t> out(n);
        EXPECT_EQ(shatter_encounter_clear_loot(db.db, s.save, map.data(), map.size(), &ctx, &r, out.data(), out.size(), &n, &e), SHATTER_OK);
        return std::string(out.begin(), out.end()) + S(Ground(s.save));
    };
    EXPECT_EQ(clear(3), clear(3));
    EXPECT_EQ(shatter_encounter_clear_loot(db.db, save.save, "map.none.x", 10, &ctx, &rng, big.data(), big.size(), &needed, &err), SHATTER_NOT_FOUND);
}

TEST(c_api_17_kill_xp_with_fervor_progress_and_character_level_from_the_save) {
    DbHandle db(tu::RichDir());
    SaveHandle save = MakeSave(db.db);   // Guerreiro nível 3 do fixture
    const std::string map = "map.act1.crypt";
    const std::string enemy = "enemy.hollow_sentinel";
    shatter_xp_info p{};
    ASSERT_EQ(shatter_character_progress(db.db, save.save, 0, map.data(), map.size(), &p), SHATTER_OK);
    EXPECT_EQ(p.level, 3);
    EXPECT_EQ(p.level_cap, 6);
    EXPECT_NEAR(p.xp_to_next, tu::RichDb().XpToNextLevel(3), 1e-9);
    shatter_xp_info x{};
    ASSERT_EQ(shatter_xp_award_kill(db.db, save.save, 0, map.data(), map.size(), enemy.data(), enemy.size(), 4, 0, nullptr, 0, 1, &x), SHATTER_OK);
    EXPECT_NEAR(x.awarded, 16.0 * 3.0, 1e-9);            // fervor_xp_mult 3,0: XP +200%
    EXPECT_EQ(x.level_before, 3);
    shatter_xp_info y{};
    ASSERT_EQ(shatter_xp_award_kill(db.db, save.save, 0, map.data(), map.size(), enemy.data(), enemy.size(), 4, 0, nullptr, 0, 0, &y), SHATTER_OK);
    EXPECT_NEAR(y.awarded, 16.0, 1e-9);                   // sem Fervor
    EXPECT_NEAR(y.xp_in_level, x.xp_in_level + 16.0, 1e-9);
    const char* mod = "modifier.elite.swift";
    shatter_xp_info e{};
    ASSERT_EQ(shatter_xp_award_kill(db.db, save.save, 0, map.data(), map.size(), enemy.data(), enemy.size(), 4, 1, mod, std::strlen(mod), 0, &e),
              SHATTER_OK);
    EXPECT_NEAR(e.awarded, 16.0 * 3.0, 1e-9);             // elite sorteado: elite_xp_mult 3,0 x modificador
    // O nível sobe no save e o getter o devolve.
    for (int i = 0; i < 400 && p.level < 6; ++i) {
        ASSERT_EQ(shatter_xp_award_kill(db.db, save.save, 0, map.data(), map.size(), "enemy.crypt_guardian", 20, 4, 0, nullptr, 0, 1, &x), SHATTER_OK);
        ASSERT_EQ(shatter_character_progress(db.db, save.save, 0, map.data(), map.size(), &p), SHATTER_OK);
    }
    EXPECT_EQ(p.level, 6);
    EXPECT_NEAR(p.xp_to_next, 0.0, 1e-12);
    const json::Value ch = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) { return shatter_save_character_json(save.save, 0, o, c, n); }));
    EXPECT_EQ(ch["level"].AsInt(), 6);
    // Recusas.
    EXPECT_EQ(shatter_xp_award_kill(db.db, save.save, 0, map.data(), map.size(), "enemy.nope", 10, 4, 0, nullptr, 0, 1, &x), SHATTER_NOT_FOUND);
    EXPECT_EQ(shatter_xp_award_kill(db.db, save.save, 9, map.data(), map.size(), enemy.data(), enemy.size(), 4, 0, nullptr, 0, 1, &x), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_xp_award_kill(db.db, save.save, 0, map.data(), map.size(), enemy.data(), enemy.size(), 0, 0, nullptr, 0, 1, &x), SHATTER_INVALID_ARGUMENT);
    EXPECT_EQ(shatter_xp_award_kill(db.db, save.save, 0, map.data(), map.size(), enemy.data(), enemy.size(), 4, 1, "modifier.elite.nope", 19, 1, &x), SHATTER_NOT_FOUND);
}

TEST(c_api_17_skill_timing_weapon_makes_the_maul_slower_than_the_sword_in_the_real_content) {
    DbHandle db(tu::ContentDir());
    ASSERT_TRUE(db.db != nullptr);
    shatter_statblock* sb = nullptr;
    ASSERT_EQ(shatter_statblock_create(&sb), SHATTER_OK);
    const char* skill = "skill.warrior.iron_cut";
    const char* cls = "class.warrior";
    auto timing = [&](const char* weapon) {
        shatter_action_timing t{};
        EXPECT_EQ(shatter_skill_timing_weapon(db.db, skill, std::strlen(skill), sb, cls, std::strlen(cls), weapon, std::strlen(weapon), &t), SHATTER_OK);
        return t;
    };
    const shatter_action_timing sword = timing("item_base.iron_sword");
    const shatter_action_timing maul = timing("item_base.stone_maul");
    const shatter_action_timing bare = timing("");
    shatter_action_timing plain{};
    ASSERT_EQ(shatter_skill_timing(db.db, skill, std::strlen(skill), sb, nullptr, 0, &plain), SHATTER_OK);
    EXPECT_NEAR(sword.windup + sword.impact + sword.recovery, plain.windup + plain.impact + plain.recovery, 1e-12);   // a inicial não muda
    EXPECT_NEAR(bare.recovery, plain.recovery, 1e-12);
    EXPECT_TRUE(maul.windup + maul.impact + maul.recovery > 1.4 * (sword.windup + sword.impact + sword.recovery));
    EXPECT_NEAR(maul.cooldown, sword.cooldown, 1e-12);
    shatter_action_timing t{};
    EXPECT_EQ(shatter_skill_timing_weapon(db.db, skill, std::strlen(skill), sb, cls, std::strlen(cls), "item_base.nope", 14, &t), SHATTER_NOT_FOUND);
    EXPECT_EQ(shatter_skill_timing_weapon(db.db, skill, std::strlen(skill), nullptr, cls, std::strlen(cls), "", 0, &t), SHATTER_INVALID_ARGUMENT);
    shatter_statblock_destroy(sb);
}

TEST(c_api_17_hero_move_rules_come_from_rules_csv_with_layout_and_range_validation) {
    DbHandle db(tu::RichDir());
    shatter_hero_move_rules m{};
    ASSERT_EQ(shatter_db_hero_move_rules(db.db, &m), SHATTER_OK);
    EXPECT_NEAR(m.accel_seconds, 0.10, 1e-12);
    EXPECT_NEAR(m.decel_seconds, 0.08, 1e-12);
    EXPECT_EQ(shatter_db_hero_move_rules(db.db, nullptr), SHATTER_INVALID_ARGUMENT);
    std::uint32_t layout[SHATTER_LAYOUT_EXT8_COUNT] = {};
    std::size_t needed = 0;
    ASSERT_EQ(shatter_layout_info_ext8(layout, SHATTER_LAYOUT_EXT8_COUNT, &needed), SHATTER_OK);
    EXPECT_EQ(layout[0], 16u);
    EXPECT_EQ(layout[1], 0u);
    EXPECT_EQ(layout[2], 8u);
    shatter_error err{};
    EXPECT_EQ(shatter_layout_check_ext8(layout, SHATTER_LAYOUT_EXT8_COUNT, &err), SHATTER_OK);
    layout[2] += 8;
    EXPECT_EQ(shatter_layout_check_ext8(layout, SHATTER_LAYOUT_EXT8_COUNT, &err), SHATTER_VERSION_MISMATCH);
    // Faixa 0 a 0,5 s: fora dela o conteudo e recusado (E_RANGE); no limite passa; chave ausente e E_REQUIRED.
    auto load = [&](const std::string& oldLine, const std::string& newLine) {
        const std::string rules = tu::Replace(tu::ReadFile(tu::RichDir() + "/rules.csv"), oldLine, newLine);
        ContentDB c;
        bool ok = true;
        for (const char* t : tu::kTableNames) {
            const std::string path = tu::RichDir() + "/" + t;
            if (tu::IsOptionalTable(t) && !std::filesystem::exists(std::filesystem::u8path(path))) continue;
            ok = c.LoadTableCsv(t, std::string(t) == "rules.csv" ? rules : tu::ReadFile(path)) && ok;
        }
        return ok && c.Finalize();
    };
    EXPECT_FALSE(load("hero_move_accel_seconds,0.10", "hero_move_accel_seconds,0.6"));
    EXPECT_FALSE(load("hero_move_decel_seconds,0.08", "hero_move_decel_seconds,-0.01"));
    EXPECT_TRUE(load("hero_move_accel_seconds,0.10", "hero_move_accel_seconds,0.5"));
    EXPECT_TRUE(load("hero_move_decel_seconds,0.08", "hero_move_decel_seconds,0"));
    EXPECT_FALSE(load("hero_move_decel_seconds,0.08\n", ""));
    // O conteudo real tem os valores combinados.
    DbHandle real(tu::ContentDir());
    ASSERT_EQ(shatter_db_hero_move_rules(real.db, &m), SHATTER_OK);
    EXPECT_NEAR(m.accel_seconds, 0.10, 1e-12);
    EXPECT_NEAR(m.decel_seconds, 0.08, 1e-12);
}

TEST(c_api_story_echoes_verdict_hunger_and_state_json) {
    DbHandle db(tu::RichDir());
    SaveHandle save = MakeSave(db.db);
    const std::string dir = tu::DataDir() + "/../../../EchoesOfTheShatter/Content/Data/Story";
    shatter_story* story = nullptr;
    shatter_error err{};
    ASSERT_EQ(shatter_story_load_directory(dir.data(), dir.size(), nullptr, &story, &err), SHATTER_OK);
    ASSERT_TRUE(story != nullptr);
    EXPECT_EQ(shatter_story_load_directory("/nao/existe", 11, nullptr, &story, &err), SHATTER_IO_ERROR);
    ASSERT_EQ(shatter_story_load_directory(dir.data(), dir.size(), nullptr, &story, &err), SHATTER_OK);

    const std::string region = "region.r1.crypt";
    std::uint8_t isNew = 9;
    ASSERT_EQ(shatter_story_record_echo(story, save.save, "echo.r1.broken_hammer", 21, &isNew), SHATTER_OK);
    EXPECT_EQ(isNew, 1);
    ASSERT_EQ(shatter_story_record_echo(story, save.save, "echo.r1.broken_hammer", 21, &isNew), SHATTER_OK);
    EXPECT_EQ(isNew, 0);
    EXPECT_EQ(shatter_story_record_echo(story, save.save, "echo.r1.nope", 12, &isNew), SHATTER_NOT_FOUND);
    std::uint8_t revealed = 9;
    const std::string hammer = "skill.enemy.guardian_hammer";
    ASSERT_EQ(shatter_story_skill_revealed(story, save.save, region.data(), region.size(), hammer.data(), hammer.size(), &revealed), SHATTER_OK);
    EXPECT_EQ(revealed, 1);

    // Sem o General vencido o veredito não vale e o save não muda.
    const std::string devour = "verdict.r1.devour";
    std::int32_t result = -1;
    ASSERT_EQ(shatter_story_apply_verdict(story, save.save, devour.data(), devour.size(), &result), SHATTER_OK);
    EXPECT_EQ(result, SHATTER_VERDICT_GENERAL_NOT_DEFEATED);

    // Vence o General (o contador de vitórias avança) e devora.
    shatter_rng rng{};
    ASSERT_EQ(shatter_rng_for_stream(31, SHATTER_RNG_LOOT, 0, &rng), SHATTER_OK);
    const std::string boss = "enemy.crypt_guardian";
    std::size_t needed = 0;
    std::vector<std::uint8_t> buf(1 << 16);
    ASSERT_EQ(shatter_save_roll_boss_loot(db.db, save.save, 0, boss.data(), boss.size(), 3, &rng, buf.data(), buf.size(), &needed, &err), SHATTER_OK);
    ASSERT_EQ(shatter_story_apply_verdict(story, save.save, devour.data(), devour.size(), &result), SHATTER_OK);
    EXPECT_EQ(result, SHATTER_VERDICT_OK);
    const std::string exorcise = "verdict.r1.exorcise";
    ASSERT_EQ(shatter_story_apply_verdict(story, save.save, exorcise.data(), exorcise.size(), &result), SHATTER_OK);
    EXPECT_EQ(result, SHATTER_VERDICT_ALREADY_DECIDED);

    const json::Value st = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_story_state_json(story, save.save, o, c, n);
    }));
    EXPECT_EQ(st["hunger"].AsInt(), static_cast<std::int64_t>(1));
    EXPECT_EQ(st["hunger_max"].AsInt(), static_cast<std::int64_t>(4));
    ASSERT_EQ(st["verdicts"].Size(), static_cast<std::size_t>(1));
    EXPECT_EQ(st["verdicts"].At(0)["region_state"].AsString(), std::string("stain"));
    const json::Value rj = Parse(TwoCalls([&](std::uint8_t* o, std::size_t c, std::size_t* n) {
        return shatter_story_region_json(story, save.save, region.data(), region.size(), o, c, n);
    }));
    EXPECT_TRUE(rj["decided"].AsBool());
    EXPECT_EQ(rj["options"].Size(), static_cast<std::size_t>(2));
    EXPECT_EQ(rj["echoes_found"].AsInt(), static_cast<std::int64_t>(1));

    // O progresso vai no arquivo e volta igual.
    const std::string text = SaveBytes(save.save);
    SaveHandle again;
    std::int32_t load = -1;
    ASSERT_EQ(shatter_save_from_json(text.data(), text.size(), &again.save, &load, &err), SHATTER_OK);
    EXPECT_EQ(SaveBytes(again.save), text);
    EXPECT_EQ(shatter_story_region_json(story, save.save, "region.none.x", 13, nullptr, 0, &needed), SHATTER_NOT_FOUND);
    shatter_story_destroy(story);
    shatter_story_destroy(nullptr);
}
