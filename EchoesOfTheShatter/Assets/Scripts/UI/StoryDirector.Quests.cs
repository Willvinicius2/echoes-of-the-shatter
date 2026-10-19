using System.Collections.Generic;
using Echoes.Core;
using Echoes.Interop;
using UnityEngine;
using UnityEngine.InputSystem;

namespace Echoes.UI
{
    // Missoes da Regiao 1 no cliente (docs/design/21 secao "Missoes"): o progresso e do core (quests.csv, campo `story.quests` do save); aqui so
    // avisos de evento (falar com NPC, chegar ao Guardiao), o toast de conclusao e o diario na tecla J.
    public sealed partial class StoryDirector
    {
        QuestJournal journal;
        readonly HashSet<string> doneQuests = new HashSet<string>();

        /// <summary>O diario de missoes esta aberto.</summary>
        public static bool JournalOpen { get; private set; }

        void InitQuests(StoryState state)
        {
            doneQuests.Clear();
            foreach (var quest in state.Quests) if (quest.IsDone) doneQuests.Add(quest.QuestId);
        }

        void Update()
        {
            var keyboard = Keyboard.current;
            if (keyboard == null || db == null) return;
            if (keyboard[Key.J].wasPressedThisFrame && (JournalOpen || (!VerdictOpen && !RefugeController.AnyScreenOpen))) ToggleJournal();
            else if (JournalOpen && keyboard[Key.Escape].wasPressedThisFrame) ToggleJournal();
        }

        void ToggleJournal()
        {
            if (JournalOpen)
            {
                journal?.Close();
                journal = null;
                JournalOpen = false;
                return;
            }
            if (host == null || host.Root == null) host = ScreenHost.Current;
            if (host == null) return;
            journal = new QuestJournal(host.Root, Loc, CurrentState());
            journal.Show();
            JournalOpen = true;
        }

        /// <summary>
        /// Avisa um evento de missao ao core ("talk" + id do NPC, "reach_map_boss" + id do mapa). Se concluir alguma, grava o save e avisa o jogador.
        /// Devolve quantas missoes foram concluidas agora (0 sem historia carregada).
        /// </summary>
        public int ReportQuest(string type, string target)
        {
            if (db == null || string.IsNullOrEmpty(target)) return 0;
            var completed = Save.StoryQuestEvent(db, type, target);
            if (completed <= 0) return 0;
            GameSession.Save.Save(rules); // RF-54: progresso de missao vai para o disco
            AnnounceQuests();
            return completed;
        }

        // Compara com as concluidas ja conhecidas e avisa as novas (Ecos e veredito concluem missoes sozinhos no core).
        void AnnounceQuests()
        {
            if (db == null) return;
            var state = Save.ReadStory(db);
            var any = false;
            foreach (var quest in state.Quests)
            {
                if (!quest.IsDone || !doneQuests.Add(quest.QuestId)) continue;
                any = true;
                ScreenHost.Toast(ScreenKit.Fmt(Loc, "ui.quest.done", ("name", Loc.Get(quest.QuestId + ".name"))), ToastKind.Banner);
                if (Loc.TryGet("ui.quest.reward." + quest.Reward, out var reward))
                    ScreenHost.Toast(ScreenKit.Fmt(Loc, "ui.quest.reward", ("text", reward)), ToastKind.Info);
            }
            if (any) GameSession.Save.Save(rules);
        }
    }
}
