// Revisão do core da Etapa 2 (docs/tecnico/17_revisao_core_etapa2.md): reproduções de achados nas regras de combate.
//
// Cada teste afirma o comportamento CORRETO do achado do docs/17 (todos corrigidos e LIGADOS; sem variável de ambiente).
#include <memory>

#include "test_util.h"

using namespace shatter;

namespace {

using Overrides = std::vector<std::pair<std::string, std::string>>;


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

}  // namespace

// ---------------------------------------------------------------------------------------------
// B1 — +1 carga ao matar elite some quando a poção com MENOS cargas absolutas já está cheia, mesmo com outra poção
// refillOnEliteKill abaixo do máximo (combat.cpp:230-245). shatter_c.h promete "*added = 0 se todas estavam cheias".
// ---------------------------------------------------------------------------------------------
TEST(revisao_B1_carga_de_elite_perdida_com_pocao_minima_cheia) {
    // Resguardo com 1 carga máxima (dado plausível); Vida com 3. Recarga longa para isolar a regra.
    const std::unique_ptr<ContentDB> dbp = RichWith({{"potions.csv",
        "id,kind,fractionOfMaxLife,duration,maxCharges,rechargeSeconds,useTime,moveSpeedWhileUsing,globalLockout,"
        "refillOnEliteKill,hotkeySlot\n"
        "potion.life,heal,0.4,,3,1000000,0.4,0.5,1.0,true,1\n"
        "potion.ward,barrier,0.3,6,1,1000000,0.4,0.5,1.0,true,2\n"}});
    const ContentDB& db = *dbp;
    ASSERT_TRUE(db.Errors().empty());
    PotionBelt belt = MakeFullPotionBelt(db);
    PotionOutcome out;
    ASSERT_TRUE(UsePotion(db, belt, "potion.life", 100.0, 1.0, &out) == PotionUseStatus::Ok);  // Vida 2/3
    TickPotions(db, belt, 2.0);
    EXPECT_EQ(PotionCharges(belt, "potion.ward"), 1);  // Resguardo 1/1 (cheio, mas é o de MENOS cargas)
    // Correto: a Vida não está cheia, então a carga do elite entra nela.
    EXPECT_TRUE(AddChargeOnEliteKill(db, belt));
    EXPECT_EQ(PotionCharges(belt, "potion.life"), 3);
}

// ---------------------------------------------------------------------------------------------
// B2 — no simulador, o DoT causado pelo herói ignora a barreira do elite (expedition.cpp:620-633: o HitInput do tick
// não recebe defenderBarrier), enquanto o golpe direto respeita (expedition.cpp:448-451; docs/04 §11, passo 9).
// ---------------------------------------------------------------------------------------------
TEST(revisao_B2_dot_do_idle_ignora_a_barreira_do_elite) {
    const std::string table = tu::ReadFile(tu::RichDir() + "/skills.csv");
    // Corte de Ferro sem dano direto e com veneno ao acertar: todo o dano que o elite recebe vem do DoT.
    const std::string skills = tu::Replace(table, "attack|melee|physical,melee,,10,,,,1,1.1,1.2,0,0,0.2,0.1,0.2,60,,1,,,",
                                           "attack|melee|physical,melee,,0,,,,1,1.1,1.2,0,0,0.2,0.1,0.2,60,,1,effect.poison_stack,,");
    const std::string maps = "id,monsterLevel,tier,encounters,bossEncounter,areaLootTable,idleAllowed\n"
                             "map.act1.crypt,4,0,enc.crypt.elite_shield,enc.crypt.guardian,loot.crypt.area,true\n";
    const std::string mods = tu::ReadFile(tu::RichDir() + "/elite_modifiers.csv");
    const std::unique_ptr<ContentDB> withBarrier = RichWith({{"skills.csv", skills}, {"maps.csv", maps}});
    const std::unique_ptr<ContentDB> noBarrier = RichWith(
        {{"skills.csv", skills}, {"maps.csv", maps}, {"elite_modifiers.csv", tu::Replace(mods, "50,,,,0.4,", "50,,,,0,")}});
    ASSERT_TRUE(withBarrier->Errors().empty());
    ASSERT_TRUE(noBarrier->Errors().empty());
    auto firstEncounter = [](const ContentDB& db) {
        const ExpeditionRequest req = tu::MakeRequest(db, 1, 7, 20, 3);
        return SimulateRange(db, req, ExpeditionProgress(), 0, 1).receipts.at(0);
    };
    const EncounterReceipt a = firstEncounter(*withBarrier);
    const EncounterReceipt b = firstEncounter(*noBarrier);
    ASSERT_TRUE(a.kills == 1 && b.kills == 1);
    // Correto: a barreira de 40% da vida absorve parte do veneno, então o elite com Escudo demora mais para morrer.
    if (!(a.duration > b.duration + 1e-9))
        FAIL("com barreira " + std::to_string(a.duration) + " s, sem barreira " + std::to_string(b.duration) + " s");
}

// ---------------------------------------------------------------------------------------------
// M5 — a barreira da poção é a MESMA no manual (Vitals) e no idle: reaplicar renova só a parte da poção e a de outra
// fonte fica; ao fim do tempo sai só a parte da poção. Os dois caminhos usam ApplyPotionBarrier/TickPotionBarrier.
// ---------------------------------------------------------------------------------------------
TEST(revisao_M5_barreira_da_pocao_igual_no_manual_e_no_idle) {
    // "Idle": variáveis soltas (como o simulador).
    double barrier = 40.0;                 // 40 de outra fonte (elite/habilidade)
    double potionAmount = 0.0, remaining = 0.0;
    ApplyPotionBarrier(barrier, potionAmount, remaining, 30.0, 5.0);
    ApplyPotionBarrier(barrier, potionAmount, remaining, 30.0, 5.0);  // reaplicar renova, não acumula
    EXPECT_NEAR(barrier, 70.0, 1e-9);

    // "Manual": Vitals com a mesma situação.
    Vitals v{};
    v.life = 500.0;
    v.barrier = 40.0;
    PotionOutcome po;
    po.barrierAmount = 30.0;
    po.barrierSeconds = 5.0;
    ApplyPotionOutcome(v, po, 1000.0);
    ApplyPotionOutcome(v, po, 1000.0);
    EXPECT_NEAR(v.barrier, barrier, 1e-9);

    // Passa o tempo: sai só a parte da poção nos dois caminhos.
    TickPotionBarrier(barrier, potionAmount, remaining, 6.0);
    StatBlock stats;
    TickVitals(v, stats, nullptr, 6.0, false);
    EXPECT_NEAR(barrier, 40.0, 1e-9);
    EXPECT_NEAR(v.barrier, barrier, 1e-9);
}
