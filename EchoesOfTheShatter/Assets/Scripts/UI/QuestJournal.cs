using System.Collections.Generic;
using Echoes.Core;
using Echoes.Interop;
using UnityEngine;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Diario de missoes (tecla J): lista as missoes liberadas e as concluidas, com progresso. So UI; estado, progresso e status vem do core
    /// (<see cref="StoryQuestInfo"/>) e os textos do Loc (<c>quest.*.name</c>, <c>quest.*.desc</c>). Missao trancada nao aparece.
    /// </summary>
    public sealed class QuestJournal
    {
        readonly VisualElement host;
        readonly LocalizationService loc;
        readonly StoryState state;
        VisualElement backdrop;

        public QuestJournal(VisualElement host, LocalizationService loc, StoryState state)
        {
            this.host = host;
            this.loc = loc;
            this.state = state ?? new StoryState();
        }

        public bool IsOpen => backdrop != null;

        /// <summary>Missoes que o diario mostra, na ordem da tabela: as ativas primeiro, depois as concluidas.</summary>
        public static List<StoryQuestInfo> Visible(StoryState state)
        {
            var list = new List<StoryQuestInfo>();
            if (state == null) return list;
            foreach (var q in state.Quests) if (q.IsActive) list.Add(q);
            foreach (var q in state.Quests) if (q.IsDone) list.Add(q);
            return list;
        }

        public void Show()
        {
            Close();
            backdrop = MenuUi.Backdrop(host, 0.7f);
            backdrop.name = "quest-journal";
            backdrop.pickingMode = PickingMode.Position;
            var card = MenuUi.Card(backdrop);
            card.style.minWidth = 760;
            MenuUi.Title(card, "ui.quest.title", loc, 40);
            var shown = Visible(state);
            if (shown.Count == 0) ScreenKit.Line(card, loc.Get("ui.quest.empty"), 22, ScreenKit.Muted);
            foreach (var q in shown) AddEntry(card, q);
            var hint = ScreenKit.Line(card, loc.Get("ui.quest.close_hint"), 18, ScreenKit.Muted);
            hint.style.marginTop = 14;
            hint.style.unityTextAlign = TextAnchor.MiddleCenter;
        }

        void AddEntry(VisualElement card, StoryQuestInfo q)
        {
            var done = q.IsDone;
            var title = loc.Get(q.QuestId + ".name");
            if (q.ObjectiveCount > 1) title += $"  {Mathf.Min(q.Progress, q.ObjectiveCount)}/{q.ObjectiveCount}";
            var head = ScreenKit.Line(card, (done ? "✔ " : "• ") + title, 26, done ? ScreenKit.Good : ScreenKit.Gold, true);
            head.style.marginTop = 12;
            if (loc.TryGet(q.QuestId + ".desc", out var desc)) ScreenKit.Line(card, desc, 20, done ? ScreenKit.Muted : ScreenKit.Text);
        }

        public void Close()
        {
            backdrop?.RemoveFromHierarchy();
            backdrop = null;
        }
    }
}
