// Stun, imunidades e Guarda Quebrada (docs/13, item 3) e o chefe: escudo frontal, fases, rugido, invocação e padrões
// por seed (itens 4 e 6). Passo fixo de 1/60 s como no jogo em tempo real.
#include <cmath>
#include <memory>

#include "test_util.h"

using namespace shatter;

namespace {

constexpr double kDt = 1.0 / 60.0;
constexpr double kPi = 3.14159265358979323846;

struct Timed {
    double t = 0.0;
    BossEvent e;
};

struct Arena {
    const ContentDB& db = tu::RichDb();
    const EnemyData* boss = db.FindEnemy("enemy.crypt_guardian");
    StatBlock sb;
    EffectContainer fx;
    std::vector<Timed> log;
    double now = 0.0;
    Vec2 bossPos{0.0, 0.0};
    Vec2 player{0.0, 1000.0};
    std::unique_ptr<BossFight> fight;

    explicit Arena(std::uint64_t seed) {
        BuildEnemyStatBlock(*boss, 4, sb);
        fight = std::make_unique<BossFight>(db, *boss, 4, seed);
    }

    void Collect(const std::vector<BossEvent>& ev) {
        for (const BossEvent& e : ev) log.push_back({now, e});
    }

    void Run(double seconds) {
        const int n = static_cast<int>(seconds / kDt + 0.5);
        for (int i = 0; i < n; ++i) {
            std::vector<BossEvent> ev;
            BossFight::Context c;
            c.boss = bossPos;
            c.player = player;
            now += kDt;
            fight->Step(kDt, c, sb, ev);
            std::vector<EffectEvent> fxEvents;
            fx.Tick(kDt, db.EffectLookup(), sb, fxEvents);
            Collect(ev);
        }
    }

    StatusApply Apply(const char* effectId) {
        std::vector<BossEvent> ev;
        const StatusApply r = fight->ApplyEffect(db, *db.FindEffect(effectId), "player", 1.0, fx, sb, ev);
        Collect(ev);
        return r;
    }

    BossFight::DamageResult Hit(double amount, Vec2 origin) {
        std::vector<BossEvent> ev;
        const BossFight::DamageResult r = fight->ApplyDamage(amount, bossPos, origin, ev);
        Collect(ev);
        return r;
    }

    int Count(BossEvent::Kind k) const {
        int n = 0;
        for (const Timed& t : log) n += t.e.kind == k ? 1 : 0;
        return n;
    }
    const Timed* First(BossEvent::Kind k, std::size_t from = 0) const {
        for (std::size_t i = from; i < log.size(); ++i)
            if (log[i].e.kind == k) return &log[i];
        return nullptr;
    }
};

Vec2 FromFront(double degrees, double dist = 500.0) {
    const double a = degrees * kPi / 180.0;
    return Vec2{std::sin(a) * dist, std::cos(a) * dist};
}

// Alvo comum (herói/sentinela) com status e contêiner próprios.
struct Target {
    StatBlock sb;
    EffectContainer fx;
    ActionStatus st;
    double now = 0.0;
    Target(const ContentDB& db, const char* enemyId, bool elite) {
        const EnemyData* e = enemyId != nullptr ? db.FindEnemy(enemyId) : nullptr;
        if (e != nullptr) BuildEnemyStatBlock(*e, 3, sb);
        st.Init(MakeStatusProfile(db, e, elite));
    }
    StatusApply Apply(const ContentDB& db, const char* effectId) {
        return st.ApplyEffect(db, *db.FindEffect(effectId), "player", 1.0, TriggerKind::None, fx, sb);
    }
    void Advance(const ContentDB& db, double seconds) {
        const int n = static_cast<int>(seconds / kDt + 0.5);
        for (int i = 0; i < n; ++i) {
            std::vector<EffectEvent> ev;
            fx.Tick(kDt, db.EffectLookup(), sb, ev);
            st.Tick(kDt, sb);
            now += kDt;
        }
    }
};

}  // namespace

// ---------------------------------------------------------------------------------------------
// Stun e Guarda Quebrada
// ---------------------------------------------------------------------------------------------
TEST(status_stun_interrupts_commons_for_08s_and_elites_are_immune) {
    const ContentDB& db = tu::RichDb();
    EXPECT_TRUE(db.FindEffect("effect.stun")->interruptsAction);
    Target common(db, "enemy.hollow_sentinel", false);
    EXPECT_TRUE(common.st.CanAct());
    EXPECT_TRUE(CanAct(common.sb));
    const StatusApply r = common.Apply(db, "effect.stun");
    EXPECT_TRUE(r.applied && r.stunned && r.interrupted);        // interrompe a preparação em andamento
    EXPECT_NEAR(r.stunSeconds, 0.8, 1e-12);
    EXPECT_FALSE(common.st.CanAct());
    EXPECT_FALSE(CanAct(common.sb));                              // o efeito também zera a velocidade de ataque
    common.Advance(db, 0.7);
    EXPECT_FALSE(common.st.CanAct());
    common.Advance(db, 0.11);
    EXPECT_TRUE(common.st.CanAct());
    EXPECT_TRUE(CanAct(common.sb));
    // Elite (fixo ou sorteado), chefe e constructo: imunes; nada é aplicado.
    Target eliteFixed(db, "enemy.shielded_sentinel", false);
    Target eliteRolled(db, "enemy.hollow_sentinel", true);
    for (Target* t : {&eliteFixed, &eliteRolled}) {
        const StatusApply s = t->Apply(db, "effect.stun");
        EXPECT_TRUE(s.stunBlocked);
        EXPECT_FALSE(s.applied || s.stunned || s.interrupted);
        EXPECT_FALSE(t->fx.Has("effect.stun"));
        EXPECT_TRUE(t->st.CanAct());
    }
    Target boss(db, "enemy.crypt_guardian", false);
    EXPECT_TRUE(boss.Apply(db, "effect.stun").stunBlocked);
}

TEST(status_guard_break_commons_get_damage_bonus_but_no_stagger) {
    const ContentDB& db = tu::RichDb();
    Target common(db, "enemy.hollow_sentinel", false);
    for (int i = 1; i <= 4; ++i) {
        const StatusApply r = common.Apply(db, "effect.guard_break");
        EXPECT_FALSE(r.staggered);
        EXPECT_EQ(r.guardBreakStacks, i <= 3 ? i : 3);            // até 3 acúmulos
    }
    EXPECT_NEAR(common.sb.Get(StatId::DamageTaken), 1.3, 1e-9);   // +10% por acúmulo
    EXPECT_TRUE(common.st.CanAct());
}

TEST(status_guard_break_staggers_immune_targets_with_immunity_and_single_timer) {
    const ContentDB& db = tu::RichDb();
    Target elite(db, "enemy.shielded_sentinel", false);
    EXPECT_FALSE(elite.Apply(db, "effect.guard_break").staggered);
    EXPECT_FALSE(elite.Apply(db, "effect.guard_break").staggered);
    const StatusApply third = elite.Apply(db, "effect.guard_break");
    EXPECT_TRUE(third.staggered && third.interrupted && third.removeBarrier);   // quebra a barreira/escudo
    EXPECT_NEAR(third.staggerSeconds, 1.5, 1e-12);
    EXPECT_EQ(third.guardBreakStacks, 0);                                       // os acúmulos foram consumidos
    EXPECT_EQ(elite.fx.StackCount("effect.guard_break"), 0);
    EXPECT_TRUE(elite.st.Staggered());
    EXPECT_FALSE(elite.st.CanAct());
    EXPECT_NEAR(elite.sb.Get(StatId::DamageTaken), 1.3, 1e-9);                  // +30% durante o stagger
    elite.Advance(db, 1.45);
    EXPECT_TRUE(elite.st.Staggered());
    elite.Advance(db, 0.1);
    EXPECT_FALSE(elite.st.Staggered());
    EXPECT_NEAR(elite.sb.Get(StatId::DamageTaken), 1.0, 1e-9);                  // bônus saiu
    // Imunidade de 4 s (elite) a partir do início do stagger: 3 novos acúmulos aos ~1,6 s não atordoam.
    for (int i = 0; i < 3; ++i) EXPECT_FALSE(elite.Apply(db, "effect.guard_break").staggered);
    EXPECT_EQ(elite.fx.StackCount("effect.guard_break"), 3);
    elite.Advance(db, 2.5);                                                     // passou dos 4 s
    EXPECT_TRUE(elite.Apply(db, "effect.guard_break").staggered);               // 3 acúmulos ainda valiam (timer renovado)

    // Chefe: imunidade de 8 s.
    Target boss(db, "enemy.crypt_guardian", false);
    for (int i = 0; i < 2; ++i) boss.Apply(db, "effect.guard_break");
    EXPECT_TRUE(boss.Apply(db, "effect.guard_break").staggered);
    EXPECT_NEAR(boss.st.ImmunityRemaining(), 8.0, 1e-12);
    boss.Advance(db, 2.0);
    for (int i = 0; i < 3; ++i) EXPECT_FALSE(boss.Apply(db, "effect.guard_break").staggered);
    boss.Advance(db, 6.1);                                                      // 8,1 s depois do stagger
    EXPECT_TRUE(boss.Apply(db, "effect.guard_break").staggered);

    // Timer único: o 2º acúmulo, 5 s depois do 1º, renova os dois (sem timer único o 1º expiraria aos 8 s).
    Target t(db, "enemy.hollow_sentinel", false);
    t.Apply(db, "effect.guard_break");
    t.Advance(db, 5.0);
    t.Apply(db, "effect.guard_break");
    t.Advance(db, 4.0);                                                         // t = 9 s
    EXPECT_EQ(t.fx.StackCount("effect.guard_break"), 2);
    t.Advance(db, 3.9);                                                         // t = 12,9 s (< 5 + 8)
    EXPECT_EQ(t.fx.StackCount("effect.guard_break"), 2);
    t.Advance(db, 0.2);                                                         // t = 13,1 s: os dois expiraram juntos
    EXPECT_EQ(t.fx.StackCount("effect.guard_break"), 0);
}

// ---------------------------------------------------------------------------------------------
// Escudo frontal do chefe
// ---------------------------------------------------------------------------------------------
TEST(boss_front_shield_blocks_inside_plus_minus_60_degrees_only) {
    Arena a(1);
    a.fight->Start();
    a.Run(kDt);   // o 1º passo vira o chefe para o jogador (frente = +z)
    ASSERT_TRUE(a.boss->shieldArcDegrees == 120.0);
    const Vec2 B = a.bossPos;
    EXPECT_TRUE(a.fight->ShieldCovers(B, FromFront(0)));
    EXPECT_TRUE(a.fight->ShieldCovers(B, FromFront(59)));
    EXPECT_TRUE(a.fight->ShieldCovers(B, FromFront(-59)));
    EXPECT_FALSE(a.fight->ShieldCovers(B, FromFront(61)));
    EXPECT_FALSE(a.fight->ShieldCovers(B, FromFront(-61)));
    EXPECT_FALSE(a.fight->ShieldCovers(B, FromFront(90)));
    EXPECT_FALSE(a.fight->ShieldCovers(B, FromFront(180)));
    // Golpe pela frente: 0 de dano à vida; por trás: entra.
    const double life = a.fight->Life();
    const BossFight::DamageResult front = a.Hit(50.0, FromFront(20));
    EXPECT_TRUE(front.shieldBlocked);
    EXPECT_NEAR(front.applied, 0.0, 0.0);
    EXPECT_NEAR(a.fight->Life(), life, 0.0);
    const BossFight::DamageResult back = a.Hit(50.0, FromFront(150));
    EXPECT_FALSE(back.shieldBlocked);
    EXPECT_NEAR(back.applied, 50.0, 1e-9);
    EXPECT_NEAR(a.fight->Life(), life - 50.0, 1e-9);
}

TEST(boss_guard_break_drops_the_shield_interrupts_and_staggers) {
    Arena a(3);
    a.fight->Start();
    a.Run(2.0);
    // Espera um telegraph começar para provar a interrupção.
    for (int i = 0; i < 600 && a.fight->State() != BossState::Telegraph; ++i) a.Run(kDt);
    ASSERT_TRUE(a.fight->State() == BossState::Telegraph);
    EXPECT_FALSE(a.Apply("effect.stun").applied);                   // chefe é imune ao stun
    EXPECT_FALSE(a.Apply("effect.guard_break").staggered);
    EXPECT_FALSE(a.Apply("effect.guard_break").staggered);
    const StatusApply third = a.Apply("effect.guard_break");
    EXPECT_TRUE(third.staggered && third.removeBarrier);
    EXPECT_TRUE(a.fight->State() == BossState::Stagger);
    EXPECT_EQ(a.Count(BossEvent::Kind::PatternInterrupted), 1);
    EXPECT_EQ(a.Count(BossEvent::Kind::StaggerStart), 1);
    EXPECT_EQ(a.Count(BossEvent::Kind::ShieldDown), 1);
    EXPECT_NEAR(a.First(BossEvent::Kind::StaggerStart)->e.seconds, 1.5, 1e-12);
    EXPECT_NEAR(a.First(BossEvent::Kind::ShieldDown)->e.seconds, 5.0, 1e-12);
    EXPECT_FALSE(a.fight->ShieldUp());
    EXPECT_FALSE(a.fight->ShieldCovers(a.bossPos, FromFront(0)));   // escudo caído: golpe de frente entra
    EXPECT_FALSE(a.Hit(10.0, FromFront(0)).shieldBlocked);
    EXPECT_NEAR(a.sb.Get(StatId::DamageTaken), 1.3, 1e-9);          // +30% de dano recebido no stagger
    a.Run(1.6);
    EXPECT_EQ(a.Count(BossEvent::Kind::StaggerEnd), 1);
    EXPECT_NEAR(a.sb.Get(StatId::DamageTaken), 1.0, 1e-9);
    EXPECT_FALSE(a.fight->ShieldUp());                              // o escudo fica caído por 5 s, não 1,5
    a.Run(3.5);
    EXPECT_EQ(a.Count(BossEvent::Kind::ShieldUp), 1);
    EXPECT_TRUE(a.fight->ShieldUp());
    const Timed* down = a.First(BossEvent::Kind::ShieldDown);
    const Timed* up = a.First(BossEvent::Kind::ShieldUp);
    EXPECT_NEAR(up->t - down->t, 5.0, 2.0 * kDt);
    // Imunidade de 8 s: 3 acúmulos logo depois não atordoam de novo.
    for (int i = 0; i < 3; ++i) EXPECT_FALSE(a.Apply("effect.guard_break").staggered);
}

TEST(boss_turn_rate_is_limited_and_locked_from_telegraph_to_end_of_impact) {
    Arena a(5);
    a.fight->Start();
    a.Run(kDt);
    // O jogador pula de lado a lado do chefe a 400 uu: o giro respeita 60°/s (fase 1) e trava no golpe.
    double ang = 0.0;
    Vec2 prevFacing = a.fight->Facing();
    bool locked = false;
    Vec2 lockedFacing{};
    double maxStepAngle = 0.0;
    int lockedSteps = 0;
    for (int i = 0; i < 60 * 40; ++i) {
        ang = 150.0 * static_cast<double>(i / 120);  // o jogador "salta" 150° a cada 2 s: o chefe tem de girar para alcançar
        a.player = Vec2{std::sin(ang * kPi / 180.0) * 400.0, std::cos(ang * kPi / 180.0) * 400.0};
        a.Run(kDt);
        const Vec2 f = a.fight->Facing();
        const double dot = f.x * prevFacing.x + f.z * prevFacing.z;
        const double step = std::acos(dot > 1.0 ? 1.0 : (dot < -1.0 ? -1.0 : dot)) * 180.0 / kPi;
        if (step > maxStepAngle) maxStepAngle = step;
        const BossState s = a.fight->State();
        if (s == BossState::Telegraph || s == BossState::Impact) {
            if (!locked) { locked = true; lockedFacing = f; }
            EXPECT_NEAR(f.x, lockedFacing.x, 1e-12);
            EXPECT_NEAR(f.z, lockedFacing.z, 1e-12);
            ++lockedSteps;
        } else {
            locked = false;
        }
        prevFacing = f;
    }
    EXPECT_TRUE(lockedSteps > 60);                                // houve golpes no teste
    EXPECT_TRUE(maxStepAngle <= 60.0 * kDt + 1e-6);               // nunca gira mais que 60°/s
    EXPECT_TRUE(maxStepAngle > 0.9 * 60.0 * kDt);                 // e usa a taxa máxima ao perseguir
}

// ---------------------------------------------------------------------------------------------
// Fases
// ---------------------------------------------------------------------------------------------
TEST(boss_phase_two_at_50_percent_roar_summons_exactly_two_and_resets) {
    Arena a(11);
    a.fight->Start();
    a.Run(0.3);
    ASSERT_TRUE(a.fight->State() == BossState::Waiting);
    const double maxLife = a.fight->MaxLife();
    EXPECT_NEAR(maxLife, 600.0 + 60.0 * 3.0, 1e-9);
    const Vec2 behind = FromFront(180);
    // Dano que passaria de 50%: cortado no limiar; o rugido começa já (parado entre ações).
    const BossFight::DamageResult r = a.Hit(maxLife, behind);
    EXPECT_TRUE(r.clampedByPhase);
    EXPECT_FALSE(r.killed);
    EXPECT_NEAR(r.applied, maxLife * 0.5, 1e-9);
    EXPECT_NEAR(a.fight->Life(), maxLife * 0.5, 1e-9);
    EXPECT_TRUE(a.fight->State() == BossState::Transition);
    EXPECT_TRUE(a.fight->Invulnerable());
    EXPECT_EQ(a.fight->Phase(), 2);
    ASSERT_TRUE(a.First(BossEvent::Kind::PhaseTransitionStart) != nullptr);
    EXPECT_NEAR(a.First(BossEvent::Kind::PhaseTransitionStart)->e.seconds, 2.0, 1e-12);
    const Timed* marker = a.First(BossEvent::Kind::SummonMarker);
    ASSERT_TRUE(marker != nullptr);
    EXPECT_EQ(marker->e.count, 2);
    EXPECT_EQ(marker->e.enemyId, std::string("enemy.hollow_sentinel"));
    EXPECT_NEAR(marker->e.seconds, 1.0, 1e-12);                   // surgem no meio do rugido
    // Durante o rugido o dano é ignorado (invulnerável).
    const BossFight::DamageResult inv = a.Hit(100.0, behind);
    EXPECT_TRUE(inv.invulnerable);
    EXPECT_NEAR(inv.applied, 0.0, 0.0);
    const double t0 = a.now;
    a.Run(2.1);
    ASSERT_EQ(a.Count(BossEvent::Kind::SummonSpawn), 1);
    const Timed* spawn = a.First(BossEvent::Kind::SummonSpawn);
    EXPECT_EQ(spawn->e.count, 2);
    EXPECT_NEAR(spawn->t - t0, 1.0, 3.0 * kDt);
    ASSERT_EQ(a.Count(BossEvent::Kind::PhaseTransitionEnd), 1);
    EXPECT_NEAR(a.First(BossEvent::Kind::PhaseTransitionEnd)->t - t0, 2.0, 3.0 * kDt);
    EXPECT_FALSE(a.fight->Invulnerable());
    // Sem reinvocação nos 60 s seguintes e o dano volta a valer.
    a.Run(60.0);
    EXPECT_EQ(a.Count(BossEvent::Kind::SummonSpawn), 1);
    EXPECT_EQ(a.Count(BossEvent::Kind::PhaseTransitionStart), 1);
    EXPECT_NEAR(a.Hit(40.0, behind).applied, 40.0, 1e-9);
    // Rugido não pode ser interrompido por Guarda Quebrada (acumula sem atordoar).
    // Morte: dano excedente da fase 2 mata; depois de morto, nada entra.
    const BossFight::DamageResult kill = a.Hit(1e9, behind);
    EXPECT_TRUE(kill.killed);
    EXPECT_NEAR(a.fight->Life(), 0.0, 0.0);
    EXPECT_EQ(a.Count(BossEvent::Kind::Died), 1);
    EXPECT_TRUE(a.fight->State() == BossState::Dead);
    EXPECT_NEAR(a.Hit(10.0, behind).applied, 0.0, 0.0);
    // Reinício total (o jogador morreu): vida cheia, fase 1, escudo de pé, pronto para outra luta.
    a.fight->Reset(&a.sb);
    EXPECT_NEAR(a.fight->Life(), maxLife, 0.0);
    EXPECT_EQ(a.fight->Phase(), 1);
    EXPECT_TRUE(a.fight->State() == BossState::Idle);
    EXPECT_TRUE(a.fight->ShieldUp());
    a.log.clear();
    a.fight->Start();
    a.Run(0.3);
    a.Hit(maxLife, behind);
    a.Run(2.1);
    EXPECT_EQ(a.Count(BossEvent::Kind::SummonSpawn), 1);          // a 2ª luta invoca de novo (uma vez)
}

TEST(boss_phase_transition_waits_for_the_current_pattern_to_finish) {
    Arena a(23);
    a.fight->Start();
    for (int i = 0; i < 600 && a.fight->State() != BossState::Telegraph; ++i) a.Run(kDt);
    ASSERT_TRUE(a.fight->State() == BossState::Telegraph);
    const BossFight::DamageResult r = a.Hit(a.fight->MaxLife(), FromFront(180));
    EXPECT_TRUE(r.clampedByPhase);
    EXPECT_TRUE(a.fight->State() == BossState::Telegraph);        // não interrompe o golpe em curso
    EXPECT_EQ(a.Count(BossEvent::Kind::PhaseTransitionStart), 0);
    a.Run(6.0);
    ASSERT_TRUE(a.First(BossEvent::Kind::PhaseTransitionStart) != nullptr);
    const Timed* impact = a.First(BossEvent::Kind::PatternImpact);
    const Timed* end = a.First(BossEvent::Kind::PatternEnd);
    ASSERT_TRUE(impact != nullptr && end != nullptr);
    EXPECT_TRUE(end->t <= a.First(BossEvent::Kind::PhaseTransitionStart)->t);
    EXPECT_EQ(a.Count(BossEvent::Kind::PatternInterrupted), 0);
}

// ---------------------------------------------------------------------------------------------
// Padrões por seed
// ---------------------------------------------------------------------------------------------
namespace {

std::vector<Timed> PatternRun(std::uint64_t seed, double seconds, Vec2 player, bool phaseTwo) {
    Arena a(seed);
    a.player = player;
    a.fight->Start();
    a.Run(0.2);
    if (phaseTwo) {
        a.Hit(a.fight->MaxLife(), FromFront(180));
        a.Run(2.2);
        a.log.clear();
    }
    a.Run(seconds);
    return a.log;
}

std::vector<std::string> PatternIds(const std::vector<Timed>& log) {
    std::vector<std::string> out;
    for (const Timed& t : log)
        if (t.e.kind == BossEvent::Kind::PatternStart) out.push_back(t.e.patternId);
    return out;
}

}  // namespace

TEST(boss_patterns_same_seed_same_sequence_different_seed_differs) {
    const std::vector<Timed> a = PatternRun(777, 120.0, Vec2{0.0, 900.0}, false);
    const std::vector<Timed> b = PatternRun(777, 120.0, Vec2{0.0, 900.0}, false);
    ASSERT_TRUE(a.size() == b.size());
    for (std::size_t i = 0; i < a.size(); ++i) {
        EXPECT_TRUE(a[i].e.kind == b[i].e.kind);
        EXPECT_EQ(a[i].e.patternId, b[i].e.patternId);
        EXPECT_NEAR(a[i].t, b[i].t, 0.0);
    }
    EXPECT_TRUE(PatternIds(a).size() > 20);
    int different = 0;
    for (std::uint64_t seed = 1; seed <= 6; ++seed)
        different += PatternIds(PatternRun(seed, 120.0, Vec2{0.0, 900.0}, false)) != PatternIds(a) ? 1 : 0;
    EXPECT_EQ(different, 6);
}

TEST(boss_patterns_never_repeat_three_times_and_delays_stay_in_range) {
    for (std::uint64_t seed = 1; seed <= 10; ++seed) {
        for (bool phase2 : {false, true}) {
            const std::vector<Timed> log = PatternRun(seed, 200.0, Vec2{0.0, 900.0}, phase2);
            const std::vector<std::string> ids = PatternIds(log);
            ASSERT_TRUE(ids.size() > 20);
            for (std::size_t i = 2; i < ids.size(); ++i) {
                if (ids[i] == ids[i - 1] && ids[i] == ids[i - 2]) { FAIL("padrao repetido 3 vezes (seed " + std::to_string(seed) + ")"); return; }
            }
            // Atraso entre o fim de uma ação e o telegraph da próxima: sorteado no intervalo da fase.
            const double lo = phase2 ? 0.6 : 0.8, hi = phase2 ? 1.1 : 1.4;
            for (std::size_t i = 0; i + 1 < log.size(); ++i) {
                if (log[i].e.kind != BossEvent::Kind::PatternEnd) continue;
                for (std::size_t j = i + 1; j < log.size(); ++j) {
                    if (log[j].e.kind != BossEvent::Kind::PatternStart) continue;
                    const double gap = log[j].t - log[i].t;
                    if (gap < lo - 3.0 * kDt || gap > hi + 3.0 * kDt) { FAIL("atraso fora do intervalo: " + std::to_string(gap)); return; }
                    break;
                }
            }
        }
    }
}

TEST(boss_patterns_use_phase_telegraph_times_cooldown_and_player_position_weights) {
    // Telegraph do martelo: 1,1 s na fase 1 e 0,9 s na fase 2 (boss_patterns.csv, chave id + phase).
    const std::vector<Timed> p1 = PatternRun(4, 60.0, Vec2{0.0, 900.0}, false);
    const std::vector<Timed> p2 = PatternRun(4, 60.0, Vec2{0.0, 900.0}, true);
    for (const Timed& t : p1)
        if (t.e.kind == BossEvent::Kind::PatternStart && t.e.patternId == "pattern.guardian.hammer") EXPECT_NEAR(t.e.seconds, 1.1, 1e-12);
    bool sawCharge = false;
    double lastCharge = -1000.0;
    for (const Timed& t : p2) {
        if (t.e.kind != BossEvent::Kind::PatternStart) continue;
        if (t.e.patternId == "pattern.guardian.hammer") EXPECT_NEAR(t.e.seconds, 0.9, 1e-12);
        if (t.e.patternId == "pattern.guardian.shield_charge") {
            sawCharge = true;
            EXPECT_TRUE(t.t - lastCharge >= 12.0 - 1e-9);          // recarga própria de 12 s
            lastCharge = t.t;
        }
        EXPECT_TRUE(t.e.phase == 2);
    }
    EXPECT_TRUE(sawCharge);
    for (const Timed& t : p1) EXPECT_TRUE(t.e.patternId != "pattern.guardian.shield_charge");   // só na fase 2

    // Jogador atrás do chefe: a Pancada de Escudo (ignoreIfBehind) nunca é sorteada no 1º padrão.
    // Perto e na frente (< alcance 200): peso ×2. Longe e na frente: peso normal.
    int bashBehind = 0, bashNear = 0, bashFar = 0;
    const int seeds = 300;
    for (int s = 1; s <= seeds; ++s) {
        for (int mode = 0; mode < 3; ++mode) {
            Arena a(static_cast<std::uint64_t>(s));
            a.fight->Start();
            a.Run(kDt);                                           // vira para o jogador (frente)
            if (mode == 0) a.player = Vec2{0.0, -900.0};          // atrás
            else if (mode == 1) a.player = Vec2{0.0, 150.0};      // perto e na frente
            else a.player = Vec2{0.0, 900.0};                     // longe e na frente
            a.Run(1.6);
            const Timed* first = a.First(BossEvent::Kind::PatternStart);
            ASSERT_TRUE(first != nullptr);
            const bool bash = first->e.patternId == "pattern.guardian.shield_bash";
            (mode == 0 ? bashBehind : mode == 1 ? bashNear : bashFar) += bash ? 1 : 0;
        }
    }
    EXPECT_EQ(bashBehind, 0);
    EXPECT_NEAR(static_cast<double>(bashFar) / seeds, 2.0 / 5.0, 0.08);     // pesos 3 e 2
    EXPECT_NEAR(static_cast<double>(bashNear) / seeds, 4.0 / 7.0, 0.08);    // pesos 3 e 2 × 2
}

TEST(boss_phase_and_pattern_tables_are_keyed_by_boss_and_id_plus_phase) {
    const ContentDB& db = tu::RichDb();
    ASSERT_TRUE(db.FindBossPhase("enemy.crypt_guardian", 2) != nullptr);
    EXPECT_NEAR(db.FindBossPhase("enemy.crypt_guardian", 2)->lifeThreshold, 0.5, 0.0);
    EXPECT_EQ(db.FindBossPhase("enemy.crypt_guardian", 2)->summonCount, 2);
    EXPECT_TRUE(db.FindBossPhase("enemy.crypt_guardian", 3) == nullptr);
    ASSERT_TRUE(db.FindBossPattern("pattern.guardian.hammer", 1) != nullptr);
    ASSERT_TRUE(db.FindBossPattern("pattern.guardian.hammer", 2) != nullptr);
    EXPECT_NEAR(db.FindBossPattern("pattern.guardian.hammer", 1)->telegraphSeconds, 1.1, 0.0);
    EXPECT_NEAR(db.FindBossPattern("pattern.guardian.hammer", 2)->telegraphSeconds, 0.9, 0.0);
    EXPECT_TRUE(db.FindBossPattern("pattern.guardian.shield_charge", 1) == nullptr);
    EXPECT_EQ(db.BossPatterns().size(), static_cast<std::size_t>(5));
    // Skills do chefe com forma: cone, empurrão e corredor (a largura de 150 é o raio da investida).
    EXPECT_NEAR(db.FindSkill("skill.enemy.guardian_hammer")->coneAngle, 100.0, 0.0);
    EXPECT_NEAR(db.FindSkill("skill.enemy.guardian_shield_bash")->knockback, 200.0, 0.0);
    EXPECT_NEAR(db.FindSkill("skill.enemy.guardian_shield_charge")->radius, 150.0, 0.0);
    // Dados do inimigo: escudo de 120° no total e giros por fase.
    const EnemyData* boss = db.FindEnemy("enemy.crypt_guardian");
    EXPECT_NEAR(boss->shieldArcDegrees, 120.0, 0.0);
    EXPECT_NEAR(boss->turnRateDegPerSec, 60.0, 0.0);
    EXPECT_NEAR(boss->turnRateDegPerSecPhase2, 75.0, 0.0);
    EXPECT_TRUE(boss->stunImmune);
    // Arqueiro: IA com faixa preferida e atiradores simultâneos.
    const EnemyAiData* ai = db.FindEnemyAi("enemy.ash_spitter");
    ASSERT_TRUE(ai != nullptr);
    EXPECT_NEAR(ai->preferredMin, 700.0, 0.0);
    EXPECT_EQ(ai->maxSimultaneousShooters, 2);
    EXPECT_TRUE(db.FindEnemyAi("enemy.hollow_sentinel") == nullptr);
}

TEST(trig_helpers_are_deterministic_and_accurate) {
    for (double x = -3.14159; x <= 3.14159; x += 0.05) {
        EXPECT_NEAR(DetCos(x), std::cos(x), 1e-12);
        EXPECT_NEAR(DetSin(x), std::sin(x), 1e-12);
    }
}
