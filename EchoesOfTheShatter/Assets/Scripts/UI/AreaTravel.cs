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
            Go(rules, target == CryptArea ? GameFlow.CriptaScene : GameFlow.RefugeScene);
        }

        static bool traveling;

        /// <summary>Troca de area com autosave e fade (portais e "Jogar esta rota agora"). Chamadas repetidas durante a transicao sao ignoradas.</summary>
        public static void Go(Echoes.Interop.Native.NativeRulesCore rules, string scene)
        {
            if (traveling) return;
            traveling = true;
            if (rules != null && GameSession.Save.HasSave) GameSession.Save.Save(rules); // troca de area: autosave
            var fade = ScreenHost.Current != null ? ScreenHost.Current.Fade : null;
            if (fade == null)
            {
                Load(scene);
                return;
            }
            // Fade de portal (F-06): escurece, troca a cena e a nova cena sai do preto (ScreenHost.FadeInOnNextScene).
            fade.FadeTo(1f, FadeLayer.DefaultSeconds, () => Load(scene));
        }

        static void Load(string scene)
        {
            traveling = false;
            Time.timeScale = 1f;
            ScreenHost.FadeInOnNextScene = true;
            SceneManager.LoadScene(scene, LoadSceneMode.Single);
        }
    }
}
