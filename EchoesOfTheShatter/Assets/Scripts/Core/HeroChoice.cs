using System;
using UnityEngine;

namespace Echoes.Core
{
    /// <summary>
    /// Heroi escolhido: warrior, archer ou mage (classes class.warrior, class.archer e class.mage, docs/18). Cada um joga com o proprio kit, controller e
    /// habilidades. Escolhido pelo argumento -hero ou pelo botao da tela inicial (ate a selecao de classe de verdade entrar).
    /// </summary>
    public static class HeroChoice
    {
        public static readonly string[] Ids = { "warrior", "archer", "mage" };
        const string PrefsKey = "echoes.hero.preview";
        static string current;

        public static string Id
        {
            get
            {
                if (current != null) return current;
                var arg = FromArgument();
                current = Array.IndexOf(Ids, arg) >= 0 ? arg : Array.IndexOf(Ids, PlayerPrefs.GetString(PrefsKey, Ids[0])) >= 0 ? PlayerPrefs.GetString(PrefsKey, Ids[0]) : Ids[0];
                return current;
            }
            set
            {
                current = Array.IndexOf(Ids, value) >= 0 ? value : Ids[0];
                PlayerPrefs.SetString(PrefsKey, current);
            }
        }

        /// <summary>ID de conteudo da classe do heroi escolhido (class.warrior, class.archer, class.mage).</summary>
        public static string ClassId => "class." + Id;

        public static void Cycle() => Id = Ids[(Array.IndexOf(Ids, Id) + 1) % Ids.Length];

        static string FromArgument()
        {
            var args = Environment.GetCommandLineArgs();
            for (var i = 0; i < args.Length - 1; i++)
            {
                if (string.Equals(args[i], "-hero", StringComparison.OrdinalIgnoreCase)) return args[i + 1].ToLowerInvariant();
            }
            return null;
        }

        /// <summary>Chave de Loc do nome do heroi na tela inicial.</summary>
        public static string NameKey(string id) => "ui.menu.hero." + id;
    }
}
