using System.Collections.Generic;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using Echoes.Interop.Native;
using Echoes.Presentation;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.SceneManagement;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Inventario e equipamento (docs/16 S-05, funcional e simples; a arte final espera o dono aprovar os mockups). Tecla I (acao Inventory) e botao no
    /// Refugio. Mostra o boneco modular (PaperDoll) com as posicoes de equipamento (as bloqueadas, com cadeado, vem do core), a Mochila (e o Bau no
    /// Refugio), o tooltip com nome por concordancia, afixos e a comparacao com o equipado (setas do core), o valor de venda, e as acoes equipar,
    /// desequipar, ordenar, mover e descartar (com confirmacao). Toda regra e do core; aqui so UI. Na Cripta o jogo pausa enquanto aberto (H3-04).
    /// </summary>
    [RequireComponent(typeof(ScreenHost))]
    public sealed class InventoryController : MonoBehaviour
    {
        const int Columns = 8;
        const int Cell = 58;

        [SerializeField] GameRoot root;
        [SerializeField] HeroController hero;
        [SerializeField] GameObject dollPrefab;

        ScreenHost host;
        PlayerInputHandler input;
        VisualElement screen, detail, backpackGrid, stashGrid, slotsColumn, dollImage, modal, openButton, statsPanel, undoColumn;
        readonly Dictionary<ulong, ItemContainer> pendingDiscards = new Dictionary<ulong, ItemContainer>();
        readonly Dictionary<ulong, VisualElement> undoBars = new Dictionary<ulong, VisualElement>();

        /// <summary>Segundos para desfazer um descarte de item Comum (docs/16 S-07).</summary>
        public const float UndoSeconds = 5f;
        Label backpackTitle, stashTitle;
        PaperDoll doll;
        int previousScale = 1;
        bool open;
        ItemInstanceInfo selected;
        string selectedFrom; // "backpack", "stash", "slot:<n>"
        List<ItemInstanceInfo> backpack = new List<ItemInstanceInfo>();
        List<ItemInstanceInfo> stash = new List<ItemInstanceInfo>();
        ItemInstanceInfo[] equipment = new ItemInstanceInfo[ItemSlots.Names.Length];

        public static bool IsOpen { get; private set; }

        public ItemInstanceInfo Selected => selected;
        public PaperDoll Doll => doll;
        public IReadOnlyList<ItemInstanceInfo> BackpackItems => backpack;
        LocalizationService Loc => root != null ? root.Localization : null;
        NativeRulesCore Rules => GameSession.NativeRules(root);
        bool InRefuge => SceneManager.GetActiveScene().name == GameFlow.RefugeScene;

        void Start()
        {
            host = GetComponent<ScreenHost>();
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (hero == null) hero = FindAnyObjectByType<HeroController>();
            input = FindAnyObjectByType<PlayerInputHandler>();
            if (InRefuge) BuildOpenButton();
        }

        void OnDestroy()
        {
            if (open) Close();
            IsOpen = false;
        }

        // ------------------------------------------------------------------------------------------------ entrada

        void Update()
        {
            var keyboard = Keyboard.current;
            var pressed = input != null && input.IsReady ? input.InventoryPressed : keyboard != null && keyboard[Key.I].wasPressedThisFrame;
            if (pressed && (open || !RefugeController.AnyScreenOpen)) Toggle();
            if (open && keyboard != null && keyboard[Key.Escape].wasPressedThisFrame)
            {
                if (modal != null) CloseModal();
                else Close();
            }
        }

        public void Toggle()
        {
            if (open) Close();
            else Show();
        }

        void BuildOpenButton()
        {
            openButton = new VisualElement { name = "inventory-button" };
            openButton.style.position = Position.Absolute;
            openButton.style.top = 14;
            openButton.style.right = 14;
            var glyph = input != null && input.IsReady ? input.InventoryGlyph : "I";
            var button = MenuUi.MakeButton(openButton, Loc.Get("ui.inventory.open_hint").Replace("{key}", glyph), Toggle);
            button.style.fontSize = 20;
            button.style.height = 42;
            button.style.paddingLeft = 14;
            button.style.paddingRight = 14;
            host.Root.Add(openButton);
        }

        // ------------------------------------------------------------------------------------------------ abrir e fechar

        public void Show()
        {
            if (open || Rules == null || !GameSession.Save.HasSave) return;
            open = true;
            IsOpen = true;
            Time.timeScale = 0f;
            if (openButton != null) openButton.style.display = DisplayStyle.None;
            var prefab = dollPrefab;
            var swap = hero != null ? hero.GetComponentInChildren<HeroVisualSwap>() ?? hero.GetComponent<HeroVisualSwap>() : null;
            if (swap != null && swap.CurrentPrefab != null) prefab = swap.CurrentPrefab;
            if (prefab != null) doll = PaperDoll.Create(prefab);
            BuildScreen();
            Refresh();
        }

        public void Close()
        {
            if (!open) return;
            FlushPendingDiscards(); // o que ainda esta na janela de desfazer vale ao fechar
            open = false;
            IsOpen = false;
            CloseModal();
            if (screen != null) screen.RemoveFromHierarchy();
            screen = null;
            if (doll != null) Destroy(doll.gameObject);
            doll = null;
            selected = null;
            if (!RefugeController.AnyScreenOpen) Time.timeScale = 1f;
            if (openButton != null) openButton.style.display = DisplayStyle.Flex;
        }

        // ------------------------------------------------------------------------------------------------ montagem da tela

        void BuildScreen()
        {
            screen = MenuUi.Backdrop(host.Root, 0.78f);
            screen.pickingMode = PickingMode.Position;
            var frame = new VisualElement { name = "inventory" };
            frame.style.flexDirection = FlexDirection.Column;
            frame.AddToClassList("art-frame-ornate");
            frame.style.paddingLeft = 52;
            frame.style.paddingRight = 52;
            frame.style.paddingTop = 40;
            frame.style.paddingBottom = 40;
            screen.Add(frame);

            var header = ScreenKit.Row(frame);
            var title = MenuUi.Title(header, "ui.inventory.title", Loc, 34);
            title.style.marginBottom = 8;
            var close = ScreenKit.SmallButton(header, Loc.Get("ui.common.close"), Close);
            close.name = "inventory-close";
            close.style.width = 120;

            var body = new VisualElement();
            body.style.flexDirection = FlexDirection.Row;
            frame.Add(body);

            // coluna 1: boneco e posicoes
            var left = new VisualElement();
            left.style.width = PaperDoll.Width + 150;
            left.style.flexDirection = FlexDirection.Row;
            body.Add(left);
            slotsColumn = new VisualElement { name = "slots-left" };
            slotsColumn.style.width = 74;
            slotsColumn.style.alignItems = Align.Center;
            left.Add(slotsColumn);
            var center = new VisualElement();
            center.style.alignItems = Align.Center;
            left.Add(center);
            dollImage = new VisualElement { name = "paper-doll" };
            dollImage.style.width = PaperDoll.Width * 0.72f;
            dollImage.style.height = PaperDoll.Height * 0.72f;
            Border(dollImage, 1, new Color(0.4f, 0.34f, 0.22f));
            if (doll != null) dollImage.style.backgroundImage = new StyleBackground(Background.FromRenderTexture(doll.Texture));
            dollImage.RegisterCallback<PointerMoveEvent>(e => { if (e.pressedButtons != 0 && doll != null) doll.Rotate(-e.deltaPosition.x * 0.6f); });
            center.Add(dollImage);
            var hint = ScreenKit.Line(center, Loc.Get("ui.inventory.drag_hint"), 15, ScreenKit.Muted);
            hint.style.unityTextAlign = TextAnchor.MiddleCenter;
            statsPanel = new VisualElement { name = "stats-panel" };
            statsPanel.style.width = PaperDoll.Width * 0.72f;
            statsPanel.style.marginTop = 8;
            center.Add(statsPanel);
            undoColumn = new VisualElement { name = "undo-column" };
            undoColumn.style.position = Position.Absolute;
            undoColumn.style.left = 52;
            undoColumn.style.bottom = 14;
            frame.Add(undoColumn);

            // coluna 2: grades
            var middle = new VisualElement();
            middle.style.marginLeft = 16;
            middle.style.width = Columns * (Cell + 4) + 24;
            body.Add(middle);
            backpackTitle = ScreenKit.Line(middle, string.Empty, 22, ScreenKit.Gold, true);
            backpackGrid = Grid(middle, 5 * (Cell + 4));
            var sort = ScreenKit.SmallButton(middle, Loc.Get("ui.inventory.sort"), () => { InventoryOps.Sort(root); Refresh(); });
            sort.name = "inventory-sort";
            sort.style.width = 160;
            stashTitle = ScreenKit.Line(middle, string.Empty, 22, ScreenKit.Gold, true);
            stashGrid = Grid(middle, 3 * (Cell + 4));
            stashGrid.name = "stash-grid";

            // coluna 3: detalhes
            detail = new VisualElement { name = "item-detail" };
            detail.style.marginLeft = 16;
            detail.style.width = 430;
            detail.style.height = 790;
            detail.AddToClassList("art-frame-plain");
            detail.style.paddingLeft = 26;
            detail.style.paddingRight = 26;
            detail.style.paddingTop = 22;
            detail.style.overflow = Overflow.Hidden;
            body.Add(detail);
        }

        static VisualElement Grid(VisualElement parent, float height)
        {
            var scroll = new ScrollView(ScrollViewMode.Vertical);
            scroll.style.height = height;
            scroll.style.width = Columns * (Cell + 4) + 16;
            var content = scroll.contentContainer;
            content.style.flexDirection = FlexDirection.Row;
            content.style.flexWrap = Wrap.Wrap;
            parent.Add(scroll);
            return content;
        }

        static void Border(VisualElement e, float width, Color color)
        {
            e.style.borderTopWidth = width;
            e.style.borderBottomWidth = width;
            e.style.borderLeftWidth = width;
            e.style.borderRightWidth = width;
            e.style.borderTopColor = color;
            e.style.borderBottomColor = color;
            e.style.borderLeftColor = color;
            e.style.borderRightColor = color;
        }

        // ------------------------------------------------------------------------------------------------ dados

        /// <summary>Le o save (pelo core) e redesenha tudo.</summary>
        public void Refresh()
        {
            if (!open || Rules == null || !GameSession.Save.HasSave) return;
            var save = GameSession.Save.Current;
            backpack = save.ListItems(0, ItemContainer.Backpack);
            stash = save.ListItems(0, ItemContainer.Stash);
            equipment = save.Equipment(0);
            var info = save.Inventory(Rules, 0);
            var hiddenBackpack = backpack.RemoveAll(i => pendingDiscards.ContainsKey(i.Uid)); // descarte na janela de desfazer: ja some da grade
            var hiddenStash = stash.RemoveAll(i => pendingDiscards.ContainsKey(i.Uid));
            backpackTitle.text = Loc.Get("ui.inventory.backpack").Replace("{used}", (info.BackpackUsed - hiddenBackpack).ToString()).Replace("{cap}", info.BackpackCapacity.ToString());
            backpackTitle.style.color = info.BackpackUsed - hiddenBackpack >= info.BackpackCapacity ? ScreenKit.Bad : ScreenKit.Gold;
            stashTitle.text = Loc.Get("ui.inventory.stash").Replace("{used}", (info.StashUsed - hiddenStash).ToString()).Replace("{cap}", info.StashCapacity.ToString());

            backpackGrid.Clear();
            for (var i = 0; i < info.BackpackCapacity; i++)
                backpackGrid.Add(ItemCell(i < backpack.Count ? backpack[i] : null, "backpack"));
            stashGrid.Clear();
            if (InRefuge)
            {
                stashTitle.style.color = ScreenKit.Gold;
                for (var i = 0; i < info.StashCapacity; i++) stashGrid.Add(ItemCell(i < stash.Count ? stash[i] : null, "stash"));
            }
            else
            {
                stashTitle.text = Loc.Get("ui.inventory.stash_refuge_only");
                stashTitle.style.color = ScreenKit.Muted;
            }
            BuildSlots();
            RefreshStats();
            if (selected != null && FindByUid(selected.Uid) == null && !IsEquipped(selected.Uid)) selected = null;
            ShowDetail(selected);
            if (doll != null) doll.Refresh();
        }

        ItemInstanceInfo FindByUid(ulong uid)
        {
            foreach (var item in backpack) if (item.Uid == uid) return item;
            foreach (var item in stash) if (item.Uid == uid) return item;
            return null;
        }

        bool IsEquipped(ulong uid)
        {
            foreach (var item in equipment) if (item != null && item.Uid == uid) return true;
            return false;
        }

        // ------------------------------------------------------------------------------------------------ celulas

        static string RarityClass(ItemRarity rarity)
        {
            switch (rarity)
            {
                case ItemRarity.Magic: return "art-slot--magic";
                case ItemRarity.Rare: return "art-slot--rare";
                case ItemRarity.Unique: return "art-slot--unique";
                default: return "art-slot--common";
            }
        }

        static readonly Color SelectedTint = new Color(1.35f, 1.2f, 0.8f, 1f);

        /// <summary>Icone do item (icones_itens_01, por base) sobre o slot; sem icone cai nas iniciais da base.</summary>
        void AddItemIcon(VisualElement cell, ItemInstanceInfo item, float size)
        {
            var icon = UiArt.IconFor(item);
            if (icon != null)
            {
                var image = new VisualElement { name = "icon" };
                image.style.width = size;
                image.style.height = size;
                image.style.backgroundImage = new StyleBackground(icon);
                image.pickingMode = PickingMode.Ignore;
                cell.Add(image);
                return;
            }
            var glyph = ScreenKit.Line(cell, ItemText.Glyph(Loc, item), 22, ItemText.RarityColor(item.Rarity), true);
            glyph.style.marginTop = 0;
            glyph.pickingMode = PickingMode.Ignore;
        }

        VisualElement ItemCell(ItemInstanceInfo item, string from)
        {
            var cell = new VisualElement { name = "cell" };
            cell.style.width = Cell;
            cell.style.height = Cell;
            cell.style.marginRight = 4;
            cell.style.marginBottom = 4;
            cell.style.alignItems = Align.Center;
            cell.style.justifyContent = Justify.Center;
            cell.AddToClassList(item != null ? RarityClass(item.Rarity) : "art-slot--empty");
            if (item == null) return cell;
            cell.userData = item;
            AddItemIcon(cell, item, Cell - 14);
            if (selected != null && selected.Uid == item.Uid) cell.style.unityBackgroundImageTintColor = SelectedTint;
            // seta de melhora ou piora (do core) no canto, sem precisar de Shift
            if (from == "backpack")
            {
                var verdict = ItemText.CompareVerdict(GameSession.Save.Current.Compare(Rules, 0, item.Uid));
                if (verdict != 0)
                {
                    var arrow = ScreenKit.Line(cell, verdict > 0 ? "▲" : "▼", 14, verdict > 0 ? ScreenKit.Good : ScreenKit.Bad, true);
                    arrow.style.position = Position.Absolute;
                    arrow.style.right = 4;
                    arrow.style.top = -2;
                    arrow.pickingMode = PickingMode.Ignore;
                }
            }
            cell.RegisterCallback<PointerEnterEvent>(_ => ShowDetail(item, from));
            cell.RegisterCallback<PointerLeaveEvent>(_ => ShowDetail(selected, selectedFrom));
            cell.RegisterCallback<PointerDownEvent>(e =>
            {
                if (e.button == 1 && from == "backpack") { SelectItem(item, from); EquipSelected(); return; } // botao direito equipa
                if (e.clickCount >= 2 && from == "backpack") { SelectItem(item, from); EquipSelected(); return; }  // duplo clique tambem
                SelectItem(item, from);
            });
            return cell;
        }

        /// <summary>Posicoes do prototipo (docs/16 S-05): so as habilitadas pelo core aparecem; as sem conteudo (maos, amuleto, aneis, cinto) ficam escondidas.</summary>
        void BuildSlots()
        {
            slotsColumn.Clear();
            var order = new[] { "main_hand", "head", "body", "hands", "legs", "feet", "off_hand", "amulet", "ring", "ring2", "belt" };
            foreach (var name in order)
            {
                var index = ItemSlots.IndexOf(name);
                if (!SaveGame.SlotEnabled(Rules, index)) continue;
                slotsColumn.Add(SlotCell(name, index));
            }
        }

        VisualElement SlotCell(string slotName, int index)
        {
            var item = equipment[index];
            var cell = new VisualElement { name = "slot-" + slotName };
            cell.style.width = Cell + 8;
            cell.style.height = Cell + 8;
            cell.style.marginBottom = 6;
            cell.style.alignItems = Align.Center;
            cell.style.justifyContent = Justify.Center;
            cell.AddToClassList(item != null ? RarityClass(item.Rarity) : "art-slot--empty");
            if (item == null)
            {
                // posicao vazia: icone-fantasma da peca (o boneco mostra o corpo nu)
                var ghost = UiArt.Icon(UiArt.IconName(null, false, slotName));
                if (ghost != null)
                {
                    var image = new VisualElement { name = "ghost" };
                    image.style.width = Cell - 10;
                    image.style.height = Cell - 10;
                    image.style.backgroundImage = new StyleBackground(ghost);
                    image.style.opacity = 0.22f;
                    image.pickingMode = PickingMode.Ignore;
                    cell.Add(image);
                }
            }
            var name = ScreenKit.Line(cell, Loc.Get("slot." + slotName + ".name"), 11, ScreenKit.Muted);
            name.style.position = Position.Absolute;
            name.style.bottom = 0;
            name.style.marginTop = 0;
            name.pickingMode = PickingMode.Ignore;
            if (item != null)
            {
                cell.userData = item;
                AddItemIcon(cell, item, Cell - 10);
                var from = "slot:" + index;
                cell.RegisterCallback<PointerEnterEvent>(_ => ShowDetail(item, from));
                cell.RegisterCallback<PointerLeaveEvent>(_ => ShowDetail(selected, selectedFrom));
                cell.RegisterCallback<PointerDownEvent>(e =>
                {
                    SelectItem(item, from);
                    if (e.button == 1 || e.clickCount >= 2) UnequipSelected();   // botao direito / duplo clique desequipa
                });
                if (selected != null && selected.Uid == item.Uid) cell.style.unityBackgroundImageTintColor = SelectedTint;
            }
            return cell;
        }

        // ------------------------------------------------------------------------------------------------ atributos e recursos

        static readonly (StatId id, string key)[] StatLines =
        {
            (StatId.Life, "life"), (StatId.LifeRegen, "life_regen"), (StatId.Armor, "armor"), (StatId.CritChance, "crit_chance"),
            (StatId.AttackSpeed, "attack_speed"), (StatId.MoveSpeed, "move_speed"), (StatId.ResistFire, "resist_fire"),
        };

        /// <summary>Painel de atributos (valores do core: o bloco de atributos do heroi), Ouro, Lascas e Cargas do Marco (leitura do save).</summary>
        void RefreshStats()
        {
            if (statsPanel == null) return;
            statsPanel.Clear();
            var stats = hero != null && hero.Logic != null ? hero.Logic.Self.Stats : null;
            if (stats != null)
            {
                ScreenKit.Line(statsPanel, Loc.Get("ui.inventory.stats"), 20, ScreenKit.Gold, true);
                foreach (var (id, key) in StatLines)
                {
                    var row = ScreenKit.Row(statsPanel);
                    row.name = "stat-" + key;
                    var label = ScreenKit.Line(row, ItemText.StatName(Loc, key), 17, ScreenKit.Muted);
                    label.style.marginTop = 1;
                    var value = ScreenKit.Line(row, ItemText.StatValue(key, stats.Get(id)), 17, ScreenKit.Text, true);
                    value.style.marginTop = 1;
                }
            }
            var snap = SaveReadout.Read(Rules, ExpeditionConfig.CryptMap);
            if (!snap.Valid) return;
            var title = ScreenKit.Line(statsPanel, Loc.Get("ui.inventory.resources"), 20, ScreenKit.Gold, true);
            title.style.marginTop = 8;
            ResourceRow("gold", "icon_gold", Loc.Get("ui.common.gold"), Loc.FormatInteger(snap.Gold));
            ResourceRow("shards", "icon_shards", Loc.Get("ui.inventory.shards"), Loc.FormatInteger(snap.Shards));
        }

        void ResourceRow(string name, string iconName, string label, string value)
        {
            var row = ScreenKit.Row(statsPanel);
            row.name = "res-" + name;
            var left = new VisualElement();
            left.style.flexDirection = FlexDirection.Row;
            left.style.alignItems = Align.Center;
            row.Add(left);
            var icon = UiArt.Icon(iconName);
            if (icon != null)
            {
                var image = new VisualElement();
                image.style.width = 26;
                image.style.height = 26;
                image.style.marginRight = 6;
                image.style.backgroundImage = new StyleBackground(icon);
                left.Add(image);
            }
            ScreenKit.Line(left, label, 17, ScreenKit.Muted).style.marginTop = 0;
            ScreenKit.Line(row, value, 19, ScreenKit.Gold, true).style.marginTop = 0;
        }

        // ------------------------------------------------------------------------------------------------ selecao e acoes

        public void SelectItem(ItemInstanceInfo item, string from)
        {
            selected = item;
            selectedFrom = from;
            Refresh();
        }

        /// <summary>Teste e UI: seleciona o item da Mochila pelo uid.</summary>
        public bool SelectUid(ulong uid)
        {
            var item = FindByUid(uid);
            if (item == null) return false;
            SelectItem(item, "backpack");
            return true;
        }

        public bool EquipSelected()
        {
            if (selected == null || Rules == null) return false;
            var outcome = InventoryOps.Equip(root, hero, selected.Uid);
            if (outcome.Ok)
            {
                ScreenHost.Toast(ScreenKit.Fmt(Loc, "ui.inventory.done_equipped", ("item", ItemText.Name(Loc, Rules, selected))), ToastKind.Item);
            }
            else if (outcome.Result == InvResult.SlotMismatch || outcome.Result == InvResult.SlotLocked)
            {
                ScreenHost.Toast(Loc.Get("ui.inventory.slot_mismatch"), ToastKind.Error);
            }
            else if (outcome.Result == InvResult.Full)
            {
                ScreenHost.Toast(Loc.Get("ui.inventory.full"), ToastKind.Error);
            }
            selected = null;
            Refresh();
            return outcome.Ok;
        }

        public bool UnequipSelected()
        {
            if (selected == null || selectedFrom == null || !selectedFrom.StartsWith("slot:")) return false;
            var slot = int.Parse(selectedFrom.Substring(5));
            var name = ItemText.Name(Loc, Rules, selected);
            var outcome = InventoryOps.Unequip(root, hero, slot);
            if (outcome.Ok) ScreenHost.Toast(ScreenKit.Fmt(Loc, "ui.inventory.done_unequipped", ("item", name)), ToastKind.Item);
            else if (outcome.Result == InvResult.Full) ScreenHost.Toast(Loc.Get("ui.inventory.full"), ToastKind.Error);
            selected = null;
            Refresh();
            return outcome.Ok;
        }

        public bool DiscardSelected()
        {
            if (selected == null) return false;
            var container = selectedFrom == "stash" ? ItemContainer.Stash : ItemContainer.Backpack;
            var name = ItemText.Name(Loc, Rules, selected);
            var result = InventoryOps.Discard(root, container, selected.Uid);
            if (result == InvResult.Ok) ScreenHost.Toast(ScreenKit.Fmt(Loc, "ui.inventory.done_discarded", ("item", name)), ToastKind.Item);
            selected = null;
            CloseModal();
            Refresh();
            return result == InvResult.Ok;
        }

        void MoveSelected(ItemContainer to)
        {
            if (selected == null) return;
            var result = InventoryOps.Move(root, selected.Uid, to);
            if (result == InvResult.Full) ScreenHost.Toast(Loc.Get(to == ItemContainer.Backpack ? "ui.inventory.full" : "ui.inventory.full"), ToastKind.Error);
            selected = null;
            Refresh();
        }

        // ------------------------------------------------------------------------------------------------ detalhes (tooltip)

        void ShowDetail(ItemInstanceInfo item, string from = null)
        {
            if (detail == null) return;
            detail.Clear();
            if (item == null)
            {
                ScreenKit.Line(detail, Loc.Get("ui.inventory.select_hint"), 18, ScreenKit.Muted);
                return;
            }
            var color = ItemText.RarityColor(item.Rarity);
            var name = ScreenKit.Line(detail, ItemText.Name(Loc, Rules, item), 26, color, true);
            name.name = "item-name";
            ScreenKit.Line(detail, ItemText.RarityLine(Loc, Rules, item), 18, color).name = "item-rarity";
            foreach (var (text, lineColor) in ItemText.BodyLines(Loc, Rules, item)) ScreenKit.Line(detail, text, 19, lineColor);

            var save = GameSession.Save.Current;
            var isEquipped = IsEquipped(item.Uid);
            if (!isEquipped)
            {
                var compare = save.Compare(Rules, 0, item.Uid);
                var lines = ItemText.CompareLines(Loc, compare);
                var header = ScreenKit.Line(detail, Loc.Get(compare.EquippedUid == 0 ? "ui.item.compare_empty" : "ui.item.compare_header"), 17, ScreenKit.Gold, true);
                header.style.marginTop = 14;
                foreach (var (text, lineColor) in lines) ScreenKit.Line(detail, text, 19, lineColor).name = "compare-line";
            }
            var value = save.SellValue(Rules, 0, item.Uid);
            var sell = ScreenKit.Line(detail, Loc.Get("ui.item.sell_value").Replace("{gold}", value.ToString()), 18, ScreenKit.Muted);
            sell.name = "sell-value";
            sell.style.marginTop = 10;

            // acoes do item SELECIONADO (o tooltip de passar o mouse so mostra)
            if (selected != null && selected.Uid == item.Uid)
            {
                var row = ScreenKit.Row(detail);
                row.style.marginTop = 14;
                row.style.flexWrap = Wrap.Wrap;
                if (isEquipped)
                {
                    ScreenKit.SmallButton(row, Loc.Get("ui.inventory.unequip"), () => UnequipSelected()).name = "act-unequip";
                }
                else
                {
                    if (selectedFrom == "backpack" || selectedFrom == "stash")
                    {
                        if (selectedFrom == "backpack") ScreenKit.SmallButton(row, Loc.Get("ui.inventory.equip"), () => EquipSelected()).name = "act-equip";
                        if (InRefuge) ScreenKit.SmallButton(row, Loc.Get(selectedFrom == "backpack" ? "ui.inventory.to_stash" : "ui.inventory.to_backpack"), () => MoveSelected(selectedFrom == "backpack" ? ItemContainer.Stash : ItemContainer.Backpack));
                        ScreenKit.SmallButton(row, Loc.Get("ui.inventory.discard"), AskDiscard).name = "act-discard";
                    }
                }
            }
        }

        void AskDiscard()
        {
            if (selected == null) return;
            // Comum: sem confirmacao, com 5 s para desfazer (docs/16 S-07). Magico e Raro: modal. Unico: segurar 1 s.
            if (selected.Rarity == ItemRarity.Normal)
            {
                QueueDiscard();
                return;
            }
            CloseModal();
            modal = new VisualElement { name = "discard-modal" };
            modal.style.position = Position.Absolute;
            modal.style.left = 0;
            modal.style.right = 0;
            modal.style.top = 0;
            modal.style.bottom = 0;
            modal.style.alignItems = Align.Center;
            modal.style.justifyContent = Justify.Center;
            modal.style.backgroundColor = new Color(0f, 0f, 0f, 0.55f);
            var card = MenuUi.Card(modal);
            ScreenKit.Line(card, ScreenKit.Fmt(Loc, "ui.inventory.discard_confirm", ("item", ItemText.Name(Loc, Rules, selected))), 24);
            var row = ScreenKit.Row(card);
            // Unico protegido: segurar 1 s (docs/16 S-07)
            if (selected.IsUnique) ScreenKit.HoldButton(row, Loc.Get("ui.common.confirm"), 1f, () => DiscardSelected()).name = "confirm-discard";
            else ScreenKit.SmallButton(row, Loc.Get("ui.common.confirm"), () => DiscardSelected()).name = "confirm-discard";
            ScreenKit.SmallButton(row, Loc.Get("ui.common.cancel"), CloseModal);
            screen.Add(modal);
        }

        void CloseModal()
        {
            if (modal != null) modal.RemoveFromHierarchy();
            modal = null;
        }

        /// <summary>Teste: descarta o selecionado como o jogador (Comum: janela de desfazer, confirmada ao fim; Magico e Raro: modal confirmado).</summary>
        public void ConfirmDiscardForTest()
        {
            AskDiscard();
            if (modal != null) DiscardSelected();
            else FlushPendingDiscards();
        }

        // ------------------------------------------------------------------------------------------------ desfazer (5 s)

        public int PendingDiscardCount => pendingDiscards.Count;

        /// <summary>
        /// Descarte de item Comum com janela de desfazer: o item some da grade na hora, mas o descarte real (core) so acontece quando a janela
        /// fecha (5 s, ao fechar o inventario ou trocar de area). Desfazer so tira o item da lista de pendentes. O core nao tem "restaurar".
        /// </summary>
        void QueueDiscard()
        {
            if (selected == null) return;
            var uid = selected.Uid;
            var container = selectedFrom == "stash" ? ItemContainer.Stash : ItemContainer.Backpack;
            var name = ItemText.Name(Loc, Rules, selected);
            pendingDiscards[uid] = container;
            selected = null;
            AddUndoBar(uid, name);
            Refresh();
        }

        void AddUndoBar(ulong uid, string itemName)
        {
            if (undoColumn == null) return;
            var bar = new VisualElement { name = "undo-bar" };
            bar.style.flexDirection = FlexDirection.Row;
            bar.style.alignItems = Align.Center;
            bar.style.marginTop = 4;
            bar.style.paddingLeft = 12;
            bar.style.backgroundColor = new Color(0.07f, 0.06f, 0.09f, 0.95f);
            ScreenKit.Line(bar, ScreenKit.Fmt(Loc, "ui.inventory.done_discarded", ("item", itemName)), 20).style.marginTop = 0;
            ScreenKit.SmallButton(bar, Loc.Get("ui.common.undo"), () => UndoDiscard(uid)).name = "undo-discard";
            undoColumn.Add(bar);
            undoBars[uid] = bar;
            bar.schedule.Execute(() => CommitDiscard(uid)).StartingIn((long)(UndoSeconds * 1000f));
        }

        /// <summary>Desfaz o descarte pendente (volta a aparecer na grade).</summary>
        public bool UndoDiscard(ulong uid)
        {
            if (!pendingDiscards.Remove(uid)) return false;
            RemoveUndoBar(uid);
            Refresh();
            return true;
        }

        void CommitDiscard(ulong uid)
        {
            if (!pendingDiscards.TryGetValue(uid, out var container)) return;
            pendingDiscards.Remove(uid);
            RemoveUndoBar(uid);
            InventoryOps.Discard(root, container, uid);
            Refresh();
        }

        void RemoveUndoBar(ulong uid)
        {
            if (undoBars.TryGetValue(uid, out var bar)) bar.RemoveFromHierarchy();
            undoBars.Remove(uid);
        }

        /// <summary>Confirma agora todos os descartes ainda na janela de desfazer (ao fechar o inventario).</summary>
        public void FlushPendingDiscards()
        {
            foreach (var uid in new List<ulong>(pendingDiscards.Keys)) CommitDiscard(uid);
        }
    }
}
