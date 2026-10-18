using System;
using System.IO;
using UnityEngine;

namespace Echoes.Core
{
    /// <summary>Intensidade do tremor de tela (RF-62; docs/16 S-11, aba Acessibilidade).</summary>
    public enum ShakeMode { Normal = 0, Reduced = 1, Off = 2 }

    /// <summary>
    /// Configuracoes do jogador em arquivo proprio (<c>settings.json</c> em persistentDataPath, separado do save): idioma, tremor de tela e
    /// reducao de flashes. Os remapeamentos de teclas ficam em <c>bindings.json</c> (PlayerInputHandler). Leitura tolerante: arquivo ausente ou
    /// invalido volta aos padroes sem erro.
    /// </summary>
    public static class UserSettings
    {
        [Serializable]
        sealed class Data
        {
            public string culture = string.Empty;
            public int shake;
            public bool reduceFlashes;
        }

        /// <summary>Fracao da amplitude no modo Reduzido (preferencia de acessibilidade, nao balanceamento de jogo).</summary>
        public const float ReducedShakeFactor = 0.4f;

        static Data data;
        static string pathOverride;

        public static event Action Changed;

        public static string FilePath => pathOverride ?? Path.Combine(Application.persistentDataPath, "settings.json");

        /// <summary>Testes: usa outro arquivo e relê.</summary>
        public static void UseFile(string path)
        {
            pathOverride = path;
            data = null;
        }

        static Data Current
        {
            get
            {
                if (data != null) return data;
                data = new Data();
                try
                {
                    if (File.Exists(FilePath)) JsonUtility.FromJsonOverwrite(File.ReadAllText(FilePath), data);
                }
                catch (Exception e)
                {
                    Debug.LogWarning("[Settings] Arquivo de configuracoes ignorado: " + e.Message);
                    data = new Data();
                }
                return data;
            }
        }

        /// <summary>Coluna de idioma salva ("pt_BR", "en") ou vazio quando o jogador nunca escolheu.</summary>
        public static string Culture
        {
            get => Current.culture ?? string.Empty;
            set { Current.culture = value ?? string.Empty; Save(); }
        }

        public static ShakeMode Shake
        {
            get => Enum.IsDefined(typeof(ShakeMode), Current.shake) ? (ShakeMode)Current.shake : ShakeMode.Normal;
            set { Current.shake = (int)value; Save(); }
        }

        public static bool ReduceFlashes
        {
            get => Current.reduceFlashes;
            set { Current.reduceFlashes = value; Save(); }
        }

        /// <summary>Multiplicador da amplitude do tremor de camera: 1, ReducedShakeFactor ou 0.</summary>
        public static float ShakeFactor
        {
            get
            {
                switch (Shake)
                {
                    case ShakeMode.Off: return 0f;
                    case ShakeMode.Reduced: return ReducedShakeFactor;
                    default: return 1f;
                }
            }
        }

        static void Save()
        {
            try
            {
                var dir = Path.GetDirectoryName(FilePath);
                if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
                File.WriteAllText(FilePath, JsonUtility.ToJson(Current, true));
            }
            catch (Exception e)
            {
                Debug.LogWarning("[Settings] Nao foi possivel gravar as configuracoes: " + e.Message);
            }
            Changed?.Invoke();
        }
    }
}
