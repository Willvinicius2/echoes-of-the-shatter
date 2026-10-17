// Elites sorteados (docs/13, item 5), drop do Único (item 9), calibração do idle (item 8), pernas (C-10), visualSetId
// e as validações das tabelas novas.
#include <memory>

#include "test_util.h"

using namespace shatter;

namespace {

using Overrides = std::vector<std::pair<std::string, std::string>>;

std::unique_ptr<ContentDB> MakeDb(const Overrides& ov) {
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

bool HasError(const ContentDB& db, const std::string& table, const std::string& code) {
    for (const ContentError& e : db.Errors())
        if (e.table == table && e.message.rfind(code, 0) == 0) return true;
    return false;
}

void ExpectTableError(const std::string& tag, const std::string& table, const std::string& text, const std::string& code) {
    ContentDB db;
    tu::LoadFixture(db, tu::RichDir(), table, text);
    if (db.Finalize()) { FAIL(tag + ": conteudo invalido passou"); return; }
    if (!HasError(db, table, code)) {
        std::string all;
        for (const ContentError& e : db.Errors()) all += e.table + ":" + std::to_string(e.line) + " " + e.message + "\n";
        FAIL(tag + ": esperado " + table + " " + code + "; obtido:\n" + all);
    }
}

}  // namespace

// ---------------------------------------------------------------------------------------------
// Elite
// ---------------------------------------------------------------------------------------------
TEST(elite_roll_follows_prototype_weights_consumes_one_number_and_volatile_is_off) {
    const ContentDB& db = tu::RichDb();
    ASSERT_TRUE(db.EliteModifiers().size() == 3);
    Pcg32 rng(2026), twin(2026);
    int shield = 0, swift = 0, volatileCount = 0;
    const int n = 20000;
    for (int i = 0; i < n; ++i) {
        const EliteModifierData* m = RollEliteModifier(db, rng);
        ASSERT_TRUE(m != nullptr);
        if (m->id == "modifier.elite.shield") ++shield;
        else if (m->id == "modifier.elite.swift") ++swift;
        else ++volatileCount;
        twin.NextU32();
    }
    EXPECT_EQ(volatileCount, 0);                       // peso 0 = desligado no protótipo
    EXPECT_NEAR(static_cast<double>(shield) / n, 0.5, 0.02);
    EXPECT_NEAR(static_cast<double>(swift) / n, 0.5, 0.02);
    EXPECT_EQ(rng.NextU32(), twin.NextU32());          // exatamente 1 número por sorteio
    // Sem nenhum peso: nullptr, mas ainda consome 1 número.
    const std::unique_ptr<ContentDB> off = MakeDb({{"elite_modifiers.csv",
        "id,weightPrototype,lifeMult,damageMult,xpMult,barrierFractionOfLife,moveSpeedMult,attackSpeedMult,recoveryMult,deathExplosionRadius,deathExplosionDamage,deathExplosionFuse\n"
        "modifier.elite.shield,0,,,,0.4,,,,,,\n"}});
    Pcg32 a(5), b(5);
    EXPECT_TRUE(RollEliteModifier(*off, a) == nullptr);
    b.NextU32();
    EXPECT_EQ(a.NextU32(), b.NextU32());
}

TEST(elite_profiles_stats_barrier_and_fixed_elite_use_only_the_modifier) {
    const ContentDB& db = tu::RichDb();
    const RulesConstants& r = db.Rules();
    EXPECT_NEAR(r.eliteLifeMult, 2.0, 0.0);
    const EnemyData* sentinel = db.FindEnemy("enemy.hollow_sentinel");
    StatBlock normal;
    BuildEnemyStatBlock(*sentinel, 4, normal);
    // Sorteado com Escudo: vida ×2, dano ×1,2, XP ×3 e barreira de 40% da vida máxima.
    const EliteProfile shield = MakeEliteProfile(db, db.FindEliteModifier("modifier.elite.shield"), true);
    EXPECT_TRUE(shield.rolled);
    EXPECT_NEAR(shield.lifeMult, 2.0, 1e-12);
    EXPECT_NEAR(shield.damageMult, 1.2, 1e-12);
    EXPECT_NEAR(shield.xpMult, 3.0, 1e-12);
    StatBlock sb;
    BuildEnemyStatBlock(*sentinel, 4, sb);
    ApplyEliteToStats(shield, sb);
    EXPECT_NEAR(sb.Get(StatId::Life), normal.Get(StatId::Life) * 2.0, 1e-9);
    EXPECT_NEAR(sb.ApplyTagged(StatId::Damage, 0, 10.0), 12.0, 1e-9);
    EXPECT_NEAR(EliteBarrier(shield, sb.Get(StatId::Life)), 0.4 * sb.Get(StatId::Life), 1e-9);
    // Sorteado com Veloz: velocidade +30%, velocidade de ataque +25%, recuperação ×0,8.
    const EliteProfile swift = MakeEliteProfile(db, db.FindEliteModifier("modifier.elite.swift"), true);
    EXPECT_NEAR(swift.moveSpeedMult, 1.3, 0.0);
    EXPECT_NEAR(swift.attackSpeedMult, 1.25, 0.0);
    EXPECT_NEAR(swift.recoveryMult, 0.8, 0.0);
    EXPECT_NEAR(EliteBarrier(swift, 100.0), 0.0, 0.0);
    // Elite fixo: os números do inimigo já são de elite; só o modificador entra (sem ×2 de novo).
    const EliteProfile fixedShield = MakeEliteProfile(db, db.FindEliteModifier("modifier.elite.shield"), false);
    EXPECT_FALSE(fixedShield.rolled);
    EXPECT_NEAR(fixedShield.lifeMult, 1.0, 0.0);
    EXPECT_NEAR(fixedShield.xpMult, 1.0, 0.0);
    EXPECT_NEAR(fixedShield.barrierFractionOfLife, 0.4, 0.0);
    EXPECT_EQ(db.FindEnemy("enemy.shielded_sentinel")->modifierId, std::string("modifier.elite.shield"));
    // Volátil (desligado, mas com números prontos): explosão de raio 250, 25 de dano, fusível 0,8 s.
    const EliteProfile vol = MakeEliteProfile(db, db.FindEliteModifier("modifier.elite.volatile"), true);
    EXPECT_NEAR(vol.deathExplosionRadius, 250.0, 0.0);
    EXPECT_NEAR(vol.deathExplosionDamage, 25.0, 0.0);
    EXPECT_NEAR(vol.deathExplosionFuse, 0.8, 0.0);
    // Tabela de loot do elite sorteado: a coluna opcional; sem ela, a do inimigo.
    EXPECT_EQ(EliteLootTable(*sentinel, true), sentinel->lootTableId);
}

TEST(elite_idle_rolled_elites_give_triple_xp_and_are_deterministic) {
    // Encontro só de sentinelas com 100% de chance de elite vs 0%: o elite rende XP ×3 e vive mais.
    auto mk = [](const std::string& chance) {
        return MakeDb({
            {"encounters.csv", "id,groups,weight,travelTime,isBoss\n"
                               "enc.crypt.patrol_a,enemy.hollow_sentinel:2:2:" + chance + ",1,5,false\n"
                               "enc.crypt.patrol_b,enemy.hollow_sentinel:2:2:" + chance + ",1,5,false\n"
                               "enc.crypt.guardian,enemy.crypt_guardian:1:1:0,1,10,true\n"
                               "enc.crypt.elite_shield,enemy.shielded_sentinel:1:1:0,1,8,false\n"},
            {"rules.csv", tu::Replace(Table("rules.csv"), "xp_base,100.0", "xp_base,1000000000.0")},
            {"maps.csv", "id,monsterLevel,tier,encounters,bossEncounter,areaLootTable,idleAllowed\n"
                         "map.act1.crypt,4,0,enc.crypt.patrol_a|enc.crypt.patrol_b,enc.crypt.guardian,loot.crypt.area,true\n"},
        });
    };
    const std::unique_ptr<ContentDB> none = mk("0"), all = mk("1");
    ExpeditionRequest r0 = tu::MakeRequest(*none, 1, 31), r1 = tu::MakeRequest(*all, 1, 31);
    r0.effectiveSeconds = r1.effectiveSeconds = 1200.0;
    const ExpeditionProgress p0 = SimulateRange(*none, r0, ExpeditionProgress(), 0, 8);
    const ExpeditionProgress p1 = SimulateRange(*all, r1, ExpeditionProgress(), 0, 8);
    double xp0 = 0.0, xp1 = 0.0, dur0 = 0.0, dur1 = 0.0;
    int elites0 = 0, elites1 = 0, kills0 = 0, kills1 = 0;
    for (const EncounterReceipt& rc : p0.receipts) { xp0 += rc.xpRaw; elites0 += rc.elitesKilled; kills0 += rc.kills; dur0 += rc.duration; }
    for (const EncounterReceipt& rc : p1.receipts) { xp1 += rc.xpRaw; elites1 += rc.elitesKilled; kills1 += rc.kills; dur1 += rc.duration; }
    EXPECT_EQ(elites0, 0);
    EXPECT_EQ(elites1, kills1);
    EXPECT_TRUE(kills0 > 0 && kills1 > 0);
    EXPECT_NEAR((xp1 / kills1) / (xp0 / kills0), 3.0, 1e-6);   // XP ×3 por elite sorteado
    EXPECT_TRUE(dur1 / static_cast<double>(p1.receipts.size()) > dur0 / static_cast<double>(p0.receipts.size()));
    // Determinismo (mesma seed, em 1 ou N partes).
    ExpeditionProgress q;
    for (int i = 0; i < 8; ++i) q = SimulateRange(*all, r1, q, q.nextEncounter, 1);
    EXPECT_EQ(FinalizeExpedition(*all, r1, q).resultHash, FinalizeExpedition(*all, r1, p1).resultHash);
}

TEST(elite_fixed_shield_barrier_absorbs_damage_in_idle) {
    // O elite fixo com Escudo tem barreira inicial: o mesmo inimigo sem o modificador morre mais rápido.
    auto mk = [](bool shield) {
        std::string enemies = Table("enemies.csv");
        if (!shield) enemies = tu::Replace(enemies, ",true,,,,1.5,4,modifier.elite.shield", ",true,,,,1.5,4,");
        return MakeDb({
            {"enemies.csv", enemies},
            {"maps.csv", "id,monsterLevel,tier,encounters,bossEncounter,areaLootTable,idleAllowed\n"
                         "map.act1.crypt,4,0,enc.crypt.elite_shield,enc.crypt.guardian,loot.crypt.area,true\n"},
        });
    };
    const std::unique_ptr<ContentDB> with = mk(true), without = mk(false);
    double d1 = 0.0, d0 = 0.0;
    for (std::uint64_t seed = 1; seed <= 20; ++seed) {
        ExpeditionRequest a = tu::MakeRequest(*with, 1, seed), b = tu::MakeRequest(*without, 1, seed);
        a.effectiveSeconds = b.effectiveSeconds = 300.0;
        const ExpeditionProgress pa = SimulateRange(*with, a, ExpeditionProgress(), 0, 1);
        const ExpeditionProgress pb = SimulateRange(*without, b, ExpeditionProgress(), 0, 1);
        d1 += pa.receipts[0].duration;
        d0 += pb.receipts[0].duration;
        EXPECT_EQ(pa.receipts[0].elitesKilled, 1);
    }
    EXPECT_TRUE(d1 > d0);
}

// ---------------------------------------------------------------------------------------------
// Único do Guardião
// ---------------------------------------------------------------------------------------------
namespace {

const char* kUniqueId = "unique.bell_warden_blade";

bool DropsUnique(const LootDrop& d) {
    for (const ItemInstance& it : d.items)
        if (it.uniqueId == kUniqueId) return true;
    return false;
}

std::unique_ptr<ContentDB> BossDb(const std::string& uniqueRow) {
    std::string loot = Table("loot_entries.csv");
    loot = tu::Replace(loot, "loot.crypt.guardian,unique,unique.bell_warden_blade,,1,1,1,999,true,0.2,true,5", uniqueRow);
    return MakeDb({{"loot_entries.csv", loot}});
}

}  // namespace

TEST(unique_first_kill_guaranteed_then_pity_on_fifth_after_a_drop) {
    // Chance fixa 0: só a garantia da 1ª vitória e a proteção (5ª depois do último drop) fazem o Único cair.
    const std::unique_ptr<ContentDB> dbp = BossDb("loot.crypt.guardian,unique,unique.bell_warden_blade,,1,1,1,999,true,0,true,5");
    const ContentDB& db = *dbp;
    ASSERT_TRUE(db.Errors().empty());
    const EnemyData* boss = db.FindEnemy("enemy.crypt_guardian");
    BossProgressEntry prog;
    prog.enemyId = boss->id;
    std::uint64_t uid = 100;
    Pcg32 rng(9);
    std::vector<int> dropKills;
    for (int kill = 1; kill <= 15; ++kill) {
        const LootDrop d = RollBossLoot(db, *boss, 3, prog, &uid, rng);
        if (DropsUnique(d)) dropKills.push_back(kill);
        EXPECT_EQ(prog.kills, kill);
    }
    ASSERT_TRUE(dropKills.size() == 3);
    EXPECT_EQ(dropKills[0], 1);                         // 1ª vitória: garantido
    EXPECT_EQ(dropKills[1], 6);                         // 4 sem sorte (2 a 5), a 5ª depois do drop é garantida
    EXPECT_EQ(dropKills[2], 11);
    EXPECT_EQ(prog.killsSinceUnique, 4);                // 12 a 15 sem drop ainda (o próximo, 16ª, é o garantido)
}

TEST(unique_chance_after_first_kill_is_20_percent_and_counter_resets_on_drop) {
    // Sem proteção e sem garantia: 20% por vitória (o peso não dilui as outras entradas).
    const std::unique_ptr<ContentDB> dbp = BossDb("loot.crypt.guardian,unique,unique.bell_warden_blade,,1,1,1,999,true,0.2,false,0");
    const ContentDB& db = *dbp;
    const EnemyData* boss = db.FindEnemy("enemy.crypt_guardian");
    BossProgressEntry prog;
    prog.enemyId = boss->id;
    prog.kills = 3;                                     // já venceu antes
    Pcg32 rng(1234);
    std::uint64_t uid = 1;
    int drops = 0;
    const int n = 20000;
    for (int i = 0; i < n; ++i) {
        const int before = prog.killsSinceUnique;
        const LootDrop d = RollBossLoot(db, *boss, 3, prog, &uid, rng);
        if (DropsUnique(d)) {
            ++drops;
            EXPECT_EQ(prog.killsSinceUnique, 0);
        } else {
            EXPECT_EQ(prog.killsSinceUnique, before + 1);
        }
    }
    EXPECT_NEAR(static_cast<double>(drops) / n, 0.2, 0.012);
    // As outras entradas da tabela continuam saindo (o Único não ocupa o peso delas).
    const LootDrop d = RollBossLoot(db, *boss, 3, prog, &uid, rng);
    EXPECT_TRUE(!d.items.empty() || !d.stacks.empty());
}

TEST(unique_drop_is_deterministic_never_idle_and_counter_is_saved) {
    const ContentDB& db = tu::RichDb();
    const EnemyData* boss = db.FindEnemy("enemy.crypt_guardian");
    auto run = [&](std::uint64_t seed) {
        BossProgressEntry p;
        p.enemyId = boss->id;
        std::uint64_t uid = 1;
        Pcg32 rng(seed);
        std::string trace;
        for (int i = 0; i < 40; ++i) trace += DropsUnique(RollBossLoot(db, *boss, 3, p, &uid, rng)) ? "U" : ".";
        return trace;
    };
    EXPECT_EQ(run(5), run(5));
    EXPECT_EQ(run(5)[0], 'U');
    // Idle: entradas fixas e o Único nunca saem (dupla checagem), mesmo com chance 1 e progresso de proteção.
    const std::unique_ptr<ContentDB> sure = BossDb("loot.crypt.guardian,unique,unique.bell_warden_blade,,1,1,1,999,true,1,true,1");
    const LootTableData* t = sure->FindLootTable("loot.crypt.guardian");
    LootContext idle;
    idle.mode = LootMode::Idle;
    idle.areaLevel = 3;
    BossProgressEntry p;
    idle.bossProgress = &p;
    Pcg32 rng(77);
    for (int i = 0; i < 2000; ++i) {
        const LootDrop d = RollLootTable(*sure, *t, idle, rng);
        if (DropsUnique(d)) { FAIL("Unico no idle"); break; }
    }
    EXPECT_EQ(p.kills, 0);                              // o contador é só do jogo manual
    // O contador atravessa o save (persistir ANTES de entregar o item: o contador já avançou nesta chamada).
    CharacterState c = tu::MakeWarrior(db, 3);
    c.bossProgress = {{boss->id, 4, 2}};
    SaveData s;
    s.characters.push_back(c);
    SaveData back;
    std::string err;
    ASSERT_TRUE(ParseJson(SerializeJson(s), back, &err) == LoadStatus::Ok);
    ASSERT_TRUE(back.characters[0].bossProgress.size() == 1);
    EXPECT_EQ(back.characters[0].bossProgress[0].kills, 4);
    EXPECT_EQ(back.characters[0].bossProgress[0].killsSinceUnique, 2);
}

// ---------------------------------------------------------------------------------------------
// Calibração do idle
// ---------------------------------------------------------------------------------------------
TEST(idle_calibration_manual_estimate_is_accepted_and_shows_in_forecast_and_report) {
    const ContentDB& db = tu::RichDb();
    EXPECT_ENUM_EQ(db.FindSkill("skill.warrior.shield_bash")->idle.calibration, IdleCalibration::ManualEstimate);
    EXPECT_ENUM_EQ(db.FindSkill("skill.warrior.iron_cut")->idle.calibration, IdleCalibration::BotParity);
    // Build só com habilidades calibradas por paridade: sem selo de estimativa.
    ExpeditionRequest req = tu::MakeRequest(db, 1, 8);
    EXPECT_ENUM_EQ(BuildIdleCalibration(db, req.snapshot.character), IdleCalibration::BotParity);
    const ExpeditionResult plain = SimulateExpedition(db, req);
    EXPECT_ENUM_EQ(plain.calibration, IdleCalibration::BotParity);
    // Escudada (estimativa manual) na barra: o selo da expedição, do relatório e da previsão vira "estimativa".
    req.snapshot.character.skills.push_back({"skill.warrior.shield_bash", 1, {}});
    req.snapshot.character.skillBar[3] = "skill.warrior.shield_bash";
    ExpeditionStartParams unused;
    (void)unused;
    EXPECT_TRUE(IsIdleCompatible(db, req.snapshot.character, nullptr));
    EXPECT_ENUM_EQ(BuildIdleCalibration(db, req.snapshot.character), IdleCalibration::ManualEstimate);
    const ExpeditionResult est = SimulateExpedition(db, req);
    EXPECT_ENUM_EQ(est.calibration, IdleCalibration::ManualEstimate);
    EXPECT_ENUM_EQ(ForecastExpedition(db, req, 5, 5).calibration, IdleCalibration::ManualEstimate);
    EXPECT_ENUM_EQ(ForecastExpedition(db, tu::MakeRequest(db, 1, 8), 5, 5).calibration, IdleCalibration::BotParity);
    // O selo entra no hash do resultado (resultado "estimado" não se confunde com o calibrado).
    ExpeditionRequest same = req;
    EXPECT_EQ(SimulateExpedition(db, same).resultHash, est.resultHash);
    // Único equipado com estimativa manual também puxa o selo.
    ExpeditionRequest withUnique = tu::MakeRequest(db, 1, 8);
    ItemInstance helm;
    helm.uid = 5;
    helm.baseId = "item_base.bone_helm";
    helm.rarity = Rarity::Unique;
    helm.uniqueId = "unique.idle_ready_helm";
    withUnique.snapshot.character.equipment[static_cast<std::size_t>(ItemSlot::Head)] = helm;
    EXPECT_ENUM_EQ(BuildIdleCalibration(db, withUnique.snapshot.character), IdleCalibration::ManualEstimate);
    // A porta de acesso exige amostra > 0 e selo; habilidade sem perfil continua bloqueando.
    ExpeditionRequest blocked = tu::MakeRequest(db, 1, 8);
    blocked.snapshot.character.skills.push_back({"skill.warrior.unsupported_roar", 1, {}});
    blocked.snapshot.character.skillBar[4] = "skill.warrior.unsupported_roar";
    std::vector<ContentId> ids;
    EXPECT_FALSE(IsIdleCompatible(db, blocked.snapshot.character, &ids));
    ASSERT_TRUE(ids.size() == 1);
    EXPECT_EQ(ids[0], std::string("skill.warrior.unsupported_roar"));
}

// ---------------------------------------------------------------------------------------------
// Calça (Legs), visualSetId, validações
// ---------------------------------------------------------------------------------------------
TEST(legs_slot_is_last_roundtrips_in_save_and_adds_modifiers) {
    EXPECT_EQ(kItemSlotCount, 11);
    EXPECT_EQ(static_cast<int>(ItemSlot::Legs), 10);               // no FIM: não desloca os índices da API C
    EXPECT_EQ(static_cast<int>(ItemSlot::Belt), 9);
    ItemSlot s = ItemSlot::MainHand;
    ASSERT_TRUE(ParseItemSlot("legs", s));
    EXPECT_ENUM_EQ(s, ItemSlot::Legs);
    EXPECT_EQ(std::string(ToString(ItemSlot::Legs)), std::string("legs"));
    const ContentDB& db = tu::RichDb();
    CharacterState c = tu::MakeWarrior(db, 1);
    StatBlock bare;
    ASSERT_TRUE(BuildStatBlock(db, c, bare));
    ItemInstance pants;
    pants.uid = 9;
    pants.baseId = "item_base.worn_trousers";
    c.equipment[static_cast<std::size_t>(ItemSlot::Legs)] = pants;
    StatBlock dressed;
    ASSERT_TRUE(BuildStatBlock(db, c, dressed));
    EXPECT_NEAR(dressed.Get(StatId::Armor), bare.Get(StatId::Armor) + 4.0, 1e-9);
    // Calça no lugar errado é recusada.
    CharacterState wrong = tu::MakeWarrior(db, 1);
    wrong.equipment[static_cast<std::size_t>(ItemSlot::Head)] = pants;
    std::string err;
    EXPECT_FALSE(BuildStatBlock(db, wrong, dressed, &err));
    // Save: legs vai no JSON e volta.
    CharacterState back;
    ASSERT_TRUE(CharacterFromJson(CharacterToJson(c), back));
    ASSERT_TRUE(back.equipment[static_cast<std::size_t>(ItemSlot::Legs)].has_value());
    EXPECT_EQ(back.equipment[static_cast<std::size_t>(ItemSlot::Legs)]->baseId, std::string("item_base.worn_trousers"));
    // O conteúdo real tem a base de calça e afixos que valem em legs.
    ContentDB real;
    real.LoadDirectory(tu::ContentDir());
    ASSERT_TRUE(real.Finalize());
    ASSERT_TRUE(real.FindItemBase("item_base.worn_trousers") != nullptr);
    EXPECT_ENUM_EQ(real.FindItemBase("item_base.worn_trousers")->slot, ItemSlot::Legs);
    int legsAffixes = 0;
    for (const AffixData& a : real.Affixes())
        for (ItemSlot sl : a.allowedSlots) legsAffixes += sl == ItemSlot::Legs ? 1 : 0;
    EXPECT_TRUE(legsAffixes > 0);
}

TEST(visual_set_id_is_read_exposed_and_outside_the_result_hash) {
    const ContentDB& db = tu::RichDb();
    EXPECT_EQ(db.FindItemBase("item_base.worn_trousers")->visualSetId, std::string("vset.starter"));
    EXPECT_EQ(db.FindItemBase("item_base.iron_sword")->visualSetId, std::string());   // vazio = fallback do cliente
    ExpectTableError("vset sem prefixo", "item_bases.csv",
                     tu::Replace(Table("item_bases.csv"), "f,vset.starter", "f,visual.starter"), "E_ID_PREFIX");
    // Fora do resultHash e do simulador: trocar o visual não muda a expedição.
    const std::unique_ptr<ContentDB> other = MakeDb({{"item_bases.csv",
        tu::Replace(Table("item_bases.csv"), "f,vset.starter", "f,vset.crypt_knight")}});
    ASSERT_TRUE(other->Errors().empty());
    EXPECT_EQ(SimulateExpedition(db, tu::MakeRequest(db, 1, 3)).resultHash,
              SimulateExpedition(*other, tu::MakeRequest(*other, 1, 3)).resultHash);
}

TEST(content_new_tables_validate_references_ranges_and_keys) {
    // Poções
    ExpectTableError("pocao sem recarga", "potions.csv", Table("potions.csv") + "potion.x,heal,0.1,,1,0,0.4,0.5,1.0,false,3\n", "E_RANGE");
    ExpectTableError("barreira sem duracao", "potions.csv", tu::Replace(Table("potions.csv"), "barrier,0.3,6,", "barrier,0.3,,"), "E_RULE");
    ExpectTableError("tecla repetida", "potions.csv", tu::Replace(Table("potions.csv"), "true,2", "true,1"), "E_DUP_ID");
    ExpectTableError("tipo invalido", "potions.csv", tu::Replace(Table("potions.csv"), "heal", "drink"), "E_ENUM");
    // Modificadores de elite
    ExpectTableError("explosao sem dano", "elite_modifiers.csv", tu::Replace(Table("elite_modifiers.csv"), "250,25,0.8", "250,0,0.8"), "E_RULE");
    // Fases do chefe
    ExpectTableError("fase de quem nao e chefe", "boss_phases.csv", tu::Replace(Table("boss_phases.csv"), "enemy.crypt_guardian,2", "enemy.hollow_sentinel,2"), "E_RULE");
    ExpectTableError("limiar nao decrescente", "boss_phases.csv", tu::Replace(Table("boss_phases.csv"), ",2,0.5,", ",2,1.0,"), "E_RULE");
    ExpectTableError("buraco nas fases", "boss_phases.csv", tu::Replace(Table("boss_phases.csv"), ",2,0.5,", ",3,0.5,"), "E_RULE");
    ExpectTableError("invocado inexistente", "boss_phases.csv", tu::Replace(Table("boss_phases.csv"), "enemy.hollow_sentinel,2", "enemy.nope,2"), "E_FK");
    ExpectTableError("atraso invertido", "boss_phases.csv", tu::Replace(Table("boss_phases.csv"), "60,0.8,1.4", "60,1.5,1.4"), "E_RANGE");
    // Padrões do chefe (chave id + phase)
    ExpectTableError("padrao com skill inexistente", "boss_patterns.csv", tu::Replace(Table("boss_patterns.csv"), "skill.enemy.guardian_shield_charge", "skill.enemy.nope"), "E_FK");
    ExpectTableError("padrao em fase inexistente", "boss_patterns.csv", Table("boss_patterns.csv") + "pattern.guardian.x,enemy.crypt_guardian,3,skill.enemy.guardian_hammer,1,1,1,,2,,false\n", "E_FK");
    ExpectTableError("padrao repetido na fase", "boss_patterns.csv",
                     Table("boss_patterns.csv") + "pattern.guardian.hammer,enemy.crypt_guardian,1,skill.enemy.guardian_hammer,3,1.1,1.0,,2,,false\n", "E_DUP_ID");
    ExpectTableError("padrao sem prefixo", "boss_patterns.csv", tu::Replace(Table("boss_patterns.csv"), "pattern.guardian.shield_charge", "guardian.charge"), "E_ID_PREFIX");
    // IA dos comuns
    ExpectTableError("ia de inimigo inexistente", "enemy_ai.csv", tu::Replace(Table("enemy_ai.csv"), "enemy.ash_spitter", "enemy.nope"), "E_FK");
    ExpectTableError("faixa invertida", "enemy_ai.csv", tu::Replace(Table("enemy_ai.csv"), "700,1100", "1100,700"), "E_RANGE");
    // Colunas novas
    ExpectTableError("modificador inexistente", "enemies.csv", tu::Replace(Table("enemies.csv"), "modifier.elite.shield", "modifier.elite.nope"), "E_FK");
    ExpectTableError("selo desconhecido no unico", "uniques.csv", tu::Replace(Table("uniques.csv"), "20,manual_estimate", "20,guess"), "E_ENUM");
    ExpectTableError("chance fixa fora de [0,1]", "loot_entries.csv", tu::Replace(Table("loot_entries.csv"), "true,0.2,true,5", "true,1.2,true,5"), "E_RANGE");
    ExpectTableError("entrada fixa sem manualOnly", "loot_entries.csv", tu::Replace(Table("loot_entries.csv"), "999,true,0.2,true,5", "999,false,0.2,true,5"), "E_RULE");
    // Chaves novas de rules.csv: faixas e coerência
    ExpectTableError("i-frames maiores que a esquiva", "rules.csv", tu::Replace(Table("rules.csv"), "dodge_iframes,0.2", "dodge_iframes,0.5"), "E_RULE");
    ExpectTableError("cargas de esquiva zero", "rules.csv", tu::Replace(Table("rules.csv"), "dodge_max_charges,3", "dodge_max_charges,0"), "E_RANGE");
    // Cabeçalho das tabelas novas: coluna faltando ou sobrando
    ExpectTableError("coluna faltando em potions", "potions.csv", "id,kind\npotion.life,heal\n", "E_HEADER");
    ExpectTableError("coluna extra em enemy_ai", "enemy_ai.csv", Table("enemy_ai.csv").substr(0, Table("enemy_ai.csv").find('\n')) + ",x\n", "E_HEADER");
}

TEST(content_real_prototype_tables_load_and_validate) {
    ContentDB real;
    real.LoadDirectory(tu::ContentDir());
    std::string all;
    for (const ContentError& e : real.Errors()) all += e.table + ":" + std::to_string(e.line) + " " + e.message + "\n";
    ASSERT_TRUE(real.Finalize());
    // Só invariantes (carrega, coluna lida, faixa, coerência): os NÚMEROS são do Game Designer e mudam no CSV sem tocar em C++.
    EXPECT_TRUE(!real.Potions().empty());
    EXPECT_TRUE(!real.EliteModifiers().empty());
    EXPECT_TRUE(real.BossPhases().size() >= 2);
    EXPECT_TRUE(!real.BossPatterns().empty());
    EXPECT_TRUE(!real.EnemyAis().empty());
    EXPECT_TRUE(real.Rules().retreatLifeFraction > 0.0 && real.Rules().retreatLifeFraction < 1.0);
    EXPECT_TRUE(real.Rules().dodgeRecharge > 0.0 && real.Rules().dodgeMaxCharges >= 1);
    EXPECT_TRUE(real.Rules().dodgeIframes <= real.Rules().dodgeDuration);
    EXPECT_TRUE(real.Rules().potionLockout >= 0.0);
    const double arc = real.FindEnemy("enemy.crypt_guardian")->shieldArcDegrees;
    EXPECT_TRUE(arc > 0.0 && arc <= 360.0);
    EXPECT_TRUE(real.FindUnique("unique.empty_throne_maul")->idleSupported);
    EXPECT_TRUE(real.FindUnique("unique.empty_throne_maul")->idleCalibration != IdleCalibration::None);
    EXPECT_TRUE(real.FindSkill("skill.warrior.shield_bash")->unlockLevel >= 1);
    EXPECT_TRUE(real.FindEffect("effect.stun")->interruptsAction);
    // O Único do Guardião é uma entrada fixa (garantia da 1ª vitória, chance própria e proteção).
    const LootTableData* t = real.FindLootTable("loot.crypt.guardian");
    ASSERT_TRUE(t != nullptr);
    int fixed = 0;
    for (const LootEntry& e : t->entries) {
        if (!e.IsFixed()) continue;
        ++fixed;
        EXPECT_EQ(e.refId, std::string("unique.empty_throne_maul"));
        EXPECT_TRUE(e.guaranteeFirstKill);
        EXPECT_TRUE(e.fixedChance > 0.0 && e.fixedChance <= 1.0);
        EXPECT_TRUE(e.pityKills > 0);
    }
    EXPECT_EQ(fixed, 1);
    // A luta inteira roda no conteúdo real: chefe, fases e padrões.
    BossFight fight(real, *real.FindEnemy("enemy.crypt_guardian"), 3, 99);
    EXPECT_TRUE(fight.Valid());
    StatBlock bossStats;
    BuildEnemyStatBlock(*real.FindEnemy("enemy.crypt_guardian"), 3, bossStats);
    EXPECT_NEAR(fight.MaxLife(), bossStats.Get(StatId::Life), 1e-9);
}

TEST(content_real_idle_expedition_runs_the_new_rules_end_to_end) {
    // Guerreiro com as 4 habilidades do protótipo (todas "estimativa manual") no conteúdo real (Cripta, 4 h).
    ContentDB real;
    real.LoadDirectory(tu::ContentDir());
    ASSERT_TRUE(real.Finalize());
    ExpeditionRequest req;
    CharacterState& c = req.snapshot.character;
    c.name = "Real";
    c.classId = "class.warrior";
    c.level = 20;   // o protótipo ainda não tem equipamento no teste: o nível dá a folga de vida para as 4 h
    c.skills = {{"skill.warrior.iron_cut", 1, {}}, {"skill.warrior.charge", 1, {}}, {"skill.warrior.stone_rift", 1, {}},
                {"skill.warrior.shield_bash", 1, {}}};
    c.skillBar = {"skill.warrior.iron_cut", "skill.warrior.charge", "skill.warrior.stone_rift", "skill.warrior.shield_bash", "", ""};
    ItemInstance sword;
    sword.uid = 1;
    sword.baseId = "item_base.iron_sword";
    c.equipment[static_cast<std::size_t>(ItemSlot::MainHand)] = sword;
    c.conqueredMaps = {"map.act1.crypt"};
    req.snapshot.contentVersion = real.ContentVersion();
    req.contentVersion = real.ContentVersion();
    req.mapId = "map.act1.crypt";
    AiRule heal{AiCondition::LifeBelow, 0.4, AiAction::UsePotion, "potion.life"};
    AiRule ward{AiCondition::TargetIsElite, 0.0, AiAction::UsePotion, "potion.ward"};
    AiRule bash{AiCondition::TargetIsElite, 0.0, AiAction::UseSkill, "skill.warrior.shield_bash"};
    AiRule rift{AiCondition::EnemiesAtLeast, 3.0, AiAction::UseSkill, "skill.warrior.stone_rift"};
    AiRule basic{AiCondition::Always, 0.0, AiAction::UseSkill, "skill.warrior.iron_cut"};
    req.rules = {heal, ward, bash, rift, basic};
    req.seed = 20261016;
    req.startUtc = 1'700'000'000;
    req.durationHours = 4;
    req.effectiveSeconds = 4.0 * 3600.0;
    std::vector<ContentId> blocking;
    EXPECT_ENUM_EQ(CanStartExpedition(real, c, req.mapId, 4, 12, false, req.rules.size(), &blocking), StartCheck::Ok);
    const ExpeditionResult a = SimulateExpedition(real, req);
    const ExpeditionResult b = SimulateExpedition(real, req);
    EXPECT_EQ(a.resultHash, b.resultHash);
    EXPECT_TRUE(a.stop == StopReason::DurationReached || a.stop == StopReason::Retreat);
    if (a.kills <= 100) FAIL("kills=" + std::to_string(a.kills) + " stop=" + std::to_string(static_cast<int>(a.stop)) + " enc=" + std::to_string(a.encountersCleared) + " secs=" + std::to_string(a.effectiveSeconds) + " potions=" + std::to_string(a.potionsUsed) + " heal fail=" + std::to_string(a.healFailures));
    EXPECT_ENUM_EQ(a.calibration, IdleCalibration::ManualEstimate);
    int elites = 0, dodges = 0;
    for (const EncounterReceipt& rc : a.receipts) {
        elites += rc.elitesKilled;
        dodges += rc.dodgesUsed;
    }
    EXPECT_TRUE(elites > 0);      // elites fixos (Sentinela Escudada, Cão Veloz) e sorteados
    EXPECT_TRUE(dodges > 0);
    EXPECT_TRUE(a.potionsUsed > 0);
    // Em fatias o resultado é o mesmo (RNF-02 com as regras novas).
    ExpeditionProgress p;
    int guard = 0;
    while (p.stop == StopReason::None && ++guard < 100000) p = SimulateRange(real, req, p, p.nextEncounter, 7);
    EXPECT_EQ(FinalizeExpedition(real, req, p).resultHash, a.resultHash);
}
