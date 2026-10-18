using System;
using System.Collections.Generic;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using Echoes.Interop.Native;
using UnityEngine;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// S-15 Encantador (docs/16 11.7; APIs do docs/09 secao 13). Escolhe a peca (Mochila, Bau ou equipada), mostra os afixos com a barra de qualidade e
    /// os passos de lapidacao e lista as 5 operacoes (Refinar, Reforjar com trava de 1 afixo, Adicionar afixo entre os candidatos do core, Lapidar,
    /// Desmontar), cada uma com o custo em Ouro e Lascas sempre a vista e, quando o botao esta cinza, o motivo escrito. Custo, resultado e candidatos
    /// sao do core (previa e confirmacao); aqui so UI. Cada melhoria grava o save e, se a peca esta equipada, refaz os atributos do heroi pelo core.
    /// </summary>
    public sealed class EnchantScreen
    {
        public enum Step { Pick, Confirm }

        /// <summary>Segundos segurando para Reforjar e Desmontar (docs/16 11.7); Raro ao Desmontar segura 1 s.</summary>
        public const float HoldSeconds = 0.5f;

        readonly VisualElement card;
        readonly GameRoot root;
        readonly HeroController hero;
        readonly Action close;
        ulong selectedUid;
        CraftOp? op;
        int lockedAffix = -1;
        int polishAffix = -1;
        int candidate = -1;
        AffixOfferInfo offer;
        int highlightAffix = -1;
        string message;

        public EnchantScreen(VisualElement host, GameRoot gameRoot, HeroController heroController, Action onClose)
        {
            card = host;
            root = gameRoot;
            hero = heroController;
            close = onClose;
        }

        LocalizationService Loc => root.Localization;
        NativeRulesCore Rules => GameSession.NativeRules(root);
        SaveGame Save => GameSession.Save.Current;

        public ulong SelectedUid => selectedUid;
        public CraftOp? CurrentOp => op;
        public string Message => message;

        public void Show()
        {
            card.Clear();
            card.style.minWidth = 1500;
            MenuUi.Title(card, "ui.enchant.title", Loc, 34).style.marginBottom = 8;
            var body = new VisualElement { name = "enchant-body" };
            body.style.flexDirection = FlexDirection.Row;
            card.Add(body);
            BuildLeft(body);
            BuildCenter(body);
            BuildRight(body);
            ItemWidgets.FooterResources(card, Loc, Rules);
            if (!string.IsNullOrEmpty(message)) ScreenKit.Line(card, message, 20, ScreenKit.Gold).name = "enchant-message";
            var bottom = ScreenKit.Row(card);
            bottom.style.justifyContent = Justify.FlexEnd;
            ScreenKit.SmallButton(bottom, Loc.Get("ui.common.close"), () => close()).name = "enchant-close";
        }

        // ------------------------------------------------------------------------------------------------ item

        ItemInstanceInfo Find(ulong uid)
        {
            foreach (var item in Save.Equipment(0)) if (item != null && item.Uid == uid) return item;
            foreach (var container in new[] { ItemContainer.Backpack, ItemContainer.Stash })
            {
                var found = Save.ListItems(0, container).Find(i => i.Uid == uid);
                if (found != null) return found;
            }
            return null;
        }

        bool IsEquipped(ulong uid)
        {
            foreach (var item in Save.Equipment(0)) if (item != null && item.Uid == uid) return true;
            return false;
        }

        public void SelectItem(ulong uid)
        {
            selectedUid = uid;
            op = null;
            lockedAffix = -1;
            polishAffix = -1;
            candidate = -1;
            offer = null;
            highlightAffix = -1;
            message = null;
            Show();
        }

        // ------------------------------------------------------------------------------------------------ coluna da esquerda: equipamento e grades

        void BuildLeft(VisualElement body)
        {
            var left = new VisualElement { name = "enchant-left" };
            body.Add(left);
            var equipped = new VisualElement { name = "enchant-equipment" };
            equipped.style.flexDirection = FlexDirection.Row;
            left.Add(equipped);
            var equipment = Save.Equipment(0);
            for (var i = 0; i < equipment.Length; i++)
            {
                var item = equipment[i];
                if (!SaveGame.SlotEnabled(Rules, i) || item == null) continue;
                AddCell(equipped, item);
            }
            var info = Save.Inventory(Rules, 0);
            ScreenKit.Line(left, Loc.Get("ui.inventory.backpack").Replace("{used}", info.BackpackUsed.ToString()).Replace("{cap}", info.BackpackCapacity.ToString()), 18, ScreenKit.Gold, true);
            var grid = ItemWidgets.MakeGrid(left, 4 * (ItemWidgets.Cell + 4));
            foreach (var item in Save.ListItems(0, ItemContainer.Backpack)) AddCell(grid, item);
            ScreenKit.Line(left, Loc.Get("ui.inventory.stash").Replace("{used}", info.StashUsed.ToString()).Replace("{cap}", info.StashCapacity.ToString()), 18, ScreenKit.Gold, true);
            var stash = ItemWidgets.MakeGrid(left, 3 * (ItemWidgets.Cell + 4));
            foreach (var item in Save.ListItems(0, ItemContainer.Stash)) AddCell(stash, item);
        }

        void AddCell(VisualElement grid, ItemInstanceInfo item)
        {
            var cell = ItemWidgets.MakeCell(Loc, item, item.Uid == selectedUid);
            var uid = item.Uid;
            cell.RegisterCallback<PointerDownEvent>(_ => SelectItem(uid));
            grid.Add(cell);
        }

        // ------------------------------------------------------------------------------------------------ centro: item ou confirmacao

        void BuildCenter(VisualElement body)
        {
            var center = new VisualElement { name = "enchant-center" };
            center.AddToClassList("art-frame-plain");
            center.style.width = 520;
            center.style.minHeight = 640;
            center.style.marginLeft = 20;
            center.style.paddingLeft = 26;
            center.style.paddingRight = 26;
            center.style.paddingTop = 22;
            body.Add(center);
            var item = selectedUid != 0 ? Find(selectedUid) : null;
            if (item == null)
            {
                ScreenKit.Line(center, Loc.Get("ui.enchant.pick_item"), 20, ScreenKit.Muted).name = "pick-hint";
                return;
            }
            ItemWidgets.FillDetail(center, Loc, Rules, item);
            if (IsEquipped(item.Uid)) ScreenKit.Line(center, Loc.Get("ui.inventory.equipped"), 16, ScreenKit.Muted);
            var polishMax = PolishMax();
            for (var i = 0; i < item.Affixes.Count; i++) center.Add(AffixWidget(item, i, polishMax));
            if (op.HasValue) BuildConfirm(center, item);
        }

        // polish_max_steps do rules.csv (o core so devolve o passo atual na previa).
        static int PolishMax() => (int)RulesCsv.Number("polish_max_steps", 3.0);

        VisualElement AffixWidget(ItemInstanceInfo item, int index, int polishMax)
        {
            var row = ItemWidgets.AffixRow(Loc, Rules, item.Affixes[index], polishMax, index == highlightAffix);
            row.name = "affix-" + index;
            if (op == CraftOp.Polish || op == CraftOp.Reforge)
            {
                var captured = index;
                row.RegisterCallback<PointerDownEvent>(_ => OnAffixClicked(captured));
                if ((op == CraftOp.Polish && polishAffix == index) || (op == CraftOp.Reforge && lockedAffix == index))
                    row.style.backgroundColor = new Color(0.25f, 0.2f, 0.12f, 0.8f);
            }
            return row;
        }

        void OnAffixClicked(int index)
        {
            if (op == CraftOp.Polish) polishAffix = index;
            else if (op == CraftOp.Reforge) lockedAffix = lockedAffix == index ? -1 : index; // 1 afixo travado no maximo
            Show();
        }

        // ------------------------------------------------------------------------------------------------ direita: operacoes

        static readonly CraftOp[] Ops = { CraftOp.Refine, CraftOp.Reforge, CraftOp.Add, CraftOp.Polish, CraftOp.Dismantle };

        void BuildRight(VisualElement body)
        {
            var right = new VisualElement { name = "enchant-ops" };
            right.style.marginLeft = 20;
            right.style.width = 340;
            body.Add(right);
            var item = selectedUid != 0 ? Find(selectedUid) : null;
            if (item == null) return;
            foreach (var candidateOp in Ops)
            {
                var quote = QuoteFor(item, candidateOp);
                var reason = ReasonFor(quote);
                var captured = candidateOp;
                var holder = new VisualElement { name = "op-" + candidateOp.ToString().ToLowerInvariant() };
                holder.style.marginBottom = 10;
                right.Add(holder);
                var button = ItemWidgets.ReasonButton(holder, Loc.Get(OpKey(candidateOp)), reason, () => ChooseOp(captured));
                button.name = "btn-" + candidateOp.ToString().ToLowerInvariant();
                button.style.width = 330;
                if (candidateOp == op) button.style.color = ScreenKit.Gold;
                // O custo fica sempre a vista (vermelho quando falta Ouro ou Lascas).
                if (quote.Result == CraftResult.Ok || quote.Result == CraftResult.NoGold || quote.Result == CraftResult.NoShards)
                    CostLine(holder, quote, candidateOp);
                if (quote.ExpeditionRunning && IsEquipped(item.Uid))
                    ScreenKit.Line(holder, Loc.Get("ui.enchant.err.expedition_running"), 14, ScreenKit.Muted);
            }
        }

        string OpKey(CraftOp o) => "ui.enchant.op." + o.ToString().ToLowerInvariant();

        CraftQuote QuoteFor(ItemInstanceInfo item, CraftOp o)
        {
            if (o != CraftOp.Polish) return Save.QuoteCraft(Rules, 0, item.Uid, o);
            // Lapidar: a previa e por afixo; vale se ha ao menos um afixo que ainda sobe.
            CraftQuote last = null;
            for (var i = 0; i < Math.Max(1, item.Affixes.Count); i++)
            {
                var quote = Save.QuoteCraft(Rules, 0, item.Uid, o, i);
                if (quote.Result == CraftResult.Ok || quote.Result == CraftResult.NoGold || quote.Result == CraftResult.NoShards) return quote;
                last = quote;
            }
            return last ?? Save.QuoteCraft(Rules, 0, item.Uid, o, 0);
        }

        void CostLine(VisualElement parent, CraftQuote quote, CraftOp o)
        {
            var shards = o == CraftOp.Reforge ? quote.ShardsNoLock : quote.Shards;
            var line = new VisualElement { name = "cost" };
            line.style.flexDirection = FlexDirection.Row;
            parent.Add(line);
            if (o == CraftOp.Dismantle)
            {
                ScreenKit.Line(line, ScreenKit.Fmt(Loc, "ui.enchant.gain", ("n", Loc.FormatInteger(quote.ShardsGain))), 16, ItemText.MagicColor).style.marginTop = 0;
                return;
            }
            var goldColor = quote.HaveGold >= quote.Gold ? ScreenKit.Gold : ScreenKit.Bad;
            var shardColor = quote.HaveShards >= shards ? ItemText.MagicColor : ScreenKit.Bad;
            var gold = ScreenKit.Line(line, Loc.Get("ui.enchant.cost") + ": " + Loc.FormatInteger(quote.Gold) + " " + Loc.Get("ui.common.gold"), 16, goldColor);
            gold.name = "cost-gold";
            gold.style.marginTop = 0;
            gold.style.marginRight = 14;
            var sh = ScreenKit.Line(line, Loc.FormatInteger(shards) + " " + Loc.Get("ui.inventory.shards"), 16, shardColor);
            sh.name = "cost-shards";
            sh.style.marginTop = 0;
        }

        /// <summary>Motivo escrito do botao cinza (null = habilitado).</summary>
        public string ReasonFor(CraftQuote quote)
        {
            switch (quote.Result)
            {
                case CraftResult.Ok: return null;
                case CraftResult.Unique: return Loc.Get("ui.enchant.err.unique");
                case CraftResult.WrongRarity: return Loc.Get("ui.enchant.err.wrong_rarity");
                case CraftResult.AffixLimit: return Loc.Get("ui.enchant.err.max_affixes");
                case CraftResult.AlreadyInscribed: return Loc.Get("ui.enchant.err.inscribed");
                case CraftResult.PolishMax: return Loc.Get("ui.enchant.err.max_polish");
                case CraftResult.NoCandidate: return Loc.Get("ui.enchant.err.no_candidate");
                case CraftResult.NoGold: return Loc.Get("ui.enchant.err.no_gold");
                case CraftResult.NoShards: return Loc.Get("ui.enchant.err.no_shards");
                case CraftResult.EquippedDismantle: return Loc.Get("ui.enchant.err.equipped_dismantle");
                case CraftResult.BadIndex: return Loc.Get("ui.enchant.err.bad_index");
                default: return Loc.Get("ui.enchant.err.not_found");
            }
        }

        void ChooseOp(CraftOp chosen)
        {
            op = chosen;
            lockedAffix = -1;
            polishAffix = -1;
            candidate = -1;
            offer = chosen == CraftOp.Add ? Save.CraftAddAffixOffer(Rules, 0, selectedUid) : null;
            message = null;
            if (chosen == CraftOp.Polish)
            {
                var item = Find(selectedUid);
                for (var i = 0; item != null && i < item.Affixes.Count; i++)
                {
                    var q = Save.QuoteCraft(Rules, 0, selectedUid, CraftOp.Polish, i);
                    if (q.Result == CraftResult.Ok) { polishAffix = i; break; }
                }
            }
            Show();
        }

        // ------------------------------------------------------------------------------------------------ confirmacao

        void BuildConfirm(VisualElement center, ItemInstanceInfo item)
        {
            var box = new VisualElement { name = "confirm-box" };
            box.style.marginTop = 18;
            box.style.paddingTop = 10;
            box.style.borderTopWidth = 1;
            box.style.borderTopColor = ScreenKit.Gold;
            center.Add(box);
            ScreenKit.Line(box, Loc.Get(OpKey(op.Value)), 24, ScreenKit.Gold, true);
            switch (op.Value)
            {
                case CraftOp.Refine: ConfirmRefine(box); break;
                case CraftOp.Reforge: ConfirmReforge(box, item); break;
                case CraftOp.Add: ConfirmAdd(box); break;
                case CraftOp.Polish: ConfirmPolish(box, item); break;
                default: ConfirmDismantle(box, item); break;
            }
            ScreenKit.SmallButton(box, Loc.Get("ui.common.back"), () => { op = null; Show(); }).name = "confirm-back";
        }

        void ConfirmRefine(VisualElement box)
        {
            var q = Save.QuoteCraft(Rules, 0, selectedUid, CraftOp.Refine);
            ScreenKit.Line(box, ScreenKit.Fmt(Loc, "ui.enchant.refine_range", ("min", q.AffixCountMin.ToString()), ("max", q.AffixCountMax.ToString())), 18);
            CostLine(box, q, CraftOp.Refine);
            Confirm(box, ReasonFor(q), false, 0f, () => Apply(Save.CraftRefine(Rules, 0, selectedUid)));
        }

        void ConfirmReforge(VisualElement box, ItemInstanceInfo item)
        {
            var q = Save.QuoteCraft(Rules, 0, selectedUid, CraftOp.Reforge);
            ScreenKit.Line(box, Loc.Get("ui.enchant.warn_reforge"), 17, ScreenKit.Bad).name = "warn-reforge"; // aviso fixo (Q3-6): nao da para desfazer
            ScreenKit.Line(box, Loc.Get("ui.enchant.lock_hint"), 16, ScreenKit.Muted);
            var shards = lockedAffix >= 0 ? q.ShardsWithLock : q.ShardsNoLock;
            var cost = new VisualElement { name = "cost" };
            cost.style.flexDirection = FlexDirection.Row;
            box.Add(cost);
            var goldText = ScreenKit.Line(cost, Loc.Get("ui.enchant.cost") + ": " + Loc.FormatInteger(q.Gold) + " " + Loc.Get("ui.common.gold"), 16, q.HaveGold >= q.Gold ? ScreenKit.Gold : ScreenKit.Bad);
            goldText.name = "cost-gold";
            goldText.style.marginRight = 14;
            ScreenKit.Line(cost, Loc.FormatInteger(q.ShardsNoLock) + " / " + Loc.FormatInteger(q.ShardsWithLock) + " " + Loc.Get("ui.inventory.shards") + " (" + Loc.Get("ui.enchant.lock") + ")", 16, q.HaveShards >= shards ? ItemText.MagicColor : ScreenKit.Bad).name = "cost-shards";
            string reason = ReasonFor(q);
            if (reason == null && q.HaveShards < shards) reason = Loc.Get("ui.enchant.err.no_shards");
            var captured = lockedAffix;
            Confirm(box, reason, true, HoldSeconds, () => Apply(Save.CraftReforge(Rules, 0, selectedUid, captured)));
        }

        void ConfirmAdd(VisualElement box)
        {
            if (offer == null || offer.Candidates.Count == 0)
            {
                ScreenKit.Line(box, Loc.Get("ui.enchant.err.no_candidate"), 18, ScreenKit.Muted).name = "no-candidates";
                return;
            }
            var cards = new VisualElement { name = "candidates" };
            cards.style.flexDirection = FlexDirection.Row;
            box.Add(cards);
            for (var i = 0; i < offer.Candidates.Count; i++)
            {
                var c = offer.Candidates[i];
                var (_, _, stat, modKind) = ItemWidgets.AffixRange(Rules, c.AffixId);
                var cardView = new VisualElement { name = "candidate-" + i };
                cardView.AddToClassList("art-frame-plain");
                cardView.style.width = 150;
                cardView.style.marginRight = 8;
                cardView.style.paddingLeft = 14;
                cardView.style.paddingRight = 14;
                cardView.style.paddingTop = 12;
                cardView.style.paddingBottom = 12;
                if (candidate == i) cardView.style.unityBackgroundImageTintColor = new Color(1.35f, 1.2f, 0.8f, 1f);
                ScreenKit.Line(cardView, ItemText.StatName(Loc, stat), 16, ItemText.MagicColor, true);
                ScreenKit.Line(cardView, ItemText.ModLine(Loc, stat, modKind, c.Min) + " - " + ItemText.ModLine(Loc, stat, modKind, c.Max), 14, ScreenKit.Muted);
                var index = i;
                cardView.RegisterCallback<PointerDownEvent>(_ => { candidate = index; Show(); });
                cards.Add(cardView);
            }
            var cost = Save.QuoteCraft(Rules, 0, selectedUid, CraftOp.Add);
            CostLine(box, cost, CraftOp.Add);
            var reason = candidate < 0 ? Loc.Get("ui.enchant.choose_one") : ReasonFor(cost);
            var chosen = candidate;
            Confirm(box, reason, false, 0f, () => Apply(Save.CraftAddAffixApply(Rules, 0, selectedUid, chosen)));
        }

        void ConfirmPolish(VisualElement box, ItemInstanceInfo item)
        {
            if (polishAffix < 0)
            {
                ScreenKit.Line(box, Loc.Get("ui.enchant.polish_pick"), 18, ScreenKit.Muted);
                return;
            }
            var q = Save.QuoteCraft(Rules, 0, selectedUid, CraftOp.Polish, polishAffix);
            var (_, _, stat, modKind) = ItemWidgets.AffixRange(Rules, item.Affixes[polishAffix].AffixId);
            ScreenKit.Line(box, ScreenKit.Fmt(Loc, "ui.enchant.step", ("n", q.PolishStep.ToString()), ("total", PolishMax().ToString())), 16, ScreenKit.Muted);
            ScreenKit.Line(box, ItemText.ModLine(Loc, stat, modKind, q.PolishFrom) + " → " + ItemText.ModLine(Loc, stat, modKind, q.PolishTo), 20, ItemText.RareColor).name = "polish-preview";
            CostLine(box, q, CraftOp.Polish);
            var index = polishAffix;
            Confirm(box, ReasonFor(q), false, 0f, () => Apply(Save.CraftPolish(Rules, 0, selectedUid, index)));
        }

        void ConfirmDismantle(VisualElement box, ItemInstanceInfo item)
        {
            var q = Save.QuoteCraft(Rules, 0, selectedUid, CraftOp.Dismantle);
            ScreenKit.Line(box, ScreenKit.Fmt(Loc, "ui.enchant.dismantle_gain", ("n", Loc.FormatInteger(q.ShardsGain))), 18, ItemText.MagicColor).name = "dismantle-gain";
            Confirm(box, ReasonFor(q), true, item.Rarity == ItemRarity.Rare ? 1f : HoldSeconds, () => Apply(Save.CraftDismantle(Rules, 0, selectedUid)));
        }

        void Confirm(VisualElement box, string reason, bool hold, float seconds, Action action)
        {
            var holder = new VisualElement { name = "confirm-holder" };
            box.Add(holder);
            Button button;
            if (hold && string.IsNullOrEmpty(reason)) button = ScreenKit.HoldButton(holder, Loc.Get("ui.common.hold_confirm"), seconds, action);
            else button = ItemWidgets.ReasonButton(holder, Loc.Get("ui.enchant.confirm"), reason, action);
            button.name = "confirm";
        }

        // ------------------------------------------------------------------------------------------------ resultado

        /// <summary>Aplica o resultado do core: grava o save, refaz os atributos do heroi se a peca e equipada e mostra o item novo com o afixo alterado em destaque.</summary>
        public void Apply(CraftOutcome outcome)
        {
            if (!outcome.Ok)
            {
                message = Loc.Get("ui.enchant.err.not_found");
                if (outcome.Result == CraftResult.NoGold) message = Loc.Get("ui.enchant.err.no_gold");
                else if (outcome.Result == CraftResult.NoShards) message = Loc.Get("ui.enchant.err.no_shards");
                Show();
                return;
            }
            var wasEquipped = IsEquipped(selectedUid);
            GameSession.Save.Save(Rules); // RF-54: salva ao melhorar
            if (wasEquipped && hero != null) hero.RefreshFromSave(); // o core refaz o bloco de atributos do heroi com o item novo
            var dismantled = op == CraftOp.Dismantle;
            highlightAffix = outcome.ChangedAffix;
            op = null;
            lockedAffix = -1;
            polishAffix = -1;
            candidate = -1;
            offer = null;
            if (dismantled) selectedUid = 0;
            message = Loc.Get("ui.enchant.result");
            ScreenHost.Toast(Loc.Get("ui.enchant.result"), ToastKind.Item);
            Show();
        }

        // ------------------------------------------------------------------------------------------------ acesso para testes

        public void ChooseOpForTest(CraftOp chosen) => ChooseOp(chosen);

        public void SelectOfferForTest(int index)
        {
            candidate = index;
            Show();
        }

        public void SelectAffixForTest(int index) => OnAffixClicked(index);
    }
}
