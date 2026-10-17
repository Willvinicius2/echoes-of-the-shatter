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
    /// Trocas de area: o portal publica PortalUsedEvent e esta classe grava (autosave de troca de area) e carrega a cena. Do Refugio para a Cripta
    /// o heroi ocupado numa expedicao fica retido com a fala dlg.ilsa.busy (setting).
    /// </summary>
    public sealed class AreaTravel : MonoBehaviour
    {
        public const string RefugeArea = "area.refuge";
        public const string CryptArea = "area.crypt";

        [SerializeField] GameRoot root;
        bool subscribed;

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (root == null || root.Events == null) return;
            root.Events.Subscribe<PortalUsedEvent>(OnPortal);
            subscribed = true;
        }

        void OnDestroy()
        {
            if (subscribed && root != null && root.Events != null) root.Events.Unsubscribe<PortalUsedEvent>(OnPortal);
        }

        void OnPortal(in PortalUsedEvent evt)
        {
            var rules = GameSession.NativeRules(root);
            var target = evt.TargetArea;
            if (target == CryptArea && rules != null && GameSession.Expedition.IsHeroBusy)
            {
                ScreenHost.Toast(root.Localization.Get("dlg.ilsa.busy"));
                return;
            }
            if (rules != null && GameSession.Save.HasSave) GameSession.Save.Save(rules); // troca de area: autosave
            Time.timeScale = 1f;
            SceneManager.LoadScene(target == CryptArea ? GameFlow.CriptaScene : GameFlow.RefugeScene, LoadSceneMode.Single);
        }
    }
}
