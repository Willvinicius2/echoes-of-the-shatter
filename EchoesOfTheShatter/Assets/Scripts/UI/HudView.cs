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

        const string GuardNameKey = "ui.hud.guard";

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
        [Tooltip("Segundos entre leituras do save para Ouro, Cargas, nível e XP (técnico).")]
        [SerializeField, Min(0.1f)] float readoutSeconds = 1f;
        [Tooltip("Segundos do brilho do checkpoint (F-07).")]
        [SerializeField, Min(0.1f)] float flashSeconds = 0.5f;

        /// <summary>
        /// Fração da barra de XP do nível atual. Quem calcula é o core (curva de XP); enquanto o Backend não expõe a API a barra fica oculta e
        /// só aparecem nível e XP total. Ligue aqui a função (nível, XP) → [0,1] quando existir.
        /// </summary>
        public static System.Func<int, double, float> XpFraction;

        sealed class SkillSlotView
        {
            public VisualElement Root;
            public VisualElement Icon;
            public VisualElement Cooldown;
            public Label CooldownText;
            public Label Key;
            public Label Name;
            public int LastCooldownKey = int.MinValue;
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
        Label deathDetail;
        VisualElement goldIcon, chargesIcon, fervorBox, levelBox, xpBar, xpFill, checkpointFlash;
        Label goldValue, chargesValue, levelValue, xpValue;
        ArenaController arena;
        float readoutTimeLeft;
        bool wasDead;
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
        long lastLifeShown = long.MinValue;
        long lastMaxLifeShown = long.MinValue;
        long lastResourceShown = long.MinValue;
        long lastMaxResourceShown = long.MinValue;
        int lastDodgeCharges = -1;
        float lastDodgeFill = -1f;

        void OnEnable()
        {
            document = GetComponent<UIDocument>();
            QueryElements();
        }

        void Start()
        {
            if (hudRoot == null) QueryElements(); // o UIDocument pode montar a árvore depois do nosso OnEnable
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (hero == null) hero = FindAnyObjectByType<HeroController>();
            if (arena == null) arena = FindAnyObjectByType<ArenaController>();
            if (worldCamera == null) worldCamera = Camera.main;
            if (root == null) return;
            localization = root.Localization;
            events = root.Events;
            if (localization != null) localization.CultureChanged += OnCultureChanged;
            if (events != null)
            {
                events.Subscribe<HitEvent>(OnHit);
                events.Subscribe<ActionDeniedEvent>(OnDenied);
                events.Subscribe<CheckpointReachedEvent>(OnCheckpoint);
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
            events.Unsubscribe<CheckpointReachedEvent>(OnCheckpoint);
        }

        void Update()
        {
            if (hudRoot == null)
            {
                QueryElements();
                if (hudRoot == null) return;
                LocLabel.ApplyAll(hudRoot, localization);
            }
            var logic = hero != null ? hero.Logic : null;
            if (logic == null) return;
            if (!ReferenceEquals(boundLogic, logic)) Bind(logic);

            var self = logic.Self;
            UpdateVitals(self);
            UpdateSkills(logic, self);
            UpdateDodge(logic);
            UpdatePotions(logic);
            deathOverlay?.EnableInClassList(HiddenClass, !self.IsDead);
            if (self.IsDead && !wasDead) ShowDeathDetail();
            wasDead = self.IsDead;
            UpdateReadout(Time.unscaledDeltaTime);

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
            hudRoot = r.Q<VisualElement>("hud-root"); // null enquanto o UIDocument não montou a árvore
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
            deathDetail = r.Q<Label>("death-detail");
            goldIcon = r.Q<VisualElement>("gold-icon");
            chargesIcon = r.Q<VisualElement>("charges-icon");
            goldValue = r.Q<Label>("gold-value");
            chargesValue = r.Q<Label>("charges-value");
            levelBox = r.Q<VisualElement>("level-box");
            levelValue = r.Q<Label>("level-value");
            xpBar = r.Q<VisualElement>("xp-bar");
            xpFill = r.Q<VisualElement>("xp-fill");
            xpValue = r.Q<Label>("xp-value");
            fervorBox = r.Q<VisualElement>("fervor");
            checkpointFlash = r.Q<VisualElement>("checkpoint-flash");
            var goldTexture = UiArt.Icon("icon_gold");
            if (goldIcon != null && goldTexture != null) goldIcon.style.backgroundImage = new StyleBackground(goldTexture);
            if (chargesIcon != null) chargesIcon.style.backgroundColor = new Color(0.43f, 0.66f, 1f, 1f); // TODO(asset ui.icon.marker_charge): icone das Cargas do Marco ainda nao existe
            readoutTimeLeft = 0f;
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
                var flask = slot?.Q<VisualElement>("flask");
                var flaskTexture = UiArt.Icon(i == 0 ? "icon_potion_life" : "icon_potion_ward");
                if (flask != null && flaskTexture != null)
                {
                    flask.style.backgroundImage = new StyleBackground(flaskTexture);
                    flask.style.unityBackgroundScaleMode = ScaleMode.ScaleToFit;
                }
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
                // Com kit (docs/18) o botão direito (espaço 1) é a defesa: aparece como slot sem habilidade, com o nome da Loc.
                var isGuardSlot = i == (int)HeroCombatLogic.GuardButton && logic.HasKit;
                view.Root.EnableInClassList(EmptyClass, skill == null && !isGuardSlot);
                view.Root.EnableInClassList(LockedClass, skill != null && !slot.Unlocked);
                var icon = skill != null ? FindIcon(skill.Id) : null;
                view.Root.EnableInClassList(HasIconClass, icon != null);
                if (view.Icon != null)
                    view.Icon.style.backgroundImage = icon != null ? new StyleBackground(icon) : new StyleBackground(StyleKeyword.None);
                if (view.Name != null)
                {
                    if (isGuardSlot) view.Name.text = localization != null ? localization.Get(GuardNameKey) : string.Empty;
                    else view.Name.text = skill != null && localization != null ? localization.Get(skill.NameKey) : string.Empty;
                }
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
            BuildDodgePips(logic.Dodge.MaxCharges);
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
            // Só monta texto quando o número mostrado muda (sem alocação por quadro).
            var life = Shown(self.Life);
            var lifeMax = (long)Math.Round(maxLife);
            if (life != lastLifeShown || lifeMax != lastMaxLifeShown)
            {
                lastLifeShown = life;
                lastMaxLifeShown = lifeMax;
                var lifeText = ValueOfMax(life, lifeMax);
                if (lifeValue != null) lifeValue.text = lifeText;
                if (lifeOrbValue != null) lifeOrbValue.text = lifeText;
            }
            var resource = Shown(self.Resource);
            var resourceMax = (long)Math.Round(maxResource);
            if (resource != lastResourceShown || resourceMax != lastMaxResourceShown)
            {
                lastResourceShown = resource;
                lastMaxResourceShown = resourceMax;
                if (resourceOrbValue != null) resourceOrbValue.text = ValueOfMax(resource, resourceMax);
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

                var key = cooling ? CooldownKey(slot.Cooldown.Remaining) : int.MinValue + 1;
                if (key != view.LastCooldownKey)
                {
                    view.LastCooldownKey = key;
                    if (view.CooldownText != null)
                        view.CooldownText.text = cooling && localization != null ? FormatCooldown(slot.Cooldown.Remaining) : string.Empty;
                }
            }
        }

        void UpdateDodge(HeroCombatLogic logic)
        {
            var dodge = logic.Dodge; // cargas e recarga vêm do core (IDodgeCharges)
            var count = dodge.Charges;
            var fill = (float)dodge.RechargeFraction;
            if (count == lastDodgeCharges && Mathf.Approximately(fill, lastDodgeFill)) return;
            lastDodgeCharges = count;
            lastDodgeFill = fill;
            for (var i = 0; i < pips.Length; i++)
            {
                var full = i < count;
                pips[i].EnableInClassList(PipFullClass, full);
                // A carga que está recarregando é a primeira vazia (recarga em série).
                SetWidth(pipFills[i], full ? 1f : i == count ? fill : 0f);
            }
        }

        void UpdatePotions(HeroCombatLogic logic)
        {
            for (var i = 0; i < potionViews.Length; i++)
            {
                var view = potionViews[i];
                var potion = logic.GetPotion(i);
                if (view.Root == null || potion == null) continue;
                var count = potion.Charges;
                if (count != view.LastCount)
                {
                    view.LastCount = count;
                    if (view.Count != null && localization != null) view.Count.text = localization.FormatInteger(count);
                    view.Root.EnableInClassList(PotionEmptyClass, count == 0);
                }
                var recharge = (float)potion.RechargeFraction;
                if (!Mathf.Approximately(recharge, view.LastRecharge))
                {
                    view.LastRecharge = recharge;
                    SetHeight(view.Recharge, potion.IsFull ? 0f : 1f - recharge);
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

        /// <summary>Ouro, Cargas, nível e XP lidos do save (a cada <see cref="readoutSeconds"/>) e o ícone do Fervor quando ativo.</summary>
        void UpdateReadout(float dt)
        {
            fervorBox?.EnableInClassList(HiddenClass, !RunState.FervorActive);
            readoutTimeLeft -= dt;
            if (readoutTimeLeft > 0f || localization == null) return;
            readoutTimeLeft = readoutSeconds;
            var snap = SaveReadout.Read();
            if (!snap.Valid) return;
            if (goldValue != null) goldValue.text = localization.FormatInteger(snap.Gold);
            if (chargesValue != null) chargesValue.text = snap.Charges + "/12";
            if (levelValue != null) levelValue.text = ScreenKit.Fmt(localization, "ui.common.level", ("level", snap.Level.ToString()));
            if (xpValue != null) xpValue.text = ScreenKit.Fmt(localization, "ui.hud.xp_total", ("xp", localization.FormatInteger((long)System.Math.Floor(snap.Xp))));
            var fraction = XpFraction != null ? XpFraction(snap.Level, snap.Xp) : -1f;
            if (xpBar != null) xpBar.style.display = fraction >= 0f ? DisplayStyle.Flex : DisplayStyle.None;
            if (fraction >= 0f) SetWidth(xpFill, fraction);
        }

        /// <summary>"Você caiu": a linha de baixo diz o que acontece (a luta recomeça na arena; senão, volta ao checkpoint). Nada foi perdido vem do UXML.</summary>
        void ShowDeathDetail()
        {
            if (deathDetail == null || localization == null) return;
            var inArena = arena != null && arena.Phase == ArenaPhase.Fighting;
            deathDetail.text = localization.Get(inArena ? "ui.death.boss_restart" : "ui.death.checkpoint");
        }

        void OnCheckpoint(in CheckpointReachedEvent evt)
        {
            if (checkpointFlash == null) return;
            if (!UserSettings.ReduceFlashes) // opcao de acessibilidade: sem o clarao, fica so o aviso
            {
                checkpointFlash.AddToClassList("hud__flash--on");
                checkpointFlash.schedule.Execute(() => checkpointFlash.RemoveFromClassList("hud__flash--on")).StartingIn((long)(flashSeconds * 1000f));
            }
            if (localization != null) ShowToast(localization.Get("ui.hud.checkpoint"));
        }

        void ShowToast(string text)
        {
            if (toast == null || toastLabel == null) return;
            toastLabel.text = text;
            toast.AddToClassList(ToastVisibleClass);
            toastTimeLeft = toastSeconds;
        }

        void OnCultureChanged()
        {
            LocLabel.ApplyAll(hudRoot, localization);
            boundLogic = null; // reaplica nomes das habilidades no próximo quadro
            lastLifeShown = long.MinValue;
            lastResourceShown = long.MinValue;
            readoutTimeLeft = 0f;
            if (wasDead) ShowDeathDetail();
            for (var i = 0; i < skillViews.Length; i++)
            {
                if (skillViews[i] != null) skillViews[i].LastCooldownKey = int.MinValue;
            }
            for (var i = 0; i < potionViews.Length; i++)
            {
                if (potionViews[i] != null) potionViews[i].LastCount = -1;
            }
        }

        static long Shown(double value) => (long)Math.Ceiling(value - 1e-9);

        string ValueOfMax(long value, long max)
        {
            // O separador "/" é notação numérica, não texto: "142/180" (docs/03, seção 4.1).
            return localization.FormatInteger(value) + "/" + localization.FormatInteger(max);
        }

        /// <summary>Muda só quando o texto da recarga muda: segundos inteiros acima de 1 s, décimos abaixo.</summary>
        static int CooldownKey(double seconds)
        {
            return seconds >= 1.0 ? (int)Math.Ceiling(seconds) * 100 : (int)Math.Ceiling(Math.Max(0.1, seconds) * 10.0);
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
