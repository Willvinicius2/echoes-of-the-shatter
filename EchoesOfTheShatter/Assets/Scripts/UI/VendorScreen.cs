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
    /// S-14 Vendedor (docs/16 11.3; APIs do docs/09 secao 13): a Mochila e o Bau a esquerda e, a direita, tres abas. Vender (valor do core; Raro pede
    /// confirmacao, Unico segurar 1 s; Comum e Magico saem com 5 s para desfazer; Alt+clique marca como lixo e "Vender marcados" soma), Recomprar (os
    /// ultimos itens vendidos, preco do core) e Frascos (Frasco de Recarga: comprar 1 ou encher ate o maximo). Preco, recompra, maximo e Ouro sao
    /// sempre do core; aqui so UI. Cada acao grava o save (RF-54).
    /// </summary>
    public sealed class VendorScreen
    {
        public enum Tab { Sell, Buyback, Flasks }

        /// <summary>Segundos para desfazer a venda de Comum e Magico (docs/16 S-07).</summary>
        public const float UndoSeconds = 5f;

        readonly VisualElement card;
        readonly GameRoot root;
        readonly Action close;
        readonly Dictionary<ulong, ItemContainer> pending = new Dictionary<ulong, ItemContainer>();
        readonly HashSet<ulong> marked = new HashSet<ulong>();
        Tab tab;
        ItemInstanceInfo selected;
        ItemContainer selectedFrom;
        string message;
        VisualElement modal;

        public VendorScreen(VisualElement host, GameRoot gameRoot, Action onClose)
        {
            card = host;
            root = gameRoot;
            close = onClose;
        }

        public Tab CurrentTab => tab;
        public int PendingCount => pending.Count;
        public string Message => message;
        LocalizationService Loc => root.Localization;
        NativeRulesCore Rules => GameSession.NativeRules(root);
        SaveGame Save => GameSession.Save.Current;

        public void Show()
        {
            card.Clear();
            card.style.minWidth = 1320;
            MenuUi.Title(card, "ui.vendor.title", Loc, 34).style.marginBottom = 8;
            var body = new VisualElement { name = "vendor-body" };
            body.style.flexDirection = FlexDirection.Row;
            card.Add(body);
            BuildGrids(body);
            BuildRight(body);
            ItemWidgets.FooterResources(card, Loc, Rules);
            var bottom = ScreenKit.Row(card);
            bottom.style.justifyContent = Justify.FlexEnd;
            ScreenKit.SmallButton(bottom, Loc.Get("ui.common.close"), () => close()).name = "vendor-close";
        }

        // ------------------------------------------------------------------------------------------------ grades

        void BuildGrids(VisualElement body)
        {
            var left = new VisualElement { name = "vendor-grids" };
            body.Add(left);
            var info = Save.Inventory(Rules, 0);
            ScreenKit.Line(left, Loc.Get("ui.inventory.backpack").Replace("{used}", info.BackpackUsed.ToString()).Replace("{cap}", info.BackpackCapacity.ToString()), 20, ScreenKit.Gold, true);
            FillGrid(ItemWidgets.MakeGrid(left, 5 * (ItemWidgets.Cell + 4)), ItemContainer.Backpack, info.BackpackCapacity);
            ScreenKit.Line(left, Loc.Get("ui.inventory.stash").Replace("{used}", info.StashUsed.ToString()).Replace("{cap}", info.StashCapacity.ToString()), 20, ScreenKit.Gold, true);
            FillGrid(ItemWidgets.MakeGrid(left, 3 * (ItemWidgets.Cell + 4)), ItemContainer.Stash, info.StashCapacity);
        }

        void FillGrid(VisualElement grid, ItemContainer container, int capacity)
        {
            var items = Save.ListItems(0, container);
            items.RemoveAll(i => pending.ContainsKey(i.Uid)); // venda na janela de desfazer: ja some da grade
            for (var i = 0; i < capacity; i++)
            {
                var item = i < items.Count ? items[i] : null;
                var cell = ItemWidgets.MakeCell(Loc, item, item != null && selected != null && selected.Uid == item.Uid, item != null && marked.Contains(item.Uid));
                if (item != null)
                {
                    var captured = item;
                    cell.RegisterCallback<PointerDownEvent>(e =>
                    {
                        if (e.altKey) ToggleMark(captured);
                        else Select(captured, container);
                    });
                }
                grid.Add(cell);
            }
        }

        void Select(ItemInstanceInfo item, ItemContainer container)
        {
            selected = item;
            selectedFrom = container;
            message = null;
            Show();
        }

        void ToggleMark(ItemInstanceInfo item)
        {
            if (!marked.Remove(item.Uid)) marked.Add(item.Uid);
            Show();
        }

        // ------------------------------------------------------------------------------------------------ abas

        void BuildRight(VisualElement body)
        {
            var right = new VisualElement { name = "vendor-right" };
            right.style.marginLeft = 24;
            right.style.width = 560;
            body.Add(right);
            var tabs = ScreenKit.Row(right);
            tabs.style.justifyContent = Justify.FlexStart;
            AddTab(tabs, "ui.vendor.tab.sell", Tab.Sell, "tab-sell");
            AddTab(tabs, "ui.vendor.tab.buyback", Tab.Buyback, "tab-buyback");
            AddTab(tabs, "ui.vendor.tab.flasks", Tab.Flasks, "tab-flasks");
            var content = new VisualElement { name = "vendor-content" };
            content.style.marginTop = 10;
            right.Add(content);
            switch (tab)
            {
                case Tab.Sell: BuildSell(content); break;
                case Tab.Buyback: BuildBuyback(content); break;
                default: BuildFlasks(content); break;
            }
            if (!string.IsNullOrEmpty(message))
            {
                var line = ScreenKit.Line(right, message, 18, ScreenKit.Gold);
                line.name = "vendor-message";
            }
        }

        void AddTab(VisualElement row, string key, Tab value, string name)
        {
            var button = new Button(() => { tab = value; message = null; Show(); }) { text = Loc.Get(key), name = name };
            button.AddToClassList("art-tab");
            button.style.fontSize = 22;
            button.style.height = 48;
            button.style.marginRight = 6;
            if (tab == value) button.style.color = ScreenKit.Gold;
            row.Add(button);
        }

        // ------------------------------------------------------------------------------------------------ Vender

        void BuildSell(VisualElement content)
        {
            if (selected != null && Save.ListItems(0, selectedFrom).Exists(i => i.Uid == selected.Uid) && !pending.ContainsKey(selected.Uid))
            {
                var panel = new VisualElement { name = "sell-detail" };
                panel.AddToClassList("art-frame-plain");
                panel.style.paddingLeft = 24;
                panel.style.paddingRight = 24;
                panel.style.paddingTop = 18;
                panel.style.paddingBottom = 18;
                content.Add(panel);
                ItemWidgets.FillDetail(panel, Loc, Rules, selected);
                var value = Save.SellValue(Rules, 0, selected.Uid);
                ScreenKit.Line(panel, ScreenKit.Fmt(Loc, "ui.vendor.value", ("amount", Loc.FormatInteger(value))), 20, ScreenKit.Gold, true).name = "sell-value";
                var sell = ScreenKit.SmallButton(panel, Loc.Get("ui.vendor.sell"), AskSellSelected);
                sell.name = "act-sell";
            }
            else
            {
                var all = Save.ListItems(0, ItemContainer.Backpack).Count + Save.ListItems(0, ItemContainer.Stash).Count;
                ScreenKit.Line(content, all == 0 ? Loc.Get("ui.vendor.empty") : Loc.Get("ui.inventory.select_hint"), 20, ScreenKit.Muted).name = "sell-hint";
            }
            BuildMarkedBar(content);
            BuildUndoBars(content);
        }

        void BuildMarkedBar(VisualElement content)
        {
            if (marked.Count == 0) return;
            long total = 0;
            var byRarity = new int[4];
            foreach (var item in MarkedItems())
            {
                total += Save.SellValue(Rules, 0, item.Uid);
                byRarity[(int)item.Rarity]++;
            }
            var line = ScreenKit.Line(content, ScreenKit.Fmt(Loc, "ui.vendor.marked_total",
                ("count", marked.Count.ToString()), ("amount", Loc.FormatInteger(total)),
                ("normal", byRarity[0].ToString()), ("magic", byRarity[1].ToString()), ("rare", byRarity[2].ToString()), ("unique", byRarity[3].ToString())), 18, ScreenKit.Text);
            line.name = "marked-total";
            line.style.marginTop = 12;
            var button = ScreenKit.SmallButton(content, Loc.Get("ui.vendor.sell_marked"), AskSellMarked);
            button.name = "act-sell-marked";
        }

        List<ItemInstanceInfo> MarkedItems()
        {
            var list = new List<ItemInstanceInfo>();
            foreach (var container in new[] { ItemContainer.Backpack, ItemContainer.Stash })
                foreach (var item in Save.ListItems(0, container))
                    if (marked.Contains(item.Uid) && !pending.ContainsKey(item.Uid)) list.Add(item);
            return list;
        }

        // Confirmacoes da S-07: Comum e Magico sem confirmar (com 5 s para desfazer), Raro confirma, Unico segura 1 s.
        void AskSellSelected()
        {
            if (selected == null) return;
            var item = selected;
            if (item.Rarity == ItemRarity.Normal || item.Rarity == ItemRarity.Magic)
            {
                QueueSale(item, selectedFrom);
                return;
            }
            ShowConfirm(ScreenKit.Fmt(Loc, "ui.vendor.confirm_sell", ("item", ItemText.Name(Loc, Rules, item))), item.IsUnique, () => SellNow(item.Uid, selectedFrom, true));
        }

        void AskSellMarked()
        {
            var items = MarkedItems();
            if (items.Count == 0) return;
            var risky = items.FindAll(i => i.Rarity == ItemRarity.Rare || i.Rarity == ItemRarity.Unique);
            var anyUnique = items.Exists(i => i.IsUnique);
            Action sellAll = () =>
            {
                foreach (var item in items) SellNow(item.Uid, ContainerOf(item.Uid), false);
                marked.Clear();
                GameSession.Save.Save(Rules);
                message = ScreenKit.Fmt(Loc, "ui.vendor.sold_many", ("count", items.Count.ToString()));
                Show();
            };
            if (risky.Count == 0) sellAll();
            else ShowConfirm(ScreenKit.Fmt(Loc, "ui.vendor.confirm_marked", ("count", risky.Count.ToString())), anyUnique, sellAll);
        }

        ItemContainer ContainerOf(ulong uid)
        {
            return Save.ListItems(0, ItemContainer.Backpack).Exists(i => i.Uid == uid) ? ItemContainer.Backpack : ItemContainer.Stash;
        }

        /// <summary>Vende de vez (o core paga, guarda na recompra e pode expulsar o mais antigo). Devolve o resultado.</summary>
        public VendorOutcome SellNow(ulong uid, ItemContainer container, bool refresh)
        {
            var info = Save.VendorBuybackInfo(Rules);
            var outcome = Save.VendorSell(Rules, 0, container, uid);
            if (outcome.Ok)
            {
                selected = null;
                marked.Remove(uid);
                GameSession.Save.Save(Rules);
                if (refresh)
                {
                    message = outcome.Evicted ? ScreenKit.Fmt(Loc, "ui.vendor.sold_evicted", ("gold", Loc.FormatInteger(outcome.Gold))) : ScreenKit.Fmt(Loc, "ui.vendor.sold", ("gold", Loc.FormatInteger(outcome.Gold)));
                    Show();
                }
            }
            else if (refresh)
            {
                message = VendorError(outcome.Result);
                Show();
            }
            return outcome;
        }

        // ---- venda com 5 s para desfazer (Comum e Magico): some da grade ja, o core so vende quando a janela fecha

        void QueueSale(ItemInstanceInfo item, ItemContainer container)
        {
            var buyback = Save.VendorBuybackInfo(Rules);
            if (buyback.WouldEvict && (buyback.EvictRarity == ItemRarity.Rare || buyback.EvictRarity == ItemRarity.Unique))
            {
                // O 11o item expulsa o mais antigo; se ele e Raro ou Unico a venda pede confirmacao extra com aviso (docs/16 11.2).
                ShowConfirm(ScreenKit.Fmt(Loc, "ui.vendor.buyback_warn_evict", ("rarity", Loc.Get(ItemText.RarityKey(buyback.EvictRarity)))), buyback.EvictRarity == ItemRarity.Unique, () => SellNow(item.Uid, container, true));
                return;
            }
            pending[item.Uid] = container;
            selected = null;
            message = null;
            Show();
            card.schedule.Execute(() => CommitSale(item.Uid)).StartingIn((long)(UndoSeconds * 1000f));
        }

        void BuildUndoBars(VisualElement content)
        {
            foreach (var pair in pending)
            {
                var uid = pair.Key;
                var item = FindAny(uid);
                var bar = new VisualElement { name = "undo-bar" };
                bar.style.flexDirection = FlexDirection.Row;
                bar.style.alignItems = Align.Center;
                bar.style.marginTop = 10;
                ScreenKit.Line(bar, ScreenKit.Fmt(Loc, "ui.vendor.sold_undo", ("item", item != null ? ItemText.Name(Loc, Rules, item) : string.Empty)), 18).style.marginTop = 0;
                ScreenKit.SmallButton(bar, Loc.Get("ui.common.undo"), () => UndoSale(uid)).name = "undo-sale";
                content.Add(bar);
            }
        }

        ItemInstanceInfo FindAny(ulong uid)
        {
            foreach (var container in new[] { ItemContainer.Backpack, ItemContainer.Stash })
            {
                var found = Save.ListItems(0, container).Find(i => i.Uid == uid);
                if (found != null) return found;
            }
            return null;
        }

        public bool UndoSale(ulong uid)
        {
            if (!pending.Remove(uid)) return false;
            Show();
            return true;
        }

        void CommitSale(ulong uid)
        {
            if (!pending.TryGetValue(uid, out var container)) return;
            pending.Remove(uid);
            if (GameSession.Save == null || !GameSession.Save.HasSave) return;
            var outcome = Save.VendorSell(Rules, 0, container, uid);
            if (outcome.Ok) GameSession.Save.Save(Rules);
            Show();
        }

        /// <summary>Confirma agora todas as vendas ainda na janela de desfazer (ao fechar a tela).</summary>
        public void Flush()
        {
            foreach (var uid in new List<ulong>(pending.Keys)) CommitSale(uid);
        }

        // ------------------------------------------------------------------------------------------------ Recomprar

        void BuildBuyback(VisualElement content)
        {
            var info = Save.VendorBuybackInfo(Rules);
            var inv = Save.Inventory(Rules, 0);
            var gold = Save.Currency(SaveGame.GoldId);
            if (info.Items.Count == 0)
            {
                ScreenKit.Line(content, Loc.Get("ui.vendor.buyback_empty"), 20, ScreenKit.Muted).name = "buyback-empty";
                return;
            }
            var scroll = new ScrollView(ScrollViewMode.Vertical);
            scroll.style.height = 430;
            content.Add(scroll);
            foreach (var entry in info.Items)
            {
                var row = ScreenKit.Row(scroll.contentContainer);
                row.name = "buyback-row";
                row.style.marginTop = 4;
                var left = new VisualElement();
                left.style.flexDirection = FlexDirection.Row;
                left.style.alignItems = Align.Center;
                row.Add(left);
                left.Add(ItemWidgets.MakeCell(Loc, entry.Item, false, false, 48));
                ScreenKit.Line(left, ItemText.Name(Loc, Rules, entry.Item), 18, ItemText.RarityColor(entry.Item.Rarity)).style.marginTop = 0;
                var buy = new VisualElement();
                row.Add(buy);
                string reason = null;
                if (inv.BackpackUsed >= inv.BackpackCapacity) reason = Loc.Get("ui.vendor.err.full");
                else if (gold < entry.Price) reason = Loc.Get("ui.vendor.no_gold");
                var captured = entry;
                var button = ItemWidgets.ReasonButton(buy, ScreenKit.Fmt(Loc, "ui.vendor.buyback_price", ("amount", Loc.FormatInteger(entry.Price))), reason, () => Rebuy(captured.Item.Uid));
                button.name = "act-rebuy";
                button.style.width = 200;
            }
        }

        public VendorOutcome Rebuy(ulong uid)
        {
            var outcome = Save.VendorRebuy(Rules, 0, uid);
            if (outcome.Ok)
            {
                GameSession.Save.Save(Rules);
                message = ScreenKit.Fmt(Loc, "ui.vendor.rebought", ("gold", Loc.FormatInteger(outcome.Gold)));
            }
            else message = VendorError(outcome.Result);
            Show();
            return outcome;
        }

        // ------------------------------------------------------------------------------------------------ Frascos

        void BuildFlasks(VisualElement content)
        {
            var stock = Save.VendorStock(Rules).Find(s => s.RefId == SaveGame.RefillFlaskId);
            if (string.IsNullOrEmpty(stock.Id))
            {
                ScreenKit.Line(content, Loc.Get("ui.vendor.empty"), 20, ScreenKit.Muted);
                return;
            }
            ScreenKit.Line(content, Loc.Get(SaveGame.RefillFlaskId + ".name"), 26, ScreenKit.Gold, true).name = "flask-name";
            ScreenKit.Line(content, Loc.Get(SaveGame.RefillFlaskId + ".desc"), 18, ScreenKit.Muted);
            ScreenKit.Line(content, ScreenKit.Fmt(Loc, "ui.vendor.price", ("amount", Loc.FormatInteger(stock.PriceGold))), 20, ScreenKit.Text).name = "flask-price";
            ScreenKit.Line(content, ScreenKit.Fmt(Loc, "ui.vendor.owned", ("n", stock.Owned.ToString()), ("max", stock.CarryCap.ToString())), 22, ScreenKit.Gold, true).name = "flask-owned";
            var gold = Save.Currency(SaveGame.GoldId);
            var missing = stock.CarryCap - stock.Owned;
            string buyReason = missing <= 0 ? Loc.Get("ui.vendor.flask_max") : gold < stock.PriceGold ? Loc.Get("ui.vendor.no_gold") : null;
            string fillReason = missing <= 0 ? Loc.Get("ui.vendor.flask_max") : gold < stock.PriceGold * missing ? Loc.Get("ui.vendor.no_gold") : null;
            var buttons = new VisualElement();
            buttons.style.marginTop = 14;
            content.Add(buttons);
            ItemWidgets.ReasonButton(buttons, Loc.Get("ui.vendor.buy_flask"), buyReason, () => BuyFlask(stock.Id, 1)).name = "act-buy-flask";
            var fill = ItemWidgets.ReasonButton(buttons, Loc.Get("ui.vendor.fill_flasks").Replace("3", stock.CarryCap.ToString()), fillReason, () => BuyFlask(stock.Id, missing));
            fill.name = "act-fill-flasks";
        }

        public VendorOutcome BuyFlask(string stockId, int qty)
        {
            var outcome = Save.VendorBuy(Rules, stockId, Math.Max(1, qty));
            if (outcome.Ok)
            {
                GameSession.Save.Save(Rules);
                message = ScreenKit.Fmt(Loc, "ui.vendor.bought", ("gold", Loc.FormatInteger(outcome.Gold)));
            }
            else message = VendorError(outcome.Result);
            Show();
            return outcome;
        }

        string VendorError(VendorResult result)
        {
            switch (result)
            {
                case VendorResult.Full: return Loc.Get("ui.vendor.err.full");
                case VendorResult.NoGold: return Loc.Get("ui.vendor.no_gold");
                case VendorResult.CarryCap: return Loc.Get("ui.vendor.flask_max");
                case VendorResult.NotFound: return Loc.Get("ui.vendor.err.not_found");
                default: return Loc.Get("ui.vendor.err.not_found");
            }
        }

        // ------------------------------------------------------------------------------------------------ confirmacao

        void ShowConfirm(string text, bool hold, Action onConfirm)
        {
            CloseModal();
            modal = new VisualElement { name = "vendor-modal" };
            modal.style.position = Position.Absolute;
            modal.style.left = 0;
            modal.style.right = 0;
            modal.style.top = 0;
            modal.style.bottom = 0;
            modal.style.alignItems = Align.Center;
            modal.style.justifyContent = Justify.Center;
            modal.style.backgroundColor = new Color(0f, 0f, 0f, 0.6f);
            var box = MenuUi.Card(modal);
            box.style.minWidth = 560;
            ScreenKit.Line(box, text, 24).style.unityTextAlign = TextAnchor.MiddleCenter;
            var row = ScreenKit.Row(box);
            if (hold) ScreenKit.HoldButton(row, Loc.Get("ui.common.hold_confirm"), 1f, () => { CloseModal(); onConfirm(); }).name = "confirm-sell";
            else ScreenKit.SmallButton(row, Loc.Get("ui.common.confirm"), () => { CloseModal(); onConfirm(); }).name = "confirm-sell";
            ScreenKit.SmallButton(row, Loc.Get("ui.common.cancel"), CloseModal).name = "cancel-sell";
            card.Add(modal);
        }

        void CloseModal()
        {
            modal?.RemoveFromHierarchy();
            modal = null;
        }

        // ------------------------------------------------------------------------------------------------ acesso para testes

        public void SelectForTest(ItemInstanceInfo item, ItemContainer container) => Select(item, container);

        /// <summary>Marca (ou desmarca) um item como lixo, como o Alt+clique.</summary>
        public void MarkForTest(ulong uid)
        {
            if (!marked.Remove(uid)) marked.Add(uid);
            Show();
        }

        public void SetTab(Tab value)
        {
            tab = value;
            Show();
        }
    }
}
