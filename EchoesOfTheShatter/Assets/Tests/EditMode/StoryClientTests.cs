using System;
using System.IO;
using Echoes.Core;
using Echoes.Interop;
using Echoes.Interop.Native;
using Echoes.UI;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    /// <summary>
    /// Historia da Regiao 1 no cliente (API C shatter_story_*): leitura dos JSON do core, Ecos, veredito recusado sem o General vencido, Fome e o
    /// bonus de atributos somado ao bloco do heroi. As regras sao do core; aqui so se confere a ligacao do C#.
    /// </summary>
    [Category("Historia")]
    public sealed class StoryClientTests
    {
        const long T0 = 1_800_000_000;
        const string StateJson =
            "{\"hunger\":1,\"hunger_max\":4,\"stat_bonus_pct\":10,\"echoes\":[\"echo.r1.broken_hammer\",\"echo.r1.shield_memory\"],\"verdicts\":[" +
            "{\"region_id\":\"region.r1.crypt\",\"verdict_id\":\"verdict.r1.devour\",\"choice\":\"devour\",\"region_state\":\"stain\"," +
            "\"hub_state\":\"hub.fortified_garrison\",\"hunger_delta\":1,\"stat_bonus_pct\":10,\"grants_relic\":\"\"," +
            "\"grants_signature\":\"skill.devoured.guardian_slam\",\"last_words_key\":\"\"}]}";

        [Test]
        public void StoryState_reads_relic_and_stain_effects()
        {
            var json = "{\"hunger\":0,\"hunger_max\":4,\"stat_bonus_pct\":0,\"potion_effect_pct\":25,\"stain_elite_bonus_by_map\":{\"map.act1.crypt\":15},\"echoes\":[],\"verdicts\":[]}";
            var state = StoryState.FromJson(json);
            Assert.AreEqual(25.0, state.PotionEffectPct);
            Assert.AreEqual(15.0, state.StainEliteBonusByMap["map.act1.crypt"]);
        }

        [Test]
        public void StoryLines_follow_progress_and_verdict()
        {
            const string region = "region.r1.crypt";
            var fresh = StoryState.FromJson("{\"hunger\":0,\"hunger_max\":4,\"echoes\":[],\"verdicts\":[]}");
            Assert.AreEqual("dlg.ilsa.intro_1", StoryLines.For(InteractableNpc.Ilsa, fresh, region)[0]);
            Assert.AreEqual("dlg.tico.intro", StoryLines.For(InteractableNpc.Tico, fresh, region)[0]);
            var echoes = StoryState.FromJson("{\"hunger\":0,\"hunger_max\":4,\"echoes\":[\"echo.r1.broken_hammer\"],\"verdicts\":[]}");
            Assert.AreEqual("dlg.ilsa.general_lore", StoryLines.For(InteractableNpc.Ilsa, echoes, region)[0]);
            Assert.AreEqual("dlg.bram.echo_blade", StoryLines.For(InteractableNpc.Bram, echoes, region)[0]);
            Assert.Contains("dlg.odete.warning", StoryLines.For(InteractableNpc.Odete, echoes, region));
            var devoured = StoryState.FromJson(StateJson);
            Assert.AreEqual("dlg.ilsa.after_devour", StoryLines.For(InteractableNpc.Ilsa, devoured, region)[0]);
            Assert.Contains("dlg.ilsa.years_pass", StoryLines.For(InteractableNpc.Ilsa, devoured, region));
            Assert.AreEqual("dlg.tico.after_years", StoryLines.For(InteractableNpc.Tico, devoured, region)[0]);
            Assert.AreEqual("dlg.bram.after_devour", StoryLines.For(InteractableNpc.Bram, devoured, region)[0]);
            CollectionAssert.IsEmpty(StoryLines.For(InteractableNpc.Ilsa, null, region));
        }

        string dir;
        NativeRulesCore rules;
        SaveService saves;
        StoryDb story;

        [SetUp]
        public void SetUp()
        {
            dir = Path.Combine(Path.GetTempPath(), "echoes_story_" + Guid.NewGuid().ToString("N"));
            rules = (NativeRulesCore)TestWorld.LoadNativeRules();
            saves = new SaveService(dir, new FakeGameClock(T0));
            Assert.IsTrue(saves.NewGame(rules, 0, "Teste"));
            story = StoryDb.Load(rules, Path.Combine(TestWorld.DataDirectory, "Story"), out var error);
            Assert.IsNotNull(story, error);
        }

        [TearDown]
        public void TearDown()
        {
            story?.Dispose();
            saves?.Dispose();
            rules?.Dispose();
            if (Directory.Exists(dir)) Directory.Delete(dir, true);
        }

        SaveGame Save => saves.Current;

        [Test]
        public void StateJson_IsParsed()
        {
            var state = StoryState.FromJson(StateJson);
            Assert.AreEqual(1, state.Hunger);
            Assert.AreEqual(4, state.HungerMax);
            Assert.AreEqual(10.0, state.StatBonusPct, 1e-9);
            Assert.AreEqual(2, state.Echoes.Count);
            Assert.IsTrue(state.HasEcho("echo.r1.shield_memory"));
            Assert.AreEqual("hub.fortified_garrison", state.HubState);
            var verdict = state.VerdictOf("region.r1.crypt");
            Assert.IsNotNull(verdict);
            Assert.IsTrue(verdict.IsDevour);
            Assert.IsTrue(state.HasSignature("skill.devoured.guardian_slam"));
            Assert.IsFalse(state.HasRelic("relic.r1.rest"));
        }

        [Test]
        public void StateJson_ReadsDevouredCostAndStainLoot()
        {
            var json = "{\"hunger\":1,\"hunger_max\":4,\"devoured_hunger_cost\":1,\"stain_loot_table_by_map\":{\"map.act1.crypt\":\"loot.crypt.stain\"},\"echoes\":[],\"verdicts\":[]}";
            var state = StoryState.FromJson(json);
            Assert.AreEqual(1, state.DevouredHungerCost);
            Assert.AreEqual("loot.crypt.stain", state.StainLootTableByMap["map.act1.crypt"]);
        }

        [Test]
        public void DevouredKit_GatesTheSlamByHungerAndFillsTheLastFreeSlot()
        {
            var kit = new Echoes.Gameplay.DevouredKit(StoryState.FromJson(
                "{\"hunger\":2,\"hunger_max\":4,\"devoured_hunger_cost\":1,\"echoes\":[],\"verdicts\":[{\"region_id\":\"region.r1.crypt\",\"verdict_id\":\"verdict.r1.devour\",\"grants_signature\":\"skill.devoured.guardian_slam\"}]}"));
            const string slam = "skill.devoured.guardian_slam";
            Assert.IsTrue(kit.CanCast("skill.warrior.iron_cut"));
            Assert.IsTrue(kit.CanCast(slam));
            kit.Spent(slam);
            Assert.IsTrue(kit.CanCast(slam));   // Fome 3 de 4
            kit.Spent(slam);
            Assert.AreEqual(4, kit.Hunger);
            Assert.IsFalse(kit.CanCast(slam));  // Fome cheia: negado
            Assert.IsTrue(kit.CanCast("skill.warrior.iron_cut"));
            kit.ResetRun();
            Assert.IsTrue(kit.CanCast(slam));

            var bar = new[] { "skill.warrior.iron_cut", string.Empty, "skill.warrior.charge", "skill.warrior.stone_rift", "skill.warrior.shield_bash", string.Empty };
            kit.FillBar(bar);
            Assert.AreEqual(slam, bar[5]);
            Assert.AreEqual(string.Empty, bar[1]);   // o espaco 1 e a defesa
        }

        [Test]
        public void DevouredKit_CarriesSpentHungerToTheKitReadAfterTheVerdict()
        {
            const string json = "{\"hunger\":0,\"hunger_max\":4,\"devoured_hunger_cost\":1,\"echoes\":[],\"verdicts\":[{\"region_id\":\"region.r1.crypt\",\"verdict_id\":\"verdict.r1.devour\",\"grants_signature\":\"skill.devoured.guardian_slam\"}]}";
            var old = new Echoes.Gameplay.DevouredKit(StoryState.FromJson(json));
            old.Spent("skill.devoured.guardian_slam");
            var fresh = new Echoes.Gameplay.DevouredKit(StoryState.FromJson(json));
            fresh.CarrySpentFrom(old);
            Assert.AreEqual(1, fresh.Hunger);
            fresh.CarrySpentFrom(null);   // sem kit anterior (primeiro Devorar): nada muda
            Assert.AreEqual(1, fresh.Hunger);
        }

        [Test]
        public void Quests_FromCore_FollowTalkEchoesAndJournal()
        {
            var state = StoryState.FromJson("{}");
            Assert.AreEqual(0, state.Quests.Count);   // JSON sem chave quests
            state = Save.ReadStory(story);
            Assert.AreEqual(4, state.Quests.Count);
            Assert.IsTrue(state.QuestOf("quest.r1.first_call").IsActive);
            Assert.IsTrue(state.QuestOf("quest.r1.echoes").Status == "locked");
            Assert.AreEqual(0, Save.StoryQuestEvent(story, "talk", "npc.tico"));
            Assert.AreEqual(1, Save.StoryQuestEvent(story, "talk", "npc.ilsa"));
            Assert.IsTrue(Save.StoryRecordEcho(story, "echo.r1.broken_hammer", out _));
            state = Save.ReadStory(story);
            Assert.IsTrue(state.QuestDone("quest.r1.first_call"));
            Assert.AreEqual(1, state.QuestOf("quest.r1.echoes").Progress);
            Assert.AreEqual(3, state.QuestOf("quest.r1.echoes").ObjectiveCount);
            Assert.AreEqual("unlock.return_marker", state.QuestOf("quest.r1.first_call").Reward);
            // Diario: ativas primeiro, depois as concluidas; a trancada (verdict) nao aparece.
            var shown = QuestJournal.Visible(state);
            Assert.AreEqual("quest.r1.echoes", shown[0].QuestId);
            Assert.AreEqual("quest.r1.first_call", shown[shown.Count - 1].QuestId);
            Assert.IsNull(shown.Find(q => q.QuestId == "quest.r1.verdict"));
        }

        [Test]
        public void StoryLines_IntroPlaysOnceAndCryptDoneAfterVerdict()
        {
            const string region = "region.r1.crypt";
            var heard = StoryState.FromJson("{\"echoes\":[],\"verdicts\":[],\"quests\":[{\"quest_id\":\"quest.r1.first_call\",\"status\":\"done\"}]}");
            Assert.AreEqual("dlg.ilsa.general_lore", StoryLines.For(InteractableNpc.Ilsa, heard, region)[0]);
            var won = StoryState.FromJson(StateJson.Replace("}]}", "}],\"quests\":[{\"quest_id\":\"quest.r1.verdict\",\"status\":\"done\"}]}"));
            Assert.AreEqual("dlg.ilsa.crypt_done", StoryLines.For(InteractableNpc.Ilsa, won, region)[0]);
        }

        [Test]
        public void BrokenJson_GivesEmptyState()
        {
            Assert.AreEqual(0, StoryState.FromJson("{nao e json").HungerMax);
            Assert.AreEqual(string.Empty, StoryRegionInfo.FromJson(null).RegionId);
        }

        [Test]
        public void HungerText_FillsPipsUpToTheMax()
        {
            Assert.AreEqual("Fome ●●○○", StoryDirector.HungerText("Fome", 2, 4));
            Assert.AreEqual("Fome", StoryDirector.HungerText("Fome", 0, 0).Trim());
        }

        [Test]
        public void NewSave_HasNoStoryProgress()
        {
            var state = Save.ReadStory(story);
            Assert.AreEqual(0, state.Hunger);
            Assert.Greater(state.HungerMax, 0);
            Assert.AreEqual(0, state.Echoes.Count);
            Assert.AreEqual(0, state.Verdicts.Count);
            Assert.AreEqual(string.Empty, state.HubState);
        }

        [Test]
        public void Region_ListsBothOptionsExorciseFirst()
        {
            var region = Save.ReadStoryRegion(story, StoryDirector.RegionId);
            Assert.AreEqual(StoryDirector.RegionId, region.RegionId);
            Assert.IsFalse(region.Decided);
            Assert.AreEqual(2, region.Options.Count);
            Assert.IsTrue(region.Options[0].IsExorcise);
            Assert.IsTrue(region.Options[1].IsDevour);
            Assert.Greater(region.Options[1].HungerDelta, 0);
            Assert.AreEqual(0, region.EchoesFound);
            Assert.Greater(region.EchoesTotal, 0);
        }

        [Test]
        public void RecordEcho_IsNewOnlyOnce_AndRevealsTheSkill()
        {
            Assert.IsTrue(Save.StoryRecordEcho(story, "echo.r1.broken_hammer", out var first));
            Assert.IsTrue(first);
            Assert.IsTrue(Save.StoryRecordEcho(story, "echo.r1.broken_hammer", out var again));
            Assert.IsFalse(again);
            Assert.IsTrue(Save.StorySkillRevealed(story, StoryDirector.RegionId, "skill.enemy.guardian_hammer"));
            Assert.IsFalse(Save.StorySkillRevealed(story, StoryDirector.RegionId, "skill.enemy.guardian_shield_bash"));
            Assert.AreEqual(1, Save.ReadStoryRegion(story, StoryDirector.RegionId).EchoesFound);
        }

        [Test]
        public void RecordEcho_UnknownEcho_IsRefused()
        {
            Assert.IsFalse(Save.StoryRecordEcho(story, "echo.nao.existe", out var isNew));
            Assert.IsFalse(isNew);
        }

        [Test]
        public void Verdict_WithoutDefeatingTheGeneral_ChangesNothing()
        {
            Assert.AreEqual(VerdictResult.GeneralNotDefeated, Save.StoryApplyVerdict(story, "verdict.r1.devour"));
            Assert.AreEqual(0, Save.ReadStory(story).Hunger);
            Assert.AreEqual(VerdictResult.Unknown, Save.StoryApplyVerdict(story, "verdict.nao.existe"));
        }

        [Test]
        public void StoryBonus_RaisesTheHeroLife()
        {
            using (var plain = Save.StatsOfCharacter(rules, 0, 1))
            {
                var before = plain.Get(StatId.Life);
                Save.StoryStatBonusPct = 10.0;
                using (var boosted = Save.StatsOfCharacter(rules, 0, 1))
                    Assert.Greater(boosted.Get(StatId.Life), before);
                Save.StoryStatBonusPct = 0.0;
            }
        }
    }
}
