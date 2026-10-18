using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop.Native;
using UnityEngine;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Menu inicial (docs/16 S-01): Continuar (primario quando ha save, com a legenda do save: nome, classe, nivel, area e o selo "Expedicao pronta"),
    /// Novo jogo, Carregar (quando ha varios slots), Opcoes, Sair, a versao no canto e o link "Abrir pasta de logs". Continuar e Novo jogo levam ao
    /// Refugio (o numero de slots vem de SaveSettings.SlotCount; com 1 slot Novo jogo sobre um save existente pede para apagar antes).
    /// Argumentos de teste: -autostart (entra sozinha), -shot arquivo.png (captura a tela inicial).
    /// </summary>
    [RequireComponent(typeof(UIDocument))]
    public sealed class MainMenuController : MonoBehaviour
    {
        [SerializeField] GameRoot root;
        [SerializeField, Min(0f)] float autoStartDelay = 1.5f;
        float autoStartAt = -1f;
        float shotAt = -1f;
        string shotPath;
        VisualElement rootElement;
        VisualElement backdrop;
        VisualElement card;
        LocalizationService loc;
        OptionsView options;
        bool inMain;

        public OptionsView Options => options;
        NativeRulesCore Rules => GameSession.NativeRules(root);

        void Start()
        {
            GameSettings.ApplySaved();
            GameSession.Save.LoadedFromBackup += (slot, backup) => GameSession.PendingToastKey = "ui.save.backup_loaded"; // o aviso aparece no Refugio
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            loc = root != null ? root.Localization : null;
            rootElement = GetComponent<UIDocument>().rootVisualElement;
            options = new OptionsView(loc, PlayerInputHandler.FindLoadedActions(), ShowMain, true);
            loc.CultureChanged += OnCultureChanged;
            ShowMain();

            // Teste do player: -shot <arquivo.png> salva uma captura da tela inicial apos 2 s.
            shotPath = GameFlow.ArgValue("-shot");
            if (!string.IsNullOrEmpty(shotPath)) shotAt = Time.realtimeSinceStartup + 2f;
            if (GameFlow.AutoStartRequested) autoStartAt = Time.realtimeSinceStartup + autoStartDelay;
        }

        void OnDestroy()
        {
            if (loc != null) loc.CultureChanged -= OnCultureChanged;
        }

        void OnCultureChanged()
        {
            if (inMain && !options.IsOpen) ShowMain(); // idioma trocado: o menu se refaz sem reiniciar
        }

        void Fresh()
        {
            inMain = false;
            rootElement.Clear();
            backdrop = MenuUi.Backdrop(rootElement, 1f);
            card = MenuUi.Card(backdrop);
        }

        /// <summary>Slot do Continuar: o save mais recente entre os slots validos (-1 se nao ha save).</summary>
        public int ContinueSlot(out SlotInfo info)
        {
            info = default;
            var best = -1;
            if (Rules == null) return best;
            for (var slot = 0; slot < SaveSettings.SlotCount; slot++)
            {
                var candidate = GameSession.Save.Peek(Rules, slot);
                if (!candidate.Exists) continue;
                if (best < 0 || candidate.LastSeenUtc > info.LastSeenUtc)
                {
                    best = slot;
                    info = candidate;
                }
            }
            return best;
        }

        /// <summary>Refaz a tela inicial (o save pode ter mudado fora do menu: testes e capturas).</summary>
        public void Refresh() => ShowMain();

        void ShowMain()
        {
            Fresh();
            inMain = true;
            MenuUi.Title(card, "ui.menu.title", loc, 54);
            var slot = ContinueSlot(out var info);
            if (slot >= 0)
            {
                MenuUi.MakeButton(card, loc.Get("ui.menu.continue"), () => PlaySlot(slot)).name = "continue";
                var legend = ScreenKit.Line(card, ContinueLegend(info), 20, ScreenKit.Muted);
                legend.name = "continue-legend";
                legend.style.unityTextAlign = TextAnchor.MiddleCenter;
                if (info.ExpeditionReady)
                {
                    var seal = ScreenKit.Line(card, loc.Get("ui.menu.expedition_ready"), 20, ScreenKit.Gold, true);
                    seal.name = "expedition-seal";
                    seal.style.unityTextAlign = TextAnchor.MiddleCenter;
                }
            }
            MenuUi.MakeButton(card, loc.Get("ui.menu.new_game"), OnNewGame).name = "play";
            if (SaveSettings.SlotCount > 1) MenuUi.MakeButton(card, loc.Get("ui.menu.load"), ShowSlots).name = "load";
            MenuUi.MakeButton(card, loc.Get("ui.menu.options"), OpenOptions).name = "options";
            MenuUi.MakeButton(card, loc.Get("ui.menu.quit"), GameFlow.Quit).name = "quit";

            // Versao no canto (RNF-11) e o link para a pasta de logs.
            var version = new Label(ScreenKit.Fmt(loc, "ui.menu.version", ("version", Application.version)));
            version.name = "version";
            version.style.position = Position.Absolute;
            version.style.right = 24;
            version.style.bottom = 18;
            version.style.fontSize = 18;
            version.style.color = ScreenKit.Muted;
            backdrop.Add(version);
            var logs = new Label(loc.Get("ui.common.open_logs")) { name = "open-logs" };
            logs.style.position = Position.Absolute;
            logs.style.left = 24;
            logs.style.bottom = 18;
            logs.style.fontSize = 18;
            logs.style.color = ScreenKit.Gold;
            logs.style.unityFontStyleAndWeight = FontStyle.Italic;
            logs.RegisterCallback<ClickEvent>(_ => MenuUi.OpenLogsFolder());
            backdrop.Add(logs);
        }

        /// <summary>"Aria - Guerreiro · Nivel 3 - Refugio do Marco": nome, classe e nivel (Loc) e a area onde o Continuar entra.</summary>
        string ContinueLegend(SlotInfo info)
        {
            var classLevel = ScreenKit.Fmt(loc, "ui.save.card_class_level", ("level", info.Level.ToString()));
            return info.CharacterName + " - " + classLevel + " - " + loc.Get("area.refuge.name") + (info.UsedBackup > 0 ? " - " + loc.Get("ui.save.backup_flag") : string.Empty);
        }

        void OpenOptions()
        {
            options.Open(rootElement);
        }

        void OnNewGame()
        {
            if (Rules == null)
            {
                ShowMessage(loc.Get("ui.error.content_load"));
                return;
            }
            if (SaveSettings.SlotCount == 1)
            {
                var info = GameSession.Save.Peek(Rules, 0);
                if (info.Exists) ShowOverwrite(info);
                else ShowNameEntry(0);
            }
            else ShowSlots();
        }

        // Novo jogo com 1 slot e save existente: so apaga depois de segurar 1 s (docs/16 S-02).
        void ShowOverwrite(SlotInfo info)
        {
            Fresh();
            MenuUi.Title(card, "ui.save.delete_title", loc, 36);
            ScreenKit.Line(card, ScreenKit.Fmt(loc, "ui.save.delete_body", ("name", info.CharacterName), ("n", "1")), 24).style.unityTextAlign = TextAnchor.MiddleCenter;
            var hold = ScreenKit.HoldButton(card, loc.Get("ui.common.hold_confirm"), 1f, () => { GameSession.Save.Delete(0); ShowNameEntry(0); });
            hold.name = "overwrite-hold";
            MenuUi.MakeButton(card, loc.Get("ui.common.back"), ShowMain);
        }

        void ShowMessage(string text)
        {
            Fresh();
            ScreenKit.Line(card, text, 24).style.unityTextAlign = TextAnchor.MiddleCenter;
            MenuUi.MakeButton(card, loc.Get("ui.common.back"), ShowMain);
        }

        void ShowSlots()
        {
            Fresh();
            card.style.minWidth = 720;
            MenuUi.Title(card, "ui.save.title", loc, 40);
            for (var slot = 0; slot < SaveSettings.SlotCount; slot++)
            {
                var index = slot;
                var info = GameSession.Save.Peek(Rules, slot);
                var row = ScreenKit.Row(card);
                row.style.marginTop = 10;
                var text = info.Exists
                    ? info.CharacterName + " - " + ScreenKit.Fmt(loc, "ui.save.card_class_level", ("level", info.Level.ToString())) + (info.ExpeditionRunning ? " - " + loc.Get("ui.exp.running") : string.Empty) + (info.UsedBackup > 0 ? " - " + loc.Get("ui.save.backup_flag") : string.Empty)
                    : ScreenKit.Fmt(loc, "ui.save.slot", ("n", (slot + 1).ToString())) + " - " + loc.Get("ui.save.slot_empty");
                ScreenKit.Line(row, text, 24);
                var buttons = new VisualElement();
                buttons.style.flexDirection = FlexDirection.Row;
                row.Add(buttons);
                ScreenKit.SmallButton(buttons, info.Exists ? loc.Get("ui.save.load") : loc.Get("ui.save.new_game"), () => PlaySlot(index));
                if (info.Exists) ScreenKit.HoldButton(buttons, loc.Get("ui.save.delete"), 1f, () => { GameSession.Save.Delete(index); ShowSlots(); });
            }
            MenuUi.MakeButton(card, loc.Get("ui.common.back"), ShowMain);
        }

        /// <summary>Carrega o slot; se nao existe, pede o nome e cria o jogo novo.</summary>
        void PlaySlot(int slot)
        {
            var outcome = GameSession.Save.Load(Rules, slot);
            switch (outcome)
            {
                case LoadOutcome.Ok:
                    EnterGame();
                    break;
                case LoadOutcome.NotFound:
                    ShowNameEntry(slot);
                    break;
                case LoadOutcome.VersionMismatch:
                    ShowMessage(loc.Get("ui.save.too_new"));
                    break;
                default:
                    ShowMessage(loc.Get("ui.save.all_corrupt"));
                    break;
            }
        }

        void ShowNameEntry(int slot)
        {
            Fresh();
            MenuUi.Title(card, "ui.menu.new_game", loc, 40);
            var field = new TextField { maxLength = 16, value = loc.TryGet("ui.create.default_name", out var def) ? def : "Guerreiro" };
            field.style.fontSize = 28;
            card.Add(field);
            MenuUi.MakeButton(card, loc.Get("ui.common.confirm"), () =>
            {
                if (!GameSession.Save.NewGame(Rules, slot, field.value)) ShowMessage(loc.Get("ui.save.all_corrupt"));
                else EnterGame();
            });
            MenuUi.MakeButton(card, loc.Get("ui.common.back"), ShowMain);
            // Teste do player (-autostart): confirma sozinho com o nome padrao.
            if (GameFlow.AutoStartRequested) card.schedule.Execute(() => { if (GameSession.Save.NewGame(Rules, slot, field.value)) EnterGame(); }).StartingIn(800);
        }

        void EnterGame()
        {
            RunState.Reset();
            GameFlow.StartRefuge();
        }

        void Update()
        {
            if (shotAt > 0f && Time.realtimeSinceStartup >= shotAt)
            {
                shotAt = -1f;
                ScreenCapture.CaptureScreenshot(shotPath);
            }
            if (autoStartAt > 0f && Time.realtimeSinceStartup >= autoStartAt)
            {
                autoStartAt = -1f;
                // -autostart: com save entra pelo Continuar, sem save cria o jogo novo.
                if (ContinueSlot(out _) >= 0) PlaySlot(ContinueSlot(out _));
                else OnNewGame();
            }
        }
    }
}
