using System;
using System.Collections.Generic;
using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>Espacos visuais do heroi modular (docs/04, 17.4). Os nomes seguem o item: Chest = slot body do core.</summary>
    public enum HeroPartSlot { Head = 0, Chest = 1, Hands = 2, Legs = 3, Feet = 4 }

    /// <summary>Regioes do corpo base (uma malha cada, Body_Head... Body_Feet). Bit por regiao.</summary>
    [Flags]
    public enum BodyRegion
    {
        None = 0, Head = 1, Torso = 2, Arms = 4, Hands = 8, Legs = 16, Feet = 32,
        All = Head | Torso | Arms | Hands | Legs | Feet,
    }

    /// <summary>
    /// Peca de armadura de um heroi (SO_HeroPart_Heroi_Slot_Conjunto): slot, visualSetId, regioes do corpo que esconde e o prefab com o
    /// SkinnedMeshRenderer. Dado de apresentacao; o core so conhece o item e o seu visualSetId.
    /// </summary>
    [CreateAssetMenu(menuName = "Echoes/Hero Part", fileName = "SO_HeroPart_Warrior_Chest_Starter")]
    public sealed class HeroPart : ScriptableObject
    {
        public HeroPartSlot slot;
        [Tooltip("vset.starter, vset.iron_guard...")]
        public string visualSetId = HeroPartCatalog.StarterSet;
        [Tooltip("Regioes do corpo base que ficam escondidas com a peca vestida.")]
        public BodyRegion hidesRegions;
        [Tooltip("Prefab da peca (FBX com o SkinnedMeshRenderer e o material do conjunto).")]
        public GameObject prefab;

        /// <summary>Nome do slot no core (item_bases.csv.slot) para este espaco.</summary>
        public static string CoreSlotName(HeroPartSlot slot)
        {
            switch (slot)
            {
                case HeroPartSlot.Head: return "head";
                case HeroPartSlot.Chest: return "body";
                case HeroPartSlot.Hands: return "hands";
                case HeroPartSlot.Legs: return "legs";
                default: return "feet";
            }
        }

        public static bool TryFromCoreSlot(string coreSlot, out HeroPartSlot slot)
        {
            for (var i = 0; i <= (int)HeroPartSlot.Feet; i++)
            {
                if (CoreSlotName((HeroPartSlot)i) == coreSlot)
                {
                    slot = (HeroPartSlot)i;
                    return true;
                }
            }
            slot = HeroPartSlot.Head;
            return false;
        }
    }
}
