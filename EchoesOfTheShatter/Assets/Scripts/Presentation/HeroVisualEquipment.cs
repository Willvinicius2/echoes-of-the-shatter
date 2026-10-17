using System.Collections.Generic;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Resolve o conjunto visual de um item (docs/04, 17.4) pelo CORE: <c>shatter_item_visual_set_id</c> (uniques.visualSetId, depois
    /// item_bases.visualSetId, depois vset.starter). A Unity nao le mais o CSV; so decide o slot visual modular pelo slot do item base.
    /// </summary>
    public static class VisualSetResolver
    {
        /// <summary>Slot modular e conjunto do item. Arma, anel etc. (sem peca modular): false.</summary>
        public static bool TryResolve(IRulesCore rules, string baseId, string uniqueIdOrNull, out HeroPartSlot slot, out string visualSetId)
        {
            slot = HeroPartSlot.Head;
            visualSetId = HeroPartCatalog.StarterSet;
            if (rules == null || string.IsNullOrEmpty(baseId)) return false;
            var info = rules.FindItemBase(baseId);
            if (info == null || !HeroPart.TryFromCoreSlot(info.Slot, out slot)) return false;
            var set = rules.ItemVisualSetId(baseId, uniqueIdOrNull ?? string.Empty);
            visualSetId = string.IsNullOrEmpty(set) ? HeroPartCatalog.StarterSet : set;
            return true;
        }
    }

    /// <summary>
    /// Liga o equipamento do heroi (o SAVE, pelo core: base e Unico de cada item equipado) ao ModularCharacter pelo conjunto visual do core:
    /// cada item de slot visual veste a peca do seu conjunto; o resto fica em vset.starter (a armadura inicial aprovada). Sem save (cena aberta
    /// direto no editor), usa as bases de <see cref="HeroController.EquipmentIds"/>. <see cref="Refresh"/> reaplica depois de equipar/desequipar.
    /// </summary>
    [DefaultExecutionOrder(-10)]
    [DisallowMultipleComponent]
    public sealed class HeroVisualEquipment : MonoBehaviour
    {
        [SerializeField] HeroController hero;
        [SerializeField] ModularCharacter modular;
        [SerializeField] GameRoot root;

        void Start()
        {
            if (hero == null) hero = GetComponentInParent<HeroController>();
            if (modular == null) modular = GetComponentInChildren<ModularCharacter>();
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            Refresh();
        }

        /// <summary>Reaplica o equipamento atual (save pelo core, ou as bases do heroi sem save).</summary>
        public void Refresh()
        {
            if (modular == null) return;
            var rules = root != null && root.Rules != null ? root.Rules.Core : null;
            var items = new List<(string baseId, string uniqueId)>();
            var native = GameSession.NativeRules(root);
            var fromSave = native != null && GameSession.Save.HasSave;
            if (fromSave)
            {
                foreach (var item in GameSession.Save.Current.Equipment(0))
                    if (item != null) items.Add((item.BaseId, item.UniqueId));
            }
            else if (hero != null && hero.EquipmentIds != null)
            {
                foreach (var id in hero.EquipmentIds) items.Add((id, string.Empty));
            }
            Apply(items, rules, fromSave); // com save, posicao vazia = corpo base nu (docs/16 S-05); sem save, o starter
        }

        /// <summary>Veste os itens (base e Unico) nos slots visuais; slots sem item ficam no starter.</summary>
        public void Apply(IEnumerable<(string baseId, string uniqueId)> items, IRulesCore rules, bool emptySlotsAreNude = false)
        {
            if (modular == null) modular = GetComponentInChildren<ModularCharacter>();
            modular.Build();
            var dressed = new HashSet<HeroPartSlot>();
            if (items != null)
            {
                foreach (var (baseId, uniqueId) in items)
                {
                    if (!VisualSetResolver.TryResolve(rules, baseId, uniqueId, out var slot, out var set)) continue; // arma, anel...: sem visual modular
                    modular.Equip(slot, set);
                    dressed.Add(slot);
                }
            }
            for (var i = 0; i <= (int)HeroPartSlot.Feet; i++)
            {
                if (dressed.Contains((HeroPartSlot)i)) continue;
                if (emptySlotsAreNude) modular.Unequip((HeroPartSlot)i);
                else modular.Equip((HeroPartSlot)i, HeroPartCatalog.StarterSet);
            }
        }
    }
}
