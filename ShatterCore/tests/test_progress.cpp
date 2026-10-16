// Progresso manual e início de expedição — RF-35 (cargas), RF-50 (domínio), RF-31/RF-37/RF-38 pelo save,
// e RF-48 (motivo "relógio voltou" no resultado).
#include "test_util.h"

using namespace shatter;

namespace {

constexpr UnixSeconds kStart = 1'700'000'000;

// Save com um Guerreiro que ainda NÃO dominou a Cripta.
SaveData FreshSave(int charges) {
    const ContentDB& db = tu::RichDb();
    SaveData s;
    s.contentVersion = db.ContentVersion();
    CharacterState c = tu::MakeWarrior(db, 3);
    c.conqueredMaps.clear();
    s.characters.push_back(c);
    s.markerCharges = charges;
    return s;
}

ExpeditionStartParams Params(int hours, std::uint64_t seed = 99) {
    ExpeditionStartParams p;
    p.characterIndex = 0;
    p.mapId = "map.act1.crypt";
    p.rules = tu::DefaultRules();
    p.durationHours = hours;
    p.seed = seed;
    p.startUtc = kStart;
    return p;
}

AreaRunOutcome Run(bool end, bool boss) {
    AreaRunOutcome r;
    r.reachedEnd = end;
    r.bossDefeated = boss;
    return r;
}

}  // namespace

TEST(progress_rf35_charges_never_exceed_twelve) {
    const ContentDB& db = tu::RichDb();
    // Começar com 12 cargas e ganhar +1 (limpar a área na mão) resulta em 12.
    SaveData s = FreshSave(12);
    s.characters[0].conqueredMaps = {"map.act1.crypt"};
    AreaRunReward rw;
    ASSERT_TRUE(RecordAreaRun(db, s, 0, "map.act1.crypt", Run(true, false), &rw));
    EXPECT_EQ(s.markerCharges, 12);
    EXPECT_EQ(rw.chargesGained, 0);
    // Com 5 cargas: +1 por limpar, +2 por vencer o chefe (o maior dos dois, não a soma).
    s.markerCharges = 5;
    ASSERT_TRUE(RecordAreaRun(db, s, 0, "map.act1.crypt", Run(true, false), &rw));
    EXPECT_EQ(s.markerCharges, 6);
    EXPECT_EQ(rw.chargesGained, 1);
    ASSERT_TRUE(RecordAreaRun(db, s, 0, "map.act1.crypt", Run(true, true), &rw));
    EXPECT_EQ(s.markerCharges, 8);
    EXPECT_EQ(rw.chargesGained, 2);
    EXPECT_FALSE(rw.newConquest);  // já dominada: sem o bônus de área nova
    // Corrida sem chegar ao fim nem vencer o chefe não dá nada.
    ASSERT_TRUE(RecordAreaRun(db, s, 0, "map.act1.crypt", Run(false, false), &rw));
    EXPECT_EQ(s.markerCharges, 8);
    // Um save que por algum motivo já passou do teto nunca perde cargas ao ganhar mais.
    s.markerCharges = 14;
    ASSERT_TRUE(RecordAreaRun(db, s, 0, "map.act1.crypt", Run(true, false), &rw));
    EXPECT_EQ(s.markerCharges, 14);
    // Personagem ou mapa inexistentes: recusado sem alterar nada.
    const int before = s.markerCharges;
    EXPECT_FALSE(RecordAreaRun(db, s, 3, "map.act1.crypt", Run(true, true), &rw));
    EXPECT_FALSE(RecordAreaRun(db, s, 0, "map.nowhere", Run(true, true), &rw));
    EXPECT_EQ(s.markerCharges, before);
}

TEST(progress_rf50_conquest_requires_end_and_boss_and_grants_five) {
    const ContentDB& db = tu::RichDb();
    SaveData s = FreshSave(0);
    std::vector<ContentId> blocking;
    // RF-31: sem domínio, a expedição é recusada ("área não dominada").
    EXPECT_ENUM_EQ(StartExpedition(db, s, Params(1), &blocking), StartCheck::MapNotConquered);
    // Limpar a área sem vencer o Guardião: +1 carga, mas continua sem domínio e continua recusando.
    AreaRunReward rw;
    ASSERT_TRUE(RecordAreaRun(db, s, 0, "map.act1.crypt", Run(true, false), &rw));
    EXPECT_FALSE(rw.newConquest);
    EXPECT_EQ(s.markerCharges, 1);
    EXPECT_TRUE(s.characters[0].conqueredMaps.empty());
    EXPECT_ENUM_EQ(StartExpedition(db, s, Params(1), &blocking), StartCheck::MapNotConquered);
    // Vencer o Guardião sem ter percorrido a área nesta corrida: +2 (chefe), sem domínio.
    ASSERT_TRUE(RecordAreaRun(db, s, 0, "map.act1.crypt", Run(false, true), &rw));
    EXPECT_FALSE(rw.newConquest);
    EXPECT_EQ(s.markerCharges, 3);
    // Percorrer até o fim e vencer o Guardião na mesma corrida: domínio + 5 cargas (+2 chefe, +3 área nova).
    ASSERT_TRUE(RecordAreaRun(db, s, 0, "map.act1.crypt", Run(true, true), &rw));
    EXPECT_TRUE(rw.newConquest);
    EXPECT_EQ(rw.chargesGained, 5);
    EXPECT_EQ(s.markerCharges, 8);
    ASSERT_EQ(s.characters[0].conqueredMaps.size(), static_cast<std::size_t>(1));
    EXPECT_EQ(s.characters[0].conqueredMaps[0], std::string("map.act1.crypt"));
    // ...e a opção na Ilsa fica liberada.
    EXPECT_ENUM_EQ(CanStartExpedition(db, s.characters[0], "map.act1.crypt", 1, s.markerCharges, false, 3, &blocking),
                   StartCheck::Ok);
    // O +5 respeita o teto de 12.
    SaveData full = FreshSave(10);
    ASSERT_TRUE(RecordAreaRun(db, full, 0, "map.act1.crypt", Run(true, true), &rw));
    EXPECT_EQ(full.markerCharges, 12);
    EXPECT_EQ(rw.chargesGained, 2);
    EXPECT_TRUE(rw.newConquest);
    // Endgame sem chefe: chegar ao fim conquista e atualiza o maior tier vencido.
    SaveData eg = FreshSave(0);
    ASSERT_TRUE(RecordAreaRun(db, eg, 0, "map.endgame.ossuary_deep", Run(true, false), &rw));
    EXPECT_TRUE(rw.newConquest);
    EXPECT_EQ(eg.characters[0].highestTierCleared, 2);
    EXPECT_EQ(eg.markerCharges, 1 + 3);
}

TEST(progress_start_expedition_freezes_snapshot_and_spends_charges) {
    const ContentDB& db = tu::RichDb();
    SaveData s = FreshSave(12);
    s.characters[0].conqueredMaps = {"map.act1.crypt"};
    // RF-35: 5 h com 3 cargas é recusada; nada muda no save.
    s.markerCharges = 3;
    EXPECT_ENUM_EQ(StartExpedition(db, s, Params(5)), StartCheck::NotEnoughCharges);
    EXPECT_TRUE(s.expeditions.empty());
    EXPECT_EQ(s.markerCharges, 3);
    // RF-39: duração fora de 1–12 h e 7 regras são recusadas.
    s.markerCharges = 12;
    EXPECT_ENUM_EQ(StartExpedition(db, s, Params(0)), StartCheck::InvalidDuration);
    EXPECT_ENUM_EQ(StartExpedition(db, s, Params(13)), StartCheck::InvalidDuration);
    ExpeditionStartParams seven = Params(1);
    seven.rules.resize(7);
    EXPECT_ENUM_EQ(StartExpedition(db, s, seven), StartCheck::TooManyRules);
    // RF-43: habilidade sem IdleProfile bloqueia, com o ID para a mensagem localizada.
    SaveData roar = s;
    roar.characters[0].skillBar[3] = "skill.warrior.unsupported_roar";
    std::vector<ContentId> blocking;
    EXPECT_ENUM_EQ(StartExpedition(db, roar, Params(1), &blocking), StartCheck::IdleIncompatible);
    ASSERT_EQ(blocking.size(), static_cast<std::size_t>(1));
    EXPECT_EQ(blocking[0], std::string("skill.warrior.unsupported_roar"));
    EXPECT_TRUE(StartExpedition(db, s, Params(1, 7), &blocking) == StartCheck::Ok);
    EXPECT_TRUE(blocking.empty());
    // Ok: Running, snapshot congelado, content_version gravado, 4 h × 1 carga descontadas.
    SaveData run = FreshSave(12);
    run.characters[0].conqueredMaps = {"map.act1.crypt"};
    ASSERT_TRUE(StartExpedition(db, run, Params(4, 4242)) == StartCheck::Ok);
    EXPECT_EQ(run.markerCharges, 8);
    ASSERT_EQ(run.expeditions.size(), static_cast<std::size_t>(1));
    const SavedExpedition& e = run.expeditions[0];
    EXPECT_ENUM_EQ(e.status, ExpeditionStatus::Running);
    EXPECT_EQ(e.characterIndex, 0);
    EXPECT_EQ(e.request.seed, static_cast<std::uint64_t>(4242));
    EXPECT_EQ(e.request.startUtc, kStart);
    EXPECT_EQ(e.request.durationHours, 4);
    EXPECT_EQ(e.request.contentVersion, db.ContentVersion());
    EXPECT_EQ(e.request.snapshot.contentVersion, db.ContentVersion());
    EXPECT_EQ(e.request.rules.size(), static_cast<std::size_t>(3));
    EXPECT_EQ(e.request.snapshot.character.level, 3);
    // RF-38: trocar o equipamento do personagem vivo depois do início não muda o pedido congelado.
    const std::string frozen = json::Serialize(SaveToJson(run)["expeditions"], false);
    run.characters[0].equipment[static_cast<std::size_t>(ItemSlot::MainHand)].reset();
    run.characters[0].level = 6;
    EXPECT_EQ(json::Serialize(SaveToJson(run)["expeditions"], false), frozen);
    // RF-37: com uma expedição ativa, uma 2ª é recusada (mesmo de outro personagem do save).
    run.characters.push_back(run.characters[0]);
    ExpeditionStartParams other = Params(1);
    other.characterIndex = 1;
    EXPECT_ENUM_EQ(StartExpedition(db, run, other), StartCheck::AnotherExpeditionRunning);
    EXPECT_ENUM_EQ(StartExpedition(db, run, Params(1)), StartCheck::AnotherExpeditionRunning);
    EXPECT_EQ(run.markerCharges, 8);
    // Personagem inexistente.
    ExpeditionStartParams ghost = Params(1);
    ghost.characterIndex = 9;
    EXPECT_ENUM_EQ(StartExpedition(db, run, ghost), StartCheck::UnknownContent);
}

TEST(progress_collected_slot_is_reused_and_cannot_be_collected_again) {
    const ContentDB& db = tu::RichDb();
    SaveData s = FreshSave(12);
    s.characters[0].conqueredMaps = {"map.act1.crypt"};
    ASSERT_TRUE(StartExpedition(db, s, Params(1, 11)) == StartCheck::Ok);
    ExpeditionRequest req = s.expeditions[0].request;
    req.effectiveSeconds = 600;
    const ExpeditionResult r = SimulateExpedition(db, req);
    ASSERT_TRUE(CollectExpedition(db, s, 0, r));
    EXPECT_FALSE(CollectExpedition(db, s, 0, r));
    // A vaga coletada é reaproveitada pela próxima expedição (o AA tem 1 vaga).
    ASSERT_TRUE(StartExpedition(db, s, Params(2, 12)) == StartCheck::Ok);
    ASSERT_EQ(s.expeditions.size(), static_cast<std::size_t>(1));
    EXPECT_ENUM_EQ(s.expeditions[0].status, ExpeditionStatus::Running);
    EXPECT_EQ(s.expeditions[0].collectedResultHash, static_cast<std::uint64_t>(0));
    EXPECT_EQ(s.markerCharges, 12 - 1 - 2);
}

TEST(progress_rf48_clock_rollback_is_the_reported_stop_reason) {
    const ContentDB& db = tu::RichDb();
    const RulesConstants& rules = db.Rules();
    const UnixSeconds lastSeen = kStart + 2 * 3600;  // T
    ExpeditionRequest req = tu::MakeRequest(db, 4, 31);
    req.startUtc = kStart;
    auto resolve = [&](UnixSeconds localNow) {
        ClockInput in;
        in.localNowUtc = localNow;
        in.lastSeenUtc = lastSeen;
        const TrustedNow now = ResolveNow(in, rules);
        const OfflineWindow w = ComputeExpeditionWindow(req.startUtc, req.durationHours, now, lastSeen, rules);
        ExpeditionRequest r = req;
        r.effectiveSeconds = w.effectiveSeconds;
        ExpeditionProgress p = SimulateRange(db, r, ExpeditionProgress(), 0, 0xFFFFFFFFu);
        ApplyWindowStop(p, w);
        return FinalizeExpedition(db, r, p);
    };
    // Agora = T − 6 min: encerra no último ponto conhecido (2 h), motivo "relógio voltou".
    const ExpeditionResult back = resolve(lastSeen - 6 * 60);
    EXPECT_ENUM_EQ(back.stop, StopReason::ClockRollback);
    EXPECT_TRUE(back.effectiveSeconds <= 2 * 3600.0);
    EXPECT_TRUE(back.effectiveSeconds > 2 * 3600.0 - 60.0);
    // Agora = T − 4 min: segue normal (ainda em andamento, sem motivo de relógio).
    const ExpeditionResult fine = resolve(lastSeen - 4 * 60);
    EXPECT_ENUM_EQ(fine.stop, StopReason::DurationReached);
    EXPECT_TRUE(fine.effectiveSeconds <= 2 * 3600.0 - 240.0);
    // O motivo entra no hash (o relatório e a coleta enxergam a diferença).
    ExpeditionRequest same = req;
    same.effectiveSeconds = 2 * 3600.0;
    EXPECT_NE(back.resultHash, SimulateExpedition(db, same).resultHash);
    // Recuo e outras paradas reais não viram ClockRollback.
    ExpeditionProgress retreat;
    retreat.stop = StopReason::Retreat;
    OfflineWindow w;
    w.endedByRollback = true;
    ApplyWindowStop(retreat, w);
    EXPECT_ENUM_EQ(retreat.stop, StopReason::Retreat);
}
