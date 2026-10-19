using System;
using Echoes.Core;
using Echoes.Interop;
using UnityEngine;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Tela de veredito (docs/design/21, cena 5): o General caiu de joelhos e o Cacador escolhe Exorcizar ou Devorar. A escolha e irreversivel, entao
    /// o aviso fica sempre a vista e cada opcao so vale segurando o botao (padrao das acoes perigosas, docs/16 S-02). Textos, numeros e efeitos vem do
    /// core (<see cref="StoryRegionInfo"/>) e do Loc; aqui so UI. Quem aplica o veredito e o <see cref="StoryDirector"/> (callback).
    /// </summary>
    public sealed class VerdictScreen
    {
        /// <summary>Segundos segurando para confirmar o veredito.</summary>
        public const float HoldSeconds = 1f;

        readonly VisualElement host;
        readonly LocalizationService loc;
        readonly StoryRegionInfo region;
        readonly Action<StoryVerdictInfo> onChosen;
        VisualElement backdrop;

        public VerdictScreen(VisualElement host, LocalizationService loc, StoryRegionInfo region, Action<StoryVerdictInfo> onChosen)
        {
            this.host = host;
            this.loc = loc;
            this.region = region;
            this.onChosen = onChosen;
        }

        public bool IsOpen => backdrop != null;

        public void Show()
        {
            Close();
            backdrop = MenuUi.Backdrop(host, 0.85f);
            backdrop.name = "verdict-screen";
            backdrop.pickingMode = PickingMode.Position;
            var card = MenuUi.Card(backdrop);
            card.style.minWidth = 1100;
            MenuUi.Title(card, "ui.verdict.title", loc, 44);
            ScreenKit.Line(card, loc.Get("dlg.guardian.kneel"), 24, ScreenKit.Muted).style.unityTextAlign = TextAnchor.MiddleCenter;
            var warning = ScreenKit.Line(card, loc.Get("ui.verdict.prompt"), 26, ScreenKit.Bad, true);
            warning.name = "verdict-warning";
            warning.style.unityTextAlign = TextAnchor.MiddleCenter;
            warning.style.marginBottom = 14;

            var row = new VisualElement { name = "verdict-options" };
            row.style.flexDirection = FlexDirection.Row;
            row.style.justifyContent = Justify.Center;
            card.Add(row);
            foreach (var option in region.Options) BuildOption(row, option);

            var hint = ScreenKit.Line(card, loc.Get("ui.verdict.hold_hint"), 20, ScreenKit.Muted);
            hint.style.unityTextAlign = TextAnchor.MiddleCenter;
            hint.style.marginTop = 12;
        }

        public void Close()
        {
            backdrop?.RemoveFromHierarchy();
            backdrop = null;
        }

        void BuildOption(VisualElement parent, StoryVerdictInfo option)
        {
            var column = MenuUi.Plain(parent);
            column.name = "verdict-" + option.Choice;
            column.style.width = 480;
            column.style.marginLeft = 12;
            column.style.marginRight = 12;
            column.style.paddingTop = 14;
            column.style.paddingBottom = 14;
            column.style.paddingLeft = 18;
            column.style.paddingRight = 18;

            var title = ScreenKit.Line(column, loc.Get(option.VerdictId + ".name"), 34, ScreenKit.Gold, true);
            title.style.unityTextAlign = TextAnchor.MiddleCenter;
            ScreenKit.Line(column, loc.Get("ui.verdict." + option.Choice + "_desc"), 22);

            // Efeitos que o core informa (so os que existem; nenhum numero e do C#).
            if (option.HungerDelta > 0)
                ScreenKit.Line(column, ScreenKit.Fmt(loc, "ui.verdict.hunger_gain", ("n", option.HungerDelta.ToString())), 22, ScreenKit.Bad);
            if (option.StatBonusPct > 0.0)
                ScreenKit.Line(column, ScreenKit.Fmt(loc, "ui.verdict.bonus", ("n", Pct(option.StatBonusPct))), 22, ScreenKit.Good);
            if (!string.IsNullOrEmpty(option.GrantsRelic))
                ScreenKit.Line(column, ScreenKit.Fmt(loc, "ui.verdict.relic", ("name", loc.Get(option.GrantsRelic + ".name"))), 22, ScreenKit.Good);
            if (!string.IsNullOrEmpty(option.GrantsSignature))
                ScreenKit.Line(column, ScreenKit.Fmt(loc, "ui.verdict.signature", ("name", loc.Get(option.GrantsSignature + ".name"))), 22, ScreenKit.Good);

            var spacer = new VisualElement();
            spacer.style.height = 12;
            column.Add(spacer);
            var chosen = option;
            var button = ScreenKit.HoldButton(column, loc.Get("ui.verdict." + option.Choice), HoldSeconds, () => onChosen?.Invoke(chosen));
            button.name = "verdict-confirm-" + option.Choice;
        }

        static string Pct(double value) => value == Math.Floor(value) ? ((long)value).ToString() : value.ToString("0.#", System.Globalization.CultureInfo.InvariantCulture);
    }
}
