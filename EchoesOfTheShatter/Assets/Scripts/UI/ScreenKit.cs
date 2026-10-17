using System;
using System.Collections.Generic;
using Echoes.Core;
using UnityEngine;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Pecas das telas funcionais da Etapa 3 (UI Toolkit em codigo, cores e tamanhos no estilo do menu do docs/03): rotulos por chave de Loc com
    /// substituicao de {campos}, linhas de valor, toast e o botao de segurar 1 s. A arte final das telas vem depois da aprovacao dos mockups.
    /// </summary>
    public static class ScreenKit
    {
        public static readonly Color Gold = new Color(0.86f, 0.68f, 0.32f, 1f);
        public static readonly Color Text = new Color(0.93f, 0.9f, 0.84f, 1f);
        public static readonly Color Muted = new Color(0.62f, 0.58f, 0.52f, 1f);
        public static readonly Color Good = new Color(0.45f, 0.78f, 0.45f, 1f);
        public static readonly Color Bad = new Color(0.85f, 0.38f, 0.32f, 1f);

        /// <summary>Texto da chave de Loc com {campos} trocados (ex.: Fmt(loc, "ui.exp.cost", ("n", "2"))).</summary>
        public static string Fmt(LocalizationService loc, string key, params (string name, string value)[] fields)
        {
            var text = loc != null ? loc.Get(key) : key;
            foreach (var (name, value) in fields) text = text.Replace("{" + name + "}", value);
            return text;
        }

        public static Label Line(VisualElement parent, string text, int size = 22, Color? color = null, bool bold = false)
        {
            var label = new Label(text);
            label.style.fontSize = size;
            label.style.color = color ?? Text;
            label.style.whiteSpace = WhiteSpace.Normal;
            label.style.marginTop = 6;
            if (bold) label.style.unityFontStyleAndWeight = FontStyle.Bold;
            parent.Add(label);
            return label;
        }

        public static VisualElement Row(VisualElement parent)
        {
            var row = new VisualElement();
            row.style.flexDirection = FlexDirection.Row;
            row.style.alignItems = Align.Center;
            row.style.justifyContent = Justify.SpaceBetween;
            parent.Add(row);
            return row;
        }

        public static Button SmallButton(VisualElement parent, string text, Action onClick)
        {
            var button = MenuUi.MakeButton(parent, text, onClick);
            button.style.fontSize = 20;
            button.style.height = 44;
            button.style.marginLeft = 4;
            button.style.marginRight = 4;
            return button;
        }

        /// <summary>Acao perigosa (apagar): so vale depois de segurar o botao por 1 s (docs/16, S-02).</summary>
        public static Button HoldButton(VisualElement parent, string text, float seconds, Action onConfirmed)
        {
            var button = SmallButton(parent, text, null);
            IVisualElementScheduledItem pending = null;
            button.RegisterCallback<PointerDownEvent>(_ =>
            {
                pending = button.schedule.Execute(() => onConfirmed()).StartingIn((long)(seconds * 1000f));
            });
            button.RegisterCallback<PointerUpEvent>(_ => pending?.Pause());
            button.RegisterCallback<PointerLeaveEvent>(_ => pending?.Pause());
            return button;
        }
    }

    /// <summary>Aviso curto no topo da tela (toast): uma linha por vez, some sozinho em 3 s. Usa o tempo real (funciona com o jogo pausado).</summary>
    public sealed class ToastLayer
    {
        readonly Label label;
        readonly Queue<string> queue = new Queue<string>();
        IVisualElementScheduledItem hide;

        public ToastLayer(VisualElement root)
        {
            label = new Label();
            label.style.position = Position.Absolute;
            label.style.top = 36;
            label.style.alignSelf = Align.Center;
            label.style.left = new Length(20, LengthUnit.Percent);
            label.style.right = new Length(20, LengthUnit.Percent);
            label.style.unityTextAlign = TextAnchor.MiddleCenter;
            label.style.fontSize = 24;
            label.style.color = ScreenKit.Text;
            label.style.backgroundColor = new Color(0.07f, 0.06f, 0.09f, 0.92f);
            label.style.paddingTop = label.style.paddingBottom = 10;
            label.style.display = DisplayStyle.None;
            label.pickingMode = PickingMode.Ignore;
            root.Add(label);
        }

        public string Current => label.style.display == DisplayStyle.Flex ? label.text : string.Empty;

        public void Show(string text, float seconds = 3f)
        {
            label.text = text;
            label.style.display = DisplayStyle.Flex;
            hide?.Pause();
            hide = label.schedule.Execute(() => label.style.display = DisplayStyle.None).StartingIn((long)(seconds * 1000f));
        }
    }
}
