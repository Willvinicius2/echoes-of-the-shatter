using Echoes.Core;
using Echoes.Gameplay;
using UnityEngine;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Esc pausa e abre o menu de pausa (Continuar, resolucao e janela, Voltar ao inicio). A pausa para o tempo do jogo
    /// (Time.timeScale = 0; so a pausa usa isso, o hitstop nunca) e o audio; a UI Toolkit segue em tempo real. Esc de novo continua.
    /// </summary>
    [RequireComponent(typeof(UIDocument))]
    public sealed class PauseController : MonoBehaviour
    {
        [SerializeField] GameRoot root;
        [SerializeField] PlayerInputHandler input;

        UIDocument document;
        VisualElement overlay;
        bool paused;

        public bool IsPaused => paused;

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (input == null) input = FindAnyObjectByType<PlayerInputHandler>();
            document = GetComponent<UIDocument>();
            Build();
            SetPaused(false);
        }

        void OnDestroy()
        {
            if (paused)
            {
                Time.timeScale = 1f;
                AudioListener.pause = false;
            }
        }

        void Build()
        {
            var loc = root != null ? root.Localization : null;
            var rootElement = document.rootVisualElement;
            overlay = MenuUi.Backdrop(rootElement, 0.7f);
            var card = MenuUi.Card(overlay);
            MenuUi.Title(card, "ui.pause.title", loc, 44);
            MenuUi.MakeButton(card, loc.Get("ui.pause.resume"), () => SetPaused(false));
            MenuUi.AddDisplayOptions(card, loc);
            MenuUi.MakeButton(card, loc.Get("ui.pause.to_menu"), BackToTitle);
        }

        void Update()
        {
            if (RefugeController.AnyScreenOpen) return;
            if (input != null && input.IsReady && input.PausePressed) SetPaused(!paused);
        }

        // Menu principal: o jogo e salvo antes de sair (docs/16, S-10).
        void BackToTitle()
        {
            var rules = Echoes.Core.GameSession.NativeRules(root);
            if (rules != null && Echoes.Core.GameSession.Save.HasSave) Echoes.Core.GameSession.Save.Save(rules);
            GameFlow.ToMainMenu();
        }

        public void SetPaused(bool value)
        {
            paused = value;
            if (overlay != null) overlay.style.display = value ? DisplayStyle.Flex : DisplayStyle.None;
            Time.timeScale = value ? 0f : 1f;
            AudioListener.pause = value;
        }
    }
}
