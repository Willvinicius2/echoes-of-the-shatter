// Fuga do inimigo no core (enemy_ai.csv: fleeLifeFraction, fleeSeconds, fleeOncePerLife).
// Observação: o simulador idle NÃO modela fuga de inimigo (eles lutam até morrer); esta regra é só da luta manual. Por isso
// a paridade aqui é com o contrato de decisão (o mesmo que o EnemyCombatLogic do cliente implementava) e com o CSV.
#include "test_util.h"

using namespace shatter;

namespace {
FleeProfile Profile(double f, double s, bool once) {
    FleeProfile p;
    p.lifeFraction = f;
    p.seconds = s;
    p.oncePerLife = once;
    return p;
}
}  // namespace

TEST(flee_starts_below_fraction_lasts_seconds_and_ends_by_time) {
    FleeState st(Profile(0.25, 1.0, true));
    EXPECT_FALSE(st.Step(0.1, 100.0, 100.0, true, false).fleeing);
    EXPECT_FALSE(st.Step(0.1, 25.0, 100.0, true, false).fleeing);   // exatamente na fração: não (estritamente abaixo)
    const FleeStep a = st.Step(0.1, 24.0, 100.0, true, false);
    EXPECT_TRUE(a.fleeing && a.started && !a.ended);
    EXPECT_NEAR(a.remaining, 1.0, 1e-12);
    const FleeStep b = st.Step(0.5, 24.0, 100.0, true, false);
    EXPECT_TRUE(b.fleeing && !b.started);
    EXPECT_NEAR(b.remaining, 0.5, 1e-12);
    const FleeStep c = st.Step(0.5, 24.0, 100.0, true, false);
    EXPECT_TRUE(!c.fleeing && c.ended);
    // Uma vez por vida: não foge de novo, nem baixando mais a vida.
    EXPECT_FALSE(st.Step(0.1, 5.0, 100.0, true, false).fleeing);
    st.Reset();  // revive
    EXPECT_TRUE(st.Step(0.1, 5.0, 100.0, true, false).started);
}

TEST(flee_repeats_without_once_per_life_and_stops_without_target_or_when_dead) {
    FleeState st(Profile(0.5, 2.0, false));
    EXPECT_TRUE(st.Step(0.1, 10.0, 100.0, true, false).started);
    const FleeStep lost = st.Step(0.1, 10.0, 100.0, false, false);   // sem alvo: acaba
    EXPECT_TRUE(!lost.fleeing && lost.ended);
    EXPECT_TRUE(st.Step(0.1, 10.0, 100.0, true, false).started);     // sem "uma vez": foge de novo
    EXPECT_TRUE(!st.Step(0.1, 0.0, 100.0, true, true).fleeing);      // morto
    EXPECT_FALSE(st.Fleeing());
    // Sem alvo, nem começa.
    FleeState idle(Profile(0.5, 2.0, false));
    EXPECT_FALSE(idle.Step(0.1, 1.0, 100.0, false, false).fleeing);
    // Vida máxima inválida nunca decide.
    EXPECT_FALSE(idle.Step(0.1, 0.0, 0.0, true, false).fleeing);
}

TEST(flee_zero_fraction_never_flees_and_zero_seconds_ends_next_step) {
    FleeState never{Profile(0.0, 4.0, true)};
    EXPECT_FALSE(never.Step(0.1, 1.0, 100.0, true, false).fleeing);
    FleeState zero(Profile(0.5, 0.0, true));
    EXPECT_TRUE(zero.Step(0.1, 1.0, 100.0, true, false).started);
    const FleeStep n = zero.Step(0.1, 1.0, 100.0, true, false);
    EXPECT_TRUE(n.ended && !n.fleeing);
}

TEST(flee_real_content_profiles_are_read_from_enemy_ai_csv) {
    ContentDB real;
    ASSERT_TRUE(real.LoadDirectory(tu::ContentDir()));
    int withFlee = 0;
    for (const EnemyAiData& ai : real.EnemyAis()) {
        if (ai.fleeLifeFraction <= 0.0) continue;
        ++withFlee;
        EXPECT_TRUE(ai.fleeLifeFraction < 1.0 && ai.fleeSeconds > 0.0);
        FleeState st(Profile(ai.fleeLifeFraction, ai.fleeSeconds, ai.fleeOncePerLife));
        EXPECT_FALSE(st.Step(0.0, 1000.0 * ai.fleeLifeFraction, 1000.0, true, false).fleeing);       // no limite: não
        EXPECT_TRUE(st.Step(0.0, 1000.0 * ai.fleeLifeFraction - 1.0, 1000.0, true, false).started);  // abaixo: começa
    }
    EXPECT_TRUE(withFlee > 0);
}
