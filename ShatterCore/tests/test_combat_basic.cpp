// Combate básico (docs/18, API C 1.5): as 7 chaves novas de rules.csv, o kit básico por classe (basic_kits.csv, tabela
// opcional), a coluna `pierce`, a semântica de forma das habilidades (docs/18 §8 item 3), a defesa com arco (efeitos com a
// tag `guard`), recurso por golpe e por bloqueio, regeneração em movimento, compatibilidade com o idle e `cast_speed` neutro.
// Tudo contra o conteúdo REAL (Content/Data) com 3 classes; os cenários inválidos trocam UMA tabela por texto alterado.
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <memory>

#include "test_util.h"

using namespace shatter;

namespace {

using Overrides = std::vector<std::pair<std::string, std::string>>;

std::unique_ptr<ContentDB> RealDb(const Overrides& ov = {}, const std::vector<std::string>& skip = {}) {
    auto db = std::make_unique<ContentDB>();
    for (const char* t : tu::kTableNames) {
        if (std::find(skip.begin(), skip.end(), std::string(t)) != skip.end()) continue;
        const std::string path = tu::ContentDir() + "/" + t;
        if (tu::IsOptionalTable(t) && !std::filesystem::exists(std::filesystem::u8path(path))) continue;
        std::string text = tu::ReadFile(path);
        for (const auto& o : ov)
            if (o.first == t) text = o.second;
        db->LoadTableCsv(t, text);
    }
    // basic_kits.csv (docs/18 4.6) é opcional de verdade e não está nas tabelas dos fixtures: só o conteúdo real a traz.
    if (std::find(skip.begin(), skip.end(), std::string("basic_kits.csv")) == skip.end()) {
        std::string text = tu::ReadFile(tu::ContentDir() + "/basic_kits.csv");
        for (const auto& o : ov)
            if (o.first == "basic_kits.csv") text = o.second;
        db->LoadTableCsv("basic_kits.csv", text);
    }
    db->Finalize();
    return db;
}

const ContentDB& Real() {
    static const std::unique_ptr<ContentDB> db = RealDb();
    return *db;
}

// Troca a última célula (explosionRadius) da linha de uma habilidade em skills.csv.
std::string _SetExplosion(std::string text, const std::string& skillId, const std::string& value) {
    const std::size_t at = text.find("\n" + skillId + ",");
    if (at == std::string::npos) {
        FAIL("_SetExplosion: habilidade nao encontrada: " + skillId);
        return text;
    }
    const std::size_t end = text.find('\n', at + 1);
    const std::size_t comma = text.rfind(',', end);
    text.replace(comma + 1, end - comma - 1, value);
    return text;
}

std::string Table(const std::string& name) { return tu::ReadFile(tu::ContentDir() + "/" + name); }

// O banco tem algum erro desta tabela cujo texto começa com `code`?
bool HasError(const ContentDB& db, const std::string& table, const std::string& code) {
    for (const ContentError& e : db.Errors())
        if (e.table == table && e.message.rfind(code, 0) == 0) return true;
    return false;
}

// Carrega o conteúdo real com UMA tabela trocada e exige que a validação recuse com `code` naquela tabela.
void ExpectRejected(const std::string& tag, const std::string& table, const std::string& text, const std::string& code) {
    auto db = RealDb({{table, text}});
    if (db->Errors().empty()) {
        FAIL(tag + ": passou na validacao");
        return;
    }
    if (!HasError(*db, table, code)) FAIL(tag + ": codigo " + code + " nao apareceu em " + table);
}

CharacterState Hero(const std::string& classId, int level = 1) {
    CharacterState c;
    c.name = "Teste";
    c.classId = classId;
    c.level = level;
    return c;
}

StatBlock HeroStats(const std::string& classId) {
    StatBlock sb;
    std::string err;
    if (!BuildStatBlock(Real(), Hero(classId), sb, &err)) FAIL("BuildStatBlock " + classId + ": " + err);
    return sb;
}

}  // namespace

// ---------------------------------------------------------------------------------------------------------------------
// rules.csv: as 7 chaves
// ---------------------------------------------------------------------------------------------------------------------
TEST(combat_basic_rules_keys_are_read_from_rules_csv) {
    std::string rules = Table("rules.csv");
    rules = tu::Replace(rules, "combo_window,0.5", "combo_window,1.25");
    rules = tu::Replace(rules, "combo_window_after_dodge,0.3", "combo_window_after_dodge,1.5");
    rules = tu::Replace(rules, "attack_buffer,0.22", "attack_buffer,0.5");
    rules = tu::Replace(rules, "heavy_hold_threshold,0.35", "heavy_hold_threshold,0.75");
    rules = tu::Replace(rules, "light_windup_credit_max,0.7", "light_windup_credit_max,0.25");
    rules = tu::Replace(rules, "guard_lower_time,0.1", "guard_lower_time,0.2");
    rules = tu::Replace(rules, "dash_shot_range,1000", "dash_shot_range,1337");
    auto db = RealDb({{"rules.csv", rules}});
    ASSERT_TRUE(db->Errors().empty());
    const RulesConstants& r = db->Rules();
    EXPECT_NEAR(r.comboWindow, 1.25, 0.0);
    EXPECT_NEAR(r.comboWindowAfterDodge, 1.5, 0.0);
    EXPECT_NEAR(r.attackBuffer, 0.5, 0.0);
    EXPECT_NEAR(r.heavyHoldThreshold, 0.75, 0.0);
    EXPECT_NEAR(r.lightWindupCreditMax, 0.25, 0.0);
    EXPECT_NEAR(r.guardLowerTime, 0.2, 0.0);
    EXPECT_NEAR(r.dashShotRange, 1337.0, 0.0);
    // O conteúdo real também as traz (nenhuma é zero: o número de balanceamento mora só no CSV).
    const RulesConstants& real = Real().Rules();
    EXPECT_TRUE(real.comboWindow > 0.0 && real.comboWindowAfterDodge > 0.0 && real.attackBuffer > 0.0);
    EXPECT_TRUE(real.heavyHoldThreshold > 0.0 && real.guardLowerTime > 0.0 && real.dashShotRange > 0.0);
    EXPECT_TRUE(real.lightWindupCreditMax > 0.0 && real.lightWindupCreditMax <= 1.0);
}

TEST(combat_basic_rules_keys_are_required_and_range_checked) {
    const std::string rules = Table("rules.csv");
    for (const char* key : {"combo_window,0.5\n", "combo_window_after_dodge,0.3\n", "attack_buffer,0.22\n",
                            "heavy_hold_threshold,0.35\n", "light_windup_credit_max,0.7\n", "guard_lower_time,0.1\n",
                            "dash_shot_range,1000"}) {
        const std::string from = key;
        ExpectRejected(std::string("sem ") + key, "rules.csv", tu::Replace(rules, from, ""), "E_REQUIRED");
    }
    ExpectRejected("tempo acima de 5 s", "rules.csv", tu::Replace(rules, "attack_buffer,0.22", "attack_buffer,5.5"), "E_RANGE");
    ExpectRejected("tempo negativo", "rules.csv", tu::Replace(rules, "combo_window,0.5", "combo_window,-0.1"), "E_RANGE");
    ExpectRejected("credito acima de 1", "rules.csv", tu::Replace(rules, "light_windup_credit_max,0.7", "light_windup_credit_max,1.5"),
                   "E_RANGE");
    ExpectRejected("alcance do tiro absurdo", "rules.csv", tu::Replace(rules, "dash_shot_range,1000", "dash_shot_range,100000"),
                   "E_RANGE");
    ExpectRejected("chave repetida", "rules.csv", rules + "combo_window,0.6\n", "E_DUP_ID");
    ExpectRejected("valor nao numerico", "rules.csv", tu::Replace(rules, "guard_lower_time,0.1", "guard_lower_time,abc"), "E_TYPE");
}

// ---------------------------------------------------------------------------------------------------------------------
// basic_kits.csv
// ---------------------------------------------------------------------------------------------------------------------
TEST(combat_basic_kits_of_the_three_classes_are_read_and_consistent) {
    const ContentDB& db = Real();
    ASSERT_TRUE(db.Errors().empty());
    EXPECT_EQ(db.BasicKits().size(), static_cast<std::size_t>(3));
    for (const char* cid : {"class.warrior", "class.archer", "class.mage"}) {
        const BasicKitData* k = db.FindBasicKit(cid);
        ASSERT_TRUE(k != nullptr);
        EXPECT_EQ(k->classId, std::string(cid));
        ASSERT_TRUE(!k->lightChain.empty() && k->lightChain.size() <= kMaxLightChain);
        for (const ContentId& id : k->lightChain) {
            ASSERT_TRUE(db.FindSkill(id) != nullptr);
            EXPECT_EQ(db.FindSkill(id)->classId, std::string(cid));
        }
        EXPECT_EQ(db.FindClass(cid)->startingSkill, k->lightChain.front());  // o golpe 1 é a habilidade inicial
        ASSERT_TRUE(db.FindSkill(k->heavySkill) != nullptr);
        EXPECT_EQ(db.FindSkill(k->heavySkill)->classId, std::string(cid));
        EXPECT_TRUE(k->heavyChargeTime > 0.0);
        EXPECT_TRUE(k->heavyMaxMult >= 1.0);
        EXPECT_TRUE(k->guardArc > 0.0 && k->guardArc <= 360.0);
        ASSERT_TRUE(db.FindEffect(k->chargeEffect) != nullptr);
        ASSERT_TRUE(db.FindEffect(k->guardEffect) != nullptr);
        EXPECT_TRUE(HasTag(db.FindEffect(k->guardEffect)->tags, Tag::Guard));
        EXPECT_FALSE(HasTag(db.FindEffect(k->chargeEffect)->tags, Tag::Guard));
        for (const ContentId& id : k->guardPerfectEffects) EXPECT_TRUE(db.FindEffect(id) != nullptr);
    }
    // O Guerreiro defende só pela frente; o Mago, em cúpula (docs/18 3); o Arqueiro repete o golpe 1 no golpe 2.
    EXPECT_TRUE(db.FindBasicKit("class.warrior")->guardArc < 360.0);
    EXPECT_NEAR(db.FindBasicKit("class.mage")->guardArc, 360.0, 0.0);
    const BasicKitData* archer = db.FindBasicKit("class.archer");
    ASSERT_TRUE(archer->lightChain.size() == 3);
    EXPECT_EQ(archer->lightChain[0], archer->lightChain[1]);
    EXPECT_FALSE(archer->lightChain[0] == archer->lightChain[2]);
    EXPECT_TRUE(db.FindBasicKit("class.nope") == nullptr);
    EXPECT_TRUE(db.FindBasicKit("") == nullptr);
}

TEST(combat_basic_kits_validation_rejects_broken_rows) {
    const std::string kits = Table("basic_kits.csv");
    const std::string archerChain = "skill.archer.quick_shot|skill.archer.quick_shot|skill.archer.fan_shot";
    ExpectRejected("classe inexistente", "basic_kits.csv", tu::Replace(kits, "class.mage,", "class.nope,"), "E_FK");
    ExpectRejected("classe repetida", "basic_kits.csv", tu::Replace(kits, "class.mage,", "class.archer,"), "E_DUP_ID");
    ExpectRejected("4 golpes leves", "basic_kits.csv", tu::Replace(kits, archerChain, archerChain + "|skill.archer.quick_shot"), "E_RANGE");
    ExpectRejected("golpe de outra classe", "basic_kits.csv",
                   tu::Replace(kits, archerChain, "skill.archer.quick_shot|skill.mage.arcane_dart|skill.archer.fan_shot"), "E_RULE");
    ExpectRejected("golpe forte inexistente", "basic_kits.csv", tu::Replace(kits, "skill.archer.piercing_shot", "skill.archer.nope"), "E_FK");
    ExpectRejected("efeito de carga inexistente", "basic_kits.csv", tu::Replace(kits, "effect.charging.archer", "effect.nope"), "E_FK");
    ExpectRejected("defesa sem a tag guard", "basic_kits.csv", tu::Replace(kits, "effect.guarding.archer", "effect.charging.archer"),
                   "E_RULE");
    ExpectRejected("efeito da perfeita inexistente", "basic_kits.csv", tu::Replace(kits, "effect.stun|effect.guard_break", "effect.stun|effect.nope"),
                   "E_FK");
    ExpectRejected("carga maxima abaixo de 1", "basic_kits.csv", tu::Replace(kits, ",0.9,2,", ",0.9,0.5,"), "E_RANGE");
    ExpectRejected("tempo de carga zero", "basic_kits.csv", tu::Replace(kits, ",0.9,2,", ",0,2,"), "E_RANGE");
    ExpectRejected("arco acima de 360", "basic_kits.csv", tu::Replace(kits, ",120,0,0.25,", ",400,0,0.25,"), "E_RANGE");
    ExpectRejected("arco negativo", "basic_kits.csv", tu::Replace(kits, ",120,0,0.25,", ",-5,0,0.25,"), "E_RANGE");
    ExpectRejected("numero invalido", "basic_kits.csv", tu::Replace(kits, ",0.9,2,", ",abc,2,"), "E_TYPE");
    ExpectRejected("cabecalho sem coluna obrigatoria", "basic_kits.csv",
                   tu::Replace(kits.substr(0, kits.find('\n') + 1), "heavySkill,", ""), "E_HEADER");
    ExpectRejected("id invalido", "basic_kits.csv", tu::Replace(kits, "class.warrior,", "Class.Warrior,"), "E_ID_FORMAT");
}

TEST(combat_basic_kits_table_is_optional) {
    // Sem a tabela: o conteúdo finaliza e nenhuma classe tem kit.
    auto none = RealDb({}, {"basic_kits.csv"});
    EXPECT_TRUE(none->Errors().empty());
    EXPECT_TRUE(none->BasicKits().empty());
    EXPECT_TRUE(none->FindBasicKit("class.warrior") == nullptr);
    // Só o cabeçalho: tabela vazia, também sem erro.
    const std::string kits = Table("basic_kits.csv");
    auto header = RealDb({{"basic_kits.csv", kits.substr(0, kits.find('\n') + 1)}});
    EXPECT_TRUE(header->Errors().empty());
    EXPECT_TRUE(header->BasicKits().empty());

    // LoadDirectory: a pasta sem basic_kits.csv carrega; sem outra tabela, não.
    namespace fs = std::filesystem;
    const std::string tmp = tu::TmpDir("combat_basic_no_kits");
    for (const char* t : tu::kTableNames) {
        const std::string name = t;
        fs::copy_file(fs::u8path(tu::ContentDir() + "/" + name), fs::u8path(tmp + "/" + name), fs::copy_options::overwrite_existing);
    }
    ContentDB dir;
    EXPECT_TRUE(dir.LoadDirectory(tmp));
    EXPECT_TRUE(dir.Finalize());
    EXPECT_TRUE(dir.BasicKits().empty());
    fs::remove(fs::u8path(tmp + "/potions.csv"));
    ContentDB broken;
    EXPECT_FALSE(broken.LoadDirectory(tmp));  // as outras tabelas continuam obrigatórias
}

TEST(combat_basic_kits_defaults_for_the_optional_columns) {
    // As 7 colunas opcionais podem faltar no cabeçalho (valor neutro).
    const std::string text =
        "classId,lightChain,heavySkill,heavyChargeTime,heavyMaxMult,chargeEffect,guardEffect,guardArc\n"
        "class.mage,skill.mage.arcane_dart,skill.mage.fireball,1,2,effect.charging.heavy,effect.guarding.mage,360\n";
    auto db = RealDb({{"basic_kits.csv", text}});
    ASSERT_TRUE(db->Errors().empty());
    const BasicKitData* k = db->FindBasicKit("class.mage");
    ASSERT_TRUE(k != nullptr);
    EXPECT_NEAR(k->guardMaxHold, 0.0, 0.0);
    EXPECT_NEAR(k->guardPerfectWindow, 0.0, 0.0);
    EXPECT_NEAR(k->guardDrainPerDamage, 0.0, 0.0);
    EXPECT_TRUE(k->guardPerfectEffects.empty());
    EXPECT_TRUE(db->FindBasicKit("class.warrior") == nullptr);
}

// ---------------------------------------------------------------------------------------------------------------------
// skills.csv: pierce e semântica de forma
// ---------------------------------------------------------------------------------------------------------------------
TEST(combat_basic_pierce_column_is_read_validated_and_optional) {
    const ContentDB& db = Real();
    EXPECT_EQ(db.FindSkill("skill.archer.piercing_shot")->pierce, kPierceAll);
    EXPECT_EQ(db.FindSkill("skill.mage.arcane_ray")->pierce, kPierceAll);
    EXPECT_EQ(db.FindSkill("skill.archer.quick_shot")->pierce, 0);
    EXPECT_EQ(db.FindSkill("skill.warrior.iron_cut")->pierce, 0);

    const std::string skills = Table("skills.csv");
    // Coluna `pierce` ausente do cabeçalho (conteúdo antigo): tudo 0.
    std::string old;
    {
        std::size_t pos = 0;
        while (pos < skills.size()) {
            std::size_t nl = skills.find('\n', pos);
            if (nl == std::string::npos) nl = skills.size();
            std::string line = skills.substr(pos, nl - pos);
            if (line.empty()) break;
            line.erase(line.rfind(','));  // tira as duas últimas colunas (pierce e explosionRadius)
            line.erase(line.rfind(','));
            old += line + "\n";
            pos = nl + 1;
        }
    }
    auto legacy = RealDb({{"skills.csv", old}});
    EXPECT_TRUE(legacy->Errors().empty());
    EXPECT_EQ(legacy->FindSkill("skill.archer.piercing_shot")->pierce, 0);

    // 99 em um projétil e 3 (atravessa 3 alvos) também valem; 100 e negativo não.
    const std::string piercing = "1500,,1,,,false,,,,,,,,1,,,3200,,,99,";
    auto three = RealDb({{"skills.csv", tu::Replace(skills, piercing, "1500,,1,,,false,,,,,,,,1,,,3200,,,3,")}});
    EXPECT_TRUE(three->Errors().empty());
    EXPECT_EQ(three->FindSkill("skill.archer.piercing_shot")->pierce, 3);
    ExpectRejected("pierce 100", "skills.csv", tu::Replace(skills, piercing, "1500,,1,,,false,,,,,,,,1,,,3200,,,100,"), "E_RANGE");
    ExpectRejected("pierce negativo", "skills.csv", tu::Replace(skills, piercing, "1500,,1,,,false,,,,,,,,1,,,3200,,,-1,"), "E_RANGE");
    ExpectRejected("pierce fracionario", "skills.csv", tu::Replace(skills, piercing, "1500,,1,,,false,,,,,,,,1,,,3200,,,1.5,"), "E_TYPE");
    // pierce só em projétil: a Chuva de Flechas é área.
    ExpectRejected("pierce em area", "skills.csv",
                   tu::Replace(skills, "1100,300,1,,,false,,,,,,,,3,,,,,,,", "1100,300,1,,,false,,,,,,,,3,,,,,,5,"), "E_RULE");
}

TEST(combat_basic_skill_behavior_follows_the_data) {
    const ContentDB& db = Real();
    auto beh = [&](const char* id) { return ClassifySkill(*db.FindSkill(id)); };
    // (a) projétil com explosionRadius > 0 explode no impacto; `radius` é só a largura de colisão do corredor.
    EXPECT_TRUE(beh("skill.mage.arcane_orb").explodes);
    EXPECT_TRUE(beh("skill.mage.fireball").explodes);
    for (const char* id : {"skill.mage.arcane_orb", "skill.mage.fireball"}) {
        const SkillData& s = *db.FindSkill(id);
        EXPECT_TRUE(s.explosionRadius > 0.0 && s.radius > 0.0);
        EXPECT_TRUE(s.radius < s.explosionRadius);  // o corredor é estreito: a explosão não acontece antes do alvo
    }
    EXPECT_NEAR(db.FindSkill("skill.mage.arcane_dart")->explosionRadius, 0.0, 0.0);
    EXPECT_FALSE(beh("skill.mage.arcane_dart").explodes);
    EXPECT_FALSE(beh("skill.archer.quick_shot").explodes);
    // (b) vários projéteis com ângulo = leque.
    EXPECT_TRUE(beh("skill.archer.fan_shot").fan);
    EXPECT_FALSE(beh("skill.archer.quick_shot").fan);
    EXPECT_FALSE(beh("skill.mage.fireball").fan);
    // (c) área com range 0 é centrada em quem usa; (d) área com range > 0 cai no cursor.
    EXPECT_TRUE(beh("skill.mage.frost_nova").selfCentered);
    EXPECT_FALSE(beh("skill.mage.frost_nova").groundTargeted);
    EXPECT_TRUE(beh("skill.archer.arrow_rain").groundTargeted);
    EXPECT_FALSE(beh("skill.archer.arrow_rain").selfCentered);
    // (e) dash com tag projectile pula e atira; a Investida do Guerreiro (melee) não.
    EXPECT_TRUE(beh("skill.archer.back_leap").dashBackShot);
    EXPECT_FALSE(beh("skill.warrior.charge").dashBackShot);
    // Nada disso vale para golpes corpo a corpo.
    const SkillBehavior melee = beh("skill.warrior.iron_cut");
    EXPECT_TRUE(!melee.explodes && !melee.fan && !melee.selfCentered && !melee.groundTargeted && !melee.dashBackShot);
    EXPECT_EQ(melee.pierce, 0);
    EXPECT_EQ(beh("skill.archer.piercing_shot").pierce, kPierceAll);
    EXPECT_EQ(beh("skill.mage.arcane_ray").pierce, kPierceAll);
    // O leque sai do ângulo do CSV e tem várias flechas; a Chuva tem alcance e raio; o pulo usa o range do CSV.
    const SkillData& fan = *db.FindSkill("skill.archer.fan_shot");
    EXPECT_TRUE(fan.projectiles > 1 && fan.coneAngle > 0.0);
    const SkillData& rain = *db.FindSkill("skill.archer.arrow_rain");
    EXPECT_TRUE(rain.range > 0.0 && rain.radius > 0.0 && rain.impact > 0.0);
    EXPECT_TRUE(db.FindSkill("skill.archer.back_leap")->range > 0.0 && db.Rules().dashShotRange > 0.0);
}

TEST(combat_basic_skill_shape_rules_are_validated) {
    const std::string skills = Table("skills.csv");
    // Leque sem ângulo.
    ExpectRejected("leque sem angulo", "skills.csv", tu::Replace(skills, "1100,,3,,,false,,,,,,,,1,28,", "1100,,3,,,false,,,,,,,,1,,"), "E_RULE");
    // Área sem raio.
    ExpectRejected("area sem raio", "skills.csv", tu::Replace(skills, "0.35,0,340,1,effect.chill", "0.35,0,0,1,effect.chill"), "E_RULE");
    // Explosão só em projétil; radius sozinho (sem explosionRadius) não explode.
    ExpectRejected("explosao em area", "skills.csv", _SetExplosion(skills, "skill.mage.frost_nova", "100"), "E_RULE");
    ExpectRejected("explosao negativa", "skills.csv", _SetExplosion(skills, "skill.mage.fireball", "-1"), "E_RANGE");
    auto noExplosion = RealDb({{"skills.csv", _SetExplosion(skills, "skill.mage.fireball", "")}});
    EXPECT_TRUE(noExplosion->Errors().empty());
    EXPECT_FALSE(ClassifySkill(*noExplosion->FindSkill("skill.mage.fireball")).explodes);
    EXPECT_TRUE(noExplosion->FindSkill("skill.mage.fireball")->radius > 0.0);
    // Dash com tag projectile sem dash_shot_range.
    auto noRange = RealDb({{"rules.csv", tu::Replace(Table("rules.csv"), "dash_shot_range,1000", "dash_shot_range,0")}});
    EXPECT_TRUE(HasError(*noRange, "skills.csv", "E_RULE"));
    // Mesma regra com o alcance positivo passa.
    EXPECT_TRUE(Real().Errors().empty());
}

// ---------------------------------------------------------------------------------------------------------------------
// Defesa com arco (docs/18 8.1): efeitos com a tag guard só reduzem o dano de golpe vindo de dentro do arco
// ---------------------------------------------------------------------------------------------------------------------
namespace {

struct GuardScenario {
    StatBlock attacker;
    StatBlock defender;
    EffectContainer fx;

    explicit GuardScenario(const ContentDB& db, const char* guardEffectId) {
        defender.SetBase(StatId::Life, 1000.0);
        if (guardEffectId != nullptr)
            fx.Apply(*db.FindEffect(guardEffectId), "self", 1.0, TriggerKind::None, defender, db.Rules());
    }

    HitResult Hit(const ContentDB& db, bool fromArc, double* rngAfter = nullptr) const {
        HitInput in;
        in.attacker = &attacker;
        in.defender = &defender;
        in.skillTags = Tag::Attack | Tag::Melee | Tag::Physical;
        in.baseDamage[0] = 100.0;
        in.coefficient = 1.0;
        in.defenderLife = 1000.0;
        in.fromGuardArc = fromArc;
        Pcg32 rng = Pcg32::ForStream(99, RngStream::Combat, 0);
        const HitResult r = ResolveHit(in, db.Rules(), rng);
        if (rngAfter != nullptr) *rngAfter = static_cast<double>(rng.State());
        return r;
    }
};

double DamageTakenMore(const ContentDB& db, const char* effectId) {
    for (const Modifier& m : db.FindEffect(effectId)->modifiers)
        if (m.stat == StatId::DamageTaken) return m.value;
    return 0.0;
}

}  // namespace

TEST(combat_basic_guard_effect_only_reduces_damage_from_inside_the_arc) {
    const ContentDB& db = Real();
    for (const char* id : {"effect.guarding.warrior", "effect.guarding.archer", "effect.guarding.mage"}) {
        GuardScenario s(db, id);
        const double reduction = DamageTakenMore(db, id);
        ASSERT_TRUE(reduction < 0.0);
        const HitResult outside = s.Hit(db, false);
        const HitResult inside = s.Hit(db, true);
        EXPECT_NEAR(outside.totalDamage, 100.0, 1e-9);                     // de fora do arco: dano cheio
        EXPECT_NEAR(inside.totalDamage, 100.0 * (1.0 + reduction), 1e-9);  // de dentro: o efeito vale
        EXPECT_TRUE(inside.totalDamage < outside.totalDamage);
    }
    // Sem efeito de defesa, a flag não muda nada.
    GuardScenario bare(db, nullptr);
    EXPECT_NEAR(bare.Hit(db, true).totalDamage, bare.Hit(db, false).totalDamage, 0.0);
}

TEST(combat_basic_guard_flag_changes_only_the_guard_modifier_and_consumes_the_same_rng) {
    const ContentDB& db = Real();
    GuardScenario s(db, "effect.guarding.warrior");
    // O mod de DamageTaken ganha a exigência da tag; a lentidão de andar com a guarda erguida vale sempre.
    bool damageTakenGuarded = false, moveSpeedPlain = false;
    for (const Modifier& m : s.defender.Modifiers()) {
        if (m.stat == StatId::DamageTaken) damageTakenGuarded = (m.requiredTags & Mask(Tag::Guard)) != 0;
        if (m.stat == StatId::MoveSpeed) moveSpeedPlain = m.requiredTags == 0;
    }
    EXPECT_TRUE(damageTakenGuarded);
    EXPECT_TRUE(moveSpeedPlain);
    EXPECT_TRUE(s.defender.Get(StatId::MoveSpeed) < 1.0);
    EXPECT_NEAR(s.defender.Get(StatId::DamageTaken), 1.0, 0.0);  // sem o contexto do arco, o atributo não muda
    EXPECT_NEAR(s.defender.GetTagged(StatId::DamageTaken, Mask(Tag::Guard)), 1.0 + DamageTakenMore(db, "effect.guarding.warrior"), 1e-12);

    // Outros modificadores de dano recebido do alvo valem dentro e fora do arco.
    Modifier plain;
    plain.stat = StatId::DamageTaken;
    plain.kind = ModKind::More;
    plain.value = 0.5;
    plain.source = "test";
    s.defender.AddModifier(plain);
    const double r = 1.0 + DamageTakenMore(db, "effect.guarding.warrior");
    EXPECT_NEAR(s.Hit(db, false).totalDamage, 150.0, 1e-9);
    EXPECT_NEAR(s.Hit(db, true).totalDamage, 150.0 * r, 1e-9);

    // O consumo de RNG é o mesmo dentro e fora do arco (3 números); trocar a flag não desloca o fluxo.
    double a = 0.0, b = 0.0;
    s.Hit(db, false, &a);
    s.Hit(db, true, &b);
    EXPECT_NEAR(a, b, 0.0);

    // Quebra de Guarda (aumento de dano recebido) não é efeito de defesa: vale de fora do arco.
    GuardScenario gb(db, "effect.guard_break");
    EXPECT_TRUE(gb.Hit(db, false).totalDamage > 100.0);
    EXPECT_NEAR(gb.Hit(db, false).totalDamage, gb.Hit(db, true).totalDamage, 0.0);
}

TEST(combat_basic_guard_effect_expires_and_removes_its_modifiers) {
    const ContentDB& db = Real();
    GuardScenario s(db, "effect.guarding.warrior");
    EXPECT_TRUE(s.fx.Has("effect.guarding.warrior"));
    std::vector<EffectEvent> events;
    // Reaplicado a cada tick enquanto o botão está apertado: o efeito dura 0,1 s e renova.
    const double dur = db.FindEffect("effect.guarding.warrior")->duration;
    ASSERT_TRUE(dur > 0.0);
    for (int i = 0; i < 30; ++i) {
        s.fx.Tick(db.Rules().fixedStep, db.EffectLookup(), s.defender, events);
        s.fx.Apply(*db.FindEffect("effect.guarding.warrior"), "self", 1.0, TriggerKind::None, s.defender, db.Rules());
    }
    EXPECT_TRUE(s.fx.Has("effect.guarding.warrior"));
    EXPECT_EQ(s.fx.StackCount("effect.guarding.warrior"), 1);
    EXPECT_NEAR(s.Hit(db, true).totalDamage, 100.0 * (1.0 + DamageTakenMore(db, "effect.guarding.warrior")), 1e-9);
    // Soltou o botão: some em até a duração do efeito e o dano volta ao normal mesmo de dentro do arco.
    for (int i = 0; i < 12; ++i) s.fx.Tick(db.Rules().fixedStep, db.EffectLookup(), s.defender, events);
    EXPECT_FALSE(s.fx.Has("effect.guarding.warrior"));
    EXPECT_NEAR(s.Hit(db, true).totalDamage, 100.0, 1e-9);
}

// ---------------------------------------------------------------------------------------------------------------------
// Recurso: por golpe, por bloqueio, regeneração em movimento
// ---------------------------------------------------------------------------------------------------------------------
TEST(combat_basic_resource_on_hit_and_on_block_in_real_time) {
    const ContentDB& db = Real();
    const ClassData* warrior = db.FindClass("class.warrior");
    ASSERT_TRUE(warrior->resourceOnHit > 0.0 && warrior->resourceOnBlock > 0.0);
    const StatBlock sb = HeroStats("class.warrior");
    Vitals v = CreateVitals(sb, warrior);
    EXPECT_NEAR(v.resource, 0.0, 0.0);  // o Ímpeto começa vazio (decai fora de combate)
    GainResourceOnHit(v, sb, warrior);
    EXPECT_NEAR(v.resource, warrior->resourceOnHit, 0.0);
    GainResourceOnBlock(v, sb, warrior);
    EXPECT_NEAR(v.resource, warrior->resourceOnHit + warrior->resourceOnBlock, 1e-12);
    for (int i = 0; i < 100; ++i) GainResourceOnHit(v, sb, warrior);
    EXPECT_NEAR(v.resource, sb.Get(StatId::Resource), 0.0);  // limitado ao máximo
    EXPECT_NEAR(ResourceOnHit(warrior), warrior->resourceOnHit, 0.0);
    EXPECT_NEAR(ResourceOnBlock(warrior), warrior->resourceOnBlock, 0.0);
    // Sem classe, nada.
    Vitals none;
    GainResourceOnHit(none, sb, nullptr);
    GainResourceOnBlock(none, sb, nullptr);
    EXPECT_NEAR(none.resource, 0.0, 0.0);
    EXPECT_NEAR(ResourceOnHit(nullptr), 0.0, 0.0);
    // Foco e Mana não ganham por golpe nem por bloqueio (docs/18 4.3).
    for (const char* cid : {"class.archer", "class.mage"}) {
        const ClassData* c = db.FindClass(cid);
        const StatBlock s2 = HeroStats(cid);
        Vitals v2 = CreateVitals(s2, c);
        v2.resource = 10.0;
        GainResourceOnHit(v2, s2, c);
        GainResourceOnBlock(v2, s2, c);
        EXPECT_NEAR(v2.resource, 10.0, 0.0);
    }
}

TEST(combat_basic_resource_regen_is_slower_while_moving_only_for_focus) {
    const ContentDB& db = Real();
    const ClassData* archer = db.FindClass("class.archer");
    ASSERT_TRUE(archer->regenMultWhileMoving > 0.0 && archer->regenMultWhileMoving < 1.0);
    const StatBlock sb = HeroStats("class.archer");
    const double regen = sb.Get(StatId::ResourceRegen);
    ASSERT_TRUE(regen > 0.0);
    // O Foco começa cheio (não decai fora de combate).
    Vitals start = CreateVitals(sb, archer);
    EXPECT_NEAR(start.resource, sb.Get(StatId::Resource), 0.0);

    Vitals still = start, moving = start, legacy = start;
    still.resource = moving.resource = legacy.resource = 0.0;
    still.life = moving.life = 10.0;
    TickVitals(still, sb, archer, 1.0, true, false);
    TickVitals(moving, sb, archer, 1.0, true, true);
    TickVitals(legacy, sb, archer, 1.0, true);  // chamada antiga: parado
    EXPECT_NEAR(still.resource, regen, 1e-12);
    EXPECT_NEAR(moving.resource, regen * archer->regenMultWhileMoving, 1e-12);
    EXPECT_NEAR(legacy.resource, still.resource, 0.0);
    EXPECT_NEAR(still.life, moving.life, 0.0);  // a vida não depende do movimento
    EXPECT_TRUE(moving.resource < still.resource);
    // O máximo vale mesmo andando.
    Vitals full = start;
    TickVitals(full, sb, archer, 5.0, true, true);
    EXPECT_NEAR(full.resource, sb.Get(StatId::Resource), 0.0);

    // Mana (multiplicador 1): andar não muda; sem classe: andar não muda.
    const ClassData* mage = db.FindClass("class.mage");
    const StatBlock msb = HeroStats("class.mage");
    Vitals m1 = CreateVitals(msb, mage), m2 = m1;
    m1.resource = m2.resource = 0.0;
    TickVitals(m1, msb, mage, 1.0, true, false);
    TickVitals(m2, msb, mage, 1.0, true, true);
    EXPECT_NEAR(m1.resource, m2.resource, 0.0);
    EXPECT_NEAR(m1.resource, msb.Get(StatId::ResourceRegen), 1e-12);
    Vitals n1 = m1, n2 = m1;
    n1.resource = n2.resource = 0.0;
    TickVitals(n1, msb, nullptr, 1.0, true, false);
    TickVitals(n2, msb, nullptr, 1.0, true, true);
    EXPECT_NEAR(n1.resource, n2.resource, 0.0);
}

// ---------------------------------------------------------------------------------------------------------------------
// Idle: só o golpe 1 e a barra
// ---------------------------------------------------------------------------------------------------------------------
TEST(combat_basic_idle_compatibility_ignores_the_other_kit_skills) {
    const ContentDB& db = Real();
    // Guerreiro: golpe 1 + Q/E/R têm perfil; combo 2 e 3 e o forte não precisam, mesmo na barra.
    CharacterState w = Hero("class.warrior");
    w.skillBar = {"skill.warrior.iron_cut", "skill.warrior.charge", "skill.warrior.stone_rift", "skill.warrior.shield_bash",
                  "skill.warrior.combo_2", "skill.warrior.heavy_slash"};
    std::vector<ContentId> blocking;
    EXPECT_TRUE(IsIdleCompatible(db, w, &blocking));
    EXPECT_TRUE(blocking.empty());
    w.skillBar[4] = "skill.warrior.combo_3";
    EXPECT_TRUE(IsIdleCompatible(db, w, nullptr));
    // Barra vazia: o golpe 1 do kit (Corte de Ferro) tem perfil, então segue compatível.
    CharacterState bare = Hero("class.warrior");
    EXPECT_TRUE(IsIdleCompatible(db, bare, nullptr));

    // Arqueiro: o golpe 1 (Disparo Reto) e as habilidades da barra não têm perfil -> bloqueado (RF-43, esperado).
    CharacterState a = Hero("class.archer");
    a.skillBar = {"skill.archer.quick_shot", "skill.archer.back_leap", "skill.archer.arrow_rain", "skill.archer.fan_shot",
                  "skill.archer.piercing_shot", ""};
    blocking.clear();
    EXPECT_FALSE(IsIdleCompatible(db, a, &blocking));
    auto has = [&](const char* id) { return std::find(blocking.begin(), blocking.end(), std::string(id)) != blocking.end(); };
    EXPECT_TRUE(has("skill.archer.quick_shot"));
    EXPECT_TRUE(has("skill.archer.back_leap"));
    EXPECT_TRUE(has("skill.archer.arrow_rain"));
    EXPECT_FALSE(has("skill.archer.fan_shot"));       // golpe 3 do combo: não exige perfil
    EXPECT_FALSE(has("skill.archer.piercing_shot"));  // golpe forte: não exige perfil
    // O golpe 1 conta mesmo com a barra vazia.
    CharacterState a2 = Hero("class.archer");
    blocking.clear();
    EXPECT_FALSE(IsIdleCompatible(db, a2, &blocking));
    ASSERT_EQ(blocking.size(), static_cast<std::size_t>(1));
    EXPECT_EQ(blocking[0], std::string("skill.archer.quick_shot"));

    // Mago: o mesmo, por Dardo Arcano.
    CharacterState m = Hero("class.mage");
    m.skillBar = {"skill.mage.arcane_dart", "skill.mage.frost_nova", "skill.mage.arcane_ray", "", "", ""};
    blocking.clear();
    EXPECT_FALSE(IsIdleCompatible(db, m, &blocking));
    EXPECT_TRUE(std::find(blocking.begin(), blocking.end(), std::string("skill.mage.arcane_dart")) != blocking.end());
    EXPECT_TRUE(std::find(blocking.begin(), blocking.end(), std::string("skill.mage.frost_nova")) != blocking.end());
}

// ---------------------------------------------------------------------------------------------------------------------
// cast_speed neutro, armas e atributos das classes novas
// ---------------------------------------------------------------------------------------------------------------------
TEST(combat_basic_cast_speed_has_a_neutral_base_for_classes_that_do_not_define_it) {
    const ContentDB& db = Real();
    const StatBlock mage = HeroStats("class.mage");
    EXPECT_NEAR(mage.Get(StatId::CastSpeed), 1.0, 0.0);
    EXPECT_NEAR(mage.Get(StatId::AttackSpeed), 1.0, 0.0);
    const SkillData& dart = *db.FindSkill("skill.mage.arcane_dart");
    ASSERT_TRUE(HasTag(dart.tags, Tag::Spell));
    const ActionTimingInfo t = ComputeActionTiming(db, dart, mage);
    EXPECT_NEAR(t.windup, dart.windup, 0.0);  // velocidade neutra: o tempo do CSV, sem fator escondido
    EXPECT_NEAR(t.impact, dart.impact, 0.0);
    EXPECT_NEAR(t.recovery, dart.recovery, 0.0);
    EXPECT_NEAR(t.cost, dart.cost, 0.0);
    // O feitiço usa cast_speed (não attack_speed): +25% de conjuração encurta os três tempos.
    StatBlock fast = mage;
    Modifier cast;
    cast.stat = StatId::CastSpeed;
    cast.kind = ModKind::More;
    cast.value = 0.25;
    cast.source = "test";
    fast.AddModifier(cast);
    const ActionTimingInfo tf = ComputeActionTiming(db, dart, fast);
    EXPECT_NEAR(tf.windup, dart.windup / 1.25, 1e-12);
    EXPECT_NEAR(tf.recovery, dart.recovery / 1.25, 1e-12);
    // Um ataque (sem tag spell) do Arqueiro ignora cast_speed e não é afetado por ela.
    const StatBlock archer = HeroStats("class.archer");
    const SkillData& shot = *db.FindSkill("skill.archer.quick_shot");
    EXPECT_NEAR(ComputeActionTiming(db, shot, archer).windup, shot.windup, 0.0);
    EXPECT_TRUE(CanAct(mage) && CanMove(mage));
}

TEST(combat_basic_new_classes_stats_and_the_hunter_bow_come_from_the_csv) {
    const ContentDB& db = Real();
    const ClassData* archer = db.FindClass("class.archer");
    const ClassData* mage = db.FindClass("class.mage");
    ASSERT_TRUE(archer != nullptr && mage != nullptr);
    EXPECT_EQ(archer->resourceId, std::string("resource.focus"));
    EXPECT_EQ(mage->resourceId, std::string("resource.mana"));
    EXPECT_NEAR(archer->resourceDecayOutOfCombat, 0.0, 0.0);
    EXPECT_NEAR(mage->regenMultWhileMoving, 1.0, 0.0);
    // Os dois ficam mais frágeis que o Guerreiro (plano: "frágil", "pouca defesa").
    const double wLife = HeroStats("class.warrior").Get(StatId::Life);
    EXPECT_TRUE(HeroStats("class.archer").Get(StatId::Life) < wLife);
    EXPECT_TRUE(HeroStats("class.mage").Get(StatId::Life) < HeroStats("class.archer").Get(StatId::Life));
    EXPECT_TRUE(HeroStats("class.mage").Get(StatId::Resource) > HeroStats("class.archer").Get(StatId::Resource));
    // Arco inicial do Arqueiro: arma de projétil na mão principal; o dano do Disparo Reto vem dela.
    const ItemBaseData* bow = db.FindItemBase("item_base.hunter_bow");
    ASSERT_TRUE(bow != nullptr);
    EXPECT_TRUE(bow->slot == ItemSlot::MainHand);
    EXPECT_EQ(bow->weaponTags, Mask(Tag::Projectile));
    EXPECT_TRUE(bow->weaponDamage[0] > 0.0);
    const SkillData& shot = *db.FindSkill("skill.archer.quick_shot");
    EXPECT_TRUE(shot.scalesWithWeapon);
    EXPECT_NEAR(ComputeSkillBaseDamage(db, shot, bow)[0], bow->weaponDamage[0], 0.0);
    EXPECT_NEAR(ComputeSkillBaseDamage(db, shot, nullptr)[0], db.Rules().unarmedWeaponDamagePhysical, 0.0);
    // O Mago não usa arma: dano fixo por elemento no CSV.
    const SkillData& fire = *db.FindSkill("skill.mage.fireball");
    EXPECT_FALSE(fire.scalesWithWeapon);
    EXPECT_TRUE(ComputeSkillBaseDamage(db, fire, nullptr)[1] > 0.0);
    // O arco equipa e entra no StatBlock do Arqueiro (implícito de crítico).
    CharacterState a = Hero("class.archer");
    ItemInstance it;
    it.uid = 1;
    it.baseId = "item_base.hunter_bow";
    a.equipment[static_cast<std::size_t>(ItemSlot::MainHand)] = it;
    StatBlock sb;
    std::string err;
    ASSERT_TRUE(BuildStatBlock(db, a, sb, &err));
    EXPECT_TRUE(sb.Get(StatId::CritChance) > HeroStats("class.archer").Get(StatId::CritChance));
}

TEST(combat_basic_effects_of_the_kit_are_plain_data) {
    const ContentDB& db = Real();
    // Chill: lentidão sem dano e sem tag de defesa; carga: só lentidão.
    const EffectData* chill = db.FindEffect("effect.chill");
    ASSERT_TRUE(chill != nullptr);
    ASSERT_EQ(chill->modifiers.size(), static_cast<std::size_t>(1));
    EXPECT_TRUE(chill->modifiers[0].stat == StatId::MoveSpeed && chill->modifiers[0].value < 0.0);
    EXPECT_FALSE(HasTag(chill->tags, Tag::Guard));
    for (const char* id : {"effect.charging.heavy", "effect.charging.archer"}) {
        const EffectData* e = db.FindEffect(id);
        ASSERT_TRUE(e != nullptr);
        EXPECT_TRUE(e->stackRule == StackRule::Refresh);
        for (const Modifier& m : e->modifiers) EXPECT_TRUE(m.stat == StatId::MoveSpeed);
    }
    // Defesa: DamageTaken + lentidão, renovada a cada tick (curta, refresh).
    for (const char* id : {"effect.guarding.warrior", "effect.guarding.archer", "effect.guarding.mage"}) {
        const EffectData* e = db.FindEffect(id);
        ASSERT_TRUE(e != nullptr);
        EXPECT_TRUE(e->stackRule == StackRule::Refresh);
        EXPECT_TRUE(e->duration > 0.0 && e->duration <= 0.25);
        bool dt = false, ms = false;
        for (const Modifier& m : e->modifiers) {
            dt = dt || (m.stat == StatId::DamageTaken && m.value < 0.0);
            ms = ms || (m.stat == StatId::MoveSpeed && m.value < 0.0);
        }
        EXPECT_TRUE(dt && ms);
    }
    // A tag guard não é aceita só em efeitos: o parser de tags a conhece (e rejeita nomes errados).
    TagMask m = 0;
    EXPECT_TRUE(ParseTagList("guard", m));
    EXPECT_EQ(m, Mask(Tag::Guard));
    EXPECT_EQ(TagListToString(Mask(Tag::Guard)), std::string("guard"));
    EXPECT_FALSE(ParseTagList("guarda", m));
}

TEST(combat_basic_new_classes_are_blocked_from_expeditions_and_the_warrior_seal_ignores_kit_only_skills) {
    const ContentDB& db = Real();
    // Arqueiro e Mago: sem expedição no protótipo (Q18-2, RF-43) porque o golpe 1 e a barra não têm perfil idle.
    for (const char* cid : {"class.archer", "class.mage"}) {
        CharacterState c = Hero(cid, 3);
        c.conqueredMaps = {"map.act1.crypt"};
        std::vector<ContentId> blocking;
        EXPECT_ENUM_EQ(CanStartExpedition(db, c, "map.act1.crypt", 1, 12, false, 3, &blocking), StartCheck::IdleIncompatible);
        EXPECT_FALSE(blocking.empty());
    }
    // Guerreiro com o kit completo na barra: expedição liberada e selo igual ao da barra só com habilidades de idle.
    CharacterState w = Hero("class.warrior", 3);
    w.conqueredMaps = {"map.act1.crypt"};
    w.skillBar = {"skill.warrior.iron_cut", "skill.warrior.charge", "skill.warrior.stone_rift", "skill.warrior.shield_bash", "", ""};
    EXPECT_ENUM_EQ(CanStartExpedition(db, w, "map.act1.crypt", 1, 12, false, 3, nullptr), StartCheck::Ok);
    const IdleCalibration base = BuildIdleCalibration(db, w);
    EXPECT_TRUE(base != IdleCalibration::None);
    w.skillBar[4] = "skill.warrior.combo_3";
    w.skillBar[5] = "skill.warrior.heavy_slash";
    EXPECT_ENUM_EQ(CanStartExpedition(db, w, "map.act1.crypt", 1, 12, false, 3, nullptr), StartCheck::Ok);
    EXPECT_TRUE(BuildIdleCalibration(db, w) == base);
    EXPECT_TRUE(IsKitOnlySkill(db, "class.warrior", "skill.warrior.heavy_slash"));
    EXPECT_TRUE(IsKitOnlySkill(db, "class.warrior", "skill.warrior.combo_2"));
    EXPECT_FALSE(IsKitOnlySkill(db, "class.warrior", "skill.warrior.iron_cut"));  // o golpe 1 conta
    EXPECT_FALSE(IsKitOnlySkill(db, "class.warrior", "skill.warrior.charge"));
    EXPECT_FALSE(IsKitOnlySkill(db, "class.nope", "skill.warrior.heavy_slash"));
}

// ---------------------------------------------------------------------------------------------------------------------
// Multiplicador do ataque forte (docs/18 1.4): regra do core, aplicada como `more` neste golpe
// ---------------------------------------------------------------------------------------------------------------------
TEST(combat_basic_heavy_charge_multiplier_is_linear_and_rejects_out_of_range) {
    const BasicKitData* kit = Real().FindBasicKit("class.warrior");
    ASSERT_TRUE(kit != nullptr && kit->heavyMaxMult > 1.0);
    double m = -1.0;
    ASSERT_TRUE(HeavyChargeMultiplier(*kit, 0.0, m));
    EXPECT_NEAR(m, 1.0, 0.0);
    ASSERT_TRUE(HeavyChargeMultiplier(*kit, 1.0, m));
    EXPECT_NEAR(m, kit->heavyMaxMult, 1e-12);
    ASSERT_TRUE(HeavyChargeMultiplier(*kit, 0.5, m));
    EXPECT_NEAR(m, 1.0 + (kit->heavyMaxMult - 1.0) * 0.5, 1e-12);
    m = -7.0;
    for (double bad : {-0.001, 1.001, 2.0, -1.0, std::nan(""), HUGE_VAL}) {
        EXPECT_FALSE(HeavyChargeMultiplier(*kit, bad, m));
        EXPECT_NEAR(m, -7.0, 0.0);  // saída intacta
    }
}

TEST(combat_basic_hit_more_multiplies_this_hit_only_before_the_crit) {
    const ContentDB& db = Real();
    StatBlock atk, def;
    def.SetBase(StatId::Life, 10000.0);
    atk.SetBase(StatId::CritChance, 1.0);  // sempre critica: o `more` entra antes do multiplicador do crítico
    auto hit = [&](double more) {
        HitInput in;
        in.attacker = &atk;
        in.defender = &def;
        in.skillTags = Tag::Attack | Tag::Melee | Tag::Physical;
        in.baseDamage[0] = 100.0;
        in.coefficient = 1.0;
        in.defenderLife = 10000.0;
        in.hitMore = more;
        Pcg32 rng = Pcg32::ForStream(5, RngStream::Combat, 0);
        const HitResult r = ResolveHit(in, db.Rules(), rng);
        return std::make_pair(r, rng.State());
    };
    const auto base = hit(1.0);
    const auto heavy = hit(1.5);
    EXPECT_TRUE(base.first.critical && heavy.first.critical);
    EXPECT_NEAR(heavy.first.totalDamage, base.first.totalDamage * 1.5, 1e-9);
    EXPECT_EQ(base.second, heavy.second);  // mesmo consumo de RNG
    // Soma com um `more` do atacante (multiplicam entre si), não substitui.
    Modifier mod;
    mod.stat = StatId::Damage;
    mod.kind = ModKind::More;
    mod.value = 0.2;
    mod.source = "t";
    atk.AddModifier(mod);
    EXPECT_NEAR(hit(1.5).first.totalDamage, base.first.totalDamage * 1.2 * 1.5, 1e-9);
}
