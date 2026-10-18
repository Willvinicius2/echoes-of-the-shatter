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
        public BannerLayer Banners { get; private set; }
        public FadeLayer Fade { get; private set; }

        /// <summary>true so na primeira montagem depois de uma troca de cena: a nova cena sai do preto (fade de portal).</summary>
        public static bool FadeInOnNextScene;

        void Awake()
        {
            Current = this;
        }

        void OnEnable()
        {
            Current = this;
            Root = GetComponent<UIDocument>().rootVisualElement;
            Toasts = new ToastLayer(Root);
            Banners = new BannerLayer(Root);
            Fade = new FadeLayer(Root, FadeInOnNextScene);
            if (FadeInOnNextScene)
            {
                FadeInOnNextScene = false;
                Fade.FadeTo(0f, FadeLayer.DefaultSeconds);
            }
        }

        void OnDestroy()
        {
            if (Current == this) Current = null;
        }

        /// <summary>Faixa larga (nome da area, vitoria); sem ScreenHost vai para o log.</summary>
        public static void Banner(string title, string subtitle = null, float seconds = 3f)
        {
            if (Current != null && Current.Banners != null) Current.Banners.Show(title, subtitle, seconds);
            else Debug.Log("[Banner] " + title + (string.IsNullOrEmpty(subtitle) ? string.Empty : " - " + subtitle));
        }

        public static void Toast(string text, ToastKind kind = ToastKind.Info)
        {
            if (Current != null && Current.Toasts != null) Current.Toasts.Show(text, kind);
            else Debug.Log("[Toast] " + text);
        }
    }
}
