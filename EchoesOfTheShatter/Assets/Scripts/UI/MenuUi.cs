using System;
using Echoes.Core;
using UnityEngine;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Pecas da tela inicial e da pausa montadas em codigo (UI Toolkit): painel, titulo, botoes e as opcoes de resolucao e janela.
    /// Todo texto vem de chave de localizacao (o codigo so tem as chaves). Cores no estilo do menu (superficie escura e dourado).
    /// </summary>
    public static class MenuUi
    {
        static readonly Color Gold = new Color(0.86f, 0.68f, 0.32f, 1f);
        static readonly Color Text = new Color(0.93f, 0.9f, 0.84f, 1f);

        public static VisualElement Backdrop(VisualElement root, float alpha)
        {
            var backdrop = new VisualElement { name = "backdrop" };
            backdrop.style.position = Position.Absolute;
            backdrop.style.left = 0;
            backdrop.style.top = 0;
            backdrop.style.right = 0;
            backdrop.style.bottom = 0;
            backdrop.style.backgroundColor = new Color(0.02f, 0.02f, 0.04f, alpha);
            backdrop.style.alignItems = Align.Center;
            backdrop.style.justifyContent = Justify.Center;
            root.Add(backdrop);
            return backdrop;
        }

        /// <summary>Painel das telas: moldura ornamentada do kit aprovado (classe art-frame-ornate no UiArt.uss).</summary>
        public static VisualElement Card(VisualElement parent)
        {
            var card = new VisualElement { name = "card" };
            card.AddToClassList("art-frame-ornate");
            card.style.minWidth = 520;
            card.style.alignItems = Align.Stretch;
            parent.Add(card);
            return card;
        }

        /// <summary>Painel liso (moldura de pedra sem ornamento) para areas internas.</summary>
        public static VisualElement Plain(VisualElement parent)
        {
            var panel = new VisualElement { name = "panel" };
            panel.AddToClassList("art-frame-plain");
            parent.Add(panel);
            return panel;
        }

        /// <summary>Titulo por chave de Loc (LocLabel).</summary>
        public static LocLabel Title(VisualElement parent, string locKey, LocalizationService loc, int size)
        {
            var label = new LocLabel { LocKey = locKey };
            label.Apply(loc);
            label.style.fontSize = size;
            label.style.color = Gold;
            label.style.unityFontStyleAndWeight = FontStyle.Bold;
            label.style.unityTextAlign = TextAnchor.MiddleCenter;
            label.style.marginBottom = 28;
            parent.Add(label);
            return label;
        }

        /// <summary>Botao do kit aprovado: normal, hover e desabilitado vem do UiArt.uss (art-button).</summary>
        public static Button MakeButton(VisualElement parent, string text, Action onClick)
        {
            var button = new Button(onClick) { text = text };
            button.AddToClassList("art-button");
            button.style.fontSize = 28;
            button.style.height = 64;
            button.style.marginTop = 10;
            parent.Add(button);
            return button;
        }

        /// <summary>Abre a pasta onde o jogo grava o log (Player.log fica em persistentDataPath no Windows).</summary>
        public static void OpenLogsFolder()
        {
            Application.OpenURL("file:///" + Application.persistentDataPath.Replace('\\', '/'));
        }

        /// <summary>Botoes de resolucao e de modo de janela (cada clique aplica e salva).</summary>
        public static void AddDisplayOptions(VisualElement parent, LocalizationService loc)
        {
            Button resolution = null, window = null;
            Action refresh = () =>
            {
                resolution.text = loc.Get("ui.options.resolution") + ": " + GameSettings.Width + " x " + GameSettings.Height;
                window.text = loc.Get("ui.options.window_mode") + ": " + loc.Get(GameSettings.Fullscreen ? "ui.options.fullscreen" : "ui.options.windowed");
            };
            resolution = MakeButton(parent, string.Empty, () =>
            {
                GameSettings.CycleResolution();
                refresh();
            });
            window = MakeButton(parent, string.Empty, () =>
            {
                GameSettings.ToggleFullscreen();
                refresh();
            });
            resolution.style.fontSize = 22;
            window.style.fontSize = 22;
            refresh();
        }
    }
}
