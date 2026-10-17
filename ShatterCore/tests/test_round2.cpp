// Rodada 2 (docs/13, "Balanceamento e dados"): dano desarmado, fichas de ataque no simulador, telegraph do elite Veloz,
// summonAtFraction, wallStaggerSeconds, patrolSpeedMult, requireOnScreen e require_on_screen_margin.
#include <cmath>
#include <memory>

#include "test_util.h"

using namespace shatter;

namespace {

using Overrides = std::vector<std::pair<std::string, std::string>>;

// Conteúdo REAL com tabelas trocadas.
std::unique_ptr<ContentDB> RealDb(const Overrides& ov = {}) {
    auto db = std::make_unique<ContentDB>();
    for (const char* t : tu::kTableNames) {
        const std::string path = tu::ContentDir() + "/" + t;
        if (tu::IsOptionalTable(t) && !std::filesystem::exists(std::filesystem::u8path(path))) continue;
        std::string text = tu::ReadFile(path);
        for (const auto& o : ov)
            if (o.first == t) text = o.second;
        db->LoadTableCsv(t, text);
    }
    db->Finalize();
    return db;
}

std::unique_ptr<ContentDB> RichWith(const Overrides& ov) {
    auto db = std::make_unique<ContentDB>();
    for (const char* t : tu::kTableNames) {
        std::string text = tu::ReadFile(tu::RichDir() + "/" + t);
        for (const auto& o : ov)
            if (o.first == t) text = o.second;
        db->LoadTableCsv(t, text);
    }
    db->Finalize();
    return db;
}

std::string Table(const std::string& name) { return tu::ReadFile(tu::RichDir() + "/" + name); }

ExpeditionRequest BareHero(const ContentDB& db, int level, bool sword) {
    ExpeditionRequest req;
    CharacterState& c = req.snapshot.character;
    c.name = "R2";
    c.classId = "class.warrior";
    c.level = level;
    c.skills = {{"skill.warrior.iron_cut", 1, {}}};
    c.skillBar[0] = "skill.warrior.iron_cut";
    if (sword) {
        ItemInstance it;
        it.uid = 1;
        it.baseId = "item_base.iron_sword";
        c.equipment[static_cast<std::size_t>(ItemSlot::MainHand)] = it;
    }
    c.conqueredMaps = {"map.act1.crypt"};
    req.snapshot.contentVersion = db.ContentVersion();
    req.contentVersion = db.ContentVersion();
    req.mapId = "map.act1.crypt";
    req.rules = {{AiCondition::Always, 0.0, AiAction::UseSkill, "skill.warrior.iron_cut"}};
    req.seed = 77;
    req.startUtc = 1'700'000'000;
    req.durationHours = 1;
    req.effectiveSeconds = 3600.0;
    return req;
}

}  // namespace

// ---------------------------------------------------------------------------------------------
// Dano desarmado
// ---------------------------------------------------------------------------------------------
TEST(r2_unarmed_weapon_damage_comes_from_rules_and_is_used_by_idle_and_manual) {
    const std::unique_ptr<ContentDB> real = RealDb();
    ASSERT_TRUE(real->Errors().empty());
    const double unarmed = real->Rules().unarmedWeaponDamagePhysical;
    EXPECT_TRUE(unarmed > 0.0);
    EXPECT_TRUE(real->Rules().requireOnScreenMargin >= 0.0);
    const SkillData* cut = real->FindSkill("skill.warrior.iron_cut");
    ASSERT_TRUE(cut != nullptr && cut->scalesWithWeapon);
    // Sem arma: só físico, o valor da regra. Com arma: o dano da arma. Golpe que não escala: o dele.
    const auto bare = ComputeSkillBaseDamage(*real, *cut, nullptr);
    EXPECT_NEAR(bare[0], unarmed, 0.0);
    EXPECT_NEAR(bare[1] + bare[2] + bare[3], 0.0, 0.0);
    const ItemBaseData* sword = real->FindItemBase("item_base.iron_sword");
    EXPECT_NEAR(ComputeSkillBaseDamage(*real, *cut, sword)[0], sword->weaponDamage[0], 0.0);
    const SkillData* strike = real->FindSkill("skill.enemy.sentinel_strike");
    EXPECT_NEAR(ComputeSkillBaseDamage(*real, *strike, nullptr)[0], strike->baseDamage[0], 0.0);
    // Idle: o herói desarmado mata (antes causava 0 de dano e o encontro só terminava por recuo).
    ExpeditionRequest req = BareHero(*real, 20, false);
    const ExpeditionResult r = SimulateExpedition(*real, req);
    EXPECT_TRUE(r.kills > 0);
    double dealt = 0.0;
    for (const EncounterReceipt& rc : r.receipts) dealt += rc.damageDealt;
    EXPECT_TRUE(dealt > 0.0);
    // O dano vem da regra: com 0 o herói desarmado volta a não causar dano.
    std::string rulesText = tu::ReadFile(tu::ContentDir() + "/rules.csv");
    const std::size_t at = rulesText.find("unarmed_weapon_damage_physical,");
    ASSERT_TRUE(at != std::string::npos);
    const std::size_t eol = rulesText.find_first_of("\r\n", at);
    rulesText.replace(at, eol - at, "unarmed_weapon_damage_physical,0");
    const std::unique_ptr<ContentDB> zero = RealDb({{"rules.csv", rulesText}});
    ASSERT_TRUE(zero->Errors().empty());
    const ExpeditionResult none = SimulateExpedition(*zero, BareHero(*zero, 20, false));
    EXPECT_EQ(none.kills, 0);
    // Com espada equipada o dano é o da espada, não o desarmado (mais kills no mesmo tempo).
    const ExpeditionResult armed = SimulateExpedition(*real, BareHero(*real, 20, true));
    EXPECT_TRUE(armed.kills > r.kills);
}

// ---------------------------------------------------------------------------------------------
// Fichas de ataque
// ---------------------------------------------------------------------------------------------
TEST(r2_attack_tokens_limit_simultaneous_attackers_of_the_same_enemy_in_idle) {
    const std::string header = Table("enemy_ai.csv").substr(0, Table("enemy_ai.csv").find('\n') + 1);
    auto aiRow = [&](int tokens) {
        std::vector<std::string> cells(21);
        cells[0] = "enemy.hollow_sentinel";
        cells[1] = "6";
        cells[12] = tokens > 0 ? std::to_string(tokens) : std::string();
        std::string row;
        for (std::size_t i = 0; i < cells.size(); ++i) row += (i ? "," : "") + cells[i];
        return header + row + "\n";
    };
    // Um bando de 5 sentinelas por encontro; sem elite sorteado.
    const std::string enc =
        "id,groups,weight,travelTime,isBoss\nenc.crypt.patrol_a,enemy.hollow_sentinel:5:5:0,1,5,false\n"
        "enc.crypt.guardian,enemy.crypt_guardian:1:1:0,1,10,true\n";
    const std::string maps = "id,monsterLevel,tier,encounters,bossEncounter,areaLootTable,idleAllowed\n"
                             "map.act1.crypt,4,0,enc.crypt.patrol_a,enc.crypt.guardian,loot.crypt.area,true\n";
    auto meanDamage = [&](int tokens) {
        const std::unique_ptr<ContentDB> db = RichWith({{"enemy_ai.csv", aiRow(tokens)}, {"encounters.csv", enc}, {"maps.csv", maps}});
        EXPECT_TRUE(db->Errors().empty());
        double taken = 0.0, dur = 0.0;
        int n = 0;
        for (std::uint64_t seed = 1; seed <= 30; ++seed) {
            ExpeditionRequest req = tu::MakeRequest(*db, 1, seed, 8, 3);
            const ExpeditionProgress p = SimulateRange(*db, req, ExpeditionProgress(), 0, 3);
            for (const EncounterReceipt& rc : p.receipts) { taken += rc.damageTaken; dur += rc.duration; ++n; }
        }
        return std::make_pair(taken / n, dur / n);
    };
    const auto free = meanDamage(0), two = meanDamage(2), one = meanDamage(1);
    EXPECT_TRUE(one.first < two.first);        // menos atacantes ao mesmo tempo, menos dano
    EXPECT_TRUE(two.first < free.first);
    // Determinismo e fatias com as fichas em jogo (ordem de rodízio estável).
    const std::unique_ptr<ContentDB> db = RichWith({{"enemy_ai.csv", aiRow(2)}, {"encounters.csv", enc}, {"maps.csv", maps}});
    ExpeditionRequest req = tu::MakeRequest(*db, 1, 5, 8, 3);
    const ExpeditionResult whole = SimulateExpedition(*db, req);
    ExpeditionProgress parts;
    int guard = 0;
    while (parts.stop == StopReason::None && ++guard < 100000) parts = SimulateRange(*db, req, parts, parts.nextEncounter, 9);
    EXPECT_EQ(FinalizeExpedition(*db, req, parts).resultHash, whole.resultHash);
    EXPECT_EQ(SimulateExpedition(*db, req).resultHash, whole.resultHash);
}

TEST(r2_attack_tokens_in_real_content_exist_for_hounds_and_do_not_apply_to_enemies_without_ai_row) {
    const std::unique_ptr<ContentDB> real = RealDb();
    ASSERT_TRUE(real->FindEnemyAi("enemy.ash_hound") != nullptr);
    EXPECT_TRUE(real->FindEnemyAi("enemy.ash_hound")->attackTokens > 0);
    EXPECT_TRUE(real->FindEnemyAi("enemy.swift_ash_hound")->attackTokens > 0);
    EXPECT_TRUE(real->FindEnemyAi("enemy.hollow_sentinel") == nullptr);   // sem linha: sem limite
    EXPECT_TRUE(real->FindEnemyAi("enemy.ghost_archer")->maxSimultaneousShooters > 0);
}

// ---------------------------------------------------------------------------------------------
// Telegraph do elite Veloz
// ---------------------------------------------------------------------------------------------
TEST(r2_swift_elite_keeps_the_telegraph_with_or_without_the_modifier_stats) {
    const std::unique_ptr<ContentDB> real = RealDb();
    const EnemyData* hound = real->FindEnemy("enemy.swift_ash_hound");
    const SkillData* bite = real->FindSkill("skill.enemy.ash_bite");
    ASSERT_TRUE(hound != nullptr && bite != nullptr);
    const double windup = bite->windup;
    const EliteModifierData* swift = real->FindEliteModifier(hound->modifierId);
    ASSERT_TRUE(swift != nullptr);
    const double atk = swift->attackSpeedMult, rec = swift->recoveryMult;
    EXPECT_TRUE(atk > 0.0);
    const EliteProfile prof = MakeEliteProfile(*real, swift, false);
    StatBlock plain;
    BuildEnemyStatBlock(*hound, 3, plain);
    const ActionTimingInfo common = ComputeActionTiming(*real, *bite, plain);
    EXPECT_NEAR(common.windup, windup, 1e-12);
    // (a) bloco SEM os mods do modificador (o caso do bug: 0,3 virava 0,375)
    const ActionTimingInfo noMods = ComputeActionTiming(*real, *bite, plain, &prof);
    EXPECT_NEAR(noMods.windup, windup, 1e-12);
    // (b) bloco COM os mods
    StatBlock withMods = plain;
    ApplyEliteToStats(prof, withMods);
    const ActionTimingInfo withEliteMods = ComputeActionTiming(*real, *bite, withMods, &prof);
    EXPECT_NEAR(withEliteMods.windup, windup, 1e-12);
    // O resultado é o mesmo nos dois casos: impacto ÷ attackSpeedMult e recuperação × recoveryMult ÷ attackSpeedMult.
    EXPECT_NEAR(noMods.impact, withEliteMods.impact, 1e-12);
    EXPECT_NEAR(noMods.recovery, withEliteMods.recovery, 1e-12);
    EXPECT_NEAR(withEliteMods.impact, bite->impact / atk, 1e-12);
    EXPECT_NEAR(withEliteMods.recovery, bite->recovery * rec / atk, 1e-12);
    // O telegraph nunca encurta nem alonga com o modificador; o ciclo muda só por impacto e recuperação.
    const double swiftCycle = withEliteMods.windup + withEliteMods.impact + withEliteMods.recovery;
    EXPECT_NEAR(swiftCycle, windup + (bite->impact + bite->recovery * rec) / atk, 1e-12);
}

// ---------------------------------------------------------------------------------------------
// Dados novos lidos pelo core
// ---------------------------------------------------------------------------------------------
TEST(r2_new_columns_are_read_from_the_real_content) {
    const std::unique_ptr<ContentDB> real = RealDb();
    ASSERT_TRUE(real->Errors().empty());
    const double frac = real->FindBossPhase("enemy.crypt_guardian", 2)->summonAtFraction;
    EXPECT_TRUE(frac > 0.0 && frac < 1.0);
    EXPECT_NEAR(real->FindBossPhase("enemy.crypt_guardian", 1)->summonAtFraction, 0.0, 0.0);
    EXPECT_TRUE(real->FindSkill("skill.enemy.guardian_shield_charge")->wallStaggerSeconds > 0.0);
    EXPECT_NEAR(real->FindSkill("skill.enemy.guardian_hammer")->wallStaggerSeconds, 0.0, 0.0);
    const double patrol = real->FindEnemy("enemy.hollow_sentinel")->patrolSpeedMult;
    EXPECT_TRUE(patrol > 0.0 && patrol <= 1.0);
    EXPECT_NEAR(real->FindEnemy("enemy.ash_hound")->patrolSpeedMult, 0.0, 0.0);
    EXPECT_TRUE(real->FindEnemyAi("enemy.ghost_archer")->requireOnScreen);
    EXPECT_FALSE(real->FindEnemyAi("enemy.ash_hound")->requireOnScreen);
    // O valor é balanceamento (docs/09 §8.2); o teste só garante que a coluna foi lida e reduz o dano.
    for (const char* id : {"skill.warrior.iron_cut", "skill.warrior.charge", "skill.warrior.stone_rift", "skill.warrior.shield_bash"}) {
        const double m = real->FindSkill(id)->idle.damageTakenMult;
        EXPECT_TRUE(m > 0.0 && m < 1.0);
    }
}

TEST(r2_new_columns_are_validated) {
    auto fails = [&](const std::string& tag, const std::string& table, const std::string& text, const std::string& code) {
        ContentDB db;
        tu::LoadFixture(db, tu::RichDir(), table, text);
        if (db.Finalize()) { FAIL(tag + ": passou"); return; }
        for (const ContentError& e : db.Errors())
            if (e.table == table && e.message.rfind(code, 0) == 0) return;
        FAIL(tag + ": codigo " + code + " nao apareceu");
    };
    fails("invocacao sem fracao", "boss_phases.csv", tu::Replace(Table("boss_phases.csv"), ",0.6,1.1,0.5", ",0.6,1.1,"), "E_RULE");
    fails("fracao 1", "boss_phases.csv", tu::Replace(Table("boss_phases.csv"), ",0.6,1.1,0.5", ",0.6,1.1,1"), "E_RULE");
    fails("patrulha acima de 1", "enemies.csv", tu::Replace(Table("enemies.csv"), ",0.5\n", ",1.5\n"), "E_RANGE");
    fails("stagger de parede negativo", "skills.csv", tu::Replace(Table("skills.csv"), ",2.0\n", ",-1\n"), "E_RANGE");
    fails("requireOnScreen invalido", "enemy_ai.csv", tu::Replace(Table("enemy_ai.csv"), "2.0,2,true", "2.0,2,yes"), "E_TYPE");
    fails("margem negativa", "rules.csv", tu::Replace(Table("rules.csv"), "require_on_screen_margin,100", "require_on_screen_margin,-5"), "E_RANGE");
}

TEST(r2_summon_moment_is_data_not_a_constant) {
    // 0,25 da transição de 2,0 s: o marcador e o surgimento caem em 0,5 s (com 0,5 caíam em 1,0 s).
    std::string phases = Table("boss_phases.csv");
    phases = tu::Replace(phases, ",0.6,1.1,0.5", ",0.6,1.1,0.25");
    const std::unique_ptr<ContentDB> db = RichWith({{"boss_phases.csv", phases}});
    ASSERT_TRUE(db->Errors().empty());
    const EnemyData* boss = db->FindEnemy("enemy.crypt_guardian");
    BossFight fight(*db, *boss, 4, 1);
    StatBlock sb;
    BuildEnemyStatBlock(*boss, 4, sb);
    std::vector<BossEvent> ev;
    fight.Start();
    BossFight::Context c;
    c.player = {0.0, 1000.0};
    fight.Step(1.0 / 60.0, c, sb, ev);
    fight.ApplyDamage(fight.MaxLife(), c.boss, {0.0, -400.0}, ev);
    double marker = -1.0, spawnAt = -1.0, t = 0.0;
    for (const BossEvent& e : ev)
        if (e.kind == BossEvent::Kind::SummonMarker) marker = e.seconds;
    for (int i = 0; i < 60 * 3 && spawnAt < 0.0; ++i) {
        ev.clear();
        fight.Step(1.0 / 60.0, c, sb, ev);
        t += 1.0 / 60.0;
        for (const BossEvent& e : ev)
            if (e.kind == BossEvent::Kind::SummonSpawn) spawnAt = t;
    }
    EXPECT_NEAR(marker, 0.5, 1e-12);
    EXPECT_NEAR(spawnAt, 0.5, 2.0 / 60.0);
}

TEST(r2_charge_hitting_a_wall_staggers_the_boss_and_drops_the_shield) {
    // Fase 2 do Guardião: a Investida do Escudo (wallStaggerSeconds 2,0) em impacto.
    bool tested = false;
    for (std::uint64_t seed = 1; seed <= 40 && !tested; ++seed) {
        const ContentDB& db = tu::RichDb();
        const EnemyData* boss = db.FindEnemy("enemy.crypt_guardian");
        BossFight fight(db, *boss, 4, seed);
        StatBlock sb;
        BuildEnemyStatBlock(*boss, 4, sb);
        std::vector<BossEvent> ev;
        BossFight::Context c;
        c.player = {0.0, 900.0};
        fight.Start();
        fight.Step(1.0 / 60.0, c, sb, ev);
        // Sem padrão em impacto: nada acontece.
        EXPECT_FALSE(fight.OnWallHit(sb, ev));
        fight.ApplyDamage(fight.MaxLife(), c.boss, {0.0, -400.0}, ev);
        for (int i = 0; i < 60 * 3; ++i) fight.Step(1.0 / 60.0, c, sb, ev);   // rugido da fase 2
        ASSERT_TRUE(fight.Phase() == 2);
        bool hammerChecked = false;
        for (int i = 0; i < 60 * 120 && !tested; ++i) {
            fight.Step(1.0 / 60.0, c, sb, ev);
            if (fight.State() != BossState::Impact || fight.CurrentPattern() == nullptr) continue;
            if (fight.CurrentPattern()->id != "pattern.guardian.shield_charge") {
                if (!hammerChecked) {
                    EXPECT_FALSE(fight.OnWallHit(sb, ev));          // martelo/pancada não têm stagger de parede
                    hammerChecked = true;
                }
                continue;
            }
            ev.clear();
            ASSERT_TRUE(fight.OnWallHit(sb, ev));
            EXPECT_TRUE(fight.State() == BossState::Stagger);
            EXPECT_FALSE(fight.ShieldUp());
            EXPECT_NEAR(fight.ShieldDownRemaining(), 5.0, 1e-9);
            EXPECT_NEAR(sb.Get(StatId::DamageTaken), 1.3, 1e-9);
            int interrupted = 0, staggerStart = 0, shieldDown = 0;
            double seconds = 0.0;
            for (const BossEvent& e : ev) {
                interrupted += e.kind == BossEvent::Kind::PatternInterrupted ? 1 : 0;
                if (e.kind == BossEvent::Kind::StaggerStart) { ++staggerStart; seconds = e.seconds; }
                shieldDown += e.kind == BossEvent::Kind::ShieldDown ? 1 : 0;
            }
            EXPECT_EQ(interrupted, 1);
            EXPECT_EQ(staggerStart, 1);
            EXPECT_EQ(shieldDown, 1);
            EXPECT_NEAR(seconds, 2.0, 0.0);
            EXPECT_FALSE(fight.OnWallHit(sb, ev));                  // já em stagger
            // O stagger de parede dura 2,0 s e depois o chefe volta a agir.
            for (int k = 0; k < 60 * 2 + 3; ++k) fight.Step(1.0 / 60.0, c, sb, ev);
            EXPECT_TRUE(fight.State() != BossState::Stagger);
            EXPECT_NEAR(sb.Get(StatId::DamageTaken), 1.0, 1e-9);
            tested = true;
        }
    }
    EXPECT_TRUE(tested);
}
