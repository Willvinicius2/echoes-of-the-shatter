using System;
using System.Collections.Generic;
using Echoes.Core;
using Echoes.Gameplay;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Opcoes (docs/16 S-11; RF-58, RF-62, RF-65), usada pelo menu inicial e pela pausa. Abas: Jogo (idioma sem reiniciar, resolucao e janela),
    /// Controles (remapeamento com conflito, Esc fixo e a acao Interagir) e Acessibilidade (tremor de tela e reducao de flashes). As escolhas
    /// valem na hora e persistem em settings.json (idioma, tremor) e bindings.json (teclas); por isso nao ha Aplicar/Cancelar.
    /// </summary>
    public sealed class OptionsView
    {
        public enum Tab { Game, Controls, Access }

        /// <summary>Acoes remapeaveis na ordem da tabela (docs/16 S-11). Move, Mira, Mapa, Arvore e Pausa ficam de fora.</summary>
        public static readonly string[] RemapActions =
        {
            InputActionNames.BasicAttack, InputActionNames.Skill1, InputActionNames.Skill2, InputActionNames.Skill3, InputActionNames.Skill4,
            InputActionNames.Skill5, InputActionNames.Dodge, InputActionNames.Potion1, InputActionNames.Potion2, InputActionNames.Inventory,
            InputActionNames.Interact,
        };

        static readonly string[] Cultures = { "pt_BR", "en" };
        const string KeyboardGroup = "Keyboard&Mouse";

        readonly LocalizationService loc;
        readonly InputActionAsset actions;
        readonly Action onClose;
        readonly bool showHeroPreview;
        VisualElement backdrop;
        VisualElement card;
        Label footer;
        VisualElement footerButtons;
        string footerKey;
        InputActionRebindingExtensions.RebindingOperation rebind;
        Tab tab;

        public bool IsOpen => card != null;
        public Tab CurrentTab => tab;

        public OptionsView(LocalizationService localization, InputActionAsset inputActions, Action close, bool heroPreview)
        {
            loc = localization;
            actions = inputActions;
            onClose = close;
            showHeroPreview = heroPreview;
        }

        // ------------------------------------------------------------------------------------------------ abrir e fechar

        public void Open(VisualElement host)
        {
            Close(false);
            PlayerInputHandler.LoadOverrides(actions); // mostra as teclas ja remapeadas mesmo fora da cena de jogo
            backdrop = MenuUi.Backdrop(host, 0.86f);
            backdrop.pickingMode = PickingMode.Position;
            loc.CultureChanged += OnCultureChanged;
            Build();
        }

        /// <summary>Vai direto a uma aba (capturas e testes).</summary>
        public void ShowTab(Tab value)
        {
            tab = value;
            footerKey = null;
            if (card != null) Build();
        }

        public void Close(bool notify = true)
        {
            rebind?.Cancel();
            rebind = null;
            if (backdrop == null) return;
            loc.CultureChanged -= OnCultureChanged;
            backdrop.RemoveFromHierarchy();
            backdrop = null;
            card = null;
            if (notify) onClose?.Invoke();
        }

        void OnCultureChanged()
        {
            if (card != null) Build();
        }

        // ------------------------------------------------------------------------------------------------ montagem

        void Build()
        {
            if (backdrop == null) return;
            backdrop.Clear();
            card = MenuUi.Card(backdrop);
            card.style.minWidth = 860;
            card.name = "options-card";
            MenuUi.Title(card, "ui.options.title", loc, 44);

            var tabs = ScreenKit.Row(card);
            tabs.style.justifyContent = Justify.Center;
            AddTab(tabs, "ui.options.tab_game", Tab.Game);
            AddTab(tabs, "ui.options.tab_controls", Tab.Controls);
            AddTab(tabs, "ui.options.tab_access", Tab.Access);

            var body = new VisualElement { name = "options-body" };
            body.style.marginTop = 16;
            card.Add(body);
            switch (tab)
            {
                case Tab.Game: BuildGame(body); break;
                case Tab.Controls: BuildControls(body); break;
                default: BuildAccess(body); break;
            }

            footer = ScreenKit.Line(card, footerKey != null ? loc.Get(footerKey) : string.Empty, 20, ScreenKit.Muted);
            footer.name = "options-footer";
            footer.style.unityTextAlign = TextAnchor.MiddleCenter;
            footerButtons = ScreenKit.Row(card);
            footerButtons.style.justifyContent = Justify.Center;

            var bottom = ScreenKit.Row(card);
            bottom.style.justifyContent = Justify.Center;
            bottom.style.marginTop = 10;
            ScreenKit.SmallButton(bottom, loc.Get("ui.common.restore_defaults"), RestoreDefaults).name = "options-restore";
            ScreenKit.SmallButton(bottom, loc.Get("ui.common.back"), () => Close()).name = "options-back";
        }

        void AddTab(VisualElement row, string key, Tab value)
        {
            var button = new Button(() => { tab = value; footerKey = null; Build(); }) { text = loc.Get(key), name = "tab-" + value.ToString().ToLowerInvariant() };
            button.AddToClassList("art-tab");
            button.style.fontSize = 22;
            button.style.height = 48;
            button.style.marginLeft = 4;
            button.style.marginRight = 4;
            if (tab == value) button.style.color = ScreenKit.Gold;
            row.Add(button);
        }

        // ------------------------------------------------------------------------------------------------ aba Jogo

        void BuildGame(VisualElement body)
        {
            var lang = ScreenKit.Row(body);
            ScreenKit.Line(lang, loc.Get("ui.options.language"), 24);
            var choices = new VisualElement();
            choices.style.flexDirection = FlexDirection.Row;
            lang.Add(choices);
            foreach (var culture in Cultures)
            {
                var value = culture;
                var button = ScreenKit.SmallButton(choices, loc.Get("ui.options.lang_" + culture), () => SetLanguage(value));
                button.name = "lang-" + culture;
                if (loc.Culture == culture) button.style.color = ScreenKit.Gold;
            }
            MenuUi.AddDisplayOptions(body, loc);
            if (showHeroPreview)
            {
                Button hero = null;
                hero = MenuUi.MakeButton(body, string.Empty, () => { HeroChoice.Cycle(); hero.text = HeroLabel(); });
                hero.style.fontSize = 22;
                hero.text = HeroLabel();
            }
        }

        string HeroLabel() => loc.Get("ui.menu.hero_preview") + ": " + loc.Get(HeroChoice.NameKey(HeroChoice.Id));

        /// <summary>Troca o idioma na hora (sem reiniciar) e grava a escolha; as telas se refazem pelo evento CultureChanged.</summary>
        public void SetLanguage(string culture)
        {
            UserSettings.Culture = culture;
            loc.SetCulture(culture);
        }

        // ------------------------------------------------------------------------------------------------ aba Acessibilidade

        void BuildAccess(VisualElement body)
        {
            var shake = ScreenKit.Row(body);
            ScreenKit.Line(shake, loc.Get("ui.options.screen_shake"), 24);
            var shakeButton = ScreenKit.SmallButton(shake, ShakeLabel(), null);
            shakeButton.name = "shake";
            shakeButton.clicked += () =>
            {
                CycleShake();
                shakeButton.text = ShakeLabel();
            };
            var flashes = ScreenKit.Row(body);
            ScreenKit.Line(flashes, loc.Get("ui.options.reduce_flashes"), 24);
            var flashButton = ScreenKit.SmallButton(flashes, OnOff(UserSettings.ReduceFlashes), null);
            flashButton.name = "flashes";
            flashButton.clicked += () =>
            {
                UserSettings.ReduceFlashes = !UserSettings.ReduceFlashes;
                flashButton.text = OnOff(UserSettings.ReduceFlashes);
            };
            ScreenKit.Line(body, loc.Get("ui.options.camera_shake.desc"), 18, ScreenKit.Muted);
        }

        string OnOff(bool value) => loc.Get(value ? "ui.options.on" : "ui.options.off");

        string ShakeLabel() => loc.Get("ui.options.shake." + UserSettings.Shake.ToString().ToLowerInvariant());

        /// <summary>Normal, Reduzido, Desligado e de volta (RF-62; valem para o proximo tremor).</summary>
        public static void CycleShake()
        {
            UserSettings.Shake = (ShakeMode)(((int)UserSettings.Shake + 1) % 3);
        }

        // ------------------------------------------------------------------------------------------------ aba Controles

        /// <summary>Indices dos bindings de teclado e mouse (sem o cabecalho de composto) da acao: o 1o e o Principal, o 2o a Alternativa.</summary>
        public static List<int> BindingIndices(InputAction action)
        {
            var list = new List<int>();
            for (var i = 0; i < action.bindings.Count; i++)
            {
                var b = action.bindings[i];
                if (b.isComposite || b.isPartOfComposite) continue;
                list.Add(i);
            }
            return list;
        }

        /// <summary>Outra acao do mapa que ja usa a tecla recem-atribuida (conflito: a tela pergunta "Trocar as duas?").</summary>
        public static bool TryFindConflict(InputActionMap map, InputAction action, int bindingIndex, out InputAction other, out int otherIndex)
        {
            other = null;
            otherIndex = -1;
            if (map == null) return false;
            var path = action.bindings[bindingIndex].effectivePath;
            if (string.IsNullOrEmpty(path)) return false;
            foreach (var candidate in map.actions)
            {
                if (candidate == action) continue;
                for (var i = 0; i < candidate.bindings.Count; i++)
                {
                    var b = candidate.bindings[i];
                    if (b.isComposite || b.isPartOfComposite) continue;
                    if (!string.Equals(b.effectivePath, path, StringComparison.OrdinalIgnoreCase)) continue;
                    if (candidate.name == InputActionNames.Pause || candidate.name == InputActionNames.Aim) continue; // fixas: nunca trocam
                    other = candidate;
                    otherIndex = i;
                    return true;
                }
            }
            return false;
        }

        void BuildControls(VisualElement body)
        {
            var map = actions != null ? actions.FindActionMap(InputActionNames.Map, false) : null;
            if (map == null)
            {
                ScreenKit.Line(body, loc.Get("ui.options.unbound"), 22, ScreenKit.Muted);
                return;
            }
            var header = ScreenKit.Row(body);
            ScreenKit.Line(header, loc.Get("ui.options.col_action"), 20, ScreenKit.Gold, true).style.width = 300;
            ScreenKit.Line(header, loc.Get("ui.options.col_primary"), 20, ScreenKit.Gold, true).style.width = 200;
            ScreenKit.Line(header, loc.Get("ui.options.col_alt"), 20, ScreenKit.Gold, true).style.width = 200;
            var scroll = new ScrollView(ScrollViewMode.Vertical);
            scroll.style.height = 420;
            body.Add(scroll);
            foreach (var name in RemapActions)
            {
                var action = map.FindAction(name, false);
                if (action == null) continue;
                var row = ScreenKit.Row(scroll.contentContainer);
                row.name = "row-" + name;
                ScreenKit.Line(row, ActionLabel(name), 22).style.width = 300;
                var indices = BindingIndices(action);
                var primary = indices.Count > 0 ? indices[0] : -1;
                var alt = indices.Count > 1 ? indices[1] : -1;
                AddBindingCell(row, action, primary, "primary");
                AddBindingCell(row, action, alt, "alt");
            }
        }

        /// <summary>Nome da acao na tabela (chaves ui.action.*; Habilidade e Pocao levam o numero).</summary>
        string ActionLabel(string name)
        {
            if (name == InputActionNames.BasicAttack) return loc.Get("ui.action.attack");
            if (name == InputActionNames.Dodge) return loc.Get("ui.action.dodge");
            if (name == InputActionNames.Inventory) return loc.Get("ui.action.inventory");
            if (name == InputActionNames.Interact) return loc.Get("ui.action.interact");
            if (name.StartsWith("Skill", StringComparison.Ordinal)) return ScreenKit.Fmt(loc, "ui.action.skill", ("n", name.Substring(5)));
            if (name.StartsWith("Potion", StringComparison.Ordinal)) return ScreenKit.Fmt(loc, "ui.action.potion", ("n", name.Substring(6)));
            return name;
        }

        void AddBindingCell(VisualElement row, InputAction action, int index, string slot)
        {
            var text = index >= 0 && !string.IsNullOrEmpty(action.bindings[index].effectivePath) ? action.GetBindingDisplayString(index) : "-";
            var button = ScreenKit.SmallButton(row, text, () => StartRebind(action, index));
            button.name = slot + "-" + action.name;
            button.style.width = 200;
            button.style.marginLeft = 0;
        }

        void SetFooter(string key)
        {
            footerKey = key;
            if (footer != null) footer.text = key != null ? loc.Get(key) : string.Empty;
        }

        /// <summary>Espera a proxima tecla para a acao (Esc cancela e nao e remapeavel). Um 2o binding vazio e criado sob demanda.</summary>
        void StartRebind(InputAction action, int index)
        {
            if (rebind != null || action == null) return;
            if (index < 0)
            {
                action.AddBinding(string.Empty);
                index = action.bindings.Count - 1;
            }
            var map = action.actionMap;
            var wasEnabled = map != null && map.enabled;
            map?.Disable(); // exigencia do Input System: a acao nao pode estar ativa durante o remapeamento
            var previousOverride = action.bindings[index].overridePath;
            var previousPath = action.bindings[index].effectivePath;
            SetFooter("ui.options.press_key");
            rebind = action.PerformInteractiveRebinding(index)
                .WithControlsExcluding("<Mouse>/position")
                .WithControlsExcluding("<Mouse>/delta")
                .WithControlsExcluding("<Mouse>/scroll")
                .WithControlsExcluding("<Pointer>/position")
                .WithCancelingThrough("<Keyboard>/escape")
                .OnComplete(op =>
                {
                    op.Dispose();
                    rebind = null;
                    if (wasEnabled) map.Enable();
                    AfterRebind(action, index, previousOverride, previousPath);
                })
                .OnCancel(op =>
                {
                    op.Dispose();
                    rebind = null;
                    if (wasEnabled) map.Enable();
                    SetFooter("ui.options.esc_fixed");
                    Build();
                })
                .Start();
        }

        void AfterRebind(InputAction action, int index, string previousOverride, string previousPath)
        {
            if (TryFindConflict(action.actionMap, action, index, out var other, out var otherIndex))
            {
                // "Trocar as duas?": Sim entrega a tecla antiga a outra acao; Nao desfaz.
                SetFooter("ui.options.conflict");
                Build();
                ScreenKit.SmallButton(footerButtons, loc.Get("ui.common.yes"), () =>
                {
                    other.ApplyBindingOverride(otherIndex, previousPath ?? string.Empty);
                    Commit();
                }).name = "conflict-yes";
                ScreenKit.SmallButton(footerButtons, loc.Get("ui.common.no"), () =>
                {
                    if (string.IsNullOrEmpty(previousOverride)) action.RemoveBindingOverride(index);
                    else action.ApplyBindingOverride(index, previousOverride);
                    Commit();
                }).name = "conflict-no";
                return;
            }
            Commit();
        }

        void Commit()
        {
            PlayerInputHandler.SaveOverrides(actions);
            SetFooter(null);
            Build();
        }

        // ------------------------------------------------------------------------------------------------ restaurar

        void RestoreDefaults()
        {
            switch (tab)
            {
                case Tab.Controls:
                    actions?.RemoveAllBindingOverrides();
                    PlayerInputHandler.SaveOverrides(actions);
                    break;
                case Tab.Access:
                    UserSettings.Shake = ShakeMode.Normal;
                    UserSettings.ReduceFlashes = false;
                    break;
                default:
                    GameSettings.Apply(GameSettings.DefaultWidth, GameSettings.DefaultHeight, false);
                    break;
            }
            SetFooter(null);
            Build();
        }
    }
}
