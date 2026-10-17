using System;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop.Native;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Na Cripta: vencer o Guardiao grava o dominio da area e as cargas (RecordAreaRun, RF-35 e RF-50) e salva antes de qualquer outra coisa (RF-55).
    /// Sem save carregado (cena aberta direto no editor) nao faz nada.
    /// </summary>
    public sealed class RunRecorder : MonoBehaviour
    {
        [SerializeField] GameRoot root;
        bool subscribed;
        bool recorded;

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (root == null || root.Events == null) return;
            root.Events.Subscribe<ArenaStateEvent>(OnArena);
            subscribed = true;
        }

        void OnDestroy()
        {
            if (subscribed && root != null && root.Events != null) root.Events.Unsubscribe<ArenaStateEvent>(OnArena);
        }

        void OnArena(in ArenaStateEvent evt)
        {
            if (evt.Phase != ArenaPhase.Won || recorded) return;
            var rules = GameSession.NativeRules(root);
            if (rules == null || !GameSession.Save.HasSave) return;
            recorded = true;
            var reward = GameSession.Save.Current.RecordAreaRun(rules, 0, ExpeditionConfig.CryptMap, true, true);
            GameSession.Save.Save(rules);
            if (reward.ChargesGained > 0) ScreenHost.Toast("+" + reward.ChargesGained + " " + root.Localization.Get("ui.hud.charges"));
        }
    }
}
