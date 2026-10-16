using System.Collections.Generic;
using Echoes.Interop;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    /// <summary>
    /// Stub provisório do motor de regras contra os critérios [SC] que ele porta do ShatterCore e os
    /// valores do próprio header C++ (rng.h). Quando a DLL existir, os mesmos casos viram testes do
    /// Interop.* sobre a implementação P/Invoke.
    /// </summary>
    [Category("Interop")]
    public sealed class StubRulesCoreTests
    {
        [Test]
        public void LoadsTheRealContentWithoutErrors()
        {
            using (var rules = TestWorld.LoadRules())
            {
                Assert.IsTrue(rules.IsLoaded);
                Assert.Greater(rules.ContentVersion, 0u);
                Assert.IsNotNull(rules.FindClass("class.warrior"));
                Assert.IsNotNull(rules.FindSkill("skill.warrior.iron_cut"));
                Assert.IsNotNull(rules.FindEnemy("enemy.crypt_guardian"));
                Assert.AreEqual(2, rules.Potions.Count);
            }
        }

        [Test]
        public void MissingDirectoryIsAnIoError()
        {
            using (var rules = new StubRulesCore())
            {
                var errors = new List<RulesError>();
                var status = rules.LoadContent("/does/not/exist", errors);
                Assert.AreEqual(RulesStatus.IoError, status);
                Assert.IsNotEmpty(errors);
                Assert.IsFalse(rules.IsLoaded);
            }
        }

        [Test]
        public void DodgeNumbersMatchTheDesign()
        {
            // RF-15 / docs/13 item 1: vêm de rules.csv (ou dos valores pendentes até as chaves existirem).
            using (var rules = TestWorld.LoadRules())
            {
                var c = rules.Combat;
                Assert.AreEqual(3, c.DodgeMaxCharges);
                Assert.AreEqual(1.5, c.DodgeRechargeSeconds, 1e-9);
                Assert.AreEqual(0.35, c.DodgeDurationSeconds, 1e-9);
                Assert.AreEqual(0.2, c.DodgeInvulnerableSeconds, 1e-9);
                Assert.AreEqual(1.0 / 60.0, c.FixedStep, 1e-12);
            }
        }

        [Test]
        public void Pcg32MatchesTheCppHeader()
        {
            // Valores gerados compilando ShatterCore/include/shatter/rng.h com g++ (Pcg32::ForStream).
            var a = StubPcg32.ForStream(12345UL, RngStream.Combat, 0);
            Assert.AreEqual(4676505128741286108UL, a.State);
            var expected = new uint[] { 1461504787u, 1574462682u, 3554518833u, 3153681334u, 492636793u };
            for (var i = 0; i < expected.Length; i++) Assert.AreEqual(expected[i], StubPcg32.NextU32(ref a), $"u32[{i}]");

            var loot = StubPcg32.ForStream(12345UL, RngStream.Loot, 7);
            Assert.AreEqual(2995466130u, StubPcg32.NextU32(ref loot));
            Assert.AreEqual(963957577u, StubPcg32.NextU32(ref loot));
            Assert.AreEqual(4148443666u, StubPcg32.NextU32(ref loot));

            Assert.AreEqual(2126950807486867704UL, StubPcg32.DeriveSeed(42UL, RngStream.Events, 3));

            var c = StubPcg32.ForStream(999UL, RngStream.Combat, 1);
            Assert.AreEqual(0.90025907754898071, StubPcg32.NextUnit(ref c), 0.0);
            Assert.AreEqual(0u, StubPcg32.NextBelow(ref c, 10));

            var d = StubPcg32.CreateDefault();
            Assert.AreEqual(465482994u, StubPcg32.NextU32(ref d));
        }

        [Test]
        public void StatFormulaIs2574()
        {
            // RF-01: base 100, planos +10 e +20, aumentados +20% e +30%, "mais" 10% e 20% = 257,4.
            var block = new StubStatBlock();
            block.SetBase(StatId.Life, 100.0);
            block.AddModifier(new StubModifier { Stat = StatId.Life, Kind = StubModKind.Flat, Value = 10 });
            block.AddModifier(new StubModifier { Stat = StatId.Life, Kind = StubModKind.Flat, Value = 20 });
            block.AddModifier(new StubModifier { Stat = StatId.Life, Kind = StubModKind.Increased, Value = 0.2 });
            block.AddModifier(new StubModifier { Stat = StatId.Life, Kind = StubModKind.Increased, Value = 0.3 });
            block.AddModifier(new StubModifier { Stat = StatId.Life, Kind = StubModKind.More, Value = 0.1 });
            block.AddModifier(new StubModifier { Stat = StatId.Life, Kind = StubModKind.More, Value = 0.2 });
            Assert.AreEqual(257.4, block.Get(StatId.Life), 1e-6);
        }

        [Test]
        public void TaggedModifierOnlyAppliesWithAllTags()
        {
            // RF-02: "+15% projétil" não altera o Corte de Ferro; "+15% corpo a corpo" altera.
            var block = new StubStatBlock();
            block.AddModifier(new StubModifier { Stat = StatId.Damage, Kind = StubModKind.Increased, Value = 0.15, RequiredTags = SkillTags.Projectile });
            var ironCut = SkillTags.Attack | SkillTags.Melee | SkillTags.Physical;
            Assert.AreEqual(100.0, block.ApplyTagged(StatId.Damage, ironCut, 100.0), 1e-9);
            block.AddModifier(new StubModifier { Stat = StatId.Damage, Kind = StubModKind.Increased, Value = 0.15, RequiredTags = SkillTags.Melee });
            Assert.AreEqual(115.0, block.ApplyTagged(StatId.Damage, ironCut, 100.0), 1e-9);
        }

        [Test]
        public void RepeatedReadsDoNotRecompute()
        {
            // RF-03: leitura repetida usa o cache; mudar algo recalcula.
            var block = new StubStatBlock();
            block.SetBase(StatId.Armor, 20.0);
            block.Get(StatId.Armor);
            var count = block.RecomputeCount;
            block.Get(StatId.Armor);
            Assert.AreEqual(count, block.RecomputeCount);
            block.AddModifier(new StubModifier { Stat = StatId.Armor, Kind = StubModKind.Flat, Value = 8 });
            Assert.AreEqual(28.0, block.Get(StatId.Armor), 1e-9);
            Assert.AreEqual(count + 1, block.RecomputeCount);
        }

        [Test]
        public void ResolveHitAlwaysConsumesThreeNumbers()
        {
            using (var rules = TestWorld.LoadRules())
            {
                var attacker = rules.CreateEnemyStats("enemy.hollow_sentinel", 3);
                var defender = rules.CreateEnemyStats("enemy.stone_herald", 3);
                var request = new HitRequest
                {
                    Attacker = attacker, Defender = defender, SkillTags = SkillTags.Attack | SkillTags.Physical,
                    BaseDamage = new DamageByType { Physical = 10 }, Coefficient = 1.0, CanBeBlocked = true,
                    DefenderLife = 100, DefenderBarrier = 0,
                };
                var rng = rules.CreateRng(7UL, RngStream.Combat, 0);
                var copy = rng;
                rules.ResolveHit(in request, ref rng);
                StubPcg32.NextU32(ref copy);
                StubPcg32.NextU32(ref copy);
                StubPcg32.NextU32(ref copy);
                Assert.AreEqual(copy.State, rng.State, "crítico, evasão e bloqueio: sempre 3 números");

                request.IsDamageOverTime = true;
                var before = rng;
                rules.ResolveHit(in request, ref rng);
                Assert.AreEqual(before.State, rng.State, "DoT não consome RNG");
            }
        }

        [Test]
        public void ArmorReducesSmallHitsMoreThanBigOnes()
        {
            // RF-07 e o exemplo da seção 11 do 04: A = 500 → golpe de 100 perde 50%, golpe de 1000 perde ~9%.
            var rules = new StubRulesConstants { ArmorDamageFactor = 5.0, ArmorMaxReduction = 0.9 };
            Assert.AreEqual(0.5, StubDamage.ArmorReduction(500, 100, rules), 1e-9);
            Assert.AreEqual(500.0 / 5500.0, StubDamage.ArmorReduction(500, 1000, rules), 1e-9);
            for (var d = 1; d < 1000; d++)
                Assert.GreaterOrEqual(StubDamage.ArmorReduction(300, d, rules), StubDamage.ArmorReduction(300, d + 1, rules));
        }

        [Test]
        public void CritMultipliesByTheBaseMultiplier()
        {
            // RF-06: golpe de 100 crítico = 150 antes das defesas.
            using (var rules = TestWorld.LoadRules())
            {
                var attacker = new StubStatBlock();
                attacker.SetBase(StatId.CritChance, 1.0);
                var defender = new StubStatBlock();
                defender.SetBase(StatId.Life, 1000);
                var request = new HitRequest
                {
                    Attacker = attacker, Defender = defender, SkillTags = SkillTags.Spell | SkillTags.Fire,
                    BaseDamage = new DamageByType { Fire = 100 }, Coefficient = 1.0, CanBeBlocked = false,
                    DefenderLife = 1000,
                };
                var rng = rules.CreateRng(1UL, RngStream.Combat, 0);
                var result = rules.ResolveHit(in request, ref rng);
                Assert.IsTrue(result.Critical);
                Assert.AreEqual(150.0, result.AfterModifiers.Fire, 1e-9);
            }
        }

        [Test]
        public void EvasionIsCappedAt70Percent()
        {
            // RF-06: alvo com 90% de evasão evade 70% ± 0,5 (amostra de 100 mil ataques).
            using (var rules = TestWorld.LoadRules())
            {
                var attacker = new StubStatBlock();
                var defender = new StubStatBlock();
                defender.SetBase(StatId.EvasionChance, 0.9);
                var request = new HitRequest
                {
                    Attacker = attacker, Defender = defender, SkillTags = SkillTags.Attack | SkillTags.Physical,
                    BaseDamage = new DamageByType { Physical = 10 }, Coefficient = 1.0, CanBeBlocked = true,
                    DefenderLife = 1e9,
                };
                var rng = rules.CreateRng(99UL, RngStream.Combat, 0);
                var evaded = 0;
                const int samples = 100000;
                for (var i = 0; i < samples; i++)
                {
                    if (rules.ResolveHit(in request, ref rng).Outcome == HitOutcome.Evaded) evaded++;
                }
                Assert.AreEqual(0.70, evaded / (double)samples, 0.005);
            }
        }

        [Test]
        public void StunZeroesActionAndRespectsImmunity()
        {
            using (var rules = TestWorld.LoadRules())
            {
                var common = rules.FindEnemy("enemy.hollow_sentinel");
                var stats = rules.CreateEnemyStats(common.Id, 3);
                var effects = rules.CreateEffectSet(stats, common);
                Assert.IsTrue(effects.Apply("effect.stun", 1.0, "test"));
                Assert.IsFalse(rules.CanAct(stats));
                Assert.IsFalse(rules.CanMove(stats));
                for (var i = 0; i < 60; i++) effects.Tick(1.0 / 60.0, null);
                Assert.IsTrue(rules.CanAct(stats), "0,8 s depois o atordoamento acabou");

                var herald = rules.FindEnemy("enemy.stone_herald");
                var heraldStats = rules.CreateEnemyStats(herald.Id, 3);
                var heraldEffects = rules.CreateEffectSet(heraldStats, herald);
                Assert.IsFalse(heraldEffects.Apply("effect.stun", 1.0, "test"), "constructo é imune (docs/13, item 3)");
                Assert.IsTrue(rules.CanAct(heraldStats));
            }
        }

        [Test]
        public void GuardBreakStacksUpToThree()
        {
            // RF-08/09: acumular até 3 nunca passa de 3.
            using (var rules = TestWorld.LoadRules())
            {
                var stats = rules.CreateEnemyStats("enemy.stone_herald", 3);
                var effects = rules.CreateEffectSet(stats, rules.FindEnemy("enemy.stone_herald"));
                for (var i = 0; i < 5; i++) effects.Apply("effect.guard_break", 1.0, "test");
                Assert.AreEqual(3, effects.StackCount("effect.guard_break"));
                Assert.AreEqual(1.3, stats.Get(StatId.DamageTaken), 1e-9);
            }
        }

        [Test]
        public void EffectExpiresOnTheExactFixedStep()
        {
            // Tolerância de tempo do core (kTimeEps): 8 s a 1/60 = 480 passos, nem um a mais.
            using (var rules = TestWorld.LoadRules())
            {
                var stats = rules.CreateEnemyStats("enemy.stone_herald", 3);
                var effects = rules.CreateEffectSet(stats, rules.FindEnemy("enemy.stone_herald"));
                effects.Apply("effect.guard_break", 1.0, "test");
                for (var i = 0; i < 479; i++) effects.Tick(1.0 / 60.0, null);
                Assert.AreEqual(1, effects.StackCount("effect.guard_break"));
                effects.Tick(1.0 / 60.0, null);
                Assert.AreEqual(0, effects.StackCount("effect.guard_break"));
                Assert.AreEqual(1.0, stats.Get(StatId.DamageTaken), 1e-12, "mods saem junto com o efeito");
            }
        }

        [Test]
        public void NegativeResistanceReachesTheFloor()
        {
            // RawResist de src/damage.cpp: fraqueza não para no zero do Get; vai até resist_floor (-1).
            using (var rules = TestWorld.LoadRules())
            {
                var attacker = new StubStatBlock();
                var defender = new StubStatBlock();
                defender.SetBase(StatId.ResistFire, -2.0);
                var request = new HitRequest
                {
                    Attacker = attacker, Defender = defender, SkillTags = SkillTags.Spell | SkillTags.Fire,
                    BaseDamage = new DamageByType { Fire = 100 }, Coefficient = 1.0, DefenderLife = 1000,
                };
                var rng = rules.CreateRng(3UL, RngStream.Combat, 0);
                var result = rules.ResolveHit(in request, ref rng);
                Assert.AreEqual(200.0, result.AfterMitigation.Fire, 1e-9);
            }
        }

        [Test]
        public void SameSeedSameSequenceOfHits()
        {
            // Determinismo do stub: mesma seed + mesmos CSV = mesmos golpes.
            Assert.AreEqual(RunFight(2024UL), RunFight(2024UL));
            Assert.AreNotEqual(RunFight(2024UL), RunFight(2025UL));
        }

        static string RunFight(ulong seed)
        {
            using (var rules = TestWorld.LoadRules())
            {
                var attacker = rules.CreateHeroStats(new HeroBuild("class.warrior", 5, new[] { "item_base.iron_sword" }));
                var defender = rules.CreateEnemyStats("enemy.hollow_sentinel", 3);
                var rng = rules.CreateRng(seed, RngStream.Combat, 0);
                var sb = new System.Text.StringBuilder();
                for (var i = 0; i < 200; i++)
                {
                    var request = new HitRequest
                    {
                        Attacker = attacker, Defender = defender, SkillTags = SkillTags.Attack | SkillTags.Melee | SkillTags.Physical,
                        BaseDamage = new DamageByType { Physical = 9 }, Coefficient = 1.0, CanBeBlocked = true, DefenderLife = 1e6,
                    };
                    var r = rules.ResolveHit(in request, ref rng);
                    sb.Append(r.Critical ? 'C' : '.');
                }
                return sb.ToString();
            }
        }
    }
}
