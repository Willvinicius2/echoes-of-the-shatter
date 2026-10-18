using Echoes.Core;
using Echoes.Gameplay;
using UnityEngine;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Pausa (docs/16 S-10): Esc pausa e abre Continuar, Opcoes, Abrir pasta de logs, Menu principal e Sair do jogo. A pausa para o tempo do jogo
    /// (Time.timeScale = 0; so a pausa usa isso, o hitstop nunca) e o audio; a UI Toolkit segue em tempo real. Menu principal e Sair avisam que o
    /// jogo e salvo automaticamente e SALVAM antes de sair. Esc de novo continua.
    /// </summary>
    [RequireComponent(typeof(UIDocument))]
    public sealed class PauseController : MonoBehaviour
    {
        [SerializeField] GameRoot root;
        [SerializeField] PlayerInputHandler input;

        UIDocument document;
        VisualElement overlay;
        VisualElement card;
        OptionsView options;
        bool paused;
        bool built;

        public bool IsPaused => paused;
        public OptionsView Options => options;

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (input == null) input = FindAnyObjectByType<PlayerInputHandler>();
            document = GetComponent<UIDocument>();
            var actions = input != null ? input.Actions : PlayerInputHandler.FindLoadedActions();
            options = new OptionsView(root.Localization, actions, ShowMain, false);
            Build();
            SetPaused(false);
            root.Localization.CultureChanged += OnCultureChanged;
        }

        void OnDestroy()
        {
            if (root != null && root.Localization != null) root.Localization.CultureChanged -= OnCultureChanged;
            if (paused)
            {
                Time.timeScale = 1f;
                AudioListener.pause = false;
            }
        }

        void OnCultureChanged()
        {
            if (built && !options.IsOpen) ShowMain();
        }

        void Build()
        {
            overlay = MenuUi.Backdrop(document.rootVisualElement, 0.7f);
            built = true;
            ShowMain();
        }

        void ShowMain()
        {
            var loc = root.Localization;
            overlay.Clear();
            card = MenuUi.Card(overlay);
            MenuUi.Title(card, "ui.pause.title", loc, 44);
            MenuUi.MakeButton(card, loc.Get("ui.pause.resume"), () => SetPaused(false)).name = "pause-resume";
            MenuUi.MakeButton(card, loc.Get("ui.pause.options"), () => options.Open(document.rootVisualElement)).name = "pause-options";
            MenuUi.MakeButton(card, loc.Get("ui.common.open_logs"), MenuUi.OpenLogsFolder).name = "pause-logs";
            MenuUi.MakeButton(card, loc.Get("ui.pause.main_menu"), () => ConfirmExit(false)).name = "pause-main-menu";
            MenuUi.MakeButton(card, loc.Get("ui.pause.quit"), () => ConfirmExit(true)).name = "pause-quit";
        }

        // Menu principal e Sair: aviso de salvamento e, ao confirmar, salva antes de sair (docs/16, S-10).
        void ConfirmExit(bool quit)
        {
            var loc = root.Localization;
            overlay.Clear();
            card = MenuUi.Card(overlay);
            ScreenKit.Line(card, loc.Get("ui.pause.save_warning"), 26).style.unityTextAlign = TextAnchor.MiddleCenter;
            MenuUi.MakeButton(card, loc.Get("ui.common.confirm"), () => ExitNow(quit)).name = "exit-confirm";
            MenuUi.MakeButton(card, loc.Get("ui.common.cancel"), ShowMain).name = "exit-cancel";
        }

        /// <summary>Salva e sai (menu principal ou fechar o jogo).</summary>
        public void ExitNow(bool quit)
        {
            SaveNow();
            if (quit) GameFlow.Quit();
            else GameFlow.ToMainMenu();
        }

        void SaveNow()
        {
            var rules = GameSession.NativeRules(root);
            if (rules != null && GameSession.Save.HasSave) GameSession.Save.Save(rules);
        }

        void Update()
        {
            if (RefugeController.AnyScreenOpen || InventoryController.IsOpen) return;
            if (options != null && options.IsOpen)
            {
                // Esc fecha as Opcoes (e volta a pausa), a menos que o remapeamento esteja esperando uma tecla.
                if (input != null && input.IsReady && input.PausePressed) options.Close();
                return;
            }
            if (input != null && input.IsReady && input.PausePressed) SetPaused(!paused);
        }

        public void SetPaused(bool value)
        {
            paused = value;
            if (!value) options?.Close(false);
            if (overlay != null)
            {
                overlay.style.display = value ? DisplayStyle.Flex : DisplayStyle.None;
                if (value) ShowMain();
            }
            Time.timeScale = value ? 0f : 1f;
            AudioListener.pause = value;
        }
    }
}
