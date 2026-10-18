using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using Echoes.Interop.Native;
using Echoes.Presentation;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Modo de captura do PLAYER para a prancha das telas (-uishots pasta, com -savedir de um save descartavel). Sem janela (-batchmode): a camera da
    /// cena e renderizada a mao numa RenderTexture 1920x1080 e a UI Toolkit vai para outra (PanelSettings.targetTexture); as duas sao compostas em
    /// CPU e gravadas em PNG. Percorre menu, opcoes, Refugio (HUD, pausa, expedicao, relatorio, inventario) e Cripta (HUD, faixa de area, checkpoint,
    /// morte, Fase 2, vitoria) e o Guerreiro com o conjunto Raro. Cada etapa tem log e a execucao inteira tem limite de tempo; nunca roda no jogo normal.
    /// </summary>
    public sealed class UiShotsRunner : MonoBehaviour
    {
        const int Width = 1920, Height = 1080;
        const float StageTimeout = 40f;
        string folder;
        string stage = "inicio";
        RenderTexture sceneRt, uiRt;
        readonly HashSet<PanelSettings> panels = new HashSet<PanelSettings>();

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Boot()
        {
            var path = GameFlow.ArgValue("-uishots");
            if (string.IsNullOrEmpty(path)) return;
            var go = new GameObject("UiShotsRunner");
            DontDestroyOnLoad(go);
            go.AddComponent<UiShotsRunner>().folder = path;
        }

        void Start()
        {
            Directory.CreateDirectory(folder);
            sceneRt = new RenderTexture(Width, Height, 24, RenderTextureFormat.ARGB32) { antiAliasing = 1, name = "UiShotsScene" };
            uiRt = new RenderTexture(Width, Height, 24, RenderTextureFormat.ARGB32) { antiAliasing = 1, name = "UiShotsUi" };
            StartCoroutine(Run());
            StartCoroutine(Watchdog());
        }

        void Stage(string name)
        {
            stage = name;
            Debug.Log("[UiShots] etapa: " + name + " (cena " + SceneManager.GetActiveScene().name + ")");
        }

        IEnumerator Watchdog()
        {
            yield return new WaitForSecondsRealtime(420f);
            Debug.LogError("[UiShots] TIMEOUT geral: parou na etapa '" + stage + "'");
            Application.Quit(1);
        }

        void Fail(string message)
        {
            Debug.LogError("[UiShots] FALHA na etapa '" + stage + "': " + message);
            Application.Quit(1);
        }

        IEnumerator WaitScene(string scene, float settle = 1.2f)
        {
            var t = 0f;
            while (SceneManager.GetActiveScene().name != scene && t < StageTimeout)
            {
                t += Time.unscaledDeltaTime;
                yield return null;
            }
            if (SceneManager.GetActiveScene().name != scene)
            {
                Fail("a cena " + scene + " nao carregou");
                yield break;
            }
            yield return new WaitForSecondsRealtime(settle);
        }

        // ------------------------------------------------------------------------------------------------ captura

        void BindPanels()
        {
            foreach (var doc in FindObjectsByType<UIDocument>(FindObjectsSortMode.None))
            {
                if (doc.panelSettings == null) continue;
                doc.panelSettings.targetTexture = uiRt;
                panels.Add(doc.panelSettings);
            }
        }

        /// <summary>Renderiza a camera da cena na RT (manual) e, se pedido, a UI por cima; grava o PNG.</summary>
        IEnumerator Snap(string file, bool withUi = true, Camera camera = null)
        {
            BindPanels();
            yield return new WaitForEndOfFrame();
            var cam = camera != null ? camera : Camera.main;
            var scene = new Texture2D(Width, Height, TextureFormat.RGBA32, false);
            if (cam != null)
            {
                var previous = cam.targetTexture;
                cam.targetTexture = sceneRt;
                cam.Render();
                cam.targetTexture = previous;
                RenderTexture.active = sceneRt;
                scene.ReadPixels(new Rect(0, 0, Width, Height), 0, 0);
                scene.Apply();
                RenderTexture.active = null;
            }
            else
            {
                var fill = new Color32[Width * Height];
                for (var i = 0; i < fill.Length; i++) fill[i] = new Color32(15, 11, 20, 255); // fundo do menu (sem camera de cena)
                scene.SetPixels32(fill);
            }
            if (withUi)
            {
                var ui = new Texture2D(Width, Height, TextureFormat.RGBA32, false);
                RenderTexture.active = uiRt;
                ui.ReadPixels(new Rect(0, 0, Width, Height), 0, 0);
                ui.Apply();
                RenderTexture.active = null;
                Blend(scene, ui);
                Destroy(ui);
            }
            var path = Path.Combine(folder, file);
            File.WriteAllBytes(path, scene.EncodeToPNG());
            Destroy(scene);
            Debug.Log("[UiShots] capturada: " + path + " (" + new FileInfo(path).Length + " bytes)");
        }

        // Alfa direto (a UI Toolkit grava na RT com o alfa da cobertura): saida = ui sobre a cena.
        static void Blend(Texture2D scene, Texture2D ui)
        {
            var a = scene.GetPixels32();
            var b = ui.GetPixels32();
            for (var i = 0; i < a.Length; i++)
            {
                var alpha = b[i].a / 255f;
                if (alpha <= 0f) continue;
                a[i].r = (byte)Mathf.Clamp(b[i].r * alpha + a[i].r * (1f - alpha), 0f, 255f);
                a[i].g = (byte)Mathf.Clamp(b[i].g * alpha + a[i].g * (1f - alpha), 0f, 255f);
                a[i].b = (byte)Mathf.Clamp(b[i].b * alpha + a[i].b * (1f - alpha), 0f, 255f);
            }
            scene.SetPixels32(a);
            scene.Apply();
        }

        static IEnumerator Settle(float seconds = 0.6f)
        {
            yield return new WaitForSecondsRealtime(seconds);
        }

        static void Teleport(HeroController hero, Vector3 position)
        {
            var controller = hero.GetComponent<CharacterController>();
            controller.enabled = false;
            hero.transform.position = new Vector3(position.x, 0f, position.z);
            controller.enabled = true;
        }

        // ------------------------------------------------------------------------------------------------ roteiro

        IEnumerator Run()
        {
            // ---- menu (S-01), com um save criado so para a captura
            Stage("menu");
            yield return WaitScene(GameFlow.MainMenuScene, 1.0f);
            var menu = FindAnyObjectByType<MainMenuController>();
            var root = FindAnyObjectByType<GameRoot>();
            if (menu == null || root == null) { Fail("sem menu ou GameRoot"); yield break; }
            var rules = GameSession.NativeRules(root);
            if (rules == null) { Fail("sem motor nativo"); yield break; }
            GameSession.Save.NewGame(rules, 0, "Aria");
            GameSession.Save.Current.RecordAreaRun(rules, 0, ExpeditionConfig.CryptMap, true, true);
            GameSession.Save.Save(rules);
            menu.Refresh();
            yield return Settle();
            yield return Snap("01_menu_inicial.png");

            Stage("opcoes");
            menu.Options.Open(menu.GetComponent<UIDocument>().rootVisualElement);
            yield return Settle();
            yield return Snap("02_opcoes_jogo.png");
            menu.Options.ShowTab(OptionsView.Tab.Controls);
            yield return Settle();
            yield return Snap("03_opcoes_controles.png");
            menu.Options.ShowTab(OptionsView.Tab.Access);
            yield return Settle();
            yield return Snap("04_opcoes_acessibilidade.png");
            menu.Options.Close();

            // ---- Refugio
            Stage("refugio");
            GameFlow.StartRefuge();
            yield return WaitScene(GameFlow.RefugeScene, 4.5f); // passa a faixa de area e o fade
            var refuge = FindAnyObjectByType<RefugeController>();
            var hero = FindAnyObjectByType<HeroController>();
            if (refuge == null || hero == null) { Fail("sem Refugio ou heroi"); yield break; }
            TestSettings.HeroGodMode = true;
            yield return Snap("05_refugio_hud.png");

            Stage("pausa");
            var pause = FindAnyObjectByType<PauseController>();
            pause.SetPaused(true);
            yield return Settle();
            yield return Snap("06_pausa.png");
            pause.SetPaused(false);

            Stage("inventario");
            var drop = DropAndPickup(rules);
            Debug.Log("[UiShots] itens pegos: " + drop);
            var inventory = FindAnyObjectByType<InventoryController>();
            inventory.Show();
            yield return Settle(1.0f);
            var items = GameSession.Save.Current.ListItems(0, ItemContainer.Backpack);
            if (items.Count > 0) inventory.SelectUid((items.Find(x => x.Rarity != ItemRarity.Normal) ?? items[0]).Uid);
            yield return Settle();
            yield return Snap("07_inventario.png");
            inventory.Close();

            Stage("relatorio");
            refuge.Config.Hours = 1;
            refuge.StartExpedition();
            refuge.DebugAdvance(3601);
            refuge.StartCollect();
            var wait = 0f;
            while (refuge.IsCollecting && wait < 60f) { wait += Time.unscaledDeltaTime; yield return null; }
            yield return Settle(1.0f);
            yield return Snap("08_relatorio.png");

            Stage("expedicao: regra da dica e bloqueio RF-43");
            refuge.AdjustRule(refuge.LastReport != null ? refuge.LastReport.TipKey : null);
            yield return Settle();
            yield return Snap("09_expedicao_ajustar_regra.png");
            refuge.CloseScreen();
            refuge.Config.Rules.Add(new AiRuleDef("always", 0, "use_skill", "skill.warrior.charge"));
            refuge.OpenExpeditionScreen();
            yield return Settle();
            yield return Snap("10_expedicao_bloqueio_rf43.png");
            refuge.CloseScreen();
            refuge.Config.Rules.RemoveAll(r => r.RefId == "skill.warrior.charge");

            // ---- Cripta: entra pelo "Jogar esta rota agora" (Fervor ligado)
            Stage("cripta");
            RunState.FervorActive = true;
            GameFlow.StartGame();
            yield return WaitScene(GameFlow.CriptaScene, 1.3f);
            hero = FindAnyObjectByType<HeroController>();
            TestSettings.HeroGodMode = true;
            yield return Snap("11_cripta_hud_fervor_faixa_area.png");
            yield return Settle(3.2f); // a faixa de area sai
            yield return Snap("12_cripta_hud.png");

            Stage("checkpoint");
            var zones = new List<CheckpointZone>(FindObjectsByType<CheckpointZone>(FindObjectsSortMode.None));
            zones.Sort((x, y) => string.CompareOrdinal(x.name, y.name));
            CheckpointZone zone = zones.Find(z => z.transform != hero.Checkpoint);
            if (zone != null)
            {
                Teleport(hero, zone.transform.position);
                yield return new WaitForSecondsRealtime(0.12f);
                yield return Snap("13_checkpoint_retorno_visual.png");
            }

            Stage("morte");
            TestSettings.HeroGodMode = false;
            Kill(hero);
            yield return Settle(0.35f);
            yield return Snap("14_morte_nada_perdido.png");
            yield return Settle(2.4f);

            Stage("arena e Fase 2");
            var arena = FindAnyObjectByType<ArenaController>();
            var host = FindAnyObjectByType<CombatSystemHost>();
            TestSettings.HeroGodMode = true;
            Teleport(hero, new Vector3(arena.Trigger.center.x, 0f, arena.Trigger.center.y));
            yield return Settle(1.0f);
            TestSettings.HeroGodMode = false;
            Kill(hero);
            yield return Settle(0.35f);
            yield return Snap("15_morte_arena_luta_recomeca.png");
            yield return Settle(2.4f);
            TestSettings.HeroGodMode = true;
            Teleport(hero, new Vector3(arena.Trigger.center.x, 0f, arena.Trigger.center.y));
            yield return Settle(2.5f);
            var summoner = FindAnyObjectByType<BossSummoner>();
            var skill = host.Rules.FindSkill("skill.warrior.iron_cut");
            var boss = arena.Boss;
            var until = Time.realtimeSinceStartup + 120f;
            while (summoner.Spawned.Count == 0 && !boss.Combatant.IsDead && Time.realtimeSinceStartup < until)
            {
                var info = boss.Logic.Boss.Info;
                var p = boss.Combatant.Position;
                var behind = new PlanarVector(p.X - (float)info.FacingX * 3f, p.Z - (float)info.FacingZ * 3f);
                for (var k = 0; k < 3; k++) host.Combat.ApplySkillHit(hero.Combatant, boss.Combatant, skill, behind);
                yield return new WaitForSecondsRealtime(0.5f);
            }
            Debug.Log("[UiShots] invocadas: " + summoner.Spawned.Count);
            yield return Settle(1.2f);
            yield return Snap("16_fase2_sentinelas_invocadas.png");

            Stage("vitoria");
            var won = new ArenaStateEvent { Phase = ArenaPhase.Won };
            host.Events.Publish(in won);
            yield return Settle(0.9f);
            yield return Snap("17_vitoria_faixa.png");

            Stage("guerreiro raro");
            var modular = hero.GetComponentInChildren<ModularCharacter>();
            if (modular == null) { Fail("heroi sem ModularCharacter"); yield break; }
            for (var i = 0; i < 5; i++) modular.Equip((HeroPartSlot)i, HeroPartCatalog.WarriorRareSet);
            var follow = FindAnyObjectByType<FollowCamera>();
            var cam = Camera.main;
            follow.enabled = false;
            var pos = hero.transform.position;
            cam.transform.position = pos + hero.transform.forward * 3.4f + Vector3.up * 1.4f;
            cam.transform.LookAt(pos + Vector3.up * 1.0f);
            cam.fieldOfView = 30f;
            yield return Settle(0.6f);
            yield return Snap("18_guerreiro_conjunto_raro_frente.png", false);
            cam.transform.position = pos - hero.transform.forward * 3.4f + Vector3.up * 1.4f;
            cam.transform.LookAt(pos + Vector3.up * 1.0f);
            yield return Settle(0.4f);
            yield return Snap("19_guerreiro_conjunto_raro_costas.png", false);
            for (var i = 0; i < 5; i++) modular.Equip((HeroPartSlot)i, HeroPartCatalog.StarterSet);
            cam.transform.position = pos + hero.transform.forward * 3.4f + Vector3.up * 1.4f;
            cam.transform.LookAt(pos + Vector3.up * 1.0f);
            yield return Settle(0.4f);
            yield return Snap("20_guerreiro_conjunto_starter_frente.png", false);

            Stage("fim");
            Debug.Log("[UiShots] concluido em " + folder);
            Application.Quit();
        }

        static void Kill(HeroController hero) => hero.ForceDeathForTest();

        /// <summary>Rola o drop do Guardiao varias vezes e pega tudo (itens Magicos e Raros e moedas) para o inventario da captura.</summary>
        static int DropAndPickup(NativeRulesCore rules)
        {
            var save = GameSession.Save.Current;
            var picked = 0;
            for (var i = 0; i < 4; i++)
            {
                var json = save.DropLoot(rules, i % 2 == 0 ? "loot.crypt.guardian" : "loot.crypt.common", 3, 0, -1, (ulong)(500 + i), out _);
                foreach (var item in ItemInstanceInfo.ListFromJson(json))
                {
                    if (save.Pickup(rules, 0, item.Uid) != PickupDest.NotFound) picked++;
                }
            }
            return picked;
        }
    }
}
