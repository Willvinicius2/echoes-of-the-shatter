using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Faixa larga no meio-alto da tela (nome da area por 3 s no F-06, vitoria sobre o Guardiao no S-13). Em FILA (uma por vez, nenhuma se perde),
    /// com fade de entrada e saida; usa tempo real (funciona com o jogo pausado).
    /// </summary>
    public sealed class BannerLayer
    {
        sealed class Entry
        {
            public string Title, Subtitle;
            public float Seconds;
        }

        public const float FadeSeconds = 0.35f;

        readonly VisualElement band;
        readonly Label title;
        readonly Label subtitle;
        readonly Queue<Entry> pending = new Queue<Entry>();
        readonly List<string> shown = new List<string>();
        bool showing;

        public BannerLayer(VisualElement root)
        {
            band = new VisualElement { name = "banner" };
            band.style.position = Position.Absolute;
            band.style.left = 0;
            band.style.right = 0;
            band.style.top = new Length(18, LengthUnit.Percent);
            band.style.minHeight = 140;
            band.style.alignItems = Align.Center;
            band.style.justifyContent = Justify.Center;
            band.style.paddingTop = 18;
            band.style.paddingBottom = 18;
            band.style.opacity = 0f;
            band.style.display = DisplayStyle.None;
            band.pickingMode = PickingMode.Ignore;
            band.style.backgroundColor = new Color(0.04f, 0.03f, 0.06f, 0.82f);
            var edge = new Color(0.72f, 0.56f, 0.26f, 1f);
            band.style.borderTopWidth = 2;
            band.style.borderBottomWidth = 2;
            band.style.borderTopColor = edge;
            band.style.borderBottomColor = edge;
            band.style.transitionProperty = new List<StylePropertyName> { new StylePropertyName("opacity") };
            band.style.transitionDuration = new List<TimeValue> { new TimeValue(FadeSeconds, TimeUnit.Second) };
            title = new Label();
            title.style.fontSize = 54;
            title.style.color = ScreenKit.Gold;
            title.style.unityFontStyleAndWeight = FontStyle.Bold;
            title.style.unityTextAlign = TextAnchor.MiddleCenter;
            title.pickingMode = PickingMode.Ignore;
            subtitle = new Label();
            subtitle.style.fontSize = 28;
            subtitle.style.color = ScreenKit.Text;
            subtitle.style.unityTextAlign = TextAnchor.MiddleCenter;
            subtitle.style.marginTop = 6;
            subtitle.pickingMode = PickingMode.Ignore;
            band.Add(title);
            band.Add(subtitle);
            root.Add(band);
        }

        /// <summary>Textos da faixa que esta na tela agora (vazio se nenhuma).</summary>
        public string Current => band.style.display == DisplayStyle.Flex ? title.text : string.Empty;
        public string CurrentSubtitle => band.style.display == DisplayStyle.Flex ? subtitle.text : string.Empty;
        public int PendingCount => pending.Count;

        /// <summary>Titulos de tudo que ja apareceu (testes).</summary>
        public IReadOnlyList<string> Shown => shown;

        public void Show(string titleText, string subtitleText, float seconds)
        {
            pending.Enqueue(new Entry { Title = titleText, Subtitle = subtitleText ?? string.Empty, Seconds = Mathf.Max(0.5f, seconds) });
            if (!showing) Next();
        }

        void Next()
        {
            if (pending.Count == 0)
            {
                showing = false;
                band.style.display = DisplayStyle.None;
                return;
            }
            var entry = pending.Dequeue();
            showing = true;
            title.text = entry.Title;
            subtitle.text = entry.Subtitle;
            subtitle.style.display = string.IsNullOrEmpty(entry.Subtitle) ? DisplayStyle.None : DisplayStyle.Flex;
            shown.Add(entry.Title);
            band.style.display = DisplayStyle.Flex;
            band.schedule.Execute(() => band.style.opacity = 1f).StartingIn(30);
            var total = (long)(entry.Seconds * 1000f);
            band.schedule.Execute(() => band.style.opacity = 0f).StartingIn(Math.Max(60, total - (long)(FadeSeconds * 1000f)));
            band.schedule.Execute(Next).StartingIn(total);
        }
    }

    /// <summary>Camada preta de tela cheia para o fade da troca de area (portais): sai do preto ao entrar e vai ao preto antes de trocar a cena.</summary>
    public sealed class FadeLayer
    {
        public const float DefaultSeconds = 0.4f;

        readonly VisualElement layer;
        IVisualElementScheduledItem tick;

        public FadeLayer(VisualElement root, bool startBlack)
        {
            layer = new VisualElement { name = "fade" };
            layer.style.position = Position.Absolute;
            layer.style.left = 0;
            layer.style.right = 0;
            layer.style.top = 0;
            layer.style.bottom = 0;
            layer.style.backgroundColor = Color.black;
            layer.style.opacity = startBlack ? 1f : 0f;
            layer.pickingMode = PickingMode.Ignore;
            root.Add(layer);
        }

        public float Alpha => layer.style.opacity.value;

        /// <summary>Anima a opacidade ate <paramref name="target"/> em tempo real e chama <paramref name="done"/> no fim.</summary>
        public void FadeTo(float target, float seconds, Action done = null)
        {
            tick?.Pause();
            var from = layer.style.opacity.value;
            if (seconds <= 0f)
            {
                layer.style.opacity = target;
                layer.pickingMode = target > 0.5f ? PickingMode.Position : PickingMode.Ignore;
                done?.Invoke();
                return;
            }
            var elapsed = 0f;
            layer.pickingMode = PickingMode.Position; // bloqueia cliques durante a transicao
            var last = Time.realtimeSinceStartup;
            tick = layer.schedule.Execute(() =>
            {
                var now = Time.realtimeSinceStartup;
                elapsed += now - last;
                last = now;
                var t = Mathf.Clamp01(elapsed / seconds);
                layer.style.opacity = Mathf.Lerp(from, target, t);
                if (t < 1f) return;
                tick.Pause();
                layer.pickingMode = target > 0.5f ? PickingMode.Position : PickingMode.Ignore;
                done?.Invoke();
            }).Every(16);
        }
    }
}
