using System.Collections.Generic;
using Echoes.Interop;
using UnityEngine;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Arte final da UI (kit aprovado ui_kit_01 e icones_itens_01, recortados em Assets/Resources/UiArt): molduras 9-slice, slots por raridade,
    /// botoes e icones de item. Os valores de 9-slice saem de <c>slices.json</c> (gerado junto com os recortes). Sem o arquivo ou sem a textura
    /// o elemento fica com o estilo simples (cores), nunca quebra.
    /// </summary>
    public static class UiArt
    {
        public const string FrameOrnate = "frame_ornate";
        public const string FramePlain = "frame_plain";
        public const string SlotEmpty = "slot_empty";
        public const string SlotCommon = "slot_common";
        public const string SlotMagic = "slot_magic";
        public const string SlotRare = "slot_rare";
        public const string SlotUnique = "slot_unique";
        public const string ButtonNormal = "button_normal";
        public const string ButtonHover = "button_hover";
        public const string ButtonDisabled = "button_disabled";
        public const string Tab = "tab";
        public const string BarThin = "bar_thin";

        public readonly struct Slice
        {
            public readonly int Left, Top, Right, Bottom;
            public Slice(int l, int t, int r, int b) { Left = l; Top = t; Right = r; Bottom = b; }
        }

        static readonly Dictionary<string, Texture2D> textures = new Dictionary<string, Texture2D>();
        static Dictionary<string, Slice> slices;

        // Mapa base de item -> icone (icones_itens_01). Bases sem entrada caem no icone da posicao; sem icone, a UI mostra as iniciais.
        // TODO(asset ui.icon.hunter_bow): o Arco do Cacador ainda nao tem icone proprio (so Guerreiro no prototipo); usa a espada.
        static readonly Dictionary<string, string> iconByBase = new Dictionary<string, string>
        {
            { "item_base.iron_sword", "icon_sword" },
            { "item_base.stone_maul", "icon_hammer" },
            { "item_base.iron_helm", "icon_helm" },
            { "item_base.leather_vest", "icon_vest" },
            { "item_base.leather_gloves", "icon_gloves" },
            { "item_base.worn_boots", "icon_boots" },
            { "item_base.worn_trousers", "icon_trousers" },
            { "item_base.hunter_bow", "icon_sword" },
        };

        static readonly Dictionary<string, string> iconBySlot = new Dictionary<string, string>
        {
            { "main_hand", "icon_sword" }, { "head", "icon_helm" }, { "body", "icon_vest" },
            { "hands", "icon_gloves" }, { "legs", "icon_trousers" }, { "feet", "icon_boots" },
        };

        public static Texture2D Texture(string kitName)
        {
            return Load("UiArt/Kit/" + kitName);
        }

        static Texture2D Load(string path)
        {
            if (textures.TryGetValue(path, out var cached) && cached != null) return cached;
            var tex = Resources.Load<Texture2D>(path);
            textures[path] = tex;
            return tex;
        }

        public static Slice SliceOf(string kitName)
        {
            if (slices == null)
            {
                slices = new Dictionary<string, Slice>();
                var text = Resources.Load<TextAsset>("UiArt/Kit/slices");
                if (text != null)
                {
                    var root = MiniJson.AsObject(MiniJson.Parse(text.text));
                    foreach (var pair in root)
                    {
                        var o = MiniJson.AsObject(pair.Value);
                        slices[pair.Key] = new Slice(MiniJson.Int(o, "left", 0), MiniJson.Int(o, "top", 0), MiniJson.Int(o, "right", 0), MiniJson.Int(o, "bottom", 0));
                    }
                }
            }
            return slices.TryGetValue(kitName, out var s) ? s : default;
        }

        /// <summary>Liga a moldura 9-slice do kit ao elemento (fundo e bordas passam a ser a arte). false se a arte nao existe.</summary>
        public static bool ApplyFrame(VisualElement element, string kitName)
        {
            var tex = Texture(kitName);
            if (tex == null) return false;
            var s = SliceOf(kitName);
            element.style.backgroundColor = Color.clear;
            element.style.backgroundImage = new StyleBackground(tex);
            element.style.unitySliceLeft = s.Left;
            element.style.unitySliceTop = s.Top;
            element.style.unitySliceRight = s.Right;
            element.style.unitySliceBottom = s.Bottom;
            element.style.unitySliceScale = 1f;
            element.style.borderTopWidth = 0;
            element.style.borderBottomWidth = 0;
            element.style.borderLeftWidth = 0;
            element.style.borderRightWidth = 0;
            return true;
        }

        public static string SlotFor(ItemRarity rarity)
        {
            switch (rarity)
            {
                case ItemRarity.Magic: return SlotMagic;
                case ItemRarity.Rare: return SlotRare;
                case ItemRarity.Unique: return SlotUnique;
                default: return SlotCommon;
            }
        }

        /// <summary>Nome do icone do item: o Unico do Guardiao tem o proprio; as demais bases pelo mapa; vazio se nao ha.</summary>
        public static string IconName(string baseId, bool isUnique, string slot = null)
        {
            if (isUnique && baseId == "item_base.stone_maul") return "icon_unique_maul";
            if (baseId != null && iconByBase.TryGetValue(baseId, out var byBase)) return byBase;
            return slot != null && iconBySlot.TryGetValue(slot, out var bySlot) ? bySlot : null;
        }

        public static Texture2D Icon(string iconName)
        {
            return string.IsNullOrEmpty(iconName) ? null : Load("UiArt/Icons/" + iconName);
        }

        public static Texture2D IconFor(ItemInstanceInfo item)
        {
            return item == null ? null : Icon(IconName(item.BaseId, item.IsUnique));
        }
    }
}
