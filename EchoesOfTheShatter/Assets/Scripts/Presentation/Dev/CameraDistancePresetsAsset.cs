using System;
using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Presets de distância da câmera para o teste de escala (ferramenta de desenvolvimento). Dado de
    /// apresentação, fora do CSV de balanceamento. Crie em Assets/Data/Presentation
    /// (Create ▸ Echoes ▸ Camera Distance Presets) ou use o menu Echoes ▸ Montar cena base.
    /// </summary>
    [CreateAssetMenu(menuName = "Echoes/Camera Distance Presets", fileName = "SO_CameraDistancePresets")]
    public sealed class CameraDistancePresetsAsset : ScriptableObject
    {
        [Serializable]
        public struct Preset
        {
            [Tooltip("Rótulo técnico, só para o inspetor.")]
            public string label;
            [Tooltip("Distância da câmera ao alvo, em metros.")]
            public float distance;
        }

        [Tooltip("F1 a F4, nesta ordem.")]
        public Preset[] presets =
        {
            new Preset { label = "atual", distance = 42f },
            new Preset { label = "mais longe", distance = 56f },
            new Preset { label = "ARPG de PC", distance = 66f },
            new Preset { label = "MMO", distance = 80f },
        };
        [Tooltip("Preset aplicado ao iniciar (índice 0-based).")]
        [Min(0)] public int initialPreset = 1;
        public float minDistance = 30f;
        public float maxDistance = 100f;
        [Tooltip("Passo da roda do mouse e de PageUp/PageDown.")]
        public float step = 2f;
        [Tooltip("FOV vertical aplicado com a distância (14,2° = 25° horizontal em 16:9).")]
        public float verticalFieldOfView = 14.2f;
        [Tooltip("Plano de corte distante = distância + esta margem.")]
        public float farClipMargin = 80f;
    }
}
