using System;
using Echoes.Interop;
using UnityEngine;

namespace Echoes.Core
{
    /// <summary>
    /// Ponto de entrada da cena (docs/04_arquitetura.md, seção 6.1). Cria os serviços em ordem fixa e
    /// os entrega por referência; não há localizador global de serviços. Descarta o motor de regras
    /// ao sair do Play.
    /// </summary>
    [DefaultExecutionOrder(-1000)]
    [DisallowMultipleComponent]
    public sealed class GameRoot : MonoBehaviour
    {
        [Tooltip("Pasta dos CSV. Vazio = StreamingAssets/Data, ou Content/Data no editor.")]
        [SerializeField] string dataDirectoryOverride = string.Empty;

        [Tooltip("Seed da sessão (runSeed). 0 = nova a cada Play. Use um valor fixo para reproduzir uma luta.")]
        [SerializeField] long fixedRunSeed;

        [Tooltip("Coluna de idioma (pt_BR, en). Vazio = idioma do sistema.")]
        [SerializeField] string cultureOverride = string.Empty;

        public EventBus Events { get; private set; }
        public RulesService Rules { get; private set; }
        public LocalizationService Localization { get; private set; }

        /// <summary>Seed da área atual; o combate deriva o fluxo Combat e o de Events dela (seção 6.2).</summary>
        public ulong RunSeed { get; private set; }

        public bool IsReady => Rules != null && Rules.IsReady;

        void Awake()
        {
            Events = new EventBus();

            var dataDirectory = ContentPaths.ResolveDataDirectory(dataDirectoryOverride);
            Localization = new LocalizationService(message => Debug.LogWarning("[Loc] " + message));
            Localization.LoadDirectory(ContentPaths.LocalizationDirectory(dataDirectory));
            var culture = string.IsNullOrEmpty(cultureOverride)
                ? LocalizationTable.CultureColumnFor(SystemLanguageCode(Application.systemLanguage))
                : cultureOverride;
            Localization.SetCulture(culture);

            Rules = new RulesService(RulesCoreFactory.CreateDefault(message => Debug.LogWarning(message)));
            if (!Rules.Initialize(dataDirectory))
            {
                Debug.LogError("[GameRoot] Regras não carregaram; o combate fica desligado. Veja os erros acima.");
            }

            RunSeed = fixedRunSeed != 0 ? (ulong)fixedRunSeed : (ulong)DateTime.UtcNow.Ticks;
        }

        void OnDestroy()
        {
            Rules?.Dispose();
            Rules = null;
            Events?.Clear();
        }

        static string SystemLanguageCode(SystemLanguage language)
        {
            switch (language)
            {
                case SystemLanguage.Portuguese: return "pt";
                case SystemLanguage.Spanish: return "es";
                default: return "en";
            }
        }
    }
}
