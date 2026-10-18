using System;
using System.Collections.Generic;
using Echoes.Core;
using Echoes.Interop;
using Echoes.Interop.Native;
using UnityEngine;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Pecas de item compartilhadas pelas telas do Refugio (Vendedor, Encantador): slot com moldura de raridade e icone, grade rolavel, detalhe do item
    /// (nome, raridade, linhas do tooltip) e a faixa de um afixo (valor entre minimo e maximo, passos de lapidacao). So formata o que o core devolveu.
    /// </summary>
    public static class ItemWidgets
    {
        public const int Columns = 8;
        public const int Cell = 58;

        static readonly Color SelectedTint = new Color(1.35f, 1.2f, 0.8f, 1f);

        public static string RarityClass(ItemRarity rarity)
        {
            switch (rarity)
            {
                case ItemRarity.Magic: return "art-slot--magic";
                case ItemRarity.Rare: return "art-slot--rare";
                case ItemRarity.Unique: return "art-slot--unique";
                default: return "art-slot--common";
            }
        }

        /// <summary>Slot do item: moldura da raridade, icone (ou iniciais) e, se pedido, o realce de selecionado ou a marca de "lixo".</summary>
        public static VisualElement MakeCell(LocalizationService loc, ItemInstanceInfo item, bool selected, bool marked = false, int size = Cell)
        {
            var cell = new VisualElement { name = "cell" };
            cell.style.width = size;
            cell.style.height = size;
            cell.style.marginRight = 4;
            cell.style.marginBottom = 4;
            cell.style.alignItems = Align.Center;
            cell.style.justifyContent = Justify.Center;
            cell.AddToClassList(item != null ? RarityClass(item.Rarity) : "art-slot--empty");
            if (item == null) return cell;
            cell.userData = item;
            var icon = UiArt.IconFor(item);
            if (icon != null)
            {
                var image = new VisualElement { name = "icon" };
                image.style.width = size - 14;
                image.style.height = size - 14;
                image.style.backgroundImage = new StyleBackground(icon);
                image.pickingMode = PickingMode.Ignore;
                cell.Add(image);
            }
            else
            {
                var glyph = ScreenKit.Line(cell, ItemText.Glyph(loc, item), 22, ItemText.RarityColor(item.Rarity), true);
                glyph.style.marginTop = 0;
                glyph.pickingMode = PickingMode.Ignore;
            }
            if (selected) cell.style.unityBackgroundImageTintColor = SelectedTint;
            if (marked)
            {
                var mark = ScreenKit.Line(cell, "x", 18, ScreenKit.Bad, true);
                mark.name = "junk-mark";
                mark.style.position = Position.Absolute;
                mark.style.right = 4;
                mark.style.top = -2;
                mark.pickingMode = PickingMode.Ignore;
            }
            return cell;
        }

        /// <summary>Grade rolavel de 8 colunas; devolve o conteudo (onde as celulas entram).</summary>
        public static VisualElement MakeGrid(VisualElement parent, float height)
        {
            var scroll = new ScrollView(ScrollViewMode.Vertical);
            scroll.style.height = height;
            scroll.style.width = Columns * (Cell + 4) + 16;
            var content = scroll.contentContainer;
            content.style.flexDirection = FlexDirection.Row;
            content.style.flexWrap = Wrap.Wrap;
            parent.Add(scroll);
            return content;
        }

        /// <summary>Nome, raridade em texto e as linhas do tooltip (docs/16 S-06) do item.</summary>
        public static void FillDetail(VisualElement panel, LocalizationService loc, NativeRulesCore rules, ItemInstanceInfo item, bool includeAffixes = true)
        {
            if (item == null) return;
            var color = ItemText.RarityColor(item.Rarity);
            ScreenKit.Line(panel, ItemText.Name(loc, rules, item), 24, color, true).name = "item-name";
            ScreenKit.Line(panel, ItemText.RarityLine(loc, rules, item), 17, color).name = "item-rarity";
            foreach (var (text, lineColor) in ItemText.BodyLines(loc, rules, item, includeAffixes)) ScreenKit.Line(panel, text, 18, lineColor);
        }

        /// <summary>Faixa [minimo, maximo] de um afixo (de <c>shatter_content_json</c>); 0 e 0 se o conteudo nao existe.</summary>
        public static (double min, double max, string stat, string modKind) AffixRange(NativeRulesCore rules, string affixId)
        {
            var json = rules != null ? rules.ContentJson(affixId) : null;
            if (string.IsNullOrEmpty(json)) return (0.0, 0.0, string.Empty, "flat");
            var o = MiniJson.AsObject(MiniJson.Parse(json));
            return (MiniJson.Num(o, "min_value"), MiniJson.Num(o, "max_value"), MiniJson.Str(o, "stat"), MiniJson.Str(o, "mod_kind", "flat"));
        }

        /// <summary>
        /// Linha de um afixo para o Encantador: "+8% dano" na cor do afixo, a barra de qualidade (onde o valor cai entre o minimo e o maximo) e os
        /// passos de lapidacao (bolinhas cheias e vazias). <paramref name="highlight"/>: afixo que acabou de mudar (mais brilho).
        /// </summary>
        public static VisualElement AffixRow(LocalizationService loc, NativeRulesCore rules, AffixInfo affix, int polishMax, bool highlight)
        {
            var (min, max, stat, modKind) = AffixRange(rules, affix.AffixId);
            var row = new VisualElement { name = "affix-row" };
            row.style.marginTop = 6;
            var color = highlight ? ItemText.RareColor : ItemText.MagicColor;
            var line = ScreenKit.Row(row);
            ScreenKit.Line(line, ItemText.ModLine(loc, stat, modKind, affix.Value), 20, color, highlight).style.marginTop = 0;
            var dots = new string('●', Mathf.Clamp(affix.Polish, 0, polishMax)) + new string('○', Mathf.Max(0, polishMax - affix.Polish));
            ScreenKit.Line(line, dots, 18, ScreenKit.Gold).style.marginTop = 0;
            var track = new VisualElement { name = "affix-bar" };
            track.style.height = 6;
            track.style.marginTop = 2;
            track.style.backgroundColor = new Color(0.12f, 0.1f, 0.14f, 1f);
            var fill = new VisualElement();
            fill.style.height = Length.Percent(100f);
            fill.style.width = Length.Percent(Quality(affix.Value, min, max) * 100f);
            fill.style.backgroundColor = color;
            track.Add(fill);
            row.Add(track);
            return row;
        }

        /// <summary>Posicao do valor entre o minimo e o maximo da faixa (0 a 1); faixa vazia = cheia.</summary>
        public static float Quality(double value, double min, double max)
        {
            if (max <= min) return 1f;
            return (float)Math.Max(0.0, Math.Min(1.0, (value - min) / (max - min)));
        }

        /// <summary>Botao com o motivo escrito quando fica cinza (o texto do motivo vai logo abaixo).</summary>
        public static Button ReasonButton(VisualElement parent, string label, string reasonOrNull, Action onClick)
        {
            var holder = new VisualElement();
            parent.Add(holder);
            var button = ScreenKit.SmallButton(holder, label, onClick);
            button.style.marginLeft = 0;
            button.style.marginRight = 0;
            button.style.width = 260;
            button.SetEnabled(string.IsNullOrEmpty(reasonOrNull));
            if (!string.IsNullOrEmpty(reasonOrNull))
            {
                var reason = ScreenKit.Line(holder, reasonOrNull, 15, ScreenKit.Muted);
                reason.name = "reason";
                reason.style.marginTop = 0;
            }
            return button;
        }

        /// <summary>Ouro e Lascas do save no rodape das telas.</summary>
        public static void FooterResources(VisualElement parent, LocalizationService loc, NativeRulesCore rules)
        {
            var snap = SaveReadout.Read(rules, ExpeditionConfig.CryptMap);
            var row = ScreenKit.Row(parent);
            row.name = "footer-resources";
            row.style.justifyContent = Justify.FlexStart;
            row.style.marginTop = 8;
            var gold = ScreenKit.Line(row, loc.Get("ui.common.gold") + ": " + loc.FormatInteger(snap.Gold), 22, ScreenKit.Gold, true);
            gold.name = "footer-gold";
            gold.style.marginRight = 28;
            ScreenKit.Line(row, loc.Get("ui.inventory.shards") + ": " + loc.FormatInteger(snap.Shards), 22, ItemText.MagicColor, true).name = "footer-shards";
        }
    }
}
