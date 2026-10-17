using Echoes.Core;
using Echoes.Interop.Native;
using UnityEngine;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Tela inicial: titulo (chave de Loc), Jogar, resolucao/janela e Sair. Jogar abre os slots de save (o numero vem de SaveSettings.SlotCount; com 1
    /// slot entra direto: carrega o save ou pede o nome do heroi) e leva ao Refugio. Precisa de um UIDocument com o PanelSettings e de um GameRoot.
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

        NativeRulesCore Rules => GameSession.NativeRules(root);

        void Start()
        {
            GameSettings.ApplySaved();
            GameSession.Save.LoadedFromBackup += (slot, backup) => GameSession.PendingToastKey = "ui.save.backup_loaded"; // o aviso aparece no Refugio
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            loc = root != null ? root.Localization : null;
            rootElement = GetComponent<UIDocument>().rootVisualElement;
            ShowMain();

            // Teste do player: -shot <arquivo.png> salva uma captura da tela inicial apos 2 s.
            shotPath = GameFlow.ArgValue("-shot");
            if (!string.IsNullOrEmpty(shotPath)) shotAt = Time.realtimeSinceStartup + 2f;
            if (GameFlow.AutoStartRequested) autoStartAt = Time.realtimeSinceStartup + autoStartDelay;
        }

        void Fresh()
        {
            rootElement.Clear();
            backdrop = MenuUi.Backdrop(rootElement, 1f);
            card = MenuUi.Card(backdrop);
        }

        void ShowMain()
        {
            Fresh();
            MenuUi.Title(card, "ui.menu.title", loc, 54);
            MenuUi.MakeButton(card, loc.Get("ui.menu.play"), OnPlay).name = "play";
            MenuUi.AddDisplayOptions(card, loc);
            MenuUi.MakeButton(card, loc.Get("ui.menu.quit"), GameFlow.Quit).name = "quit";
        }

        void OnPlay()
        {
            if (Rules == null)
            {
                ShowMessage(loc.Get("ui.error.content_load"));
                return;
            }
            if (SaveSettings.SlotCount == 1) PlaySlot(0);
            else ShowSlots();
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
                OnPlay();
            }
        }
    }
}
