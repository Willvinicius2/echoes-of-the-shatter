using System;
using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// SO_LootBeam (docs/03 secao 2.3 e tokens <c>juice.loot_beam.*</c>): como cada raridade aparece no chao. Magico = brilho no item (raio 25 cm);
    /// Raro = coluna de raio 20 cm x 250 cm; Unico = coluna de raio 30 cm x 500 cm com pulso de 800 ms. Comum: nada. Dado de apresentacao (nao e
    /// balanceamento); o asset e gerado dos tokens pelo builder.
    /// </summary>
    [CreateAssetMenu(menuName = "Echoes/Loot Beam", fileName = "SO_LootBeam")]
    public sealed class LootBeamSettings : ScriptableObject
    {
        [Serializable]
        public struct Tier
        {
            public Color color;
            public float radiusMeters;
            public float heightMeters;
            public float glowRadiusMeters;
            public float pulseSeconds;
        }

        public Tier magic, rare, unique;
        public Material beamMaterial;
        public Material glowMaterial;
        public Material markerMaterial;
        [Tooltip("Tamanho (m) do marcador do item no chao enquanto nao ha modelo 3D de item (asset ART-ITEM-GROUND).")]
        public float placeholderSize = 0.35f;
        public float pickupRadiusMeters = 1.2f;
        public float interactRadiusMeters = 3f;

        public bool TryGet(int rarity, out Tier tier)
        {
            switch (rarity)
            {
                case 1: tier = magic; return true;
                case 2: tier = rare; return true;
                case 3: tier = unique; return true;
                default: tier = default; return false;
            }
        }
    }
}
