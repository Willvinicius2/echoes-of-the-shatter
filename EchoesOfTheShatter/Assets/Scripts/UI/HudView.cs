using System;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using UnityEngine;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// HUD de combate (RF-57; docs/03_design_system.md, seção 4.1) sobre <c>HudView.uxml</c>: barras e
    /// orbes de Vida e Ímpeto, barra de 6 habilidades com recarga e cadeado, esquiva com os pontos de
    /// carga, 2 poções, números de dano e a tela "Você caiu". Só lê estado e eventos; nunca calcula
    /// regra. Textos por chave de localização; cores e tamanhos nas variáveis USS dos tokens.
    /// </summary>
    [DisallowMultipleComponent]
    [RequireComponent(typeof(UIDocument))]
    public sealed class HudView : MonoBehaviour
    {
        const string LowClass = "shatter-orb--low";
        const string CoolingClass = "shatter-skill-slot--cooling";
        const string LockedClass = "shatter-skill-slot--locked";
        const string EmptyClass = "shatter-skill-slot--empty";
        const string NoResourceClass = "shatter-skill-slot--no-resource";
        const string HasIconClass = "shatter-skill-slot--has-icon";
        const string PotionEmptyClass = "shatter-potion-slot--empty";
        const string PipClass = "shatter-dodge-slot__pip";
        const string PipFullClass = "shatter-dodge-slot__pip--full";
        const string PipFillClass = "shatter-dodge-slot__pip-fill";
        const string HiddenClass = "hud--hidden";
        const string ToastVisibleClass = "hud__toast--visible";

        static readonly string[] DenyKeys =
        {
            "ui.hud.no_resource",       // DenyReason.NoResource
            "ui.hud.cooldown",          // DenyReason.Cooldown (chave ainda não existe no Loc: o aviso não aparece)
            "ui.hud.no_dodge_charges",  // DenyReason.NoDodgeCharges (idem)
            "ui.hud.potion_empty",      // DenyReason.PotionEmpty
            "ui.hud.locked",            // DenyReason.Locked (idem)
            "",                         // DenyReason.EmptySlot: sem aviso
        };

        [SerializeField] GameRoot root;
        [SerializeField] HeroController hero;
        [Tooltip("Câmera para projetar os números de dano. Vazio = Camera.main.")]
        [SerializeField] Camera worldCamera;
        [Tooltip("Ícones da barra (T_Icon_Skill_<id>_128). Sem ícone, o slot mostra o nome da habilidade.")]
        [SerializeField] SkillIconEntry[] skillIcons = Array.Empty<SkillIconEntry>();
        [Tooltip("Altura do número de dano acima dos pés, em metros.")]
        [SerializeField] float damageNumberHeight = 1.8f;
        [Tooltip("Vida abaixo desta fração ativa o pulso do orbe (docs/03, seção 5.4: 30%).")]
        [SerializeField, Range(0f, 1f)] float lowLifeFraction = 0.3f;
        [Tooltip("Segundos que um aviso fica na tela (motion.toast_visible_ms).")]
        [SerializeField, Min(0f)] float toastSeconds = 3f;
        [Tooltip("Opção \"Sempre mostrar valores\" (docs/03, seção 4.1).")]
        [SerializeField] bool alwaysShowValues = true;

        sealed class SkillSlotView
        {
            public VisualElement Root;
            public VisualElement Icon;
            public VisualElement Cooldown;
            public Label CooldownText;
            public Label Key;
            public Label Name;
            public string LastCooldownText = string.Empty;
            public float LastCooldownFraction = -1f;
        }

        sealed class PotionSlotView
        {
            public VisualElement Root;
            public Label Count;
            public Label Key;
            public VisualElement Recharge;
            public int LastCount = -1;
            public float LastRecharge = -1f;
        }

        UIDocument document;
        VisualElement hudRoot;
        VisualElement lifeFill;
        VisualElement resourceFill;
        Label lifeValue;
        VisualElement lifeOrb;
        VisualElement lifeOrbFill;
        Label lifeOrbValue;
        VisualElement resourceOrbFill;
        Label resourceOrbValue;
        VisualElement dodgePips;
        Label dodgeKey;
        VisualElement deathOverlay;
        VisualElement toast;
        Label toastLabel;
        DamageNumberLayer damageLayer;
        readonly SkillSlotView[] skillViews = new SkillSlotView[HeroCombatLogic.SlotCount];
        readonly PotionSlotView[] potionViews = new PotionSlotView[2];
        VisualElement[] pips = Array.Empty<VisualElement>();
        VisualElement[] pipFills = Array.Empty<VisualElement>();

        LocalizationService localization;
        EventBus events;
        HeroCombatLogic boundLogic;
        bool subscribed;
        float toastTimeLeft;
        float lastLifeFraction = -1f;
        float lastResourceFraction = -1f;
        string lastLifeText = string.Empty;
        string lastResourceText = string.Empty;
        int lastDodgeCharges = -1;
        float lastDodgeFill = -1f;

        void OnEnable()
        {
            document = GetComponent<UIDocument>();
            QueryElements();
        }

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (hero == null) hero = FindAnyObjectByType<HeroController>();
            if (worldCamera == null) worldCamera = Camera.main;
            if (root == null) return;
            localization = root.Localization;
            events = root.Events;
            if (localization != null) localization.CultureChanged += OnCultureChanged;
            if (events != null)
            {
                events.Subscribe<HitEvent>(OnHit);
                events.Subscribe<ActionDeniedEvent>(OnDenied);
                subscribed = true;
            }
            LocLabel.ApplyAll(hudRoot, localization);
        }

        void OnDestroy()
        {
            if (localization != null) localization.CultureChanged -= OnCultureChanged;
            if (!subscribed || events == null) return;
            events.Unsubscribe<HitEvent>(OnHit);
            events.Unsubscribe<ActionDeniedEvent>(OnDenied);
        }

        void Update()
        {
            var logic = hero != null ? hero.Logic : null;
            if (logic == null || hudRoot == null) return;
            if (!ReferenceEquals(boundLogic, logic)) Bind(logic);

            var self = logic.Self;
            UpdateVitals(self);
            UpdateSkills(logic, self);
            UpdateDodge(logic);
            UpdatePotions(logic);
            deathOverlay?.EnableInClassList(HiddenClass, !self.IsDead);

            var dt = Time.deltaTime;
            if (toastTimeLeft > 0f)
            {
                toastTimeLeft -= dt;
                if (toastTimeLeft <= 0f) toast?.RemoveFromClassList(ToastVisibleClass);
            }
            damageLayer?.Tick(dt, worldCamera);
        }

        void QueryElements()
        {
            var r = document != null ? document.rootVisualElement : null;
            if (r == null) return;
            hudRoot = r.Q<VisualElement>("hud-root") ?? r;
            lifeFill = r.Q<VisualElement>("life-fill");
            resourceFill = r.Q<VisualElement>("resource-fill");
            lifeValue = r.Q<Label>("life-value");
            lifeOrb = r.Q<VisualElement>("life-orb");
            lifeOrbFill = r.Q<VisualElement>("life-orb-fill");
            lifeOrbValue = r.Q<Label>("life-orb-value");
            resourceOrbFill = r.Q<VisualElement>("resource-orb-fill");
            resourceOrbValue = r.Q<Label>("resource-orb-value");
            dodgePips = r.Q<VisualElement>("dodge-pips");
            dodgeKey = r.Q<Label>("dodge-key");
            deathOverlay = r.Q<VisualElement>("death-overlay");
            toast = r.Q<VisualElement>("toast");
            toastLabel = r.Q<Label>("toast-label");
            damageLayer = r.Q<DamageNumberLayer>("damage-layer");

            for (var i = 0; i < skillViews.Length; i++)
            {
                var slot = r.Q<VisualElement>("skill-" + i);
                skillViews[i] = new SkillSlotView
                {
                    Root = slot,
                    Icon = slot?.Q<VisualElement>("icon"),
                    Cooldown = slot?.Q<VisualElement>("cooldown"),
                    CooldownText = slot?.Q<Label>("cooldown-text"),
                    Key = slot?.Q<Label>("key"),
                    Name = slot?.Q<Label>("name"),
                };
            }
            for (var i = 0; i < potionViews.Length; i++)
            {
                var slot = r.Q<VisualElement>("potion-" + i);
                potionViews[i] = new PotionSlotView
                {
                    Root = slot,
                    Count = slot?.Q<Label>("count"),
                    Key = slot?.Q<Label>("key"),
                    Recharge = slot?.Q<VisualElement>("recharge"),
                };
            }
            boundLogic = null;
        }

        /// <summary>Liga os slots ao herói: ícones, nomes, teclas e os pontos de carga da esquiva.</summary>
        void Bind(HeroCombatLogic logic)
        {
            boundLogic = logic;
            var input = hero.InputHandler;
            for (var i = 0; i < skillViews.Length; i++)
            {
                var view = skillViews[i];
                if (view.Root == null) continue;
                var slot = logic.GetSlot(i);
                var skill = slot != null ? slot.Skill : null;
                view.Root.EnableInClassList(EmptyClass, skill == null);
                view.Root.EnableInClassList(LockedClass, skill != null && !slot.Unlocked);
                var icon = skill != null ? FindIcon(skill.Id) : null;
                view.Root.EnableInClassList(HasIconClass, icon != null);
                if (view.Icon != null)
                    view.Icon.style.backgroundImage = icon != null ? new StyleBackground(icon) : new StyleBackground(StyleKeyword.None);
                if (view.Name != null) view.Name.text = skill != null && localization != null ? localization.Get(skill.NameKey) : string.Empty;
                if (view.Key != null && input != null) view.Key.text = input.GetBindingDisplay((HeroCommand)i);
            }
            for (var i = 0; i < potionViews.Length; i++)
            {
                var view = potionViews[i];
                if (view.Root == null) continue;
                var potion = logic.GetPotion(i);
                view.Root.EnableInClassList(HiddenClass, potion == null);
                if (view.Key != null && input != null)
                    view.Key.text = input.GetBindingDisplay(i == 0 ? HeroCommand.Potion1 : HeroCommand.Potion2);
            }
            if (dodgeKey != null && input != null) dodgeKey.text = input.GetBindingDisplay(HeroCommand.Dodge);
            BuildDodgePips(logic.Dodge.Charges.MaxCharges);
            lastDodgeCharges = -1;
        }

        void BuildDodgePips(int count)
        {
            if (dodgePips == null) return;
            dodgePips.Clear();
            pips = new VisualElement[count];
            pipFills = new VisualElement[count];
            for (var i = 0; i < count; i++)
            {
                var pip = new VisualElement();
                pip.AddToClassList(PipClass);
                var fill = new VisualElement();
                fill.AddToClassList(PipFillClass);
                pip.Add(fill);
                dodgePips.Add(pip);
                pips[i] = pip;
                pipFills[i] = fill;
            }
        }

        void UpdateVitals(Combatant self)
        {
            var maxLife = self.MaxLife;
            var lifeFraction = maxLife > 0.0 ? (float)(self.Life / maxLife) : 0f;
            if (!Mathf.Approximately(lifeFraction, lastLifeFraction))
            {
                lastLifeFraction = lifeFraction;
                SetWidth(lifeFill, lifeFraction);
                SetHeight(lifeOrbFill, lifeFraction);
                lifeOrb?.EnableInClassList(LowClass, lifeFraction > 0f && lifeFraction < lowLifeFraction);
            }

            var maxResource = self.MaxResource;
            var resourceFraction = maxResource > 0.0 ? (float)(self.Resource / maxResource) : 0f;
            if (!Mathf.Approximately(resourceFraction, lastResourceFraction))
            {
                lastResourceFraction = resourceFraction;
                SetWidth(resourceFill, resourceFraction);
                SetHeight(resourceOrbFill, resourceFraction);
            }

            if (!alwaysShowValues || localization == null) return;
            var lifeText = ValueOfMax(self.Life, maxLife);
            if (lifeText != lastLifeText)
            {
                lastLifeText = lifeText;
                if (lifeValue != null) lifeValue.text = lifeText;
                if (lifeOrbValue != null) lifeOrbValue.text = lifeText;
            }
            var resourceText = ValueOfMax(self.Resource, maxResource);
            if (resourceText != lastResourceText)
            {
                lastResourceText = resourceText;
                if (resourceOrbValue != null) resourceOrbValue.text = resourceText;
            }
        }

        void UpdateSkills(HeroCombatLogic logic, Combatant self)
        {
            for (var i = 0; i < skillViews.Length; i++)
            {
                var view = skillViews[i];
                var slot = logic.GetSlot(i);
                if (view.Root == null || slot == null || slot.IsEmpty || !slot.Unlocked) continue;

                var cooling = !slot.Cooldown.IsReady;
                view.Root.EnableInClassList(CoolingClass, cooling);
                view.Root.EnableInClassList(NoResourceClass, self.Resource + 1e-9 < slot.EffectiveCost);

                var fraction = cooling ? (float)slot.Cooldown.FractionRemaining : 0f;
                if (!Mathf.Approximately(fraction, view.LastCooldownFraction))
                {
                    view.LastCooldownFraction = fraction;
                    SetHeight(view.Cooldown, fraction);
                }

                var text = cooling && localization != null ? FormatCooldown(slot.Cooldown.Remaining) : string.Empty;
                if (text != view.LastCooldownText)
                {
                    view.LastCooldownText = text;
                    if (view.CooldownText != null) view.CooldownText.text = text;
                }
            }
        }

        void UpdateDodge(HeroCombatLogic logic)
        {
            var charges = logic.Dodge.Charges;
            var fill = (float)charges.RechargeFraction;
            if (charges.Charges == lastDodgeCharges && Mathf.Approximately(fill, lastDodgeFill)) return;
            lastDodgeCharges = charges.Charges;
            lastDodgeFill = fill;
            for (var i = 0; i < pips.Length; i++)
            {
                var full = i < charges.Charges;
                pips[i].EnableInClassList(PipFullClass, full);
                // A carga que está recarregando é a primeira vazia (recarga em série).
                SetWidth(pipFills[i], full ? 1f : i == charges.Charges ? fill : 0f);
            }
        }

        void UpdatePotions(HeroCombatLogic logic)
        {
            for (var i = 0; i < potionViews.Length; i++)
            {
                var view = potionViews[i];
                var potion = logic.GetPotion(i);
                if (view.Root == null || potion == null) continue;
                var count = potion.Charges.Charges;
                if (count != view.LastCount)
                {
                    view.LastCount = count;
                    if (view.Count != null && localization != null) view.Count.text = localization.FormatInteger(count);
                    view.Root.EnableInClassList(PotionEmptyClass, count == 0);
                }
                var recharge = (float)potion.Charges.RechargeFraction;
                if (!Mathf.Approximately(recharge, view.LastRecharge))
                {
                    view.LastRecharge = recharge;
                    SetHeight(view.Recharge, potion.Charges.IsFull ? 0f : 1f - recharge);
                }
            }
        }

        void OnHit(in HitEvent evt)
        {
            if (damageLayer == null || evt.Target == null || localization == null) return;
            var heroCombatant = hero != null ? hero.Combatant : null;
            var targetIsHero = ReferenceEquals(evt.Target, heroCombatant);
            var ownerComponent = evt.Target.Owner as Component;
            var world = ownerComponent != null
                ? ownerComponent.transform.position + Vector3.up * damageNumberHeight
                : evt.Position.ToWorld(damageNumberHeight);
            var result = evt.Result;

            if (!result.Landed)
            {
                if (localization.TryGet("ui.hud.evaded", out var evaded))
                    damageLayer.Show(null, world, 0.0, evaded, DamageNumberKind.Muted, DamageType.Physical);
                return;
            }
            if (result.Outcome == HitOutcome.Blocked && result.TotalDamage <= 0.0)
            {
                if (localization.TryGet("ui.hud.blocked", out var blocked))
                    damageLayer.Show(null, world, 0.0, blocked, DamageNumberKind.Muted, DamageType.Physical);
                return;
            }

            var kind = targetIsHero ? DamageNumberKind.Taken : result.Critical ? DamageNumberKind.Critical : DamageNumberKind.Normal;
            var amount = result.TotalDamage;
            var total = damageLayer.PendingAmount(evt.Target, kind) + amount;
            var text = localization.FormatInteger((long)Math.Round(total, MidpointRounding.AwayFromZero));
            damageLayer.Show(evt.Target, world, amount, text, kind, result.AfterMitigation.Dominant);
        }

        void OnDenied(in ActionDeniedEvent evt)
        {
            if (localization == null || toast == null || toastLabel == null) return;
            var index = (int)evt.Reason;
            if (index < 0 || index >= DenyKeys.Length || DenyKeys[index].Length == 0) return;
            if (!localization.TryGet(DenyKeys[index], out var text)) return;
            toastLabel.text = text;
            toast.AddToClassList(ToastVisibleClass);
            toastTimeLeft = toastSeconds;
        }

        void OnCultureChanged()
        {
            LocLabel.ApplyAll(hudRoot, localization);
            boundLogic = null; // reaplica nomes das habilidades no próximo quadro
            lastLifeText = string.Empty;
            lastResourceText = string.Empty;
            for (var i = 0; i < skillViews.Length; i++)
            {
                if (skillViews[i] != null) skillViews[i].LastCooldownText = null;
            }
            for (var i = 0; i < potionViews.Length; i++)
            {
                if (potionViews[i] != null) potionViews[i].LastCount = -1;
            }
        }

        string ValueOfMax(double value, double max)
        {
            // O separador "/" é notação numérica, não texto: "142/180" (docs/03, seção 4.1).
            return localization.FormatInteger((long)Math.Ceiling(value - 1e-9)) + "/" + localization.FormatInteger((long)Math.Round(max));
        }

        string FormatCooldown(double seconds)
        {
            // "3" acima de 1 s, "0,8" abaixo (docs/03, seção 5.5).
            return seconds >= 1.0
                ? localization.FormatInteger((long)Math.Ceiling(seconds))
                : localization.FormatDecimal(Math.Max(0.1, seconds), 1);
        }

        Texture2D FindIcon(string skillId)
        {
            for (var i = 0; i < skillIcons.Length; i++)
            {
                var entry = skillIcons[i];
                if (entry != null && entry.icon != null && string.Equals(entry.skillId, skillId, StringComparison.Ordinal)) return entry.icon;
            }
            return null;
        }

        static void SetWidth(VisualElement element, float fraction)
        {
            if (element == null) return;
            element.style.width = new StyleLength(new Length(Mathf.Clamp01(fraction) * 100f, LengthUnit.Percent));
        }

        static void SetHeight(VisualElement element, float fraction)
        {
            if (element == null) return;
            element.style.height = new StyleLength(new Length(Mathf.Clamp01(fraction) * 100f, LengthUnit.Percent));
        }
    }
}
