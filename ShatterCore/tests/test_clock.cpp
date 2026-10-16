// Relógio e tempo offline — RF-35 (descanso), RF-46..RF-49, RNF-09.
#include "test_util.h"

using namespace shatter;

namespace {

constexpr UnixSeconds kStart = 1'700'000'000;
constexpr UnixSeconds kHour = 3600;

TrustedNow Now(UnixSeconds local, UnixSeconds lastSeen, bool steam = false, UnixSeconds steamNow = 0) {
    ClockInput in;
    in.localNowUtc = local;
    in.hasSteamTime = steam;
    in.steamNowUtc = steamNow;
    in.lastSeenUtc = lastSeen;
    return ResolveNow(in, RulesConstants());
}

}  // namespace

TEST(clock_rf46_rf47_window_is_capped_by_duration_and_12h) {
    const RulesConstants r;
    // 4 h iniciada há 10 h: simula 4 h.
    TrustedNow n = Now(kStart + 10 * kHour, kStart);
    OfflineWindow w = ComputeExpeditionWindow(kStart, 4, n, kStart, r);
    EXPECT_NEAR(w.effectiveSeconds, 4 * 3600.0, 0.0);
    EXPECT_TRUE(w.finished);
    EXPECT_FALSE(w.endedByRollback);
    // 12 h iniciada há 30 h: simula 12 h (teto offline).
    n = Now(kStart + 30 * kHour, kStart);
    w = ComputeExpeditionWindow(kStart, 12, n, kStart, r);
    EXPECT_NEAR(w.effectiveSeconds, 12 * 3600.0, 0.0);
    // Ainda em andamento: só o que passou.
    n = Now(kStart + 90 * 60, kStart);
    w = ComputeExpeditionWindow(kStart, 4, n, kStart, r);
    EXPECT_NEAR(w.effectiveSeconds, 5400.0, 0.0);
    EXPECT_FALSE(w.finished);
    // Duração maior que o teto offline: o teto vence.
    RulesConstants shortCap = r;
    shortCap.maxOfflineHours = 6.0;
    w = ComputeExpeditionWindow(kStart, 12, Now(kStart + 30 * kHour, kStart), kStart, shortCap);
    EXPECT_NEAR(w.effectiveSeconds, 6 * 3600.0, 0.0);
    // Tudo é horário Unix UTC: o resultado só depende dos segundos (fuso do SO é irrelevante).
    const OfflineWindow w2 = ComputeExpeditionWindow(kStart + 7200, 4, Now(kStart + 7200 + 10 * kHour, kStart), kStart, r);
    EXPECT_NEAR(w2.effectiveSeconds, 4 * 3600.0, 0.0);
}

TEST(clock_rf48_rollback_tolerance_five_minutes) {
    const RulesConstants r;
    const UnixSeconds t = kStart + 2 * kHour;  // last_seen = T
    // Agora = T - 6 min: encerra no último ponto conhecido.
    TrustedNow n = Now(t - 6 * 60, t);
    EXPECT_TRUE(n.rollbackDetected);
    OfflineWindow w = ComputeExpeditionWindow(kStart, 4, n, t, r);
    EXPECT_TRUE(w.endedByRollback);
    EXPECT_TRUE(w.finished);
    EXPECT_NEAR(w.effectiveSeconds, 2 * 3600.0, 0.0);  // clamp(lastSeen - start): sem tempo extra
    // Agora = T - 4 min: segue normal.
    n = Now(t - 4 * 60, t);
    EXPECT_FALSE(n.rollbackDetected);
    w = ComputeExpeditionWindow(kStart, 4, n, t, r);
    EXPECT_FALSE(w.endedByRollback);
    EXPECT_NEAR(w.effectiveSeconds, 2 * 3600.0 - 240.0, 0.0);
    // Save novo (last_seen = 0) nunca acusa retrocesso.
    EXPECT_FALSE(Now(kStart, 0).rollbackDetected);
    // Retrocesso com last_seen antes do início não gera tempo negativo.
    w = ComputeExpeditionWindow(kStart, 4, Now(kStart - 10 * kHour, kStart - 5 * kHour), kStart - 5 * kHour, r);
    EXPECT_NEAR(w.effectiveSeconds, 0.0, 0.0);
}

TEST(clock_rf49_clock_set_forward_gives_exactly_the_chosen_duration) {
    const RulesConstants r;
    const TrustedNow n = Now(kStart + 3 * 24 * kHour, kStart);  // adiantou 3 dias numa expedição de 2 h
    const OfflineWindow w = ComputeExpeditionWindow(kStart, 2, n, kStart, r);
    EXPECT_NEAR(w.effectiveSeconds, 2 * 3600.0, 0.0);
    // E o resultado simulado é o mesmo que o de esperar as 2 h.
    const ContentDB& db = tu::RichDb();
    ExpeditionRequest a = tu::MakeRequest(db, 2, 61);
    a.effectiveSeconds = w.effectiveSeconds;
    ExpeditionRequest b = a;
    b.effectiveSeconds = ComputeExpeditionWindow(kStart, 2, Now(kStart + 2 * kHour, kStart), kStart, r).effectiveSeconds;
    EXPECT_EQ(SimulateExpedition(db, a).resultHash, SimulateExpedition(db, b).resultHash);
}

TEST(clock_steam_time_wins_when_skew_exceeds_ten_minutes) {
    TrustedNow n = Now(kStart + 11 * 60, kStart, true, kStart);  // PC 11 min adiantado
    EXPECT_TRUE(n.usedSteam);
    EXPECT_EQ(n.now, kStart);
    n = Now(kStart + 9 * 60, kStart, true, kStart);
    EXPECT_FALSE(n.usedSteam);
    EXPECT_EQ(n.now, kStart + 9 * 60);
    n = Now(kStart - 11 * 60, kStart, true, kStart);  // PC atrasado: usa a Steam, sem acusar retrocesso
    EXPECT_TRUE(n.usedSteam);
    EXPECT_FALSE(n.rollbackDetected);
    // Relógio local voltado 1 dia, mas a Steam confirma a hora real: não é retrocesso.
    n = Now(kStart - 24 * kHour, kStart, true, kStart + 10);
    EXPECT_TRUE(n.usedSteam);
    EXPECT_FALSE(n.rollbackDetected);
    EXPECT_FALSE(Now(kStart, kStart, false, 0).usedSteam);
}

TEST(clock_rf35_daily_rest_does_not_accumulate_and_respects_max) {
    const RulesConstants r;
    std::int64_t lastDay = UtcDay(kStart);
    // Mesmo dia: nada.
    int charges = ApplyDailyRest(3, lastDay, Now(kStart + 100, kStart), r);
    EXPECT_EQ(charges, 3);
    // Novo dia UTC: +4.
    charges = ApplyDailyRest(3, lastDay, Now(kStart + 86400, kStart), r);
    EXPECT_EQ(charges, 7);
    EXPECT_EQ(lastDay, UtcDay(kStart) + 1);
    // 3 dias sem abrir o jogo: só +4 (não acumula os dias perdidos).
    charges = ApplyDailyRest(0, lastDay, Now(kStart + 4 * 86400, kStart), r);
    EXPECT_EQ(charges, 4);
    // Respeita o teto de 12 (12 + descanso = 12).
    lastDay = UtcDay(kStart);
    EXPECT_EQ(ApplyDailyRest(12, lastDay, Now(kStart + 86400, kStart), r), 12);
    EXPECT_EQ(ApplyDailyRest(10, lastDay, Now(kStart + 2 * 86400, kStart), r), 12);
    // Relógio voltando nunca concede.
    std::int64_t day = UtcDay(kStart) - 5;
    const TrustedNow back = Now(kStart - 3600, kStart + 3600);
    EXPECT_TRUE(back.rollbackDetected);
    EXPECT_EQ(ApplyDailyRest(2, day, back, r), 2);
    EXPECT_EQ(day, UtcDay(kStart) - 5);
    // Dia UTC com horário negativo.
    EXPECT_EQ(UtcDay(-1), -1);
    EXPECT_EQ(UtcDay(0), 0);
    EXPECT_EQ(UtcDay(86399), 0);
    EXPECT_EQ(UtcDay(86400), 1);
}

TEST(clock_last_seen_never_goes_backwards) {
    EXPECT_EQ(NextLastSeen(1000, Now(900, 1000)), 1000);
    EXPECT_EQ(NextLastSeen(1000, Now(1500, 1000)), 1500);
}
