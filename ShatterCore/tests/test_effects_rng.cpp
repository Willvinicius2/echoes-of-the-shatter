// Efeitos (RF-08, RF-09, RF-10) e RNG (sequências, fluxos, sem viés).
#include "test_util.h"

using namespace shatter;

namespace {

EffectData Slow() {
    EffectData e;
    e.id = "effect.slow";
    e.duration = 3.0;
    e.stackRule = StackRule::Refresh;
    e.modifiers.push_back({StatId::MoveSpeed, ModKind::More, -0.3, 0, ""});
    return e;
}

std::unordered_map<ContentId, const EffectData*> Lookup(std::initializer_list<const EffectData*> list) {
    std::unordered_map<ContentId, const EffectData*> m;
    for (const EffectData* e : list) m[e->id] = e;
    return m;
}

}  // namespace

TEST(effects_rf08_refresh_resets_duration) {
    const RulesConstants rules;
    const EffectData slow = Slow();
    const auto lookup = Lookup({&slow});
    StatBlock sb;
    EffectContainer fx;
    std::vector<EffectEvent> ev;
    EXPECT_TRUE(fx.Apply(slow, "p", 1.0, TriggerKind::None, sb, rules));
    EXPECT_NEAR(sb.Get(StatId::MoveSpeed), 0.7, 1e-12);
    for (int i = 0; i < 20; ++i) fx.Tick(0.1, lookup, sb, ev);  // 2 s
    EXPECT_NEAR(fx.Active()[0].remaining, 1.0, 1e-6);
    EXPECT_TRUE(fx.Apply(slow, "p", 1.0, TriggerKind::None, sb, rules));  // reaplicar
    EXPECT_EQ(fx.StackCount("effect.slow"), 1);
    EXPECT_NEAR(fx.Active()[0].remaining, 3.0, 1e-12);
    for (int i = 0; i < 29; ++i) fx.Tick(0.1, lookup, sb, ev);
    EXPECT_TRUE(fx.Has("effect.slow"));
    for (int i = 0; i < 3; ++i) fx.Tick(0.1, lookup, sb, ev);
    EXPECT_FALSE(fx.Has("effect.slow"));
    EXPECT_NEAR(sb.Get(StatId::MoveSpeed), 1.0, 1e-12);  // mod removido ao expirar
    EXPECT_TRUE(!ev.empty() && ev.back().kind == EffectEvent::Kind::Expired);
}

TEST(effects_rf09_stack_n_never_exceeds_max) {
    const RulesConstants rules;
    EffectData e;
    e.id = "effect.poison_stack";
    e.duration = 5.0;
    e.stackRule = StackRule::StackN;
    e.maxStacks = 3;
    e.modifiers.push_back({StatId::Armor, ModKind::Flat, -10.0, 0, ""});
    const auto lookup = Lookup({&e});
    StatBlock sb;
    sb.SetBase(StatId::Armor, 100);
    EffectContainer fx;
    for (int i = 0; i < 10; ++i) {
        EXPECT_TRUE(fx.Apply(e, "p", 1.0, TriggerKind::None, sb, rules));
        EXPECT_TRUE(fx.StackCount("effect.poison_stack") <= 3);
    }
    EXPECT_EQ(fx.StackCount("effect.poison_stack"), 3);
    EXPECT_NEAR(sb.Get(StatId::Armor), 70.0, 1e-9);  // 3 instâncias independentes
    // O mais antigo é substituído: a ordem de aplicação avança.
    EXPECT_TRUE(fx.Active()[0].applyOrder < fx.Active()[1].applyOrder);
    std::vector<EffectEvent> ev;
    for (int i = 0; i < 51; ++i) fx.Tick(0.1, lookup, sb, ev);
    EXPECT_EQ(fx.StackCount("effect.poison_stack"), 0);
    EXPECT_NEAR(sb.Get(StatId::Armor), 100.0, 1e-9);
}

TEST(effects_rf09_strongest_only_keeps_max) {
    const RulesConstants rules;
    EffectData e;
    e.id = "effect.guard_break";
    e.duration = 5.0;
    e.stackRule = StackRule::StrongestOnly;
    e.modifiers.push_back({StatId::Armor, ModKind::More, -0.2, 0, ""});
    StatBlock sb;
    sb.SetBase(StatId::Armor, 100);
    EffectContainer fx;
    EXPECT_TRUE(fx.Apply(e, "p", 1.0, TriggerKind::None, sb, rules));
    EXPECT_NEAR(sb.Get(StatId::Armor), 80.0, 1e-9);
    EXPECT_FALSE(fx.Apply(e, "p", 0.5, TriggerKind::None, sb, rules));  // mais fraco: ignorado
    EXPECT_NEAR(sb.Get(StatId::Armor), 80.0, 1e-9);
    EXPECT_TRUE(fx.Apply(e, "p", 2.0, TriggerKind::None, sb, rules));   // mais forte substitui
    EXPECT_NEAR(sb.Get(StatId::Armor), 60.0, 1e-9);
    EXPECT_EQ(fx.StackCount("effect.guard_break"), 1);
    std::vector<EffectEvent> ev;
    const auto lookup = Lookup({&e});
    fx.Tick(2.0, lookup, sb, ev);
    EXPECT_TRUE(fx.Apply(e, "p", 2.0, TriggerKind::None, sb, rules));   // empate renova a duração
    EXPECT_NEAR(fx.Active()[0].remaining, 5.0, 1e-12);
}

TEST(effects_dot_ticks_and_expiry_order) {
    const RulesConstants rules;
    EffectData burn;
    burn.id = "effect.burn";
    burn.duration = 4.0;
    burn.tickInterval = 1.0;
    burn.damagePerTick[static_cast<std::size_t>(Index(DamageType::Fire))] = 3.0;
    burn.tags = Mask(Tag::Fire);
    const auto lookup = Lookup({&burn});
    StatBlock sb;
    EffectContainer fx;
    fx.Apply(burn, "p", 2.0, TriggerKind::None, sb, rules);  // magnitude 2 => 6 por tick
    std::vector<EffectEvent> ev;
    for (int i = 0; i < 40; ++i) fx.Tick(0.1, lookup, sb, ev);
    int ticks = 0;
    for (const EffectEvent& e : ev) {
        if (e.kind == EffectEvent::Kind::DamageTick) {
            ++ticks;
            EXPECT_NEAR(e.damage[1], 6.0, 1e-9);
        }
    }
    EXPECT_EQ(ticks, 4);
    EXPECT_TRUE(ev.back().kind == EffectEvent::Kind::Expired);
    EXPECT_FALSE(fx.Has("effect.burn"));
}

TEST(effects_rf10_trigger_icd_and_chain_rule) {
    RulesConstants rules;  // trigger_icd_min = 0,25 s
    EffectData spark;
    spark.id = "effect.block_spark";
    spark.duration = 2.0;
    spark.trigger = TriggerKind::OnBlock;
    spark.modifiers.push_back({StatId::Damage, ModKind::Increased, 0.2, 0, ""});
    const auto lookup = Lookup({&spark});
    StatBlock sb;
    EffectContainer fx;
    // Dois gatilhos "ao bloquear" no mesmo instante disparam 1 vez (recarga interna).
    EXPECT_TRUE(fx.Apply(spark, "p", 1.0, TriggerKind::None, sb, rules));
    EXPECT_FALSE(fx.Apply(spark, "p", 1.0, TriggerKind::None, sb, rules));
    std::vector<EffectEvent> ev;
    fx.Tick(0.2, lookup, sb, ev);
    EXPECT_FALSE(fx.Apply(spark, "p", 1.0, TriggerKind::None, sb, rules));  // 0,2 < 0,25
    fx.Tick(0.1, lookup, sb, ev);
    EXPECT_TRUE(fx.Apply(spark, "p", 1.0, TriggerKind::None, sb, rules));   // 0,3 >= 0,25
    // Efeito disparado não dispara outro do mesmo TriggerKind na mesma cadeia.
    EffectContainer fx2;
    StatBlock sb2;
    EXPECT_FALSE(fx2.Apply(spark, "p", 1.0, TriggerKind::OnBlock, sb2, rules));
    EXPECT_FALSE(fx2.Has("effect.block_spark"));
    EXPECT_TRUE(fx2.Apply(spark, "p", 1.0, TriggerKind::OnHit, sb2, rules));  // gatilho de outro tipo é permitido
    // ICD declarado maior que o mínimo vale; menor que o mínimo sobe para 0,25 s.
    EffectData slowSpark = spark;
    slowSpark.id = "effect.slow_spark";
    slowSpark.internalCooldown = 1.0;
    const auto lk2 = Lookup({&slowSpark});
    EffectContainer fx3;
    StatBlock sb3;
    EXPECT_TRUE(fx3.Apply(slowSpark, "p", 1.0, TriggerKind::None, sb3, rules));
    for (int i = 0; i < 9; ++i) fx3.Tick(0.1, lk2, sb3, ev);
    EXPECT_FALSE(fx3.Apply(slowSpark, "p", 1.0, TriggerKind::None, sb3, rules));  // 0,9 s < 1 s
    fx3.Tick(0.1, lk2, sb3, ev);
    EXPECT_TRUE(fx3.Apply(slowSpark, "p", 1.0, TriggerKind::None, sb3, rules));
}

TEST(effects_rf10_no_loop_in_ten_thousand_ticks) {
    const RulesConstants rules;
    EffectData a;
    a.id = "effect.on_hit_a";
    a.duration = 1.0;
    a.trigger = TriggerKind::OnHit;
    const auto lookup = Lookup({&a});
    StatBlock sb;
    EffectContainer fx;
    std::vector<EffectEvent> ev;
    int applied = 0;
    for (int i = 0; i < 10000; ++i) {
        // Cada tick um golpe tenta disparar o efeito; o efeito disparado tenta disparar a si mesmo (mesmo tipo).
        if (fx.Apply(a, "p", 1.0, TriggerKind::None, sb, rules)) {
            ++applied;
            if (fx.Apply(a, "p", 1.0, TriggerKind::OnHit, sb, rules)) FAIL("cadeia do mesmo tipo passou");
        }
        fx.Tick(1.0 / 60.0, lookup, sb, ev);
    }
    // 10000 ticks de 1/60 s = 166,7 s; com recarga de 0,25 s no máximo ~667 disparos.
    EXPECT_TRUE(applied <= 700);
    EXPECT_TRUE(applied >= 600);
    EXPECT_TRUE(fx.StackCount("effect.on_hit_a") <= 1);
}

TEST(effects_clear_removes_mods) {
    const RulesConstants rules;
    const EffectData slow = Slow();
    StatBlock sb;
    EffectContainer fx;
    fx.Apply(slow, "p", 1.0, TriggerKind::None, sb, rules);
    fx.Clear(sb);
    EXPECT_FALSE(fx.Has("effect.slow"));
    EXPECT_NEAR(sb.Get(StatId::MoveSpeed), 1.0, 1e-12);
    EXPECT_TRUE(fx.Apply(slow, "p", 1.0, TriggerKind::None, sb, rules));
}

// ---------------------------------------------------------------------------
TEST(rng_known_sequences_are_stable) {
    // Valores gravados: mudar o gerador invalida saves com expedição em andamento.
    Pcg32 r(42, 54);
    const std::uint32_t expected[] = {0xa15c02b7u, 0x7b47f409u, 0xba1d3330u, 0x83d2f293u, 0xbfa4784bu, 0xcbed606eu};
    for (std::uint32_t e : expected) EXPECT_EQ(r.NextU32(), e);
    std::uint64_t s = 0;
    EXPECT_EQ(SplitMix64Next(s), 0xE220A8397B1DCDAFull);
    EXPECT_EQ(SplitMix64Next(s), 0x6E789E6AA1B965F4ull);
}

TEST(rng_streams_are_independent_and_reproducible) {
    Pcg32 a = Pcg32::ForStream(1234, RngStream::Combat, 7);
    Pcg32 b = Pcg32::ForStream(1234, RngStream::Combat, 7);
    Pcg32 c = Pcg32::ForStream(1234, RngStream::Loot, 7);
    Pcg32 d = Pcg32::ForStream(1234, RngStream::Combat, 8);
    Pcg32 e = Pcg32::ForStream(1235, RngStream::Combat, 7);
    int same = 0;
    for (int i = 0; i < 100; ++i) {
        const std::uint32_t x = a.NextU32();
        EXPECT_EQ(x, b.NextU32());
        if (x == c.NextU32()) ++same;
        if (x == d.NextU32()) ++same;
        if (x == e.NextU32()) ++same;
    }
    EXPECT_TRUE(same < 3);
}

TEST(rng_next_below_unbiased_and_in_range) {
    Pcg32 r(2024);
    const std::uint32_t bound = 6;
    std::array<int, 6> counts{};
    const int n = 600000;
    for (int i = 0; i < n; ++i) {
        const std::uint32_t v = r.NextBelow(bound);
        if (v >= bound) { FAIL("fora da faixa"); return; }
        ++counts[v];
    }
    for (int c : counts) EXPECT_NEAR(static_cast<double>(c) / n, 1.0 / 6.0, 0.004);
    EXPECT_EQ(r.NextBelow(0), static_cast<std::uint32_t>(0));
    for (int i = 0; i < 1000; ++i) {
        const std::int32_t v = r.RangeInt(-3, 3);
        if (v < -3 || v > 3) { FAIL("RangeInt fora da faixa"); return; }
    }
    EXPECT_EQ(r.RangeInt(5, 2), 5);
    for (int i = 0; i < 1000; ++i) {
        const double u = r.NextUnit();
        if (u < 0.0 || u >= 1.0) { FAIL("NextUnit fora de [0,1)"); return; }
    }
}

TEST(rng_chance_always_consumes_one_number) {
    Pcg32 a(5), b(5);
    a.Chance(0.0);
    a.Chance(1.0);
    a.Chance(0.5);
    b.NextU32(); b.NextU32(); b.NextU32();
    EXPECT_EQ(a.State(), b.State());
    Pcg32 z(1);
    for (int i = 0; i < 100; ++i) {
        if (z.Chance(0.0)) { FAIL("p=0 nunca"); return; }
        if (!z.Chance(1.0)) { FAIL("p=1 sempre"); return; }
    }
}
