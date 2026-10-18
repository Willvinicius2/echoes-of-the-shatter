using System.Collections.Generic;
using Echoes.Core;
using Echoes.Gameplay;
using UnityEngine;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Aviso "[F] Abrir baú" do objeto mais próximo que o herói pode acionar (baú, alavanca do atalho) e a própria ação Interagir (RF-64, remapeável).
    /// A tecla mostrada vem do Input System (acompanha o remapeamento); o texto, do Loc. Chama <see cref="IInteractable.Interact"/> ao apertar.
    /// </summary>
    [RequireComponent(typeof(ScreenHost))]
    public sealed class InteractPromptView : MonoBehaviour
    {
        [SerializeField] GameRoot root;
        [SerializeField] HeroController hero;
        [Tooltip("Segundos entre buscas de objetos novos na cena (técnico).")]
        [SerializeField, Min(0.1f)] float rescanSeconds = 1f;

        readonly List<IInteractable> objects = new List<IInteractable>();
        PlayerInputHandler input;
        VisualElement prompt;
        Label label;
        float rescanLeft;

        /// <summary>Objeto que o aviso mostra agora (testes).</summary>
        public IInteractable Current { get; private set; }

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (hero == null) hero = FindAnyObjectByType<HeroController>();
            input = FindAnyObjectByType<PlayerInputHandler>();
            var host = GetComponent<ScreenHost>();
            prompt = new VisualElement { name = "interact-prompt" };
            prompt.style.position = Position.Absolute;
            prompt.style.bottom = 200;
            prompt.style.left = new Length(35, LengthUnit.Percent);
            prompt.style.right = new Length(35, LengthUnit.Percent);
            prompt.style.backgroundColor = new Color(0.07f, 0.06f, 0.09f, 0.9f);
            prompt.style.display = DisplayStyle.None;
            prompt.pickingMode = PickingMode.Ignore;
            label = ScreenKit.Line(prompt, string.Empty, 24, ScreenKit.Gold, true);
            label.style.unityTextAlign = TextAnchor.MiddleCenter;
            host.Root.Add(prompt);
            Rescan();
        }

        void Rescan()
        {
            objects.Clear();
            foreach (var behaviour in FindObjectsByType<MonoBehaviour>(FindObjectsSortMode.None))
            {
                if (behaviour is IInteractable interactable) objects.Add(interactable);
            }
            rescanLeft = rescanSeconds;
        }

        void Update()
        {
            if (hero == null || hero.Combatant == null || root == null) return;
            rescanLeft -= Time.unscaledDeltaTime;
            if (rescanLeft <= 0f) Rescan();
            Current = Nearest();
            var blocked = RefugeController.AnyScreenOpen || InventoryController.IsOpen || Time.timeScale == 0f;
            if (Current == null || blocked)
            {
                prompt.style.display = DisplayStyle.None;
                return;
            }
            var glyph = input != null && input.IsReady ? input.InteractGlyph : "F";
            label.text = ScreenKit.Fmt(root.Localization, "ui.interact.prompt", ("key", glyph), ("action", root.Localization.Get(Current.PromptKey)));
            prompt.style.display = DisplayStyle.Flex;
            if (input != null && input.IsReady && input.InteractPressed) Current.Interact();
        }

        IInteractable Nearest()
        {
            IInteractable best = null;
            var bestDistance = float.MaxValue;
            foreach (var candidate in objects)
            {
                if (candidate == null || !(candidate as Object) || !candidate.CanInteract) continue;
                var d = hero.transform.position - candidate.Position;
                d.y = 0f;
                var distance = d.magnitude;
                if (distance <= candidate.Reach && distance < bestDistance)
                {
                    best = candidate;
                    bestDistance = distance;
                }
            }
            return best;
        }
    }
}
