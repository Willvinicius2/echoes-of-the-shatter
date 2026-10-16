using System;
using System.Collections.Generic;
using Echoes.Interop;
using UnityEngine;

namespace Echoes.Core
{
    /// <summary>
    /// Dono do motor de regras na sessão de jogo (docs/04_arquitetura.md, seções 6.1 e 10.4).
    /// Carrega os CSV, guarda os erros e entrega o <see cref="IRulesCore"/> ao gameplay.
    /// Hoje usa o stub em C#; a troca pela DLL acontece em <see cref="RulesCoreFactory"/>.
    /// </summary>
    public sealed class RulesService : IDisposable
    {
        readonly List<RulesError> errors = new List<RulesError>();

        public RulesService(IRulesCore core)
        {
            Core = core ?? throw new ArgumentNullException(nameof(core));
        }

        public IRulesCore Core { get; private set; }

        public bool IsReady { get; private set; }

        public IReadOnlyList<RulesError> Errors => errors;

        public string DataDirectory { get; private set; } = string.Empty;

        public bool Initialize(string dataDirectory)
        {
            DataDirectory = dataDirectory ?? string.Empty;
            errors.Clear();
            var status = Core.LoadContent(DataDirectory, errors);
            IsReady = status == RulesStatus.Ok;

            if (!IsReady)
            {
                Debug.LogError($"[Rules] Falha ao carregar o conteúdo de '{DataDirectory}' ({status}, {errors.Count} erro(s)).");
                for (var i = 0; i < errors.Count; i++) Debug.LogError("[Rules] " + errors[i]);
                return false;
            }

            Debug.Log($"[Rules] {Core.ImplementationName} carregou content_version {Core.ContentVersion} de '{DataDirectory}'.");
            if (Core.IsProvisional)
            {
                Debug.LogWarning("[Rules] Motor de regras PROVISÓRIO (stub em C#). Trocar pela DLL do ShatterCore quando a API C existir.");
                if (Core is StubRulesCore stub)
                {
                    for (var i = 0; i < stub.PendingValuesUsed.Count; i++)
                        Debug.LogWarning("[Rules] Valor provisório de docs/13 em uso (falta no CSV): " + stub.PendingValuesUsed[i]);
                }
            }
            return true;
        }

        public void Dispose()
        {
            Core?.Dispose();
            Core = null;
            IsReady = false;
        }
    }
}
