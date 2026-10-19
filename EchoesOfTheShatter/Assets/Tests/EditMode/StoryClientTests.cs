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
