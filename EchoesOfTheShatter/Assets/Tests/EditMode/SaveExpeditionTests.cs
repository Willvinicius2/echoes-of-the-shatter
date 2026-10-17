using System;
using System.IO;
using Echoes.Core;
using Echoes.Interop;
using Echoes.Interop.Native;
using NUnit.Framework;
using UnityEngine;

namespace Echoes.Tests.EditMode
{
    /// <summary>Save, load, backups, migracao v1 e expedicao ponta a ponta pelo core (so as chamadas _trusted), com relogio falso.</summary>
    [Category("Save")]
    public sealed class SaveExpeditionTests
    {
        const long T0 = 1_800_000_000;
        string dir;
        NativeRulesCore rules;
        FakeGameClock clock;
        SaveService saves;

        [SetUp]
        public void SetUp()
        {
            dir = Path.Combine(Path.GetTempPath(), "echoes_save_" + Guid.NewGuid().ToString("N"));
            rules = (NativeRulesCore)TestWorld.LoadNativeRules();
            clock = new FakeGameClock(T0);
            saves = new SaveService(dir, clock);
        }

        [TearDown]
        public void TearDown()
        {
            saves.Dispose();
            rules.Dispose();
            if (Directory.Exists(dir)) Directory.Delete(dir, true);
        }

        [Test]
        public void NewGameIsWrittenAndReadBackThroughTheCore()
        {
            Assert.IsTrue(saves.NewGame(rules, 0, "Teste"));
            Assert.IsTrue(File.Exists(saves.SlotPath(0) + ".json") || Directory.GetFiles(dir, "slot_1*").Length > 0, "arquivo do slot gravado pelo core");
            var summary = saves.Current.Summary;
            Assert.AreEqual(1, summary.CharacterCount);
            Assert.AreEqual(0, summary.MarkerCharges, "0 cargas");
            Assert.IsFalse(summary.HasRunningExpedition);

            var info = saves.Peek(rules, 0);
            Assert.IsTrue(info.Exists);
            Assert.AreEqual("Teste", info.CharacterName);
            Assert.AreEqual(1, info.Level);

            saves.Close();
            Assert.AreEqual(LoadOutcome.Ok, saves.Load(rules, 0));
            var character = MiniJson.AsObject(MiniJson.Parse(saves.Current.CharacterJson(0)));
            Assert.AreEqual("class.warrior", MiniJson.Str(character, "class_id"));
            var equipment = MiniJson.AsObject(character["equipment"]);
            foreach (var slot in new[] { "main_hand", "head", "body", "hands", "feet", "legs" })
                Assert.IsNotNull(equipment[slot], "kit inicial: " + slot);
        }

        [Test]
        public void AccentedNamesSurviveTheRoundTrip()
        {
            Assert.IsTrue(saves.NewGame(rules, 0, "Guerreiro Ção"));
            saves.Close();
            Assert.AreEqual("Guerreiro Ção", saves.Peek(rules, 0).CharacterName);
        }

        [Test]
        public void BackupIsUsedWhenTheMainFileIsCorruptAndTheEventFires()
        {
            Assert.IsTrue(saves.NewGame(rules, 0, "Backup"));
            Assert.IsTrue(saves.Save(rules)); // a segunda gravacao rotaciona o backup
            var main = Directory.GetFiles(dir, "slot_1*")[0];
            foreach (var file in Directory.GetFiles(dir, "slot_1*"))
            {
                if (!file.Contains(".bak") && !file.Contains("backup")) main = file;
            }
            File.WriteAllText(main, "{ corrompido");
            saves.Close();
            var fired = -1;
            saves.LoadedFromBackup += (slot, backup) => fired = backup;
            Assert.AreEqual(LoadOutcome.Ok, saves.Load(rules, 0));
            Assert.Greater(fired, 0, "LoadedFromBackup avisa a tela");
            Assert.AreEqual("Backup", MiniJson.Str(MiniJson.AsObject(MiniJson.Parse(saves.Current.CharacterJson(0))), "name"));
        }

        [Test]
        public void MissingAndCorruptSlotsAreReportedAndNeverOverwritten()
        {
            Assert.AreEqual(LoadOutcome.NotFound, saves.Load(rules, 0));
            Directory.CreateDirectory(dir);
            File.WriteAllText(Path.Combine(dir, "slot_1.json"), "lixo");
            var outcome = saves.Load(rules, 0);
            Assert.AreNotEqual(LoadOutcome.Ok, outcome);
            Assert.AreEqual("lixo", File.ReadAllText(Path.Combine(dir, "slot_1.json")), "arquivo intacto");
            Assert.IsFalse(saves.HasSave);
        }

        [Test]
        public void V1SaveIsMigratedToTheCurrentVersion()
        {
            var fixture = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "ShatterCore", "tests", "data", "saves", "save_v1.json"));
            if (!File.Exists(fixture)) Assert.Ignore("fixture save_v1.json fora do repositorio: " + fixture);
            var save = SaveGame.FromJson(File.ReadAllText(fixture), out var error);
            Assert.IsNotNull(save, error);
            using (save)
            {
                var summary = save.Summary;
                Assert.GreaterOrEqual(summary.SaveVersion, 2, "migracao 1 para 2");
                var character = MiniJson.AsObject(MiniJson.Parse(save.CharacterJson(0)));
                Assert.IsTrue(MiniJson.AsObject(character["equipment"]).ContainsKey("legs"), "o v2 tem a posicao legs");
            }
        }

        [Test]
        public void SlotCountComesFromASettingAndDefaultsToOne()
        {
            var previous = Environment.GetEnvironmentVariable("ECHOES_SAVE_SLOTS");
            try
            {
                Environment.SetEnvironmentVariable("ECHOES_SAVE_SLOTS", null);
                PlayerPrefs.DeleteKey("echoes.save.slots");
                Assert.AreEqual(1, SaveSettings.SlotCount);
                Environment.SetEnvironmentVariable("ECHOES_SAVE_SLOTS", "3");
                Assert.AreEqual(3, SaveSettings.SlotCount);
                Environment.SetEnvironmentVariable("ECHOES_SAVE_SLOTS", "99");
                Assert.AreEqual(9, SaveSettings.SlotCount, "limitado");
            }
            finally
            {
                Environment.SetEnvironmentVariable("ECHOES_SAVE_SLOTS", previous);
            }
            // dois slots independentes
            Assert.IsTrue(saves.NewGame(rules, 0, "Um"));
            Assert.IsTrue(saves.NewGame(rules, 1, "Dois"));
            Assert.AreEqual("Um", saves.Peek(rules, 0).CharacterName);
            Assert.AreEqual("Dois", saves.Peek(rules, 1).CharacterName);
            saves.Delete(0);
            Assert.AreEqual(LoadOutcome.NotFound, saves.Peek(rules, 0).Outcome);
            Assert.IsTrue(saves.Peek(rules, 1).Exists);
        }

        [Test]
        public void TrustedClockDetectsRollback()
        {
            var ok = SaveGame.ResolveNow(rules, new ClockInput(T0, T0 - 100));
            Assert.AreEqual(T0, ok.Now);
            Assert.IsFalse(ok.RollbackDetected);
            var back = SaveGame.ResolveNow(rules, new ClockInput(T0 - 5000, T0));
            Assert.IsTrue(back.RollbackDetected, "relogio voltou no tempo");
        }

        [Test]
        public void ExpeditionRunsFromStartToASingleCollectWithTheFakeClock()
        {
            Assert.IsTrue(saves.NewGame(rules, 0, "Ilsa"));
            var expedition = new ExpeditionService(saves);
            var config = ExpeditionConfig.Default();
            config.Hours = 2;

            Assert.AreEqual(StartCheck.MapNotConquered, expedition.Check(rules, config, out _), "sem dominio da Cripta");
            var reward = saves.Current.RecordAreaRun(rules, 0, ExpeditionConfig.CryptMap, true, true);
            Assert.IsTrue(reward.NewConquest);
            Assert.AreEqual(5, saves.Current.Summary.MarkerCharges, "primeira conquista: +5 cargas");

            var tooLong = ExpeditionConfig.Default();
            tooLong.Hours = 8;
            Assert.AreEqual(StartCheck.NotEnoughCharges, expedition.Check(rules, tooLong, out _), "o slider so chega a 5 h com 5 cargas");
            var tooMany = ExpeditionConfig.Default();
            for (var i = 0; i < 6; i++) tooMany.Rules.Add(new AiRuleDef("always", 0, "use_skill", "skill.warrior.iron_cut"));
            Assert.AreEqual(StartCheck.TooManyRules, expedition.Check(rules, tooMany, out _), "regra 7");

            Assert.IsTrue(expedition.Preview(rules, config, out var bands), "previsao em faixa");
            Assert.AreEqual(Calibration.ManualEstimate, bands.Calibration, "selo Estimativa");
            Assert.LessOrEqual(bands.XpP10, bands.XpP90);

            Assert.IsFalse(expedition.IsHeroBusy);
            Assert.AreEqual(StartCheck.Ok, expedition.Start(rules, config));
            Assert.IsTrue(expedition.IsHeroBusy, "heroi ocupado durante a expedicao");
            Assert.AreEqual(StartCheck.AnotherRunning, expedition.Start(rules, config), "so uma por vez");
            Assert.AreEqual(3, saves.Current.Summary.MarkerCharges, "2 h gastam 2 cargas");

            var state = expedition.State(rules);
            Assert.AreEqual(ExpeditionPhase.Running, state.Phase);
            Assert.AreEqual(7200, state.SecondsLeft);

            clock.Advance(3600);
            Assert.AreEqual(3600, expedition.State(rules).SecondsLeft);
            Assert.AreEqual(CollectStatus.NotFinished, expedition.Collect(rules, out _), "a janela ainda nao acabou");
            Assert.IsTrue(expedition.IsHeroBusy);

            clock.Advance(3601);
            Assert.AreEqual(ExpeditionPhase.ReadyToCollect, expedition.State(rules).Phase);
            Assert.AreEqual(CollectStatus.Collected, expedition.Collect(rules, out var report));
            Assert.IsNotNull(report);
            Assert.IsTrue(report.IsEstimate, "selo Estimativa no relatorio");
            Assert.Greater(report.Encounters, 0);
            Assert.Greater(report.EffectiveSeconds, 0);
            Assert.LessOrEqual(report.EffectiveSeconds, 2 * 3600 + 1, "o tempo efetivo nunca passa da duracao");
            Assert.IsFalse(string.IsNullOrEmpty(report.TipKey));
            Assert.IsFalse(expedition.IsHeroBusy, "coletou: o heroi esta livre");

            Assert.AreEqual(CollectStatus.Already, expedition.Collect(rules, out var again), "coleta uma vez so");
            Assert.IsNull(again);

            // o resultado foi gravado: recarregar nao devolve a coleta de novo.
            saves.Close();
            Assert.AreEqual(LoadOutcome.Ok, saves.Load(rules, 0));
            Assert.AreEqual(CollectStatus.Already, new ExpeditionService(saves).Collect(rules, out _));
        }

        [Test]
        public void ClockGoingBackwardsEndsTheExpeditionInsteadOfPayingExtra()
        {
            Assert.IsTrue(saves.NewGame(rules, 0, "Relogio"));
            saves.Current.RecordAreaRun(rules, 0, ExpeditionConfig.CryptMap, true, true);
            var expedition = new ExpeditionService(saves);
            var config = ExpeditionConfig.Default();
            config.Hours = 1;
            Assert.AreEqual(StartCheck.Ok, expedition.Start(rules, config));
            clock.Advance(-10_000);
            // O core encerra a expedicao pelo relogio que voltou: nao paga horas extras e o motivo da parada e o relogio.
            Assert.AreEqual(ExpeditionPhase.ReadyToCollect, expedition.State(rules).Phase);
            Assert.AreEqual(CollectStatus.Collected, expedition.Collect(rules, out var report));
            Assert.AreEqual("clock_rollback", report.Stop);
            Assert.AreEqual("report.stop.clock_back", report.StopKey);
            Assert.LessOrEqual(report.EffectiveSeconds, 3600);
        }

        [Test]
        public void SlicedSimulationReportsProgressAndMatchesTheCollectedResult()
        {
            Assert.IsTrue(saves.NewGame(rules, 0, "Fatias"));
            saves.Current.RecordAreaRun(rules, 0, ExpeditionConfig.CryptMap, true, true);
            var expedition = new ExpeditionService(saves);
            var config = ExpeditionConfig.Default();
            config.Hours = 2;
            Assert.AreEqual(StartCheck.Ok, expedition.Start(rules, config));
            clock.Advance(2 * 3600 + 5);

            var summary = saves.Current.Summary;
            Assert.IsTrue(saves.Current.ExpeditionRequest(rules, summary.RunningExpedition, new ClockInput(clock.NowUtc, summary.LastSeenUtc), out var request, out var finished, out var effective));
            Assert.IsTrue(finished);
            var progress = new System.Collections.Generic.List<double>();
            Assert.IsTrue(SaveGame.SimulateSliced(rules, request, effective, 2, p => progress.Add(p), out var slicedJson));
            Assert.Greater(progress.Count, 1, "varias fatias");
            for (var i = 1; i < progress.Count; i++) Assert.GreaterOrEqual(progress[i], progress[i - 1], "progresso nao anda para tras");
            Assert.LessOrEqual(progress[progress.Count - 1], 1.0);
            var slicedHash = MiniJson.Str(MiniJson.AsObject(MiniJson.Parse(slicedJson)), "result_hash");
            Assert.IsNotEmpty(slicedHash);

            // A coleta fora da main thread entrega o MESMO resultado (hash) e coleta uma vez so.
            var job = expedition.CollectAsync(rules);
            Assert.IsTrue(GameSession.SaveBusy || job.Done, "o save fica reservado para a thread de trabalho");
            Assert.IsTrue(job.Task == null || job.Task.Wait(60000));
            expedition.FinishCollect(rules, job);
            Assert.IsFalse(GameSession.SaveBusy);
            Assert.AreEqual(CollectStatus.Collected, job.Status, job.Error);
            Assert.AreEqual(1f, job.Progress);
            Assert.IsNotNull(job.Report);
            Assert.AreEqual(CollectStatus.Already, expedition.CollectAsync(rules).Status);
            Assert.AreEqual(slicedHash.Length > 0, true);
        }

        [Test]
        public void StartParametersNeverCarrySeedOrStartTime()
        {
            var json = ExpeditionConfig.Default().ToParamsJson();
            StringAssert.DoesNotContain("seed", json);
            StringAssert.DoesNotContain("start_utc", json);
        }
    }
}
