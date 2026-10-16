// Poções (docs/13, item 2), esquiva (item 1), vitals e tempos de ação: regras do core usadas pelo combate em tempo real
// (pela API C) e pelo simulador idle. Os números vêm do fixture rico (cópia do conteúdo real).
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

// Poções que nunca recarregam por tempo: isolam o efeito de "carga +1 ao matar elite".
std::unique_ptr<ContentDB> NoRechargeDb() {
    return MakeDb({{"potions.csv",
                    "id,kind,fractionOfMaxLife,duration,maxCharges,rechargeSeconds,useTime,moveSpeedWhileUsing,globalLockout,"
                    "refillOnEliteKill,hotkeySlot\n"
                    "potion.life,heal,0.4,,3,1000000,0.4,0.5,1.0,true,1\n"
                    "potion.ward,barrier,0.3,6,2,1000000,0.4,0.5,1.0,true,2\n"}});
}

}  // namespace

// ---------------------------------------------------------------------------------------------
// Poções
// ---------------------------------------------------------------------------------------------
TEST(potions_use_spends_charge_starts_global_lockout_and_series_recharge) {
    const ContentDB& db = tu::RichDb();
    PotionBelt belt = MakeFullPotionBelt(db);
    ASSERT_TRUE(belt.slots.size() == 2);
    EXPECT_EQ(PotionCharges(belt, "potion.life"), 3);
    EXPECT_EQ(PotionCharges(belt, "potion.ward"), 2);

    PotionOutcome out;
    EXPECT_ENUM_EQ(UsePotion(db, belt, "potion.life", 200.0, 1.0, &out), PotionUseStatus::Ok);
    EXPECT_EQ(PotionCharges(belt, "potion.life"), 2);
    EXPECT_NEAR(out.healAmount, 80.0, 1e-9);           // 40% de 200
    EXPECT_NEAR(out.barrierAmount, 0.0, 0.0);
    EXPECT_NEAR(out.useTime, 0.4, 1e-12);
    EXPECT_NEAR(out.lockout, 1.0, 1e-12);

    // Trava global de 1,0 s entre QUALQUER poção.
    EXPECT_ENUM_EQ(UsePotion(db, belt, "potion.ward", 200.0, 1.0, &out), PotionUseStatus::LockedOut);
    EXPECT_ENUM_EQ(UsePotion(db, belt, "potion.life", 200.0, 1.0, &out), PotionUseStatus::LockedOut);
    EXPECT_EQ(PotionCharges(belt, "potion.ward"), 2);  // recusa não gasta carga
    TickPotions(db, belt, 0.5);
    EXPECT_ENUM_EQ(UsePotion(db, belt, "potion.ward", 200.0, 1.0, &out), PotionUseStatus::LockedOut);
    TickPotions(db, belt, 0.5);
    EXPECT_ENUM_EQ(UsePotion(db, belt, "potion.ward", 200.0, 1.0, &out), PotionUseStatus::Ok);
    EXPECT_NEAR(out.barrierAmount, 60.0, 1e-9);        // 30% de 200
    EXPECT_NEAR(out.barrierSeconds, 6.0, 1e-12);
    EXPECT_NEAR(out.healAmount, 0.0, 0.0);
    EXPECT_ENUM_EQ(UsePotion(db, belt, "potion.nope", 200.0, 1.0, &out), PotionUseStatus::UnknownPotion);

    // Recarga EM SÉRIE (um relógio só): a Vida estava cheia ao beber; 40 s por carga.
    // Já passou 1 s desde o uso: faltam 39 s para a 1ª carga e mais 40 s para a 2ª.
    TickPotions(db, belt, 38.0);
    EXPECT_EQ(PotionCharges(belt, "potion.life"), 2);
    TickPotions(db, belt, 1.0);
    EXPECT_EQ(PotionCharges(belt, "potion.life"), 3);
}

TEST(potions_recharge_is_serial_not_parallel) {
    const ContentDB& db = tu::RichDb();
    PotionBelt belt = MakeFullPotionBelt(db);
    PotionOutcome out;
    // Esvazia a Vida (3 usos, respeitando a trava).
    for (int i = 0; i < 3; ++i) {
        ASSERT_TRUE(UsePotion(db, belt, "potion.life", 100.0, 1.0, &out) == PotionUseStatus::Ok);
        TickPotions(db, belt, 1.0);
    }
    EXPECT_EQ(PotionCharges(belt, "potion.life"), 0);
    // O relógio começou no 1º uso (3 s atrás): faltam 37 s. Série: 40 s por carga, uma de cada vez.
    TickPotions(db, belt, 36.9);
    EXPECT_EQ(PotionCharges(belt, "potion.life"), 0);
    TickPotions(db, belt, 0.2);
    EXPECT_EQ(PotionCharges(belt, "potion.life"), 1);
    TickPotions(db, belt, 39.0);
    EXPECT_EQ(PotionCharges(belt, "potion.life"), 1);
    TickPotions(db, belt, 1.0);
    EXPECT_EQ(PotionCharges(belt, "potion.life"), 2);
    TickPotions(db, belt, 40.0);
    EXPECT_EQ(PotionCharges(belt, "potion.life"), 3);
    TickPotions(db, belt, 1000.0);
    EXPECT_EQ(PotionCharges(belt, "potion.life"), 3);  // nunca passa do máximo
    // O Resguardo (2 cargas, 60 s) também voltou a cheio e o relógio parou.
    EXPECT_EQ(PotionCharges(belt, "potion.ward"), 2);
}

TEST(potions_elite_kill_adds_charge_to_the_least_charged_ties_go_to_life) {
    const std::unique_ptr<ContentDB> dbp = NoRechargeDb();
    const ContentDB& db = *dbp;
    PotionBelt belt = MakeFullPotionBelt(db);
    PotionOutcome out;
    EXPECT_FALSE(AddChargeOnEliteKill(db, belt));      // tudo cheio: nada entra
    ASSERT_TRUE(UsePotion(db, belt, "potion.life", 100.0, 1.0, &out) == PotionUseStatus::Ok);   // Vida 2/3
    TickPotions(db, belt, 1.0);
    ASSERT_TRUE(UsePotion(db, belt, "potion.ward", 100.0, 1.0, &out) == PotionUseStatus::Ok);   // Resguardo 1/2
    TickPotions(db, belt, 1.0);
    // Vida 2, Resguardo 1: o Resguardo tem MENOS cargas.
    EXPECT_TRUE(AddChargeOnEliteKill(db, belt));
    EXPECT_EQ(PotionCharges(belt, "potion.ward"), 2);
    EXPECT_EQ(PotionCharges(belt, "potion.life"), 2);
    // Vida 2, Resguardo 2 (empate em cargas absolutas): a Vida (1ª do CSV) recebe.
    EXPECT_TRUE(AddChargeOnEliteKill(db, belt));
    EXPECT_EQ(PotionCharges(belt, "potion.life"), 3);
    EXPECT_FALSE(AddChargeOnEliteKill(db, belt));
}

TEST(potions_refill_normalize_and_save_slots) {
    const ContentDB& db = tu::RichDb();
    // Estado salvo parcial e com lixo: ID desconhecido sai, excesso é cortado, poção ausente entra cheia.
    std::vector<PotionSlotState> saved = {{"potion.life", 99, 0.0}, {"potion.gone", 5, 0.0}};
    PotionBelt belt = MakePotionBelt(db, saved);
    ASSERT_TRUE(belt.slots.size() == 2);
    EXPECT_EQ(belt.slots[0].potionId, std::string("potion.life"));
    EXPECT_EQ(belt.slots[0].charges, 3);
    EXPECT_EQ(belt.slots[1].potionId, std::string("potion.ward"));
    EXPECT_EQ(belt.slots[1].charges, 2);
    // Faltando carga sem relógio salvo (v1 migrado): a recarga começa.
    belt = MakePotionBelt(db, {{"potion.life", 1, 0.0}});
    EXPECT_EQ(belt.slots[0].charges, 1);
    EXPECT_NEAR(belt.slots[0].rechargeRemaining, 40.0, 1e-12);
    // Chegar ao Refúgio / checkpoint: cheio e sem trava.
    belt.lockoutRemaining = 0.7;
    RefillPotions(db, belt);
    EXPECT_EQ(belt.slots[0].charges, 3);
    EXPECT_NEAR(belt.slots[0].rechargeRemaining, 0.0, 0.0);
    EXPECT_NEAR(belt.lockoutRemaining, 0.0, 0.0);
    // Ida e volta no save (potion_slots).
    CharacterState c = tu::MakeWarrior(db, 1, 2);
    c.potionSlots = {{"potion.life", 2, 12.5}, {"potion.ward", 1, 30.0}};
    c.bossProgress = {{"enemy.crypt_guardian", 7, 3}};
    CharacterState back;
    ASSERT_TRUE(CharacterFromJson(CharacterToJson(c), back));
    ASSERT_TRUE(back.potionSlots.size() == 2);
    EXPECT_EQ(back.potionSlots[0].charges, 2);
    EXPECT_NEAR(back.potionSlots[0].rechargeRemaining, 12.5, 0.0);
    EXPECT_EQ(back.potionSlots[1].potionId, std::string("potion.ward"));
    ASSERT_TRUE(back.bossProgress.size() == 1);
    EXPECT_EQ(back.bossProgress[0].kills, 7);
    EXPECT_EQ(back.bossProgress[0].killsSinceUnique, 3);
}

TEST(potions_resolve_heal_and_ward_follow_potion_effect_attribute) {
    const ContentDB& db = tu::RichDb();
    const PotionData* life = db.FindPotion("potion.life");
    const PotionData* ward = db.FindPotion("potion.ward");
    ASSERT_TRUE(life != nullptr && ward != nullptr);
    PotionOutcome h = ResolvePotion(*life, 300.0, 1.5);
    EXPECT_NEAR(h.healAmount, 180.0, 1e-9);            // 0,4 × 300 × 1,5
    PotionOutcome w = ResolvePotion(*ward, 300.0, 1.0);
    EXPECT_NEAR(w.barrierAmount, 90.0, 1e-9);
    EXPECT_NEAR(w.barrierSeconds, 6.0, 0.0);
    EXPECT_EQ(DefaultHealPotion(db)->id, std::string("potion.life"));
}

// ---------------------------------------------------------------------------------------------
// Esquiva
// ---------------------------------------------------------------------------------------------
TEST(dodge_three_charges_serial_recharge_and_iframe_window) {
    const RulesConstants& r = tu::RichDb().Rules();
    EXPECT_EQ(r.dodgeMaxCharges, 3);
    DodgeState d;
    NormalizeDodge(r, d);
    EXPECT_EQ(d.charges, 3);
    EXPECT_ENUM_EQ(TryStartDodge(r, d, 0.0), DodgeStartStatus::Ok);
    EXPECT_EQ(d.charges, 2);
    EXPECT_ENUM_EQ(TryStartDodge(r, d, 0.0), DodgeStartStatus::Active);   // já esquivando
    // i-frames: [0, 0,2) — 0,0 e 0,1 sim; 0,2 e 0,3 não (RF-15).
    EXPECT_TRUE(DodgeInvulnerable(r, d));
    TickDodge(r, d, 0.1);
    EXPECT_TRUE(DodgeInvulnerable(r, d));
    TickDodge(r, d, 0.1);                                                  // 0,2 exatos: já saiu da janela
    EXPECT_FALSE(DodgeInvulnerable(r, d));
    TickDodge(r, d, 0.1);                                                  // 0,3: ainda esquivando, sem i-frames
    EXPECT_TRUE(d.active);
    EXPECT_FALSE(DodgeInvulnerable(r, d));
    TickDodge(r, d, 0.06);                                                 // 0,36 > 0,35: acabou
    EXPECT_FALSE(d.active);

    // Esquiva perfeita: o recurso só vale com golpe DENTRO dos i-frames.
    DodgeState p;
    NormalizeDodge(r, p);
    ASSERT_TRUE(TryStartDodge(r, p, 0.0) == DodgeStartStatus::Ok);
    EXPECT_NEAR(DodgePerfectReward(r, p), 10.0, 0.0);
    TickDodge(r, p, 0.25);
    EXPECT_NEAR(DodgePerfectReward(r, p), 0.0, 0.0);

    // 3 esquivas seguidas gastam tudo; a 4ª falha; recarga em série de 1,5 s por carga (4,5 s para encher).
    DodgeState s;
    NormalizeDodge(r, s);
    for (int i = 0; i < 3; ++i) {
        ASSERT_TRUE(TryStartDodge(r, s, 0.0) == DodgeStartStatus::Ok);
        TickDodge(r, s, 0.4);
    }
    EXPECT_EQ(s.charges, 0);
    EXPECT_ENUM_EQ(TryStartDodge(r, s, 0.0), DodgeStartStatus::NoCharges);
    // O relógio começou na 1ª esquiva (1,2 s atrás): falta 0,3 s para a 1ª carga.
    TickDodge(r, s, 0.29);
    EXPECT_EQ(s.charges, 0);
    TickDodge(r, s, 0.02);
    EXPECT_EQ(s.charges, 1);
    TickDodge(r, s, 1.48);
    EXPECT_EQ(s.charges, 1);
    TickDodge(r, s, 0.02);
    EXPECT_EQ(s.charges, 2);                       // 1,5 s depois da anterior
    TickDodge(r, s, 1.48);
    EXPECT_EQ(s.charges, 2);
    TickDodge(r, s, 0.02);
    EXPECT_EQ(s.charges, 3);
}

TEST(dodge_costs_resource_and_ai_dodge_spends_a_charge_without_window) {
    RulesConstants r = tu::RichDb().Rules();
    r.dodgeCostResource = 5.0;
    DodgeState d;
    NormalizeDodge(r, d);
    EXPECT_ENUM_EQ(TryStartDodge(r, d, 4.9), DodgeStartStatus::NotEnoughResource);
    EXPECT_EQ(d.charges, 3);                        // recusa não gasta carga
    EXPECT_ENUM_EQ(TryStartDodge(r, d, 5.0), DodgeStartStatus::Ok);
    // IA do idle: gasta carga, sem janela de invulnerabilidade.
    DodgeState ai;
    NormalizeDodge(r, ai);
    EXPECT_TRUE(DodgeSpendCharge(r, ai));
    EXPECT_TRUE(DodgeSpendCharge(r, ai));
    EXPECT_TRUE(DodgeSpendCharge(r, ai));
    EXPECT_FALSE(DodgeSpendCharge(r, ai));          // sem carga: o golpe acerta
    EXPECT_FALSE(ai.active);
}

TEST(dodge_idle_ai_never_dodges_more_than_the_charges_allow) {
    // Dano alto e telegrafado: a IA esquiva 50%, mas só enquanto houver carga (3 + 1 a cada 1,5 s).
    const ContentDB& db = tu::RichDb();
    ExpeditionRequest req = tu::MakeRequest(db, 1, 4242);
    const ExpeditionResult r = SimulateExpedition(db, req);
    int dodges = 0;
    for (const EncounterReceipt& rc : r.receipts) dodges += rc.dodgesUsed;
    EXPECT_TRUE(dodges > 0);
    const double cap = static_cast<double>(db.Rules().dodgeMaxCharges) + r.effectiveSeconds / db.Rules().dodgeRecharge;
    EXPECT_TRUE(static_cast<double>(dodges) <= cap + 1.0);
    // Com 1 carga que leva 60 s para voltar, esquiva bem menos (e leva mais dano).
    const std::unique_ptr<ContentDB> slow = MakeDb({{"rules.csv",
        tu::Replace(tu::Replace(tu::ReadFile(tu::RichDir() + "/rules.csv"), "dodge_max_charges,3", "dodge_max_charges,1"),
                    "dodge_recharge,1.5", "dodge_recharge,60")}});
    ASSERT_TRUE(slow->Errors().empty());
    const ExpeditionResult rs = SimulateExpedition(*slow, tu::MakeRequest(*slow, 1, 4242));
    int dodgesSlow = 0;
    for (const EncounterReceipt& rc : rs.receipts) dodgesSlow += rc.dodgesUsed;
    EXPECT_TRUE(static_cast<double>(dodgesSlow) <= 1.0 + rs.effectiveSeconds / 60.0 + 1.0);
    EXPECT_TRUE(dodgesSlow < dodges);
    double takenFast = 0.0, takenSlow = 0.0;
    for (const EncounterReceipt& rc : r.receipts) takenFast += rc.damageTaken / static_cast<double>(r.receipts.size());
    for (const EncounterReceipt& rc : rs.receipts) takenSlow += rc.damageTaken / static_cast<double>(rs.receipts.size());
    EXPECT_TRUE(takenSlow > takenFast);
}

// ---------------------------------------------------------------------------------------------
// Vitals e tempos de ação (IRulesCore)
// ---------------------------------------------------------------------------------------------
TEST(vitals_regen_decay_barrier_expiry_and_resource_spend) {
    const ContentDB& db = tu::RichDb();
    StatBlock sb;
    ASSERT_TRUE(BuildStatBlock(db, tu::MakeWarrior(db, 3), sb));
    const ClassData* cls = db.FindClass("class.warrior");
    ASSERT_TRUE(cls != nullptr);
    Vitals v = CreateVitals(sb, cls);
    EXPECT_NEAR(v.life, sb.Get(StatId::Life), 0.0);
    const bool decays = cls->resourceDecayOutOfCombat > 0.0;
    EXPECT_NEAR(v.resource, decays ? 0.0 : sb.Get(StatId::Resource), 0.0);
    v.life = sb.Get(StatId::Life) - 10.0;
    TickVitals(v, sb, cls, 1.0, true);
    EXPECT_NEAR(v.life, sb.Get(StatId::Life) - 10.0 + sb.Get(StatId::LifeRegen), 1e-9);
    // Recurso: ganha até o teto, gasta só se couber.
    GainResource(v, sb, 1e9);
    EXPECT_NEAR(v.resource, sb.Get(StatId::Resource), 0.0);
    EXPECT_FALSE(TrySpendResource(v, sb.Get(StatId::Resource) + 1.0));
    EXPECT_NEAR(v.resource, sb.Get(StatId::Resource), 0.0);
    EXPECT_TRUE(TrySpendResource(v, 30.0));
    EXPECT_NEAR(v.resource, sb.Get(StatId::Resource) - 30.0, 1e-9);
    if (decays) {
        const double before = v.resource;
        TickVitals(v, sb, cls, 1.0, false);
        EXPECT_NEAR(v.resource, before - cls->resourceDecayOutOfCombat + sb.Get(StatId::ResourceRegen), 1e-9);
    }
    // Barreira de poção some no fim do tempo.
    v.barrier = 50.0;
    v.barrierSecondsLeft = 2.0;
    TickVitals(v, sb, cls, 1.0, true);
    EXPECT_NEAR(v.barrier, 50.0, 0.0);
    TickVitals(v, sb, cls, 1.0, true);
    EXPECT_NEAR(v.barrier, 0.0, 0.0);
    EXPECT_NEAR(v.barrierSecondsLeft, 0.0, 0.0);
    // Morto não regenera.
    v.life = 0.0;
    TickVitals(v, sb, cls, 1.0, true);
    EXPECT_NEAR(v.life, 0.0, 0.0);
}

TEST(action_timing_applies_speed_cooldown_cost_and_elite_telegraph_rule) {
    const ContentDB& db = tu::RichDb();
    StatBlock sb;
    ASSERT_TRUE(BuildStatBlock(db, tu::MakeWarrior(db, 1), sb));
    const SkillData* cleave = db.FindSkill("skill.warrior.cleave");
    ASSERT_TRUE(cleave != nullptr);
    ActionTimingInfo t = ComputeActionTiming(db, *cleave, sb);
    EXPECT_NEAR(t.windup, cleave->windup / sb.Get(StatId::AttackSpeed), 1e-12);
    EXPECT_NEAR(t.recovery, cleave->recovery / sb.Get(StatId::AttackSpeed), 1e-12);
    EXPECT_NEAR(t.cost, 20.0, 0.0);
    EXPECT_NEAR(t.cooldown, 3.0, 1e-12);
    // Atributos de velocidade: +100% de velocidade de ataque dobra a rapidez (mod "more").
    Modifier m;
    m.stat = StatId::AttackSpeed;
    m.kind = ModKind::More;
    m.value = 1.0;
    m.source = "teste";
    sb.AddModifier(m);
    const ActionTimingInfo fast = ComputeActionTiming(db, *cleave, sb);
    EXPECT_NEAR(fast.windup, t.windup / 2.0, 1e-12);
    // Elite Veloz: o telegraph (windup) NÃO encurta; recuperação ×0,8 e velocidade ×1,25 só no impacto e na recuperação.
    const EliteModifierData* swift = db.FindEliteModifier("modifier.elite.swift");
    ASSERT_TRUE(swift != nullptr);
    const EliteProfile prof = MakeEliteProfile(db, swift, false);
    StatBlock en;
    BuildEnemyStatBlock(*db.FindEnemy("enemy.hollow_sentinel"), 3, en);
    const SkillData* strike = db.FindSkill("skill.enemy.sentinel_strike");
    const ActionTimingInfo base = ComputeActionTiming(db, *strike, en);
    ApplyEliteToStats(prof, en);
    const ActionTimingInfo el = ComputeActionTiming(db, *strike, en, &prof);
    EXPECT_NEAR(el.windup, base.windup, 1e-12);
    EXPECT_NEAR(el.impact, base.impact / 1.25, 1e-12);
    EXPECT_NEAR(el.recovery, base.recovery * 0.8 / 1.25, 1e-12);
    // Velocidade de movimento e CanAct/CanMove.
    EXPECT_NEAR(MoveSpeedUu(en, 380.0), 380.0 * 1.3, 1e-9);
    EXPECT_TRUE(CanAct(en) && CanMove(en));
    Modifier stun;
    stun.stat = StatId::AttackSpeed;
    stun.kind = ModKind::More;
    stun.value = -1.0;
    stun.source = "teste";
    en.AddModifier(stun);
    EXPECT_FALSE(CanAct(en));
    EXPECT_TRUE(CanMove(en));
}

TEST(pick_enemy_attack_is_weighted_deterministic_and_consumes_one_number) {
    const ContentDB& db = tu::RichDb();
    const EnemyData* boss = db.FindEnemy("enemy.crypt_guardian");
    ASSERT_TRUE(boss != nullptr && boss->attacks.size() >= 2);
    int counts[8] = {0};
    Pcg32 a(77), b(77);
    for (int i = 0; i < 20000; ++i) {
        const int pick = PickEnemyAttack(*boss, a);
        ASSERT_TRUE(pick >= 0 && pick < 8);
        ++counts[pick];
    }
    double total = 0.0;
    for (const EnemyAttack& at : boss->attacks) total += at.weight;
    for (std::size_t k = 0; k < boss->attacks.size(); ++k)
        EXPECT_NEAR(static_cast<double>(counts[k]) / 20000.0, boss->attacks[k].weight / total, 0.02);
    for (int i = 0; i < 20000; ++i) PickEnemyAttack(*boss, b);
    EXPECT_EQ(a.NextU32(), b.NextU32());            // mesma posição do fluxo (1 número por escolha)
    EnemyData none;
    Pcg32 c(1), d(1);
    EXPECT_EQ(PickEnemyAttack(none, c), -1);
    d.NextU32();
    EXPECT_EQ(c.NextU32(), d.NextU32());            // mesmo sem ataques consome 1 número
}

// ---------------------------------------------------------------------------------------------
// Poções no simulador idle
// ---------------------------------------------------------------------------------------------
TEST(idle_ward_potion_rule_and_elite_kill_refill_work_and_are_deterministic) {
    // Só o encontro do elite fixo (Escudo); poções sem recarga por tempo; Vida e Resguardo zerados no início.
    const std::unique_ptr<ContentDB> dbp = MakeDb({
        {"potions.csv",
         "id,kind,fractionOfMaxLife,duration,maxCharges,rechargeSeconds,useTime,moveSpeedWhileUsing,globalLockout,"
         "refillOnEliteKill,hotkeySlot\n"
         "potion.life,heal,0.4,,3,1000000,0.4,0.5,1.0,true,1\n"
         "potion.ward,barrier,0.3,6,2,1000000,0.4,0.5,1.0,true,2\n"},
        {"maps.csv", "id,monsterLevel,tier,encounters,bossEncounter,areaLootTable,idleAllowed\n"
                     "map.act1.crypt,4,0,enc.crypt.elite_shield,enc.crypt.guardian,loot.crypt.area,true\n"},
    });
    const ContentDB& db = *dbp;
    ExpeditionRequest req = tu::MakeRequest(db, 1, 99, 1, 0);
    req.snapshot.character.potionSlots = {{"potion.life", 0, 0.0}, {"potion.ward", 2, 0.0}};
    AiRule ward;
    ward.condition = AiCondition::TargetIsElite;
    ward.action = AiAction::UsePotion;
    ward.refId = "potion.ward";
    AiRule basic;
    basic.condition = AiCondition::Always;
    basic.action = AiAction::UseSkill;
    basic.refId = "skill.warrior.iron_cut";
    req.rules = {ward, basic};
    req.effectiveSeconds = 600.0;
    const ExpeditionProgress p = SimulateRange(db, req, ExpeditionProgress(), 0, 3);
    ASSERT_TRUE(p.receipts.size() == 3);
    EXPECT_TRUE(p.receipts[0].potionsUsed >= 1);                 // o Resguardo foi bebido contra o elite
    EXPECT_EQ(p.receipts[0].elitesKilled, 1);
    ASSERT_TRUE(p.potionSlots.size() == 2);
    // Cada elite morto devolve 1 carga na poção com menos cargas (a Vida, que começou em 0).
    EXPECT_TRUE(p.potionSlots[0].charges >= 1);
    // Mesma coisa em fatias de 1: o estado atravessa encontros (potionSlots no progresso).
    ExpeditionProgress q;
    for (int i = 0; i < 3; ++i) q = SimulateRange(db, req, q, q.nextEncounter, 1);
    ASSERT_TRUE(q.potionSlots.size() == 2);
    EXPECT_EQ(q.potionSlots[0].charges, p.potionSlots[0].charges);
    EXPECT_EQ(q.potionSlots[1].charges, p.potionSlots[1].charges);
    const ExpeditionResult a = FinalizeExpedition(db, req, p), b = FinalizeExpedition(db, req, q);
    EXPECT_EQ(a.resultHash, b.resultHash);
}

TEST(idle_retreat_happens_below_25_percent_only_without_heal_charges) {
    EXPECT_NEAR(tu::RichDb().Rules().retreatLifeFraction, 0.25, 0.0);
    // Dano pesado e Vida zerada (sem recarga): recua. Com cargas de Vida, não recua com a vida baixa.
    std::string skills = tu::ReadFile(tu::RichDir() + "/skills.csv");
    skills = tu::Replace(skills, "skill.enemy.sentinel_strike,,,attack|melee|physical,melee,,8,", "skill.enemy.sentinel_strike,,,attack|melee|physical,melee,,30,");
    const std::unique_ptr<ContentDB> dbp = MakeDb({{"skills.csv", skills},
        {"potions.csv", "id,kind,fractionOfMaxLife,duration,maxCharges,rechargeSeconds,useTime,moveSpeedWhileUsing,globalLockout,"
                        "refillOnEliteKill,hotkeySlot\n"
                        "potion.life,heal,0.4,,3,1000000,0.4,0.5,1.0,false,1\n"
                        "potion.ward,barrier,0.3,6,2,1000000,0.4,0.5,1.0,false,2\n"}});
    int retreatsWithout = 0, retreatsWith = 0;
    for (std::uint64_t seed = 1; seed <= 8; ++seed) {
        ExpeditionRequest none = tu::MakeRequest(*dbp, 4, seed, 1, 0);
        ExpeditionRequest some = tu::MakeRequest(*dbp, 4, seed, 1, 3);
        const ExpeditionResult a = SimulateExpedition(*dbp, none), b = SimulateExpedition(*dbp, some);
        retreatsWithout += a.stop == StopReason::Retreat ? 1 : 0;
        retreatsWith += b.stop == StopReason::Retreat ? 1 : 0;
        if (a.stop == StopReason::Retreat) {
            const EncounterReceipt& last = a.receipts.back();
            EXPECT_TRUE(last.lifeFractionAtEnd < 0.25 + 1e-9);   // limiar de 25%, não 20%
        }
    }
    EXPECT_EQ(retreatsWithout, 8);
    EXPECT_TRUE(retreatsWith <= retreatsWithout);
}
