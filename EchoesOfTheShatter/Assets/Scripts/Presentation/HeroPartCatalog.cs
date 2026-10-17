using System;
using System.Collections.Generic;
using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>Catalogo de pecas de um heroi (SO_HeroPartCatalog_Heroi): indice (slot, visualSetId) para a peca.</summary>
    [CreateAssetMenu(menuName = "Echoes/Hero Part Catalog", fileName = "SO_HeroPartCatalog_Warrior")]
    public sealed class HeroPartCatalog : ScriptableObject
    {
        public const string StarterSet = "vset.starter";

        public string heroId = "Warrior";
        public List<HeroPart> parts = new List<HeroPart>();

        // Poucas pecas por heroi: busca linear (sem cache que possa ficar velho quando o catalogo e remontado).
        public bool TryGet(HeroPartSlot slot, string visualSetId, out HeroPart part)
        {
            foreach (var p in parts)
            {
                if (p != null && p.slot == slot && string.Equals(p.visualSetId, visualSetId ?? string.Empty, StringComparison.Ordinal))
                {
                    part = p;
                    return true;
                }
            }
            part = null;
            return false;
        }

        /// <summary>
        /// Resolucao com fallback (17.4): a peca do conjunto pedido; sem ela, a peca starter do slot (e avisa no log); sem nenhuma, null
        /// (o corpo base nu aparece naquela regiao).
        /// </summary>
        public HeroPart Resolve(HeroPartSlot slot, string visualSetId, Action<string> warn = null)
        {
            if (!string.IsNullOrEmpty(visualSetId) && TryGet(slot, visualSetId, out var part)) return part;
            if (TryGet(slot, StarterSet, out var starter))
            {
                if (!string.IsNullOrEmpty(visualSetId) && visualSetId != StarterSet)
                    warn?.Invoke($"[Modular] {heroId}: sem peca {slot}/{visualSetId}; usando {StarterSet}.");
                return starter;
            }
            return null;
        }

    }
}
