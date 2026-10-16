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
