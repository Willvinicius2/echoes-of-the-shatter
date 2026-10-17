using System;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;
using Echoes.Gameplay;
using Echoes.Interop;
using Echoes.Interop.Native;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    /// <summary>
    /// A DLL nativa do ShatterCore (P/Invoke) contra o stub em C#: os mesmos cenarios rodam nos dois e o
    /// golpe tem de dar o mesmo dano com a mesma seed (docs/04_arquitetura.md, secoes 9.7 e 13.2).
    /// Se a DLL nao carregar (ausente, ponteiro do Git LFS), so <see cref="NativeLibraryLoads"/> falha;
    /// os demais ficam ignorados com o motivo.
    /// </summary>
    [Category("Interop")]
    public sealed class NativeRulesCoreTests
    {
        const double Tolerance = 1e-9;
        const string Sentinel = "enemy.hollow_sentinel";
        const string Sword = "item_base.iron_sword";

        static readonly string[] EnemyIds =
        {
            "enemy.hollow_sentinel", "enemy.ash_hound", "enemy.stone_herald", "enemy.ghost_archer",
            "enemy.shielded_sentinel", "enemy.swift_ash_hound", "enemy.crypt_guardian",
        };

        static NativeRulesCore LoadNative()
        {
            if (!NativeRulesCore.TryCreate(out var core, out var reason))
                Assert.Ignore("shattercore.dll nao carregou: " + reason);
            var errors = new List<RulesError>();
            var status = core.LoadContent(TestWorld.DataDirectory, errors);
            Assert.AreEqual(RulesStatus.Ok, status, "CSV nao carregou no nativo: " + string.Join("\n", errors));
            return core;
        }

        // ---------------------------------------------------------------------------------------------
        // Interop.* (docs/04, secao 9.7)
        // ---------------------------------------------------------------------------------------------

        [Test]
        public void NativeLibraryLoads()
        {
            var ok = NativeRulesCore.TryCreate(out var core, out var reason);
            if (!ok)
            {
                var importer = UnityEditor.AssetImporter.GetAtPath("Assets/Plugins/x86_64/shattercore.dll") as UnityEditor.PluginImporter;
                reason += importer == null
                    ? " | PluginImporter: nenhum em Assets/Plugins/x86_64/shattercore.dll"
                    : $" | PluginImporter: editor={importer.GetCompatibleWithEditor()} win64={importer.GetCompatibleWithPlatform(UnityEditor.BuildTarget.StandaloneWindows64)} any={importer.GetCompatibleWithAnyPlatform()} preload={importer.isPreloaded}";
                reason += " | cwd=" + Directory.GetCurrentDirectory();
            }
            Assert.IsTrue(ok, reason);
            using (core)
            {
                Assert.AreEqual(1u, core.ApiVersion);
                Assert.AreEqual(NativeRulesCore.Name, core.ImplementationName);
                Assert.IsFalse(core.IsProvisional);
            }
        }

        [Test]
        public void PluginImporterIsWindowsX64Only()
        {
            // docs/04, secao 9.3: Any Platform desligado, so Windows x64 (jogo e Editor), carregada na inicializacao.
            var importer = UnityEditor.AssetImporter.GetAtPath("Assets/Plugins/x86_64/shattercore.dll") as UnityEditor.PluginImporter;
            Assert.IsNotNull(importer, "a DLL precisa estar em Assets/Plugins/x86_64");
            Assert.IsFalse(importer.GetCompatibleWithAnyPlatform(), "Any Platform ligado");
            Assert.IsTrue(importer.GetCompatibleWithEditor(), "Editor");
            Assert.IsTrue(importer.GetCompatibleWithPlatform(UnityEditor.BuildTarget.StandaloneWindows64), "Windows x64");
            Assert.IsFalse(importer.GetCompatibleWithPlatform(UnityEditor.BuildTarget.StandaloneLinux64), "Linux");
            Assert.IsFalse(importer.GetCompatibleWithPlatform(UnityEditor.BuildTarget.StandaloneOSX), "macOS");
            Assert.IsTrue(importer.isPreloaded, "Load on startup");
        }

        [Test]
        public void VersionMatchesSource()
        {
            // Interop.VersionMatchesSource: shatter_api_version() da DLL == SHATTER_C_API_VERSION do header versionado.
            var header = FindHeader();
            var match = Regex.Match(File.ReadAllText(header), @"#define\s+SHATTER_C_API_VERSION\s+(\d+)u?");
            Assert.IsTrue(match.Success, "SHATTER_C_API_VERSION nao encontrado em " + header);
            var expected = uint.Parse(match.Groups[1].Value);
            using (var core = LoadNative())
            {
                Assert.AreEqual(expected, core.ApiVersion, "a DLL em Assets/Plugins esta desatualizada em relacao ao header");
            }
        }

        [Test]
        public void LayoutMatchesTheNativeStructs()
        {
            LoadNative().Dispose(); // garante a DLL; o TryCreate ja conferiu o layout
            Assert.IsTrue(NativeLayout.Check(out var message), message);
            Assert.AreEqual(82, NativeLayout.Build().Length);
        }

        [Test]
        public void LoadsTheRealContentLikeTheStub()
        {
            using (var native = LoadNative())
            using (var stub = TestWorld.LoadRules())
            {
                Assert.IsTrue(native.IsLoaded);
                Assert.Greater(native.ContentVersion, 0u);
                Assert.AreEqual(stub.ContentVersion, native.ContentVersion);
                Assert.AreEqual(stub.Combat.FixedStep, native.Combat.FixedStep, 1e-12);
                Assert.AreEqual(stub.Combat.MinCooldown, native.Combat.MinCooldown, 1e-12);
                Assert.IsNotNull(native.FindSkill("skill.warrior.iron_cut"));
            }
        }

        [Test]
        public void MissingDirectoryIsAnIoError()
        {
            if (!NativeRulesCore.TryCreate(out var core, out var reason)) Assert.Ignore(reason);
            using (core)
            {
                var errors = new List<RulesError>();
                var status = core.LoadContent(Path.Combine(Path.GetTempPath(), "echoes-does-not-exist-" + Guid.NewGuid().ToString("N")), errors);
                Assert.AreEqual(RulesStatus.IoError, status);
                Assert.IsNotEmpty(errors);
                Assert.IsFalse(core.IsLoaded);
            }
        }

        [Test]
        public void EmptyDirectoryArgumentIsInvalid()
        {
            if (!NativeRulesCore.TryCreate(out var core, out var reason)) Assert.Ignore(reason);
            using (core)
            {
                var errors = new List<RulesError>();
                Assert.AreEqual(RulesStatus.InvalidArgument, core.LoadContent(string.Empty, errors));
            }
        }

        [Test]
        public void InvalidContentReportsTheNativeErrorList()
        {
            // Copia o conteudo e quebra uma chave estrangeira: o banco devolve CONTENT_INVALID e a lista de erros em JSON.
            var dir = Path.Combine(Path.GetTempPath(), "echoes-badcontent-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(dir);
            try
            {
                foreach (var file in Directory.GetFiles(TestWorld.DataDirectory, "*.csv"))
                    File.Copy(file, Path.Combine(dir, Path.GetFileName(file)));
                var enemies = Path.Combine(dir, "enemy_attacks.csv");
                File.WriteAllText(enemies, File.ReadAllText(enemies).Replace("enemy.hollow_sentinel", "enemy.nobody_here"));

                if (!NativeRulesCore.TryCreate(out var core, out var reason)) Assert.Ignore(reason);
                using (core)
                {
                    var errors = new List<RulesError>();
                    var status = core.LoadContent(dir, errors);
                    Assert.AreEqual(RulesStatus.ContentInvalid, status);
                    Assert.IsNotEmpty(errors);
                    Assert.IsFalse(core.IsLoaded);
                    StringAssert.Contains("enemy_attacks", errors[0].Table);
                }
            }
            finally
            {
                Directory.Delete(dir, true);
            }
        }

        [Test]
        public void TwoCallBufferPatternRetriesWithTheNeededSize()
        {
            using (var native = LoadNative())
            {
                // Capacidade de 4 bytes: a 1a chamada devolve BUFFER_TOO_SMALL com o tamanho, a 2a traz o JSON inteiro.
                var small = native.LookupJson("skill.warrior.iron_cut", 4);
                var big = native.LookupJson("skill.warrior.iron_cut", 4096);
                Assert.IsNotNull(small);
                Assert.Greater(small.Length, 4);
                Assert.AreEqual(big, small);
                StringAssert.Contains("skill.warrior.iron_cut", small);
                Assert.IsNull(native.LookupJson("skill.nobody.nothing"), "ID que nao existe: NOT_FOUND vira nulo");
            }
        }

        // ---------------------------------------------------------------------------------------------
        // Paridade nativo x stub (mesmos cenarios nos dois)
        // ---------------------------------------------------------------------------------------------

        [Test]
        public void RngStreamsMatch()
        {
            using (var native = LoadNative())
            using (var stub = TestWorld.LoadRules())
            {
                foreach (var seed in new ulong[] { 0, 1, 12345, 424242, ulong.MaxValue })
                {
                    foreach (var stream in new[] { RngStream.Combat, RngStream.Loot, RngStream.Events })
                    {
                        var a = native.CreateRng(seed, stream, 7);
                        var b = stub.CreateRng(seed, stream, 7);
                        Assert.AreEqual(b.State, a.State, $"seed {seed} stream {stream}");
                        Assert.AreEqual(b.Increment, a.Increment, $"seed {seed} stream {stream}");
                    }
                }
            }
        }

        [Test]
        public void HeroStatsMatch()
        {
            using (var native = LoadNative())
            using (var stub = TestWorld.LoadRules())
            {
                foreach (var level in new[] { 1, 5, 12 })
                {
                    var build = new HeroBuild("class.warrior", level, new[] { Sword });
                    using (var a = native.CreateHeroStats(in build))
                    using (var b = stub.CreateHeroStats(in build))
                    {
                        AssertStatsEqual(b, a, $"heroi nivel {level}", skipMoveSpeed: true);
                    }
                }
            }
        }

        [Test]
        public void EnemyStatsMatch()
        {
            using (var native = LoadNative())
            using (var stub = TestWorld.LoadRules())
            {
                foreach (var id in EnemyIds)
                {
                    foreach (var level in new[] { 1, 3, 10 })
                    {
                        using (var a = native.CreateEnemyStats(id, level))
                        using (var b = stub.CreateEnemyStats(id, level))
                        {
                            AssertStatsEqual(b, a, $"{id} nivel {level}");
                        }
                    }
                }
            }
        }

        [Test]
        public void UnknownIdsThrowArgumentException()
        {
            using (var native = LoadNative())
            {
                Assert.Throws<ArgumentException>(() => native.CreateEnemyStats("enemy.nobody", 1));
                var bad = new HeroBuild("class.nobody", 1, null);
                Assert.Throws<ArgumentException>(() => native.CreateHeroStats(in bad));
                var badItem = new HeroBuild("class.warrior", 1, new[] { "item_base.nothing" });
                Assert.Throws<ArgumentException>(() => native.CreateHeroStats(in badItem));
            }
        }

        [Test]
        public void HeroHitsOnTheSentinelMatchWithTheSameSeed()
        {
            // O golpe do heroi (Corte de Ferro) contra a Sentinela, 1000 vezes, com a mesma seed nos dois motores.
            using (var native = LoadNative())
            using (var stub = TestWorld.LoadRules())
            {
                var hero = new HeroBuild("class.warrior", 5, new[] { Sword });
                using (var nAtk = native.CreateHeroStats(in hero))
                using (var nDef = native.CreateEnemyStats(Sentinel, 3))
                using (var sAtk = stub.CreateHeroStats(in hero))
                using (var sDef = stub.CreateEnemyStats(Sentinel, 3))
                {
                    var skill = stub.FindSkill("skill.warrior.iron_cut");
                    var weapon = stub.FindItemBase(Sword);
                    var rngN = native.CreateRng(TestWorld.Seed, RngStream.Combat, 0);
                    var rngS = stub.CreateRng(TestWorld.Seed, RngStream.Combat, 0);
                    var crits = 0;
                    var evaded = 0;
                    double total = 0;
                    for (var i = 0; i < 1000; i++)
                    {
                        var life = 150.0 + i % 50;
                        var barrier = i % 5 == 0 ? 10.0 : 0.0;
                        var dot = i % 7 == 0;
                        var rn = Request(nAtk, nDef, skill, stub.GetSkillBaseDamage(skill, weapon), life, barrier, dot);
                        var rs = Request(sAtk, sDef, skill, stub.GetSkillBaseDamage(skill, weapon), life, barrier, dot);
                        var a = native.ResolveHit(in rn, ref rngN);
                        var b = stub.ResolveHit(in rs, ref rngS);
                        AssertHitsEqual(b, a, i);
                        Assert.AreEqual(rngS.State, rngN.State, $"estado do RNG apos o golpe {i}");
                        if (a.Critical) crits++;
                        if (a.Outcome == HitOutcome.Evaded) evaded++;
                        total += a.TotalDamage;
                    }
                    Assert.Greater(total, 0.0);
                    Assert.Greater(crits, 0, "a seed deveria produzir ao menos um critico em 1000 golpes");
                    TestContext.WriteLine($"1000 golpes: dano total {total:R}, criticos {crits}, evasoes {evaded}");
                }
            }
        }

        [Test]
        public void EnemyHitsOnTheHeroMatchWithTheSameSeed()
        {
            using (var native = LoadNative())
            using (var stub = TestWorld.LoadRules())
            {
                var hero = new HeroBuild("class.warrior", 5, new[] { Sword });
                foreach (var enemyId in new[] { Sentinel, "enemy.stone_herald", "enemy.crypt_guardian" })
                {
                    using (var nDef = native.CreateHeroStats(in hero))
                    using (var nAtk = native.CreateEnemyStats(enemyId, 3))
                    using (var sDef = stub.CreateHeroStats(in hero))
                    using (var sAtk = stub.CreateEnemyStats(enemyId, 3))
                    {
                        var rngN = native.CreateRng(99, RngStream.Combat, 1);
                        var rngS = stub.CreateRng(99, RngStream.Combat, 1);
                        for (var i = 0; i < 300; i++)
                        {
                            var damage = new DamageByType { Physical = 12 + i % 9, Fire = i % 4 == 0 ? 6 : 0, Cold = i % 6 == 0 ? 5 : 0 };
                            var rn = new HitRequest
                            {
                                Attacker = nAtk, Defender = nDef, SkillTags = SkillTags.Attack | SkillTags.Melee | SkillTags.Physical,
                                BaseDamage = damage, Coefficient = 1.0, CanBeBlocked = true, DefenderLife = 100, DefenderBarrier = 0,
                            };
                            var rs = rn;
                            rs.Attacker = sAtk;
                            rs.Defender = sDef;
                            AssertHitsEqual(stub.ResolveHit(in rs, ref rngS), native.ResolveHit(in rn, ref rngN), i, enemyId);
                        }
                    }
                }
            }
        }

        [Test]
        public void EffectiveCooldownMatches()
        {
            using (var native = LoadNative())
            using (var stub = TestWorld.LoadRules())
            {
                var hero = new HeroBuild("class.warrior", 5, new[] { Sword });
                using (var a = native.CreateHeroStats(in hero))
                using (var b = stub.CreateHeroStats(in hero))
                {
                    foreach (var id in new[] { "skill.warrior.iron_cut", "skill.warrior.charge", "skill.warrior.stone_rift", "skill.warrior.shield_bash" })
                    {
                        var skill = stub.FindSkill(id);
                        Assert.AreEqual(stub.GetEffectiveCooldown(b, skill), native.GetEffectiveCooldown(a, skill), Tolerance, id);
                    }
                }
            }
        }

        [Test]
        public void EffectsStackExpireAndHonorStunImmunityLikeTheStub()
        {
            using (var native = LoadNative())
            using (var stub = TestWorld.LoadRules())
            {
                foreach (var enemyId in new[] { Sentinel, "enemy.shielded_sentinel", "enemy.crypt_guardian" })
                {
                    var info = stub.FindEnemy(enemyId);
                    using (var nStats = native.CreateEnemyStats(enemyId, 3))
                    using (var sStats = stub.CreateEnemyStats(enemyId, 3))
                    using (var nFx = native.CreateEffectSet(nStats, info))
                    using (var sFx = stub.CreateEffectSet(sStats, info))
                    {
                        // Guarda Quebrada no limite de acumulos vira stagger e consome os acumulos SO no core (alvo imune ao stun):
                        // a paridade vale so para o alvo comum, ate o stub ganhar a regra (ou sair).
                        if (!info.IsElite && !info.IsBoss)
                        {
                            for (var i = 0; i < 2; i++)
                                Assert.AreEqual(sFx.Apply("effect.guard_break", 1.0, "hero"), nFx.Apply("effect.guard_break", 1.0, "hero"), $"{enemyId} guard_break {i}");
                            Assert.AreEqual(sFx.StackCount("effect.guard_break"), nFx.StackCount("effect.guard_break"), enemyId);
                            Assert.AreEqual(sStats.Get(StatId.DamageTaken), nStats.Get(StatId.DamageTaken), Tolerance, enemyId);
                        }

                        Assert.AreEqual(sFx.Apply("effect.stun", 1.0, "hero"), nFx.Apply("effect.stun", 1.0, "hero"), enemyId + " stun");
                        Assert.AreEqual(sFx.ActiveCount, nFx.ActiveCount, enemyId);
                        Assert.AreEqual(sStats.Get(StatId.MoveSpeed), nStats.Get(StatId.MoveSpeed), Tolerance, enemyId + " stun move speed");
                        Assert.IsFalse(nFx.Apply("effect.nothing", 1.0, "hero"), "efeito inexistente");

                        var step = stub.Combat.FixedStep;
                        var nEvents = new List<EffectTickEvent>();
                        var sEvents = new List<EffectTickEvent>();
                        for (var t = 0; t < 600; t++)
                        {
                            nFx.Tick(step, nEvents);
                            sFx.Tick(step, sEvents);
                        }
                        Assert.AreEqual(sEvents.Count, nEvents.Count, enemyId + " eventos");
                        for (var i = 0; i < sEvents.Count; i++)
                        {
                            Assert.AreEqual(sEvents[i].EffectId, nEvents[i].EffectId);
                            Assert.AreEqual(sEvents[i].Expired, nEvents[i].Expired);
                        }
                        Assert.AreEqual(sFx.ActiveCount, nFx.ActiveCount, enemyId + " depois de 10 s");
                        Assert.AreEqual(sStats.Get(StatId.MoveSpeed), nStats.Get(StatId.MoveSpeed), Tolerance, enemyId + " depois de expirar");

                        nFx.Apply("effect.guard_break", 1.0, "hero");
                        nFx.Clear();
                        Assert.AreEqual(0, nFx.ActiveCount);
                        Assert.AreEqual(0, nFx.StackCount("effect.guard_break"));
                    }
                }
            }
        }

        [Test]
        public void CombatRunsTheSameFightOnBothCores()
        {
            // O combate em passo fixo inteiro (CombatSystem) com o mesmo cenario e a mesma seed nos dois motores.
            var nativeHits = RunFight(LoadNative());
            var stubHits = RunFight(TestWorld.LoadRules());
            Assert.Greater(stubHits.Count, 0);
            Assert.AreEqual(stubHits.Count, nativeHits.Count, "numero de golpes");
            for (var i = 0; i < stubHits.Count; i++)
            {
                Assert.AreEqual(stubHits[i].Result.TotalDamage, nativeHits[i].Result.TotalDamage, Tolerance, $"golpe {i}");
                Assert.AreEqual(stubHits[i].Result.LifeLost, nativeHits[i].Result.LifeLost, Tolerance, $"golpe {i}");
                Assert.AreEqual(stubHits[i].Result.Critical, nativeHits[i].Result.Critical, $"golpe {i}");
                Assert.AreEqual(stubHits[i].Result.Outcome, nativeHits[i].Result.Outcome, $"golpe {i}");
            }
        }

        [Test]
        public void EffectSetKeepsTheDatabaseAliveAfterTheCoreIsDisposed()
        {
            var native = LoadNative();
            var info = native.FindEnemy(Sentinel);
            var stats = native.CreateEnemyStats(Sentinel, 3);
            var fx = native.CreateEffectSet(stats, info);
            native.Dispose();
            try
            {
                Assert.IsTrue(fx.Apply("effect.guard_break", 1.0, "hero"), "o banco continua vivo enquanto ha efeitos");
                Assert.AreEqual(1, fx.StackCount("effect.guard_break"));
            }
            finally
            {
                fx.Dispose();
                stats.Dispose();
            }
            Assert.DoesNotThrow(() => fx.Dispose(), "descartar de novo nao pode falhar");
        }

        [Test]
        public void ForeignStatBlocksAreRejected()
        {
            using (var native = LoadNative())
            using (var stub = TestWorld.LoadRules())
            using (var mine = native.CreateEnemyStats(Sentinel, 1))
            using (var foreign = stub.CreateEnemyStats(Sentinel, 1))
            {
                var rng = native.CreateRng(1, RngStream.Combat, 0);
                var request = new HitRequest { Attacker = foreign, Defender = mine, BaseDamage = new DamageByType { Physical = 5 }, Coefficient = 1.0, DefenderLife = 10 };
                Assert.Throws<ArgumentException>(() => native.ResolveHit(in request, ref rng));
                Assert.Throws<ArgumentException>(() => native.CreateEffectSet(foreign, null));
            }
        }

        [Test]
        public void DisposedStatBlockThrows()
        {
            using (var native = LoadNative())
            {
                var stats = native.CreateEmptyStats();
                Assert.AreEqual(1.0, stats.Get(StatId.AttackSpeed), Tolerance);
                var revision = stats.Revision;
                stats.Dispose();
                Assert.Throws<ObjectDisposedException>(() => stats.Get(StatId.Life));
                Assert.GreaterOrEqual(revision, 0ul);
            }
        }

        [Test]
        public void LiveRegistryTracksAndDisposesCores()
        {
            // A-06: todo nucleo nativo tem dono; a rede de seguranca (saida do Play, recarga de dominio) descarta as sobras.
            NativeRulesCore.DisposeAllLive();
            var a = LoadNative();
            var b = LoadNative();
            Assert.AreEqual(2, NativeRulesCore.LiveCount);
            a.Dispose();
            Assert.AreEqual(1, NativeRulesCore.LiveCount);
            Assert.IsTrue(b.IsLoaded);
            NativeRulesCore.DisposeAllLive();
            Assert.AreEqual(0, NativeRulesCore.LiveCount);
            Assert.IsFalse(b.IsLoaded);
        }

        [Test]
        public void StillInStubListNoLongerHoldsTheBackendItems()
        {
            // A-01: o que a API 1.1 entrega saiu do stub; a lista so tem o que ainda falta.
            foreach (var wired in new[] { "TickVitals", "ResolvePotion", "GetActionTiming", "PickAttack", "dodge" })
                Assert.That(NativeRulesCore.StillInStub, Has.None.Contains(wired + " e"), wired);
            Assert.That(NativeRulesCore.StillInStub, Has.Some.Contains("NextBelow"));
            Assert.That(NativeRulesCore.StillInStub, Has.Some.Contains("FindClass"));
            Assert.That(NativeRulesCore.StillInStub.Count, Is.LessThanOrEqualTo(8));
        }

        [Test]
        public void ExtLayoutAndMinorVersionAreChecked()
        {
            LoadNative().Dispose();
            Assert.IsTrue(NativeLayout.CheckExt(out var message), message);
            Assert.AreEqual(114, NativeLayout.BuildExt().Length);
        }

        [Test]
        public void Ext3LayoutOfTheFleeResultIsCheckedAndApiMinorIsAtLeast3()
        {
            LoadNative().Dispose();
            Assert.IsTrue(NativeLayout.CheckExt3(out var message), message);
            var values = NativeLayout.BuildExt3();
            Assert.AreEqual(6, values.Length);
            Assert.AreEqual(16u, values[0], "shatter_flee_result tem 16 bytes");
            Assert.GreaterOrEqual(ShatterNative.shatter_api_minor(), 3u);
        }

        [Test]
        public void CombatRulesComeFromTheDatabaseExtension()
        {
            using (var native = LoadNative())
            using (var stub = TestWorld.LoadRules())
            {
                var n = native.Combat;
                var c = stub.Combat;
                Assert.AreEqual(c.DodgeMaxCharges, n.DodgeMaxCharges);
                Assert.AreEqual(c.DodgeRechargeSeconds, n.DodgeRechargeSeconds, Tolerance);
                Assert.AreEqual(c.DodgeDurationSeconds, n.DodgeDurationSeconds, Tolerance);
                Assert.AreEqual(c.DodgeInvulnerableSeconds, n.DodgeInvulnerableSeconds, Tolerance);
                Assert.AreEqual(c.OutOfCombatSeconds, n.OutOfCombatSeconds, Tolerance);
                Assert.AreEqual(c.PotionLockoutSeconds, n.PotionLockoutSeconds, Tolerance);
                Assert.IsEmpty(native.LoadWarnings, "nenhum valor provisorio: tudo vem da DLL");
            }
        }

        [Test]
        public void TimingCostMoveSpeedAndVitalsMatchTheStub()
        {
            using (var native = LoadNative())
            using (var stub = TestWorld.LoadRules())
            {
                var hero = new HeroBuild("class.warrior", 5, new[] { Sword });
                var cls = stub.FindClass("class.warrior");
                using (var a = native.CreateHeroStats(in hero))
                using (var b = stub.CreateHeroStats(in hero))
                {
                    foreach (var id in new[] { "skill.warrior.iron_cut", "skill.warrior.charge", "skill.warrior.stone_rift", "skill.warrior.shield_bash" })
                    {
                        var skill = stub.FindSkill(id);
                        var tn = native.GetActionTiming(a, skill);
                        var ts = stub.GetActionTiming(b, skill);
                        Assert.AreEqual(ts.Windup, tn.Windup, Tolerance, id);
                        Assert.AreEqual(ts.Impact, tn.Impact, Tolerance, id);
                        Assert.AreEqual(ts.Recovery, tn.Recovery, Tolerance, id);
                        Assert.AreEqual(stub.GetEffectiveCost(b, skill), native.GetEffectiveCost(a, skill), Tolerance, id);
                    }
                    Assert.AreEqual(stub.GetMoveSpeedUu(b, cls.MoveSpeedUu), native.GetMoveSpeedUu(a, cls.MoveSpeedUu), Tolerance, "heroi");

                    var vn = native.CreateVitals(a, cls);
                    var vs = stub.CreateVitals(b, cls);
                    Assert.AreEqual(vs.Life, vn.Life, Tolerance);
                    Assert.AreEqual(vs.Resource, vn.Resource, Tolerance);
                    native.TickVitals(ref vn, a, cls, 1.0, false);
                    stub.TickVitals(ref vs, b, cls, 1.0, false);
                    Assert.AreEqual(vs.Life, vn.Life, Tolerance);
                    native.GainResource(ref vn, a, 30.0);
                    stub.GainResource(ref vs, b, 30.0);
                    Assert.AreEqual(vs.Resource, vn.Resource, Tolerance);
                    Assert.AreEqual(stub.TrySpendResource(ref vs, 10.0), native.TrySpendResource(ref vn, 10.0));
                    Assert.AreEqual(vs.Resource, vn.Resource, Tolerance);
                    Assert.IsFalse(native.TrySpendResource(ref vn, 99999.0));
                    vn.Life = 10.0;
                    vs.Life = 10.0;
                    foreach (var potion in stub.Potions)
                    {
                        var on = native.ResolvePotion(potion, a, in vn);
                        var os = stub.ResolvePotion(potion, b, in vs);
                        Assert.AreEqual(os.LifeAfter, on.LifeAfter, Tolerance, potion.Id);
                        Assert.AreEqual(os.BarrierAfter, on.BarrierAfter, Tolerance, potion.Id);
                        Assert.AreEqual(os.BarrierSeconds, on.BarrierSeconds, Tolerance, potion.Id);
                        Assert.AreEqual(os.LifeGained, on.LifeGained, Tolerance, potion.Id);
                    }
                }
                var sentinel = stub.FindEnemy(Sentinel);
                using (var a = native.CreateEnemyStats(Sentinel, 3))
                using (var b = stub.CreateEnemyStats(Sentinel, 3))
                    Assert.AreEqual(stub.GetMoveSpeedUu(b, sentinel.MoveSpeedUu), native.GetMoveSpeedUu(a, sentinel.MoveSpeedUu), Tolerance, "inimigo");
            }
        }

        [Test]
        public void StunAndGuardBreakGoThroughTheActor()
        {
            using (var native = LoadNative())
            {
                var common = native.FindEnemy(Sentinel);
                using (var stats = native.CreateEnemyStats(Sentinel, 3))
                using (var fx = native.CreateEffectSet(stats, common))
                {
                    Assert.IsTrue(native.CanAct(stats));
                    Assert.IsTrue(fx.Apply("effect.stun", 1.0, "hero"));
                    Assert.IsTrue(fx.LastApply.Stunned);
                    Assert.IsFalse(native.CanAct(stats), "atordoado nao age");
                    Assert.IsFalse(native.CanMove(stats));
                    var events = new List<EffectTickEvent>();
                    for (var i = 0; i < 70; i++) fx.Tick(native.Combat.FixedStep, events);
                    Assert.IsTrue(native.CanAct(stats), "o atordoamento acabou");
                }

                var elite = native.FindEnemy("enemy.shielded_sentinel");
                using (var stats = native.CreateEnemyStats(elite.Id, 3))
                using (var fx = native.CreateEffectSet(stats, elite))
                {
                    Assert.IsFalse(fx.Apply("effect.stun", 1.0, "hero"));
                    Assert.IsTrue(fx.LastApply.StunBlocked, "elite fixo e imune ao stun");
                    for (var i = 0; i < 2; i++) Assert.IsTrue(fx.Apply("effect.guard_break", 1.0, "hero"));
                    Assert.IsTrue(native.CanAct(stats));
                    Assert.IsTrue(fx.Apply("effect.guard_break", 1.0, "hero"));
                    Assert.IsTrue(fx.LastApply.Staggered, "no 3o acumulo o alvo imune entra em stagger");
                    Assert.IsFalse(native.CanAct(stats));
                }
            }
        }

        [Test]
        public void PickAttackUsesTheCoreAndTheEventsStream()
        {
            using (var native = LoadNative())
            {
                var rng = native.CreateRng(5, RngStream.Events, 0);
                var before = rng.State;
                var index = native.PickAttack(ref rng, native.FindEnemy(Sentinel));
                Assert.GreaterOrEqual(index, 0);
                Assert.AreNotEqual(before, rng.State, "consome 1 numero do fluxo");
                Assert.AreEqual(-1, native.PickAttack(ref rng, null));
            }
        }

        [Test]
        public void PotionBeltDodgeEliteAndBossRunNatively()
        {
            using (var native = LoadNative())
            {
                var hero = new HeroBuild("class.warrior", 5, new[] { Sword });
                using (var stats = native.CreateHeroStats(in hero))
                using (var belt = native.CreatePotionBelt())
                {
                    Assert.AreEqual(native.Potions.Count, belt.Count);
                    Assert.AreEqual(native.Potions[0].MaxCharges, belt.GetEntry(0).Charges);
                    Assert.AreEqual(PotionUseStatus.Ok, belt.TryUse(0, stats));
                    Assert.AreEqual(native.Potions[0].MaxCharges - 1, belt.GetEntry(0).Charges);
                    Assert.Greater(belt.LockoutRemaining, 0.0);
                    Assert.AreEqual(PotionUseStatus.LockedOut, belt.TryUse(0, stats), "trava global");
                    belt.Tick(native.Combat.PotionLockoutSeconds + 0.1);
                    Assert.AreEqual(PotionUseStatus.Ok, belt.TryUse(0, stats));
                    belt.Refill();
                    Assert.IsTrue(belt.GetEntry(0).IsFull);
                    Assert.IsFalse(belt.OnEliteKilled(), "tudo cheio: nada a acrescentar");
                    Assert.AreEqual(PotionUseStatus.Unknown, belt.TryUse(99, stats));
                }

                using (var dodge = native.CreateDodge())
                {
                    Assert.AreEqual(native.Combat.DodgeMaxCharges, dodge.Charges);
                    Assert.AreEqual(DodgeStartStatus.Ok, dodge.TryStart(0.0));
                    Assert.IsTrue(dodge.IsInvulnerable);
                    Assert.AreEqual(native.Combat.DodgeMaxCharges - 1, dodge.Charges);
                    Assert.AreEqual(DodgeStartStatus.Active, dodge.TryStart(0.0));
                    dodge.Tick(native.Combat.DodgeDurationSeconds + 0.01);
                    Assert.IsFalse(dodge.IsDodging);
                    dodge.Reset();
                    Assert.IsTrue(dodge.IsFull);
                }

                var rng = native.CreateRng(5, RngStream.Events, 0);
                var roll = native.RollElite(ref rng);
                Assert.IsTrue(roll.Rolled);
                Assert.IsNotEmpty(roll.ModifierId);
                using (var enemy = native.CreateEnemyStats(Sentinel, 3))
                {
                    var life = enemy.Get(StatId.Life);
                    native.ApplyElite(enemy, in roll);
                    Assert.AreEqual(life * roll.LifeMult, enemy.Get(StatId.Life), 1e-6, "elite sorteado multiplica a vida");
                }

                using (var bossStats = native.CreateEnemyStats("enemy.crypt_guardian", 5))
                using (var boss = native.CreateBoss("enemy.crypt_guardian", 5, 7))
                {
                    boss.Start();
                    var events = new List<BossEvent>();
                    for (var i = 0; i < 300; i++) boss.Step(native.Combat.FixedStep, 0, 0, 0, 4, bossStats, events);
                    Assert.IsNotEmpty(events);
                    Assert.AreEqual(BossEventKind.PatternStart, events[0].Kind);
                    var info = boss.Info;
                    Assert.AreEqual(1, info.Phase);
                    Assert.AreEqual(info.MaxLife, info.Life, 1e-9);
                    var front = boss.ApplyDamage(50.0, 0, 0, info.FacingX * 4.0, info.FacingZ * 4.0);
                    Assert.IsTrue(front.ShieldBlocked, "escudo frontal: dano de frente e bloqueado");
                    Assert.AreEqual(0.0, front.Applied);
                    var back = boss.ApplyDamage(50.0, 0, 0, -info.FacingX * 4.0, -info.FacingZ * 4.0);
                    Assert.IsFalse(back.ShieldBlocked);
                    Assert.Greater(back.Applied, 0.0);
                }
            }
        }

        [Test]
        public void LegsSlotEquipsThroughTheNativeCharacterBuilder()
        {
            // C-18: ItemSlot ganhou Legs no fim; o C# so manda o nome do slot (item_bases.csv), sem enum espelhado.
            using (var native = LoadNative())
            {
                var bare = new HeroBuild("class.warrior", 5, new[] { Sword });
                var dressed = new HeroBuild("class.warrior", 5, new[] { Sword, "item_base.worn_trousers" });
                using (var a = native.CreateHeroStats(in bare))
                using (var b = native.CreateHeroStats(in dressed))
                    Assert.Greater(b.Get(StatId.Armor), a.Get(StatId.Armor), "a calca soma armadura (armor:flat:4)");
            }
        }

        [Test]
        public void FactoryPrefersTheNativeCoreAndReportsNoFallback()
        {
            var warnings = new List<string>();
            using (var core = RulesCoreFactory.CreateDefault(warnings.Add))
            {
                if (core is StubRulesCore) Assert.Ignore("DLL nativa indisponivel: " + RulesCoreFactory.LastFallbackReason);
                Assert.IsInstanceOf<NativeRulesCore>(core);
                Assert.IsEmpty(warnings);
                Assert.IsEmpty(RulesCoreFactory.LastFallbackReason);
            }
        }

        // ---------------------------------------------------------------------------------------------

        static List<HitEvent> RunFight(IRulesCore rules)
        {
            using (var world = new TestWorld(null, rules))
            {
                var hero = world.AddHero(PlanarVector.Zero);
                world.AddEnemy(Sentinel, new PlanarVector(0f, 1.2f), 3);
                world.AddEnemy("enemy.ash_hound", new PlanarVector(2f, 1.5f), 3);
                hero.logic.Press(HeroCommand.BasicAttack);
                for (var s = 0; s < 8; s++)
                {
                    world.Run(0.5);
                    hero.logic.Press(HeroCommand.BasicAttack);
                }
                return new List<HitEvent>(world.Hits);
            }
        }

        static HitRequest Request(IStatBlock attacker, IStatBlock defender, SkillInfo skill, DamageByType baseDamage, double life, double barrier, bool dot)
        {
            return new HitRequest
            {
                Attacker = attacker,
                Defender = defender,
                SkillTags = skill.Tags,
                BaseDamage = baseDamage,
                Coefficient = skill.Coefficient(1),
                IsDamageOverTime = dot,
                CanBeBlocked = !dot,
                DefenderLife = life,
                DefenderBarrier = barrier,
            };
        }

        static void AssertStatsEqual(IStatBlock expected, IStatBlock actual, string label, bool skipMoveSpeed = false)
        {
            var contexts = new[]
            {
                SkillTags.None,
                SkillTags.Attack | SkillTags.Melee | SkillTags.Physical,
                SkillTags.Spell | SkillTags.Fire,
                SkillTags.Attack | SkillTags.Projectile,
            };
            for (var s = 0; s < (int)StatId.Count; s++)
            {
                // Heroi: o core guarda MoveSpeed em uu/s (class_stats.csv, 450); o stub segue com multiplicador. Comparado por GetMoveSpeedUu.
                if (skipMoveSpeed && (StatId)s == StatId.MoveSpeed) continue;
                foreach (var tags in contexts)
                    Assert.AreEqual(expected.GetTagged((StatId)s, tags), actual.GetTagged((StatId)s, tags), Tolerance, $"{label}: {(StatId)s} / {tags}");
            }
        }

        static void AssertHitsEqual(HitResult expected, HitResult actual, int index, string label = "")
        {
            var where = $"{label} golpe {index}";
            Assert.AreEqual(expected.Outcome, actual.Outcome, where);
            Assert.AreEqual(expected.Critical, actual.Critical, where);
            Assert.AreEqual(expected.Landed, actual.Landed, where);
            Assert.AreEqual(expected.Killed, actual.Killed, where);
            Assert.AreEqual(expected.TotalDamage, actual.TotalDamage, Tolerance, where + " dano total");
            Assert.AreEqual(expected.AbsorbedByBarrier, actual.AbsorbedByBarrier, Tolerance, where + " barreira");
            Assert.AreEqual(expected.LifeLost, actual.LifeLost, Tolerance, where + " vida perdida");
            Assert.AreEqual(expected.DefenderLifeAfter, actual.DefenderLifeAfter, Tolerance, where + " vida restante");
            Assert.AreEqual(expected.DefenderBarrierAfter, actual.DefenderBarrierAfter, Tolerance, where + " barreira restante");
            for (var t = 0; t < DamageByType.Count; t++)
            {
                Assert.AreEqual(expected.AfterModifiers[t], actual.AfterModifiers[t], Tolerance, where + $" apos modificadores[{t}]");
                Assert.AreEqual(expected.AfterMitigation[t], actual.AfterMitigation[t], Tolerance, where + $" apos mitigacao[{t}]");
            }
        }

        static string FindHeader()
        {
            var dir = new DirectoryInfo(Directory.GetCurrentDirectory());
            while (dir != null)
            {
                var candidate = Path.Combine(dir.FullName, "ShatterCore", "include", "shatter", "shatter_c.h");
                if (File.Exists(candidate)) return candidate;
                dir = dir.Parent;
            }
            Assert.Ignore("shatter_c.h nao encontrado a partir de " + Directory.GetCurrentDirectory());
            return null;
        }
    }
}
