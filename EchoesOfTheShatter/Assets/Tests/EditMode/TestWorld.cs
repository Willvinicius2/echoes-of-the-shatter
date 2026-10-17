using System;
using System.Collections.Generic;
using System.IO;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    /// <summary>
    /// Monta um combate de teste com o motor de regras provisório (stub) e os CSV reais de
    /// <c>EchoesOfTheShatter/Content/Data</c>. Sem cena e sem UnityEngine: só lógica pura.
    /// </summary>
    internal sealed class TestWorld : IDisposable
    {
        public const string WarriorClass = "class.warrior";
        public const string Sword = "item_base.iron_sword";
        public const ulong Seed = 12345UL;

        static readonly string[] DefaultBar =
        {
            "skill.warrior.iron_cut", "skill.warrior.charge", "skill.warrior.stone_rift", "skill.warrior.shield_bash", "", "",
        };

        public readonly IRulesCore Rules;
        public readonly EventBus Events = new EventBus();
        public readonly CombatSystem Combat;
        public readonly List<HitEvent> Hits = new List<HitEvent>();
        public readonly List<HitAvoidedEvent> Avoided = new List<HitAvoidedEvent>();
        public readonly List<ActionDeniedEvent> Denied = new List<ActionDeniedEvent>();

        public TestWorld(CombatFeelValues feel = null, IRulesCore rules = null)
        {
            Rules = rules ?? LoadRules();
            Combat = new CombatSystem(Rules, Events, Seed, feel ?? new CombatFeelValues(), 8);
            Events.Subscribe<HitEvent>(OnHit);
            Events.Subscribe<HitAvoidedEvent>(OnAvoided);
            Events.Subscribe<ActionDeniedEvent>(OnDenied);
        }

        public double Step => Rules.Combat.FixedStep;

        /// <summary>Pasta dos CSV: ECHOES_CONTENT_DIR, ou Content/Data a partir da pasta atual (no editor, a raiz do projeto).</summary>
        public static string DataDirectory
        {
            get
            {
                var env = Environment.GetEnvironmentVariable("ECHOES_CONTENT_DIR");
                if (!string.IsNullOrEmpty(env)) return env;
                var dir = new DirectoryInfo(Directory.GetCurrentDirectory());
                while (dir != null)
                {
                    var candidates = new[]
                    {
                        Path.Combine(dir.FullName, "Content", "Data"),
                        Path.Combine(dir.FullName, "EchoesOfTheShatter", "Content", "Data"),
                        Path.Combine(dir.FullName, "Assets", "StreamingAssets", "Data"),
                    };
                    foreach (var candidate in candidates)
                    {
                        if (File.Exists(Path.Combine(candidate, "rules.csv"))) return candidate;
                    }
                    dir = dir.Parent;
                }
                return Path.Combine(Directory.GetCurrentDirectory(), "Content", "Data");
            }
        }

        public static StubRulesCore LoadRules()
        {
            var core = new StubRulesCore();
            var errors = new List<RulesError>();
            var status = core.LoadContent(DataDirectory, errors);
            Assert.AreEqual(RulesStatus.Ok, status, "CSV não carregou: " + string.Join("\n", errors));
            return core;
        }

        public (Combatant combatant, HeroCombatLogic logic) AddHero(PlanarVector position, int level = 5, IReadOnlyList<string> bar = null, IBasicKit kit = null)
        {
            var classInfo = Rules.FindClass(WarriorClass);
            var weapon = Rules.FindItemBase(Sword);
            var build = new HeroBuild(WarriorClass, level, new[] { Sword });
            var stats = Rules.CreateHeroStats(in build);
            var effects = Rules.CreateEffectSet(stats, null);
            var combatant = new Combatant(CombatTeam.Hero, WarriorClass, level, stats, effects, classInfo, null, weapon, 0.3f)
            {
                Position = position,
                Forward = PlanarVector.Forward,
            };
            var logic = new HeroCombatLogic(combatant, Rules, bar ?? DefaultBar, kit);
            Combat.Register(combatant, logic);
            logic.AimPoint = position + PlanarVector.Forward * 3f;
            return (combatant, logic);
        }

        /// <summary>O core nativo carregado com os CSV reais; sem a DLL o teste fica ignorado com o motivo.</summary>
        public static IRulesCore LoadNativeRules()
        {
            if (!Echoes.Interop.Native.NativeRulesCore.TryCreate(out var core, out var reason)) Assert.Ignore("shattercore.dll nao carregou: " + reason);
            var errors = new List<RulesError>();
            var status = core.LoadContent(DataDirectory, errors);
            Assert.AreEqual(RulesStatus.Ok, status, "CSV nao carregou no nativo: " + string.Join(" | ", errors));
            return core;
        }

        public (Combatant combatant, EnemyCombatLogic logic) AddEnemy(string enemyId, PlanarVector position, int level = 3, float radius = 0.5f, EliteProfile elite = default)
        {
            var info = Rules.FindEnemy(enemyId);
            Assert.IsNotNull(info, enemyId);
            var stats = Rules.CreateEnemyStats(enemyId, level);
            var barrier = !elite.IsNone ? Rules.ApplyElite(stats, in elite) : 0.0;
            var effects = Rules.CreateEffectSet(stats, info, elite.Rolled);
            var combatant = new Combatant(CombatTeam.Enemy, enemyId, level, stats, effects, null, info, null, radius)
            {
                Position = position,
                Forward = -PlanarVector.Forward,
                Elite = elite,
                InitialBarrier = barrier,
            };
            var logic = new EnemyCombatLogic(combatant, Rules);
            Combat.Register(combatant, logic);
            return (combatant, logic);
        }

        /// <summary>Roda <paramref name="seconds"/> em passos fixos.</summary>
        public void Run(double seconds)
        {
            var steps = (int)Math.Round(seconds / Step);
            for (var i = 0; i < steps; i++) Combat.Step(Step);
        }

        public int HitsOn(Combatant target)
        {
            var count = 0;
            foreach (var hit in Hits)
            {
                if (ReferenceEquals(hit.Target, target)) count++;
            }
            return count;
        }

        public void Dispose()
        {
            foreach (var c in Combat.Combatants)
            {
                (c.Actor as IDisposable)?.Dispose();
                c.Effects?.Dispose();
                c.Stats.Dispose();
            }
            Combat.Dispose();
            Rules.Dispose();
        }

        void OnHit(in HitEvent evt) => Hits.Add(evt);
        void OnAvoided(in HitAvoidedEvent evt) => Avoided.Add(evt);
        void OnDenied(in ActionDeniedEvent evt) => Denied.Add(evt);
    }
}
