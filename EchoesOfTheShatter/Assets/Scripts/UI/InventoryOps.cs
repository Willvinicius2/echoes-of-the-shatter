using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using Echoes.Interop.Native;
using Echoes.Presentation;
using UnityEngine;

namespace Echoes.UI
{
    /// <summary>
    /// Operacoes de inventario do jogador: chamam o core (regras de posicao, capacidade, troca, ordenacao) e, se deu certo, atualizam o que o
    /// cliente mostra: o bloco de atributos do heroi (o proprio core troca so os modificadores dos itens), a arma das habilidades, o visual
    /// modular (pelo conjunto visual do core) e o save. Nenhuma regra mora aqui.
    /// </summary>
    public static class InventoryOps
    {
        static IStatBlock HeroStats(HeroController hero) => hero != null && hero.Logic != null ? hero.Logic.Self.Stats : null;

        static bool Ready(GameRoot root, out NativeRulesCore rules, out SaveGame save)
        {
            rules = GameSession.NativeRules(root);
            save = GameSession.Save != null && GameSession.Save.HasSave ? GameSession.Save.Current : null;
            return rules != null && save != null;
        }

        /// <summary>Depois de mudar o equipamento: arma do heroi, visual do boneco (heroi e previa) e save.</summary>
        public static void AfterEquipmentChange(GameRoot root, HeroController hero)
        {
            if (hero != null) hero.OnEquipmentChanged();
            foreach (var visual in Object.FindObjectsByType<HeroVisualEquipment>(FindObjectsSortMode.None)) visual.Refresh();
            var rules = GameSession.NativeRules(root);
            if (rules != null && GameSession.Save.HasSave) GameSession.Save.Save(rules);
        }

        public static EquipOutcome Equip(GameRoot root, HeroController hero, ulong uid, int slot = -1)
        {
            if (!Ready(root, out var rules, out var save)) return new EquipOutcome(InvResult.Error, -1, 0, false);
            var outcome = save.Equip(rules, 0, uid, slot, HeroStats(hero));
            if (outcome.Ok) AfterEquipmentChange(root, hero);
            return outcome;
        }

        public static EquipOutcome Unequip(GameRoot root, HeroController hero, int slot)
        {
            if (!Ready(root, out var rules, out var save)) return new EquipOutcome(InvResult.Error, -1, 0, false);
            var outcome = save.Unequip(rules, 0, slot, HeroStats(hero));
            if (outcome.Ok) AfterEquipmentChange(root, hero);
            return outcome;
        }

        public static InvResult Discard(GameRoot root, ItemContainer container, ulong uid)
        {
            if (!Ready(root, out var rules, out var save)) return InvResult.Error;
            var result = save.Discard(0, container, uid);
            if (result == InvResult.Ok) GameSession.Save.Save(rules);
            return result;
        }

        public static InvResult Move(GameRoot root, ulong uid, ItemContainer to)
        {
            if (!Ready(root, out var rules, out var save)) return InvResult.Error;
            var result = save.Move(rules, 0, uid, to);
            if (result == InvResult.Ok) GameSession.Save.Save(rules);
            return result;
        }

        public static void Sort(GameRoot root)
        {
            if (!Ready(root, out var rules, out var save)) return;
            save.Sort(rules, 0);
            GameSession.Save.Save(rules);
        }
    }
}
