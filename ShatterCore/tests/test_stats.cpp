// Atributos e modificadores — RF-01, RF-02, RF-03, RF-04, RF-05 e conversões de texto.
#include <random>

#include "test_util.h"

using namespace shatter;

TEST(stats_rf01_formula_257_4) {
    // base 100, planos +10 e +20, aumentados +20% e +30%, "mais" 10% e 20% => 130 * 1,5 * 1,1 * 1,2
    StatBlock sb;
    sb.SetBase(StatId::Life, 100);
    sb.AddModifier({StatId::Life, ModKind::Flat, 10, 0, "a"});
    sb.AddModifier({StatId::Life, ModKind::Flat, 20, 0, "b"});
    sb.AddModifier({StatId::Life, ModKind::Increased, 0.20, 0, "c"});
    sb.AddModifier({StatId::Life, ModKind::Increased, 0.30, 0, "d"});
    sb.AddModifier({StatId::Life, ModKind::More, 0.10, 0, "e"});
    sb.AddModifier({StatId::Life, ModKind::More, 0.20, 0, "f"});
    EXPECT_NEAR(sb.Get(StatId::Life), 257.4, 1e-6);
    const StatBlock::Breakdown b = sb.Explain(StatId::Life, 0);
    EXPECT_NEAR(b.sumFlat, 30.0, 1e-12);
    EXPECT_NEAR(b.sumIncreased, 0.5, 1e-12);
    EXPECT_NEAR(b.productMore, 1.32, 1e-12);
    EXPECT_NEAR(ComputeStatValue(100, 30, 0.5, 1.32), 257.4, 1e-6);
}

TEST(stats_rf02_tags_filter_modifiers) {
    StatBlock sb;
    const TagMask ironCut = Tag::Attack | Tag::Melee | Tag::Physical;
    const TagMask projectile = Tag::Attack | Tag::Projectile | Tag::Physical;
    sb.AddModifier({StatId::Damage, ModKind::Increased, 0.15, Mask(Tag::Projectile), "p"});
    EXPECT_NEAR(sb.ApplyTagged(StatId::Damage, ironCut, 100), 100.0, 1e-9);  // sem tag projétil: não altera
    EXPECT_NEAR(sb.ApplyTagged(StatId::Damage, projectile, 100), 115.0, 1e-9);
    sb.AddModifier({StatId::Damage, ModKind::Increased, 0.15, Mask(Tag::Melee), "m"});
    EXPECT_NEAR(sb.ApplyTagged(StatId::Damage, ironCut, 100), 115.0, 1e-9);
    // Todas as tags exigidas precisam estar presentes.
    sb.AddModifier({StatId::Damage, ModKind::More, 1.0, Tag::Melee | Tag::Fire, "mf"});
    EXPECT_NEAR(sb.ApplyTagged(StatId::Damage, ironCut, 100), 115.0, 1e-9);
    EXPECT_NEAR(sb.ApplyTagged(StatId::Damage, ironCut | Mask(Tag::Fire), 100), 230.0, 1e-9);
    // Get() sem tags ignora mods com tag exigida.
    sb.SetBase(StatId::Damage, 50);
    EXPECT_NEAR(sb.Get(StatId::Damage), 50.0, 1e-9);
}

TEST(stats_rf03_cache_and_dirty) {
    StatBlock sb;
    sb.SetBase(StatId::Life, 100);
    EXPECT_TRUE(sb.IsDirty());
    EXPECT_NEAR(sb.Get(StatId::Life), 100.0, 1e-12);
    EXPECT_FALSE(sb.IsDirty());
    const std::uint64_t rev = sb.Revision();
    EXPECT_NEAR(sb.Get(StatId::Life), 100.0, 1e-12);  // leitura repetida não recalcula nem muda a revisão
    EXPECT_FALSE(sb.IsDirty());
    EXPECT_EQ(sb.Revision(), rev);
    sb.AddModifier({StatId::Life, ModKind::Flat, 10, 0, "item:1"});  // trocar de item
    EXPECT_TRUE(sb.IsDirty());
    EXPECT_EQ(sb.Revision(), rev + 1);
    EXPECT_NEAR(sb.Get(StatId::Life), 110.0, 1e-12);
    EXPECT_FALSE(sb.IsDirty());
    EXPECT_EQ(sb.RemoveModifiersFrom("item:1"), static_cast<std::size_t>(1));
    EXPECT_TRUE(sb.IsDirty());
    EXPECT_NEAR(sb.Get(StatId::Life), 100.0, 1e-12);
    EXPECT_EQ(sb.RemoveModifiersFrom("item:1"), static_cast<std::size_t>(0));
    EXPECT_FALSE(sb.IsDirty());  // nada removido: nada invalidado
}

TEST(stats_rf04_never_negative_and_caps_in_ten_thousand_combinations) {
    std::mt19937_64 gen(42);  // só neste teste: gera combinações; o motor não usa <random>
    std::uniform_real_distribution<double> val(-5.0, 5.0);
    std::uniform_int_distribution<int> kind(0, 2), stat(0, kStatCount - 1), cnt(0, 6);
    for (int i = 0; i < 10000; ++i) {
        StatBlock sb;
        const StatId s = static_cast<StatId>(stat(gen));
        sb.SetBase(s, val(gen));
        const int n = cnt(gen);
        for (int k = 0; k < n; ++k) sb.AddModifier({s, static_cast<ModKind>(kind(gen)), val(gen), 0, "x"});
        const double v = sb.Get(s);
        if (!(v >= 0.0)) { FAIL("atributo negativo"); return; }
    }
    // Custo com redução de 200% é 0; recarga com redução de 99% fica em 0,1 s.
    EXPECT_NEAR(ComputeStatValue(10.0, 0.0, -2.0, 1.0), 0.0, 1e-12);
    RulesConstants rules;
    EXPECT_NEAR(EffectiveCooldown(5.0, 100.0, rules), 0.1, 1e-12);
    EXPECT_NEAR(EffectiveCooldown(5.0, 0.0, rules), 5.0, 1e-12);  // recuperação inválida => neutra
}

TEST(stats_base_neutral_values_and_order) {
    StatBlock sb;
    EXPECT_NEAR(sb.Get(StatId::DamageTaken), 1.0, 1e-12);
    EXPECT_NEAR(sb.Get(StatId::AttackSpeed), 1.0, 1e-12);
    EXPECT_NEAR(sb.Get(StatId::Life), 0.0, 1e-12);
    sb.AddModifier({StatId::Life, ModKind::Flat, 1, 0, "a"});
    sb.AddModifier({StatId::Life, ModKind::Flat, 2, 0, "b"});
    EXPECT_EQ(sb.Modifiers().size(), static_cast<std::size_t>(2));
    EXPECT_EQ(sb.Modifiers()[0].source, std::string("a"));  // ordem de inserção
    sb.ClearModifiers();
    EXPECT_TRUE(sb.Modifiers().empty());
}

TEST(stats_rf05_xp_curve) {
    ContentDB db;
    EXPECT_NEAR(db.XpToNextLevel(1), 100.0, 1e-9);
    EXPECT_NEAR(db.XpToNextLevel(2), 160.0, 1e-9);
    EXPECT_NEAR(db.XpToNextLevel(3), 269.7056274847714, 1e-6);  // 100 + 60 * 2^1,5
    EXPECT_NEAR(db.XpToNextLevel(5), 580.0, 1e-9);              // 100 + 60 * 4^1,5
    db.MutableRules().xpExponent = 2.0;
    EXPECT_NEAR(db.XpToNextLevel(4), 100.0 + 60.0 * 9.0, 1e-9);
}

TEST(types_parse_and_format) {
    TagMask m = 0;
    EXPECT_TRUE(ParseTagList("attack|melee|physical", m));
    EXPECT_EQ(m, static_cast<TagMask>(Tag::Attack | Tag::Melee | Tag::Physical));
    EXPECT_EQ(TagListToString(m), std::string("attack|melee|physical"));
    EXPECT_TRUE(ParseTagList("", m));
    EXPECT_EQ(m, static_cast<TagMask>(0));
    EXPECT_FALSE(ParseTagList("attack|banana", m));
    EXPECT_FALSE(ParseTagList("attack||melee", m));
    EXPECT_TRUE(IsValidContentId("skill.warrior.iron_cut"));
    EXPECT_FALSE(IsValidContentId("Skill.warrior"));
    EXPECT_FALSE(IsValidContentId("skill"));
    StatId s;
    for (int i = 0; i < kStatCount; ++i) {
        EXPECT_TRUE(ParseStatId(ToString(static_cast<StatId>(i)), s));
        EXPECT_EQ(static_cast<int>(s), i);
    }
    ItemSlot sl;
    for (int i = 0; i < kItemSlotCount; ++i) {
        EXPECT_TRUE(ParseItemSlot(ToString(static_cast<ItemSlot>(i)), sl));
        EXPECT_EQ(static_cast<int>(sl), i);
    }
    Rarity r;
    EXPECT_TRUE(ParseRarity("unique", r));
    EXPECT_ENUM_EQ(r, Rarity::Unique);
    DamageType d;
    EXPECT_TRUE(ParseDamageType("lightning", d));
    EXPECT_FALSE(ParseDamageType("holy", d));
}
