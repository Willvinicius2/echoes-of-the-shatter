using System;
using System.Collections.Generic;
using System.IO;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using Echoes.Interop.Native;
using Echoes.Presentation;
using Echoes.UI;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.UIElements;

namespace Echoes.Tests.EditMode
{
    /// <summary>
    /// Fechamento da Cripta no cliente: configuracoes do jogador, remapeamento, Fase 2 do Guardiao, faixa e fade, leitura do save para a HUD,
    /// bloqueio de expedicao com nome, dica do relatorio, arte final da UI e o 2o conjunto de armadura do Guerreiro.
    /// </summary>
    [Category("Mapa")]
    public sealed class MapaClientTests
    {
        const long T0 = 1_800_000_000;

        static LocalizationService LoadLoc()
        {
            var loc = new LocalizationService(_ => { });
            loc.LoadDirectory(ContentPaths.LocalizationDirectory(TestWorld.DataDirectory));
            loc.SetCulture("pt_BR");
            return loc;
        }

        // ------------------------------------------------------------------------------------------------ configuracoes

        [Test]
        public void UserSettings_PersistLanguageAndShake_AndScaleTheShake()
        {
            var path = Path.Combine(Path.GetTempPath(), "echoes_settings_" + Guid.NewGuid().ToString("N") + ".json");
            try
            {
                UserSettings.UseFile(path);
                Assert.AreEqual(string.Empty, UserSettings.Culture, "sem arquivo: o jogo usa o idioma do sistema");
                Assert.AreEqual(1f, UserSettings.ShakeFactor);
                UserSettings.Culture = "en";
                UserSettings.Shake = ShakeMode.Reduced;
                Assert.AreEqual(UserSettings.ReducedShakeFactor, UserSettings.ShakeFactor);
                UserSettings.Shake = ShakeMode.Off;
                Assert.AreEqual(0f, UserSettings.ShakeFactor);
                UserSettings.ReduceFlashes = true;

                UserSettings.UseFile(path); // relê do disco
                Assert.AreEqual("en", UserSettings.Culture);
                Assert.AreEqual(ShakeMode.Off, UserSettings.Shake);
                Assert.IsTrue(UserSettings.ReduceFlashes);
            }
            finally
            {
                UserSettings.UseFile(null);
                if (File.Exists(path)) File.Delete(path);
            }
        }

        [Test]
        public void UserSettings_CorruptFileFallsBackToDefaults()
        {
            var path = Path.Combine(Path.GetTempPath(), "echoes_settings_bad_" + Guid.NewGuid().ToString("N") + ".json");
            File.WriteAllText(path, "{ isto nao e json");
            try
            {
                UserSettings.UseFile(path);
                Assert.AreEqual(ShakeMode.Normal, UserSettings.Shake);
                Assert.AreEqual(string.Empty, UserSettings.Culture);
            }
            finally
            {
                UserSettings.UseFile(null);
                File.Delete(path);
            }
        }

        [Test]
        public void LanguageSwitch_ChangesTextsWithoutRestart()
        {
            var path = Path.Combine(Path.GetTempPath(), "echoes_settings_lang_" + Guid.NewGuid().ToString("N") + ".json");
            try
            {
                UserSettings.UseFile(path);
                var loc = LoadLoc();
                var changed = 0;
                loc.CultureChanged += () => changed++;
                var view = new OptionsView(loc, null, null, false);
                Assert.AreEqual("Opções", loc.Get("ui.options.title"));
                view.SetLanguage("en");
                Assert.AreEqual("Options", loc.Get("ui.options.title"));
                Assert.AreEqual(1, changed, "as telas ouvem CultureChanged e se refazem");
                Assert.AreEqual("en", UserSettings.Culture, "a escolha persiste");
            }
            finally
            {
                UserSettings.UseFile(null);
                if (File.Exists(path)) File.Delete(path);
            }
        }

        // ------------------------------------------------------------------------------------------------ remapeamento

        static InputActionAsset MakeActions()
        {
            var asset = ScriptableObject.CreateInstance<InputActionAsset>();
            var map = asset.AddActionMap(InputActionNames.Map);
            map.AddAction(InputActionNames.Dodge, InputActionType.Button).AddBinding("<Keyboard>/space", groups: "Keyboard&Mouse");
            map.AddAction(InputActionNames.Skill2, InputActionType.Button).AddBinding("<Keyboard>/q", groups: "Keyboard&Mouse");
            var move = map.AddAction(InputActionNames.Move, InputActionType.Value);
            move.AddCompositeBinding("2DVector").With("Up", "<Keyboard>/w").With("Down", "<Keyboard>/s").With("Left", "<Keyboard>/a").With("Right", "<Keyboard>/d");
            return asset;
        }

        [Test]
        public void Remap_DodgeToShift_MovesTheKey_AndSpaceNoLongerDodges()
        {
            var asset = MakeActions();
            try
            {
                var dodge = asset.FindActionMap(InputActionNames.Map).FindAction(InputActionNames.Dodge);
                var index = OptionsView.BindingIndices(dodge)[0];
                Assert.AreEqual("<Keyboard>/space", dodge.bindings[index].effectivePath);
                dodge.ApplyBindingOverride(index, "<Keyboard>/leftShift");
                Assert.AreEqual("<Keyboard>/leftShift", dodge.bindings[index].effectivePath);

                // persistencia: o JSON salvo reaplica no asset novo (e o espaco deixa de esquivar)
                var json = asset.SaveBindingOverridesAsJson();
                asset.RemoveAllBindingOverrides(); // volta ao padrao (espaco) e reaplica o arquivo salvo, como o jogo faz ao abrir
                Assert.AreEqual("<Keyboard>/space", dodge.bindings[index].effectivePath);
                asset.LoadBindingOverridesFromJson(json);
                Assert.AreEqual("<Keyboard>/leftShift", dodge.bindings[index].effectivePath);
                Assert.AreNotEqual("<Keyboard>/space", dodge.bindings[index].effectivePath, "o espaco deixou de esquivar");
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(asset);
            }
        }

        [Test]
        public void Remap_FindsConflictAndIgnoresCompositeParts()
        {
            var asset = MakeActions();
            try
            {
                var map = asset.FindActionMap(InputActionNames.Map);
                var dodge = map.FindAction(InputActionNames.Dodge);
                var skill = map.FindAction(InputActionNames.Skill2);
                dodge.ApplyBindingOverride(0, "<Keyboard>/q"); // mesma tecla da Habilidade 2
                Assert.IsTrue(OptionsView.TryFindConflict(map, dodge, 0, out var other, out var otherIndex));
                Assert.AreSame(skill, other);
                Assert.AreEqual(0, otherIndex);

                dodge.ApplyBindingOverride(0, "<Keyboard>/w"); // W so existe como parte do composto de andar: nao e conflito
                Assert.IsFalse(OptionsView.TryFindConflict(map, dodge, 0, out _, out _));

                Assert.AreEqual(1, OptionsView.BindingIndices(map.FindAction(InputActionNames.Dodge)).Count);
                Assert.AreEqual(0, OptionsView.BindingIndices(map.FindAction(InputActionNames.Move)).Count, "o composto e suas partes nao entram na tabela");
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(asset);
            }
        }

        [Test]
        public void Remap_TableHasEveryActionTheDocAsks()
        {
            CollectionAssert.Contains(OptionsView.RemapActions, InputActionNames.Interact);
            CollectionAssert.Contains(OptionsView.RemapActions, InputActionNames.Dodge);
            CollectionAssert.DoesNotContain(OptionsView.RemapActions, InputActionNames.Pause, "Esc nao e remapeavel");
        }

        // ------------------------------------------------------------------------------------------------ Fase 2 do Guardiao

        [Test]
        public void SummonPositions_CycleThroughMarks_AndOffsetRepeats()
        {
            var marks = new List<Vector3> { new Vector3(10, 0, 20), new Vector3(14, 0, 20) };
            Assert.AreEqual(marks[0], BossSummoner.PositionFor(marks, 0, 1.5f));
            Assert.AreEqual(marks[1], BossSummoner.PositionFor(marks, 1, 1.5f));
            Assert.AreEqual(marks[0] + Vector3.right * 1.5f, BossSummoner.PositionFor(marks, 2, 1.5f), "a 3a invocada nao nasce em cima da 1a");
            Assert.AreEqual(Vector3.zero, BossSummoner.PositionFor(new List<Vector3>(), 0, 1.5f));
        }

        // ------------------------------------------------------------------------------------------------ faixa e fade

        [Test]
        public void Banner_QueuesInsteadOfDroppingAndKeepsOrder()
        {
            var root = new VisualElement();
            var banners = new BannerLayer(root);
            banners.Show("Cripta Partida", null, 3f);
            banners.Show("Guardião derrotado", "Marco de Retorno instalado", 3f);
            Assert.AreEqual("Cripta Partida", banners.Current);
            Assert.AreEqual(1, banners.PendingCount, "a segunda espera a vez; nenhuma se perde");
            CollectionAssert.AreEqual(new[] { "Cripta Partida" }, banners.Shown);
        }

        [Test]
        public void Fade_ImmediateReachesTargetAndCallsBack()
        {
            var root = new VisualElement();
            var fade = new FadeLayer(root, true);
            Assert.AreEqual(1f, fade.Alpha);
            var called = false;
            fade.FadeTo(0f, 0f, () => called = true);
            Assert.AreEqual(0f, fade.Alpha);
            Assert.IsTrue(called);
        }

        [Test]
        public void AreaBanner_NamesComeFromLocByScene()
        {
            var loc = LoadLoc();
            Assert.AreEqual("Refúgio do Marco", loc.Get(AreaBanner.NameKeyFor(GameFlow.RefugeScene)));
            Assert.AreEqual("Cripta Partida", loc.Get(AreaBanner.NameKeyFor(GameFlow.CriptaScene)));
            Assert.IsNull(AreaBanner.NameKeyFor(GameFlow.MainMenuScene));
            Assert.AreEqual(3f, AreaBanner.Seconds, "F-06: 3 s");
            Assert.AreEqual(3f, RunRecorder.VictoryBannerSeconds, "S-13: banner por 3 s");
        }

        // ------------------------------------------------------------------------------------------------ expedicao e relatorio

        [Test]
        public void Rf43_BlockerNamesComeFromLoc()
        {
            var loc = LoadLoc();
            Assert.AreEqual("Investida", loc.Get("skill.warrior.charge.name"));
            Assert.AreEqual("Investida", ExpeditionBlockers.Names("[\"skill.warrior.charge\"]", loc));
            Assert.AreEqual("Investida", ExpeditionBlockers.Names("{\"skills\":[\"skill.warrior.charge\"]}", loc));
            Assert.AreEqual(string.Empty, ExpeditionBlockers.Names("", loc));
            Assert.AreEqual(string.Empty, ExpeditionBlockers.Names("nao e json {", loc));
            var text = ScreenKit.Fmt(loc, "ui.exp.err.skill_blocked", ("skill", ExpeditionBlockers.Names("[\"skill.warrior.charge\"]", loc)));
            StringAssert.Contains("Investida", text);
        }

        [Test]
        public void ReportTip_PointsToThePotionRule()
        {
            var rules = new List<AiRuleDef>
            {
                new AiRuleDef("enemies_at_least", 2, "use_skill", "skill.warrior.shield_bash"),
                new AiRuleDef("life_below", 0.35, "use_potion", string.Empty),
            };
            Assert.AreEqual(1, RefugeController.RuleForTip("report.tip.raise_potion", rules));
            Assert.AreEqual(1, RefugeController.RuleForTip("report.tip.more_potions", rules));
            Assert.AreEqual(-1, RefugeController.RuleForTip("report.tip.all_good", rules));
            Assert.AreEqual(-1, RefugeController.RuleForTip(null, rules));
        }

        // ------------------------------------------------------------------------------------------------ leitura do save

        [Test]
        public void SaveReadout_ReadsLevelGoldAndCharges_FromTheRealSave()
        {
            var dir = Path.Combine(Path.GetTempPath(), "echoes_readout_" + Guid.NewGuid().ToString("N"));
            var rules = (NativeRulesCore)TestWorld.LoadNativeRules();
            var saves = new SaveService(dir, new FakeGameClock(T0));
            try
            {
                Assert.IsTrue(saves.NewGame(rules, 0, "Teste"));
                GameSession.Use(saves);
                var snap = SaveReadout.Read();
                Assert.IsTrue(snap.Valid);
                Assert.AreEqual(1, snap.Level);
                Assert.AreEqual(0, snap.Gold);
                Assert.AreEqual(0, snap.Charges);

                var reward = saves.Current.RecordAreaRun(rules, 0, ExpeditionConfig.CryptMap, true, true);
                Assert.Greater(reward.ChargesGained, 0);
                Assert.AreEqual(reward.ChargesGained, SaveReadout.Read().Charges, "as cargas da HUD vem do save");
            }
            finally
            {
                GameSession.Reset();
                rules.Dispose();
                if (Directory.Exists(dir)) Directory.Delete(dir, true);
            }
        }

        [Test]
        public void RecordAreaRun_WithoutReachingTheEnd_DoesNotConquer()
        {
            var dir = Path.Combine(Path.GetTempPath(), "echoes_reached_" + Guid.NewGuid().ToString("N"));
            var rules = (NativeRulesCore)TestWorld.LoadNativeRules();
            var saves = new SaveService(dir, new FakeGameClock(T0));
            try
            {
                Assert.IsTrue(saves.NewGame(rules, 0, "Teste"));
                var denied = saves.Current.RecordAreaRun(rules, 0, ExpeditionConfig.CryptMap, false, true); // RF-50: chefe sem chegar a arena nao conta
                Assert.IsFalse(denied.NewConquest, "sem chegar a arena nao grava dominio");
                Assert.Less(denied.ChargesGained, 5, "as 3 cargas de area nova nao vem");
                var granted = saves.Current.RecordAreaRun(rules, 0, ExpeditionConfig.CryptMap, true, true);
                Assert.IsTrue(granted.NewConquest);
            }
            finally
            {
                saves.Dispose();
                rules.Dispose();
                if (Directory.Exists(dir)) Directory.Delete(dir, true);
            }
        }

        // ------------------------------------------------------------------------------------------------ arte final

        [Test]
        public void UiArt_KitAndIconsExistAndSlicesAreSet()
        {
            foreach (var name in new[] { UiArt.FrameOrnate, UiArt.FramePlain, UiArt.SlotEmpty, UiArt.SlotCommon, UiArt.SlotMagic, UiArt.SlotRare, UiArt.SlotUnique, UiArt.ButtonNormal, UiArt.ButtonHover, UiArt.ButtonDisabled, UiArt.Tab, UiArt.BarThin })
            {
                Assert.IsNotNull(UiArt.Texture(name), "sprite do kit: " + name);
                var s = UiArt.SliceOf(name);
                Assert.Greater(s.Left + s.Right, 0, "9-slice de " + name);
            }
            foreach (var icon in new[] { "icon_sword", "icon_hammer", "icon_helm", "icon_vest", "icon_gloves", "icon_boots", "icon_trousers", "icon_unique_maul", "icon_potion_life", "icon_potion_ward", "icon_gold", "icon_shards" })
                Assert.IsNotNull(UiArt.Icon(icon), "icone: " + icon);
        }

        [Test]
        public void UiArt_EveryItemBaseInTheCsvHasAnIcon_AndTheUniqueHasItsOwn()
        {
            var lines = File.ReadAllLines(Path.Combine(TestWorld.DataDirectory, "item_bases.csv"));
            for (var i = 1; i < lines.Length; i++)
            {
                var cells = lines[i].Split(',');
                if (cells.Length < 2 || cells[0].Length == 0) continue;
                if (cells[1] == "off_hand") continue; // TODO(asset ui.icon.shield): escudos (docs/19) ainda sem icone aprovado; a UI mostra as iniciais
                Assert.IsNotNull(UiArt.IconName(cells[0], false, cells[1]), "base sem icone: " + cells[0]);
            }
            Assert.AreEqual("icon_unique_maul", UiArt.IconName("item_base.stone_maul", true));
            Assert.AreEqual("icon_hammer", UiArt.IconName("item_base.stone_maul", false));
            Assert.AreEqual("icon_trousers", UiArt.IconName("item_base.worn_trousers", false));
        }

        [Test]
        public void UiArt_ThemeImportsTheArtStylesheet()
        {
            var theme = File.ReadAllText(Path.Combine(Application.dataPath, "UI", "ShatterRuntimeTheme.tss"));
            StringAssert.Contains("UiArt.uss", theme);
            var uss = File.ReadAllText(Path.Combine(Application.dataPath, "Resources", "UiArt", "UiArt.uss"));
            foreach (var cls in new[] { ".art-button:hover", ".art-button:disabled", ".art-slot--unique", ".art-tab", ".art-frame-ornate" })
                StringAssert.Contains(cls, uss);
        }

        [Test]
        public void ItemText_StatValueFormatsFractionsAsPercent()
        {
            Assert.AreEqual("5%", ItemText.StatValue("crit_chance", 0.05));
            Assert.AreEqual("450", ItemText.StatValue("move_speed", 450));
            Assert.AreEqual("12.5", ItemText.StatValue("life_regen", 12.5));
        }

        // ------------------------------------------------------------------------------------------------ Loc

        [Test]
        public void Loc_NewKeysExistInBothLanguages()
        {
            var loc = LoadLoc();
            foreach (var key in new[] { "ui.hud.xp_total", "ui.pause.save_warning", "report.adjust_rule", "ui.death.nothing_lost", "ui.death.boss_restart", "ui.boss.defeated", "ui.boss.marker_installed", "ui.item.pick_stash", "ui.action.interact" })
            {
                loc.SetCulture("pt_BR");
                Assert.IsTrue(loc.TryGet(key, out var pt) && pt.Length > 0, "pt_BR " + key);
                loc.SetCulture("en");
                Assert.IsTrue(loc.TryGet(key, out var en) && en.Length > 0, "en " + key);
            }
            Assert.IsEmpty(loc.Table.DuplicateKeys, "chave duplicada ja quebrou o build");
        }

        // ------------------------------------------------------------------------------------------------ 2o conjunto do Guerreiro

        [Test]
        public void WarriorRareSet_HasFivePartsWithTheRareMaterial_AndFallbackStillWorks()
        {
            var catalog = UnityEditor.AssetDatabase.LoadAssetAtPath<HeroPartCatalog>(Echoes.EditorTools.HeroModularBuilder.CatalogPath("Warrior"));
            Assert.IsNotNull(catalog);
            for (var i = 0; i < 5; i++)
            {
                var slot = (HeroPartSlot)i;
                Assert.IsTrue(catalog.TryGet(slot, HeroPartCatalog.WarriorRareSet, out var part), "peca Rara " + slot);
                Assert.IsNotNull(part.prefab);
                var renderer = part.prefab.GetComponentInChildren<SkinnedMeshRenderer>(true);
                StringAssert.Contains("Rare", renderer.sharedMaterial.name);
                Assert.AreEqual("SG_Character", System.IO.Path.GetFileNameWithoutExtension(UnityEditor.AssetDatabase.GetAssetPath(renderer.sharedMaterial.shader)), "mesmo shader do Starter");
                Assert.AreEqual(catalog.Resolve(slot, HeroPartCatalog.StarterSet).hidesRegions, part.hidesRegions, "esconde as mesmas regioes do corpo");
            }
            Assert.AreEqual(catalog.Resolve(HeroPartSlot.Head, HeroPartCatalog.StarterSet), catalog.Resolve(HeroPartSlot.Head, "vset.inexistente"), "conjunto desconhecido cai no Starter");
        }
    }
}
