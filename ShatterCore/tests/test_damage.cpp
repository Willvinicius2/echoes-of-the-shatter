// ResolveHit — RF-06, RF-07 e cada passo da ordem de cálculo.
#include "test_util.h"

using namespace shatter;

namespace {

HitInput Basic(const StatBlock& atk, const StatBlock& def, TagMask tags, double phys, double fire = 0.0) {
    HitInput in;
    in.attacker = &atk;
    in.defender = &def;
    in.skillTags = tags;
    in.baseDamage[static_cast<std::size_t>(Index(DamageType::Physical))] = phys;
    in.baseDamage[static_cast<std::size_t>(Index(DamageType::Fire))] = fire;
    in.defenderLife = 1e9;
    return in;
}

const TagMask kMelee = Tag::Attack | Tag::Melee | Tag::Physical;

}  // namespace

TEST(damage_rf06_evasion_cap_70_percent_over_100k_attacks) {
    const RulesConstants rules;
    StatBlock atk, def;
    def.SetBase(StatId::EvasionChance, 0.9);
    Pcg32 rng(777);
    int evaded = 0;
    const int n = 100000;
    for (int i = 0; i < n; ++i) {
        const HitResult r = ResolveHit(Basic(atk, def, kMelee, 10), rules, rng);
        if (r.outcome == HitOutcome::Evaded) {
            ++evaded;
            if (r.landed || r.totalDamage != 0.0) { FAIL("evadido nao pode causar dano"); return; }
        }
    }
    EXPECT_NEAR(100.0 * evaded / n, 70.0, 0.5);
}

TEST(damage_rf06_spell_ignores_evasion) {
    const RulesConstants rules;
    StatBlock atk, def;
    def.SetBase(StatId::EvasionChance, 0.9);
    Pcg32 rng(5);
    for (int i = 0; i < 20000; ++i) {
        const HitResult r = ResolveHit(Basic(atk, def, Tag::Spell | Tag::Fire, 0, 10), rules, rng);
        if (r.outcome == HitOutcome::Evaded) { FAIL("feitico foi evadido"); return; }
    }
}

TEST(damage_rf06_block_cap_50_percent_and_mitigation) {
    RulesConstants rules;
    StatBlock atk, def;
    def.SetBase(StatId::BlockChance, 0.8);
    Pcg32 rng(99);
    int blocked = 0;
    const int n = 100000;
    for (int i = 0; i < n; ++i) {
        const HitResult r = ResolveHit(Basic(atk, def, kMelee, 10), rules, rng);
        if (r.outcome == HitOutcome::Blocked) {
            ++blocked;
            if (r.totalDamage != 0.0) { FAIL("bloqueio com block_mitigation=1 anula o golpe"); return; }
            if (!r.landed) { FAIL("bloqueado ainda conta como acertado"); return; }
        }
    }
    EXPECT_NEAR(100.0 * blocked / n, 50.0, 0.7);
    // Mitigação parcial (valor vem dos dados): bloqueio deixa passar a fração restante.
    rules.blockMitigation = 0.6;
    def.SetBase(StatId::BlockChance, 1.0);
    Pcg32 rng2(1);
    bool sawBlocked = false;
    for (int i = 0; i < 200; ++i) {
        const HitResult r = ResolveHit(Basic(atk, def, Tag::Spell | Tag::Physical, 100), rules, rng2);
        if (r.outcome == HitOutcome::Blocked) {
            sawBlocked = true;
            EXPECT_NEAR(r.afterMitigation[0], 40.0, 1e-9);
        }
    }
    EXPECT_TRUE(sawBlocked);
    // canBeBlocked = false nunca bloqueia.
    Pcg32 rng3(1);
    for (int i = 0; i < 200; ++i) {
        HitInput in = Basic(atk, def, kMelee, 10);
        in.canBeBlocked = false;
        if (ResolveHit(in, rules, rng3).outcome == HitOutcome::Blocked) { FAIL("bloqueou sem poder"); return; }
    }
}

TEST(damage_rf06_resist_cap_75_and_floor) {
    const RulesConstants rules;
    StatBlock atk, def;
    Pcg32 rng(3);
    def.SetBase(StatId::ResistFire, 1.0);  // 100% vira 75%
    HitResult r = ResolveHit(Basic(atk, def, Tag::Spell | Tag::Fire, 0, 100), rules, rng);
    EXPECT_NEAR(r.afterMitigation[1], 25.0, 1e-9);
    def.SetBase(StatId::ResistFire, 0.0);
    def.AddModifier({StatId::ResistFire, ModKind::Flat, -0.5, 0, "weak"});  // fraqueza real: dano x1,5
    r = ResolveHit(Basic(atk, def, Tag::Spell | Tag::Fire, 0, 100), rules, rng);
    EXPECT_NEAR(r.afterMitigation[1], 150.0, 1e-9);
    def.AddModifier({StatId::ResistFire, ModKind::Flat, -5.0, 0, "weaker"});  // piso -100%
    r = ResolveHit(Basic(atk, def, Tag::Spell | Tag::Fire, 0, 100), rules, rng);
    EXPECT_NEAR(r.afterMitigation[1], 200.0, 1e-9);
    EXPECT_NEAR(ClampResistance(0.9, rules), 0.75, 1e-12);
    EXPECT_NEAR(ClampResistance(-3.0, rules), -1.0, 1e-12);
}

TEST(damage_rf06_armor_only_physical_elemental_untouched) {
    const RulesConstants rules;
    StatBlock atk, def;
    def.SetBase(StatId::Armor, 500);
    Pcg32 rng(11);
    const HitResult r = ResolveHit(Basic(atk, def, Tag::Spell | Tag::Physical | Tag::Fire, 100, 100), rules, rng);
    EXPECT_NEAR(r.afterMitigation[0], 50.0, 1e-9);   // A=500, D=100 => reducao de 50%
    EXPECT_NEAR(r.afterMitigation[1], 100.0, 1e-9);  // fogo nao passa pela armadura
    EXPECT_NEAR(r.totalDamage, 150.0, 1e-9);
}

TEST(damage_rf06_crit_multiplier_base_150) {
    const RulesConstants rules;
    StatBlock atk, def;
    atk.SetBase(StatId::CritChance, 1.0);
    Pcg32 rng(2);
    HitResult r = ResolveHit(Basic(atk, def, kMelee, 100), rules, rng);
    EXPECT_TRUE(r.critical);
    EXPECT_NEAR(r.afterModifiers[0], 150.0, 1e-9);  // antes das defesas
    // Multiplicador de crítico modificado: base 1,5 + 0,5 plano = 2,0.
    atk.AddModifier({StatId::CritMultiplier, ModKind::Flat, 0.5, 0, "m"});
    r = ResolveHit(Basic(atk, def, kMelee, 100), rules, rng);
    EXPECT_NEAR(r.afterModifiers[0], 200.0, 1e-9);
    // Sem chance de crítico nunca crita.
    atk.SetBase(StatId::CritChance, 0.0);
    for (int i = 0; i < 1000; ++i) {
        if (ResolveHit(Basic(atk, def, kMelee, 100), rules, rng).critical) { FAIL("crit sem chance"); return; }
    }
}

TEST(damage_rf07_armor_monotonic_big_hits_reduced_less) {
    const RulesConstants rules;
    std::uint64_t s = 12345;
    for (int i = 0; i < 1000; ++i) {
        const double armor = 1.0 + static_cast<double>(SplitMix64Next(s) % 5000);
        const double small = 1.0 + static_cast<double>(SplitMix64Next(s) % 500);
        const double big = small * (1.5 + static_cast<double>(SplitMix64Next(s) % 20));
        const double rs = ArmorReduction(armor, small, rules), rb = ArmorReduction(armor, big, rules);
        // Monotônico; estritamente menor enquanto o teto de 90% não domina o golpe pequeno.
        if (!(rb <= rs) || (rs < rules.armorMaxReduction && !(rb < rs))) {
            FAIL("golpe maior deveria ser reduzido menos");
            return;
        }
    }
    EXPECT_NEAR(ArmorReduction(500, 100, rules), 0.5, 1e-12);
    EXPECT_NEAR(ArmorReduction(500, 1000, rules), 500.0 / 5500.0, 1e-12);
    EXPECT_NEAR(ArmorReduction(1e9, 1, rules), 0.9, 1e-12);  // teto de 90%
    EXPECT_NEAR(ArmorReduction(0, 100, rules), 0.0, 1e-12);
    EXPECT_NEAR(ArmorReduction(100, 0, rules), 0.0, 1e-12);
}

TEST(damage_always_three_rng_draws_except_dot) {
    const RulesConstants rules;
    StatBlock atk, def;
    const TagMask variants[] = {kMelee, Tag::Spell | Tag::Fire, Tag::Attack | Tag::Projectile};
    for (TagMask tags : variants) {
        Pcg32 rng(42), ref(42);
        ResolveHit(Basic(atk, def, tags, 10, 10), rules, rng);
        ref.NextU32(); ref.NextU32(); ref.NextU32();
        EXPECT_EQ(rng.State(), ref.State());
    }
    // Mesmo evadido ou com atributos extremos: 3 números.
    def.SetBase(StatId::EvasionChance, 1.0);
    def.SetBase(StatId::BlockChance, 1.0);
    atk.SetBase(StatId::CritChance, 1.0);
    Pcg32 rng(9), ref(9);
    ResolveHit(Basic(atk, def, kMelee, 10), rules, rng);
    ref.NextU32(); ref.NextU32(); ref.NextU32();
    EXPECT_EQ(rng.State(), ref.State());
    // DoT: nenhum número, nunca critica/evade/bloqueia.
    Pcg32 rngDot(9), refDot(9);
    HitInput in = Basic(atk, def, Mask(Tag::Fire), 0, 10);
    in.isDamageOverTime = true;
    const HitResult r = ResolveHit(in, rules, rngDot);
    EXPECT_EQ(rngDot.State(), refDot.State());
    EXPECT_FALSE(r.critical);
    EXPECT_ENUM_EQ(r.outcome, HitOutcome::Hit);
}

TEST(damage_damage_taken_barrier_and_kill) {
    const RulesConstants rules;
    StatBlock atk, def;
    def.AddModifier({StatId::DamageTaken, ModKind::More, -0.3, 0, "fx:effect.firm_stance"});
    Pcg32 rng(1);
    HitInput in = Basic(atk, def, Tag::Spell | Tag::Fire, 0, 100);
    in.defenderLife = 100;
    in.defenderBarrier = 30;
    HitResult r = ResolveHit(in, rules, rng);
    EXPECT_NEAR(r.totalDamage, 70.0, 1e-9);
    EXPECT_NEAR(r.absorbedByBarrier, 30.0, 1e-9);
    EXPECT_NEAR(r.lifeLost, 40.0, 1e-9);
    EXPECT_NEAR(r.defenderLifeAfter, 60.0, 1e-9);
    EXPECT_NEAR(r.defenderBarrierAfter, 0.0, 1e-9);
    EXPECT_FALSE(r.killed);
    in.defenderLife = 20;
    in.defenderBarrier = 0;
    r = ResolveHit(in, rules, rng);
    EXPECT_TRUE(r.killed);
    EXPECT_NEAR(r.defenderLifeAfter, 0.0, 1e-12);  // vida mínima 0
    EXPECT_NEAR(r.lifeLost, 20.0, 1e-9);
    in.defenderLife = 0;  // já morto: não "mata" de novo
    EXPECT_FALSE(ResolveHit(in, rules, rng).killed);
}

TEST(damage_modifiers_by_tag_and_coefficient) {
    const RulesConstants rules;
    StatBlock atk, def;
    atk.AddModifier({StatId::Damage, ModKind::Increased, 0.5, Mask(Tag::Fire), "fire"});
    atk.AddModifier({StatId::Damage, ModKind::Flat, 5, Mask(Tag::Physical), "flatphys"});
    Pcg32 rng(1);
    HitInput in = Basic(atk, def, Tag::Attack | Tag::Melee, 10, 10);
    in.coefficient = 2.0;
    const HitResult r = ResolveHit(in, rules, rng);
    EXPECT_NEAR(r.afterModifiers[0], (20.0 + 5.0), 1e-9);  // (10*2 + 5)
    EXPECT_NEAR(r.afterModifiers[1], 20.0 * 1.5, 1e-9);
    HitInput none;
    Pcg32 rng2(1);
    EXPECT_NEAR(ResolveHit(none, rules, rng2).totalDamage, 0.0, 1e-12);  // atacante/defensor nulos: sem efeito
}
