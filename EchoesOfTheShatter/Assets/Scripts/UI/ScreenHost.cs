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

        public static void Toast(string text, ToastKind kind = ToastKind.Info)
        {
            if (Current != null && Current.Toasts != null) Current.Toasts.Show(text, kind);
            else Debug.Log("[Toast] " + text);
        }
    }
}
