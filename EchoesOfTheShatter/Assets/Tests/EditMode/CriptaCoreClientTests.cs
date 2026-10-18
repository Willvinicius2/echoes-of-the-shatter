using System;
using System.IO;
using System.Linq;
using Echoes.Core;
using Echoes.Interop;
using Echoes.Interop.Native;
using Echoes.UI;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    /// <summary>
    /// Core da Cripta (API C 1.7) pelo cliente: XP por morte com Fervor e nivel no save, estado do mundo (bau, parede secreta, atalho) gravado em
    /// disco, baus que rolam loot uma vez so, loot ao limpar encontro e encontros sorteados pela semente da visita. Tudo com o core nativo e o save real.
    /// </summary>
    [Category("CriptaCore")]
    public sealed class CriptaCoreClientTests
    {
        const long T0 = 1_800_000_000;
        const string Map = ExpeditionConfig.CryptMap;
        string dir;
        NativeRulesCore rules;
        SaveService saves;

        [SetUp]
        public void SetUp()
        {
            dir = Path.Combine(Path.GetTempPath(), "echoes_cripta_core_" + Guid.NewGuid().ToString("N"));
            rules = (NativeRulesCore)TestWorld.LoadNativeRules();
            saves = new SaveService(dir, new FakeGameClock(T0));
            Assert.IsTrue(saves.NewGame(rules, 0, "Teste"));
        }

        [TearDown]
        public void TearDown()
        {
            saves.Dispose();
            rules.Dispose();
            if (Directory.Exists(dir)) Directory.Delete(dir, true);
        }

        SaveGame Save => saves.Current;

        [Test]
        public void KillXp_AddsToTheSave_AndFervorMultipliesIt()
        {
            var before = Save.CharacterProgress(rules, 0, Map);
            Assert.AreEqual(1, before.Level);
            var plain = Save.AwardKillXp(rules, 0, Map, "enemy.hollow_sentinel", 3, false, "", false, out var ok);
            Assert.IsTrue(ok);
            Assert.Greater(plain.Awarded, 0.0, "a morte rende XP");
            var fervor = rules.Fervor();
            var boosted = Save.AwardKillXp(rules, 0, Map, "enemy.hollow_sentinel", 3, false, "", true, out ok);
            Assert.IsTrue(ok);
            Assert.AreEqual(plain.Awarded * fervor.XpMult, boosted.Awarded, 1e-6, "Fervor: o multiplicador vem do rules.csv pelo core");
            Assert.AreEqual(3.0, fervor.XpMult, 1e-9, "XP +200% com o CSV atual");
            var after = Save.CharacterProgress(rules, 0, Map);
            Assert.IsTrue(after.Level > before.Level || after.XpInLevel > before.XpInLevel, "o XP entrou no save");
        }

        [Test]
        public void KillXp_EliteGivesMore_AndTheLevelRisesInTheSaveUpToTheAreaCap()
        {
            var common = Save.AwardKillXp(rules, 0, Map, "enemy.hollow_sentinel", 3, false, "", false, out _);
            var modifier = rules.Fervor().XpMult > 0 ? FirstModifier() : "";
            var elite = Save.AwardKillXp(rules, 0, Map, "enemy.hollow_sentinel", 3, true, modifier, false, out _);
            Assert.Greater(elite.Awarded, common.Awarded, "elite sorteado rende mais XP");

            var levels = 0;
            for (var i = 0; i < 4000 && !Save.CharacterProgress(rules, 0, Map).AtCap; i++)
            {
                var award = Save.AwardKillXp(rules, 0, Map, "enemy.hollow_sentinel", 3, false, "", false, out _);
                if (award.LeveledUp) levels++;
            }
            var progress = Save.CharacterProgress(rules, 0, Map);
            Assert.Greater(levels, 0, "subiu de nivel");
            Assert.IsTrue(progress.AtCap, "o teto de nivel da area (nivel do monstro + xp_cap_levels_above_area)");
            Assert.AreEqual(3 + 2, progress.LevelCap, "teto da Cripta: derivado do CSV (3 + 2)");
            var capped = Save.AwardKillXp(rules, 0, Map, "enemy.hollow_sentinel", 3, false, "", false, out _);
            Assert.AreEqual(progress.Level, capped.Level, "no teto o XP nao sobe mais o nivel");
        }

        string FirstModifier()
        {
            var lines = File.ReadAllLines(Path.Combine(TestWorld.DataDirectory, "elite_modifiers.csv"));
            return lines.Skip(1).Select(l => l.Split(',')[0]).First(id => id.Length > 0);
        }

        [Test]
        public void WorldState_ChestSecretAndShortcut_SurviveTheSaveFile()
        {
            Assert.IsFalse(Save.IsWorldObjectOpen(Map, "chest.crypt.01"));
            Assert.IsTrue(Save.SetWorldObjectOpen(Map, "chest.crypt.01", true));
            Assert.IsTrue(Save.SetWorldObjectOpen(Map, "secret.crypt.cracked_wall", true));
            Assert.IsTrue(Save.SetWorldObjectOpen(Map, "shortcut.crypt.a", true));
            Assert.IsTrue(saves.Save(rules));

            saves.Close();
            Assert.AreEqual(LoadOutcome.Ok, saves.Load(rules, 0));
            foreach (var id in new[] { "chest.crypt.01", "secret.crypt.cracked_wall", "shortcut.crypt.a" })
                Assert.IsTrue(Save.IsWorldObjectOpen(Map, id), id + " continua aberto depois de salvar e carregar");
            Assert.IsFalse(Save.IsWorldObjectOpen(Map, "chest.crypt.02"), "so o que o jogador abriu");
        }

        [Test]
        public void Chest_OpensOnce_PersistsAndRollsLootFromTheCore()
        {
            var json = Save.OpenChest(rules, Map, "chest.crypt.04", 3, 0, -1, 12345UL, out var result, out var error);
            Assert.AreEqual(ChestOpenResult.Opened, result, error);
            Assert.IsTrue(Save.IsWorldObjectOpen(Map, "chest.crypt.04"), "o core marcou o bau como aberto");
            var again = Save.OpenChest(rules, Map, "chest.crypt.04", 3, 0, -1, 12345UL, out var second, out _);
            Assert.AreEqual(ChestOpenResult.AlreadyOpen, second, "bau aberto nao rola de novo");
            Assert.IsEmpty(again ?? string.Empty);
            Assert.IsTrue(saves.Save(rules));
            saves.Close();
            saves.Load(rules, 0);
            Save.OpenChest(rules, Map, "chest.crypt.04", 3, 0, -1, 99UL, out var afterReload, out _);
            Assert.AreEqual(ChestOpenResult.AlreadyOpen, afterReload, "continua aberto depois de salvar e carregar");
        }

        [Test]
        public void EncounterClearLoot_RollsTheAreaTable()
        {
            var rolledSomething = false;
            for (var seed = 1UL; seed < 400UL && !rolledSomething; seed++)
            {
                var json = Save.EncounterClearLoot(rules, Map, 3, 0, -1, seed, out var error);
                Assert.IsEmpty(error ?? string.Empty);
                rolledSomething = !string.IsNullOrEmpty(json) && json != "[]";
            }
            Assert.IsTrue(rolledSomething, "a tabela da area (loot.crypt.area) rende Ouro ou Lascas ao limpar um encontro");
        }

        [Test]
        public void EncounterRoll_IsDeterministicByVisitSeed_AndWithinMinAndMax()
        {
            Assert.IsTrue(Save.BeginAreaVisit(rules, Map, out var seedA));
            Assert.IsTrue(Save.BeginAreaVisit(rules, Map, out var seedB));
            Assert.AreNotEqual(seedA, seedB, "cada visita tem a sua semente");
            Assert.AreEqual(2, Save.WorldState(Map).Visits);

            var map = SaveGame.MapInfoOf(rules, Map);
            Assert.AreEqual(3, map.MonsterLevel);
            Assert.AreEqual(5, map.Chests.Count, "5 baus do docs/14");
            foreach (var id in map.Encounters)
            {
                var one = SaveGame.RollEncounter(rules, id, seedA);
                var two = SaveGame.RollEncounter(rules, id, seedA);
                Assert.AreEqual(one.Groups.Count, two.Groups.Count);
                for (var g = 0; g < one.Groups.Count; g++)
                {
                    Assert.AreEqual(one.Groups[g].Count, two.Groups[g].Count, id + ": mesma semente, mesma formacao (tambem depois de um checkpoint)");
                    for (var s = 0; s < one.Groups[g].Count; s++)
                    {
                        Assert.AreEqual(one.Groups[g].Slots[s].Elite, two.Groups[g].Slots[s].Elite);
                        Assert.AreEqual(one.Groups[g].Slots[s].ModifierId, two.Groups[g].Slots[s].ModifierId);
                    }
                }
            }
        }

        [Test]
        public void EncounterRoll_CountsStayBetweenMinAndMaxOfTheCsv()
        {
            var rows = File.ReadAllLines(Path.Combine(TestWorld.DataDirectory, "encounters.csv")).Skip(1).Where(l => l.Length > 0).ToList();
            Assert.IsTrue(Save.BeginAreaVisit(rules, Map, out var seed));
            foreach (var row in rows)
            {
                var cells = row.Split(',');
                if (cells[4] == "true") continue;
                var rolled = SaveGame.RollEncounter(rules, cells[0], seed);
                var groups = cells[1].Split('|');
                Assert.AreEqual(groups.Length, rolled.Groups.Count, cells[0]);
                for (var i = 0; i < groups.Length; i++)
                {
                    var parts = groups[i].Split(':');
                    Assert.GreaterOrEqual(rolled.Groups[i].Count, int.Parse(parts[1]), cells[0] + " minimo");
                    Assert.LessOrEqual(rolled.Groups[i].Count, int.Parse(parts[2]), cells[0] + " maximo");
                }
            }
        }

        [Test]
        public void XpBar_ComesFromTheCoreProgress()
        {
            GameSession.Use(saves);
            try
            {
                var first = SaveReadout.Read(rules, Map);
                Assert.IsTrue(first.Valid);
                Assert.AreEqual(1, first.Level);
                Assert.AreEqual(0f, first.XpFraction, 1e-6);
                Save.AwardKillXp(rules, 0, Map, "enemy.hollow_sentinel", 3, false, "", false, out _);
                var after = SaveReadout.Read(rules, Map);
                Assert.Greater(after.XpFraction + after.Level - 1, 0f, "XP entrou: a barra anda ou o nivel sobe");
                Assert.Greater(after.XpToNext, 0.0, "o core diz quanto o nivel pede");
            }
            finally
            {
                GameSession.Reset();
                saves = new SaveService(dir, new FakeGameClock(T0));
            }
        }
    }
}
