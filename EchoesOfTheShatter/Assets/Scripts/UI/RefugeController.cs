using System;
using System.Collections.Generic;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop.Native;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// O Refugio (hub, docs/16 S-04): Ilsa configura e inicia a expedicao (S-08), Tico mostra o estado e entrega o relatorio (S-09). Telas funcionais
    /// em UI Toolkit; a arte final vem depois da aprovacao dos mockups. Tudo passa por <see cref="ExpeditionService"/> (so chamadas _trusted).
    /// Teclas de teste (acelerador de debug, ligado no prototipo): F8 conquista a Cripta (+5 cargas), F9 avanca 1 h, F10 avanca 12 h.
    /// </summary>
    [RequireComponent(typeof(ScreenHost))]
    public sealed class RefugeController : MonoBehaviour
    {
        [SerializeField] GameRoot root;
        [SerializeField] HeroController hero;

        PlayerInputHandler input;
        ScreenHost host;
        VisualElement overlay, prompt;
        Label promptLabel;
        readonly List<InteractableNpc> npcs = new List<InteractableNpc>();
        readonly ExpeditionConfig config = ExpeditionConfig.Default();
        VisualElement screen;
        bool screenOpen;

        /// <summary>Alguma tela do Refugio esta aberta (a pausa por Esc espera).</summary>
        public static bool AnyScreenOpen { get; private set; }

        public bool ScreenOpen => screenOpen;
        public ExpeditionConfig Config => config;
        LocalizationService Loc => root != null ? root.Localization : null;
        NativeRulesCore Rules => GameSession.NativeRules(root);

        void Start()
        {
            host = GetComponent<ScreenHost>();
            input = FindAnyObjectByType<PlayerInputHandler>();
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (hero == null) hero = FindAnyObjectByType<HeroController>();
            npcs.AddRange(FindObjectsByType<InteractableNpc>(FindObjectsSortMode.None));
            EnsureSave();

            var rootElement = host.Root;
            overlay = new VisualElement { name = "refuge-overlay" };
            overlay.style.position = Position.Absolute;
            overlay.style.left = 0;
            overlay.style.right = 0;
            overlay.style.top = 0;
            overlay.style.bottom = 0;
            overlay.pickingMode = PickingMode.Ignore;
            rootElement.Add(overlay);

            prompt = new VisualElement();
            prompt.style.position = Position.Absolute;
            prompt.style.bottom = 160;
            prompt.style.alignSelf = Align.Center;
            prompt.style.left = new Length(30, LengthUnit.Percent);
            prompt.style.right = new Length(30, LengthUnit.Percent);
            prompt.style.backgroundColor = new Color(0.07f, 0.06f, 0.09f, 0.9f);
            prompt.style.display = DisplayStyle.None;
            prompt.pickingMode = PickingMode.Ignore;
            promptLabel = ScreenKit.Line(prompt, string.Empty, 24, ScreenKit.Gold, true);
            promptLabel.style.unityTextAlign = TextAnchor.MiddleCenter;
            rootElement.Add(prompt);

            // Teste do player (-smoke): conquista a Cripta, inicia, avanca o relogio, coleta e registra o relatorio no log (e na captura -shot).
            if (GameFlow.ArgValue("-smoke") != null) StartCoroutine(SmokeRun());
            if (!string.IsNullOrEmpty(GameSession.PendingToastKey))
            {
                ScreenHost.Toast(Loc.Get(GameSession.PendingToastKey));
                GameSession.PendingToastKey = null;
            }
            else if (GameSession.Save.Current != null && Rules != null)
            {
                var charges = GameSession.Save.Current.Summary.MarkerCharges;
                ScreenHost.Toast(Loc.Get("ui.hud.charges") + " " + charges + "/12");
            }
        }

        System.Collections.IEnumerator SmokeRun()
        {
            yield return new WaitForSecondsRealtime(2f);
            var shotBase = GameFlow.ArgValue("-shot");
            if (!string.IsNullOrEmpty(shotBase)) ScreenCapture.CaptureScreenshot(shotBase.Replace(".png", "_hud.png"));
            yield return new WaitForSecondsRealtime(1f);
            DebugConquerCrypt();
            config.Hours = 1;
            var check = StartExpedition();
            Debug.Log("[Smoke] expedicao iniciada: " + check + ", heroi ocupado=" + GameSession.Expedition.IsHeroBusy);
            yield return new WaitForSecondsRealtime(1f);
            DebugAdvance(3601);
            StartCollect();
            while (IsCollecting) yield return null;
            var status = LastCollectStatus;
            Debug.Log("[Smoke] coleta: " + status + (LastReport != null ? ", encontros=" + LastReport.Encounters + ", xp=" + LastReport.Xp + ", estimativa=" + LastReport.IsEstimate : string.Empty));
            yield return new WaitForSecondsRealtime(1f);
            var shot = GameFlow.ArgValue("-shot");
            if (!string.IsNullOrEmpty(shot)) ScreenCapture.CaptureScreenshot(shot);
            yield return new WaitForSecondsRealtime(1f);
            Debug.Log("[Smoke] segunda coleta: " + GameSession.Expedition.Collect(Rules, out _));
        }

        // O Refugio aberto direto no editor (sem passar pelo menu) joga com o slot 1: carrega ou cria um Guerreiro.
        void EnsureSave()
        {
            var rules = Rules;
            if (rules == null || GameSession.Save.HasSave) return;
            if (GameSession.Save.Load(rules, 0) != LoadOutcome.Ok) GameSession.Save.NewGame(rules, 0, "Guerreiro");
        }

        void Update()
        {
            if (job != null)
            {
                if (bar != null) bar.value = job.Progress * 100f;
                if (job.Done) CompleteCollect();
                return;
            }
            var keyboard = Keyboard.current;
            if (keyboard != null && SaveSettings.DebugAccelerator) DebugKeys(keyboard);
            if (screenOpen)
            {
                if (keyboard != null && keyboard[Key.Escape].wasPressedThisFrame) CloseScreen();
                return;
            }
            var near = NearestNpc();
            if (near == null)
            {
                prompt.style.display = DisplayStyle.None;
                return;
            }
            promptLabel.text = "[" + InteractGlyph() + "] " + Loc.Get("npc." + near.npcId + ".name") + " - " + Loc.Get("ui.common.talk");
            prompt.style.display = DisplayStyle.Flex;
            if (input != null && input.IsReady ? input.InteractPressed : keyboard != null && keyboard[Key.F].wasPressedThisFrame) Interact(near.npcId);
        }

        string InteractGlyph() => input != null && input.IsReady ? input.InteractGlyph : "F";

        InteractableNpc NearestNpc()
        {
            if (hero == null) return null;
            InteractableNpc best = null;
            var bestDistance = float.MaxValue;
            foreach (var npc in npcs)
            {
                var d = hero.transform.position - npc.transform.position;
                d.y = 0f;
                var distance = d.magnitude;
                if (distance <= npc.radius && distance < bestDistance)
                {
                    best = npc;
                    bestDistance = distance;
                }
            }
            return best;
        }

        void DebugKeys(Keyboard keyboard)
        {
            if (keyboard[Key.F8].wasPressedThisFrame) DebugConquerCrypt();
            if (keyboard[Key.F9].wasPressedThisFrame) DebugAdvance(3600);
            if (keyboard[Key.F10].wasPressedThisFrame) DebugAdvance(12 * 3600);
        }

        /// <summary>Teste: marca a Cripta como dominada (+5 cargas) sem precisar vencer o Guardiao.</summary>
        public void DebugConquerCrypt()
        {
            var rules = Rules;
            if (rules == null || !GameSession.Save.HasSave) return;
            var reward = GameSession.Save.Current.RecordAreaRun(rules, 0, ExpeditionConfig.CryptMap, true, true);
            GameSession.Save.Save(rules);
            ScreenHost.Toast("[debug] " + (reward.NewConquest ? "Cripta dominada, +" + reward.ChargesGained + " cargas" : "Cripta ja dominada"));
        }

        /// <summary>Teste: avanca o relogio local do jogo (acelerador de debug da expedicao).</summary>
        public void DebugAdvance(long seconds)
        {
            SystemGameClock.DebugOffsetSeconds += seconds;
            ScreenHost.Toast("[debug] +" + (seconds / 3600) + " h");
        }

        // ---------------------------------------------------------------------------------------------- conversas

        public void Interact(string npcId)
        {
            if (npcId == InteractableNpc.Ilsa) TalkToIlsa();
            else TalkToTico();
        }

        VisualElement OpenScreen()
        {
            CloseScreen();
            screenOpen = true;
            AnyScreenOpen = true;
            Time.timeScale = 0f; // o Refugio nao tem o que pausar alem do heroi andando
            prompt.style.display = DisplayStyle.None;
            var backdrop = MenuUi.Backdrop(overlay, 0.55f);
            backdrop.pickingMode = PickingMode.Position;
            screen = backdrop;
            return MenuUi.Card(backdrop);
        }

        public void CloseScreen()
        {
            if (screen != null) screen.RemoveFromHierarchy();
            screen = null;
            if (screenOpen) Time.timeScale = 1f;
            screenOpen = false;
            AnyScreenOpen = false;
        }

        string Hms(long seconds)
        {
            var hours = seconds / 3600;
            var minutes = (seconds % 3600) / 60;
            return ScreenKit.Fmt(Loc, "report.time.value", ("hours", hours.ToString()), ("minutes", minutes.ToString()));
        }

        /// <summary>Ilsa: fala conforme o estado e, se a rota esta liberada, abre a configuracao da expedicao.</summary>
        public void TalkToIlsa()
        {
            var rules = Rules;
            if (rules == null) return;
            var card = OpenScreen();
            MenuUi.Title(card, "npc.ilsa.name", Loc, 36);
            var state = GameSession.Expedition.State(rules);
            var busy = state.Phase == ExpeditionPhase.Running || state.Phase == ExpeditionPhase.ReadyToCollect;
            if (busy && SaveSettings.HeroBusyDuringExpedition)
            {
                ScreenKit.Line(card, Loc.Get("dlg.ilsa.busy"));
                if (state.Phase == ExpeditionPhase.Running)
                    ScreenKit.Line(card, ScreenKit.Fmt(Loc, "ui.exp.in_progress", ("time", Hms(state.SecondsLeft))), 20, ScreenKit.Muted);
                MenuUi.MakeButton(card, Loc.Get("ui.common.close"), CloseScreen);
                return;
            }
            var check = GameSession.Expedition.Check(rules, config, out _);
            if (check == StartCheck.MapNotConquered)
            {
                ScreenKit.Line(card, Loc.Get("dlg.ilsa.not_dominated"));
                MenuUi.MakeButton(card, Loc.Get("ui.common.close"), CloseScreen);
                return;
            }
            ScreenKit.Line(card, Loc.Get("dlg.ilsa.greeting"));
            ScreenKit.Line(card, Loc.Get(check == StartCheck.NotEnoughCharges ? "dlg.ilsa.no_charges" : "dlg.ilsa.offer"), 20, ScreenKit.Muted);
            MenuUi.MakeButton(card, Loc.Get("ui.exp.configure"), OpenExpeditionScreen);
            MenuUi.MakeButton(card, Loc.Get("ui.common.close"), CloseScreen);
        }

        // ---------------------------------------------------------------------------------------------- S-08 expedicao

        static readonly string[] Objectives = { "xp", "gold", "materials" };

        string RuleLabel(AiRuleDef rule)
        {
            if (rule.Action == "use_potion") return ScreenKit.Fmt(Loc, "ui.exp.rule.potion_below", ("pct", Mathf.RoundToInt((float)rule.Param * 100f).ToString()));
            if (rule.Condition == "always") return Loc.Get("ui.exp.rule.default_attack");
            return ScreenKit.Fmt(Loc, "ui.exp.rule.skill_if_enemies", ("skill", Loc.Get(rule.RefId + ".name")), ("n", Mathf.RoundToInt((float)rule.Param).ToString()));
        }

        static readonly AiRuleDef[] Presets =
        {
            new AiRuleDef("life_below", 0.35, "use_potion", string.Empty),
            new AiRuleDef("enemies_at_least", 3, "use_skill", "skill.warrior.stone_rift"),
            new AiRuleDef("enemies_at_least", 2, "use_skill", "skill.warrior.shield_bash"),
            new AiRuleDef("always", 0, "use_skill", "skill.warrior.iron_cut"),
        };

        int MaxHours()
        {
            var charges = GameSession.Save.Current != null ? GameSession.Save.Current.Summary.MarkerCharges : 0;
            return Mathf.Clamp(charges, 1, 12);
        }

        public void OpenExpeditionScreen()
        {
            var rules = Rules;
            if (rules == null) return;
            var card = OpenScreen();
            card.style.minWidth = 760;
            config.Hours = Mathf.Clamp(config.Hours, 1, MaxHours());
            Render();

            void Render()
            {
                card.Clear();
                var charges = GameSession.Save.Current.Summary.MarkerCharges;
                MenuUi.Title(card, "ui.exp.configure", Loc, 34);
                ScreenKit.Line(card, ScreenKit.Fmt(Loc, "ui.exp.charges", ("n", charges.ToString()), ("max", "12")), 22, ScreenKit.Gold);
                ScreenKit.Line(card, ScreenKit.Fmt(Loc, "ui.exp.area.crypt", ("min", "2"), ("max", "4")));

                var objective = ScreenKit.Row(card);
                ScreenKit.Line(objective, Loc.Get("ui.exp.objective"));
                ScreenKit.SmallButton(objective, Loc.Get("ui.exp.objective." + config.Objective), () =>
                {
                    config.Objective = Objectives[(Array.IndexOf(Objectives, config.Objective) + 1) % Objectives.Length];
                    Render();
                });

                var duration = ScreenKit.Row(card);
                ScreenKit.Line(duration, Loc.Get("ui.exp.duration"));
                var spin = new VisualElement();
                spin.style.flexDirection = FlexDirection.Row;
                duration.Add(spin);
                ScreenKit.SmallButton(spin, "-", () => { config.Hours = Mathf.Max(1, config.Hours - 1); Render(); });
                ScreenKit.Line(spin, ScreenKit.Fmt(Loc, "ui.exp.hours", ("hours", config.Hours.ToString())), 24, ScreenKit.Text, true);
                ScreenKit.SmallButton(spin, "+", () => { config.Hours = Mathf.Min(MaxHours(), config.Hours + 1); Render(); });
                if (MaxHours() < 12) ScreenKit.Line(card, ScreenKit.Fmt(Loc, "ui.exp.duration_cap", ("n", MaxHours().ToString())), 18, ScreenKit.Muted);
                ScreenKit.Line(card, ScreenKit.Fmt(Loc, "ui.exp.cost", ("n", config.Hours.ToString())), 20, ScreenKit.Muted);

                ScreenKit.Line(card, Loc.Get("ui.exp.rules"), 22, ScreenKit.Gold, true);
                for (var i = 0; i < config.Rules.Count; i++)
                {
                    var index = i;
                    var row = ScreenKit.Row(card);
                    ScreenKit.Line(row, ScreenKit.Fmt(Loc, "ui.exp.rule_slot", ("n", (i + 1).ToString())) + ": " + RuleLabel(config.Rules[i]), 20);
                    var tools = new VisualElement();
                    tools.style.flexDirection = FlexDirection.Row;
                    row.Add(tools);
                    ScreenKit.SmallButton(tools, "^", () => { Swap(index, index - 1); Render(); });
                    ScreenKit.SmallButton(tools, "v", () => { Swap(index, index + 1); Render(); });
                    ScreenKit.SmallButton(tools, "x", () => { config.Rules.RemoveAt(index); Render(); });
                }
                if (config.Rules.Count < 6)
                    ScreenKit.SmallButton(card, Loc.Get("ui.exp.rule_add"), () => { AddNextPreset(); Render(); });
                else ScreenKit.Line(card, ScreenKit.Fmt(Loc, "ui.exp.rules_full", ("n", "6")), 18, ScreenKit.Muted);

                // Previsao em faixa e selo "Estimativa" (o core diz se ainda e estimativa).
                ScreenKit.Line(card, Loc.Get("ui.exp.forecast"), 22, ScreenKit.Gold, true);
                if (GameSession.Expedition.Preview(rules, config, out var bands))
                {
                    ScreenKit.Line(card, ScreenKit.Fmt(Loc, "ui.exp.forecast.value", ("min", Mathf.RoundToInt((float)bands.XpP10).ToString()), ("max", Mathf.RoundToInt((float)bands.XpP90).ToString())), 20);
                    ScreenKit.Line(card, ScreenKit.Fmt(Loc, "ui.exp.forecast.gold", ("min", Mathf.RoundToInt((float)bands.GoldP10).ToString()), ("max", Mathf.RoundToInt((float)bands.GoldP90).ToString())), 20);
                    var risk = bands.RetreatProbability < 0.1 ? "low" : bands.RetreatProbability < 0.35 ? "medium" : "high";
                    ScreenKit.Line(card, ScreenKit.Fmt(Loc, "ui.exp.forecast.risk", ("risk", Loc.Get("ui.exp.risk." + risk))), 20);
                    if (bands.Calibration == Calibration.ManualEstimate)
                    {
                        var badge = ScreenKit.Line(card, Loc.Get("ui.exp.estimate.badge"), 18, ScreenKit.Gold, true);
                        badge.tooltip = Loc.Get("ui.exp.estimate.desc");
                        ScreenKit.Line(card, Loc.Get("ui.exp.estimate.desc"), 16, ScreenKit.Muted);
                    }
                }

                var check = GameSession.Expedition.Check(rules, config, out _);
                if (check != StartCheck.Ok) ScreenKit.Line(card, ErrorText(check), 20, ScreenKit.Bad);
                var buttons = ScreenKit.Row(card);
                var start = ScreenKit.SmallButton(buttons, Loc.Get("ui.exp.start"), ConfirmStart);
                start.SetEnabled(check == StartCheck.Ok);
                ScreenKit.SmallButton(buttons, Loc.Get("ui.common.close"), CloseScreen);
            }
        }

        string ErrorText(StartCheck check)
        {
            switch (check)
            {
                case StartCheck.MapNotConquered: return Loc.Get("ui.exp.err.not_dominated");
                case StartCheck.NotEnoughCharges: return Loc.Get("ui.exp.err.no_charges");
                case StartCheck.AnotherRunning: return Loc.Get("ui.exp.err.busy");
                case StartCheck.InvalidDuration: return Loc.Get("ui.exp.err.duration_range");
                case StartCheck.TooManyRules: return Loc.Get("ui.exp.err.rules_max");
                case StartCheck.IdleIncompatible: return ScreenKit.Fmt(Loc, "ui.exp.err.skill_blocked", ("skill", string.Empty));
                default: return check.ToString();
            }
        }

        void Swap(int a, int b)
        {
            if (b < 0 || b >= config.Rules.Count) return;
            var tmp = config.Rules[a];
            config.Rules[a] = config.Rules[b];
            config.Rules[b] = tmp;
        }

        void AddNextPreset()
        {
            foreach (var preset in Presets)
            {
                var exists = config.Rules.Exists(r => r.Condition == preset.Condition && r.Action == preset.Action && r.RefId == preset.RefId && Math.Abs(r.Param - preset.Param) < 1e-6);
                if (!exists)
                {
                    config.Rules.Add(new AiRuleDef(preset.Condition, preset.Param, preset.Action, preset.RefId));
                    return;
                }
            }
        }

        void ConfirmStart()
        {
            var card = OpenScreen();
            MenuUi.Title(card, "ui.exp.start_title", Loc, 34);
            ScreenKit.Line(card, Loc.Get("ui.exp.start_confirm"));
            var row = ScreenKit.Row(card);
            ScreenKit.SmallButton(row, Loc.Get("ui.exp.start"), () => StartExpedition());
            ScreenKit.SmallButton(row, Loc.Get("ui.common.back"), OpenExpeditionScreen);
        }

        /// <summary>Inicia pelo relogio confiavel (confirmado na tela) e fecha com a dica de que pode fechar o jogo.</summary>
        public StartCheck StartExpedition()
        {
            var rules = Rules;
            var check = GameSession.Expedition.Start(rules, config);
            CloseScreen();
            ScreenHost.Toast(check == StartCheck.Ok ? Loc.Get("ui.exp.started_hint") : ErrorText(check));
            return check;
        }

        // ---------------------------------------------------------------------------------------------- S-09 relatorio

        /// <summary>Tico: nada, em curso ou pronto. Pronto: "Coletar" entrega o loot (uma vez so) e mostra o relatorio.</summary>
        public void TalkToTico()
        {
            var rules = Rules;
            if (rules == null) return;
            var card = OpenScreen();
            MenuUi.Title(card, "npc.tico.name", Loc, 36);
            var state = GameSession.Expedition.State(rules);
            switch (state.Phase)
            {
                case ExpeditionPhase.Running:
                    ScreenKit.Line(card, Loc.Get("dlg.tico.waiting"));
                    ScreenKit.Line(card, ScreenKit.Fmt(Loc, "ui.exp.remaining", ("time", Hms(state.SecondsLeft))), 20, ScreenKit.Muted);
                    MenuUi.MakeButton(card, Loc.Get("ui.common.close"), CloseScreen);
                    break;
                case ExpeditionPhase.ReadyToCollect:
                    ScreenKit.Line(card, Loc.Get("dlg.tico.report_ready"));
                    MenuUi.MakeButton(card, Loc.Get("ui.exp.collect"), () => StartCollect());
                    MenuUi.MakeButton(card, Loc.Get("ui.common.close"), CloseScreen);
                    break;
                default:
                    ScreenKit.Line(card, Loc.Get("dlg.tico.nothing"));
                    MenuUi.MakeButton(card, Loc.Get("ui.common.close"), CloseScreen);
                    break;
            }
        }

        public ExpeditionReport LastReport { get; private set; }

        CollectJob job;
        ProgressBar bar;

        public bool IsCollecting => job != null;
        public CollectStatus LastCollectStatus { get; private set; } = CollectStatus.Error;

        /// <summary>
        /// Coleta fora da main thread: mostra "O Tico esta voltando..." com a barra de progresso da simulacao em fatias; quando termina (uma vez so, pelo core)
        /// mostra o relatorio com o selo Estimativa.
        /// </summary>
        public CollectJob StartCollect()
        {
            if (job != null) return job;
            job = GameSession.Expedition.CollectAsync(Rules);
            if (job.Done)
            {
                CompleteCollect();
                return job;
            }
            var card = OpenScreen();
            MenuUi.Title(card, "ui.loading.tico", Loc, 34);
            bar = new ProgressBar { lowValue = 0f, highValue = 100f };
            bar.style.height = 28;
            bar.style.marginTop = 16;
            card.Add(bar);
            return job;
        }

        void CompleteCollect()
        {
            var finished = job;
            job = null;
            GameSession.Expedition.FinishCollect(Rules, finished);
            LastCollectStatus = finished.Status;
            if (finished.Status != CollectStatus.Collected)
            {
                CloseScreen();
                return;
            }
            ShowReport(finished.Report);
        }

        void ShowReport(ExpeditionReport report)
        {
            LastReport = report;
            var card = OpenScreen();
            card.style.minWidth = 700;
            MenuUi.Title(card, "report.title", Loc, 34);
            if (report.IsEstimate)
            {
                var badge = ScreenKit.Line(card, Loc.Get("ui.exp.estimate.badge"), 18, ScreenKit.Gold, true);
                badge.tooltip = Loc.Get("ui.exp.estimate.desc");
            }
            ScreenKit.Line(card, Loc.Get("dlg.tico.delivery"), 20, ScreenKit.Muted);
            Field(card, "report.time", Hms((long)report.EffectiveSeconds));
            Field(card, "report.encounters", report.Encounters.ToString());
            Field(card, "report.potions", report.PotionsUsed.ToString());
            Field(card, "report.stop", Loc.Get(report.StopKey));
            Field(card, "ui.exp.objective.xp", Mathf.RoundToInt((float)report.Xp).ToString());
            Field(card, "ui.common.gold", report.Gold.ToString());
            Field(card, "report.loot", report.ItemCount == 0
                ? Loc.Get("report.empty")
                : Loc.Get("rarity.normal.name") + " " + report.CommonCount + " - " + Loc.Get("rarity.magic.name") + " " + report.MagicCount + " - " + Loc.Get("rarity.rare.name") + " " + report.RareCount);
            if (!string.IsNullOrEmpty(report.TipKey)) Field(card, "report.tip", Loc.Get(report.TipKey));
            ScreenKit.Line(card, Loc.Get("report.invite"), 18, ScreenKit.Muted);
            var row = ScreenKit.Row(card);
            ScreenKit.SmallButton(row, Loc.Get("ui.exp.configure"), OpenExpeditionScreen);
            ScreenKit.SmallButton(row, Loc.Get("ui.common.close"), CloseScreen);
        }

        void Field(VisualElement card, string labelKey, string value)
        {
            var row = ScreenKit.Row(card);
            ScreenKit.Line(row, Loc.Get(labelKey), 20, ScreenKit.Muted);
            ScreenKit.Line(row, value, 20);
        }
    }
}
