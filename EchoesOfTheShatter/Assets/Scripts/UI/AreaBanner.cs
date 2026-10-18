using Echoes.Core;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Echoes.UI
{
    /// <summary>Faixa com o nome da area por 3 s ao entrar (F-06). O nome vem do Loc pela cena (Refugio ou Cripta).</summary>
    public sealed class AreaBanner : MonoBehaviour
    {
        /// <summary>Segundos da faixa (docs/16 F-06).</summary>
        public const float Seconds = 3f;

        [SerializeField] GameRoot root;

        /// <summary>Chave de Loc do nome da area da cena (null se a cena nao e uma area).</summary>
        public static string NameKeyFor(string sceneName)
        {
            if (sceneName == GameFlow.RefugeScene) return "area.refuge.name";
            if (sceneName == GameFlow.CriptaScene) return "map.act1.crypt.name";
            return null;
        }

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            var key = NameKeyFor(SceneManager.GetActiveScene().name);
            if (root == null || key == null) return;
            ScreenHost.Banner(ScreenKit.Fmt(root.Localization, "ui.hud.area_name", ("area", root.Localization.Get(key))), null, Seconds);
        }
    }
}
