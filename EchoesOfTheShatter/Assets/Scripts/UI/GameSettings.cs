using System.Collections.Generic;
using UnityEngine;

namespace Echoes.UI
{
    /// <summary>
    /// Resolução e modo de janela do jogador (RNF: configuráveis). Guardado em PlayerPrefs; a primeira execução abre em janela 1280x720.
    /// A linha de comando (-screen-width, -screen-height, -screen-fullscreen) tem prioridade do Unity e não é tocada aqui.
    /// </summary>
    public static class GameSettings
    {
        const string WidthKey = "echoes.res.w";
        const string HeightKey = "echoes.res.h";
        const string FullscreenKey = "echoes.res.fullscreen";
        public const int DefaultWidth = 1280;
        public const int DefaultHeight = 720;

        static readonly Vector2Int[] CommonSizes =
        {
            new Vector2Int(1280, 720), new Vector2Int(1600, 900), new Vector2Int(1920, 1080), new Vector2Int(2560, 1440), new Vector2Int(3840, 2160),
        };

        public static int Width => PlayerPrefs.GetInt(WidthKey, DefaultWidth);
        public static int Height => PlayerPrefs.GetInt(HeightKey, DefaultHeight);
        public static bool Fullscreen => PlayerPrefs.GetInt(FullscreenKey, 0) != 0;

        /// <summary>Tamanhos oferecidos: os comuns que cabem no monitor (mais o atual).</summary>
        public static List<Vector2Int> AvailableSizes()
        {
            var list = new List<Vector2Int>();
            var display = Screen.currentResolution;
            foreach (var size in CommonSizes)
            {
                if (size.x <= display.width && size.y <= display.height) list.Add(size);
            }
            var current = new Vector2Int(Width, Height);
            if (!list.Contains(current)) list.Add(current);
            if (list.Count == 0) list.Add(new Vector2Int(DefaultWidth, DefaultHeight));
            list.Sort((a, b) => a.x != b.x ? a.x.CompareTo(b.x) : a.y.CompareTo(b.y));
            return list;
        }

        public static void ApplySaved()
        {
            Apply(Width, Height, Fullscreen, false);
        }

        public static void Apply(int width, int height, bool fullscreen, bool save = true)
        {
            Screen.SetResolution(width, height, fullscreen ? FullScreenMode.FullScreenWindow : FullScreenMode.Windowed);
            if (!save) return;
            PlayerPrefs.SetInt(WidthKey, width);
            PlayerPrefs.SetInt(HeightKey, height);
            PlayerPrefs.SetInt(FullscreenKey, fullscreen ? 1 : 0);
            PlayerPrefs.Save();
        }

        public static void CycleResolution()
        {
            var sizes = AvailableSizes();
            var index = sizes.IndexOf(new Vector2Int(Width, Height));
            var next = sizes[(index + 1) % sizes.Count];
            Apply(next.x, next.y, Fullscreen);
        }

        public static void ToggleFullscreen()
        {
            Apply(Width, Height, !Fullscreen);
        }
    }
}
