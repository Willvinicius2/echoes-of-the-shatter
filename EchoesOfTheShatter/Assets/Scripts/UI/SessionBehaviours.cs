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
    /// Raiz de UI das cenas de jogo (Refugio e Cripta): um UIDocument acima do HUD com o toast e o container das telas. Quem precisa avisar o
    /// jogador usa <see cref="ScreenHost.Current"/>.
    /// </summary>
    [RequireComponent(typeof(UIDocument))]
    public sealed class ScreenHost : MonoBehaviour
    {
        public static ScreenHost Current { get; private set; }

        public VisualElement Root { get; private set; }
        public ToastLayer Toasts { get; private set; }

        void Awake()
        {
            Current = this;
        }

        void OnEnable()
        {
            Current = this;
            Root = GetComponent<UIDocument>().rootVisualElement;
            Toasts = new ToastLayer(Root);
        }

        void OnDestroy()
        {
            if (Current == this) Current = null;
        }

        public static void Toast(string text)
        {
            if (Current != null && Current.Toasts != null) Current.Toasts.Show(text);
            else Debug.Log("[Toast] " + text);
        }
    }

    /// <summary>Autosave a cada 5 min (RF-54) e ao sair do jogo; a troca de area e a coleta gravam por conta propria.</summary>
    public sealed class AutosaveRunner : MonoBehaviour
    {
        [SerializeField] GameRoot root;
        float next;

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            next = Time.realtimeSinceStartup + SaveSettings.AutosaveSeconds;
        }

        void Update()
        {
            if (Time.realtimeSinceStartup < next) return;
            next = Time.realtimeSinceStartup + SaveSettings.AutosaveSeconds;
            SaveNow();
        }

        void OnApplicationQuit() => SaveNow();

        public void SaveNow()
        {
            var rules = GameSession.NativeRules(root);
            if (rules != null && GameSession.Save.HasSave) GameSession.Save.Save(rules);
        }
    }

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
