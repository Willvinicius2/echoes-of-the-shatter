// Fronteira da API C (docs/04_arquitetura.md, seções 9.2 e 9.7): versão e layout, argumento nulo,
// BUFFER_TOO_SMALL sem efeito colateral, ida e volta de cada grupo de funções e o MESMO resultado do C++
// (golpe, expedição, golden). Este executável é ligado à DLL/so shattercore.
#include <cstring>
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
    EXPECT_EQ(shatter_potions_from_save(db.db, save.save, 9, &again.p), SHATTER_INVALID_ARGUMENT);
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
