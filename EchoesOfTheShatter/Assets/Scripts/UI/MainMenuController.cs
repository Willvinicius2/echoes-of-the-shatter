using Echoes.Core;
using UnityEngine;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Tela inicial: titulo (chave de Loc) e os botoes Jogar e Sair, mais resolucao e janela. Jogar carrega a Cripta.
    /// Precisa de um UIDocument com o PanelSettings e de um GameRoot na cena (localizacao). Com -autostart entra sozinha na Cripta.
    /// </summary>
    [RequireComponent(typeof(UIDocument))]
    public sealed class MainMenuController : MonoBehaviour
    {
        [SerializeField] GameRoot root;
        [SerializeField, Min(0f)] float autoStartDelay = 1.5f;
        float autoStartAt = -1f;

        void Start()
        {
            GameSettings.ApplySaved();
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            var loc = root != null ? root.Localization : null;
            var document = GetComponent<UIDocument>();
            var rootElement = document.rootVisualElement;
            rootElement.Clear();

            var backdrop = MenuUi.Backdrop(rootElement, 1f);
            var card = MenuUi.Card(backdrop);
            MenuUi.Title(card, "ui.menu.title", loc, 54);
            MenuUi.MakeButton(card, loc.Get("ui.menu.play"), GameFlow.StartGame).name = "play";
            MenuUi.AddDisplayOptions(card, loc);
            MenuUi.MakeButton(card, loc.Get("ui.menu.quit"), GameFlow.Quit).name = "quit";

            if (GameFlow.AutoStartRequested) autoStartAt = Time.realtimeSinceStartup + autoStartDelay;
        }

        void Update()
        {
            if (autoStartAt > 0f && Time.realtimeSinceStartup >= autoStartAt)
            {
                autoStartAt = -1f;
                GameFlow.StartGame();
            }
        }
    }
}
